"""Tests for the man-in-the-loop approval gate."""

from __future__ import annotations

import pytest

from ragin.cycle.hitl import (
    ApprovalGateway,
    ApprovalLevel,
    ClaimedApprover,
    DefaultRiskBasedPolicy,
    FileAuditTrail,
    NullAuditor,
    RequiresApprovalError,
    risk_from_state,
)

HIGH_RISK_STATE = {
    "session_id": "s-apt",
    "classification": {"skill_level": "apt", "confidence": 0.9},
    "cti_analysis": {"extracted_techniques": ["T1059.001", "T1571"]},
    "plan": {},
    "deception_response": {"response_text": "listening on port 4444"},
}

LOW_RISK_STATE = {
    "session_id": "s-novice",
    "classification": {"skill_level": "novice", "confidence": 0.9},
    "cti_analysis": {"extracted_techniques": ["T1033"]},
    "plan": {},
    "deception_response": {"response_text": "uid=1001(webapp)"},
}


class TestRisk:
    def test_apt_credential_hunt_scores_high(self):
        assert risk_from_state(HIGH_RISK_STATE) >= 7.0

    def test_novice_query_scores_low(self):
        assert risk_from_state(LOW_RISK_STATE) <= 6.0

    def test_credential_dumping_raises_score(self):
        state = {**LOW_RISK_STATE, "cti_analysis": {"extracted_techniques": ["T1003.008"]}}
        assert risk_from_state(state) >= risk_from_state(LOW_RISK_STATE)


class TestPolicy:
    def test_apt_listener_requires_approval(self):
        assert DefaultRiskBasedPolicy().level_for(HIGH_RISK_STATE) == ApprovalLevel.REQUIRE

    def test_novice_probe_is_auto(self):
        assert ApprovalGateway().level_for(LOW_RISK_STATE) == ApprovalLevel.AUTO

    def test_thresholds_respect_notify_zone(self):
        state = {
            "session_id": "s-mid",
            "classification": {"skill_level": "expert"},
            "cti_analysis": {"extracted_techniques": ["T1552.005"]},
            "plan": {},
            "deception_response": {"response_text": "metadata"},
        }
        assert DefaultRiskBasedPolicy().level_for(state) in (ApprovalLevel.NOTIFY, ApprovalLevel.REQUIRE)


class TestGateway:
    def test_required_action_denies_when_approver_rejects(self):
        gateway = ApprovalGateway(approver=ClaimedApprover(lambda r: False))
        assert gateway.requires_approval(HIGH_RISK_STATE)
        decision = gateway.resolve(HIGH_RISK_STATE)
        assert decision.approved is False

    def test_no_approver_raises(self):
        gateway = ApprovalGateway()  # no approver attached
        with pytest.raises(RequiresApprovalError):
            gateway.resolve(HIGH_RISK_STATE)

    def test_audit_trail_records_decision(self, tmp_path):
        trail = FileAuditTrail(path=str(tmp_path / "audit.jsonl"))
        gateway = ApprovalGateway(approver=ClaimedApprover(lambda r: True), auditor=trail)
        gateway.resolve(HIGH_RISK_STATE, decided_by="test")
        line = (tmp_path / "audit.jsonl").read_text().strip()
        assert '"action": "spawn_decoy_listener"' in line
        assert '"approved": true' in line

    def test_build_request_action_for_credentials(self):
        state = {**LOW_RISK_STATE, "cti_analysis": {"extracted_techniques": ["T1003.008"]}}
        request = ApprovalGateway().build_request(state)
        assert request.action == "deploy_fabricated_credential"

    def test_build_request_action_for_listener(self):
        request = ApprovalGateway().build_request(HIGH_RISK_STATE)
        assert request.action == "spawn_decoy_listener"

    def test_null_auditor_is_noop(self):
        gateway = ApprovalGateway(auditor=NullAuditor())
        assert gateway.resolve(LOW_RISK_STATE).approved is True
