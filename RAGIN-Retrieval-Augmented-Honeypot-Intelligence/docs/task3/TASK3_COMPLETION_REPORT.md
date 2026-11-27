# RAGIN Task 3 Completion Report

**Status: DESIGN COMPLETE / DEPLOYMENT BLOCKED.**

The offline AWS boundary design, approval packet, service-authentication contract, EDGE isolation plan, egress/metadata controls, telemetry/privacy plan, and acceptance tests are complete. Read-only SSH and AWS CLI inspection verified the current EC2/VPC state, while effective IAM behavior, independent reachability, logging delivery, and the target security boundaries remain unverified. No mutations or public exposure were performed.

## What was verified

- All seven Task 1 reports and all six Task 2 reports were read before producing this task's artifacts.
- The active application path remains Task 2's `server_v2 -> Sandbox -> mandatory Harness`; Task 3 does not change that contract.
- `docker-compose.field.yml` is a single-host Docker bridge design with Cowrie as the only intended published listener and an `internal: true` bridge (`docker-compose.field.yml:49-160`). This is not proof of a two-EC2 AWS boundary.
- `scripts/field_provision.sh` contains intended host UFW, DOCKER-USER egress, Tailscale management, and collection steps (`scripts/field_provision.sh:14-78`). It has not been run on the stated EC2 hosts in this task.
- The Python image has no default non-root user or image-level capability hardening (`Dockerfile.python:1-15`), and the field Compose file lacks explicit Cowrie resource, capability, read-only, and no-new-privilege controls.
- The Rust gateway source registers generation/model/cost/metrics routes without visible request authentication (`llm-gateway/src/main.rs:58-136`); its config has an empty API-key map and wildcard CORS (`llm-gateway/config.toml:126-129`). It is excluded from the future field serving dependency path.
- SSH read-only inspection verified both instances in the same VPC but different subnets, each with a public IPv4 address; exact IDs, types, AMI, AZ, subnet, VPC, and attached security-group identifiers are recorded in `AWS_CURRENT_STATE_AUDIT.md`.
- CORE has no observed application listener and EDGE has no Docker/Cowrie runtime. Both expose Ubuntu `sshd` on public TCP/22.
- Both hosts report inactive UFW and iptables `INPUT/FORWARD/OUTPUT ACCEPT`. IMDSv2 tokens were obtainable; AWS reports hop limit 2 and an enabled IMDS endpoint. The IMDS IAM-info endpoint returned HTTP 404. The SSM Agent snap is installed and active, but `describe-instance-information` returned no target instances.
- Authorized AWS CLI inspection verified a default VPC, direct IGW routing, public-addressing subnets, current SG/NACL rules, unencrypted root EBS, no VPC Flow Logs, no VPC endpoints, no configured CloudTrail trails, and Cost Explorer month-to-date unblended total of USD 0.000000 for 2026-10-01 through 2026-10-09. Billing lag remains possible.

## What remains unverified

Effective IAM permissions, CloudWatch delivery, Session Manager registration, independent external reachability, and billing completeness. CORE is definitively not in the requested private-subnet posture: both public addressing and the direct IGW route are verified.

## Existing risks

### P0 deployment blockers

1. **CORE is in a public-addressing subnet with a direct IGW route.** Its SG currently limits inbound TCP/22 to one `/32`, but this is not a private CORE boundary.
2. **EDGE is broadly exposed at the SG layer and currently exposes the real Ubuntu SSH daemon.** No Docker/Cowrie runtime was observed; the required deception boundary is absent.
3. **Egress and evidence controls are weak.** SG/NACL/host egress are permissive, roots are unencrypted, and no VPC Flow Logs are configured.
4. **Rust gateway authentication is unresolved.** It must remain outside the field dependency path until authenticated and tested.

### P1 design/readiness issues

- The repository's one-host field package does not implement the requested AWS zone separation, and neither inspected host currently runs that containerized field package.
- `internal: true` and security-group restrictions cannot replace mTLS, host/container firewall policy, or IAM/IMDS hardening.
- Both inspected hosts have permissive host firewall defaults; AWS SG/NACL egress is also allow-all. `scripts/field_provision.sh` has not been applied and itself defaults UFW outbound to allow and resolves provider IPs at one point in time.
- Field Compose uses `cowrie/cowrie:latest` and lacks explicit resource/capability hardening.
- Existing security documentation claims Rust gateway API-key enforcement (`docs/SECURITY_HARDENING.md:32-50`) that is not supported by current gateway source; this is documentation drift and must not be used as evidence.
- Protected audit storage, encryption, retention, tamper evidence, VPC Flow Logs, and multi-writer durability are not established on AWS.

## Proposed changes requiring approval

The detailed change matrix is in `AWS_CHANGE_APPROVAL_PLAN.md`: private CORE placement or a staged replacement if the existing primary ENI is subnet-bound, SG/NACL and egress changes, IMDS/IAM hardening, overlay/SSM administration, mTLS, protected logs, and only then public Cowrie exposure. No changes were applied, no service was deployed, and no public port was opened.

Cost-sensitive recommendation: avoid NAT Gateway, new EC2, load balancer, and public IP additions. Use a private CORE subnet and an operator/service overlay if its operational controls are approved. SSM interface endpoints, CloudWatch ingestion, EBS/public IPv4, and managed secret services may incur charges and require an explicit budget decision.

## Tests and results

- Repository/source audit: completed.
- AWS control-plane identity: AUTHORIZED through the configured `default` profile; account identifier was not retained in the report.
- Authorized SSH read-only inspection: PASS for both hosts; instance metadata, network addresses/routes, listeners, services, firewall state, storage, Docker absence, IMDSv2 behavior, and SSM Agent state collected without secrets.
- Current security gates: FAIL for EDGE deception isolation and host egress baseline; public Ubuntu SSH and permissive host firewall were observed.
- `bash -n scripts/field_provision.sh`: PASS.
- `docker compose --env-file ... config --quiet`: PASS (`rc=0`) when rendering a temporary copy with `.env.field.example` materialized as `.env.field`; the direct repository-path check correctly refused because `.env.field` is absent. No services were started.
- Independent external network reachability, effective IAM permissions, CloudWatch delivery, audit restart, and emergency isolation tests: not run.
- Rust build/authentication tests: not run.
- Docker containers were not started and no external attack target was contacted or scanned. The only AWS network action was the explicitly authorized, read-only STS identity probe; it returned `rc=255` and yielded no usable identity.

The exact offline and live procedures are in `TASK3_SECURITY_TEST_PLAN.md`.

## Task 4 prerequisites

Task 4 must not assume deployment readiness. Before it starts, obtain a redacted AWS read-only inventory, decide overlay versus SSM, approve any chargeable resources, verify private CORE placement or approve and validate the staged migration branch, verify service mTLS in a non-public mode, resolve the Rust gateway disposition, complete ethics/IRB or waiver gates, and approve the live security acceptance window. Laya remains a later provider task and must not bypass Task 2 verification.
