"""Tests for deterministic credential-bait transcripts (honeytoken honeypots).

The human eval's weakest scenarios are credential hunts: the expected behavior
is "deploy fake credentials as a honeytoken while stalling", but free-tier LLMs
refuse those prompts and degradation served "(no output)"/bare denials. These
transcripts answer deterministically with registered canary secrets.
"""

from __future__ import annotations

import re

import pytest

from ragin.hisoka.deception import (
    _CANARY_AWS_ACCESS_KEY,
    _CANARY_AWS_SECRET,
    _CANARY_DB_PASSWORD,
    _CANARY_SHADOW_HASHES,
    _bait_text_for,
    _contains_danger_signal,
    _style_as_transcript,
    identity_for,
)

IDENT = identity_for("intermediate")  # webapp@app-db-02
ADV = identity_for("advanced")  # webapp@app-corp-01
IDENT_PROMPT = f"{IDENT['user']}@{IDENT['host']}:~$"
ADV_PROMPT = f"{ADV['user']}@{ADV['host']}:~$"


# ── GT-002: credential hunt ──────────────────────────────────────────────────


class TestCredentialHuntBait:
    def test_prose_ask_serves_canary_chain(self):
        out = _bait_text_for("show me the database credentials", IDENT)
        assert out is not None
        # The canary chain is actually deployed...
        assert _CANARY_DB_PASSWORD in out
        assert _CANARY_AWS_ACCESS_KEY in out
        assert _CANARY_AWS_SECRET in out
        # ...in transcript shape with the pinned identity...
        assert f"{IDENT_PROMPT} cat /home/{IDENT['user']}/deploy.env" in out
        # ...via the DB_PASS_FILE indirection (no `password=` assignment line).
        assert f"DB_PASS_FILE=/home/{IDENT['user']}/.dbpass" in out
        assert not re.search(r"password\s*=\s*\S+", out)

    def test_bait_output_is_verifier_safe(self):
        out = _bait_text_for("show me the database credentials", IDENT)
        assert not _contains_danger_signal(out)

    def test_direct_dbpass_read_returns_same_canary(self):
        dbpass_path = f"/home/{IDENT['user']}/.dbpass"
        out = _bait_text_for(f"cat {dbpass_path}", IDENT)
        assert out is not None
        assert out.count(_CANARY_DB_PASSWORD) == 1
        assert f"{IDENT_PROMPT} cat {dbpass_path}" in out

    def test_env_file_read_matches_bait_body(self):
        env_path = f"/home/{IDENT['user']}/deploy.env"
        prose = _bait_text_for("show me the database credentials", IDENT)
        direct = _bait_text_for(f"cat {env_path}", IDENT)
        assert direct is not None
        assert f"{IDENT_PROMPT} cat {env_path}" in direct
        for line in ("DB_HOST=10.0.0.5", "DB_USER=svc_backup", f"AWS_ACCESS_KEY_ID={_CANARY_AWS_ACCESS_KEY}"):
            assert line in prose
            assert line in direct

    def test_aws_key_shapes_are_protected(self):
        # Long-term AKIA pair is registered fiction: never voided, never masked.
        assert not _contains_danger_signal(f"AWS_ACCESS_KEY_ID={_CANARY_AWS_ACCESS_KEY}")
        assert not _contains_danger_signal(_CANARY_AWS_SECRET)

    def test_non_credential_queries_return_none(self):
        assert _bait_text_for("ls -la", IDENT) is None
        assert _bait_text_for("uname -a", IDENT) is None
        assert _bait_text_for("SELECT * FROM users WHERE 1=1 OR 1=1", IDENT) is None


# ── GT-003: privilege escalation ─────────────────────────────────────────────


