# Sprint Cost Ledger

## Observed

| Check | Result | Interpretation |
|---|---|---|
| Cost Explorer, 2026-10-01 to 2026-10-08, daily unblended cost | `0 USD` for each returned day | Current query observed zero; not a credit-balance guarantee or future-cost guarantee |
| AWS Budgets | no budget object returned | No CLI-visible project budget was configured |
| Credit balance | not available from the used AWS CLI APIs | User estimate of approximately $100 remains unverified |

## Sprint changes

| Resource | One-time | Recurring | Actual action |
|---|---:|---:|---|
| Private subnet `subnet-07fae34b3db734bb2` | $0 expected | $0 expected | created and verified |
| Route table `rtb-04bf376f929483d4c` | $0 expected | $0 expected | created, associated, local route only |
| Temporary local/AWS mTLS tests | $0 AWS service cost expected | $0 | temporary rules/listener removed |

## Approval-gated cost items

Replacement CORE compute, encrypted snapshot or image storage, overlap runtime, SSM interface endpoints, NAT, and any additional EBS storage require a fresh price check in eu-north-1 and explicit approval. No estimate is presented as an AWS-enforced cap.

The sprint target remains $25 incremental spend and a $70 planning ceiling, but neither is enforced by AWS. No new recurring paid service should be created until the account credit balance is verified in the billing console.
