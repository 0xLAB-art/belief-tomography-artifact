#!/usr/bin/env python3
"""Build a SHA-256 immutable release manifest for the evaluation infrastructure.

The manifest is intentionally allowed to be INCOMPLETE. Missing model, prompt,
cost, latency or raw-served artifacts are reported as missing categories rather
than invented. ``--strict`` turns an INCOMPLETE package into a hard failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ragin.evaluation.release_manifest import (  # noqa: E402
    ManifestIncomplete,
    build_manifest,
)


def _files(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.exists()]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _shared_core_observed(root: Path) -> dict[str, dict[str, object]]:
    """Record shared-core hashes as *observed*, never as frozen snapshots.

    These files move under peer ownership. The manifest must not imply that the
    bytes will still match later, and no copy is made of them here.
    """
    observed: dict[str, dict[str, object]] = {}
    for relative in (
        "ragin/cycle/strict_research.py",
        "ragin/cycle/verification_deadline.py",
        "ragin/cycle/harness.py",
        "ragin/gateway/generation.py",
        "ragin/gateway/client.py",
        "ragin/hisoka/deception.py",
    ):
        path = root / relative
        if path.exists():
            observed[relative] = {
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
                "status": "OBSERVED_AT_MANIFEST_TIME_NOT_FROZEN",
            }
    return observed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--release-id",
        default="evaluation_infra_v1_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
    )
    parser.add_argument("--out-root", type=Path, default=ROOT / "docs/research/evaluation_infra_v1/releases")
    parser.add_argument(
        "--smoke-out",
        type=Path,
        nargs="+",
        default=None,
        help="one or more bounded TEST_ONLY smoke directories",
    )
    parser.add_argument(
        "--docs",
        type=Path,
        nargs="+",
        default=None,
        help="living evaluation documents to preserve in the package",
    )
    parser.add_argument(
        "--tests",
        type=Path,
        nargs="+",
        default=None,
        help="focused ablation test files to preserve in the package",
    )
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=None,
        help="read-only copy of the owned source bytes taken for this manifest",
    )
    parser.add_argument("--strict", action="store_true", help="fail if any required category is incomplete")
    args = parser.parse_args()

    eval_dir = ROOT / "ragin/evaluation"
    config_dir = ROOT / "configs/ablation/eval_v1"
    scripts = [
        ROOT / "scripts/ablation_preflight_v1.py",
        ROOT / "scripts/run_ablation_track_a_v1.py",
        ROOT / "scripts/run_ablation_track_b_v1.py",
        ROOT / "scripts/analyze_ablation_v1.py",
        ROOT / "scripts/build_ablation_human_packet_v1.py",
        ROOT / "scripts/build_ablation_release_manifest_v1.py",
    ]
    docs = args.docs or [
        ROOT / "docs/research/ABLATION_RESULTS.md",
        ROOT / "docs/research/DECISION_LAYER_VALIDITY_REPORT.md",
        ROOT / "docs/research/DECEPTION_EFFECTIVENESS_ANALYSIS.md",
        ROOT / "docs/research/REPRODUCIBILITY_REPORT.md",
    ]
    tests = args.tests or sorted((ROOT / "tests/unit").glob("test_ablation_*_v1.py"))
    snapshot_files = (
        sorted(path for path in args.snapshot_root.rglob("*") if path.is_file())
        if args.snapshot_root is not None and args.snapshot_root.exists()
        else []
    )
    artifacts_by_category: dict[str, list[Path]] = {
        "source": _files(sorted(eval_dir.glob("*.py")) + scripts + list(docs) + list(tests) + snapshot_files),
        "configs": _files(sorted(config_dir.glob("*.json"))),
        "data": _files([ROOT / "data/host_fiction.json"]),
        "seeds": _files([ROOT / "configs/ablation/eval_v1/allocation_sequence_v1.json"]),
        # Model weights, prompt bundles and cost receipts are deliberately absent
        # until a real frozen run produces them.
        "model": [],
        "prompts": [],
        "costs": [],
        "latency": [],
        "raw_served": [],
    }
    if args.smoke_out:
        for smoke in args.smoke_out:
            artifacts_by_category["latency"].extend(_files([smoke / "summary.json"]))
            artifacts_by_category["raw_served"].extend(
                sorted(path for path in smoke.rglob("*") if path.is_file() and path.name != "summary.json")
            )
    try:
        manifest = build_manifest(
            root=ROOT,
            release_id=args.release_id,
            artifacts_by_category=artifacts_by_category,
            out_root=args.out_root,
            metadata={
                "scope": "EVALUATION_INFRASTRUCTURE_ONLY",
                "measurement_status": "NOT_MEASURED",
                "package_status": "INCOMPLETE_BY_DESIGN",
                "smoke_out": [str(path) for path in (args.smoke_out or [])],
                "smoke_claim": "TEST_ONLY_B0_NATIVE_INTEGRATION_SMOKE; not an ablation",
                "snapshot_root": str(args.snapshot_root) if args.snapshot_root else None,
                "shared_core_observed_not_frozen": _shared_core_observed(ROOT),
                "readiness": "NOT_READY",
            },
            unavailable={
                "model": "no frozen generative model/checkpoint exists locally",
                "prompts": "no frozen attacker prompt bundle exists",
                "costs": "no measured provider cost exists",
                "latency": "no measured real-arm latency artifact exists"
                if not args.smoke_out
                else "only TEST_ONLY smoke latency is present; not a measured arm",
                "raw_served": "no measured B1-B3 raw served transcript exists"
                if not args.smoke_out
                else "only TEST_ONLY B0 native raw transcripts are present; not an ablation arm",
            },
            strict=args.strict,
        )
    except ManifestIncomplete as exc:
        print(json.dumps({"status": "INCOMPLETE", "strict": True, "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
