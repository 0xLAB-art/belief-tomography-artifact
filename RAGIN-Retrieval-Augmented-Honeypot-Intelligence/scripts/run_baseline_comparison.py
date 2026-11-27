#!/usr/bin/env python3
"""B4: No-RAG baseline comparison.

Compares RAGIN full pipeline (Chrollo→Don→Hisoka) vs baseline (Hisoka only, no Don CTI).
Demonstrates RAG augmentation value for the ESWA paper.

Usage:
    python scripts/run_baseline_comparison.py --limit 10
    python scripts/run_baseline_comparison.py --limit 10 --json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


PAIR_SCHEMA_VERSION = 1
PAIR_KEY = "suite+scenario_id"


def scenario_id(suite: str, name: str) -> str:
    return f"{suite}:{name}"


def manifest_hash(rows: list[dict]) -> str:
    lines = sorted(f"{r.get('suite', '?')}|{r.get('scenario_id') or r.get('name', '')}" for r in rows)
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def row_audit(rows: list[dict]) -> dict:
    keys = [r.get("scenario_id") or r.get("name", "") for r in rows]
    return {
        "row_count": len(rows),
        "unique_scenario_ids": len(keys) == len(set(keys)),
        "duplicate_ids": sorted({k for k in keys if keys.count(k) > 1}),
        "suites": sorted({r.get("suite", "?") for r in rows}),
    }


def assert_paired_rows(rag_rows: list[dict], nr_rows: list[dict]) -> dict:
    a = row_audit(rag_rows)
    b = row_audit(nr_rows)
    problems: list[str] = []
    if not a["unique_scenario_ids"]:
        problems.append(f"rag duplicate ids: {a['duplicate_ids']}")
    if not b["unique_scenario_ids"]:
        problems.append(f"no_rag duplicate ids: {b['duplicate_ids']}")
    a_keys = {r.get("scenario_id") or r.get("name", "") for r in rag_rows}
    b_keys = {r.get("scenario_id") or r.get("name", "") for r in nr_rows}
    if a_keys != b_keys:
        problems.append(
            f"asymmetric sets: only_rag={sorted(a_keys - b_keys)[:5]} only_no_rag={sorted(b_keys - a_keys)[:5]}"
        )

    def suite_map(rows):
        out: dict[str, set] = {}
        for r in rows:
            out.setdefault(r.get("suite", "?"), set()).add(r.get("scenario_id") or r.get("name", ""))
        return out

    sa, sb = suite_map(rag_rows), suite_map(nr_rows)
    if set(sa) != set(sb) or any(sa[s] != sb[s] for s in sa if s in sb):
        rag_counts = {key: len(value) for key, value in sa.items()}
        no_rag_counts = {key: len(value) for key, value in sb.items()}
        problems.append(f"suite membership mismatch: rag={rag_counts} no_rag={no_rag_counts}")
    audit = {
        "rag": a,
        "no_rag": b,
        "exact_set_equal": a_keys == b_keys,
        "ok": not problems,
        "problems": problems,
    }
    if problems:
        raise AssertionError("B4 pairing contract violated: " + "; ".join(problems))
    return audit


def provider_metadata() -> dict:
    llm_base = os.environ.get("RAGIN_LLM_BASE_URL", "").rstrip("/")
    az_ep = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    has_llm = bool(os.environ.get("RAGIN_LLM_API_KEY") and llm_base)
    has_az = bool(os.environ.get("AZURE_OPENAI_KEY") and az_ep)
    has_tok = bool(os.environ.get("TOKENROUTER_API_KEY"))
    has_or = bool(os.environ.get("OPENROUTER_API_KEY"))
    source = "llm_gateway"
    if not has_llm:
        source = (
            "azure" if has_az else "tokenrouter" if has_tok else "openrouter" if has_or else "local_gateway_default"
        )
    base = llm_base if has_llm else (f"{az_ep}/openai" if has_az else "http://localhost:8080")
    return {
        "gateway_source": source,
        "base_url": base,
        "model": os.environ.get("RAGIN_LLM_MODEL", "") or os.environ.get("AZURE_OPENAI_DEPLOYMENT", ""),
        "api_key_present": has_llm or has_az or has_tok or has_or,
    }


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


def create_harness(with_rag: bool = True):
    """Create a Harness with or without Don CTI engine."""
    from ragin.cycle.adapters import ChrolloAdapter, DonAdapter, HisokaAdapter
    from ragin.cycle.harness import Harness

    # Resolve the LLM endpoint the same way run_live_benchmark does:
    # env-driven apmix/OpenRouter first, legacy local gateway as a last
    # resort. (The old hardwired tokenrouter URL predated the apmix wiring
    # and silently degraded the whole B4 arm to template responses.)
    llm_key = os.environ.get("RAGIN_LLM_API_KEY", "")
    llm_base = os.environ.get("RAGIN_LLM_BASE_URL", "").rstrip("/")
    az_key = os.environ.get("AZURE_OPENAI_KEY", "")
    az_ep = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    gateway = "http://localhost:8080"
    api_key = os.environ.get("TOKENROUTER_API_KEY", os.environ.get("OPENROUTER_API_KEY", ""))
    if llm_key and llm_base:
        api_key = llm_key
        gateway = llm_base
    elif az_key and az_ep:
        api_key = az_key
        gateway = f"{az_ep}/openai"

    classifier = ChrolloAdapter()
    cti_engine = DonAdapter(gateway_url=gateway, api_key=api_key) if with_rag else None
    deceiver = HisokaAdapter(
        gateway_url=gateway,
        api_key=api_key,
    )

    harness = Harness(
        classifier=classifier,
        cti_engine=cti_engine,
        deceiver=deceiver,
    )
    return harness


def main() -> None:
    parser = argparse.ArgumentParser(description="RAGIN B4: No-RAG Baseline Comparison")
    parser.add_argument("--limit", type=int, default=10, help="Max queries per suite (default: 10)")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    parser.add_argument("--report", default="results/b4_baseline_comparison.json", help="Report output path")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    load_env(Path(__file__).resolve().parent.parent / ".env")

    def per_row(result) -> list[dict]:
        """Per-scenario rows so bootstrap_ci.py can compute paired CIs.

        Without row-level scores, the RAG-vs-baseline arm can only be
        reported as point averages (no CI). Row shape mirrors
        results/live_benchmark_audited.json so the CI battery can pair
        scenarios by name across arms.
        """
        rows = [
            {
                "name": r.name,
                "suite": r.suite,
                "scenario_id": scenario_id(r.suite, r.name),
                "score": r.score,
                "passed": r.passed,
                "quality_class": r.details.get("quality_class") if isinstance(r.details, dict) else None,
                "error": r.error,
            }
            for r in (list(result.technique_results) + list(result.actor_results) + list(result.persona_results))
        ]
        # Fresh-rerun addition: dump raw response texts (repo-contained path,
        # no user input) so an independent family-disjoint labeler can
        # re-score the paired delta afterward.
        dump_path = Path(__file__).resolve().parents[1] / "results" / "b4_fresh_responses.jsonl"
        with dump_path.open("a", encoding="utf-8") as fh:
            for r in (list(result.technique_results) + list(result.actor_results) + list(result.persona_results)):
                fh.write(json.dumps({
                    "suite": r.suite, "name": r.name,
                    "scenario_id": scenario_id(r.suite, r.name),
                    "response_text": (r.details or {}).get("response_full") or (r.details or {}).get("response_preview", ""),
                }, ensure_ascii=False) + "\n")
        return rows

    def arm_payload(result, tech, actor, persona) -> dict:
        return {
            "elapsed_s": result.elapsed_s,
            "metrics": asdict(result.metrics),
            "technique_avg": tech.avg_score,
            "actor_avg": actor.avg_score,
            "persona_avg": persona.avg_score,
            "per_row": per_row(result),
            "row_audit": row_audit(per_row(result)),
            "manifest_hash": manifest_hash(per_row(result)),
            "pair_key": PAIR_KEY,
        }

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    from ragin.benchmark.harness_bridge import run_live_benchmark
    from ragin.cycle.session import Session

    session_counter = [0]

    def session_factory() -> Session:
        session_counter[0] += 1
        return Session.create(source_ip=f"b4-{session_counter[0]}")

    # ── Run with RAG (full pipeline) ─────────────────────────────────────
    print(f"[1/3] Running FULL pipeline (Don CTI enabled), limit={args.limit}...")
    harness_rag = create_harness(with_rag=True)
    result_rag = run_live_benchmark(
        harness=harness_rag,
        session_factory=session_factory,
        limit=args.limit,
    )
    print(f"  Done in {result_rag.elapsed_s:.1f}s")

    # Crash-guard: persist the completed RAG arm immediately so a quota death
    # in arm 2 never loses it (the 0.855 lesson, applied here).
    rag_payload = arm_payload(
        result_rag,
        result_rag.technique_report,
        result_rag.actor_report,
        result_rag.persona_report,
    )
    interim = {
        "experiment": "B4_no_rag_baseline",
        "limit": args.limit,
        "partial": True,
        "rag": rag_payload,
        "no_rag": {},
        "metadata": {
            "schema_version": PAIR_SCHEMA_VERSION,
            "pair_key": PAIR_KEY,
            "provider": provider_metadata(),
            "arm_order": ["rag", "no_rag"],
            "order_policy": "sequential arms; shared session counter continued across arms",
            "scenario_manifest_hash": manifest_hash(rag_payload["per_row"]),
        },
    }
    report_path.write_text(json.dumps(interim, indent=2, default=str))
    print("  (interim report with RAG arm saved)")

    # ── Run without RAG (baseline) ───────────────────────────────────────
    print(f"\n[2/3] Running BASELINE (No Don CTI), limit={args.limit}...")
    harness_no_rag = create_harness(with_rag=False)
    result_no_rag = run_live_benchmark(
        harness=harness_no_rag,
        session_factory=session_factory,
        limit=args.limit,
    )
    print(f"  Done in {result_no_rag.elapsed_s:.1f}s")

    # ── Compare results ──────────────────────────────────────────────────
    print("\n[3/3] Comparison Results")
    print("=" * 70)

    rag_tech = result_rag.technique_report
    no_rag_tech = result_no_rag.technique_report
    rag_actor = result_rag.actor_report
    no_rag_actor = result_no_rag.actor_report
    rag_persona = result_rag.persona_report
    no_rag_persona = result_no_rag.persona_report

    print(f"\n{'Suite':<20} {'RAG':>10} {'No-RAG':>10} {'Delta':>10} {'RAG Win?':>10}")
    print("-" * 60)

    for name, r_rep, nr_rep in [
        ("CTI Technique", rag_tech, no_rag_tech),
        ("CTI Actor", rag_actor, no_rag_actor),
        ("Persona Realism", rag_persona, no_rag_persona),
    ]:
        r_score = r_rep.avg_score
        nr_score = nr_rep.avg_score
        delta = r_score - nr_score
        win = "✓" if delta > 0 else ("=" if delta == 0 else "✗")
        print(f"{name:<20} {r_score:>10.3f} {nr_score:>10.3f} {delta:>+10.3f} {win:>10}")

    # Overall
    r_overall = (rag_tech.avg_score + rag_actor.avg_score + rag_persona.avg_score) / 3
    nr_overall = (no_rag_tech.avg_score + no_rag_actor.avg_score + no_rag_persona.avg_score) / 3
    print("-" * 60)
    print(f"{'OVERALL':<20} {r_overall:>10.3f} {nr_overall:>10.3f} {r_overall - nr_overall:>+10.3f}")

    # EffectivenessMetrics comparison
    print("\n  Effectiveness Metrics:")
    print(f"  {'Metric':<35} {'RAG':>10} {'No-RAG':>10}")
    print(f"  {'-' * 55}")
    for label, r_val, nr_val in [
        ("TTPs detected", result_rag.metrics.ttps_detected, result_no_rag.metrics.ttps_detected),
        ("Unique TTPs", result_rag.metrics.ttps_detected_unique, result_no_rag.metrics.ttps_detected_unique),
        (
            "Avg response time (ms)",
            f"{result_rag.metrics.avg_response_time_ms:.0f}",
            f"{result_no_rag.metrics.avg_response_time_ms:.0f}",
        ),
        (
            "Sessions with engagement",
            result_rag.metrics.sessions_with_engagement,
            result_no_rag.metrics.sessions_with_engagement,
        ),
    ]:
        print(f"  {label:<35} {r_val:>10} {nr_val:>10}")

    # Save report
    no_rag_payload = arm_payload(result_no_rag, no_rag_tech, no_rag_actor, no_rag_persona)
    pair_audit = assert_paired_rows(rag_payload["per_row"], no_rag_payload["per_row"])

    report_data = {
        "experiment": "B4_no_rag_baseline",
        "limit": args.limit,
        "partial": False,
        "rag": rag_payload,
        "no_rag": no_rag_payload,
        "metadata": {
            "schema_version": PAIR_SCHEMA_VERSION,
            "pair_key": PAIR_KEY,
            "provider": provider_metadata(),
            "arm_order": ["rag", "no_rag"],
            "order_policy": "sequential arms; shared session counter continued across arms",
            "seed": os.environ.get("RAGIN_SEED", ""),
            "session_counter_final": session_counter[0],
            "scenario_manifest_hash_rag": rag_payload["manifest_hash"],
            "scenario_manifest_hash_no_rag": no_rag_payload["manifest_hash"],
        },
        "pair_assertions": pair_audit,
    }

    report_path.write_text(json.dumps(report_data, indent=2, default=str))
    print(f"\n  Report saved to {report_path}")

    if args.json:
        print(json.dumps(report_data, indent=2, default=str))


if __name__ == "__main__":
    main()
