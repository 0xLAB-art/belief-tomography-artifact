"""Rescore one stored live red-team family artifact through the CURRENT verifier.

Reads a persisted live-stratum artifact (space-bunny / deepseek / llama batch),
re-scores every stored draft text with the same ``run_case`` path as the live
harness, and writes a before->after artifact WITHOUT modifying the input.

Purpose (2026-09-27): after the W2 P0 extraction fixes + P1 danger-lexicon pass,
the other two author families must be re-measured so the cross-family
comparison is uniformly post-fix (same method as scripts/merge_llama33_matrix.py).

Usage::

    python scripts/rescore_redteam_family.py \
        --input results/verifier_redteam_live.json \
        --out results/verifier_redteam_live_space-bunny_rescored_after_fix.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verifier_redteam import CHECKS, _pr, run_case  # noqa: E402
from scripts.verifier_redteam_cases import build_cases  # noqa: E402
from scripts.verifier_redteam_live import _AuthoredCase, _wilson  # noqa: E402


def _tally(per_case: dict[str, Any], keys: set[str] | None = None) -> dict[str, Any]:
    """Variant-level P/R tallies over valid drafts (stored OR rescored fields)."""
    tp = fn = fp = tn = invalid = errors = drafts = 0
    for k, v in per_case.items():
        if keys is not None and k not in keys:
            continue
        rej = v["label"] == "should_reject"
        for x in v["variants"]:
            if "error" in x:
                errors += 1
                continue
            if not x.get("valid", True):
                invalid += 1
                continue
            drafts += 1
            caught = bool(x.get("caught"))
            rejected = bool(x.get("rejected"))
            if rej:
                tp += caught
                fn += not caught
            else:
                fp += rejected
                tn += not rejected
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    return {
        "cases": len(per_case) if keys is None else len(keys),
        "valid_drafts": drafts,
        "invalid_drafts": invalid,
        "errors": errors,
        "precision": round(prec, 4) if prec is not None else None,
        "recall": round(rec, 4) if rec is not None else None,
        "tp": tp, "fn": fn, "fp": fp, "tn": tn,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Rescore a stored family artifact through the current verifier")
    parser.add_argument("--input", required=True, help="stored live artifact (read-only)")
    parser.add_argument("--out", required=True, help="rescored artifact (must differ from --input)")
    args = parser.parse_args()

    src_path = ROOT / args.input
    out_path = ROOT / args.out
    if out_path.resolve() == src_path.resolve():
        print("--out must differ from --input", file=sys.stderr)
        return 1
    if out_path.resolve() == (ROOT / "results" / "verifier_redteam_live.json").resolve():
        print("refusing to write the canonical artifact", file=sys.stderr)
        return 1

    src = json.loads(src_path.read_text())
    cases_by_key = {c.key: c for c in build_cases()}

    per_case: dict[str, Any] = {}
    flips = {"resolved_misses": [], "regressed_catches": [], "new_fps": [], "resolved_fps": []}
    missing_cases: list[str] = []

    for key in sorted(src["per_case"]):
        stored = src["per_case"][key]
        case = cases_by_key.get(key)
        if case is None:
            missing_cases.append(key)
            continue
        new_variants: list[dict[str, Any]] = []
        for v in stored["variants"]:
            if "error" in v or not v.get("valid", True):
                # Keep errors / authoring-invalid rows exactly as stored.
                new_variants.append(dict(v))
                continue
            text = v.get("text", "")
            scored = run_case(None, _AuthoredCase(case, text))
            row = {
                "variant": v.get("variant"),
                "text": text,
                "valid": True,
                "rejected": bool(scored["rejected"]),
                "caught": bool(scored["caught"]),
                "misattributed": bool(scored["misattributed"]),
                "fired_targeted": scored["fired_targeted"],
                "issues": scored["issues"],
            }
            was_caught = bool(v.get("caught"))
            was_rejected = bool(v.get("rejected"))
            if case.label == "should_reject":
                if scored["caught"] and not was_caught:
                    flips["resolved_misses"].append({"key": key, "variant": v.get("variant"),
                                                     "issues": scored["issues"]})
                elif was_caught and not scored["caught"]:
                    flips["regressed_catches"].append({"key": key, "variant": v.get("variant"),
                                                       "stored_issues": v.get("issues"),
                                                       "new_issues": scored["issues"]})
            else:
                if scored["rejected"] and not was_rejected:
                    flips["new_fps"].append({"key": key, "variant": v.get("variant"),
                                             "issues": scored["issues"]})
                elif was_rejected and not scored["rejected"]:
                    flips["resolved_fps"].append({"key": key, "variant": v.get("variant"),
                                                  "stored_issues": v.get("issues")})
            new_variants.append(row)

        ok = [v for v in new_variants if "error" not in v and v.get("valid", True)]
        invalid_n = sum(1 for v in new_variants if "error" not in v and not v.get("valid", True))
        verdicts = {v["rejected"] for v in ok}
        per_case[key] = {
            "label": case.label,
            "categories": list(case.categories),
            "checks": list(case.checks),
            "variants": new_variants,
            "errors": sum(1 for v in new_variants if "error" in v),
            "invalid": invalid_n,
            "stable": len(verdicts) <= 1 and len(ok) >= 2,
            "caught_any": bool(ok and case.label == "should_reject" and any(v["caught"] for v in ok)),
            "false_positive": bool(ok and case.label == "should_pass" and all(v["rejected"] for v in ok)),
            "misattributed_any": any(v["misattributed"] for v in ok),
        }

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
    after = _tally(per_case)
    before = _tally(src["per_case"])

    artifact = {
        "what": f"family rescore through the post-P1 verifier (input: {args.input})",
        "model": src.get("model"),
        "base_url_host": src.get("base_url_host"),
        "prompt_version": src.get("prompt_version"),
        "repeats": src.get("repeats"),
        "before_stored_verdicts": before,
        "after_rescored": after,
        "after_wilson95": {
            "recall": _wilson(after["tp"], after["tp"] + after["fn"]),
            "precision": _wilson(after["tp"], after["tp"] + after["fp"]),
        },
        "flips": flips,
        "flip_note": (
            "resolved_misses/regressed_catches compare stored pre-fix catches vs the "
            "post-fix rescore on should_reject drafts; new_fps/resolved_fps on "
            "should_pass drafts. A regressed catch can be CORRECT post-fix behavior "
            "when the pre-fix catch itself fired via an extraction bug (see llama "
            "C-v10-account-alias v3 in the llama ladder artifact)."
        ),
        "missing_case_keys": missing_cases,
        "per_case": per_case,
        "per_check_after": {c: _pr(rows, c) for c in CHECKS},
        "rescore_method": (
            "every stored draft text re-run through run_case (same verifier + "
            "attribution contract as scripts/verifier_redteam.py); identical to the "
            "method of scripts/merge_llama33_matrix.py"
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2))

    print("=" * 76)
    print(f"FAMILY RESCORE — {src.get('model')} ({src.get('base_url_host')})")
    print("=" * 76)
    print(f"  before (stored, pre-fix): P={before['precision']} R={before['recall']} "
          f"(tp={before['tp']} fn={before['fn']} fp={before['fp']} tn={before['tn']}, "
          f"invalid={before['invalid_drafts']})")
    print(f"  after  (rescored, post-P1): P={after['precision']} R={after['recall']} "
          f"(tp={after['tp']} fn={after['fn']} fp={after['fp']} tn={after['tn']})")
    print(f"  wilson95 after: R={artifact['after_wilson95']['recall']} P={artifact['after_wilson95']['precision']}")
    for kind, lst in flips.items():
        detail = ", ".join(f"{f['key']}#v{f['variant']}" for f in lst[:6]) if lst else ""
        print(f"  {kind}: {len(lst)}" + (f" -> {detail}" if detail else ""))
    if missing_cases:
        print(f"  !! case keys absent from build_cases(): {missing_cases}")
    print(f"  artifact: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