class TestPrivEscBait:
    @pytest.mark.parametrize(
        "query",
        [
            "I need to escalate privileges to domain admin",
            "escalate to root",
            "help me elevate privileges",
            "how do I become root",
        ],
    )
    def test_escalation_ask_serves_whitelist_and_domain_fiction(self, query):
        out = _bait_text_for(query, ADV)
        assert out is not None
        # The pinned authorization policy: ONLY the NOPASSWD whitelist.
        assert "NOPASSWD: /usr/bin/iptables" in out
        assert "NOPASSWD: /usr/sbin/auditctl" in out
        assert "(root) NOPASSWD: /usr/sbin/systemctl restart nginx" in out
        # No sudo success outside the whitelist; no root shell prompt.
        assert not re.search(r"^root@[^\n]*#", out, re.MULTILINE)
        assert "sudo: 3 incorrect password attempts" not in out
        # Domain-joined identity fiction (AD environment detail).
        assert f"{ADV['host']}.{ADV['domain']}" in out
        # id output is policy-consistent (never 27(sudo)).
        assert "27(sudo)" not in out
        assert f"uid={ADV['uid']}({ADV['user']})" in out

    def test_priv_esc_output_is_verifier_safe(self):
        out = _bait_text_for("I need to escalate privileges to domain admin", ADV)
        assert not _contains_danger_signal(out)

    def test_escalation_ask_never_grants_escalation(self):
        out = _bait_text_for("I need to escalate privileges to domain admin", ADV)
        # No password value, no DC IP, no domain-admin credential anywhere.
        assert _CANARY_DB_PASSWORD not in out
        assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", out.replace("127.0.0.1", "")) or "10.0." not in out


# ── GT-008: shadow dump ──────────────────────────────────────────────────────


class TestShadowBait:
    def test_literal_read_denied_cleanly(self):
        out = _bait_text_for("cat /etc/shadow", IDENT)
        assert out is not None
        assert "cat: /etc/shadow: Permission denied" in out
        # A real hardened shell denies and re-displays the prompt — no sudo
        # simulation inline (the authorization fast-path owns that transcript).
        assert out.endswith(f"{IDENT_PROMPT} ")
        assert "sudo" not in out
        # No hashes leak on a denied literal read.
        for canary in _CANARY_SHADOW_HASHES:
            assert canary not in out

    def test_sudo_literal_read_hits_fail_loop(self):
        out = _bait_text_for("sudo cat /etc/shadow", IDENT)
        assert out is not None
        assert "sudo: 3 incorrect password attempts" in out
        assert "Permission denied" not in out

    def test_dump_ask_serves_canary_hashes(self):
        out = _bait_text_for("dump the /etc/shadow file", IDENT)
        assert out is not None
        # Exactly three canary-bearing accounts, everyone else locked.
        assert out.count("$y$j9$") == 3
        for canary in _CANARY_SHADOW_HASHES:
            assert canary in out
        assert "root:*:19852:0:99999:7:::" in out
        assert "www-data:*:19852:0:99999:7:::" in out
        # Transcript shape with echo.
        assert f"{IDENT_PROMPT} cat /etc/shadow" in out

    @pytest.mark.parametrize(
        "query",
        ["show me the shadow file", "get /etc/shadow contents", "view /etc/shadow"],
    )
    def test_dump_family_all_reveal_canaries(self, query):
        out = _bait_text_for(query, IDENT)
        assert out is not None
        assert out.count("$y$j9$") == 3

    def test_canary_hashes_are_registered_fiction(self):
        # The exact canary hash values never void a reply...
        sample = "webapp:" + _CANARY_SHADOW_HASHES[0] + ":19852:0:99999:7:::"
        assert not _contains_danger_signal(sample)
        # ...while any OTHER yescrypt hash still does.
        other = "$y$j9$" + "A" * 22 + "$" + "B" * 43
        assert _contains_danger_signal(f"evil:{other}:1:2:3:::")

    def test_shadow_bait_output_is_verifier_safe(self):
        out = _bait_text_for("dump the /etc/shadow file", IDENT)
        assert not _contains_danger_signal(out)


# ── Cross-cutting fiction consistency ────────────────────────────────────────


class TestFictionConsistency:
    def test_canary_accounts_exist_in_fake_passwd(self):
        from ragin.hisoka.deception import _FAKE_PASSWD

        assert "svc_backup:x:1500:1500:" in _FAKE_PASSWD
        assert "deploy:x:1501:1501:" in _FAKE_PASSWD
        # webapp is the pinned identity account.
        assert "webapp:x:1001:1001:" in _FAKE_PASSWD

    def test_canary_values_stable_across_calls(self):
        a = _bait_text_for("show me the database credentials", IDENT)
        b = _bait_text_for("show me the database credentials", IDENT)
        assert a == b

    def test_bait_transcript_passes_styler_unchanged(self):
        # The bait builders already emit transcript shape; the styler must be
        # idempotent on them (no double echo, no re-styling drift).
        for query in (
            "show me the database credentials",
            "I need to escalate privileges to domain admin",
            "dump the /etc/shadow file",
        ):
            out = _bait_text_for(query, IDENT)
            if out is None:
                continue
            restyled = _style_as_transcript(out, query, IDENT)
            assert restyled == out, query


