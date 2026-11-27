# RAGIN Task 3.6: Remediation Priority Matrix

| Priority | Finding | Evidence | Required disposition | Approval/status |
|---|---|---|---|---|
| P0 | EDGE administration is internet-wide | EDGE SG allowed TCP/22 from `0.0.0.0/0`; Ubuntu sshd remains host-bound | Restrict TCP/22 to the verified operator `/32` as an interim administration state | **Applied and fresh-SSH verified** |
| P0 | EDGE exposes unused web ports | EDGE SG allowed TCP/80 and 443 globally; no corresponding listener was observed | Remove both ingress rules; do not open a honeypot/web listener | **Applied and read-back verified** |
| P0 | EDGE deception boundary is absent | Docker command absent and Cowrie inactive | Install/configure only in a later approved deployment window; never expose Ubuntu sshd as Cowrie | Not authorized in this task |
| P0 | CORE is not private | Public IPv4, public-mapping subnet, and direct IGW default route | Stage private-subnet migration or replacement; do not move the primary ENI in place | Design complete; separate approval required |
| P0 | Rust gateway authentication unresolved | Task 3 source review found no demonstrated request authentication | Keep gateway out of the field dependency path or remediate and test separately | No port opening or deployment |
| P1 | Host and cloud egress are permissive | UFW inactive, iptables ACCEPT, SG/NACL allow-all egress | Build an allowlist and apply incrementally only after access/rollback approval | Pending design and approval |
| P1 | IMDS endpoint remains enabled with hop limit 2 | EC2 metadata options and token test | Disable EDGE IMDS if no AWS need; otherwise require a proven container-safe hop-1 design | Separate approval required |
| P1 | No SSM management path | Agent active but SSM API registration empty; no endpoints/profile | Add least-privilege role and connectivity only after cost review; retain SSH until verified | Separate IAM/network approval required |
| P1 | Root EBS volumes unencrypted | Both attached roots report `Encrypted=false` | Use encrypted snapshot/restore or replacement cutover; no in-place claim | Separate storage approval required |
| P1 | Network/audit evidence incomplete | No VPC Flow Logs or configured CloudTrail trail; CloudWatch agent inactive | Choose protected, cost-bounded audit destination and retention | Separate logging approval required |

## Ordering rule

The approved EDGE inbound SG batch was applied in the order: add the verified operator `/32` rule, re-read and verify it, then remove public TCP/22, 80, and 443. No host, route, NACL, IAM, metadata, EBS, or egress mutation was bundled.
