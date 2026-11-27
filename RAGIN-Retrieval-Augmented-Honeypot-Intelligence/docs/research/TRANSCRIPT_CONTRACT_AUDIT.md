# Transcript / command-echo contract audit (2026-10-23)

**Scope:** who puts the command echo on the wire, whether the attacker receives it twice,
and what the served payload of a turn actually is.
**Verdict:** the duplication was real, it came from RAGIN (not Cowrie), and it was
inconsistent within a single session. A versioned contract (`v2`) now separates the two
layers. Historical evidence is untouched; new evidence is produced under `v2`.
**Non-claim:** nothing here measures deception effectiveness. No model ran.

---

## 1. Method

1. Byte-level trace of both arms of the bounded loopback proof
   (`docs/research/persona_alignment_20261023T054559Z/ssh_client.ragin.stdout`).
2. Static trace of every composer between the generator and the socket.
3. Execution-level check of the classification heuristic that gates echo insertion.
4. Inventory of the scorers that consume the served text.
5. A/B run of the same five-command session under both contracts.

Artifacts used: `persona_alignment_20261023T052609Z` (v1, duplicate present),
`persona_alignment_20261023T054559Z` (v2, duplicate absent).

---

## 2. Findings

### F1 — There are two independent echo sources, and only one is Cowrie's

| Source | Owner | Evidence |
|---|---|---|
| PTY echo of the bytes the attacker typed | Cowrie / Twisted terminal | `webapp@web-srv-01:~$ whoami` appears before RAGIN's payload is written; every arm (native included) shows it |
| `prompt + command` line prepended to the generated body | RAGIN, `ragin/hisoka/deception.py::_style_as_transcript` (line 709) | The line is absent from the model/template body and present in `serving_trace.candidate_text` |

The native arm receives exactly one echo per command. The RAGIN arm received two for
four of five commands, which is only possible if RAGIN adds the second one.

### F2 — The attacker does receive the duplicate bytes

`persona_alignment_20261023T052609Z/ssh_client.ragin.stdout`, verbatim:

```
webapp@web-srv-01:~$ whoami
webapp@web-srv-01:~$ whoami
webapp
```

The `served_text` recorded by the harness equals the second line plus the answer, so the
duplicate is inside the measured stimulus, not a terminal artefact.

### F3 — Duplication varied by command because a prose heuristic misclassified flags

`_style_as_transcript` prepends only when `_looks_like_shell_command()` (line 674) says the
input is a command. That function rejected any input matching `_PROSE_WORD_RE`, which
contained the bare token `a` under `\b` boundaries — so `uname -a`, `ls -a` and `df -a`
were classified as English prose and served *without* an echo:

| Command | `_looks_like_shell_command` (v1 code) | Echo in served payload |
|---|---|---|
| `whoami`, `id`, `hostname`, `cat /etc/os-release` | True | yes |
| `uname -a` | **False** (token `a` matched prose regex) | no |

That is the whole of the "4 of 5" inconsistency. It was a heuristic defect, not a design
decision, and it is independent of the duplication question itself.

The regex now excludes flag-like tokens (`(?<![-\w])…(?![-\w])`), so every command in the
frozen corpus is classified as a command.

### F4 — The model path has the same problem, via a different entry point

`_postprocess_llm_output_with_provenance` (line 2117) returns the model draft nearly
verbatim, so an LLM that prints its own prompt line is served with a duplicate. `v2`
strips exactly one leading echo line there as well; the draft→served provenance value is
unchanged (`MODEL_CONTENT_POSTPROCESSED`).

### F5 — Why 14 tests assert the transcript shape

The echo-prepending behaviour is not accidental: `_style_as_transcript` was introduced
(v5.5 notes in the source) because bare template fallbacks had a different *style* from
LLM turns — no prompt, no echo — which an attacker model flagged as canned. The
regression suite therefore encodes "a fallback turn looks like a model turn" in
`tests/unit/test_hisoka.py` and `tests/unit/test_credential_baits.py` (14 assertions).

Those tests remain valid under `v1` and were left untouched. The style-parity goal is
preserved under `v2` by the frontend: the PTY echo supplies the transcript shape without
RAGIN fabricating it, which is strictly more faithful.

### F6 — No automated score counts the echo as generated content

* `ragin/cycle/metrics.py::InteractionMetrics` records timings and stage metadata only —
  no response text reaches it.
* `ragin/benchmark/effectiveness.py::composite_score` is a weighted sum of honeytoken
  trigger, engagement, persona accuracy, detection precision and artifact-access rates.
  **It contains no text-quality term at all**, so the historical `0.880` composite is not
  a measure of served-response quality and cannot be inflated or deflated by the echo.
