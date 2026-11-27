# RAGIN Source-to-Result File Lineage Index

**Snapshot:** 2026-10-14; Git root `/home/elaref/Documents/research/ragin/RAGIN-Retrieval-Augmented-Honeypot-Intelligence`. This is a path and static-reference index for the working tree, including pre-existing modified/untracked files. It does not claim runtime execution or artifact provenance from a filename alone.

**Scope:** Python source files and Rust files below `llm-gateway/src/`, excluding Git metadata, virtual environments, caches, and Rust `target/`. All top-level Python experiment runners under `scripts/` are scanned for literal result paths. Results payloads are not copied into this index.

## Source inventory

Found **368 Python files** and **10 Rust source files**. Git state column distinguishes current tracked/modified/untracked state. Directory placement is only a navigation aid; runtime activation is defined by imports, entrypoints, and deployment configuration in [the architecture overview](SYSTEM_ARCHITECTURE_CURRENT.md).

| Path | Git state |
|---|---|
| `dist/ragin-sp-mirror/scripts/audit_figure_geometry.py` | untracked |
| `dist/ragin-sp-mirror/scripts/bootstrap_ci.py` | untracked |
| `dist/ragin-sp-mirror/scripts/build_anonymized_mirror.py` | untracked |
| `dist/ragin-sp-mirror/scripts/gen_sp_figures.py` | untracked |
| `dist/ragin-sp-mirror/scripts/verifier_ci_cluster_bootstrap.py` | untracked |
| `dist/ragin-sp-mirror/scripts/verifier_harm_cases.py` | untracked |
| `dist/ragin-sp-mirror/scripts/verifier_harm_probe.py` | untracked |
| `dist/ragin-sp-mirror/scripts/verifier_redteam.py` | untracked |
| `dist/ragin-sp-mirror/scripts/verifier_redteam_cases.py` | untracked |
| `ragin/__init__.py` | tracked |
| `ragin/auth/__init__.py` | tracked |
| `ragin/auth/rbac.py` | tracked |
| `ragin/benchmark/__init__.py` | tracked |
| `ragin/benchmark/core.py` | M |
| `ragin/benchmark/cowrie_adapter.py` | tracked |
| `ragin/benchmark/effectiveness.py` | tracked |
| `ragin/benchmark/harness_bridge.py` | tracked |
| `ragin/benchmark/honeygpt_benchmark.py` | tracked |
| `ragin/benchmark/human_eval.py` | tracked |
| `ragin/benchmark/human_eval_personas.py` | tracked |
| `ragin/benchmark/run_benchmarks.py` | tracked |
| `ragin/capture_v4/__init__.py` | ?? |
| `ragin/capture_v4/cowrie.py` | ?? |
| `ragin/capture_v4/lineage.py` | ?? |
| `ragin/capture_v4/manifest.py` | ?? |
| `ragin/capture_v4/privacy.py` | ?? |
| `ragin/capture_v4/registry.py` | ?? |
| `ragin/chrollo/__init__.py` | tracked |
| `ragin/chrollo/classifier.py` | tracked |
| `ragin/chrollo/features.py` | M |
| `ragin/chrollo/features_seq.py` | tracked |
| `ragin/chrollo/models.py` | tracked |
| `ragin/chrollo/pipeline.py` | M |
| `ragin/chrollo/session_parser.py` | tracked |
| `ragin/cycle/__init__.py` | tracked |
| `ragin/cycle/adapters.py` | M |
| `ragin/cycle/containment/__init__.py` | ?? |
| `ragin/cycle/containment/audit_integrity.py` | ?? |
| `ragin/cycle/containment/container_egress.py` | ?? |
| `ragin/cycle/containment/metadata_isolation.py` | ?? |
| `ragin/cycle/containment/restart_persistence.py` | ?? |
| `ragin/cycle/coordination.py` | tracked |
| `ragin/cycle/graph.py` | M |
| `ragin/cycle/harness.py` | M |
| `ragin/cycle/hitl.py` | tracked |
| `ragin/cycle/metrics.py` | tracked |
| `ragin/cycle/multi_turn.py` | tracked |
| `ragin/cycle/provider_transport.py` | ?? |
| `ragin/cycle/sandbox.py` | M |
| `ragin/cycle/session.py` | tracked |
| `ragin/cycle/supported_claims.py` | M |
| `ragin/cycle/threat_modeling.py` | tracked |
| `ragin/cycle/verifier.py` | M |
| `ragin/decision/__init__.py` | ?? |
| `ragin/decision/laya_decision.py` | ?? |
| `ragin/decision/laya_runtime.py` | ?? |
| `ragin/decision/optional.py` | ?? |
| `ragin/decision_fusion_v4/__init__.py` | ?? |
| `ragin/decision_fusion_v4/benchmark.py` | ?? |
| `ragin/decision_fusion_v4/config.py` | ?? |
| `ragin/decision_fusion_v4/evidence_export.py` | ?? |
| `ragin/decision_fusion_v4/matched_runner.py` | ?? |
| `ragin/decision_fusion_v4/policy.py` | ?? |
| `ragin/decision_fusion_v4/policy_v2.py` | ?? |
| `ragin/decision_fusion_v4/runtime_mode.py` | ?? |
| `ragin/decoys/__init__.py` | tracked |
| `ragin/decoys/base.py` | tracked |
| `ragin/decoys/http_service.py` | tracked |
| `ragin/decoys/manager.py` | tracked |
| `ragin/decoys/ssh_service.py` | tracked |
| `ragin/decoys/telnet_service.py` | tracked |
| `ragin/don/__init__.py` | M |
| `ragin/don/attack_heatmap.py` | tracked |
| `ragin/don/command_aware_v2.py` | ?? |
| `ragin/don/cti_corpus.py` | tracked |
| `ragin/don/cti_feeds.py` | tracked |
| `ragin/don/evidence_judge.py` | ?? |
| `ragin/don/extended_cti_loader.py` | tracked |
| `ragin/don/graph.py` | tracked |
| `ragin/don/intel_corpus.py` | tracked |
| `ragin/don/lightrag_adapter.py` | tracked |
| `ragin/don/mitre_cti_loader.py` | tracked |
| `ragin/don/models.py` | M |
| `ragin/don/pipeline.py` | tracked |
| `ragin/don/rag_engine.py` | M |
| `ragin/don/threat_mapper.py` | tracked |
| `ragin/don/vector_store.py` | tracked |
| `ragin/gateway/__init__.py` | tracked |
| `ragin/gateway/client.py` | tracked |
| `ragin/graph/__init__.py` | tracked |
| `ragin/graph/fiction.py` | M |
| `ragin/graph/host_fiction.py` | M |
| `ragin/graph/mitre.py` | tracked |
| `ragin/hisoka/__init__.py` | tracked |
| `ragin/hisoka/deceiver.py` | M |
| `ragin/hisoka/deception.py` | M |
| `ragin/hisoka/dwell_tracker.py` | tracked |
| `ragin/hisoka/fs_ledger.py` | tracked |
| `ragin/hisoka/honeytokens.py` | tracked |
| `ragin/hisoka/memory.py` | tracked |
| `ragin/hisoka/models.py` | tracked |
| `ragin/hisoka/persona.py` | tracked |
| `ragin/hisoka/pipeline.py` | tracked |
| `ragin/hisoka/response_generator.py` | tracked |
| `ragin/hisoka/session_manager.py` | tracked |
| `ragin/hisoka/strategy_generator_v1.py` | ?? |
| `ragin/intelligence/__init__.py` | tracked |
| `ragin/intelligence/adaptive_response.py` | tracked |
| `ragin/intelligence/evasion_detector.py` | tracked |
| `ragin/intelligence/models.py` | tracked |
| `ragin/intelligence/skill_strategy.py` | tracked |
| `ragin/jev/__init__.py` | tracked |
| `ragin/jev/assessment.py` | tracked |
| `ragin/jev/client.py` | tracked |
| `ragin/jev/models.py` | tracked |
| `ragin/jev/orchestration.py` | tracked |
| `ragin/monitoring/__init__.py` | tracked |
| `ragin/monitoring/alerts.py` | tracked |
| `ragin/monitoring/audit.py` | tracked |
| `ragin/monitoring/health.py` | tracked |
| `ragin/monitoring/metrics.py` | tracked |
| `ragin/rollout/__init__.py` | tracked |
| `ragin/rollout/manager.py` | tracked |
| `ragin/rollout/metrics.py` | tracked |
| `ragin/rollout/models.py` | tracked |
| `ragin/server.py` | M |
| `ragin/server_v2.py` | M |
| `ragin/siem/__init__.py` | tracked |
| `ragin/siem/connector.py` | tracked |
| `ragin/siem/elasticsearch.py` | tracked |
| `ragin/siem/splunk.py` | tracked |
| `ragin/siem/syslog.py` | tracked |
| `ragin/transport/__init__.py` | ?? |
| `ragin/transport/mtls.py` | ?? |
| `ragin/utils.py` | tracked |
| `scripts/_tmp_launcher.py` | ?? |
| `scripts/_tmp_launcher2.py` | ?? |
| `scripts/_tmp_launcher4.py` | ?? |
| `scripts/ablation_battery.py` | tracked |
| `scripts/analyze_hf2024_v4_reference_free.py` | ?? |
| `scripts/audit_ai_rater_reliability_v2.py` | ?? |
| `scripts/audit_figure_geometry.py` | M |
| `scripts/audit_live_benchmark.py` | tracked |
| `scripts/audit_pre_reference_prediction_recovery_v1.py` | ?? |
| `scripts/backup_field_data.py` | tracked |
| `scripts/bare_llm_backend.py` | tracked |
| `scripts/bench_rag_ir.py` | tracked |
| `scripts/benchmark_fullcorpus_graph.py` | tracked |
| `scripts/benchmark_seq_features.py` | tracked |
| `scripts/bootstrap_ci.py` | M |
| `scripts/build_anonymized_mirror.py` | ?? |
| `scripts/build_consensus.py` | tracked |
| `scripts/build_don_v2_corpus.py` | ?? |
| `scripts/build_human_reference_handoff.py` | ?? |
| `scripts/build_v3_blind_instrument.py` | ?? |
| `scripts/calibrate_chrollo.py` | tracked |
| `scripts/capture_real_linux_transcripts.py` | tracked |
| `scripts/check_apmix_catalog.py` | tracked |
| `scripts/collect_field_data.py` | tracked |
| `scripts/compare_run_stability.py` | tracked |
| `scripts/cowrie_comparison.py` | tracked |
| `scripts/cowrie_pipeline_bridge.py` | tracked |
| `scripts/cross_session_consistency_bench.py` | tracked |
| `scripts/cti_manual_audit.py` | tracked |
| `scripts/deploy.py` | tracked |
| `scripts/determinism_sweep.py` | tracked |
| `scripts/drive_cowrie.py` | tracked |
| `scripts/dryrun_bait_transcripts.py` | tracked |
| `scripts/e2e_test.py` | tracked |
| `scripts/field_health_check.py` | tracked |
| `scripts/field_smoke_ssh.py` | tracked |
| `scripts/finalize_reference_169_apmix_run.py` | ?? |
| `scripts/finalize_v4_real_holdout_preregistration.py` | ?? |
| `scripts/freeze_don_v2.py` | ?? |
| `scripts/freeze_evidence_judge_contract.py` | ?? |
| `scripts/freeze_policy_contract_serving_observability_v1.py` | ?? |
| `scripts/freeze_policy_v2_review_packet_v1.py` | ?? |
| `scripts/gen_sp_figures.py` | ?? |
| `scripts/gen_two_channel_tables.py` | tracked |
| `scripts/generate_training_data.py` | tracked |
| `scripts/graph_consistency_bench.py` | tracked |
| `scripts/human_blind_eval.py` | tracked |
| `scripts/jev_ab_eval.py` | tracked |
| `scripts/jev_dwell_replay.py` | tracked |
| `scripts/jev_hard_subset.py` | tracked |
| `scripts/jev_real_logs_eval.py` | tracked |
| `scripts/laya_ablation_analysis.py` | ?? |
| `scripts/laya_blind_annotation_workflow.py` | ?? |
| `scripts/laya_candidate_audit.py` | ?? |
| `scripts/laya_candidate_pool_v2.py` | ?? |
| `scripts/laya_candidate_quality_audit.py` | ?? |
| `scripts/laya_confirmatory_analysis.py` | ?? |
| `scripts/laya_confirmatory_selection.py` | ?? |
| `scripts/laya_decision_v2_exploratory_120.py` | ?? |
| `scripts/laya_e2e_two_sessions.py` | ?? |
| `scripts/laya_frozen_runner.py` | ?? |
| `scripts/laya_independent_candidate_pool.py` | ?? |
| `scripts/laya_label_pipeline.py` | ?? |
| `scripts/laya_leakage_review_v2.py` | ?? |
| `scripts/laya_manifest_consistency_check.py` | ?? |
| `scripts/laya_manipulation_audit_v2a.py` | ?? |
| `scripts/laya_paired_comparison.py` | ?? |
| `scripts/laya_primary_169_blind_execution_v2a.py` | ?? |
| `scripts/laya_real_inference_pilot.py` | ?? |
| `scripts/learning_curve_chrollo.py` | tracked |
| `scripts/llm_proxy_label.py` | ?? |
| `scripts/locked_ai_reference_evaluation_v1.py` | ?? |
| `scripts/merge_llama33_matrix.py` | tracked |
| `scripts/monitor.py` | tracked |
| `scripts/mtp_steering_eval.py` | tracked |
| `scripts/normalize_and_freeze_v3.py` | ?? |
| `scripts/opencode_proxy.py` | ?? |
| `scripts/persona_recheck.py` | tracked |
| `scripts/prepare_expert_ai_panel_v1a.py` | ?? |
| `scripts/prepare_v4_real_holdout_preregistration.py` | ?? |
| `scripts/primary_169_locked_analysis_v1.py` | ?? |
| `scripts/primary_169_reference_apmix_v1.py` | ?? |
| `scripts/render_validation_section.py` | tracked |
| `scripts/rescore_judge_panel.py` | tracked |
| `scripts/rescore_redteam_family.py` | tracked |
| `scripts/reseed_audit_pipeline.py` | tracked |
| `scripts/retrain_chrollo.py` | tracked |
| `scripts/retrain_chrollo_ngram.py` | tracked |
| `scripts/run_baseline_comparison.py` | M |
| `scripts/run_don_v2_substantive_final_v1.py` | ?? |
| `scripts/run_evidence_judge_paired_validation_v1.py` | ?? |
| `scripts/run_evidence_judge_real_data_ablation_v1.py` | ?? |
| `scripts/run_external_baseline.py` | tracked |
| `scripts/run_hf2024_postfix_family_disjoint_v1.py` | ?? |
| `scripts/run_hf2024_substantive_final_v1.py` | ?? |
| `scripts/run_hf2024_v4_raw_execution.py` | ?? |
| `scripts/run_human_eval.py` | tracked |
| `scripts/run_human_eval_parallel.py` | tracked |
| `scripts/run_human_eval_subagents.py` | tracked |
| `scripts/run_live_benchmark.py` | tracked |
| `scripts/run_v4_pre_execution_provenance_audit.py` | ?? |
| `scripts/run_v4_real_evidence_recovery_audit.py` | ?? |
| `scripts/run_v4_synthetic_benchmark.py` | ?? |
| `scripts/run_v4_synthetic_integration_smoke.py` | ?? |
| `scripts/score_human_eval.py` | tracked |
| `scripts/serve_provenance.py` | tracked |
| `scripts/serve_provenance_v2.py` | tracked |
| `scripts/sp2027_rescue_behavior_benchmark.py` | ?? |
| `scripts/timing_fingerprint_rocauc.py` | tracked |
| `scripts/tune_chrollo.py` | tracked |
| `scripts/two_channel_metrics.py` | tracked |
| `scripts/v4_acquisition_integrity_checkpoint.py` | ?? |
| `scripts/v4_capture_dry_run.py` | ?? |
| `scripts/v4_capture_finalize.py` | ?? |
| `scripts/v4_capture_progress.py` | ?? |
| `scripts/v4_capture_readiness_freeze.py` | ?? |
| `scripts/v4_capture_validate.py` | ?? |
| `scripts/v4_controlled_admin_capture.py` | ?? |
| `scripts/v4_cowrie_capture_dry_run.py` | ?? |
| `scripts/v4_cowrie_capture_watch.py` | ?? |
| `scripts/validate_algorithms.py` | tracked |
| `scripts/validate_phase1.py` | tracked |
| `scripts/validate_release_artifacts.py` | ?? |
| `scripts/verifier_ci_cluster_bootstrap.py` | ?? |
| `scripts/verifier_ci_manifest.py` | ?? |
| `scripts/verifier_harm_cases.py` | ?? |
| `scripts/verifier_harm_probe.py` | ?? |
| `scripts/verifier_redteam.py` | tracked |
| `scripts/verifier_redteam_cases.py` | tracked |
| `scripts/verifier_redteam_check.py` | M |
| `scripts/verifier_redteam_cross_family.py` | tracked |
| `scripts/verifier_redteam_live.py` | tracked |
| `scripts/verifier_redteam_opencode_fill.py` | tracked |
| `scripts/verifier_redteam_security_oracle.py` | ?? |
| `services/mock_provider.py` | ?? |
| `tests/__init__.py` | tracked |
| `tests/benchmark_traditional.py` | tracked |
| `tests/conftest.py` | M |
| `tests/integration/__init__.py` | tracked |
| `tests/integration/test_gateway_api.py` | tracked |
| `tests/integration/test_laya_real_model.py` | ?? |
| `tests/integration/test_performance.py` | tracked |
| `tests/integration/test_pipeline.py` | tracked |
| `tests/integration/test_policy_contract_serving_observability_v1.py` | ?? |
| `tests/integration/test_readiness.py` | tracked |
| `tests/integration/test_stability.py` | tracked |
| `tests/integration/test_substantive_runtime_integration_v1.py` | ?? |
| `tests/security/__init__.py` | tracked |
| `tests/security/test_adversarial.py` | tracked |
| `tests/security/test_input_validation.py` | tracked |
| `tests/security/test_mtls_transport.py` | ?? |
| `tests/security/test_task2_verified_serving.py` | ?? |
| `tests/test_e2e_comprehensive.py` | tracked |
| `tests/test_performance_benchmark.py` | tracked |
| `tests/test_security_validation.py` | tracked |
| `tests/unit/__init__.py` | tracked |
| `tests/unit/test_adapters.py` | tracked |
| `tests/unit/test_anonymized_mirror.py` | ?? |
| `tests/unit/test_artifact_consistency.py` | M |
| `tests/unit/test_attack_heatmap.py` | tracked |
| `tests/unit/test_b4_pairing_contract.py` | ?? |
| `tests/unit/test_benchmark.py` | M |
| `tests/unit/test_capture_v4.py` | ?? |
| `tests/unit/test_chrollo.py` | tracked |
| `tests/unit/test_coordination.py` | tracked |
| `tests/unit/test_cowrie_adapter.py` | tracked |
| `tests/unit/test_cowrie_capture.py` | ?? |
| `tests/unit/test_credential_baits.py` | tracked |
| `tests/unit/test_cti_manual_audit.py` | M |
| `tests/unit/test_cycle.py` | tracked |
| `tests/unit/test_cycle_graph.py` | M |
| `tests/unit/test_deception_prompt.py` | tracked |
| `tests/unit/test_decision_fusion_v4.py` | ?? |
| `tests/unit/test_don.py` | M |
| `tests/unit/test_don_graph.py` | tracked |
| `tests/unit/test_don_v2.py` | ?? |
| `tests/unit/test_evidence_judge.py` | ?? |
| `tests/unit/test_evidence_judge_filtering.py` | ?? |
| `tests/unit/test_extended_cti.py` | tracked |
| `tests/unit/test_features_seq.py` | tracked |
| `tests/unit/test_fiction_graph.py` | M |
| `tests/unit/test_figure_geometry.py` | tracked |
| `tests/unit/test_gateway_integration.py` | tracked |
| `tests/unit/test_gateway_reasoning_models.py` | tracked |
| `tests/unit/test_harness_threat_modeling.py` | tracked |
| `tests/unit/test_hisoka.py` | M |
| `tests/unit/test_hisoka_memory.py` | tracked |
| `tests/unit/test_hitl.py` | tracked |
| `tests/unit/test_honeytoken_propagation.py` | tracked |
| `tests/unit/test_host_fiction.py` | M |
| `tests/unit/test_host_fiction_wiring.py` | M |
| `tests/unit/test_human_blind_eval.py` | tracked |
| `tests/unit/test_human_eval.py` | tracked |
| `tests/unit/test_human_eval_subagents.py` | tracked |
| `tests/unit/test_intelligence.py` | tracked |
| `tests/unit/test_jevi.py` | tracked |
| `tests/unit/test_judge_panel_corrections.py` | tracked |
| `tests/unit/test_laya_confirmatory_analysis.py` | ?? |
| `tests/unit/test_laya_decision_v2.py` | ?? |
| `tests/unit/test_lightrag_adapter.py` | tracked |
| `tests/unit/test_metrics.py` | tracked |
| `tests/unit/test_mitre_chain.py` | tracked |
| `tests/unit/test_mitre_chain_end.py` | tracked |
| `tests/unit/test_monitoring.py` | tracked |
| `tests/unit/test_multi_turn.py` | tracked |
| `tests/unit/test_opencode_proxy.py` | ?? |
| `tests/unit/test_optional_assessment.py` | ?? |
| `tests/unit/test_policy_v2_candidate.py` | ?? |
| `tests/unit/test_postprocess_hardening.py` | tracked |
| `tests/unit/test_provider_enabled_acceptance.py` | ?? |
| `tests/unit/test_provider_transport.py` | ?? |
| `tests/unit/test_provider_transport_adapter.py` | ?? |
| `tests/unit/test_provider_transport_config.py` | ?? |
| `tests/unit/test_rollout.py` | tracked |
| `tests/unit/test_serve_provenance.py` | tracked |
| `tests/unit/test_server_v2.py` | M |
| `tests/unit/test_server_v2_laya_config.py` | ?? |
| `tests/unit/test_server_v2_laya_runtime_no_second_path.py` | ?? |
| `tests/unit/test_strategy_generator_v1.py` | ?? |
| `tests/unit/test_supported_claims.py` | tracked |
| `tests/unit/test_threat_mapper_gt.py` | tracked |
| `tests/unit/test_threat_modeling.py` | tracked |
| `tests/unit/test_timing_fingerprint.py` | M |
| `tests/unit/test_ttp_extraction_accuracy.py` | tracked |
| `tests/unit/test_two_channel_metrics.py` | M |
| `tests/unit/test_v4_generator_strategy_wiring_fix.py` | ?? |
| `tests/unit/test_v4_real_prototype.py` | ?? |
| `tests/unit/test_validate_release_artifacts.py` | ?? |
| `tests/unit/test_verifier.py` | M |
| `tests/unit/test_verifier_redteam.py` | M |
| `tests/unit/test_verifier_redteam_security_oracle.py` | ?? |
| `tests/unit/test_watch_audit_pipeline.py` | tracked |
| `tools/ingest_expert_ai_panel.py` | ?? |
| `llm-gateway/src/clients.rs` | tracked |
| `llm-gateway/src/config.rs` | tracked |
| `llm-gateway/src/error.rs` | tracked |
| `llm-gateway/src/gateway.rs` | tracked |
| `llm-gateway/src/lib.rs` | tracked |
| `llm-gateway/src/main.rs` | tracked |
| `llm-gateway/src/metrics.rs` | tracked |
| `llm-gateway/src/models.rs` | tracked |
| `llm-gateway/src/prompt_engine.rs` | tracked |
| `llm-gateway/src/validation.rs` | tracked |

