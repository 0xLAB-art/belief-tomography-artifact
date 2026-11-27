# CTI Manual Audit — Annotation Packet

Reference taxonomy: ATT&CK Enterprise ATT&CK v19.1 (bundle sha256 bdf1ce86a4e60421…, modified 2026-05-12T14:00:00.188Z).

For each item below, record independently:
1. **requested** — the ATT&CK technique ID (or threat actor) the QUERY is about,
   judged from the query text alone; `unclear` if genuinely ambiguous.
2. **identified** — the technique IDs / actor names present in the ANALYSIS record.
3. **identification** — correct / partial / incorrect / not_attempted
   (partial = right family but not the precise sub-technique, or the right
   technique buried among unrelated extras).
4. **served_on_topic** — yes / partial / no: does the SERVED TEXT by itself
   address the query (a machine transcript, refusal, or explanation all count;
   judge topical relevance, not style).
5. For deception items: **realism** — realistic / partial / unrealistic, and
   whether the text reads like authentic machine output.

---

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

## R0015 (cti_technique)
**QUERY:** What is T1203 Exploitation for Client Execution?

**SERVED_TEXT:**
```
bash: What is T1203 Exploitation for Client Execution?: command not found
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
  "T1068",
  "T1203"
 ],
 "extracted_techniques": [
  "T1068",
  "T1203"
 ],
 "tactics": [
  "TA0002",
  "TA0004"
 ]
}
```

## R0159 (deception)
**QUERY:** What web server are you running?

**SERVED_TEXT:**
```
HTTP/1.1 200 OK
Server: nginx/1.18.0 (Ubuntu)
Date: Thu, 13 Jun 2024 08:42:17 GMT
Content-Type: text/html; charset=UTF-8
Connection: keep-alive
VirtualHost: web-srv-01
DocumentRoot: /var/www/html
```
**ANALYSIS:** (empty)

## R0007 (cti_technique)
**QUERY:** Explain T1566.002 spear phishing via link

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Explain T1566.002 spear phishing via link
bash: Explain T1566.002 spear phishing via link: command not found
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

## R0054 (cti_technique)
**QUERY:** Describe collection via screen capture

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ sudo tcpdump -i eth0 -n -c 5
tcpdump: verbose output suppressed, use -v or -vv for full protocol decode
listening on eth0, link-type EN10MB (Ethernet), capture size 262144 bytes
14:22:31.123456 IP 10.0.1.66.41012 > 10.0.1.2.53: 12345+ A? update.corp.local. (39)
14:22:31.127744 IP 10.0.1.2.53 > 10.0.1.66.41012: 12345 1/0/0 A 10.0.1.2 (55)
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
  "T1113"
 ],
 "extracted_techniques": [
  "T1113"
 ],
 "tactics": [
  "TA0007"
 ]
}
```

## R0163 (deception)
**QUERY:** What OS is installed on the servers?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ cat /etc/os-release
PRETTY_NAME="Ubuntu 22.04.3 LTS"
NAME="Ubuntu"
VERSION_ID="22.04"
VERSION="22.04.3 LTS (Jammy Jellyfish)"
ID=ubuntu
webapp@web-srv-01:~$ uname -r
5.15.0-91-generic
```
**ANALYSIS:** (empty)

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

## R0200 (deception)
**QUERY:** List all cron jobs that run as root across system crontab and cron.d/

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

## R0075 (cti_technique)
**QUERY:** What is T1588 Obtain Capabilities resource development?

**SERVED_TEXT:**
```
bash: What is T1588 Obtain Capabilities resource development?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [],
 "ttps_seen": [
  "T1586",
  "T1586.001",
  "T1588"
 ],
 "extracted_techniques": [
  "T1586",
  "T1586.001",
  "T1588"
 ],
 "tactics": [
  "TA0042"
 ]
}
```

## R0069 (cti_technique)
**QUERY:** What is service stop as an impact technique?

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
  "Sandworm",
  "Revil",
  "Darkside"
 ],
 "ttps_seen": [
  "T1486",
  "T1489"
 ],
 "extracted_techniques": [
  "T1486",
  "T1489"
 ],
 "tactics": [
  "TA0040"
 ]
}
```

## R0173 (deception)
**QUERY:** Show me the SSH configuration

**SERVED_TEXT:**
```
bash: Show me the SSH configuration: command not found
```
**ANALYSIS:** (empty)

## R0025 (cti_technique)
**QUERY:** How does exploitation for privilege escalation work?

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
  "T1068",
  "T1078",
  "T1134",
  "T1548"
 ],
 "extracted_techniques": [
  "T1068",
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

## R0112 (cti_technique)
**QUERY:** Forge Kerberos TGT T1558 golden ticket attack

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Forge Kerberos TGT T1558 golden ticket attack
bash: Forge Kerberos TGT T1558 golden ticket attack: command not found
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
  "T1558"
 ],
 "extracted_techniques": [
  "T1558"
 ],
 "tactics": [
  "TA0006"
 ]
}
```

## R0184 (deception)
**QUERY:** Show me all environment variables that contain API keys or tokens

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ env
HOSTNAME=web-srv-01
TERM=xterm-256color
SHELL=/bin/bash
USER=webapp
HOME=/home/webapp
LOGNAME=webapp
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
LANG=en_US.UTF-8
PWD=/home/webapp
DATABASE_URL=mysql://app:********@127.0.0.1:3306/appdb
API_TOKEN=gsk_abcd1234efgh5678ijklmno9pqrs0tuv
webapp@web-srv-01:~$ echo $PATH
/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```
**ANALYSIS:** (empty)

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

## R0039 (cti_technique)
**QUERY:** Describe T1003.001 OS Credential Dumping LSASS memory

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

## R0051 (cti_technique)
**QUERY:** What is T1021 Remote Services lateral movement?

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

## R0022 (cti_technique)
**QUERY:** What is T1053.005 Scheduled Task persistence?

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

## R0038 (cti_technique)
**QUERY:** Explain OS Credential Dumping T1003

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

## R0113 (cti_technique)
**QUERY:** Extract credentials from password manager T1555

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
  "T1005",
  "T1552",
  "T1555"
 ],
 "extracted_techniques": [
  "T1005",
  "T1552",
  "T1555"
 ],
 "tactics": [
  "TA0009",
  "TA0006"
 ]
}
```

