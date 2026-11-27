#!/usr/bin/env python3
"""Offline preflight for the RAGIN B0-B3 ablation run contract.

Exit codes:
  0  EXECUTION_READY (all contract facts resolved and enforceable)
  2  DESIGN_VALID but NOT_READY (expected in this phase)
  3  DESIGN_INVALID

No model is invoked, no provider is contacted, no image is pulled and no
listener is opened. ``--env-check`` only asks the local Docker daemon whether
the pinned Cowrie image ID is already cached.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ragin.evaluation.ablation_contract import (  # noqa: E402
    DESIGN_INVALID,
    EXECUTION_NOT_READY,
    EXECUTION_READY,
    _add,
    evaluate_readiness,
    load_contract,
)


def _attach_generation_contract(report, contract: dict) -> None:
    """Opt-in read of the peer generation contract; never invokes a provider.

    The module is transport-neutral and validates an already-provided config.
    This preflight does not set env vars, does not open a socket and does not
    choose a model. With the opt-in flag it consumes the active snapshot and
    compares it with the frozen contract; a mismatch or unresolved field is a
    blocker, never a quiet fallback.
    """
    try:
        from ragin.gateway.generation import GenerationConfigError, resolve_generation_config
    except Exception as exc:  # noqa: BLE001 - missing peer module is an integration blocker
        _add(
            report.blockers,
            "GENERATION_CONTRACT_MODULE_UNAVAILABLE",
            "generation",
            f"ragin.gateway.generation could not be imported: {type(exc).__name__}",
            "consume the peer generation helper; do not recreate or edit it here",
        )
        report.execution_status = EXECUTION_NOT_READY
        return
    try:
        config = resolve_generation_config()
    except GenerationConfigError as exc:
        _add(report.blockers, "BLOCKED_GENERATION_CONFIG", "generation", str(exc))
        report.execution_status = EXECUTION_NOT_READY
        return
    if config is None:
        _add(
            report.blockers,
            "GENERATION_CONTRACT_NOT_ACTIVATED",
            "generation",
            "--generation-contract was requested but RAGIN_GENERATION_CONTRACT is not enabled; "
            "legacy call-site defaults remain active and the proposed decoding is not applied",
        )
        report.execution_status = EXECUTION_NOT_READY
        return
    snapshot = config.snapshot()
    requested = (contract.get("generation") or {}).get("decoding") or {}
    mismatch = {}
    for key in ("temperature", "max_tokens", "top_p", "seed"):
        if key in requested and requested.get(key) is not None and snapshot.get(key) != requested.get(key):
            mismatch[key] = {"requested": requested.get(key), "effective": snapshot.get(key)}
    frozen_model = (contract.get("generation") or {}).get("model_id")
    if frozen_model and snapshot.get("model") != frozen_model:
        mismatch["model"] = {"requested": frozen_model, "effective": snapshot.get("model")}
    if mismatch:
        _add(
            report.blockers,
            "BLOCKED_GENERATION_CONFIG",
            "generation",
            f"the peer effective generation snapshot differs from the frozen contract: {mismatch}",
            "reconcile the frozen contract with the actual generation config before execution",
        )
        report.execution_status = EXECUTION_NOT_READY
    report.resolved["generation_contract"] = {
        "snapshot": snapshot,
        "module": "ragin.gateway.generation",
        "probe": "OPT_IN_READ_ONLY_NO_PROVIDER_CALL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=ROOT / "configs/ablation/eval_v1/run_contract_v1.json")
    parser.add_argument("--env-check", action="store_true", help="check cached B0 image ID locally; never pulls")
    parser.add_argument(
        "--generation-contract",
        action="store_true",
        help="opt in to reading the peer generation contract snapshot; never calls a provider",
    )
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    contract = load_contract(args.contract, repo_root=ROOT)
    report = evaluate_readiness(contract, repo_root=ROOT, env_check=args.env_check)
    if args.generation_contract:
        _attach_generation_contract(report, contract)
    payload = report.to_dict()
    if args.json_out is not None:
        if args.json_out.exists():
            print(f"refusing to overwrite preflight artifact: {args.json_out}", file=sys.stderr)
            return 2
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2, sort_keys=True))
    if report.design.status == DESIGN_INVALID:
        return 3
    return 0 if report.execution_status == EXECUTION_READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
