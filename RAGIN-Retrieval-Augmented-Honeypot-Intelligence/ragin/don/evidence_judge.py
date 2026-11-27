from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field

CONTRACT_VERSION = "EVIDENCE_JUDGE_V1"
FILTERING_CONTRACT_VERSION = "EVIDENCE_JUDGE_FILTERING_V1"


class EvidenceLabel(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    IRRELEVANT = "IRRELEVANT"
    CONTRADICTORY = "CONTRADICTORY"
    UNKNOWN = "UNKNOWN"


class SufficiencyLabel(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTING = "CONFLICTING"
    UNKNOWN = "UNKNOWN"


class EvidenceCandidate(BaseModel):
    doc_id: str = ""
    title: str = ""
    content: str = ""
    source: str = ""
    provenance_status: str = "UNKNOWN"
    source_version: str = ""
    provenance_hash: str = ""
    command_patterns: list[str] = Field(default_factory=list)
    behavior_tags: list[str] = Field(default_factory=list)


class CandidateJudgment(BaseModel):
    doc_id: str
    label: EvidenceLabel
    relates_to_command: bool | None
    substantively_supports_behavior: bool | None
    support_kind: EvidenceLabel
    provenance_sufficient: bool
    context_status: str
    rationale_codes: list[str] = Field(default_factory=list)


class BundleSufficiency(BaseModel):
    label: SufficiencyLabel
    policy_behavior: str
    supporting_doc_ids: list[str] = Field(default_factory=list)
    contradictory_doc_ids: list[str] = Field(default_factory=list)
    rationale_codes: list[str] = Field(default_factory=list)


class EvidenceJudgeTrace(BaseModel):
    contract_version: str = CONTRACT_VERSION
    judge_version: str
    adapter_kind: str
    command: str
    context_missing_or_ambiguous: bool
    candidate_judgments: list[CandidateJudgment] = Field(default_factory=list)
    sufficiency: BundleSufficiency
    probabilities: dict[str, float] = Field(default_factory=dict)


class EvidenceFilteringTrace(BaseModel):
    contract_version: str = FILTERING_CONTRACT_VERSION
    original_relevant_doc_ids: list[str] = Field(default_factory=list)
    filtered_relevant_doc_ids: list[str] = Field(default_factory=list)
    excluded_doc_ids: list[str] = Field(default_factory=list)
    partial_doc_ids: list[str] = Field(default_factory=list)
    contradictory_doc_ids: list[str] = Field(default_factory=list)
    unknown_doc_ids: list[str] = Field(default_factory=list)
    filtered_sufficiency: SufficiencyLabel
    policy_visible_evidence_ids: list[str] = Field(default_factory=list)
    rationale_codes: list[str] = Field(default_factory=list)


class EvidenceScoringAdapter(Protocol):
    kind: str
    enabled: bool
    calibrated: bool

    def score(self, command: str, candidates: Sequence[EvidenceCandidate]) -> Mapping[str, Any]: ...


class EvidenceJudge(Protocol):
    version: str
    adapter_kind: str

    def judge(
        self,
        command: str,
        candidates: Sequence[EvidenceCandidate | Mapping[str, Any]],
        *,
        preceding_commands: Sequence[str] = (),
    ) -> EvidenceJudgeTrace: ...


class ExternalScoringAdapter:
    kind = "external"
    enabled = False
    calibrated = False

    def score(self, command: str, candidates: Sequence[EvidenceCandidate]) -> Mapping[str, Any]:
        raise RuntimeError("external evidence scoring is disabled")


class LayaScoringAdapter:
    kind = "laya_fixed_choice"
    enabled = False
    calibrated = False

    def score(self, command: str, candidates: Sequence[EvidenceCandidate]) -> Mapping[str, Any]:
        raise RuntimeError("Laya scoring adapter is disabled")


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_./:-]+", value.lower()))


def _policy_behavior(command: str, candidates: Sequence[EvidenceCandidate]) -> str:
    tags = sorted({tag for candidate in candidates for tag in candidate.behavior_tags})
    return ",".join(tags) if tags else "observed_command_behavior"


class DeterministicEvidenceJudge:
    version = "DETERMINISTIC_COMMAND_GROUNDED_V1"
    adapter_kind = "deterministic"

    def judge(
        self,
        command: str,
        candidates: Sequence[EvidenceCandidate | Mapping[str, Any]],
        *,
        preceding_commands: Sequence[str] = (),
    ) -> EvidenceJudgeTrace:
        normalized = [candidate if isinstance(candidate, EvidenceCandidate) else EvidenceCandidate(**candidate) for candidate in candidates]
        context = [str(item) for item in preceding_commands if str(item).strip()]
        all_commands = [*context, command]
        context_ambiguous = not command.strip() or (any(token in command for token in ("'", '"')) and command.count("'") % 2 == 1)
        command_tokens = _tokens(" ".join(all_commands))
        judgments: list[CandidateJudgment] = []
        for candidate in normalized:
            doc_tokens = _tokens(" ".join([candidate.title, candidate.content, *candidate.behavior_tags]))
            patterns = [pattern.lower() for pattern in candidate.command_patterns if pattern]
            matched_patterns = [pattern for pattern in patterns if pattern in " ".join(all_commands).lower()]
            overlap = command_tokens & doc_tokens
            relation = bool(matched_patterns or overlap)
            behavior_support = bool(matched_patterns or set(candidate.behavior_tags) & command_tokens)
            provenance = bool(candidate.doc_id.strip() and candidate.source.strip() and candidate.provenance_status == "VALID")
            contradiction = any(marker in candidate.content.lower() for marker in ("contradicts", "not evidence", "did not occur"))
            if contradiction and relation:
                label = EvidenceLabel.CONTRADICTORY
                support_kind = EvidenceLabel.CONTRADICTORY
                codes = ["explicit_contradiction"]
            elif not provenance:
                label = EvidenceLabel.UNKNOWN
                support_kind = EvidenceLabel.UNKNOWN
                codes = ["insufficient_provenance"]
            elif not relation:
                label = EvidenceLabel.IRRELEVANT
                support_kind = EvidenceLabel.IRRELEVANT
                codes = ["no_command_relation"]
            elif behavior_support and not context_ambiguous:
                label = EvidenceLabel.SUPPORTED
                support_kind = EvidenceLabel.SUPPORTED
                codes = ["command_pattern_or_behavior_match"]
            elif relation:
                label = EvidenceLabel.PARTIAL
                support_kind = EvidenceLabel.PARTIAL
                codes = ["related_without_direct_behavior_support"]
            else:
                label = EvidenceLabel.UNKNOWN
                support_kind = EvidenceLabel.UNKNOWN
                codes = ["ambiguous_context"]
            judgments.append(
                CandidateJudgment(
                    doc_id=candidate.doc_id,
                    label=label,
                    relates_to_command=relation if candidate.content or candidate.title else None,
                    substantively_supports_behavior=behavior_support if candidate.content else None,
                    support_kind=support_kind,
                    provenance_sufficient=provenance,
                    context_status="AMBIGUOUS" if context_ambiguous else ("PRESENT" if all_commands else "MISSING"),
                    rationale_codes=codes,
                )
            )
        sufficient = self._sufficiency(judgments, command, normalized, context_ambiguous)
        return EvidenceJudgeTrace(
            judge_version=self.version,
            adapter_kind=self.adapter_kind,
            command=command,
            context_missing_or_ambiguous=context_ambiguous,
            candidate_judgments=judgments,
            sufficiency=sufficient,
        )

    @staticmethod
    def _sufficiency(
        judgments: Sequence[CandidateJudgment],
        command: str,
        candidates: Sequence[EvidenceCandidate],
        context_ambiguous: bool,
    ) -> BundleSufficiency:
        supported = [item.doc_id for item in judgments if item.label == EvidenceLabel.SUPPORTED]
        contradictory = [item.doc_id for item in judgments if item.label == EvidenceLabel.CONTRADICTORY]
        if contradictory and supported:
            label = SufficiencyLabel.CONFLICTING
            codes = ["supported_and_contradictory_evidence"]
        elif contradictory:
            label = SufficiencyLabel.CONFLICTING
            codes = ["contradictory_evidence"]
        elif context_ambiguous:
            label = SufficiencyLabel.UNKNOWN
            codes = ["ambiguous_command_context"]
        elif supported:
            label = SufficiencyLabel.SUFFICIENT
            codes = ["direct_behavior_support"]
        elif any(item.label == EvidenceLabel.PARTIAL for item in judgments):
            label = SufficiencyLabel.INSUFFICIENT
            codes = ["partial_support_only"]
        elif judgments:
            label = SufficiencyLabel.INSUFFICIENT
            codes = ["no_substantive_support"]
        else:
            label = SufficiencyLabel.UNKNOWN
            codes = ["no_candidates"]
        return BundleSufficiency(
            label=label,
            policy_behavior=_policy_behavior(command, candidates),
            supporting_doc_ids=supported,
            contradictory_doc_ids=contradictory,
            rationale_codes=codes,
        )


def judge_bundle(
    command: str,
    documents: Sequence[Mapping[str, Any]],
    *,
    preceding_commands: Sequence[str] = (),
    judge: EvidenceJudge | None = None,
) -> dict[str, Any]:
    trace = (judge or DeterministicEvidenceJudge()).judge(command, documents, preceding_commands=preceding_commands)
    payload = trace.model_dump(mode="json")
    payload["trace_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload


def filter_judged_evidence(
    retrieval: Mapping[str, Any],
    judge_trace: Mapping[str, Any],
) -> dict[str, Any]:
    documents = retrieval.get("documents", [])
    original_relevant = [str(doc_id) for doc_id in retrieval.get("relevant_doc_ids", [])]
    document_by_id = {str(document.get("doc_id")): document for document in documents if isinstance(document, Mapping)}
    judgments = {
        str(judgment.get("doc_id")): judgment
        for judgment in judge_trace.get("candidate_judgments", [])
        if isinstance(judgment, Mapping) and judgment.get("doc_id")
    }
    filtered: list[str] = []
    partial: list[str] = []
    contradictory: list[str] = []
    unknown: list[str] = []
    excluded: list[str] = []
    for doc_id in original_relevant:
        judgment = judgments.get(doc_id)
        document = document_by_id.get(doc_id)
        label = judgment.get("label") if judgment else EvidenceLabel.UNKNOWN.value
        provenance_valid = bool(
            judgment
            and judgment.get("provenance_sufficient") is True
            and isinstance(document, Mapping)
            and document.get("provenance_status") == "VALID"
            and document.get("sanitization_status") == "SANITIZED"
            and document.get("conflict_status") == "NONE"
        )
        if label == EvidenceLabel.SUPPORTED.value and provenance_valid:
            filtered.append(doc_id)
        else:
            excluded.append(doc_id)
            if label == EvidenceLabel.PARTIAL.value:
                partial.append(doc_id)
            elif label == EvidenceLabel.CONTRADICTORY.value:
                contradictory.append(doc_id)
            else:
                unknown.append(doc_id)
    if contradictory:
        sufficiency = SufficiencyLabel.CONFLICTING
        rationale = ["contradictory_relevant_evidence"]
    elif judge_trace.get("context_missing_or_ambiguous") is True:
        sufficiency = SufficiencyLabel.UNKNOWN
        rationale = ["ambiguous_command_context"]
    elif filtered:
        sufficiency = SufficiencyLabel.SUFFICIENT
        rationale = ["validated_supported_relevant_evidence"]
    elif partial:
        sufficiency = SufficiencyLabel.INSUFFICIENT
        rationale = ["partial_relevant_evidence_only"]
    elif unknown:
        sufficiency = SufficiencyLabel.UNKNOWN
        rationale = ["no_validated_supporting_relevant_evidence"]
    else:
        sufficiency = SufficiencyLabel.UNKNOWN
        rationale = ["no_relevant_evidence"]
    return EvidenceFilteringTrace(
        original_relevant_doc_ids=original_relevant,
        filtered_relevant_doc_ids=filtered,
        excluded_doc_ids=excluded,
        partial_doc_ids=partial,
        contradictory_doc_ids=contradictory,
        unknown_doc_ids=unknown,
        filtered_sufficiency=sufficiency,
        policy_visible_evidence_ids=filtered,
        rationale_codes=rationale,
    ).model_dump(mode="json")


__all__ = [
    "CONTRACT_VERSION",
    "FILTERING_CONTRACT_VERSION",
    "EvidenceLabel",
    "SufficiencyLabel",
    "EvidenceCandidate",
    "CandidateJudgment",
    "BundleSufficiency",
    "EvidenceJudgeTrace",
    "EvidenceFilteringTrace",
    "EvidenceScoringAdapter",
    "EvidenceJudge",
    "ExternalScoringAdapter",
    "LayaScoringAdapter",
    "DeterministicEvidenceJudge",
    "judge_bundle",
    "filter_judged_evidence",
]
