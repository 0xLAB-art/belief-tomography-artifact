# Pre-Registration v3 — Deception-Plane Yield under a Family-Disjoint Attacker Brain

**Frozen:** 2026-10-30 (before any v3 session runs)
**Design lineage:** v1 (2026-10-28, sha 65d96d18…) → v2 (2026-10-28, sha 1b714bb6…) → v3 (this document)
**Motivation:** the v2 exploratory census found planted artifacts in 11/20 RAGIN-arm transcripts vs 0/20 stock (Fisher p=0.00015, specific planted shapes 6/20), labeled exploratory and named "the candidate endpoint a future contrast should promote." The v2 attacker brain (gpt-6-astra, agentrouter.org) shared a provider family with the serving generator — the self-play circularity caveat. This v3 run addresses both: the promoted endpoint becomes primary, and the attacker brain moves to a family disjoint from the serving provider.

## Amendment 2 (2026-10-31, before unblinding — primary analysis not yet run)

**Brain replacement — WITHDRAWN (2026-10-31):** the gemini-3.8-flash
switch via apinex.bond was attempted but produced no recorded sessions
(rate-limit storms and a transport bug crashed every launch before a
session completed). The recorded dataset is the ORIGINAL Amendment 1
brain: `claude-sonnet-5-5` served by `api.beatapi.io` (Anthropic family,
disjoint from the OpenAI serving generator), n=10/arm on disk. The two
evasion_probe #1 sessions first recorded on the claude brain were moved
to supplementary during the failed switch and re-recorded within the
final 10/arm set. No analysis was run between Amendment 2's writing and
this withdrawal; the unblinding order is preserved. Endpoint, personas, caps,
arms, n, endpoints (primary/secondary), decision rule, and analysis script
are unchanged. Rationale: the promoted primary endpoint requires a
family-disjoint brain; apinex serves one with ~1.5 s latency and no
observed rate limit (vs beatapi's 1 request/minute and exhausted credit).
No sessions on the new brain ran before this amendment.

## Design

- **Arms:** A = stock cowrie (127.0.0.1:2221), C = full RAGIN loop (127.0.0.1:2223). Same host, same caveats as v2 (local self-play, shared endpoint, surfaces differ by design).
- **Attacker brain (pre-registered; Amendment 1, 2026-10-30, before any session ran):** `claude-sonnet-5-5` served by `api.beatapi.io` (Anthropic family) — **disjoint** from the serving generator (`gpt-5.6-sol`, agentrouter.org, OpenAI family) and from every prior attacker brain in this project. Originally scoped as claude-opus-5-5 on agentrouter.org; that channel is unavailable on both keys (verified 2026-10-30), and beatapi serves claude-sonnet-5-5 over chat completions at a 4 s probe latency under a 1-successful-request-per-minute shared key limit (the run is therefore serialized through scripts/beatapi_gate.py). No pilot sessions were run on this brain before this document was frozen.
- **n = 10 per arm** (2 runs × 5 personas: novice, recon, credential_hunter, apt_patient, evasion_probe), interleaved A/C by (persona, run_id) with a fixed seeded order (SEED=20261030). Caps persona-scaled as v2 (12/18/25/30/30); session budget 35 min; interactive_timeout 3600 s (both arms, as v2).
- **No optional stopping. No endpoint switching. No re-runs on nulls.** Deviations logged in the analysis artifact.

## Endpoints

- **PRIMARY (promoted from v2 exploratory, powered):** planted-artifact yield — a session's returned transcript contains at least one *specific planted shape*: `AKIA[0-9A-Z]{16}`, `AWS_SECRET_ACCESS_KEY=…`, `DB_(PASSWORD|PASSWD|PASS)=…`, or a planted `VAR=value` assignment, per the frozen v2 coding regexes (sha256 3945d721…). Analysis: two-sided Fisher exact (C vs A) + risk difference with 10,000-resample stratified percentile bootstrap.
- **Power (declared before the run):** v2 observed yield 0.55 with control structurally 0; at n=10/arm the design has ≥97% power (α=0.05 two-sided) to detect a 0.55 vs 0 separation at ≥3/10 successes.
- **SECONDARY:** (a) bait_read count; (b) bait capture (read → reuse attempt); (c) turns survived, KM/log-rank, horizon 30; (d) honeypot-detection verdicts — including transcript-level tell analysis of any `VERDICT: honeypot` output, reported regardless of direction.
- **EXPLORATORY (labeled, non-confirmatory):** per-shape yield breakdown; provider content-filter blocking rate under the beatapi transport.

## Decision rule

- Primary Fisher p < 0.05 two-sided with the v2 direction (C > A): the deception-plane yield result is **confirmatory** under a family-disjoint attacker.
- Primary null: published as a null; no v4 on this endpoint.
- Any `VERDICT: honeypot` output in arm C is analyzed and reported symmetrically — as a deception-failure datum, not an aside.

## Artifacts

- Sessions: `results/field_attack_v3/sessions_v3_arm{A,C}.jsonl`
- Analysis: `results/field_attack_v3/arm_v3_stats.json` (schema `ragin.field_attack.arm_stats_v3.v1`)
- Analysis script: `scripts/field_attack_stats_v3.py` (v2 script + promoted primary; frozen before unblinding)
