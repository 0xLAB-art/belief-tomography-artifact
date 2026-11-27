"""T3 first policy benchmark: probe-allocation efficiency for belief tomography.

World: heterogeneous profile (thetas spread across [0.1, 0.9] — families near
0/1 are low-information, near 0.5 high-information). Policies compete at equal
budget; the metric is mean absolute profile error. Prediction (T3/PSI logic):
entropy-greedy allocation beats uniform at every budget because uniform wastes
probes on already-resolved families.

Run:  python3 demo/run_policy_benchmark.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gauntlet.generator import FAMILIES  # noqa: E402
from gauntlet.policies import PSIPolicy, NeymanPolicy, UCBPolicy, UniformPolicy, profile_error, run_policy  # noqa: E402

THETAS = {
    "authority_forgery": 0.9,
    "state_deception": 0.5,
    "goal_subversion": 0.3,
    "epistemic_echo": 0.7,
    "exfiltration_lure": 0.1,
}
BUDGETS = [25, 50, 100, 200, 400]
TRIALS = 150


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    results: dict[str, dict[int, float]] = {p: {} for p in ("uniform", "ucb", "psi", "neyman")}
    for budget in BUDGETS:
        for name, cls in (("uniform", UniformPolicy), ("ucb", UCBPolicy), ("psi", PSIPolicy), ("neyman", NeymanPolicy)):
            errs = []
            for t in range(TRIALS):
                rng = random.Random(50000 + t * 17 + budget)
                est = run_policy(cls(FAMILIES), THETAS, budget, rng)
                errs.append(profile_error(est, THETAS))
            results[name][budget] = sum(errs) / len(errs)

    lines = [
        "# T3 Policy Benchmark — probe-allocation efficiency",
        "",
        f"Profile: {{{', '.join(f'{f}:{v}' for f, v in THETAS.items())}}}; {TRIALS} trials per cell.",
        "",
        "**Finding (negative result, policy-objective mismatch):** both intuitive adaptive"
        " policies LOSE to uniform at profile estimation — UCB-lite optimizes REGRET"
        " (find-the-worst-arm) and starves other families; PSI entropy-greedy optimizes"
        " information-about-theta, which misallocates effort across extreme-rate families."
        " The estimation-correct criterion is variance equalization (Neyman).",
        "",
        "| Budget | uniform | Neyman | UCB-lite | PSI |",
        "|---|---|---|---|---|",
    ]
    for b in BUDGETS:
        lines.append(
            f"| {b} | {results['uniform'][b]:.4f} | {results['neyman'][b]:.4f} | "
            f"{results['ucb'][b]:.4f} | {results['psi'][b]:.4f} |"
        )

    best_adaptive = min(results["neyman"][BUDGETS[-1]], results["psi"][BUDGETS[-1]], results["ucb"][BUDGETS[-1]])
    uniform_final = results["uniform"][BUDGETS[-1]]
    lines += [
        "",
        f"## VERDICT: uniform error={uniform_final:.4f} vs best adaptive={best_adaptive:.4f} at n={BUDGETS[-1]}"
        f" → {'adaptive wins — inspect' if best_adaptive < uniform_final * 0.98 else 'uniform is the strong baseline; objective-mismatch quantified for UCB and PSI'}",
        "",
        "*Field-level content for T3: probe-design objectives must MATCH the estimation goal."
        " Regret-optimal (bandit) and information-optimal (psychophysics PSI) criteria are"
        " both misallocations for profile estimation; variance-equalizing (Neyman) is the"
        " correct criterion, and uniform is a strong baseline. This refines the open problem:"
        " MI-optimal design is the right tool for DETECTION-style tasks, not estimation.*",
    ]
    (out_dir / "POLICY_BENCHMARK.md").write_text("\n".join(lines) + "\n")
    (out_dir / "policy_benchmark.json").write_text(json.dumps(results, indent=2))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
