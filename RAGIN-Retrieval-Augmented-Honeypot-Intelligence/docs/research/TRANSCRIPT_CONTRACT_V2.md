# Transcript contract — normative specification

**Identifier:** `ragin.transcript_contract`
**Versions:** `v1` (legacy, default), `v2` (current for new experiments)
**Implementation:** `ragin/cycle/transcript_contract.py`, `ragin/hisoka/deception.py`
**Audit:** `docs/research/TRANSCRIPT_CONTRACT_AUDIT.md`
**Status:** v2 implemented and exercised end-to-end; adoption is opt-in (see §7)

---

## 1. Scope

This contract governs the **command echo** in an attacker-visible SSH turn: the
`user@host:~$ <command>` line. It does **not** govern banners, prompts or any other
transport framing, which belong to Cowrie.

## 2. Definitions

| Term | Definition |
|---|---|
| **PTY echo** | The bytes the attacker's terminal makes visible when they type. Produced by the frontend (Cowrie), not by RAGIN. |
| **Model draft** | Raw generator output, before RAGIN post-processing. |
| **Candidate** | The text RAGIN asks the verifier to clear. |
| **Served payload** | The exact string RAGIN returns to the frontend. This is what `served_response_sha256` digests. |
| **Attacker stimulus** | PTY echo + served payload, in that order, as captured by the terminal. |

## 3. Echo ownership

| Version | Owner of the echo | Server behaviour |
|---|---|---|
| `v1` | **server** (legacy) | Prepends `prompt$ command` when a command-shaped body carries no echo; rewrites a variant echo to the exact command; passes prose through bare. |
| `v2` | **frontend** | Never prepends. Removes exactly one leading line that is an exact echo of this command. Leaves every other byte untouched. |

`v2` is the correct model of a real shell: a command is echoed exactly once, by the
terminal.

## 4. Invariants

1. **Ownership is explicit.** Every serving trace carries
   `metadata.transcript_contract = {version, echo_owner, description, source, …}`.
2. **No silent normalization.** RAGIN MUST NOT rewrite, reorder, trim or re-wrap any
   output line of a served payload. Under `v2` the only permitted removal is a single
   leading exact echo line; under `v1` the only permitted rewrite is the echo line itself.
3. **Empty is a valid payload.** A silent command yields an empty payload; the frontend
   re-prints the prompt. Placeholders such as `(no output)` are forbidden.
4. **Error text is content.** `bash: <cmd>: command not found` and similar lines are
   preserved and are subject to verification, not stripped.
5. **Exactness of echo detection.** A line is an echo only if its command tokens equal the
   attacker's command after whitespace normalization. A prompt-shaped line for a different
   command is content.
6. **Provenance is never lost.** `model_draft_used`, `serving_outcome`, `template_id`,
   `candidate_sha256`, `served_response_sha256`, `served_response_bytes` and
   `served_text_scope="ragin_response_payload"` are recorded alongside the payload.
7. **Unknown versions fail closed.** `resolve()` raises `ValueError` for a value outside
   `{v1, v2}`. There is no silent fallback.
8. **Historical reproducibility.** `v1` remains byte-identical to the behaviour that
   produced the pre-2026-10-23 artifacts and remains the default.

## 5. Selection and recording

```
RAGIN_TRANSCRIPT_CONTRACT=v2      # any new experiment
unset / RAGIN_TRANSCRIPT_CONTRACT=v1   # historical reproduction
```

The version is resolved once per call, recorded in `metadata.transcript_contract`, and
also recorded by the proof harness in `run_manifest.prelaunch.json`
(`provenance.transcript_contract`) and in `summary.json` (`transcript_contract`).

## 6. Conformance tests

`tests/unit/test_transcript_contract_v2.py`:

1. default is `v1`; explicit and env values win; unknown raises;
2. `v1` still prepends, and leaves an existing echo untouched;
3. `v2` never prepends;
4. `v2` strips only an exact leading echo, and not one for another command;
5. `v2` preserves multiline output, error text and empty bodies;
6. five identical turns produce five identical echo-free payloads;
7. model post-processing strips a draft echo under `v2` and not under `v1`;
8. flag commands (`uname -a`, `ls -a`, `df -a`) are commands, not prose;
9. the serving trace records contract, echo owner, payload scope and byte count.

End-to-end: `scripts/prove_cowrie_persona_alignment_v1.py` runs under `v2` and fails the
run (`transcript_contract_violated`) if any served payload repeats the command or if any
turn lacks the frontend echo.

## 7. Migration and residuals

* No fixture, checkpoint or historical artifact is rewritten.
* Evidence produced before 2026-10-23 is `v1` and stays valid for what it measured; it must
  not be pooled with `v2` runs.
* Adoption is opt-in: a new experiment that omits the variable gets `v1` and is
  identifiable as such from the recorded version. Making `v2` mandatory when an ablation
  arm is declared is a pending enforcement change.
* Human raters must be shown the **attacker stimulus** (framing + payload), not the payload
  alone, or the echo question reappears as a rater artefact.
