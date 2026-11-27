# RAGIN V4 Substantive Final Results

Experiment: `HF2024_SUBSTANTIVE_FINAL_V1`  
Design: family-disjoint, reference-free retrospective validation  
Classification: `SUBSTANTIVE_RETROSPECTIVE_EVALUATION_COMPLETED`

## Scope and freeze

The evaluation used the pinned HF-2024 dataset revision `d201aafbbcbb5347078ca64f06c5428fa6814bc9`, dataset SHA256 `7ea4b916841708c36dbe24f95b882f06335e85ed2e77bdc70ba985c9c9653752`. The 1,458 normalized command families were filtered against both prior 240-case holdouts. The resulting pool contained 1,159 eligible unique families. A deterministic SHA256 rule selected 240 families and one source-group record per family.

The observation unit is one selected source-group record and its observed ordered command sequence. Source groups are not asserted to be native SSH sessions. No semantic balancing, label filtering, policy-based sampling, synthetic fixture, replay record, or previously used exact source record was selected.

The frozen integration SHA256 was `5a20a15da37830ef41d1d21da706a211e8247fdaa7723cdd3f606be9a5054fe5`; the authoritative generator SHA256 was `3c1e0c9f85510adc17758c4f4aded547c57fca8c7aa69fea209790315fdbdae2`. The runtime mode initialization check confirmed baseline uses `HisokaAdapter`, while both substantive modes use `SubstantiveStrategyAdapter` with the existing deterministic or logistic policy arm.

## Holdout and execution

| Measure | Result |
|---|---:|
| Unique cases | 240 |
| Unique source groups | 240 |
| Unique normalized command families | 240 |
| Prior-family overlap | 0 |
| Baseline executions | 240/240 |
| Deterministic executions | 240/240 |
| Logistic executions | 240/240 |
| Total arm-case records | 720/720 |
| Duplicate case-arm pairs | 0 |

All 720 records were produced by the matched runtime path with attacker commands treated as inert input data. No external generation calls, AWS operations, networking changes, or captured-command execution occurred.

## Policy and evidence observations

| Arm | Gate states | Selected strategies |
|---|---|---|
| Baseline | `NOT_APPLICABLE_BASELINE`: 240 | `baseline`: 240 |
| Deterministic | `LOW_RELEVANCE`: 234; `VALID_EVIDENCE`: 6 | `baseline`: 240 |
| Logistic | `LOW_RELEVANCE`: 234; `VALID_EVIDENCE`: 6 | `baseline`: 234; `maximize_recon_surface`: 6 |

Strategy disagreement was 0/240 for baseline versus deterministic, 6/240 for baseline versus logistic, and 6/240 for deterministic versus logistic. This is a strongly gate-limited and collapsed policy observation, not a policy-correctness result.

For the 480 V4 records, the raw delivery flag was true in 477 and `NOT_VERIFIABLE` in 3. That raw flag is not interpreted as substantive consumption on fail-safe records because the baseline fallback response can carry legacy metadata. Observed substantive generator consumption was 3/480; served consumption was `NOT_VERIFIABLE` for 3/480; 474/480 were baseline or fail-safe fallback serves. The 3 observed substantive serves were logistic `maximize_recon_surface` cases.

Fallback counts were 468 invalid-evidence-gate fallbacks and 6 baseline-policy fallbacks. Three additional policy-valid logistic cases reached a verifier fallback serve on a second attempt; their final served strategy consumption and commit event remain `NOT_VERIFIABLE`.

## Behavioral comparisons

| Matched comparison | Raw response changes | Changes after decorative-marker removal | State-transition hash changes |
|---|---:|---:|---:|
| Baseline vs deterministic | 0/240 | 0/240 | `NOT_VERIFIABLE` |
| Baseline vs logistic | 3/240 | 3/240 | `NOT_VERIFIABLE` |
| Deterministic vs logistic | 3/240 | 3/240 | `NOT_VERIFIABLE` |

