# Persona alignment — erratum and corrected evidence (2026-10-23)

**Supersedes the interpretation of:** `docs/research/persona_alignment_20261023T042600Z/`
**New evidence:** `docs/research/persona_alignment_20261023T052609Z/`
**Status:** `PARTIAL_ALIGNMENT` — prompts and four of five answers now align; two realism
defects remain (section 5). No hypothesis is supported or refuted by this document.

This document corrects a conclusion that was carried into
`docs/research/recovery_final_20261023T042900Z/FINAL_HANDOFF.md` ("Persona boundary").
It does not change any code path that the frozen artifacts depend on, and it leaves
every earlier artifact byte-identical. Where a previous statement is wrong, it is
retracted below and the bytes that contradict it are cited.

---

## 1. Retraction: the 04:26 run did not test the RAGIN arm at all

`persona_alignment_20261023T042600Z` recorded `webapp@web-srv-01:/$` for the RAGIN arm
and an empty answer for every command. That was read as "the frontend persona differs"
and "the deterministic generator has no strict-verifiable transcript". Both readings are
wrong for that run.

The RAGIN arm's generation requests were rejected before any response was produced:

```
persona_alignment_20261023T042600Z/ragin_server.log
  07:25:02  POST /v1/chat/completions  401
  07:25:05  POST /v1/chat/completions  401      (one per command, 5 total)

persona_alignment_20261023T042600Z/cowrie.ragin.log
  [HTTP11ClientProtocol,client] LLM API error (status 401): {"error": "unauthorized"}
```

An unauthenticated request and a fail-closed generator both render as an empty shell
response, so that run cannot distinguish them. **The blockers `answer:whoami`,
`answer:uname -a`, `answer:hostname`, `answer:cat /etc/os-release` and `prompt_cwd` from
that run are retracted as evidence about RAGIN behaviour.** They are preserved as-is in
the frozen directory; this erratum is the correction of record.

The run also predates the harness fix it was read against: its manifest records script
SHA-256 `7a084892…`, whereas the archived copy taken at 04:29 (`recovery_final_20261023T042900Z/source_bytes/scripts/`)
is `7307a8fe…` and does contain the `COWRIE_LLM_API_KEY` wiring. The wiring had therefore
been added but never exercised when the handoff was written. The file has since changed
again (patch mount, 401 gate, echo-aware parser); the hash of record for the evidence in
section 4 is the one stored in
`persona_alignment_20261023T052609Z/run_manifest.prelaunch.json`.

---

## 2. Confirmed defect: the LLM backend's cwd is hardcoded

Independent of the 401, the prompt mismatch was real and its cause is confirmed in the
pinned image (`sha256:710f1e46…`):

| Layer | Source | Behaviour |
|---|---|---|
| LLM backend | `llm/protocol.py:103` `self.cwd = "/"` | cwd is always `/`; prompt renders `/` |
| Native shell | `shell/honeypot.py` `showPrompt()` | cwd starts at `avatar.home`; renders `~` and `~/sub` |
| LLM avatar | `llm/avatar.py` `CowrieUser` | carries **no** passwd entry → no home to derive |

So the same declared persona necessarily showed two different prompts depending on the
backend. `COWRIE_HONEYPOT_BACKEND=llm` was therefore not representable as the native
persona without a patch.

### Fix

* `scripts/persona_prompt_patch.py` — the whole patch, as text replacement over the
  image's own file: cwd starts in the session home, the prompt renders `~` / `~/sub`.
  The upstream bytes are hash-pinned (`4cbc4408…`), every anchor must match exactly once,
  and the patched source is compiled before use.
* The patched file is bind-mounted read-only over
  `/cowrie/cowrie-git/src/cowrie/llm/protocol.py` **for the RAGIN container only**. The
  native arm stays byte-identical to the image, so the comparison stays a comparison.
* The LLM avatar has no passwd entry, so the persona home is supplied explicitly as
  `COWRIE_LLM_HOME` from `configs/ablation/persona_lab_v1/persona.json` and recorded in
  the run manifest (redacted env included).

---

## 3. Confirmed defect: deterministic templates disagreed with the strict contract

Once the 401 was fixed, two commands were still rejected — this time by the verifier,
for template reasons (`persona_alignment_20261023T052109Z`):

| Command | Candidate served to the verifier | Verdict |
|---|---|---|
| `hostname` | `webapp@web-srv-01:~$ hostname` / `bash: hostname: command not found` | `MISSING_EVIDENCE / SHELL_ERROR_TEXT` |
| `cat /etc/os-release` | echo, five lines, then `webapp@web-srv-01:~$ uname -r` and the kernel | `CLAIM_MISMATCH / UNEXPECTED_PROMPT_ECHO` |

