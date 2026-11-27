# Scientific Conclusion — Laya Independent Value

## Verdict

**INCONCLUSIVE — insufficient independent evidence.**

This is the current honest conclusion. The engineering integration exists, but the
independent labeled experiment does not yet exist.

## What is established

- Laya performs real local inference and the optional assessment seam is
  integrated into the active Chrollo path.
- `server_v2` now has a minimal first-class Laya config surface: default OFF,
  explicit opt-in, invalid values fail safe, and no second serving path is added.
- Focused regression tests for the new server_v2 Laya config surface pass in this
  session.
- An expanded independent candidate pool and blinded annotation package now exist,
  with rater templates for r1, r2, r3, and a pre-agreed adjudication contract.
- A frozen prediction/evaluation skeleton exists and can accept later labels
  without changing prediction logic.
- A gating preregistration artifact exists and was written before human labels
  were available.

## What is NOT established

- No independent human labels exist yet.
- The independent candidate pool remains below the intended 100–150 target, even
  after expansion.
- Cowrie provenance is not independent malicious/benign ground truth.
- Real-linux provenance is not independent benign ground truth.
- Many session-file candidates contain informational or advisory prompts rather
  than executed attack activity, so provenance alone is insufficient for class.
- Therefore no claim that Laya provides independent decision value beyond Chrollo
  is justified yet.
- Therefore no claim that Laya's latency cost is justified is justified yet.

## Test integrity note

In this session, bare pytest reports non-zero exit when tests fail. The main unit
suite has failures and exits non-zero. Some sub-suites pass and exit 0. The
unrelated verifier oracle failure is confirmed pre-existing and was not fixed here
just to obtain green output.

## Conditional verdict framing

- RETAIN — would require measurable independent value.
- RETAIN CONDITIONALLY — would require independent evidence that selective
  invocation produces enough value to justify cost.
- DROP — would require independent evidence that cost exceeds measurable value.
- INCONCLUSIVE — current state.

Current state is **INCONCLUSIVE**.

## Recommended next legitimate step

Collect real human labels for the blinded packet, validate rater files,
compute agreement, adjudicate, freeze the held-out set, and then run the frozen
Chrollo/Laya evaluation under the preregistered conditional gate. Only then can
the verdict move off INCONCLUSIVE.
