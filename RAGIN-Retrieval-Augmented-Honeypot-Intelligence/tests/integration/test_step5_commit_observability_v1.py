"""Step 5 — commit observability: explicit dispositions for every serving attempt.

Invariants under test (mirrors the serving-trace contract in
ragin/cycle/harness.py::_serving_attempt / _strict_commit):

1. Every RESPONSE_GENERATE serving_trace records an EXPLICIT commit
   disposition — accepted / rejected / not_attempted — with a reason. No
   attempt is left as NOT_VERIFIABLE after the turn resolves, and nothing is
   inferred by downstream consumers.
2. commit_state_effect is consistent with the graph hashes: "no_op_state_unchanged"
   iff before == after, "state_changed" iff before != after.
3. A verifier-rejected or HITL-denied attempt records commit not_attempted
   with the reason (verification_failed / approval_not_granted).
4. A generator commit REJECTION (clean committed=False) rolls the fiction
   graph AND the host store back, and PERSISTS the rollback to
   host_fiction_path so a restart cannot resurrect the rejected update. The
   turn then fail-safes to the verified fallback template
   (SAFE_FALLBACK_SERVED) — never an unverified serve.
5. A commit-time EXCEPTION (host promote/persist failure — durability
   unknown) FAILS CLOSED: the attempt's rejected disposition with rollback
   state hashes is recorded in the serving trace, then the turn aborts with
   verified_serving_failed. No fallback serve after a persistence failure.
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from ragin.cycle.adapters import SubstantiveStrategyAdapter
from ragin.cycle.harness import Harness
from ragin.cycle.hitl import ApprovalGateway, ApprovalLevel
from ragin.cycle.session import EventType, Session
from tests.integration.test_substantive_runtime_integration_v1 import (
    RejectingVerifier,
    SyntheticClassifier,
    SyntheticDon,
    RequestedStrategySelector,
    valid_bundle,
)
from ragin.decision_fusion_v4.runtime_mode import decision_arm_for_runtime


class CommitRejectingAdapter(SubstantiveStrategyAdapter):
    """Adapter whose generator refuses the commit after verification+HITL pass.

    Mimics a real rejection faithfully: the pending proposal is discarded and
    the generator's own state is NEVER mutated (visits stays 0), then
    committed=False is reported so the harness must roll back fiction + host.
    """

    def commit_candidate(self, candidate, *, verifier_passed, hitl_approved):
        metadata = candidate.get("metadata") if isinstance(candidate, dict) else None
        candidate_id = metadata.get("strategy_candidate_id") if isinstance(metadata, dict) else None
        if candidate_id:
            self._pending.pop(str(candidate_id), None)
        return {"committed": False, "reason": "synthetic_commit_rejected"}


class ExplodingCommitAdapter(SubstantiveStrategyAdapter):
    """Adapter whose generator commit raises at commit time."""

    def commit_candidate(self, candidate, *, verifier_passed, hitl_approved):
        raise RuntimeError("synthetic_commit_exception")


def make_harness(strategy, *, verifier=None, approval_gateway=None, adapter=None, host_fiction_path=None):
    adapter = adapter or SubstantiveStrategyAdapter("RAGIN_V4_SUBSTANTIVE_DETERMINISTIC")
    harness = Harness(
        classifier=SyntheticClassifier(),
        cti_engine=SyntheticDon(valid_bundle(strategy)),
        deceiver=adapter,
        verifier=verifier,
        mandatory_verification=True,
        max_retries=0,
        approval_gateway=approval_gateway,
        decision_arm=decision_arm_for_runtime("RAGIN_V4_SUBSTANTIVE_DETERMINISTIC"),
        host_fiction_path=host_fiction_path,
    )
    harness._policy_selector = RequestedStrategySelector(strategy)
    return harness, adapter


def serving_traces(session):
    return [e.data["serving_trace"] for e in session.replay() if e.event_type == EventType.RESPONSE_GENERATE]


def assert_disposition_consistent(trace):
    """commit_state_effect must agree with the graph hashes; accepted/rejected
    attempts must carry a reason, never NOT_VERIFIABLE."""
    assert trace["commit_event"] in {"accepted", "rejected", "not_attempted"}
    assert trace["commit_reason"] not in {None, "", "NOT_VERIFIABLE"}
    if trace["commit_event"] in {"accepted", "rejected"}:
        before, after = trace["commit_graph_before_sha256"], trace["commit_graph_after_sha256"]
        if before is not None and after is not None:
            assert trace["commit_state_effect"] == ("no_op_state_unchanged" if before == after else "state_changed")


def test_accepted_commit_records_explicit_disposition_and_graph_hashes():
    harness, _ = make_harness("maximize_recon_surface")
    with TemporaryDirectory() as directory:
        session = Session.create(source_ip="synthetic", session_dir=directory)
        result = harness.process(session, "ls -la")
        trace = result.deception_response["metadata"]["serving_attempts"][0]
        assert trace["commit_event"] == "accepted"
        assert trace["commit_reason"] == "accepted"
        assert trace["commit_state_effect"] in {"state_changed", "no_op_state_unchanged"}
        assert trace["commit_graph_before_sha256"]
        assert trace["commit_graph_after_sha256"]
        assert_disposition_consistent(trace)
        # The event log carries the same dispositions as the served metadata.
        event_trace = serving_traces(session)[0]
        assert event_trace["commit_event"] == "accepted"
        assert event_trace["commit_graph_after_sha256"] == trace["commit_graph_after_sha256"]
        # verification record carries the commit disposition too (not inferred).
        assert result.verification["commit_event"] == "accepted"
        assert result.verification["commit_state_effect"] == trace["commit_state_effect"]


def test_verifier_rejected_attempt_records_not_attempted_with_reason():
    harness, _ = make_harness("maximize_recon_surface", verifier=RejectingVerifier())
    with TemporaryDirectory() as directory:
        session = Session.create(source_ip="synthetic", session_dir=directory)
        result = harness.process(session, "ls -la")
        traces = serving_traces(session)
        assert result.error == "verified_serve_unavailable"
        attempt = traces[0]
        assert attempt["commit_event"] == "not_attempted"
        assert attempt["commit_reason"] == "verification_failed"
        assert attempt["hitl_result"] == {"evaluated": False, "approved": None, "reason": "verification_not_passed"}
        # The fallback attempt (verifier rejects it too) also carries an
        # explicit disposition in its event, emitted after verification.
        fallback = traces[-1]
        assert fallback["commit_event"] == "not_attempted"
        assert fallback["commit_reason"] == "verification_failed"
        assert fallback["verifier_verdict"]["passed"] is False


def test_hitl_require_records_not_attempted_with_approval_reason():
    require_gateway = ApprovalGateway(policy=lambda state: ApprovalLevel.REQUIRE, approver=None)
    harness, _ = make_harness("maximize_recon_surface", approval_gateway=require_gateway)
    with TemporaryDirectory() as directory:
        session = Session.create(source_ip="synthetic", session_dir=directory)
        result = harness.process(session, "ls -la")
        traces = serving_traces(session)
        assert result.error == "verified_serve_unavailable"
        attempt = traces[0]
        assert attempt["verifier_verdict"]["passed"] is True
        assert attempt["hitl_result"]["approved"] is False
        assert attempt["commit_event"] == "not_attempted"
        assert attempt["commit_reason"] == "approval_not_granted"
        # Fallback was also denied by HITL — disposition explicit, no silent serve.
        fallback = traces[-1]
        assert fallback["commit_event"] == "not_attempted"
        assert fallback["commit_reason"] == "approval_not_granted"
        assert result.deception_response == {}


def test_generator_commit_rejection_rolls_back_and_persists_rollback():
    host_path = None
    with TemporaryDirectory() as directory:
        host_path = str(Path(directory) / "host_fiction.json")
        harness, adapter = make_harness(
            "maximize_recon_surface", adapter=CommitRejectingAdapter("RAGIN_V4_SUBSTANTIVE_DETERMINISTIC"), host_fiction_path=host_path
        )
        session = Session.create(source_ip="synthetic", session_dir=directory)
        result = harness.process(session, "ls -la")
        traces = serving_traces(session)
        # Fail-safe: the rejected strategy candidate does NOT reach the
        # attacker; the verified fallback template serves instead.
        assert result.error is None
        assert result.deception_response["metadata"]["serving_outcome"] == "SAFE_FALLBACK_SERVED"
        attempt = traces[0]
        assert attempt["commit_event"] == "rejected"
        assert attempt["commit_reason"] == "generator_commit_rejected:synthetic_commit_rejected"
        assert attempt["commit_state_effect"] == "not_committed"
        assert attempt["commit_graph_before_sha256"] == attempt["commit_graph_after_sha256"]
        # Fiction graph rolled back: only the identity-seeded facts remain —
        # no fact carries an "accepted" source from the rejected candidate
        # (the fallback commit observes the template and adds no facts here).
        for fact in harness.fiction(session.session_id).facts():
            assert fact[3] != "accepted"
        # Generator-side pending/visit state fully discarded.
        assert adapter._generators[session.session_id].state.visits == 0
        assert not adapter._pending
        # The rollback was PERSISTED: at every point after the rejection the
        # on-disk host store matches the rolled-back in-memory store (a restart
        # cannot resurrect the rejected update).
        persisted = json.loads(Path(host_path).read_text())
        assert persisted == harness._host_store.to_dict()
        # Fallback attempt carries its own explicit, consistent disposition.
        fallback = traces[-1]
        assert fallback["commit_event"] == "accepted"
        assert fallback["commit_reason"] == "accepted_safe_fallback"
        assert_disposition_consistent(fallback)


def test_commit_exception_fails_closed_with_recorded_disposition():
    harness, adapter = make_harness("maximize_recon_surface", adapter=ExplodingCommitAdapter("RAGIN_V4_SUBSTANTIVE_DETERMINISTIC"))
    with TemporaryDirectory() as directory:
        session = Session.create(source_ip="synthetic", session_dir=directory)
        result = harness.process(session, "ls -la")
        traces = serving_traces(session)
        # FAIL CLOSED: a commit-time exception aborts the turn — nothing is
        # served, no fallback is attempted after a durability failure
        # (guards tests/security/test_task2_verified_serving.py::
        # test_persistence_failure_is_safe).
        assert result.error == "verified_serving_failed"
        assert result.response_text == ""
        # The attempt's evidence still reaches the serving trace: explicit
        # rejected disposition + rollback state hashes + verifier/HITL state.
        attempt = traces[0]
        assert len(traces) == 1  # aborted before any fallback attempt
        assert attempt["commit_event"] == "rejected"
        assert attempt["commit_reason"] == "commit_exception:RuntimeError"
        assert attempt["commit_state_effect"] == "not_committed"
        assert attempt["commit_graph_before_sha256"] == attempt["commit_graph_after_sha256"]  # rollback restored
        assert attempt["verifier_verdict"]["passed"] is True
        assert attempt["hitl_result"]["approved"] is True
        # Fiction graph rolled back: only identity-seeded facts remain.
        for fact in harness.fiction(session.session_id).facts():
            assert fact[3] != "accepted"
        # Generator never mutated by the exploded commit.
        assert adapter._generators[session.session_id].state.visits == 0


def test_every_attempt_in_multi_attempt_turn_has_a_disposition():
    """With retries, EVERY attempt trace (not just the last) carries a
    complete disposition record."""
    harness, _ = make_harness("maximize_recon_surface", verifier=RejectingVerifier())
    harness._max_retries = 1  # 2 generator attempts + 1 fallback
    with TemporaryDirectory() as directory:
        session = Session.create(source_ip="synthetic", session_dir=directory)
        result = harness.process(session, "ls -la")
        traces = serving_traces(session)
        assert result.error == "verified_serve_unavailable"
        assert len(traces) == 3  # two rejected attempts + fallback
        for trace in traces:
            assert trace["commit_event"] == "not_attempted"
            assert trace["commit_reason"] == "verification_failed"
            assert_disposition_consistent(trace)
