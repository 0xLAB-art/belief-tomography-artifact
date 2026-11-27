#!/usr/bin/env python3
"""Publish the effective generation-config artifact for the B0-B3 preflight.

``ragin.evaluation.ablation_contract`` blocks with
``UNRESOLVED_EFFECTIVE_GENERATION_CONFIG`` until a third owner publishes a pure
applied-decoding / model-exposure artifact whose SHA-256 is recorded in the run
contract. This script is that publisher. It is strictly offline:

* it resolves the opt-in generation contract (``RAGIN_GENERATION_CONTRACT`` +
  ``RAGIN_GEN_*`` / ``RAGIN_GENERATION_CONFIG_PATH``) through the same
  validated module the serving client uses — it never invents values;
* it refuses to publish when the applied decoding differs from the frozen run
  contract's requested decoding (exit 3), so a mismatch can never be papered
  over;
* it never opens a socket, contacts a provider, loads a model, or pulls an
  image.

Exit codes:
  0  artifact written (or already current)
  2  generation contract not activated / unresolved (nothing written)
  3  applied decoding differs from the frozen contract (nothing written)
  1  unexpected failure

Usage:
  python3 scripts/publish_effective_generation_config_v1.py \\
      --contract configs/ablation/eval_v1/run_contract_v1.json \\
      --out configs/ablation/eval_v1/effective_generation_config_v1.json

Record the printed ``artifact_sha256`` in the run contract's
``generation.effective_config`` block. Re-run with --force only when the
decoding contract itself was intentionally revised.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ragin.gateway.generation import (  # noqa: E402
    GenerationConfigError,
    require_model_exposure,
    resolve_generation_config,
)

ARTIFACT_SCHEMA = "ragin.generation.effective_config.v1"
_DECODE_KEYS = ("temperature", "top_p", "max_tokens", "seed")

# Non-claims travel with the artifact so no reader can mistake configuration
# for measured behaviour.
_NON_CLAIMS = [
    "Configuration only: no provider was contacted and no model was loaded "
    "while producing this artifact.",
    "The artifact records what RAGIN's generation client places on the wire. "
    "Whether a given backend honors top_p/seed is unverified until observed "
    "in a live run's request/response trace.",
    "Model identity/weights availability is out of scope here and remains a "
    "separate preflight blocker (UNRESOLVED_MODEL).",
]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise SystemExit("run contract is not a JSON object")
    return payload


def build_artifact(environ: dict[str, str] | None = None) -> dict[str, Any]:
    """Resolve the active contract and return the artifact payload.

    Raises GenerationConfigError when the contract is enabled but invalid; the
    caller treats a ``None`` return (contract disabled) as unresolved.
    """
    config = resolve_generation_config(environ)
    if config is None:
        return {}
    exposure = require_model_exposure(environ)
    return {
        "schema": ARTIFACT_SCHEMA,
        "generation_contract_version": config.snapshot()["version"],
        "applied_decoding": config.decoding_payload(),
        "seed_status": config.seed_status,
        "model": config.model,
        "config_sha256": config.config_sha256,
        "source": config.source,
        "max_retries": config.max_retries,
        "enforcement": {
            "layer": "ragin.gateway.client.GatewayClient.generate (contract-active branch)",
            "effect": (
                "every generated request carries these decoding values; conflicting "
                "per-call overrides raise GenerationConfigError"
            ),
        },
        "model_exposure": {
            "require_model_exposure": exposure,
            "mode_env": "RAGIN_REQUIRE_MODEL_EXPOSURE",
            "status": "ENABLED" if exposure else "DISABLED",
        },
        "published_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "non_claims": list(_NON_CLAIMS),
    }


def _mismatches(applied: dict[str, Any], requested: dict[str, Any]) -> dict[str, Any]:
    """Fields the frozen contract requested but the applied config differs on."""
    problems: dict[str, Any] = {}
    for key in _DECODE_KEYS:
        wanted = requested.get(key)
        if wanted is None or key not in applied:
            continue
        if applied.get(key) != wanted:
            problems[key] = {"requested": wanted, "applied": applied.get(key)}
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        type=Path,
        default=ROOT / "configs" / "ablation" / "eval_v1" / "run_contract_v1.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "configs" / "ablation" / "eval_v1" / "effective_generation_config_v1.json",
    )
    parser.add_argument("--force", action="store_true", help="overwrite an existing artifact")
    args = parser.parse_args(argv)

    if args.out.exists() and not args.force:
        print(
            f"refusing to overwrite existing artifact: {args.out} (use --force after a "
            "deliberate contract revision)",
            file=sys.stderr,
        )
        return 2

    try:
        artifact = build_artifact()
    except GenerationConfigError as exc:
        # The error message names only the offending field — safe to print.
        print(f"generation contract unresolved/invalid: {exc}", file=sys.stderr)
        return 2
    if not artifact:
        print(
            "generation contract is not activated (RAGIN_GENERATION_CONTRACT unset); "
            "legacy call-site defaults would remain in effect, so no artifact is published",
            file=sys.stderr,
        )
        return 2

    contract = _load_contract(args.contract)
    requested = (contract.get("generation") or {}).get("decoding") or {}
    problems = _mismatches(artifact["applied_decoding"], requested)
    if problems:
        print(
            "applied decoding differs from the frozen run contract; refusing to publish: "
            f"{json.dumps(problems, sort_keys=True)}",
            file=sys.stderr,
        )
        return 3

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "artifact": str(args.out),
                "artifact_sha256": _sha256_file(args.out),
                "applied_decoding": artifact["applied_decoding"],
                "seed_status": artifact["seed_status"],
                "require_model_exposure": artifact["model_exposure"]["require_model_exposure"],
                "config_sha256": artifact["config_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
