# v7 Lateral Rerun — Per-Turn Metadata Validation

**Goal:** confirm per-turn metadata logging lands in artifacts and fast-path attribution shows per turn.
**Config:** cross-weights, attacker `gpt-5.6-luna-free` (apmix), defender `deepseek-v4.1-flash-free` (apmix), family `lateral_pivot`, max 12 turns.

## Attribution fixes made before/during the reruns

1. **`ledger-replay` path** — the deceiver's fiction-replay path sets `fs_replay: True`; the script's attribution chain didn't check it, so exact re-issues would have been misattributed as `template` with false `[warn]` spam. Added to the chain.
2. **`gateway-degraded`** — run #1 exposed that template fallbacks fire *inside* gateway-attributed turns (LLM output trips the danger scrubber → internal template fallback), while the gateway counter still increments. Without this, degradation is invisible in per-turn attribution (`tpl=3/4` vs `paths.gateway=9` mismatch). The script now snapshots the template counter per turn and marks degraded turns.

## Canary redesign (blocked the first two launches)

The old canary planted the nonce in the *context* and demanded it in the reply. After the transcript-styling session tightened the prompt contract to "print ONLY what a real terminal would show", deepseek **correctly suppresses context-planted nonces** — the canary false-failed by design (deterministic, 2/2 launches).

New canary: `echo zq7canary` — faithful-by-design (a real terminal MUST print the argument). Requires a **standalone output line** equal to the nonce: the transcript echo line also contains the token, but templates never emit a bare output line, so a template fallback cannot false-pass. Verified: passes attempt 1, output is exactly `webapp@web-srv-01:~$ echo zq7canary` + `zq7canary`.

## Run #1 (valid, 21:29Z) — per-turn attribution

| Session | turns | left_early | bait | gw | tpl | paths |
|---|---|---|---|---|---|---|
| lateral / baseline | 12 (full) | no | 7 | 9 | 3 | ssh 3, gateway 9 (3 degraded) |
| lateral / treated | 12 (full) | no | 10 | 9 | 4 | ssh 3, gateway 9 (4 degraded) |

- **Zero early leaves, both arms, all 12 turns** — replicates v6's result on the lateral family with the new attacker model (luna), against a defender that refuses some outputs (3–4 in-session degradations). Styled template fallbacks held the fiction; the v5.5 "inconsistent responses" leave stays dead.
- **Fast-path attribution confirmed live**: T1–T3 (`ssh root@…`, `scp …`, `ssh-keyscan …`) all attributed `ssh` deterministic fast-path in both arms; the keyscan flag-parse fix from the anomaly investigation is in the path.
- **Metadata landed in the artifact** (`turn_meta` per turn: turn number, command, attributed path) — the original deliverable is confirmed working.
- Treated bait 10 vs baseline 7 — kind-aware decoy-topology bait still surfaces through the degradations.
- Attacker behavior diverged by arm from T4: baseline drifted to nginx-config recon (`/tmp/nginx.conf`, grep `server_name|proxy_pass`), treated went credential-hunting then **docker-socket enumeration** (`docker ps -a`, `docker inspect` mounts/env) — consistent with the lateral Jev objective (`maximize_recon_surface`) steering toward pivot material.

## Run #2 (invalid — apmix quota exhausted mid-run)

Relaunch to capture `gateway-degraded` attribution hit **HTTP 429 `insufficient_quota`** on every apmix call: *"Your monthly allowance is used up."* Baseline died at turn 8, treated at turn 3, both `[attacker-llm-error]`. Artifact preserved as `jev_dwell_replay_v7_lateral_quota429.json` (kept only as evidence of the outage; the overwritten run-#1 JSON is captured in the table above from the analysis output printed before the relaunch).

AgentRouter (`deepseek-v4-flash`) was probed as fallback defender: still disqualified (content filter blocks Hisoka persona prompts; today it additionally rejects the stored key with 未提供令牌).

## Verification state

- 1285 unit tests green, ruff clean (prior certification; script-only changes since, ruff-checked + py_compile'd).
- **Outstanding:** `gateway-degraded` per-turn attribution is implemented and lint-clean but not yet exercised on live traffic — blocked on apmix quota reset (monthly).

## Next session

1. Re-run `--families lateral_pivot` (then cloud + the rest) after the apmix monthly reset to validate `gateway-degraded` attribution and gather clean cross-weights n>1 data.
2. Consider registering lateral **decoy** credentials as protected fiction (like the IMDS trio) so the defender stops voiding replies that echo our own bait — run #1's 3–4 degradations were likely exactly that.
