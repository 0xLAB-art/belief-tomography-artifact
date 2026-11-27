# Gap Closure Plan — 2026-10-28 → S&P 2027 submission

**Scope:** close the four reviewer-facing gaps named on 2026-10-28, without touching the
framing (Paper.1 "Intelligence Ladder") and without reopening Laya.
**Deadline chain:** abstract registration Nov 10 · full paper Nov 17 AoE.
**Budget:** ~3.5–4 working days of engineering/writing (mine) + ~30–45 min (yours: AWS auth,
one field-config approval, one provider confirmation). Everything else is passive waiting.

---

## 0. State check (measured today, not recalled)

| Item | Reality on disk / on host |
|---|---|
| Field endpoint | EDGE `REDACTED_FLEET_HOST:2222` live since 2026-10-25; CORE serves via mTLS |
| Real external traffic | 996 cowrie events / 97 session.connect (Oct 8–9, 11, 25–26); **2 hashed sources**; 368 interactive events (305 `command.input`, 60 emulated logins); **0 file/download events** |
| Field export | `evidence/field/` holds only `exit_evidence_2026-10-26.md`; `run/field_export/` empty; **no cron ever existed** (F3 confirmed) |
| Field honeytoken census | exit-evidence says "0 deployed" — but that probe looked for cowrie's native `honeytokens` feature, while the field bait (`.dbpass`, `.env` AWS keys) is served by the RAGIN fiction layer. **Census is mis-scoped; contradictory with §5.6's live-batch numbers.** |
| AWS access | `aws sts get-caller-identity` → **session expired** (blocks all host-side work) |
| A/B artifact | `results/field_attack/arm_comparison.json`, 15/15 sessions, dwell 143.0 vs 105.0 s, latency 16.86 vs 8.17 s/turn, sensitive reads A 0/0/6 vs C 44/22/22 — **no CI, no test, no power statement** |
| AI jury v1 | `results/laya_research/ai_jury_v1/`, 3 jurors × 120 cases, packet sha `8a99ead2…`, Fleiss κ 0.811 (9-class), binary 0.967–0.975 — **all three are GPT-family checkpoints**, and **none of it is in the paper yet** |
| JEV | G4 0.714 / G6 0.833 / G7 0.563 fail + I2 0.583, i.e. three-instance negative result — **presentation problem only** |
| Build | `sp2027.pdf` 20 pp; §5 has 8 subsections; page budget still needs a trim pass |

---

## Status — updated 2026-10-28 (evening)

| Gap | State | Evidence |
|---|---|---|
| 1 — field | **plumbing done, collection running** | census artifact `evidence/field/census_2026-10-28.json`; `/etc/cron.d/ragin-field-census` on EDGE verified; exit-evidence §G added; honeytoken-census contradiction corrected |
| 2 — A/B stats | **done** | `results/field_attack/arm_stats_bootstrap_v1.json` + `docs/ARM_AB_PREREGISTRATION_2026-10-28.md` + 8 tests; §5.6 rewritten |
| 3 — AI-judged | **approach changed** (no OpenRouter credits available) | see Gap 3: deterministic oracle + protocol sensitivity, cross-family only if a second provider appears |
| 4 — JEV framing | not started | — |

