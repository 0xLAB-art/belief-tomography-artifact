# 08 — Research Reproducibility Audit

**Method:** Trace experiment-to-paper provenance for the verifier redteam claims and related metrics. Distinguish artifact consistency (do the numbers match the paper?) from scientific validity (do the experiments support the claims?).

## 8.1 Artifact consistency — VERIFIED

The `scripts/verifier_redteam_check.py` checker validates 47 claims against 4 canonical artifacts. All 47 PASS.

### Claim-to-artifact mapping

| Paper claim (§VI-C) | Artifact | Checker claims | Status |
|---------------------|----------|----------------|--------|
| "precision 1.000 and recall 1.000 overall and on every check" (offline) | verifier_redteam.json | 16 claims (n_cases=105, cases list len=105, P=1.000, R=1.000, FP=0, FN=0, should_reject=78, should_pass=27, misattributed_keys=[], all_gates_pass=True, 4 per-check P/R=1.000) | ✅ PASS |
| "precision 1.000 (95% Wilson CI 0.977–1.000, zero false positives across 63 benign drafts), recall 0.931 (CI 0.883–0.960), per-case verdict agreement 0.988" over "236 drafts" | verifier_redteam_live_deepseek-v4-flash-free.json | 15 claims (model=deepseek-v4-flash-free, authored_drafts=236, cases=80, P=1.000, FP=0, should_pass=63, Wilson P lo=0.977, Wilson P hi=1.000, R=0.931, Wilson R lo=0.883, Wilson R hi=0.960, agreement rate=0.988, agree=79, total=80, authoring_errors=0) | ✅ PASS |
| "precision 0.995 with a single residual FP … recall 0.943, agreement 1.000" over "261 drafts" (post-fix canonical live) | verifier_redteam_live.json | 9 claims (model=space-bunny-free, authored_drafts=261, cases=89, P=0.995, FP=1, should_pass=68, R=0.943, agreement rate=1.000, authoring_errors=0) | ✅ PASS |
| "re-derived the deepseek result almost exactly (precision 0.994, recall 0.942, agreement 1.000)" (pre-fix) | verifier_redteam_live_space-bunny-free_prefix.json | 5 claims (model=space-bunny-free, cases=80, P=0.994, R=0.942, agreement rate=1.000) | ✅ PASS |

### Internal consistency checks

The checker also validates that counts are internally consistent (tp+fn=should_reject, tn+fp=should_pass, stored P/R match counts at printed precision). All PASS.

### Rounding contract (AC4)

The `r3()` helper maps 4-decimal raws to 3-decimal paper prints:
- 0.9306 → 0.931 (deepseek recall)
- 0.9415 → 0.942 (prefix recall)
- 0.9767 → 0.977 (deepseek Wilson P lo)
- 0.9938 → 0.994 (prefix precision)
- 0.9945 → 0.995 (post-fix precision)
- 0.9875 → 0.988 (deepseek agreement rate)

All PASS. This closes the gap that caused 7 false failures in the first manual cross-check.

## 8.2 Provenance records

### verifier_artifacts_manifest.json

```json
{
  "kind": "verifier_redteam_artifact_manifest",
  "generated_by": "scripts/verifier_redteam_check.py",
  "artifacts": [
    {"artifact": "verifier_redteam.json", "sha256": "8f19dde...", "size_bytes": 48744},
    {"artifact": "verifier_redteam_live_deepseek-v4-flash-free.json", "sha256": "11ef44f...", "size_bytes": 131246},
    {"artifact": "verifier_redteam_live.json", "sha256": "3f6f93f...", "size_bytes": 147625},
    {"artifact": "verifier_redteam_live_space-bunny-free_prefix.json", "sha256": "a5308f0...", "size_bytes": 131251}
  ]
}
```

### verifier_integrity_provenance.json

Records: generated_at_utc=2026-10-10T22:00:00+00:00, git_commit=f0c4042c0eb2ee25854796b770ea440f0b5851b2, git_branch=main, is_dirty=true, python_version=3.12.3, checker_script=scripts/verifier_redteam_check.py, manifest_out=results/verifier_artifacts_manifest.json.

**Note:** `is_dirty: true` — the repo had uncommitted changes when the provenance was generated. This is expected for a development repo but means the provenance record does not guarantee a clean git checkout reproduces the artifacts.

