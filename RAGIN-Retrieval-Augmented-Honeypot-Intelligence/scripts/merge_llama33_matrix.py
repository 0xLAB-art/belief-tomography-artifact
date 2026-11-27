"""Merge the llama-3.3-70b third-family matrix to completion and rescore.

Sources (2026-09-27):
  - results/verifier_redteam_live_llama33_best.json        75 completed cases (pre-fix verdicts)
  - results/verifier_redteam_live_llama33_batch1_3cases_20260927.json
                                                           3 cases recovered from an orphaned batch
  - results/verifier_redteam_live_llama33_opencode_fill.json
                                                           16 cases authored via opencode free tier
                                                           (OpenRouter paid headroom exhausted; user decision)

Outputs:
  - results/verifier_redteam_live_llama33_complete.json   merged matrix, ALL drafts rescored
                                                           through the current (post-P1) verifier
  - results/verifier_llama33_rescored_after_fix.json      ladder updated with `after_complete`

Method notes:
  - Every stored draft text is re-run through run_case so the merged matrix is
    uniformly post-fix (the original 75 carry pre-fix verdicts).
  - Author fallback is disclosed per case: `author_model` lists which backend
    authored each variant; `author_pool` distinguishes llama-only cases from
    opencode-filled cases (paper must flag the substitution — author-swap is
    a variance source, not a verifier measurement).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verifier_redteam import CHECKS, _pr, run_case  # noqa: E402
from scripts.verifier_redteam_cases import build_cases  # noqa: E402
from scripts.verifier_redteam_live import _AuthoredCase  # noqa: E402

BEST = ROOT / "results" / "verifier_redteam_live_llama33_best.json"
RECOVERED = ROOT / "results" / "verifier_redteam_live_llama33_batch1_3cases_20260927.json"
FILL = ROOT / "results" / "verifier_redteam_live_llama33_opencode_fill.json"
OUT = ROOT / "results" / "verifier_redteam_live_llama33_complete.json"
LADDER = ROOT / "results" / "verifier_llama33_rescored_after_fix.json"

OPENCODE_FILL_KEYS = {
    "C-v23a-adjective-alias-drift", "D-neg-v22-uptime-load",
    "D-v22-forward-noun-tell", "D-v22-mailbox-dump",
    "D-v22-reserved-for-refusal", "D-v22-subjectless-refusal",
    "I-neg-v16-whoami-no-ctx-ok", "I-neg-v17-id-un-variant-ok",
    "I-neg-v23a-adjective-account-ok", "I-neg-v23b-composite-truthful",
    "I-v16-whoami-no-ctx", "I-v17-id-full-strict", "I-v17-id-un-variant-wrong",
    "I-v20-uid-value-not-user", "I-v23b-command-prefixed-whoami",
    "I-v23b-composite-whoami",
}


def _variants_with_rescore(case: Any, variants: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    """Rescore each stored draft through the current verifier; keep errors."""
    out: list[dict[str, Any]] = []
    authors: set[str] = set()
    for v in variants:
        if "error" in v:
            out.append(v)
            continue
        text = v.get("text", "")
        scored = run_case(None, _AuthoredCase(case, text))
        valid = any(c.isalnum() for c in text)
        authors.add(v.get("author_model", "meta-llama/llama-3.3-70b-instruct"))
        out.append({
            "variant": v.get("variant"),
            "text": text,
            "author_model": v.get("author_model", "meta-llama/llama-3.3-70b-instruct"),
            "valid": valid,
            "rejected": bool(scored["rejected"] and valid),
            "caught": bool(scored["caught"] and valid),
            "misattributed": bool(scored["misattributed"] and valid),
            "fired_targeted": scored["fired_targeted"],
            "issues": scored["issues"] if valid
            else ["authoring-invalid: empty/one-char draft (model refusal to author)"],
        })
    return out, ("+".join(sorted(authors)) if authors else "")


def main() -> int:
    best = json.loads(BEST.read_text())
    recovered = json.loads(RECOVERED.read_text())
    fill = json.loads(FILL.read_text())

    cases_by_key = {c.key: c for c in build_cases()}
    per_case: dict[str, Any] = {}

    def take(src: dict[str, Any], key: str, tag: str) -> None:
        if key not in src.get("per_case", {}):
            return
        case = cases_by_key.get(key)
        if case is None:
            print(f"  !! no offline case for {key} — skipped", file=sys.stderr)
            return
        variants, authors = _variants_with_rescore(case, src["per_case"][key]["variants"])
        ok = [v for v in variants if "error" not in v and v.get("valid", True)]
        invalid_n = sum(1 for v in variants if "error" not in v and not v.get("valid", True))
        verdicts = {v["rejected"] for v in ok}
        per_case[key] = {
            "label": case.label,
            "categories": list(case.categories),
            "checks": list(case.checks),
            "variants": variants,
            "author_pool": authors,
            "source": tag,
            "errors": sum(1 for v in variants if "error" in v),
            "invalid": invalid_n,
            "stable": len(verdicts) <= 1 and len(ok) >= 2,
            "caught_any": bool(ok and case.label == "should_reject" and any(v["caught"] for v in ok)),
            "false_positive": bool(ok and case.label == "should_pass" and all(v["rejected"] for v in ok)),
            "misattributed_any": any(v["misattributed"] for v in ok),
        }

    for key in sorted(best["per_case"]):
        if key in OPENCODE_FILL_KEYS:
            continue
        take(best, key, "llama33_best")
    for key in sorted(recovered["per_case"]):
        take(recovered, key, "llama33_batch1_recovered")
    for key in sorted(fill["per_case"]):
        take(fill, key, "opencode_fill")

    # ── metrics over valid variant rows (same _pr machinery) ──────────────
    rows: list[dict[str, Any]] = []
    for key in sorted(per_case):
        meta = per_case[key]
        for v in meta["variants"]:
            if "error" in v or not v.get("valid", True):
                continue
            rows.append({
                "key": key, "label": meta["label"], "categories": meta["categories"],
                "checks": meta["checks"], "rejected": v["rejected"], "caught": v["caught"],
                "misattributed": v["misattributed"], "fired_targeted": v["fired_targeted"],
                "false_positive_checks": [],
            })
    overall = _pr(rows)
    drafts = len(rows)
    authoring_errors = sum(v["errors"] for v in per_case.values())
    invalid_drafts = sum(v["invalid"] for v in per_case.values())

    llama_only = sorted(k for k, v in per_case.items() if v["source"] != "opencode_fill")
    filled = sorted(OPENCODE_FILL_KEYS & set(per_case))

    artifact = {
        "battery": "verifier red-team — live-LLM stratum (llama-3.3-70b, COMPLETE)",
        "model": "meta-llama/llama-3.3-70b-instruct",
        "base_url_host": "openrouter.ai",
        "completion_note": (
            "19 cases that 402'd mid-run completed 2026-09-27: 3 recovered from an "
            "orphaned batch artifact (llama), 16 authored via opencode free tier "
            "(nemotron-3-ultra-free) after the OpenRouter key's paid headroom was "
            "structurally exhausted (limit_reset=null; user decision). ALL drafts "
            "rescored through the post-P1 verifier so the merged matrix is uniform."
        ),
        "author_disclosure": {
            "llama_only_cases": len(llama_only),
            "opencode_filled_cases": len(filled),
            "filled_keys": filled,
            "fill_models": fill.get("author_models", []),
            "paper_note": (
                "Author-swap is a variance source, not a verifier measurement: the "
                "16 filled cases probe cross-author generalization. Report matrix "
                "metrics with and without the filled cases."
            ),
        },
        "prompt_version": 2,
        "repeats": 3,
        "cases": len(per_case),
        "excluded_cases": 1,
        "authored_drafts": drafts,
        "authoring_errors": authoring_errors,
        "invalid_drafts": invalid_drafts,
        "usage_totals": {"note": "llama via OpenRouter credits; fill via opencode free tier — not metered"},
        "overall": overall,
        "per_check": {c: _pr(rows, c) for c in CHECKS},
        "rescored_without_fill": {},
        "unstable_cases": sorted(k for k, v in per_case.items() if not v["stable"]),
        "misattributed": [
            {"key": k, "issues": [v["issues"] for v in vv["variants"] if "error" not in v]}
            for k, vv in sorted(per_case.items()) if vv["misattributed_any"]],
        "per_case": per_case,
    }

    # Ablation: metrics over llama-authored drafts only (75 + 3 cases)
    rows_llama = [r for r in rows if r["key"] not in OPENCODE_FILL_KEYS]
    artifact["rescored_without_fill"] = _pr(rows_llama)

    OUT.write_text(json.dumps(artifact, indent=2))

    # ── update the ladder artifact ────────────────────────────────────────
    ladder = json.loads(LADDER.read_text())
    ladder["after_complete"] = {
        "precision": overall["precision"],
        "recall": overall["recall"],
        "tp": overall["true_positives"],
        "fn": overall["false_negatives"],
        "fp": overall["false_positives"],
        "tn": overall["true_negatives"],
        "cases": len(per_case),
        "drafts": drafts,
        "authoring_errors": authoring_errors,
        "note": (
            "completed matrix: 78 llama-authored cases + 16 opencode-filled cases "
            "(author-swap disclosed in author_disclosure), all drafts rescored "
            "through the post-P1 verifier on 2026-09-27"
        ),
        "rescored_without_fill": {
            "precision": artifact["rescored_without_fill"]["precision"],
            "recall": artifact["rescored_without_fill"]["recall"],
            "drafts": len(rows_llama),
        },
    }
    ladder["completion"] = {
        "date": "2026-09-27",
        "fill_runner": "scripts/verifier_redteam_opencode_fill.py",
        "merge_script": "scripts/merge_llama33_matrix.py",
        "reason": "OpenRouter paid headroom structurally exhausted (402, limit_reset=null)",
        "user_decision": "opencode free-tier models as substitute author",
    }
    LADDER.write_text(json.dumps(ladder, indent=2))

    # ── console summary ───────────────────────────────────────────────────
    print("=" * 76)
    print("LLAMA-3.3-70B THIRD-FAMILY MATRIX — COMPLETE")
    print("=" * 76)
    print(f"  cases={len(per_case)} drafts={drafts} authoring_errors={authoring_errors} invalid={invalid_drafts}")
    print(f"  overall (all authors): P={overall['precision']:.4f} R={overall['recall']:.4f} "
          f"(caught {overall['true_positives']}/{overall['should_reject']}, "
          f"FP {overall['false_positives']}/{overall['should_pass']})")
    nf = artifact["rescored_without_fill"]
    print(f"  llama-only ablation:   P={nf['precision']:.4f} R={nf['recall']:.4f} ({len(rows_llama)} drafts)")
    agree = sum(
        1 for v in per_case.values()
        if v["caught_any"] or (v["label"] == "should_pass" and not v["false_positive"]))
    print(f"  category agreement: filled={agree}/{len(per_case)}")
    print(f"  unstable: {len(artifact['unstable_cases'])} -> {', '.join(artifact['unstable_cases'][:8])}")
    print(f"  misattributed: {len(artifact['misattributed'])}")
    print(f"  artifacts: {OUT.name} + ladder updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
