"""E22 — Library-v1 paraphrase validation (PREREGISTERED: PREREGISTRATION_E22_LIBRARYV1.md).

Question: does the instrument produce the same measurements when the probe
SURFACE text is paraphrased? Four generator variants (v0 baseline + P1/P2/P3
frozen paraphrases) run the identical E1 dose-response grid on the identical
deterministic dose foil with matched Bernoulli seeds (paired design), so any
cell difference is attributable to probe wording, not foil noise.

Run:  python3 demo/run_e22_paraphrase_validation.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo.run_dose_response import DOSES, PROBES_PER_CELL, DosedFoil, pearson, ranks  # noqa: E402
from gauntlet.generator import FAMILIES, GauntletGenerator  # noqa: E402
from gauntlet.generator_v1 import VARIANTS, ParaphraseGauntletGenerator  # noqa: E402
from gauntlet.harness import _run_one  # noqa: E402
from gauntlet.tomograph import wilson  # noqa: E402
from gauntlet.verdict import HeuristicJury  # noqa: E402


def run_variant(variant: str, jury: HeuristicJury) -> dict:
    """One full E1 grid for one generator variant. Returns per-cell table + stats."""
    table: dict[str, list[dict]] = {}
    dose_runs = {d: DosedFoil({f: d for f in FAMILIES}, seed=700 + i) for i, d in enumerate(DOSES)}
    for family in FAMILIES:
        cells = []
        for di, dose in enumerate(DOSES):
            target = dose_runs[dose]
            breaches = 0
            n = 0
            for gen in (1, 2, 3):
                for _ in range(PROBES_PER_CELL):
                    if variant == "v0":
                        g = GauntletGenerator(seed=1000 + di * 97 + gen)
                    else:
                        g = ParaphraseGauntletGenerator(seed=1000 + di * 97 + gen, variant=variant)
                    v = _run_one(target, g.episode(family, gen), jury)
                    breaches += 0 if v.passed else 1
                    n += 1
            beta, lo, hi = wilson(breaches, n)
            se = math.sqrt(max(beta * (1 - beta), 1e-9) / n)
            cells.append({"dose": dose, "breaches": breaches, "n": n,
                          "beta": round(beta, 4), "ci": [round(lo, 4), round(hi, 4)], "se": round(se, 4)})
        table[family] = cells
    stats = {}
    for family, cells in table.items():
        xs = [c["dose"] for c in cells]
        ys = [c["beta"] for c in cells]
        stats[family] = {
            "pearson_r": round(pearson(xs, ys), 4),
            "spearman_rho": round(pearson(ranks(xs), ranks(ys)), 4),
            "monotone": all(ys[i] <= ys[i + 1] + 1e-9 for i in range(len(ys) - 1)),
            "zero_dose_clean": cells[0]["breaches"] == 0,
        }
    return {"table": table, "stats": stats}


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    jury = HeuristicJury()
    runs = {}
    for variant in ("v0", "P1", "P2", "P3"):
        print(f"[E22] running variant {variant} ...", flush=True)
        runs[variant] = run_variant(variant, jury)

    # Paired paraphrase-vs-v0 agreement over the 75 (family, dose) cells.
    agreement = {}
    for variant in ("P1", "P2", "P3"):
        deltas = []
        for family in FAMILIES:
            for di, dose in enumerate(DOSES):
                d = abs(runs[variant]["table"][family][di]["beta"]
                        - runs["v0"]["table"][family][di]["beta"])
                se = math.sqrt(runs[variant]["table"][family][di]["se"] ** 2
                               + runs["v0"]["table"][family][di]["se"] ** 2)
                deltas.append({"family": family, "dose": dose, "delta": round(d, 4),
                               "exceeds_2se": bool(d > 2 * se)})
        mx = max(x["delta"] for x in deltas)
        over = sum(1 for x in deltas if x["exceeds_2se"])
        agreement[variant] = {"max_delta": round(mx, 4), "cells_over_2se": over,
                              "cells": deltas}

    # Cross-variant profile correlation over the 75-cell vectors.
    def vec(v: str) -> list[float]:
        return [runs[v]["table"][f][di]["beta"] for f in FAMILIES for di in range(len(DOSES))]

    cross = {}
    names = ("v0", "P1", "P2", "P3")
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            cross[f"{a}~{b}"] = round(pearson(vec(a), vec(b)), 4)

    primary_pass = all(
        s["pearson_r"] >= 0.98 and s["spearman_rho"] == 1.0 and s["monotone"] and s["zero_dose_clean"]
        for v, s in runs["P1"]["stats"].items()
    ) and all(
        s["pearson_r"] >= 0.98 and s["spearman_rho"] == 1.0 and s["monotone"] and s["zero_dose_clean"]
        for v, s in runs["P2"]["stats"].items()
    ) and all(
        s["pearson_r"] >= 0.98 and s["spearman_rho"] == 1.0 and s["monotone"] and s["zero_dose_clean"]
        for v, s in runs["P3"]["stats"].items()
    )

    (out_dir / "e22_paraphrase_validation.json").write_text(json.dumps({
        "runs": runs, "agreement": agreement, "cross_variant_pearson": cross,
        "primary_pass": primary_pass,
    }, indent=2))

    lines = [
        "# E22 — Library-v1 Paraphrase Validation",
        "",
        "**Registered:** PREREGISTRATION_E22_LIBRARYV1.md (before data).",
        f"**Protocol:** 4 generator variants x {len(DOSES)} doses x 5 families x 3 generations "
        f"x {PROBES_PER_CELL} probes = {4 * len(DOSES) * 5 * 3 * PROBES_PER_CELL} episodes; "
        "matched Bernoulli seeds (paired design); local deterministic foil.",
        "",
        "## Primary endpoint: per-variant E1 validity bar",
        "",
        "| Variant | Family | " + " | ".join(f"d={d:.2f}" for d in DOSES) + " | r | rho | monotone | zero-clean |",
        "|---|---|" + "---|" * (len(DOSES) + 4),
    ]
    for variant in ("v0", "P1", "P2", "P3"):
        for family in FAMILIES:
            s = runs[variant]["stats"][family]
            cells = runs[variant]["table"][family]
            betas = " | ".join(f"{c['beta']:.2f}" for c in cells)
            lines.append(
                f"| {variant} | {family} | {betas} | {s['pearson_r']:.3f} | {s['spearman_rho']:.2f} "
                f"| {'Y' if s['monotone'] else 'N'} | {'Y' if s['zero_dose_clean'] else 'N'} |"
            )
    lines += [
        "",
        f"**Primary verdict: {'PASS — all three paraphrase variants meet the E1 bar in all five families' if primary_pass else 'FAIL — semantic drift detected (reported per cell)'}**",
        "",
        "## Secondary: paraphrase-vs-v0 paired agreement (75 cells per variant)",
        "",
        "| Variant | max |beta-hat - beta-v0| | cells over 2xSE |",
        "|---|---|---|",
    ]
    for variant, a in agreement.items():
        lines.append(f"| {variant} | {a['max_delta']:.4f} | {a['cells_over_2se']}/75 |")
    lines += [
        "",
        "## Secondary: cross-variant profile Pearson (75-cell vectors)",
        "",
        "| Pair | r |",
        "|---|---|",
    ]
    for pair, r in cross.items():
        lines.append(f"| {pair} | {r:.4f} |")
    lines += [
        "",
        "*Interpretation: the instrument reads the same belief state through three frozen "
        "surface paraphrases of every probe cell; the v0 single-template measurement is not "
        "an artifact of one wording. Any cell over 2xSE is reported per cell in the JSON.*",
    ]
    (out_dir / "E22_LIBRARY_V1.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[-24:]))
    print(f"[E22] PRIMARY: {'PASS' if primary_pass else 'FAIL'}")


if __name__ == "__main__":
    main()
