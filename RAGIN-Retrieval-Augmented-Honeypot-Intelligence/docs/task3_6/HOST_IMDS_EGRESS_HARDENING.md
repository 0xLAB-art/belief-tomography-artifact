# RAGIN Task 3.6: Host, IMDS, and Egress Hardening

## Observed baseline

Both instances require IMDSv2 tokens, but the metadata endpoint is enabled and `HttpPutResponseHopLimit=2`. Tokens were obtainable from the host. No IAM-info document was returned because neither instance has an attached profile. This reduces current credential exposure but is not a durable container-isolation control.

Both hosts report inactive UFW, empty inspected nftables rules, and iptables `INPUT`, `FORWARD`, and `OUTPUT` policies of `ACCEPT`. AWS SG and the shared default NACL allow all egress. Docker was absent, so container forwarding and Docker socket behavior were not testable.

## Approval-gated hardening policy

| Boundary | Target control | Safe prerequisite | Current status |
|---|---|---|---|
| EDGE metadata | Disable IMDS endpoint if the final EDGE software has no AWS API need; otherwise require a proven hop-1/container design | Confirm no required AWS bootstrap or management dependency; test on an isolated copy/path | Not applied |
| CORE metadata | Keep IMDSv2 required; use a narrowly scoped profile only if a documented service needs it | IAM review and profile approval | Not applied |
| Host ingress | Allow only management, required service binds, and local health paths | Capture SSH rollback and verify alternate access | Not applied |
| Host egress | Default-deny or narrow allowlist for DNS, time, package/security updates, authenticated CORE traffic, and approved logging | Build a complete dependency matrix; test allow/deny destinations owned by the project | Not applied |
| Container boundary | No privileged containers, no host network, no Docker socket, no sensitive host mounts, read-only root where compatible, bounded CPU/memory/PIDs/uploads | Deploy only after image and Compose review; do not execute attacker payloads | Not deployed |
| Forwarding | Explicit DOCKER-USER/nftables policy for container-to-metadata and arbitrary internet paths | Validate rule ordering and rollback before enabling Docker | Not applied |

Security groups alone cannot enforce host/container boundaries or stop a process that already has host privileges. Do not enable a default-deny host firewall until SSH, DNS, time, package, CORE, logging, and recovery paths are documented and tested.

## Egress policy shape

The final EDGE should have only authenticated EDGE-to-CORE traffic, required infrastructure resolution/time/update traffic, and an approved audit path. It must not reach arbitrary attacker-selected destinations, cloud metadata, Docker control sockets, or provider credentials. The final CORE should accept only authenticated application traffic from the approved EDGE identity and operator management path.

No host firewall, metadata option, NACL, SG egress, route, or Docker change was made.
