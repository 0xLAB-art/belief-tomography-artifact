# Deployment Manifest

State observed 2026-10-08T20:27:00Z. This manifest separates deployed resources from prepared targets.

## AWS resources

| Role | Resource | Actual state |
|---|---|---|
| CORE | `i-062a400b300f4f9e4` | running `m7i-flex.large`; public `REDACTED_FLEET_HOST`; private `172.31.17.217`; public subnet; staging mTLS listener bound to private IP only |
| EDGE | `i-05bc6aab0bd4260a7` | running `t3.micro`; public `REDACTED_FLEET_HOST`; private `172.31.35.203`; Ubuntu sshd operator-only plus loopback Cowrie staging |
| CORE target | `subnet-07fae34b3db734bb2` | `172.31.48.0/20`, eu-north-1a, no public-IP mapping |
| CORE target route table | `rtb-04bf376f929483d4c` | associated with target subnet; only `172.31.0.0/16 -> local` |
| Current CORE SG | `sg-03486d70769d21e4e` | operator TCP/22 plus temporary TCP/8443 from EDGE private `/32`; unrestricted egress |
| Current EDGE SG | `sg-077b8f78668f4f646` | operator TCP/22 ingress; unrestricted egress |
| IAM profile | `RAGIN-SSM-ManagedProfile` | attached to both; `AmazonSSMManagedInstanceCore` |
| Private management | `eice-023d2c69cb6690c48` | create-complete in prepared eu-north-1a subnet; ENI `eni-097341d0d05830cbe`, private IP `172.31.61.22`; dedicated SG `sg-05f6e3f406f0c9be2` |

Both root volumes are still unencrypted: CORE `vol-0537ee06e67f63cc5`, EDGE `vol-05925e722a36cd345`.

## Application state

- `server_v2` remains the repaired mandatory-verification path.
- `ragin/transport/mtls.py` adds strict TLS client-certificate and SAN identity enforcement.
- CORE runs a restricted `ragin-staging:20261008` container with `server_v2 --mode pipeline`, no provider key, and the dead-local provider URL `127.0.0.1:9` to force safe fallback.
- EDGE runs Cowrie 3.1.1 on `127.0.0.1:2222`; a root-owned `socat` service forwards only loopback Cowrie traffic to CORE mTLS on `172.31.17.217:8443`. The staging container uses host networking and is therefore not the final field isolation design.
- Provider key material and repository `.env` files were not copied to AWS; staging uses a generated API key and temporary three-day mTLS certificates.
- Rust gateway, Laya, JEV/OpenCode, and public application listeners are not running.

## Reconciliation rule

The prepared subnet is not evidence that CORE is private. The current CORE primary ENI remains in its original public subnet. Replacement/cutover is required for actual private placement. The current staging listener is not a public application listener: its bind address is the private IP and its SG source is EDGE's private `/32`.

## Sprint AWS change record

CloudTrail timestamps: subnet created at `2026-10-08T19:57:02Z`; route table created at `2026-10-08T19:57:04Z`; public-IP mapping disabled at `19:57:06Z`; association completed at `19:57:07Z`. The temporary CORE rule `sgr-02f8c8986dc89b953` was added after verifying the SG is attached only to CORE; it allows TCP/8443 from `172.31.35.203/32` and does not expose the public address. The EIC endpoint/SG was then created only for RAGIN private management. No instance, IAM role, volume, outbound rule, or EDGE ingress rule was changed.

Rollback is limited to these sprint-created resources: verify the subnet has no ENI, disassociate `rtbassoc-0a7dc98da6998e9e`, delete `rtb-04bf376f929483d4c`, then delete `subnet-07fae34b3db734bb2`. This rollback does not touch either existing instance.
