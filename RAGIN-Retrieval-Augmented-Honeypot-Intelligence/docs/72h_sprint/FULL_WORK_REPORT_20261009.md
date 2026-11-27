# RAGIN 72-Hour Sprint: Full Work Report

Date: 2026-10-09  
Repository: `RAGIN-Retrieval-Augmented-Honeypot-Intelligence`  
Scope: controlled local/provider staging, evidence production, and safe AWS inspection  
Status: **PARTIAL — local provider-backed staging verified; AWS private deployment and public exposure remain blocked**

## 1. Executive summary

The main implementation milestone completed in this work period was replacing
the active APMix-generation selector in the local staging path with a
loopback-only bridge around the installed OpenCode CLI. The bridge uses a
restricted deny-all tool profile and exposes only an OpenAI-compatible local
HTTP interface to the RAGIN process. No provider secret was written to the
repository or transmitted to AWS.

The replacement path was validated in three layers:

1. A bounded provider-backed completion using `opencode/space-bunny-free`.
2. A local `server_v2` request through Chrollo, Don, Hisoka, mandatory
   deterministic verification, and accepted state commit.
3. An isolated local Cowrie container request reaching the same serving path
   and returning a verifier-approved SSH-visible response.

A separate bounded benchmark completed with three sessions and zero pipeline
errors. Two cases were `GENERATED_VERIFIED`; one persona case used the
explicit `TEMPLATE_FALLBACK_VERIFIED` path. The fallback case is not counted
as model-generated output.

The AWS instances were not mutated during this phase. The existing AWS CORE
runtime remains intentionally fallback-only because the local OpenCode bridge
was not made a permanent private AWS dependency. CORE still has its historical
public address and public-subnet placement, and the existing root volumes
remain unencrypted. No public honeypot or public RAGIN listener was opened.

## 2. Work completed

### 2.1 OpenCode provider bridge

Implemented and tested:

- `scripts/opencode_proxy.py`: loopback-only OpenAI-compatible bridge.
- `scripts/opencode_cli_bridge_safe_config.json`: deny-all tool profile for
  the delegated OpenCode agent.
- Child-process filtering that prevents legacy provider/API environment names
  from being inherited by the OpenCode process.
- Free-model selection with `opencode/space-bunny-free` as the active local
  selector.
- Safe handling of provider failure, unavailable models, and bounded request
  execution.

The bridge was bound to `127.0.0.1:8731` only. It was stopped after testing.
No public or AWS-facing bridge listener was created.

The active configuration examples now use:

```text
RAGIN_LLM_BASE_URL=http://127.0.0.1:8731/v1
RAGIN_LLM_MODEL=opencode/space-bunny-free
BENCH_ENGINE_MODEL=opencode/space-bunny-free
```

The field configuration retains a placeholder for a future approved private
bridge rather than pretending that the local loopback bridge is reachable from
AWS. Historical APMix references and historical evidence were preserved; they
were not relabeled as OpenCode results.

### 2.2 Real provider-backed completion

The configured historical DeepSeek selector was not present in the observed
provider catalog and was not called. The alternate OpenCode model
`opencode/space-bunny-free` completed a bounded request under the deny-all
profile.

Observed local probe:

| Field | Result |
|---|---|
| Provider path | OpenCode CLI through local loopback bridge |
| Model | `opencode/space-bunny-free` |
| Result | Successful completion |
| Elapsed time | Approximately 6.2 seconds |
| Output tokens | 10 |
| Reported cost | 0 by the local/provider response metadata |
| Billing conclusion | Not independently guaranteed; no paid model was selected |

The result was passed through the mandatory RAGIN verifier. The provider
completion was not treated as authoritative merely because it returned HTTP or
text; only the accepted serving path could produce a visible response.

### 2.3 Local RAGIN serving path

The local `server_v2` pipeline was run with the OpenCode bridge and processed:

```text
echo SPACE_BUNNY_PIPELINE_PROBE
```

Observed result:

- Session: `ses-872e6679aaf6466e`
- Serving path: `GENERATED_VERIFIED`
- Verifier: `FictionConsistencyVerifier`
- Verification: passed and accepted
- State commit: accepted after verification
- Candidate digest: `93612c9609b931a3a206362632e108f742b58ffecbe40f7fe72d226e7a8a1157`

This is local controlled staging evidence. It is not evidence that the current
AWS CORE instance has permanent provider connectivity.

### 2.4 Isolated Cowrie integration

The local Cowrie test used a pinned image digest and a constrained Docker
bridge network. It did not use host networking and did not publish a public
port.

