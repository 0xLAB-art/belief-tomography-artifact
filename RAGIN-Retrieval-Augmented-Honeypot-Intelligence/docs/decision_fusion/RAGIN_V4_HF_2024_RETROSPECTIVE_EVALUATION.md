# RAGIN V4 HF 2024 Retrospective Evaluation

## Outcome

The HF 2024 source was verified and a new 240-case retrospective holdout was frozen before any V4 arm execution. The study stopped at preflight because the required blinded reference stage cannot currently be authorized: no non-paid, locally runnable reference provider with a frozen identity and prompt is available. No raw arm output, reference label, or effectiveness metric was produced.

## Source

The pinned revision is `d201aafbbcbb5347078ca64f06c5428fa6814bc9`. The downloaded sessions, commands, and raw-sample hashes match the requested values. The sessions file contains 6,658 valid 2024 rows, 6,658 unique published `session_id` values, 6,658 unique source-IP values, 33,259 nonempty command entries, and no command-count mismatches. The source README states that `session_id` is an anonymized attacker source-IP grouping, not a native Cowrie session. The raw sample is format reference only and contains no native session field.

The retrospective observational unit is therefore one source-IP-group command sequence. This study makes no native-session independence claim. Source grouping, repeated automated activity, and dataset preprocessing induce dependence and are limitations rather than grounds for relabeling the data.

## Holdout

The deterministic namespace is `RAGIN_V4_HF_2024_RETROSPECTIVE_V1`. Selection sorts SHA256 of namespace, source group ID, and the SHA256 of the final nonempty command. Exactly one case was selected per source group, with the final nonempty command as current input and preceding published commands represented only as context. No ATT&CK label, severity, policy output, retrieval score, or expected outcome entered selection.

The holdout contains exactly 240 cases and is frozen at [v4_hf2024_retrospective_holdout_freeze_v1a.json](../../results/decision_fusion_v4/v4_hf2024_retrospective_holdout_freeze_v1a.json). A pre-execution self-check corrected the separator serialization from a literal `\\0` string in the preserved v1 artifact to actual NUL bytes in v1a. The corrected holdout is disjoint from the audited exploratory/primary identifiers and local session-sequence hashes, excludes the 40 prospective admin captures, and has not been executed.

## V4 preflight

The implementation and candidate hashes match the V4 freeze. Chrollo loaded successfully; offline Don indexed 25,397 documents; the frozen logistic model loaded; all three graphs built; Hisoka, verifier, and HITL constructed; and the frozen V4 test suite passed 48 tests. Commands were treated as inert strings and were never executed or replayed.

## Blocker

The reference protocol requires three fresh blinded annotations plus adjudication. The environment contains no authorized non-paid local reference model with downloadable local weights. Ollama lists only cloud model tags, and neither those models nor the Codex gateway was used. Because reference identity and prompt cannot be frozen under the stated cost boundary, raw three-arm execution would create outputs that cannot complete the preregistered scientific endpoint. Execution is therefore stopped before the first arm.

No raw execution freeze, blind reference freeze, or locked analysis artifact is created because those stages did not complete. The prospective V4 study remains blocked and all previous V2/V3/V4 freezes are preserved.

## Scientific boundary

This is a source-verification and preflight result, not a retrospective effectiveness result. The attack-only corpus cannot establish benign-administration classification or real attacker engagement. Published ATT&CK labels and severity fields were not used as ground truth. Request/response replay variants were not treated as live honeypot behavior.