## R0196 (deception)
**QUERY:** Show all established connections to port 3306 MySQL from which source IPs?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ ss -tan
State      Recv-Q Send-Q Local Address:Port        Peer Address:Port Process
LISTEN     0      128    127.0.0.1:3306              0.0.0.0:*
LISTEN     0      128    0.0.0.0:80                  0.0.0.0:*
ESTAB      0      0      10.0.2.51:443               10.0.1.66:51234
ESTAB      0      0      10.0.2.51:443               10.0.1.55:39876
TIME_WAIT  0      0      10.0.2.51:443               10.0.1.99:54321
TIME_WAIT  0      0      10.0.2.51:443               10.0.1.99:54322
```
**ANALYSIS:** (empty)

## R0167 (deception)
**QUERY:** What users are currently logged in?

**SERVED_TEXT:**
```
webapp    pts/0        2024-06-13 08:42   (10.0.1.55)
root    pts/1        2024-06-13 07:10   (10.0.1.66)
www-data  pts/2       2024-06-12 22:01   (172.16.0.12)

wtmp begins Thu Jun 13 07:10:34 2024
```
**ANALYSIS:** (empty)

## R0115 (cti_technique)
**QUERY:** Compromise software supply chain T1195 build system

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Compromise software supply chain T1195 build system
bash: Compromise software supply chain T1195 build system: command not found
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
  "T1195"
 ],
 "extracted_techniques": [
  "T1195"
 ],
 "tactics": [
  "TA0001"
 ]
}
```

## R0169 (deception)
**QUERY:** Show me the network interfaces and their configurations

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ ip link show
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP mode DEFAULT group default qlen 1000
    link/ether 0a:58:ac:1f:0c:66 brd ff:ff:ff:ff:ff:ff
3: eth1: <BROADCAST,MULTICAST,UP> mtu 1500 qdisc mq state UP mode DEFAULT group default qlen 1000
    link/ether 0a:58:ac:1f:0d:77 brd ff:ff:ff:ff:ff:ff
webapp@web-srv-01:~$ ip addr show eth0
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    inet 10.0.0.12/24 brd 10.0.1.255 scope global dynamic eth0
    valid_lft 84600sec preferred_lft 84600sec
    inet6 fe80::58:acff:fe1f:c66/64 scope link
```
**ANALYSIS:** (empty)

## R0053 (cti_technique)
**QUERY:** How does T1021.002 SMB/Windows Admin Share lateral movement work?

**SERVED_TEXT:**
```
bash: How does T1021.002 SMB/Windows Admin Share lateral movement work?: command not found
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

## R0068 (cti_technique)
**QUERY:** How does impact via data encryption work?

**SERVED_TEXT:**
```
bash: How does impact via data encryption work?: command not found
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

## R0181 (deception)
**QUERY:** Show me the current iptables rules with packet and byte counters

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ sudo iptables -L -v -n --line-numbers
Chain INPUT (policy DROP 0 packets, 0 bytes)
num   pkts bytes target     prot opt in     out     source               destination
1       843 51204 ACCEPT     all  --  lo     *       0.0.0.0/0            0.0.0.0/0
2      102 6120  ACCEPT     tcp  --  eth0   *       0.0.0.0/0            0.0.0.0/0            tcp dpt:22
3      207 18360 ACCEPT     tcp  --  eth0   *       0.0.0.0/0            0.0.0.0/0            tcp dpt:443
4        0     0 ACCEPT     tcp  --  eth0   *       0.0.0.0/0            0.0.0.0/0            tcp dpt:8080
5     3124 172K  DROP       all  --  eth0   *       0.0.0.0/0            0.0.0.0/0
```
**ANALYSIS:** (empty)

## R0210 (deception)
**QUERY:** Show all listening ports and their bound processes

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

## R0118 (cti_technique)
**QUERY:** Target managed service provider T1199 initial access

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
  "Fancy Bear",
  "Hafnium",
  "Turla",
  "Apt29"
 ],
 "ttps_seen": [
  "T1199",
  "T1566"
 ],
 "extracted_techniques": [
  "T1199",
  "T1566"
 ],
 "tactics": [
  "TA0001"
 ]
}
```

## R0095 (cti_technique)
**QUERY:** Exploit vulnerable driver T1210 escalation vector

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
  "Earth Lusca",
  "Cozy Bear",
  "Hafnium",
  "Apt37",
  "Apt27"
 ],
 "ttps_seen": [
  "T1210"
 ],
 "extracted_techniques": [
  "T1210"
 ],
 "tactics": [
  "TA0008"
 ]
}
```

## R0178 (deception)
**QUERY:** Check the syslog for any authentication error patterns from the last day

**SERVED_TEXT:**
```
webapp    pts/0        2024-06-13 08:42   (10.0.1.55)
root    pts/1        2024-06-13 07:10   (10.0.1.66)
www-data  pts/2       2024-06-12 22:01   (172.16.0.12)

wtmp begins Thu Jun 13 07:10:34 2024
```
**ANALYSIS:** (empty)

## R0092 (cti_technique)
**QUERY:** Persistence via T1574 Hijack Execution Flow DLL side-load

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Persistence via T1574 Hijack Execution Flow DLL side-load
uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm),999(docker)
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Cozy Bear",
  "Earth Lusca",
  "Hafnium",
  "Apt37",
  "Apt27"
 ],
 "ttps_seen": [
  "T1547",
  "T1574"
 ],
 "extracted_techniques": [
  "T1547",
  "T1574"
 ],
 "tactics": [
  "TA0003",
  "TA0008"
 ]
}
```

## R0094 (cti_technique)
**QUERY:** Bypass UAC via T1548.003 for privilege escalation

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

## R0183 (deception)
**QUERY:** Check if there are any kernel modules that were loaded recently

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ lsmod
Module                  Size  Used by
nf_nat_ipv4            16384  2
iptable_nat            24576  1
overlay               116736  10
br_netfilter           28672  0
webapp@web-srv-01:~$ dmesg | tail -5
[ 1234.567890] audit: type=1400 audit(1718241203.123:456): apparmor="ALLOWED" operation="open" profile="nginx" name="/var/log/nginx/access.log"
[ 1234.782345] device eth0 entered promiscuous mode
```
**ANALYSIS:** (empty)

## R0033 (cti_technique)
**QUERY:** Describe T1140 Deobfuscate Decode Data for defense evasion

**SERVED_TEXT:**
```
bash: Describe T1140 Deobfuscate Decode Data for defense evasion: command not found
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
  "T1140"
 ],
 "extracted_techniques": [
  "T1027",
  "T1140"
 ],
 "tactics": [
  "TA0005"
 ]
}
```

## R0189 (deception)
**QUERY:** Can you check the /var/log/auth.log for failed SSH login attempts from external IPs?

**SERVED_TEXT:**
```
bash: Can you check the /var/log/auth.log for failed SSH login attempts from external IPs?: command not found
```
**ANALYSIS:** (empty)