Controls exercised:

- No host Docker socket mount.
- No privileged mode.
- Dropped capabilities.
- `no-new-privileges`.
- Read-only root filesystem.
- Bounded memory, CPU, and PID limits.
- Local-only test listener.
- Temporary bridge-subnet firewall exception removed after testing.
- Host SSH, metadata, and arbitrary external connectivity denied from the
  container test path.

Controlled command:

```text
true
```

Observed result:

- Cowrie session: `ses-7d4b10c6af0c4475`
- SSH-visible output: `webapp@web-srv-01:~$`
- Serving path: `GENERATED_VERIFIED`
- Verifier: `FictionConsistencyVerifier`
- Verification: passed and accepted
- Candidate digest: `ad6289a471e2af8418db17b29a2e794995534a2985ad93f8417c9b3e82f63939`
- Field export: written to the temporary test location

This demonstrates the local Cowrie-to-RAGIN generated-serving path. It does
not authorize public Cowrie exposure and does not prove that AWS EDGE can
reach an OpenCode provider without an approved private transport.

### 2.5 Provider-backed benchmark

Command:

```text
.venv/bin/python scripts/run_live_benchmark.py \
  --limit 1 \
  --engine graph \
  --report results/overnight_20261009/opencode_provider_limit1.json
```

Results:

| Suite | Cases | Score | Serving path | Latency |
|---|---:|---:|---|---:|
| CTI technique | 1 | 0.850 | `GENERATED_VERIFIED` | 71,910 ms |
| CTI actor | 1 | 0.850 | `GENERATED_VERIFIED` | 8,916 ms |
| Persona realism | 1 | 0.800 | `TEMPLATE_FALLBACK_VERIFIED` | 9,516 ms |

Run-level metrics:

- Total sessions: 3.
- Sessions with engagement: 3.
- Pipeline errors: 0.
- Total elapsed time: 90.36 seconds.
- Average response time: 30,114 ms.
- Deception artifacts deployed: 3.
- Deception artifacts accessed: 0.
- Unique TTPs detected: 1.

The persona case is explicitly separated from the two provider-backed cases.
The benchmark scores are not independent attacker labels, human evaluations,
or field-effectiveness evidence. The sample is intentionally bounded and is
not statistically sufficient for broad research claims.

### 2.6 Research measurement boundary

The earlier fallback benchmark reported CTI scores that could be derived from
the internal Don analysis channel. The scorer audit showed that these values
must not be presented as evidence of successful generative deception or
independent attacker behavior. The new report preserves the serving path for
each case so generated and fallback outputs remain distinguishable.

No public observations, human attacker labels, or independent ground truth
were collected.

### 2.7 AWS inspection and safety boundary

The existing AWS state was read through the configured AWS CLI and previously
validated SSH/SSM channels. No cloud mutation was performed in this work
period.

Current relevant state:

- Existing RAGIN-CORE and RAGIN-EDGE instances remain the only project compute
  resources.
- Both existing instances remain administratively reachable through SSH and
  SSM according to the latest live readback.
- CORE remains public-addressed and on an internet-routed subnet.
- CORE application staging is private-bound and authenticated, but the host is
  not a private-subnet deployment.
- The prepared private subnet, local route table, and EIC management endpoint
  remain available for a future approved cutover.
- Existing root EBS volumes remain unencrypted.
- Existing dedicated security-group egress remains broader than the final
  desired allowlist.
- No public Cowrie port, RAGIN API, NAT gateway, paid VPC endpoint,
  replacement instance, snapshot, or replacement volume was created in this
  phase.
- The attempted AWS reverse-tunnel route was rejected by the hardened SSH
  forwarding policy before a remote listener was created. No SSH policy was
  weakened.

The current AWS CORE runtime is therefore not reported as provider-backed.
Its safe fallback behavior remains the deployed AWS behavior.

## 3. Validation performed

### Passed in this work period

- OpenCode proxy unit and integration selection suite: **59 passed**.
- `scripts/opencode_proxy.py` compilation: **passed**.
- New evidence JSON validation: **passed**.
- `docker compose --env-file .env.example config --quiet`: **passed**.
- `docker compose --env-file .env config --quiet`: **passed**.
- `git diff --check`: **passed**.
- Provider-backed benchmark: **completed with 0 pipeline errors**.
- Temporary listener check: **no `8731` or `8843` listener remained**.
- Local server_v2 provider-backed serving: **passed**.
- Local isolated Cowrie provider-backed serving: **passed**.

### Earlier evidence retained, not rerun here

