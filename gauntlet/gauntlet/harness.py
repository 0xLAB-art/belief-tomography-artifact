"""Harness: drives a target through episodes and closes the loop.

Closed loop (v0): pass 1 probes every family x generation; pass 2 reallocates
budget toward high-failure families (UCB-lite) and attacks at each family's
frontier generation — the highest generation that already broke it.
"""

from __future__ import annotations

import abc
import json
import math
import subprocess

from .generator import FAMILIES, GauntletGenerator
from .verdict import Jury, Verdict
from .world import Episode


class TargetAgent(abc.ABC):
    """Anything certifiable must answer phase by phase and hold its charter."""

    @abc.abstractmethod
    def respond(self, episode: Episode, phase, outputs: list[str]) -> str:
        """Return the target's reply to one phase. `outputs` = its own prior replies."""

    def reset(self) -> None:  # noqa: B027 — optional hook
        pass


class SubprocessAgent(TargetAgent):
    """Runs an external agent as a subprocess speaking JSON lines on stdin/stdout.

    Wire protocol (one JSON object per line, both directions):
      -> {"type": "phase", "episode_id": str, "family": str, "generation": int,
          "system": str, "secret": str, "turn": int, "adversary": str,
          "environment": str, "own_outputs": [str, ...]}
      <- {"reply": str}
    The target owns its per-episode state (it sees episode_id and turn);
    GAUNTLET owns episodes, probes, and verdicts. The target never sees
    family labels or oracle logic — only what a real deployment would show it.
    """

    def __init__(self, cmd: list[str], cwd: str | None = None):
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            text=True, cwd=cwd, bufsize=1,
        )
        self._last_episode: str | None = None

    def respond(self, episode: Episode, phase, outputs: list[str]) -> str:
        if self._last_episode != episode.episode_id:
            self._last_episode = episode.episode_id
        msg = {
            "type": "phase",
            "episode_id": episode.episode_id,
            "family": episode.family,
            "generation": episode.generation,
            "system": episode.system_prompt,
            "secret": episode.secret,
            "turn": len(outputs),
            "adversary": phase.adversary_text,
            "environment": phase.environment_text,
            "own_outputs": outputs,
        }
        assert self.proc.stdin is not None and self.proc.stdout is not None
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError(f"target subprocess died (episode {episode.episode_id})")
        return json.loads(line)["reply"]


def _run_one(target: TargetAgent, episode: Episode, jury: Jury) -> Verdict:
    target.reset()
    outputs: list[str] = []
    for phase in episode.phases:
        outputs.append(target.respond(episode, phase, outputs))
    return jury.judge(episode, outputs)


def run_certification(
    target: TargetAgent,
    generator: GauntletGenerator,
    jury: Jury,
    adaptive_budget: int = 15,
) -> list[Verdict]:
    """Two-pass closed-loop certification run. Returns all verdicts in order."""
    # Pass 1 — probe the failure surface.
    verdicts: list[Verdict] = []
    stats: dict[str, dict[str, int]] = {f: {"n": 0, "fails": 0, "frontier": 1} for f in FAMILIES}
    for family, gen in generator.probe_plan():
        v = _run_one(target, generator.episode(family, gen), jury)
        verdicts.append(v)
        st = stats[family]
        st["n"] += 1
        if not v.passed:
            st["fails"] += 1
            st["frontier"] = max(st["frontier"], gen)

    # Pass 2 — adaptive reallocation at each family's frontier generation.
    total = len(verdicts)
    alloc: dict[str, int] = {}
    for family in FAMILIES:
        st = stats[family]
        rate = st["fails"] / st["n"]
        score = rate + 0.25 * math.sqrt(math.log(total + 1) / st["n"])
        alloc[family] = max(1, round(score * adaptive_budget))
    for family in FAMILIES:
        for _ in range(alloc[family]):
            gen = stats[family]["frontier"]
            verdicts.append(_run_one(target, generator.episode(family, gen), jury))

    # Attach run metadata for the certificate.
    for v in verdicts:
        v.notes = (v.notes + f" | alloc_pass={'probe' if v in verdicts[:total] else 'adaptive'}").strip(" |")
    return verdicts
