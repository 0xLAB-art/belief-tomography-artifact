# RAGIN Task 3.6: Security Acceptance Matrix

| Control | Status | Direct evidence |
|---|---|---|
| Authorized SSH remains functional | PASS | Fresh CORE and EDGE SSH after SSH hardening and UFW |
| SSM managed-node registration | PASS | Both instance IDs `Online` |
| Independent SSM session to CORE | PASS | Returned expected instance ID and hostname |
| Independent SSM session to EDGE | PASS | Returned expected instance ID and hostname |
| EDGE public web ingress absent | PASS | SG has no 80/443; no host listener |
| EDGE real-shell isolation | INCOMPLETE | SSH remains reachable to operator; Cowrie not deployed |
| CORE application internet reachability | INCOMPLETE | No application listener exists, but CORE remains public-subnet/public-IP |
| Unauthorized service requests fail | PASS for local mTLS primitive | Rogue client certificate rejected; live service absent |
| IMDSv2 and hop limit | PASS | Tokens required and hop limit 1 on both |
| AWS credential access by future container | INCOMPLETE | Docker absent; no container test |
| Host incoming restriction | PASS | UFW deny-incoming and operator SSH rule |
| Arbitrary outbound denial | INCOMPLETE | UFW/SG/NACL outgoing remain allow |
| Encrypted storage | FAIL | Both root EBS volumes remain unencrypted |
| Protected network telemetry | INCOMPLETE | No VPC Flow Logs; no configured trail observed |
| Audit restart durability | NOT RUN | No RAGIN service deployed |
| Emergency isolation rehearsal | INCOMPLETE | Runbook documented but not exercised live |
| No unapproved resources | PASS | Only approved IAM role/profile; no endpoint/NAT/EC2/storage resource |
| Public honeypot activation | PASS as prohibition | No Cowrie, Docker, RAGIN service, or public honeypot started |

The system is not ready for public exposure or CORE isolation cutover while any required boundary remains INCOMPLETE or FAIL.
