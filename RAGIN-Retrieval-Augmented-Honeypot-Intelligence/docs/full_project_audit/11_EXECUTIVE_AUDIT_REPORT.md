# 11 — Executive Audit Report

**RAGIN — Retrieval-Augmented Honeypot Intelligence**  
**Audit date:** 2026-10-10  
**Auditor:** Buffy (Codebuff)  
**Scope:** Complete project discovery, source-code mapping, architecture reconstruction, and evidence-based technical audit  
**Constraint:** No feature development, no refactoring, no deployment, no destructive actions

---

## TL;DR

RAGIN is a **mature, carefully engineered AI-security research project** with a strong core security invariant: **no deception response reaches an SSH attacker without passing machine verification.** This invariant is implemented, integrated, tested (471/471 tests PASS across 6 suites executed this audit), and validated against pinned artifacts (47/47 artifact-consistency checks PASS).

The project is **NOT a simple honeypot.** It's a research platform with: a Random Forest attacker classifier (Chrollo), a hybrid RAG CTI engine (Don), an LLM-based adaptive deceiver with 100+ danger-signal regex patterns (Hisoka), a fiction-graph consistency layer, a cross-session host-fiction store, a human-in-the-loop approval gate, an optional authenticated provider transport, and a Cowrie SSH bridge that serves verified responses to real attackers.

The codebase is **actively developed** (43 commits ahead of origin, dirty worktree, 6932 session files on disk) and **partially deployed** (local Docker Compose works; field deployment requires an approved private LLM bridge; AWS deployment is historical/unverified).

The **primary risk** is not a bug — it's scope: 93 test files, 225 result files, 107 source modules, 2 allied paper submissions (TDSC + SP2027), and a codebase where critical security properties are distributed across 4+ verification layers in 4+ files. A new developer or reviewer needs significant context to understand what's verified, what's tested, and what's deployed.

---

## What exists

### Source code (107 Python modules in ragin/)

| Layer | Components | Status |
|-------|-----------|--------|
| **Entry points** | server_v2.py (pipeline + disabled standalone), server.py (legacy, hisoka route disabled) | server_v2 is authoritative; server.py is legacy |
| **Orchestration** | Harness (stateless loop), Sandbox (attacker I/O), Session (crash-safe JSONL log) | Integrated + tested |
| **Verification** | FictionConsistencyVerifier (4 check layers), HostFictionVerifier (cross-session), supported_claims (opt-in fail-closed), bridge_verifier_artifact (canonical templates) | Integrated + tested + artifact-validated |
| **Classification** | ChrolloClassifier (sklearn RF), ChrolloAdapter | Integrated + tested (needs model artifact for inference) |
| **CTI** | ThreatRAGEngine (BM25 + vector + optional LLM), DonAdapter | Integrated + tested (BM25 works offline; vector+LLM needs backend) |
| **Deception** | AdaptiveDeceiver, ResponseGenerator (LLM + 100+ deterministic fast-paths), PersonaManager, ArtifactInjector, HoneytokenEngine, FilesystemLedger | Integrated + tested (100+ hisoka tests) |
| **HITL** | ApprovalGateway (risk-based AUTO/NOTIFY/REQUIRE), ClaimedApprover, ConsoleApprover, FileAuditTrail | Integrated + tested |
| **Transport** | GatewayClient (shared HTTP), ProviderTransport (auth-gated subclass), ProviderTransportAdapter (injects into ResponseGenerator) | Implemented + tested (11/11), not live |
| **mTLS** | build_server_context_from_env, peer_certificate_authorized | Implemented + tested, not in Docker Compose |
| **Jev** | Jev System One (free zen gateway, additive classification) | Implemented, light testing |
| **Untested/unintegrated** | RBAC, Decoys, SIEM, Rollout, Coordination, Intelligence, Monitoring (partial) | Implemented but not wired or tested |

### Tests (93 files, 471/471 PASS in executed suites)

- ✅ Verifier redteam artifact consistency: 47/47 PASS (offline, no LLM needed)
- ✅ Provider transport: 11/11 PASS
- ✅ Security task2 verified serving: 13/13 PASS (tests the core invariant)
- ✅ Verifier + fiction + hisoka + artifact consistency: 186/186 PASS
- ✅ Server v2 (including Cowrie bridge): 24/24 PASS
- ✅ Cycle + don + chrollo + hitl + host fiction: 230/230 PASS
- ⚠️ Integration tests (5 files): NOT executed this audit
- ⚠️ E2E tests (1 file): NOT executed this audit
- ❌ Some components have NO tests (RBAC, Decoys, SIEM, Rollout, Coordination, Intelligence)

### Research artifacts (225 files in results/)

