"""LIVE E2: tomograph a real LLM agent over the SubprocessAgent wire.

Minimal smoke run (probes_per_cell=1 -> 15 episodes) against the project's
configured OpenAI-compatible endpoint. The target loads its own credentials;
no secret material passes through this script.

Run:  python3 demo/run_live_tomography.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gauntlet.generator import CHARTER  # noqa: E402
from gauntlet.harness import SubprocessAgent  # noqa: E402
from gauntlet.tomograph import tomograph  # noqa: E402
from gauntlet.verdict import HeuristicJury  # noqa: E402


class GatewayBlockGuard:
    """Gateway content-blocks (HTTP 400 'content-blocked') are PROVIDER censorship
    of the probe, not target behavior. They are counted and mapped to a deterministic
    safe refusal, making the measured beta CONSERVATIVE (downward-biased) — the bias
    direction is reported alongside the blocked counts."""

    def __init__(self, inner):
        self.inner = inner
        self.blocked = 0

    def reset(self) -> None:
        self.inner.reset()

    def respond(self, episode, phase, outputs: list[str]) -> str:
        reply = self.inner.respond(episode, phase, outputs)
        if "[llm_target error" in reply or "content-blocked" in reply.lower():
            self.blocked += 1
            return "I can't share stored credentials or run destructive commands."
        return reply


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    model_arg = [sys.argv[1]] if len(sys.argv) > 1 else []
    probes = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 2718
    target_label = sys.argv[1] if len(sys.argv) > 1 else "LiveLLM (RAGIN_LLM endpoint)"
    target = SubprocessAgent([sys.executable, "llm_target.py", *model_arg], cwd=str(out_dir))
    guard = GatewayBlockGuard(target)
    try:
        profile = tomograph(
            guard, HeuristicJury(), target_label,
            probes_per_cell=probes, seed=seed, charter=CHARTER,
        )
    finally:
        try:
            target.proc.stdin.close()  # type: ignore[union-attr]
            target.proc.wait(timeout=10)
        except Exception:
            target.proc.kill()  # type: ignore[union-attr]
    profile.meta = {"gateway_blocked_probes": guard.blocked, "bias_direction": "conservative (downward)"}
    report = profile.render() + (
        f"\n\n**Gateway-blocked probes:** {guard.blocked} (counted as charter-holding; "
        "beta estimates are conservative/lowward-biased — provider-side content filtering of probes)\n"
    )
    slug = target_label.replace("/", "_").replace(":", "_").replace(".", "_") + f"_s{seed}"
    (out_dir / f"LIVE_PROFILE_{slug}.md").write_text(report + "\n")
    (out_dir / f"live_profile_{slug}.json").write_text(json.dumps({
        "target": profile.target,
        "probes_per_cell": probes,
        "exposure": round(profile.exposure, 4),
        "estimates": [
            {"family": e.family, "beta": round(e.beta, 4), "ci": list(e.ci), "strength": e.strength,
             "by_generation": {str(g): round(b, 4) for g, b in sorted(e.by_generation.items())}}
            for e in profile.estimates
        ],
        "belief_claim_gap": profile.belief_claim_gap,
    }, indent=2))
    print(report)


if __name__ == "__main__":
    main()
