# Conditional Laya Policy — Results Status

## Status

**Study design is defined; empirical conditional-policy results are pending
independent labels and a paired run.**

## Policies under study

1. **LAYA_OFF** — no Laya inference, baseline behavior only.
2. **LAYA_ALWAYS** — Laya runs on every case where the optional assessment
   seam is enabled.
3. **LAYA_GATED** — Laya runs only under a predefined condition.

## Predefined gate (documented before test-set inspection)

For this study the provisional gate is:

- invoke Laya only when Chrollo confidence is below a fixed, pre-specified
  threshold **and** the optional Laya config is enabled.

The exact threshold must be chosen **before** inspecting final held-out
outcomes. In this session, that threshold has **not** been finalized for the
independent set, so the gated results are **provisional / not finalized**.

## Metrics required

For each policy:
- percentage of commands invoking Laya
- accuracy
- macro-F1
- precision / recall / balanced accuracy
- Laya correction rate
- Laya harm rate
- NO_SIGNAL rate
- mean / median / P95 latency
- end-to-end pipeline latency
- CPU RSS where observable
- model load time
- estimated per-session latency overhead

## Current empirical basis

This study cannot be finalized yet because:
- independent labels are not available
- the predefined gate threshold for the independent set is not finalized

The real Laya CPU pilot latency envelope already observed in this repo is the
only current empirical input to the cost side of the question:
- first-call-with-load: ~5–6.6s
- steady-state per-call: ~1.3–4.9s envelope across two runs
- this-run mean ~4.9s / p50 ~4.87s / p95 ~5.9s
- earlier ablation-run mean ~1.32s / p95 ~1.41s / first-call load ~6.64s

That cost profile is real; the decision value on independent cases is not yet
established.

## Research question

Does selective Laya assessment produce enough independent decision value to
justify its computational cost?

Answer: **not yet determinable from independent evidence.**
