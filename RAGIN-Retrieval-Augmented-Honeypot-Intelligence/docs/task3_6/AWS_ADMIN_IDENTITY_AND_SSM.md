# RAGIN Task 3.6: AWS Administrative Identity and SSM

**Phase B preflight timestamp:** 2026-10-08T18:59:31Z
**Scope:** read-only refresh plus approval-ready IAM/SSM design. No IAM, instance-profile, network, or host mutation was performed.

## Current identity

The read-only STS check returned an assumed-role ARN for `AccountFullAccessRole`, not a direct root ARN. This confirms a temporary assumed-role session at the AWS CLI boundary, but does not prove how the session was obtained, whether MFA was used, or that the role is least privilege. The role is broader than required for routine RAGIN operations and is a privileged-account risk.

No credential values, access-key material, tokens, or private keys are included here.

The current CLI identity remains the privileged assumed `AccountFullAccessRole` session. It is suitable for authorized inspection but is not a least-privilege EC2 instance role and must not be attached to either instance.

## EC2 management state

| Check | CORE | EDGE |
|---|---|---|
| Instance profile | None observed | None observed |
| SSM Agent | Snap service active | Snap service active |
| SSM managed-instance result | Not listed by `describe-instance-information` | Not listed by `describe-instance-information` |
| Session Manager login | Verified independent command session | Verified independent command session |
| Existing SSH | Verified read-only path | Verified read-only path |

Keep SSH available until an independent Session Manager or private-overlay login has succeeded and been recorded. Agent presence alone is not an administrative path.

Current AWS reads still show no instance profile on either running instance and no SSM managed-instance registration. Both hosts report SSM Agent `3.3.4121.0`, active as a snap service. The host diagnostic reports all three required regional HTTPS endpoints reachable, but its AWS Credentials check fails with `no EC2 instance role found`. The agent reports a newer available regional version (`3.3.5512.0`); updating it is not part of this approval packet.

The target SGs retain all-protocol outbound access, the default route still reaches the IGW, and no VPC endpoints exist. This is sufficient for the current SSM connectivity test, but it is not the desired private CORE architecture.

## Proposed minimum role and instance profile

**Status: APPLIED AND VERIFIED.** The role/profile names were rechecked before creation and are now attached only to the two RAGIN instances.

| Resource | Proposed value | Purpose |
|---|---|---|
| IAM role | `RAGIN-SSM-ManagedRole` | EC2-trusted role for the two RAGIN nodes |
| Instance profile | `RAGIN-SSM-ManagedProfile` | Passes the role to EC2 without changing the instances' SSH path |
| Attached policy | AWS managed `arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore`, current observed default version `v2` | Standard SSM managed-node permissions only |
| Additional permissions | None | No S3, KMS, CloudWatch, Secrets Manager, EC2 mutation, IAM, or administrator permissions |

The exact trust policy is:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

The current AWS managed policy document was read-only inspected. Its three action groups are SSM association/inventory/status operations, `ssmmessages` control/data channels, and `ec2messages` message delivery operations, all with `Resource: "*"` as required by those service APIs. It does not grant an operator permission to start sessions or mutate EC2. Operator permissions remain separate and should use MFA and a narrower change role than the current account-wide session.

AWS documents `AmazonSSMManagedInstanceCore` as providing the required instance permissions for Session Manager: [Session Manager prerequisites](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-prerequisites.html) and [instance permissions for Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-getting-started-instance-profile.html).

AWS also supports Default Host Management Configuration, but that is an account-level alternative. It is not selected here because this task is scoped to two named instances and must avoid an account-wide IAM behavior change without separate approval.

## Exact approved-change boundary

The applied IAM/EC2 change boundary was:

1. Create the EC2-trusted role above.
2. Attach only `AmazonSSMManagedInstanceCore`.
3. Create the instance profile and add the role to it.
4. Associate that profile with `i-062a400b300f4f9e4` and `i-05bc6aab0bd4260a7`.
5. Re-read both instances and wait for managed-node registration.
6. Start one controlled Session Manager shell to each instance, verify host identity, and terminate the sessions.

No SG, route, subnet, endpoint, NAT gateway, instance state, SSH setting, metadata option, host firewall, or outbound rule is included. Existing SSH remains available until both Session Manager connections are independently proven.

## Least-privilege target

Use a dedicated temporary-credential operator role with MFA and only the read/change permissions needed for the approved change window. Use separate deployment and inspection roles; do not use root credentials or an account-wide role for steady-state operation. Do not disable, rotate, delete, or replace the current identity in this task.

For SSM, attach only the minimum managed-instance policy needed for Session Manager, after a policy review. Adding an instance profile is an IAM mutation and requires explicit approval. Connectivity may use the existing public egress temporarily, or approved private endpoints; interface endpoints have recurring charges and were not present in the current VPC.

The current recommendation is the standard managed policy above rather than an administrator-wide role. Session logging to CloudWatch Logs or S3, KMS-encrypted sessions, Parameter Store, Patch Manager, or inventory extensions would require separately reviewed permissions and are intentionally excluded.

## Cost and network decision

No VPC endpoint or NAT gateway is needed to establish SSM now: both hosts have a working default route and read-only HTTPS probes/`ssm-cli` diagnostics reached `ssm`, `ssmmessages`, and `ec2messages` in `eu-north-1`. This preserves the current cost profile but leaves internet egress and public-subnet exposure unresolved.

For a later private CORE design, AWS PrivateLink endpoints for SSM, SSMMessages, and EC2Messages can remove the internet dependency; optional S3, Logs, and KMS endpoints depend on enabled features. Interface endpoints incur hourly per-AZ and data-processing charges, while a NAT gateway incurs hourly and per-GB processing charges. Neither option is approved or created here. See [AWS Systems Manager VPC endpoint guidance](https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-create-vpc.html), [interface endpoint pricing](https://aws.amazon.com/privatelink/pricing/), and [NAT gateway pricing](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html).

## Acceptance gate

SSM is PASS for this administration phase: both instances appear as managed, independent Session Manager command sessions returned matching instance IDs and hostnames, sessions terminated cleanly, and existing SSH remained available. No further IAM or SSM mutation is pending.
