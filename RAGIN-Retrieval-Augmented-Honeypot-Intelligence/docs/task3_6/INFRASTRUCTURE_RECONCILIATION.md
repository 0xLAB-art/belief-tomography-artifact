# RAGIN Task 3.6: Infrastructure Reconciliation Record

## Current deployed inventory

The existing EC2 instances, default VPC, subnets, route table, ENIs, SGs, and EBS volumes were reconciled with AWS CLI readback. The applied changes are represented by:

- `RAGIN-SSM-ManagedRole` with EC2 trust and `AmazonSSMManagedInstanceCore` only.
- `RAGIN-SSM-ManagedProfile` attached to the two existing RAGIN instance IDs only.
- Existing dedicated SGs with operator-only TCP/22 ingress and unchanged outbound rules.
- Existing instances with IMDSv2 required and hop limit 1.
- Host-managed SSH hardening and UFW ingress policy recorded in the final-state documents.

## Reconciliation procedure

Before any future Terraform/CloudFormation adoption:

1. Import the exact existing VPC, subnets, route table, IGW, ENIs, instances, EBS volumes, and SGs into a state file held in restricted operator storage.
2. Import the applied IAM role/profile and verify the trust/policy diff before planning.
3. Run a plan that contains no replacement, termination, public-IP change, route change, or EBS action.
4. Compare the plan with `AWS_FINAL_STATE.md` and `CHANGE_AND_ROLLBACK_LOG.md`.
5. Apply only after the plan is reviewed; never use an unreviewed `apply`, destroy, or replacement operation.

No IaC import or apply was run in this task. A future private-subnet migration, encrypted-volume cutover, egress redesign, and Cowrie deployment must be represented as separate reviewed plans rather than inferred from the current state.