## Experiment runner result-path references

Method: parse each `scripts/*.py` file with Python AST and collect string constants containing `results/`, then report the source line where each literal occurs. Values are deduplicated per runner and line. Computed paths, environment variables, shell scripts, symlinks, and paths held in non-string forms may be missed. A literal is a static relationship clue, not proof that a particular run produced or consumed an artifact.

**Coverage:** 134 top-level Python runners scanned; 87 contain result-path literals.

| Runner | Line | Literal path/value |
|---|---:|---|
| `scripts/ablation_battery.py` | 2 | `TDSC ablation battery (plan §5) — deterministic stratum, runnable offline.

Five ablations, each disabling exactly one loop component, each measured on
its own target metric. Per the plan: "Ablations 1–4 must be *worse* on their
target metric — not crash — which is also the robustness test reviewers
will run."

\| #  \| Ablation      \| Disabled                        \| Target metric (worse = better ablation proof)   \|
\|----\|---------------\|---------------------------------\|--------------------------------------------------\|
\| A1 \| no-fiction    \| fiction_block seeding (C1)      \| fiction facts seeded into the plan               \|
\| A2 \| no-bait-steer \| strategy_block seeding (C3)     \| strategy/next-technique context absent from plan \|
\| A3 \| no-verify     \| FictionConsistencyVerifier (C2) \| responses served with no verification verdict    \|
\| A4 \| no-approval   \| risk-based policy → all AUTO    \| REQUIRE gating + audit trail empty               \|
\| A5 \| no-graph      \| _run_linear fallback path (C5)  \| same transitions, no LangGraph features          \|

Deterministic stratum: the Hisoka deceiver runs against an unreachable
gateway, so every response comes from the deterministic fast-paths/templates
(0 LLM tokens). Analysis uses Don's offline ThreatMapper (no LLM) so the
risk policy receives real technique IDs and REQUIRE can fire. The live-LLM
stratum reuses this battery unchanged once the apmix quota resets.

Output: results/ablation_battery.json
` |
| `scripts/ablation_battery.py` | 132 | `results/ablation_audit_full.jsonl` |
| `scripts/ablation_battery.py` | 137 | `results/ablation_audit_nofiction.jsonl` |
| `scripts/ablation_battery.py` | 160 | `results/ablation_audit_noverify.jsonl` |
| `scripts/ablation_battery.py` | 167 | `results/ablation_audit_nobait.jsonl` |
| `scripts/ablation_battery.py` | 185 | `results/ablation_audit_noapproval.jsonl` |
| `scripts/ablation_battery.py` | 191 | `results/ablation_audit_nograph.jsonl` |
| `scripts/ablation_battery.py` | 367 | `results/ablation_battery.json` |
| `scripts/audit_ai_rater_reliability_v2.py` | 40 | `results/laya_research/ai_raters/codex_r1.json` |
| `scripts/audit_ai_rater_reliability_v2.py` | 48 | `results/laya_research/ai_raters/codex_r2.json` |
| `scripts/audit_ai_rater_reliability_v2.py` | 56 | `results/laya_research/ai_raters/codex_r3.json` |
| `scripts/audit_ai_rater_reliability_v2.py` | 64 | `results/laya_research/rater_labels/r1.json` |
| `scripts/audit_ai_rater_reliability_v2.py` | 72 | `results/laya_research/rater_labels/r2.json` |
| `scripts/audit_ai_rater_reliability_v2.py` | 80 | `results/laya_research/rater_labels/r3.json` |
| `scripts/audit_ai_rater_reliability_v2.py` | 91 | `results/laya_research/rater_packets/r1.json` |
| `scripts/audit_ai_rater_reliability_v2.py` | 97 | `results/laya_research/rater_packets/r2.json` |
| `scripts/audit_ai_rater_reliability_v2.py` | 103 | `results/laya_research/rater_packets/r3.json` |
| `scripts/audit_ai_rater_reliability_v2.py` | 576 | `

For the three repeated-packet pairs, model identity is `DERIVED_UNVERIFIED` because at least one member lacks independently supported model identity. The three `agent_run_01`/`02`/`03` within-Codex comparisons are separately retained as same-observed-model run-to-run comparisons; they do not establish correctness or generalize beyond these runs.

## 11. What these results DO support

- A reproducible description of agreement among six labeled AI-agent annotation runs on 120 shared cases.
- Conservative multiclass and fixed-rater binary reliability estimates with explicit `UNCERTAIN` handling.
- Identification and preservation of exact consensus, binary-supported consensus, strict exact majorities, and ambiguous cases.
- Descriptive run-to-run stability for repeated packet assignments.

## 12. What these results DO NOT support

- They do not establish human inter-rater reliability or create human ground truth.
- They do not establish that any annotation is correct.
- They do not justify majority-voting AI annotations into final truth.
- They do not support a model-specific or cross-model stability claim where model identity is unverified.
- They do not provide a Chrollo-vs-Laya prediction comparison or a confirmatory scientific result.

## 13. Freeze boundary before confirmatory analysis

This v2 reliability audit is frozen before any confirmatory labels or predictions are joined. No Chrollo/Laya prediction was inspected, no ground truth was created, and no confirmatory Chrollo-vs-Laya analysis was run. Ambiguous cases remain represented in the audit artifacts. The confirmatory scientific verdict remains **INCONCLUSIVE**.

The machine-generated freeze manifest is `results/laya_research/ai_rater_reliability_freeze_v2.json`. Do not modify it after confirmatory labels or predictions are joined.
` |
| `scripts/audit_ai_rater_reliability_v2.py` | 605 | `results/laya_research/ai_rater_runs_manifest_v2.json` |
| `scripts/audit_ai_rater_reliability_v2.py` | 606 | `results/laya_research/ai_rater_pairwise_agreement_v2.json` |
| `scripts/audit_ai_rater_reliability_v2.py` | 607 | `results/laya_research/ai_rater_multirater_reliability_v2.json` |
| `scripts/audit_ai_rater_reliability_v2.py` | 608 | `results/laya_research/ai_rater_disagreement_map_v2.jsonl` |
| `scripts/audit_ai_rater_reliability_v2.py` | 609 | `results/laya_research/ai_rater_stability_summary_v2.json` |
| `scripts/audit_figure_geometry.py` | 2 | `Figure geometry audit for the paper's five TikZ/pgfplots figures.

The figures are drawn from declared coordinates, so a class of rendering
defects is mechanically checkable from the compiled output alone:

  1. border bands  -- dense ink along the canvas edge (clipped content);
  2. node rects    -- solid borders via long horizontal runs, dashed
                      borders via periodic dash runs, then any continuous
                      ink run >= MIN_RUN px strictly inside a rect. Text
                      cannot produce such runs; only a crossing line can;
  3. run inventory -- every H/V run >= MIN_RUN px, which must resolve to
                      a declared path, data element, or axis line.

Each figure is re-rendered in isolation (standalone class, pdflatex,
300 dpi raster) so the audit never depends on the surrounding paper.
Writes results/figure_geometry_audit.json and prints a summary; exits 1
on any defect.

Usage:  python scripts/audit_figure_geometry.py
Needs:  pdflatex, pdftoppm, Pillow.
` |
| `scripts/audit_pre_reference_prediction_recovery_v1.py` | 287 | `results/laya_research/gating_preregistration.json` |
| `scripts/bench_rag_ir.py` | 2 | `Statistically-powered RAG evaluation for A*-venue submission.

Design:
  * 50 expert-curated MITRE ATT&CK technique queries spanning all 14 tactics.
  * Ground truth derived from the retrieval corpus itself: a document is
    relevant (grade 2) iff the technique ID appears in its heading region
    (title + first 300 chars) — the canonical ATT&CK page for that technique;
    grade 1 = ID mention in the heading region (tactic tables, cross-refs).
    Parent-technique queries also credit sub-technique pages at grade 2.
  * Arms:
      graph   - Don corrective-RAG LangGraph (novelty arm, LLM-stochastic)
      hybrid  - single-shot hybrid dense+BM25 retrieval (legacy arm)
      dense   - dense vector retrieval only (ablation)
      sparse  - BM25 keyword retrieval only (ablation)
  * 5 runs per query for the graph arm; deterministic arms computed once
    (zero run-variance, reported honestly).
  * Metrics: P@5, Recall@20, MRR, nDCG@10 (graded, standard definitions).
  * Statistics: per-query run-mean paired Wilcoxon signed-rank, Holm-
    Bonferroni correction across the 3 pairings, rank-biserial effect size,
    bootstrap 95% CI of the mean difference.

Checkpointed after every query (results/stat_eval/checkpoint.json); --resume
continues an interrupted run.

Usage:
    python scripts/bench_rag_ir.py [--runs 5] [--resume] [--smoke]
` |
| `scripts/bench_rag_ir.py` | 439 | `saved -> results/stat_eval/summary.json` |
| `scripts/benchmark_fullcorpus_graph.py` | 2 | `Full-corpus RAG benchmark: legacy single-shot vs LangGraph graph (LLM mode).

Corpus: the ~22k LightRAG benchmark documents (ATT&CK-derived, the
artifact's real retrieval corpus) loaded into ThreatRAGEngine's
VectorStore + BM25 index.

Engine LLM: the user's Azure OpenAI resource (deployment
``qwen--qwen38-27b``, a *reasoning* model) via GatewayClient's OpenAI
compatibility (gateway_url={endpoint}/openai), so the graph's
decompose/grade/rewrite nodes run their real LLM paths behind the same
safety guards as production.  Token budgets are raised for the panel
because reasoning models burn completion tokens before answering.

Panel: the Azure judge always runs (single deployment on the resource);
OpenRouter free judges are added best-effort when a key is staged and
quota allows — inter-judge Cohen's kappa is reported only when >= 2
judges produced enough overlapping scores, otherwise the panel is
labelled single-rater.

Outputs: results/model_quality/fullcorpus_graph_benchmark.json
` |
| `scripts/benchmark_seq_features.py` | 2 | `Benchmark sequence-aware features against the 10-feature Chrollo baseline.

Two evaluation regimes:

1. **Same-distribution** — stratified 80/20 split of the 2,000-session
   corpus (identical split to production training). This is the
   apples-to-apples accuracy comparison.

2. **Template-disjoint** — the generator's command banks are split in
   half by template; one model trains on sessions built from templates
   A, the other on sessions built from complementary templates B. Both
   are evaluated on B-only and A-only held-out sets. This defeats
   template memorization: an n-gram model can only score well here if
   it learned generalizable attack-structure signal, not the specific
   commands in the training templates.

Feature groups benchmarked: baseline (10), baseline+phase (+8),
baseline+ngram (+32), baseline+all (+40). A small grid is swept and
selected by OOF over each regime's training split; the test set is
touched once per (regime, feature-group) pair.

Statistics: paired bootstrap (10k resamples) and McNemar exact test for
each gain over baseline.

Outputs:
  results/model_quality/seq_features_benchmark.json
` |
| `scripts/bootstrap_ci.py` | 2 | `Bootstrap/Wilson confidence intervals for every disk-provable claim.

Motivation: the TDSC plan requires CIs on the live A/B composite. The
original 0.855-vs-0.693 composite cited /tmp/ragin_live_bench_final_v5.json
(deleted). This script computes honest intervals from artifacts that ARE on
disk and flags what is not re-derivable, so the paper's numbers always have
a provenance trail:

  - results/live_benchmark_audited.json  (218 rows: technique/actor/persona)
  - results/graph_consistency_bench.json (C1: 45 re-query turns)
  - results/mtp_steering_eval.json       (C3: 10 next-TTP predictions)
  - results/b4_baseline_comparison.json  (RAG vs no-RAG, avgs only)

Methods (no numpy/scipy needed):
  - Wilson score interval for binary rates (exact-ish, small-n safe)
  - Percentile bootstrap for continuous means (deterministic seed)

Exit code 0 iff all proofs pass.
` |
| `scripts/bootstrap_ci.py` | 328 | `RESOLVED 2026-09-22 — the uncitable 0.855 (cited a deleted /tmp artifact) has been RE-DERIVED from a persisted run: results/live_benchmark_zodiac_20260922.json (graph engine, 218 queries, full per-row bodies, 0 errors).` |
| `scripts/build_anonymized_mirror.py` | 84 | `results/b4_baseline_zodiac_20260922.json` |
| `scripts/build_anonymized_mirror.py` | 85 | `results/external_baseline_model_coherent.json` |
| `scripts/build_anonymized_mirror.py` | 86 | `results/verifier_redteam.json` |
| `scripts/build_anonymized_mirror.py` | 87 | `results/verifier_redteam_supported_claims.json` |
| `scripts/build_anonymized_mirror.py` | 88 | `results/verifier_redteam_cross_family.json` |
| `scripts/build_anonymized_mirror.py` | 89 | `results/verifier_ci_cluster_bootstrap.json` |
| `scripts/build_anonymized_mirror.py` | 90 | `results/verifier_harm_probe.json` |
| `scripts/build_anonymized_mirror.py` | 91 | `results/bootstrap_ci.json` |
| `scripts/build_anonymized_mirror.py` | 92 | `results/stability_run1_vs_run2.json` |
| `scripts/build_anonymized_mirror.py` | 93 | `results/live_benchmark_zodiac_20260922.json` |
| `scripts/build_anonymized_mirror.py` | 94 | `results/live_benchmark_zodiac_20260922_run2.json` |
| `scripts/build_anonymized_mirror.py` | 95 | `results/vor_guarded_served_text_lower_bounds.json` |
| `scripts/build_anonymized_mirror.py` | 96 | `results/serve_provenance.json` |
| `scripts/build_anonymized_mirror.py` | 97 | `results/figure_geometry_audit.json` |
| `scripts/build_anonymized_mirror.py` | 98 | `results/hitl_audit_bench.jsonl` |
| `scripts/build_anonymized_mirror.py` | 99 | `results/sp2027_rescue/behavior_trajectory_benchmark.json` |
| `scripts/build_consensus.py` | 2 | `Build consensus.json from per-evaluator scored JSON files.

Reads evaluator-alpha.json, evaluator-beta.json, evaluator-gamma.json
from results/human_eval_scored/, computes per-scenario consensus means/ranges/
agreement, and writes a fresh consensus.json with correct data.

The old consensus.json (Jul 28) had a duplication bug — per-evaluator scores
were identical across all 8 scenarios. The per-evaluator files (Jul 29) contain
the correct varying scores. This script fixes the consensus.
` |
| `scripts/build_consensus.py` | 21 | `results/human_eval_scored` |
| `scripts/build_human_reference_handoff.py` | 14 | `results/laya_research/blind_annotation_confirmatory_v3.json` |
| `scripts/build_human_reference_handoff.py` | 15 | `results/laya_research/v3_annotation_instrument_freeze.json` |
| `scripts/build_human_reference_handoff.py` | 16 | `results/laya_research/v3_annotation_results_freeze.json` |
| `scripts/build_human_reference_handoff.py` | 17 | `results/laya_research/v3_multirater_reliability.json` |
| `scripts/build_human_reference_handoff.py` | 18 | `results/laya_research/v3_pairwise_multiclass_agreement.json` |
| `scripts/build_human_reference_handoff.py` | 19 | `results/laya_research/v3_pairwise_binary_agreement.json` |
| `scripts/build_human_reference_handoff.py` | 93 | `results/laya_research/blind_annotation_confirmatory_v3.json` |
| `scripts/build_human_reference_handoff.py` | 603 | `results/laya_research/rater_packets_v3/` |
| `scripts/build_human_reference_handoff.py` | 617 | `results/laya_research/human_annotation_schema_v1.json` |
| `scripts/build_human_reference_handoff.py` | 619 | `results/laya_research/human_rater_packets_v3` |
| `scripts/build_human_reference_handoff.py` | 744 | `results/laya_research/blind_annotation_confirmatory_v3.json` |
| `scripts/build_human_reference_handoff.py` | 753 | `results/laya_research/human_handoff_integrity.json` |
| `scripts/build_human_reference_handoff.py` | 760 | `results/laya_research/human_annotation_schema_v1.json` |
| `scripts/build_human_reference_handoff.py` | 762 | `results/laya_research/human_handoff_integrity.json` |
| `scripts/build_human_reference_handoff.py` | 763 | `results/laya_research/v3_annotation_instrument_freeze.json` |
| `scripts/build_human_reference_handoff.py` | 769 | `results/laya_research/human_rater_packets_v3/` |
| `scripts/build_human_reference_handoff.py` | 772 | `results/laya_research/human_rater_packets_v3/` |
| `scripts/build_human_reference_handoff.py` | 825 | `results/laya_research/human_reference_preregistration_freeze.json` |
| `scripts/build_v3_blind_instrument.py` | 31 | `results/laya_research/blind_annotation_confirmatory.json` |
| `scripts/build_v3_blind_instrument.py` | 32 | `results/laya_research/rater_packets/r1.json` |
| `scripts/build_v3_blind_instrument.py` | 33 | `results/laya_research/rater_packets/r2.json` |
| `scripts/build_v3_blind_instrument.py` | 34 | `results/laya_research/rater_packets/r3.json` |
| `scripts/build_v3_blind_instrument.py` | 35 | `results/laya_research/ai_rater_runs_manifest.json` |
| `scripts/build_v3_blind_instrument.py` | 36 | `results/laya_research/ai_rater_pairwise_agreement.json` |
| `scripts/build_v3_blind_instrument.py` | 37 | `results/laya_research/ai_rater_stability_summary.json` |
| `scripts/build_v3_blind_instrument.py` | 38 | `results/laya_research/ai_rater_disagreement_map.jsonl` |
| `scripts/build_v3_blind_instrument.py` | 39 | `results/laya_research/ai_rater_runs_manifest_v2.json` |
| `scripts/build_v3_blind_instrument.py` | 40 | `results/laya_research/ai_rater_pairwise_agreement_v2.json` |
| `scripts/build_v3_blind_instrument.py` | 41 | `results/laya_research/ai_rater_multirater_reliability_v2.json` |
| `scripts/build_v3_blind_instrument.py` | 42 | `results/laya_research/ai_rater_disagreement_map_v2.jsonl` |
| `scripts/build_v3_blind_instrument.py` | 43 | `results/laya_research/ai_rater_stability_summary_v2.json` |
| `scripts/build_v3_blind_instrument.py` | 44 | `results/laya_research/ai_rater_reliability_freeze_v2.json` |
| `scripts/build_v3_blind_instrument.py` | 46 | `results/laya_research/confirmatory_case_ids.txt` |
| `scripts/build_v3_blind_instrument.py` | 47 | `results/laya_research/confirmatory_subset_manifest.json` |
| `scripts/build_v3_blind_instrument.py` | 48 | `results/laya_research/frozen_predictions.jsonl` |
| `scripts/build_v3_blind_instrument.py` | 49 | `results/laya_research/confirmatory_frozen_predictions.jsonl` |
| `scripts/build_v3_blind_instrument.py` | 50 | `results/laya_research/gating_preregistration.json` |
| `scripts/build_v3_blind_instrument.py` | 468 | `results/laya_research/blind_annotation_confirmatory_v3.json` |
| `scripts/build_v3_blind_instrument.py` | 469 | `results/laya_research/v3_sanitization_policy.json` |
| `scripts/build_v3_blind_instrument.py` | 470 | `results/laya_research/v3_transformation_audit.jsonl` |
| `scripts/build_v3_blind_instrument.py` | 471 | `results/laya_research/v3_behavioral_equivalence_check.json` |
| `scripts/build_v3_blind_instrument.py` | 472 | `results/laya_research/v3_blindness_redteam.json` |
| `scripts/build_v3_blind_instrument.py` | 473 | `results/laya_research/v3_dependence_structure.json` |
| `scripts/build_v3_blind_instrument.py` | 476 | `results/laya_research/rater_packets_v3/r1.json` |
| `scripts/build_v3_blind_instrument.py` | 477 | `results/laya_research/rater_packets_v3/r2.json` |
| `scripts/build_v3_blind_instrument.py` | 478 | `results/laya_research/rater_packets_v3/r3.json` |
| `scripts/build_v3_blind_instrument.py` | 479 | `results/laya_research/rater_packets_v3/r1.csv` |
| `scripts/build_v3_blind_instrument.py` | 480 | `results/laya_research/rater_packets_v3/r2.csv` |
| `scripts/build_v3_blind_instrument.py` | 481 | `results/laya_research/rater_packets_v3/r3.csv` |
| `scripts/build_v3_blind_instrument.py` | 482 | `results/laya_research/rater_packets_v3/INSTRUCTIONS.txt` |
| `scripts/build_v3_blind_instrument.py` | 483 | `results/laya_research/v3_final_packet_integrity.json` |
| `scripts/check_apmix_catalog.py` | 2 | `apmix catalog + quota watch — appends one probe to a JSONL history.

Checks (0 tokens when quota is exhausted; exactly 1 token when live):
  1. catalog — GET /v1/models (free): are the wired models still listed?
  2. quota   — POST /v1/chat/completions, max_tokens=1 on RAGIN_LLM_MODEL.
  3. reseed  — if any raw benchmark run is newer than its judge-audited
     sibling, re-run the panel audit and audited stability offline so the
     published numbers stay consistent with the artifacts (never calls the
     LLM; see scripts/reseed_audit_pipeline.py).

Emits/updates:
  results/apmix_probe_history.jsonl  — one JSON line per probe (append-only)
  results/apmix_quota_status.json    — latest probe (what the snapshot doc renders)

Exit codes (systemd Unit Failure semantics):
  exit 0 healthy · exit 2 catalog drift · exit 3 reseeded but stability
  verdict is ``review`` · exit 1 probe/network failure

Standalone:  python3 scripts/check_apmix_catalog.py
` |
| `scripts/compare_run_stability.py` | 2 | `Run-to-run stability comparison for the live 218-query benchmark.

Compares the two persisted zodiac runs (same corpus, same engine, same
wiring; independent LLM sessions) row-by-row and emits the stability
artifact the methodology section cites:

  - per-suite means and deltas
  - pass-decision agreement (would a reviewer's verdict replicate?)
  - per-row mean absolute difference (LLM-stratum variance)
  - headline metrics (TTP counts, honeytokens, engagement)

Usage:
    python3 scripts/compare_run_stability.py         --run-a results/live_benchmark_zodiac_20260922.json         --run-b results/live_benchmark_zodiac_20260922_run2.json         --out results/stability_run1_vs_run2.json
` |
| `scripts/compare_run_stability.py` | 100 | `results/live_benchmark_zodiac_20260922.json` |
| `scripts/compare_run_stability.py` | 101 | `results/live_benchmark_zodiac_20260922_run2.json` |
| `scripts/compare_run_stability.py` | 102 | `results/stability_run1_vs_run2.json` |
| `scripts/compare_run_stability.py` | 103 | `results/live_benchmark_zodiac_20260922_judgescored.json` |
| `scripts/compare_run_stability.py` | 104 | `results/live_benchmark_zodiac_20260922_run2_judgescored.json` |
| `scripts/cowrie_comparison.py` | 2 | `Build a RAGIN-vs-Cowrie effectiveness comparison from a live Cowrie JSON log
plus the existing RAGIN live_benchmark.json (chrollo→don→hisoka 30-session
benchmark).

Usage:
    python scripts/cowrie_comparison.py         --cowrie data/cowrie_logs/cowrie.json         --ragin  results/live_benchmark.json         --output results/cowrie_comparison.json
` |
| `scripts/cowrie_comparison.py` | 93 | `results/live_benchmark.json` |
| `scripts/cowrie_comparison.py` | 94 | `results/cowrie_comparison.json` |
| `scripts/determinism_sweep.py` | 2 | `Serve-path determinism sweep (companion to the C1 bench).

The C1 bench proves byte-identical replay for the 9-probe plan set. This
sweep widens the net: every deterministic fast-path family the deceiver
routes to (identity, file listings, services, network, cloud/metadata,
bait chains, generic fallbacks) is probed REPEATS times per session and
each probe's answers are compared byte-for-byte.

Intentionally-deterministic-by-design time fiction (ambient listing
evolution in fs_ledger.ambient_rewrite) is bucketed: within one bucket
the output is byte-identical, and this sweep completes far inside one
bucket, so any divergence is a real per-call nondeterminism defect.

Output: results/determinism_sweep.json (exit 1 on any divergence).
` |
| `scripts/determinism_sweep.py` | 143 | `results/determinism_sweep.json` |
| `scripts/finalize_v4_real_holdout_preregistration.py` | 10 | `results/decision_fusion_v4` |
| `scripts/finalize_v4_real_holdout_preregistration.py` | 115 | `results/decision_fusion_v4/v4_real_prototype_implementation_freeze_v1.json` |
| `scripts/finalize_v4_real_holdout_preregistration.py` | 116 | `results/decision_fusion_v4/v4_future_evaluation_protocol_v1.json` |
| `scripts/finalize_v4_real_holdout_preregistration.py` | 117 | `results/decision_fusion_v4/v4_real_holdout_selection_freeze_v1.json` |
| `scripts/finalize_v4_real_holdout_preregistration.py` | 118 | `results/decision_fusion_v4/v4_real_reference_protocol_preregistration_v1.json` |
| `scripts/freeze_don_v2.py` | 9 | `results/decision_fusion_v4/don_v2_command_aware` |
| `scripts/freeze_don_v2.py` | 40 | `results/decision_fusion_v4/don_v2_command_aware/don_v2_development_validation_v1.json` |
| `scripts/freeze_evidence_judge_contract.py` | 10 | `results/evidence_judge/evidence_judge_contract_freeze_v1.json` |
| `scripts/freeze_policy_contract_serving_observability_v1.py` | 9 | `results/decision_fusion_v4/don_v2_substantive_final_v1/raw_execution_records.jsonl` |
| `scripts/freeze_policy_contract_serving_observability_v1.py` | 10 | `results/decision_fusion_v4/policy_contract_serving_observability_v1` |
| `scripts/freeze_policy_v2_review_packet_v1.py` | 8 | `results/decision_fusion_v4/policy_v2_independent_review_packet_v1` |
| `scripts/freeze_policy_v2_review_packet_v1.py` | 11 | `results/decision_fusion_v4/policy_contract_serving_observability_v1/sha256_manifest.json` |
| `scripts/freeze_policy_v2_review_packet_v1.py` | 12 | `results/decision_fusion_v4/don_v2_substantive_final_v1/raw_execution_records.jsonl` |
| `scripts/freeze_policy_v2_review_packet_v1.py` | 56 | `results/decision_fusion_v4/policy_contract_serving_observability_v1/sha256_manifest.json` |
| `scripts/gen_sp_figures.py` | 2 | `Generate ``paper/figures/generated_values.tex`` from the result artifacts.

Why
---
Every plotted number in the S&P figures used to be a literal in the figure
source. Nothing tied those literals to the artifacts, so they drifted: on
2026-10-08 the persona interval in Figure~2 still carried a lower error of
0.0573 while ``results/bootstrap_ci.json`` had been regenerated to 0.0587.
A stale error bar is invisible to every existing check.

This script makes the figures read their values from one generated file, and
``--check`` fails when the committed file disagrees with the artifacts, so the
drift becomes a CI failure instead of a figure a reader cannot trust.

Sources
-------
``results/bootstrap_ci.json``            live both-channel means + CIs, grounding deltas
``results/stability_run1_vs_run2.json``  second-run point estimates
``results/b4_baseline_zodiac_20260922.json``  grounded/ungrounded TTP counts
``results/model_quality/chrollo_calibration.json``  profiler baseline accuracy
``results/sp2027_rescue/behavior_trajectory_benchmark.json``  trajectory endpoint

Usage::

    python scripts/gen_sp_figures.py           # write the generated file
    python scripts/gen_sp_figures.py --check   # fail if stale, write nothing
` |
| `scripts/gen_sp_figures.py` | 42 | `results/bootstrap_ci.json` |
| `scripts/gen_sp_figures.py` | 43 | `results/stability_run1_vs_run2.json` |
| `scripts/gen_sp_figures.py` | 44 | `results/b4_baseline_zodiac_20260922.json` |
| `scripts/gen_sp_figures.py` | 45 | `results/model_quality/chrollo_calibration.json` |
| `scripts/gen_sp_figures.py` | 46 | `results/sp2027_rescue/behavior_trajectory_benchmark.json` |
| `scripts/gen_two_channel_tables.py` | 1 | `Generate §VI two-channel LaTeX tables from declared-channel artifacts.

Tables (paper §VI):
  1. two-channel metrics for the current-model ragin_full config: served-text
     is shown BOTH raw (echo-crediting rubric, the historical numbers) and
     echo-guarded (post-audit scorer; guarded means from the audit artifact's
     correction block, valid for this surface because the audit proved
     row-identity by pre-guard score equality on all 218 rows) vs CTI-analysis
     per suite
  2. external-baseline ladder under the DECLARED served-text channel
     (results/external_baseline_model_coherent.json) — levels are pre-guard
     and labeled as such; paired per-row deltas are scorer-invariant because
     the compared arms serve byte-identical strings on the decisive rows
  3. manual audit summary (results/cti_manual_audit.json): annotator
     agreement, strict P/R/F1, adjudication, and machine-vs-human agreement
     before/after the echo guard

Writes results/section_vi_two_channel_tables.tex.
` |
| `scripts/gen_two_channel_tables.py` | 81 | `%   results/cti_manual_audit.json); the audited surface was proven` |
| `scripts/gen_two_channel_tables.py` | 215 | `% Echo-guard correction provenance: results/cti_manual_audit.json (echo_guard_correction): ` |
| `scripts/gen_two_channel_tables.py` | 228 | `% Historical note (Sep-22 campaign): its official technique (0.960) and actor (0.850) averages were BOTH-channel (served text max analysis). Its served-text-only equivalents are 0.493 / 0.666 under the raw rubric. Do not compare across channels; see results/technique_rubric_diff_investigation.json.` |
| `scripts/graph_consistency_bench.py` | 2 | `C1 re-query fingerprint battery (TDSC plan §4) — deterministic stratum.

The plan's C1 experiment: "Re-query battery: hostname, cat /etc/hostname,
uname -a, id, cat /etc/passwd, cat /etc/shadow, IMDS, repeated 20× per
session → contradiction rate 0 vs system-prompt baseline" plus the
adversarial round: "re-query with false facts injected in prompt →
contradiction recorded (not silent)".

Three configurations:

  graph-full       the real loop: fiction seeding (C1) + verify-before-serve
                   (C2) sharing one per-session FictionGraph
  no-enforcement   the HoneyGPT-style analogue: fiction block stripped from
                   the plan AND the verifier nulled — prompt-only pinning
  (mechanism)      direct FictionGraph probes: assert-once semantics, false-
                   fact adoption → contradiction RECORDED, verifier wiring

Metrics per config: contradictions per turn (target 0 in graph-full),
byte-identical replay rate (determinism), verifier coverage, and — for the
adversarial round — whether injected false facts are adopted or rejected.

Deterministic stratum (0 LLM tokens): the deceiver runs gateway-less, so
every response comes from the protocol fast-paths/templates. The LLM stratum
reuses this battery unchanged once quota resets.

Output: results/graph_consistency_bench.json
` |
| `scripts/graph_consistency_bench.py` | 335 | `results/graph_consistency_bench.json` |
| `scripts/human_blind_eval.py` | 2 | `Blind human evaluation protocol — "Real system or honeypot?" (S&P P0).

Builds a randomized, de-identified transcript packet for expert raters and
scores the collected ratings (detection accuracy, false-honeypot rate,
pairwise agreement, Cohen's κ / Krippendorff's α over binary verdicts).

Protocol (docs/FIELD_ETHICS.md §4):
  1. Sources: transcripts from real Linux captures, Cowrie, the vanilla-LLM
     arm, the stateful-LLM arm, and RAGIN (verified loop). Equal-mix packet,
     order shuffled with a fixed seed per rater (reproducible randomization).
  2. Raters see ONLY the transcript content — no arm names, no system info,
     no session metadata that leaks provenance. Transcripts are de-identified:
     hostnames/usernames are normalized to a common fake shape per transcript
     so naming style can't fingerprint an arm.
  3. Per transcript the rater answers: real or honeypot (binary), confidence
     1–5, realism 1–5, consistency 1–5, command correctness 1–5,
     detectability notes, and the reason for the decision (free text).
  4. Raters never see another rater's answers until everyone is done.

Usage:
  python scripts/human_blind_eval.py build --arms cowrie:10,vanilla_llm:10,ragin:10,real_linux:10       --out results/human_blind/packet_rater1.json --seed 11 --rater rater1
  python scripts/human_blind_eval.py score --packet results/human_blind/packet_rater1.json       --answers results/human_blind/answers_rater1.json
` |
| `scripts/human_blind_eval.py` | 83 | `Load n de-identified transcripts for an arm from the results tree.

    Source maps (extend as new arms complete):
      ragin        -> results/human_eval_full.json (verified-loop transcripts)
      vanilla_llm  -> results/external_baseline_llm_unverified.json per-row
      stateful_llm -> results/external_baseline_stateful_llm.json per-row
      real_linux   -> data/real_linux_transcripts.json (curated captures; add
                      before packet build — see FIELD_ETHICS §4 step 1)
      cowrie       -> data/cowrie_logs rotated captures, scripted-output shape
    ` |
