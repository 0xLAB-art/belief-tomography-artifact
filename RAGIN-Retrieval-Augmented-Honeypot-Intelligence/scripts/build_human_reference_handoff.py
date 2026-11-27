#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT = ROOT / "results/laya_research/blind_annotation_confirmatory_v3.json"
INSTRUMENT_FREEZE = ROOT / "results/laya_research/v3_annotation_instrument_freeze.json"
RESULTS_FREEZE = ROOT / "results/laya_research/v3_annotation_results_freeze.json"
AGREEMENT = ROOT / "results/laya_research/v3_multirater_reliability.json"
PAIRWISE_MULTI = ROOT / "results/laya_research/v3_pairwise_multiclass_agreement.json"
PAIRWISE_BINARY = ROOT / "results/laya_research/v3_pairwise_binary_agreement.json"

EXPECTED_FREEZE_PACKET_HASHES = {
    "r1": "8059af3cebe8ecde86cfcd2da3c65fa123ee988a202e445a8c5134eebf8ff4bc",
    "r2": "f21dbd52a9efe3771acfcb7e3218f8a88e1634814fd30f83b7a7a670558960cc",
    "r3": "1e178e1a58cc30e2367f057393ba27387bc11d54beeccf8feafd8707330bde7d",
}
EXPECTED_INSTRUMENT_CASE_COUNT = 120
EXPECTED_INSTRUMENT_FREEZE_SHA256 = "cd42e93d661dddeecd5ac6ef585fc4ad574b6751b14645ae5efa3a1004972e6c"
EXPECTED_RESULTS_FREEZE_SHA256 = "ddcec6b139350ca9427f7a0e04fe8c45cc7a56082a47128d34a49cf89db41d09"
EXPECTED_CASE_ID_SET_SHA256 = (
    "00d89835c7bce9ea8e66c27f657f6c46770bf47f078bae2fd8a770ff20ae6a45"
)
TAXONOMY = [
    "BENIGN",
    "RECON",
    "SUSPICIOUS",
    "EXPLOITATION",
    "PRIVILEGE_ESCALATION",
    "DATA_ACCESS",
    "PERSISTENCE",
    "OTHER_ATTACK",
    "UNCERTAIN",
]