Cause: `Hisoka._lookup_template` had no `hostname` branch (falling through to the
"command not found" fallback) and its os-release template appended a second prompt echo
and a `uname -r` block. The strict contract (`ragin/cycle/strict_research.py`) pins
`hostname` to the host and os-release to exactly five lines, so both templates could
never be served under `research_strict_v1`.

Fix (`ragin/hisoka/deception.py`): added `hostname`, `hostname -s`, `hostname -f`,
`uname`, `uname -s`, `uname -r` branches matching the strict contract, and reduced the
os-release transcript to the five pinned lines with no echo.

---

## 4. Corrected evidence — `persona_alignment_20261023T052609Z`

Two real loopback SSH sessions, five commands each, provider disabled, strict profile.

```
status                      PARTIAL_ALIGNMENT
reachability                {"llm_requests": 5, "unauthorized_401": 0, "authenticated": true}
prompt, native arm          webapp@web-srv-01:~$        (all five turns)
prompt, RAGIN arm           webapp@web-srv-01:~$        (all five turns)
patch                       4cbc4408… (image) -> b6efa7a0… (mounted, RAGIN only)
manifest                    33 files, FROZEN, hashes verified
```

| Command | Strict verdict | Native answer | RAGIN answer |
|---|---|---|---|
| `whoami` | `SUPPORTED / OUTPUT_MATCHES` | `webapp` | `webapp` |
| `id` | `SUPPORTED / OUTPUT_MATCHES` | `…groups=1001(webapp)` | `…groups=1001(webapp),4(adm),999(docker)` |
| `uname -a` | `SUPPORTED / OUTPUT_MATCHES` | same line | same line |
| `hostname` | `SUPPORTED / OUTPUT_MATCHES` | `web-srv-01` | `web-srv-01` |
| `cat /etc/os-release` | `SUPPORTED / OUTPUT_MATCHES` | five lines | five lines |

The gate that makes this interpretable: `llm_arm_reachability()` classifies the
container log, and a run with any `status 401` is now recorded as `INVALID` with an
`llm_arm_unauthenticated` blocker instead of answer-level blockers.

---

## 5. Remaining defects (not fixed here)

### 5.1 `id` supplementary groups — a constant B0-vs-RAGIN difference

Native Cowrie's `id` prints the primary gid only; the persona declares
`4(adm),999(docker)` and the RAGIN `id` line honours it. This is a real cross-arm
difference, but it is constant across every RAGIN arm, so it does not bias the
B1↔B2↔B3↔B4↔B5 contrasts the ablation protocol defines. It is covered by the protocol's
existing accounting for B0's architectural difference. **It was not changed**, because
narrowing the persona's declared groups would edit a frozen research fixture to match a
frontend handler limitation; that decision needs to be taken explicitly and versioned.

### 5.2 The served text duplicates the frontend's command echo

The honeypot frontend already echoes the typed command. Strict-profile transcripts
*also* begin with `prompt$ command`, because `_style_as_transcript` prepends one. Attacker
view from the run above:

```
webapp@web-srv-01:~$ whoami
webapp@web-srv-01:~$ whoami      <- duplicated, served text
webapp
```

This happens for 4 of 5 commands; `uname -a` is the exception (its answer is replaced by
the identity pin without an echo), so the duplication is also *inconsistent within one
session*. Both properties are detection signals and both affect realism ratings.

Not fixed here: `_style_as_transcript` is the shared transcript-shape contract used by
the deterministic and model paths and asserted by 14 checks in
`tests/unit/test_hisoka.py` and `tests/unit/test_credential_baits.py`. Removing the
redundant echo is a behaviour change that belongs in a deliberate, versioned revision of
that contract, not in a proof-harness repair.

---

## 6. Non-claims

* No B0–B3 comparison was run. Nothing here is evidence about deception effectiveness.
* Generation was deterministic (`provider=http://127.0.0.1:9`, `RAGIN_PROVIDER_ENABLED=0`).
  No model was loaded and no provider was called.
* Both sessions were loopback-only, in throwaway containers from a cached image
  (`--pull=never`), with proxy variables cleared. This is application-level isolation;
  the earlier, unverified claim that it is a network sandbox is not repeated.

## 7. Files touched by this erratum's work

| File | Change |
|---|---|
| `scripts/persona_prompt_patch.py` | new — hash-pinned prompt/cwd patch |
| `scripts/prove_cowrie_persona_alignment_v1.py` | patch mount, `COWRIE_LLM_HOME`, 401 gate, echo-aware parser, pre-launch env provenance, corrected expectations |
| `ragin/hisoka/deception.py` | deterministic templates aligned to the strict contract (`hostname*`, `uname*`, os-release) |
| `tests/unit/test_persona_alignment_v1.py` | patch, parser and reachability regressions (10 tests) |

Verification: `455 passed` across 11 focused suites (hisoka, credential baits, strict
profile, supported claims, persona alignment, verifier red-team, host fiction, strict
harness, runtime-truth P0, ablation retrieval modes, generation contract); Ruff clean on
all changed files.
