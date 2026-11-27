"""Tests for the host-level persistent fiction layer (cross-session consistency).

Covers: reconnect shared-graph semantics, per_session promotion rules
(verified-only), cross-session contradiction checks, host-identity swap
detection (per-skill identities name different machines), persistence
round-trip, and the HostFictionVerifier's fail-closed composition.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ragin.cycle.verifier import FictionConsistencyVerifier  # noqa: E402
from ragin.graph.host_fiction import (  # noqa: E402
    HostFictionStore,
    HostFictionVerifier,
    _is_host_stable,
)
from ragin.hisoka.deception import identity_for  # noqa: E402

NOVICE = identity_for("novice")
INTERMEDIATE = identity_for("intermediate")

IP_ADDR = (
    "webapp@web-srv-01:~$ ip addr\n"
    "1: lo: <LOOPBACK,UP> mtu 65536\n"
    "    inet 127.0.0.1/8 scope host lo\n"
    "2: eth0: <BROADCAST,MULTICAST,UP> mtu 1500\n"
    "    inet 10.0.0.12/24 brd 10.0.0.255 scope global eth0\n"
    "3: docker0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500\n"
    "    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0\n"
)
IP_ADDR_DRIFT = IP_ADDR.replace("172.17.0.1", "172.18.0.1")


def _store(policy: str = "per_session") -> HostFictionStore:
    return HostFictionStore(host_key="host-a", policy=policy)


class TestHostStablePredicates:
    def test_scoped_interface_facts_are_host_stable(self):
        assert _is_host_stable("ip:docker0")
        assert _is_host_stable("port:22")
        assert _is_host_stable("ip")
        assert _is_host_stable("kernel")
        assert not _is_host_stable("ip_seen")

    def test_unknown_policy_rejected(self):
        with pytest.raises(ValueError):
            HostFictionStore(host_key="h", policy="yolo")


class TestReconnectPolicy:
    def test_reconnect_shares_one_graph(self):
        store = _store("reconnect")
        g1 = store.session_graph("s1", identity=NOVICE)
        g2 = store.session_graph("s2", identity=NOVICE)
        assert g1 is g2
        g1.observe(IP_ADDR)
        assert g2.facts()  # session B sees session A's facts


class TestPromotion:
    def test_only_verified_sessions_promote(self):
        store = _store()
        g = store.session_graph("s1", identity=NOVICE)
        g.observe(IP_ADDR)
        assert store.promote_verified("s1") == 0  # not marked verified yet
        store.mark_verified("s1")
        promoted = store.promote_verified("s1")
        assert promoted > 0
        # loopback excluded; eth0 host ip + docker0 scoped + host/os/kernel/... facts
        facts = {(s, p): vals for (s, p), vals in store._host_facts.items()}
        assert ("env", "ip:docker0") in facts
        assert facts[("env", "ip:docker0")] == {"172.17.0.1": ["s1"]}
        assert ("env", "ip") in facts

    def test_unverified_session_keyerror_on_mark(self):
        store = _store()
        with pytest.raises(KeyError):
            store.mark_verified("ghost")


class TestCrossSessionChecks:
    def test_drift_detected_and_repetition_not(self):
        store = _store()
        g1 = store.session_graph("s1", identity=NOVICE)
        g1.observe(IP_ADDR)
        store.mark_verified("s1")
        store.promote_verified("s1")
        # Same host, new session, drift on the docker0 address:
        g2 = store.session_graph("s2", identity=NOVICE)
        g2.observe(IP_ADDR_DRIFT)
        check = store.check_against_host("s2", g2)
        assert not check.consistent
        assert check.contradictions[0]["predicate"] == "ip:docker0"
        assert check.contradictions[0]["prior_sessions"] == ["s1"]
        # A revisiting attacker REPEATING the fact must not be flagged:
        g3 = store.session_graph("s3", identity=NOVICE)
        g3.observe(IP_ADDR)
        check3 = store.check_against_host("s3", g3)
        assert check3.consistent
        assert check3.checked_against >= 1

    def test_fqdn_remention_is_not_contradiction(self):
        """Regression (external-baseline hostfiction run, 2026-09-27): a draft
        re-mentioning the pinned host as an FQDN (`hostname -f` →
        web-srv-01.corp.local) after a prior session promoted the SHORT-form
        seed must NOT be a cross-session contradiction — same machine,
        mirroring the session graph's FQDN-aware _same_value."""
        store = _store()
        g1 = store.session_graph("s1", identity=NOVICE)
        g1.observe("webapp@web-srv-01:~$ hostname\nweb-srv-01\n")
        store.mark_verified("s1")
        store.promote_verified("s1")
        g2 = store.session_graph("s2", identity=NOVICE)
        g2.observe("webapp@web-srv-01:~$ hostname -f\nweb-srv-01.corp.local\n")
        check = store.check_against_host("s2", g2)
        assert check.consistent, check.contradictions

    def test_verifier_rejects_cross_session_drift(self):
        store = _store()
        g1 = store.session_graph("s1", identity=NOVICE)
        inner1 = FictionConsistencyVerifier(fictions={"s1": g1})
        w1 = HostFictionVerifier(inner1, store)
        out1 = w1.verify(
            {"response_text": IP_ADDR},
            {"session_id": "s1", "attacker_input": "ip addr", "classification": {"skill_level": "novice"}},
        )
        assert out1["passed"] is True
        g1.observe(IP_ADDR, source="accepted")
        store.mark_verified("s1")
        store.promote_verified("s1")

        g2 = store.session_graph("s2", identity=NOVICE)
        inner2 = FictionConsistencyVerifier(fictions={"s2": g2})
        w2 = HostFictionVerifier(inner2, store)
        out2 = w2.verify(
            {"response_text": IP_ADDR_DRIFT},
            {"session_id": "s2", "attacker_input": "ip addr", "classification": {"skill_level": "novice"}},
        )
        assert out2["passed"] is False
        assert any(i.startswith("cross-session-contradiction") for i in out2["issues"])

    def test_inner_failure_short_circuits_cross_check(self):
        store = _store()
        g1 = store.session_graph("s1", identity=NOVICE)
        g1.observe(IP_ADDR)
        store.mark_verified("s1")
        store.promote_verified("s1")
        g2 = store.session_graph("s2", identity=NOVICE)
        inner = FictionConsistencyVerifier(fictions={"s2": g2})
        wrapper = HostFictionVerifier(inner, store)
        # Session-level failure (os drift, the shape the session graph
        # demonstrably catches) must surface the SESSION issue; no
        # cross-session issue may be appended on top of a failed draft.
        bad = "Linux web-srv-01 4.19.0-25-amd64 #1 SMP Debian x86_64 GNU/Linux\n"
        out = wrapper.verify(
            {"response_text": bad},
            {"session_id": "s2", "attacker_input": "uname -a", "classification": {"skill_level": "novice"}},
        )
        assert out["passed"] is False
        assert not any(i.startswith("cross-session-contradiction") for i in out["issues"])


