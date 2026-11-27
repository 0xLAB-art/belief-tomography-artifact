"""Probe-allocation policies for belief tomography (T3 first benchmark).

The estimation layer is faithful to the instrument: each probe of family f
returns a Bernoulli(theta_f) breach verdict (the jury outcome), exactly as the
probe/verdict pipeline produces. E1/E5 validated that layer; this module
benchmarks the POLICY question: which family should each probe target?

Policies:
  uniform    — round-robin across families
  ucb        — GAUNTLET v0's UCB-lite: allocate by observed rate + exploration bonus
  psi        — PSI-style Bayesian adaptive design (imported from psychophysics,
               Watson 2017 / Kontsevich & Tyler 1999): maintain a Beta posterior
               per family; pick the family with maximal expected posterior-entropy
               reduction after one more probe.
"""

from __future__ import annotations

import math
import random


def _beta_entropy(alpha: float, beta: float) -> float:
    """Differential entropy of Beta(alpha, beta)."""
    a, b = alpha, beta
    return (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        - (a - 1) * _digamma(a)
        - (b - 1) * _digamma(b)
        + (a + b - 2) * _digamma(a + b)
    )


def _digamma(x: float) -> float:
    result = 0.0
    while x < 6:
        result -= 1 / x
        x += 1
    return result + math.log(x) - 1 / (2 * x) - 1 / (12 * x * x) + 1 / (120 * x**4)


class Policy:
    def __init__(self, families):
        self.families = list(families)
        self.alpha = {f: 1.0 for f in self.families}
        self.beta = {f: 1.0 for f in self.families}

    def next_family(self, rng: random.Random) -> str:  # noqa: B027
        raise NotImplementedError

    def observe(self, family: str, breach: bool) -> None:
        if breach:
            self.alpha[family] += 1
        else:
            self.beta[family] += 1

    def estimates(self) -> dict[str, float]:
        return {f: a / (a + b) for f, (a, b) in
                ((f, (self.alpha[f], self.beta[f])) for f in self.families)}


class UniformPolicy(Policy):
    def __init__(self, families):
        super().__init__(families)
        self._i = 0

    def next_family(self, rng: random.Random) -> str:
        f = self.families[self._i % len(self.families)]
        self._i += 1
        return f


class UCBPolicy(Policy):
    def next_family(self, rng: random.Random) -> str:
        total = sum(self.alpha[f] + self.beta[f] for f in self.families) - 2 * len(self.families)
        best, best_score = None, -1.0
        for f in self.families:
            n = self.alpha[f] + self.beta[f] - 2
            rate = self.alpha[f] / (self.alpha[f] + self.beta[f])
            score = rate + 0.25 * math.sqrt(math.log(total + 1) / max(1, n))
            if score > best_score:
                best, best_score = f, score
        return best


class NeymanPolicy(Policy):
    """Variance-equalizing allocation: probe the family with maximal posterior
    variance. This is the error-optimal criterion for profile ESTIMATION
    (equalizes p(1-p)/n across families) — as opposed to regret-optimal (UCB)
    or information-optimal (PSI) criteria, which serve different objectives."""

    def next_family(self, rng: random.Random) -> str:
        best, best_var = None, -1.0
        for f in self.families:
            a, b = self.alpha[f], self.beta[f]
            n = a + b
            var = (a * b) / (n * n * (n + 1))
            if var > best_var:
                best, best_var = f, var
        return best


class PSIPolicy(Policy):
    """Greedy expected-entropy-reduction probe placement (QUEST+/PSI transplanted)."""

    def next_family(self, rng: random.Random) -> str:
        best, best_gain = None, -1.0
        for f in self.families:
            a, b = self.alpha[f], self.beta[f]
            theta = a / (a + b)
            # expected posterior entropies after one Bernoulli draw
            h_breach = _beta_entropy(a + 1, b)
            h_pass = _beta_entropy(a, b + 1)
            expected_h = theta * h_breach + (1 - theta) * h_pass
            gain = _beta_entropy(a, b) - expected_h
            if gain > best_gain:
                best, best_gain = f, gain
        if best is None:
            best = rng.choice(self.families)
        return best


def run_policy(policy: Policy, thetas: dict[str, float], budget: int, rng: random.Random) -> dict[str, float]:
    for _ in range(budget):
        f = policy.next_family(rng)
        breach = rng.random() < thetas[f]
        policy.observe(f, breach)
    return policy.estimates()


def profile_error(est: dict[str, float], thetas: dict[str, float]) -> float:
    return sum(abs(est[f] - thetas[f]) for f in thetas) / len(thetas)
