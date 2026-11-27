# RAGIN Task 3.8: Final Infrastructure Blockers

## Implemented and verified from this session

- Accurate reconciliation of the prior task3_8 narrative against the actual task3_7 result.
- Explicit recording that the live authorized mTLS case is still BLOCKED, not PASS.
- Explicit recording that AWS API access was not available from this session, so no live AWS mutation, private-subnet creation, endpoint creation, snapshot, replacement volume, replacement instance, or cutover was performed.
- Updated root-cause analysis with the repaired certificate profile and the required live retry matrix.
- Updated CORE migration approval packet and encrypted-storage cutover plan so they no longer imply a completed migration.

## Tested but failed before repair

- The previous authorized client certificate was rejected by the CORE `CERT_REQUIRED` server during the live private-path test recorded in Task 3.7.
- This failure is documented in `MTLS_ROOT_CAUSE_ANALYSIS.md` and is not presented as a security pass.

## Designed but not deployed

- Repaired mTLS certificate profile with explicit CA constraints, SKI/AKI, EKU, SAN, and validity handling.
- Private CORE subnet and route table.
- Replacement CORE instance with encrypted root storage.
- Private SSM endpoint path or another private management overlay.
- Permanent EDGE-to-CORE service listener using the validated certificate contract.
- Dependency-specific outbound allowlist and Docker forwarding policy.
- Protected audit delivery, VPC Flow Logs, and emergency isolation rehearsal.

## Remaining P0/P1 blockers

1. CORE still has a public IPv4 address and direct IGW route.
2. Current roots are unencrypted.
3. Permanent egress containment is incomplete.
4. The live authorized mTLS case is still BLOCKED pending a re-test with the repaired certificate profile from a reachable operator session.
5. The real RAGIN application has not been deployed behind the validated mTLS contract.
6. EDGE is still Ubuntu SSH, not Cowrie, and no attacker-facing container isolation exists.
7. Telemetry, protected audit durability, emergency recovery rehearsal, and ethics/privacy approval remain incomplete.

## Session-access blockers

- AWS CLI session expired; refresh from the terminal was not available.
- Root SSH was blocked from this environment.
- SSM Session Manager was not reachable from this environment.
- Live AWS reads and any regulated change therefore could not be performed from this session.

## Explicit non-decisions

- No public Cowrie, RAGIN API, Docker container, Rust gateway, Laya service, or third-party target was contacted.
- No EC2 instance, EBS volume, snapshot, KMS key, subnet, route table, VPC endpoint, NAT gateway, or paid resource was created.
- No existing CORE or EDGE resource was modified or terminated.
- Task 4 was not started and public honeypot activation was not enabled.

## Smallest exact AWS change requests still requiring approval

1. Re-verify live AWS state for CORE, EDGE, VPC, subnets, route tables, IGW, NACLs, SGs, volumes, SSM endpoints, and cost before any change.
2. Approve a private CORE subnet, route table, and chosen private SSM management path.
3. Approve encrypted replacement CORE storage and replacement compute, with the existing CORE retained for rollback.
4. Approve the coordinated private-network and encrypted-storage cutover and its maintenance window.
5. Later approve the separate EDGE encrypted-root and deception-plane migration.
6. Approve the live mTLS re-test using the repaired certificate profile from a reachable EDGE-to-CORE path.

