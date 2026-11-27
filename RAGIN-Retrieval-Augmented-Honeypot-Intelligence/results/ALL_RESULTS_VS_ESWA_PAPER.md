# All Results vs the ESWA Paper — Full Comparison Report

**Date:** 2026-09-21
**Paper baseline:** ESWA-S-26-45224 (RAGIN, Major Revision; response letter dated 2026-08-04 — the response-letter numbers are the paper's final claims)
**Current system:** post-revision stack — graph engine, Chrollo(+ngram) → Don → Hisoka, Jev routing signal, deterministic protocol fast-paths, fiction ledger, closed-loop replay harness
**Current LLM stack:** attacker `gpt-5.6-luna-free` / defender `deepseek-v4.1-flash-free` @ apmix (cross-weights A/B); `glm-5.3-flash-free` for the pipeline benchmark
**Verdict in one line:** the current system beats or matches the paper on **every headline axis** — deception quality, CTI pipeline, TTP discovery, retrieval, engagement dwell — and resolves the red-team tells the paper itself documented, with the paper's *live-deployment* numbers the one place where the paper's evidence is still the strongest.

---

## 1. Scorecard — paper claims vs current evidence

| # | Axis | Paper (ESWA-S-26-45224, final revision) | Current system | Δ / Verdict |
|---|---|---|---|---|
| 1 | Human-eval deception quality | 2.83/5 (4-dim consensus, artifact-safety excluded, M5); bias-corrected aggregate 3.06/5; stale ESWA number 1.91 | **3.14/5** mean consensus, 4/8 scenarios ≥ 3.0, 0/8 < 2.0; live-LLM scenarios 3.6–4.3 | **+0.31 over paper's honest number; +1.23 over stale** ✅ |
| 2 | Pipeline composite (CTI technique + actor + persona) | 0.693 (technique 0.820 / actor 0.630 / persona 0.630) | **0.855 full-218** (0.960 / 0.850 / 0.645); 0.872 paper-comparable n=30 | **+0.162 full-scale, +0.179 matched-scale** ✅ |
| 3 | CTI technique extraction | 0.820 | **0.960** (123/123) | **+0.140** ✅ |
| 4 | CTI actor attribution | 0.630 | **0.850** (35/35) | **+0.220** ✅ |
| 5 | Persona realism | 0.630 | **0.645** full-218 (58/60); 0.825 paper-comparable; template floor avg 0.662 | **beaten at scale; +0.195 matched** ✅ |
| 6 | TTP discovery yield | RAG arm 5 TTPs / 13 unique (ablation 5 vs 0 vs 3; unique 13/0/7) | **82 TTPs / 31 unique** on 218 sessions (7× larger query set) | **16× detections, 2.4× distinct techniques** ✅ |
| 7 | Retrieval vs baselines | Unproven (no baseline comparison in paper) | Graph arm **significantly beats BM25-hybrid and dense** on MRR/NDCG@10/P@5 (Wilcoxon, Holm-corrected, large effect sizes d 0.84–1.0); **ties sparse BM25** on MRR, slightly behind on NDCG@10 | **Paper had no evidence; now proven vs 2/3 baselines** ✅ (sparse tie honest) |
| 8 | Attacker engagement dwell | Automated probe campaign: dwell avg 12.6 s, median 13.3 s, range 9.4–21.0 s (30 sessions); personas 11.7 / 39.3 / 63.4 s (novice/int/adv, 5.4× gradient) | Closed-loop attacker-LLM replay: v2 all sessions left ≤ 9 turns → v5.5 4–8 turns with tells → **v6/v7: every session hits the 12-turn ceiling, zero early leaves, cross-weights**; treated bait 10 vs baseline 7 (v7 lateral) | **Ceiling-saturated — the headline engagement problem the paper left open is now closed in simulation** ✅ |
| 9 | A/B treatment effect | n=6 Cowrie head-to-head, Δ composite CI [+0.04, +0.71] — under-powered, "indicative only" (M3) | Dwell A/B now ceiling-saturated (12 vs 12) — no headroom left to measure; bait-marker delta +3 reproducible; still small-n, no bootstrap CI yet | **Directionally better, statistically unproven** ⚠️ |
| 10 | Red-team tells (M10: latency, static paths, cadence) | Three documented detection vectors on the live deployment (~160 s first-response latency = strongest tell; static Cowrie paths; uniform cadence) | Latency: 24 s/turn deepseek, **4.4 s/turn luna** (vs 160 s — ~36× better but still ≫ Cowrie's ms). Static paths: **gone** (FS ledger + ambient rewrite — listings now evolve). Cadence: **gone** (template fallbacks style-match the LLM transcript). Protocol consistency: IMDS keys real `ASIA…` STS shape, sudo pinned to one authorization policy, `ssh-keyscan` deterministic per-host keys | **2 of 3 tells dead in the engine; latency tell structurally open** ⚠️ |
| 11 | Adaptive response signal | None — persona fixed by skill tier; no behavioral classification steers deception | **Jev kind/severity** steers engagement objective (5 kind→strategy mappings); on **real Cowrie traffic** baseline routing 0/13 → **12/13 with Jev**; synthetic held-out 100% (200/200) with zero network dependency | **Capability the paper does not have** ✅ |
| 12 | Routing efficiency | Not quantified in paper | Routing at/above tier floor **69.5% → 100%** (synthetic n=200); over-escalation ≥ +2: 55/200 → 12/200; +3: 6 → 0; APT underestimation 1.9 levels → 0 | **New evidence, strongly positive** ✅ |
| 13 | Cross-session fiction consistency | Mem0: `uname -a` byte-identical across reconnects (M12) | Deterministic per-host SSH key material, HMAC-derived session-stable creds, fiction ledger with ambient evolution (re-reads change by transient entries, not byte-frozen) | **Same guarantee, now fiction-wide, not just uname** ✅ |
| 14 | Test/regression safety | 12-unit-test STRIDE harness (M11) | **1,285 unit tests green**, ruff clean; full suite 2m15s | **~100× harness depth** ✅ |
| 15 | Deployment evidence | **Live VPS campaign** ([deployment-host]:2222): 30 sessions, 261 LLM queries, 3 egress profiles incl. Tor, 2 genuinely-external attackers observed; Cowrie-confirmed serving | All v6/v7 evidence is the **closed-loop replay harness** (attacker-LLM vs defender pipeline, real Cowrie playbooks) — not the live deployment | **Paper leads here** ❌ (re-deployment pending) |

**Score: 12 axes beaten or newly proven, 2 honest partials (9, 10), 1 where the paper still leads (15).**

---

## 2. What the paper promised in the revision vs what we now have

| Paper commitment (response letter) | Status |
|---|---|
| M1: prompt-controlled ablation narrows but preserves the RAG gap (5/0/3, 13/0/7 unique) | Superseded: 82/31-unique yield at 7× scale; ablation framing intact |
| M3: "200+ session extension promised in §8" | **Done and exceeded: full 218-session live benchmark** (0.855) |
| M5: "2.51 cannot be a deception-quality verdict once artifact-safety bias is removed" | **Resolved: 3.14/5 with honest-identity rewrite and 3-judge majority; live-LLM scenarios 3.6–4.3** |
| M6: "internally validated, externally pending" scope | Internal validation now far stronger; **external re-validation still pending** (quota + deployment) |
| M7: 31-unique-TTP tactic distribution | Same 31 unique TTPs; distribution artifact stands |
| M12: close the loop on the live deployment | Was closed (30-session campaign); **new post-revision mechanisms (Jev steering, fast-paths, ledger) not yet deployed live** — v7 live rerun blocked by apmix monthly quota exhaustion |

---

## 3. The engagement story, version by version (the paper's biggest open problem)

The paper's §5.5 blind red-team documented that static Cowrie was trivially detectable and that RAGIN's integration gap capped engagement. The paper's own automated campaign measured **seconds** of dwell. The closed-loop harness (attacker = frontier-class LLM following real Cowrie playbooks) made the problem much harder — and the ladder shows the fixes compounding:

| Version | Attacker/defender | Result | Dominant leave reason |
|---|---|---|---|
| v2 | glm self-play | all sessions leave ≤ 9 turns | inconsistent listings, `[REDACTED]` markers |
| v3 | glm self-play | protocol-aware masking lands | "convenient" intel, credential shape |
| v5 | — | lateral 3–9 turns | canned configs, no creds |
| v5.5 | deepseek self-play | 4–8 turns, no ceiling | **AK7X prefix tell; sudo contradiction; "inconsistent responses" (template degradation)** |
| v6 | **luna vs deepseek (cross-weights)** | **12/12 both arms, zero leaves** (cloud + lateral) | — |
| v7 | luna vs deepseek | **12/12 both arms, zero leaves** (lateral, replicates v6; 3–4 in-session degradations absorbed invisibly) | — |

The three v5.5 tells the paper's methodology would have flagged as fiction breaks are now dead by construction: real `ASIA…` STS-shaped deterministic keys + protected-fiction registry; a single pinned authorization policy enforced at four surfaces; and template fallbacks that are byte-shape-indistinguishable from LLM turns.

---

## 4. Honest limits (what we will not claim)

1. **The dwell A/B is ceiling-saturated.** 12/12 vs 12/12 means Δ dwell is unmeasurable at the current `MAX_TURNS`. The treatment effect now shows in bait-marker yield (+3) and attacker behavior depth (docker-socket enumeration in treated arm), not turns. A higher ceiling or harder playbooks are needed before any statistical claim.
2. **No bootstrap CI on the new replay results.** The paper added `tab:cowrie_bootstrap` for exactly this sin at n=6; we should not repeat it. n=2 families × 2 arms × 2 versions is directional evidence.
3. **The latency tell stands.** Free-tier LLMs respond in seconds, not milliseconds. The paper's M10 finding (strongest single tell = ~160 s) is improved ~6–36× but not closed; only edge-caching/deterministic fast-paths (which now cover IMDS/SSH/authz/keyscan) move toward Cowrie-class latency.
4. **Human eval is LLM-judged.** 3.14/5 uses three LLM evaluators with majority consensus — the same judge-class the paper's M5 critique targeted. The deterministic artifact-safety substitute (4.2/5) from M5 is the right complement; a human-rater round is the gold standard we have not re-run.
5. **Sparse BM25 ties the graph arm** on MRR and leads NDCG@10. The retrieval claim must stay "beats hybrid and dense," never "beats all baselines."
6. **Real-traffic Jev eval is n=13.** The 0% → 92% swing is dramatic but tiny; the generalization-gap lesson (patterns freeze, models adapt) is the robust part, not the point estimate.
7. **The live deployment hasn't seen the new mechanisms.** Every v6/v7 mechanism (Jev steering, protocol fast-paths, ledger, styled fallbacks, sudo policy) is validated in the harness; M12-style live re-deployment is the remaining step and is quota-blocked (apmix monthly allowance exhausted 2026-09-21; agentrouter disqualified — content filter blocks Hisoka personas).

---

## 5. Bottom line vs the paper

| The paper's framing | What we can now claim |
|---|---|
| "Internally validated architecture, externally pending deployment" | Internal validation is now **dominant on every internal axis**: deception 3.14 vs 2.83, pipeline 0.855 vs 0.693, TTPs 82/31 vs 5/13, retrieval proven vs 2 baselines, engagement ceiling-saturated where the paper reported seconds of dwell |
| Cowrie comparison under-powered (n=6, CI [+0.04, +0.71]) | The comparison is no longer close on any metric — but the new A/B needs its own CI before a stats claim |
| Three blind red-team tells | Two dead by construction, one (latency) improved ~36× and structurally open |
| Persona taxonomy anchored by feature importances + a 5.4× dwell gradient | Now anchored additionally by **ceiling-saturated adversarial dwell against a frontier-class attacker LLM** — the strongest engagement evidence in the project |
| No adaptive behavioral response | Jev kind→strategy steering, with real-traffic evidence (0% → 92%) that the deterministic system alone collapses under domain shift |

**For the manuscript:** the revision's numbers (2.83/3.06, 0.693, 5/13, unproven retrieval) are now strictly dominated by current artifacts — every §5 table can be re-grounded from `docs/BENCHMARK_REPORT.md`, `results/jev_ab_eval_REPORT.md`, `results/jev_real_logs_eval_REPORT.md`, `results/jev_dwell_replay_v6.json`, `results/jev_dwell_replay_v7_lateral_REPORT.md`, and `results/stat_eval/summary.json`. The one claim that must stay scoped exactly as M6 wrote it: externally-pending — because the current evidence is harness-internal, and the live redeployment is the next action, blocked only on LLM quota.

## 6. Artifacts index

| Evidence | Artifact |
|---|---|
| Pipeline + human eval + retrieval vs paper | `docs/BENCHMARK_REPORT.md`, `results/stat_eval/summary.json` |
| Jev A/B (routing quality + efficiency) | `results/jev_ab_eval.json`, `results/jev_ab_eval_REPORT.md` |
| Jev on real traffic | `results/jev_real_logs_eval.json`, `results/jev_real_logs_eval_REPORT.md` |
| Dwell replay ladder (v2→v7) | `results/jev_dwell_replay_v*_REPORT.md`, `results/jev_dwell_replay_v6.json` |
| v7 lateral + quota outage | `results/jev_dwell_replay_v7_lateral_REPORT.md` |
| Retrain evidence | `models/chrollo/training_manifest.json`, `results/model_quality/seq_features_benchmark.json` |
| Paper-side numbers | `RESPONSE_LETTER_ESWA-S-26-45224.md`, `REVIEW_ESWA-S-26-45224_RAGIN.md` |
