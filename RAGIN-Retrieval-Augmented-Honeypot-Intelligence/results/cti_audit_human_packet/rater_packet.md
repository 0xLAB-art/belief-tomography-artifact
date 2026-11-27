# Blind Annotation Task — Independent Rater Packet

You are rating outputs of a research cyber-deception system. Packets are
blinded: no system labels, no gold answers, no model names. Work alone.
Reference taxonomy: ATT&CK Enterprise ATT&CK v19.1.
Time budget ≈ 2–3 min/item. Record your independent judgment per the
instructions; there is no reward for agreeing with any prior label.
Consent: docs/HUMAN_EVAL_CONSENT.md must be signed before this packet.

---
## R0079 (cti_technique)
**QUERY:** Use compromised SSH keys T1133 for external remote access

**SERVED_TEXT:**
```
bash: Use compromised SSH keys T1133 for external remote access: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Cozy Bear",
  "Fancy Bear",
  "Hafnium",
  "Turla",
  "Apt29"
 ],
 "ttps_seen": [
  "T1133"
 ],
 "extracted_techniques": [
  "T1133"
 ],
 "tactics": [
  "TA0001"
 ]
}
```

## R0091 (cti_technique)
**QUERY:** Modify system process via service creation T1543.001

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Modify system process via service creation T1543.001
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.1 169432 11236 ?        Ss   Mar12   0:05 /sbin/init
root       389  0.0  0.0 102276  4088 ?        S    Mar12   0:00 /lib/systemd/systemd-udevd
webapp     1234  0.2  1.5 456789 32100 ?       Sl   09:20   0:12 python3 app/server.py
www-data   5678  0.1  0.8 234567 18000 ?       S    08:00   0:03 nginx: worker process
mysql      9012  0.3  2.1 678901 45000 ?       Sl   08:00   0:15 /usr/sbin/mysqld
root       9876  0.0  0.0  20248  2604 ?        Ss   08:00   0:00 /usr/sbin/cron -f
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Cozy Bear",
  "Solarwinds",
  "Darkhotel"
 ],
 "ttps_seen": [
  "T1543"
 ],
 "extracted_techniques": [
  "T1543"
 ],
 "tactics": [
  "TA0003"
 ]
}
```

## R0121 (cti_technique)
**QUERY:** Disable Defender registry T1562.001 defense evasion

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Disable Defender registry T1562.001 defense evasion
bash: Disable Defender registry T1562.001 defense evasion: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Darkside",
  "Apt29",
  "Lazarus Group",
  "Fancy Bear",
  "Sandworm"
 ],
 "ttps_seen": [
  "T1027",
  "T1562",
  "T1562.001"
 ],
 "extracted_techniques": [
  "T1027",
  "T1562",
  "T1562.001"
 ],
 "tactics": [
  "TA0005"
 ]
}
```

## R0080 (cti_technique)
**QUERY:** Leverage default credentials T1078.001 for initial access

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ cat /home/webapp/deploy.env
APP_ENV=production
APP_HOST=web-srv-01.corp.local
DB_HOST=10.0.0.5
DB_PORT=3306
DB_NAME=appdb
DB_USER=svc_backup
DB_PASS_FILE=/home/webapp/.dbpass
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIANZNIDYVHPF56D6JK
AWS_SECRET_ACCESS_KEY=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
webapp@web-srv-01:~$ cat /home/webapp/.dbpass
KvUbKvNQoDNZOz0Bt8bG6G!7
webapp@web-srv-01:~$ 
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Hafnium",
  "Salt Typhoon",
  "Apt28",
  "Cozy Bear",
  "Fancy Bear"
 ],
 "ttps_seen": [
  "T1005",
  "T1078",
  "T1552",
  "T1566"
 ],
 "extracted_techniques": [
  "T1005",
  "T1078",
  "T1552",
  "T1566"
 ],
 "tactics": [
  "TA0001",
  "TA0009",
  "TA0006"
 ]
}
```

## R0097 (cti_technique)
**QUERY:** Disable Windows Defender T1562.001 defense evasion

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Disable Windows Defender T1562.001 defense evasion
bash: Disable Windows Defender T1562.001 defense evasion: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Darkside",
  "Apt29",
  "Lazarus Group",
  "Fancy Bear",
  "Sandworm"
 ],
 "ttps_seen": [
  "T1027",
  "T1562",
  "T1562.001"
 ],
 "extracted_techniques": [
  "T1027",
  "T1562",
  "T1562.001"
 ],
 "tactics": [
  "TA0005"
 ]
}
```

## R0029 (cti_technique)
**QUERY:** What is defense evasion via process injection?