class TestHostIdentityPin:
    def test_returning_attacker_reclassified_is_flagged(self):
        store = _store()
        store.session_graph("s1", identity=NOVICE)  # first contact pins web-srv-01
        swap = store.identity_mismatch(INTERMEDIATE)
        assert swap is not None
        assert swap["field"] == "host"
        assert "app-db-02" in swap["offered"]

    def test_same_identity_no_swap(self):
        store = _store()
        store.session_graph("s1", identity=NOVICE)
        assert store.identity_mismatch(NOVICE) is None
        assert store.identity_mismatch(None) is None

    def test_later_session_seeded_with_pinned_identity(self):
        """Provisioning-time pin: a reclassified session is seeded with the
        machine pinned at first contact (per-skill identities name different
        hosts otherwise) — the swap fails SESSION-level verification."""
        store = _store()
        store.session_graph("s1", identity=NOVICE)
        g2 = store.session_graph("s2", identity=INTERMEDIATE)
        assert g2 is not None
        facts = {p: v for (_s, p), (v, _src) in {(s, p): (v, src) for s, p, v, src in g2.facts()}.items()}
        assert facts.get("hostname") == NOVICE["host"]  # NOT app-db-02

    def test_reclassified_session_draft_fails_session_verification(self):
        """A draft naming the OTHER machine under the pinned seed is rejected
        by the session-level hostname check (swap made impossible at
        provisioning time)."""
        store = _store()
        store.session_graph("s1", identity=NOVICE)
        g2 = store.session_graph("s2", identity=INTERMEDIATE)  # pinned → NOVICE seed
        inner = FictionConsistencyVerifier(fictions={"s2": g2})
        wrapper = HostFictionVerifier(inner, store)
        swap_text = "webapp@app-db-02:~$ hostname\napp-db-02\n"
        out = wrapper.verify(
            {"response_text": swap_text},
            {"session_id": "s2", "attacker_input": "hostname", "classification": {"skill_level": "intermediate"}},
        )
        assert out["passed"] is False
        assert any("hostname" in i for i in out["issues"])


class TestPersistence:
    def test_roundtrip_preserves_and_still_catches(self, tmp_path):
        store = _store()
        g1 = store.session_graph("s1", identity=NOVICE)
        g1.observe(IP_ADDR)
        store.mark_verified("s1")
        store.promote_verified("s1")
        path = tmp_path / "host_a.json"
        store.save(path)

        loaded = HostFictionStore.load(path)
        assert loaded.host_key == "host-a"
        assert loaded.pinned_identity == NOVICE
        assert loaded.to_dict()["host_facts"] == store.to_dict()["host_facts"]
        g2 = loaded.session_graph("s2", identity=NOVICE)
        g2.observe(IP_ADDR_DRIFT)
        check = loaded.check_against_host("s2", g2)
        assert not check.consistent
