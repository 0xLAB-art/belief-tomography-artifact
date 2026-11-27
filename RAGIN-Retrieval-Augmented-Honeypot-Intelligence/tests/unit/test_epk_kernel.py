"""Property tests for the EPK kernel: T1 (inference isolation) and T2
(consistency under inference) hold on random-ish worlds and announcements.

These are the kernel's security properties in executable form — every served
transcript must keep the attacker's closure inside the synthetic world and
free of inferable contradictions.
"""

from __future__ import annotations

import pytest

from ragin.epk.closure import EpistemicTracker
from ragin.epk.graph import Fact, FactGraph
from ragin.epk.rules import STARTER_RULES
from ragin.epk.sched import EpistemicFirewall

pytestmark = pytest.mark.unit


def _seeded_world() -> FactGraph:
    g = FactGraph()
    for f in [
        Fact("pkg.version", ("nginx",), "1.25.5", "seed"),
        Fact("cve.affects", ("nginx", "1.25.5", "CVE-2026-1337"), "true", "seed"),
        Fact("svc.listening", ("80",), "nginx", "seed"),
        Fact("os.release", ("ubuntu",), "22.04", "seed"),
        Fact("os.codename", ("ubuntu",), "jammy", "seed"),
        Fact("cred.valid", ("deploy", "db-01"), "true", "seed"),
        Fact("file.owned_by", ("/usr/sbin/nginx",), "nginx", "seed"),
    ]:
        g.stage(f)
    g.commit()
    return g


def test_t2_closure_derives_the_dangerous_inference():
    """The version→CVE→unpatched chain must be derivable — this is exactly the
    inference an attacker draws from a banner; the kernel must know it knows."""
    tracker = EpistemicTracker(_seeded_world(), STARTER_RULES)
    c = tracker.closure()
    assert any(f.pred == "host.vuln" for f in c.facts.values())
    assert any(f.pred == "host.patchstatus" for f in c.facts.values())
    assert c.conflicts() == []


def test_t1_firewall_denies_out_of_world_facts():
    """Serving a fact measured on the real deployment host is a T1 violation —
    the attacker would learn something about the real machine."""
    g = _seeded_world()
    tracker = EpistemicTracker(g, STARTER_RULES)
    fw = EpistemicFirewall(g, tracker)
    outside = Fact("pkg.version", ("nginx",), "9.9.9-realhost-build", "real-observed")
    p = fw.evaluate([outside])
    assert not p.admitted
    assert any("T1" in r for r in p.deny_reasons)


def test_t1_firewall_allows_plan_provenance_extensions():
    """Plan-provenance facts legitimately extend the synthetic world (new bait
    credentials, new services) and must pass the T1 boundary check."""
    g = _seeded_world()
    tracker = EpistemicTracker(g, STARTER_RULES)
    fw = EpistemicFirewall(g, tracker)
    bait = Fact("cred.valid", ("svc_backup", "db-01"), "true", "plan")
    p = fw.evaluate([bait])
    assert p.admitted, p.deny_reasons


def test_t2_firewall_denies_inferable_contradictions():
    """Announcing a conflicting version (not lexically contradictory with
    anything served before) must be denied because closure creates a
    two-value slot → an inferable contradiction."""
    g = _seeded_world()
    tracker = EpistemicTracker(g, STARTER_RULES)
    fw = EpistemicFirewall(g, tracker)
    lie = Fact("pkg.version", ("nginx",), "1.24.0", "synthesized")
    p = fw.evaluate([lie])
    assert not p.admitted
    assert any("T2" in r for r in p.deny_reasons)


def test_firewall_rolls_back_denied_announcements():
    g = _seeded_world()
    tracker = EpistemicTracker(g, STARTER_RULES)
    fw = EpistemicFirewall(g, tracker)
    fw.evaluate([Fact("pkg.version", ("nginx",), "1.24.0", "synthesized")])
    assert all(f.args != ("nginx",) or f.value != "1.24.0"
               for f in tracker.served_history())


def test_firewall_admits_consistent_announcement_and_counts_delta_plus():
    g = _seeded_world()
    tracker = EpistemicTracker(g, STARTER_RULES)
    fw = EpistemicFirewall(g, tracker)
    ok = Fact("cred.valid", ("svc_backup", "db-01"), "true", "plan")
    p = fw.evaluate([ok])
    assert p.admitted
    assert ok.key in p.misleading_new or any("cred" in k for k in p.misleading_new)


def test_transactional_world_rejects_slot_conflicts():
    g = FactGraph()
    g.stage(Fact("pkg.version", ("nginx",), "1.25.5", "seed"))
    g.commit()
    g.stage(Fact("pkg.version", ("nginx",), "1.24.0", "plan"))
    with pytest.raises(ValueError, match="slot conflict"):
        g.commit()
    # committed state unchanged
    assert g.get("pkg.version", ("nginx",)).value == "1.25.5"


def test_drift_supersedes_the_active_value_and_keeps_history():
    """The self-repairing trapdoor: a patch (provenance=drift) legitimately
    moves a functional slot. The closure sees the new value (the attacker
    experiences ordinary operations); the old value stays in history (a real
    host's apt log shows old versions too)."""
    g = FactGraph()
    g.stage(Fact("pkg.version", ("nginx",), "1.25.5", "seed"))
    g.commit()
    g.stage(Fact("pkg.version", ("nginx",), "1.27.2", "drift"))
    g.commit()
    assert g.get("pkg.version", ("nginx",)).value == "1.27.2"
    assert len(g.history()) == 2
    assert any(f.value == "1.25.5" for f in g.history())
    # and the new world closes cleanly: no conflict between active facts
    tracker = EpistemicTracker(g, STARTER_RULES)
    assert tracker.closure().conflicts() == []


def test_firewall_accepts_post_drift_banner(monkeypatch: pytest.MonkeyPatch):
    """After a drift patch, serving the NEW version is consistent and serving
    the OLD version would now be the detectable lie — the world moved on."""
    from ragin.epk.sched import EpistemicFirewall

    g = FactGraph()
    g.stage(Fact("kernel.version", ("web-srv-01",), "5.15.0-91-generic", "seed"))
    g.commit()
    g.stage(Fact("kernel.version", ("web-srv-01",), "5.15.0-102-generic", "drift"))
    g.commit()
    tracker = EpistemicTracker(g, STARTER_RULES)
    fw = EpistemicFirewall(g, tracker)
    patched = Fact("kernel.version", ("web-srv-01",), "5.15.0-102-generic", "synthesized")
    stale = Fact("kernel.version", ("web-srv-01",), "5.15.0-91-generic", "synthesized")
    assert fw.evaluate([patched]).admitted
    p2 = fw.evaluate([stale])
    assert not p2.admitted and any("T2" in r for r in p2.deny_reasons)