**SERVED_TEXT:**
```
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.1 169432 11236 ?        Ss   Mar12   0:05 /sbin/init
root       389  0.0  0.0 102276  4088 ?        S    Mar12   0:00 /lib/systemd/systemd-udevd
webapp     1234  0.2  1.5 456789 32100 ?       Sl   09:20   0:12 python3 app/server.py
www-data   5678  0.1  0.8 234567 18000 ?       S    08:00   0:03 nginx: worker process
mysql      9012  0.3  2.1 678901 45000 ?       Sl   08:00   0:15 /usr/sbin/mysqld
root       9876  0.0  0.0  20248  2604 ?        Ss   08:00   0:00 /usr/sbin/cron -f
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Apt29",
  "Lazarus Group",
  "Fancy Bear",
  "Fin7",
  "Earth Lusca"
 ],
 "ttps_seen": [
  "T1027",
  "T1055",
  "T1566"
 ],
 "extracted_techniques": [
  "T1027",
  "T1055",
  "T1566"
 ],
 "tactics": [
  "TA0001",
  "TA0005",
  "TA0002"
 ]
}
```

## R0045 (cti_technique)
**QUERY:** Explain T1083 File and Directory Discovery

**SERVED_TEXT:**
```
total 44
drwxr-xr-x 3 webapp webapp 4096 Feb 20 11:04 .
drwxr-xr-x 4 root root 4096 Feb 20 11:04 ..
-rw-r--r-- 1 webapp webapp  705 Feb 20 11:02 app.config
-rw-r--r-- 1 webapp webapp  296 Feb 20 11:02 server.log
-rw-r--r-- 1 webapp webapp 1881 Feb 20 11:03 main.py
drwxr-xr-x 2 webapp webapp 4096 Feb 20 11:04 static
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Apt20",
  "Charming Kitten"
 ],
 "ttps_seen": [
  "T1046",
  "T1083"
 ],
 "extracted_techniques": [
  "T1046",
  "T1083"
 ],
 "tactics": [
  "TA0007"
 ]
}
```

## R0044 (cti_technique)
**QUERY:** What is remote system discovery in the attack chain?

**SERVED_TEXT:**
```
bash: What is remote system discovery in the attack chain?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Apt20",
  "Charming Kitten"
 ],
 "ttps_seen": [
  "T1018",
  "T1046"
 ],
 "extracted_techniques": [
  "T1018",
  "T1046"
 ],
 "tactics": [
  "TA0007"
 ]
}
```

## R0036 (cti_technique)
**QUERY:** How does credential dumping work?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ cat /home/webapp/deploy.env
APP_ENV=production
APP_HOST=web-srv-01.corp.local
DB_HOST=10.0.0.5
DB_PORT=3306
DB_NAME=appdb
DB_USER=svc_backup
DB_PASS_FILE=/home/webapp/.dbpass
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIANZNIDYVHPF56D6JK
AWS_SECRET_ACCESS_KEY=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
webapp@web-srv-01:~$ cat /home/webapp/.dbpass
KvUbKvNQoDNZOz0Bt8bG6G!7
webapp@web-srv-01:~$ 
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Carbanak",
  "Hafnium",
  "Fin7",
  "Apt37",
  "Unc3886"
 ],
 "ttps_seen": [
  "T1003",
  "T1003.008"
 ],
 "extracted_techniques": [
  "T1003",
  "T1003.008"
 ],
 "tactics": [
  "TA0006"
 ]
}
```

## R0052 (cti_technique)
**QUERY:** Explain pass the hash T1550.002 lateral movement

**SERVED_TEXT:**
```
bash: Explain pass the hash T1550.002 lateral movement: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Carbanak",
  "Hafnium",
  "Apt37",
  "Unc3886",
  "Salt Typhoon"
 ],
 "ttps_seen": [
  "T1005",
  "T1021",
  "T1550",
  "T1552"
 ],
 "extracted_techniques": [
  "T1005",
  "T1021",
  "T1550",
  "T1552"
 ],
 "tactics": [
  "TA0008",
  "TA0009",
  "TA0006"
 ]
}
```

## R0011 (cti_technique)
**QUERY:** Describe how attackers run malicious commands via command-line interface

**SERVED_TEXT:**
```
bash: Describe how attackers run malicious commands via command-line interface: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Fin7",
  "Earth Lusca",
  "Lazarus Group",
  "Revil",
  "Darkhotel"
 ],
 "ttps_seen": [
  "T1059",
  "T1204"
 ],
 "extracted_techniques": [
  "T1059",
  "T1204"
 ],
 "tactics": [
  "TA0002"
 ]
}
```

## R0065 (cti_technique)
**QUERY:** What is exfiltration over web service?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ systemctl list-units --type=service --state=running --no-legend
  cron.service                              loaded active running Regular background program processing daemon
  mysql.service                             loaded active running MySQL Community Server 8.0.33
  nginx.service                             loaded active running A high performance web server
  ssh.service                               loaded active running OpenBSD Secure Shell server

webapp@web-srv-01:~$ ss -tlnp
State      Recv-Q Send-Q Local Address:Port  Peer Address:Port Process
LISTEN     0      128    127.0.0.1:3306        0.0.0.0:*        users:(("mysqld",pid=9012,fd=15))
LISTEN     0      128    0.0.0.0:443           0.0.0.0:*        users:(("nginx",pid=5678,fd=10))
LISTEN     0      128    0.0.0.0:80            0.0.0.0:*        users:(("nginx",pid=5678,fd=10))
LISTEN     0      128    0.0.0.0:8080        0.0.0.0:*        users:(("nginx",pid=5678,fd=10))
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Apt41",
  "Darkside",
  "Revil",
  "Apt27"
 ],
 "ttps_seen": [
  "T1041",
  "T1567"
 ],
 "extracted_techniques": [
  "T1041",
  "T1567"
 ],
 "tactics": [
  "TA0010"
 ]
}
```