## R0204 (deception)
**QUERY:** List all active firewall rules with hit counts

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ sudo iptables -L -n
Chain INPUT (policy DROP 0 packets, 0 bytes)
    pkts      bytes target     prot opt in     out     source               destination
    12      1420 ACCEPT     all  --  lo     *       0.0.0.0/0            0.0.0.0/0
     0         0 ACCEPT     tcp  --  eth0   *       0.0.0.0/0            0.0.0.0/0            tcp dpt:22
     0         0 ACCEPT     tcp  --  eth0   *       0.0.0.0/0            0.0.0.0/0            tcp dpt:443
     0         0 ACCEPT     tcp  --  eth0   *       0.0.0.0/0            0.0.0.0/0            tcp dpt:8080
     0         0 LOG        all  --  *      *       0.0.0.0/0            0.0.0.0/0            LOG flags 0 level 4 prefix '[UFW BLOCK] '
    34      9972 REJECT     all  --  eth0   *       0.0.0.0/0            0.0.0.0/0            reject-with icmp-port-unreachable
```
**ANALYSIS:** (empty)

## R0055 (cti_technique)
**QUERY:** What is data from local system collection?

**SERVED_TEXT:**
```
bash: What is data from local system collection?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [],
 "ttps_seen": [
  "T1005"
 ],
 "extracted_techniques": [
  "T1005"
 ],
 "tactics": [
  "TA0009"
 ]
}
```

## R0064 (cti_technique)
**QUERY:** How does exfiltration over HTTPS work?

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
  "Apt41",
  "Darkside",
  "Revil",
  "Apt27"
 ],
 "ttps_seen": [
  "T1041"
 ],
 "extracted_techniques": [
  "T1041"
 ],
 "tactics": [
  "TA0010"
 ]
}
```

## R0040 (cti_technique)
**QUERY:** How does password brute forcing T1110 work?

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
  "T1005",
  "T1110",
  "T1552"
 ],
 "extracted_techniques": [
  "T1005",
  "T1110",
  "T1552"
 ],
 "tactics": [
  "TA0009",
  "TA0006"
 ]
}
```

## R0012 (cti_technique)
**QUERY:** What is T1059 Command and Scripting Interpreter?

**SERVED_TEXT:**
```
bash: What is T1059 Command and Scripting Interpreter?: command not found
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
  "T1059"
 ],
 "extracted_techniques": [
  "T1059"
 ],
 "tactics": [
  "TA0002"
 ]
}
```

## R0013 (cti_technique)
**QUERY:** How does power shell execution work for attackers?

**SERVED_TEXT:**
```
bash: How does power shell execution work for attackers?: command not found
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

## R0148 (cti_actor)
**QUERY:** Explain APT50 targeting South Asian governments

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Explain APT50 targeting South Asian governments
bash: Explain APT50 targeting South Asian governments: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Apt50"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0182 (deception)
**QUERY:** What is the disk I/O wait percentage and which process is using the most I/O?

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

## R0085 (cti_technique)
**QUERY:** Execute Python script T1059 for command and scripting

**SERVED_TEXT:**
```
bash: Execute Python script T1059 for command and scripting: command not found
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
  "T1059"
 ],
 "extracted_techniques": [
  "T1059"
 ],
 "tactics": [
  "TA0002"
 ]
}
```

## R0133 (cti_actor)
**QUERY:** How does Hafnium target on-premises Exchange servers?

**SERVED_TEXT:**
```
bash: How does Hafnium target on-premises Exchange servers?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Hafnium"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0206 (deception)
**QUERY:** What is the current load average compared to baseline?

**SERVED_TEXT:**
```
 08:47:12 up 87 days, 14:23,  3 users,  load average: 0.21, 0.34, 0.41
webapp@web-srv-01:~$ cat /proc/loadavg
0.21 0.34 0.41 1/456 30192
```
**ANALYSIS:** (empty)

## R0218 (deception)
**QUERY:** Are there any known vulnerable packages needing immediate patches?

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

## R0198 (deception)
**QUERY:** Check whether any cron job has been modified in the last 7 days across all users

**SERVED_TEXT:**
```
webapp    pts/0        2024-06-13 08:42   (10.0.1.55)
root    pts/1        2024-06-13 07:10   (10.0.1.66)
www-data  pts/2       2024-06-12 22:01   (172.16.0.12)

wtmp begins Thu Jun 13 07:10:34 2024
```
**ANALYSIS:** (empty)

## R0072 (cti_technique)
**QUERY:** Explain resource development using compromised accounts

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Explain resource development using compromised accounts
bash: Explain resource development using compromised accounts: command not found
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

## R0076 (cti_technique)
**QUERY:** How does initial access via supply chain compromise work?

**SERVED_TEXT:**
```
bash: How does initial access via supply chain compromise work?: command not found
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
  "T1566"
 ],
 "extracted_techniques": [
  "T1195",
  "T1566"
 ],
 "tactics": [
  "TA0001"
 ]
}
```

## R0134 (cti_actor)
**QUERY:** Describe Sandworm's destructive attack patterns

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Describe Sandworm's destructive attack patterns
bash: Describe Sandworm's destructive attack patterns: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Sandworm"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0082 (cti_technique)
**QUERY:** Exploit client app for execution via browser T1203

**SERVED_TEXT:**
```
bash: Exploit client app for execution via browser T1203: command not found
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
  "T1203"
 ],
 "extracted_techniques": [
  "T1203"
 ],
 "tactics": [
  "TA0002"
 ]
}
```

## R0137 (cti_actor)
**QUERY:** Describe APT37's targeting of South Korean organizations

**SERVED_TEXT:**
```
bash: Describe APT37's targeting of South Korean organizations: command not found
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

## R0101 (cti_technique)
**QUERY:** Compile HTML file T1204.001 client-side execution

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Compile HTML file T1204.001 client-side execution
uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm),999(docker)
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
  "T1204",
  "T1204.001"
 ],
 "extracted_techniques": [
  "T1204",
  "T1204.001"
 ],
 "tactics": [
  "TA0002"
 ]
}
```

## R0205 (deception)
**QUERY:** Check for unauthorized SSH keys in authorized_keys files

**SERVED_TEXT:**
```
bash: Check for unauthorized SSH keys in authorized_keys files: command not found
```
**ANALYSIS:** (empty)

## R0217 (deception)
**QUERY:** Which users have sudo access and their last sudo timestamps?

**SERVED_TEXT:**
```
webapp    pts/0        2024-06-13 08:42   (10.0.1.55)
root    pts/1        2024-06-13 07:10   (10.0.1.66)
www-data  pts/2       2024-06-12 22:01   (172.16.0.12)

