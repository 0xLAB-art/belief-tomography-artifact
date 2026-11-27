#!/usr/bin/env python3
"""Run the 8 ground-truth scenarios through the live RAGIN pipeline,
capture outputs, and produce pre-filled SessionEvaluation JSON for human scoring.

Usage:
    python scripts/run_human_eval.py
    python scripts/run_human_eval.py --output results/human_eval.json
    python scripts/run_human_eval.py --limit 3   # quick smoke test
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger(__name__)


def load_env(env_path: str | Path) -> None:
    p = Path(env_path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip("\"'")
        if k not in os.environ:
            os.environ.setdefault(k, v)


def build_persona_override_adapter():
    """Chrollo adapter that honors the ground-truth expected persona.

    Chrollo's RF defaults to 'apt' on single commands (no history); the human
    eval needs the pipeline to exercise all personas, so the eval runner wraps
    the adapter and overrides skill_level per scenario. Defined at module level
    so the parallel runner can reuse it.
    """
    from ragin.cycle.adapters import ChrolloAdapter

    class _PersonaOverrideAdapter(ChrolloAdapter):
        def __init__(self) -> None:
            super().__init__()
            self._override: str | None = None

        def set_persona(self, persona: str) -> None:
            self._override = persona

        def classify(self, attacker_input: str, session_context: dict) -> dict:
            base = super().classify(attacker_input, session_context)
            if self._override is not None:
                base["skill_level"] = self._override
                base["confidence"] = 0.9
                base["persona_override"] = True
            return base

    return _PersonaOverrideAdapter


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="RAGIN Human Evaluation Runner")
    parser.add_argument("--output", default="results/human_eval.json", help="Output JSON path")
    parser.add_argument("--limit", type=int, default=None, help="Limit scenarios (smoke test)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument(
        "--engine",
        choices=("graph", "linear"),
        default="graph",
        help="graph = checkpointed LangGraph loop (fiction+steering+HITL+verify, default); linear = legacy Harness",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    load_env(Path(__file__).resolve().parent.parent / ".env")

    # --- Imports -----------------------------------------------------------
    from ragin.benchmark.harness_bridge import outcome_from_pipeline_result
    from ragin.benchmark.human_eval import (
        ALL_RUBRICS,
        EVALUATOR_PROTOCOL,
        SAMPLE_SCENARIOS,
        create_evaluation_template,
    )
    from ragin.cycle.adapters import ChrolloAdapter, DonAdapter, HisokaAdapter
    from ragin.cycle.harness import Harness
    from ragin.cycle.session import Session

    # --- Build real pipeline -----------------------------------------------
    api_key = os.environ.get("TOKENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("WARNING: TOKENROUTER_API_KEY/OPENROUTER_API_KEY not set; LLM stages will fail.")

    # Match the base URL to whichever OpenAI-compatible key is available.
    gateway = "https://api.tokenrouter.com/api"
    llm_key = os.environ.get("RAGIN_LLM_API_KEY", "")
    llm_base = os.environ.get("RAGIN_LLM_BASE_URL", "").rstrip("/")
    az_key = os.environ.get("AZURE_OPENAI_KEY", "")
    az_ep = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    if llm_key and llm_base:
        api_key = llm_key
        gateway = llm_base
    elif az_key and az_ep:
        # Legacy Azure AI Foundry staging ({endpoint}/openai).
        api_key = az_key
        gateway = f"{az_ep}/openai"
    elif not os.environ.get("TOKENROUTER_API_KEY") and os.environ.get("OPENROUTER_API_KEY"):
        gateway = "https://openrouter.ai/api"
    os.environ.setdefault("RAGIN_DON_MODEL", "glm-5.3-flash-free")
    os.environ.setdefault("RAGIN_HISOKA_MODEL", "glm-5.3-flash-free")

    print("[1/3] Initializing pipeline...")

    # Ponytail: Chrollo's RF defaults to 'apt' on single commands (no history).
    # For human eval we want the pipeline to actually exercise all 4 personas,
    # so wrap ChrolloAdapter to honor the ground-truth expected persona.
    classifier = build_persona_override_adapter()()
    cti_engine = DonAdapter(gateway_url=gateway, api_key=api_key)
    deceiver = HisokaAdapter(gateway_url=gateway, api_key=api_key)

    if args.engine == "graph":
        # TDSC loop: fiction graph (C1) + MITRE steering (C3) + HITL gate (C4)
        # + fiction-consistency verification (C2), checkpointed by LangGraph (C5).
        from ragin.cycle.graph import DeceptionPipeline
        from ragin.cycle.hitl import ApprovalGateway, ClaimedApprover, DefaultRiskBasedPolicy, FileAuditTrail

        audit_path = os.environ.get("RAGIN_HITL_AUDIT_TRAIL", "results/hitl_audit_eval.jsonl")
        approval_gateway = ApprovalGateway(
            policy=DefaultRiskBasedPolicy(),
            approver=ClaimedApprover(decision_fn=lambda req: req.risk_score < 9.0),
            auditor=FileAuditTrail(path=audit_path),
        )
        harness = DeceptionPipeline(
            classifier=classifier,
            analyzer=cti_engine,
            deceiver=deceiver,
            approval_gateway=approval_gateway,
            human_in_the_loop=False,  # unattended eval: policy auto/claim, audit recorded
            max_retries=2,
        )
        print(f"  Engine: LangGraph deception loop (HITL audit -> {audit_path})")
    else:
        harness = Harness(
            classifier=classifier,
            cti_engine=cti_engine,
            deceiver=deceiver,
        )
        print("  Engine: linear Harness (legacy)")
    print(f"  Harness ready ({len(SAMPLE_SCENARIOS)} scenarios loaded)")

    # --- Run scenarios -----------------------------------------------------
    scenarios = SAMPLE_SCENARIOS[: args.limit] if args.limit else SAMPLE_SCENARIOS

    print(f"\n[2/3] Running {len(scenarios)} scenarios through pipeline...")

    evaluation_sessions: list[dict] = []
    raw_results: list[dict] = []

    for idx, sc in enumerate(scenarios, 1):
        label = f"  [{idx}/{len(scenarios)}] {sc.scenario_id}: {sc.attacker_input[:50]}"
        print(f"{label:<65}", end="", flush=True)

        session = Session.create(source_ip=f"human-eval-{sc.scenario_id}")
        t0 = time.monotonic()
        classifier.set_persona(sc.expected_persona)

        try:
            pr = (
                harness.process_with_threat_modeling(session, sc.attacker_input)
                if args.engine == "linear"
                else harness.process(session, sc.attacker_input)
            )
            elapsed = time.monotonic() - t0

            outcome = outcome_from_pipeline_result(pr, sc.attacker_input)

            # --- Pre-fill TurnEvaluation -----------------------------------
            turn_eval = {
                "turn_number": 1,
                "query": sc.attacker_input,
                "response_text": outcome.response_text,
                "persona_used": outcome.persona_name,
                "ttps_extracted": outcome.ttps_extracted,
            }

            session_eval = create_evaluation_template(
                session_id=sc.scenario_id,
                turns=[turn_eval],
                attacker_profile=sc.expected_persona,
            )

            evaluation_sessions.append(session_eval.to_dict())

            raw_results.append(
                {
                    "scenario_id": sc.scenario_id,
                    "ground_truth": sc.to_dict(),
                    "classification": outcome.classification,
                    "cti_analysis": outcome.cti_analysis,
                    "deception": outcome.deception,
                    "verification": outcome.verification,
                    "approval": getattr(pr, "approval", {}),
                    "plan": getattr(pr, "plan", {}),
                    "response_text": outcome.response_text,
                    "persona_name": outcome.persona_name,
                    "ttps_extracted": outcome.ttps_extracted,
                    "elapsed_s": round(elapsed, 2),
                    "error": outcome.error,
                }
            )

            print(f"  {elapsed:.1f}s  persona={outcome.persona_name or '?'}")

        except Exception as e:
            elapsed = time.monotonic() - t0
            print(f"  FAIL ({elapsed:.1f}s): {e}")
            raw_results.append(
                {
                    "scenario_id": sc.scenario_id,
                    "ground_truth": sc.to_dict(),
                    "error": str(e),
                }
            )

        finally:
            try:
                session.close("human_eval_complete")
            except Exception as e:
                logger.debug("Error closing session: %s", e)

    # --- Build output ------------------------------------------------------
    print(f"\n[3/3] Writing results to {args.output} ...")

    output = {
        "meta": {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_scenarios": len(scenarios),
            "engine": args.engine,
            "gateway": gateway,
            "description": "RAGIN Human Evaluation — pre-filled from live pipeline output. "
            "Scores default to ACCEPTABLE(3); evaluators must override.",
        },
        "evaluator_protocol": EVALUATOR_PROTOCOL,
        "rubrics": [r.to_dict() for r in ALL_RUBRICS],
        "evaluation_sessions": evaluation_sessions,
        "raw_pipeline_outputs": raw_results,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"  Done — {len(scenarios)} scenarios, {out_path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
