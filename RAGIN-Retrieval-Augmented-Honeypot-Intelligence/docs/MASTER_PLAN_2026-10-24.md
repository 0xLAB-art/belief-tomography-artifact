# RAGIN Master Plan — 2026-10-24 → Project Finish

**Deadline chain:** S&P 2027 abstract **Nov 10** (17 days) · full paper **Nov 17 AoE** ·
TDSC fallback reuses everything afterward.
**Start state:** see `PROJECT_STATE_2026-10-24.md` — suite 2088/0, git clean, JEV+apmix live,
VPS idle-but-free, research-realism gaps open.

---

## Phase 0 — Adversarial hardening ✅ DONE (2026-10-24)

Red-team wave 1 (serving-layer live pentest + verification-gate payload battery) found 11 real
vulnerabilities; all fixed with 96 regression tests; suite 2088/0; redteam 47/47 held.
Details: `PROJECT_STATE_2026-10-24.md` §4. Pending: **wave 2** (data-pipeline injection,
LLM/JEV chain abuse, crypto/config) — schedule inside Phase 2 windows when model concurrency
allows; findings feed the paper's hardening section.

## Phase 1 — Field deployment go/no-go (Oct 25–27) — DECISION REQUIRED

Both VPS are idle-but-free ($0 credits), so this is a research decision, not a cost one.
- [x] Renew mTLS certs (EDGE + CORE) — executed 2026-10-25 per `FIELD_REVIVAL_2026-10-25.md`:
      fresh CA (10y) + 90d leafs, CN/SAN per role, 3072-bit RSA; expiry ~2027-01-23, rotation
      reminder early January. (Plan line was stale — renewal happened in the revival.)
- [x] Ethics/hardening review pass (`FIELD_ETHICS.md`, `SECURITY_HARDENING.md`, the
      APPROVAL_REQUIRED matrix items) — recorded 2026-10-26 in
      `FIELD_ETHICS_REVIEW_2026-10-26.md`: external-observable hard gates PASS (admin SSH
      closed, :2222 sole public listener, CORE 8443 filtered); findings F1–F4 (§3 hashing
      attributed to the wrong mechanism; bridge persists raw src_ip alongside hashed; §6
      cron command invalid as written; matrix rows stale vs revival); APPROVAL_REQUIRED
      inventory surfaced, none executed. **PENDING SSM** (AWS session expired): egress
      probe (`iptables -L DOCKER-USER` + internal curl must fail), endpoint `.env.field`
      secret scan, `ss -tlnp` inside hosts.
- [x] Open EDGE :2222 → enable apmix path on CORE → external end-to-end probe — executed
      2026-10-25 (revival evidence: external SSH handshake → cowrie host key + password
      prompt; 0 → 27 cowrie events; boot log provider=apmix auth=configured; intel E2E
      `E2E_RESULT: PASS` 2026-10-26)
- [ ] Collect 12–14 days of real attacker sessions; export via `run/field_export/`
      — **PENDING SSM**: `evidence/field/` + `run/field_export/` empty; collector must run
      on the endpoint (and §6 step-4 command is invalid — see review F3; fix before cron)
- **If no-go:** leave instances running ($0) and rely on blind packets + a bounded
  self-play field-sim instead; state the limitation honestly in the paper.
- **Exit evidence:** `evidence/field/` populated with real sessions; per-day session counts;
  at least one honeytoken interaction or an honest zero-interaction census.

## Phase 2 — JEV gate study: instance #3 of the thesis (Oct 26–28) — ran early 2026-10-24 (Step 15 `45b9a9f8`; artifact re-checked 2026-10-26)

- [x] Freeze the Laya v12 battery as-is (60 eval + 24 injection cases, sha256 protocol file)
  — re-checked 2026-10-26: all three recorded input hashes MATCH the files on disk (ev freeze
  `dd6c6dbc…`, inj freeze `166117d3…`, contract `c3fea3c9…`); protocol line reads
  "frozen Laya v12 battery reused verbatim (no post-hoc thresholds)".
