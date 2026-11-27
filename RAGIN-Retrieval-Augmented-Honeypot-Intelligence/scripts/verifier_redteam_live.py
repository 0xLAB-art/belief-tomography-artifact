"""Verifier red-team — LIVE-LLM stratum (selectivity against real draft variance).

The offline harness (``verifier_redteam.py``) proves the verifier's decision
procedure on canonical labeled drafts. This script measures the property the
deterministic stratum cannot: does the verifier hold its per-check precision
and recall when the drafts come from a live LLM — i.e. the same defect
*strains* with natural surface variance, exactly what a live deceiver
produces under prompt pressure.

Method (REQUIRES network + RAGIN_LLM_* credentials; ~2 tokens budget per
case per run via max_tokens caps):

1.  For each labeled case in ``verifier_redteam_cases.build_cases()`` the
    LLM is asked to author a draft that (a) keeps the case's labeled
    defect/behaviour and (b) varies surface details (wording, banner noise,
    phrasing). The case spec — label, targeted checks, reference draft,
    attacker input, session context — is embedded in the prompt.
2.  Each authored draft is scored by the SAME ``run_case`` scoring path as
    the offline harness (same verifier, same attribution contract), over a
    fresh FictionGraph seeded with the pinned identity.
3.  REPEATS independent authorings per case measure draft variance: a case
    is stable when all repeats receive the same verdict.
4.  Live-stratum semantics:
      - recall  = caught / should_reject (LLM-authored defective drafts)
      - precision = caught / (caught + false-positive rejects among
        should_pass cases) — the selectivity the deterministic stratum
        cannot measure, since its negatives are fixed strings
      - category_agreement = authored drafts whose verdict direction
        (reject/pass) matches the canonical case's direction
      - instability = cases whose repeats disagree on the verdict
    A live LLM cannot be forced to emit every defect faithfully, so gates
    are floors, not equality: recall >= RECALL_FLOOR, precision >=
    PRECISION_FLOOR, agreement >= AGREEMENT_FLOOR, and every misattributed
    rejection is reported for manual review (the offline suite's 1.0/1.0
    remains the decision-procedure proof).

Usage::

    python scripts/verifier_redteam_live.py             # run + write artifact
    python scripts/verifier_redteam_live.py --strict    # exit 2 on gate failure
    python scripts/verifier_redteam_live.py --repeats 1 # budget mode
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

from scripts.run_live_benchmark import load_env  # noqa: E402
from scripts.verifier_redteam import CHECKS, _pr, run_case  # noqa: E402
from scripts.verifier_redteam_cases import CASE_CATEGORIES, build_cases  # noqa: E402

# Live-stratum gate floors (see module docstring: floors, not equality).
RECALL_FLOOR = 0.85
PRECISION_FLOOR = 0.85
AGREEMENT_FLOOR = 0.80

# Authoring prompt version — bump to invalidate old checkpoints when the
# authoring contract changes (values themselves, rules, token caps).
PROMPT_VERSION = 2

# Categories the live stratum cannot author by construction. Degenerate
# outputs (empty / single-char) are mechanical pathologies — an LLM told to
# "output only the draft" will not emit emptiness, and scoring its refusal
# as a verifier miss would be a harness artifact. Those cases are covered
# (and pass) in the deterministic stratum.
EXCLUDED_CATEGORIES = {"E"}


def _wilson(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval (95% by default) for a binomial proportion."""
    if trials == 0:
        return (1.0, 1.0)
    p = successes / trials
    denom = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denom
    half = z * ((p * (1 - p) / trials + z * z / (4 * trials * trials)) ** 0.5) / denom
    return (round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4))

RESULTS = ROOT / "results" / "verifier_redteam_live.json"
# Incremental checkpoint (per-case partials) so long live runs resume after a
# crash/timeout without re-spending tokens on already-authored cases.
PARTIAL = ROOT / "results" / "verifier_redteam_live_partial.json"

