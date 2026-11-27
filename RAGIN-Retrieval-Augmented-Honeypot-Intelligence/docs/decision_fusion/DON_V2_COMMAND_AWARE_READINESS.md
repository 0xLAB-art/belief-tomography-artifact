# Don V2 Command-Aware Threat Intelligence

Status: `DON_V2_READY`

This is a versioned, opt-in retrieval implementation for Linux/SSH command
inputs. The historical Don path remains the default. No V4 policy, Evidence
Gate threshold, Hisoka implementation, frozen holdout, or historical result
was changed.

## Corrected defects

The legacy path constructs a query from a classification value, observed
techniques, and only the first five commands. In offline mode it performs
BM25 search over the broad `mitre_attack.jsonl` corpus while the dense vector
path is disabled. This allowed generic ATT&CK documents to dominate and did
not retain a command-aware relevance trace. Don V2 uses the complete bounded
preceding-command context, current command, static features, exact command
patterns, lexical scoring, behavior overlap, deterministic reranking, and a
session/context-bound cache key.

## Command analyzer coverage

The analyzer is static and treats all shell text as inert data. It records
executable names, arguments, shell operators, path categories, discovery,
credential, persistence, download, and execution indicators, download-to-
execution relationships, parse state, and ambiguity. It does not execute
commands, resolve paths, fetch URLs, or infer malicious intent.

## Corpus

The additional corpus contains 18 command-grounded records derived from the
existing local MITRE ATT&CK STIX export. Technique documents cover Unix shell,
account, service, file, system, network, credential, transfer, SSH, deletion,
cron, and systemd behavior. Five documented relationship records are included
when available for download, SSH, credential, and persistence patterns.

Each record retains source URL or source identifier, local source revision,
retrieval date, license/permission metadata, evidence ID, command patterns,
behavior tags, supported technique IDs, and a provenance hash. The original
MITRE corpus is unchanged. No new network retrieval was performed in this
implementation.

## Development validation

The nine frozen synthetic fixtures cover benign administration,
reconnaissance, file inspection, download, credentials, persistence,
multi-command continuity, malformed/ambiguous input, and irrelevant input.
Rule-based oracles were used for command-specific retrieval, ambiguity,
download/execution continuity, and irrelevant-evidence rejection.

Results:

- New Don V2 tests: 10 passed, 0 failed.
- Focused existing Don/V4/generator/wiring tests: 109 passed, 0 failed.
- Actual DonAdapter evidence bundle: command-aware trace exported and
  accepted by the existing Evidence Gate on relevant synthetic evidence.
- Irrelevant synthetic input: rejected as `NO_EVIDENCE`.
- External generation calls: 0.
- Attacker commands executed: 0.
- Cache leakage: not observed; session and full context are in the cache key.
- Mandatory verifier/HITL implementation: unchanged and outside this retrieval
  change.

The broad `tests/unit tests/security` invocation also produced 1,717 passes,
22 unrelated pre-existing failures, and 10 fixture/dependency errors. The
failures concern missing `mem0`, missing gateway/TTP fixtures, existing Laya
label residue, and an existing verifier-oracle condition. They are not
included as Don V2 failures and were not modified.

## Exact freeze

Freeze directory:

`results/decision_fusion_v4/don_v2_command_aware/`

- `don_v2_freeze_v1.json` SHA256:
  `703013c412e8ba1e1e7f000c8a46e1baf958485aea6fb78e38329ee64a7e36b9`
- `sha256_manifest.json` SHA256:
  `b97f49b07b428bb1684ecec908b21fa6a383bc2266675e827b08e642df6df142`
- `don_v2_development_validation_v1.json` SHA256:
  `00903245b0a2f1d6011a140dad820109c8629eb2975036290fa9ca0d5612b25b`
- command-aware corpus SHA256:
  `d1a2f015eae91c91702fa9ccc5cdbdb8a074d7cb05e62d93208a30919cb242f4`

The primary source hashes are recorded in the manifest. Important unchanged
protected paths at freeze are:

- `ragin/decision_fusion_v4/policy.py`:
  `9d3862d13ab3c5679b80935e37d3ff4ee0795fa56a95f28a56c58074d7e1261d`
- `ragin/decision_fusion_v4/benchmark.py`:
  `eb8285576733eb88b23194aaca82355b41f422e9d61219a424911ff98e7dcb35`
- `ragin/hisoka/strategy_generator_v1.py`:
  `3c1e0c9f85510adc17758c4f4aded547c57fca8c7aa69fea209790315fdbdae2`
- `ragin/cycle/verifier.py`:
  `317095714829be1d02ae78c2c445ca743ebd20c220c97132119007d8468e28f3`

## Limitations and blockers

This is development readiness, not an effectiveness evaluation. The added
corpus is a small derived corpus, not a newly independently curated Linux/SSH
threat-intelligence release. Its ATT&CK technique relationships remain source
claims, not ground truth for individual commands. The analyzer preserves
ambiguity and does not infer intent. No new 720-case evaluation is authorized
or included. The missing optional dependency and unrelated fixture failures
remain repository-level regression limitations.
