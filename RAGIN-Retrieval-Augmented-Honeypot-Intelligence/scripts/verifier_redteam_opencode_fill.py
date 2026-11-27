"""Fill remaining live red-team cases via opencode free-tier author models.

Context (2026-09-27): the llama-3.3-70b matrix had 19 cases × 3 variants
unauthored because the OpenRouter key's paid headroom was structurally
exhausted (402 "can only afford 44 tokens"; limit_reset=null — promo credit,
no reset cycle). User decision: use opencode's own free model tier instead of
adding credits. This runner shells out to ``opencode run -m <model> --pure``
per authoring call (one-shot agent mode, no stored credentials needed),
extracts the draft from a <<<DRAFT ... DRAFT>>> sentinel, and scores it with
the SAME ``run_case`` path as ``verifier_redteam_live.py``.

Differences vs the canonical live harness (documented in the artifact):
  - author backend is opencode agent mode (temperature not directly settable;
    variance comes from the variant instruction in the shared prompt)
  - per-variant ``author_model`` records which free model authored the draft
    (fallback chain on 429/timeout/refusal)
  - writes ONLY the --out artifact (never results/verifier_redteam_live.json)

Usage::

    python scripts/verifier_redteam_opencode_fill.py \
        --only "K1,K2,K3,K4" \
        --out results/verifier_redteam_live_llama33_opencode_fill.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verifier_redteam import CHECKS, _pr, run_case  # noqa: E402
from scripts.verifier_redteam_live import (  # noqa: E402
    AGREEMENT_FLOOR,
    EXCLUDED_CATEGORIES,
    PRECISION_FLOOR,
    PROMPT_VERSION,
    RECALL_FLOOR,
    _author_prompt,
    _AuthoredCase,
)

# Free-tier author chain: first is primary; later entries are per-call
# fallbacks when the primary 429s, times out, refuses, or drops the sentinel.
AUTHOR_MODELS = [
    "opencode/nemotron-3-ultra-free",
    "opencode/mimo-v2.6-flash-free",
    "opencode/ling-3.0-flash-fin-free",
]
CALL_TIMEOUT_S = 150
SENTINEL_RE = re.compile(r"<<<DRAFT\n(.*?)\nDRAFT>>>", re.DOTALL)

SENTINEL_RULES = (
    "\nOutput format: reply with exactly one block in this shape and NOTHING"
    " else:\n<<<DRAFT\n(the draft text)\nDRAFT>>>"
)


def _flatten_prompt(case: Any, variant: int) -> str:
    msgs = _author_prompt(case, variant)
    return "\n\n".join(m["content"] for m in msgs) + SENTINEL_RULES


def _clean_draft(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith(("text\n", "console\n", "sh\n", "bash\n")):
            cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.strip()
    return cleaned


def _opencode_author(prompt: str, model: str) -> tuple[str | None, str | None]:
    """One authoring call via `opencode run`. Returns (draft, error)."""
    try:
        proc = subprocess.run(
            ["opencode", "run", "-m", model, "--pure", prompt],
            capture_output=True,
            text=True,
            timeout=CALL_TIMEOUT_S,
            cwd=str(ROOT),
        )
    except subprocess.TimeoutExpired:
        return None, f"TimeoutExpired after {CALL_TIMEOUT_S}s ({model})"
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        return None, f"opencode exit {proc.returncode}: {tail[-1][:120] if tail else '(no output)'}"
    m = SENTINEL_RE.search(proc.stdout or "")
    if not m:
        head = (proc.stdout or "").strip().splitlines()
        return None, f"no DRAFT sentinel: {head[0][:120] if head else '(empty output)'}"
    draft = _clean_draft(m.group(1))
    if not any(c.isalnum() for c in draft):
        return None, f"empty/non-alnum draft ({model})"
    return draft, None


def _author_with_fallback(prompt: str) -> tuple[str | None, str | None, str]:
    for model in AUTHOR_MODELS:
        draft, err = _opencode_author(prompt, model)
        if draft is not None:
            return draft, None, model
        print(f"    [fallback] {model}: {err}", flush=True)
    return None, err, ",".join(AUTHOR_MODELS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fill llama red-team gaps via opencode free tier")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--only", required=True, help="comma-separated case keys")
    parser.add_argument("--out", required=True, help="fill artifact path (never the canonical file)")
    args = parser.parse_args()

    out_path = ROOT / args.out
    if out_path.resolve() == (ROOT / "results" / "verifier_redteam_live.json").resolve():
        print("refusing to write the canonical artifact", file=sys.stderr)
        return 1

    from scripts.verifier_redteam_cases import build_cases

    want = {k.strip() for k in args.only.split(",") if k.strip()}
    cases = [c for c in build_cases() if c.key in want]
    cases = [c for c in cases if not (c.categories and c.categories[0] in EXCLUDED_CATEGORIES)]
    missing = want - {c.key for c in cases}
    if missing:
        print(f"unknown/excluded keys ignored: {sorted(missing)}", file=sys.stderr)

    # Resume: reload the fill artifact itself; skip variants already authored.
    artifact: dict[str, Any] = {
        "battery": "verifier red-team — live-LLM stratum (opencode fill)",
        "model": "llama-3.3-70b + opencode-free fill (see author_models)",
        "author_models": AUTHOR_MODELS,
        "base_url_host": "opencode local CLI (free tier)",
        "prompt_version": PROMPT_VERSION,
        "repeats": args.repeats,
        "cases": len(cases),
        "excluded_cases": 0,
        "authored_drafts": 0,
        "authoring_errors": 0,
        "invalid_drafts": 0,
        "usage_totals": {"prompt_tokens": 0, "completion_tokens": 0,
                         "calls": 0, "note": "opencode free tier — not metered"},
        "elapsed_s": 0.0,
        "overall": {},
        "per_check": {},
        "category_agreement": {},
        "unstable_cases": [],
        "misattributed": [],
        "gates": {"recall_floor": RECALL_FLOOR, "precision_floor": PRECISION_FLOOR,
                  "agreement_floor": AGREEMENT_FLOOR},
        "per_case": {},
    }
    if out_path.exists():
        try:
            saved = json.loads(out_path.read_text())
            if saved.get("prompt_version") == PROMPT_VERSION:
                artifact["per_case"].update(saved.get("per_case", {}))
                print(f"[resume] {sum(len(v['variants']) for v in artifact['per_case'].values())}"
                      " variants restored")
        except Exception:  # noqa: BLE001 — corrupt artifact = start fresh
            pass

    def _persist() -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(artifact, indent=2))

    t0 = time.time()
    for case in cases:
        state = artifact["per_case"].setdefault(
            case.key,
            {"label": case.label, "categories": list(case.categories),
             "checks": list(case.checks), "variants": [], "author": "opencode-free-fill"},
        )
        have = {v.get("variant") for v in state["variants"] if "error" not in v}
        for variant in range(1, args.repeats + 1):
            if variant in have:
                continue
            prompt = _flatten_prompt(case, variant)
            draft, err, author_model = _author_with_fallback(prompt)
            if draft is None:
                state["variants"].append(
                    {"variant": variant, "error": f"{type(err).__name__ if err else 'Error'}: {err}"[:200],
                     "author_model": author_model})
                print(f"  {case.key:<28} v{variant} ERROR: {err}", flush=True)
                _persist()
                continue
            scored = run_case(None, _AuthoredCase(case, draft))
            valid = any(c.isalnum() for c in draft)
            state["variants"].append(
                {
                    "variant": variant,
                    "text": draft,
                    "author_model": author_model,
                    "valid": valid,
                    "rejected": bool(scored["rejected"] and valid),
                    "caught": bool(scored["caught"] and valid),
                    "misattributed": bool(scored["misattributed"] and valid),
                    "fired_targeted": scored["fired_targeted"],
                    "issues": scored["issues"] if valid
                    else ["authoring-invalid: empty/one-char draft (model refusal to author)"],
                })
            flag = "caught" if scored["caught"] and valid else ("-" if case.label == "should_pass" else "MISS")
            print(f"  {case.key:<28} v{variant} {flag:<6} by={author_model.split('/')[-1]}", flush=True)
            _persist()

        # Per-case rollup (same semantics as the live harness)
        ok = [v for v in state["variants"] if "error" not in v and v.get("valid", True)]
        invalid_n = sum(1 for v in state["variants"] if "error" not in v and not v.get("valid", True))
        verdicts = {v["rejected"] for v in ok}
        state["errors"] = sum(1 for v in state["variants"] if "error" in v)
        state["invalid"] = invalid_n
        state["stable"] = len(verdicts) <= 1 and len(ok) >= 2
        state["caught_any"] = bool(ok and case.label == "should_reject" and any(v["caught"] for v in ok))
        state["false_positive"] = bool(ok and case.label == "should_pass" and all(v["rejected"] for v in ok))
        state["misattributed_any"] = any(v["misattributed"] for v in ok)
        _persist()

    # ── metrics over valid variant rows (same _pr machinery as offline) ────
    rows: list[dict[str, Any]] = []
    for case in cases:
        for v in artifact["per_case"][case.key]["variants"]:
            if "error" in v or not v.get("valid", True):
                continue
            rows.append(
                {"key": case.key, "label": case.label, "categories": list(case.categories),
                 "checks": list(case.checks), "rejected": v["rejected"], "caught": v["caught"],
                 "misattributed": v["misattributed"], "fired_targeted": v["fired_targeted"],
                 "false_positive_checks": []})
    overall = _pr(rows)
    artifact["authored_drafts"] = len(rows)
    artifact["authoring_errors"] = sum(v.get("errors", 0) for v in artifact["per_case"].values())
    artifact["invalid_drafts"] = sum(v.get("invalid", 0) for v in artifact["per_case"].values())
    artifact["elapsed_s"] = round(time.time() - t0, 1)
    artifact["overall"] = overall
    artifact["per_check"] = {c: _pr(rows, c) for c in CHECKS}
    rejects = [c for c in cases if c.label == "should_reject"]
    passes = [c for c in cases if c.label == "should_pass"]
    cat_rej = sum(1 for c in rejects if artifact["per_case"][c.key]["caught_any"])
    cat_agree = cat_rej + sum(1 for c in passes if not artifact["per_case"][c.key]["false_positive"])
    cat_total = len(rejects) + len(passes)
    artifact["category_agreement"] = {
        "agree": cat_agree, "total": cat_total,
        "rate": round(cat_agree / cat_total, 4) if cat_total else 1.0}
    artifact["unstable_cases"] = sorted(
        k for k, v in artifact["per_case"].items() if not v.get("stable", False))
    artifact["misattributed"] = [
        {"key": k, "issues": [v["issues"] for v in vv["variants"] if "error" not in v]}
        for k, vv in artifact["per_case"].items() if vv.get("misattributed_any")]
    _persist()

    print("\n" + "=" * 76)
    print("OPENCODE FILL STRATUM (subset metrics — merge before gating)")
    print("=" * 76)
    o = overall
    print(f"  drafts={len(rows)} errors={artifact['authoring_errors']} "
          f"invalid={artifact['invalid_drafts']}")
    if o.get("should_reject") or o.get("should_pass"):
        print(f"  overall: P={o['precision']:.3f} R={o['recall']:.3f} "
              f"(caught {o['true_positives']}/{o['should_reject']}, FP {o['false_positives']}/{o['should_pass']})")
    print(f"  category agreement: {cat_agree}/{cat_total} = {artifact['category_agreement']['rate']}")
    print(f"  artifact: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
