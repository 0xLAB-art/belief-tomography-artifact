#!/usr/bin/env python3
"""Freeze or verify exact source/config/test bytes for the recovery-final package.

Usage:
  python scripts/freeze_recovery_final_v1.py freeze --out <dir>
  python scripts/freeze_recovery_final_v1.py verify --out <dir>

The freeze mode copies exact bytes under ``<dir>/source_bytes/`` and writes
``<dir>/SOURCE_MANIFEST.json`` (no self-hash; the manifest is hashed separately
into ``<dir>/SOURCE_MANIFEST.sha256``).  Verify mode re-hashes the worktree and
reports ``changed``/``missing``/``added`` without rewriting anything.

Only source, config, and test files are archived: no secrets, no ``.env``, no
raw attacker dumps, no session/corpus data.  This script adds no framework; it
is a bounded byte-archive helper for the final package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Base runtime list is the v2 trace runner's own list (single source of truth).
BASE_LIST_MODULE = "scripts/run_p0_loopback_ssh_trace_v2.py"

EXTRA_GLOBS = (
    "ragin/evaluation/**/*.py",
    "scripts/*ablation*_v1.py",
    "scripts/preflight_generation_contract_v1.py",
    "scripts/prove_cowrie_persona_alignment_v1.py",
    "scripts/freeze_recovery_final_v1.py",
    "configs/ablation/eval_v1/**/*",
    "configs/ablation/persona_lab_v1/**/*",
    "tests/unit/test_ablation_*_v1.py",
    "tests/unit/test_preflight_generation_contract_v1*.py",
    "tests/**/test_persona_*.py",
)

SKIP_PARTS = {"__pycache__", ".pyc"}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_base_list() -> list[str]:
    import importlib.util

    spec = importlib.util.spec_from_file_location("_ragin_v2_trace", ROOT / BASE_LIST_MODULE)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import {BASE_LIST_MODULE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.SOURCE_FILES)


def collect_paths() -> list[str]:
    paths = set(load_base_list())
    for pattern in EXTRA_GLOBS:
        for path in ROOT.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT)
            if any(part in SKIP_PARTS for part in rel.parts):
                continue
            if path.suffix == ".pyc":
                continue
            paths.add(rel.as_posix())
    return sorted(paths)


def git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError:
        return ""


def metadata() -> dict:
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": git("rev-parse", "HEAD"),
        "git_dirty_tracked_count": len(
            [line for line in git("status", "--porcelain").splitlines() if not line.startswith("??")]
        ),
        "python": sys.version.split()[0],
        "model": "opencode/deepseek-v4.1-flash-free",
        "provider_inference_calls": 0,
        "external_calls": 0,
        "notes": "source/config/test bytes only; no secrets, env values, or raw data",
    }


def freeze(out: Path) -> int:
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty {out}")
    out.mkdir(parents=True, exist_ok=True)
    entries = []
    for rel in collect_paths():
        src = ROOT / rel
        if not src.is_file():
            entries.append({"path": rel, "exists": False})
            continue
        data = src.read_bytes()
        dest = out / "source_bytes" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        entries.append(
            {
                "path": rel,
                "exists": True,
                "size_bytes": len(data),
                "sha256": sha_bytes(data),
                "archived": (dest.relative_to(out)).as_posix(),
            }
        )
    manifest = {"metadata": metadata(), "entries": entries}
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    (out / "SOURCE_MANIFEST.json").write_text(text, encoding="utf-8")
    (out / "SOURCE_MANIFEST.sha256").write_text(
        f"{sha_bytes(text.encode())}  SOURCE_MANIFEST.json\n", encoding="utf-8"
    )
    absent = [e["path"] for e in entries if not e["exists"]]
    print(f"frozen {len(entries)} paths ({len(absent)} absent) -> {out}")
    if absent:
        print("absent:", ", ".join(absent))
    return 0


def verify(out: Path) -> int:
    manifest = json.loads((out / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    changed, missing, ok = [], [], 0
    for entry in manifest["entries"]:
        rel = entry["path"]
        src = ROOT / rel
        if not entry.get("exists"):
            if src.is_file():
                changed.append(rel)
            continue
        if not src.is_file():
            missing.append(rel)
            continue
        if src.stat().st_size == entry["size_bytes"] and sha_file(src) == entry["sha256"]:
            ok += 1
        else:
            changed.append(rel)
    result = {
        "verified_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": sha_bytes((out / "SOURCE_MANIFEST.json").read_bytes()),
        "ok": ok,
        "changed": changed,
        "missing": missing,
    }
    print(json.dumps(result, indent=2))
    return 0 if not changed and not missing else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("freeze", "verify"))
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    return freeze(out) if args.mode == "freeze" else verify(out)


if __name__ == "__main__":
    raise SystemExit(main())