* The served text *is* retained verbatim as the experimental stimulus
  (`ragin/evaluation/closed_loop.py:84`, `ragin/evaluation/records.py:61`) and is what a
  human rater sees in `ragin/evaluation/human_packet.py`, so the duplicate did affect
  human-facing realism ratings, not automated scores.

Corollary for the manuscript: the `0.880` composite and any "served-text score" are
different instruments. Neither may stand in for attacker-visible deception quality.

---

## 3. Decision

The duplication is **not** protocol-faithful — a real shell echoes the typed line once —
so behaviour changed, under a new contract version rather than by editing the frozen
fixture or by quietly changing `v1`:

* `v1` (legacy) is preserved exactly and stays the default, so every historical artifact
  still reproduces byte-for-byte.
* `v2` is defined as "the frontend owns the echo; the server serves output only". It never
  prepends, and it strips exactly one leading echo line that repeats the attacker's
  command.
* The version is resolved once from `RAGIN_TRANSCRIPT_CONTRACT`, unknown values raise, and
  every serving trace records the version, the echo owner, the payload scope and the
  payload byte count.
* New evidence is regenerated only under `v2`. The spec is
  `docs/research/TRANSCRIPT_CONTRACT_V2.md`.

The change was not made to improve a score: no score reads this field (F6). It was made
because the previous output was not what a real shell does and was internally
inconsistent.

---

## 4. Measurement integrity after the change

The per-interaction record now separates these layers explicitly:

| Layer | Where it is recorded | Notes |
|---|---|---|
| Transport framing (banner, prompt, PTY echo) | terminal capture (`ssh_client.*.stdout`), `raw_terminal.*.json` | Cowrie-owned; outside RAGIN's payload |
| Model draft | `serving_trace.candidate_text` + `model_draft_used` / exposure flags | redacted, truncated, hashed |
| Post-contract candidate | `verification.candidate_sha256` | what the verifier cleared |
| Verification decision | `verification.*` (`passed`, `strict_verdict`, `strict_reason`, `issues`) | fail-closed |
| Fallback | `serving_outcome`, `template_id`, `template_fallback_reason` | distinguishes template/fallback from model |
| Served payload | `system_response.text` + `served_response_sha256`, `served_response_bytes`, `served_text_scope` | exact bytes RAGIN returned |
| Echo / non-echo split | `transcript_contract` + the terminal capture | contract says who owns the echo; the capture proves it |
| Per-turn / per-session consistency | proof `turn_checks` / `summary.transcript_contract` | one row per turn |

Primary deception evaluation must use the served payload **plus** the terminal framing,
because the attacker's stimulus is the concatenation. Model-only text quality is a
secondary diagnostic (see `EXPERIMENT_READINESS_REPORT.md`).

---

## 5. Verification performed

| Check | Result |
|---|---|
| `tests/unit/test_transcript_contract_v2.py` (new) | 11 passed |
| 8 related suites (hisoka, credential baits, persona alignment, strict profile, supported claims, strict harness, runtime-truth P0, contract) | 321 passed, exit 0 (subset run) |
| Final 9-file run — the exact command recorded in the change manifest | **359 passed**, exit 0, re-run after the last source edit |
| `ruff` on all changed files | clean, exit 0 |
| Real loopback E2E, contract `v2` (`persona_alignment_20261023T054559Z`) | 5/5 `SUPPORTED`, prompt identical both arms, `served_payload_echo_turns: []`, `frontend_echo_missing_turns: []`, `ok: true` |
| Real loopback E2E, contract `v1` (`persona_alignment_20261023T052609Z`) | duplicate present, preserved as historical evidence |

Attacker view under `v2`:

```
webapp@web-srv-01:~$ whoami
webapp
webapp@web-srv-01:~$ id
uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm),999(docker)
```

---

## 6. Open items (not resolved here)

1. **`id` supplementary groups** — native Cowrie prints the primary gid only; RAGIN
   honours the persona's `4(adm),999(docker)`. Constant across all RAGIN arms, so it does
   not bias B1↔B5 contrasts; it does differ from B0 and is recorded as such.
2. **Contract adoption is opt-in** — a run that forgets `RAGIN_TRANSCRIPT_CONTRACT=v2`
   silently produces `v1` output. The version is recorded, so the mistake is detectable
   after the fact, but nothing fails closed. Making `v2` mandatory for experiments that
   declare an ablation arm is the natural next step and is listed in the readiness report.
3. **Transport framing is measured only by the persona proof** — the closed-loop harness
   records the payload and the terminal capture, but no single artifact currently asserts
   their concatenation for every arm. That is the next measurement gap to close before a
   pilot.
