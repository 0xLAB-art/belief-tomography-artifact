# Final strict joint trace handoff — 2026-10-23T03:48:43Z

**Trace status: PASS (scoped). Readiness: NOT READY. This is not a matched B0/B1–B3 pilot.**

## 1. Run record

- Command: `.venv/bin/python scripts/run_p0_loopback_ssh_trace_v2.py --out docs/research/p0_strict_joint_trace_20261023T034843Z --negative-command 'cat /etc/sudoers'`
- Raw exit: `0`; run id: `20261023T034849Z-1148555`; finished: `20261023T034911Z`.
- Positive commands: `whoami`, `id`, `uname -a` (one session).
- Negative command: `cat /etc/sudoers` (separate SSH session).
- Cowrie image: `cowrie/cowrie:latest` ID `sha256:710f1e4601a663ac8591f58a42b44e4cd3b7ea170c7e6cdb9e54c430a30cd459`; launched from ID with `--pull=never`; listeners loopback only (`127.0.0.1:41781`, `127.0.0.1:47483`).
- Provider disabled (`RAGIN_PROVIDER_ENABLED=0`), model/Laya disabled (`RAGIN_LAYA_ENABLED=0`), JEV disabled (`RAGIN_JEVI_ENABLED=0`), egress endpoints closed loopback (`127.0.0.1:9`); no AWS/JEV/external provider was called. This is application-level disablement, not a hard network namespace block.

## 2. PROMINENT UNRESOLVED BLOCKER: outer Cowrie identity contradicts inner RAGIN identity

The raw SSH stream is contradictory at the **frontend** layer. The outer Cowrie prompt is `root@svr04:/#`, while the RAGIN response claims `webapp@web-srv-01` and `uid=1001(webapp)`. The strict verifier checks the RAGIN candidate only; it does **not** check the outer Cowrie prompt/banner. Therefore the candidate/verified/served hash agreement is real but **does not establish that all attacker-visible identity is consistent**.

Positive raw stream (305 bytes, full-frontend stimulus):

```text
Welcome to svr04
root@svr04:/# whoami
webapp@web-srv-01:~$ whoami
webapp
root@svr04:/# id
webapp@web-srv-01:~$ id
uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm),999(docker)
root@svr04:/# uname -a
Linux web-srv-01 5.15.0-91-generic #167-Ubuntu SMP x86_64 GNU/Linux
root@svr04:/# 
```

- Positive raw stdout SHA-256: `97877eea921f48d111013f95f67761bf17ec553c436a7a2be34fbd2806d41be4` (305 bytes).
- API candidate = verified = served SHA-256 by turn: `whoami` `9d1799d0206e9e9b52e136d93f0719ddd7917d6aa81fb11cbe53e580694a00a4`; `id` `07c19f5749fbf27b2d1bddec046a2edfd79a7cc7c552eb10bc30e321726e4a06`; `uname -a` `3bbd2728041d286dd6bc3446fc9ad7f095179e72d662c5b6b2c63dda46e89210`.
- Those three hashes cover the RAGIN API candidate/served text only. They do **not** cover the outer `root@svr04:/#` prompt, the banner, or the cross-layer identity contradiction.

This is a readiness blocker for the matched B0/B1–B3 pilot. Human/transcript-quality evaluation must consume the **full frontend stimulus, including prompts**, and must not strip or normalize away the contradiction. The blocker remains until a supported Cowrie persona/configuration matching the pinned RAGIN identity is validated separately. No late Cowrie behavior rewrite or runner relaxation was performed.

## 3. Negative availability cost (actual, not assumed)

- `cat /etc/sudoers` was sent in a separate SSH session after the three positives.
- Observed HTTP 503 count: **1**. `negative_fail_closed`: **true**. `negative_no_accepted_commit`: **true**. `SYSTEM_RESPONSE` count for the negative session: **0**.
- All four negative attempts: `strict_verdict=UNSUPPORTED_COMMAND`, `passed=false`, `commit_event=not_attempted`, `commit_reason=verification_failed`.
- Raw negative stdout is 68 bytes (SHA-256 `1a075f53a80d59b8d4b1c259ca1585c1a86ecdc95b54eac132da02630d848524`), containing the banner, the command echo, and then a **blank prompt** with no answer:
```text
Welcome to svr04
root@svr04:/# cat /etc/sudoers
root@svr04:/# 
```
- The client then reports `Connection closed`; there is no explanatory rejection text. This blank-prompt/closed-session behavior is the measured **availability cost** of strict rejection at the frontend.

## 4. Scoped checks that passed