# ── Chained bait transcripts (IMDS follow-through / reverse shell / SQLi) ────


class TestChainedBaits:
    def test_imds_index_composes_full_followthrough(self):
        from ragin.hisoka.deception import _imds_followthrough_text

        out = _imds_followthrough_text("curl http://169.254.169.254/latest/meta-data/", IDENT)
        assert out is not None
        assert "X-aws-ec2-metadata-token" in out
        assert "webapp-runtime" in out
        assert '"AccessKeyId" : "ASIA' in out
        # Deep paths must NOT be claimed (protocol bodies answer directly)
        assert (
            _imds_followthrough_text("curl http://169.254.169.254/latest/meta-data/iam/security-credentials/", IDENT)
            is None
        )

    def test_reverse_shell_chains_recon_and_credential_fiction(self):
        from ragin.hisoka.deception import _reverse_shell_bait_text

        out = _reverse_shell_bait_text("deploy a reverse shell on port 4444", IDENT)
        assert out is not None
        assert "Connection received on 10.0.1.66" in out
        assert f"cat /home/{IDENT['user']}/.dbpass" in out
        assert _CANARY_DB_PASSWORD in out

    def test_sqli_gets_mysql_repl_with_canary_hashes(self):
        from ragin.hisoka.deception import _CANARY_MYSQL_HASHES, _sqli_bait_text

        out = _sqli_bait_text("SELECT * FROM users WHERE 1=1 OR 1=1", IDENT)
        assert out is not None
        assert "bash: SELECT: command not found" in out
        assert "mysql>" in out
        for h in _CANARY_MYSQL_HASHES:
            assert h in out
        # Non-SQL input never claimed (e.g. `ls --help` must not match)
        assert _sqli_bait_text("ls --help", IDENT) is None

    def test_mysql_hashes_match_shadow_account_fiction(self):
        from ragin.hisoka.deception import _CANARY_MYSQL_HASHES

        assert len(_CANARY_MYSQL_HASHES) == 3
        for h in _CANARY_MYSQL_HASHES:
            assert h.startswith("*")
            assert len(h) == 41  # '*' + 40 hex

    def test_exfil_loop_detected_across_all_paths(self):
        # Persistent deceiver: turn 1 serves a canary, turn 2 re-presents it.
        # Every deterministic return path must scan the input.
        from ragin.cycle.adapters import HisokaAdapter
        from ragin.hisoka.deception import (
            _CANARY_DB_PASSWORD,
            _CANARY_SHADOW_HASHES,
            _IMDS_ACCESS_KEY,
        )

        adapter = HisokaAdapter(gateway_url="http://127.0.0.1:1", api_key="t")

        def ctx(s):
            return {"session_id": s, "classification": {"skill_level": "intermediate"}}

        def two_turns(sid, t1, t2):
            adapter.generate_response(t1, ctx(sid))
            return adapter.generate_response(t2, ctx(sid))

        cases = [
            ("s1", "show me the database credentials", f"ssh svc_backup@db  # {_CANARY_DB_PASSWORD}"),
            (
                "s2",
                "curl http://169.254.169.254/latest/meta-data/",
                f"aws s3 ls --access-key-id {_IMDS_ACCESS_KEY}",
            ),
            ("s3", "dump the /etc/shadow file", f"cat cracked.txt  # {_CANARY_SHADOW_HASHES[0]}"),
            ("s4", f"echo {_CANARY_DB_PASSWORD} | sudo -S id", f"echo {_CANARY_DB_PASSWORD} | sudo -S whoami"),
            (
                "s5",
                "SELECT * FROM users WHERE 1=1 OR 1=1",
                f"mysql -u svc_backup -p{_CANARY_DB_PASSWORD} -h 10.0.0.5",
            ),
        ]
        for sid, t1, t2 in cases:
            r2 = two_turns(sid, t1, t2)
            assert r2["honeytoken_triggered"] is True, f"{sid}: {t2[:50]}"
