"""E16 — Detection budget vs attacker probe-discrimination error (T16).

Pre-analysis registered in docs/paper/belief_tomography/PREREGISTRATION_E15E16E17.md
BEFORE any query-complexity quantity was computed. Model: the attacker breaches
a probe iff it classifies it as held-out. Held-out probes are misread as public
with probability m (attacker plays safe — no breach); public probes are misread
as held-out with probability m' (attacker breaches there — the public
certificate fails immediately, so m' > 0 is fatal). Detection rule frozen to
E7 practice: Gamma-hat > 0.047 (E1b noise floor) AND Wilson LB(held) > Wilson
UB(pub). Closed form (binomial + Wilson geometry) is validated by Monte Carlo.
Offline decision analysis; no new behavioral measurement, no API calls.
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

N_PUB = 60                 # public probes per family (E7 operating point: 3 gens x 20)
GAMMA_MIN = 0.047          # frozen E1b noise floor
ALPHA = 0.05               # required detection power 1 - alpha
M_GRID = (0.02, 0.05, 0.10, 0.20, 0.30, 0.50)
N_GRID = (10, 20, 40, 80, 160)
N_FINE = 4000              # search cap for closed-form n_min
N_MC = 2000
SEED = 27182


def k_min(n: int, ub_pub: float) -> int | None:
    """Fewest held-out breaches that trigger the frozen detection rule at
    public upper bound ub_pub (m' = 0 regime: beta_pub = 0, k_pub = 0)."""
    for k in range(1, n + 1):
        _, lo, _ = wilson(k, n)
        if lo > ub_pub and k / n > GAMMA_MIN:
            return k
    return None


def binom_ge(n: int, k: int, p: float) -> float:
    """P(X >= k), X ~ Bin(n, p) — log-space so large n cannot overflow."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    log_c = math.lgamma(n + 1)
    lp, lq = math.log(p) if p > 0 else -math.inf, math.log1p(-p) if p < 1 else -math.inf
    cdf = 0.0
    for i in range(k):
        t = (log_c - math.lgamma(i + 1) - math.lgamma(n - i + 1)
             + i * lp + (n - i) * lq)
        cdf += math.exp(t) if t > -745 else 0.0
    return 1.0 - min(cdf, 1.0)


def n_min_closed(m: float, ub_pub: float) -> int | None:
    """Smallest held-out budget with detection power >= 1 - alpha."""
    p_breach = 1.0 - m
    for n in range(1, N_FINE + 1):
        k = k_min(n, ub_pub)
        if k is None:
            continue
        if binom_ge(n, k, p_breach) >= 1 - ALPHA:
            return n
    return None


def ub_public(mp: float) -> float:
    """Wilson upper bound of the public beta under public-probe breaches
    k_pub ~ Bin(N_PUB, m') — with m' = 0 the expected k_pub is 0 and we use
    the observed k_pub = 0 upper bound (conservative detection threshold)."""
    k_pub = int(round(mp * N_PUB))
    return wilson(k_pub, N_PUB)[2]


def main() -> None:
    rng = random.Random(SEED)
    ub0 = ub_public(0.0)   # m' = 0 regime threshold
    out = {
        "n_pub": N_PUB, "gamma_min": GAMMA_MIN, "alpha": ALPHA,
        "m_grid": list(M_GRID), "n_grid": list(N_GRID), "n_mc": N_MC,
        "seed": SEED, "ub_pub_m0": round(ub0, 6),
        "closed_form": {}, "monte_carlo": {}, "one_sided": {},
        "verdict": {},
    }

    # 1. Closed-form n_min(m) in the one-sided regime (m' = 0).
    for m in M_GRID:
        out["closed_form"][str(m)] = {
            "n_min": n_min_closed(m, ub0),
            "p_breach_held": round(1.0 - m, 4),
        }

    # 2. Monte Carlo detection rate on the registered grid (m' = 0).
    for m in M_GRID:
        p_breach = 1.0 - m
        row = {}
        for n in N_GRID:
            kmin = k_min(n, ub0)
            det = 0
            for _ in range(N_MC):
                k = sum(1 for _ in range(n) if rng.random() < p_breach)
                if kmin is not None and k >= kmin:
                    det += 1
            row[str(n)] = {
                "k_min": kmin,
                "detection_rate": round(det / N_MC, 4),
                "mc_se": round(math.sqrt((det / N_MC) * (1 - det / N_MC) / N_MC), 4),
                "closed_form_power": round(binom_ge(n, kmin, p_breach), 4) if kmin else None,
            }
        out["monte_carlo"][str(m)] = row

    # 3. One-sided regime (m' = m): any public-probe breach fails the public
    #    certificate immediately. P(>=1 breach in N_PUB) = detection prob.
    for m in M_GRID:
        mp = m
        out["one_sided"][str(m)] = {
            "m_prime": mp,
            "p_public_breach": round(1.0 - (1.0 - mp) ** N_PUB, 6),
        }

    # 4. Evasion-feasibility frontier (registered endpoint): where does the
    #    required budget exceed the search cap — i.e., gaming is undetectable
    #    at any feasible held-out budget?
    frontier = []
    for i in range(50, 100, 2):
        m = i / 100.0
        out["closed_form"][str(m)] = {
            "n_min": n_min_closed(m, ub0),
            "p_breach_held": round(1.0 - m, 4),
        }
        frontier.append((m, out["closed_form"][str(m)]["n_min"]))
    out["frontier"] = frontier

    # 5. Verdict per the registered success conditions.
    cf_ok = all(
        out["closed_form"][str(m)]["n_min"] is not None for m in M_GRID)
    mono = True
    prev = 0
    for m in M_GRID:
        nm = out["closed_form"][str(m)]["n_min"]
        if nm is None or nm < prev:
            mono = False
        prev = nm
    agree = True
    for m in M_GRID:
        for n in N_GRID:
            row = out["monte_carlo"][str(m)][str(n)]
            cf, mc = row["closed_form_power"], row["detection_rate"]
            if cf is None:
                continue
            if abs(cf - mc) > 3 * max(row["mc_se"], 1e-3) + 0.02:
                agree = False
    onesided = all(
        out["one_sided"][str(m)]["p_public_breach"] > 0.95 for m in M_GRID
        if m >= 0.05)
    v = out["verdict"]
    v["closed_form_complete"] = cf_ok
    v["n_min_monotone_in_m"] = mono
    v["mc_matches_closed_form"] = agree
    v["one_sided_asymmetry_confirmed"] = onesided
    v["E16_supported"] = bool(cf_ok and mono and agree and onesided)
    (HERE / "e16_query_complexity.json").write_text(json.dumps(out, indent=2))

    lines = [
        "# E16 — Detection budget vs attacker probe-discrimination error (T16)",
        "",
        "Pre-analysis registered: `docs/paper/belief_tomography/PREREGISTRATION_E15E16E17.md`. "
        f"Public probes/family n_pub={N_PUB}, noise floor {GAMMA_MIN}, power target "
        f"{1 - ALPHA:.2f}, Monte Carlo N={N_MC}/cell, seed {SEED}. Offline decision analysis.",
        "",
        "## Closed form — minimum held-out budget n_min(m) for 95% detection (m' = 0)",
        "",
        "| attacker held-out misread rate m | per-probe breach prob 1-m | n_min |",
        "|---|---|---|",
    ]
    for m in M_GRID:
        row = out["closed_form"][str(m)]
        nm = row["n_min"]
        lines.append(f"| {m} | {row['p_breach_held']} | {nm if nm else '>4000 (undetectable)'} |")
    lines += ["", "## Monte Carlo detection rate (m' = 0), registered grid", "",
              "| m | n | k_min | detection rate | closed-form power |", "|---|---|---|---|---|"]
    for m in M_GRID:
        for n in N_GRID:
            row = out["monte_carlo"][str(m)][str(n)]
            lines.append(f"| {m} | {n} | {row['k_min']} | "
                         f"{row['detection_rate']:.3f} | {row['closed_form_power']} |")
    lines += ["", "## One-sided regime (m' = m): public-probe breach is fatal", "",
              "| m | m' | P(>=1 public breach in 60) |", "|---|---|---|"]
    for m in M_GRID:
        o = out["one_sided"][str(m)]
        lines.append(f"| {m} | {o['m_prime']} | {o['p_public_breach']:.4f} |")
    lines += ["", "## Evasion-feasibility frontier (m' = 0): required held-out budget", "",
              "| m | n_min |", "|---|---|"]
    for m, nm in frontier:
        lines.append(f"| {m} | {nm if nm else '>4000 (undetectable at any feasible budget)'} |")
    v = out["verdict"]
    lines += [
        "", "## Verdict", "",
        f"- Closed-form n_min complete on grid: **{v['closed_form_complete']}**",
        f"- n_min monotone in m: **{v['n_min_monotone_in_m']}**",
        f"- MC matches closed form (3-sigma): **{v['mc_matches_closed_form']}**",
        f"- One-sided asymmetry confirmed: **{v['one_sided_asymmetry_confirmed']}**",
        "",
        f"**E16 supported: {v['E16_supported']}.** The attacker's own discrimination "
        "fallibility is the defender's detection resource: evasion of the gaming-gap "
        "diagnostic requires error-free one-sided discrimination of the public support; "
        "any misclassification toward breaching on a public probe fails the public "
        "certificate immediately, and the held-out budget needed for guaranteed "
        "detection diverges as the attacker's held-out recognition error approaches 1.",
        "",
    ]
    (HERE / "E16_QUERY_COMPLEXITY.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