- ✅ 4 canonical verifier redteam artifacts (pinned, SHA256 manifest, provenance record)
- ✅ Offline stratum: 105 cases, P=R=1.000, zero FPs/FNs
- ✅ Live deepseek: 236 drafts, P=1.000, R=0.931, Wilson CIs
- ✅ Live space-bunny post-fix: 261 drafts, P=0.995, R=0.943
- ✅ Live space-bunny pre-fix: 80 cases, P=0.994, R=0.942
- ⚠️ CTI manual audit corpus (766KB): exists, not verified this audit
- ⚠️ Human eval scored results: exist, not verified this audit
- ⚠️ External baselines (multiple JSONs): exist, not verified this audit
- ⚠️ Ablation battery: exists, not verified this audit
- ⚠️ SP2027 rescue benchmark: recently added, not inspected

### Deployment (Docker Compose + historical AWS)

- ✅ Local Docker Compose: 9 services, ragin-internal (isolated) + ragin-external networks, NGINX frontend, Cowrie SSH honeypot
- ⚠️ Field deployment: docker-compose.field.yml exists, .env.field.example has placeholder bridge URL (requires explicit approval)
- ⚠️ AWS: all identifiers historical, no current state verified, no AWS access confirmed
- ❌ server_v2 is NOT a Docker Compose service (the compose runs legacy server.py)

---

## What actually works

1. **The core security invariant:** No unverified content reaches an SSH attacker. This is tested (13 security tests), implemented in the harness (_process_verified → _strict_verify → _strict_commit), and validated by artifact checks.

2. **The verification chain:** FictionConsistencyVerifier catches degenerate output, danger signals (refusal/self-reference/secret patterns), identity-pin violations, and fiction contradictions. HostFictionVerifier adds cross-session consistency. The bridge_verifier_artifact ensures supported commands (whoami, id, id -un) always get canonical template responses on the SSH wire.

3. **Deterministic fast-paths:** sudo, IMDS (169.254.169.254), SSH host keys, sudo -l, credential bait, filesystem replay — all handled deterministically without LLM involvement. This is critical for identity consistency: the most identity-revealing commands never drift.

4. **Danger signal detection:** 100+ regex patterns catch refusal phrasing, AI self-reference, real secrets (AWS keys, SQL dumps, password= values), honeypot tells, and surveillance self-reference. Patterns are tightly motivated by live red-team findings (V3 through V22).

5. **Artifact pinning:** The verifier_redteam_check.py script pins exact counts, metrics, and rounding. Tampering flips the exit code to 1 and names the drift. This closes the paper<->artifact drift risk.

6. **Session durability:** Sessions are append-only JSONL with fsync after each write. Session.wake() recovers from disk. HostFictionStore uses atomic file replace. HITL audit trail uses append-only JSONL.

7. **Provider transport safety:** ProviderTransport raises ProviderUnavailableError when unauthenticated (no silent fallback to unauthenticated endpoint). Placeholder keys are treated as unconfigured. 11 tests cover the contract.

---

## What is broken or incomplete

### Broken (confirmed)

1. **server_v2 standalone mode is disabled:** `create_app(mode="standalone")` raises RuntimeError. This is intentional (prevents unverified serving) but means the standalone path is dead code.

2. **server.py hisoka route returns 410:** Legacy unverified serving is disabled. The `_handle_deception()` function and response_cache are dead code.

3. **server_v2 is not in Docker Compose:** The compose runs legacy server.py services. If server_v2 is the intended production path, it needs a service definition.

### Incomplete (needs work)

4. **No rate limiting in server_v2:** server.py has it; server_v2 doesn't. Risk for direct exposure.

5. **_TRANSCRIPT_MAP session resolution is crude:** In-memory dict, 20K entry bound, full clear when full, no persistence across restarts. Works for dev, fragile for long-running field deploys.

6. **Provider transport is not live:** Implemented and tested but no provider configured. If the project needs a paid LLM provider, this needs deployment work.

7. **Cross-session fiction not validated in live field:** HostFictionStore is unit-tested but not validated in a live deployment with reconnecting attackers.

8. **Config hierarchy is unclear:** 4 config sources (env, .env.example, settings.yaml, docker-compose.yml) with overlapping concerns and a latent bug (settings.yaml `${...}` placeholders are NOT expanded by yaml.safe_load).

9. **Large deception.py (3195 lines):** 100+ regex patterns, 20+ functions, 5 concerns in one file. Works, but hard to review and extend.

10. **Some components have no tests:** RBAC, Decoys, SIEM, Rollout, Coordination, Intelligence. Some are not wired into the serving path (so low risk), but the lack of tests makes them hard to assess.

---

## What remains unknown

### Not verified this audit

