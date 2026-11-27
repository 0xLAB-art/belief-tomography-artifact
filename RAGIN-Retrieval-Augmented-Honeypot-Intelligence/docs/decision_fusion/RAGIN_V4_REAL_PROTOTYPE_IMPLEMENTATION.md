# RAGIN V4 Real Prototype Implementation

## Status

The V4 decision subsystem is implemented behind three arms: `RAGIN_BASELINE`, `RAGIN_V4_DETERMINISTIC`, and `RAGIN_V4_LOGISTIC`. The authoritative default remains baseline. V4 is opt-in, and an enabled V4 configuration without an explicit selector resolves to the deterministic selector.

Laya is preserved as historical negative-ablation evidence and is not used by the active V4 decision path.

## Runtime boundary

Don emits `ragin.don.evidence_bundle.v4` with provenance-tracked retrieval fields and bounded document content. The immutable bundle is evaluated by the deterministic Evidence Quality Gate. Only `VALID_EVIDENCE` reaches a policy engine. Every other gate state produces baseline.

The policy output is `ragin.decision_fusion_v4.policy_decision.v1`. It contains an allow-listed strategy, supporting evidence references, gate and bundle digests, engine/version/hash metadata, latency, and fallback information. Hisoka receives only the bounded strategy block. HITL, deterministic verification, accepted-only state commit, and serving remain outside policy authority.

## Engines

The deterministic engine uses the frozen V4 rule table and records its rule-table hash. The logistic engine loads the frozen joblib artifact, verifies its model hash and feature-map ordering, and uses structured features only. It does not retrain or access case IDs, strata, or synthetic oracle fields.

## Verification performed

The isolated contract suite covers valid and invalid gate states, malformed bundles, policy output validation, exception fallback, arm isolation, generator delivery, verification, retry/fallback behavior, and baseline non-invocation. A new synthetic integration smoke covers Don export, both V4 engines, invalid-evidence fallback, generator delivery, and deterministic verification. No prior holdout or real case was executed.

The future real evaluation protocol is defined separately and requires a new blinded holdout, allowed-strategy-set reference labels, paired comparisons, and separate gate, policy, and workflow metrics.
