"""Core data model: adversarial episodes and their phases."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Phase:
    """One adversary -> target interaction step inside an episode."""

    adversary_text: str
    environment_text: str = ""  # untrusted tool/environment output shown to target
    # Oracles checked on the target's output after this phase is answered.


@dataclass
class Episode:
    """A single adversarial world: a closed scenario aimed at one target property."""

    episode_id: str
    family: str  # attack family id
    generation: int  # escalation generation 1..3
    target_property: str  # the safety/capability claim under test
    system_prompt: str  # the target's charter (what it must uphold)
    secret: str  # value the target must never disclose
    oracles: list[str] = field(default_factory=list)
    phases: list[Phase] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
