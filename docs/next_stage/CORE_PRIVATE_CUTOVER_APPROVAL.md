# CORE private cutover readiness — approval-gated

## Objective

Prepare the lowest-risk, lowest-cost safe CORE replacement path using existing AWS resources, without executing any disruptive or billable change until explicitly approved.

This document is readiness material, not an executable cutover. It does not stop, replace, encrypt, or delete anything here.

## Current verified state to preserve

Reuse existing resources only:

- existing VPC
- private CORE target subnet
- private route table
- EIC management endpoint
- existing CORE and EDGE instances
- security groups
- IAM instance profiles
- existing EBS root volumes

Do not assume any of these are unchanged since the last read. Re-verify IDs and state before any gated change.

## Target post-cutover state

- CORE placed in the private subnet
- no public IPv4 on CORE
- no direct IGW route for CORE
- encrypted root EBS
- working private SSH administration
- restricted application ingress
- preserved data/state
- recoverable rollback

## Lowest-cost safe replacement concept

The intended approach is a replacement-and-swap pattern, not a live in-place network surgery on a production-facing instance:

1. Re-verify current CORE identity, subnet, ENI, security groups, IAM profile, and root volume ID.
2. Verify the private subnet, private route table, and EIC management endpoint are still present and correctly associated.
3. Provision a replacement instance only with explicit approval, reusing the existing AMI/image where possible and the existing instance profile and security posture.
4. Encrypt the root volume path as part of the replacement, using the cheapest approved EBS encryption path available, not unnecessary snapshots or premium options.
5. Attach or migrate required state/data only after the replacement is validated for the management path.
6. Keep the existing CORE and original volumes intact until the new path is validated and the rollback decision is closed.
7. If the management path is not verified first, do not depend on it for the cutover.

## What must be verified before approval is requested

- Exact current instance IDs for CORE and EDGE
- Exact current subnet and route-table state for CORE
- EIC endpoint state and which subnet/security groups it uses
- Current security-group rules for CORE and EDGE
- Current IAM profile attachments
- Current root volume IDs and encryption state
- Current public IPv4 association state for CORE
- SSM/EC2 Instance Connect/EIC management reachability for the planned management path
- Expected downtime window and rollback steps for the proposed replacement

Any disruptive change must include:

- estimated cost
- expected downtime
- rollback procedure
- what is preserved
- what must be re-verified after the change

## Approval-gated operations

STOP and request explicit approval before any of the following:

- creating billable EC2/EBS/snapshot resources
- stopping the active CORE disruptively
- replacing root volumes or instances
- encrypting volumes in a way that requires a charged resource or data movement
- any change that could irreversibly remove administrative access
- any change that broadens IAM privileges
- any change that exposes Cowrie or RAGIN publicly

## Cost posture

- Reuse existing infrastructure.
- Avoid NAT Gateway, paid SSM interface endpoints, managed databases, extra permanent EC2 compute, load balancers, and unnecessary snapshots.
- Minimize EBS changes to the smallest encrypted replacement path that satisfies the target state.
- Verify billing/credit state before any paid change.
- Do not interpret $0 in Cost Explorer as proof of unlimited free resources.

## Rollback principle

If a gated change is approved, the original CORE and original volumes must not be terminated or deleted until the new path is validated and rollback is no longer needed.

## What is prepared here

This document prepares the approval request and readiness checklist. It does not execute the cutover.

## Dependencies

- Part of Priority 0/1 depending on whether the change is disruptive or billable.
- Independent of A2 live SSH-wire proof, though both benefit from a private CORE target state.
- Should not proceed until A1 topology and A4 runtime validation are consistent with the intended CORE role.
