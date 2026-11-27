#!/usr/bin/env python3
"""Step 5 — working-system observability runner (plan: docs/PAPER_REMAINING_STEPS_2026-10-14.md).

Exercises the COMPLETE active serving path end to end:

    Chrollo classify -> Don evidence export (judge/filter) -> evidence gate
    -> V4 policy -> substantive generator -> mandatory verifier -> HITL
    -> fiction/host commit -> final serving (Harness + Sandbox)

and writes one JSONL record per attacker turn carrying the full required
evidence set: correlated request/session/turn/case/arm IDs, source/config
hashes, input/context hashes, retrieval query/corpus/document IDs, judge
identity and outputs, before/after policy-visible evidence, gate reason,
selected strategy, generator consumption, generated/served hashes,
verification/retries/fallback, approval, explicit commit disposition
(accepted/rejected/not_attempted with reason + state hashes), per-stage and
end-to-end latency, and provider/model identity with errors when applicable.

Phases:
  run    — execute the scenarios, write turn_records.jsonl + run_manifest.json
  audit  — verify evidence-field coverage + admissibility invariants
  freeze — write a sha256 manifest over all artifacts

Usage:
  python scripts/run_step5_working_system_observability_v1.py run \
      --out results/step5_working_system_observability_v1 --overwrite
  python scripts/run_step5_working_system_observability_v1.py audit \
      --out results/step5_working_system_observability_v1
  python scripts/run_step5_working_system_observability_v1.py freeze \
      --out results/step5_working_system_observability_v1

Scenarios (all 11 required, 13 cases / 18 turns):
  baseline_flags_off (x3, incl. one Sandbox serving-layer turn)
  supported_evidence, partial_only_evidence, irrelevant_evidence,
  conflicting_evidence, missing_provenance, model_timeout, malformed_output,
  verifier_rejection, hitl_require_no_approval, fallback_invalid_evidence,
  persistence_restart (x3 incl. restart), rejected_update_rollback
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import logging
import os
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Deterministic offline defaults for the runner process. Scenarios override
# the evidence-judge flags explicitly per case.
os.environ.setdefault("RAGIN_RAG_MODE", "offline")
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

from ragin.cycle.adapters import (  # noqa: E402
    ChrolloAdapter,
    DonAdapter,
    HisokaAdapter,
    SubstantiveStrategyAdapter,
)
from ragin.cycle.harness import Harness  # noqa: E402
from ragin.cycle.hitl import ApprovalGateway, ApprovalLevel  # noqa: E402
from ragin.cycle.sandbox import Sandbox, SandboxConfig  # noqa: E402
from ragin.cycle.session import EventType, Session  # noqa: E402
from ragin.decision_fusion_v4.evidence_export import sha256_json  # noqa: E402
from ragin.don.models import (  # noqa: E402
    ClassificationLabel,
    IntelDocument,
    MITRETactic,
    SeverityLevel,
    ThreatAnalysis,
)
from ragin.graph.host_fiction import HostFictionStore  # noqa: E402

PROTOCOL = "ragin.step5.working_system_observability.v1"
CLOSED_GATEWAY = "http://127.0.0.1:9"  # deterministic provider-unavailable port

SOURCE_FILES = [
    "ragin/cycle/harness.py",
    "ragin/cycle/adapters.py",
    "ragin/cycle/session.py",
    "ragin/cycle/sandbox.py",
    "ragin/cycle/verifier.py",
    "ragin/cycle/hitl.py",
    "ragin/cycle/graph.py",
    "ragin/decision_fusion_v4/evidence_export.py",
    "ragin/decision_fusion_v4/policy.py",
    "ragin/decision_fusion_v4/benchmark.py",
    "ragin/don/evidence_judge.py",
    "ragin/don/rag_engine.py",
    "ragin/don/models.py",
    "ragin/chrollo/classifier.py",
    "ragin/hisoka/deception.py",
    "ragin/hisoka/deceiver.py",
    "ragin/hisoka/strategy_generator_v1.py",
    "ragin/graph/fiction.py",
    "ragin/graph/host_fiction.py",
    "ragin/server_v2.py",
    "ragin/gateway/client.py",
    "scripts/run_step5_working_system_observability_v1.py",
]

ENV_KEYS = [
    "RAGIN_RAG_MODE",
    "RAGIN_EVIDENCE_JUDGE_ENABLED",
    "RAGIN_EVIDENCE_JUDGE_FILTERING_ENABLED",
    "RAGIN_PROVIDER_ENABLED",
    "RAGIN_PROVIDER_URL",
    "RAGIN_FAIL_CLOSED",
    "RAGIN_LAYA_ENABLED",
    "RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL",
    "RAGIN_HOST_KEY",
    "RAGIN_HOST_FICTION_POLICY",
    "RAGIN_DON_RETRIEVAL_VERSION",
    "RAGIN_RUNTIME_MODE",
    "GATEWAY_URL",
    "RAGIN_GATEWAY_URL",
]
SECRET_ENV_KEYS = ["OPENROUTER_API_KEY", "RAGIN_API_KEY", "RAGIN_PROVIDER_API_KEY"]

# Real-corpus files (baseline scenario retrieval corpus identity).
CORPUS_FILES = ["data/corpus/command_aware_v2.jsonl", "data/corpus/mitre_attack.jsonl"]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def sha256_obj(value: Any) -> str:
    try:
        return sha256_json(value)
    except (TypeError, ValueError):
        return sha256_text(json.dumps(value, sort_keys=True, default=str))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Component fixtures
# ─────────────────────────────────────────────────────────────────────────────


class ResultCapturingHarness(Harness):
    """Harness that exposes the last PipelineResult (for Sandbox turns)."""

    last_result: Any = None

    def process(self, session: Session, attacker_input: str):  # type: ignore[override]
        self.last_result = super().process(session, attacker_input)
        return self.last_result


class FixtureDonEngine:
    """Returns a crafted ThreatAnalysis so build_evidence_bundle (the REAL
    evidence-export + judge/filter path) runs on controlled documents."""

    def __init__(self, analysis: ThreatAnalysis) -> None:
        self._analysis = analysis

    def analyze(self, req: Any, session_log: Any) -> ThreatAnalysis:
        return self._analysis


class MalformedBundleDon:
    """CTI engine returning a malformed evidence bundle (gate input failure)."""

    def analyze(self, req: Any, session_log: Any) -> dict[str, Any]:
        return {"evidence_bundle": {"malformed": True}}


class TimeoutDeceiver:
    """Generator that always times out (model timeout where applicable)."""

    def generate_response(self, attacker_input: str, session_context: dict[str, Any]) -> dict[str, Any]:
        raise TimeoutError("synthetic model timeout")


class MalformedDeceiver:
    """Generator that returns a malformed candidate (no response_text) but
    reports strategy consumption honestly."""

    def generate_response(self, attacker_input: str, session_context: dict[str, Any]) -> dict[str, Any]:
        decision = session_context.get("policy_decision") if isinstance(session_context.get("policy_decision"), dict) else {}
        strategy = str(decision.get("selected_response_strategy", ""))
        return {
            "response_text": "",
            "metadata": {
                "selected_strategy": strategy,
                "strategy_delivered_to_generator": True,
                "strategy_consumed_by_template": True,
                "actual_generator_invocation": True,
                "candidate_response_sha256": sha256_text(""),
            },
        }


class CommitRejectingAdapter(SubstantiveStrategyAdapter):
    """Generator refuses the commit after verification+HITL pass: the pending
    proposal is discarded, generator state is never mutated, committed=False
    is reported so the harness must roll fiction + host back."""

    def commit_candidate(self, candidate: dict[str, Any], *, verifier_passed: bool, hitl_approved: bool) -> dict[str, Any]:
        metadata = candidate.get("metadata") if isinstance(candidate, dict) else None
        candidate_id = metadata.get("strategy_candidate_id") if isinstance(metadata, dict) else None
        if candidate_id:
            self._pending.pop(str(candidate_id), None)
        return {"committed": False, "reason": "synthetic_commit_rejected"}


class RejectingVerifier:
    """Verifier that rejects every candidate (used for the verifier-rejection
    scenario; applies to the fallback too -> no serve)."""

    def verify(self, response: dict[str, Any], session_context: dict[str, Any]) -> dict[str, Any]:
        return {"passed": False, "issues": ["synthetic_rejection"], "deterministic": True}


def require_no_approver_gateway() -> ApprovalGateway:
    """HITL policy REQUIRE with no approver -> approval_required, no commit."""
    return ApprovalGateway(policy=lambda state: ApprovalLevel.REQUIRE, approver=None)


def fixture_doc(
    doc_id: str,
    title: str,
    content: str,
    *,
    source: str = "step5-fixture-corpus",
    command_patterns: list[str] | None = None,
    behavior_tags: list[str] | None = None,
    provenance_status: str = "VALID",
) -> IntelDocument:
    metadata: dict[str, Any] = {
        "provenance_status": provenance_status,
        "sanitization_status": "SANITIZED",
        "conflict_status": "NONE",
    }
    if command_patterns is not None:
        metadata["command_patterns"] = command_patterns
    if behavior_tags is not None:
        metadata["behavior_tags"] = behavior_tags
    return IntelDocument(
        doc_id=doc_id,
        title=title,
        content=content,
        source=source,
        score=0.9,
        metadata=metadata,
    )


FIXTURE_RECON_DOC = fixture_doc(
    "step5-supported-1",
    "Directory listing reconnaissance behavior",
    "Adversaries run ls -la during reconnaissance to enumerate directory "
    "entries, permissions, owners, and hidden files on the target host. "
    "Observed in novice probing sessions before credential access attempts.",
    command_patterns=["ls -la"],
    behavior_tags=["directory_listing"],
)
FIXTURE_PARTIAL_DOC = fixture_doc(
    "step5-partial-1",
    "Shell workload monitoring notes",
    "Monitoring notes for shell workload activity in the environment; the ls "
    "utility output is retained for audit review by the operations team.",
    behavior_tags=["session_monitoring"],
)
FIXTURE_IRRELEVANT_DOC = fixture_doc(
    "step5-irrelevant-1",
    "Backup rotation policy",
    "Backup rotation policy for the monitoring platform; archives age out "
    "after thirty days according to the retention schedule.",
)
FIXTURE_CONTRADICTING_DOC = fixture_doc(
    "step5-conflicting-2",
    "Contradicting reconnaissance report",
    "This report contradicts the ls -la reconnaissance claim: the ls -la "
    "listing did not occur on this host according to the audit trail.",
    command_patterns=["ls -la"],
    behavior_tags=["directory_listing"],
)
FIXTURE_NO_PROVENANCE_DOC = fixture_doc(
    "step5-noprovenance-1",
    "Unattributed capture",
    "Unattributed capture of shell activity referencing ls -la output on an "
    "unknown source system.",
    source="",
    command_patterns=["ls -la"],
    behavior_tags=["directory_listing"],
    provenance_status="UNKNOWN",
)

RECON_TACTIC = MITRETactic(
    tactic_id="TA0043",
    tactic_name="Reconnaissance",
    confidence=0.9,
    techniques=["T1046"],
    sub_techniques=[],
)


def fixture_corpus_sha(docs: list[IntelDocument]) -> str:
    return sha256_obj([{"doc_id": d.doc_id, "title": d.title, "content": d.content, "source": d.source} for d in docs])


def fixture_analysis(analysis_id: str, docs: list[IntelDocument], *, query: str) -> ThreatAnalysis:
    corpus_sha = fixture_corpus_sha(docs)
    trace = {
        "query": query,
        "query_coverage": {"complete": True, "covered_terms": [], "required_terms": []},
        "implementation_version": "command_aware_v2_step5_fixture",
        "top_k": 10,
        "corpus_sha256": corpus_sha,
        "context_projection": {"preceding_commands": []},
        "cache_key": f"step5-fixture:{analysis_id}",
    }
    return ThreatAnalysis(
        analysis_id=analysis_id,
        session_id="step5fixture",
        classification=ClassificationLabel.MALICIOUS,
        severity=SeverityLevel.HIGH,
        confidence=0.93,
        tactics=[RECON_TACTIC],
        intel_documents=docs,
        raw_features={"command_aware_v2": {"retrieval_trace": trace}},
    )


def real_corpus_sha() -> dict[str, str]:
    out = {}
    for rel in CORPUS_FILES:
        path = REPO_ROOT / rel
        if path.exists():
            out[rel] = sha256_file(path)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Evidence-judge flag control (read per build_evidence_bundle call)
# ─────────────────────────────────────────────────────────────────────────────


@contextlib.contextmanager
def evidence_flags(*, judge: bool, filtering: bool):
    keys = {
        "RAGIN_EVIDENCE_JUDGE_ENABLED": "1" if judge else "0",
        "RAGIN_EVIDENCE_JUDGE_FILTERING_ENABLED": "1" if filtering else "0",
    }
    old = {k: os.environ.get(k) for k in keys}
    os.environ.update(keys)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ─────────────────────────────────────────────────────────────────────────────
# Expectation observation / matching
# ─────────────────────────────────────────────────────────────────────────────


def _observed(rec: dict[str, Any]) -> dict[str, Any]:
    pol = rec.get("policy") or {}
    srv = rec.get("serving") or {}
    attempts = srv.get("attempts") or [{}]
    first, last = attempts[0], attempts[-1]
    events = rec.get("events_index") or []
    sess = rec.get("session") or {}
    return {
        "policy_applied": pol.get("applied"),
        "gate_state": pol.get("gate_state"),
        "gate_reason": pol.get("gate_reason"),
        "strategy": pol.get("selected_response_strategy"),
        "served": srv.get("served"),
        "outcome": srv.get("outcome"),
        "consumed": any(a.get("strategy_consumed_by_template") is True for a in attempts),
        "error": rec.get("error"),
        "attempt0_commit": first.get("commit_event"),
        "attempt0_reason": first.get("commit_reason"),
        "attempt0_generation_error": first.get("generation_error") or None,
        "attempt_last_commit": last.get("commit_event"),
        "attempt_last_reason": last.get("commit_reason"),
        "served_commit": (rec.get("verification") or {}).get("commit_event") if srv.get("served") else None,
        "gateway_fallback": (rec.get("provider") or {}).get("gateway_fallback"),
        "serve_path": srv.get("serve_path"),
        "strategy_update_count": sum(1 for e in events if e.get("stage") == "strategy_update"),
        "attacker_inputs_after": sess.get("attacker_inputs_after"),
        "session_resumed": sess.get("session_resumed"),
        "judge_enabled": (rec.get("source_config") or {}).get("judge_enabled"),
        "persistence": rec.get("persistence"),
        "rollback": rec.get("rollback"),
    }


def _match(expected: Any, observed: Any) -> bool:
    if isinstance(expected, dict) and "$contains" in expected:
        return str(expected["$contains"]) in str(observed)
    if isinstance(expected, dict) and "$in" in expected:
        return observed in expected["$in"]
    if isinstance(expected, dict) and isinstance(observed, dict):
        return all(_match(v, observed.get(k)) for k, v in expected.items())
    return observed == expected


def evaluate_expectation(rec: dict[str, Any]) -> dict[str, Any]:
    expected = rec.get("expectation") or {}
    observed = _observed(rec)
    checks = {key: {"expected": exp, "observed": observed.get(key), "passed": _match(exp, observed.get(key))} for key, exp in expected.items()}
    return {"checks": checks, "passed": all(c["passed"] for c in checks.values())}


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────


class Step5Runner:
    def __init__(self, out: Path, *, overwrite: bool) -> None:
        self.out = out
        if out.exists() and overwrite:
            shutil.rmtree(out)
        if (out / "turn_records.jsonl").exists() and not overwrite:
            raise SystemExit("BLOCKED_OUTPUT_ALREADY_EXISTS: pass --overwrite to re-run into this directory")
        self.sessions_dir = out / "sessions"
        self.host_store_dir = out / "host_store"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.host_store_dir.mkdir(parents=True, exist_ok=True)
        self.records: list[dict[str, Any]] = []
        self.request_seq = 0
        self._chrollo: dict[str, ChrolloAdapter] = {}
        self._real_don: DonAdapter | None = None
        self.source_config_base = self._build_source_config_base()

    # -- shared components -------------------------------------------------
    def _build_source_config_base(self) -> dict[str, Any]:
        files = {}
        for rel in SOURCE_FILES:
            path = REPO_ROOT / rel
            files[rel] = sha256_file(path) if path.exists() else None
        env = {key: os.environ.get(key) for key in ENV_KEYS}
        env.update({key: ("<set>" if os.environ.get(key) else "") for key in SECRET_ENV_KEYS})
        git_head = os.popen(f"git -C {REPO_ROOT} rev-parse HEAD 2>/dev/null").read().strip() or None
        dirty = os.popen(f"git -C {REPO_ROOT} status --porcelain 2>/dev/null | wc -l").read().strip()
        return {
            "files": files,
            "env": env,
            "real_corpus_sha256": real_corpus_sha(),
            "git_head": git_head,
            "git_dirty_files": int(dirty) if dirty.isdigit() else None,
        }

    def get_chrollo(self, arm: str) -> ChrolloAdapter:
        if arm not in self._chrollo:
            self._chrollo[arm] = ChrolloAdapter(decision_arm=arm)
        return self._chrollo[arm]

    def get_real_don(self) -> DonAdapter:
        if self._real_don is None:
            self._real_don = DonAdapter(gateway_url=CLOSED_GATEWAY)
        return self._real_don

    # -- harness factory ---------------------------------------------------
    def make_harness(
        self,
        *,
        arm: str,
        cti_engine: Any,
        deceiver: Any,
        verifier: Any = None,
        approval_gateway: ApprovalGateway | None = None,
        host_fiction_path: str | None = None,
        host_store: HostFictionStore | None = None,
        component_identities: dict[str, Any],
        judge_enabled: bool,
        judge_filtering: bool,
        scenario_config: dict[str, Any] | None = None,
    ) -> ResultCapturingHarness:
        harness = ResultCapturingHarness(
            classifier=self.get_chrollo(arm),
            cti_engine=cti_engine,
            deceiver=deceiver,
            verifier=verifier,
            mandatory_verification=True,
            approval_gateway=approval_gateway,
            decision_arm=arm,
            host_fiction_path=host_fiction_path,
            host_store=host_store,
        )
        harness.component_identities = component_identities  # type: ignore[attr-defined]
        harness.judge_enabled = judge_enabled  # type: ignore[attr-defined]
        harness.judge_filtering = judge_filtering  # type: ignore[attr-defined]
        harness.scenario_config = scenario_config or {}  # type: ignore[attr-defined]
        return harness

    # -- turn execution ----------------------------------------------------
    def execute_turn(
        self,
        *,
        case_id: str,
        arm: str,
        turn_index: int,
        attacker_input: str,
        harness: ResultCapturingHarness,
        session: Session,
        expectation: dict[str, Any],
        sandbox: Sandbox | None = None,
        session_dir: Path | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.request_seq += 1
        request_id = f"req-{self.request_seq:04d}"
        events_before = len(session.replay())
        t_wall = time.perf_counter()
        sandbox_response = None
        if sandbox is not None:
            resp = sandbox.handle_command(
                (harness.scenario_config or {}).get("source_ip", "_"),
                attacker_input,
                session_id=session.session_id,
            )
            result = harness.last_result
            sandbox_response = {
                "session_id": resp.session_id,
                "serve_path": resp.serve_path,
                "candidate_sha256": resp.candidate_sha256,
                "approval": resp.approval,
                "processing_time_ms": resp.processing_time_ms,
                "command_count": resp.command_count,
                "status": resp.status,
                "error": resp.error,
            }
        else:
            result = harness.process(session, attacker_input)
        wall_ms = (time.perf_counter() - t_wall) * 1000.0

        all_events = session.replay()
        turn_events = all_events[events_before:]
        rec = self._build_record(
            request_id=request_id,
            case_id=case_id,
            arm=arm,
            turn_index=turn_index,
            attacker_input=attacker_input,
            harness=harness,
            session=session,
            all_events=all_events,
            turn_events=turn_events,
            result=result,
            expectation=expectation,
            wall_ms=wall_ms,
            sandbox_response=sandbox_response,
            extra=extra or {},
        )
        rec["expectation_result"] = evaluate_expectation(rec)
        status = "PASS" if rec["expectation_result"]["passed"] else "EXPECT-FAIL"
        failed = [k for k, c in rec["expectation_result"]["checks"].items() if not c["passed"]]
        print(f"[{status}] {case_id} turn {turn_index} ({request_id})"
              + (f" failed={failed}" if failed else f" served={rec['serving']['served']} gate={rec['policy'].get('gate_state')}"))
        if extra:
            print(f"         extra={json.dumps(extra, default=str)[:400]}")
        self.records.append(rec)
        return rec

    # -- record construction ------------------------------------------------
    def _build_record(
        self,
        *,
        request_id: str,
        case_id: str,
        arm: str,
        turn_index: int,
        attacker_input: str,
        harness: ResultCapturingHarness,
        session: Session,
        all_events: list,
        turn_events: list,
        result: Any,
        expectation: dict[str, Any],
        wall_ms: float,
        sandbox_response: dict[str, Any] | None,
        extra: dict[str, Any],
    ) -> dict[str, Any]:
        classification = result.classification or {}
        cti_payload = result.cti_analysis if isinstance(result.cti_analysis, dict) else {}
        bundle = cti_payload.get("evidence_bundle") if isinstance(cti_payload, dict) else None

        policy_events = [e for e in turn_events if e.event_type == EventType.STRATEGY_UPDATE]
        policy_applied = bool(policy_events)
        policy_event = policy_events[-1] if policy_events else None

        attempts = [
            e.data["serving_trace"]
            for e in turn_events
            if e.event_type == EventType.RESPONSE_GENERATE
            and isinstance(e.data, dict)
            and isinstance(e.data.get("serving_trace"), dict)
        ]

        metadata = result.deception_response.get("metadata") if isinstance(result.deception_response, dict) else {}
        metadata = metadata if isinstance(metadata, dict) else {}
        served = bool(result.error is None) and bool((result.deception_response or {}).get("response_text"))
        verification = dict(result.verification or {})
        approval = dict(result.approval or {})
        text = str((result.deception_response or {}).get("response_text", "") or "")

        # -- cti / retrieval / judge view ---------------------------------
        retrieval = (bundle or {}).get("retrieval") if isinstance(bundle, dict) else None
        retrieval = retrieval if isinstance(retrieval, dict) else {}
        documents = retrieval.get("documents") or []
        trace_summary = retrieval.get("trace_summary") or {}
        judge = (bundle or {}).get("evidence_judge") if isinstance(bundle, dict) else None
        judge_filter = (bundle or {}).get("evidence_judge_filter") if isinstance(bundle, dict) else None
        judge_enabled = bool(getattr(harness, "judge_enabled", False))
        if judge is not None:
            judgments = [
                {
                    "doc_id": j.get("doc_id"),
                    "label": j.get("label"),
                    "rationale_codes": j.get("rationale_codes"),
                    "provenance_sufficient": j.get("provenance_sufficient"),
                    "relates_to_command": j.get("relates_to_command"),
                    "substantively_supports_behavior": j.get("substantively_supports_behavior"),
                }
                for j in (judge.get("candidate_judgments") or [])
            ]
            judge_block = {
                "enabled": True,
                "judge_version": judge.get("judge_version"),
                "adapter_kind": judge.get("adapter_kind"),
                "trace_sha256": judge.get("trace_sha256"),
                "contract_version": judge.get("contract_version"),
                "command": judge.get("command"),
                "context_missing_or_ambiguous": judge.get("context_missing_or_ambiguous"),
                "sufficiency": judge.get("sufficiency"),
                "candidate_judgments": judgments,
            }
        else:
            judge_block = {
                "enabled": False,
                "reason": (
                    "evidence_judge_flags_off"
                    if not judge_enabled
                    else "evidence_judge_not_in_bundle_bundle_bypassed_export_path"
                ),
                "flags_at_run": {
                    "judge_enabled": judge_enabled,
                    "judge_filtering": bool(getattr(harness, "judge_filtering", False)),
                },
            }

        cti_block = {
            "error": cti_payload.get("error") or None,
            "analysis_id": cti_payload.get("analysis_id"),
            "severity": cti_payload.get("severity"),
            "don_classification": cti_payload.get("classification"),
            "ttps_seen": cti_payload.get("ttps_seen"),
            "extracted_techniques": cti_payload.get("extracted_techniques"),
            "bundle_sha256": sha256_json(bundle) if isinstance(bundle, dict) else None,
            "evidence_bundle": bundle,
            "retrieval": {
                "query": retrieval.get("query"),
                "backend": retrieval.get("backend"),
                "implementation_version": retrieval.get("implementation_version"),
                "corpus_sha256": trace_summary.get("corpus_sha256"),
                "retrieval_status": retrieval.get("retrieval_status"),
                "retrieved_count": retrieval.get("retrieved_count"),
                "relevant_count": retrieval.get("relevant_count"),
                "relevant_doc_ids": retrieval.get("relevant_doc_ids"),
                "query_coverage": retrieval.get("query_coverage"),
                "document_ids": [d.get("doc_id") for d in documents if isinstance(d, dict)],
                "documents_meta": [
                    {
                        "doc_id": d.get("doc_id"),
                        "source": d.get("source"),
                        "provenance_status": d.get("provenance_status"),
                        "sanitization_status": d.get("sanitization_status"),
                        "conflict_status": d.get("conflict_status"),
                    }
                    for d in documents
                    if isinstance(d, dict)
                ],
            },
            "judge": judge_block,
            "judge_filter": judge_filter,
            "gate_preview": (bundle or {}).get("evidence_gate_preview") if isinstance(bundle, dict) else None,
        }

        # -- policy ---------------------------------------------------------
        if policy_applied and isinstance(policy_event.data, dict):
            policy_block = {"applied": True, **policy_event.data, "event_id": policy_event.event_id}
        else:
            policy_block = {
                "applied": False,
                "reason": "RAGIN_BASELINE_arm_policy_stage_not_in_path",
                "gate_state": None,
                "gate_reason": None,
                "selected_response_strategy": None,
            }

        # -- policy-visible evidence before/after ---------------------------
        if policy_applied and isinstance(bundle, dict):
            before = None
            basis = None
            if isinstance(judge_filter, dict):
                before = list(judge_filter.get("original_relevant_doc_ids") or [])
                basis = "judge_filter_original_relevant_doc_ids"
            elif retrieval:
                before = list(retrieval.get("relevant_doc_ids") or [])
                basis = "retrieval_relevant_doc_ids_unfiltered"
            else:
                before = []
                basis = "bundle_missing_retrieval_section"
            after = list(policy_block.get("valid_doc_ids") or [])
            policy_visible = {
                "applied": True,
                "before": before,
                "after": after,
                "basis": basis,
                "judge_filter_visible": list(judge_filter.get("gate_policy_visible_evidence_ids") or []) if isinstance(judge_filter, dict) else None,
            }
        elif policy_applied:
            policy_visible = {"applied": True, "before": [], "after": [], "basis": "bundle_missing", "judge_filter_visible": None}
        else:
            policy_visible = {
                "applied": False,
                "before": None,
                "after": None,
                "reason": "RAGIN_BASELINE_arm_no_policy_visible_evidence_stage",
            }

        # -- serving ---------------------------------------------------------
        stage = metadata.get("serving_outcome")
        if stage is None and attempts:
            stage = attempts[-1].get("outcome")
        served_attempt = next(
            (a for a in attempts if a.get("commit_event") == "accepted"),
            None,
        )
        candidate_hash = metadata.get("candidate_response_sha256") or (served_attempt or {}).get("candidate_response_sha256")
        if candidate_hash is None and attempts:
            candidate_hash = attempts[0].get("candidate_response_sha256")
        fallback_used = stage in {"SAFE_FALLBACK_SERVED", "GENERATION_NOT_APPLICABLE"}
        serving_block = {
            "served": served,
            "response_text": text,
            "response_sha256": sha256_text(text) if text else None,
            "outcome": stage,
            "serve_path": verification.get("serve_path") or (sandbox_response or {}).get("serve_path"),
            "candidate_response_sha256": candidate_hash,
            "served_response_sha256": metadata.get("served_response_sha256"),
            "attempt_count": len(attempts),
            "retries": max(0, len(attempts) - 1),
            "fallback_used": fallback_used,
            "fallback_reason": metadata.get("fallback_reason") or (attempts[-1].get("fallback_reason") if attempts and attempts[-1].get("fallback_reason") not in (None, "NOT_VERIFIABLE") else None),
            "attempts": attempts,
            "sandbox_response": sandbox_response,
        }

        # -- provider / model identity ---------------------------------------
        provider_block = {
            "components": (harness.component_identities or {}),  # type: ignore[attr-defined]
            "gateway_url": (harness.scenario_config or {}).get("gateway_url"),  # type: ignore[attr-defined]
            "gateway_fallback": metadata.get("gateway_fallback"),
            "template_id": metadata.get("template_id"),
            "template_fallback_reason": metadata.get("template_fallback_reason"),
            "template_anchored": metadata.get("template_anchored"),
            "generator_version": metadata.get("generator_version"),
            "runtime_mode": metadata.get("runtime_mode"),
            "strategy_source": metadata.get("strategy_source"),
            "errors": {
                "classification": classification.get("error") or None,
                "cti": cti_payload.get("error") or None,
                "generation": [a.get("generation_error") for a in attempts if a.get("generation_error")],
                "pipeline": result.error,
            },
        }

        # -- latency -----------------------------------------------------------
        stages = []
        prev_ts = None
        for e in turn_events:
            ts = e.timestamp
            delta = round((ts - prev_ts).total_seconds() * 1000.0, 3) if prev_ts else None
            stages.append(
                {
                    "event_id": e.event_id,
                    "stage": e.event_type.value,
                    "source": e.source,
                    "at": ts.isoformat(),
                    "since_prev_ms": delta,
                }
            )
            prev_ts = ts
        latency = {
            "end_to_end_ms": round(float(result.total_time_ms), 3),
            "wall_ms": round(wall_ms, 3),
            "sandbox_processing_time_ms": (sandbox_response or {}).get("processing_time_ms"),
            "policy_latency_ms": policy_block.get("latency_ms") if policy_applied else None,
            "stages": stages,
        }

        # -- hashes / session ---------------------------------------------------
        try:
            context_sha = sha256_json({"classification": classification, "cti_analysis": cti_payload})
        except (TypeError, ValueError):
            context_sha = sha256_text(json.dumps({"classification": classification, "cti_analysis": cti_payload}, sort_keys=True, default=str))

        resumed = any(e.event_type == EventType.SESSION_RESUME for e in turn_events)
        session_block = {
            "session_id": session.session_id,
            "session_dir": str(session_dir_of(session)),
            "event_count_after": len(all_events),
            "attacker_inputs_after": sum(1 for e in all_events if e.event_type == EventType.ATTACKER_INPUT),
            "session_resumed": resumed,
        }

        source_config = {
            **self.source_config_base,
            "judge_enabled": judge_enabled,
            "judge_filtering": bool(getattr(harness, "judge_filtering", False)),
            "mandatory_verification": bool(harness.mandatory_verification),
            "max_retries": harness._max_retries,  # noqa: SLF001
            "verifier": type(harness._verifier).__name__ if harness._verifier else None,  # noqa: SLF001
            "approval_gateway_policy": type(harness._approval_gateway._policy).__name__,  # noqa: SLF001
            "scenario_config": (harness.scenario_config or {}),  # type: ignore[attr-defined]
        }

        record = {
            "protocol": PROTOCOL,
            "recorded_at": now_iso(),
            "request_id": request_id,
            "case_id": case_id,
            "arm": arm,
            "turn_index": turn_index,
            "session": session_block,
            "attacker_input": attacker_input,
            "input_sha256": sha256_text(attacker_input),
            "context_sha256": context_sha,
            "source_config": source_config,
            "classification": classification,
            "cti": cti_block,
            "policy": policy_block,
            "policy_visible_evidence": policy_visible,
            "serving": serving_block,
            "verification": verification,
            "approval": approval,
            "provider": provider_block,
            "latency": latency,
            "events_emitted": result.events_emitted,
            "events_index": [
                {"event_id": e.event_id, "stage": e.event_type.value, "source": e.source, "at": e.timestamp.isoformat()}
                for e in turn_events
            ],
            "error": result.error,
            "expectation": expectation,
        }
        record.update(extra)
        return record


def session_dir_of(session: Session) -> Path:
    return session._dir  # noqa: SLF001


# ─────────────────────────────────────────────────────────────────────────────
# Scenarios
# ─────────────────────────────────────────────────────────────────────────────


def scenario_baseline_flags_off(runner: Step5Runner) -> None:
    case = "baseline_flags_off"
    arm = "RAGIN_BASELINE"
    with evidence_flags(judge=False, filtering=False):
        deceiver = HisokaAdapter(gateway_url=CLOSED_GATEWAY)
        harness = runner.make_harness(
            arm=arm,
            cti_engine=runner.get_real_don(),
            deceiver=deceiver,
            component_identities={
                "classifier": "ChrolloAdapter/ChrolloClassifier",
                "cti": "DonAdapter/ThreatRAGEngine(offline)",
                "deceiver": "HisokaAdapter/AdaptiveDeceiver(gateway unreachable)",
            },
            judge_enabled=False,
            judge_filtering=False,
            scenario_config={"source_ip": "198.51.100.10", "gateway_url": CLOSED_GATEWAY, "flags": "all_off"},
        )
        session_dir = runner.sessions_dir / case
        session = Session.create(source_ip="198.51.100.10", session_dir=session_dir)
        expect = {
            "policy_applied": False,
            "served": True,
            "gateway_fallback": True,
            "serve_path": {"$contains": "TEMPLATE_FALLBACK"},
            "strategy_update_count": 0,
            "judge_enabled": False,
            "attempt0_commit": "accepted",
            "error": None,
        }
        runner.execute_turn(
            case_id=case, arm=arm, turn_index=1, attacker_input="ls -la",
            harness=harness, session=session, expectation=expect,
        )
        runner.execute_turn(
            case_id=case, arm=arm, turn_index=2, attacker_input="whoami",
            harness=harness, session=session, expectation=expect,
        )
        # Serving-layer turn through the Sandbox (final serving surface).
        sandbox = Sandbox(harness=harness, config=SandboxConfig(session_dir=str(session_dir), source_ip="198.51.100.10"))
        runner.execute_turn(
            case_id=case, arm=arm, turn_index=3, attacker_input="uname -a",
            harness=harness, session=session, expectation=expect, sandbox=sandbox, session_dir=session_dir,
        )


def _v4_harness(runner: Step5Runner, *, analysis: ThreatAnalysis | None = None, **kwargs: Any) -> ResultCapturingHarness:
    arm = "RAGIN_V4_DETERMINISTIC"
    deceiver = kwargs.pop("deceiver", None) or SubstantiveStrategyAdapter("RAGIN_V4_SUBSTANTIVE_DETERMINISTIC")
    cti_engine = kwargs.pop("cti_engine", None) or DonAdapter(engine=FixtureDonEngine(analysis))
    identities = kwargs.pop(
        "component_identities",
        {
            "classifier": "ChrolloAdapter/ChrolloClassifier",
            "cti": "DonAdapter/FixtureDonEngine(real build_evidence_bundle export path)",
            "deceiver": type(deceiver).__name__,
        },
    )
    return runner.make_harness(arm=arm, cti_engine=cti_engine, deceiver=deceiver, component_identities=identities, **kwargs)


def scenario_supported_evidence(runner: Step5Runner) -> None:
    case = "supported_evidence"
    arm = "RAGIN_V4_DETERMINISTIC"
    analysis = fixture_analysis("step5-supported", [FIXTURE_RECON_DOC], query="novice ls -la")
    with evidence_flags(judge=True, filtering=True):
        harness = _v4_harness(
            runner, analysis=analysis,
            judge_enabled=True, judge_filtering=True,
            scenario_config={"flags": "judge+filter_on", "condition": "supported_evidence"},
        )
        session = Session.create(source_ip="198.51.100.20", session_dir=runner.sessions_dir / case)
        runner.execute_turn(
            case_id=case, arm=arm, turn_index=1, attacker_input="ls -la",
            harness=harness, session=session,
            expectation={
                "policy_applied": True,
                "gate_state": "VALID_EVIDENCE",
                "gate_reason": "validated_bundle",
                "strategy": "maximize_recon_surface",
                "served": True,
                "outcome": "STRATEGY_CONSUMED_AND_SERVED",
                "consumed": True,
                "attempt0_commit": "accepted",
                "served_commit": "accepted",
                "strategy_update_count": 1,
                "judge_enabled": True,
                "error": None,
            },
        )


def scenario_partial_only_evidence(runner: Step5Runner) -> None:
    case = "partial_only_evidence"
    arm = "RAGIN_V4_DETERMINISTIC"
    analysis = fixture_analysis("step5-partial", [FIXTURE_PARTIAL_DOC], query="novice ls -la")
    with evidence_flags(judge=True, filtering=False):
        harness = _v4_harness(
            runner, analysis=analysis,
            judge_enabled=True, judge_filtering=False,
            scenario_config={"flags": "judge_on_filter_off", "condition": "partial_only_evidence"},
        )
        session = Session.create(source_ip="198.51.100.21", session_dir=runner.sessions_dir / case)
        runner.execute_turn(
            case_id=case, arm=arm, turn_index=1, attacker_input="ls -la",
            harness=harness, session=session,
            expectation={
                "policy_applied": True,
                "gate_state": "LOW_RELEVANCE",
                "gate_reason": "evidence_judge_insufficient",
                "strategy": "baseline",
                "served": True,
                "outcome": "GENERATION_NOT_APPLICABLE",
                "consumed": False,
                "attempt0_commit": "accepted",
                "judge_enabled": True,
                "error": None,
            },
        )


def scenario_irrelevant_evidence(runner: Step5Runner) -> None:
    case = "irrelevant_evidence"
    arm = "RAGIN_V4_DETERMINISTIC"
    analysis = fixture_analysis("step5-irrelevant", [FIXTURE_IRRELEVANT_DOC], query="novice ls -la")
    with evidence_flags(judge=True, filtering=True):
        harness = _v4_harness(
            runner, analysis=analysis,
            judge_enabled=True, judge_filtering=True,
            scenario_config={"flags": "judge+filter_on", "condition": "irrelevant_evidence"},
        )
        session = Session.create(source_ip="198.51.100.22", session_dir=runner.sessions_dir / case)
        runner.execute_turn(
            case_id=case, arm=arm, turn_index=1, attacker_input="ls -la",
            harness=harness, session=session,
            expectation={
                "policy_applied": True,
                "gate_state": "NO_EVIDENCE",
                "gate_reason": "no_relevant_documents",
                "strategy": "baseline",
                "served": True,
                "outcome": "GENERATION_NOT_APPLICABLE",
                "consumed": False,
                "attempt0_commit": "accepted",
                "error": None,
            },
        )


def scenario_conflicting_evidence(runner: Step5Runner) -> None:
    case = "conflicting_evidence"
    arm = "RAGIN_V4_DETERMINISTIC"
    analysis = fixture_analysis(
        "step5-conflicting", [FIXTURE_RECON_DOC, FIXTURE_CONTRADICTING_DOC], query="novice ls -la"
    )
    with evidence_flags(judge=True, filtering=True):
        harness = _v4_harness(
            runner, analysis=analysis,
            judge_enabled=True, judge_filtering=True,
            scenario_config={"flags": "judge+filter_on", "condition": "conflicting_evidence"},
        )
        session = Session.create(source_ip="198.51.100.23", session_dir=runner.sessions_dir / case)
        runner.execute_turn(
            case_id=case, arm=arm, turn_index=1, attacker_input="ls -la",
            harness=harness, session=session,
            expectation={
                "policy_applied": True,
                "gate_state": "UNRESOLVED_CONFLICT",
                "gate_reason": "evidence_judge_filter_conflicting",
                "strategy": "baseline",
                "served": True,
                "outcome": "GENERATION_NOT_APPLICABLE",
                "consumed": False,
                "attempt0_commit": "accepted",
                "error": None,
            },
        )


def scenario_missing_provenance(runner: Step5Runner) -> None:
    case = "missing_provenance"
    arm = "RAGIN_V4_DETERMINISTIC"
    analysis = fixture_analysis("step5-noprovenance", [FIXTURE_NO_PROVENANCE_DOC], query="novice ls -la")
    with evidence_flags(judge=True, filtering=True):
        harness = _v4_harness(
            runner, analysis=analysis,
            judge_enabled=True, judge_filtering=True,
            scenario_config={"flags": "judge+filter_on", "condition": "missing_provenance"},
        )
        session = Session.create(source_ip="198.51.100.24", session_dir=runner.sessions_dir / case)
        runner.execute_turn(
            case_id=case, arm=arm, turn_index=1, attacker_input="ls -la",
            harness=harness, session=session,
            expectation={
                "policy_applied": True,
                "gate_state": "INVALID_PROVENANCE",
                "gate_reason": "invalid_or_unknown_provenance",
                "strategy": "baseline",
                "served": True,
                "outcome": "GENERATION_NOT_APPLICABLE",
                "consumed": False,
                "attempt0_commit": "accepted",
                "error": None,
            },
        )


def scenario_model_timeout(runner: Step5Runner) -> None:
    case = "model_timeout"
    arm = "RAGIN_V4_DETERMINISTIC"
    analysis = fixture_analysis("step5-timeout", [FIXTURE_RECON_DOC], query="novice ls -la")
    with evidence_flags(judge=True, filtering=True):
        harness = _v4_harness(
            runner, analysis=analysis, deceiver=TimeoutDeceiver(),
            judge_enabled=True, judge_filtering=True,
            component_identities={
                "classifier": "ChrolloAdapter/ChrolloClassifier",
                "cti": "DonAdapter/FixtureDonEngine(real build_evidence_bundle export path)",
                "deceiver": "TimeoutDeceiver(raises TimeoutError on generate)",
            },
            scenario_config={"flags": "judge+filter_on", "condition": "model_timeout"},
        )
        session = Session.create(source_ip="198.51.100.25", session_dir=runner.sessions_dir / case)
        runner.execute_turn(
            case_id=case, arm=arm, turn_index=1, attacker_input="ls -la",
            harness=harness, session=session,
            expectation={
                "policy_applied": True,
                "gate_state": "VALID_EVIDENCE",
                "served": True,
                "outcome": "SAFE_FALLBACK_SERVED",
                "attempt0_commit": "not_attempted",
                "attempt0_reason": {"$contains": "generation_failed"},
                "attempt0_generation_error": "generator_exception:TimeoutError",
                "attempt_last_commit": "accepted",
                "error": None,
            },
        )


def scenario_malformed_output(runner: Step5Runner) -> None:
    case = "malformed_output"
    arm = "RAGIN_V4_DETERMINISTIC"
    analysis = fixture_analysis("step5-malformed", [FIXTURE_RECON_DOC], query="novice ls -la")
    with evidence_flags(judge=True, filtering=True):
        harness = _v4_harness(
            runner, analysis=analysis, deceiver=MalformedDeceiver(),
            judge_enabled=True, judge_filtering=True,
            component_identities={
                "classifier": "ChrolloAdapter/ChrolloClassifier",
                "cti": "DonAdapter/FixtureDonEngine(real build_evidence_bundle export path)",
                "deceiver": "MalformedDeceiver(returns candidate without response_text)",
            },
            scenario_config={"flags": "judge+filter_on", "condition": "malformed_output"},
        )
        session = Session.create(source_ip="198.51.100.26", session_dir=runner.sessions_dir / case)
        runner.execute_turn(
            case_id=case, arm=arm, turn_index=1, attacker_input="ls -la",
            harness=harness, session=session,
            expectation={
                "policy_applied": True,
                "gate_state": "VALID_EVIDENCE",
                "served": True,
                "outcome": "SAFE_FALLBACK_SERVED",
                "consumed": True,
                "attempt0_commit": "not_attempted",
                "attempt0_reason": "verification_failed",
                "attempt_last_commit": "accepted",
                "error": None,
            },
        )


def scenario_verifier_rejection(runner: Step5Runner) -> None:
    case = "verifier_rejection"
    arm = "RAGIN_V4_DETERMINISTIC"
    analysis = fixture_analysis("step5-verifier-reject", [FIXTURE_RECON_DOC], query="novice ls -la")
    with evidence_flags(judge=True, filtering=True):
        harness = _v4_harness(
            runner, analysis=analysis, verifier=RejectingVerifier(),
            judge_enabled=True, judge_filtering=True,
            component_identities={
                "classifier": "ChrolloAdapter/ChrolloClassifier",
                "cti": "DonAdapter/FixtureDonEngine(real build_evidence_bundle export path)",
                "deceiver": "SubstantiveStrategyAdapter",
                "verifier": "RejectingVerifier(rejects every candidate incl. fallback)",
            },
            scenario_config={"flags": "judge+filter_on", "condition": "verifier_rejection"},
        )
        session = Session.create(source_ip="198.51.100.27", session_dir=runner.sessions_dir / case)
        runner.execute_turn(
            case_id=case, arm=arm, turn_index=1, attacker_input="ls -la",
            harness=harness, session=session,
            expectation={
                "policy_applied": True,
                "gate_state": "VALID_EVIDENCE",
                "served": False,
                "error": "verified_serve_unavailable",
                "consumed": True,
                "attempt0_commit": "not_attempted",
                "attempt0_reason": "verification_failed",
                "attempt_last_commit": "not_attempted",
                "attempt_last_reason": "verification_failed",
            },
        )


def scenario_hitl_require_no_approval(runner: Step5Runner) -> None:
    case = "hitl_require_no_approval"
    arm = "RAGIN_V4_DETERMINISTIC"
    analysis = fixture_analysis("step5-hitl-require", [FIXTURE_RECON_DOC], query="novice ls -la")
    with evidence_flags(judge=True, filtering=True):
        harness = _v4_harness(
            runner, analysis=analysis, approval_gateway=require_no_approver_gateway(),
            judge_enabled=True, judge_filtering=True,
            component_identities={
                "classifier": "ChrolloAdapter/ChrolloClassifier",
                "cti": "DonAdapter/FixtureDonEngine(real build_evidence_bundle export path)",
                "deceiver": "SubstantiveStrategyAdapter",
                "approval": "ApprovalGateway(policy=REQUIRE, approver=None)",
            },
            scenario_config={"flags": "judge+filter_on", "condition": "hitl_require_without_approval"},
        )
        session = Session.create(source_ip="198.51.100.28", session_dir=runner.sessions_dir / case)
        runner.execute_turn(
            case_id=case, arm=arm, turn_index=1, attacker_input="ls -la",
            harness=harness, session=session,
            expectation={
                "policy_applied": True,
                "gate_state": "VALID_EVIDENCE",
                "served": False,
                "error": "verified_serve_unavailable",
                "consumed": True,
                "attempt0_commit": "not_attempted",
                "attempt0_reason": "approval_not_granted",
                "attempt_last_commit": "not_attempted",
                "attempt_last_reason": "approval_not_granted",
            },
        )


def scenario_fallback_invalid_evidence(runner: Step5Runner) -> None:
    case = "fallback_invalid_evidence"
    arm = "RAGIN_V4_DETERMINISTIC"
    with evidence_flags(judge=True, filtering=True):
        harness = _v4_harness(
            runner, cti_engine=MalformedBundleDon(),
            judge_enabled=True, judge_filtering=True,
            component_identities={
                "classifier": "ChrolloAdapter/ChrolloClassifier",
                "cti": "MalformedBundleDon(returns {malformed: True} bundle)",
                "deceiver": "SubstantiveStrategyAdapter",
            },
            scenario_config={"flags": "judge+filter_on", "condition": "fallback_invalid_evidence"},
        )
        session = Session.create(source_ip="198.51.100.29", session_dir=runner.sessions_dir / case)
        runner.execute_turn(
            case_id=case, arm=arm, turn_index=1, attacker_input="ls -la",
            harness=harness, session=session,
            expectation={
                "policy_applied": True,
                "gate_state": "RETRIEVAL_FAILURE",
                "gate_reason": "malformed_bundle",
                "strategy": "baseline",
                "served": True,
                "outcome": "GENERATION_NOT_APPLICABLE",
                "consumed": False,
                "attempt0_commit": "accepted",
                "error": None,
            },
        )


def scenario_persistence_restart(runner: Step5Runner) -> None:
    case = "persistence_restart"
    arm = "RAGIN_V4_DETERMINISTIC"
    analysis = fixture_analysis("step5-persistence", [FIXTURE_RECON_DOC], query="novice ls -la")
    session_dir = runner.sessions_dir / case
    host_path = runner.host_store_dir / f"{case}_host_fiction.json"
    base_expect = {
        "policy_applied": True,
        "gate_state": "VALID_EVIDENCE",
        "served": True,
        "outcome": "STRATEGY_CONSUMED_AND_SERVED",
        "consumed": True,
        "attempt0_commit": "accepted",
        "served_commit": "accepted",
        "error": None,
    }
    with evidence_flags(judge=True, filtering=True):
        # Phase A: two turns on harness instance 1 (writes session log +
        # host fiction file).
        harness1 = _v4_harness(
            runner, analysis=analysis,
            judge_enabled=True, judge_filtering=True,
            host_fiction_path=str(host_path),
            scenario_config={"flags": "judge+filter_on", "condition": "persistence_phase_a"},
        )
        session = Session.create(source_ip="198.51.100.30", session_dir=session_dir)
        runner.execute_turn(
            case_id=case, arm=arm, turn_index=1, attacker_input="ls -la",
            harness=harness1, session=session, expectation=base_expect,
        )
        runner.execute_turn(
            case_id=case, arm=arm, turn_index=2, attacker_input="ls -la",
            harness=harness1, session=session, expectation=base_expect,
        )
        pinned_before = harness1._host_store.pinned_identity  # noqa: SLF001
        host_facts_before = len(harness1._host_store._host_facts)  # noqa: SLF001
        # Phase B: RESTART — new store (loaded from disk), new harness
        # instance, new sandbox: the session is resumed from its durable log.
        store2 = HostFictionStore.load(host_path)
        harness2 = _v4_harness(
            runner, analysis=analysis,
            judge_enabled=True, judge_filtering=True,
            host_store=store2, host_fiction_path=str(host_path),
            scenario_config={"flags": "judge+filter_on", "condition": "persistence_phase_b_restart"},
        )
        sandbox = Sandbox(harness=harness2, config=SandboxConfig(session_dir=str(session_dir), source_ip="198.51.100.30"))
        rec3 = runner.execute_turn(
            case_id=case, arm=arm, turn_index=3, attacker_input="ls -la",
            harness=harness2, session=session, expectation={
                **base_expect,
                "session_resumed": True,
                "attacker_inputs_after": 3,
            },
            sandbox=sandbox, session_dir=session_dir,
        )
        pinned_after = store2.pinned_identity
        host_facts_after = len(store2._host_facts)  # noqa: SLF001
        rec3["persistence"] = {
            "restarted": True,
            "session_resume_event_in_turn": rec3["session"]["session_resumed"],
            "attacker_inputs_after": rec3["session"]["attacker_inputs_after"],
            "pinned_identity_before_restart": pinned_before,
            "pinned_identity_after_restart": pinned_after,
            "identity_stable": pinned_before == pinned_after and pinned_before is not None,
            "host_facts_before_restart": host_facts_before,
            "host_facts_after_restart": host_facts_after,
            "host_facts_preserved": host_facts_after >= host_facts_before and host_facts_before >= 0,
            "host_store_sha256": sha256_file(host_path) if host_path.exists() else None,
            "session_log_sha256": sha256_file(session._log_path),  # noqa: SLF001
            "notes": (
                "Durable across restart: session event log, pinned host identity, "
                "promoted host facts, verified-session flags. Per-session fiction "
                "graphs and generator state are in-memory by design (fresh graph "
                "after restart under policy=per_session)."
            ),
        }
        # Re-evaluate expectation now that the persistence block exists.
        rec3["expectation_result"] = evaluate_expectation(rec3)
        ok = rec3["expectation_result"]["passed"]
        print(f"[{'PASS' if ok else 'EXPECT-FAIL'}] {case} turn 3 persistence re-check "
              + json.dumps(rec3["persistence"], default=str)[:300])


def scenario_rejected_update_rollback(runner: Step5Runner) -> None:
    case = "rejected_update_rollback"
    arm = "RAGIN_V4_DETERMINISTIC"
    analysis = fixture_analysis("step5-rollback", [FIXTURE_RECON_DOC], query="novice ls -la")
    host_path = runner.host_store_dir / f"{case}_host_fiction.json"
    with evidence_flags(judge=True, filtering=True):
        harness = _v4_harness(
            runner, analysis=analysis, deceiver=CommitRejectingAdapter("RAGIN_V4_SUBSTANTIVE_DETERMINISTIC"),
            judge_enabled=True, judge_filtering=True,
            host_fiction_path=str(host_path),
            component_identities={
                "classifier": "ChrolloAdapter/ChrolloClassifier",
                "cti": "DonAdapter/FixtureDonEngine(real build_evidence_bundle export path)",
                "deceiver": "CommitRejectingAdapter(generator refuses commit; pending discarded, state untouched)",
            },
            scenario_config={"flags": "judge+filter_on", "condition": "rejected_update_rollback"},
        )
        session = Session.create(source_ip="198.51.100.31", session_dir=runner.sessions_dir / case)
        rec = runner.execute_turn(
            case_id=case, arm=arm, turn_index=1, attacker_input="ls -la",
            harness=harness, session=session,
            expectation={
                "policy_applied": True,
                "gate_state": "VALID_EVIDENCE",
                "served": True,
                "outcome": "SAFE_FALLBACK_SERVED",
                "attempt0_commit": "rejected",
                "attempt0_reason": "generator_commit_rejected:synthetic_commit_rejected",
                "attempt_last_commit": "accepted",
                "error": None,
            },
        )
        attempt0 = rec["serving"]["attempts"][0]
        persisted = json.loads(host_path.read_text())
        rec["rollback"] = {
            "commit0_before_after_equal": attempt0.get("commit_graph_before_sha256") == attempt0.get("commit_graph_after_sha256"),
            "commit0_state_effect": attempt0.get("commit_state_effect"),
            "generator_visits": harness._deceiver._generators[session.session_id].state.visits,  # noqa: SLF001
            "pending_candidates": len(harness._deceiver._pending),  # noqa: SLF001
            "host_file_matches_memory": persisted == harness._host_store.to_dict(),  # noqa: SLF001
            "host_store_sha256": sha256_file(host_path) if host_path.exists() else None,
            "notes": (
                "Rejected generator commit -> fiction graph restored (before==after), "
                "host store restored AND re-persisted to disk, pending proposal "
                "discarded, generator state never mutated (visits==0); the turn "
                "fail-safes to the verified fallback template."
            ),
        }
        rec["expectation_result"] = evaluate_expectation(rec)
        ok = rec["expectation_result"]["passed"]
        print(f"[{'PASS' if ok else 'EXPECT-FAIL'}] {case} rollback re-check " + json.dumps(rec["rollback"], default=str)[:300])


SCENARIOS = [
    scenario_baseline_flags_off,
    scenario_supported_evidence,
    scenario_partial_only_evidence,
    scenario_irrelevant_evidence,
    scenario_conflicting_evidence,
    scenario_missing_provenance,
    scenario_model_timeout,
    scenario_malformed_output,
    scenario_verifier_rejection,
    scenario_hitl_require_no_approval,
    scenario_fallback_invalid_evidence,
    scenario_persistence_restart,
    scenario_rejected_update_rollback,
]


# ─────────────────────────────────────────────────────────────────────────────
# Phases
# ─────────────────────────────────────────────────────────────────────────────


def phase_run(out: Path, *, overwrite: bool) -> dict[str, Any]:
    runner = Step5Runner(out, overwrite=overwrite)
    started = time.perf_counter()
    failures = []
    for scenario in SCENARIOS:
        try:
            scenario(runner)
        except Exception as exc:  # noqa: BLE001 - record scenario crash as evidence
            failures.append({"scenario": scenario.__name__, "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()})
            print(f"[SCENARIO-CRASH] {scenario.__name__}: {type(exc).__name__}: {exc}")
    records_path = out / "turn_records.jsonl"
    with records_path.open("w") as fh:
        for rec in runner.records:
            fh.write(json.dumps(rec, default=str) + "\n")
    expectation_failures = [
        {"request_id": r["request_id"], "case_id": r["case_id"], "failed": [k for k, c in r["expectation_result"]["checks"].items() if not c["passed"]]}
        for r in runner.records
        if not r["expectation_result"]["passed"]
    ]
    manifest = {
        "protocol": PROTOCOL,
        "phase": "run",
        "recorded_at": now_iso(),
        "duration_s": round(time.perf_counter() - started, 3),
        "scenarios": [s.__name__ for s in SCENARIOS],
        "turn_count": len(runner.records),
        "cases": sorted({r["case_id"] for r in runner.records}),
        "source_config": runner.source_config_base,
        "scenario_crashes": failures,
        "expectation_failures": expectation_failures,
        "python": sys.version,
    }
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    status = {
        "status": "PASS" if not failures and not expectation_failures else "FAIL",
        "turns": len(runner.records),
        "scenario_crashes": len(failures),
        "expectation_failures": expectation_failures,
        "records": str(records_path),
    }
    print(json.dumps(status, indent=2, default=str))
    return status


def _coverage(rec: dict[str, Any]) -> dict[str, str]:
    """Per-record presence of every plan-required evidence field.
    Returns field -> 'present' | 'na:<reason>' | 'missing'."""
    out: dict[str, str] = {}
    srv = rec.get("serving") or {}
    pol = rec.get("policy") or {}
    cti = rec.get("cti") or {}
    attempts = srv.get("attempts") or []

    sid = (rec.get("session") or {}).get("session_id")
    out["correlated_ids"] = "present" if all(rec.get(k) is not None for k in ("request_id", "case_id", "arm", "turn_index")) and sid else "missing"
    sc = rec.get("source_config") or {}
    out["source_config_hashes"] = "present" if sc.get("files") and sc.get("env") else "missing"
    out["input_context_hashes"] = "present" if rec.get("input_sha256") and rec.get("context_sha256") else "missing"

    r = cti.get("retrieval") or {}
    bundle = cti.get("evidence_bundle")
    if r.get("query") and r.get("document_ids") is not None and (r.get("corpus_sha256") or sc.get("real_corpus_sha256")):
        out["retrieval_query_corpus_docids"] = "present"
    elif isinstance(bundle, dict) and "retrieval" not in bundle:
        out["retrieval_query_corpus_docids"] = "na:bundle_missing_retrieval_section"
    elif cti.get("error"):
        out["retrieval_query_corpus_docids"] = "na:cti_failed"
    else:
        out["retrieval_query_corpus_docids"] = "missing"

    j = cti.get("judge") or {}
    bundle_for_judge = cti.get("evidence_bundle")
    if j.get("enabled") and j.get("judge_version") and j.get("trace_sha256") and j.get("sufficiency") is not None:
        out["judge_identity_outputs"] = "present"
    elif j.get("enabled") is False and not (sc.get("judge_enabled")):
        out["judge_identity_outputs"] = "na:judge_flags_off_explicit"
    elif not isinstance(bundle_for_judge, dict) or "retrieval" not in bundle_for_judge:
        out["judge_identity_outputs"] = "na:bundle_bypassed_export_path_malformed"
    else:
        out["judge_identity_outputs"] = "missing"

    pv = rec.get("policy_visible_evidence") or {}
    if pv.get("applied") and pv.get("before") is not None and pv.get("after") is not None:
        out["policy_visible_before_after"] = "present"
    elif pv.get("applied") is False and pv.get("reason"):
        out["policy_visible_before_after"] = "na:baseline_arm_no_policy_stage"
    else:
        out["policy_visible_before_after"] = "missing"

    if pol.get("applied") and pol.get("gate_state") and pol.get("gate_reason"):
        out["gate_reason"] = "present"
    elif pol.get("applied") is False and pol.get("reason"):
        out["gate_reason"] = "na:baseline_arm"
    else:
        out["gate_reason"] = "missing"

    if pol.get("applied") and pol.get("selected_response_strategy"):
        out["selected_strategy"] = "present"
    elif pol.get("applied") is False:
        out["selected_strategy"] = "na:baseline_arm"
    else:
        out["selected_strategy"] = "missing"

    if rec.get("arm") == "RAGIN_BASELINE" and pol.get("applied") is False:
        out["generator_consumption"] = "na:baseline_arm_no_strategy_generator"
    elif attempts and all(
        (a.get("strategy_consumed_by_template") not in (None, "NOT_VERIFIABLE"))
        or a.get("generation_error")
        for a in attempts
    ):
        out["generator_consumption"] = "present"
    else:
        out["generator_consumption"] = "missing"

    gen_hash = any(a.get("candidate_response_sha256") for a in attempts) or srv.get("candidate_response_sha256")
    if srv.get("served"):
        out["generated_served_hashes"] = "present" if gen_hash and srv.get("served_response_sha256") else "missing"
    else:
        out["generated_served_hashes"] = "present" if gen_hash else "missing"

    if rec.get("verification") is not None and attempts:
        out["verification_retries_fallback"] = "present"
    else:
        out["verification_retries_fallback"] = "missing"

    if rec.get("approval") or any(isinstance(a.get("hitl_result"), dict) for a in attempts):
        out["approval"] = "present"
    else:
        out["approval"] = "missing"

    if attempts and all(a.get("commit_event") and a.get("commit_reason") for a in attempts):
        out["commit_dispositions"] = "present"
    else:
        out["commit_dispositions"] = "missing"

    lat = rec.get("latency") or {}
    out["per_stage_and_e2e_latency"] = "present" if lat.get("end_to_end_ms") is not None and lat.get("stages") else "missing"

    prov = rec.get("provider") or {}
    out["provider_identity_errors"] = "present" if prov.get("components") and isinstance(prov.get("errors"), dict) else "missing"

    return out


INVARIANT_ACCESSORS: dict[str, Any] = {}  # filled by audit()


def audit(out: Path, *, overwrite: bool) -> dict[str, Any]:
    records_path = out / "turn_records.jsonl"
    if not records_path.exists():
        raise SystemExit(f"BLOCKED_MISSING_INPUT: {records_path} (run phase first)")
    records = [json.loads(line) for line in records_path.read_text().splitlines() if line.strip()]
    audit_dir = out / "audit"
    if audit_dir.exists() and not overwrite:
        raise SystemExit("BLOCKED_OUTPUT_ALREADY_EXISTS: pass --overwrite to regenerate the audit")
    audit_dir.mkdir(parents=True, exist_ok=True)

    # ---- 1. evidence coverage --------------------------------------------
    per_field: dict[str, dict[str, Any]] = {}
    for rec in records:
        for field, status in _coverage(rec).items():
            bucket = per_field.setdefault(field, {"present": 0, "na": 0, "missing": 0, "missing_cases": [], "na_reasons": set()})
            key = "missing" if status == "missing" else ("na" if status.startswith("na") else "present")
            bucket[key] += 1
            if key == "missing":
                bucket["missing_cases"].append(rec["request_id"])
            elif key == "na":
                bucket["na_reasons"].add(status)
    coverage = {}
    coverage_pass = True
    for field, bucket in sorted(per_field.items()):
        entry = {
            "records_total": len(records),
            "present": bucket["present"],
            "explicit_na": bucket["na"],
            "missing": bucket["missing"],
            "na_reasons": sorted(bucket["na_reasons"]),
            "missing_cases": bucket["missing_cases"],
        }
        if bucket["missing"]:
            coverage_pass = False
        coverage[field] = entry
    coverage_doc = {"protocol": PROTOCOL, "phase": "audit:coverage", "recorded_at": now_iso(), "status": "PASS" if coverage_pass else "FAIL", "fields": coverage}
    (audit_dir / "evidence_coverage.json").write_text(json.dumps(coverage_doc, indent=2, default=str))

    # ---- 2. admissibility invariants --------------------------------------
    invariants: list[dict[str, Any]] = []

    def check(name: str, predicate, detail: str) -> None:
        violations = []
        for rec in records:
            try:
                ok, why = predicate(rec)
            except Exception as exc:  # noqa: BLE001
                ok, why = False, f"eval-error: {type(exc).__name__}: {exc}"
            if not ok:
                violations.append({"request_id": rec["request_id"], "case_id": rec["case_id"], "why": why})
        invariants.append({"name": name, "detail": detail, "status": "PASS" if not violations else "FAIL", "violations": violations})

    def attempts_of(rec):
        return (rec.get("serving") or {}).get("attempts") or []

    def inv01(rec: dict[str, Any]):
        er = rec.get("expectation_result") or {}
        if er.get("passed") is True:
            return True, ""
        failed = [k for k, c in (er.get("checks") or {}).items() if not c.get("passed")]
        return False, "expectation failed: " + ", ".join(failed)

    check(
        "INV01_expectations_match",
        inv01,
        "Every scenario's declared expectation (gate state, outcome, dispositions) is observed — the scenario exercised the intended condition.",
    )

    def inv02(rec):
        if not (rec.get("serving") or {}).get("served"):
            return True, ""
        v = rec.get("verification") or {}
        a = rec.get("approval") or {}
        if v.get("passed") is not True or v.get("accepted") is not True:
            return False, f"verification passed={v.get('passed')} accepted={v.get('accepted')}"
        if a.get("approved") is not True:
            return False, f"approval approved={a.get('approved')}"
        if v.get("commit_event") != "accepted":
            return False, f"verification.commit_event={v.get('commit_event')}"
        return True, ""

    check(
        "INV02_served_turns_have_verifier_approval_commit_disposition",
        inv02,
        "Every served turn: verification passed+accepted, approval approved, commit disposition accepted (observable, not inferred).",
    )

    def inv04(rec):
        for i, att in enumerate(attempts_of(rec)):
            if att.get("commit_event") == "accepted":
                vv = att.get("verifier_verdict") or {}
                hh = att.get("hitl_result") or {}
                if vv.get("passed") is not True:
                    return False, f"attempt {i} committed without verifier pass"
                if isinstance(hh, dict) and hh.get("approved") is not True:
                    return False, f"attempt {i} committed without HITL approval"
        v = rec.get("verification") or {}
        if v.get("commit_event") == "accepted" and (v.get("passed") is not True or (rec.get("approval") or {}).get("approved") is not True):
            return False, "verification.commit_event accepted but verifier/HITL not approved"
        return True, ""

    check(
        "INV04_no_unauthorized_commit",
        inv04,
        "No commit is accepted without a passing verifier verdict AND approved HITL on that attempt.",
    )

    def inv05(rec):
        pol = rec.get("policy") or {}
        if not pol.get("applied"):
            return True, ""
        refs = pol.get("supporting_evidence_refs") or []
        valid = set(pol.get("valid_doc_ids") or [])
        if not set(refs).issubset(valid):
            return False, f"refs {refs} not subset of valid {sorted(valid)}"
        if pol.get("gate_state") != "VALID_EVIDENCE":
            consumed = [i for i, a in enumerate(attempts_of(rec)) if a.get("strategy_consumed_by_template") is True]
            if consumed:
                return False, f"strategy consumed on attempts {consumed} though gate={pol.get('gate_state')}"
            if pol.get("selected_response_strategy") not in (None, "baseline"):
                return False, f"non-baseline strategy {pol.get('selected_response_strategy')} with gate={pol.get('gate_state')}"
        else:
            if pol.get("selected_response_strategy") in (None, "baseline"):
                return False, "VALID_EVIDENCE but no non-baseline strategy selected"
        return True, ""

    check(
        "INV05_no_unsafe_evidence_promotion",
        inv05,
        "Policy refs subset of gate-valid IDs; non-VALID gate never consumes a strategy or selects non-baseline; VALID gate selects one.",
    )

    def inv06(rec):
        pol = rec.get("policy") or {}
        has_su = any(e.get("stage") == "strategy_update" for e in (rec.get("events_index") or []))
        if rec.get("arm") == "RAGIN_BASELINE":
            if pol.get("applied") or has_su:
                return False, "baseline arm carries a V4 policy stage"
            blob = json.dumps({k: rec.get(k) for k in ("policy",)}, default=str)
            if "deterministic_v1" in blob or "logistic" in blob:
                return False, "baseline arm references a V4 policy engine"
        else:
            if not pol.get("applied") or not has_su:
                return False, "V4 arm missing policy stage"
            if pol.get("arm") != rec.get("arm"):
                return False, f"policy arm {pol.get('arm')} != record arm {rec.get('arm')}"
        return True, ""

    check(
        "INV06_no_arm_state_leakage",
        inv06,
        "Baseline records carry no V4 policy stage/engine; V4 records carry exactly the policy stage of their own arm.",
    )

    def inv07(rec):
        pol = rec.get("policy") or {}
        if not pol.get("applied"):
            return True, ""
        cti = rec.get("cti") or {}
        pv = rec.get("policy_visible_evidence") or {}
        if pv.get("applied"):
            if list(pv.get("after") or []) != list(pol.get("valid_doc_ids") or []):
                return False, "policy_visible.after != policy.valid_doc_ids"
            jf_visible = pv.get("judge_filter_visible")
            if jf_visible is not None and list(jf_visible) != list(pol.get("valid_doc_ids") or []):
                return False, "judge_filter.gate_policy_visible_evidence_ids != policy.valid_doc_ids"
        bundle = cti.get("evidence_bundle")
        if isinstance(bundle, dict) and bundle.get("retrieval"):
            relevant = list((bundle.get("retrieval") or {}).get("relevant_doc_ids") or [])
            if pol.get("gate_state") == "VALID_EVIDENCE" and not set(pol.get("valid_doc_ids") or []).issubset(set(relevant)):
                return False, "gate-valid ids not subset of bundle relevant ids"
        # consumed strategy matches the policy decision
        for att in attempts_of(rec):
            if att.get("strategy_consumed_by_template") is True and att.get("selected_strategy") not in (None, pol.get("selected_response_strategy")):
                return False, f"attempt selected_strategy {att.get('selected_strategy')} != policy {pol.get('selected_response_strategy')}"
        # Build-time gate preview vs policy-time gate re-evaluation (two
        # independent evaluations of the same bundle must agree).
        preview = cti.get("gate_preview") if isinstance(cti.get("gate_preview"), dict) else None
        if preview:
            if preview.get("gate_state") != pol.get("gate_state"):
                return False, f"bundle gate_preview state {preview.get('gate_state')} != policy {pol.get('gate_state')}"
            if preview.get("reason_code") != pol.get("gate_reason"):
                return False, f"bundle gate_preview reason {preview.get('reason_code')} != policy {pol.get('gate_reason')}"
        if rec.get("arm") != "RAGIN_BASELINE" and isinstance(bundle, dict):
            if cti.get("bundle_sha256") and pol.get("evidence_bundle_sha256") and cti.get("bundle_sha256") != pol.get("evidence_bundle_sha256"):
                return False, "recorded bundle sha != policy evidence_bundle_sha256"
        return True, ""

    check(
        "INV07_policy_visible_evidence_and_strategy_match_trace",
        inv07,
        "Gate-valid IDs, judge-filter visible IDs, policy-visible before/after, bundle hash and consumed strategy all agree across bundle, policy decision and serving attempts.",
    )

    def inv08(rec):
        for i, att in enumerate(attempts_of(rec)):
            event, reason, effect = att.get("commit_event"), att.get("commit_reason"), att.get("commit_state_effect")
            if event not in {"accepted", "rejected", "not_attempted"}:
                return False, f"attempt {i} commit_event={event!r}"
            if not reason or reason == "NOT_VERIFIABLE":
                return False, f"attempt {i} commit_reason={reason!r}"
            if event == "not_attempted":
                if effect != "not_committed":
                    return False, f"attempt {i} not_attempted with effect={effect!r}"
                continue
            before, after = att.get("commit_graph_before_sha256"), att.get("commit_graph_after_sha256")
            if not before or not after:
                return False, f"attempt {i} ({event}) missing state hashes before={before!r} after={after!r}"
            if effect == "state_changed" and before == after:
                return False, f"attempt {i} claims state_changed but hashes equal"
            if effect in {"no_op_state_unchanged", "not_committed"} and before != after:
                return False, f"attempt {i} claims {effect} but hashes differ"
            if effect not in {"state_changed", "no_op_state_unchanged", "not_committed"}:
                return False, f"attempt {i} commit_state_effect={effect!r}"
        v = rec.get("verification") or {}
        if v.get("commit_event") == "accepted" and (not v.get("commit_graph_before_sha256") or not v.get("commit_graph_after_sha256")):
            return False, "verification record missing commit graph hashes"
        return True, ""

    check(
        "INV08_commit_dispositions_explicit_with_state_hashes",
        inv08,
        "Every attempt carries an explicit disposition (accepted/rejected/not_attempted) with reason; accepted/rejected commits carry consistent before/after state hashes; no-op and rejected (not_committed) states are labeled explicitly — never inferred.",
    )

    def inv09(rec):
        srv = rec.get("serving") or {}
        if srv.get("fallback_used"):
            if not srv.get("fallback_reason") or srv.get("fallback_reason") == "NOT_VERIFIABLE":
                return False, f"fallback used without explicit reason (reason={srv.get('fallback_reason')!r})"
        for i, att in enumerate(attempts_of(rec)):
            if att.get("commit_state_effect") == "no_op_state_unchanged" and att.get("commit_graph_before_sha256") != att.get("commit_graph_after_sha256"):
                return False, f"attempt {i} no-op label inconsistent with hashes"
        return True, ""

    check(
        "INV09_fallback_and_noop_events_explicit",
        inv09,
        "Fallback turns record an explicit fallback reason; no-op commits are recorded explicitly and consistently.",
    )

    def inv10(rec):
        for i, att in enumerate(attempts_of(rec)):
            for key in ("commit_event", "commit_reason", "commit_state_effect"):
                if att.get(key) == "NOT_VERIFIABLE":
                    return False, f"attempt {i} {key} left as NOT_VERIFIABLE"
        return True, ""

    check(
        "INV10_no_inference_filled_commit_metadata",
        inv10,
        "No attempt leaves commit metadata as the NOT_VERIFIABLE sentinel — nothing is left for downstream inference.",
    )

    # INV11 decorative markers: baseline vs supported substantive response
    by_case = {r["case_id"]: r for r in records if r.get("turn_index") == 1}
    base = by_case.get("baseline_flags_off") or {}
    supported = by_case.get("supported_evidence") or {}
    base_text = ((base.get("serving") or {}).get("response_text") or "")
    sup_text = ((supported.get("serving") or {}).get("response_text") or "")
    base_sem = "\n".join(base_text.splitlines()[1:])
    sup_sem = "\n".join(sup_text.splitlines()[1:])
    inv11_ok = bool(base_sem and sup_sem and base_sem != sup_sem)
    invariants.append(
        {
            "name": "INV11_response_differences_survive_decorative_marker_removal",
            "detail": "First line (prompt/echo decoration) stripped from baseline and supported-evidence responses; remaining content must differ.",
            "status": "PASS" if inv11_ok else "FAIL",
            "violations": [] if inv11_ok else [{"request_id": f"{(base.get('request_id'))},{(supported.get('request_id'))}", "case_id": "baseline_flags_off/supported_evidence", "why": f"stripped equal/empty (base_sha={sha256_text(base_sem)[:12]}, sup_sha={sha256_text(sup_sem)[:12]})"}],
            "observed": {"baseline_stripped_sha256": sha256_text(base_sem), "supported_stripped_sha256": sha256_text(sup_sem)},
        }
    )

    def inv12(rec):
        if rec.get("case_id") != "persistence_restart" or rec.get("turn_index") != 3:
            return True, ""
        p = rec.get("persistence") or {}
        if not p.get("session_resume_event_in_turn"):
            return False, "no SESSION_RESUME event in restart turn"
        if p.get("attacker_inputs_after") != 3:
            return False, f"attacker_inputs_after={p.get('attacker_inputs_after')}"
        if not p.get("identity_stable"):
            return False, "pinned identity changed across restart"
        if not p.get("host_facts_preserved"):
            return False, "host facts not preserved"
        if not rec.get("serving", {}).get("served"):
            return False, "turn after restart not served"
        return True, ""

    check(
        "INV12_persistence_restart_continuity",
        inv12,
        "After restart: session log resumes (SESSION_RESUME), turn count continues, pinned host identity and promoted host facts persist, and the turn serves with full dispositions.",
    )

    def inv13(rec):
        if rec.get("case_id") != "rejected_update_rollback":
            return True, ""
        rb = rec.get("rollback") or {}
        for key in ("commit0_before_after_equal", "host_file_matches_memory"):
            if rb.get(key) is not True:
                return False, f"{key}={rb.get(key)!r}"
        if rb.get("generator_visits") != 0:
            return False, f"generator_visits={rb.get('generator_visits')}"
        if rb.get("pending_candidates") != 0:
            return False, f"pending_candidates={rb.get('pending_candidates')}"
        att = (rec.get("serving") or {}).get("attempts") or [{}]
        if att[0].get("commit_event") != "rejected":
            return False, "first attempt not rejected"
        if att[-1].get("commit_event") != "accepted":
            return False, "fallback commit not accepted"
        return True, ""

    check(
        "INV13_rejected_update_rolled_back_and_persisted",
        inv13,
        "Rejected update: fiction graph restored (before==after), host store restored AND persisted to disk, generator state untouched, fallback commit accepted.",
    )

    def inv14(rec):
        if (rec.get("serving") or {}).get("served"):
            return True, ""
        attempts = attempts_of(rec)
        if any(a.get("commit_event") == "accepted" for a in attempts):
            return False, "turn not served but a commit was accepted"
        if not rec.get("error"):
            return False, "turn not served and no explicit error recorded"
        return True, ""

    check(
        "INV14_no_unserved_state_mutation_and_errors_explicit",
        inv14,
        "A turn that does not serve records an explicit error and never leaves an accepted commit behind.",
    )

    failed_invariants = [inv["name"] for inv in invariants if inv["status"] != "PASS"]
    invariants_doc = {
        "protocol": PROTOCOL,
        "phase": "audit:invariants",
        "recorded_at": now_iso(),
        "status": "PASS" if not failed_invariants else "FAIL",
        "records": len(records),
        "invariants": invariants,
    }
    (audit_dir / "invariants.json").write_text(json.dumps(invariants_doc, indent=2, default=str))

    # ---- 3. expectations summary -------------------------------------------
    expectations_doc = {
        "protocol": PROTOCOL,
        "phase": "audit:expectations",
        "recorded_at": now_iso(),
        "status": "PASS" if all((r.get("expectation_result") or {}).get("passed") for r in records) else "FAIL",
        "cases": [
            {
                "request_id": r["request_id"],
                "case_id": r["case_id"],
                "turn_index": r["turn_index"],
                "passed": (r.get("expectation_result") or {}).get("passed"),
                "checks": (r.get("expectation_result") or {}).get("checks"),
            }
            for r in records
        ],
    }
    (audit_dir / "expectations.json").write_text(json.dumps(expectations_doc, indent=2, default=str))

    status = {
        "status": "PASS" if coverage_pass and not failed_invariants and expectations_doc["status"] == "PASS" else "FAIL",
        "coverage": coverage_doc["status"],
        "invariants": invariants_doc["status"],
        "expectations": expectations_doc["status"],
        "failed_invariants": failed_invariants,
        "records": len(records),
    }
    print(json.dumps(status, indent=2, default=str))
    return status


def phase_freeze(out: Path, *, overwrite: bool) -> dict[str, Any]:
    manifest_path = out / "sha256_manifest.json"
    if manifest_path.exists() and not overwrite:
        raise SystemExit("BLOCKED_OUTPUT_ALREADY_EXISTS: pass --overwrite to regenerate the manifest")
    files = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path != manifest_path:
            files[str(path.relative_to(out))] = sha256_file(path)
    manifest = {
        "protocol": PROTOCOL,
        "phase": "freeze",
        "recorded_at": now_iso(),
        "file_count": len(files),
        "files": files,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"status": "PASS", "frozen_files": len(files), "manifest": str(manifest_path)}, indent=2))
    return {"status": "PASS", "frozen_files": len(files)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 5 working-system observability runner")
    parser.add_argument("phase", choices=["run", "audit", "freeze", "all"])
    parser.add_argument("--out", default=str(REPO_ROOT / "results" / "step5_working_system_observability_v1"))
    parser.add_argument("--overwrite", action="store_true", help="replace existing outputs in --out (run/audit/freeze phases)")
    args = parser.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        out = Path.cwd() / out
    exit_bad = False
    if args.phase in {"run", "all"}:
        exit_bad = phase_run(out, overwrite=args.overwrite)["status"] != "PASS" or exit_bad
    if args.phase in {"audit", "all"}:
        exit_bad = audit(out, overwrite=args.overwrite or args.phase == "all")["status"] != "PASS" or exit_bad
    if args.phase in {"freeze", "all"}:
        phase_freeze(out, overwrite=args.overwrite or args.phase == "all")
    raise SystemExit(1 if exit_bad else 0)


if __name__ == "__main__":
    main()