- [x] Run JEV arm vs deterministic control through G1–G8 + I2 (pacing for 1 req/min ≈ 1.5 h wall)
  — **G1–G8: done** (60/60 eval calls ok; G1–G3/G5/G8 PASS; G4 required-abstain-recall 0.7143
  < 0.9, G6 state-contract alignment 0.8333 < 0.85, G7 strategy-compat 0.5625 < 0.8 FAIL),
  `final_decision_v1.json` failed list consistent with `results_v1.json` gates.
  **I2: NOT GRADED by the runner** — re-check found no I2 gate anywhere in the JEV artifact:
  `I2` (`injected_target_adoption_rate <= 0.1`, v4 protocol freeze line 142) is absent from the
  gates dict, `inj_metrics` carries no adoption-rate metric (the 24/24 injection cases were
  scored with the G1–G8 metric family instead), and JEV ran the v3-lineage contract.
  **I2 re-graded 2026-10-26 (decision resolved — no protocol deviation needed):**
  `scripts/jev_i2_addendum_v1.py` mirrors the frozen `compute_inj_metrics` loop (raw pre-rule
  choices vs `conflicting_target` on `conflicting_dimensions`), inputs sha256-pinned (inj freeze
  `166117d3…` verified equal to the JEV-run-recorded hash) →
  `results/jev_decision_v1/i2_addendum_v1.json`: adopted **7/12 → rate 0.5833 > 0.1 → I2 FAIL**;
  classification unchanged (`JEV_FAIL_GATES_G4_G6_G7` — G4/G6/G7 failed independently).
  Pinned by `tests/unit/test_jev_i2_addendum.py` (4 tests). §5.5 reports I2 alongside G1–G8.
  Per-call pacing is not visible in `jev_decision_v1_run.log` (no timestamps).
- [x] Emit `final_decision.json` in the same schema (TUNING_FAIL lineage)
  — `results/jev_decision_v1/final_decision_v1.json`: schema
  `ragin.jev_v12_gate_study.final_decision.v1`, status COMPLETE, classification
  `JEV_FAIL_GATES_G4_G6_G7`, candidate `jev-1.14-free (typed-questions arm)`, decided
  2026-10-24T19:53:20Z, control reference = deterministic floor + Laya v12 numbers in
  `results/laya_decision_v4/`.
- Either outcome is a paper finding: JEV fails gates → third confirmation of "post-verification
  intelligence buys adaptation, not safety"; JEV passes → "the failure was the integration
  contract, not learned decision models" — a deployable design rule.
  **Observed outcome (re-checked): JEV fails G4/G6/G7 → first branch.**
- [x] Prune Laya checkpoints on the GPU mount (keep v12_final + reports; free ~7.9 GB)
      — done 2026-10-26: 10 dev dirs (v8/v9/v10/v11/v12_dev × rlcd/softce, 808 MB each) removed
      from `/mnt/01DCDC2BF6665BC0/ragin_laya_gpu/checkpoints`; mount 9.5 GB → 1.6 GB
      (**freed 7.9 GB**); only `laya_v12_balanced_allrows_gpu_redesign_v1_final_v1` kept;
      reports untouched in `results/laya_decision_v4/`.

## Phase 3 — Realism: AI adversarial workload (pivoted 2026-10-24)

**Decision (researcher):** human raters dropped — blind packets stay as a prepared optional
artifact. Realism is measured by (a) an AI adversarial workload and (b) background traffic.

- [x] `scripts/field_attack_driver.py`: 5 attacker personas (novice / recon / credential-hunter
      / APT-patient / evasion-probe) driven by an apmix LLM over SSH against the live endpoint
- [x] Pilot validated end-to-end (after fixing bridge 401: API_KEY quoting bug + cowrie key
      trailing newline) — verified serving with sha256 provenance confirmed
- [x] Full batch: 15 sessions → `results/field_attack/sessions.jsonl`
- [x] Batch-1 signal: credential-hunter consumed planted honeytokens (.env AWS keys, .dbpass)
      — artifact-access and credential-interaction metrics alive for the first time
- [x] Repeat the workload per arm (cowrie-only vs RAGIN) for the comparison section
      — done 2026-10-26 as **local self-play** (researcher choice; live route blocked by
      expired AWS session): driver parameterized (`RAGIN_ATTACK_HOST/PORT/OUT`, defaults
      = live endpoint), never-deployed compose override, watchdog+retry rode cowrie's
      single-threaded-reactor wedges. **15/15 sessions per arm, 0 errors** →
      `results/field_attack/arm_comparison.json` (script + 4 tests):
      A cowrie-only 186 turns / dwell mean 143.0 s / 16.9 s per turn;
      C RAGIN 185 turns / dwell 105.0 s / 8.2 s per turn; sensitive-read hits on C
      `.dbpass` 44, AWS-key 22, `.env` 22 vs A 0/0/6 — the RAGIN arm's planted credential
      honeytokens got consumed (batch-1 finding reproduced on a second surface).
      Caveats emitted in the artifact: shared host IP (endpoint confound vs the
      never-co-locate design) + surfaces differ by design; numbers labeled local self-play,
      not field traffic. the LLM-judge 3.86 stays as a secondary, honestly-labeled signal.