1. **CTI manual audit reproducibility:** The 766KB corpus and 3 blinded annotators exist but were not re-run.
2. **Human eval reproducibility:** Multiple scored dirs exist but were not re-run.
3. **Chrollo classifier accuracy:** The model artifact and benchmark_report.json exist but were not re-run.
4. **Full test suite:** 471 tests executed across 6 suites. The remaining ~46 files (integration, e2e, some unit) were not run.
5. **AWS current state:** All AWS identifiers are historical. No AWS access confirmed.
6. **Field deployment status:** No confirmation that any field endpoint is currently live.
7. **Provider transport live status:** No confirmation that a provider is configured or reachable.
8. **SP2027 rescue benchmark:** Recently added, not inspected.
9. **Overnight 20261009 results:** Recently added, not inspected.

### Not inspected (out of scope for this audit)

1. **ragin/auth/rbac.py** — exists, not wired, not tested
2. **ragin/decoys/** — 5 modules, not wired, not tested
3. **ragin/intelligence/** — 4 modules, not tested
4. **ragin/jev/** — 4 modules, light testing
5. **ragin/monitoring/** — 4 modules, partial tests
6. **ragin/rollout/** — 4 modules, not tested
7. **ragin/siem/** — 4 modules, not tested
8. **ragin/decision/** — 2 modules, not tested
9. **ragin/cycle/coordination.py** — imported optionally, not tested
10. **data/sessions/ses-*.jsonl** — 6932 files, not inspected individually
11. **Most result JSON files** — not inspected (only the 4 canonical verifier artifacts + manifest + provenance + derived_headline_values)
12. **External PDFs** (ESWA-D-26-33173.pdf, imc_vpn.pdf) — binary, not inspected

---

## Top 5 highest-priority actions

### 1. P0-1: Prevent RAGIN_REQUIRE_AUTH=false from silently disabling auth

**Why:** The current behavior (return True for all requests when REQUIRE_AUTH=false and API_KEY empty) is a silent auth bypass. If someone sets this in production (or a Docker compose env typo), the entire auth surface disappears.

**Acceptance criteria:**
- [ ] server_v2.py emits WARNING log when REQUIRE_AUTH is False at startup
- [ ] server_v2.py emits WARNING log when API_KEY is empty and REQUIRE_AUTH is False
- [ ] docker-compose.yml explicitly sets RAGIN_REQUIRE_AUTH (or documents that the default is enabled)
- [ ] .env.example documents that RAGIN_REQUIRE_AUTH must be enabled in production

### 2. P0-3: Wire server_v2 as a Docker Compose service (if it's the production path)

**Why:** The Docker Compose runs legacy server.py (hisoka route returns 410). If server_v2 is the intended production path with mandatory verification, it must be a Docker service. Currently, the "auth authoritative verified pipeline" exists in code but is NOT deployed in the standard compose.

**Acceptance criteria:**
- [ ] docker-compose.yml has a pipeline service running server_v2 --mode pipeline
- [ ] Pipeline service is on ragin-internal (isolated)
- [ ] Pipeline service can reach the gateway
- [ ] Cowrie can reach the pipeline (RAGIN_BRIDGE_HOST or new network)
- [ ] Pipeline service has RAGIN_API_KEY set
- [ ] Pipeline service does NOT expose ports to host directly

### 3. P1-2: Fix _TRANSCRIPT_MAP for long-running field deploys

**Why:** The in-memory transcript map is a crude session-resolution mechanism that doesn't survive restarts and has a crude clear behavior. For field deployments (which are long-running), this needs to be more robust. Session continuity should survive a server restart via the disk-backed Session.wake() path.

**Acceptance criteria:**
- [ ] Session continuity survives server restart (via disk-backed sessions)
- [ ] Transcript map uses bounded LRU eviction (not full clear)
- [ ] Transcript map size is configurable
- [ ] Test simulates 20K+ sessions and asserts memory stays bounded
- [ ] Document that X-Session-Id header is the preferred pinning mechanism

### 4. P2-1: Run the full test suite and record results

**Why:** 471 tests executed this audit, but ~46 files remain (integration, e2e, some unit). Previous reports of 1413-1657 passed suggest a larger suite. We need the full picture before claiming the test suite is healthy.

**Acceptance criteria:**
- [ ] Run `pytest tests/ -v --tb=short` with .venv
- [ ] Record full pass/fail/skip counts
- [ ] Identify which tests are skipped and why
- [ ] Fix any failing tests (not weaken assertions)
- [ ] Record results in audit output

### 5. P2-2 + P2-3: Verify CTI + human eval + classifier claims against artifacts

**Why:** The verifier redteam claims are solidly anchored (47/47 checks PASS). But the paper likely makes additional claims from CTI audit, human eval, and classifier accuracy that were NOT verified this audit. Before the paper is final, these need verification.

**Acceptance criteria:**
- [ ] Run cti_manual_audit.py and verify corpus produces reported annotations
- [ ] Run human_blind_eval.py and verify scored results match paper claims
- [ ] Run benchmark_core.py (or relevant) and verify classifier accuracy matches
- [ ] Check training/tuning manifests are consistent with reported metrics
- [ ] Document any gaps found

---

## Confidence levels

| Area | Confidence | Reason |
|------|-----------|--------|
| Core security invariant (no unverified content served) | HIGH | Tested (13 security tests), implemented in harness, artifact-validated |
| Verification chain mechanics | HIGH | Read all 4 layers, traced full flow, tested |
| Provider transport safety | HIGH | 11 tests, read provider_transport.py fully |
| Server v2 auth and session management | HIGH | Read server_v2.py fully, 24 tests pass |
| Cowrie bridge behavior | HIGH | 8 bridge tests, read openai_chat_completions fully |
| Artifact consistency (verifier redteam) | HIGH | 47/47 checks PASS, checker is offline and deterministic |
| Harness orchestration | HIGH | Read harness.py fully, 230+13 tests pass |
| Fiction graph and host fiction | HIGH | Read both files, 30+ tests pass |
| Hisoka deception (deterministic fast-paths, danger patterns) | HIGH | Read deception.py (lines 1-1098 of 3195), 100+ tests pass |
| Don CTI engine (BM25) | MEDIUM | Read rag_engine.py, BM25 tests pass, vector+LLM path needs backend |
| Chrollo classifier | MEDIUM | Read classifier.py, tests pass, model artifact not re-run |
| Deployment state (local Docker) | HIGH | Read docker-compose.yml fully, confirmed structure |
| Deployment state (field + AWS) | LOW | No access confirmed, all AWS identifiers historical |
| CTI audit reproducibility | LOW | Not verified this audit |
| Human eval reproducibility | LOW | Not verified this audit |
| Untested components (RBAC, Decoys, SIEM, Rollout, Coordination, Intelligence) | LOW | No tests, not fully read, not wired |
| SP2027 rescue benchmark | LOW | Recently added, not inspected |
| Overnight 20261009 results | LOW | Recently added, not inspected |
| Full test suite (remaining ~46 files) | LOW | Not executed this audit |

---

## Artifact locations

All deliverables are in: `docs/full_project_audit/`

| File | Content |
|------|--------|
| 01_WORKSPACE_INVENTORY.md | Complete filesystem and repo inventory with coverage ledger |
| 02_ARCHITECTURE_MAP.md | System architecture with 8 Mermaid diagrams |
| 03_RUNTIME_CALL_GRAPH.md | Authoritative request flow, serve-path labels, verification chain, session lifecycle, auth chain |
| 04_COMPONENT_STATUS_MATRIX.md | Each component's IMPLEMENTED/INTEGRATED/TESTED/DEPLOYED/VALIDATED status |
| 05_SECURITY_AUDIT.md | Trust boundaries, 2 P0 + 5 P1 + 6 P2 + 4 P3 findings, 17 confirmed safe items |
| 06_AWS_DEPLOYMENT_AUDIT.md | Historical AWS identifiers, deployment scripts, Docker Compose variants, intended vs actual, field config, egress architecture, deployment gaps |
| 07_TEST_COVERAGE_AUDIT.md | 93 test files, 471/471 PASS in executed suites, coverage matrix, gap analysis |
| 08_RESEARCH_REPRODUCIBILITY_AUDIT.md | 47/47 artifact checks PASS, experiment populations, scientific validity assessment, paper-claim-to-artifact mapping |
| 09_TECHNICAL_DEBT.md | 27 items: dead code, duplication, design defects, config drift, missing safeguards, observability gaps, maintainability risks |
| 10_PRIORITY_REMEDIATION_ROADMAP.md | 19 prioritized tasks (5 P0, 5 P1, 6 P2, 5 P3) with acceptance criteria and dependencies |
| 11_EXECUTIVE_AUDIT_REPORT.md | This file |

Machine-readable:
- `inventory.json` — NOT YET CREATED (this session focused on human-readable reports)
- `architecture_graph.json` — NOT YET CREATED
- `audit_findings.json` — NOT YET CREATED

These 3 JSON files can be generated from the markdown reports above if needed for downstream tooling.

---

## Bottom line

RAGIN is a real, working, tested system with a strong security core. The verifier-invariant architecture is sound and well-tested. The project's primary risks are scope and deployment readiness, not fundamental design flaws. The field deployment path requires additional work (server_v2 as a Docker service, rate limiting, session resolution hardening, provider transport if needed). The paper's core verifier claims are solidly anchored to artifacts. The surrounding claims (CTI, human eval, classifier) need verification before final submission.
