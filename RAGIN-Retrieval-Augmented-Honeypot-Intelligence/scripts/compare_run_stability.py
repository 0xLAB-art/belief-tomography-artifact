#!/usr/bin/env python3
"""Run-to-run stability comparison for the live 218-query benchmark.

Compares the two persisted zodiac runs (same corpus, same engine, same
wiring; independent LLM sessions) row-by-row and emits the stability
artifact the methodology section cites:

  - per-suite means and deltas
  - pass-decision agreement (would a reviewer's verdict replicate?)
  - per-row mean absolute difference (LLM-stratum variance)
  - headline metrics (TTP counts, honeytokens, engagement)

Usage:
    python3 scripts/compare_run_stability.py \
        --run-a results/live_benchmark_zodiac_20260922.json \
        --run-b results/live_benchmark_zodiac_20260922_run2.json \
        --out results/stability_run1_vs_run2.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Persona rows carry suite tag "deception" in the artifacts (not "persona_realism").
SUITES = ("cti_technique", "cti_actor", "deception")


def load_rows(path: str) -> dict[tuple[str, str], dict]:
    data = json.loads(Path(path).read_text())
    rows: dict[tuple[str, str], dict] = {}
    for suite_key in ("technique_results", "actor_results", "persona_results"):
        for row in data.get(suite_key, []):
            rows[(row["suite"], row["name"])] = row
    return rows, data


def suite_rows(rows: dict[tuple[str, str], dict], suite: str) -> list[dict]:
    return [r for (s, _), r in rows.items() if s == suite]


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def compare_suite(
    rows_a: dict[tuple[str, str], dict],
    rows_b: dict[tuple[str, str], dict],
    suite: str,
) -> dict:
    keys = sorted(set(rows_a) & set(rows_b) & {k for k in rows_a if k[0] == suite})
    only_a = sorted(k for k in rows_a if k[0] == suite and k not in rows_b)
    only_b = sorted(k for k in rows_b if k[0] == suite and k not in rows_a)

    scores_a = [rows_a[k]["score"] for k in keys]
    scores_b = [rows_b[k]["score"] for k in keys]
    diffs = [b - a for a, b in zip(scores_a, scores_b, strict=True)]
    abs_diffs = [abs(d) for d in diffs]
    pass_agree = sum(
        1 for k in keys if rows_a[k]["passed"] == rows_b[k]["passed"]
    )

    return {
        "suite": suite,
        "paired_rows": len(keys),
        "unpaired_run_a": len(only_a),
        "unpaired_run_b": len(only_b),
        "mean_run_a": round(mean(scores_a), 4),
        "mean_run_b": round(mean(scores_b), 4),
        "delta": round(mean(scores_b) - mean(scores_a), 4),
        "mean_abs_row_diff": round(mean(abs_diffs), 4),
        "max_abs_row_diff": round(max(abs_diffs), 4) if abs_diffs else 0.0,
        "pass_agreement": round(pass_agree / len(keys), 4) if keys else 0.0,
        "pass_agree_count": pass_agree,
    }


def load_corrected(path: str) -> dict[tuple[str, str], dict]:
    """Load the judge-audited rows (rescore_judge_panel.py output).

    Pass decisions are recomputed at the judge's 0.3 threshold so the
    audited comparison uses the same contract as the raw one.
    """
    data = json.loads(Path(path).read_text())
    rows: dict[tuple[str, str], dict] = {}
    for row in data["corrected_rows"]:
        row = dict(row)
        row["passed"] = row["score"] >= 0.3
        rows[(row["suite"], row["name"])] = row
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-a", default="results/live_benchmark_zodiac_20260922.json")
    ap.add_argument("--run-b", default="results/live_benchmark_zodiac_20260922_run2.json")
    ap.add_argument("--out", default="results/stability_run1_vs_run2.json")
    ap.add_argument("--audited-a", default="results/live_benchmark_zodiac_20260922_judgescored.json")
    ap.add_argument("--audited-b", default="results/live_benchmark_zodiac_20260922_run2_judgescored.json")
    ap.add_argument("--no-audited", action="store_true",
                    help="skip the judge-audited panel comparison")
    args = ap.parse_args()

    rows_a, data_a = load_rows(args.run_a)
    rows_b, data_b = load_rows(args.run_b)

    suite_comparisons = [compare_suite(rows_a, rows_b, s) for s in SUITES]

    # Composite over all paired rows.
    keys_all = sorted(set(rows_a) & set(rows_b))
    all_a = [rows_a[k]["score"] for k in keys_all]
    all_b = [rows_b[k]["score"] for k in keys_all]
    pass_agree_all = sum(1 for k in keys_all if rows_a[k]["passed"] == rows_b[k]["passed"])

    ma, mb = data_a["metrics"], data_b["metrics"]

    composite = {
        "paired_rows": len(keys_all),
        "composite_run_a": round(mean(all_a), 4),
        "composite_run_b": round(mean(all_b), 4),
        "delta": round(mean(all_b) - mean(all_a), 4),
        "mean_abs_row_diff": round(mean([abs(b - a) for a, b in zip(all_a, all_b, strict=True)]), 4),
        "pass_agreement": round(pass_agree_all / len(keys_all), 4) if keys_all else 0.0,
    }

    # Verdict bands: |delta| < 0.03 and pass agreement >= 0.95 => stable.
    stable = abs(composite["delta"]) < 0.03 and composite["pass_agreement"] >= 0.95
    composite["verdict"] = "stable" if stable else "review"

    artifact = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_a": {"path": args.run_a, "elapsed_s": data_a.get("elapsed_s"), "metrics": ma},
        "run_b": {"path": args.run_b, "elapsed_s": data_b.get("elapsed_s"), "metrics": mb},
        "suites": suite_comparisons,
        "composite": composite,
        "headline_metric_deltas": {
            "ttps_detected": {"run_a": ma.get("ttps_detected"), "run_b": mb.get("ttps_detected")},
            "ttps_detected_unique": {"run_a": ma.get("ttps_detected_unique"), "run_b": mb.get("ttps_detected_unique")},
            "sessions_with_engagement": {
                "run_a": ma.get("sessions_with_engagement"),
                "run_b": mb.get("sessions_with_engagement"),
            },
            "persona_correct_assignments": {
                "run_a": ma.get("persona_correct_assignments"),
                "run_b": mb.get("persona_correct_assignments"),
            },
        },
    }

    # Judge-audited panel: recompute the comparison on the corrected rows
    # (rescore_judge_panel.py) so agreement numbers reflect the audited
    # persona judge rather than the raw one.
    if not args.no_audited:
        aud_a_path, aud_b_path = Path(args.audited_a), Path(args.audited_b)
        if aud_a_path.exists() and aud_b_path.exists():
            rows_aud_a = load_corrected(str(aud_a_path))
            rows_aud_b = load_corrected(str(aud_b_path))
            # Technique/actor rows are untouched by the audit; splice them
            # from the raw runs so the audited composite covers all 218 rows.
            for k, r in rows_a.items():
                if k[0] != "deception" and k not in rows_aud_a:
                    rows_aud_a[k] = r
            for k, r in rows_b.items():
                if k[0] != "deception" and k not in rows_aud_b:
                    rows_aud_b[k] = r
            aud_suites = [compare_suite(rows_aud_a, rows_aud_b, s) for s in SUITES]
            keys_aud = sorted(set(rows_aud_a) & set(rows_aud_b))
            aud_a_scores = [rows_aud_a[k]["score"] for k in keys_aud]
            aud_b_scores = [rows_aud_b[k]["score"] for k in keys_aud]
            aud_agree = sum(1 for k in keys_aud if rows_aud_a[k]["passed"] == rows_aud_b[k]["passed"])
            aud_composite = {
                "paired_rows": len(keys_aud),
                "composite_run_a": round(mean(aud_a_scores), 4),
                "composite_run_b": round(mean(aud_b_scores), 4),
                "delta": round(mean(aud_b_scores) - mean(aud_a_scores), 4),
                "mean_abs_row_diff": round(mean([abs(b - a) for a, b in zip(aud_a_scores, aud_b_scores, strict=True)]), 4),
                "pass_agreement": round(aud_agree / len(keys_aud), 4) if keys_aud else 0.0,
            }
            aud_composite["verdict"] = (
                "stable" if abs(aud_composite["delta"]) < 0.03
                and aud_composite["pass_agreement"] >= 0.95 else "review"
            )
            panel = json.loads(
                (Path(__file__).resolve().parent.parent
                 / "results" / "live_benchmark_judge_panel_corrected.json").read_text()
            )
            artifact["audited_panel"] = {
                "what": ("comparison recomputed on the judge-audited rows "
                         "(harness artifacts reclassified, bait deployments "
                         "credited, floats rounded); technique/actor rows "
                         "are unchanged and spliced from the raw runs. "
                         "Suite means retain the reclassified harness row at "
                         "its recorded 0.0 (it is a row of the campaign); the "
                         "deception-only means excluding harness artifacts "
                         "are in corrections.per_run"),
                "sources": {"run_a": str(aud_a_path), "run_b": str(aud_b_path)},
                "suites": aud_suites,
                "composite": aud_composite,
                "corrections": {
                    "canary_bias_magnitude": panel.get("total_canary_bias_magnitude"),
                    "per_run": [
                        {"source": r["source"], "mean_raw": r["mean_raw"],
                         "mean_corrected": r["mean_corrected_deception"],
                         "bait_credit_rows": r["bait_credit_rows"],
                         "reclassified_harness": r["reclassified_harness"]}
                        for r in panel.get("runs", [])
                    ],
                },
            }

    out = Path(args.out)
    out.write_text(json.dumps(artifact, indent=2) + "\n")

    # Console summary.
    print(f"Stability: run_a vs run_b -> {out}")
    print(f"  composite: {composite['composite_run_a']} vs {composite['composite_run_b']} "
          f"(delta {composite['delta']:+.4f}, MAD {composite['mean_abs_row_diff']:.4f}, "
          f"pass-agree {composite['pass_agreement']:.3f}) -> {composite['verdict']}")
    for s in suite_comparisons:
        print(f"  {s['suite']:<16} {s['mean_run_a']:.3f} vs {s['mean_run_b']:.3f} "
              f"(delta {s['delta']:+.3f}, MAD {s['mean_abs_row_diff']:.3f}, "
              f"pass-agree {s['pass_agreement']:.3f}, n={s['paired_rows']})")
    if "audited_panel" in artifact:
        ap_comp = artifact["audited_panel"]["composite"]
        print(f"  audited composite: {ap_comp['composite_run_a']} vs "
              f"{ap_comp['composite_run_b']} (delta {ap_comp['delta']:+.4f}, "
              f"pass-agree {ap_comp['pass_agreement']:.3f}) -> {ap_comp['verdict']}")
    print(f"  ttps_detected: {ma.get('ttps_detected')} vs {mb.get('ttps_detected')} "
          f"(unique {ma.get('ttps_detected_unique')} vs {mb.get('ttps_detected_unique')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
