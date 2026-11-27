# RAGIN Task 3: EDGE Honeypot Isolation

## Required invariant

The public EDGE surface is Cowrie deception only. It must not expose the real Ubuntu shell, Docker control, AWS credentials, internal APIs, or a local inference service. This is a deployment invariant that requires live validation; repository configuration alone cannot prove it.

## Current repository posture

| Evidence | Interpretation |
|---|---|
| `docker-compose.field.yml:54-63,86-93` publishes TCP/22 to Cowrie and attaches it to `honeypot-internal` | Intended public SSH deception boundary for the one-host field package |
| `docker-compose.field.yml:156-160` marks the bridge `internal: true` | Useful container-network control, not an AWS VPC/private-subnet guarantee |
| `scripts/field_provision.sh:17-24` allows TCP/22 and `tailscale0` | Administrative access is intended to be overlay-only, but the script has not been run or verified on the stated EC2 hosts |
| `Dockerfile.python:1-15` has no `USER`, capability drop, or read-only default | Image-level least privilege is incomplete |
| `docker-compose.field.yml` has no `read_only`, `cap_drop`, `no-new-privileges`, resource limits, or upload quota for Cowrie | A public deployment needs an explicit container hardening overlay |
| `docker-compose.field.yml:97-115` defines an unverified `bare-llm` baseline profile | It must remain research-only and never be attached to the RAGIN public arm |

## Current host observation

The supplied read-only SSH inspection found that RAGIN-EDGE has public IPv4 `REDACTED_FLEET_HOST`, Ubuntu `sshd` listening on `0.0.0.0:22` and `[::]:22`, no Docker binary, no Cowrie container, inactive UFW, and iptables base policies of `ACCEPT`. Therefore the current public endpoint is administrative Ubuntu SSH, not a Cowrie deception endpoint. This is a deployment-gate failure, not evidence of isolation.

## Safe SSH transition

1. Inventory the current admin path and open a second operator session before changing port bindings.
2. Install and verify the operator overlay or SSM access while the existing access method remains available.
3. Bind the real `sshd` only to the overlay/private management address. Do not use public TCP/22 for administration.
4. Publish Cowrie on the public interface's TCP/22. If the host cannot bind Cowrie and management independently, stop and redesign before opening the port.
5. Verify from an operator-only path that `sshd` works, and from an isolated external test source that public TCP/22 reaches Cowrie banners/session semantics rather than Ubuntu `sshd`.
6. Disable or firewall any alternate public SSH, telnet, HTTP, backend, Docker, Redis, metrics, and management listeners.

## Container boundary

The approved hardening profile should include:

- non-root Cowrie user where supported by the image;
- `no-new-privileges:true`, `cap_drop: [ALL]`, and only documented capabilities;
- `read_only: true` with narrowly scoped writable volumes for Cowrie logs and bounded uploads;
- CPU, memory, PID, file-size, session, and upload quotas;
- no `/var/run/docker.sock`, host PID/network/IPC, privileged mode, host filesystem mounts, or device mounts;
- fixed image digest rather than `cowrie:latest` for a field campaign;
- explicit health and restart limits that cannot create an outbound storm;
- separate export process or one-way collection path with no attacker write access to audit storage.

Uploads must be stored as untrusted bytes, size-limited, non-executable, and never mounted into an execution-capable host path. Malware is not executed. Attacker-supplied C2 addresses are logged as data and never contacted.

## EDGE-to-CORE rule

EDGE may call only the fixed CORE controller hostname/private address and port using the mTLS client identity described in `CORE_SERVICE_AUTHENTICATION.md`. The destination must not be attacker-controlled request data or an unrestricted environment override. Provider/model credentials stay on CORE or the later LOCAL provider boundary.

## Isolation acceptance evidence

The following must be captured after approval, not inferred from Compose:

| Check | Evidence |
|---|---|
| Public 22 is Cowrie | Redacted external banner/session transcript and host listener map |
| Public 22 is not Ubuntu sshd | `ss -ltnp` bound addresses plus controlled external check |
| No Docker socket/privilege | Container inspect output and filesystem/mount/capability review |
| No metadata access | Controlled negative request from container and host metadata settings |
| No arbitrary egress | Host firewall counters and controlled denied-connection test |
| CORE only via mTLS | SG flow evidence plus authenticated/unauthenticated request pair |
| Evidence survives isolation | Protected copy/export and restart recovery record |
