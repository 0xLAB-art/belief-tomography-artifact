# RAGIN V4 Policy V2 Independent Review Packet

Status: `POLICY_V2_READY_FOR_INDEPENDENT_REVIEW`

This packet reviews the inactive `EVIDENCE_GROUNDED_DETERMINISTIC_V2` candidate. It is an automated provenance, rule-coverage, and synthetic-safety review package; it is not a human scientific review and contains no fabricated human annotations.

## Provenance and activation status

The candidate source is verified at SHA256 `93304c62e3975a0b65e7c534b4e982c3b1e9d4e0360e9be2e35d24ec2ef9b80e`. The Don V2 command-aware corpus is verified at SHA256 `d1a2f015eae91c91702fa9ccc5cdbdb8a074d7cb05e62d93208a30919cb242f4`.

Policy V2 is not registered as the deployed selector and remains inactive. The frozen V4 policy source remains available at SHA256 `9d3862d13ab3c5679b80935e37d3ff4ee0795fa56a95f28a56c58074d7e1261d`. No HF-2024 records were used as review examples and no new evaluation was run.

The pre-existing manifest at `results/decision_fusion_v4/policy_contract_serving_observability_v1/sha256_manifest.json` currently hashes to `ea950bb342d73eded557f37bdcb3c7d3174b4c64d06c1a87a08c7f93f2c64e6a`. A preceding recorded hash is `2b55fa69cdbfc9e97eaac4e1949e919b5727a4ccf427a809793451aaa06c856e`. The file is untracked in the current worktree, so Git cannot establish the mutation history. Both hashes and that limitation are preserved in `manifest_mutation_audit.json`; the old manifest was not rewritten by this review packet.

One manifest limitation is explicit: its source list did not originally include the Don V2 corpus. This new packet records the corpus hash independently.

## Automated rule-coverage review

| Rule | Required observed evidence and context | Strategy | Safe abstention | Source basis |
|---|---|---|---|---|
| `DONV2_T1105_EXECUTION_RELATIONSHIP` | Grounded T1105, current/preceding command projection, and an observed download-to-execution relationship | `contain_in_fiction_and_instrument` | Transfer alone, ambiguity, conflict, invalid evidence, or missing relationship | MITRE T1105 and Don V2 relationship evidence |
| `DONV2_CREDENTIAL_CONTEXT` | Grounded T1003 or T1552.001 plus credential indicator or credential-path context | `steer_to_honeytoken_credentials` | Technique without command context, ambiguity, conflict, or invalid evidence | MITRE T1552.001 and Don V2 command evidence |
| `DONV2_CRON_PERSISTENCE` | Grounded T1053.003 plus a persistence indicator and command context | `fake_success_and_return_visits` | Crontab text without persistence context, ambiguity, conflict, or invalid evidence | MITRE T1053.003 and Don V2 command evidence |
| `DONV2_NETWORK_TOPOLOGY` | Grounded T1016 plus network-path and environment-discovery context | `expose_decoy_internal_topology` | Network text without network context, ambiguity, conflict, or invalid evidence | MITRE T1016 and Don V2 command evidence |
| `DONV2_DISCOVERY_SURFACE` | Grounded discovery evidence plus an environment-discovery indicator and command context | `maximize_recon_surface` | Discovery technique without observed discovery context, ambiguity, conflict, or invalid evidence | MITRE discovery technique sources and Don V2 command evidence |
| `DONV2_BENIGN_ADMINISTRATION` | Valid gate, benign classification, informational severity, and no forbidden indicators | `low_intensity_administration` | Any missing/invalid/conflicting evidence or forbidden indicator | Gate and classifier contract |
| `ABSTAIN_UNSUPPORTED_BEHAVIOR` | No higher-priority supported predicate matches | `baseline` | Always fail-safe baseline | Frozen safety contract |

The implemented rules do not treat a technique ID alone as proof of malicious intent. They require command-grounded context, provenance, and a non-ambiguous gate state. Transfer without an independently observed execution relationship, shell alone, deletion alone, and relationship-only documents without technique fields remain baseline/abstain counterexamples.

The main review risks are assumptions that static relationship and indicator fields are reliable observations rather than proof of execution, and that benign classification plus informational severity is sufficient for low-intensity behavior. These are bounded by the required context and fail-safe baseline, but require independent human review before activation.

## Synthetic examples and safety

The packet includes four machine-readable examples: supported discovery, transfer-only abstention, ambiguous context abstention, and invalid-provenance abstention. The existing synthetic validation covers all six substantive strategy paths, conflicting and irrelevant evidence, missing provenance, verifier rejection, HITL handling, accepted-only fictional-state commit, and complete serving traces. The validation result is 159 passed and 0 failed in the exact review-gate suite.

Required safety conditions are: inert command inputs, no real host mutation, synthetic decoy resources only, mandatory verifier, mandatory HITL policy, accepted-only fictional-state commit, complete per-attempt serving trace, and baseline fail-safe behavior.

## Reviewer fields

The independent reviewer must complete identity, verdict, conflict disclosure, and notes. They are intentionally `null`/`PENDING` in the machine-readable packet. Automated checks must not be interpreted as independent human judgment.

## Package contents

The additive package is `results/decision_fusion_v4/policy_v2_independent_review_packet_v1/` and contains the coverage packet, manifest mutation audit, provenance/integrity record, and SHA256 manifest. Its manifest hash is `3d357e51c0e7c524b9522843fffb69ac6607b7d4f7de19d0c2411a53ede0b818`.

The candidate is ready for independent review, not activation, deployment, policy-correctness claims, superiority claims, or effectiveness claims.
