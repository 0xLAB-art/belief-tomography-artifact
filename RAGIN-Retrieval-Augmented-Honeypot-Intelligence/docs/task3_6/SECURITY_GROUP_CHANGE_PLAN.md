# RAGIN Task 3.6: Security-Group Change Plan

## First approval packet: EDGE inbound rules

**Resource:** `sg-077b8f78668f4f646` (`launch-wizard-4`), attached to `i-05bc6aab0bd4260a7` only in the inspected ENI result.
**Current state:** TCP/22, TCP/80, and TCP/443 from `0.0.0.0/0`; all-protocol egress from `0.0.0.0/0`.
**Exact intended change:** retain only TCP/22 from the already verified operator IPv4 `/32` currently used by CORE administration; remove public TCP/22, TCP/80, and TCP/443. Egress is unchanged in this packet.

The literal operator address is intentionally omitted from this artifact. The implementation operator must read it from the just-captured AWS rule and the active SSH source, confirm they match, and substitute that exact `/32` in the approved command. No new operator address may be guessed.

## Safe application order after approval

1. Re-read `sg-077b8f78668f4f646`, verify VPC and sole target attachment, and confirm the operator source `/32` matches the active SSH source.
2. Add TCP/22 from that `/32` if it is not already present.
3. Re-read the SG and establish a fresh authorized SSH connection to EDGE while the existing session remains available.
4. Revoke TCP/22 from `0.0.0.0/0` and revoke TCP/80 and TCP/443 from `0.0.0.0/0`.
5. Re-read the SG and confirm the exact resulting ingress set is one TCP/22 `/32` rule and no web ingress.

Illustrative AWS CLI shape, with the operator value resolved at execution time and never logged:

```bash
aws ec2 authorize-security-group-ingress --group-id sg-077b8f78668f4f646 \
  --ip-permissions 'IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges=[{CidrIp=<VERIFIED_OPERATOR_CIDR>,Description="operator-admin"}]'
aws ec2 revoke-security-group-ingress --group-id sg-077b8f78668f4f646 \
  --protocol tcp --port 22 --cidr 0.0.0.0/0
aws ec2 revoke-security-group-ingress --group-id sg-077b8f78668f4f646 \
  --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 revoke-security-group-ingress --group-id sg-077b8f78668f4f646 \
  --protocol tcp --port 443 --cidr 0.0.0.0/0
```

The command block is not authorization and was not executed. The add-before-revoke order protects against an accidental administrative lockout. Existing TCP sessions generally are not retroactively terminated by a security-group rule change, but a fresh connection is mandatory evidence.

## Applied result

**Recorded UTC:** 2026-10-08T18:48:29Z (post-change readback)
**Approval:** Explicit user approval received for this bounded EDGE inbound batch.
**Operator source verified:** `REDACTED_OPERATOR_HOST/32`; it matched the existing CORE administration rule, the current public source, and the active EDGE SSH peer.

The restricted TCP/22 rule was added first and read back successfully. A fresh SSH connection succeeded before public-rule removal. Public TCP/22, TCP/80, and TCP/443 were then revoked. A second independent fresh SSH connection succeeded afterward. Final ingress was exactly TCP/22 from `REDACTED_OPERATOR_HOST/32`; no IPv6, referenced-group, or other inbound rules remained.

## Approval and rollback

| Item | Assessment |
|---|---|
| Approval status | **APPROVED and VERIFIED** |
| Reversible | Yes, by restoring the captured ingress rules; rollback itself is another SG mutation and requires operator control-plane access |
| Direct cost | None expected for SG rule changes |
| Downtime | None expected; public 80/443 were not observed as host listeners |
| Lockout risk | Medium if the operator `/32` is wrong or current source changes before the fresh-connect test; reduced by add-first and keeping the current session |
| Resource-sharing check | Passed for the two target SGs: each was attached to only its target ENI in the inspected result. The default NACL and main route table are shared and are not touched |
| Rollback | Re-authorize the captured pre-state rules exactly, then verify from the control plane and with a controlled connection. Do not broaden to `0.0.0.0/0` unless an incident decision explicitly requires it. Rollback was not needed |
| Verification | `describe-security-groups`, fresh authorized SSH, instance/system status checks, and unchanged instance/ENI IDs |

No public honeypot port was opened by this packet. No CORE rule was changed.