The three residual logistic differences were substantive fictional recon responses, not suffix-only or formatting-only changes. The corresponding action trace was `inspect`, with fictional recon-surface content and accepted fictional-state transitions. Three logistic records exposed before/proposed/after fictional-state hashes. Cross-arm state-transition differences are `NOT_VERIFIABLE` because no matched pair had observable state hashes on both arms. No template-ID comparison was verifiable because the runtime did not emit a stable template-ID field for these records.

These results show limited observed substantive generator influence in this cohort. They do not establish policy quality, superiority, deception effectiveness, or attacker engagement.

## Safety and state integrity

| Invariant | Result |
|---|---:|
| Verifier passes | 720/720 |
| Verifier failures | 0 |
| Recorded safety violations | 0 |
| Automatic/gateway HITL approvals | 720/720 |
| Human reviews | 0 |
| Accepted fictional-state commits | 3 |
| Rejected fictional-state commits | 0 observed |
| Commit events not verifiable | 717 |
| Real attacker commands executed | 0 |
| Duplicate case-arm pairs | 0 |
| Cross-arm fictional-state reuse observed | No |

Verifier passes and automatic approvals are observed safety invariants. They do not verify unobserved production serving or commit behavior. Full commit observability was absent for baseline and fail-safe fallback responses.

## Limitations and interpretation

Runtime correctness is supported by the frozen implementation, mode-initialization check, 201-test regression suite, and complete arm-case execution. Substantive generator influence is supported only for the 3 served logistic cases whose V1 generator metadata, action, fictional state hashes, and accepted commit were all observable.

Policy selection quality was not evaluated because no independent reference judgments were available. Real-world attacker engagement was not evaluated. The corpus is retrospective and drawn from the same HF-2024 source dataset; family exclusion reduces direct overlap with the two prior holdouts but does not make the evidence independent prospective field data. The large `LOW_RELEVANCE` gate fraction and deterministic single-strategy collapse limit behavioral variation. Artificial follow-up probes were not used.

Two earlier runner attempts were preserved as aborted and excluded: a 401-record detached-process interruption and a 142-record performance-limited attempt. The final attempt completed all 720 case-arm executions; a post-execution path-serialization defect was corrected without rerunning or merging records. The final raw freeze contains only the complete 720-record attempt.

## Reproducibility artifacts

All files below are additive under `results/decision_fusion_v4/hf2024_substantive_final_v1/`:

- `holdout_freeze.json`, SHA256 `a07ed246966c0b8f3fa7718438822cafe227fe64b1e40f9ce326d03ebd0ac97d`
- `protocol_freeze.json`, SHA256 `0d638e1c8e4d245edbff637131c9d51d93186f5f47bb298f42e0949bb3a64178`
- `implementation_environment_freeze.json`, SHA256 `cd7547324ed3f9e1bb82ee70fbd2c54e585c7ac234a62199df66eb0bf515c900`
- `raw_execution_records_final_attempt_003.jsonl`, SHA256 `4028864ccef805a5944215bf86ee29af6c40635b6e026702a5c2777d9ad91b26`
- `raw_execution_freeze.json`, SHA256 `627cfdd37e84c7f8d59382d2e734abf096f090b585f63f749e9632319224daea`
- `locked_substantive_behavioral_analysis.json`, SHA256 `95018ad994220fa14936c6d8541190286fe3f90a277c25027a6ec080c2478204`
- `sha256_manifest.json`, SHA256 `f35caff28a516e05646d693b4dcfcf7e8e1cde4fc5ff3dd5e4a489339d29cea6`

The complete implementation and artifact hash manifest is authoritative. Historical V4 and HF-2024 freezes were not modified.

## Claims boundary

- Runtime correctness: evaluated.
- Substantive generator influence: observed in 3 matched logistic cases only.
- Fictional-state differences: observed in the same 3 matched cases.
- Policy selection quality: **NOT EVALUATED**.
- Real-world attacker engagement: **NOT EVALUATED**.
- Policy superiority or effectiveness: **not claimed**.