## R0061 (cti_technique)
**QUERY:** Describe T1071.004 Application Layer Protocol C2 via DNS

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ cat /etc/resolv.conf
nameserver 10.0.1.2
nameserver 10.0.0.2
search corp.local
options timeout:2 attempts:3
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Ghostemperor",
  "Turla",
  "Apt28",
  "Lazarus Group",
  "Fancy Bear"
 ],
 "ttps_seen": [
  "T1071"
 ],
 "extracted_techniques": [
  "T1071"
 ],
 "tactics": [
  "TA0011"
 ]
}
```

## R0058 (cti_technique)
**QUERY:** What is command and control via DNS?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ cat /etc/resolv.conf
nameserver 10.0.1.2
nameserver 10.0.0.2
search corp.local
options timeout:2 attempts:3
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Ghostemperor",
  "Turla",
  "Apt28",
  "Lazarus Group",
  "Fancy Bear"
 ],
 "ttps_seen": [
  "T1071"
 ],
 "extracted_techniques": [
  "T1071"
 ],
 "tactics": [
  "TA0011"
 ]
}
```

## R0111 (cti_technique)
**QUERY:** Steal web session cookie T1539 via network sniffing

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Steal web session cookie T1539 via network sniffing
bash: Steal web session cookie T1539 via network sniffing: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Carbanak",
  "Hafnium",
  "Fin7",
  "Apt37",
  "Unc3886"
 ],
 "ttps_seen": [
  "T1539"
 ],
 "extracted_techniques": [
  "T1539"
 ],
 "tactics": [
  "TA0006"
 ]
}
```

## R0005 (cti_technique)
**QUERY:** Explain valid accounts as an initial access technique

**SERVED_TEXT:**
```
uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm),999(docker)
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Cozy Bear",
  "Fancy Bear",
  "Hafnium",
  "Turla",
  "Apt29"
 ],
 "ttps_seen": [
  "T1078",
  "T1566"
 ],
 "extracted_techniques": [
  "T1078",
  "T1566"
 ],
 "tactics": [
  "TA0001"
 ]
}
```

## R0077 (cti_technique)
**QUERY:** Explain T1195.002 Supply Chain Compromise software supply chain

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Explain T1195.002 Supply Chain Compromise software supply chain
bash: Explain T1195.002 Supply Chain Compromise software supply chain: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Cozy Bear",
  "Fancy Bear",
  "Hafnium",
  "Turla",
  "Apt29"
 ],
 "ttps_seen": [
  "T1195",
  "T1195.002"
 ],
 "extracted_techniques": [
  "T1195",
  "T1195.002"
 ],
 "tactics": [
  "TA0001"
 ]
}
```

## R0110 (cti_technique)
**QUERY:** Keylogging T1056 for credential capture on endpoint

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ cat /home/webapp/deploy.env
APP_ENV=production
APP_HOST=web-srv-01.corp.local
DB_HOST=10.0.0.5
DB_PORT=3306
DB_NAME=appdb
DB_USER=svc_backup
DB_PASS_FILE=/home/webapp/.dbpass
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIANZNIDYVHPF56D6JK
AWS_SECRET_ACCESS_KEY=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
webapp@web-srv-01:~$ cat /home/webapp/.dbpass
KvUbKvNQoDNZOz0Bt8bG6G!7
webapp@web-srv-01:~$ 
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Carbanak",
  "Hafnium",
  "Fin7",
  "Apt37",
  "Unc3886"
 ],
 "ttps_seen": [
  "T1056"
 ],
 "extracted_techniques": [
  "T1056"
 ],
 "tactics": [
  "TA0006"
 ]
}
```

## R0093 (cti_technique)
**QUERY:** Elevate privilege T1548.001 Elevated Execution with Prompt

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ sudo -l
Matching Defaults entries for webapp on web-srv-01:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin

User webapp may run the following commands on web-srv-01:
    (root) NOPASSWD: /usr/bin/iptables
    (root) NOPASSWD: /usr/sbin/auditctl
    (root) NOPASSWD: /usr/bin/tcpdump
    (root) NOPASSWD: /usr/sbin/systemctl restart nginx
webapp@web-srv-01:~$ id
uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm),999(docker)
webapp@web-srv-01:~$ hostname -f
web-srv-01.corp.local
webapp@web-srv-01:~$ 
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [],
 "ttps_seen": [
  "T1548"
 ],
 "extracted_techniques": [
  "T1548"
 ],
 "tactics": [
  "TA0004"
 ]
}
```