## Phase 4 — Wave-2 hardening + ops fixes (Nov 1–5, interleaved with writing)

- [x] Wave-2 attacks (pipeline injection, LLM/JEV chain, crypto/config) → fix HIGHs only
      — pipeline + LLM/JEV chain: 2026-10-25 `eea364d3` (14/16 findings, 42 regressions in
      `tests/unit/test_wave2_hardening.py`, suite 2130/0). crypto/config audit 2026-10-26:
      HIGH fixed — `audit_integrity` signed/verified rows with the git-tracked default key
      `test-host-audit-key-v1` (forgeable WS3 tamper-evidence); now fails closed (no default,
      published literals rejected forever, verify fails without key), `RAGIN_AUDIT_HOST_KEY`
      documented in `.env.example`, 8 regressions in
      `tests/unit/test_wave2_crypto_config.py`. Deferrals (MEDIUM, fix-HIGHs-only):
      `ragin-test-key-2024` absent from server_v2 placeholder-refusal set (dev-harness key —
      3 test suites + `start_services.sh` export it; needs a coordinated local-dev posture
      change; no production instance affected), public `RAGIN_IP_SALT` default with
      bridge/validate scripts hardcoding the salt instead of reading the env override, and
      silent unkeyed manifest-digest downgrade when a capture runs without `--study-secret`
      (kind marker records `sha256` honestly). Secrets-in-tree scan: clean (session-file hit
      = AWS documentation example pair). Note: `.venv-gpu/` (21k files) is tracked in git —
      hygiene cleanup candidate, separate line.
- [x] Latency: deterministic fast-paths for common commands + LLM response cache
      (44 s/command kills field sessions; must drop before Phase 1 data has value)
      — done 2026-10-26: `RAGIN_FASTPATH_COMMON` (common commands answered from the
      pinned fiction) + `RAGIN_LLM_CACHE` (in-session identical-prompt replay), both
      default-on and both deferred under model-exposure mode, the enabled provider
      path (WS1 acceptance contract: the provider must be reached every turn), and
      `RAGIN_TEMPLATE_FALLBACK=disabled`. Read commands stay ledger-owned (never
      cached), so mutation → regenerate still holds. Measured with a 1 s/turn
      sleeping-gateway stub: a 14-turn session drops 14 → 3 gateway calls (4.7×;
      ≈ 8 min saved per session at the real 44 s/turn). Tests:
      `tests/unit/test_latency_fastpath_cache.py` (23), full unit suite green.
- [x] `apmix_quota_status.json` atomic write in `check_apmix_catalog.py` (stops the 0-byte
      truncation that breaks `test_watch_audit_pipeline`)
      — landed 2026-10-24 in `d818deb3` (tmp write + `os.replace`); verified 2026-10-26:
      `test_watch_audit_pipeline` 10/10, a live run wrote the artifact at
      2026-10-26T06:04:39Z (`audit_pipeline: ok`, 398 B valid JSON), no stale `.tmp`.
      Residual fixed 2026-10-26: `run_zodiac_eval.sh` gate 5 now persists the
      same file atomically (tmp + `mv`) in the watch-compatible schema
      (`audit_pipeline: skipped` + rich keys; legacy keys kept for the
      snapshot renderer) — pinned by `TestZodiacWriterContract` in
      `tests/unit/test_watch_audit_pipeline.py` (12/12 green).
- [x] `docs/ARCHITECTURE.md` rewrite to the harness design (use the archify diagrams as source);
      decide fate of `server.py`/`siem`/`rollout`/`auth` (delete or wire)
      — rewrite landed 2026-10-24 in `d818deb3`; fate decided 2026-10-26: `server.py` KEPT
      as the marked legacy zodiac/compose entry (Dockerfile CMD, all compose files,
      `install_zodiac_stack.sh` systemd units, `deploy.py`, security-test contract — it is
      load-bearing, "do not extend"); `siem`/`rollout`/`auth` DELETED (18 files: 11 modules +
      `test_rollout.py` + `ragin/config/rollout/`) after verifying zero live callers.
      Suite green: 2139 passed, 9 skipped; legacy path `tests/security/
      test_task2_verified_serving.py` 19/19.