SEEDS = {
    "human_rater_01": 2026101301,
    "human_rater_02": 2026101302,
    "human_rater_03": 2026101303,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def check_source_freezes() -> tuple[list[dict[str, str]], dict[str, object]]:
    instrument = json.loads(INSTRUMENT.read_text(encoding="utf-8"))
    instrument_freeze = json.loads(INSTRUMENT_FREEZE.read_text(encoding="utf-8"))
    results_freeze = json.loads(RESULTS_FREEZE.read_text(encoding="utf-8"))

    if sha256(INSTRUMENT_FREEZE) != EXPECTED_INSTRUMENT_FREEZE_SHA256:
        raise AssertionError("instrument freeze hash check failed")
    if sha256(RESULTS_FREEZE) != EXPECTED_RESULTS_FREEZE_SHA256:
        raise AssertionError("annotation results freeze hash check failed")
    if len(instrument) != EXPECTED_INSTRUMENT_CASE_COUNT:
        raise AssertionError("canonical instrument does not contain 120 cases")
    if any(set(item) != {"id", "evidence", "context"} for item in instrument):
        raise AssertionError("canonical instrument schema changed")
    ids = [item["id"] for item in instrument]
    if len(set(ids)) != EXPECTED_INSTRUMENT_CASE_COUNT:
        raise AssertionError("canonical instrument has duplicate case IDs")
    id_hash = hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()
    if id_hash != EXPECTED_CASE_ID_SET_SHA256:
        raise AssertionError("canonical case-ID set hash mismatch")

    freeze_hashes = instrument_freeze.get("artifact_sha256", {})
    expected_instrument_hash = freeze_hashes.get(
        "results/laya_research/blind_annotation_confirmatory_v3.json"
    )
    if expected_instrument_hash and sha256(INSTRUMENT) != expected_instrument_hash:
        raise AssertionError("canonical instrument hash does not match its freeze")
    if not results_freeze.get("integrity_assertions", {}).get(
        "instrument_freeze_unchanged", False
    ):
        raise AssertionError("V3 results freeze does not assert instrument integrity")
    if results_freeze.get("predictions_accessed") is not False:
        raise AssertionError("V3 results freeze does not preserve prediction boundary")
    return instrument, {"instrument_freeze": instrument_freeze, "results_freeze": results_freeze}


AI_STATUS = dedent(
    '''
    # V3 AI Label Status

    Status: exploratory annotation-reliability evidence only.

    The three valid V3 agent runs (`v3_agent_run_01`, `v3_agent_run_03`, and
    `v3_agent_run_04`) are exploratory annotation-reliability evidence. They
    are not human raters and they are not a reference standard. AI majority
    vote is prohibited as confirmatory truth. Their labels must not influence
    human raters or adjudicators. The poor agreement result is preserved as a
    scientific result and is not repaired by rerunning annotators.

    Future Chrollo-vs-Laya confirmatory analysis requires independently
    collected human labels.

    ## Frozen aggregate reliability statistics

    These are aggregate values only; no case-level labels are included here.

    - Valid runs: 3; invalid run excluded: `v3_agent_run_02`.
    - Invalid-run reason: `PREDECLARED_BLINDNESS_BOUNDARY_VIOLATION`.
    - Multiclass: N=120; observed agreement=0.341667; Fleiss kappa=0.077003.
    - Multiclass pairwise exact agreement range: 0.083333–0.475000.
    - Binary: eligible N=112; excluded N=8 for unresolved `UNCERTAIN` values;
      observed agreement=0.505952; Fleiss kappa=-0.022925.
    - Binary pairwise agreement range: 0.258929–0.655462.

    The binary projection and all confirmatory analyses are separately frozen
    in the human protocol. No AI label is used as human-reference evidence.
    '''
).strip()


PROTOCOL = dedent(
    '''
    # Human Reference Standard Protocol

    Protocol version: `human_v1`
    Status: preregistered and frozen before human labels are collected.
    Scope: independent offline cybersecurity behavior classification of the
    exact frozen V3 set of 120 opaque cases.

    ## 1. Purpose and evidence boundary

    This study creates an independently collected human reference standard.
    The existing V3 instrument and its 120 case IDs are immutable. Human
    raters label only the observable evidence and neutral context supplied in
    their packet. They must not infer source, honeypot status, authorization,
    or actor intent from formatting or context.

    The three valid V3 AI runs are exploratory reliability evidence only. They
    are not human raters, are not a reference standard, and cannot be
    majority-voted or adjudicated into truth. AI labels must not influence
    human raters or adjudicators. The invalid run remains quarantined.

    ## 2. Human study design

    There are three independent primary human raters:

    - `human_rater_01`
    - `human_rater_02`
    - `human_rater_03`

    Preferred expertise includes cybersecurity, systems security, incident
    response, penetration testing, digital forensics, or security research,
    with the ability to interpret Linux commands, shell behavior, privilege
    operations, reconnaissance, exploitation, credential or data access, and
    persistence. Primary raters work independently. No discussion is permitted
    before all initial ratings are frozen.

    A fourth expert, `human_adjudicator_01`, adjudicates every case that is not
    a unanimous 3/3 non-`UNCERTAIN` primary result. The adjudicator is not one
    of the primary raters if avoidable.

    Pseudonymous IDs are used in all research artifacts. Personal names and
    unnecessary personal information are not collected.

    ## 3. Metadata and contamination declaration

    The metadata form records only pseudonymous rater ID, security expertise
    category, approximate years of security experience, Linux familiarity,
    incident-response familiarity, offensive-security familiarity, prior
    familiarity with RAGIN, prior access to Chrollo/Laya outputs, conflict or
    contamination declaration, and annotation start and finish timestamps.

    Before annotation, every primary rater and the adjudicator must answer:

    1. Have you seen any Chrollo predictions for these cases?
    2. Have you seen any Laya predictions for these cases?
    3. Have you seen prior AI annotations for these cases?
    4. Have you seen another human rater's annotations?
    5. Have you previously worked directly on constructing this exact 120-case
       evaluation set?

    Any `YES` is recorded and flagged for PI review before inclusion; it does
    not automatically delete the rater. The coordinator maps the neutral
    declaration fields in the handoff form to these five questions.

    ## 4. Frozen taxonomy

    The taxonomy cannot change after human labeling begins:

    - `BENIGN`: observable routine or defensive administration or information
      lookup with no defensible evidence of attack behavior.
    - `RECON`: observable enumeration or probing reasonably associated with
      discovery or preparation for attack.
    - `SUSPICIOUS`: observable concerning behavior that does not justify a
      stronger category.
    - `EXPLOITATION`: observable active exploitation, payload execution,
      injection, vulnerability abuse, malicious download-and-execute, or
      equivalent.
    - `PRIVILEGE_ESCALATION`: observable attempt to gain privileges beyond the
      current level.
    - `DATA_ACCESS`: observable reading, collecting, staging, or exfiltration
      of credentials, tokens, private keys, databases, or other data.
    - `PERSISTENCE`: observable creation of a durable foothold.
    - `OTHER_ATTACK`: clearly adversarial behavior not better represented by
      another attack category.
    - `UNCERTAIN`: evidence insufficient to assign a defensible category.

    Critical labeling rules:

    - Label observed behavior, not presumed actor intent.
    - Do not infer source, honeypot status, or authorization merely from
      formatting.
    - Natural-language discussion of an attack technique is not execution.
    - A standard Linux command alone is not automatically malicious.
    - Do not balance categories or use expected prevalence.
    - `UNCERTAIN` is valid when evidence is genuinely insufficient.

    ## 5. Binary analysis boundary

    Human raters and the adjudicator are not shown the binary projection. The
    locked internal mapping is:

    - `BENIGN` -> `NEGATIVE`.
    - `RECON`, `SUSPICIOUS`, `EXPLOITATION`, `PRIVILEGE_ESCALATION`,
      `DATA_ACCESS`, `PERSISTENCE`, and `OTHER_ATTACK` -> `POSITIVE`.
    - `UNCERTAIN` -> unresolved and excluded from the primary binary reference
      until adjudication.

    ## 6. Primary annotation packet and output

    Each primary rater receives all 120 cases in an independent deterministic
    order. The packet contains only an opaque `case_id`, frozen `evidence`,
    frozen neutral `context`, and empty `label` and `note` fields. Evidence and
    context are byte-equivalent to the frozen V3 instrument. Raters must
    annotate all 120 cases independently.

    For each case, complete:

    ```json
    {"case_id": "...", "label": "...", "note": "short evidence-based reason"}
    ```

    Notes must be short and evidence-based. Labels must be one of the nine
    frozen taxonomy values. The human output schema requires exactly 120 unique
    frozen case IDs, no blank labels, and no extra fields.

    ## 7. Predeclared agreement statistics

    Before labels are collected, the following are frozen for the three
    primary raters:

    - Multiclass raw exact agreement.
    - Pairwise exact agreement and pairwise Cohen's kappa.
    - Fleiss' kappa.
    - Category-specific disagreement.
    - Binary eligible N, excluded N, observed agreement, and Fleiss' kappa.

    For the pre-adjudication binary reliability calculation, use only cases
    where all three initial ratings are non-`UNCERTAIN`. Report exclusions
    explicitly; never silently recode `UNCERTAIN`.

    ## 8. Predeclared adjudication

    After all three primary annotation files are frozen:

    - If all three primary humans give the same non-`UNCERTAIN` multiclass
      label, mark `UNANIMOUS_REFERENCE`, use that exact label, and do not send
      the case to the adjudicator.
    - Every other case is sent to the blinded adjudicator, including 2/3 exact
      agreement, three different labels, any `UNCERTAIN`, binary disagreement,
      or fine-grained category disagreement.

    The adjudicator receives only the opaque case ID, evidence, neutral
    context, and anonymized `RATER_A`, `RATER_B`, and `RATER_C` labels with
    their short notes. The adjudicator must not receive AI labels, model
    predictions or names, scores, source provenance, expected answers, or
    previous correctness results. The adjudicator assigns one of the nine
    taxonomy labels or `UNRESOLVED`, with a short rationale.

    Final reference construction is immutable:

    - 3/3 exact non-`UNCERTAIN`: `UNANIMOUS_PRIMARY_HUMANS`.
    - Non-unanimous case adjudicated to a taxonomy label:
      `BLINDED_HUMAN_ADJUDICATION`.
    - Adjudicator returns `UNRESOLVED`: `reference_status=UNRESOLVED`, with no
      forced truth label.

    Preserve all three original ratings, original notes, the adjudicator
    decision, and the adjudication rationale. Never overwrite primary ratings.

    ## 9. Confirmatory eligibility gate

    Before labels exist, primary binary confirmatory analysis is eligible only
    if all of the following hold:

    - At least 100 of 120 cases receive a resolved human reference label.
    - At least 90 cases remain evaluable after the binary reference projection.
    - All model predictions were frozen before human reference creation.
    - No threshold or decision rule changed after labels.

    If fewer than 100 cases resolve, binary model comparison is exploratory.
    Multiclass results are descriptive for all resolved cases. If fewer than
    90 cases receive resolved multiclass references, multiclass model
    comparison is explicitly exploratory. Human agreement is always reported.
    AI agreement cannot satisfy any threshold.

    ## 10. Locked endpoints and paired test

    On the same resolved paired cases, report balanced accuracy as primary.
    Secondary binary metrics are accuracy, macro-F1, precision,
    recall/sensitivity, specificity, FPR, FNR, and the confusion matrix.
    Where applicable, multiclass metrics are macro-F1, per-class precision,
    per-class recall, and the confusion matrix. All `UNCERTAIN` and
    `UNRESOLVED` exclusions are reported with counts.

    For the paired binary Chrollo-vs-Laya comparison use exact two-sided
    McNemar/binomial treatment when the discordant count is small. Define:

    - `C`: Chrollo wrong, Laya correct.
    - `H`: Chrollo correct, Laya wrong.

    Report `C`, `H`, `C+H`, exact p-value, and absolute paired accuracy
    difference. Absence of significance is not interpreted as equivalence.

    ## 11. Locked bootstrap

    Use paired bootstrap only. Each of 10,000 replicates resamples the same
    case IDs jointly for the human reference, Chrollo result, and Laya result;
    models are never bootstrapped independently. Report 95% percentile CIs for
    balanced accuracy, accuracy, macro-F1, sensitivity, specificity, and
    paired metric differences. If verified session groups later support
    clustered resampling, report cluster bootstrap only as a sensitivity
    analysis. Do not invent session groups.

    ## 12. Locked gated policy

    The existing gate remains Chrollo confidence < 0.65 for invoking Laya.
    Do not change or optimize this threshold on human labels. Unless its
    scientific basis is independently justified with development data, all
    gated-policy results are labeled `PREREGISTERED EXPLORATORY` and are not
    promoted to primary confirmatory evidence because of favorable results.

    ## 13. Stop boundary

    This freeze ends before label collection. No human annotation, simulated
    judgment, adjudication case generation, prediction access, label join,
    threshold tuning, model execution, or confirmatory analysis is performed
    under this handoff.
    '''
).strip()


CONFIRMATORY = dedent(
    '''
    # Confirmatory Analysis Preregistration

    Status: locked before human labels are collected. This document defines
    analysis only; it does not contain human labels or case-level model output.

    ## Reference eligibility

    The primary binary comparison is confirmatory only when at least 100 of 120
    cases have a resolved human reference and at least 90 cases remain
    evaluable after the locked binary projection. The model outputs must have
    been frozen before reference creation, and no threshold or decision rule
    may change after labels. Below 100 resolved cases, binary comparison is
    exploratory. Multiclass results are descriptive for resolved cases and are
    exploratory as a model comparison below 90 resolved multiclass references.

    `UNCERTAIN` is unresolved/excluded from primary binary evaluation until
    adjudication. `UNRESOLVED` has no forced label. Every exclusion is counted.

    ## Locked projection

    `BENIGN` maps to `NEGATIVE`. `RECON`, `SUSPICIOUS`, `EXPLOITATION`,
    `PRIVILEGE_ESCALATION`, `DATA_ACCESS`, `PERSISTENCE`, and `OTHER_ATTACK`
    map to `POSITIVE`. `UNCERTAIN` is unresolved/excluded until adjudication.

    ## Endpoints

    Primary binary metric: balanced accuracy.

    Secondary binary metrics: accuracy, macro-F1, precision,
    recall/sensitivity, specificity, FPR, FNR, and confusion matrix.

    Multiclass metrics where applicable: macro-F1, per-class precision,
    per-class recall, and confusion matrix. Report all `UNCERTAIN` and
    `UNRESOLVED` exclusions explicitly.

    ## Paired comparison

    Compare Chrollo and Laya on the same human-reference-labeled case IDs with
    McNemar. Let `C` be Chrollo wrong/Laya correct and `H` be Chrollo
    correct/Laya wrong. Report `C`, `H`, `C+H`, exact two-sided p-value when
    the discordant count is small, and the absolute paired accuracy
    difference. Non-significance is not equivalence.

    ## Bootstrap

    Use paired bootstrap with 10,000 replicates. Resample the same case IDs
    jointly for the human reference and both model results. Report 95%
    percentile confidence intervals for balanced accuracy, accuracy, macro-F1,
    sensitivity, specificity, and paired metric differences. Cluster bootstrap
    is a sensitivity analysis only if verified session groups are available;
    none may be invented.

    ## Gated policy

    Preserve the existing invocation gate: Chrollo confidence < 0.65. Do not
    optimize it on human labels. Unless independently justified with
    development data, gated-policy results are labeled `PREREGISTERED
    EXPLORATORY`, not primary confirmatory evidence.

    ## Non-execution rule

    No endpoint, paired test, bootstrap, threshold tuning, model execution, or
    model/reference join is run during this preregistration handoff.
    '''
).strip()


HUMAN_INSTRUCTIONS = dedent(
    '''
    # Independent Offline Cybersecurity Behavior Classification

    This packet contains 120 cases. Complete every case independently and do
    not discuss cases with other raters before your initial file is frozen.

    For each case, select exactly one label from the nine labels below and add
    a short evidence-based note:

    - `BENIGN`
    - `RECON`
    - `SUSPICIOUS`
    - `EXPLOITATION`
    - `PRIVILEGE_ESCALATION`
    - `DATA_ACCESS`
    - `PERSISTENCE`
    - `OTHER_ATTACK`
    - `UNCERTAIN`

    Label observed behavior, not presumed intent. Do not infer source,
    honeypot status, or authorization from formatting. Natural-language
    discussion of a technique is not execution. A standard Linux command alone
    is not automatically malicious. Do not balance categories or use expected
    prevalence. Use `UNCERTAIN` when the supplied evidence is genuinely
    insufficient.

    Keep each note short and tied to the evidence shown in the case. Do not
    add fields, change case IDs, reorder the frozen text inside a case, or omit
    a case. The completed output for each case is:

    ```json
    {"case_id": "...", "label": "...", "note": "short evidence-based reason"}
    ```

    Return all 120 completed items under the required output schema. The
    coordinator will freeze the file before any discussion or later review.
    '''
).strip()


ADJUDICATOR_INSTRUCTIONS = dedent(
    '''
    # Blinded Human Adjudicator Instructions

    This workspace is intentionally empty at preregistration. Adjudication
    case packets may be generated only after all three primary annotation files
    are frozen.

    For each assigned disagreement case, review only the opaque case ID,
    frozen evidence, neutral context, and anonymized `RATER_A`, `RATER_B`, and
    `RATER_C` labels with their short notes. Assign one frozen taxonomy label or
    `UNRESOLVED` and write a short evidence-based rationale.

    Work independently. Do not seek an expected answer, infer source or
    authorization, or use information outside the supplied case materials and
    the frozen taxonomy. Preserve the three original ratings and notes; never
    overwrite them.
    '''
).strip()


SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "human_annotation_schema_v1",
    "title": "Human annotation output schema v1",
    "type": "object",
    "additionalProperties": False,
    "required": ["rater_id", "annotation_protocol_version", "packet_sha256", "items"],
    "properties": {
        "rater_id": {"type": "string", "pattern": "^human_rater_0[1-3]$"},
        "annotation_protocol_version": {"const": "human_v1"},
        "packet_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "items": {
            "type": "array",
            "minItems": EXPECTED_INSTRUMENT_CASE_COUNT,
            "maxItems": EXPECTED_INSTRUMENT_CASE_COUNT,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["case_id", "label", "note"],
                "properties": {
                    "case_id": {"type": "string", "minLength": 1},
                    "label": {"enum": TAXONOMY, "type": "string"},
                    "note": {"type": "string", "minLength": 1},
                },
            },
        },
    },
    "x-validation": [
        "items must contain the identical frozen 120-case ID set exactly once",
        "labels must be non-blank and members of the frozen taxonomy",
    ],
}


