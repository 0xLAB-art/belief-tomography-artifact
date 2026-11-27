# Running Services

Latest verified checkpoint: 2026-10-09T04:48:17Z.

Observed 2026-10-08 UTC. This is a staging inventory, not public-deployment approval.

| Host | Service | Binding | State | Notes |
|---|---|---|---|---|
| CORE | `ragin-core-staging` | `172.31.17.217:8443` | running | Host-networked container; mTLS and API authentication required; provider URL intentionally unavailable so bounded fallback is exercised. |
| EDGE | `socat-ragin.service` | `127.0.0.1:18083` | running | Root-owned loopback-only mTLS forwarder to CORE. |
| EDGE | `ragin-cowrie-staging` | internal bridge `ragin-cowrie-internal`; host forward `127.0.0.1:2222` | running | Cowrie 3.1.1 pinned digest; read-only root, dropped capabilities, no Docker socket, no-new-privileges, non-root, bounded memory/CPU/PIDs; no host networking. |
| CORE/EDGE | Ubuntu `sshd` | administrative port 22 | running | Operator-restricted; not exposed as a public deception service. |
| CORE/EDGE | SSM Agent | AWS control plane | Online | Existing `RAGIN-SSM-ManagedProfile`. |

Public application/deception listeners were not opened. Public connection attempts to CORE `8443` and EDGE `2222/18083` timed out. Current CORE provider runtime is fallback-only after the bounded provider-backed generation test removed its temporary credential.

The 2026-10-09 local OpenCode/Cowrie validation used temporary loopback
services and a bridge-subnet-only UFW rule. The Cowrie container, local
`server_v2`, OpenCode bridge, and `8843/tcp` exception were stopped/removed
after the test; no local `8731` or `8843` listener remains.

The bounded provider benchmark completed after that validation with the same
temporary OpenCode bridge profile. The benchmark report records two
`GENERATED_VERIFIED` cases and one `TEMPLATE_FALLBACK_VERIFIED` case; the
bridge was stopped after the report was written.

Rollback of staging services is host-local: stop/remove the named containers and `socat-ragin.service`, then remove only the temporary `/etc/ragin` staging material after preserving evidence. AWS SG rollback is recorded in `CHANGE_AND_ROLLBACK_LOG.md`.