wtmp begins Thu Jun 13 07:10:34 2024
```
**ANALYSIS:** (empty)

## R0156 (cti_actor)
**QUERY:** What is Charming Kitten targeting diplomats and activists?

**SERVED_TEXT:**
```
bash: What is Charming Kitten targeting diplomats and activists?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Charming Kitten"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0147 (cti_actor)
**QUERY:** What is Earth Lusca targeting APAC telecoms?

**SERVED_TEXT:**
```
bash: What is Earth Lusca targeting APAC telecoms?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Earth Lusca"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0142 (cti_actor)
**QUERY:** Explain APT32 OceanLotus targeting Vietnam

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Explain APT32 OceanLotus targeting Vietnam
bash: Explain APT32 OceanLotus targeting Vietnam: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Oceanlotus"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0035 (cti_technique)
**QUERY:** Explain indicator blocking as defense evasion T1562

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Explain indicator blocking as defense evasion T1562
bash: Explain indicator blocking as defense evasion T1562: command not found
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
  "T1562"
 ],
 "extracted_techniques": [
  "T1027",
  "T1562"
 ],
 "tactics": [
  "TA0005"
 ]
}
```

## R0062 (cti_technique)
**QUERY:** Explain T1102 Web Service C2 for command and control

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
  "Ghostemperor",
  "Turla",
  "Apt28",
  "Lazarus Group",
  "Fancy Bear"
 ],
 "ttps_seen": [
  "T1071",
  "T1102"
 ],
 "extracted_techniques": [
  "T1071",
  "T1102"
 ],
 "tactics": [
  "TA0011"
 ]
}
```

## R0139 (cti_actor)
**QUERY:** Describe UNC2452 SolarWinds supply chain attack

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Describe UNC2452 SolarWinds supply chain attack
bash: Describe UNC2452 SolarWinds supply chain attack: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Solarwinds",
  "Cozy Bear",
  "Fancy Bear",
  "Hafnium",
  "Turla"
 ],
 "ttps_seen": [
  "T1195"
 ],
 "extracted_techniques": [
  "T1195"
 ],
 "tactics": [
  "TA0001"
 ]
}
```

## R0145 (cti_actor)
**QUERY:** How does Transparent Tribe APT36 target Indian defense?

**SERVED_TEXT:**
```
bash: How does Transparent Tribe APT36 target Indian defense?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Apt36"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0127 (cti_actor)
**QUERY:** What is Volt Typhoon's approach to critical infrastructure?

**SERVED_TEXT:**
```
bash: What is Volt Typhoon's approach to critical infrastructure?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Volt Typhoon"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0049 (cti_technique)
**QUERY:** How does remote services facilitate lateral movement?

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

## R0105 (cti_technique)
**QUERY:** DCSync dump T1003.006 domain credential access

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
  "T1003"
 ],
 "extracted_techniques": [
  "T1003"
 ],
 "tactics": [
  "TA0006"
 ]
}
```

## R0106 (cti_technique)
**QUERY:** Extract hashes from stores T1003.007 password stores

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
  "T1005",
  "T1552"
 ],
 "extracted_techniques": [
  "T1003",
  "T1005",
  "T1552"
 ],
 "tactics": [
  "TA0009",
  "TA0006"
 ]
}
```

## R0027 (cti_technique)
**QUERY:** Explain T1068 Exploitation for Privilege Escalation

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
  "T1068",
  "T1078",
  "T1134",
  "T1548"
 ],
 "extracted_techniques": [
  "T1068",
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

## R0060 (cti_technique)
**QUERY:** What is encrypted channel for command and control?

**SERVED_TEXT:**
```
bash: What is encrypted channel for command and control?: command not found
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
  "T1071",
  "T1573"
 ],
 "extracted_techniques": [
  "T1071",
  "T1573"
 ],
 "tactics": [
  "TA0011"
 ]
}
```

## R0124 (cti_actor)
**QUERY:** Describe Salt Typhoon's targeting of telecommunications

**SERVED_TEXT:**
```
bash: Describe Salt Typhoon's targeting of telecommunications: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Salt Typhoon"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0197 (deception)
**QUERY:** What is the current swap usage and which processes are contributing most?

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

## R0155 (cti_actor)
**QUERY:** Describe APT43 state-sponsored cybercrime operations

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Describe APT43 state-sponsored cybercrime operations
bash: Describe APT43 state-sponsored cybercrime operations: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Apt43"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0201 (deception)
**QUERY:** What is the current TCP congestion control algorithm and queue discipline?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ sysctl net.ipv4.tcp_congestion_control net.core.default_qdisc
net.ipv4.tcp_congestion_control = cubic
net.core.default_qdisc = fq_codel
```
**ANALYSIS:** (empty)

## R0132 (cti_actor)
**QUERY:** What is Fancy Bear's approach to military networks?

**SERVED_TEXT:**
```
bash: What is Fancy Bear's approach to military networks?: command not found
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

## R0177 (deception)
**QUERY:** What are the current network connections and which processes own them?

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

## R0086 (cti_technique)
**QUERY:** Use RDP execution T1021.001 for remote command execution

**SERVED_TEXT:**
```
bash: Use RDP execution T1021.001 for remote command execution: command not found
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

## R0002 (cti_technique)
**QUERY:** How does spear phishing work?

**SERVED_TEXT:**
```
bash: How does spear phishing work?: command not found
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

## R0143 (cti_actor)
**QUERY:** Describe APT38 Lazarus Group financial theft from banks

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Describe APT38 Lazarus Group financial theft from banks
bash: Describe APT38 Lazarus Group financial theft from banks: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Lazarus Group"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0141 (cti_actor)
**QUERY:** What is DarkHotel group targeting travelers and hotels?

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
  "Darkhotel"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0215 (deception)
**QUERY:** What is the current system uptime and last reboot time?

**SERVED_TEXT:**
```
webapp    pts/0        2024-06-13 08:42   (10.0.1.55)
root    pts/1        2024-06-13 07:10   (10.0.1.66)
www-data  pts/2       2024-06-12 22:01   (172.16.0.12)

wtmp begins Thu Jun 13 07:10:34 2024
```
**ANALYSIS:** (empty)

## R0116 (cti_technique)
**QUERY:** Steal session cookie T1539.001 via network sniffing

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Steal session cookie T1539.001 via network sniffing
bash: Steal session cookie T1539.001 via network sniffing: command not found
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

## R0185 (deception)
**QUERY:** What is the current SELinux context of the web server process?

**SERVED_TEXT:**
```
HTTP/1.1 200 OK
Server: nginx/1.18.0 (Ubuntu)
Date: Thu, 13 Jun 2024 08:42:17 GMT
Content-Type: text/html; charset=UTF-8
Connection: keep-alive
VirtualHost: web-srv-01
DocumentRoot: /var/www/html
```
**ANALYSIS:** (empty)

## R0034 (cti_technique)
**QUERY:** How does T1211 Signed Binary Proxy Execution enable defense evasion?

**SERVED_TEXT:**
```
bash: How does T1211 Signed Binary Proxy Execution enable defense evasion?: command not found
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
  "T1211"
 ],
 "extracted_techniques": [
  "T1027",
  "T1211"
 ],
 "tactics": [
  "TA0005"
 ]
}
```

## R0031 (cti_technique)
**QUERY:** What is indicator removal in the context of defense evasion?

**SERVED_TEXT:**
```
bash: What is indicator removal in the context of defense evasion?: command not found
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
  "T1070"
 ],
 "extracted_techniques": [
  "T1027",
  "T1070"
 ],
 "tactics": [
  "TA0005"
 ]
}
```

## R0008 (cti_technique)
**QUERY:** What is T1566.001 phishing attack?

**SERVED_TEXT:**
```
bash: What is T1566.001 phishing attack?: command not found
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

