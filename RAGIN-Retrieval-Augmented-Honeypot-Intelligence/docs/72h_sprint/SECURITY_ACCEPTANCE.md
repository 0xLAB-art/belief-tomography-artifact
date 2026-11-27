# Security Acceptance Matrix

## Phase 2 checkpoint

- PASS: provider-backed candidate traversed isolated Cowrie, EDGE mTLS, CORE serving, mandatory verifier, and returned to the controlled SSH session.
- PASS: Cowrie container no longer uses host networking; tested access to the approved bridge forwarder succeeded while host SSH, EC2 metadata, and external connectivity test access were blocked.
- PASS: fallback provenance is now recorded as `TEMPLATE_FALLBACK_VERIFIED`; focused regression suite including the optional adapter passed 29 tests.
- INCOMPLETE: CORE private placement, encrypted EBS, complete host/Docker default-deny egress, Laya inference, public exposure, and broad effectiveness measurements.

| Control | Result | Evidence and limitation |
|---|---|---|
| Authorized SSH remains available | PASS | Fresh SSH checks to both public operator-restricted addresses |
| SSM management | PASS | Both instances Online with agent `3.3.4121.0`; private-subnet continuity not tested |
| Private CORE subnet prepared | PASS | Dedicated target subnet and local-only route verified |
| CORE actually private | FAIL | Existing CORE still has public IPv4 and direct IGW route |
| CORE public application ports | PASS for current empty host | SG/UFW expose only operator SSH; no app listener; not equivalent to private placement |
| EDGE public web ports | PASS | Existing EDGE SG has no 80/443 ingress |
| Real Ubuntu SSH replaced by Cowrie | INCOMPLETE | Staging Cowrie is loopback-only on `127.0.0.1:2222`; operator SSH remains on port 22 and public exposure is intentionally not attempted |
| mTLS authorized identity | PASS locally | Actual TLS socket through `server_v2` bridge returned 200 with correct SAN and API key |
| mTLS unauthorized identity | PASS locally | Wrong SAN 403; rogue CA and missing certificate failed handshake |
| mTLS deployed on AWS | PASS for staging | CORE `server_v2` listener on private `172.31.17.217:8443`; temporary SG/UFW source is EDGE private `/32`; not private-subnet placement |
| Mandatory verifier/fallback | PASS in controlled staging | Real CORE provenance event shows deterministic verifier accepted the served response; provider-disabled Cowrie path returned verified template behavior |
| Session ownership/replay | PASS in controlled staging | EDGE mTLS session create, command, and replay returned HTTP 200; session token remained inside test process |
| Metadata IMDSv2/hop limit | PASS current instances | Required tokens and hop limit 1 observed; future container reachability not tested |
| Arbitrary attacker egress denied | INCOMPLETE | Cowrie staging has no public exposure; permanent Docker/host egress deny policy is not yet applied |
| Encrypted EBS | FAIL | Both current root volumes report `Encrypted=false` |
| Protected durable audit delivery | INCOMPLETE | Local append-only event logs exist; protected independent delivery not deployed |
| Emergency isolation rehearsal | INCOMPLETE | Procedure exists; controlled AWS rehearsal not performed |
| Laya/NO_SIGNAL | BLOCKED | Laya not integrated by scope; no result claimed |
| Public field pilot | BLOCKED | No exposure approval, ethics gate, Cowrie isolation, or complete acceptance gate |
