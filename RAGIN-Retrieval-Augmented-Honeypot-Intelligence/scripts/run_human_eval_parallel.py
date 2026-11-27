#!/usr/bin/env python3
"""Parallel human-eval runner: 8 GT scenarios concurrently through the LangGraph engine.

Same output schema as scripts/run_human_eval.py (pre-filled SessionEvaluation JSON +
raw pipeline outputs incl. verification/approval/plan) but wall-clock ~= one turn
instead of 8x, because each scenario's LLM calls are independent.

Usage:
    .venv/bin/python scripts/run_human_eval_parallel.py [--output results/human_eval_full.json]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from run_human_eval import build_persona_override_adapter, load_env  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Parallel RAGIN Human Evaluation (graph engine)")
    parser.add_argument("--output", default="results/human_eval_full.json")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)

    load_env(Path(__file__).resolve().parent.parent / ".env")

    from ragin.benchmark.harness_bridge import outcome_from_pipeline_result
    from ragin.benchmark.human_eval import (
        ALL_RUBRICS,
        EVALUATOR_PROTOCOL,
        SAMPLE_SCENARIOS,
        create_evaluation_template,
    )
    from ragin.cycle.adapters import ChrolloAdapter, DonAdapter, HisokaAdapter
    from ragin.cycle.graph import DeceptionPipeline
    from ragin.cycle.hitl import ApprovalGateway, ClaimedApprover, DefaultRiskBasedPolicy, FileAuditTrail
    from ragin.cycle.session import Session

    llm_key = os.environ.get("RAGIN_LLM_API_KEY", "")
    llm_base = os.environ.get("RAGIN_LLM_BASE_URL", "").rstrip("/")
    az_key = os.environ.get("AZURE_OPENAI_KEY", "")
    az_ep = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    if llm_key and llm_base:
        gateway = llm_base
    elif az_key and az_ep:
        gateway = f"{az_ep}/openai"  # legacy Azure staging
    else:
        gateway = "https://api.tokenrouter.com/api"
    api_key = llm_key or az_key or os.environ.get("TOKENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")

    audit_path = os.environ.get("RAGIN_HITL_AUDIT_TRAIL", "results/hitl_audit_eval.jsonl")
    approval_gateway = ApprovalGateway(
        policy=DefaultRiskBasedPolicy(),
        approver=ClaimedApprover(decision_fn=lambda req: req.risk_score < 9.0),
        auditor=FileAuditTrail(path=audit_path),
    )
    print(f"[1/3] Building LangGraph engine (gateway={gateway}) ...")
    pipe = DeceptionPipeline(
        classifier=ChrolloAdapter(),
        analyzer=DonAdapter(gateway_url=gateway, api_key=api_key),
        deceiver=HisokaAdapter(gateway_url=gateway, api_key=api_key),
        approval_gateway=approval_gateway,
        human_in_the_loop=False,
        max_retries=2,
    )

    scenarios = SAMPLE_SCENARIOS[: args.limit] if args.limit else SAMPLE_SCENARIOS

    # Per-scenario persona-override classifier: each thread needs its OWN
    # pipeline instance (the graph caches fiction graphs per session_id, and
    # LangGraph checkpointer is shared) — build one pipe per worker thread.
    thread_local = {}

    def _pipe_for_thread():
        import threading

        tid = threading.get_ident()
        if tid not in thread_local:
            override_cls = build_persona_override_adapter()
            thread_local[tid] = DeceptionPipeline(
                classifier=override_cls(),
                analyzer=DonAdapter(gateway_url=gateway, api_key=api_key),
                deceiver=HisokaAdapter(gateway_url=gateway, api_key=api_key),
                approval_gateway=approval_gateway,
                human_in_the_loop=False,
                max_retries=2,
            )
        return thread_local[tid]

    def _run(sc):
        t0 = time.monotonic()
        pipe = _pipe_for_thread()
        classifier = pipe._classifier
        classifier.set_persona(sc.expected_persona)
        session = Session.create(source_ip=f"human-eval-{sc.scenario_id}")
        try:
            pr = pipe.process(session, sc.attacker_input)
            outcome = outcome_from_pipeline_result(pr, sc.attacker_input)
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
            raw = {
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
                "elapsed_s": round(time.monotonic() - t0, 2),
                "error": outcome.error,
            }
            return session_eval.to_dict(), raw
        except Exception as e:
            return None, {
                "scenario_id": sc.scenario_id,
                "ground_truth": sc.to_dict(),
                "error": str(e),
            }
        finally:
            try:
                session.close("human_eval_complete")
            except Exception:
                pass

    print(f"[2/3] Running {len(scenarios)} scenarios x {args.workers} workers ...")
    evaluation_sessions: list[dict] = []
    raw_results: list[dict] = []
    t_start = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_run, sc): sc for sc in scenarios}
        for done, fut in enumerate(as_completed(futures), 1):
            sess, raw = fut.result()
            if sess:
                evaluation_sessions.append(sess)
                print(
                    f"  [{done}/{len(scenarios)}] {raw['scenario_id']}: "
                    f"persona={raw['persona_name']} ttps={raw['ttps_extracted']} "
                    f"{raw['elapsed_s']}s err={raw['error']}"
                )
            else:
                print(f"  [{done}/{len(scenarios)}] {raw['scenario_id']}: FAIL — {raw['error'][:80]}")
            raw_results.append(raw)

    evaluation_sessions.sort(key=lambda s: s["session_id"])
    raw_results.sort(key=lambda r: r["scenario_id"])

    print("[3/3] Writing output ...")
    output = {
        "meta": {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_scenarios": len(scenarios),
            "engine": "langgraph-parallel",
            "gateway": gateway,
            "wall_clock_s": round(time.monotonic() - t_start, 1),
            "description": "RAGIN Human Evaluation — pre-filled from live pipeline output (LangGraph engine, parallel).",
        },
        "evaluator_protocol": EVALUATOR_PROTOCOL,
        "rubrics": [r.to_dict() for r in ALL_RUBRICS],
        "evaluation_sessions": evaluation_sessions,
        "raw_pipeline_outputs": raw_results,
    }
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, default=str))
    total_s = time.monotonic() - t_start
    print(f"  Done — {len(scenarios)} scenarios in {total_s:.1f}s wall-clock -> {out_path}")


if __name__ == "__main__":
    main()
