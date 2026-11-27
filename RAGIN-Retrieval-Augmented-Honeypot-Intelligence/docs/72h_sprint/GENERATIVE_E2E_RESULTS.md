# Generative End-to-End Results

## Provider-backed path

The current OpenCode local controlled path is:

`OpenCode CLI -> loopback bridge -> local server_v2 -> Chrollo/Don/Hisoka -> mandatory verifier -> accepted state`.

For session `ses-872e6679aaf6466e`, `echo SPACE_BUNNY_PIPELINE_PROBE`
returned `SPACE_BUNNY_PIPELINE_PROBE` using `opencode/space-bunny-free`.
The audit record contains `GENERATED_VERIFIED`,
`FictionConsistencyVerifier`, `passed=true`, `accepted=true`, and candidate
digest `93612c9609b931a3a206362632e108f742b58ffecbe40f7fe72d226e7a8a1157`.
The deny-all OpenCode agent was active. This run was local and loopback-only;
it did not expose AWS or Cowrie publicly.

The controlled flow was:

`SSH test client -> Cowrie 3.1.1 -> EDGE internal bridge -> EDGE mTLS forwarder -> CORE -> Chrollo/Don/Hisoka -> mandatory verifier -> Cowrie output`.

For session `ses-46a0642581094765`, the command `echo generated42` produced a provider-backed candidate using `claude-sonnet-4-6-free`. CORE committed and served it only after `FictionConsistencyVerifier` passed. The candidate digest was `470489c8ce7da2ba6b722652559fdb903a3781c2cee9fc8239c2b610a50c8736`, and the final text was observed in the controlled SSH session.

## Current isolated Cowrie/OpenCode result

The current provider-independent-of-APMix path was exercised through a
loopback OpenCode CLI bridge and an isolated local Cowrie 3.0.15 container.
There was no host port publication. Command `true` produced the visible
response `webapp@web-srv-01:~$`; session `ses-7d4b10c6af0c4475` recorded
`GENERATED_VERIFIED`, deterministic `FictionConsistencyVerifier` acceptance,
and candidate digest
`ad6289a471e2af8418db17b29a2e794995534a2985ad93f8417c9b3e82f63939`.
The container used bridge networking, bounded resources, read-only root,
dropped capabilities, and no-new-privileges. The temporary local firewall
exception was removed after the run.

This is the strongest current real-generation Cowrie evidence, but it is
local controlled staging. The AWS CORE process still uses disabled-provider
fallback because the hardened SSH server rejects the temporary reverse
tunnel needed to connect it to the workstation bridge.

## Fallback and provenance regression

After the provider test, credentials were removed and the safe fallback runtime was restored. A separate `whoami` session recorded `TEMPLATE_FALLBACK_VERIFIED`, `passed=true`, and an accepted commit. A serving provenance defect that previously hardcoded `GENERATED_VERIFIED` was corrected in `ragin/cycle/harness.py`, covered by `test_candidate_provenance_label_survives_commit`, and deployed in image `ragin-staging:20261009`.

## Limits

This is one current local OpenCode provider-backed generation, one current
isolated local Cowrie/OpenCode run, one historical controlled Cowrie/provider
flow, and a bounded fallback campaign, not a broad
effectiveness evaluation. The configured DeepSeek model was unavailable in
the catalog, Laya was not used, and no public attacker observations were
collected. Evidence is redacted and names the exact session, provider
identity, verifier, and candidate digest without storing secrets.