- `all_turns_consistent`: `True`
- `bridge_http_200`: `True`
- `cowrie_container_ran`: `True`
- `exact_one_negative_input`: `True`
- `exact_three_positive_decisions`: `True`
- `exact_three_positive_generations`: `True`
- `exact_three_positive_inputs`: `True`
- `exact_three_positive_metrics`: `True`
- `exact_three_positive_responses`: `True`
- `exact_three_positive_verifications`: `True`
- `negative_fail_closed`: `True`
- `negative_http_503_observed`: `True`
- `negative_no_accepted_commit`: `True`
- `negative_no_fabricated_claim`: `True`
- `negative_terminal_observed`: `True`
- `no_runner_error`: `True`
- `required_event_types`: `True`
- `server_loopback_only`: `True`
- `ssh_loopback_only`: `True`
- `strict_profile_observed`: `True`
- `terminal_has_answers`: `True`
- `terminal_has_echo`: `True`
- `terminal_has_prompt`: `True`
- `terminal_offsets_distinct_after_echo`: `True`

These checks prove the bounded candidate/transport/strict/deadline/503/no-commit properties. They do **not** prove full attacker-visible transcript consistency, matched-pilot readiness, or model execution.

## 5. Failed run retained (do not overwrite)

- Failed artifact: `docs/research/p0_strict_joint_trace_20261023T034216Z` (exit 1, status FAIL).
- Only failing check was `negative_fail_closed`: rejected `VERIFICATION` events omitted `strict_verdict`, `verification_policy`, and `deadline_enforced`; the fallback rejection had no `VERIFICATION` event. This was an observability bug, not a verifier failure.
- Fixed in `ragin/cycle/harness.py` by emitting the full sanitized verification dict plus disposition on every rejection, including the fallback rejection. The runner check was not relaxed.
- Failed summary SHA-256: `55e6236ec613fd7896961e2868a0596822ae473730e993dbb9414b3ef043f8ef`; failed manifest SHA-256: `630705b18783a8e6bdb58699602c7635321fa585ff145c257245e0afadc8af9b`. The failed directory verified unchanged after the new run (`0` changed files).

## 6. Exact prelaunch source hashes (authoritative for this run)

No source **byte snapshots** were taken at launch. The prelaunch manifest recorded exact sizes and SHA-256 only; source bytes were not copied. The following are the exact launch hashes.

| path | bytes | SHA-256 at launch |
|---|---:|---|
| `configs/ablation/manifest_v1.json` | 2343 | `bce8d0786335ac3bde41d3c6276c8e43c5d814172332eff69026ef5447e3383d` |
| `docs/research/CAUSAL_ABLATION_PROTOCOL.md` | 22408 | `c64db9185ba550cfe65de9da461f21d0cfd10763837ff6b5bb15e5a5b5f84adc` |
| `ragin/capture_v4/privacy.py` | 4434 | `328d227310c5fafaa5237c98f203082f9004752be710d63dd5a387a2a8472382` |
| `ragin/cycle/adapters.py` | 31028 | `a00f1bf753285b34847562db2f610be93d8dd8e415fc3040c9310ac9cb0e671c` |
| `ragin/cycle/classification.py` | 3691 | `d86ab64489f8819b15e6ac4ddcdc79863ee492b73326cd18e1c157a0dd352730` |
| `ragin/cycle/harness.py` | 70428 | `cd6122fd11d24c514d1efff2eb92aed7db03637cfb5d000bdd840567fe584314` |
| `ragin/cycle/provider_transport.py` | 15174 | `9b6af18d9666cb22fd485ff7e38d58c991ef5f86c5bdeb8275f8dfb28ac9f9ca` |
| `ragin/cycle/sandbox.py` | 24813 | `c0d9c3a6367093542448a5455ab3e448732908ff3431e5773a8146b6f77f28db` |
| `ragin/cycle/session.py` | 11797 | `72f8c66b9c6b84618dcc62607859fe81d1e9d63d6d7766da02d6dd0a74693b12` |
| `ragin/cycle/strict_research.py` | 12591 | `5cff1d20b01eb76b89da1a7cb580defa1f8cb625832daf12da5fcc813ad53692` |
| `ragin/cycle/verification_deadline.py` | 15046 | `67dd7a45757cb1dc7bebebe0f3c41e5cfe7928b9c225cbc6e16f2e16030f62d1` |
| `ragin/cycle/verifier.py` | 15210 | `0e4e917fbd76e93b3d2611712dfa54c83a64e43026da88864ad2409f9dfced4d` |
| `ragin/decision_fusion_v4/evidence_export.py` | 10182 | `bd2910d5cd0cdc8af9f7e998ffe29a88d36455c2016dddd8c5148f6526d3c419` |
| `ragin/don/intel_corpus.py` | 7367 | `76ac0938396612db281e8e56af253ab646655eb8e2e18584bf16753ab7537e84` |
| `ragin/don/rag_engine.py` | 41135 | `ded5ede13c6804988a9136b190bf4e59f17da50aab19202046018d616054e905` |
| `ragin/don/vector_store.py` | 7561 | `4189ce343613c9ecf314ac9218f123ce771dbc4faaa90f8ea598f277d7394fef` |
| `ragin/gateway/client.py` | 21312 | `1a13ab4a5542e1e6ede4aeb017215bbe45b1c28b427ee8dc6c2d7af7d2242b54` |
| `ragin/gateway/generation.py` | 14398 | `9e7601c6cc3ae4f5d607c0940db07ea02a32e9b27e6a8aaa5b0c52728ce450cb` |
| `ragin/graph/host_fiction.py` | 17715 | `eb694ee3ad93f1f95dc00ab65d4865cf2a48654cafcb8792a2698e78c8dfadee` |
| `ragin/hisoka/deceiver.py` | 36074 | `f4968b01ca54b63da1d50203088c18f3b5eb801f2145967a0113dc73e564f297` |
| `ragin/hisoka/deception.py` | 180051 | `d30164765c85fbcf14c8d3dcf030067073695e21d940ccd8b2744ce95db411d7` |
| `ragin/server_v2.py` | 48260 | `a50a6674f2e2f8530841719e5f4df5a3b418614a1f22e0595393dfc45c019052` |
| `scripts/run_p0_loopback_ssh_trace_v1.py` | 35250 | `4a982e090bcd1f7b363ed03b0de0b691ebc1c6be9449fd0ea1036f866fed03f8` |
| `scripts/run_p0_loopback_ssh_trace_v2.py` | 45907 | `9c2282bcbbe0894b81dcc9451fa26e4d2a130d17369a8ba0cfc8bcc5d99c3909` |

