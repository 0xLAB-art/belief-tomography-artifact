# 06 — AWS Readiness and Approval

**Status this session:** AWS current state NOT verified.
**Reason:** AWS CLI is present (`/home/elaref/.local/bin/aws`) but the session is expired (`aws: [ERROR]: Your session has expired. Please reauthenticate using 'aws login'.`). Read-only inventory therefore could not be completed.

---

## 06.1 What was attempted

Commands attempted (read-only, no resource creation):

- `aws configure list`
- `aws sts get-caller-identity --output json`
- `aws ec2 describe-regions --output json --query Regions[].RegionName`

All returned rc 255 with the expired-session error.

---

## 06.2 Historical identifiers (NOT verified this session)

These were recorded in the prior audit and prior project docs. They are historical only until re-verified.

- Region: `eu-north-1`
- CORE: `i-062a400b300f4f9e4`
- EDGE: `i-05bc6aab0bd4260a7`
- VPC: `vpc-044a70ed680faff8b`
- Subnet: `subnet-07fae34b3db734bb2`
- Route table: `rtb-04bf376f929483d4c`
- EIC endpoint: `eice-023d2c69cb6690c48`

**Do not treat these as current.**

---

## 06.3 Questions that must be answered from AWS before field migration

1. Is CORE still running, and does it still have a public address?
2. Is CORE root EBS encrypted?
3. Is CORE running the verified pipeline (server_v2 pipeline mode), or the legacy server.py services?
4. Can EDGE authenticate to CORE using its existing service identity (keys/mTLS/instance role)?
5. Is the provider path actually operational from the AWS-hosted pipeline?
6. Are egress restrictions effective (no unintended public egress from the pipeline)?
7. Is protected audit persistence in place (session logs, host fiction, field export)?
8. Do recovery paths survive private subnet migration (SSM, management, inference transport)?

---

## 06.4 Constraints that still apply

- No new billable EC2 instances.
- No new paid EBS snapshots or volumes.
- No NAT Gateways.
- No paid SSM interface endpoints.
- No paid inference.
- No public honeypot activation.
- No destructive CORE cutover.
- No broad security-group or IAM changes.
- No public inference proxies.
- No disabling production authentication or mTLS.

These were not changed this session; they remain binding for any AWS work.

---

## 06.5 Cost exposure estimate (to be confirmed after read-only inventory)

Cannot be reliably estimated until the current CORE/EDGE state and EBS encryption status are verified. Before any approval packet is finalized, the read-only inventory must confirm:

- instance state and type,
- EBS volume(s) and encryption,
- Elastic IP association (if any),
- security group rules,
- any existing paid services attached to the account.

Until then, any dollar figure would be fabricated.

---

## 06.6 Approval packet outline (for when inventory is available)

A proper approval packet for any paid or disruptive AWS change should contain:

1. Current-state evidence (read-only outputs with redaction of secrets):
   - instance state, type, launch time
   - EBS volume id, size, encryption status, attachment
   - public IP / Elastic IP status
   - security group ingress/egress summary
   - route table and subnet placement
   - IAM role attached to instances (if any)
   - SSM reachability status (if applicable)
2. Proposed change, exact and minimal:
   - what is being changed,
   - why,
   - what is NOT being changed,
   - rollback steps.
3. Cost exposure:
   - expected incremental cost,
   - billing caps or watches to set,
   - who authorizes any overage.
4. Operational impact:
   - downtime window,
   - SSH/Cowrie availability during change,
   - pipeline serving impact,
   - field data impact.
5. Verification after change:
   - what read-only checks confirm success,
   - what failure looks like,
   - who is notified.
6. Authorization:
   - named approver,
   - explicit yes for any paid/disruptive step.

---

## 06.7 Verdict

**AWS current state: unavailable this session.**
**Approvals needed: any AWS change requiring credentials or cost must wait for re-authentication + read-only inventory + an approval packet built from actual current state.**

This session did not create, modify, or delete any AWS resources.
