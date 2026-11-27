"""E15 — Counterintelligence tomogram: defender-side deception release (T15).

Pre-analysis registered in docs/paper/belief_tomography/PREREGISTRATION_E15E16E17.md
BEFORE any deception-release quantity was computed. Uses only the frozen E9
profiles (e9_forgery.json): display profile = what the defender publishes,
held profile = true per-family behavior. The attacker simulation adds decision
analysis on top; no new behavioral measurement, no API calls.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
FAMS = ("authority_forgery", "state_deception", "goal_subversion",
        "epistemic_echo", "exfiltration_lure")

BUDGET = 120
N_MC = 2000
SEED = 31337
VERIF_SHARES = (0.2, 0.5)
PHO_GRID = (0.0, 0.5, 1.0)


def alloc_uniform(b: int) -> dict[str, int]:
    base, rem = divmod(b, len(FAMS))
    return {f: base + (1 if i < rem else 0) for i, f in enumerate(FAMS)}


def alloc_argmax(b: int, profile: dict[str, float]) -> dict[str, int]:
    f = max(FAMS, key=lambda x: (profile[x], -FAMS.index(x)))
    return {x: (b if x == f else 0) for x in FAMS}


def alloc_proportional(b: int, profile: dict[str, float]) -> dict[str, int]:
    tot = sum(profile[x] for x in FAMS)
    if tot <= 0:
        return alloc_uniform(b)
    raw = {x: b * profile[x] / tot for x in FAMS}
    out = {x: int(raw[x]) for x in FAMS}
    rem = b - sum(out.values())
    order = sorted(FAMS, key=lambda x: raw[x] - out[x], reverse=True)
    for i in range(rem):
        out[order[i % len(order)]] += 1
    return out


def success(a: dict[str, int], true_p: dict[str, float], rng) -> tuple[float, float]:
    """Monte-Carlo one campaign: returns (successes, is_success_float)."""
    hits = 0
    for f in FAMS:
        for _ in range(a[f]):
            if rng.random() < true_p[f]:
                hits += 1
    return hits, float(hits > 0)


def main() -> None:
    import random
    data = json.loads((HERE / "e9_forgery.json").read_text())
    rng = random.Random(SEED)
    out = {"budget": BUDGET, "n_mc": N_MC, "seed": SEED,
           "verif_shares": list(VERIF_SHARES), "pho_grid": list(PHO_GRID),
           "targets": {}, "verdict": {}}

    for foil, runs in data["targets"].items():
        out["targets"][foil] = {}
        for seed, prof in runs.items():
            display = {f: prof["public"][f] for f in FAMS}
            true_p = {f: prof["held"][f] for f in FAMS}
            res: dict[str, dict] = {}

            def sim(policy_alloc, n_runs=N_MC):
                """Expected success is exact for a deterministic allocation;
                the Monte Carlo run supplies the registered per-campaign
                hit-rate (P(at least one success)) with its standard error."""
                exact = sum(policy_alloc[f] * true_p[f] for f in FAMS)
                hit_rate = 0.0
                for _ in range(n_runs):
                    _, hit = success(policy_alloc, true_p, rng)
                    hit_rate += hit
                hr = hit_rate / n_runs
                se = math.sqrt(hr * (1 - hr) / n_runs) if n_runs else 0.0
                return exact, hr, se

            res["uniform"] = dict(zip(("succ", "hit_rate", "hit_rate_se"), sim(alloc_uniform(BUDGET))))
            res["honest_argmax"] = dict(zip(("succ", "hit_rate", "hit_rate_se"), sim(alloc_argmax(BUDGET, true_p))))
            res["decoy_argmax"] = dict(zip(("succ", "hit_rate", "hit_rate_se"), sim(alloc_argmax(BUDGET, display))))
            res["decoy_proportional"] = dict(zip(("succ", "hit_rate", "hit_rate_se"),
                                                 sim(alloc_proportional(BUDGET, display))))
            for v in VERIF_SHARES:
                # verification share of budget is spent re-running the public
                # suite (measurement episodes, no success); the remainder is
                # allocated by the published ranking.
                b_rest = int(round(BUDGET * (1 - v)))
                a = alloc_argmax(b_rest, display)
                res[f"public_verifier_v{v}"] = dict(
                    zip(("succ", "hit_rate", "hit_rate_se"), sim(a)), verif_share=v)
            for pho in PHO_GRID:
                decoy = res["decoy_argmax"]["succ"]
                uni = res["uniform"]["succ"]
                res[f"heldout_verifier_p{pho}"] = {
                    "succ": pho * uni + (1 - pho) * decoy,
                    "trust_collapse_flag": pho > 0}

            d_arg = res["honest_argmax"]["succ"] - res["decoy_argmax"]["succ"]
            d_prop = res["honest_argmax"]["succ"] - res["decoy_proportional"]["succ"]
            out["targets"][foil][seed] = {
                "display": display, "true": true_p, "policies": res,
                "deception_gain_argmax": round(d_arg, 4),
                "deception_gain_proportional": round(d_prop, 4),
                "stability": all(
                    abs(res[f"public_verifier_v{v}"]["succ"] - res["decoy_argmax"]["succ"]) < 1e-9
                    for v in VERIF_SHARES),
                "monotone_in_pho": all(
                    res[f"heldout_verifier_p{PHO_GRID[i+1]}"]["succ"]
                    >= res[f"heldout_verifier_p{PHO_GRID[i]}"]["succ"] - 1e-9
                    for i in range(len(PHO_GRID) - 1)),
            }

    sh = out["targets"]["ShapingFoil"]
    ho = out["targets"]["HonestFoil"]
    v = out["verdict"]
    v["shaping_gain_positive"] = all(r["deception_gain_argmax"] > 0 for r in sh.values())
    v["honest_gain_zero"] = all(r["deception_gain_argmax"] == 0 for r in ho.values())
    v["stability_holds"] = all(r["stability"] for r in sh.values())
    v["monotone_in_pho"] = all(r["monotone_in_pho"] for r in sh.values())
    v["E15_supported"] = bool(v["shaping_gain_positive"] and v["honest_gain_zero"]
                              and v["stability_holds"] and v["monotone_in_pho"])
    (HERE / "e15_deception_release.json").write_text(json.dumps(out, indent=2))

    lines = [
        "# E15 — Counterintelligence tomogram: deception release (T15)",
        "",
        "Pre-analysis registered: `docs/paper/belief_tomography/PREREGISTRATION_E15E16E17.md`. "
        f"Attacker budget B={BUDGET}, Monte Carlo N={N_MC}, seed {SEED}. True behavior = E9 held "
        "profile; published = E9 display profile. Decision analysis on frozen data, not a "
        "behavioral measurement.",
        "",
    ]
    for foil in out["targets"]:
        for seed, r in out["targets"][foil].items():
            p = r["policies"]
            lines.append(f"## {foil} (seed {seed})")
            lines.append("")
            lines.append("| policy | expected attacker success |")
            lines.append("|---|---|")
            for name in ("uniform", "honest_argmax", "decoy_argmax", "decoy_proportional",
                         "public_verifier_v0.2", "public_verifier_v0.5",
                         "heldout_verifier_p0.0", "heldout_verifier_p0.5",
                         "heldout_verifier_p1.0"):
                lines.append(f"| {name} | {p[name]['succ']:.4f} |")
            lines.append("")
            lines.append(f"- deception gain (argmax): **{r['deception_gain_argmax']:.4f}** "
                         f"(honest {p['honest_argmax']['succ']:.3f} → decoy {p['decoy_argmax']['succ']:.3f})")
            lines.append(f"- deception gain (proportional): {r['deception_gain_proportional']:.4f}")
            lines.append(f"- stable under public verification: {r['stability']}; "
                         f"monotone collapse in p_ho: {r['monotone_in_pho']}")
            lines.append("")
    lines += [
        "## Verdict", "",
        f"- ShapingFoil decoy misdirects (gain > 0): **{v['shaping_gain_positive']}**",
        f"- HonestFoil control gain zero: **{v['honest_gain_zero']}**",
        f"- Verification stability (public suite): **{v['stability_holds']}**",
        f"- Monotone trust collapse in p_ho: **{v['monotone_in_pho']}**",
        "",
        f"**E15 supported: {v['E15_supported']}.**",
        "",
    ]
    (HERE / "E15_DECEPTION_RELEASE.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
