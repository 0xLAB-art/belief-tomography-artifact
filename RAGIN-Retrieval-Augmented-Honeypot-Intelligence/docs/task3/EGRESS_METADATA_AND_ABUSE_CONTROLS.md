# RAGIN Task 3: Egress, Metadata, and Abuse Controls

## Control matrix

| Threat | Target control | Current evidence | Required proof |
|---|---|---|---|
| EDGE becomes an attack relay | SG default-deny egress, host firewall, Docker DOCKER-USER default drop, no attacker-selected destinations | `scripts/field_provision.sh:29-54` proposes DOCKER-USER rules; it has not been executed on the EC2 hosts | Counters and denied connection tests for arbitrary TCP/UDP, DNS, ICMP, and attacker-supplied C2 |
| Container reaches IMDS | Disable IMDS on EDGE; otherwise IMDSv2 required, hop limit 1, host/container deny for `169.254.169.254` | No AWS metadata configuration exists in the repository | EC2 metadata options plus controlled container negative test |
| AWS credentials leak | No AWS role on EDGE; no provider keys on EDGE; redaction and secret scans | Field Compose passes backend/provider environment variables to the one-host service layout (`docker-compose.field.yml:125-142`) | Instance-profile audit, environment/mount audit, and redacted process inspection |
| Provider endpoint misuse | CORE/LOCAL-only provider access, fixed allowlist, TLS certificate verification, rate and budget caps | Field script resolves a provider IP at provisioning time (`scripts/field_provision.sh:38-46`) | Current DNS/IP allowlist test, rotation procedure, and denied alternate egress |
| DNS abuse/tunneling | Restrict DNS to VPC resolver/approved resolver, rate-limit queries, log anomalies | Field script permits general outbound by UFW and does not implement a DNS policy | Resolver rules, query-volume alert, and controlled tunneling-negative test |
| Upload/resource exhaustion | Size, PID, CPU, memory, file, session, and timeout limits; no execution | Compose lacks explicit field resource limits; logs are bounded at `:36-40` | Container inspect, saturation test in an isolated lab, and recovery evidence |
| Public inference exposure | No public local inference bind; LOCAL initiates authenticated overlay connection | No Laya integration exists | Port/listener inventory and authenticated/unauthenticated connection pair |
| Emergency isolation failure | Quarantine SG and stop/isolate procedure independent of EDGE | No AWS shutdown procedure is implemented | Operator rehearsal preserving logs and proving CORE/admin access remains available |

## Current host evidence

Both inspected hosts have a default route through the VPC subnet gateway, UFW reports `inactive`, and iptables reports `INPUT`, `FORWARD`, and `OUTPUT` policies of `ACCEPT`. AWS SG egress and the default NACL both allow all protocols to `0.0.0.0/0`. Docker is absent on both hosts, so no container egress boundary exists to validate. IMDSv2 tokens were obtainable; AWS reports `HttpTokens=required`, `HttpEndpoint=enabled`, and `HttpPutResponseHopLimit=2` on both instances. The IMDS IAM-info endpoint returned HTTP 404. These facts are current risks, not passing controls.

## Metadata posture

Recommended EC2 settings for both nodes:

```text
HttpTokens = required
HttpPutResponseHopLimit = 1
HttpEndpoint = disabled on EDGE when no AWS API is required
```

Do not treat the hop limit as a complete container boundary. Combine it with no EDGE role, host firewall rules, Docker egress policy, and a negative test. CORE may require an AWS API for logs or operator tooling; scope that role and route narrowly.

## Abuse and resource controls

- Put hard request and transcript limits at EDGE and CORE before provider calls.
- Limit simultaneous SSH sessions, commands per session, upload bytes, file count, and container PIDs.
- Apply timeouts to EDGE-to-CORE, generation, verification, persistence, and audit export separately.
- Use bounded retries and a global circuit breaker. Provider unavailability must produce a vetted fallback or a safe transport failure.
- Alert on egress drops, unexpected destinations, metadata probes, rapid session creation, upload spikes, repeated authentication failures, and CORE request rejection.
- Keep a kill switch that blocks EDGE at the SG layer before stopping it. Preserve evidence before deleting containers or volumes.

## Important limitations

AWS SGs do not see every container-level flow and cannot replace the host firewall. Docker networks do not create a cryptographic trust boundary. DNS allowlisting by a single provision-time IP is fragile under provider rotation. Every operational rule must have a refresh and failure mode that is fail-closed.
