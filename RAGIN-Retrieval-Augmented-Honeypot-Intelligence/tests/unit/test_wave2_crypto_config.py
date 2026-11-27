"""Wave-2 crypto/config follow-up (2026-10-26).

The Oct 25 wave (commit eea364d3) fixed data-pipeline injection and the
LLM/JEV chain (14/16 findings, tests/unit/test_wave2_hardening.py). This file
covers the third family — crypto/config:

HIGH fixed here (audit-integrity key):
* ``audit_integrity`` signed and verified audit rows with a hardcoded default
  key (``test-host-audit-key-v1``) tracked in git — anyone with a copy of the
  repo could forge \"intact\" rows, making the WS3 tamper-evidence invariant
  meaningless the moment the module is wired.
* The signer now refuses to run without an explicit ``RAGIN_AUDIT_HOST_KEY``,
  previously published key literals stay rejected, and verification fails
  closed when no key is configured.
* ``.env.example`` documents the key (empty template, generation hint).

Deferred from this wave (MEDIUM, documented on the MASTER_PLAN Phase 4
wave-2 line — fix-HIGHs-only gate):
* ``ragin-test-key-2024`` (public dev key in scripts/deploy.py,
  start_services.sh) is not in server_v2's placeholder-refusal set; adding it
  breaks the local dev harness (three test suites + start_services export it),
  so it needs a coordinated local-dev posture change. No production instance
  is affected (the field deployment boots with a real key).
* ``RAGIN_IP_SALT`` ships a public default and scripts/cowrie_pipeline_bridge.py
  + scripts/validate_phase1.py hardcode the salt instead of reading the env
  override (documented research-reproducibility default).
* A capture run without ``--study-secret`` silently downgrades to the unkeyed
  manifest digest (the kind marker records ``sha256`` honestly, but no warning
  is emitted).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ragin.cycle.containment import audit_integrity as ai

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


class TestAuditHostKeyFailClosed:
    """No default key: signing raises, verification fails, published keys stay dead."""

    def test_sign_refuses_when_key_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("RAGIN_AUDIT_HOST_KEY", raising=False)
        with pytest.raises(RuntimeError, match="RAGIN_AUDIT_HOST_KEY"):
            ai.sign_audit_row({"event": "serve", "session": "s1"})

    def test_sign_refuses_empty_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RAGIN_AUDIT_HOST_KEY", "")
        with pytest.raises(RuntimeError, match="RAGIN_AUDIT_HOST_KEY"):
            ai.sign_audit_row({"event": "serve"})

    def test_previously_published_default_stays_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The old hardcoded literal must not become valid by setting it back."""
        monkeypatch.setenv("RAGIN_AUDIT_HOST_KEY", "test-host-audit-key-v1")
        assert ai._audit_host_key() is None
        with pytest.raises(RuntimeError, match="RAGIN_AUDIT_HOST_KEY"):
            ai.sign_audit_row({"event": "serve"})

    def test_sign_verify_roundtrip_with_real_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RAGIN_AUDIT_HOST_KEY", "a" * 64)
        row = ai.sign_audit_row({"event": "serve", "session": "s1"})
        assert row["_audit_signature"] and len(row["_audit_signature"]) == 64
        assert ai.verify_audit_row(row)["integrity_ok"] is True

        tampered = dict(row, event="serve-then-swapped")
        verdict = ai.verify_audit_row(tampered)
        assert verdict["integrity_ok"] is False
        assert verdict["reason"] == "signature mismatch"

    def test_verify_fails_closed_without_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RAGIN_AUDIT_HOST_KEY", "b" * 64)
        row = ai.sign_audit_row({"event": "serve"})
        monkeypatch.delenv("RAGIN_AUDIT_HOST_KEY")
        verdict = ai.verify_audit_row(row)
        assert verdict["integrity_ok"] is False
        assert "not configured" in verdict["reason"]

    def test_chain_verification_without_key_flags_rows_not_crash(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("RAGIN_AUDIT_HOST_KEY", "c" * 64)
        rows = [ai.sign_audit_row({"event": e}) for e in ("create", "cmd", "serve")]
        monkeypatch.delenv("RAGIN_AUDIT_HOST_KEY")
        chain = ai.audit_chain_verified(rows)
        assert chain["verified"] is False
        assert chain["ok_count"] == 0

    def test_restart_persistent_log_refuses_without_key(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.delenv("RAGIN_AUDIT_HOST_KEY", raising=False)
        log = ai.RestartPersistentAuditLog(str(tmp_path / "audit.jsonl"))
        with pytest.raises(RuntimeError, match="RAGIN_AUDIT_HOST_KEY"):
            log.append({"event": "serve"})


class TestEnvExampleDocumentsAuditKey:
    def test_env_example_has_empty_audit_host_key_template(self) -> None:
        text = (ROOT / ".env.example").read_text()
        lines = [ln for ln in text.splitlines() if ln.startswith("RAGIN_AUDIT_HOST_KEY=")]
        assert lines, ".env.example must document RAGIN_AUDIT_HOST_KEY"
        assert lines[0] == "RAGIN_AUDIT_HOST_KEY=", (
            f"template must ship EMPTY (fail-closed copy/paste), got: {lines[0]!r}"
        )
        assert "secrets.token_hex" in text, "generation hint missing"