**Update 2026-10-28 (late): v2 study is running.** The v1 null was a ceiling artifact, and the
ceiling was worse than documented: cowrie closes an interactive session at
`[honeypot] interactive_timeout` = **300 s**, so the 14-turn cap and the five-minute transport
limit stacked. v2 raises the timeout to 3600 s (local arms only), caps turns at 30, uses
gpt-6-astra at reasoning effort=low (v1's apmiх model is retired), keeps A/C interleaved per
persona run, and pre-registers `turns survived` (KM + log-rank) plus `bait capture` as the two
confirmatory endpoints. 20 sessions per arm, 4 workers; artifacts land in
`sessions_v2_arm{A,C}.jsonl` and `arm_v2_stats.json`. The v1 artifact is not pooled in.

**Headline from Gap 2, which changes the paper's story:** no confirmatory endpoint
survives the pre-registered Holm correction at 15 sessions/arm. Dwell medians are
110.0 s vs 107.3 s (the −37.9 s mean gap is three long sessions in the stock arm);
time to first response is 16.9 s vs 8.2 s (unadjusted p=0.04, adjusted p=0.12);
bait-targeting intent does not differ (4/15 vs 6/15, Fisher p=0.70). The paper now
reports a bounded null plus a 60 s detectable-effect floor instead of a contrast.

---

## Gap 1 — Dwell comes from the closed-loop harness, not the field

**Honest target (this is the part that must not be oversold).** Real external traffic on a
public SSH honeypot is scanner-grade: handshake + emulated shell, no depth. 19 more days of it
will **not** produce attacker dwell numbers. So "close the gap" means four concrete things,
none of which is "harness dwell becomes field dwell":

1. **Make field collection actually run** — the exit-evidence finding is that the §6 daily
   export was never scheduled and the runbook command is invalid. Fix the runbook, install a
   cron/systemd timer on CORE, prove it fires once, and land the first real export in
   `evidence/field/` (hashed IPs only, raw IPs stay on host — FIELD_ETHICS §3).
2. **Reconcile the honeytoken census** — the paper cannot simultaneously say "0 honeytokens
   deployed in the field" and "30 AWS / 67 .dbpass / 35 .env honeytoken reads" for the live
   batch. Correct `exit_evidence_2026-10-26.md` §D to say what was and was not probed
   (cowrie-native vs RAGIN fiction bait), and say the same thing in §5.6.
3. **Collect passively until Nov 16** with two snapshots (Nov 5, Nov 16): per-day event and
   session counts, unique hashed sources, command-class census, and an explicit
   "scanner-grade / no file retrieval" statement.
4. **Reframe the claim in the paper** — §5.6 keeps dwell as *closed-loop harness* evidence and
   adds a field-observation paragraph with its own label: *real external interaction exists,
   the deception plane engaged (LLM refusals appear in the command log), depth is
   scanner-limited*. That is a boundary statement, and it is defensible; anything stronger
   gets killed in rebuttal.

**Acceptance:** export runs unattended and has produced ≥1 day of real sessions in
`evidence/field/`; census contradiction gone from both the doc and §5.6; field paragraph
carries the honest label and per-day numbers; §5.6 does not claim field dwell.
**Effort:** ~1 day engineering + passive collection. **Blocks on:** your `aws login`.

---

## Gap 2 — A/B treatment effect is small-n with no CI

This is the cheapest real win: the per-session data already exists (15 vs 15 with per-turn
logs), so no new runs are needed to make it statistically legible.

1. **Write the decision rule before running** (pre-registration discipline, same as the frozen
   gates): metric set = dwell_s, turn latency, output chars, sensitive-read hits, turns;
   interval = percentile bootstrap 10k, fixed seed, stratified by persona pair; tests =
   Mann–Whitney U (continuous) + Fisher exact (session-level binary: did this session touch
   any bait file). Add a censoring note: dwell is bounded by the 12-turn cap, so the mean is a
   truncated statistic and must be reported as such.
2. **Emit `results/field_attack/arm_stats_bootstrap_v1.json`** with point estimates, CIs,
   p-values, effect sizes, per-persona breakdown, and the caveats already in
   `arm_comparison.json` (shared host IP, differing surfaces, local self-play).
3. **Report whatever it says.** Expectation: dwell and latency CIs will likely straddle zero at
   n=15, while bait consumption (44/22/22 vs 0/0/6) is the signal that survives. Then the
   paper says "no measurable dwell difference at this n; a clear difference in whether the
   session reached planted credentials, Fisher p=…" — that is *stronger* than today's
   "directionally better", because it is falsifiable.
4. Optional, only if the CIs are embarrassing and quota is free: extend to n=25/arm with the
   same driver and re-run the same pre-registered analysis. Not scheduled by default.
5. Replace the §5.6 numbers with the CI-bearing versions; add a unit test that pins the
   artifact schema (repo convention: numbers never move without their artifact re-check).

**Acceptance:** artifact + tests + one paper table where every number has an interval.
**Effort:** ~0.5 day. **Blocks on:** nothing.

---

## Gap 3 — Everything is AI-judged

The jury v1 result is genuinely good (κ 0.811, binary ≥0.97), but as it stands it is **three
checkpoints of one model family**, which a reviewer will read as one rater with three voices.
Closing it has three parts:

**Constraint (2026-10-28):** the available key is agentrouter only, and its group exposes just
three GPT-family checkpoints. Cross-**family** jurisdiction therefore cannot be bought. The
honest substitutes, in order of value:

1. **A non-LLM reference.** A deterministic rule-based labeler over the same 120 cases
   (regex/keyword classifier derived from the frozen operational taxonomy, no model calls).
   Jury-vs-oracle agreement is evidence of a different kind than model-vs-model agreement, and
   it costs nothing. This is now the primary addition, not a side check.
2. **Protocol sensitivity, not model diversity.** Re-label the same packet under two additional
   framings (e.g. evidence-only vs. transcript-with-commands, and a terse-definition variant)
   with the same three checkpoints; report agreement within framing and across framings. This
   measures whether the labels are an artifact of one prompt contract — a question reviewers
   actually ask — and it is labelled as protocol sensitivity, never as model diversity.
3. **Paper surface + disclosure.** New §5.x subsection: protocol (verbatim taxonomy), packet
   provenance (sha-pinned), panel named **as three checkpoints of one family**, κ values,
   protocol-sensitivity split, oracle agreement, and one sentence stating it is an
   **AI-workload behavioral eval, not a human study**; the human rater protocol moves to the
   appendix as a pre-registered future-work item (packets r1–r3 stay untouched).
4. **Only if a second provider materialises** (a free-tier key from another vendor, or a
   local open-weights model on the 8 GB GPU), add one cross-family juror and report the split.
   The 8 GB card rules out a strong 70B-class judge; a 7B-class local juror is a fallback, not
   a headline.

**Acceptance:** `ai_jury_v2` artifact (oracle + two extra framings), agreement recomputed, §5.x
with the disclosure sentence intact, claims→evidence rows, appendix protocol.
**Effort:** ~1 day (the two extra framings are 240 calls; the oracle is local).

---

## Gap 4 — JEV negative result must read as a finding, not a failure

Zero new experiments; this is framing plus one artifact citation.

1. In §5.5, lead with the claim ("a learned gate did not clear the contract at any threshold we
   tried") and treat G4/G6/G7 + I2 as the measurement, not the verdict on the method.
2. Add one boxed **design rule** — *price the gate against the deterministic floor; if the
   learned rung cannot clear all gates, the floor is the deployable configuration* — and call
   back to it from §1 and §6 so the negative result becomes contribution #3, not a footnote.
3. Add the claims→evidence rows (JEV, Laya, fold-down) in the same wording used in the paper,
   so the map and the text can be diffed.

**Acceptance:** §5.5 opening reframed, box + two call-backs, claims rows; build clean.
**Effort:** ~0.5 day. **Blocks on:** nothing.

---

## Schedule

| Date | Work | Gate |
|---|---|---|
| Oct 28 (today) | Gap 2 pre-registration + script + artifact; ask for AWS login | CI artifact exists |
| Oct 29 | Gap 2 paper integration + tests; Gap 4 reframe draft | suite green |
| Oct 30–31 | Gap 3 jury v2 (2 OpenRouter families) + deterministic oracle | κ + cross-family split |
| Nov 1 | Gap 1: export runbook fix, cron, first real export, census reconciliation | `evidence/field/` non-empty |
| Nov 2–3 | Gap 3 §5.x subsection + appendix; Gap 1 §5.6 field paragraph | build clean, 0 undefined refs |
| Nov 4–6 | buffer; trim pass (20 pp → budget); claims map line-by-line read | page budget met |
| Nov 7–9 | §1 / §6 / §7 + figures (existing plan) | — |
| Nov 8 | abstract frozen | — |
| Nov 10 | **abstract registered** | — |
| Nov 11–16 | assembly, final field snapshot Nov 16, final build | — |
| Nov 17 | submit (AoE) | — |

---

## Explicitly out of scope

- **Laya retuning** — 12 failed tunings + a failed learned gate is the evidence for the floor.
- **Market-number comparisons** — published honeypot numbers are not comparable; the paper keeps
  the qualitative capability table and the in-house baseline arms.
- **Recruiting human raters now** — protocol + packets are pre-registered; no 13-day path to a
  credible human study, and a rushed one is worse than a labeled AI-workload eval.

## Risks

| Risk | Mitigation |
|---|---|
| Field traffic stays scanner-grade; no depth by Nov 16 | Claim stays harness-labeled; field paragraph is a boundary, not a result |
| Bootstrap CIs straddle zero at n=15 | Pre-registered decision rule: report it as a null at this n, keep bait-consumption as the signal |
| AWS session keeps expiring | All host work batched into one session on Nov 1; runbook + cron so later snapshots need no interactive work |
| OpenRouter rate limits / model churn on free tiers | Fixed model ids recorded in the manifest, retries + resume cache (same pattern as jury v1) |
| Page budget already at 20 pp | Every addition paired with a trim in §2/§5.1; trim pass scheduled Nov 4–6 |
| Adding text that outruns the evidence | Paper rule stands: no row in the claims→evidence map, no sentence in the paper |

## v2 collection: transport defects found and fixed (2026-10-28 late)

Three defects kept the paired 30-turn workload from producing data; each was
diagnosed from the provider's own responses rather than guessed:

| Defect | Evidence | Fix |
|---|---|---|
| Fresh TLS handshake per turn | `_ssl.c:983 handshake timed out` under 3 concurrent workers | one kept-alive `HTTPSConnection` per worker (`_post_json`) with a single reconnect |
| Reasoning burned the output budget | `status: incomplete`, `reason: max_output_tokens`, output items were reasoning-only, no message | 3000 tokens on attempt 1, 7000 on attempt 2 |
| Empty 200s from the shared per-model budget | `429 … 10000000 tokens per 60 seconds … retry after N` | 429/5xx honoured with the provider-stated wait, four attempts |

With those fixed, arm C sessions reach the 30-turn cap with **zero scripted
fallbacks** (`fallbacks` is recorded per session and surfaced as
`turn_fallbacks` / `sessions_model_only` in the stats artifact). Duplicate
persona/run records from a resumed worker are de-duplicated in `load()` by
keeping the most complete record per pair.

`scripts/watch_v2_complete.sh` runs detached: when both arms hold 20 pairs it
writes `results/field_attack/arm_v2_stats.json` once, so the analysis lands even
if the collecting session ends.

### Amendment 1 — filesystem-scope line (v2.1-scoped)

A model-issued `find /` runs synchronously over cowrie's emulated tree and pins
the container at 100% CPU (`docker stats` 100.9%, new handshakes refused with
`No existing session`). The attacker prompt therefore gained one sentence,
identical for both arms: *stay within /home, /etc, /opt, /srv and /var/www; do
not scan the entire filesystem*. A driver-side guard rewrites a bare
`find / <expr>` to `find / -maxdepth 4 <expr>` if the model ignores it.
Records carry `prompt_version` (`v2.0` before, `v2.1-scoped` after), so the
boundary is auditable and any sensitivity check can split on it.
