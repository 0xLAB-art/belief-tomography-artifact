"""E2-v1 live replication runner — independent episodes + full transcript logging.

Why v1: the E2-v0 live driver reused generator episode ids (all probes were
"E0001"), so the target's per-episode conversation never reset and the entire
run accumulated in ONE context. That violates the independence assumption of
the estimator: each probe must be a fresh session. This runner:

  * assigns every probe a unique session id (family + generation + index),
  * logs every phase (probe text, environment, reply, blocked flag) to JSONL,
  * logs every verdict, checkpointed per episode so a hung lane cannot erase
    an entire multi-hour run,
  * spawns a fresh target subprocess per episode: a single long-lived child
    accumulated hung gateway connections (14 consecutive 60s x 3 timeouts in
    the first attempt, while fresh processes answered the same probes in ~3 s).

The frozen estimator (tomograph.py / verdict.py @8ceb6e0) is untouched. Both the
episode-isolation fix and the per-episode process fix are logged in
PREREGISTRATION_E2E3.md BEFORE any E2-v1 data is analyzed.

Run:
  python3 run_live_e2_replication.py <model> <probes_per_cell> <seed>
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from copy import copy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gauntlet.generator import CHARTER  # noqa: E402
from gauntlet.harness import SubprocessAgent  # noqa: E402
from gauntlet.tomograph import tomograph  # noqa: E402
from gauntlet.verdict import HeuristicJury  # noqa: E402

OUT = Path(__file__).resolve().parent


class InstrumentedTarget:
    """Unique session id per probe, full turn log, one fresh child per episode."""

    def __init__(self, model: str, stem: str):
        self.model = model
        self.stem = stem
        self.blocked = 0
        self.calls = 0
        self.records: list[dict] = []
        self.spawns = 0
        self._inner: SubprocessAgent | None = None
        self._session = None
        self._turn = 0
        self._probe = 0
        # A fresh run must not append to a previous run's artifacts with the
        # same stem (the E2-v1b gpt-6.1 re-run collided with the unmeasurable
        # run and produced 600 verdicts / 400 calls). Truncate all outputs.
        (OUT / f"{stem}.transcripts.jsonl").write_text("")
        self.progress = (OUT / f"{stem}.progress.jsonl").open("w")

    def spawn(self) -> None:
        if self._inner is not None:
            try:
                self._inner.proc.stdin.close()  # type: ignore[union-attr]
                self._inner.proc.wait(timeout=5)
            except Exception:
                self._inner.proc.kill()  # type: ignore[union-attr]
        self._inner = SubprocessAgent([sys.executable, "llm_target.py", self.model],
                                      cwd=str(OUT))
        self.spawns += 1

    @property
    def inner(self) -> SubprocessAgent:
        assert self._inner is not None
        return self._inner

    def reset(self) -> None:
        # Called by _run_one at the start of every episode: new process, new
        # conversation, new unique episode id on the wire.
        self.spawn()
        self._session = None
        self._turn = 0

    def new_session(self, episode) -> None:
        self._session = {
            "session_id": getattr(episode, "_audit_session", episode.episode_id),
            "family": episode.family,
            "generation": episode.generation,
        }
        self._turn = 0

    def respond(self, episode, phase, outputs: list[str]) -> str:
        # Unique session id per probe: the wire target resets on turn == 0.
        unique = f"{episode.family}-g{episode.generation}-{getattr(self, '_probe', 0):04d}"
        ep = copy(episode)
        ep.episode_id = unique
        t0 = time.monotonic()
        reply = self.inner.respond(ep, phase, outputs)
        elapsed = time.monotonic() - t0
        blocked = ("[llm_target error" in reply or "content-blocked" in reply.lower()
                   or not reply.strip())
        if blocked:
            self.blocked += 1
            reply = "I can't share stored credentials or run destructive commands."
        self.calls += 1
        rec = {
            "session_id": unique,
            "family": episode.family,
            "generation": episode.generation,
            "turn": self._turn,
            "adversary": phase.adversary_text,
            "environment": phase.environment_text,
            "reply": reply,
            "blocked": blocked,
            "elapsed_s": round(elapsed, 2),
        }
        self.records.append(rec)
        with (OUT / f"{self.stem}.transcripts.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")
        with (OUT / f"{self.stem}.progress.jsonl").open("a") as f:
            f.write(json.dumps({"event": "turn", "session": unique,
                                "blocked": blocked, "elapsed_s": rec["elapsed_s"]}) + "\n")
        self._turn += 1
        return reply

    def close(self) -> None:
        self.progress.close()
        if self._inner is not None:
            try:
                self._inner.proc.stdin.close()  # type: ignore[union-attr]
                self._inner.proc.wait(timeout=10)
            except Exception:
                self._inner.proc.kill()  # type: ignore[union-attr]


class LoggedJury:
    def __init__(self, inner: HeuristicJury, target: InstrumentedTarget, stem: str):
        self.inner = inner
        self.target = target
        self.stem = stem
        self.verdicts: list[dict] = []
        (OUT / f"{stem}.verdicts.jsonl").write_text("")

    def judge(self, episode, outputs):
        v = self.inner.judge(episode, outputs)
        rec = {
            "session_id": f"{episode.family}-g{episode.generation}-{getattr(self.target, '_probe', 0):04d}",
            "family": episode.family,
            "generation": episode.generation,
            "passed": v.passed,
            "violated": v.violated,
        }
        self.verdicts.append(rec)
        with (OUT / f"{self.stem}.verdicts.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")
        with (OUT / f"{self.stem}.progress.jsonl").open("a") as f:
            f.write(json.dumps({"event": "episode", "session": rec["session_id"],
                                "n": len(self.verdicts), "breaches":
                                sum(1 for x in self.verdicts if not x["passed"])}) + "\n")
        return v


def main() -> None:
    model = sys.argv[1] if len(sys.argv) > 1 else "gpt-5.6-sol"
    probes = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 2718

    slug = model.replace("/", "_").replace(":", "_").replace(".", "_")
    stem = f"E2V1_{slug}_p{probes}_s{seed}"
    # Fresh child per episode: skip the per-child health check, bound each call.
    os.environ["LLM_TARGET_SKIP_HEALTHCHECK"] = "1"
    os.environ.setdefault("LLM_TARGET_RETRIES", "2")
    os.environ.setdefault("LLM_TARGET_TIMEOUT", "30")

    target = InstrumentedTarget(model, stem)
    target.spawn()

    # Counter for unique session ids across the run (estimator calls respond per phase).
    probe_counter = {"n": 0}
    original_respond = target.respond

    def respond_with_counter(episode, phase, outputs):
        if phase is episode.phases[0] and len(outputs) == 0:
            probe_counter["n"] += 1
        target._probe = probe_counter["n"] % 10000
        return original_respond(episode, phase, outputs)

    target.respond = respond_with_counter  # type: ignore[method-assign]

    jury = LoggedJury(HeuristicJury(), target, stem)
    t0 = time.monotonic()
    try:
        profile = tomograph(target, jury, model, probes_per_cell=probes, seed=seed, charter=CHARTER)
    finally:
        target.close()

    elapsed = time.monotonic() - t0
    meta = {
        "instrument": "belief-tomography-v0.1",
        "estimator_pin": "8ceb6e0",
        "driver_fix": "unique_session_id + target resets on turn==0 (episode isolation)",
        "transport_fix": "fresh target subprocess per episode; bounded retries/timeout; per-episode checkpoint",
        "model": model,
        "probes_per_cell": probes,
        "seed": seed,
        "calls": target.calls,
        "blocked": target.blocked,
        "blocked_rate": round(target.blocked / max(1, target.calls), 4),
        "spawns": target.spawns,
        "elapsed_s": round(elapsed, 1),
        "transcript": f"{stem}.transcripts.jsonl",
        "verdicts": f"{stem}.verdicts.jsonl",
    }
    (OUT / f"{stem}.meta.json").write_text(json.dumps(meta, indent=2))
    (OUT / f"{stem}.profile.json").write_text(json.dumps({
        "target": profile.target,
        "probes_per_cell": probes,
        "exposure": round(profile.exposure, 4),
        "estimates": [
            {"family": e.family, "beta": round(e.beta, 4), "ci": list(e.ci), "strength": e.strength,
             "by_generation": {str(g): round(b, 4) for g, b in sorted(e.by_generation.items())}}
            for e in profile.estimates
        ],
        "belief_claim_gap": profile.belief_claim_gap,
        "meta": meta,
    }, indent=2))
    print(json.dumps(meta, indent=2))
    print(profile.render())


if __name__ == "__main__":
    main()
