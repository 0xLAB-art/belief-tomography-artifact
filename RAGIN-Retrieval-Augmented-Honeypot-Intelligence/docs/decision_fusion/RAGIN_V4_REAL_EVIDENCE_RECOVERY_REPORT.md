# RAGIN V4 Real-Evidence Recovery Report

## 1. Why the first 240 were rejected

The previous 240-record selection was preserved but rejected before execution because record-level natural or controlled capture lineage could not be established. The records are structurally distinct provenance-unresolved derived session records, not a verified real holdout. No V4 arm, gate, policy, generator, verifier, reference annotation, or effectiveness analysis was run.

## 2. Structural uniqueness is not real provenance

Unique event-sequence, context, and file hashes establish that records differ as repository artifacts. They do not establish that an artifact originated in a naturally collected or controlled real session. Eligibility therefore requires an upstream raw capture, native session identity, or explicit documentary capture chain.

## 3. Existing source audit

`data/sessions/` is a RAGIN-derived event export with session IDs and timestamps but no resolvable raw capture parent, deployment identifier, source offset, or capture manifest. It remains `DERIVED_WITH_UNTRACEABLE_PARENT` and contributes zero verified groups.

`data/cowrie_logs/` contains timestamped native Cowrie session events with source-file hashes and session identifiers. Repository field documentation describes Cowrie as the controlled honeypot source. A metadata-only reconstruction yields one candidate per native Cowrie session with at least one input event.

`data/field/` is documented as passive field collection, but the current export has session IDs and timestamps without an attacker-input event or linked raw capture identifier. It is real-source evidence in provenance terms but unusable for the required canonical evaluation input contract.

`data/real_linux_transcripts.json` is documented as 12 genuine sessions recorded by `scripts/capture_real_linux_transcripts.py` on a real Linux host. The capture script documents fixed read-only command execution and real command output. These are controlled real administration records, not attacker sessions; their per-record native session IDs and capture timestamps are unavailable.

## 4. data/sessions lineage recovery

All enumerated records were checked structurally for native session identifiers, timestamps, and record hashes. No pre-existing manifest or raw source parent was found. The recovery therefore records the unresolved derived status rather than promoting the records based on their filenames or content shape.

## 5. Cowrie reconstruction feasibility

Reconstruction is feasible without semantic selection. The frozen rule is one case per native Cowrie session, selecting the final non-empty `cowrie.command.input` in deterministic timestamp/source-file/line order. Three native sessions lacked such an event and were excluded from the canonical candidates. Candidate provenance includes native session ID, event timestamps, source-file identities and hashes, complete event-sequence hash, and documented controlled-honeypot origin.

## 6. Field-record recovery

The field export cannot currently provide the required attacker/operator input contract. No input field is invented and no field record is forced into the pool. A future capture manifest must preserve native raw input events and their parent linkage.

## 7. Controlled-admin provenance

The real Linux transcript artifact is linked to the documented capture script and preregistered statement that 12 genuine sessions were recorded on a real Linux host. Each record is hashed and tied to its array index and source artifact hash. Missing per-record capture identifiers are recorded as limitations, not silently fabricated.

## 8. Existing verified pool size

The recovered pool contains 25 defensible independence groups: 13 controlled real honeypot Cowrie groups and 12 controlled real administration groups. No holdout is selected from this pool.

## 9. Remaining provenance gap

The pool is below both the final target of 240 and the minimum authorization threshold of 180. The V4 real study is therefore blocked. The original 240 selection remains historical and rejected.

## 10. Prospective collection contract

A provenance-from-birth contract is frozen for future acquisition. Each native capture must receive a capture ID, native session ID, source class, collector version, deployment/environment ID, start/end timestamps, raw-log path and SHA256, event and input counts, null parent for native captures, explicit non-synthetic/non-replay/non-fixture flags, and a pre-evaluation capture-manifest hash. One native capture session is one independence group. The acquisition target is 260 groups to preserve replacement headroom; the final holdout target remains 240 and the minimum authorization threshold remains 180.

## 11. Scientific boundary

This recovery used only source, structural, documentary, and cryptographic metadata. No security labels, V4 outputs, gate outputs, policy outputs, Hisoka responses, verifier outcomes, reference labels, or effectiveness metrics were inspected or generated.