## 8.3 Experiment populations — DO NOT MERGE

| Population | Size | Description | Artifact |
|------------|------|-------------|----------|
| Offline verifier stratum | 105 cases | Canonical red-team cases, 4 check layers, no LLM involvement | verifier_redteam.json |
| Live deepseek-v4-flash-free | 236 drafts, 80 cases | Space-bunny-free model, post-fix | verifier_redteam_live_deepseek-v4-flash-free.json |
| Live space-bunny-free (post-fix) | 261 drafts, 89 cases | Second-author re-derivation, grown suite | verifier_redteam_live.json |
| Live space-bunny-free (pre-fix) | 80 cases | Pre-fix baseline | verifier_redteam_live_space-bunny-free_prefix.json |
| Synthetic SSH experiments | (various) | capture_real_linux_transcripts.py, synthetic training data | data/sessions/, training manifests |
| Field observations | 6932 session files | Real attacker sessions (if field deployed) | data/sessions/ses-*.jsonl |
| CTI manual audit | 766KB corpus | Blinded annotator packets (3 annotators A/B/C) | cti_manual_audit_corpus.json, cti_audit_annotations_*.json |
| Human blind eval | multiple scored dirs | human_blind_eval.py runs | results/human_blind/, human_eval_scored* |
| External baselines | multiple JSONs | run_external_baseline.py reruns | external_baseline*.json |
| Ablation battery | 5 ablation_audit_*.jsonl + ablation_battery.json | Ablation: noapproval, nobait, nofiction, nograph, noverify, full | ablation_battery.py |

**Critical:** These populations must NOT be merged when reporting. The offline stratum (105 cases, P=R=1.000) is a property of the verifier itself on canonical cases. The live strata (236-261 drafts, P=0.995-1.000, R=0.931-0.943) are property of the verifier + model combination on attacker-authored drafts. They answer different questions.

## 8.4 Scientific validity assessment

### Strengths

1. **Ground-truth independence:** The offline verifier stratum (verifier_redteam.json) uses canonical cases with known should_reject/should_pass labels. The live strata use attacker-authored drafts with independent adjudication. The CTI manual audit uses blinded annotator packets (3 independent annotators, blinding key in cti_audit_blinding_key.json).

2. **Artifact pinning:** The checker pins exact counts, metrics, and rounding. Tampering flips exit code to 1 and names the drift.

3. **Wilson CIs:** Bootstrap CIs are computed (bootstrap_ci.py, results/bootstrap_ci.json). The paper reports Wilson 95% CIs for precision and recall.

4. **Multiple model families:** Deepseek-v4-flash-free AND space-bunny-free both tested. Pre-fix AND post-fix both archived.

5. **Ablation:** 5 ablation conditions (noapproval, nobait, nofiction, nograph, noverify) + full. Each ablation audit has a JSONL file.

6. **Baseline comparison:** External baselines include cowrie_guarded_rerun, hostfiction comparisons, and ragin_full_repro variants. Multiple baseline artifacts exist (external_baseline_comparison.json, b4_baseline_comparison.json, cowrie_comparison.json).

7. **Reproducibility scripts:** scripts/verifier_redteam_check.py is fully offline (no network, no imports from live harness). bootstrap_ci.py, two_channel_metrics.py, gen_two_channel_tables.py are reproducible.

### Gaps and threats to validity

1. **Denominator clarity:** The paper's §VI-C claims mix "236 drafts" with "80 cases" — the 236 is authored drafts, 80 is the case suite size. The checker correctly distinguishes these (authored_drafts=236, cases=80). A reader could confuse them. The provenance record helps but the paper text should be clear.

2. **Model availability:** The models used (deepseek-v4-flash-free, space-bunny-free) are OpenCode CLI bridge models. If the bridge or model is unavailable, the live experiments cannot be re-run. The offline stratum (verifier_redteam.json) IS reproducible without any model — it's pure verifier logic on canonical cases.

3. **Single reviewer for some claims:** The CTI manual audit has 3 annotators but the paper's human evaluation may rely on fewer. Check human_blind_eval.py and human_eval_scored* for the actual rater count.

