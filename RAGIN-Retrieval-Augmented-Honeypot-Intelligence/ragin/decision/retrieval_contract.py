"""Versioned retrieval-evidence decision adapter — the v12 contract, implemented.

Motivation (v12 no-rerun recovery audit, finding 5): the runtime API speaks the
old attack contract (``attack``/``stage``/``severity``) while the frozen v12
study's contract is ``evidence_state``/``strategy``/``evidence_ref`` with
supply-document membership and mechanical caller rules. Routing v12 answers
through the old attack normalizer is forbidden; this module is the explicit,
separate, versioned adapter the audit says an integration *would require*.

Contract fidelity
-----------------
Decoding and enforcement are faithful ports of the frozen runner
(``scripts/laya_v12_balanced_allrows_gpu_runner_v1.py``):

* ``parse_choice`` semantics — ``type == "choice"``, string choice inside the
  declared label vocabulary, non-empty numeric ``probabilities`` dict. Every
  membership test type-guards the value first, so an unhashable choice (list,
  dict) invalidates the question instead of raising TypeError.
* ``apply_caller_rules`` semantics — ``ABSTAIN`` (baseline, no refs) unless the
  whole payload is schema-valid AND ``evidence_state == "SUFFICIENT"`` AND the
  chosen reference is a supplied document id; otherwise ``SELECT``.

Novel design: decoupled per-question fail-safe channels
-------------------------------------------------------
The frozen metric couples state errors into strategy/reference outcomes via the
caller rule — that coupling is deliberate and is applied exactly as declared.
What is NEW here is failure isolation at *decoding* time: each of the three
questions is decoded and validated independently, so a malformed state answer
can never corrupt, erase, or crash the strategy/reference views. Every event
records both the raw per-question views (decoupled) and the mechanically
enforced outcome (coupled), making the coupling contribution visible per request
instead of hidden. The saved-output decomposition
(``scripts/laya_v12_coupling_decomposition_v1.py``) shows decoupling alone
cannot pass G7/G8 — this adapter therefore records both views for auditability
and applies the frozen rule for action, without claiming a performance change.

Integration of the evidence quarantine (I2)
-------------------------------------------
Retrieval documents are run through ``quarantine_state`` before the state can
reach the provider, with full removal provenance recorded in the event.

Activation boundary (how this differs from a second live path)
--------------------------------------------------------------
This module is inert until a caller explicitly constructs it with its own
``infer`` callable and model identity. It does NOT auto-load the v12 fitted
directory, does NOT import into ``laya_runtime``/``laya_decision``/the server,
and a unit test asserts that non-wiring. Constructing an adapter here is
contract engineering, not checkpoint promotion or behavioral validation: the
v12 classification ``TUNING_FAIL_REDESIGN_REQUIRED`` stands, and no frozen
artifact is read, written, or re-scored.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from ragin.decision.bounded_worker import shared_infer_worker
from ragin.decision.evidence_quarantine import (
    EVIDENCE_STATES,
    STRATEGIES,
    quarantine_state,
)
from ragin.decision.state_bounds import DEFAULT_MAX_STATE_CHARS, TRUNCATION_POLICY, bound_state

CONTRACT_VERSION = "ragin.laya_retrieval_decision.v1"
EVENT_SCHEMA = "ragin.laya_retrieval_decision.decision_event.v1"
ENFORCEMENT_RULE = "apply_caller_rules.v1"  # faithful port of the frozen runner rule
QUESTION_IDS = ("evidence_state", "strategy", "evidence_ref")

ABSTAIN = {"action": "ABSTAIN", "strategy": "baseline", "evidence_refs": []}

_NONE_REF = "NONE"


def _labels_for(question_id: str, canonical_refs: frozenset[str]) -> frozenset[str]:
    if question_id == "evidence_state":
        return EVIDENCE_STATES
    if question_id == "strategy":
        return STRATEGIES
    return canonical_refs  # evidence_ref: supplied ids | {"NONE"}


def parse_choice(answer: Any, labels: frozenset[str]) -> tuple[str | None, bool]:
    """Frozen-runner ``parse_choice`` semantics, TypeError-safe on bad types."""
    if not isinstance(answer, Mapping) or answer.get("type") != "choice":
        return None, False
    label = answer.get("choice")
    probabilities = answer.get("probabilities")
    probs_ok = (
        isinstance(probabilities, Mapping)
        and len(probabilities) > 0
        and all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in probabilities.values()
        )
    )
    # isinstance guard first: an unhashable choice must not raise in `in labels`.
    ok = isinstance(label, str) and label in labels and probs_ok
    return (label if isinstance(label, str) else None), ok


def apply_caller_rules(
    schema_ok: bool,
    state_label: str | None,
    strategy_label: str | None,
    ref_label: str | None,
    supplied_ids: frozenset[str],
) -> dict[str, Any]:
    """Frozen-runner ``apply_caller_rules`` semantics, verbatim in behavior."""
    if not schema_ok:
        return dict(ABSTAIN)
    if state_label != "SUFFICIENT":
        return dict(ABSTAIN)
    if ref_label in supplied_ids:
        return {"action": "SELECT", "strategy": strategy_label, "evidence_refs": [ref_label]}
    return dict(ABSTAIN)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class RetrievalDecisionAdapter:
    """Versioned adapter for the v12 retrieval-evidence contract.

    Parameters mirror the existing adapters (bounded shared worker, one truncation
    rule) but the contract is the retrieval-evidence one, never the attack one.
    ``infer`` receives the quarantined, bounded state text and must return a
    mapping with an ``answers`` dict in the frozen payload shape. Prompt
    construction and checkpoint loading belong to the caller-supplied ``infer``
    and ``manifest_provider``; this adapter never loads weights itself.
    """

    def __init__(
        self,
        infer: Callable[[str], Any],
        *,
        model: str,
        manifest_provider: Callable[[], Mapping[str, Any]] | None = None,
        timeout_s: float = 30.0,
        max_state_chars: int = DEFAULT_MAX_STATE_CHARS,
    ) -> None:
        self._infer = infer
        self._model = model
        self._manifest_provider = manifest_provider
        self._timeout_s = timeout_s
        self._max_state_chars = max_state_chars

    def _manifest(self) -> dict[str, Any]:
        if self._manifest_provider is None:
            return {}
        try:
            return dict(self._manifest_provider())
        except Exception as exc:  # provenance must not break fail-safe behavior
            return {"manifest_error": type(exc).__name__}

    def decide(
        self,
        *,
        session_id: str,
        state: Mapping[str, Any],
        supplied_doc_ids: Iterable[str],
    ) -> dict[str, Any]:
        started = time.monotonic()

        # 1) Input quarantine before anything can reach the provider (I2 layer).
        # Digest chain: raw_state -> (quarantine) -> source_state -> (bound) -> effective_input.
        raw_state_sha256 = _sha256(json.dumps(state, sort_keys=True, default=str))
        clean_state, quarantine_provenance = quarantine_state(state)

        # 2) One shared truncation rule, digests named precisely.
        text = json.dumps(clean_state, sort_keys=True, default=str)
        source_state_sha256 = _sha256(text)
        bounded_text, truncated = bound_state(text, self._max_state_chars)
        effective_input_sha256 = _sha256(bounded_text)

        # 3) Bounded admission with explicit non-ok outcomes.
        status, result = shared_infer_worker().run(self._infer, bounded_text, self._timeout_s)
        payload: Mapping[str, Any] | None = None
        error: str | None = None
        if status == "timeout":
            error = "timeout"
        elif status == "busy":
            error = "busy"
        elif status == "error":
            error = type(result).__name__
        elif not isinstance(result, Mapping):
            error = "TypeError"
        else:
            payload = result

        # 4) Supplied-document membership from the caller (never inferred).
        supplied_ids = frozenset(str(doc_id) for doc_id in supplied_doc_ids)
        canonical_refs = supplied_ids | {_NONE_REF}

        # 5) Decoupled per-question decoding: each channel fails independently.
        answers = payload.get("answers") if payload is not None else None
        raw_answers: dict[str, str | None] = {}
        per_question_valid: dict[str, bool] = {}
        schema_ok = payload is not None
        for question_id in QUESTION_IDS:
            try:
                answer = answers.get(question_id) if isinstance(answers, Mapping) else None
                label, ok = parse_choice(answer, _labels_for(question_id, canonical_refs))
            except Exception:  # one bad channel must never corrupt the others
                label, ok = None, False
            raw_answers[question_id] = label
            per_question_valid[question_id] = ok
            schema_ok = schema_ok and ok

        # 6) Declared validity flags (schema / allow-list / membership).
        allow_list_valid = (
            raw_answers["evidence_state"] in EVIDENCE_STATES
            and raw_answers["strategy"] in STRATEGIES
            and raw_answers["evidence_ref"] in canonical_refs
        )
        evidence_ref_valid = raw_answers["evidence_ref"] in canonical_refs

        # 7) Mechanical, frozen caller rule on top of the decoupled views.
        enforced = apply_caller_rules(
            schema_ok,
            raw_answers["evidence_state"],
            raw_answers["strategy"],
            raw_answers["evidence_ref"],
            supplied_ids,
        )

        latency_ms = (time.monotonic() - started) * 1000
        manifest = self._manifest()
        fallback_reason = None
        if error is not None:
            fallback_reason = error
        elif not schema_ok:
            fallback_reason = "schema_invalid"

        return {
            "schema": EVENT_SCHEMA,
            "contract_version": CONTRACT_VERSION,
            "session_id": session_id,
            "model": self._model,
            "checkpoint": manifest.get("checkpoint"),
            "model_hash": manifest.get("model_hash"),
            "revision": manifest.get("revision"),
            "real_model_verified": bool(
                manifest.get("runtime_verified") and manifest.get("checkpoint_verified")
            ),
            "payload_status": "ok" if error is None else error,
            "error": error,
            "latency_ms": round(latency_ms, 3),
            # Provenance: raw, post-quarantine and effective digests.
            "raw_state_sha256": raw_state_sha256,
            "source_state_sha256": source_state_sha256,
            "effective_input_sha256": effective_input_sha256,
            "source_state_chars": len(text),
            "effective_input_chars": len(bounded_text),
            "input_truncated": truncated,
            "truncation_policy": TRUNCATION_POLICY,
            # Quarantine provenance for the I2 input layer.
            "quarantine": quarantine_provenance,
            # Decoupled raw views + per-question validity (failure isolation).
            "raw_answers": raw_answers,
            "per_question_valid": dict(per_question_valid),
            "schema_ok": bool(schema_ok),
            "allow_list_valid": bool(allow_list_valid),
            "evidence_ref_valid": bool(evidence_ref_valid),
            "supplied_doc_ids": sorted(supplied_ids),
            # Coupled mechanical enforcement (frozen rule, applied exactly).
            "enforced": enforced,
            "enforcement_rule": ENFORCEMENT_RULE,
            "fallback_reason": fallback_reason,
        }
