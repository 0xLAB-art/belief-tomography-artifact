# RAGIN Task 3.7: Change and Rollback Log

## Persistent changes

**None.** The Task 3.6 persistent baseline remains unchanged. No instance, volume, subnet, route table, IAM role, endpoint, NAT gateway, public address, or outbound rule was changed in Task 3.7.

## Temporary private mTLS validation changes

| UTC window | Resource | Temporary change | Result | Cleanup / rollback |
|---|---|---|---|---|
| `2026-10-08T19:20:54Z`–`2026-10-08T19:26:33Z` | CORE SG `sg-03486d70769d21e4e` | TCP/24443 from EDGE SG `sg-077b8f78668f4f646` | Used only for an ephemeral private test | Revoked by SG tuple; final ingress is operator TCP/22 only |
| Same window | CORE UFW | Allow TCP/24443 from `172.31.35.203` | Used only for an ephemeral private test | Deleted; final UFW lists only operator SSH |
| Same window | CORE/EDGE temporary files/processes | Test CA, server/client certificates, ephemeral listener | No application deployed; authorized certificate test failed, rogue rejection passed | Processes and temporary directories removed; no repository material retained |

CloudTrail event history records the SG authorize/revoke events. Final AWS and host readback was captured at `2026-10-08T19:26:53Z`.

## Recovery

If a future approved mTLS test leaves a rule behind, identify the exact rule by group, protocol, port, and source group, revoke only that tuple, remove the matching host rule, then verify SG/UFW, SSH, and SSM. Never remove the operator TCP/22 rule during cleanup.
