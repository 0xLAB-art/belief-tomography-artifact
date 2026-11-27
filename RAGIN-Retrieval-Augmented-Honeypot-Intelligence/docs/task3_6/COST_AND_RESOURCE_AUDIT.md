# RAGIN Task 3.6: Cost and Resource Audit

## Resources changed

| Resource | Change | Direct recurring cost |
|---|---|---|
| `RAGIN-SSM-ManagedRole` | Created with EC2 trust and one AWS-managed SSM policy | None for the role itself |
| `RAGIN-SSM-ManagedProfile` | Created and associated with the two existing instances | None for the profile itself |
| CORE/EDGE | Existing profile association, host SSH/UFW changes, IMDS hop limit | No new compute/storage/network resource |
| Local workstation | AWS-signed Session Manager plugin installed | Local package only |

No EC2, subnet, route table, NAT gateway, VPC endpoint, load balancer, database, snapshot, EBS volume, or public address was created.

Cost Explorer readback for 2026-10-01 through 2026-10-07 returned `0 USD` unblended usage. This is not proof of zero charges, credits, or future billing.

## Deferred cost risks

Private CORE management may require SSM interface endpoints with per-AZ hourly and data-processing charges, or a NAT gateway with hourly and per-GB charges. EBS encryption migration may add snapshot, KMS, and replacement-volume costs. CloudWatch/Flow Logs and public IPv4 usage may also incur charges. No such resource is approved or deployed by this task.
