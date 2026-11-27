"""Tests for the session fiction graph (verified deception memory)."""

from __future__ import annotations

import pytest

from ragin.graph.fiction import FictionGraph

IDENTITY = {
    "user": "webapp",
    "uid": "1001",
    "host": "web-srv-01",
    "domain": "corp.local",
    "distro": "Ubuntu 22.04.3 LTS",
    "kernel": "5.15.0-91-generic",
    "ip": "10.0.2.51",
}


@pytest.fixture
def graph() -> FictionGraph:
    return FictionGraph(session_id="sess-1", identity=IDENTITY)


class TestSeeding:
    def test_identity_is_seeded(self, graph):
        facts = {p: v for s, p, v, src in graph.facts()}
        assert facts["user"] == "webapp"
        assert facts["hostname"] == "web-srv-01"
        assert facts["os"] == "Ubuntu 22.04.3 LTS"

    def test_fresh_graph_is_consistent(self, graph):
        assert graph.summary()["consistent"]


class TestObservation:
    def test_consistent_reply_adds_no_contradictions(self, graph):
        obs = graph.observe("Linux web-srv-01 5.15.0-91-generic #167 SMP x86_64 GNU/Linux listening on port 4444")
        assert obs.consistent
        assert obs.added  # kernel/port mentioned are brand-new facts

    def test_version_strings_are_not_hostnames(self, graph):
        obs = graph.observe("Linux app-db-02 5.15.0-91-generic #167 SMP x86_64 GNU/Linux")
        assert obs.consistent
        hostnames = {f[2] for f in graph.facts() if f[1] == "hostname"}
        assert "5.15.0-91-generic" not in hostnames
        assert hostnames == {"web-srv-01"}  # seeded identity only

    def test_hostname_drift_is_flagged(self, graph):
        graph.observe("uid=1001(webapp) on web-srv-01.corp.local")
        obs = graph.observe("now running on other-host.corp.local 6.8.0-99-generic")
        assert not obs.consistent
        assert any(c["predicate"] == "hostname" for c in obs.contradictions)
        assert not graph.summary()["consistent"]

    def test_kernel_drift_is_flagged(self, graph):
        obs = graph.observe("Welcome to Ubuntu 22.04.3 LTS, kernel 6.8.0-99-generic")
        assert not obs.consistent

    def test_user_drift_is_flagged(self, graph):
        obs = graph.observe("uid=0(root) gid=0(root)")
        assert any(c["predicate"] == "user" for c in obs.contradictions)

    def test_port_mentions_are_not_stable(self, graph):
        obs = graph.observe("listening on port 4444")
        assert obs.consistent
        assert any(p == "port:4444" for _, p, _, _ in graph.facts())


class TestPromptBlock:
    def test_fact_block_serializes_identity(self, graph):
        block = graph.fact_block()
        assert "webapp" in block
        assert "web-srv-01" in block
        assert "corp.local" in block

    def test_empty_graph_has_no_block(self):
        g = FictionGraph(session_id="empty")
        assert g.fact_block() == ""

    def test_fact_block_is_injectable_prompt_text(self, graph):
        block = graph.fact_block()
        assert block.startswith("Environment state established earlier in this session")


class TestDistroExtraction:
    """The C1-battery uname regression: ``Ubuntu\\s+\\S+`` matched the
    '#167-Ubuntu SMP' banner present in EVERY real ``uname -a`` output,
    extracting os="Ubuntu SMP " — a guaranteed false contradiction of the
    pinned identity on the single most common fingerprint probe. Distro
    matching now requires a version-like token after the name."""

    UNAME = (
        "Linux web-srv-01 5.15.0-91-generic #167-Ubuntu SMP Fri Jul 14 10:07:39 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux"
    )

    def test_uname_banner_does_not_contradict_pinned_os(self, graph):
        obs = graph.observe(self.UNAME)
        assert obs.consistent
        assert obs.contradictions == []

    def test_uname_banner_does_not_extract_banner_text_as_os(self, graph):
        graph.observe(self.UNAME)
        os_values = {v for _, p, v, _ in graph.facts() if p == "os"}
        # Only the identity-seeded distro exists — never the SMP banner text.
        assert os_values == {"Ubuntu 22.04.3 LTS"}

    def test_true_distro_string_is_still_extracted(self, graph):
        obs = graph.observe("Welcome to Ubuntu 22.04.3 LTS (GNU/Linux 5.15.0-91-generic x86_64)")
        assert obs.consistent
        os_values = {v for _, p, v, _ in graph.facts() if p == "os"}
        assert any("22.04" in v for v in os_values)

    def test_uname_rotations_stay_consistent(self, graph):
        # The exact C1 re-query rotation that regressed: identical uname -a
        # replayed every turn must never self-contradict.
        for _ in range(5):
            assert graph.observe(self.UNAME).consistent


