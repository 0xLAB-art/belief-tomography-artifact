# Cowrie Container Isolation

Status: PASS for non-public staging isolation.

## Implemented controls

Cowrie 3.1.1 now runs on the pinned image digest recorded in `evidence/cowrie_container_isolation.json`, on the internal bridge `ragin-cowrie-internal` (`172.29.0.0/29`) without host networking or Docker port publication. A root-owned, hardened local forwarder exposes only `127.0.0.1:2222` to the operator's controlled test client and forwards to the container at `172.29.0.2:2222`.

The container uses a read-only root filesystem, a 64 MiB noexec/nosuid temporary filesystem, dropped capabilities, no-new-privileges, non-root UID 999, 384 MiB memory, 0.5 CPU, and 128 PIDs. It has no Docker socket or host administrative filesystem mount. The mTLS forwarder is reachable only from the internal bridge at `172.29.0.1:18083` and certificate files are mounted read-only with restrictive host permissions.

## Observed tests

The container reached the approved mTLS forwarder. Direct connections to the EDGE host SSH address, EC2 metadata, and an owned connectivity test target were blocked. Operator SSH and SSM remained available. Controlled Cowrie-to-CORE fallback and provider-backed flows both completed while the listener remained loopback-only. Evidence is in `evidence/cowrie_container_isolation.json` and `evidence/real_generation_e2e.json`.

The same four-path probe was independently rerun at 2026-10-09T03:36:03Z with results: forwarder `CONNECTED`; host SSH `BLOCKED`; metadata `BLOCKED`; external test target `BLOCKED`.

## Boundary

This is controlled staging, not public deployment. Public port 22 remains closed, and no public Cowrie or RAGIN application listener was opened. Host-level outbound policy is not yet a complete dependency-specific default-deny policy; that remains a migration/field-readiness blocker. The internal bridge and container checks do not by themselves prove all future Docker forwarding behavior under a public workload.
