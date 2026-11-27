"""Wiring tests: HostFictionStore behind the RAGIN_HOST_FICTION opt-in flag.

Flag OFF (default): DeceptionGraph behaves byte-identically to the legacy
session-scoped path — no store, no wrapper, same graph objects per session.
Flag ON: session graphs come from the host store (pinned identity), the
verifier is wrapped for cross-session checks, and finalize-time promotion
binds verified facts to the host.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ragin.cycle.graph import DeceptionGraph  # noqa: E402
from ragin.graph.host_fiction import HostFictionStore, HostFictionVerifier  # noqa: E402
from ragin.hisoka.deception import identity_for  # noqa: E402

NOVICE = identity_for("novice")
INTERMEDIATE = identity_for("intermediate")


class TestFlagOff:
    def test_default_has_no_store(self, monkeypatch):
        monkeypatch.delenv("RAGIN_HOST_FICTION", raising=False)
        g = DeceptionGraph()
        assert g._host_store is None
        assert not isinstance(g._verifier, HostFictionVerifier)

    def test_legacy_graph_reuse_per_session(self, monkeypatch):
        monkeypatch.delenv("RAGIN_HOST_FICTION", raising=False)
        g = DeceptionGraph()
        a, b = g.fiction("s1"), g.fiction("s1")
        assert a is b
        assert g.fiction("s2") is not a

    def test_no_env_no_wrapper(self, monkeypatch):
        monkeypatch.setenv("RAGIN_HOST_FICTION", "")
        g = DeceptionGraph()
        assert g._host_store is None


class TestFlagOn:
    @pytest.fixture
    def graph(self, monkeypatch):
        monkeypatch.setenv("RAGIN_HOST_FICTION", "1")
        monkeypatch.delenv("RAGIN_HOST_FICTION_POLICY", raising=False)
        g = DeceptionGraph()
        yield g
        monkeypatch.delenv("RAGIN_HOST_FICTION", raising=False)

    def test_store_and_wrapper_installed(self, graph):
        assert isinstance(graph._host_store, HostFictionStore)
        assert isinstance(graph._verifier, HostFictionVerifier)

    def test_policy_switch(self, monkeypatch):
        monkeypatch.setenv("RAGIN_HOST_FICTION", "1")
        monkeypatch.setenv("RAGIN_HOST_FICTION_POLICY", "reconnect")
        g = DeceptionGraph()
        assert g._host_store.policy == "reconnect"

    def test_host_pinned_provisioning(self, graph):
        g1 = graph.fiction("s1", skill_level="novice")
        assert g1 is not None
        pinned = graph._host_store.pinned_identity
        assert pinned == NOVICE
        # Reclassified later session still faces the SAME machine:
        g2 = graph.fiction("s2", skill_level="intermediate")
        facts = {p: v for s, p, v, _src in g2.facts() if p == "hostname"}
        assert facts["hostname"] == NOVICE["host"]

    def test_finalize_promotes_verified_turns(self, graph):
        session_id = "sess-x"
        graph.fiction(session_id)  # provision through the store
        state = {
            "session_id": session_id,
            "verification": {"passed": True, "issues": []},
            "deception_response": {"response_text": "ok"},
            "attacker_input": "whoami",
            "classification": {"skill_level": "novice"},
        }
        graph.finalize_node(state)
        assert graph._host_store._sessions[session_id]["verified"] is True
        assert any(p == "user" for _s, p, _v, _src in graph._host_store._sessions[session_id]["graph"].facts())

    def test_finalize_skips_failed_turns(self, graph):
        state = {
            "session_id": "sess-y",
            "verification": {"passed": False, "issues": ["x"]},
            "deception_response": {"response_text": "bad"},
            "attacker_input": "whoami",
            "classification": {"skill_level": "novice"},
        }
        graph.finalize_node(state)
        assert "sess-y" not in graph._host_store._sessions

    def test_cross_session_draft_rejected_through_full_stack(self, graph):
        """End-to-end: session 1 serves/passes `ip addr`; session 2's drift
        draft on the same host is rejected by the wrapped verifier."""
        s1, s2 = "sess-a", "sess-b"
        ip_addr = (
            "webapp@web-srv-01:~$ ip addr\n"
            "2: eth0: <BROADCAST,MULTICAST,UP> mtu 1500\n"
            "    inet 10.0.0.12/24 brd 10.0.0.255 scope global eth0\n"
            "3: docker0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500\n"
            "    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0\n"
        )
        drifted = ip_addr.replace("172.17.0.1", "172.18.0.1")
        ctx_base = {"classification": {"skill_level": "novice"}}

        for sid, text in ((s1, ip_addr), (s2, drifted)):
            graph.fiction(sid)  # pipeline provisions the session graph first
            out = graph._verifier.verify(
                {"response_text": text},
                {"session_id": sid, "attacker_input": "ip addr", **ctx_base},
            )
            if sid == s1:
                assert out["passed"] is True
                graph.fiction(s1).observe(ip_addr, source="accepted")
                graph._host_store.mark_verified(s1)
                graph._host_store.promote_verified(s1)
            else:
                assert out["passed"] is False
                assert any(i.startswith("cross-session-contradiction") for i in out["issues"])


class TestVerifierInvariantSource:
    def test_registered_graph_identity_is_authoritative(self, monkeypatch):
        """The verifier must check identity against the session graph's pinned
        identity, not a classification re-derivation (single invariant source)."""
        monkeypatch.delenv("RAGIN_HOST_FICTION", raising=False)
        from ragin.cycle.verifier import FictionConsistencyVerifier

        store = HostFictionStore(host_key="h", policy="per_session")
        store.session_graph("s1", identity=NOVICE)
        g2 = store.session_graph("s2", identity=INTERMEDIATE)  # pinned → NOVICE seed
        v = FictionConsistencyVerifier(fictions={"s2": g2})
        out = v.verify(
            {"response_text": "webapp@app-db-02:~$ hostname\napp-db-02\n"},
            {"session_id": "s2", "attacker_input": "hostname", "classification": {"skill_level": "intermediate"}},
        )
        assert out["passed"] is False
        assert any("hostname" in i for i in out["issues"])
