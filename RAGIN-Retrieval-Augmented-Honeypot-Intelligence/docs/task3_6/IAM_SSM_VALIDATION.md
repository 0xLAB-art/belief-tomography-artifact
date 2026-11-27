# RAGIN Task 3.6: IAM and SSM Validation

**Validation window:** 2026-10-08, CloudTrail timestamps `22:06:57+03:00` through `22:07:12+03:00`

## Applied IAM state

| Resource | Final state |
|---|---|
| Role | `RAGIN-SSM-ManagedRole` |
| Trust | EC2 service principal only, action `sts:AssumeRole` |
| Attached policy | `arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore`, observed default version `v2` |
| Instance profile | `RAGIN-SSM-ManagedProfile` |
| Profile members | Only `RAGIN-SSM-ManagedRole` |
| Attached instances | CORE and EDGE only |
| Extra permissions | None added |

The role does not grant EC2, IAM, Secrets Manager, S3, KMS, CloudWatch, or administrator actions. The current operator session remains broad and was not modified.

## Direct validation

- Both instance descriptions show the profile and remain running.
- `describe-instance-information` reports both IDs `Online` with agent `3.3.4121.0`.
- `ssm-cli get-diagnostics` reports valid role credentials on both hosts.
- CORE Session Manager command returned instance `i-062a400b300f4f9e4` and hostname `ip-172-31-17-217`.
- EDGE Session Manager command returned instance `i-05bc6aab0bd4260a7` and hostname `ip-172-31-35-203`.
- Fresh SSH remained successful for both hosts after profile association and host firewall changes.
- The local Session Manager plugin `1.2.835.0` was installed from the AWS-signed package after fingerprint and package-signature verification.

## Rollback

Keep SSH until a separately approved replacement path exists. To roll back the SSM branch: disassociate the profile from both instances, remove the role from the profile, delete the profile, detach `AmazonSSMManagedInstanceCore`, and delete the role. Re-read instance profiles and confirm SSH remains available. No rollback is currently required.