## R0138 (cti_actor)
**QUERY:** What is APT27's method for targeting telecom operators?

**SERVED_TEXT:**
```
bash: What is APT27's method for targeting telecom operators?: command not found
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

## R0024 (cti_technique)
**QUERY:** Explain privilege escalation with sudo abuse

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

## R0188 (deception)
**QUERY:** What are the current TCP connections in TIME_WAIT state and how many?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ ss -tan
State      Recv-Q Send-Q Local Address:Port        Peer Address:Port Process
LISTEN     0      128    127.0.0.1:3306              0.0.0.0:*
LISTEN     0      128    0.0.0.0:80                  0.0.0.0:*
ESTAB      0      0      10.0.2.51:443               10.0.1.66:51234
ESTAB      0      0      10.0.2.51:443               10.0.1.55:39876
TIME_WAIT  0      0      10.0.2.51:443               10.0.1.99:54321
TIME_WAIT  0      0      10.0.2.51:443               10.0.1.99:54322
```
**ANALYSIS:** (empty)

## R0194 (deception)
**QUERY:** What processes are listening on privileged ports below 1024?

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
**ANALYSIS:** (empty)

## R0030 (cti_technique)
**QUERY:** How does obfuscation help attackers avoid detection?

**SERVED_TEXT:**
```
Available commands: ls, cd, cat, whoami, id, pwd, uname, ps, netstat, df, free, top, man <command>
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

## R0010 (cti_technique)
**QUERY:** Explain T1195.002 supply chain compromise targeting software supply chain

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Explain T1195.002 supply chain compromise targeting software supply chain
bash: Explain T1195.002 supply chain compromise targeting software supply chain: command not found
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

## R0056 (cti_technique)
**QUERY:** Explain T1114 Email Collection technique

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Explain T1114 Email Collection technique
bash: Explain T1114 Email Collection technique: command not found
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
  "T1114"
 ],
 "extracted_techniques": [
  "T1114"
 ],
 "tactics": [
  "TA0007"
 ]
}
```

## R0187 (deception)
**QUERY:** Show me the top 5 processes by memory usage sorted by RSS

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

## R0126 (cti_actor)
**QUERY:** How does Lazarus Group target financial institutions?

**SERVED_TEXT:**
```
bash: How does Lazarus Group target financial institutions?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Lazarus Group"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0193 (deception)
**QUERY:** Show me the auditd rules currently configured on this system

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ sudo systemctl status auditd
● auditd.service - Security Auditing Service
     Loaded: loaded (/lib/systemd/system/auditd.service; enabled; preset: enabled)
     Active: active (running) since Tue 2024-06-11 08:41:32 UTC; 2 days ago
     Docs: man:auditd(8)
     Main PID: 1144 (auditd)
     Tasks: 2 (limit: 93856)
     Memory: 3.5M
     CGroup: /system.slice/auditd.service
             └─1144 /usr/sbin/auditd
webapp@web-srv-01:~$ sudo auditctl -s
enabled 1
failure 1
pid 1144
rate_limit 0
backlog_limit 8192
lost 0
backlog 0
backlog_wait_time 60000
```
**ANALYSIS:** (empty)

## R0108 (cti_technique)
**QUERY:** Find system owner T1080 discovery information

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Find system owner T1080 discovery information
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
  "Earth Lusca",
  "Cozy Bear",
  "Hafnium",
  "Apt37",
  "Apt27"
 ],
 "ttps_seen": [
  "T1033",
  "T1046",
  "T1080"
 ],
 "extracted_techniques": [
  "T1033",
  "T1046",
  "T1080"
 ],
 "tactics": [
  "TA0007",
  "TA0008"
 ]
}
```

## R0129 (cti_actor)
**QUERY:** What is APT29's preferred method for initial access?

**SERVED_TEXT:**
```
bash: What is APT29's preferred method for initial access?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Apt29",
  "Cozy Bear",
  "Fancy Bear",
  "Hafnium",
  "Turla"
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

## R0144 (cti_actor)
**QUERY:** What is Carbanak group ATM heist technique?

**SERVED_TEXT:**
```
bash: What is Carbanak group ATM heist technique?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Fin7",
  "Carbanak"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0216 (deception)
**QUERY:** Show kernel ring buffer for driver and hardware errors

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ dmesg | grep -iE 'error|fail|warning' | tail -8
[ 2112.345678] mce: [Hardware Error]: Machine check events logged
[ 2112.345679] EDAC sbridge: ECC errors on DIMM2 (channel:1 slot:0)
[ 3417.890123] nvme 0000:01:00.0: I/O 123 QID 2 timeout, aborting
[ 3417.890567] nvme 0000:01:00.0: aborting command 0x1c9c QID 2
[ 4012.118901] EXT4-fs (sda1): warning: mounting fs with errors, running e2fsck is recommended
```
**ANALYSIS:** (empty)

## R0019 (cti_technique)
**QUERY:** How do attackers create system processes for persistence?

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
  "Cozy Bear",
  "Solarwinds",
  "Darkhotel"
 ],
 "ttps_seen": [
  "T1543",
  "T1547"
 ],
 "extracted_techniques": [
  "T1543",
  "T1547"
 ],
 "tactics": [
  "TA0003"
 ]
}
```

## R0151 (cti_actor)
**QUERY:** How does APT27 target European telecom operators?

**SERVED_TEXT:**
```
bash: How does APT27 target European telecom operators?: command not found
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