class TestSerialization:
    def test_to_dict_roundtrip(self, graph):
        data = graph.to_dict()
        assert data["session_id"] == "sess-1"
        assert data["consistent"] is True
        ids = {f["predicate"] for f in data["facts"]}
        assert "hostname" in ids


class TestL3RedTeamFixes:
    """Third-family (llama-3.3) red-team FPs fixed in the fiction extractor.

    Source: results/verifier_redteam_live_llama33_best.json FP taxonomy —
    benign drafts were rejected because the extractor minted garbage facts.
    Each test pins one observed FP shape plus its true-drift counterpart.
    """

    def test_kernel_label_tail_is_not_a_value(self, graph):
        # `Kernel version:` with no version token captured "version:" as the
        # kernel value (C-neg-ports-unstable, C-neg-hostname-remention FPs).
        # A colon-separated label WITHOUT a version-like value must not mint
        # a kernel fact; a real token after it still must.
        obs = graph.observe("Additional info:\n  Kernel version:\n  Uptime: 23 hours")
        assert obs.consistent
        obs2 = graph.observe("Kernel version: 4.15.0 on the secondary node")
        assert not obs2.consistent  # genuine drift must still fire

    def test_distro_across_newline_is_not_extracted(self, graph):
        # `running Ubuntu \n5.15.0-91` — the old \s gap crossed the newline
        # and minted os="Ubuntu \n5.15.0" from kernel prose.
        obs = graph.observe("welcome to web-srv-01, running Ubuntu \n5.15.0-91-generic #167-Ubuntu SMP")
        os_values = {v for _, p, v, _ in graph.facts() if p == "os"}
        assert obs.consistent
        assert all("\n" not in v for v in os_values)

    def test_parenthesized_distro_is_build_provenance(self, graph):
        # `(gcc (Ubuntu 9.4.0-1ubuntu1~20.04.1) 9.4.0 ...)` in gcc -v banners
        # is COMPILER provenance, not the OS (C-neg-hostname-remention[1] FP).
        obs = graph.observe(
            "Linux version 5.15.0-91-generic (buildd@ubuntu) (gcc (Ubuntu 9.4.0-1ubuntu1~20.04.1) 9.4.0, GNU ld (GNU Binutils for Ubuntu) 2.34)"
        )
        os_values = {v for _, p, v, _ in graph.facts() if p == "os"}
        assert obs.consistent
        assert all("9.4.0" not in v for v in os_values)

    def test_login_banner_value_must_be_on_the_same_line(self, graph):
        # `web-srv-01 login: \nwelcome to ...` — the old \s* keyword-value gap
        # crossed the newline and captured "welcome" as the session user.
        obs = graph.observe("web-srv-01 login: \nwelcome to web-srv-01, running fine")
        users = {v for _, p, v, _ in graph.facts() if p == "user"}
        assert obs.consistent
        assert "welcome" not in users
        assert users == {"webapp"}  # identity seed only

    def test_real_user_on_the_value_line_is_still_captured(self, graph):
        # The same-line rule must not break the V10 alias-drift contract: the
        # drift fact is not committed (the pinned user stands) but the
        # contradiction MUST fire.
        obs = graph.observe("webapp@web-srv-01:~$ ps aux\nrunning as the svc_backup account")
        assert not obs.consistent  # alias drift must fire (V10 contract)
        assert any(c["predicate"] == "user" and c["after"] == "svc_backup" for c in obs.contradictions)
