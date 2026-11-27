# Step 3 Evidence Reference Gate Audit (2026-10-14)

## Decision

`REFERENCE_PENDING_REVIEWER_INPUT` at audit time; resolved later the same day — see `docs/artifact_audit/STEP3_REFERENCE_FREEZE_AND_LOCKED_ANALYSIS_2026-10-14.md` (`REFERENCE_FROZEN_AI_DERIVED`, single fixed-model reviewer, explicitly not human ground truth). Step 3 could not pass its reference gate from the artifacts frozen at the time of this audit. The 120-case blind packet is intact and excludes system Judge/Gate outputs, but it contains no completed candidate or bundle annotations. No evidence-support labels, correctness metrics, or arm comparisons were created in this step.

This is a packet/provenance audit, not an evidence-support reference and not human ground truth. At the time of this audit Step 3 remained open and the locked analysis was deferred until a reference had been completed and frozen under an authorized annotation protocol. That condition was later met under the separately frozen AI-derived protocol V2.2; see `STEP3_REFERENCE_FREEZE_AND_LOCKED_ANALYSIS_2026-10-14.md` for the freeze verification, locked analysis, and decision answers.

## Scope and blindness

The case-level artifact inspected was `results/evidence_judge_real_data_ablation_v1/blinded_reference_packet.json`. During later method discovery, the coordinator also read aggregate `descriptive_execution_summary.json` and `final_paired_audit.json`; this is disclosed here and in the annotation protocol. The matched arm output and downstream case-level comparison remain unopened. The packet declares `decisions_omitted`, `judge_outputs_omitted`, and `gate_outputs_omitted` as true. Its case records contain the observed command, available context, behavioral claim, retrieved candidates, and blank review slots. The three AI raters receive only the separately frozen case/context/claim/candidate batches, never those aggregate summaries or any system output.

The packet contains 120 unique case IDs and 947 candidate slots (1 case with 1 candidate, 2 with 5 candidates, and 117 with 8 candidates). All 120 bundle review structures are unfilled; all 947 candidate review structures are unfilled. Thus the existing packet is an annotation instrument, not a completed reference.

## Integrity checks

The frozen packet hash is `975f24fca75b0deb8d930252294ddf729eff850d715f87dc8bcac0706c4aacb5`, matching its value in `results/evidence_judge_real_data_ablation_v1/sha256_manifest.json`. The protocol freeze hash is `fa5a7908b8d131b3db2a32b0330ab1713beda10008aa6760e50843804837d5b4`, also matching the manifest. Five packet/input artifacts covered by the manifest were rehashed with no mismatch; arm-output artifacts were intentionally excluded from this verification read. The manifest itself has SHA256 `ccb8087f03eafa2cf39a431ec7612ee1496ea054c2952ec2061bba301460de2c`.

The manifest and protocol both state `REFERENCE_UNAVAILABLE`. The protocol explicitly bars self-generated labels, Judge outputs, Gate outcomes, and prior model outputs from serving as reference labels. The annotation guide requires candidate and bundle labels with source/document citations. No completed reviewer files or adjudication records are present in the reviewed packet package.

## Required next input

Complete and freeze the candidate and bundle reviews under the existing annotation guide, with source/document citations for every non-`UNKNOWN` decision. Use independent reviewers and adjudicate disagreements if a human reference is sought. If the study instead uses an AI-derived reference, freeze the separate protocol, fixed model identity/assignment, complete reviewer outputs, disclosure of dependence, and restricted claim language before joining any arm outcomes. Preserve unresolved evidence as `UNKNOWN`.

Only after the reference freeze may the existing retrospective arm outputs be joined for the planned descriptive analysis. The cohort must not be reused as a new confirmatory holdout or for post hoc model selection presented as confirmatory performance.

## Reproduction

- Workspace: `/home/elaref/Documents/research/ragin/RAGIN-Retrieval-Augmented-Honeypot-Intelligence`
- Packet: `results/evidence_judge_real_data_ablation_v1/blinded_reference_packet.json`
- Protocol: `results/evidence_judge_real_data_ablation_v1/protocol_freeze.json`
- Annotation guide: `results/evidence_judge_real_data_final_paired_audit_v1/annotation_guide.md`
- Packet schema: `ragin.evidence_judge_blinded_reference_packet.v1`
- Packet cases / unique IDs / candidate slots: `120 / 120 / 947`
- Completed candidate reviews / bundle reviews: `0 / 0`
- Reference decision at audit time: `REFERENCE_PENDING_REVIEWER_INPUT`
- Resolution (2026-10-14): `REFERENCE_FROZEN_AI_DERIVED` under protocol V2.2; see `STEP3_REFERENCE_FREEZE_AND_LOCKED_ANALYSIS_2026-10-14.md`