## R0114 (cti_technique)
**QUERY:** Access VPN T1133 external remote services initial access

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ systemctl list-units --type=service --state=running --no-legend
  cron.service                              loaded active running Regular background program processing daemon
  mysql.service                             loaded active running MySQL Community Server 8.0.33
  nginx.service                             loaded active running A high performance web server
  ssh.service                               loaded active running OpenBSD Secure Shell server

webapp@web-srv-01:~$ ss -tlnp
State      Recv-Q Send-Q Local Address:Port  Peer Address:Port Process
LISTEN     0      128    127.0.0.1:3306        0.0.0.0:*        users:(("mysqld",pid=9012,fd=15))
LISTEN     0      128    0.0.0.0:443           0.0.0.0:*        users:(("nginx",pid=5678,fd=10))
LISTEN     0      128    0.0.0.0:80            0.0.0.0:*        users:(("nginx",pid=5678,fd=10))
LISTEN     0      128    0.0.0.0:8080        0.0.0.0:*        users:(("nginx",pid=5678,fd=10))
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Cozy Bear",
  "Hafnium",
  "Salt Typhoon",
  "Volt Typhoon",
  "Earth Lusca"
 ],
 "ttps_seen": [
  "T1021",
  "T1133",
  "T1566"
 ],
 "extracted_techniques": [
  "T1021",
  "T1133",
  "T1566"
 ],
 "tactics": [
  "TA0008",
  "TA0001"
 ]
}
```

## R0037 (cti_technique)
**QUERY:** What is brute forcing in credential access?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ cat /home/webapp/deploy.env
APP_ENV=production
APP_HOST=web-srv-01.corp.local
DB_HOST=10.0.0.5
DB_PORT=3306
DB_NAME=appdb
DB_USER=svc_backup
DB_PASS_FILE=/home/webapp/.dbpass
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIANZNIDYVHPF56D6JK
AWS_SECRET_ACCESS_KEY=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
webapp@web-srv-01:~$ cat /home/webapp/.dbpass
KvUbKvNQoDNZOz0Bt8bG6G!7
webapp@web-srv-01:~$ 
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Carbanak",
  "Hafnium",
  "Fin7",
  "Apt37",
  "Unc3886"
 ],
 "ttps_seen": [
  "T1110"
 ],
 "extracted_techniques": [
  "T1110"
 ],
 "tactics": [
  "TA0006"
 ]
}
```

## R0073 (cti_technique)
**QUERY:** What is T1586 Compromise Accounts resource development technique?

**SERVED_TEXT:**
```
bash: What is T1586 Compromise Accounts resource development technique?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [],
 "ttps_seen": [
  "T1586",
  "T1586.001"
 ],
 "extracted_techniques": [
  "T1586",
  "T1586.001"
 ],
 "tactics": [
  "TA0042"
 ]
}
```