| `scripts/jev_ab_eval.py` | 296 | `results/jev_ab_eval.json` |
| `scripts/jev_dwell_replay.py` | 2 | `Dwell-time impact of kind-aware deception — replay simulation on REAL Cowrie sessions.

Design (honest simulation, not live attackers):
  For each unique real session family (from data/cowrie_logs/), an LLM
  (deepseek-v4.1-flash-free) plays the attacker following that family's
  recorded playbook. Each turn:
    1. The attacker LLM emits the next command (greedy, 1 candidate).
    2. Hisoka generates the deception response TWICE:
         baseline : persona only (no Jev signal)
         treated  : persona + Jev attack-kind guidance (recorded assessments)
    3. The attacker LLM sees the response and decides: continue or leave.
  Dwell time is simulated turns (each turn ~= one command round-trip);
  we also track bait discovery (fake_service / planted path mentions)
  and the leave reason when the attacker quits.

The Jev severities/kinds come from the live gateway assessments recorded in
results/jev_real_logs_eval.json (real model output on real sessions).

Usage:
  RAGIN_LLM_* env (loaded from .env) .venv/bin/python scripts/jev_dwell_replay.py
` |
| `scripts/jev_dwell_replay.py` | 657 | `results/jev_dwell_replay.json` |
| `scripts/jev_hard_subset.py` | 2 | `Hard-subset A/B for the JEV fold-down claim: rerun the routing comparison
on the stratum where the deterministic floor is not already at ceiling.

The published A/B (jev_ab_eval.json, n=200) reported Δ=0.0 with BOTH arms at
100% floor-correctness — a ceiling comparison with zero statistical power.
This script re-runs the same eval machinery over the full 400-session held-out
corpus and slices the analysis to the only rows where JEV's adjustment could
matter: sessions whose deterministic baseline routing lands BELOW the tier's
risk floor. On the complement (floor already correct), JEV is powerless to
change the pass decision by design — it only escalates — so including those
rows measures nothing about subsumption.

Outputs results/jev_hard_subset.json with:
  - full-corpus counts (base failures on 400, not 200)
  - per-tier and per-family breakdown of informative rows
  - floor margins (how far below the floor the baseline lands)
  - the ceiling-resolution statement the paper now makes

Offline: Chrollo + Supervisor routing are deterministic; NO LLM quota is
consumed. A --with-jev flag optionally runs the live JEV arm when quota
allows; default is the offline informative-stratum census.

Usage:
    .venv/bin/python scripts/jev_hard_subset.py [--corpus 400] [--with-jev]
` |
| `scripts/jev_real_logs_eval.py` | 204 | `results/jev_real_logs_eval.json` |
| `scripts/jev_real_logs_eval.py` | 205 | `Saved -> results/jev_real_logs_eval.json` |
| `scripts/laya_ablation_analysis.py` | 1 | `Analyze the recorded real-inference pilot into matched ablation evidence.

Reads results/laya_research/real_inference_cpu_pilot.jsonl (raw records from the
actual model run) and computes per-case paired metrics against trivial baselines
(always-benign and random with seed), writing
results/laya_research/matched_ablation_analysis.json.

Baselines from data only — B0: predict benign for every case; R0: seeded random
coin. These are lower bounds a real assessment provider must exceed; no
unverifiable claim is made about Chrollo/Hisoka deltas because the full
downstream pipeline was not exercised in this pilot.
` |
| `scripts/laya_ablation_analysis.py` | 21 | `results/laya_research/real_inference_cpu_pilot.jsonl` |
| `scripts/laya_ablation_analysis.py` | 22 | `results/laya_research/matched_ablation_analysis.json` |
| `scripts/laya_blind_annotation_workflow.py` | 2 | `Offline blinded annotation workflow for the independent Laya evaluation.

This script does NOT fabricate human labels. It only:

 1. Loads the blinded packet (results/laya_research/blind_annotation_packet.json).
 2. Optionally reseeds the item order for a fresh annotator copy (deterministic
    seed per rater so the same rater can regenerate the same order, but different
    raters get different orders unless they explicitly share a seed).
 3. Emits an annotation template the rater fills by hand (JSON or CSV).
 4. Stores per-rater labels under results/laya_research/rater_labels/<rater>.json
    when the rater supplies them via a JSON file or programmatic input.
 5. Keeps the truth/manifest (independent_label_candidates.json) separate and
    never exposes it to raters.

Annotation schema (compact, cybersecurity SSH-task oriented):

  BENIGN
  RECON
  SUSPICIOUS
  EXPLOITATION
  PRIVILEGE_ESCALATION
  DATA_ACCESS
  OTHER_ATTACK
  UNCERTAIN

Binary mapping (derived later for evaluation, NOT shown to raters):

  BENIGN            -> benign
  RECON             -> malicious
  SUSPICIOUS        -> malicious (uncertain leaning malicious)
  EXPLOITATION      -> malicious
  PRIVILEGE_ESCALATION -> malicious
  DATA_ACCESS       -> malicious
  OTHER_ATTACK      -> malicious
  UNCERTAIN         -> unresolved (do not collapse silently)

The rater file schema:

  {
    "rater_id": "r1",
    "annotation_version": 1,
    "started_at": "...",
    "completed_at": "...",
    "order_seed": 12345,
    "labels": [
      {"case_id": "...", "label": "BENIGN", "notes": "...", "timestamp": "..."},
      ...
    ],
    "notes": "...",
    "interrupted": false
  }

Inter-rater agreement is computed only after labels are collected, in a
separate evaluation step, never here.
` |
| `scripts/laya_blind_annotation_workflow.py` | 67 | `results/laya_research/blind_annotation_packet.json` |
| `scripts/laya_blind_annotation_workflow.py` | 68 | `results/laya_research/independent_label_candidates.json` |
| `scripts/laya_blind_annotation_workflow.py` | 69 | `results/laya_research/rater_labels` |
| `scripts/laya_candidate_audit.py` | 2 | `Prediction-blind candidate quality audit.

Reads the v2 candidate pool and produces:
- results/laya_research/candidate_quality_audit.jsonl

This script must NOT consult Chrollo/Laya predictions, disagreement flags,
or confidence when deciding inclusion. It only looks at source/evidence quality.
` |
| `scripts/laya_candidate_pool_v2.py` | 2 | `Build expanded independent-label candidate pool v2 (maximally defensible pool).

Sources (in priority order):
1. data/cowrie_logs/ (historical controlled Cowrie sessions)
2. data/real_linux_transcripts.json (real admin-style transcripts)
3. data/sessions/*.jsonl (human_eval style sessions, attacker_input commands)

Output:
- results/laya_research/independent_label_candidates_v2.json
- results/laya_research/blind_annotation_packet_v2.json
- results/laya_research/annotation_manifest_v2.json

This script does NOT assign labels. It only builds a blinded, de-duplicated,
stratified candidate set from raw provenance-preserving material.

Leakage screening:
- Remove examples whose evidence contains obvious prompt-stuffing leakage
  tokens that would reveal evaluation context, e.g. the exact proof probe
  string used in serving validation.
- Flag words like "provider", "label", "true", "score" are NOT auto-rejected
  because they can appear in legitimate English cybersecurity text; instead
  only the specific serving probe string is excluded.
` |
| `scripts/laya_candidate_pool_v2.py` | 36 | `results/laya_research` |
| `scripts/laya_candidate_pool_v2.py` | 298 | `results/laya_research/rater_templates` |
| `scripts/laya_candidate_pool_v2.py` | 299 | `results/laya_research/rater_labels` |
| `scripts/laya_candidate_pool_v2.py` | 334 | `results/laya_research/annotation_examples` |
| `scripts/laya_candidate_quality_audit.py` | 2 | `Prediction-blind candidate quality audit for the Laya independent eval pool.

This script characterizes each of the 307 distinct candidates using only
observable evidence and provenance metadata. It must NOT consult Chrollo,
Laya, confidence, disagreement, or any model-prediction field when deciding
quality labels. It outputs a JSONL audit so later curation steps can be
reviewed independently of the confirmatory subset selection.

Output:
    results/laya_research/candidate_quality_audit.jsonl
` |
| `scripts/laya_candidate_quality_audit.py` | 25 | `results/laya_research/independent_label_candidates_v2.json` |
| `scripts/laya_candidate_quality_audit.py` | 26 | `results/laya_research/annotation_manifest_v2.json` |
| `scripts/laya_candidate_quality_audit.py` | 527 | `results/laya_research` |
| `scripts/laya_confirmatory_analysis.py` | 1 | `Confirmatory analysis pipeline for the Laya-vs-Chrollo independent evaluation.

This tool refuses to run its confirmatory analysis unless genuine rater label
files exist under results/laya_research/rater_labels/. Synthetic/fixture labels
used by tests must NEVER be written to that directory.

Usage:

  .venv/bin/python scripts/laya_confirmatory_analysis.py [--dry-run]

  (no real labels present)  -> prints "REFUSING:" and exits 2
  (labels present)          -> prints/ writes results/laya_research/confirmatory_analysis.json
` |
| `scripts/laya_confirmatory_analysis.py` | 338 | `No human-label join may be simulated; analysis is refused until genuine per-rater label files land in results/laya_research/rater_labels/.` |
| `scripts/laya_confirmatory_selection.py` | 2 | `Prediction-blind confirmatory subset selection for the Laya independent eval.

Selection rules:
- Use the candidate quality audit only.
- Exclude EXCLUDE-band cases.
- Deduplicate by cluster: one representative per cluster unless we need more
  cases to reach min_n.
- Stratified by observable evidence characteristics only:
    - source_family
    - context_depth
    - quality_band
    - interpretability
- Attempt a target near 120, allowed range 100-150.
- Never consult Chrollo / Laya / confidence / disagreement / model fields.

Outputs:
    results/laya_research/confirmatory_subset_manifest.json
    results/laya_research/confirmatory_case_ids.txt
` |
| `scripts/laya_decision_v2_exploratory_120.py` | 846 | `**. The 169-case primary holdout remains
unevaluated, unlabeled, and untouched. No policy or threshold tuning occurred.

## Artifact manifest

- Pre-run integrity: `results/laya_decision_v2/exploratory_120_pre_run_integrity.json`
- Input manifest: `results/laya_decision_v2/exploratory_120_input_manifest.json`
- Decision events: `results/laya_decision_v2/exploratory_120_laya_decisions.jsonl`
- Decision metrics: `results/laya_decision_v2/exploratory_120_decision_metrics.json`
- Workflow metrics: `results/laya_decision_v2/exploratory_120_workflow_metrics.json`
- Paired statistics: `results/laya_decision_v2/exploratory_120_paired_statistics.json`
- Evaluation freeze: `results/laya_decision_v2/exploratory_120_evaluation_freeze_v2.json`

` |
| `scripts/laya_e2e_two_sessions.py` | 1 | `Two local e2e runs: ChrolloAdapter → Sandbox → Harness (mandatory verification ON).

Identical benign synthetic inputs; RAGIN_LAYA_ENABLED=0 vs =1 (separate processes,
same checkpoint). Evidence: per-run session event log replay showing the
CLASSIFICATION event with/without a laya_assessment block, plus trace IDs.
Raw evidence: results/laya_research/e2e_sessions.json
` |
| `scripts/laya_independent_candidate_pool.py` | 2 | `Build the independent-label candidate pool and blinded annotation packet.

Provably model-free: reads only raw Cowrie logs + real_linux_transcripts.json,
normalizes SSH transcripts, strips all model/prediction/class metadata, assigns
opaque IDs, shuffles, and writes two artifacts:

  results/laya_research/independent_label_candidates.json  (full manifest,
    includes provenance META held separate from raters)
  results/laya_research/blind_annotation_packet.json       (packets only,
    shuffled, no class labels, no model outputs, no provenance metadata)

The blind packet is what a human rater sees. The candidates manifest keeps the
provenance/later-truth mapping in a separate file so it can be disclosed ONLY
after labels are collected, for evaluation.
` |
| `scripts/laya_independent_candidate_pool.py` | 28 | `results/laya_research/independent_label_candidates.json` |
| `scripts/laya_independent_candidate_pool.py` | 29 | `results/laya_research/blind_annotation_packet.json` |
| `scripts/laya_leakage_review_v2.py` | 2 | `Leakage review for the v2 candidate pool.

This script:
- loads the current blind packet
- inspects the flagged cases against their source files
- redacts or excludes cases whose evidence reveals ground truth / experiment context
- writes:
    results/laya_research/leakage_review_v2.json
and updates the blind packet if leakage is removed/redacted.

It does NOT look at Chrollo/Laya predictions.
` |
| `scripts/laya_manifest_consistency_check.py` | 15 | `results/laya_research/independent_label_candidates.json` |
| `scripts/laya_manifest_consistency_check.py` | 16 | `results/laya_research/blind_annotation_packet.json` |
| `scripts/laya_paired_comparison.py` | 1 | `Paired comparison summary for the Laya ON/OFF e2e runs plus the existing
45-case pilot. Reads results/laya_research/e2e_sessions.json (runtime behavior)
and real_inference_cpu_pilot.jsonl (classification quality on synthetic labeled
cases). Writes results/laya_research/paired_comparison.json.

Explicitly separates: runtime-behavior deltas (trace-proven) from
classification-quality deltas (synthetic labels, NOT independent evaluation
data). No statistical improvement claim is made.
` |
| `scripts/laya_real_inference_pilot.py` | 1 | `Real Laya inference pilot on synthetic SSH sessions (CPU, pinned revision).

Ground truth labels are assigned by construction: BENIGN_* = 0 (benign), MAL_* = 1 (malicious).
Evidence is written to results/laya_research/real_inference_cpu_pilot.jsonl.

Run with the RAGIN venv python (torch/laya installed there):
    .venv/bin/python scripts/laya_real_inference_pilot.py
` |
| `scripts/learning_curve_chrollo.py` | 2 | `Learning-curve study for the Chrollo classifier.

Trains the shipped configuration (500 trees / depth 16 / unweighted) on
growing stratified subsets of the 1,600-session training pool and
evaluates on the fixed 400-session held-out set, with multiple
subsample seeds per size. Fits a power law acc(n) = a - b * n^(-c) to
project the accuracy at 2x and 10x the current corpus and reports
whether more data would keep helping.

Outputs:
  results/model_quality/chrollo_learning_curve.png
  results/model_quality/chrollo_learning_curve.json

Usage:
    python scripts/learning_curve_chrollo.py [--reps 5]
` |
| `scripts/locked_ai_reference_evaluation_v1.py` | 212 | `results/laya_research/gating_preregistration.json` |
| `scripts/locked_ai_reference_evaluation_v1.py` | 400 | `- Prediction provenance: pre-reference hash and chronology verified for `results/laya_research/confirmatory_frozen_predictions.jsonl`.` |
| `scripts/merge_llama33_matrix.py` | 1 | `Merge the llama-3.3-70b third-family matrix to completion and rescore.

Sources (2026-09-27):
  - results/verifier_redteam_live_llama33_best.json        75 completed cases (pre-fix verdicts)
  - results/verifier_redteam_live_llama33_batch1_3cases_20260927.json
                                                           3 cases recovered from an orphaned batch
  - results/verifier_redteam_live_llama33_opencode_fill.json
                                                           16 cases authored via opencode free tier
                                                           (OpenRouter paid headroom exhausted; user decision)

Outputs:
  - results/verifier_redteam_live_llama33_complete.json   merged matrix, ALL drafts rescored
                                                           through the current (post-P1) verifier
  - results/verifier_llama33_rescored_after_fix.json      ladder updated with `after_complete`

Method notes:
  - Every stored draft text is re-run through run_case so the merged matrix is
    uniformly post-fix (the original 75 carry pre-fix verdicts).
  - Author fallback is disclosed per case: `author_model` lists which backend
    authored each variant; `author_pool` distinguishes llama-only cases from
    opencode-filled cases (paper must flag the substitution — author-swap is
    a variance source, not a verifier measurement).
` |
| `scripts/mtp_steering_eval.py` | 2 | `TDSC C3 battery — MITRE predictive baiting (mtp_steering_eval), offline.

Plan claim (C3): the deception plan is graph-informed — given the techniques
observed so far, the system ranks the attacker's *likely next* techniques and
seeds bait for them BEFORE they are attempted (proactive, not reactive).

Three measured axes, deterministic stratum (0 LLM tokens):

1. next-TTP top-k accuracy — over multi-turn attack chains grounded in the GT
   corpus, each turn predicts the next turn's techniques from the techniques
   observed in prior turns (production ThreatMapper extraction -> MITRE graph
   prediction). Reported as top-1 / top-3 accuracy + MRR.
2. Bait-steering hit rate — full DeceptionGraph runs per chain turn: does the
   plan's strategy_block actually carry bait for the NEXT turn's techniques?
3. Ablation gap — the same measure on no-bait-steer (A2) must be ~0: the gap
   between full and ablated is the steer signal's measured contribution.

The live-LLM stratum reuses the same chains and scorer once apmix resets.

Output: results/mtp_steering_eval.json
` |
| `scripts/mtp_steering_eval.py` | 383 | `results/mtp_steering_eval.json` |
| `scripts/mtp_steering_eval.py` | 384 | `
artifact: results/mtp_steering_eval.json  (` |
| `scripts/normalize_and_freeze_v3.py` | 14 | `results/laya_research` |
| `scripts/normalize_and_freeze_v3.py` | 247 | `results/laya_research/rater_packets_v3/` |
| `scripts/normalize_and_freeze_v3.py` | 458 | `results/laya_research/rater_labels_v3_ai/` |
| `scripts/normalize_and_freeze_v3.py` | 458 | `results/laya_research/rater_run_provenance_v3/` |
| `scripts/persona_recheck.py` | 67 | `results/hitl_audit_bench.jsonl` |
| `scripts/prepare_expert_ai_panel_v1a.py` | 11 | `results/laya_research` |
| `scripts/prepare_expert_ai_panel_v1a.py` | 166 | `results/laya_research/expert_ai_panel_preregistration_freeze_v1.json` |
| `scripts/prepare_expert_ai_panel_v1a.py` | 174 | `results/laya_research/rater_packets_v3/` |
| `scripts/prepare_v4_real_holdout_preregistration.py` | 13 | `results/decision_fusion_v4` |
| `scripts/prepare_v4_real_holdout_preregistration.py` | 53 | `results/decision_fusion_v4` |
| `scripts/prepare_v4_real_holdout_preregistration.py` | 53 | `results/laya_decision_v2` |
| `scripts/prepare_v4_real_holdout_preregistration.py` | 53 | `results/laya_decision_v3` |
| `scripts/prepare_v4_real_holdout_preregistration.py` | 53 | `results/laya_research` |
| `scripts/prepare_v4_real_holdout_preregistration.py` | 179 | `results/laya_decision_v2` |
| `scripts/prepare_v4_real_holdout_preregistration.py` | 241 | `results/laya_research/` |
| `scripts/prepare_v4_real_holdout_preregistration.py` | 242 | `results/decision_fusion_v4/` |
| `scripts/render_validation_section.py` | 2 | `Render the TDSC validation-status section of the results snapshot doc.

Reads the three validation artifact JSONs plus the persisted apmix quota
probe and emits markdown to stdout. azure_healthcheck.sh appends this to
results/azure_services_snapshot.md so the doc's numbers always come straight
from the artifacts — never hand-copied figures that rot.

Standalone usage: python3 scripts/render_validation_section.py
` |
| `scripts/render_validation_section.py` | 33 | `results/graph_consistency_bench.json` |
| `scripts/render_validation_section.py` | 34 | `results/ablation_battery.json` |
| `scripts/render_validation_section.py` | 35 | `results/mtp_steering_eval.json` |
| `scripts/render_validation_section.py` | 36 | `results/apmix_quota_status.json` |
| `scripts/render_validation_section.py` | 77 | `_artifact missing (`results/graph_consistency_bench.json`)_` |
| `scripts/render_validation_section.py` | 101 | `_artifact missing (`results/ablation_battery.json`)_` |
| `scripts/render_validation_section.py` | 124 | `_artifact missing (`results/mtp_steering_eval.json`)_` |
| `scripts/render_validation_section.py` | 127 | `results/bootstrap_ci.json` |
| `scripts/render_validation_section.py` | 164 | `_artifact missing (`results/bootstrap_ci.json`) — run `scripts/bootstrap_ci.py`_` |
| `scripts/render_validation_section.py` | 169 | `results/stability_run1_vs_run2.json` |
| `scripts/rescore_judge_panel.py` | 2 | `Corrected re-scoring of the live judge panel (persona stratum).

The 60-row persona stratum of the live benchmark was graded by the
deterministic realism judge (_score_persona_realism). Reading the persisted
rows against that scorer's actual terms surfaced three measurement artifacts,
not three system failures:

  1. Bait-deployment blindness — rows where the honeypot correctly served
     registered canary bait (API-key-shaped values from the bait templates)
     received no deployment credit and were additionally penalized for
     brevity. The judge punished the system's best behavior.
  2. Harness artifacts in the deception mean — rows whose transcript is a
     session-harness bug (e.g. an echo of the query text into a shell,
     producing ``command not found``) are not deception judgments and are
     reclassified as harness artifacts.
  3. Float precision — scores like 0.44999999999999996 were persisted raw.

This script re-scores offline (no LLM quota) and writes
results/live_benchmark_judge_panel_corrected.json with per-row corrections,
summary deltas, and an explicit canary-bias measurement.

Usage:
    .venv/bin/python scripts/rescore_judge_panel.py
` |
| `scripts/rescore_redteam_family.py` | 1 | `Rescore one stored live red-team family artifact through the CURRENT verifier.

Reads a persisted live-stratum artifact (space-bunny / deepseek / llama batch),
re-scores every stored draft text with the same ``run_case`` path as the live
harness, and writes a before->after artifact WITHOUT modifying the input.

Purpose (2026-09-27): after the W2 P0 extraction fixes + P1 danger-lexicon pass,
the other two author families must be re-measured so the cross-family
comparison is uniformly post-fix (same method as scripts/merge_llama33_matrix.py).

Usage::

    python scripts/rescore_redteam_family.py         --input results/verifier_redteam_live.json         --out results/verifier_redteam_live_space-bunny_rescored_after_fix.json
` |
| `scripts/retrain_chrollo_ngram.py` | 129 | `results/model_quality/seq_features_benchmark.json — baseline+ngram was the only feature family improving all three regimes (+6.0pp same-distribution p=1.2e-7; +3.9pp template-disjoint; +3.7pp strict bank-disjoint), while +phase/+all degraded the strict regime (overfit).` |
| `scripts/run_baseline_comparison.py` | 164 | `results/b4_baseline_comparison.json` |
| `scripts/run_baseline_comparison.py` | 176 | `Per-scenario rows so bootstrap_ci.py can compute paired CIs.

        Without row-level scores, the RAG-vs-baseline arm can only be
        reported as point averages (no CI). Row shape mirrors
        results/live_benchmark_audited.json so the CI battery can pair
        scenarios by name across arms.
        ` |
