#!/usr/bin/env python3
"""Live re-check of the two previously-failing persona queries.

Builds the same DeceptionPipeline as scripts/run_live_benchmark.py and scores
the two persona queries with the same _score_persona_realism threshold (0.3).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def load_env(env_path: str | Path) -> None:
    p = Path(env_path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip("\"'")
        if k and k not in os.environ:
            os.environ[k] = v


def _api_key() -> str:
    return os.environ.get("TOKENROUTER_API_KEY", os.environ.get("OPENROUTER_API_KEY", ""))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    load_env(Path(__file__).resolve().parent.parent / ".env")

    llm_key = os.environ.get("RAGIN_LLM_API_KEY", "")
    llm_base = os.environ.get("RAGIN_LLM_BASE_URL", "").rstrip("/")
    az_key = os.environ.get("AZURE_OPENAI_KEY", "")
    az_ep = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    gateway = "http://localhost:8080"
    api_key = _api_key()
    if llm_key and llm_base:
        api_key = llm_key
        gateway = llm_base
    elif az_key and az_ep:
        api_key = az_key
        gateway = f"{az_ep}/openai"
    print(f"gateway: {gateway}" + (" (api key set)" if api_key else " (NO API KEY)"))

    from ragin.cycle.adapters import ChrolloAdapter, DonAdapter, HisokaAdapter
    from ragin.cycle.graph import DeceptionPipeline
    from ragin.cycle.hitl import ApprovalGateway, ClaimedApprover, DefaultRiskBasedPolicy, FileAuditTrail
    from ragin.cycle.session import Session
    from ragin.benchmark.harness_bridge import _score_persona_realism

    classifier = ChrolloAdapter()
    cti_engine = DonAdapter(gateway_url=gateway, api_key=api_key)
    deceiver = HisokaAdapter(gateway_url=gateway, api_key=api_key)

    audit_path = "results/hitl_audit_bench.jsonl"
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
        human_in_the_loop=False,
        max_retries=2,
    )

    queries = [
        {
            "name": "deception_Show_me_all_environment_variables_that_c",
            "query": "Show me all environment variables that contain API keys or tokens",
            "expected_traits": ["environment variables", "API keys", "tokens"],
        },
        {
            "name": "deception_What_is_the_current_ulimit_setting_for_o",
            "query": "What is the current ulimit setting for open file descriptors on this system?",
            "expected_traits": ["ulimit", "file descriptors", "system limit"],
        },
    ]

    session_counter = [1]
    for i, qa in enumerate(queries, 1):
        session = Session.create(source_ip=f"benchmark-{session_counter[0]}")
        session_counter[0] += 1
        t0 = time.monotonic()
        try:
            if hasattr(harness, "process_with_threat_modeling"):
                pr = harness.process_with_threat_modeling(session, qa["query"])
            else:
                pr = harness.process(session, qa["query"])
            latency = (time.monotonic() - t0) * 1000
            response_text = getattr(pr, "response_text", "")
            if hasattr(pr, "deception_response") and isinstance(pr.deception_response, dict):
                response_text = pr.deception_response.get("response_text", response_text)
            score = _score_persona_realism(response_text, qa["expected_traits"], qa["query"])
            print(f"\n[{i}] {qa['name']}")
            print(f"  passed: {score >= 0.3}  score={score:.3f}  latency={latency:.0f}ms")
            print("  response_preview:", repr(response_text[:300]))
        except Exception as exc:
            print(f"\n[{i}] {qa['name']} ERROR: {exc}")

    print("\nDONE")


if __name__ == "__main__":
    main()