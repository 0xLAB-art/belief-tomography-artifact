# RAGIN Task 3.8: Egress, Audit, and Emergency Readiness

## Current status

- SG outbound rules remain all-protocol `0.0.0.0/0`.
- UFW allows outgoing traffic; incoming is denied except operator SSH.
- The default NACL remains allow-all.
- No Docker or Cowrie workload exists, so Docker forwarding and container metadata tests remain unavailable.
- IMDSv2 is required with hop limit 1, but the metadata endpoint remains enabled for the SSM instance role.
- No VPC Flow Logs or configured long-term CloudTrail delivery was observed.
- Both root EBS volumes remain unencrypted.

No permanent egress change was made. Blocking outgoing traffic before documenting SSM, DNS, time, package, and private-service dependencies could strand management.

## Dependency-specific implementation order

1. Inventory actual destinations and ports from the future service, SSM agent, DNS resolver, time sync, and maintenance process.
2. Test the allowlist against owned endpoints while keeping an independent SSM session or equivalent operator path open.
3. Apply SG and host rules incrementally, preserving established management and response traffic.
4. For future Docker, enforce the same policy in `DOCKER-USER`, block metadata from attacker-controlled namespaces, and never expose the Docker socket.
5. Verify allowed traffic, denied arbitrary traffic, metadata denial for the attacker workload, and SSM recovery before calling egress containment PASS.

## Protected audit design

CORE audit events should include session ID, timestamp, command event, candidate provenance, verifier decision, fallback transition, state commit, service/model version, and failure event. Source addresses should be minimized or coarsened where the research design permits. Raw credentials and unnecessary raw uploads must never enter evidence exports.

Use restrictive service-account permissions, rotation, bounded retention, log rotation, and a protected or tamper-evident copy. Keep public attacker observations separate from controlled synthetic benchmarks and preserve reproducibility manifests without private data.

## Emergency isolation rehearsal

The non-destructive rehearsal should be run only with a second operator channel confirmed:
1. Open and verify SSM on CORE and EDGE.
2. Capture current SG, UFW, process, and audit state.
3. Revoke EDGE attacker-facing ingress or attach a pre-created isolation SG while preserving SSM.
4. Confirm CORE remains reachable only through the private or management path.
5. Preserve logs and evidence, then restore the prior known-good SG state.
6. Re-test SSH/SSM and record timestamps and rule hashes.

The live rehearsal remains **INCOMPLETE** because the current public/admin path is also the only proven operator path and the public honeypot is not deployed.

## Evidence note from this session

AWS API access was not available from this session. SG, NACL, flow-log, CloudTrail, and host-firewall state could not be re-read live, and no egress or audit change was made. The items above are a readiness plan, not live verification.