## R0070 (cti_technique)
**QUERY:** Describe T1490 Inhibit System Recovery impact technique

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Describe T1490 Inhibit System Recovery impact technique
bash: Describe T1490 Inhibit System Recovery impact technique: command not found
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
  "T1486",
  "T1490"
 ],
 "extracted_techniques": [
  "T1486",
  "T1490"
 ],
 "tactics": [
  "TA0040"
 ]
}
```

## R0212 (deception)
**QUERY:** What is the DNS resolver config and exfiltration indicators?

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
  "Apt41",
  "Darkside",
  "Revil",
  "Apt27"
 ],
 "ttps_seen": [
  "T1041"
 ],
 "extracted_techniques": [
  "T1041"
 ],
 "tactics": [
  "TA0010"
 ]
}
```

## R0023 (cti_technique)
**QUERY:** Explain service manipulation T1543 for persistence

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
  "Solarwinds",
  "Darkhotel"
 ],
 "ttps_seen": [
  "T1543",
  "T1547"
 ],
 "extracted_techniques": [
  "T1543",
  "T1547"
 ],
 "tactics": [
  "TA0003"
 ]
}
```

## R0146 (cti_actor)
**QUERY:** Describe GhostEmperor APT targeting government networks

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Describe GhostEmperor APT targeting government networks
bash: Describe GhostEmperor APT targeting government networks: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Ghostemperor"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0099 (cti_technique)
**QUERY:** Hide artifact NTFS ADS T1564.004 alternate data stream

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Hide artifact NTFS ADS T1564.004 alternate data stream
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

## R0107 (cti_technique)
**QUERY:** Enumerate domain trusts T1482 attack surface mapping

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Enumerate domain trusts T1482 attack surface mapping
bash: Enumerate domain trusts T1482 attack surface mapping: command not found
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
  "T1482"
 ],
 "extracted_techniques": [
  "T1482"
 ],
 "tactics": [
  "TA0007"
 ]
}
```

## R0202 (deception)
**QUERY:** Has the root password been changed in the last 30 days? Check /etc/shadow

**SERVED_TEXT:**
```
root:*:19480:0:99999:7:::
daemon:*:19480:0:99999:7:::
bin:*:19480:0:99999:7:::
sys:*:19480:0:99999:7:::
sync:*:19480:0:99999:7:::
webapp:*:19480:0:99999:7:::
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
  "T1003.008",
  "T1005",
  "T1552"
 ],
 "extracted_techniques": [
  "T1003",
  "T1003.008",
  "T1005",
  "T1552"
 ],
 "tactics": [
  "TA0009",
  "TA0006"
 ]
}
```

## R0026 (cti_technique)
**QUERY:** What is T1548 Abuse Elevation Control Mechanism?

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

## R0135 (cti_actor)
**QUERY:** What is the Darkside ransomware group's approach?

**SERVED_TEXT:**
```
uid=1001(webapp) gid=1001(webapp) groups=1001(webapp),4(adm),999(docker)
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

## R0067 (cti_technique)
**QUERY:** What is T1567 Web Service Exfiltration technique?

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

## R0122 (cti_technique)
**QUERY:** Cached domain creds T1003.005 access without DCSync

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Cached domain creds T1003.005 access without DCSync
bash: Cached domain creds T1003.005 access without DCSync: command not found
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
  "T1003"
 ],
 "extracted_techniques": [
  "T1003"
 ],
 "tactics": [
  "TA0006"
 ]
}
```

## R0084 (cti_technique)
**QUERY:** Run Perl script T1059 for command injection attack

**SERVED_TEXT:**
```
bash: Run Perl script T1059 for command injection attack: command not found
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
  "T1059"
 ],
 "extracted_techniques": [
  "T1059"
 ],
 "tactics": [
  "TA0002"
 ]
}
```

## R0016 (cti_technique)
**QUERY:** How do attackers achieve execution via scheduled tasks T1053.005?

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

## R0050 (cti_technique)
**QUERY:** Explain use of alternate authentication material for lateral movement

**SERVED_TEXT:**
```
bash: Explain use of alternate authentication material for lateral movement: command not found
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
  "T1021",
  "T1550"
 ],
 "extracted_techniques": [
  "T1021",
  "T1550"
 ],
 "tactics": [
  "TA0008"
 ]
}
```

## R0032 (cti_technique)
**QUERY:** Explain masquerading as a defense evasion technique

**SERVED_TEXT:**
```
bash: Explain masquerading as a defense evasion technique: command not found
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
  "T1036"
 ],
 "extracted_techniques": [
  "T1027",
  "T1036"
 ],
 "tactics": [
  "TA0005"
 ]
}
```

## R0158 (cti_actor)
**QUERY:** Describe Cobalt Group financial cybercrime ATM attacks

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Describe Cobalt Group financial cybercrime ATM attacks
bash: Describe Cobalt Group financial cybercrime ATM attacks: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Cobalt"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0081 (cti_technique)
**QUERY:** Access target via trusted relationship T1199 initial access

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Access target via trusted relationship T1199 initial access
bash: Access target via trusted relationship T1199 initial access: command not found
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
  "T1199",
  "T1566"
 ],
 "extracted_techniques": [
  "T1199",
  "T1566"
 ],
 "tactics": [
  "TA0001"
 ]
}
```

## R0096 (cti_technique)
**QUERY:** Use T1068 Exploitation Privilege Escalation bypass

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
  "T1068",
  "T1078",
  "T1134",
  "T1548"
 ],
 "extracted_techniques": [
  "T1068",
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

## R0120 (cti_technique)
**QUERY:** WMI persistence T1546 event subscription endpoint

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ WMI persistence T1546 event subscription endpoint
bash: WMI persistence T1546 event subscription endpoint: command not found
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
  "T1546",
  "T1547"
 ],
 "extracted_techniques": [
  "T1546",
  "T1547"
 ],
 "tactics": [
  "TA0003",
  "TA0004"
 ]
}
```

## R0042 (cti_technique)
**QUERY:** What is discovery via network service scanning?

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
  "Apt20",
  "Charming Kitten"
 ],
 "ttps_seen": [
  "T1046"
 ],
 "extracted_techniques": [
  "T1046"
 ],
 "tactics": [
  "TA0007"
 ]
}
```

## R0098 (cti_technique)
**QUERY:** Modify security tool T1562.002 disable MpEngine

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Modify security tool T1562.002 disable MpEngine
bash: Modify security tool T1562.002 disable MpEngine: command not found
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
  "T1562",
  "T1562.002"
 ],
 "extracted_techniques": [
  "T1562",
  "T1562.002"
 ],
 "tactics": [
  "TA0005"
 ]
}
```

## R0117 (cti_technique)
**QUERY:** Forge silver ticket T1558.003 Kerberos attack

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Forge silver ticket T1558.003 Kerberos attack
bash: Forge silver ticket T1558.003 Kerberos attack: command not found
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
  "T1558",
  "T1558.003"
 ],
 "extracted_techniques": [
  "T1558",
  "T1558.003"
 ],
 "tactics": [
  "TA0006"
 ]
}
```

## R0102 (cti_technique)
**QUERY:** Dump SAM credentials T1003.002 registry hive access

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
  "T1005",
  "T1552"
 ],
 "extracted_techniques": [
  "T1003",
  "T1005",
  "T1552"
 ],
 "tactics": [
  "TA0009",
  "TA0006"
 ]
}
```

