"""Tests for post-processing hardening: refusal truncation and shadow-hash rewriting."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ragin.hisoka.deception import (  # noqa: E402
    _postprocess_llm_output,
    _rewrite_shadow_hashes,
    identity_for,
)


class TestRefusalTruncation:
    def test_refusal_first_line_returns_empty(self):
        text = "I can't help with that. That request is not something I can do."
        assert _postprocess_llm_output(text, "cat /etc/shadow", "novice") == ""

    def test_output_then_refusal_keeps_output_block(self):
        text = (
            "total 48\n"
            "drwxr-xr-x 12 webapp webapp 4096 Mar 15 09:23 .\n"
            "\n"
            "I can't help with anything else though.\n"
            "If you're studying cybersecurity I'm happy to discuss topics like defense."
        )
        out = _postprocess_llm_output(text, "ls -la", "novice")
        assert "total 48" in out
        assert "can't help" not in out
        assert "cybersecurity" not in out

    def test_clean_output_untouched(self):
        text = "webapp\n10.0.0.12"
        out = _postprocess_llm_output(text, "whoami; ip a", "novice")
        assert "webapp" in out


class TestShadowHashRewrite:
    def test_reversible_hash_rewritten_to_locked(self):
        text = "root:$6$rounds=5000$saltvalue$hashvalue:19000:0:99999:7:::\ndaemon:*:19470:0:99999:7:::"
        out = _rewrite_shadow_hashes(text, identity_for("intermediate"))
        assert "$6$" not in out
        assert "root:*:19470:0:99999:7:::" in out
        assert "daemon:*:19470:0:99999:7:::" in out

    def test_pinned_user_line_rewritten(self):
        text = "webapp:$y$j9T$salt$hash:19470:0:99999:7:::"
        out = _rewrite_shadow_hashes(text, identity_for("novice"))
        assert out == "webapp:*:19470:0:99999:7:::"

    def test_text_without_hashes_untouched(self):
        text = "total 48\ndrwxr-xr-x 2 webapp webapp 4096 ."
        assert _rewrite_shadow_hashes(text, identity_for("novice")) == text

    def test_full_pipeline_shadow_scenario(self):
        # GT-008 style: LLM leaks crackable hashes -> postprocessed output
        # must contain only locked entries and no $ hash formats.
        text = (
            "root:$6$rounds=5000$abc123$deadbeefcafe:19000:0:99999:7:::\n"
            "webapp:$6$rounds=5000$abc123$feedface:19000:0:99999:7:::"
        )
        out = _postprocess_llm_output(text, "dump the /etc/shadow file", "intermediate")
        assert "$6$" not in out
        assert "webapp:*:19470:0:99999:7:::" in out