def metadata_form(rater_id: str, role: str) -> dict[str, object]:
    return {
        "form_version": "human_metadata_v1",
        "role": role,
        "pseudonymous_rater_id": rater_id,
        "fields": {
            "security_expertise_category": "",
            "approximate_years_security_experience": "",
            "linux_familiarity": "",
            "incident_response_familiarity": "",
            "offensive_security_familiarity": "",
            "prior_familiarity_with_ragin": "",
            "prior_access_to_named_system_outputs": "",
            "conflict_or_contamination_declaration": "",
            "annotation_start_timestamp": "",
            "annotation_finish_timestamp": "",
        },
        "allowed_values": {
            "linux_familiarity": ["low", "moderate", "high"],
            "incident_response_familiarity": ["low", "moderate", "high"],
            "offensive_security_familiarity": ["low", "moderate", "high"],
            "prior_familiarity_with_ragin": ["yes", "no"],
            "prior_access_to_named_system_outputs": ["yes", "no"],
        },
        "contamination_question_ids": [
            "Q1_named_source_1_exposure",
            "Q2_named_source_2_exposure",
            "Q3_prior_machine_annotation_exposure",
            "Q4_other_human_annotation_exposure",
            "Q5_exact_case_set_construction_exposure",
        ],
        "coordinator_note": (
            "Complete the five contamination questions defined in protocol "
            "section 3 before annotation; disclose any YES for PI review."
        ),
    }


