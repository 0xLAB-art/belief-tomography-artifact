# RAGIN Task 3.6: Egress and Metadata Tests

## Verified state

- Both instances require IMDSv2 and now use `HttpPutResponseHopLimit=1`.
- Host IMDSv2 token retrieval works from the host, as required by the SSM role.
- SSM diagnostics report valid instance-role credentials and all three required service endpoints reachable.
- UFW denies incoming traffic but retains default allow outgoing.
- AWS SG egress remains all protocols to `0.0.0.0/0`; the shared default NACL also allows all egress.
- Docker is absent, so no container-to-IMDS or Docker forwarding test is possible.

## Acceptance result

| Control | Status | Reason |
|---|---|---|
| IMDSv2 enforcement | PASS | AWS readback shows tokens required |
| Hop-limit reduction | PASS | AWS readback shows hop limit 1 on both |
| Host inbound restriction | PASS | UFW deny-incoming plus operator SSH validated |
| Arbitrary outbound denial | INCOMPLETE | Outbound remains allowed to preserve undocumented dependencies and SSM |
| Container metadata isolation | INCOMPLETE | Docker/Cowrie not deployed; no container test possible |
| Attack-relay prevention | BLOCKED | Requires final service dependency matrix and host/container egress design |

No internet-wide scan or third-party destination test was performed. Before public deployment, build a narrow egress allowlist for management, DNS/time, authenticated CORE traffic, and approved logging, then test owned endpoints. Do not replace this gap with an unverified default-deny rule.
