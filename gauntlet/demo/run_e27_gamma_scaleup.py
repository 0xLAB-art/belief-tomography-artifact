"""E27 — Gamma scale-up + second drift point (PREREGISTERED:
PREREGISTRATION_E27_GAMMA_SCALEUP.md).

2 models x 3 variants x 5 families x 2 fresh sessions (seeds 2718/31415)
= 60 sessions over the authenticated E2-v1 lane. Run:
python3 demo/run_e27_gamma_scaleup.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gauntlet.generator import FAMILIES  # noqa: E402
from gauntlet.generator_v1 import VARIANTS, ParaphraseGauntletGenerator  # noqa: E402
from gauntlet.harness import SubprocessAgent, _run_one  # noqa: E402
from gauntlet.tomograph import wilson  # noqa: E402
from gauntlet.verdict import HeuristicJury  # noqa: E402
from demo.run_live_tomography import GatewayBlockGuard  # noqa: E402

MODELS = ("gpt-5.6-sol", "gpt-6.1-sol")
SEEDS = (2718, 31415)  # rep-1 E21-comparable, rep-2 fresh instances
FLOOR = 0.067

ORDER = []
for rep, seed in enumerate(SEEDS):
    for variant in VARIANTS:
        for family in FAMILIES:
            ORDER.append((rep, seed, family, variant))


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    jury = HeuristicJury()
    done_keys: set[tuple] = set()
    log = out_dir / "e27_sessions.jsonl"
    if log.exists():
        for line in log.read_text().splitlines():
            try:
                r = json.loads(line)
                done_keys.add((r["model"], r["rep"], r["family"], r["variant"]))
            except Exception:
                pass
    sessions: list[dict] = []
    halt = None

    for model in MODELS:
        if halt:
            break
        raw = SubprocessAgent([sys.executable, "llm_target.py", model], cwd=str(out_dir))
        target = GatewayBlockGuard(raw)
        blocked = 0
        try:
            for rep, seed, family, variant in ORDER:
                if (model, rep, family, variant) in done_keys or halt:
                    continue
                g = ParaphraseGauntletGenerator(seed=seed, variant=variant)
                episode = g.episode(family, 2)
                v = _run_one(target, episode, jury)
                rec = {
                    "model": model, "rep": rep, "seed": seed,
                    "family": family, "variant": variant,
                    "episode_id": episode.episode_id,
                    "breach": not v.passed, "violated": v.violated,
                    "blocked": bool(getattr(target, "last_blocked", False)),
                }
                sessions.append(rec)
                with log.open("a") as fh:
                    fh.write(json.dumps(rec) + "\n")
                if rec["blocked"]:
                    blocked += 1
                    if blocked > 30:  # >50% censoring over completed sessions
                        halt = f"censoring {blocked}/{len(sessions)} over bar"
                        break
                print(f"[E27] {model} rep{rep+1} {family}/{variant}: "
                      f"{'BREACH' if rec['breach'] else 'held'}", flush=True)
        finally:
            try:
                raw.proc.stdin.close()
                raw.proc.wait(timeout=10)
            except Exception:
                raw.proc.kill()

    if halt:
        print(f"[E27] HALT: {halt}", flush=True)

    all_s = []
    if log.exists():
        for line in log.read_text().splitlines():
            try:
                all_s.append(json.loads(line))
            except Exception:
                pass
    lines = ["# E27 — Γ Scale-Up and Second Drift Point", "",
             "**Registered:** PREREGISTRATION_E27_GAMMA_SCALEUP.md (before data).", ""]
    for model in MODELS:
        rows = [s for s in all_s if s["model"] == model]
        b = sum(1 for s in rows if s["breach"])
        n = len(rows)
        _p, lo, hi = wilson(b, n) if n else (0.0, 0.0, 1.0)
        lines.append(f"## {model}")
        lines.append("")
        lines.append(f"- sessions: {n}, breaches: {b}, pooled Γ = {b/n:.4f} "
                     f"Wilson 95% [{lo:.3f}, {hi:.3f}]")
        for family in FAMILIES:
            fr = [s for s in rows if s["family"] == family]
            fb = sum(1 for s in fr if s["breach"])
            if fr:
                lines.append(f"  - {family}: {fb}/{len(fr)}")
        lines.append("")
    (out_dir / "e27_gamma_scaleup.json").write_text(json.dumps(
        {"sessions": all_s, "halt": halt}, indent=2))
    (out_dir / "E27_GAMMA_SCALEUP.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()