### Current drift versus launch

At the post-run drift check (`2026-10-23T03:56:12Z`), 23 of 24 launch source files matched the
worktree. **One file drifted:**
- `ragin/hisoka/deception.py`: launch `180051` bytes / `d30164765c85fbcf14c8d3dcf030067073695e21d940ccd8b2744ce95db411d7`; current `180181` bytes / `8f8c9b8537bd775360dbd497a26ffb26ab55eb1934d5dd184d3aa23e8ece6c7d`.

Do **not** say the current tree matches the launch tree. The drift is consistent with the generation peer’s announced `usage_scope=LAST_PROVIDER_REQUEST_ONLY` metadata edit, but this report does not re-audit its determinism. The launch manifest remains authoritative for what was traced.

## 7. Known hash for the evaluation-owner freeze

The evaluator/freeze owner should use the launch harness hash, not a later worktree hash:

- `ragin/cycle/harness.py` launch and current: `cd6122fd11d24c514d1efff2eb92aed7db03637cfb5d000bdd840567fe584314` (70428 bytes).
- Strict profile: `ragin/cycle/strict_research.py` `5cff1d20b01eb76b89da1a7cb580defa1f8cb625832daf12da5fcc813ad53692`.
- Deadline/verdict schema: `ragin/cycle/verification_deadline.py` `67dd7a45757cb1dc7bebebe0f3c41e5cfe7928b9c225cbc6e16f2e16030f62d1`.

Evaluation-owner hash integration is a **report-mediated handoff**: no evaluation module, script, config, or doc owned by the eval peer was edited here. The eval owner must reconcile these hashes with its new modules before the final validator packages anything.

## 8. Preservation and cleanup

- Old 5352 tracked `data/`, `results/`, `paper/` files: **0** size/SHA mismatches versus the frozen 2026-10-22 baseline manifest.
- `data/sessions`: **7659** files, aggregate inventory SHA-256 `0dcb647984b7134ccc7f0a5a557db5f37dacc4e8facdf1d0d4297d61ce4b9328`, unchanged by this run.
- Owned trace container `ragin-p0-loopback-1148555-20261023T034849Z` was removed by the runner; no owned p0 container remains. The pre-existing `ragin-cowrie-shield` container (8 days old) was not touched.
- Raw trace files: 19 manifest files plus `trace_manifest.json`. Current summary SHA-256 `022940e83bf157477537cc0309bb794bcd41871a7d579bc09db559b3523957bb`; manifest SHA-256 `013e3e3e4f0b3d1dbc04b677a6f7e867bc72d6ea742a1f277178eb60b36c93f8`; prelaunch manifest SHA-256 `2d42629813ba83d06c36381a3e1dd69a3012011ac267c194ad7cf312518a2f08`.

Frozen manifests: `P0_STRICT_JOINT_TRACE_20261023T034843Z_FROZEN_MANIFEST.json` and `P0_STRICT_JOINT_TRACE_20261023T034216Z_FAILED_FROZEN_MANIFEST.json`.

## 9. Packaging deferred

Packaging of current runtime bytes plus this final trace is **deferred until all streams finish**. Final-validator package must pin a fresh tree and preserve this launch manifest and raw trace; it must not silently substitute the current `deception.py` bytes for the launch bytes. No runtime byte archive was made in this step.

## 10. Readiness boundary

- **B0/B1–B3 matched pilot: NOT READY.**
- **Attacker-visible identity consistency: NOT ESTABLISHED / CONTRADICTION OPEN.**
- **B1–B3 model execution: NOT ESTABLISHED.**
- **Hard network egress isolation: NOT ESTABLISHED** (application-level loopback disablement only).
- **Matched pilot blocked until** a supported Cowrie persona/config matching the pinned RAGIN identity is validated separately, and human/transcript quality consumes the full frontend stimulus including outer prompts.