- [x] Move evidence snapshots (`source_bytes/`, `source_snapshot*/`) out of the tree
      — done 2026-10-26: 130 files (2.2 MB) relocated to
      `../evidence_snapshots_archive/` (outside the repo, inside the project root),
      structure preserved, untracked (`git rm --cached`). Integrity: file count equal
      before/after; both `SNAPSHOT_SHA256.json` manifests re-verified in place (31/31 +
      31/31 sha256+bytes match); secret scan of snapshots clean (no .env/key files; the
      one pattern hit is the deception danger-battery source itself). No live references
      (zero tests/scripts read these paths); pointer notes left at both former locations;
      `.gitignore` now blocks `source_bytes/` + `source_snapshot*/` from ever being
      re-tracked. Bytes also remain in git history (`57be3c1c` and earlier).
- [x] Verifier F-group round 2 (credential-format repair) + in-flight triage — landed
      2026-10-26/27 (uncommitted at time of writing): detectors anchored on the credential
      itself (npm, HTTP Basic, DSN userinfo, SendGrid; V24c in `hisoka/deception.py`) plus
      placeholder-idiom precision exemptions; `results/verifier_harm_probe.json` regenerated
      → recall 0.9474 (was 0.5263), 0 false positives (was 2), only `H-offscript-capability`
      missed; abstract + §5.2 wording updated to the round-2 numbers (6/7 disclosures,
      10/10 credential formats). Triage of the same session's collateral: the canonical
      `results/verifier_redteam.json` had been regenerated in flag-OFF mode (123 cases,
      9 SC misses) which broke `test_artifact_consistency` (2 tests) — restored to its
      pinned 105-case form; fresh runs reproduce both modes (flag-off non-SC subset
      78/27 FN=0 FP=0; flag-on 123/123 P=R=1.0 = the `supported_claims` artifact), so no
      evidence was lost. Unit suite green: 2166 passed, 9 skipped (2026-10-27).