## R0014 (cti_technique)
**QUERY:** Explain T1059.001 PowerShell command execution

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Explain T1059.001 PowerShell command execution
bash: Explain T1059.001 PowerShell command execution: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Fin7",
  "Earth Lusca",
  "Lazarus Group",
  "Revil",
  "Darkhotel"
 ],
 "ttps_seen": [
  "T1059",
  "T1059.001"
 ],
 "extracted_techniques": [
  "T1059",
  "T1059.001"
 ],
 "tactics": [
  "TA0002"
 ]
}
```

## R0043 (cti_technique)
**QUERY:** How does account discovery work on a compromised system?

**SERVED_TEXT:**
```
bash: How does account discovery work on a compromised system?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Apt20",
  "Charming Kitten"
 ],
 "ttps_seen": [
  "T1046",
  "T1087"
 ],
 "extracted_techniques": [
  "T1046",
  "T1087"
 ],
 "tactics": [
  "TA0007"
 ]
}
```

## R0063 (cti_technique)
**QUERY:** How does T1573 Encrypted Channel C2 work?

**SERVED_TEXT:**
```
bash: How does T1573 Encrypted Channel C2 work?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Ghostemperor",
  "Turla",
  "Apt28",
  "Lazarus Group",
  "Fancy Bear"
 ],
 "ttps_seen": [
  "T1573"
 ],
 "extracted_techniques": [
  "T1573"
 ],
 "tactics": [
  "TA0011"
 ]
}
```

## R0009 (cti_technique)
**QUERY:** How does supply chain compromise work T1195.002?

**SERVED_TEXT:**
```
bash: How does supply chain compromise work T1195.002?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Cozy Bear",
  "Fancy Bear",
  "Hafnium",
  "Turla",
  "Apt29"
 ],
 "ttps_seen": [
  "T1195",
  "T1195.002"
 ],
 "extracted_techniques": [
  "T1195",
  "T1195.002"
 ],
 "tactics": [
  "TA0001"
 ]
}
```

## R0048 (cti_technique)
**QUERY:** Describe the lateral movement technique T1021

**SERVED_TEXT:**
```
bash: Describe the lateral movement technique T1021: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Earth Lusca",
  "Cozy Bear",
  "Hafnium",
  "Apt37",
  "Apt27"
 ],
 "ttps_seen": [
  "T1021"
 ],
 "extracted_techniques": [
  "T1021"
 ],
 "tactics": [
  "TA0008"
 ]
}
```

## R0123 (cti_technique)
**QUERY:** Hide data in NTFS ADS T1564 alternate data stream

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Hide data in NTFS ADS T1564 alternate data stream
uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm),999(docker)
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Darkside",
  "Apt29",
  "Lazarus Group",
  "Fancy Bear",
  "Sandworm"
 ],
 "ttps_seen": [
  "T1564"
 ],
 "extracted_techniques": [
  "T1564"
 ],
 "tactics": [
  "TA0005"
 ]
}
```

## R0003 (cti_technique)
**QUERY:** What is T1190 Exploit Public-Facing Application?

**SERVED_TEXT:**
```
bash: What is T1190 Exploit Public-Facing Application?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Cozy Bear",
  "Fancy Bear",
  "Hafnium",
  "Turla",
  "Apt29"
 ],
 "ttps_seen": [
  "T1190"
 ],
 "extracted_techniques": [
  "T1190"
 ],
 "tactics": [
  "TA0001"
 ]
}
```

## R0100 (cti_technique)
**QUERY:** Obfuscate via software packing T1027.002 defense evasion

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Obfuscate via software packing T1027.002 defense evasion
bash: Obfuscate via software packing T1027.002 defense evasion: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Darkside",
  "Apt29",
  "Lazarus Group",
  "Fancy Bear",
  "Sandworm"
 ],
 "ttps_seen": [
  "T1027"
 ],
 "extracted_techniques": [
  "T1027"
 ],
 "tactics": [
  "TA0005"
 ]
}
```

## R0001 (cti_technique)
**QUERY:** Explain T1566.001 in detail

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Explain T1566.001 in detail
bash: Explain T1566.001 in detail: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Cozy Bear",
  "Fancy Bear",
  "Hafnium",
  "Turla",
  "Apt29"
 ],
 "ttps_seen": [
  "T1566"
 ],
 "extracted_techniques": [
  "T1566"
 ],
 "tactics": [
  "TA0001"
 ]
}
```

## R0006 (cti_technique)
**QUERY:** What is T1078 Valid Accounts technique?

**SERVED_TEXT:**
```
uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm),999(docker)
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Cozy Bear",
  "Fancy Bear",
  "Hafnium",
  "Turla",
  "Apt29"
 ],
 "ttps_seen": [
  "T1078"
 ],
 "extracted_techniques": [
  "T1078"
 ],
 "tactics": [
  "TA0001"
 ]
}
```

## R0017 (cti_technique)
**QUERY:** How does persistence via scheduled tasks work?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ crontab -l
# m h  dom mon dow   command
*/5 * * * * /home/webapp/scripts/healthcheck.sh
0 2 * * * /home/webapp/scripts/backup.sh /srv/backup
0 3 * * 1 logrotate /etc/logrotate.conf
@reboot /usr/local/bin/start-webapp.sh
0 0 1 * * certbot renew --quiet
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Fin7",
  "Darkhotel",
  "Earth Lusca",
  "Lazarus Group",
  "Cozy Bear"
 ],
 "ttps_seen": [
  "T1053",
  "T1547"
 ],
 "extracted_techniques": [
  "T1053",
  "T1547"
 ],
 "tactics": [
  "TA0003",
  "TA0002"
 ]
}
```

## R0128 (cti_actor)
**QUERY:** Describe FIN7's attack patterns against retail

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Describe FIN7's attack patterns against retail
bash: Describe FIN7's attack patterns against retail: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Fin7"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0149 (cti_actor)
**QUERY:** Describe LuckyMouse APT41 cyber espionage operations

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Describe LuckyMouse APT41 cyber espionage operations
bash: Describe LuckyMouse APT41 cyber espionage operations: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Apt41"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0150 (cti_actor)
**QUERY:** What is APT37 Reaper targeting South Korean media?

**SERVED_TEXT:**
```
bash: What is APT37 Reaper targeting South Korean media?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Apt37"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0140 (cti_actor)
**QUERY:** How does UNC3886 target VMware infrastructure?

