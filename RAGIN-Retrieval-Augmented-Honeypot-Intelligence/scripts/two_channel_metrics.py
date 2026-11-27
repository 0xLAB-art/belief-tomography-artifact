"""Two-channel §VI metrics — served-text vs CTI-analysis, declared separately.

Background (results/technique_rubric_diff_investigation.json): the Sep-22
reference artifact scored technique/actor composites by max()ing two channels
(served text + CTI analysis), while the W1 external-baseline arms scored
served text only — comparing them as one number manufactured a phantom
generator-model regression. The fix is declared channels, reported separately.

This script computes BOTH channels for the current-model grounded pipeline
(ragin_full config) over the 218-query VOR workload, using run_live_benchmark
itself (so every channel is scored by the code that owns it), and emits the
two-channel table pair for §VI.

Channel definitions:
  served_text   deception realism: what the attacker actually receives
                (technique/actor string match on response_text only)
  cti_analysis  intelligence value: what the pipeline IDENTIFIED from the
                interaction (Don extraction: ttps_extracted / analysis text /
                candidate_actors) — never served to the attacker

Usage::

    python scripts/two_channel_metrics.py --limit 3          # smoke
    python scripts/two_channel_metrics.py --budget-s 360     # budgeted batches
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_external_baseline import _load_checkpoint, _row_name, _save_checkpoint, resolve_gateway  # noqa: E402

OUT = ROOT / "results" / "two_channel_metrics.json"
CHECKPOINT_ARM = "two_channel_metrics"


def _channel_scores(outcome: Any, qa: dict[str, Any], suite: str) -> dict[str, float]:
    """Score ONE outcome in each declared channel, separately (no max)."""
    import ragin.benchmark.harness_bridge as hb

    if suite == "cti_technique":
        served = hb._score_technique_match(
            outcome.response_text, qa.get("expected_technique", ""), query=qa.get("query"))
        analysis_text = hb._cti_analysis_text(outcome.cti_analysis)
        analysis = hb._score_technique_match(analysis_text, qa.get("expected_technique", ""))
        expected = qa.get("expected_technique", "").upper()
        extracted = {t.upper() for t in outcome.ttps_extracted}
        if expected in extracted:
            ttp_bonus = 1.0
        elif expected.split(".")[0] in extracted or any(
            exp_p == expected.split(".")[0] for exp_p in (e.split(".")[0] for e in extracted)
        ):
            ttp_bonus = 0.85
        else:
            ttp_bonus = 0.0
        analysis = max(analysis, ttp_bonus)
    elif suite == "cti_actor":
        served = hb._score_actor_match(
            outcome.response_text, qa.get("expected_actor", ""), qa.get("sector", ""),
            query=qa.get("query"))
        analysis_text = hb._cti_analysis_text(outcome.cti_analysis)
        analysis = hb._score_actor_match(analysis_text, qa.get("expected_actor", ""), qa.get("sector", ""))
        expected = qa.get("expected_actor", "").lower()
        named = {
            a.get("name", "").lower()
            for a in (outcome.cti_analysis or {}).get("candidate_actors", [])
            if isinstance(a, dict)
        }
        if any(expected == n or expected in n or n in expected for n in named):
            analysis = max(analysis, 0.85)
    else:  # deception: served-text channel only (no analysis channel by design)
        served = hb._score_persona_realism(
            outcome.response_text, qa.get("expected_traits", ""), str(qa.get("query", "")))
        analysis = None
    return {"served_text": round(served, 4), "cti_analysis": analysis}


def main() -> int:
    parser = argparse.ArgumentParser(description="Two-channel §VI metrics (declared channels)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--budget-s", type=float, default=None,
                        help="clean stop after this many wall-clock seconds (per-row checkpoint resume)")
    args = parser.parse_args()

    from ragin.benchmark.core import (
        CTI_ACTOR_QUERIES,
        CTI_TECHNIQUE_QUERIES,
        PERSONA_REALISM_QUERIES,
    )
    from ragin.cycle.adapters import ChrolloAdapter, DonAdapter, HisokaAdapter
    from ragin.cycle.graph import DeceptionPipeline
    from ragin.cycle.session import Session

    gateway_url, api_key = resolve_gateway()
    os.environ.pop("RAGIN_HOST_FICTION", None)  # store off: this measures the ragin_full config
    pipeline = DeceptionPipeline(
        classifier=ChrolloAdapter(),
        analyzer=DonAdapter(gateway_url=gateway_url, api_key=api_key),
        deceiver=HisokaAdapter(gateway_url=gateway_url, api_key=api_key),
        verifier=None,  # default FictionConsistencyVerifier (verified loop)
        approval_gateway=None,
        human_in_the_loop=False,
        max_retries=1,
    )

    workload: list[tuple[str, dict]] = []
    for qa in (CTI_TECHNIQUE_QUERIES[:args.limit] if args.limit else CTI_TECHNIQUE_QUERIES):
        workload.append(("cti_technique", qa))
    for qa in (CTI_ACTOR_QUERIES[:args.limit] if args.limit else CTI_ACTOR_QUERIES):
        workload.append(("cti_actor", qa))
    for qa in (PERSONA_REALISM_QUERIES[:args.limit] if args.limit else PERSONA_REALISM_QUERIES):
        workload.append(("deception", qa))

    saved = _load_checkpoint(CHECKPOINT_ARM, args.limit)
    prior: dict[str, dict] = {r["name"]: r for r in saved.get("rows", [])}

    t0 = time.monotonic()
    counter = [0]
    rows: list[dict] = list(prior.values())
    stopped_early = False

    for suite, qa in workload:
        q = qa["query"]
        name = _row_name(suite, q)
        if name in prior:
            continue
        if args.budget_s is not None and (time.monotonic() - t0) > args.budget_s:
            stopped_early = True
            break
        counter[0] += 1
        session = Session.create(source_ip=f"twochannel-{counter[0]}")
        try:
            pr = pipeline.process(session, q)
        except Exception as exc:  # noqa: BLE001 — a failed row is data, not a crash
            logging_row = {"name": name, "suite": suite, "error": f"{type(exc).__name__}: {exc}"[:160]}
            rows.append(logging_row)
            _save_checkpoint(CHECKPOINT_ARM, args.limit, rows, {})
            print(f"  {name[:50]} ERROR {logging_row['error']}", flush=True)
            continue
        import ragin.benchmark.harness_bridge as hb

        outcome = hb.outcome_from_pipeline_result(pr, q)
        channels = _channel_scores(outcome, qa, suite)
        row = {
            "name": name, "suite": suite, "error": None,
            "served_text": channels["served_text"],
            "cti_analysis": channels["cti_analysis"],
            "serve_path": (outcome.deception or {}).get("serve_path", "")
            if isinstance(outcome.deception, dict) else "",
            "ttps_extracted": outcome.ttps_extracted[:12],
        }
        rows.append(row)
        _save_checkpoint(CHECKPOINT_ARM, args.limit, rows, {})
        print(f"  {name[:52]:<54} served={channels['served_text']:.2f} "
              f"analysis={channels['cti_analysis'] if channels['cti_analysis'] is not None else '-'}",
              flush=True)

    by_suite: dict[str, dict[str, Any]] = {}
    for suite in ("cti_technique", "cti_actor", "deception"):
        srows = [r for r in rows if r.get("suite") == suite and r.get("error") is None]
        served = [r["served_text"] for r in srows]
        analysis = [r["cti_analysis"] for r in srows if r.get("cti_analysis") is not None]
        both = [max(r["served_text"], r["cti_analysis"]) for r in srows
                if r.get("cti_analysis") is not None]
        by_suite[suite] = {
            "rows_scored": len(srows),
            "served_text_avg": round(sum(served) / len(served), 4) if served else None,
            "cti_analysis_avg": round(sum(analysis) / len(analysis), 4) if analysis else None,
            "both_max_avg": round(sum(both) / len(both), 4) if both else None,
        }
    complete = len(rows) >= len(workload)
    artifact = {
        "what": "two-channel §VI metrics — served-text vs CTI-analysis, declared separately",
        "channel_definitions": {
            "served_text": "deception realism: what the attacker actually receives (response_text only)",
            "cti_analysis": (
                "intelligence value: what the pipeline IDENTIFIED (Don extraction — "
                "ttps_extracted, analysis text, candidate_actors); never served to attackers"
            ),
        },
        "config": {
            "generator_model": os.environ.get("RAGIN_HISOKA_MODEL", "(gateway default glm-5.3-flash-free)"),
            "pipeline": "ragin_full config (Chrollo+Don+Hisoka+fiction+verifier, store off)",
        },
        "workload_rows": len(workload),
        "rows_done": len(rows),
        "complete": complete,
        "stopped_early": stopped_early,
        "by_suite": by_suite,
        "serve_path_tally": _tally_serve_paths(rows),
        "per_row": rows,
    }
    # Full runs write the canonical two-channel artifact; --limit runs write a
    # tagged sidecar so a spot-check can never clobber the full-run table
    # (foot-gun observed 2026-09-27: an n=9 spot-check overwrote the 218-row
    # artifact — recovered from the checkpoint, now impossible).
    out = OUT if args.limit is None else OUT.with_name(OUT.stem + f"_limit{args.limit}.json")
    out.write_text(json.dumps(artifact, indent=2))
    print("=" * 76)
    print("TWO-CHANNEL METRICS (current-model ragin_full config)")
    print("=" * 76)
    for suite, s in by_suite.items():
        print(f"  {suite:<15} served_text={s['served_text_avg']} "
              f"cti_analysis={s['cti_analysis_avg']} both_max={s['both_max_avg']} (n={s['rows_scored']})")
    print(f"  rows: {len(rows)}/{len(workload)} | artifact: {out}")
    return 0


def _tally_serve_paths(rows: list[dict]) -> dict[str, int]:
    tally: dict[str, int] = {}
    for r in rows:
        sp = r.get("serve_path") or ""
        if sp:
            tally[sp] = tally.get(sp, 0) + 1
    return tally


if __name__ == "__main__":
    raise SystemExit(main())
