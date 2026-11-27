# RAGIN V4 Cowrie Prospective Capture

## Runtime observed

The current process is the `ragin-cowrie-shield` Docker container running `cowrie/cowrie:latest`. Its observed JSON event stream is `/cowrie/cowrie-git/var/log/cowrie/cowrie.json`; the effective default configuration exposes SSH on `tcp:2222:interface=0.0.0.0` inside the container. Docker published ports were empty in the read-only inspection. No AWS or network change was made.

Observed events use `eventid`, `session`, and `timestamp`. The explicit close event is `cowrie.session.closed`; the usable input event is `cowrie.command.input`. The currently observed historical log contained nine session IDs and zero input events, so it cannot produce prospective eligible captures.

## Capture boundary

The isolated adapter groups only by the native Cowrie `session` field and preserves event order across all observed JSON rotation segments. It finalizes only after `cowrie.session.closed` and at least one usable input event. Stale-session recovery is disabled. Missing rotation fragments, malformed events, missing close events, and missing input fail closed.

Each finalized session is written atomically to a protected raw artifact, flushed and sealed read-only, then passed through the existing manifest, privacy, canonical-lineage, and append-only registry contracts. The deployment/native-session pair is idempotent. Historical events are excluded by the passive collector boundary and are never entered into the prospective registry.

Raw artifacts retain the exact ordered Cowrie events needed for provenance under the local protected capture root. Study-facing canonical and registry artifacts redact source IPs and credential material; a source cluster is derived in memory with the existing keyed HMAC mechanism when a study secret is supplied. The secret is not serialized.

## Validation

The focused suite passed 39 tests. It covers native start/input/close, multi-command sessions, repeated commands across distinct sessions, close gating, rotation and missing-fragment failure, duplicate finalization, raw/manifest/canonical tamper checks, privacy and credential minimization, HMAC stability, parser grouping, lineage, atomic artifact cleanup, fixture exclusion, and deterministic re-entry after raw sealing or manifest creation. The representative Cowrie-format dry run passed with zero eligible real sessions and no network access.

The existing 40 controlled-admin captures were reverified without mutation: 40/40 raw hashes, 40/40 manifest hashes, 40/40 canonical hashes, and 40/40 lineage checks passed.

## Passive operation

After the integration freeze, the watcher observes only the existing container log through read-only `docker exec`/`docker cp` operations. It does not alter Cowrie, networking, AWS, or ports; it does not invoke any V4 policy; and it ignores sessions whose first event predates its start boundary. The current historical log therefore contributes zero honeypot captures unless a new native session arrives and satisfies the complete contract.

The prospective pool remains 40 controlled-admin captures plus zero controlled-honeypot captures. The remaining target is 220, and no additional controlled-admin captures are permitted.

## Scientific boundary

No V4 arm, Evidence Gate evaluation, reference annotation, or effectiveness analysis was run. Fixture events and historical Cowrie logs were not counted as real evidence. AWS and public network exposure were unchanged.
