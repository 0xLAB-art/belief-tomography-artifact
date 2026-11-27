# Research Evidence and Reproducibility Inventory

This inventory records where results come from, what code produced them, and what they can and cannot support. Persisted numbers are not changed or reinterpreted as new measurements.

## Evidence status categories

- **Reproducible diagnostic:** code and local inputs are present, but scope may be closed-world or synthetic.
- **Audited persisted result:** artifact and analysis path are present, but fresh rerun/provider independence is not demonstrated here.
- **Blocked/partial:** the experiment depends on unavailable/refused provider access, missing external labels, or a historical endpoint.
- **Operational trace:** useful for provenance/context, not automatically a benchmark result.

## Inventory

| Claim area | Persisted artifact(s) | Measurement code / inputs | Audit result and limitations |
|---|---|---|---|
| Grounding/ablation mechanisms | `results/ablation_battery.json` | `scripts/ablation_battery.py`; eight deterministic scenarios | Reproducible diagnostic. Arms include no-fiction, no-bait-steer, no-verify, no-approval, and no-graph. No live LLM/gateway calls; demonstrates contract/mechanism behavior, not live effectiveness. |
| Fiction graph consistency | `results/graph_consistency_bench.json` | `scripts/graph_consistency_bench.py`; 9 probes x 5 per session | Reproducible diagnostic. Closed deterministic probe set and template responses. Does not establish open-world attacker robustness. |
| Cross-session consistency | `results/cross_session_consistency_bench.json` | `scripts/cross_session_consistency_bench.py`; session-scoped/reconnect/per-session arms | Reproducible diagnostic of verifier/store classes. Host-fiction store is not proven active or durable in `server_v2`; persistence and concurrent writers remain gaps. |
| Verifier precision/recall | `results/verifier_redteam.json` | `scripts/verifier_redteam.py`, `verifier_redteam_cases.py` | 105 closed-world cases; deterministic no-network suite. Reported P/R contract is not an end-to-end serving result. |
| Supported-claim verifier | `results/verifier_redteam_supported_claims.json` | supported-claim red-team script/cases and verifier modules | 123-case deterministic suite including supported-claim stratum. Strong local contract evidence, but cannot compensate for absent verifier wiring in `server_v2`. |
| Live serving/provenance | `results/live_benchmark_zodiac_20260922.json`, `results/two_channel_metrics.json` | live benchmark runner and two-channel scorer | Persisted 218-row campaign and serve-path metadata. `two_channel_metrics.json` notes scorer echo artifacts and 97 offline echo-guard changes; a fresh guarded served-text run is required before stronger claims. |
| Run-to-run stability | `results/stability_run1_vs_run2.json`, `results/determinism_sweep.json` | stability/determinism scripts | Paired/scorer stability diagnostics using existing runs. Agreement is not independent replication or causal validity. |
| Bootstrap intervals | `results/bootstrap_ci.json` | bootstrap CI script over persisted benchmark artifact | Generated 2026-10-08 from persisted inputs. Valid only for the stated artifact and paired design; does not repair scorer or sample limitations. |
| Fallback behavior | `results/ablation_battery.json`, `results/two_channel_metrics.json`, graph/verifier tests | `cycle/graph.py`, verifier tests, fallback tests | Deterministic fallback exists in graph path and tests. Active Harness path does not guarantee fallback after verifier/provider failures. |
| JEV baseline/effect | `results/jev_ab_eval.json`, `results/jev_hard_subset.json`, `results/jev_real_logs_eval.json` | `scripts/jev_ab_eval.py`, `jev_hard_subset.py`, `jev_real_logs_eval.py` | Bounded historical evidence only. One hard-subset case assessed; five provider unavailable/refused. Real-log result uses a different historical provider endpoint and manual labels. Do not generalize to Laya. |
| JEV dwell/replay | dwell replay result files | `scripts/jev_dwell_replay.py` | Simulation with attacker/defender LLMs and recorded JEV assessments, not live attacker evidence. |
| Scorer audit / CTI | `results/cti_manual_audit.json` | CTI manual-audit script; ATT&CK v19.1, annotator/adjudicator procedure | Useful audit of echo/scorer behavior. Uses model-assisted annotators and manual adjudication; not independent human reliability evidence. Residual technique false-credit and post-correction scorer dependence are documented. |
| Intelligence Ladder / steering | `results/mtp_steering_eval.json` and related ladder artifacts | MTP/steering scripts | Small deterministic evaluation; diagnostic of mechanism, not broad intelligence or deployment performance. |
| Chrollo calibration | `results/model_quality/chrollo_calibration.json`, `chrollo_learning_curve.json` | Chrollo training/evaluation scripts; `data/training/test.jsonl`; `models/chrollo/rf_classifier.joblib` | Uses the repository's held-out test split. Not external validation; generator-derived labels and split provenance must remain explicit. |
| External baseline comparison | `results/external_baseline_comparison.json` | baseline-comparison runner; 218-row workload | Compares configured arms under shared deterministic scorers. It does not establish real attacker behavior or independent human labels. |
| Rescue/trajectory benchmark | `results/sp2027_rescue/behavior_trajectory_benchmark.json` | `scripts/sp2027_rescue_behavior_benchmark.py`; 400 test sessions and hashed train/test inputs | Provider-free, overlap check reported zero, but `gold_risk` is controller-defined and the benchmark is a self-consistency diagnostic, not independent attacker ground truth. |
| Historical failure suite | `results/benchmark_report.json` | historical benchmark runner | 158/158 failures in the persisted report. Must not be promoted as current success or silently replaced. |
| Provider/catalog health | `results/apmix_quota_status.json` and related status files | provider/catalog/quota scripts | Catalog status and model drift are operational observations; quota was not probed. Not evidence of available future Laya/JEV execution. |

## Provenance and leakage audit

Positive controls observed:

- The rescue benchmark records train/test identities and an overlap check.
- Result ledgers distinguish canonical, excluded, historical, and operational artifacts.
- Some artifacts record script names, seed, sample counts, model/provider labels, and generation dates.
- Deterministic verifier suites have local case files and explicit strata.

Open issues:

- The worktree contains extensive untracked results, logs, and session records; a clean immutable artifact manifest is not the default runtime behavior.
- README/test counts are stale relative to current collection.
- Several results depend on persisted runs rather than fresh reruns in the current environment.
- Provider drift/refusal prevents some JEV and live-provider experiments from being rerun under the original conditions.
- The 218-row live campaign and derived CI/scorer artifacts require the exact original workload, provider/model state, and scorer versions to establish a clean-room rerun.
- Classifier evaluation uses repository-supplied held-out data, not an independently collected external test set.
- Rescue benchmark `gold_risk` is generated by controller logic; it cannot be treated as independent ground truth.
- Echo correction changes the served-text scoring interpretation; uncorrected headline values must not be described as guarded live serving performance.

## Evidence needed for future claims

Before a submission-ready claim, each result should have a manifest containing: source commit, input file hashes, code/script revision, environment lock, model/provider ID and checksum where possible, prompt/template version, random seeds, scorer version, exclusions, raw-to-derived mapping, and rerun command. For live serving, add a per-response decision record proving candidate generation, verifier result/version, fallback reason, state commit decision, and response served.

## Audit conclusion

The repository contains meaningful local evidence for verifier and graph mechanisms and a large historical benchmark record. It does not yet provide one reproducible, independently grounded, end-to-end evidence chain for the public verified honeypot because the active serving path omits the verifier and several headline evaluations are scorer/provider/ground-truth bounded.
