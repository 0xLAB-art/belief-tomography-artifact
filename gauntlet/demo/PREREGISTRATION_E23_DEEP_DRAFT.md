# PREREGISTRATION — E23: E3-deep (Deception-Engine Depth Upgrade) — DRAFT, NOT YET REGISTERED

**Status:** STAGED 2026-11-22. Blocked on: (a) `aws login` re-authentication
(user action — session expired), (b) the deception-engine deepening design
pass below must be frozen in code + committed BEFORE any E23 data.

## Registered question (draft)

Does deepening the deception plane's command-layer fiction (richer fake
filesystem state, broader command semantics, multi-step consistency) increase
attacker engagement depth, and does the deeper plane move attacker measured
beliefs (Δ(B))? The E3 registered null was deployment-scoped: engagement
depth was bounded by the shallow command layer. E23 removes that bound and
re-measures.

## Deepening scope (code-level, frozen before data)

- File: `RAGIN-Retrieval-Augmented-Honeypot-Intelligence/ragin/hisoka/deception.py`
  (864-line companion `deceiver.py` holds the fast-paths: chained baits,
  sudo/authorization, ssh-protocol `_ssh_protocol_text_for` — the latter
  covers only ssh-keyscan/ssh/scp; everything else reaches the LLM deception
  loop, where the shallow-command behavior lives).
- Deepening axes (to be frozen in the amendment commit):
  1. Fake-filesystem state: a persistent per-session view consistent with the
     lateral bait facts (/etc/hosts, deploy.env, .dbpass, NAS mounts).
  2. Command semantics: realistic outputs for the top-20 recon/priv-esc
     commands observed in the E3 persona transcripts (the shallow layer's
     measured failures), rendered deterministically where possible.
  3. Multi-step consistency: the ledger already remembers reads; extend to
     writes so chained fiction stays coherent across turns.
  4. FAIL-CLOSED PRESERVED: the fiction-consistency verifier and canary
     gates are untouched; an unverified turn is still never served.
- Unchanged: personas, seeds, probe set, tomography estimator, kill gates.

## Protocol (draft)

Same registered E3 protocol (5 personas × pre-tomography / deception
session / post-tomography / retest / kill gates) on the deepened plane,
fresh sessions, ~1,900 lane calls, 2–3 h, concurrent execution with the
2026-11-20 logged deviation (6 probe workers + 4 persona pipelines).

## Endpoints (draft)

1. Primary: Δ(B) per persona on the deepened plane vs the registered E3
   floor (0.067) — the deployment-scoped null is re-tested at depth.
2. Secondary: engagement-depth metrics (turns/session, distinct commands,
   follow-through chains triggered) vs the E3 baseline — the depth upgrade
   is only meaningful if engagement measurably deepens.
3. Kill gates: unchanged from E3 (sessions complete, retest degeneracy rule,
   canary-allowlist discipline).

## Deviations

None yet. Every deviation will be logged here before the affected data is
analyzed.

## Deployment checklist (execute after `aws login`)

1. `aws login` (interactive SSO — user action).
2. Commit the deepening patch to `ragin/hisoka/deception.py` (+ any config).
3. Deploy: field compose rebuild on the EDGE/CORE host (docker compose
   -f docker-compose.field.yml up -d --build) via SSM; health-check the
   three arms; verify canary gates live before exposing sessions.
4. `python3 gauntlet/demo/run_e3_deception_gain.py` (background, ~2–3 h),
   resume-from-checkpoint semantics unchanged.
5. `python3 gauntlet/demo/analyze_e3.py` → integrate per the registered
   endpoints; quote into §6.2 and update the §10/§9 disclosures.

## Deployment + debug log (2026-11-22)

- AWS re-authed (user ran `aws login`); fleet verified: EDGE/CORE/INTEL all running.
- Deepening implemented + FROZEN: platform commits 82968b0f (deep layer, 25/25
  census coverage, negative controls correct) + 7fe6dc59 (app-config path forms).
- Deployed to CORE: chunked-b64 SSM transfer (md5-verified on host + in-container),
  docker cp into ragin-core-staging:/app/ragin/hisoka/, container restarted.
- In-container verification: module loads from /app/ragin/hisoka/deception.py,
  ext-list present, appconfig-serve YES, ip-serve YES.
- LIVE smoke results: `ip -br addr` SERVES the deep fiction (was not-found in E3);
  `echo${IFS}...` serves shell-faithfully; BUT `cat /home/webapp/backup/app.config`
  still serves empty — the live cowrie→server_v2→pipeline serve path routes cat-
  class commands through a layer that does NOT reach the deception chain (no
  traceback; the pipeline returns 200 with empty text). Localized: the pipeline's
  response generation (response_generator.py / pipeline.py response step), not the
  deception chain (which now serves correctly when called directly in-container).
- ALSO discovered: the EDGE serves `ragin-cowrie-staging` with `backend = llm`
  (cowrie.cfg on the host at /etc/ragin/cowrie.cfg, pipeline at 172.29.0.1:18083);
  honeyfs mappings are inert in llm-backend mode (deployed anyway, harmless).

