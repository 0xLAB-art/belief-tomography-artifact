# RAGIN V4 Evidence-Grounded Deterministic Policy V2

Status: `EVIDENCE_GROUNDED_DETERMINISTIC_V2`, inactive pending explicit independent review.

This is a separately versioned research candidate. Frozen V4 policy code, weights, evaluations, holdouts, and raw records were not changed. No HF-2024 evaluation was run.

## Source-grounded coverage and safety matrix

| Evidence | Directly observed behavior | Inference allowed | Policy V2 action | Safety condition |
|---|---|---|---|---|
| T1082 | system information discovery command pattern | reconnaissance-compatible behavior only | `maximize_recon_surface` with environment-discovery context | abstain on ambiguity |
| T1083 | file/directory discovery command pattern | reconnaissance-compatible behavior only | `maximize_recon_surface` with environment-discovery context | requires command-grounded evidence |
| T1016 | network configuration discovery pattern | network-discovery behavior only | `expose_decoy_internal_topology` with network context | no attacker-intent claim |
| T1053.003 | cron/persistence command pattern | persistence-compatible behavior only | `fake_success_and_return_visits` with persistence indicator | no execution of command |
| T1003/T1552.001 | credential-access evidence and credential context | credential-access-compatible behavior only | `steer_to_honeytoken_credentials` | synthetic credentials only |
| T1105 | transfer/download evidence | transfer behavior; execution only when separately observed | `contain_in_fiction_and_instrument` only with download-execution relationship | transfer alone abstains |
| T1059.004 | Unix shell interpreter | shell use only | baseline/abstain | insufficient intent evidence |
| T1070.004 | file deletion/cleanup | deletion behavior only | baseline/abstain | does not imply malicious intent |
| relationship documents | source-documented relationship text | source relationship only | no direct strategy activation | technique field must be explicit and grounded |
| conflicting, irrelevant, malformed, or unproven evidence | not sufficient for strategy selection | none | baseline/abstain | fail-safe contract |

MITRE technique IDs are not treated as proof of malicious intent. The candidate requires accepted command-grounded evidence, relevant context projection, explicit rule predicates, supporting evidence IDs, an allowed strategy, and a recorded reason.

## Implementation

`ragin/decision_fusion_v4/policy_v2.py` implements `EvidenceGroundedDeterministicPolicyV2`. It is not registered in `build_selector()` and is not active in default or deployed runtime modes.

Decision traces include gate state/reason, evidence IDs, grounded techniques and behavior tags, context indicators, ambiguity, rule ID, predicate, match result, abstention reason, policy hash, and input digest.

The old deterministic implementation remains unchanged in `ragin/decision_fusion_v4/policy.py` and `ragin/decision_fusion_v4/benchmark.py`.

## Synthetic validation

Fresh synthetic fixtures covered discovery, topology, persistence, credentials, transfer with execution relationship, benign administration, transfer-only ambiguity, shell-only ambiguity, conflicting evidence, missing provenance, all six substantive strategies, invalid evidence, verifier rejection, HITL/commit rollback, and baseline behavior.

Results: 159 passed, 0 failed. No shell command was executed.

All six non-baseline strategy paths were consumed by the substantive generator and accepted by verifier/HITL on their positive synthetic fixtures. Rejected candidates produced `STRATEGY_CONSUMED_BUT_REJECTED` traces and did not commit fictional generator state. Invalid evidence selected baseline and produced an explicit safe outcome.

This validates contract behavior only; it is not an effectiveness evaluation.

## Review checklist

- [x] Frozen V4 policy and weights unchanged
- [x] Candidate inactive by default
- [x] No technique relabeling or intent fabrication
- [x] Evidence IDs and provenance retained
- [x] Ambiguous and insufficient context abstains
- [x] Transfer-only behavior does not imply execution
- [x] Invalid/conflicting evidence fails safe
- [x] Baseline regression tested
- [x] Verifier/HITL/accepted-only commit tested
- [ ] Independent human scientific review
- [ ] Separate candidate freeze approving activation
- [ ] Fresh future evaluation registration

External and human review remain pending. Automated tests do not replace independent scientific review.

## Future evaluation hypotheses

1. A future preregistered validation can test whether explicit Don V2 behavior-to-rule mappings increase observable non-baseline selection without treating selection frequency as correctness.
2. Complete per-attempt serving traces can test whether selected strategies are consumed and served rather than falling back.
3. Independent evidence-quality and policy-quality references are required before evaluating correctness or superiority.

## Artifacts and hashes

Directory: `results/decision_fusion_v4/policy_contract_serving_observability_v1/`

- `case_reconciliation.json`: `63f13b1ef2b14d5052ff430975d4f10d01590dab6bf7a99958d401265b322cb0`
- `policy_contract_audit.json`: `4466c8fe816291bf0f8e05c7a872b11314559146e43fd1b4ff2b2e93bd41c137`
- `proposed_policy_coverage_specification_v1.json`: `6dee03158a1a5d44ff3b10729413c3c0c2947096d6da6cc1599229a6db1d494c`
- `synthetic_validation.json`: `f3637e1f81ff186241b85fce80ce70cecd4f904c5d3d3b6c4231d7002114ad0c`
- `sha256_manifest.json`: `ea950bb342d73eded557f37bdcb3c7d3174b4c64d06c1a87a08c7f93f2c64e6a`

Source hashes:

- `ragin/decision_fusion_v4/policy_v2.py`: `93304c62e3975a0b65e7c534b4e982c3b1e9d4e0360e9be2e35d24ec2ef9b80e`
- `tests/unit/test_policy_v2_candidate.py`: `b453d065b70a10de07d9efddc8b9cd5f800a18ea3e6ff6f16a7fadaaadeb5fc9`
- `ragin/cycle/adapters.py`: `83fe4152db969af8c27fc55a6a531a49e229c5a5a00106a5b880d8c3ebde0256`
- `ragin/cycle/harness.py`: `98ff76913b279a7d052f348922c8de657d2486fdc9348b318c064345fdffcb42`
- Don V2 corpus: `d1a2f015eae91c91702fa9ccc5cdbdb8a074d7cb05e62d93208a30919cb242f4`

Historical raw records remain unchanged at SHA256 `2e674299280764e07b153a6dd8c693d714c154a1b28ee0b56700ac1fca3f6ede`.

Classification: `POLICY_V2_CANDIDATE_READY_FOR_REVIEW`.