**SERVED_TEXT:**
```
bash: How does UNC3886 target VMware infrastructure?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Unc3886"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0136 (cti_actor)
**QUERY:** How does Revil deploy its ransomware payload?

**SERVED_TEXT:**
```
bash: How does Revil deploy its ransomware payload?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Sandworm",
  "Revil",
  "Darkside"
 ],
 "ttps_seen": [
  "T1486"
 ],
 "extracted_techniques": [
  "T1486"
 ],
 "tactics": [
  "TA0040"
 ]
}
```

## R0154 (cti_actor)
**QUERY:** Explain APT20 targeting government and aviation sectors

**SERVED_TEXT:**
```
bash: Explain APT20 targeting government and aviation sectors: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Apt20"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0152 (cti_actor)
**QUERY:** Describe Turla group satellite-based covert C2

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Describe Turla group satellite-based covert C2
bash: Describe Turla group satellite-based covert C2: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Apt27",
  "Turla"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0125 (cti_actor)
**QUERY:** What techniques does APT28 use against government targets?

**SERVED_TEXT:**
```
bash: What techniques does APT28 use against government targets?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Apt28",
  "Fancy Bear"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0131 (cti_actor)
**QUERY:** Describe Cozy Bear's targeting of diplomatic organizations

**SERVED_TEXT:**
```
bash: Describe Cozy Bear's targeting of diplomatic organizations: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Apt29",
  "Cozy Bear"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0172 (deception)
**QUERY:** What services are currently running?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ systemctl list-units --type=service --state=running --no-legend
  cron.service                              loaded active running Regular background program processing daemon
  mysql.service                             loaded active running MySQL Community Server 8.0.33
  nginx.service                             loaded active running A high performance web server
  ssh.service                               loaded active running OpenBSD Secure Shell server

webapp@web-srv-01:~$ ss -tlnp
State      Recv-Q Send-Q Local Address:Port  Peer Address:Port Process
LISTEN     0      128    127.0.0.1:3306        0.0.0.0:*        users:(("mysqld",pid=9012,fd=15))
LISTEN     0      128    0.0.0.0:443           0.0.0.0:*        users:(("nginx",pid=5678,fd=10))
LISTEN     0      128    0.0.0.0:80            0.0.0.0:*        users:(("nginx",pid=5678,fd=10))
LISTEN     0      128    0.0.0.0:8080        0.0.0.0:*        users:(("nginx",pid=5678,fd=10))
```
**ANALYSIS:** (empty)

## R0171 (deception)
**QUERY:** Check the system logs for any recent activity

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ sudo tail -n 15 /var/log/syslog
Jun 13 08:40:01 {host} CRON[30192]: (root) CMD (command -v debian-sa1 > /dev/null && debian-sa1 1 1)
Jun 13 08:41:03 {host} sshd[29544]: Failed password for invalid user admin from 10.0.1.99 port 54321 ssh2
Jun 13 08:41:05 {host} sshd[29544]: Failed password for invalid user admin from 10.0.1.99 port 54322 ssh2
Jun 13 08:41:09 {host} sshd[29544]: Connection closed by authenticating user admin 10.0.1.99 port 54323 [preauth]
Jun 13 08:42:17 {host} nginx[5678]: 10.0.1.66 - - [13/Jun/2024:08:42:17 +0000] "GET /admin/login HTTP/1.1" 404 490 "-" "curl/8.3.0"
```
**ANALYSIS:** (empty)

## R0191 (deception)
**QUERY:** What is the current ulimit setting for open file descriptors on this system?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ ulimit -a
core file size          (blocks, -c) 0
data seg size           (kbytes, -d) unlimited
scheduling priority             (-e) 0
file size               (blocks, -f) unlimited
virtual memory          (kbytes, -v) unlimited
open files                      (-n) 1024
max user processes              (-u) 65535
stack size              (kbytes, -s) 8192
```
**ANALYSIS:** (empty)

## R0190 (deception)
**QUERY:** Show me the nginx access log filtered for 5xx error codes in the last hour

**SERVED_TEXT:**
```
webapp    pts/0        2024-06-13 08:42   (10.0.1.55)
root    pts/1        2024-06-13 07:10   (10.0.1.66)
www-data  pts/2       2024-06-12 22:01   (172.16.0.12)

