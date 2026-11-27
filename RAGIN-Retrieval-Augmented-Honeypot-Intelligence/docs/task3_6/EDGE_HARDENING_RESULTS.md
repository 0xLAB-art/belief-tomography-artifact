# RAGIN Task 3.6: EDGE Hardening Results

## Verified controls

- AWS SG `sg-077b8f78668f4f646` is attached only to RAGIN-EDGE.
- Final AWS ingress is exactly TCP/22 from operator `REDACTED_OPERATOR_HOST/32`; TCP/80 and TCP/443 are absent.
- UFW is active with default deny incoming and one operator TCP/22 rule.
- SSH effective configuration disables password, keyboard-interactive, root, X11, agent forwarding, TCP forwarding, tunnels, and user environments.
- `MaxAuthTries=3`, `MaxSessions=4`, `LoginGraceTime=20`, and keepalive controls are active.
- Fresh SSH and Session Manager tests pass.
- No Docker binary, Cowrie service, or public web listener was observed.
- IMDSv2 is required with hop limit 1. The endpoint remains enabled for the attached SSM role.

## Not yet a deception boundary

Public TCP/22 still reaches Ubuntu `sshd` from the operator `/32`; this is administrative containment, not a honeypot. Cowrie must later bind the public deception endpoint while Ubuntu SSH is moved to a management-only path. That transition requires a separate controlled deployment window, container privilege/resource review, Docker socket isolation, no host shell passthrough, and a fresh positive/negative listener test.

## Rollback

Restore the captured UFW directory under `/var/backups/ragin/ufw-prestate`, disable UFW only through an independent SSM session, and restore `/var/backups/ragin/sshd-hardening-prestate*` before reloading SSH. AWS SG rollback is the captured pre-state rule set. No rollback was needed.
