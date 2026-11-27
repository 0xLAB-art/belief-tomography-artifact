"""EPK integration surface: opt-in epistemic screening for the serving path.

`EPKScreen` wraps the kernel (world + tracker + firewall) behind a single
call the pipeline can make on every candidate response, BEFORE the existing
verifier/HITL machinery. Enabled via RAGIN_EPK_ENABLED=1 (default off — the
kernel is additive: denial by the firewall only *adds* a rejection reason;
it never bypasses the existing gates).

The candidate facts are extracted from the response text with the v1 typed
extractor (kernel builds, package versions, service declarations); the
extractor is intentionally conservative — it only extracts what it can type,
so a missed fact degrades to the legacy behavior (legacy gates decide).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

from ragin.epk.closure import EpistemicTracker
from ragin.epk.graph import Fact, FactGraph
from ragin.epk.rules import STARTER_RULES
from ragin.epk.sched import EpistemicFirewall, Profile

_KERNEL_RE = re.compile(r"Linux\s+(\S+)\s+(\d+\.\d+\.\d+-\d+-generic)")
_VERSION_RE = re.compile(r"\b(nginx|mysql|openssh|apache)[-/]v?\s*(\d+\.\d+(?:\.\d+)?)",
                         re.IGNORECASE)
_SVC_RE = re.compile(r"^\s*([a-z0-9_.-]+?)\.service\s+.*?(?:Server\s+([\d.]+))?\s*$",
                     re.MULTILINE)
_LISTEN_RE = re.compile(r"(?:listen.*?|LISTEN\s+.*?):(\d{2,5})\b")
# shell-prompt hostname capture: "webapp@web-srv-01:~$" → web-srv-01
_PROMPT_HOST_RE = re.compile(r"[a-z_][a-z0-9_-]*@([a-zA-Z0-9._-]+?)[:#]", re.IGNORECASE)


def _seed_facts_from_identity(identity: dict[str, Any]) -> list[Fact]:
    """Seed the world from the host fiction identity block (W4): the pinned
    fiction identity is in-world by definition, so its facts ground the T2
    functional-slot checks on live traffic (banner-injection defense)."""
    facts: list[Fact] = []
    host = str(identity.get("host") or "web-srv-01")
    if identity.get("kernel"):
        facts.append(Fact("kernel.version", (host,), str(identity["kernel"]), "seed"))
    if identity.get("distro"):
        # "Ubuntu 22.04.3 LTS" → release fact when parseable
        parts = str(identity["distro"]).split()
        if len(parts) >= 2:
            facts.append(Fact("os.release", (parts[0].lower(),), parts[1], "seed"))
    if identity.get("ip"):
        facts.append(Fact("host.addr", (host,), str(identity["ip"]), "seed"))
    if identity.get("user"):
        facts.append(Fact("user.exists", (str(identity["user"]),), "true", "seed"))
    # the pinned hostname is THE world hostname: any other hostname appearing
    # in a prompt is a cross-surface tell (e.g. a front-end rendering its own
    # name) and is denied at the T1 boundary by the firewall
    facts.append(Fact("host.name", (host,), host, "seed"))
    return facts


@dataclass
class ScreenResult:
    admitted: bool
    profile: Profile
    extracted: list[Fact] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "admitted": self.admitted,
            "enabled": self.enabled,
            "profile": self.profile.to_dict(),
            "extracted": [f.to_dict() for f in self.extracted],
        }


def epk_enabled() -> bool:
    return os.environ.get("RAGIN_EPK_ENABLED", "0") == "1"


class EPKScreen:
    """One instance per session (world seeded from the pinned fiction identity
    when available). Thread-safety: like the rest of the v1 kernel,
    single-threaded per serving loop."""

    def __init__(self, world: FactGraph | None = None,
                 seed_identity: dict[str, Any] | None = None) -> None:
        if world is not None:
            self.world = world
        else:
            self.world = FactGraph()
            for f in _seed_facts_from_identity(seed_identity or {}):
                self.world.stage(f)
            self.world.commit()
        self.tracker = EpistemicTracker(self.world, STARTER_RULES)
        self.firewall = EpistemicFirewall(self.world, self.tracker)

    def extract(self, response_text: str) -> list[Fact]:
        """Typed extraction of candidate facts from a drafted response."""
        facts: list[Fact] = []
        m = _KERNEL_RE.search(response_text)
        if m:
            facts.append(Fact("kernel.version", (m.group(1),), m.group(2), "synthesized"))
        for svc, ver in _VERSION_RE.findall(response_text):
            facts.append(Fact("pkg.version", (svc.lower(),), ver, "synthesized"))
        for svc, ver in _SVC_RE.findall(response_text):
            facts.append(Fact("svc.named", (svc,), "running", "synthesized"))
            if ver:
                facts.append(Fact("pkg.version", (svc,), ver, "synthesized"))
        for port in _LISTEN_RE.findall(response_text):
            facts.append(Fact("svc.listening", (port,), "unknown", "synthesized"))
        for host in _PROMPT_HOST_RE.findall(response_text):
            facts.append(Fact("host.name", (host,), host, "synthesized"))
        return facts

    def screen(self, response_text: str) -> ScreenResult:
        """Extract + firewall-evaluate a drafted response. On denial the caller
        must NOT serve; on admit the extracted facts are announced (H_t grows)
        and the response may proceed to the legacy gates."""
        if not epk_enabled():
            return ScreenResult(admitted=True,
                                profile=Profile(admitted=True), enabled=False)
        facts = self.extract(response_text)
        profile = self.firewall.evaluate(facts)
        return ScreenResult(admitted=profile.admitted, profile=profile,
                            extracted=facts, enabled=True)