- [x] **Provider cutover: apmix free tier retired → agentrouter.org wired (2026-10-27).**
      Two facts found the same morning: (a) AWS session healthy again (SSM: 3 instances
      Online, eu-north-1 — Phase 1 field tasks unblocked); (b) apmix is unusable on the
      current key — Free plan, free tier retired provider-side: wired model
      `claude-sonnet-4-6-free` → `model_not_found` (404), `GET /models` → 200 with an
      **empty list**, all 50 catalog models gated Starter/Pro/Max (7 probed across
      vendors, all 403 `needs the <plan>`).
      **Replacement: agentrouter.org** (user-supplied key + explicit authorization).
      What was built:
      - `ragin/gateway/client.py`: optional **Responses transport**
        (`RAGIN_LLM_API_STYLE=responses`, POST `/v1/responses`) + optional
        `RAGIN_LLM_USER_AGENT`. Chat-shaped payloads are translated at the transport
        boundary and the observation ledger records the payload that actually went on
        the wire (`decoding_wire_fields` shows `max_output_tokens`/`stream`, not the
        dropped `temperature`). Replies are normalized back to the chat shape so all
        existing parsing/CoT-retry/observation logic is unchanged. **15 new tests**
        (`tests/unit/test_gateway_responses_style.py`); suite **2179 passed / 9 skipped**.
      - **Fails closed on contract conflict:** an active generation contract asserts
        `temperature`/`top_p` on the wire, which this endpoint rejects — the client now
        raises `GenerationConfigError` before the first request instead of reporting a
        contract the provider never received. `.env` therefore runs
        `RAGIN_GENERATION_CONTRACT=0` with a comment; re-enabling without a
        provider-capability declaration will hard-error by design.
      - `scripts/check_apmix_catalog.py` now probes the configured transport style and
        sends the UA; live run: `catalog ok (3 models)`, `quota LIVE`, exit 0.
      - `.env` rewritten (backup `.env.bak-20261027-pre-agentrouter`); `.env.example`
        documents both new vars.
      **Caveats that must travel with any new number produced on this provider:**
      1. The key's group exposes only 3 models (`gpt-5.6-sol`, `gpt-6-astra`,
         `gpt-6.1-sol` — wired: `gpt-6.1-sol`), all Responses-only;
         every `claude-*` model is 503 `no available channel` right now.
      2. The gateway 401s clients outside its supported-client allowlist (its own
         announcement #17), and on-list clients in their real formats still fail —
         only specific client identities pass. The user explicitly authorized sending a
         passing User-Agent; their announcement also says bypassing restrictions gets
         accounts banned, so this is **their accepted risk**, revertible by unsetting
         `RAGIN_LLM_USER_AGENT`.
      3. Provider **content filter blocks `cat /etc/passwd`** (400 `content-blocked`),
         both plain and through the apmix WAF rewrite `/etc/./passwd`; `cat /etc/shadow`,
         `whoami`, `id`, `uname -a`, `ls -la`, `ps aux`, `df -h`, `/var/log/auth.log`,
         `curl|sh` all pass. `cat /etc/passwd` is a top-3 attacker command, so field
         sessions on this provider will show transport errors on it — record honestly,
         do not engineer around the filter.
      4. Prior artifacts citing `claude-sonnet-4-6-free` stay historical facts; any
         future run is labeled by its actual provider + model id.

## Phase 5 — Paper reframe + write (Oct 28 → Nov 14) — detailed plan in §Paper below

## Phase 6 — Submit + artifact evaluation (Nov 15–17)

- [ ] Abstract registration **Nov 10** (title + 250-word abstract from §Paper.1)
- [ ] Full paper build Nov 15; internal read-through Nov 16; submit **Nov 17 AoE**
- [ ] Artifact prep: anonymized mirror rebuilt + `--check` PASS; no secrets; one-command repro
      (suite + benchmark + verifier battery); LAYA/JEV decision files included
- [ ] After submission: TDSC fallback — same evidence, longer format; field data keeps accruing
      for the next cycle either way

---

# §Paper — "The Intelligence Ladder" → S&P 2027 (reframe: Option A)

## Paper.1 Thesis and framing (decide once, write everything to it)

**Framing (open since Oct 8, resolved here):** deterministic verified-serving system with a
**priced intelligence ladder**. The paper does NOT claim "smart honeypot deceives attackers".
It claims a **measured pricing rule**: each AI capability added to the serving loop is kept only
if its measured marginal effect justifies its trust price; past the verification point,
additional intelligence bought adaptation, not safety — at benchmark resolution, three
independent instances agree.

**Title (working):** "The Intelligence Ladder: Pricing AI Capabilities in a Verified-Serving
Deception Honeypot"

**Contribution list (each maps to existing artifacts):**
1. A verified-serving honeypot architecture where every attacker-visible artifact passes a
   deterministic fiction-consistency gate + audit trail (design + 47/47 red-team battery,
   precision 0.994/recall 0.942; adversarial hardening pass with 11 fixed findings, zero
   behavior change to the deception surface).
2. A priced-ladder methodology: four rungs (scripted → classifier → RAG → free generation) on
   one loop with per-rung cost/latency/trust accounting and external baselines
   (cowrie/stateful-LLM/unverified-LLM/no-verifier arms).
3. Three independent instances of the negative result, each on a frozen protocol with
   pre-registered thresholds: (a) ladder fold-down Δ=0 at benchmark resolution; (b) Laya v12
   fine-tuning `TUNING_FAIL` (G4/G5/G7/G8/I2, control also below threshold → contract problem);
   (c) JEV gate study (this plan, Phase 2).
4. An honesty-first evaluation methodology: serving-contract composite vs behavioral metrics
   kept separate and labeled; LLM-judge vs human rater results labeled by who judged; blind
   human discrimination packets as the realism anchor (Phase 3 outcome).

**Abstract skeleton (250 words, written Nov 8):** honeypots increasingly delegate deception to
LLMs; we ask what each increment of intelligence costs and buys on a serving loop where nothing
unverified reaches the attacker. [results: ladder + fold-down + Laya + JEV + blind packets]
[design rule that survives]. [artifacts released].

## Paper.2 Section plan (13-page S&P format)

| § | Content | Source artifacts |
|---|---|---|
| 1 Intro (1.5 p) | The pricing question; three-instance negative result up front; contributions | cover letter draft |
| 2 Background & threat model (1.5 p) | Deception honeypots; attacker↔honeypot trust asymmetry; what "verification-first serving" means; threat model incl. adversarial-LLM judge | docs/RAGIN_THREAT_MODEL, ARCHITECTURE rewrite |
| 3 Design (2.5 p) | Harness/Session/Sandbox; verification stack (fiction-consistency + strict-research + deadline + host-fiction + HITL); ladder rungs; decision floor (deterministic policy selector) | code + archify diagrams |
| 4 Implementation (1 p) | Rust/Python transport reality, apmix provider, capture_v4 privacy, containment; hardening pass summary (11 findings, zero behavior change) | Step 11–13 commits |
| 5 Evaluation (4.5 p) | 5.1 serving-contract composite (labeled) + stability; 5.2 ladder + external baselines (channel caveat stated); 5.3 fold-down; 5.4 Laya v12 gates; 5.5 JEV gates; 5.6 blind human packets (primary realism); 5.7 verifier red-team + hardening | results/ ledger + Phase 2/3 outputs |
| 6 Discussion (1.5 p) | Why post-verification intelligence doesn't buy safety; when it would (contract-first design rule); limitations: single judge model, benchmark-resolution bounds, field-data status | LAYA_REAL_INFERENCE_STATUS + this plan |
| 7 Related (1 p) | HoneyGPT etc., LLM-agent verification, negative-result practice | paper/main.tex related |
| 8 Conclusion (0.5 p) | The pricing rule as a deployable checklist | cover letter |

## Paper.3 Claims → evidence map (nothing enters the paper without a row here)

| Claim | Evidence file | Label |
|---|---|---|
| Serving loop never emits unverified text | live pentest probes + sandbox barrier tests | verified |
| Gate catches real secret shapes | test_danger_signal_real_shapes.py (2026-10-24) | verified |
| Composite 0.880 [0.857, 0.900] | bootstrap_ci.json (6 proofs) | serving-contract score |
| Fold-down Δ=0 | jev_ab_eval.json + jev_hard_subset.json (6/400 census) | resolution-bounded |
| Laya tuning fails frozen gates | laya_v12 final_decision_v1.json | frozen-protocol negative |
| JEV arm vs deterministic control fails frozen gates G4/G6/G7 (+ I2 0.5833 > 0.1) | results/jev_decision_v1/final_decision_v1.json + i2_addendum_v1.json (JEV_FAIL_GATES_G4_G6_G7; artifacts re-checked 2026-10-26, addendum inputs sha256-pinned) | frozen-protocol negative |
| Deception realism (AI adversarial workload) | `results/field_attack/sessions.jsonl` (15 live sessions, 178 turns) + `arm_comparison.json` (15v15 local self-play, caveats emitted) | AI workload, self-play, primary |
| A/B contrast v1 (pilot, ceiling artifact) | `results/field_attack/arm_stats_bootstrap_v1.json` (15v15; dwell bounded null, Holm ns) + `docs/ARM_AB_PREREGISTRATION_2026-10-28.md` | pre-registered null, pilot |
| A/B contrast v2 (30-turn/3600 s, 20v20 interleaved) | `results/field_attack/arm_v2_stats.json` (log-rank p=0.975 Holm 1.0; turns bootstrap +4.15 [1.2, 7.15] descriptive; bait capture 0/0 Fisher p=1.0; exploratory surface artifact yield 11/20 vs 0/20 p=0.00015) + `docs/ARM_AB_PREREGISTRATION_V2_2026-10-28.md` | pre-registered null + labeled exploratory |
| AI panel labeling (120 cases, κ=0.811) + deterministic oracle (50.8%, κ=0.317) | `results/laya_research/ai_jury_v1/` + `results/laya_research/ai_jury_oracle_v1/oracle_agreement.json` | AI-workload reliability check, disclosed |
| Deterministic policy layer (v4) locked validation: recall 1.0, alignment 1.0, 0.027 ms | `results/decision_fusion_v4/v4_locked_validation_results_v1.json` + HF2024 retrospective N=720 (observational) | verified floor property |
| Availability constraint measured live: content filter blocks 41.4% of real attacker commands; framed serve-rate 0.24 | `results/provider_content_filter_probe.json` + `_serve_rate.json` (2026-10-27) | measured constraint, honest disclosure |
| Evidence Judge synthetic validation (32→0 false admissions) vs prospective real null | `results/evidence_judge_paired_validation_v1/comparison_summary.json` | synthetic positive, real-data negative — both disclosed |
| Deterministic steering: top-3 0.90 / top-1 0.50, steer attach 0.9 → 0.0 ablated; determinism sweep 39×8 = 1.0 | `results/mtp_steering_eval.json` + `results/determinism_sweep.json` | verified, in §5.5 + supplement |
| Profiler scaling: 0.855→0.887 plateaued (power-law RMSE 0.006, +1pp at 2×) | `results/model_quality/chrollo_learning_curve.json` | data-saturation evidence, supplement |
| Analysis-channel label audit: 3 raters, κ 0.866 identification / 1.0 family, ATT&CK v19.1 pinned (AI-vs-AI disclosed) | `results/cti_manual_audit.json` | label-quality lane, §5.8 + supplement |
| Deception-fiction iteration record: dwell-replay ladder v1 (0/14) → v6/v7 (12/12), tells: key prefix, fallback echo, AWS-doc credentials | `results/jev_dwell_replay_v2*–v7*` | design-record, supplement |
| Serving cost: fast-path+cache 14→3 gateway calls (4.7×); mTLS matrix fail-closed | `tests/unit/test_latency_fastpath_cache.py` + `docs/72h_sprint/MTLS_AUTHENTICATION.md` | supplement |
| Visual/narrative pass 2026-10-30: KM survival figure (fig:km) for A/B v2; fig:grounding + fig:results wired into body (were orphaned floats); section transitions carry the ladder arc; intro roadmap compressed | `paper/figures/km.tex` + `arm_v2_stats.json` KM data | central contrast now visualized; all body figures referenced |
| v3 CONFIRMATORY RESULT (2026-10-31): planted-artifact yield 6/10 vs 0/10, Fisher p=0.011, RD 0.60 [0.40,0.80]; family-disjoint brain (gemini-3.8-flash@apinex); prereg V3 + Amendment 2 | `results/field_attack_v3/arm_v3_stats.json` + `docs/ARM_AB_PREREGISTRATION_V3_2026-10-30.md` | **first confirmatory positive: replicates v2 exploratory finding** |
| Cross-family jury: claude-sonnet-5-5 agrees with each GPT checkpoint 0.76-0.81 exact / 0.86-0.88 binary; 4-rater κ drops 0.805→0.675 (correlated-error mass measured) | `results/panel_v3/crossfamily_jury_agreement.json` | coprimality quantified, §5.8 |
| Out-of-sample gate probe: 1/12 fresh formats caught (recall 0.083), 0.43 draft rejection vs 0.96 in-sample | `results/panel_v3/out_of_sample_results.json` | measured failure disclosed, §5.2 |
| Reviewer pass 2026-10-29 (5 agents): jury bootstrap CI 0.811 [0.714,0.896] + LOO 0.764-0.897; field accounting 225 verified/43 fail-closed/23 legacy; estimand defense (machine-vs-machine fidelity); saturation reframe; bait resolution-bounded (3/40 addressable); yield promoted to signature; deployment-guidance paragraph; ambient-internet contradiction fixed | `results/laya_research/ai_jury_bootstrap_ci/` + `results/field_export/` | reviewer-hardened, all disclosed |
| Elite pass 2026-10-29: A1--A4 measured counts (fiction 8→0, steer 8→0, verify 0→8 unverified serves, REQUIRE 3→0) + HITL census 2,114 decisions/83 refused | `results/ablation_battery.json` + `results/hitl_audit_bench.jsonl` | measured, §5.2 |
| Deployed hybrid retrieval trails both components (NDCG +0.21, recall@20 +0.42, Holm p<1e-5) | `results/stat_eval/summary.json` | design finding, §5.5 |
| CTI audit strict-vs-family: strict F1 0.732 vs family 1.0; 3/3 technique conflicts are echoes | `results/cti_manual_audit.json` | mechanistic echo support, §5.8 |
| Trajectory-prefix curve 0.25→0.955 + coverage deltas; 12 algorithm property proofs | `results/sp2027_rescue/...` + `results/algorithm_validation.json` | supplement Supporting Studies |
| Factual corrections: pre-repair 4-of-7, 12/12 = v6/v7, 89-case P 0.994/R 0.943, 4-of-15 intent, mTLS path, 4.7× softening | auditor report 2026-10-29 | corrected in text |
| Model-name correction: `space-bunny-free` = MiniMax M3.1 Flash (router alias; artifacts keep alias) | supplement provenance + Table `tab:verifier-cross-family` footnote (2026-10-29) | correct attribution |
| Independent design review of the frozen 120-case packet (preserved design) | `docs/laya_integration/CODEX_EXPERIMENTAL_DESIGN_REVIEW.md` + `.omo/evidence/ROLE_G_EXPERIMENTAL_DESIGN_REVIEW_20261013.json` | design-only review, cited in supplement |
| External-attacker precedent: Aug-2026 VPS, 30 sessions, 2 genuine external attackers | `results/ALL_RESULTS_VS_ESWA_PAPER.md` axis 15 | historical external-validity evidence |
| Protocol sensitivity of the panel (κ 0.663–0.790 under rewording; per-checkpoint self-reproduction 0.81–0.97) | `results/laya_research/ai_jury_protocol_sensitivity/` (2026-10-29) | disclosed wording-sensitivity measurement |
| Deception realism (human) | blind packets r1–r5 prepared, never answered (`human_returns/` empty) | human, future work |
| LLM-judge quality 3.86/5 | 20260922_180637_consensus | LLM-judged, secondary |
| Hardening: 11 findings fixed | Step 13 commit + 96 tests | verified |
| Field data | Phase 1 export (if go) OR honest no-interaction census | labeled by provenance |

## Paper.4 Writing schedule (parallel to everything else)

- [x] **Oct 28–30:** §2 + §3 drafts (design is stable; use archify diagrams as figure bases)
  — done early 2026-10-26 (reframe-fit draft, content spec only; figures still pending):
  S&P §2 rewritten as "Background and Threat Model" on both surfaces (`sp_threat_model.tex` full
  reframe; `background.tex` synced): trust asymmetry, verification-first serving defined,
  observable-trace + deterministic-oracle model, priced-rungs table `tab:rungs` (trust price +
  exit ramp per rung), 8-row attacker-capability table `tab:capability` (all prior
  evidence/nonclaim rows preserved word-for-word, + injection + judge rows), adversarial-LLM-judge
  threat paragraph with judge cites. §3 regroup: G1–G5 goals block now defined once in shared
  `design.tex` intro (was background-only → was dangling on sp2027), ladder subsection cross-refs
  §2's pricing table. Decided Paper.1 title applied to both surfaces. Build: both PDFs clean
  (0 errors, 0 undefined refs, 0 overfull); suite 2147/9 green. **Page state: sp2027 15 → 17 pp
  vs 13-page budget — trim pass required in the Nov 10–14 assembly window** (§2 currently ≈ 2.2 pp
  vs 1.5 budget; capability table* floats to the page after §2).
- [x] **Oct 31–Nov 3:** §5.1–5.4 (all existing artifacts; numbers only from the ledger + addendum)
  — done early 2026-10-26: the two MISSING subsections drafted into `sections/sp_evaluation.tex`
  with numbers verified from the artifacts: **Fold-Down at Benchmark Resolution**
  (`sec:folddown`; A/B Δ=0.0 on n=200 both arms 200/200, under-routing 0.0 all tiers;
  misroute census 6/400 = 1.5% addressable space → resolution-bounded null) and
  **Fine-Tuning Against Frozen Gates** (`sec:laya`; full 11-gate table both arms from the
  v12 results artifact — candidate fails G4/G5/G7/G8/I2, control fails G4–G8 + I2/I3 →
  contract-problem reading; in-sample fit labeled non-held-out). Composite/stability/ladder
  content already exists (rq2/scorer-audit/jeveval subsections). Build: 0 errors, 0 undefined
  refs, `tab:laya-gates` resolves; 18 pp (renumbering to the 5.1–5.7 layout lands at assembly;
  trim pass still owed).
- [x] **Nov 4–6:** §5.5 (JEV) — done early 2026-10-26 (`sec:jevgates`): G1–G8 + I2 narrative
  with artifact-verified numbers (passes G1–G3/G5/G8; fails G4 0.714, G6 0.833, G7 0.563;
  I2 re-graded 7/12 = 0.583 from pinned inputs; three-instance convergence paragraph).
  §5.6 (blind packets → AI workload per the Phase 3 pivot) and §5.7 (red-team/hardening)
  — **both done early 2026-10-27** (`sec:advworkload`, `sec:hardening` in
  `sections/sp_evaluation.tex`): §5.6 reports the 15-session live batch (178 turns,
  honeytoken consumption 30 AWS/67 .dbpass/35 .env from `sessions.jsonl`) + the 15v15
  arm contrast from `arm_comparison.json` (dwell 143.0 vs 105.0 s, 16.9 vs 8.2 s/turn,
  sensitive-read census, VERDICT outcomes) with all three artifact caveats verbatim,
  the shared-model-family self-play limitation, and human raters kept as future work;
  §5.7 reports wave-1 (11 findings / 96 tests, 12-of-15 → 0-of-11 gate bypass, held
  probes, 47/47 checks + live 80-case P 0.994/R 0.942) and wave-2 (14/16 + crypto HIGH
  fail-closed, 42+8 tests, 3 MEDIUM deferrals). Build: 0 errors, 0 undefined refs,
  0 overfull; main body ≈ 13 pp (References on p. 13, total 21 pp with supplement).
- **Nov 7–9:** §1 intro + §6 discussion + §7 related; figures final (gen_sp_figures --check)
- **Nov 8:** abstract frozen for Nov 10 registration
- **Nov 10–14:** full-paper assembly, internal adversarial read (fresh-eyes pass), build clean
- **Nov 15–17:** artifact mirror + final build + submit

## Standing rules (unchanged)

1. Every fix lands as its own commit; suite stays green (currently 2088/0).
2. No doc number changes without its artifact re-check (ledger addendum pattern).
3. Field exposure requires the ethics checklist pass — never bypass.
4. Laya stays OFF; it is evidence, not a component.
5. Every "human"/"LLM-judge" claim carries its label into the paper verbatim.