wtmp begins Thu Jun 13 07:10:34 2024
```
**ANALYSIS:** (empty)

## R0186 (deception)
**QUERY:** Check if there are any unrecognized cron jobs in /etc/cron.d/ directories

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ crontab -l
# m h  dom mon dow   command
*/5 * * * * /home/webapp/scripts/healthcheck.sh
0 2 * * * /home/webapp/scripts/backup.sh /srv/backup
0 3 * * 1 logrotate /etc/logrotate.conf
@reboot /usr/local/bin/start-webapp.sh
0 0 1 * * certbot renew --quiet
```
**ANALYSIS:** (empty)

## R0213 (deception)
**QUERY:** Show audit log entries for privilege escalation attempts last week

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ sudo -l
Matching Defaults entries for webapp on web-srv-01:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin

User webapp may run the following commands on web-srv-01:
    (root) NOPASSWD: /usr/bin/iptables
    (root) NOPASSWD: /usr/sbin/auditctl
    (root) NOPASSWD: /usr/bin/tcpdump
    (root) NOPASSWD: /usr/sbin/systemctl restart nginx
webapp@web-srv-01:~$ id
uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm),999(docker)
webapp@web-srv-01:~$ hostname -f
web-srv-01.corp.local
webapp@web-srv-01:~$ 
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Apt29",
  "Fancy Bear",
  "Volt Typhoon",
  "Apt28",
  "Lazarus Group"
 ],
 "ttps_seen": [
  "T1078",
  "T1134",
  "T1548"
 ],
 "extracted_techniques": [
  "T1078",
  "T1134",
  "T1548"
 ],
 "tactics": [
  "TA0004",
  "TA0001",
  "TA0005"
 ]
}
```

## R0211 (deception)
**QUERY:** Is SELinux enforcing and what contexts do web files have?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ getenforce
Enforcing
webapp@web-srv-01:~$ sestatus
SELinux status:                 enabled
SELinuxfs mount:                /sys/fs/selinux
SELinux root directory:         /etc/selinux
Loaded policy name:             targeted
Current mode:                   enforcing
Mode from config file:          enforcing
```
**ANALYSIS:** (empty)

## R0180 (deception)
**QUERY:** How do I generate a packet capture for the last 5 minutes on interface eth0?

**SERVED_TEXT:**
```
webapp    pts/0        2024-06-13 08:42   (10.0.1.55)
root    pts/1        2024-06-13 07:10   (10.0.1.66)
www-data  pts/2       2024-06-12 22:01   (172.16.0.12)

wtmp begins Thu Jun 13 07:10:34 2024
```
**ANALYSIS:** (empty)

## R0162 (deception)
**QUERY:** Do you have any databases accessible?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ ss -tlnp
State      Recv-Q Send-Q Local Address:Port  Peer Address:Port Process
LISTEN     0      128    127.0.0.1:3306        0.0.0.0:*        users:(("mysqld",pid=9012,fd=15))
LISTEN     0      128    127.0.0.1:5432        0.0.0.0:*        users:(("postgres",pid=1123,fd=13))
LISTEN     0      128    0.0.0.0:8080        0.0.0.0:*        users:(("nginx",pid=5678,fd=10))
LISTEN     0      128    127.0.0.1:6379        0.0.0.0:*        users:(("redis-server",pid=4455,fd=7))
```
**ANALYSIS:** (empty)

## R0179 (deception)
**QUERY:** List all Docker containers currently running and their resource usage

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ docker ps -a
CONTAINER ID   IMAGE                          COMMAND                  CREATED        STATUS                       PORTS     NAMES
a1b2c3d4e5f6   mysql:8.0                       "docker-entrypoint.s…"   3 months ago   Up 3 months                  3306/tcp    db-primary
b2c3d4e5f6a7   redis:7-alpine                   "docker-entrypoint.s…"   3 months ago   Up 3 months                  6379/tcp    cache
c3d4e5f6a7b8   nginx:1.18-alpine                "nginx -g 'daemon of…"   3 months ago   Exited (0) 2 weeks ago                  web-proxy-old
```
**ANALYSIS:** (empty)

## R0165 (deception)
**QUERY:** What patches have been applied recently?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ apt list --upgradable
Listing...
openssl/jammy-updates 3.0.2-0ubuntu1.18 amd64 [upgradable from: 3.0.2-0ubuntu1.12]
nginx/jammy-updates 1.18.0-6ubuntu14.4 amd64 [upgradable from: 1.18.0-6ubuntu14.1]
sudo/jammy-security 1.9.9p1-2ubuntu2.4 amd64 [upgradable from: 1.9.9p1-2ubuntu2.2]