- Full Python suite: 1,645 passed, 116 skipped, 34 warnings.
- mTLS positive and negative identity cases.
- Session persistence across restart.
- SSM and EIC management checks.
- Container isolation checks for host SSH, IMDS, and arbitrary external
  connectivity.
- Deterministic fallback benchmark with three sessions and zero errors.

These earlier results remain historical evidence and were not silently merged
with the new provider-backed benchmark.

## 4. Cost and resource impact

AWS impact for this work period:

- New AWS resources: none.
- AWS instance replacement: none.
- EBS/snapshot operations: none.
- NAT gateway or paid interface endpoint: none.
- Public IP allocation: none.
- Public listener activation: none.
- AWS cost caused by the local benchmark: none observed.

The inspected Cost Explorer range reported zero unblended daily usage, but
that is not proof of remaining credit balance, delayed billing, or future zero
cost. The provider response reported zero cost for the selected free model, but
that is also not an account-level billing guarantee.

## 5. Files produced or updated

Primary implementation:

- `scripts/opencode_proxy.py`
- `scripts/opencode_cli_bridge_safe_config.json`
- `tests/unit/test_opencode_proxy.py`
- `.env.example`
- `.env.field.example`
- `docker-compose.yml`

Primary evidence:

- `results/overnight_20261009/opencode_provider_limit1.json`
- `docs/72h_sprint/evidence/opencode_provider_benchmark_20261009.json`
- `docs/72h_sprint/evidence/opencode_cowrie_local_e2e_20261009.json`
- `docs/72h_sprint/evidence/opencode_space_bunny_e2e_20261009.json`

Updated sprint records:

- `docs/72h_sprint/REAL_GENERATION_VALIDATION.md`
- `docs/72h_sprint/NEW_BENCHMARK_RESULTS.md`
- `docs/72h_sprint/GENERATIVE_E2E_RESULTS.md`
- `docs/72h_sprint/EXPERIMENT_PROVENANCE.md`
- `docs/72h_sprint/OVERNIGHT_STATUS.md`
- `docs/72h_sprint/RUNNING_SERVICES.md`
- `docs/72h_sprint/SPRINT_STATUS.md`
- `docs/72h_sprint/AWS_COST_LEDGER.md`
- `docs/72h_sprint/MORNING_HANDOFF.md`

Historical research data, prior APMix/JEV/OpenCode measurements, manuscript
results, and unrelated dirty-worktree changes were preserved.

## 6. Remaining blockers

### P0/P1 infrastructure blockers

1. CORE is still public-addressed and not in the prepared private subnet.
2. Existing CORE and EDGE root volumes remain unencrypted.
3. A permanent private provider path for AWS CORE is not deployed.
4. Final dependency-specific egress restrictions are not fully implemented and
   tested.
5. Durable protected telemetry and a complete emergency-isolation rehearsal
   remain incomplete.
6. Rust gateway authentication remains unresolved and it is outside the active
   serving dependency path.

### Research blockers

1. Laya has only a provider-neutral, fixture-tested optional adapter; no real
   Laya inference result is claimed.
2. The new provider benchmark is small and controlled; it cannot support
   attacker-effectiveness or broad generative-quality claims.
3. Matched ablations and larger reproducible runs remain to be executed.
4. No public field pilot or unsolicited attacker collection occurred.
5. Ethics, privacy, and organizational review remain prerequisites for field
   collection.

## 7. Required next approvals

The smallest remaining approval packet is:

1. Approve or reject a costed replacement CORE cutover with encrypted root
   storage and private-subnet placement, retaining the current CORE for
   rollback.
2. Approve the permanent private authenticated provider transport, or accept
   fallback-only AWS operation.
3. Approve the final egress rule change only after its DNS, SSM, update,
   management, and service dependencies are tested together.
4. Separately approve any public Cowrie exposure after the complete safety,
   ethics, privacy, and emergency-isolation gates pass.

No approval is requested here for destructive operations, termination, public
exposure, account-plan changes, or paid inference.

## 8. Final disposition

**PARTIAL — CONTROLLED LOCAL PROVIDER-BACKED STAGING VERIFIED.**

The local RAGIN application can now use a real OpenCode CLI-backed completion,
route it through mandatory deterministic verification, and expose an accepted
response through an isolated local Cowrie session. The benchmark cleanly
separates generated and fallback outcomes.

The project is not yet a private AWS deployment and is not ready for public
honeypot exposure. The current safe next step is the costed private/encrypted
CORE decision and, independently, the controlled research evaluation work that
does not require public exposure.

Task 4 must not start automatically.