| `scripts/run_don_v2_substantive_final_v1.py` | 26 | `results/decision_fusion_v4/v4_hf2024_retrospective_holdout_freeze_v1a.json` |
| `scripts/run_don_v2_substantive_final_v1.py` | 27 | `results/decision_fusion_v4/hf2024_postfix_family_disjoint_v1/holdout_freeze.json` |
| `scripts/run_don_v2_substantive_final_v1.py` | 28 | `results/decision_fusion_v4/hf2024_substantive_final_v1/holdout_freeze.json` |
| `scripts/run_don_v2_substantive_final_v1.py` | 61 | `results/decision_fusion_v4/don_v2_substantive_final_v1/holdout_freeze.json` |
| `scripts/run_don_v2_substantive_final_v1.py` | 65 | `results/decision_fusion_v4/don_v2_command_aware/don_v2_freeze_v1.json` |
| `scripts/run_don_v2_substantive_final_v1.py` | 65 | `results/decision_fusion_v4/substantive_runtime_integration_v1/integration_validation_freeze_v1.json` |
| `scripts/run_don_v2_substantive_final_v1.py` | 65 | `results/decision_fusion_v4/v4_selected_logistic_policy.joblib` |
| `scripts/run_evidence_judge_paired_validation_v1.py` | 19 | `results/evidence_judge_paired_validation_v1` |
| `scripts/run_evidence_judge_paired_validation_v1.py` | 21 | `results/evidence_judge/evidence_judge_contract_freeze_v1.json` |
| `scripts/run_evidence_judge_real_data_ablation_v1.py` | 17 | `results/evidence_judge_real_data_ablation_v1` |
| `scripts/run_evidence_judge_real_data_ablation_v1.py` | 20 | `results/evidence_judge/evidence_judge_contract_freeze_v1.json` |
| `scripts/run_evidence_judge_real_data_ablation_v1.py` | 22 | `results/decision_fusion_v4/v4_hf2024_retrospective_holdout_freeze_v1.json` |
| `scripts/run_evidence_judge_real_data_ablation_v1.py` | 23 | `results/decision_fusion_v4/v4_hf2024_retrospective_holdout_freeze_v1a.json` |
| `scripts/run_evidence_judge_real_data_ablation_v1.py` | 24 | `results/decision_fusion_v4/hf2024_postfix_family_disjoint_v1/holdout_freeze.json` |
| `scripts/run_evidence_judge_real_data_ablation_v1.py` | 25 | `results/decision_fusion_v4/hf2024_substantive_final_v1/holdout_freeze.json` |
| `scripts/run_external_baseline.py` | 2 | `External baseline comparison on the version-of-record workload.

Four arms, same 218-query workload (123 technique + 35 actor + 60 persona),
same scorers as run_live_benchmark (deterministic string rubrics):

  cowrie            — vanilla Cowrie semantics: rule-based command output over
                      the real captured cowrie.json corpus, no LLM, no TTP
                      extraction beyond the adapter's command mapping.
  llm_unverified    — a bare LLM honeypot: persona prompt + attacker input,
                      no CTI retrieval, no fiction graph, no verifier, no
                      fallback. The "what current practice does" arm.
  stateful_llm      — HoneyGPT/LLM-SSHH pattern: committed host-state register
                      in the prompt, transcript memory, and an LLM
                      self-validation pass that regenerates on contradiction
                      but never fail-closes. The 2026 state-of-practice arm.
  rag_no_verifier   — full grounded pipeline (Chrollo + Don + Hisoka +
                      fiction graph + steering) with verification disabled:
                      drafts go to the wire unverified. Isolates the verifier's
                      contribution on top of the same generator.

The version-of-record campaign results (live_benchmark_zodiac_20260922*.json)
are loaded as the reference arm for the comparison table.

Usage:
    python scripts/run_external_baseline.py --arm cowrie
    python scripts/run_external_baseline.py --arm llm_unverified --limit 10   # smoke
    python scripts/run_external_baseline.py --arm stateful_llm --limit 10     # smoke
    python scripts/run_external_baseline.py --arm rag_no_verifier
    python scripts/run_external_baseline.py --arm all --report results/external_baseline.json

Each arm persists its own per-row report alongside the combined artifact, so
a quota death in one arm never loses the others (the crash-guard lesson).
` |
| `scripts/run_external_baseline.py` | 320 | `results/external_baseline_` |
| `scripts/run_external_baseline.py` | 1072 | `results/external_baseline.json` |
| `scripts/run_external_baseline.py` | 1073 | `results/live_benchmark_zodiac_20260922.json` |
| `scripts/run_hf2024_postfix_family_disjoint_v1.py` | 90 | `results/decision_fusion_v4/v4_selected_logistic_policy.joblib` |
| `scripts/run_hf2024_postfix_family_disjoint_v1.py` | 182 | `results/decision_fusion_v4/hf2024_postfix_family_disjoint_v1/holdout_freeze.json` |
| `scripts/run_hf2024_substantive_final_v1.py` | 149 | `results/decision_fusion_v4/hf2024_substantive_final_v1/holdout_freeze.json` |
| `scripts/run_hf2024_substantive_final_v1.py` | 197 | `results/decision_fusion_v4/v4_selected_logistic_policy.joblib` |
| `scripts/run_hf2024_v4_raw_execution.py` | 145 | `results/decision_fusion_v4/v4_hf2024_retrospective_raw_execution_freeze_v1.json` |
| `scripts/run_human_eval.py` | 2 | `Run the 8 ground-truth scenarios through the live RAGIN pipeline,
capture outputs, and produce pre-filled SessionEvaluation JSON for human scoring.

Usage:
    python scripts/run_human_eval.py
    python scripts/run_human_eval.py --output results/human_eval.json
    python scripts/run_human_eval.py --limit 3   # quick smoke test
` |
| `scripts/run_human_eval.py` | 72 | `results/human_eval.json` |
| `scripts/run_human_eval.py` | 140 | `results/hitl_audit_eval.jsonl` |
| `scripts/run_human_eval_parallel.py` | 2 | `Parallel human-eval runner: 8 GT scenarios concurrently through the LangGraph engine.

Same output schema as scripts/run_human_eval.py (pre-filled SessionEvaluation JSON +
raw pipeline outputs incl. verification/approval/plan) but wall-clock ~= one turn
instead of 8x, because each scenario's LLM calls are independent.

Usage:
    .venv/bin/python scripts/run_human_eval_parallel.py [--output results/human_eval_full.json]
` |
| `scripts/run_human_eval_parallel.py` | 30 | `results/human_eval_full.json` |
| `scripts/run_human_eval_parallel.py` | 63 | `results/hitl_audit_eval.jsonl` |
| `scripts/run_human_eval_subagents.py` | 2 | `Multi-persona LLM evaluator driver for RAGIN LLM-based evaluation.

Fans 7 evaluator personas out across 8 ground-truth scenarios (56 LLM calls)
with bounded concurrency, retries, danger-signal override, and consensus metrics
(pairwise Cohen kappa + Krippendorff alpha).  Run ``--dry-run`` to verify wiring.

Usage:
    python scripts/run_human_eval_subagents.py --dry-run
    python scripts/run_human_eval_subagents.py --input results/human_eval_full.json
    python scripts/run_human_eval_subagents.py --evaluators persona-strict-academic,persona-novice-reviewer
` |
| `scripts/run_human_eval_subagents.py` | 517 | `results/human_eval_full.json` |
| `scripts/run_human_eval_subagents.py` | 518 | `results/human_eval_subagents` |
| `scripts/run_live_benchmark.py` | 55 | `results/live_benchmark.json` |
| `scripts/run_live_benchmark.py` | 99 | `results/hitl_audit_bench.jsonl` |
| `scripts/run_v4_pre_execution_provenance_audit.py` | 11 | `results/decision_fusion_v4` |
| `scripts/run_v4_pre_execution_provenance_audit.py` | 102 | `results/decision_fusion_v4/v4_real_holdout_manifest_v1a.json` |
| `scripts/run_v4_pre_execution_provenance_audit.py` | 102 | `results/decision_fusion_v4/v4_real_holdout_selection_freeze_v1a.json` |
| `scripts/run_v4_pre_execution_provenance_audit.py` | 103 | `results/decision_fusion_v4/v4_real_evaluation_preregistration_freeze_v1.json` |
| `scripts/run_v4_pre_execution_provenance_audit.py` | 103 | `results/decision_fusion_v4/v4_real_holdout_independence_audit_v1.json` |
| `scripts/run_v4_pre_execution_provenance_audit.py` | 103 | `results/decision_fusion_v4/v4_real_holdout_manifest_v1a.json` |
| `scripts/run_v4_pre_execution_provenance_audit.py` | 103 | `results/decision_fusion_v4/v4_real_holdout_provenance_amendment_v1a.json` |
| `scripts/run_v4_pre_execution_provenance_audit.py` | 103 | `results/decision_fusion_v4/v4_real_holdout_selection_freeze_v1a.json` |
| `scripts/run_v4_pre_execution_provenance_audit.py` | 103 | `results/decision_fusion_v4/v4_selected_240_record_provenance_audit_v1.json` |
| `scripts/run_v4_real_evidence_recovery_audit.py` | 246 | `results/laya_research/sessions_ON` |
| `scripts/run_v4_synthetic_benchmark.py` | 194 | `results/decision_fusion_v4/evidence_gate_contract_v1.json` |
| `scripts/run_v4_synthetic_integration_smoke.py` | 110 | `results/decision_fusion_v4/v4_synthetic_integration_smoke_v1.json` |
| `scripts/score_human_eval.py` | 172 | `results/human_eval_full.json` |
| `scripts/score_human_eval.py` | 173 | `results/human_eval_scored` |
| `scripts/serve_provenance.py` | 2 | `Serve-path provenance for the live 218-query campaigns.

Answers the reviewer's question the paper must answer up front: of the
served responses, how many were produced by the verified-generation path
(LLM draft + serving-time verifier) and how many were served from vetted
deterministic content (protocol/bait fast-paths, fallback transcripts)?

Method (deterministic, offline): the gateway round-trip dominates the
latency of any LLM-in-the-loop turn (measured mean for generative turns
is tens of seconds; the slowest vetted fast-path serves complete in well
under a second, and even the longest protocol serves stay below 4 s).
A latency threshold of 4 s therefore separates the two serve paths with
a wide margin. Threshold sensitivity is reported (2 s, 6 s, 10 s) so the
headline number is not an artifact of the cut.

The protocol/bait fast-paths are NOT fallbacks in the degradation sense:
they are the loop's vetted deterministic rung (R0) serving by design —
credential-bait reveals, IMDS/SSH/authz protocol fictions, and the
template fan-out. The fallback-serves proper (verifier rejection ->
template swap) are a subset flagged by the verifier's ``fallback_served``
marker; the benchmark rows carry the verification verdict, and zero rows
record a failed verdict serve.

Outputs results/serve_provenance.json with per-suite and total splits for
both runs.

Usage:
    .venv/bin/python scripts/serve_provenance.py
` |
| `scripts/serve_provenance_v2.py` | 2 | `Serve-path provenance v2 — direct instrumentation, no latency inference.

Reads one or more live-campaign artifacts whose per-row results carry the
explicit ``serve_path`` label stamped by the graph loop (GENERATED_VERIFIED /
GENERATED_RETRY / GENERATED_UNVERIFIED / FASTPATH_DETERMINISTIC /
FALLBACK_VERIFIED / HITL_SERVED) and emits the serve-path split per suite.

This supersedes the latency-threshold estimate in serve_provenance.json: the
v1 method inferred the serve path from a 4 s round-trip cutoff (with threshold
sensitivity 2 s–10 s, where the split moved 88.1% → 67.0%). The graph loop now
stamps ``serve_path`` on every deception_response at the node that produced the
served bytes, so the split is an exact count, not an estimate. The old latency
method is kept as a cross-check: where both are available for the same run,
v2 reports the disagreement rate — every disagreement is a row the threshold
misclassified.

Usage:
    python scripts/serve_provenance_v2.py         --runs results/live_benchmark_zodiac_20260922.json                results/live_benchmark_zodiac_20260922_run2.json         --out results/serve_provenance_v2.json

Rows without a ``serve_path`` key are counted as UNKNOWN and reported
separately — they are rows produced before instrumentation or by a code path
that bypasses the graph loop; they must never be silently folded into a
labeled bucket.
` |
| `scripts/serve_provenance_v2.py` | 138 | `results/serve_provenance_v2.json` |
| `scripts/sp2027_rescue_behavior_benchmark.py` | 2 | `Held-out attacker-trajectory benchmark for the S&P rescue experiment.

This benchmark is deliberately provider-free.  It evaluates the security
controller on 400 held-out attacker sessions from ``data/training/test.jsonl``
and compares the current behavior-aware Supervisor against a skill-only
ablation.  Each session is replayed at multiple prefixes, so the unit of
analysis is an attacker trajectory rather than an isolated scripted query.

The benchmark answers four questions that the original 218-row workload could
not answer:

* Does the controller reach the command-derived risk floor early in a session?
* Does the behavior floor reduce dangerous under-routing relative to skill-only
  routing?
* What is the false-escalation cost on benign sessions?
* Are the results reproducible with a disjoint train/test corpus?

No network, LLM, provider quota, or field deployment is used.  The output is a
new evidence artifact under ``results/sp2027_rescue`` and never overwrites a
version-of-record result.
` |
| `scripts/sp2027_rescue_behavior_benchmark.py` | 194 | `results/sp2027_rescue/behavior_trajectory_benchmark.json` |
| `scripts/timing_fingerprint_rocauc.py` | 1 | `Attacker-side timing fingerprint — ROC-AUC experiment (plan item #11).

Question (paper §VI / W2 item): can an attacker distinguish RAGIN serves from
a real server by response timing alone? The TDSC paper names latency as the
one leaked channel; this experiment measures the channel and evaluates
mitigations.

Classes (all timing distributions are MEASURED, not assumed):
  - real       inter-command gaps from REAL Cowrie logs (data/cowrie_logs/*):
               the gap between an attacker's consecutive commands bundles
               attacker think time + server response — an UPPER bound on the
               traditional serve path's response time. Limitation stated in
               the artifact: we fingerprint against the session timing
               ENVELOPE, not the unobservable pure response latency.
  - ragin_llm  per-row latency_ms from the persisted benchmark runs
               (results/benchmark_report.json + results/live_benchmark_full.json):
               the measured LLM-in-the-loop serve class (min 2210 ms).
  - fastpath   the deterministic template serve path, timed in-process on the
               real code (AdaptiveDeceiver without a gateway → template +
               post-processing pipeline), covering common attacker commands.

Arms (per-workload-row observed latencies, mixture shares from the measured
serve-path provenance: ~88% verified LLM serves / ~12% vetted deterministic):
  - ragin_default    88% ragin_llm + 12% fastpath (the system as measured)
  - fastpath_only    100% fastpath (a coverage-raising mitigation; tests
                     whether an all-fast server is ITSELF fingerprintable)
  - fastpath_padded  each fastpath response padded (additive sleep) to a
                     target drawn from the real gap distribution — the viable
                     direction, since LLM latency can only be padded UP and
                     already sits above the real envelope.

Attacker model: windows of k=5 consecutive observed response latencies;
features = mean/std/min/max; logistic regression, 50/50 split, AUC on the
held-out half with a seeded bootstrap 95% CI; plus a single-feature AUC on
the raw gap (threshold analysis) and KS separability per arm.

Verdict gates:
  - leak_confirmed     AUC(ragin_default) >= 0.85
  - mitigation_viable  AUC(fastpath_padded) <= 0.65
  - fastpath_needs_pad AUC(fastpath_only) >= 0.65 (all-fast is also separable)

Usage::

    python scripts/timing_fingerprint_rocauc.py            # run + write artifact
    python scripts/timing_fingerprint_rocauc.py --windows 5
` |
| `scripts/timing_fingerprint_rocauc.py` | 138 | `results/benchmark_report.json` |
| `scripts/timing_fingerprint_rocauc.py` | 147 | `results/live_benchmark_full.json` |
| `scripts/timing_fingerprint_rocauc.py` | 349 | `measured serve-path provenance (results/serve_provenance.json reading)` |
| `scripts/two_channel_metrics.py` | 1 | `Two-channel §VI metrics — served-text vs CTI-analysis, declared separately.

Background (results/technique_rubric_diff_investigation.json): the Sep-22
reference artifact scored technique/actor composites by max()ing two channels
(served text + CTI analysis), while the W1 external-baseline arms scored
served text only — comparing them as one number manufactured a phantom
generator-model regression. The fix is declared channels, reported separately.

This script computes BOTH channels for the current-model grounded pipeline
(ragin_full config) over the 218-query VOR workload, using run_live_benchmark
itself (so every channel is scored by the code that owns it), and emits the
two-channel table pair for §VI.

Channel definitions:
  served_text   deception realism: what the attacker actually receives
                (technique/actor string match on response_text only)
  cti_analysis  intelligence value: what the pipeline IDENTIFIED from the
                interaction (Don extraction: ttps_extracted / analysis text /
                candidate_actors) — never served to the attacker

Usage::

    python scripts/two_channel_metrics.py --limit 3          # smoke
    python scripts/two_channel_metrics.py --budget-s 360     # budgeted batches
` |
| `scripts/v4_acquisition_integrity_checkpoint.py` | 82 | `results/decision_fusion_v4/v4_controlled_admin_capture_protocol_v1.json` |
| `scripts/validate_algorithms.py` | 2 | `Validation harness for the three revised algorithms (Chrollo, Don, Hisoka).

Runs minimal, deterministic checks that exercise the *claims* the paper
makes about each algorithm:

  - Chrollo (alg:chrollo): the reject band routes ambiguous scores to
    ``HoldForReview`` instead of escalating; KNN-impute fallback engages
    on small samples; output schema includes the 150-dim feature vector.

  - Don (alg:don): a poisoned document with low credibility is dropped
    before ranking; documents below the similarity floor are dropped;
    the dedup step collapses overlap between dense and sparse hits; the
    fused top-k honours the requested ``k_final``.

  - Hisoka (alg:hisoka): the static fallback (skill-tier canned
    response) is reachable; the expert gate requires BOTH precision and
    speed; the basic-tool set gates novice regardless of precision.

Output: ``results/algorithm_validation.json`` with per-test pass/fail,
counts, and observed timings. Designed to be self-contained — no
network, no LLM calls, no GPU.
` |
| `scripts/validate_release_artifacts.py` | 2 | `Release artifact path validator — closes review finding F3/F10 locally.

Parses canonical artifact references (``\path{...}``) out of the S&P
canonical appendix (``paper/sections/sp_appendix.tex``) and checks, from the
repository root:

1. Every reference that names an artifact/script/manuscript path must carry
   an explicit top-level prefix (``results/``, ``scripts/``, ``paper/``,
   ``data/``, ``docs/``). A bare name such as ``b4_baseline_zodiac_20260922.json``
   is flagged as a missing ``results/`` prefix defect — it does not resolve
   from the repo root as written.
2. Every prefixed reference must resolve to a file (or directory for
   ``*/``-suffixed entries) that exists at that resolved path.
3. Every bare reference must still have its payload present under
   ``results/`` — otherwise it is a missing-file defect as well as a
   prefix defect.

Read-only: never writes, copies, or edits any repository file. Fully offline.

Usage::

    python scripts/validate_release_artifacts.py
    python scripts/validate_release_artifacts.py --tex paper/sections/sp_appendix.tex         --results-dir results --root .

Exit codes: 0 — no path defects; 1 — at least one prefix or missing-file
defect, or the tex source could not be read.
` |
| `scripts/validate_release_artifacts.py` | 42 | `results/` |
| `scripts/validate_release_artifacts.py` | 175 | `  [missing results/ prefix] ` |
| `scripts/verifier_ci_cluster_bootstrap.py` | 2 | `Cluster-bootstrap confidence intervals for the induced-draft battery.

Why this exists
---------------
``results/verifier_redteam_cross_family.json`` reports precision/recall with
Wilson score intervals computed over *drafts*. Several drafts are generated per
case (one per repeat), so drafts inside a case are not independent and a
binomial interval over them is optimistically narrow. This script recomputes
the same quantities with a cluster bootstrap that resamples **cases**, which is
the unit the battery actually draws independently.

Inputs are the persisted per-case artifacts; nothing is re-scored and no
provider call is made. The point estimates are asserted against the published
``overall`` block of each artifact, so a drift in either the artifacts or this
aggregation fails loudly instead of silently widening an interval.

Usage::

    python scripts/verifier_ci_cluster_bootstrap.py            # write artifact
    python scripts/verifier_ci_cluster_bootstrap.py --check    # verify only
` |
| `scripts/verifier_ci_cluster_bootstrap.py` | 182 | `results/` |
| `scripts/verifier_ci_manifest.py` | 2 | `Generate a deterministic SHA-256 manifest for the pinned verifier red-team
artifacts + research-integrity provenance metadata.

Used by CI (artifact-integrity job) and reproducible locally by researchers.
No network, no LLM keys, no inference — pure local filesystem hashing.

Usage:
    python scripts/verifier_ci_manifest.py         --artifacts results/verifier_redteam.json                     results/verifier_redteam_live.json                     results/verifier_redteam_live_deepseek-v4-flash-free.json                     results/verifier_redteam_live_space-bunny-free_prefix.json         --out results/verifier_redteam_artifacts_manifest.json         --commit HEAD --branch main
` |
| `scripts/verifier_ci_manifest.py` | 74 | `results/verifier_redteam_artifacts_manifest.json` |
| `scripts/verifier_harm_probe.py` | 2 | `Probe where the verifier's coverage ends: coherent-but-harmful drafts.

Answers the question the canonical red-team corpus cannot: when a draft is
fluent, contains no tell, is consistent with the session fiction, and is still
harmful, does the serving-time gate catch it?

Method (offline, deterministic, no provider): score the ``H`` corpus from
``scripts/verifier_harm_cases.py`` through the real
``FictionConsistencyVerifier.verify`` used on the serving path, and report
what fired. The suite is additive — ``results/verifier_redteam.json`` is not
read or rewritten, so the canonical 105-case result stays reproducible.

Two readings are reported and they differ, which is the point:

``detected_by_any_check``
    the operational question — was this draft stopped before it reached the
    wire, by any check?
``caught_by_targeted_check``
    the narrower question the canonical suite scores — was it stopped *and*
    did the finding name the check the case targets?

A case can be stopped by the identity or consistency layer and still be a
danger-gate blind spot, so the two are reported separately rather than
collapsed.

Usage::

    python scripts/verifier_harm_probe.py           # run + write artifact
    python scripts/verifier_harm_probe.py --check   # verify only, no write
` |
| `scripts/verifier_redteam.py` | 1 | `Verifier red-team harness — induce verifier failures, report per-check P/R.

Closes the evaluation gap the T-IFS review named (M2 / author question 2):
the live campaigns show the verifier's *coverage* (zero unverified serves,
zero fallback serves), but its *selectivity* — does it reject the drafts it
should and pass the drafts it should not — was only sampled by the C1
adversarial round and the five mechanism checks. This harness measures
selectivity directly, per check.

Method (no LLM, no network — the verifier is a decision procedure, so
inducing its failures is an offline computation):

1.  Run a labeled corpus of attack and negative cases
    (``scripts/verifier_redteam_cases.py``) through the real
    ``FictionConsistencyVerifier.verify``.
2.  A case counts as caught when the verifier rejects the draft AND the
    rejection names the targeted check (a reject for the wrong reason is
    reported separately as a misattributed rejection).
3.  Per-check precision/recall over the cases that target that check.
    Recall = caught / should_reject; Precision = caught / (caught +
    false-positive rejects among should_pass cases targeting that check).
4.  Overall verdict gates follow the repo's artifact style:
    recall must be 1.0 on every targeted check, precision must be 1.0
    (no false positives), and every rejection must name the right check.

Outputs ``results/verifier_redteam.json`` with per-case verdicts so any
regression pins the exact failing case key.

Usage::

    python scripts/verifier_redteam.py            # run + write artifact
    python scripts/verifier_redteam.py --strict   # exit 2 on any gate failure
` |
| `scripts/verifier_redteam.py` | 150 | `artifact path (default results/verifier_redteam.json)` |
| `scripts/verifier_redteam_check.py` | 2 | `Artifact-consistency checker — pin the paper's red-team claims to artifacts.

The paper (§VI-C live-miss census, App. A artifact index) prints three
decimals; the artifacts store four-decimal raws (e.g. raw 0.9306 prints as
0.931, 0.9945 as 0.995).  The first manual cross-check produced seven false
failures from exactly this gap: exact-equality comparisons against printed
values, and a wrong ``cases`` field semantics (the offline artifact stores
``cases`` as a LIST of per-case dicts — count it with ``len``; the live
artifacts store it as an INT — compare it directly).  This checker encodes
the corrected comparison logic so paper<->artifact drift fails loudly and
permanently, offline, with no network and no imports from the live harness.

What is pinned (each claim cites the paper text it guards):

1.  ``results/verifier_redteam.json`` — offline stratum: 105 canonical cases
    (96 + the L4 third-family harvest lock), overall P=R=1.000, zero FPs, no
    misattributed rejections, and every per-check P/R
    (danger/identity/consistency/degenerate) at 1.000
    (§VI-C: "precision 1.000 and recall 1.000 overall and on every check").
2.  ``results/verifier_redteam_live_deepseek-v4-flash-free.json`` — 236
    drafts; precision 1.000 with zero FPs across 63 benign drafts, Wilson
    P CI 0.977--1.000; recall 0.931, CI 0.883--0.960; per-case verdict
    agreement 0.988 (79/80).
3.  ``results/verifier_redteam_live.json`` — space-bunny post-fix
    re-derivation on the grown suite: 261 drafts; precision 0.995 with a
    single residual FP over 68 benign drafts; recall 0.943; agreement 1.000.
4.  ``results/verifier_redteam_live_space-bunny-free_prefix.json`` — pre-fix
    run: precision 0.994, recall 0.942, agreement 1.000.

Every artifact with an ``overall`` block is also checked for internal
count consistency (tp+fn = should_reject, tn+fp = should_pass, and the
stored P/R match the counts at printed precision) so a corrupted count
fails even if the headline metrics were edited to match.

Usage::

    python scripts/verifier_redteam_check.py                 # repo artifacts
    python scripts/verifier_redteam_check.py --results-dir D # other dir

Exit codes: 0 all checks pass, 1 any check fails (or an artifact is
missing/unreadable).  Fully offline; safe to run in CI.
` |
| `scripts/verifier_redteam_check.py` | 252 | `directory holding the red-team artifacts (default: repo results/)` |
| `scripts/verifier_redteam_cross_family.py` | 1 | `Cross-family live red-team comparison — three author families, post-fix verifier.

Inputs (read-only):
  - results/verifier_redteam_live_space-bunny_rescored_after_fix.json   (space-bunny-free, 89 cases)
  - results/verifier_redteam_live_deepseek-v4-flash-free_rescored_after_fix.json (deepseek-v4-flash-free, 80 cases)
  - results/verifier_redteam_live_llama33_complete.json                 (llama-3.3-70b + opencode fill, 94 cases)

Outputs:
  - results/verifier_redteam_cross_family.json

The comparison reports, per family:
  - full-pool post-fix precision/recall (variant level, valid drafts)
  - the 80-case common subset (every family's key intersection) for an
    apples-to-apples table
  - the authentic pre-fix baseline (stored verdicts) and the recall delta
` |
| `scripts/verifier_redteam_cross_family.py` | 32 | `results/verifier_redteam_live_space-bunny_rescored_after_fix.json` |
| `scripts/verifier_redteam_cross_family.py` | 33 | `results/verifier_redteam_live_deepseek-v4-flash-free_rescored_after_fix.json` |
| `scripts/verifier_redteam_cross_family.py` | 34 | `results/verifier_redteam_live_llama33_complete.json` |
| `scripts/verifier_redteam_opencode_fill.py` | 1 | `Fill remaining live red-team cases via opencode free-tier author models.

Context (2026-09-27): the llama-3.3-70b matrix had 19 cases × 3 variants
unauthored because the OpenRouter key's paid headroom was structurally
exhausted (402 "can only afford 44 tokens"; limit_reset=null — promo credit,
no reset cycle). User decision: use opencode's own free model tier instead of
adding credits. This runner shells out to ``opencode run -m <model> --pure``
per authoring call (one-shot agent mode, no stored credentials needed),
extracts the draft from a <<<DRAFT ... DRAFT>>> sentinel, and scores it with
the SAME ``run_case`` path as ``verifier_redteam_live.py``.

Differences vs the canonical live harness (documented in the artifact):
  - author backend is opencode agent mode (temperature not directly settable;
    variance comes from the variant instruction in the shared prompt)
  - per-variant ``author_model`` records which free model authored the draft
    (fallback chain on 429/timeout/refusal)
  - writes ONLY the --out artifact (never results/verifier_redteam_live.json)

Usage::

    python scripts/verifier_redteam_opencode_fill.py         --only "K1,K2,K3,K4"         --out results/verifier_redteam_live_llama33_opencode_fill.json
` |