def make_packet(instrument: list[dict[str, str]], rater_id: str) -> list[dict[str, str]]:
    items = [
        {
            "case_id": item["id"],
            "evidence": item["evidence"],
            "context": item["context"],
            "label": "",
            "note": "",
        }
        for item in instrument
    ]
    random.Random(SEEDS[rater_id]).shuffle(items)
    return items


def write_packet_csv(path: Path, packet: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["case_id", "evidence", "context", "label", "note"]
        )
        writer.writeheader()
        writer.writerows(packet)


def build() -> None:
    instrument, freeze_sources = check_source_freezes()
    original_packet_hashes = {
        name: sha256(ROOT / f"results/laya_research/rater_packets_v3/{name}.json")
        for name in ["r1", "r2", "r3"]
    }
    if original_packet_hashes != EXPECTED_FREEZE_PACKET_HASHES:
        raise AssertionError("original V3 rater packet hash mismatch")

    write_text(ROOT / "docs/laya_integration/V3_AI_LABEL_STATUS.md", AI_STATUS)
    write_text(
        ROOT / "docs/laya_integration/HUMAN_REFERENCE_STANDARD_PROTOCOL.md", PROTOCOL
    )
    write_text(
        ROOT / "docs/laya_integration/CONFIRMATORY_ANALYSIS_PREREGISTRATION.md",
        CONFIRMATORY,
    )
    write_json(ROOT / "results/laya_research/human_annotation_schema_v1.json", SCHEMA)

    packet_dir = ROOT / "results/laya_research/human_rater_packets_v3"
    packet_dir.mkdir(parents=True, exist_ok=True)
    write_text(packet_dir / "HUMAN_RATER_INSTRUCTIONS.md", HUMAN_INSTRUCTIONS)

    packets: dict[str, list[dict[str, str]]] = {}
    packet_hashes: dict[str, str] = {}
    for rater_id in SEEDS:
        packet = make_packet(instrument, rater_id)
        packets[rater_id] = packet
        packet_path = packet_dir / f"{rater_id}.json"
        write_json(packet_path, packet)
        write_packet_csv(packet_dir / f"{rater_id}.csv", packet)
        packet_hashes[rater_id] = sha256(packet_path)

    handoff_root = ROOT / "human_handoff"
    for rater_id, short_id in zip(SEEDS, ["rater01", "rater02", "rater03"]):
        folder = handoff_root / short_id
        folder.mkdir(parents=True, exist_ok=True)
        write_json(folder / "packet.json", packets[rater_id])
        write_text(folder / "HUMAN_RATER_INSTRUCTIONS.md", HUMAN_INSTRUCTIONS)
        write_json(folder / "RATER_METADATA_FORM.json", metadata_form(rater_id, "primary"))
        template = {
            "rater_id": rater_id,
            "annotation_protocol_version": "human_v1",
            "packet_sha256": packet_hashes[rater_id],
            "items": [
                {"case_id": item["case_id"], "label": "", "note": ""}
                for item in packets[rater_id]
            ],
        }
        write_json(folder / "annotation_template.json", template)

    adjudicator_folder = handoff_root / "adjudicator"
    adjudicator_folder.mkdir(parents=True, exist_ok=True)
    write_text(adjudicator_folder / "ADJUDICATOR_INSTRUCTIONS.md", ADJUDICATOR_INSTRUCTIONS)
    write_json(
        adjudicator_folder / "ADJUDICATOR_METADATA_FORM.json",
        metadata_form("human_adjudicator_01", "adjudicator"),
    )

    handoff_dirs = {
        "rater01": [
            "packet.json",
            "HUMAN_RATER_INSTRUCTIONS.md",
            "RATER_METADATA_FORM.json",
            "annotation_template.json",
        ],
        "rater02": [
            "packet.json",
            "HUMAN_RATER_INSTRUCTIONS.md",
            "RATER_METADATA_FORM.json",
            "annotation_template.json",
        ],
        "rater03": [
            "packet.json",
            "HUMAN_RATER_INSTRUCTIONS.md",
            "RATER_METADATA_FORM.json",
            "annotation_template.json",
        ],
        "adjudicator": ["ADJUDICATOR_INSTRUCTIONS.md", "ADJUDICATOR_METADATA_FORM.json"],
    }
    forbidden_terms = [
        "chrollo",
        "laya",
        "prediction",
        "confidence",
        "prior ai",
        "source provenance",
        "expected class",
        "binary projection",
        "v2",
        "v3 ai",
        "model",
    ]
    integrity_checks: dict[str, object] = {}
    all_handoff_pass = True
    canonical_by_id = {item["id"]: item for item in instrument}
    canonical_ids = set(canonical_by_id)
    for folder_name, expected_files in handoff_dirs.items():
        folder = handoff_root / folder_name
        actual_files = sorted(p.name for p in folder.iterdir() if p.is_file())
        exact_files = sorted(expected_files)
        text = "\n".join(
            (folder / name).read_text(encoding="utf-8") for name in actual_files
        ).lower()
        packet = json.loads((folder / "packet.json").read_text(encoding="utf-8")) if folder_name != "adjudicator" else None
        case_ids = [item["case_id"] for item in packet] if packet else []
        packet_content_ok = bool(packet) and all(
            set(item) == {"case_id", "evidence", "context", "label", "note"}
            and item["case_id"] in canonical_by_id
            and item["evidence"] == canonical_by_id[item["case_id"]]["evidence"]
            and item["context"] == canonical_by_id[item["case_id"]]["context"]
            and item["label"] == ""
            and item["note"] == ""
            for item in packet
        )
        if folder_name == "adjudicator":
            checks = {
                "exact_file_set": actual_files == exact_files,
                "forbidden_terms_absent": not any(term in text for term in forbidden_terms),
                "no_adjudication_cases_present": packet is None,
                "no_binary_projection_visible": "binary" not in text and "positive" not in text and "negative" not in text,
            }
        else:
            checks = {
                "exact_file_set": actual_files == exact_files,
                "forbidden_terms_absent": not any(term in text for term in forbidden_terms),
                "exactly_120_cases": packet is not None and len(packet) == 120,
                "unique_case_ids": packet is not None and len(case_ids) == len(set(case_ids)),
                "identical_frozen_case_id_set": packet is not None and set(case_ids) == canonical_ids,
                "evidence_context_v3_equivalent": packet_content_ok,
                "labels_empty": packet is not None and all(item["label"] == "" for item in packet),
                "notes_empty": packet is not None and all(item["note"] == "" for item in packet),
                "no_prediction_fields": packet is not None and all("prediction" not in item and "confidence" not in item for item in packet),
                "no_model_identifiers": packet is not None and all("model" not in item for item in packet),
                "no_binary_projection_visible": "binary" not in text and "positive" not in text and "negative" not in text,
            }
        integrity_checks[folder_name] = checks
        all_handoff_pass = all_handoff_pass and all(checks.values())

    integrity = {
        "schema_version": "human_handoff_integrity_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all_handoff_pass else "FAIL",
        "source_boundary": {
            "canonical_instrument": "results/laya_research/blind_annotation_confirmatory_v3.json",
            "predictions_accessed": False,
            "case_level_ai_labels_accessed": False,
            "ai_labels_used_for_packet_construction": False,
        },
        "canonical_case_count": len(instrument),
        "canonical_case_id_set_sha256": EXPECTED_CASE_ID_SET_SHA256,
        "checks": integrity_checks,
    }
    write_json(ROOT / "results/laya_research/human_handoff_integrity.json", integrity)
    if not all_handoff_pass:
        raise AssertionError("human handoff integrity failed")

    freeze_paths = [
        ROOT / "docs/laya_integration/HUMAN_REFERENCE_STANDARD_PROTOCOL.md",
        packet_dir / "HUMAN_RATER_INSTRUCTIONS.md",
        ROOT / "results/laya_research/human_annotation_schema_v1.json",
        ROOT / "docs/laya_integration/CONFIRMATORY_ANALYSIS_PREREGISTRATION.md",
        ROOT / "results/laya_research/human_handoff_integrity.json",
        ROOT / "results/laya_research/v3_annotation_instrument_freeze.json",
        ROOT / "human_handoff/adjudicator/ADJUDICATOR_INSTRUCTIONS.md",
        ROOT / "human_handoff/adjudicator/ADJUDICATOR_METADATA_FORM.json",
    ]
    freeze_hashes = {str(path.relative_to(ROOT)): sha256(path) for path in freeze_paths}
    for rater_id in SEEDS:
        freeze_hashes[f"results/laya_research/human_rater_packets_v3/{rater_id}.json"] = sha256(
            packet_dir / f"{rater_id}.json"
        )
        freeze_hashes[f"results/laya_research/human_rater_packets_v3/{rater_id}.csv"] = sha256(
            packet_dir / f"{rater_id}.csv"
        )
        short_id = rater_id.replace("human_", "").replace("_", "")
        for name in [
            "packet.json",
            "HUMAN_RATER_INSTRUCTIONS.md",
            "RATER_METADATA_FORM.json",
            "annotation_template.json",
        ]:
            freeze_hashes[f"human_handoff/{short_id}/{name}"] = sha256(
                handoff_root / short_id / name
            )

    freeze = {
        "schema_version": "human_reference_preregistration_freeze_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FROZEN_PRE_ANNOTATION",
        "human_labels_collected": False,
        "human_ground_truth_exists": False,
        "predictions_accessed": False,
        "AI_labels_used_for_reference": False,
        "model_thresholds_changed": False,
        "canonical_v3_instrument_freeze_sha256": sha256(INSTRUMENT_FREEZE),
        "original_v3_rater_packet_sha256": original_packet_hashes,
        "private_shuffle_seeds": SEEDS,
        "rules": {
            "unanimity": "Only 3/3 exact non-UNCERTAIN primary agreement is UNANIMOUS_REFERENCE; no adjudicator.",
            "adjudication": "All other cases are sent to the blinded fourth human adjudicator after all primary files freeze.",
            "UNRESOLVED": "The adjudicator may return UNRESOLVED; no forced truth label is created.",
            "minimum_resolved_sample": "At least 100 of 120 resolved human references for primary binary confirmatory eligibility.",
            "minimum_binary_evaluable": "At least 90 cases after the locked binary projection.",
            "binary_projection": {
                "NEGATIVE": ["BENIGN"],
                "POSITIVE": [
                    "RECON",
                    "SUSPICIOUS",
                    "EXPLOITATION",
                    "PRIVILEGE_ESCALATION",
                    "DATA_ACCESS",
                    "PERSISTENCE",
                    "OTHER_ATTACK",
                ],
                "UNRESOLVED": ["UNCERTAIN", "UNRESOLVED"],
            },
            "McNemar": "Same resolved paired cases; C=Chrollo wrong/Laya correct, H=Chrollo correct/Laya wrong; exact two-sided treatment when discordance is small.",
            "bootstrap": "Paired bootstrap only, 10,000 replicates, same case IDs jointly resampled, 95% percentile CIs.",
            "gated_0.65_policy_status": "PREREGISTERED EXPLORATORY unless independently justified with development data; threshold remains Chrollo confidence < 0.65.",
        },
        "artifact_sha256": freeze_hashes,
        "no_adjudication_cases_generated": True,
        "confirmatory_analysis_run": False,
    }
    write_json(ROOT / "results/laya_research/human_reference_preregistration_freeze.json", freeze)

    if sha256(INSTRUMENT_FREEZE) != freeze["canonical_v3_instrument_freeze_sha256"]:
        raise AssertionError("V3 instrument freeze changed during generation")
    print(json.dumps({
        "status": "PASS",
        "cases": len(instrument),
        "packet_hashes": packet_hashes,
        "instrument_freeze_sha256": sha256(INSTRUMENT_FREEZE),
        "results_freeze_sha256": sha256(RESULTS_FREEZE),
    }, indent=2))


if __name__ == "__main__":
    build()
