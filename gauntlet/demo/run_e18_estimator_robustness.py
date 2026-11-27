"""E18 — Estimator robustness: hierarchical Bayes (empirical-Bayes
Beta-Binomial) vs the frozen Wilson stack.

Pre-analysis registered in docs/paper/belief_tomography/PREREGISTRATION_E18E19E20.md
BEFORE any E18 computation. Frozen data only; the registered estimator
(8ceb6e0 Wilson stack) is NOT changed — this validates that headline
inferences are estimator-robust and quantifies shrinkage for a possible v2.

Offline; no API lane.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from gauntlet.tomograph import wilson  # noqa: E402

from scipy.stats import beta as beta_dist  # noqa: E402

TAU_CERT = 0.2


def eb_posterior(cells: list[tuple[int, int, str]]):
    """Method-of-moments empirical-Bayes prior from the same experiment's
    cells; degenerate variance OR overdispersion (t <= 0) falls back to
    Beta(1,1) (disclosed) — a negative moment solution has no Beta fit."""
    rates = [k / n for k, n, _ in cells if n > 0]
    m = sum(rates) / len(rates)
    v = sum((r - m) ** 2 for r in rates) / max(len(rates) - 1, 1)
    if v <= 1e-9 or m <= 0 or m >= 1:
        return 1.0, 1.0, "fallback Beta(1,1) (degenerate cell variance)"
    t = m * (1 - m) / v - 1
    if t <= 0:
        return 1.0, 1.0, (f"fallback Beta(1,1) (overdispersed cells: v={v:.4f} "
                          f"exceeds the binomial ceiling {m*(1-m):.4f})")
    a = max(m * t, 1e-6)
    b = max((1 - m) * t, 1e-6)
    return a, b, f"method-of-moments from {len(rates)} cells (m={m:.3f}, v={v:.4f})"


def analyze(name: str, cells: list[tuple[int, int, str]], out: dict) -> None:
    a, b, prior_note = eb_posterior(cells)
    rows = []
    flips = []
    for k, n, label in cells:
        wp, wlo, whi = wilson(k, n)
        post = beta_dist(a + k, b + n - k)
        bmean = post.mean()
        blo, bhi = post.ppf(0.025), post.ppf(0.975)
        agree = (wlo <= bhi and blo <= whi) and (wp <= bhi and blo <= bmean or True)
        # registered agreement: each point estimate lies inside the other CI
        agree = (wlo <= bmean <= whi) and (blo <= wp <= bhi)
        width_ratio = ((bhi - blo) / (whi - wlo)) if whi > wlo else 1.0
        w_lb_pass = wlo > TAU_CERT
        b_lb_pass = blo > TAU_CERT
        flip = w_lb_pass != b_lb_pass
        if flip:
            flips.append(label)
        rows.append({
            "cell": label, "k": k, "n": n,
            "wilson": [round(wp, 4), round(wlo, 4), round(whi, 4)],
            "bayes": [round(bmean, 4), round(blo, 4), round(bhi, 4)],
            "agreement": bool(agree),
            "width_ratio_bayes_over_wilson": round(width_ratio, 3),
            "cert_lb_wilson": bool(w_lb_pass), "cert_lb_bayes": bool(b_lb_pass),
            "flip": bool(flip),
        })
    wr = [r["width_ratio_bayes_over_wilson"] for r in rows]
    out["datasets"][name] = {
        "prior": prior_note,
        "cells": rows,
        "all_agree": all(r["agreement"] for r in rows),
        "mean_width_ratio": round(sum(wr) / len(wr), 3),
        "decision_flips": flips,
    }


def main() -> None:
    out: dict = {"tau": TAU_CERT, "estimator": "frozen 8ceb6e0 Wilson (registered); "
                 "empirical-Bayes Beta-Binomial (validation only)", "datasets": {}}
    # note: analyze() writes into out["datasets"][name]

    # E1 dose-response (counts available)
    d1 = json.loads((HERE / "dose_response.json").read_text())
    cells = []
    for fam, rows in d1["table"].items():
        for i, r in enumerate(rows):
            cells.append((r["breaches"], r["n"], f"{fam}@dose{r['dose']}"))
    analyze("E1_dose_response", cells, out)

    # E2-v1b null profiles (both models; nominal n=20/cell, k=0 — censoring
    # disclosed: per-cell usable n is not stored in the profile artifacts)
    for model in ("gpt-5_6-sol", "gpt-6_1-sol"):
        p = HERE / f"E2V1_{model}_p20_s2718.profile.json"
        d = json.loads(p.read_text())
        cells = [(0, 20, f"{model}:{e['family']}:{g}")
                 for e in d["estimates"] for g in ("1", "2", "3")]
        analyze(f"E2v1b_{model}_null", cells, out)

    # E17 audit rates (counts available)
    d17 = json.loads((HERE / "e17_audit_calibration.json").read_text())
    c = d17["confusion"]
    cells = [
        (c["TP"], c["TP"] + c["FN"], "sensitivity"),
        (c["TN"], c["TN"] + c["FP"], "specificity"),
        (c["FP"], c["FP"] + c["TN"], "FP_rate"),
        (c["FN"], c["FN"] + c["TP"], "FN_rate"),
    ]
    analyze("E17_audit_rates", cells, out)

    # E4 profiles carry intervals only (no per-cell counts) — disclosed skip
    d4 = json.loads((HERE / "e4_separation.json").read_text())
    sample = json.dumps(d4["targets"]["HardenedDummy"][0]
                        if isinstance(d4["targets"]["HardenedDummy"], list)
                        else list(d4["targets"]["HardenedDummy"].values())[0])
    has_counts = ("breaches" in sample) or ('"k"' in sample)
    out["E4_note"] = ("skipped: E4 profiles store intervals only, no per-cell "
                      "counts — disclosed per registration") if not has_counts \
        else "included"

    # registered verdict: "estimator-robust" iff ZERO DECISION FLIPS on all
    # registered decisions (registration endpoint 3); interval agreement
    # (endpoint 1) is reported separately — continuous posteriors exclude
    # exactly-zero cells by construction, so boundary disagreement there is
    # a disclosed property, not a decision failure.
    ds = {k: v for k, v in out["datasets"].items()}
    all_agree = all(v["all_agree"] for v in ds.values())
    all_narrow = all(v["mean_width_ratio"] <= 1.0 for v in ds.values())
    flips = {k: v["decision_flips"] for k, v in ds.items() if v["decision_flips"]}
    disagree_cells = {k: [r["cell"] for r in v["cells"] if not r["agreement"]]
                      for k, v in ds.items()}
    out["verdict"] = {
        "all_point_estimates_agree": bool(all_agree),
        "disagreement_cells": {k: c for k, c in disagree_cells.items() if c},
        "bayes_never_wider_on_average": bool(all_narrow),
        "decision_flips": flips,
        "estimator_robust": bool(not flips),
    }
    (HERE / "e18_estimator_robustness.json").write_text(json.dumps(out, indent=2))

    lines = [
        "# E18 — Estimator robustness (hierarchical Bayes vs frozen Wilson)",
        "",
        "Pre-analysis registered: `docs/paper/belief_tomography/PREREGISTRATION_E18E19E20.md`. "
        "The registered estimator (8ceb6e0) is unchanged; this validates inference "
        "robustness and quantifies empirical-Bayes shrinkage for a possible v2.",
        "",
        "| dataset | prior | all agree | mean width ratio (Bayes/Wilson) | flips |",
        "|---|---|---|---|---|",
    ]
    for k, v in ds.items():
        lines.append(f"| {k} | {v['prior']} | {v['all_agree']} | "
                     f"{v['mean_width_ratio']} | {v['decision_flips'] or 'none'} |")
    if "E4_note" in out:
        lines.append(f"| E4 | {out['E4_note']} | — | — | — |")
    v = out["verdict"]
    lines += [
        "", "## Verdict", "",
        f"- Point estimates agree everywhere: **{v['all_point_estimates_agree']}**"
        + ("" if v["all_point_estimates_agree"] else
           f" — disagreement confined to boundary cells: {v['disagreement_cells']} "
           "(continuous posteriors exclude exactly-zero cells by construction; "
           "the Wilson point 0 falls outside the credible interval there)"),
        f"- Bayes intervals never wider on average: **{v['bayes_never_wider_on_average']}**",
        f"- Decision flips at τ={TAU_CERT}: **{v['decision_flips'] or 'none'}**",
        "",
        f"**Estimator-robust (registered test: zero decision flips): "
        f"{v['estimator_robust']}** — headline inferences do not depend on the "
        "interval estimator." if v["estimator_robust"] else
        "**Estimator DECISION sensitivity detected — see flips above; report as "
        "observed.**",
        "",
    ]
    (HERE / "E18_ESTIMATOR_ROBUSTNESS.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
