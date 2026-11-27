"""E20 — The disclosure frontier: bounded-noise (DP-style) release of a
security profile.

Pre-analysis registered in docs/paper/belief_tomography/PREREGISTRATION_E18E19E20.md
BEFORE any noise draw. Frozen E4 profiles only (graded foil, seed 31337 — the
same object E14 analyzed). The Laplace mechanism is standard machinery; the
new object is the disclosure frontier of a behavioral security certificate,
resolving E14's registered open question ("we do not claim an optimal
disclosure mechanism").

Operationalization note (MC-noise tolerance): the registration's dominance
test compares the noised release's ranking utility against the full release's
"ranking quality minus noise tolerance"; the tolerance is operationalized as
twice the Monte-Carlo standard error (~0.02 at N=2000), recorded here before
the run.

Offline; no API lane; estimator untouched.
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from gauntlet.tomograph import wilson  # noqa: E402

FAMS = ("authority_forgery", "state_deception", "goal_subversion",
        "epistemic_echo", "exfiltration_lure")
EPS_GRID = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
N_MC = 2000
SEED = 90210
TAU_TOL = 0.02          # MC-noise tolerance for the dominance test (fixed above)
FOIL, SEED4 = "HardenedDummy", 31337


def laplace(rng: random.Random, scale: float) -> float:
    u = rng.uniform(-0.5, 0.5)
    return -scale * (1 if u >= 0 else -1) * math.log(1 - 2 * abs(u))


def kendall_tau_b(x: list[float], y: list[float]) -> float:
    """Kendall tau-b with tie correction for n=5; 0.0 if undefined.
    Joint ties (pairs tied in BOTH x and y) are excluded from the numerator
    AND counted in both denominators — tau_b(x, x) must equal 1.0."""
    n = len(x)
    conc = disc = 0
    ties_x = ties_y = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = (x[i] > x[j]) - (x[i] < x[j])
            dy = (y[i] > y[j]) - (y[i] < y[j])
            if dx == 0 and dy == 0:
                ties_x += 1
                ties_y += 1
                continue
            if dx == 0:
                ties_x += 1
                continue
            if dy == 0:
                ties_y += 1
                continue
            conc += dx == dy
            disc += dx != dy
    n0 = n * (n - 1) / 2
    denom = math.sqrt(max(n0 - ties_x, 1e-9) * max(n0 - ties_y, 1e-9))
    if denom <= 1e-9:
        return 0.0
    return (conc - disc) / denom


def main() -> None:
    d4 = json.loads((HERE / "e4_separation.json").read_text())
    runs = d4["targets"][FOIL]
    r = next(x for x in runs if x["seed"] == SEED4)
    true_b = {f: b for f, b in zip(FAMS, r["betas"])}
    mean_true = sum(true_b.values()) / len(FAMS)
    fstar_true = max(FAMS, key=lambda f: (true_b[f], -FAMS.index(f)))
    # oracle self-check: tau_b of an identity ranking must be exactly 1.0
    _self = kendall_tau_b([true_b[f] for f in FAMS], [true_b[f] for f in FAMS])
    assert abs(_self - 1.0) < 1e-9, f"tau_b identity check failed: {_self}"

    rng = random.Random(SEED)
    out = {"foil": FOIL, "seed": SEED4, "eps_grid": list(EPS_GRID),
           "n_mc": N_MC, "mc_seed": SEED, "tau_tolerance": TAU_TOL,
           "true_profile": true_b, "curve": {}, "corners": {}, "verdict": {}}

    def mc_release(release_fn, label):
        """release_fn(rng) -> list of 5 released rates. Returns attacker
        advantage and defender ranking utility under the TRUE profile.
        Attacker tie-break (deviation logged 2026-11-20): uniform at random
        among tied maxima — the indifferent attacker."""
        adv = 0.0
        taus = []
        top1 = 0
        for _ in range(N_MC):
            rel = release_fn(rng)
            top = max(rel)
            tied = [f for f, v in zip(FAMS, rel) if v == top]
            f = rng.choice(tied)
            adv += true_b[f]
            taus.append(kendall_tau_b(rel, [true_b[x] for x in FAMS]))
            top1 += f == fstar_true
        return {"attacker_advantage": round(adv / N_MC - mean_true, 4),
                "kendall_tau": round(sum(taus) / N_MC, 4),
                "top1_recovery": round(top1 / N_MC, 4),
                "adv_se": round(1.96 * math.sqrt(
                    sum((true_b[f] - mean_true) ** 2 for f in FAMS) / N_MC), 4)}

    # corners
    out["corners"]["full_release"] = mc_release(
        lambda rng: [true_b[f] for f in FAMS], "full")
    out["corners"]["scalar_Umax"] = {
        "attacker_advantage": 0.0,
        "kendall_tau": 0.0,
        "top1_recovery": round(1 / len(FAMS), 4),
        "note": "no ranking released (E14: attacker reverts to uniform)"}

    # noised releases
    for eps in EPS_GRID:
        scale = 1.0 / eps

        def rel(rng, scale=scale):
            return [min(1.0, max(0.0, true_b[f] + laplace(rng, scale)))
                    for f in FAMS]

        out["curve"][str(eps)] = mc_release(rel, f"eps={eps}")

    # registered dominance tests
    full = out["corners"]["full_release"]
    scalar = out["corners"]["scalar_Umax"]
    dom_scalar = [e for e in EPS_GRID
                  if out["curve"][str(e)]["attacker_advantage"] <= scalar["attacker_advantage"] + 1e-9
                  and out["curve"][str(e)]["kendall_tau"] > 0]
    dom_full = [e for e in EPS_GRID
                if out["curve"][str(e)]["attacker_advantage"] < full["attacker_advantage"] - 1e-9
                and out["curve"][str(e)]["kendall_tau"] >= full["kendall_tau"] - TAU_TOL]
    mono_adv = all(
        out["curve"][str(EPS_GRID[i])]["attacker_advantage"]
        <= out["curve"][str(EPS_GRID[i + 1])]["attacker_advantage"] + 1e-9
        for i in range(len(EPS_GRID) - 1))
    mono_tau = all(
        out["curve"][str(EPS_GRID[i])]["kendall_tau"]
        <= out["curve"][str(EPS_GRID[i + 1])]["kendall_tau"] + 1e-9
        for i in range(len(EPS_GRID) - 1))
    v = out["verdict"]
    v["advantage_monotone_in_eps"] = bool(mono_adv)
    v["utility_monotone_in_eps"] = bool(mono_tau)
    v["dominates_scalar"] = dom_scalar
    v["dominates_full"] = dom_full
    v["corners_on_frontier_no_free_lunch"] = bool(not dom_scalar)
    v["E20_outcome"] = (
        "interior dominance found" if (dom_scalar and dom_full) else
        "corners on frontier: no free lunch — the scalar Umax is optimal against "
        "the argmax attacker, and the noised family traces the trade-off curve "
        "between the corners" if not dom_scalar else
        "partial dominance — see the endpoint lists")
    (HERE / "e20_disclosure_frontier.json").write_text(json.dumps(out, indent=2))

    lines = [
        "# E20 — The disclosure frontier (bounded-noise release of a security profile)",
        "",
        "Pre-analysis registered: `docs/paper/belief_tomography/PREREGISTRATION_E18E19E20.md`. "
        f"Frozen E4 profile ({FOIL}, seed {SEED4}); Laplace(1/eps) per cell, "
        f"MC N={N_MC}, seed {SEED}; attacker = argmax of the released profile; "
        "utility = Kendall tau-b vs the true ranking (0 if undefined). The DP "
        "guarantee is over the PROFILE space (L1 sensitivity 1 per neighboring "
        "profile), not over the underlying probe outcomes — disclosed boundary.",
        "",
        "## Corners",
        "",
        "| release | attacker advantage | Kendall tau | top-1 recovery |",
        "|---|---|---|---|",
        f"| full vector (eps=inf) | {full['attacker_advantage']:.3f} | "
        f"{full['kendall_tau']:.3f} | {full['top1_recovery']:.3f} |",
        f"| scalar Umax | {scalar['attacker_advantage']:.3f} | "
        f"{scalar['kendall_tau']:.3f} | {scalar['top1_recovery']:.3f} |",
        "",
        "## Noised releases (the trade-off curve)",
        "",
        "| eps | attacker advantage | Kendall tau | top-1 recovery |",
        "|---|---|---|---|",
    ]
    for eps in EPS_GRID:
        c = out["curve"][str(eps)]
        lines.append(f"| {eps} | {c['attacker_advantage']:.4f} | "
                     f"{c['kendall_tau']:.3f} | {c['top1_recovery']:.3f} |")
    v = out["verdict"]
    lines += [
        "", "## Verdict", "",
        f"- Advantage monotone decreasing in noise: **{v['advantage_monotone_in_eps']}**",
        f"- Utility monotone increasing in eps: **{v['utility_monotone_in_eps']}**",
        f"- Interior points dominating the scalar: **{v['dominates_scalar'] or 'none'}**",
        f"- Interior points dominating the full release: **{v['dominates_full'] or 'none'}**",
        "",
        f"**E20 outcome: {v['E20_outcome']}**",
        "",
    ]
    (HERE / "E20_DISCLOSURE_FRONTIER.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
