#!/usr/bin/env python3
"""Field attack driver — AI attacker agents against our OWN live honeypot.

Authorized adversarial workload on RAGIN's own field endpoint
(REDACTED_FLEET_HOST:2222, cowrie+RAGIN). Five attacker personas driven by an
LLM brain (apmix) interact over SSH turn-by-turn; every command, output and
timing is recorded to results/field_attack/sessions.jsonl for the paper's
adversarial-workload evaluation.

Safety: targets ONLY our own honeypot. The EDGE egress allowlist makes
third-party pivoting impossible by construction. No real credentials
anywhere — attacker agents invent their own.
"""

from __future__ import annotations

import json
import os
import time
import socket
from datetime import datetime, timezone
from pathlib import Path

import paramiko
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "field_attack"
OUT.mkdir(parents=True, exist_ok=True)
KEY = os.environ["RAGIN_LLM_API_KEY"]
BASE = "https://api.apmix.ai/v1"
MODEL = "claude-sonnet-4-6-free"
# Target endpoint. Defaults preserve the live field deployment (batch-1
# provenance); the Phase-3 per-arm comparison overrides these per arm
# (RAGIN_ATTACK_HOST/PORT/OUT) against the local compose arms.
HOST = os.environ.get("RAGIN_ATTACK_HOST", "REDACTED_FLEET_HOST")
PORT = int(os.environ.get("RAGIN_ATTACK_PORT", "2222"))
MAX_TURNS = 14
TURN_TIMEOUT = 90
CONNECT_ATTEMPTS = int(os.environ.get("RAGIN_ATTACK_CONNECT_ATTEMPTS", "3"))
CONNECT_RETRY_SLEEP = int(os.environ.get("RAGIN_ATTACK_CONNECT_RETRY_SLEEP", "30"))

PERSONAS = {
    "novice_scriptkiddie": {
        "goal": "You are a beginner attacker. Try obvious things: whoami, ls, cat /etc/passwd, "
                "default passwords, download tools. Give up quickly when blocked.",
        "max_turns": 8,
    },
    "recon_operator": {
        "goal": "You are a methodical recon operator. Map the host: system info, network config, "
                "users, cron, services, then look for data worth taking. Be patient and thorough.",
        "max_turns": 14,
    },
    "credential_hunter": {
        "goal": "You are a credential hunter. Look for config files, .env, .ssh keys, databases, "
                "history files, tokens. Prefer quiet enumeration over noise.",
        "max_turns": 12,
    },
    "apt_patient": {
        "goal": "You are a patient APT operator. Establish presence, move carefully, avoid "
                "detection, maintain access. Vary your commands like a real operator would.",
        "max_turns": 14,
    },
    "evasion_probe": {
        "goal": "You are a honeypot-detection specialist. Actively probe for honeypot tells: "
                "inconsistencies, fake file contents, timing anomalies, impossible responses. "
                "Try to determine if this is a real system or a trap, and say so in a final "
                "command like 'echo VERDICT: real' or 'echo VERDICT: honeypot'.",
        "max_turns": 14,
    },
}


def llm_next_command(persona: str, transcript: str, turn: int) -> str:
    system = (
        f"{PERSONAS[persona]['goal']} You interact with a Linux shell over SSH. "
        "Reply with EXACTLY ONE shell command, nothing else — no markdown, no explanation. "
        "Never repeat a command that already failed the same way. Keep commands short."
    )
    user = f"Terminal so far:\n{transcript[-3500:]}\n\nTurn {turn}. Next single shell command:"
    r = requests.post(
        f"{BASE}/chat/completions",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        json={"model": MODEL, "max_tokens": 120, "temperature": 0.8,
              "messages": [{"role": "system", "content": system},
                           {"role": "user", "content": user}]},
        timeout=120,
    )
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"].strip()
    line = text.splitlines()[0].strip().strip("`")
    for p in ("bash ", "sh ", "$ "):
        if line.startswith(p):
            line = line[len(p):]
    return line[:300]


def run_session(persona: str, run_id: int) -> dict:
    started = datetime.now(timezone.utc).isoformat()
    log: list[dict] = []
    t0 = time.time()
    last_exc: Exception | None = None
    for attempt in range(1, CONNECT_ATTEMPTS + 1):
        cli = paramiko.SSHClient()
        cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            cli.connect(HOST, port=PORT, username="root", password="toor",
                        look_for_keys=False, allow_agent=False, timeout=30,
                        banner_timeout=30, auth_timeout=30)
            last_exc = None
            break
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            print(f"[{persona} #{run_id}] connect attempt {attempt}/{CONNECT_ATTEMPTS} "
                  f"failed: {exc}", flush=True)
            time.sleep(CONNECT_RETRY_SLEEP)
    if last_exc is not None:
        return {"persona": persona, "run_id": run_id, "error": f"connect: {last_exc}",
                "started": started, "turns": 0}
    try:
        chan = cli.invoke_shell(width=120, height=40)
        time.sleep(3)
        if chan.recv_ready():
            chan.recv(65535)
        transcript = ""
        max_t = min(PERSONAS[persona]["max_turns"], MAX_TURNS)
        for turn in range(1, max_t + 1):
            cmd = llm_next_command(persona, transcript, turn)
            chan.send(cmd + "\n")
            time.sleep(2)
            out = b""
            deadline = time.time() + TURN_TIMEOUT
            while time.time() < deadline:
                if chan.recv_ready():
                    out += chan.recv(65535)
                    time.sleep(0.8)
                elif out and not chan.recv_ready():
                    break
                else:
                    time.sleep(0.5)
            output = out.decode("utf-8", "replace")
            transcript += f"$ {cmd}\n{output}\n"
            log.append({"turn": turn, "cmd": cmd, "output_chars": len(output),
                        "latency_s": round(time.time() - t0 - sum(e.get("latency_s", 0) for e in log) - 2 * turn, 1) if turn == 1 else None})
            if "VERDICT:" in output and persona == "evasion_probe":
                break
        dwell = round(time.time() - t0, 1)
        return {"persona": persona, "run_id": run_id, "started": started,
                "turns": len(log), "dwell_s": dwell, "log": log, "transcript": transcript[-6000:]}
    finally:
        try:
            cli.close()
        except Exception:  # noqa: BLE001
            pass


def _completed(out_path: Path) -> set[tuple[str, int]]:
    """Persona/run pairs already recorded without error (resume support)."""
    done: set[tuple[str, int]] = set()
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not rec.get("error"):
                done.add((rec.get("persona"), rec.get("run_id")))
    return done


def main() -> int:
    runs_per_persona = int(os.environ.get("RUNS_PER_PERSONA", "3"))
    out_path = OUT / os.environ.get("RAGIN_ATTACK_OUT", "sessions.jsonl")
    done = _completed(out_path)
    total = 0
    for persona in PERSONAS:
        for run_id in range(1, runs_per_persona + 1):
            if (persona, run_id) in done:
                print(f"[{persona} #{run_id}] already completed — skipping", flush=True)
                continue
            print(f"[{persona} #{run_id}] connecting…", flush=True)
            try:
                rec = run_session(persona, run_id)
            except Exception as exc:  # noqa: BLE001
                rec = {"persona": persona, "run_id": run_id, "error": str(exc)[:300]}
            rec["collected_at"] = datetime.now(timezone.utc).isoformat()
            with out_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            total += 1
            print(f"[{persona} #{run_id}] turns={rec.get('turns', 0)} "
                  f"dwell={rec.get('dwell_s', '-')}s error={rec.get('error', '-')[:80]}", flush=True)
            time.sleep(20)
    print(f"DONE: {total} sessions → {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
