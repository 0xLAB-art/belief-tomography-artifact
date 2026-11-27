# RAGIN Task 3: Field Telemetry and Privacy Plan

**Status:** design only. Public field collection requires ethics/organizational approval and live containment evidence first.

## Collection boundary

The study distinguishes public attacker observation from controlled synthetic benchmarks. The latter must never be presented as Internet attacker evidence. Historical benchmark artifacts and JEV/OpenCode results remain unchanged and are not relabeled by this plan.

## Minimum event envelope

CORE should retain a versioned, append-only decision record containing:

```text
event_schema_version
session_id / host_identity_id (pseudonymous)
request_id, timestamp, service_identity
incoming command digest and bounded command content where approved
classification and retrieval provenance
candidate digest, generator/model/version, prompt-template version
verifier policy/version, checks, decision, rejection reason
retry number, fallback transition, HITL decision
state commit result and fiction/host-state version
response digest, serve_path, transport result
error class and shutdown/isolation marker
```

Store raw source addresses only on the controlled endpoint for the minimum operational period. The existing ethics plan says collection hashes source IPs and retains raw endpoint logs for 30 days (`docs/FIELD_ETHICS.md:26-35`); that policy must be implemented and access-controlled before collection. Raw addresses must not enter prompts, retrieval corpora, published artifacts, or ordinary operator dashboards.

## Redaction and minimization

1. Hash or keyed-pseudonymize source addresses at collection export with a rotation/retention decision documented in the protocol.
2. Truncate timestamps to the analysis resolution unless incident response requires finer precision.
3. Strip cookies, authorization headers, real credentials, tokens, private keys, email addresses, and unrelated personal data from exports.
4. Treat attacker-uploaded files and command output as untrusted content. Preserve a cryptographic digest and metadata before retaining a sample; do not execute samples.
5. Keep raw evidence, redacted research exports, and derived benchmark tables in separate access-controlled stores.
6. Encrypt EBS and backups, restrict operator access by role, and log reads/exports of raw evidence.

## Retention and deletion

| Dataset | Proposed retention | Access |
|---|---:|---|
| Raw EDGE session/log data | 30 days unless an approved incident hold exists | Two-person or named operator access; no publication |
| Redacted session export | Analysis period plus publication/audit period | Research team, least privilege |
| CORE decision/audit records | At least through artifact freeze and review; exact period requires ethics approval | Protected audit role only |
| Synthetic benchmark inputs/results | Per reproducibility manifest; immutable historical artifacts | Research repository/artifact store |
| Backups | Encrypted, same policy as source; verified restore before deletion | Storage administrators only |

Deletion must be recorded as a manifest event. Do not delete evidence merely to reduce cost before the approved retention date.

## Ethics and review gates

Before any public listener: complete the ethics/IRB or waiver determination, disclosure language, data minimization review, no-retaliation rule, containment review, and operator access plan. `docs/FIELD_ETHICS.md:1-5,39-55` is a draft and explicitly says it must be completed before a public endpoint goes live.

## Tamper evidence

Use hash chaining or signed manifests for exported records, separate the signing key from the ingest host, and retain a protected copy. A successful local JSONL write or Docker log rotation is not tamper evidence. Task 2's field export remains best-effort (`docs/task2/STATE_TRANSACTION_AUDIT.md`); this plan does not claim durable AWS audit storage exists.

