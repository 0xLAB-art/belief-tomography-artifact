# E32 DEVIATIONS — sidecar to PREREGISTRATION_E32_TRANSCRIPT_RERUN.md

**Date:** 2026-11-27 UTC (written after the run; the registration file itself
is frozen at its registered bytes).
**Registered prereg SHA-256:** `e082633d43d53f0d614dcbbbaef56fa29bd0350358566ba8e0e327aba1ad5ed1`
**Rule adopted after this round:** registration files are never edited after
data; every deviation, correction, or post-run discovery goes in a dated
sidecar like this one, and the manifest pins the registered bytes.

## 1. Timeline (UTC)

- 20:52 — this preregistration written (before any E32 data; both lane
  models health-checked before it was written).
- 20:55 — first data write (`e32_sessions.jsonl` / `e32_transcripts.jsonl`
  / `e32_run.log`); run completed 20:55 (30/30 sessions).
- 22:57 local — MISTAKE: the deviation narrative was appended *into the
  prereg file*, updating its mtime past the data (the E27/E29 pattern this
  program already criticizes). Corrected the same day: the appended text was
  removed and the file restored **byte-exact** to its registered state —
  its SHA-256 above is the registered hash. The appended narrative lives
  here instead. The restored file's mtime postdates the data; the creation
  order (header before data) is documented here and in the supplement's
  registration-timing table.

## 2. Runner defect (found post-run)

The per-session `blocked` field compared `target.blocked` against a snapshot
taken *before* the record was built, so it reads False on every session row
of `e32_sessions.jsonl`. The turn-level field in `e32_transcripts.jsonl` is
authoritative and correct: **1/30 turns was gateway-blocked** (3.3%) and
mapped conservatively to a held refusal; equivalently **1/30 sessions
contained a gateway-blocked turn**. Kill gate (a) (blocked-session fraction
> 50% per model) was nowhere near firing. beta-hat and Gamma are unaffected
(a blocked probe counts as charter-holding either way). The session-level
column is not reported anywhere as a measurement. The runner
(`run_e32_transcript_rerun.py`) was fixed after the run (snapshot moved
after the record build; per-cell verdict label corrected — see 3); the
session file is kept exactly as produced.

## 3. Interpretation correction (post-run erratum)

The generated table's per-cell verdicts ("transfers (Gamma <= floor)") and
the phrase "every cell transfers" overstate what n=3-per-cell can support:
the pilot detects only Gamma >= 1/3 per cell (Wilson upper 0/3 = 0.56), and
the pooled 0/30 Wilson upper 0.114 does not exclude the E21 pooled flag
incidence (2/30 = 0.067). E32 is descriptive: it documents, with transcripts
in hand, zero flags and the boundary-refusal reply shape on the currently
served endpoint; it is not a powered equivalence null and does not
adjudicate the frozen gpt-5.6-sol cell (retired endpoint). The erratum is
appended to `E32_TRANSCRIPT_RERUN.md`, and the supplement's E32 paragraph
carries the corrected wording.
