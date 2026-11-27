"""Regression tests for direct serve-path provenance.

Locks the S&P instrumentation contract: every finalized turn carries an
explicit ``serve_path`` label stamped by the node that produced the served
bytes — never inferred from latency.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ragin.cycle.graph import (  # noqa: E402
    SERVE_PATH_FALLBACK,
    SERVE_PATH_FASTPATH,
    SERVE_PATH_GENERATED_RETRY,
    SERVE_PATH_GENERATED_UNVERIFIED,
    SERVE_PATH_GENERATED_VERIFIED,
    DeceptionGraph,
)


class _PassVerifier:
    def verify(self, response, context):
        return {"passed": True, "issues": []}


class _FailThenPassVerifier:
    """Rejects the first draft of a session, accepts the retry."""

    def __init__(self):
        self.calls = 0

    def verify(self, response, context):
        self.calls += 1
        return {"passed": self.calls > 1, "issues": [] if self.calls > 1 else ["identity-pin: x"]}


class _FakeDeceiver:
    def generate_response(self, attacker_input, ctx):
        return {"response_text": "webapp@web-srv-01:~$ ok", "persona_used": "novice"}


def _run_turn(verifier, max_retries=1):
    graph = DeceptionGraph(
        deceiver=_FakeDeceiver(),
        verifier=verifier,
        max_retries=max_retries,
    )
    result = graph.invoke("prov-session", "whoami", {})
    resp = result.get("deception_response", {})
    return result, resp


def test_verified_draft_is_labeled_generated_verified():
    _, resp = _run_turn(_PassVerifier())
    assert resp.get("serve_path") == SERVE_PATH_GENERATED_VERIFIED


def test_retry_pass_is_labeled_generated_retry():
    result, resp = _run_turn(_FailThenPassVerifier(), max_retries=2)
    assert result["verification"]["passed"] is True
    assert resp.get("serve_path") == SERVE_PATH_GENERATED_RETRY


def test_exhausted_retries_serve_fallback_labeled():
    _, resp = _run_turn(_FailThenPassVerifier(), max_retries=1)
    # The fail-safe swap must never leave the failed LLM draft's label on the
    # served bytes.
    assert resp.get("serve_path") in (SERVE_PATH_FALLBACK, SERVE_PATH_FASTPATH)


def test_null_verifier_labels_unverified_not_verified():
    class _Null:
        def verify(self, response, context):
            # The baseline-arm shape: passes everything, performs NO
            # deterministic checks, and says so.
            return {"passed": True, "issues": [], "deterministic": False}

    graph = DeceptionGraph(deceiver=_FakeDeceiver(), verifier=_Null(), max_retries=0)
    result = graph.invoke("prov-session-null", "whoami", {})
    resp = result.get("deception_response", {})
    assert resp.get("serve_path") == SERVE_PATH_GENERATED_UNVERIFIED


def test_no_deceiver_is_fastpath_labeled():
    graph = DeceptionGraph(deceiver=None, verifier=_PassVerifier(), max_retries=0)
    result = graph.invoke("prov-session-nodec", "whoami", {})
    resp = result.get("deception_response", {})
    assert resp.get("serve_path") == SERVE_PATH_FASTPATH


# ---------------------------------------------------------------------------
# v2 reporter
# ---------------------------------------------------------------------------


def test_reporter_counts_labels_exactly(tmp_path):
    from scripts.serve_provenance_v2 import analyze_run

    artifact = {
        "per_row": [
            {"suite": "cti_technique", "serve_path": "GENERATED_VERIFIED", "response_time_ms": 5000},
            {"suite": "cti_technique", "serve_path": "FASTPATH_DETERMINISTIC", "response_time_ms": 100},
            {"suite": "CTI actor", "serve_path": "GENERATED_RETRY", "response_time_ms": 5200},
            {"suite": "Persona", "serve_path": "FALLBACK_VERIFIED", "response_time_ms": 9000},
            {"suite": "Persona"},  # uninstrumented row: UNKNOWN, never folded in
        ]
    }
    p = tmp_path / "run.json"
    p.write_text(__import__("json").dumps(artifact))
    report = analyze_run(p)
    assert report["total_rows"] == 5
    assert report["labeled_rows"] == 4
    tech = report["per_suite"]["cti_technique"]["counts"]
    assert tech == {"GENERATED_VERIFIED": 1, "FASTPATH_DETERMINISTIC": 1}
    # v1 latency rule would have misclassified the 9 s fallback as LLM:
    assert report["latency_cross_check"]["v1_disagreements"] == 1


def test_reporter_flags_unknown_rows(tmp_path):
    from scripts.serve_provenance_v2 import analyze_run

    artifact = {"per_row": [{"suite": "deception", "score": 0.5}]}
    p = tmp_path / "run.json"
    p.write_text(__import__("json").dumps(artifact))
    report = analyze_run(p)
    assert report["per_suite"]["deception"]["counts"] == {"UNKNOWN": 1}
