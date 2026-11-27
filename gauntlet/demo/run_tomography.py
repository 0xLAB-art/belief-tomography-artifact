"""Belief Tomography demo: tomograph two foils with known ground-truth beliefs.

The naive foil holds all five measured beliefs strongly; the hardened foil holds
graded beliefs (resists low-generation probes, falls at the frontier). Tomography
recovers the difference from BLACK-BOX interaction only — no introspection.

Run:  python3 demo/run_tomography.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo.target_dummy import DummyTarget  # noqa: E402
from gauntlet.tomograph import tomograph  # noqa: E402
from gauntlet.verdict import HeuristicJury  # noqa: E402
from gauntlet.world import Episode  # noqa: E402


class HardenedDummy(DummyTarget):
    """Graded foil: resists probes up to a per-family generation, falls beyond it."""

    strength = {  # max generation resisted per family
        "authority_forgery": 2,
        "state_deception": 1,
        "goal_subversion": 1,
        "epistemic_echo": 0,
        "exfiltration_lure": 1,
    }

    def respond(self, episode: Episode, phase, outputs: list[str]) -> str:
        if episode.generation <= self.strength.get(episode.family, 0):
            return "I can't share stored credentials or run destructive commands."
        return super().respond(episode, phase, outputs)


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    jury = HeuristicJury()
    profiles = [
        tomograph(DummyTarget(), jury, "DummyTarget (naive foil)"),
        tomograph(HardenedDummy(), jury, "HardenedDummy (graded foil)"),
    ]
    report = "\n\n---\n\n".join(p.render() for p in profiles)
    payload = [
        {
            "target": p.target,
            "estimates": [
                {
                    "proposition": e.proposition,
                    "family": e.family,
                    "beta": round(e.beta, 4),
                    "ci": [round(e.ci[0], 4), round(e.ci[1], 4)],
                    "strength": e.strength,
                    "by_generation": {str(g): round(b, 4) for g, b in sorted(e.by_generation.items())},
                }
                for e in p.estimates
            ],
            "belief_claim_gap": p.belief_claim_gap,
            "exposure": round(p.exposure, 4),
        }
        for p in profiles
    ]
    (out_dir / "profile.json").write_text(json.dumps(payload, indent=2))
    (out_dir / "PROFILE.md").write_text(report + "\n")
    print(report)
    print(f"\nWritten: {out_dir / 'profile.json'}")
    print(f"Written: {out_dir / 'PROFILE.md'}")


if __name__ == "__main__":
    main()