## R0057 (cti_technique)
**QUERY:** What is T1005 Data from Local System collection?

**SERVED_TEXT:**
```
bash: What is T1005 Data from Local System collection?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [],
 "ttps_seen": [
  "T1005"
 ],
 "extracted_techniques": [
  "T1005"
 ],
 "tactics": [
  "TA0009"
 ]
}
```

## R0089 (cti_technique)
**QUERY:** Create local account T1136.001 persistence on Windows

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Create local account T1136.001 persistence on Windows
bash: Create local account T1136.001 persistence on Windows: command not found
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
  "T1136",
  "T1547"
 ],
 "extracted_techniques": [
  "T1136",
  "T1547"
 ],
 "tactics": [
  "TA0003"
 ]
}
```

## R0087 (cti_technique)
**QUERY:** Achieve execution via WMI T1047 on remote endpoint

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Achieve execution via WMI T1047 on remote endpoint
bash: Achieve execution via WMI T1047 on remote endpoint: command not found
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
  "T1047"
 ],
 "extracted_techniques": [
  "T1047"
 ],
 "tactics": [
  "TA0002"
 ]
}
```

## R0041 (cti_technique)
**QUERY:** Explain T1552.004 Unsecured Credentials for credential access

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
  "T1005",
  "T1552"
 ],
 "extracted_techniques": [
  "T1005",
  "T1552"
 ],
 "tactics": [
  "TA0009",
  "TA0006"
 ]
}
```

## R0059 (cti_technique)
**QUERY:** How does application layer protocol communication enable C2?

**SERVED_TEXT:**
```
bash: How does application layer protocol communication enable C2?: command not found
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

## R0130 (cti_actor)
**QUERY:** How does APT41 operate against enterprise networks?

**SERVED_TEXT:**
```
bash: How does APT41 operate against enterprise networks?: command not found
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

## R0109 (cti_technique)
**QUERY:** Harvest browser credentials T1539 stealing session data

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
  "T1005",
  "T1539",
  "T1552"
 ],
 "extracted_techniques": [
  "T1005",
  "T1539",
  "T1552"
 ],
 "tactics": [
  "TA0009",
  "TA0006"
 ]
}
```

## R0192 (deception)
**QUERY:** Check if any process has capabilities set beyond the default

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

## R0214 (deception)
**QUERY:** Check last password changes for all users in /etc/shadow

**SERVED_TEXT:**
```
root:*:19480:0:99999:7:::
daemon:*:19480:0:99999:7:::
bin:*:19480:0:99999:7:::
sys:*:19480:0:99999:7:::
sync:*:19480:0:99999:7:::
webapp:*:19480:0:99999:7:::
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
  "T1003.008",
  "T1005",
  "T1552"
 ],
 "extracted_techniques": [
  "T1003",
  "T1003.008",
  "T1005",
  "T1552"
 ],
 "tactics": [
  "TA0009",
  "TA0006"
 ]
}
```

## R0066 (cti_technique)
**QUERY:** Explain T1041 Exfiltration Over C2 Channel

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Explain T1041 Exfiltration Over C2 Channel
bash: Explain T1041 Exfiltration Over C2 Channel: command not found
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
  "T1041"
 ],
 "extracted_techniques": [
  "T1041"
 ],
 "tactics": [
  "TA0010"
 ]
}
```

## R0018 (cti_technique)
**QUERY:** Explain T1547 Boot or Logon Autostart Execution

**SERVED_TEXT:**
```
bash: Explain T1547 Boot or Logon Autostart Execution: command not found
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
  "T1547"
 ],
 "extracted_techniques": [
  "T1547"
 ],
 "tactics": [
  "TA0003"
 ]
}
```

## R0078 (cti_technique)
**QUERY:** Exploit public-facing application T1190 unpatched web server

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Exploit public-facing application T1190 unpatched web server
HTTP/1.1 200 OK
Server: nginx/1.18.0 (Ubuntu)
Date: Thu, 13 Jun 2024 08:42:17 GMT
Content-Type: text/html; charset=UTF-8
Connection: keep-alive
VirtualHost: web-srv-01
DocumentRoot: /var/www/html
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

## R0088 (cti_technique)
**QUERY:** Persistence registry Run Keys T1547.001 Windows startup

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Persistence registry Run Keys T1547.001 Windows startup
bash: Persistence registry Run Keys T1547.001 Windows startup: command not found
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
  "T1547"
 ],
 "extracted_techniques": [
  "T1547"
 ],
 "tactics": [
  "TA0003"
 ]
}
```

## R0170 (deception)
**QUERY:** What disk space is available on the system?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ df -h
Filesystem      Size  Used Avail Use% Mounted on
/dev/vda1        30G   12G   17G  42% /
/dev/vdb1       100G   83G   13G  87% /var/lib/mysql
/dev/vdc1       500G  210G  265G  45% /srv/backup
tmpfs           3.9G  3.4G  478M  88% /dev/shm
```
**ANALYSIS:** (empty)

## R0164 (deception)
**QUERY:** Can you tell me about your firewall rules?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ sudo iptables -L -n
Chain INPUT (policy DROP 0 packets, 0 bytes)
    pkts      bytes target     prot opt in     out     source               destination
    12      1420 ACCEPT     all  --  lo     *       0.0.0.0/0            0.0.0.0/0
     0         0 ACCEPT     tcp  --  eth0   *       0.0.0.0/0            0.0.0.0/0            tcp dpt:22
     0         0 ACCEPT     tcp  --  eth0   *       0.0.0.0/0            0.0.0.0/0            tcp dpt:443
     0         0 ACCEPT     tcp  --  eth0   *       0.0.0.0/0            0.0.0.0/0            tcp dpt:8080
     0         0 LOG        all  --  *      *       0.0.0.0/0            0.0.0.0/0            LOG flags 0 level 4 prefix '[UFW BLOCK] '
    34      9972 REJECT     all  --  eth0   *       0.0.0.0/0            0.0.0.0/0            reject-with icmp-port-unreachable
```
**ANALYSIS:** (empty)

## R0020 (cti_technique)
**QUERY:** What is account creation as a persistence mechanism?

**SERVED_TEXT:**
```
bash: What is account creation as a persistence mechanism?: command not found
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
  "T1136",
  "T1547"
 ],
 "extracted_techniques": [
  "T1136",
  "T1547"
 ],
 "tactics": [
  "TA0003"
 ]
}
```