## Remaining execution steps (next session)

1. Map server_v2's pipeline serve flow for cat-class commands (pipeline.py +
   response_generator.py response step) and route it through the deep layer
   (or its equivalence in the response generator).
2. Restart + live smoke (same protocol: warm-up whoami, then the census commands).
3. Freeze the routing fix in the amendment commit, THEN run E23 (~1,900 calls,
   background 2-3 h) per the protocol above.
4. Integrate per the registered endpoints; quote into §6.2/§10/§9.

## Rootfs discovery (2026-11-22, end of session)

- The EDGE cowrie container (`ragin-cowrie-staging`) runs with a READ-ONLY
  rootfs (hardening) and NO shell: in-container fs.pickle surgery is impossible;
  `docker cp` into it fails ("container rootfs is marked read-only").
- ARCHITECTURE (verified live): cowrie.cfg `backend = llm` → cowrie serves
  SSH + forwards UNKNOWN commands to the pipeline (172.29.0.1:18083 → CORE
  ragin-core-staging). KNOWN commands (cat/whoami/ls) are served by COWRIE's
  own fake filesystem (fs.pickle in the image + honeyfs) — the pipeline never
  sees them. This is why cat reads served empty (fs.pickle lacks the node)
  while echo/ip served the deep fiction (not cowrie built-ins → forwarded →
  the deployed deep layer answered — VERIFIED LIVE).
- The deepening split, now precise:
  (a) PIPELINE deep layer: DONE, deployed, live (ip/echo/printf/no-ops serve
      the deep fiction; census failures covered 25/25; negative controls
      correct; honeyfs inert in llm-backend mode, kept harmless).
  (b) COWRIE fs layer: REMAINING — fs.pickle node additions
      (/home/webapp/backup/app.config, /proc/net/fib_trie, /proc/1/*) +
      [honeyfs] content paths INSIDE the container (the etc volume:
      /cowrie/cowrie-git/etc/honeyfs/*). Requires container RECREATE with a
      new fs.pickle mount (host-side pickle prepared via the cowrie image's
      own python + picklesTools/fs classes) — a compose-recreate on the live
      plane, one careful session, go/no-go per FIELD_LAUNCH_CHECKLIST §4.
- INTERIM RESULT for the paper: the pipeline-level deep fiction is LIVE
  (echo/ip semantics serve correctly through the public face — verified
  against the E3 census failures); the cowrie-fs leg is scoped and staged.

## Verification-gate localization (2026-11-22, night session end)

- The remaining blocker is NOT deployment: the deep layer is live on CORE and
  serves for commands that reach it (ip/echo/printf/no-ops verified through the
  public face).
- cat-class commands are suppressed by the platform's FAIL-CLOSED fiction-
  consistency verification: the sandbox response (resp.error set) carries the
  empty serve because the deep fiction introduces facts (app.config contents)
  that are NOT in the verifier's accepted fact universe
  (host_fiction.json: host_facts = 6 facts; ZERO mentions of app.config /
  backup / /proc).
- The correct completion path (preserves the platform's measured 1.0/1.0
  verification guarantee — weakening or bypassing the gate is out of scope):
  register the deep-fiction facts through the verifier's intended
  fact-registration mechanism (ledger.note_fact / host_facts / the fiction
  graph contract — implementation reading required: cycle/sandbox.py
  _handle_command_unlocked → the Gate verification step), freeze, redeploy,
  then run E23 per the protocol above.
- Everything else is DONE: deep layer deployed (platform commit 82968b0f +
  7fe6dc59), in-container serve verified, live ip/echo serving verified,
  architecture mapped (EDGE cowrie-staging backend=llm → CORE
  ragin-core-staging pipeline), rootfs read-only + no-shell constraints banked.

## REGISTERED FINAL (2026-11-22): amendments frozen, E23 LAUNCHED

- Amendment 3 (be618392): harness declares deep-fiction facts into the session
  graph before verification (the verifier grounds against the same graph).
- Amendment 4 (d1bbaf40): identity-neutral deep fiction content — the
  verifier's identity-pin check flags hostname-shaped (dotted) and
  user-assignment tokens; app.config rewritten (sync.target=/mnt/nas/svc,
  db.account dropped). VERIFIER'S OWN contradiction check: 9/9 deep commands
  NONE (including /etc/hosts IP entries).
- LIVE VERIFICATION: cat /home/webapp/backup/app.config serves the deep
  fiction through the public face (paramiko, 55s wait) — the E3 census
  failures are CLOSED at the serving layer.
- E3_RESULTS archived to E3_RESULTS_BASELINE/ (baseline artifacts preserved);
  E23 runs FRESH sessions on the DEEPENED plane (same protocol, personas,
  seeds policy, estimator, kill gates as the registered E3).
- This file is now the REGISTERED E23 protocol. Any deviation is logged
  above before the affected data is analyzed.