4. **Unreported failures:** The live strata report precision/recall but NOT the full distribution of failure modes. The offline stratum has per-check P/R (danger/identity/consistency/degenerate all at 1.000) but the live strata only report overall P/R and agreement. What kinds of drafts fail? The artifacts may contain this but it's not in the checker's claims.

5. **Confidence intervals:** Wilson CIs are reported for precision and recall, but NOT for the per-check rates in the live strata. The offline stratum has per-check P/R=1.000 (exact, no CI needed) but the live strata only have overall CIs.

6. **Missing baseline denominator:** The paper compares against "vanilla honeypot" baselines but the exact baseline configuration and sample size may not be fully specified. Check cowrie_comparison.json, b4_baseline_comparison.json, external_baseline_comparison.json for denominators.

7. **Field observation bias:** If field data (6932 session files) is used in the paper, the attacker population is self-selected (only attackers who targeted the honeypot). This is inherent to honeypot research but should be acknowledged as a threat to external validity.

8. **Synthetic training data for Chrollo:** The classifier is trained on synthetic data (scripts/generate_training_data.py, 2000 sessions). If the synthetic data distribution doesn't match real attacker behavior, the classifier's real-world accuracy may differ from the reported 0.8875.

9. **Artifact lineage:** While the 4 canonical artifacts have a provenance record, the intermediate result files (cti_manual_audit_corpus.json is 766KB, external_baseline*.json are 39-91KB each) do NOT have individual provenance records. Lineage from raw experiment to these files is documented in scripts but not machine-checkable.

## 8.5 What the paper claims vs what artifacts support

| Paper section | Claim | Artifact support | Gap |
|---------------|-------|------------------|-----|
| §VI-C (offline) | P=1.000, R=1.000, zero FPs/FNs, 105 cases | ✅ verifier_redteam.json fully matches | None |
| §VI-C (live deepseek) | P=1.000, R=0.931, CI 0.977-1.000 / 0.883-0.960, agreement 0.988, 236 drafts, 80 cases, 63 benign, zero FPs | ✅ verifier_redteam_live_deepseek-v4-flash-free.json fully matches | None |
| §VI-C (live space-bunny post-fix) | P=0.995, R=0.943, agreement 1.000, 261 drafts, 89 cases, single FP, 68 benign | ✅ verifier_redteam_live.json fully matches | None |
| §VI-C (live space-bunny pre-fix) | P=0.994, R=0.942, agreement 1.000, 80 cases | ✅ verifier_redteam_live_space-bunny-free_prefix.json matches | None |
| Chrollo classifier | 0.8875 accuracy, Wilson CI [0.853, 0.914] | ⚠️ benchmark_report.json exists; needs check | Not verified this audit |
| CTI manual audit | ( blinded annotator agreement ) | ⚠️ cti_manual_audit.json exists; needs check | Not verified this audit |
| Human eval | ( scoring + correlation ) | ⚠️ results/human_blind/, human_eval_scored* exist; needs check | Not verified this audit |
| Ablation | ( effect of each component ) | ⚠️ ablation_battery.json + 5 JSONL files exist; needs check | Not verified this audit |
| External baselines | ( comparison to vanilla honeypot ) | ⚠️ external_baseline*.json exist; needs check | Not verified this audit |

## 8.6 Reproducibility verdict

**Offline verifier stratum: FULLY REPRODUCIBLE.** The checker is offline, dependency-free (beyond stdlib), and pins exact artifact contents. Any researcher can run `python scripts/verifier_redteam_check.py` and get the same 47/47 PASS result, provided the 4 artifact files are unchanged.

**Live strata: CONDITIONALLY REPRODUCIBLE.** Re-running requires the OpenCode CLI bridge with the specific models (deepseek-v4-flash-free, space-bunny-free) at the time of the original runs. Model behavior may have changed since. The artifacts are preserved and pinned, but re-generation may yield different results.

**Classifier + CTI + human eval + ablation + baselines: NOT VERIFIED this audit.** Artifacts exist but the reproducibility scripts and artifact consistency were not checked. These need a follow-up audit.

**Overall:** The core verifier claims (the paper's primary novelty — C2 of the TDSC plan) are solidly anchored to artifacts with a working consistency checker. The surrounding claims (classifier accuracy, CTI audit, human eval, baselines) need verification before the paper is final.