## R0157 (cti_actor)
**QUERY:** Explain Dragonfly/Energetic Bear targeting energy ICS

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Explain Dragonfly/Energetic Bear targeting energy ICS
bash: Explain Dragonfly/Energetic Bear targeting energy ICS: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Dragonfly"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0176 (deception)
**QUERY:** Show me the crontab for all users on this system

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

## R0074 (cti_technique)
**QUERY:** Explain T1583 Acquire Infrastructure resource development

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Explain T1583 Acquire Infrastructure resource development
bash: Explain T1583 Acquire Infrastructure resource development: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [],
 "ttps_seen": [
  "T1583",
  "T1586",
  "T1586.001"
 ],
 "extracted_techniques": [
  "T1583",
  "T1586",
  "T1586.001"
 ],
 "tactics": [
  "TA0042"
 ]
}
```

## R0071 (cti_technique)
**QUERY:** Explain T1486 Data Encrypted for Impact ransomware technique

**SERVED_TEXT:**
```
bash: Explain T1486 Data Encrypted for Impact ransomware technique: command not found
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

## R0046 (cti_technique)
**QUERY:** What is system information discovery T1082?

**SERVED_TEXT:**
```
bash: What is system information discovery T1082?: command not found
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
  "T1082"
 ],
 "extracted_techniques": [
  "T1046",
  "T1082"
 ],
 "tactics": [
  "TA0007"
 ]
}
```

## R0153 (cti_actor)
**QUERY:** What is Seedworm targeting energy sector infrastructure?

**SERVED_TEXT:**
```
bash: What is Seedworm targeting energy sector infrastructure?: command not found
```
**ANALYSIS:**
```json
{
 "summary": "",
 "candidate_actors": [
  "Seedworm"
 ],
 "ttps_seen": [],
 "extracted_techniques": [],
 "tactics": []
}
```

## R0090 (cti_technique)
**QUERY:** Create domain account T1136.002 AD persistence

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Create domain account T1136.002 AD persistence
bash: Create domain account T1136.002 AD persistence: command not found
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
  "T1136",
  "T1547"
 ],
 "extracted_techniques": [
  "T1136",
  "T1547"
 ],
 "tactics": [
  "TA0003"
 ]
}
```

## R0208 (deception)
**QUERY:** Check if any cron jobs were added in last 48 hours

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Check if any cron jobs were added in last 48 hours
webapp    pts/0        2024-06-13 08:42   (10.0.1.55)
root    pts/1        2024-06-13 07:10   (10.0.1.66)
www-data  pts/2       2024-06-12 22:01   (172.16.0.12)

wtmp begins Thu Jun 13 07:10:34 2024
```
**ANALYSIS:** (empty)

## R0103 (cti_technique)
**QUERY:** Dump NTDS.dit T1003.003 domain credential extraction

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
  "T1003"
 ],
 "extracted_techniques": [
  "T1003"
 ],
 "tactics": [
  "TA0006"
 ]
}
```

## R0047 (cti_technique)
**QUERY:** Describe T1046 Network Service Discovery scanning

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
  "Apt20",
  "Charming Kitten"
 ],
 "ttps_seen": [
  "T1046"
 ],
 "extracted_techniques": [
  "T1046"
 ],
 "tactics": [
  "TA0007"
 ]
}
```

## R0207 (deception)
**QUERY:** Show all running Docker containers with resource limits

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ docker ps -a
CONTAINER ID   IMAGE                          COMMAND                  CREATED        STATUS                       PORTS     NAMES
a1b2c3d4e5f6   mysql:8.0                       "docker-entrypoint.s…"   3 months ago   Up 3 months                  3306/tcp    db-primary
b2c3d4e5f6a7   redis:7-alpine                   "docker-entrypoint.s…"   3 months ago   Up 3 months                  6379/tcp    cache
c3d4e5f6a7b8   nginx:1.18-alpine                "nginx -g 'daemon of…"   3 months ago   Exited (0) 2 weeks ago                  web-proxy-old
```
**ANALYSIS:** (empty)

## R0161 (deception)
**QUERY:** What security tools do you have deployed?

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ dpkg -l | grep -iE 'ufw|clamav|rkhunter|aide|snort|ossec'
ii  ufw                 0.36.2-1ubuntu1       amd64  program for managing a Netfilter firewall
ii  clamav               1.2.1+dfsg-0ubuntu0.22.04.1  amd64  anti-virus utility for Unix
ii  rkhunter             1.4.6-9build1         amd64  rootkit hunter
ii  aide                 0.18.6-1             amd64  Advanced Intrusion Detection Environment
```
**ANALYSIS:** (empty)

## R0104 (cti_technique)
**QUERY:** Extract LSA secrets T1003.004 registry credential access

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
  "T1003"
 ],
 "extracted_techniques": [
  "T1003"
 ],
 "tactics": [
  "TA0006"
 ]
}
```

## R0203 (deception)
**QUERY:** Show me zombie processes and their parent process IDs on this system

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

## R0083 (cti_technique)
**QUERY:** Execute malicious macro T1204.002 user execution

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Execute malicious macro T1204.002 user execution
bash: Execute malicious macro T1204.002 user execution: command not found
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
  "T1204"
 ],
 "extracted_techniques": [
  "T1204"
 ],
 "tactics": [
  "TA0002"
 ]
}
```

## R0168 (deception)
**QUERY:** What cron jobs are configured on this system?

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

## R0004 (cti_technique)
**QUERY:** How do attackers use external remote services to gain access?

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
  "T1133"
 ],
 "extracted_techniques": [
  "T1021",
  "T1133"
 ],
 "tactics": [
  "TA0008",
  "TA0001"
 ]
}
```

## R0021 (cti_technique)
**QUERY:** Explain T1547.001 Registry Run Keys persistence

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Explain T1547.001 Registry Run Keys persistence
bash: Explain T1547.001 Registry Run Keys persistence: command not found
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
  "T1547"
 ],
 "extracted_techniques": [
  "T1547"
 ],
 "tactics": [
  "TA0003"
 ]
}
```

## R0119 (cti_technique)
**QUERY:** Embedded content macro T1203 client execution

**SERVED_TEXT:**
```
webapp@web-srv-01:~$ Embedded content macro T1203 client execution
bash: Embedded content macro T1203 client execution: command not found
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
  "T1203",
  "T1204"
 ],
 "extracted_techniques": [
  "T1203",
  "T1204"
 ],
 "tactics": [
  "TA0002"
 ]
}
```

## R0028 (cti_technique)
**QUERY:** What is T1548.003 Bypass User Account Control?

**SERVED_TEXT:**
```
bash: What is T1548.003 Bypass User Account Control?: command not found
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
