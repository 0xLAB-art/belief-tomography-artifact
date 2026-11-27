"""Tests for FictionConsistencyVerifier (C2 — verification-before-serve)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest  # noqa: F401  (fixture deps kept for future parametrization)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ragin.cycle.verifier import FictionConsistencyVerifier  # noqa: E402


@pytest.fixture
def verifier() -> FictionConsistencyVerifier:
    return FictionConsistencyVerifier()


class TestPassingResponses:
    def test_realistic_ls_output_passes(self, verifier):
        out = verifier.verify(
            {"response_text": "total 48\ndrwxr-xr-x 12 webapp webapp 4096 Mar 15 09:23 ."},
            {"session_id": "s1", "attacker_input": "ls -la", "classification": {"skill_level": "novice"}},
        )
        assert out["passed"] is True
        assert out["issues"] == []

    def test_whoami_pinned_answer_passes(self, verifier):
        out = verifier.verify(
            {"response_text": "webapp"},
            {"session_id": "s1", "attacker_input": "whoami", "classification": {"skill_level": "novice"}},
        )
        assert out["passed"] is True

    def test_id_pinned_answer_passes(self, verifier):
        out = verifier.verify(
            {"response_text": "uid=1001(webapp) gid=1001(webapp) groups=1001(webapp)"},
            {"session_id": "s1", "attacker_input": "id", "classification": {"skill_level": "novice"}},
        )
        assert out["passed"] is True

    def test_locked_shadow_entries_pass(self, verifier):
        shadow = "root:*:19470:0:99999:7:::\ndaemon:*:19470:0:99999:7:::\nwebapp:*:19470:0:99999:7:::"
        ctx = {
            "session_id": "s1",
            "attacker_input": "cat /etc/shadow",
            "classification": {"skill_level": "intermediate"},
        }
        out = verifier.verify({"response_text": shadow}, ctx)
        assert out["passed"] is True


class TestV16bPromptTailFallback:
    """V16b fallback derives the command from the transcript echo when ctx
    attacker_input is empty. Regression (2026-09-27 cross-family rescore):
    flattening `id -un` to bare `id` routed correct variant answers into the
    strict uid=() branch and false-rejected them (V17 contract violation)."""

    def test_id_un_variant_via_echo_passes_with_bare_name(self, verifier):
        text = (
            "webapp@web-srv-01:~$ id -un\n"
            "webapp\n"
            "webapp@web-srv-01:~$ printf 'active account: %s\\n' '$(id -un)'\n"
            "active account: webapp"
        )
        out = verifier.verify(
            {"response_text": text},
            {"session_id": "s1", "attacker_input": "", "classification": {"skill_level": "novice"}},
        )
        assert out["passed"] is True
        assert out["issues"] == []

    def test_bare_id_via_echo_keeps_strict_shape(self, verifier):
        out = verifier.verify(
            {"response_text": "webapp@web-srv-01:~$ id\nuid=1001(webapp) gid=1001(webapp) groups=1001(webapp)"},
            {"session_id": "s1", "attacker_input": "", "classification": {"skill_level": "novice"}},
        )
        assert out["passed"] is True

    def test_bare_id_via_echo_still_catches_wrong_user(self, verifier):
        out = verifier.verify(
            {
                "response_text": "webapp@web-srv-01:~$ id\nuid=1002(svc_backup) gid=1002(svc_backup) groups=1002(svc_backup)"
            },
            {"session_id": "s1", "attacker_input": "", "classification": {"skill_level": "novice"}},
        )
        assert out["passed"] is False
        assert any("id must report uid=1001(webapp)" in i for i in out["issues"])

    def test_id_un_variant_via_echo_still_catches_wrong_user(self, verifier):
        out = verifier.verify(
            {"response_text": "webapp@web-srv-01:~$ id -un\nsvc_backup"},
            {"session_id": "s1", "attacker_input": "", "classification": {"skill_level": "novice"}},
        )
        assert out["passed"] is False
        assert any("id variant must report 'webapp'" in i for i in out["issues"])


class TestFailingResponses:
    def test_refusal_fails(self, verifier):
        out = verifier.verify(
            {"response_text": "I can't help with that. I'm here to help with legitimate system administration."},
            {"session_id": "s2", "attacker_input": "cat /etc/shadow", "classification": {"skill_level": "novice"}},
        )
        assert out["passed"] is False
        assert any("danger-signal" in i for i in out["issues"])

    def test_ai_self_reference_fails(self, verifier):
        out = verifier.verify(
            {"response_text": "As an AI language model I cannot reveal /etc/shadow contents."},
            {"session_id": "s2", "attacker_input": "cat /etc/shadow", "classification": {"skill_level": "novice"}},
        )
        assert out["passed"] is False

    def test_whoami_wrong_user_fails(self, verifier):
        out = verifier.verify(
            {"response_text": "root"},
            {"session_id": "s2", "attacker_input": "whoami", "classification": {"skill_level": "novice"}},
        )
        assert out["passed"] is False
        assert any("identity-pin" in i for i in out["issues"])

    def test_root_prompt_fails(self, verifier):
        out = verifier.verify(
            {"response_text": "root@server:~# cat /etc/shadow"},
            {"session_id": "s2", "attacker_input": "dump the shadow file", "classification": {"skill_level": "novice"}},
        )
        assert out["passed"] is False
        assert any("identity-pin" in i for i in out["issues"])

    def test_empty_response_fails(self, verifier):
        out = verifier.verify(
            {"response_text": ""},
            {"session_id": "s2", "attacker_input": "ls", "classification": {"skill_level": "novice"}},
        )
        assert out["passed"] is False
        assert any("degenerate" in i for i in out["issues"])

    def test_fiction_contradiction_fails(self, verifier):
        # First reply establishes a hostname in the session graph; a later
        # reply naming a DIFFERENT hostname must be caught as a contradiction
        # of the stable predicate seeded from identity.
        gt_input = "hostname -f"
        session_state = {"session_id": "s3", "attacker_input": gt_input, "classification": {"skill_level": "novice"}}
        v = FictionConsistencyVerifier()
        ok = v.verify({"response_text": "web-srv-01.corp.local"}, session_state)
        assert ok["passed"] is True
        bad = v.verify({"response_text": "db-prod-09.corp.local"}, session_state)
        assert bad["passed"] is False
        assert any("fiction-contradiction" in i for i in bad["issues"])

    def test_string_response_accepted(self, verifier):
        out = verifier.verify("webapp", {"session_id": "s4", "attacker_input": "whoami"})
        assert out["passed"] is True

    def test_verifier_tag_present(self, verifier):
        out = verifier.verify({"response_text": "webapp"}, {"session_id": "s4", "attacker_input": "whoami"})
        assert out["verifier"] == "FictionConsistencyVerifier"