Installed patches:
USN-6270-1: OpenSSL 3.0.2-0ubuntu1.18 (2024-02-13)
USN-6215-1: nginx 1.18.0-6ubuntu14.4 (2024-01-22)
```
**ANALYSIS:** (empty)

## R0174 (deception)
**QUERY:** Can you check if there are any suspicious scheduled tasks on this server?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ crontab -l
# m h  dom mon dow   command
*/5 * * * * /home/webapp/scripts/healthcheck.sh
0 2 * * * /home/webapp/scripts/backup.sh /srv/backup
0 3 * * 1 logrotate /etc/logrotate.conf
@reboot /usr/local/bin/start-webapp.sh
0 0 1 * * certbot renew --quiet
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Fin7",
  "Earth Lusca",
  "Lazarus Group",
  "Revil",
  "Darkhotel"
 ],
 "ttps_seen": [
  "T1053"
 ],
 "extracted_techniques": [
  "T1053"
 ],
 "tactics": [
  "TA0002"
 ]
}
```

## R0199 (deception)
**QUERY:** Show me the last 10 lines of /var/log/syslog filtered for kernel errors

**SERVED_TEXT:**
```
webapp    pts/0        2024-06-13 08:42   (10.0.1.55)
root    pts/1        2024-06-13 07:10   (10.0.1.66)
www-data  pts/2       2024-06-12 22:01   (172.16.0.12)

wtmp begins Thu Jun 13 07:10:34 2024
```
**ANALYSIS:** (empty)

## R0175 (deception)
**QUERY:** I need to find all files modified in the last 24 hours on this system

**SERVED_TEXT:**
```
webapp    pts/0        2024-06-13 08:42   (10.0.1.55)
root    pts/1        2024-06-13 07:10   (10.0.1.66)
www-data  pts/2       2024-06-12 22:01   (172.16.0.12)

wtmp begins Thu Jun 13 07:10:34 2024
```
**ANALYSIS:** (empty)

## R0166 (deception)
**QUERY:** Show me the running processes on this machine

**SERVED_TEXT:**
```
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.1 169432 11236 ?        Ss   Mar12   0:05 /sbin/init
root       389  0.0  0.0 102276  4088 ?        S    Mar12   0:00 /lib/systemd/systemd-udevd
webapp     1234  0.2  1.5 456789 32100 ?       Sl   09:20   0:12 python3 app/server.py
www-data   5678  0.1  0.8 234567 18000 ?       S    08:00   0:03 nginx: worker process
mysql      9012  0.3  2.1 678901 45000 ?       Sl   08:00   0:15 /usr/sbin/mysqld
root       9876  0.0  0.0  20248  2604 ?        Ss   08:00   0:00 /usr/sbin/cron -f
```
**ANALYSIS:** (empty)

## R0209 (deception)
**QUERY:** What third-party packages are installed and their versions?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ dpkg -l | grep -E '^ii' | head -12
ii  openssl                   3.0.2-0ubuntu1.18            amd64  Secure Sockets Layer toolkit - cryptographic utility
ii  python3                    3.10.12-1~22.04.3            amd64  Interactive high-level object-oriented language
ii  nginx                      1.18.0-6ubuntu14.4           amd64  small, powerful, scalable web/proxy server
ii  mysql-server-8.0           8.0.33-0ubuntu0.22.04.1      amd64  MySQL database server (metapackage)
ii  redis-server               6.0.16-1ubuntu0.22.04.1      amd64  Persistent key-value database
ii  ufw                        0.36.2-1ubuntu1              amd64  program for managing a Netfilter firewall
```
**ANALYSIS:** (empty)

## R0195 (deception)
**QUERY:** Can you verify the integrity of the passwd and shadow files using md5sum?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ cat /home/webapp/deploy.env
APP_ENV=production
APP_HOST=web-srv-01.corp.local
DB_HOST=10.0.0.5
DB_PORT=3306
DB_NAME=appdb
DB_USER=svc_backup
DB_PASS_FILE=/home/webapp/.dbpass
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIANZNIDYVHPF56D6JK
AWS_SECRET_ACCESS_KEY=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
webapp@web-srv-01:~$ cat /home/webapp/.dbpass
KvUbKvNQoDNZOz0Bt8bG6G!7
webapp@web-srv-01:~$ 
```
**ANALYSIS:** (empty)

## R0160 (deception)
**QUERY:** Tell me about your network configuration

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ ip addr show eth0
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    link/ether 0a:58:ac:1f:0c:66 brd ff:ff:ff:ff:ff:ff
    inet 10.0.0.12/24 brd 10.0.1.255 scope global dynamic eth0
    valid_lft 84600sec preferred_lft 84600sec
    3: eth1: <BROADCAST,MULTICAST,UP> mtu 1500 qdisc mq state UP group default qlen 1000
    inet 172.16.0.5/16 scope global eth1
```
**ANALYSIS:** (empty)
