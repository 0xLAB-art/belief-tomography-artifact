#!/usr/bin/env python3
"""Pre-registered A/B statistics for the AI adversarial workload.

Implements `docs/ARM_AB_PREREGISTRATION_2026-10-28.md`:

  * endpoints: dwell_s (primary), first_turn_latency_s + bait_targeting
    (secondary confirmatory), turns / output chars (descriptive)
  * stratified percentile bootstrap (10k, seed 20261028, strata = persona)
  * Mann-Whitney U (exact when untied) + rank-biserial effect size
  * Fisher exact for the session-level binary
  * Holm-Bonferroni across the three confirmatory endpoints
  * censoring flag + sensitivity excluding censored sessions
  * post-hoc minimum detectable effect (normal-theory approximation)

Deviations from the frozen text are recorded in the artifact's `deviations`
list instead of being applied silently.

Usage:
  python3 scripts/field_arm_stats.py              # write the artifact
  python3 scripts/field_arm_stats.py --check      # fail on drift
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs" / "ARM_AB_PREREGISTRATION_2026-10-28.md"
DEFAULT_A = ROOT / "results" / "field_attack" / "sessions_armA_cowrie.jsonl"
DEFAULT_C = ROOT / "results" / "field_attack" / "sessions_armC_ragin.jsonl"
DEFAULT_OUT = ROOT / "results" / "field_attack" / "arm_stats_bootstrap_v1.json"

SEED = 20261028
ITERS = 10_000
CONFIRMATORY = ("dwell_s", "first_turn_latency_s", "bait_targeting")

# Commands that go after planted credentials. This is attacker intent and is
# therefore comparable across arms; what each surface *returns* for those
# commands is not (see `descriptive.surface_dependent`).
BAIT_TARGET = (
    r"(\.dbpass|\.env\b|id_rsa|authorized_keys|/etc/shadow|credential|password|"
    r"api[_-]?key|AKIA|(^|\s)aws(\s|$))"
)


def _load_comparison_module():
    """Reuse the arm-comparison regexes rather than redefining them."""
    path = ROOT / "scripts" / "field_arm_comparison.py"
    spec = importlib.util.spec_from_file_location("field_arm_comparison", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def session_metrics(record: dict) -> dict:
    log = record.get("log") or []
    latencies = [t.get("latency_s") for t in log if t.get("latency_s")]
    outputs = [t.get("output_chars", 0) for t in log]
    commands = [str(t.get("cmd", "")) for t in log]
    import re

    return {
        "persona": record.get("persona", "?"),
        "run_id": record.get("run_id"),
        "turns": int(record.get("turns") or 0),
        "dwell_s": float(record.get("dwell_s") or 0.0),
        "first_turn_latency_s": float(np.mean(latencies)) if latencies else None,
        "output_chars_per_turn": float(np.mean(outputs)) if outputs else 0.0,
        "bait_targeting": int(any(re.search(BAIT_TARGET, c, re.I) for c in commands)),
    }


def load_arm(path: Path) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [session_metrics(r) for r in rows if not r.get("error")]


def _strata(metrics: list[dict], key: str) -> dict[str, np.ndarray]:
    strata: dict[str, list[float]] = {}
    for m in metrics:
        value = m[key]
        if value is None:
            continue
        strata.setdefault(m["persona"], []).append(float(value))
    return {k: np.asarray(v, dtype=float) for k, v in strata.items()}


def _flatten(strata: dict[str, np.ndarray]) -> np.ndarray:
    return np.concatenate([strata[k] for k in sorted(strata)])


def strat_bootstrap_diff(a: dict[str, np.ndarray], c: dict[str, np.ndarray], rng, iters: int) -> dict:
    personas = sorted(set(a) & set(c))
    mean_diffs = np.empty(iters)
    median_diffs = np.empty(iters)
    for i in range(iters):
        ca, cc = [], []
        for p in personas:
            ca.append(rng.choice(a[p], size=a[p].size, replace=True))
            cc.append(rng.choice(c[p], size=c[p].size, replace=True))
        ra, rc = np.concatenate(ca), np.concatenate(cc)
        mean_diffs[i] = rc.mean() - ra.mean()
        median_diffs[i] = np.median(rc) - np.median(ra)
    va = np.concatenate([a[p] for p in personas])
    vc = np.concatenate([c[p] for p in personas])
    return {
        "diff": float(vc.mean() - va.mean()),
        "ci95": [float(np.percentile(mean_diffs, 2.5)), float(np.percentile(mean_diffs, 97.5))],
        "median_diff": float(np.median(vc) - np.median(va)),
        "median_ci95": [float(np.percentile(median_diffs, 2.5)), float(np.percentile(median_diffs, 97.5))],
        "strata": personas,
        "n_a": int(va.size),
        "n_c": int(vc.size),
    }


def mwu(a: np.ndarray, c: np.ndarray) -> dict:
    res = stats.mannwhitneyu(a, c, alternative="two-sided", method="auto")
    n_a, n_c = a.size, c.size
    u = float(res.statistic)  # U for the first sample (a)
    rank_biserial = 1.0 - (2.0 * u) / (n_a * n_c)  # negative => c larger
    return {
        "u": u,
        "p_raw": float(res.pvalue),
        "rank_biserial": float(-rank_biserial),  # positive => c larger
        "method": getattr(res, "method", "auto"),
    }


def holm(pvals: dict[str, float]) -> dict[str, float]:
    ordered = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for i, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, p * (m - i)))
        adjusted[name] = running
    return adjusted


def post_hoc_mde(pooled_sd: float, n_a: int, n_c: int) -> dict:
    """Normal-theory two-sample approximation, labelled post hoc.

    Mann-Whitney needs roughly 15% more n than the t-test at the same power,
    so this is a lower bound on the true detectable effect.
    """
    z_alpha = stats.norm.ppf(0.975)
    z_beta = stats.norm.ppf(0.80)
    d = (z_alpha + z_beta) * np.sqrt(1.0 / n_a + 1.0 / n_c)
    return {
        "method": "normal-theory two-sample approximation (post hoc; MWU needs ~15% more n)",
        "alpha": 0.05,
        "power": 0.80,
        "mde_cohens_d": round(float(d), 3),
        "mde_units": round(float(d * pooled_sd), 1),
        "pooled_sd": round(float(pooled_sd), 1),
    }


def build(a_path: Path, c_path: Path) -> dict:
    a_metrics = load_arm(a_path)
    c_metrics = load_arm(c_path)
    if len(a_metrics) != len(c_metrics):
        raise SystemExit(f"unbalanced arms: {len(a_metrics)} vs {len(c_metrics)}")

    cap_turns = max(max(m["turns"] for m in a_metrics), max(m["turns"] for m in c_metrics))
    rng = np.random.default_rng(SEED)

    endpoints: dict[str, dict] = {}
    raw_p: dict[str, float] = {}
    for name in ("dwell_s", "first_turn_latency_s", "output_chars_per_turn", "turns", "bait_targeting"):
        sa, sc = _strata(a_metrics, name), _strata(c_metrics, name)
        va, vc = _flatten(sa), _flatten(sc)
        entry: dict = {
            "tier": "primary" if name == "dwell_s" else (
                "secondary" if name in CONFIRMATORY else "descriptive"
            ),
            "unit": "session",
            "point_a": round(float(va.mean()), 2),
            "point_c": round(float(vc.mean()), 2),
            "median_a": round(float(np.median(va)), 2),
            "median_c": round(float(np.median(vc)), 2),
            "n_a": int(va.size),
            "n_c": int(vc.size),
        }
        entry.update(strat_bootstrap_diff(sa, sc, rng, ITERS))
        if name == "bait_targeting":
            table = [
                [int(vc.sum()), int(vc.size - vc.sum())],
                [int(va.sum()), int(va.size - va.sum())],
            ]
            fisher = stats.fisher_exact(table, alternative="two-sided")
            entry.update({"test": "fisher_exact", "table_c_a_true_false": table,
                          "odds_ratio": float(fisher.statistic), "p_raw": float(fisher.pvalue)})
        else:
            test = mwu(va, vc)
            entry.update({"test": "mann_whitney_u", **test})
        if name in CONFIRMATORY:
            raw_p[name] = entry["p_raw"]
            # sample size the observed effect would need at 80% power (post hoc)
            pooled_sd = float(np.concatenate([va, vc]).std(ddof=1))
            effect_d = abs(entry["diff"]) / pooled_sd if pooled_sd else 0.0
            if effect_d > 0:
                z_a, z_b = stats.norm.ppf(0.975), stats.norm.ppf(0.80)
                entry["n_required_80pct"] = int(np.ceil(2 * ((z_a + z_b) / effect_d) ** 2))
                entry["observed_cohens_d"] = round(effect_d, 3)
        endpoints[name] = entry

    adjusted = holm(raw_p)
    for name, p in adjusted.items():
        endpoints[name]["p_holm"] = float(p)
        endpoints[name]["significant_holm"] = bool(p < 0.05)

    # censoring + sensitivity: dwell restricted to sessions that ended on their own
    censored_a = [m for m in a_metrics if m["turns"] >= cap_turns]
    censored_c = [m for m in c_metrics if m["turns"] >= cap_turns]
    unc_a = [m["dwell_s"] for m in a_metrics if m["turns"] < cap_turns]
    unc_c = [m["dwell_s"] for m in c_metrics if m["turns"] < cap_turns]
    censoring = {
        "cap_turns": cap_turns,
        "censored_a": len(censored_a),
        "censored_c": len(censored_c),
        "sensitivity_uncensored": {
            "n_a": len(unc_a), "n_c": len(unc_c),
            "mean_a": round(float(np.mean(unc_a)), 1) if unc_a else None,
            "mean_c": round(float(np.mean(unc_c)), 1) if unc_c else None,
            "diff": round(float(np.mean(unc_c) - np.mean(unc_a)), 1) if unc_a and unc_c else None,
        },
    }

    pooled_dwell = np.concatenate([_flatten(_strata(a_metrics, "dwell_s")),
                                   _flatten(_strata(c_metrics, "dwell_s"))])
    power = post_hoc_mde(float(pooled_dwell.std(ddof=1)), len(a_metrics), len(c_metrics))

    comparison = _load_comparison_module()
    transcripts = {
        "A_cowrie_only": "\n".join(json.loads(line).get("transcript", "")
                                   for line in a_path.read_text(encoding="utf-8").splitlines() if line.strip()),
        "C_ragin": "\n".join(json.loads(line).get("transcript", "")
                             for line in c_path.read_text(encoding="utf-8").splitlines() if line.strip()),
    }
    surface_hits = {
        arm: {name: len(pattern.findall(text)) for name, pattern in comparison.SENSITIVE_READS.items()}
        for arm, text in transcripts.items()
    }

    return {
        "schema": "ragin.field_attack.arm_stats_bootstrap.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "preregistration": {"path": str(PREREG.relative_to(ROOT)), "sha256": _sha256(PREREG)},
        "inputs": {
            "arm_a": {"path": str(a_path.relative_to(ROOT)), "sha256": _sha256(a_path)},
            "arm_c": {"path": str(c_path.relative_to(ROOT)), "sha256": _sha256(c_path)},
            "sessions": {"a": len(a_metrics), "c": len(c_metrics)},
        },
        "bootstrap": {"iterations": ITERS, "seed": SEED, "strata": "persona",
                      "statistic": "difference of means (C - A)"},
        "endpoints": endpoints,
        "censoring": censoring,
        "power": power,
        "descriptive": {
            "surface_dependent": {
                "label": "counts what each surface returns; NOT a controlled contrast",
                "sensitive_read_hits": surface_hits,
            }
        },
        "deviations": [
            "endpoint renamed `first_turn_latency_s`: the driver records latency only on "
            "turn 1, so arm-level 'turn latency' means time-to-first-response. §5.6 must use "
            "that name.",
            "censoring sensitivity computed as complete-case dwell (excluding sessions at the "
            "turn cap) instead of substituting median turn time: dwell already contains the "
            "per-turn latencies, so the substitution would restate the raw mean.",
        ],
        "decision_rule": "docs/ARM_AB_PREREGISTRATION_2026-10-28.md §Decision rule",
    }


def _sanitize(payload: dict) -> dict:
    clean = json.loads(json.dumps(payload))
    clean.pop("generated_at", None)
    return clean


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm-a", type=Path, default=DEFAULT_A)
    parser.add_argument("--arm-c", type=Path, default=DEFAULT_C)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true", help="recompute and fail on drift")
    args = parser.parse_args(argv[1:])

    payload = build(args.arm_a, args.arm_c)

    if args.check:
        if not args.out.exists():
            print(f"missing artifact: {args.out}", file=sys.stderr)
            return 1
        existing = json.loads(args.out.read_text(encoding="utf-8"))
        if _sanitize(existing) != _sanitize(payload):
            print(f"drift: {args.out} does not match a fresh recomputation", file=sys.stderr)
            return 1
        print(f"ok: {args.out} reproduces")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for name, e in payload["endpoints"].items():
        extra = ""
        if "p_holm" in e:
            extra = (f" p_raw={e['p_raw']:.4f} p_holm={e['p_holm']:.4f}"
                     f" n_req={e.get('n_required_80pct', '-')}")
        print(f"{name:24s} A={e['point_a']:>8} C={e['point_c']:>8} diff={e['diff']:>8.2f} "
              f"CI=[{e['ci95'][0]:.2f}, {e['ci95'][1]:.2f}] "
              f"med_diff={e['median_diff']:>7.2f} medCI=[{e['median_ci95'][0]:.2f}, "
              f"{e['median_ci95'][1]:.2f}]{extra}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
