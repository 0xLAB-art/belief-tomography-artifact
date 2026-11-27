# RAGIN Task 3: AWS Change Approval Plan

No AWS mutation was performed. Each item below requires explicit approval, a change window, a tested rollback, and an operator with an already verified alternate access path.

## Proposed changes

| Resource | Exact intended change | Effect | Cost | Downtime/lockout risk | Rollback | Verification |
|---|---|---|---|---|---|---|
| CORE placement | If already private, tighten routes and remove public addressing; otherwise stage an explicitly approved replacement/restore in a private subnet because the primary ENI is subnet-bound | Removes direct public CORE reachability without pretending an in-place ENI move is safe | Existing-private case has no direct fee; replacement, temporary EBS, snapshots, or extra public IPv4 can incur cost | CORE outage, state divergence, or lockout during cutover | Keep current CORE untouched, retain rollback path, switch EDGE back only after controlled verification | Redacted inventory, private-route proof, mTLS cutover, positive/negative port tests, state/audit integrity |
| EDGE/Core SGs | Replace broad/default rules with allowlisted ingress/egress and SG reference | Enforces coarse zone boundary | No direct fee | Cowrie/admin or CORE outage if wrong | Reapply captured SG version from operator role | Rule diff, VPC Flow Logs, authenticated/unauthenticated pairs |
| EDGE metadata | Disable IMDS or require IMDSv2/hop 1; remove unnecessary instance role | Reduces credential SSRF risk | None | Host tooling may fail if it depended on IMDS | Restore prior metadata option only after incident review | Metadata negative test and application health |
| CORE metadata/IAM | Require IMDSv2, attach only scoped profile if needed | Enables minimal logs/operator tooling | CloudWatch/SSM usage may cost; profile itself does not | CORE logs/management may fail | Reattach prior minimal profile, not a broad role | IAM policy simulator/read-only review and log delivery |
| EDGE ingress | Keep public TCP/22 only for Cowrie; bind sshd to overlay/SSM | Prevents public admin shell | Public IPv4 may incur current AWS charge | Admin lockout or listener collision | Restore prior binding only from alternate access | External Cowrie check plus operator sshd check |
| Host/container firewall | Apply tested UFW/nftables/DOCKER-USER policy with default-deny egress | Blocks relay/metadata/provider abuse | None | Egress-dependent services fail; firewall reset can lock out | Restore saved rules via alternate access | Counters and controlled denied connections |
| EBS roots | Create encrypted snapshot/volume replacement and attach only through an approved cutover; do not claim in-place encryption | Protects stored sessions and host data at rest | Snapshot, replacement volume, and temporary storage charges may apply | Boot/data loss or rollback complexity if copied incorrectly | Preserve current unencrypted volumes and instance; validate encrypted restore before cutover | `describe-volumes` encrypted flag, boot test, digest/state comparison |
| mTLS | Issue per-service certs, configure CORE trust, EDGE client, rotation | Adds service identity beyond bearer key | CA/certificate service may have cost; local CA is low-cost but needs operations | EDGE-to-CORE outage during rotation | Keep overlapping old/new trust during rotation; revoke only after verification | TLS identity test, wrong-cert test, replay/authorization tests |
| Audit/logging | Enable VPC Flow Logs and protected log delivery; configure retention | Improves incident/research provenance | CloudWatch storage/ingest charges | Low; log misconfiguration can obscure evidence | Restore prior retention/destination | Log arrival, access policy, retention, redacted sample |
| Optional SSM | Add required VPC endpoints/role if overlay is not selected | Removes public SSH administration | Interface endpoints can be recurring charge | Management outage if endpoint/role incomplete | Keep existing verified path until SSM proof | Session Manager login and CloudTrail evidence |

## Approval packet contents

Before applying any row, attach:

- redacted current inventory and SG/route/IAM diff;
- cost estimate and free-plan/credit impact;
- exact operator, window, and backout owner;
- pre-staged alternate access proof;
- test commands and expected negative/positive results;
- evidence retention destination;
- explicit approval for any new chargeable resource.

## Change ordering

1. Verify and stage alternate operator access.
2. Capture current state and export rules without secrets.
3. Build/verify CORE private placement and authenticated service path in a non-public test mode.
4. Apply metadata/IAM and SG restrictions in reversible increments.
5. Harden EDGE host/container and only then consider public Cowrie ingress.
6. Run the security acceptance plan and record failures; never interpret an unreachable host as a security pass.