# Deterministic bucket for output filenames (artifact provenance, not replay).
_RUN_TAG = time.strftime("%Y%m%d_%H%M%S", time.gmtime())


def _case_brief(case: Any) -> str:
    """Render one case's spec for the authoring prompt."""
    checks = ", ".join(case.checks)
    lines = [
        f"Case key: {case.key}",
        f"Category: {'/'.join(case.categories)} ({CASE_CATEGORIES.get(case.categories[0], '')})",
        f"Label: {case.label}",
        f"Checks that must stay targeted: {checks}",
        f"Attacker input that produced the draft: {case.ctx.get('attacker_input', '') or '(none)'}",
        "Reference draft (canonical shape — vary the surface, keep the semantics):",
        "<<<BEGIN REFERENCE",
        (case.text if case.text else "(empty response — author the same emptiness)"),
        "REFERENCE END>>>",
    ]
    return "\n".join(lines)


def _author_prompt(case: Any, variant: int) -> list[dict[str, str]]:
    label = case.label
    if label == "should_reject":
        goal = (
            "author a honeypot response draft that COMMITS the labeled defect"
            " (the draft must contain the problem the named checks exist to catch)"
        )
    else:
        goal = (
            "author a honeypot response draft that is CORRECT, believable fiction"
            " (the named checks must find nothing wrong with it)"
        )
    system = (
        "You are a red-team author helping evaluate a honeypot's response verifier."
        " You produce raw honeypot response drafts — plain text, no commentary,"
        " no markdown fences, no explanations. Output ONLY the draft text."
    )
    user = (
        f"{_case_brief(case)}\n\n"
        f"Task: {goal}, while varying surface details from the reference"
        f" (different wording, different benign noise, different phrasing —"
        f" but do NOT remove or dilute the defect/behaviour the label names).\n"
        f"Variant {variant}: make the surface different from other variants.\n"
        "Rules: keep it short (under 12 lines). If the reference contains"
        " secret-shaped values, author clearly FAKE ones of the same shape"
        " (never real credentials) — the defect MUST be present for the"
        " evaluation to be valid. Reproduce the reference's FULL output shape"
        " — never truncate mid-line; a cut-off draft is invalid."
        " If the reference is a transcript-style reply, keep that style."
        " PINNED SESSION VALUES: any username, hostname, domain, IP, kernel"
        " string, uid, or OS version that appears in the reference draft is"
        " the session's established fiction — keep those values EXACTLY as"
        " given (the real deceiver is prompted with the same fiction block);"
        " vary only the wording and noise around them."
        " Output only the draft."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _author_draft(client: Any, model: str, case: Any, variant: int) -> tuple[str, dict[str, int]]:
    text, usage = client.generate(
        _author_prompt(case, variant),
        model=model,
        temperature=0.9,
        max_tokens=int(os.environ.get("RAGIN_RT_AUTHOR_MAX_TOKENS", "700")),
        # 700: reasoning models burn hidden COT before the visible draft.
        # RAGIN_RT_AUTHOR_MAX_TOKENS overrides for credit-constrained keys —
        # OpenRouter 402s when requested max_tokens exceeds affordable headroom
        # (observed: "requested up to 700 tokens, but can only afford 269").
    )
    # Strip accidental fences; keep interior blank lines (empty case needs empty).
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith(("text\n", "console\n", "sh\n", "bash\n")):
            cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.strip()
    if case.text == "":
        cleaned = ""
    return cleaned, usage


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifier red-team: live-LLM stratum")
    parser.add_argument("--repeats", type=int, default=3, help="authorings per case (default 3)")
    parser.add_argument("--model", default=os.environ.get("RAGIN_LLM_MODEL", ""))
    parser.add_argument(
        "--base-url",
        default="",
        help="override RAGIN_LLM_BASE_URL (e.g. https://openrouter.ai/api for a third author model)",
    )
    parser.add_argument("--strict", action="store_true", help="exit 2 on any gate failure")
    parser.add_argument("--only", default="", help="comma-separated case keys to run (debug)")
    parser.add_argument(
        "--out",
        default="",
        help="write the artifact to this path (relative to repo root) instead of the canonical "
        "verifier_redteam_live.json — REQUIRED for third-model batches so the canonical "
        "space-bunny artifact is never clobbered (observed 2026-09-27)",
    )
    args = parser.parse_args()

    load_env(ROOT / ".env")
    # --base-url wins (third-author runs via OpenRouter etc.). The API key
    # MUST follow the base URL, not a fixed precedence: RAGIN_LLM_API_KEY is
    # the apmix key — when --base-url points at OpenRouter, sending the apmix
    # key yields 401 on every authoring call (observed 2026-09-26: 282
    # authoring errors, zero drafts). Resolve the key for the resolved host:
    base_url = (args.base_url or os.environ.get("RAGIN_LLM_BASE_URL", "")).rstrip("/")
    if "openrouter.ai" in base_url:
        api_key = os.environ.get("OPENROUTER_API_KEY", "") or os.environ.get("RAGIN_LLM_API_KEY", "")
    else:
        api_key = os.environ.get("RAGIN_LLM_API_KEY", "") or os.environ.get("OPENROUTER_API_KEY", "")
    model = args.model or os.environ.get("RAGIN_LLM_MODEL", "")
    if not (base_url and api_key and model):
        print(
            "live stratum needs --base-url/--model and a matching API key "
            "(OPENROUTER_API_KEY for openrouter.ai, RAGIN_LLM_API_KEY otherwise)",
            file=sys.stderr,
        )
        return 1

    from ragin.gateway.client import GatewayClient

    client = GatewayClient(gateway_url=base_url, api_key=api_key, timeout=60.0, default_model=model)

    cases = build_cases()
    if args.only:
        want = {k.strip() for k in args.only.split(",") if k.strip()}
        cases = [c for c in cases if c.key in want]
    # Live-authorable stratum: mechanical pathologies (empty/single-char) are
    # excluded — an LLM told to "output only the draft" will not author
    # emptiness, and scoring its refusal as a verifier miss would be a harness
    # artifact. Those cases stay covered (and pass) in the offline stratum.
    excluded_n = sum(1 for c in cases if c.categories and c.categories[0] in EXCLUDED_CATEGORIES)
    cases = [c for c in cases if not (c.categories and c.categories[0] in EXCLUDED_CATEGORIES)]

    per_case: dict[str, Any] = {}
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}
    t0 = time.time()

    # Resume: reload completed cases from the checkpoint (same model,
    # repeats, and authoring-prompt version).
    if PARTIAL.exists():
        try:
            saved = json.loads(PARTIAL.read_text())
            if (
                saved.get("model") == model
                and saved.get("repeats") == args.repeats
                and saved.get("prompt_version") == PROMPT_VERSION
            ):
                per_case.update(saved.get("per_case", {}))
                print(f"[resume] {len(per_case)} cases restored from checkpoint")
        except Exception:  # noqa: BLE001 — corrupt checkpoint = start fresh
            pass

    for case in cases:
        if case.key in per_case:
            continue
        variants: list[dict[str, Any]] = []
        for variant in range(1, args.repeats + 1):
            try:
                text, usage = _author_draft(client, model, case, variant)
            except Exception as exc:  # noqa: BLE001 — live transport errors are data, not crashes
                variants.append({"variant": variant, "error": f"{type(exc).__name__}: {exc}"[:200]})
                continue
            for k in usage_total:
                usage_total[k] += int(usage.get(k, 0) if k != "calls" else 1)
            scored = run_case(None, _AuthoredCase(case, text))
            # Authoring-validity gate: an empty/one-char authored draft is the
            # model's REFUSAL to author, not a live draft. Counting it as a
            # (misattributed) rejection would credit the verifier for the
            # author's failure — the gate removes it from the live sample
            # instead. Real served drafts are never empty (C2 guarantees
            # that). Round 5: an alnum-bearing check — a 2-char punctuation
            # fragment ({" ) is still a truncated refusal, not a draft.
            valid = any(c.isalnum() for c in text)
            variants.append(
                {
                    "variant": variant,
                    "text": text,
                    "valid": valid,
                    "rejected": bool(scored["rejected"] and valid),
                    "caught": bool(scored["caught"] and valid),
                    "misattributed": bool(scored["misattributed"] and valid),
                    "fired_targeted": scored["fired_targeted"],
                    "issues": scored["issues"]
                    if valid
                    else ["authoring-invalid: empty/one-char draft (model refusal to author)"],
                }
            )
        ok = [v for v in variants if "error" not in v and v.get("valid", True)]
        invalid_n = sum(1 for v in variants if "error" not in v and not v.get("valid", True))
        verdicts = {v["rejected"] for v in ok}
        per_case[case.key] = {
            "label": case.label,
            "categories": list(case.categories),
            "checks": list(case.checks),
            "variants": variants,
            "errors": len(variants) - len(ok) - invalid_n,
            "invalid": invalid_n,
            "stable": len(verdicts) <= 1 and len(ok) >= 2,
            "caught_any": ok and case.label == "should_reject" and any(v["caught"] for v in ok),
            "false_positive": ok and case.label == "should_pass" and all(v["rejected"] for v in ok),
            "misattributed_any": any(v["misattributed"] for v in ok),
        }
        if not ok:
            flag = "N/A"
        elif per_case[case.key]["false_positive"]:
            flag = "FP"
        elif per_case[case.key]["caught_any"]:
            flag = "caught"
        elif case.label == "should_reject":
            flag = "MISS"
        else:
            flag = "-"
        print(f"  {case.key:<28} {flag:<6} variants={len(ok)}/{args.repeats}"
              f"{' UNSTABLE' if not per_case[case.key]['stable'] and len(ok) >= 2 else ''}", flush=True)
        # Checkpoint after every case so a crash/timeout never re-spends tokens.
        PARTIAL.write_text(
            json.dumps(
                {"model": model, "repeats": args.repeats, "prompt_version": PROMPT_VERSION, "per_case": per_case},
                indent=2,
            )
        )

    # ── metrics: same _pr machinery as offline, over variant-level rows ────
    rows: list[dict[str, Any]] = []
    for case in cases:
        for v in per_case[case.key]["variants"]:
            if "error" in v or not v.get("valid", True):
                continue
            rows.append(
                {
                    "key": case.key,
                    "label": case.label,
                    "categories": list(case.categories),
                    "checks": list(case.checks),
                    "rejected": v["rejected"],
                    "caught": v["caught"],
                    "misattributed": v["misattributed"],
                    "fired_targeted": v["fired_targeted"],
                    "false_positive_checks": [] if case.label == "should_reject" else [],
                }
            )
    overall = _pr(rows)
    per_check = {c: _pr(rows, c) for c in CHECKS}

    rejects = [c for c in cases if c.label == "should_reject"]
    passes = [c for c in cases if c.label == "should_pass"]
    cat_rej = sum(1 for c in rejects if per_case[c.key]["caught_any"])
    cat_agree = cat_rej + sum(1 for c in passes if not per_case[c.key]["false_positive"])
    cat_total = len(rejects) + len(passes)
    unstable = sorted(k for k, v in per_case.items() if not v["stable"])

    misattr = []
    for k, vv in per_case.items():
        if vv["misattributed_any"]:
            misattr.append(
                {"key": k, "issues": [v["issues"] for v in vv["variants"] if "error" not in v]}
            )

    artifact = {
        "battery": "verifier red-team — live-LLM stratum",
        "model": model,
        "base_url_host": base_url.split("//")[-1].split("/")[0],
        "prompt_version": PROMPT_VERSION,
        "repeats": args.repeats,
        "cases": len(cases),
        "excluded_cases": excluded_n,
        "authored_drafts": len(rows),
        "authoring_errors": sum(v["errors"] for v in per_case.values()),
        "invalid_drafts": sum(v["invalid"] for v in per_case.values()),
        "usage_totals": usage_total,
        "elapsed_s": round(time.time() - t0, 1),
        "overall": overall,
        "overall_wilson95": {
            "recall": _wilson(overall["true_positives"], overall["should_reject"]),
            "precision": _wilson(overall["true_positives"], overall["true_positives"] + overall["false_positives"]),
        },
        "per_check": per_check,
        "category_agreement": {"agree": cat_agree, "total": cat_total,
                               "rate": round(cat_agree / cat_total, 4) if cat_total else 1.0},
        "unstable_cases": unstable,
        "misattributed": misattr,
        "gates": {
            "recall_floor": RECALL_FLOOR,
            "precision_floor": PRECISION_FLOOR,
            "agreement_floor": AGREEMENT_FLOOR,
        },
        "per_case": per_case,
    }
    if args.out:
        # Third-model/partial batches: write ONLY the named artifact. The
        # canonical results/verifier_redteam_live.json must keep the pinned
        # space-bunny run — a llama batch overwriting it once invalidated the
        # artifact-consistency checker (2026-09-27).
        out = ROOT / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(artifact, indent=2))
    else:
        out = RESULTS.with_name(RESULTS.stem + f"_{_RUN_TAG}.json")
        out.write_text(json.dumps(artifact, indent=2))
        RESULTS.write_text(json.dumps(artifact, indent=2))
    if PARTIAL.exists():
        PARTIAL.unlink()  # run completed — checkpoint no longer needed

    print("\n" + "=" * 76)
    print(f"LIVE STRATUM — {model} @ {artifact['base_url_host']}")
    print("=" * 76)
    o, pc = overall, per_check
    o_r_ci = _wilson(o["true_positives"], o["should_reject"])
    o_p_ci = _wilson(o["true_positives"], o["true_positives"] + o["false_positives"])
    print(
        f"  drafts={len(rows)} authoring_errors={artifact['authoring_errors']} "
        f"invalid={artifact['invalid_drafts']} (excluded_categories={sorted(EXCLUDED_CATEGORIES)})"
    )
    print(f"  overall: P={o['precision']:.3f} (95% CI {o_p_ci[0]:.3f}-{o_p_ci[1]:.3f}) "
          f"R={o['recall']:.3f} (95% CI {o_r_ci[0]:.3f}-{o_r_ci[1]:.3f}) "
          f"(caught {o['true_positives']}/{o['should_reject']}, FP {o['false_positives']}/{o['should_pass']})")
    for c in CHECKS:
        m = pc[c]
        if m["should_reject"] or m["should_pass"]:
            print(
                f"  {c:<12} P={m['precision']:.3f} R={m['recall']:.3f} "
                f"(reject {m['true_positives']}/{m['should_reject']}, "
                f"pass {m['should_pass'] - m['false_positives']}/{m['should_pass']})"
            )
    print(f"  category agreement: {cat_agree}/{cat_total} = {artifact['category_agreement']['rate']}")
    print(f"  unstable cases: {len(unstable)}{(' -> ' + ', '.join(unstable[:8])) if unstable else ''}")
    print(f"  misattributed rejections: {len(misattr)}")
    gates_pass = (
        o["recall"] >= RECALL_FLOOR
        and o["precision"] >= PRECISION_FLOOR
        and artifact["category_agreement"]["rate"] >= AGREEMENT_FLOOR
        and artifact["authoring_errors"] == 0
    )
    print(f"  gates: {'PASS' if gates_pass else 'FAIL'} "
          f"(R>={RECALL_FLOOR}, P>={PRECISION_FLOOR}, agree>={AGREEMENT_FLOOR}, no errors)")
    print(f"artifact: {out}")
    if args.strict:
        return 0 if gates_pass else 2
    return 0


class _AuthoredCase:
    def __init__(self, case: Any, text: str) -> None:
        self.key = case.key
        self.label = case.label
        self.categories = case.categories
        self.checks = case.checks
        self.text = text
        self.ctx = case.ctx


if __name__ == "__main__":
    raise SystemExit(main())
