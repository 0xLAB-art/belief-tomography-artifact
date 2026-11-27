# RAGIN Task 3.6: AWS Final State

**State snapshot:** 2026-10-08T19:13:13Z
**Region:** `eu-north-1`
**Scope:** live AWS and SSH/SSM state after the approved safe-hardening actions. No public honeypot was activated.

## Compute and management

| Node | Instance | State/type | Private/public IPv4 | SG | IAM profile | SSM |
|---|---|---|---|---|---|---|
| CORE | `i-062a400b300f4f9e4` | running / `m7i-flex.large` | `172.31.17.217` / `REDACTED_FLEET_HOST` | `sg-03486d70769d21e4e` | `RAGIN-SSM-ManagedProfile` | Online |
| EDGE | `i-05bc6aab0bd4260a7` | running / `t3.micro` | `172.31.35.203` / `REDACTED_FLEET_HOST` | `sg-077b8f78668f4f646` | `RAGIN-SSM-ManagedProfile` | Online |

The shared profile contains only `RAGIN-SSM-ManagedRole`, which trusts EC2 and has only `AmazonSSMManagedInstanceCore`. No administrator policy was attached to the instance role.

## Effective hardening

- EDGE and CORE AWS inbound SGs allow only operator TCP/22 from the verified `/32`; EDGE public 80/443 remain closed.
- Both hosts have active UFW, deny incoming by default, allow only operator TCP/22, and retain outgoing allow.
- Both hosts have key-only SSH settings: password and keyboard-interactive authentication disabled, root login disabled, forwarding/X11 disabled, and bounded auth/session/keepalive settings.
- Both instances require IMDSv2 and now use response hop limit `1`; the endpoint remains enabled because the SSM instance role depends on host metadata credentials.
- Fresh SSH and independent Session Manager identity checks passed for both nodes.
- No Docker, Cowrie, RAGIN service, or public application listener was started.

## Still public or incomplete

CORE retains a public IPv4 and direct IGW-routed subnet. AWS SG/NACL and host outgoing policies remain broad. Root EBS volumes remain unencrypted, VPC Flow Logs are absent, and no configured CloudTrail trail was observed. EDGE is still Ubuntu SSH rather than Cowrie. These are not deployment-readiness claims.