## Manuscript source result references

Literal result references in LaTeX are reported for traceability. A manuscript citation to a result path does not itself establish that the displayed claim was regenerated from the current code or data snapshot.

| Manuscript file | Line | Literal reference |
|---|---:|---|
| `paper/appendix.tex` | 125 | `results/live_benchmark_zodiac_20260922.json` |
| `paper/appendix.tex` | 127 | `results/live_benchmark_zodiac_20260922_run2.json` |
| `paper/appendix.tex` | 131 | `results/b4_baseline_zodiac_20260922.json` |
| `paper/figures/generated_values.tex` | 7 | `results/bootstrap_ci.json` |
| `paper/figures/generated_values.tex` | 8 | `results/stability_run1_vs_run2.json` |
| `paper/figures/generated_values.tex` | 9 | `results/b4_baseline_zodiac_20260922.json` |
| `paper/figures/generated_values.tex` | 10 | `results/model_quality/chrollo_calibration.json` |
| `paper/figures/generated_values.tex` | 11 | `results/sp2027_rescue/behavior_trajectory_benchmark.json` |
| `paper/sections/appendix.tex` | 164 | `results/live_benchmark_zodiac_20260922.json` |
| `paper/sections/appendix.tex` | 166 | `results/live_benchmark_zodiac_20260922_run2.json` |
| `paper/sections/appendix.tex` | 170 | `results/b4_baseline_zodiac_20260922.json` |
| `paper/sections/appendix.tex` | 316 | `results/figure_geometry_audit.json` |
| `paper/sections/sp_appendix.tex` | 18 | `results/b4_baseline_zodiac_20260922.json` |
| `paper/sections/sp_appendix.tex` | 19 | `results/external_baseline_model_coherent.json` |
| `paper/sections/sp_appendix.tex` | 20 | `results/verifier_redteam.json` |
| `paper/sections/sp_appendix.tex` | 21 | `results/verifier_redteam_supported_claims.json` |
| `paper/sections/sp_appendix.tex` | 22 | `results/verifier_redteam_cross_family.json` |
| `paper/sections/sp_appendix.tex` | 23 | `results/verifier_ci_cluster_bootstrap.json` |
| `paper/sections/sp_appendix.tex` | 24 | `results/verifier_harm_probe.json` |
| `paper/sections/sp_appendix.tex` | 25 | `results/live_benchmark_zodiac_20260922.json` |
| `paper/sections/sp_appendix.tex` | 26 | `results/live_benchmark_zodiac_20260922_run2.json` |
| `paper/sections/sp_appendix.tex` | 27 | `results/stability_run1_vs_run2.json` |
| `paper/sections/sp_appendix.tex` | 62 | `results/hitl_audit_bench.jsonl` |
| `paper/sections/sp_appendix.tex` | 69 | `results/sp2027_rescue/behavior_trajectory_benchmark.json` |
| `paper/sections/two_channel_tables.tex` | 6 | `results/cti_manual_audit.json);` |
| `paper/sections/two_channel_tables.tex` | 69 | `results/cti_manual_audit.json` |
| `paper/sections/two_channel_tables.tex` | 71 | `results/technique_rubric_diff_investigation.json.` |

## Interpretation and audit boundary

- Use `SYSTEM_ARCHITECTURE_CURRENT.md` for the runtime flow, module roles, deployment split, observed result families, and findings about documentation drift.
- For any concrete artifact, follow its runner and configuration, then verify the run manifest, input hashes, timestamps, and status fields. A path string alone cannot prove producer-consumer direction or that an output is frozen/admissible.
- Source parsing and reference extraction are static checks. They do not execute optional imports, services, model providers, Rust binaries, notebooks, shell launchers, or experiment pipelines.
- Result JSON/JSONL structure was separately scanned for the architecture overview; this index intentionally excludes result payload contents and raw session data.

