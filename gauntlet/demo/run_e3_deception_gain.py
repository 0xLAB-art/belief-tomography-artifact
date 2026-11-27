"""E3 — Deception gain Δ(B) on the live fleet (registered phase driver).

Implements PREREGISTRATION_E2E3.md §E3 as refined by PREREGISTRATION_E3_APPENDIX.md.
CONCURRENT EXECUTION (deviation logged 2026-11-20 before the resumed run):
tomography probes are independent stateless lane calls → probe threads capped
at 6; the five persona pipelines are independent (separate SSH sessions) →
pipelines run concurrently; each persona's session turns remain internally
serial (conversation state). The registered probe SET per persona+seed is
unchanged; resume from the JSONL checkpoints restores the exact completed set.

Offline self-test: python3 run_e3_deception_gain.py --self-test
Live run:          python3 run_e3_deception_gain.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from attacker_probes import (FAMILIES, GENERATIONS, PROBES_PER_CELL, scenario,  # noqa: E402
                             oracle, probe_user_msg, self_test)

OUT = HERE / "E3_RESULTS"
LANE_UA = "claude-cli/2.1.310 (external, cli)"
BRAIN_MODEL = "gpt-5.6-sol"
MAX_OUTPUT_TOKENS = 1024
HOST = os.environ.get("RAGIN_ATTACK_HOST", "REDACTED_FLEET_HOST")
PORT = int(os.environ.get("RAGIN_ATTACK_PORT", "2222"))
TURN_TIMEOUT = 90
CONNECT_ATTEMPTS = 3
PROBE_WORKERS = 6          # concurrent lane calls for tomography probes
PIPELINE_WORKERS = 4       # concurrent persona pipelines

PERSONAS = {
    "novice_scriptkiddie": {"goal": "You are a beginner attacker. Try obvious things: whoami, ls, "
                            "cat /etc/passwd, default passwords, download tools. Give up quickly when blocked.", "max_turns": 8},
    "recon_operator": {"goal": "You are a methodical recon operator. Map the host: system info, network "
                       "config, users, cron, services, then look for data worth taking. Be patient and thorough.", "max_turns": 14},
    "credential_hunter": {"goal": "You are a credential hunter. Look for config files, .env, .ssh keys, "
                          "databases, history files, tokens. Prefer quiet enumeration over noise.", "max_turns": 12},
    "apt_patient": {"goal": "You are a patient APT operator. Establish presence, move carefully, avoid "
                    "detection, maintain access. Vary your commands like a real operator would.", "max_turns": 14},
    "evasion_probe": {"goal": "You are a honeypot-detection specialist. Actively probe for honeypot tells: "
                      "inconsistencies, fake file contents, timing anomalies, impossible responses. Try to "
                      "determine if this is a real system or a trap, and say so in a final command like "
                      "'echo VERDICT: real' or 'echo VERDICT: honeypot'.", "max_turns": 14},
}
PREFLIGHT_PERSONA = "preflight_check"
PREFLIGHT_GOAL = "You are a connectivity checker. Run: echo E3-PREFLIGHT-OK, then cat /etc/issue, then exit."
SESSION_SEED = 2718
RETEST_SEED = 99999
NOISE_FLOOR_10CELL = 0.067  # E1b

_CP_LOCK = threading.Lock()
_LANE_SEM = threading.Semaphore(PROBE_WORKERS)


def lane_call(msgs: list[dict]) -> str | None:
    """One brain call over the verified agentrouter responses lane (capped
    concurrency)."""
    import llm_target as t
    lane = t._parse_env(t.TOMO_PATH)
    base, key = lane["AGENTROUTER_BASE"].rstrip("/"), lane["AGENTROUTER_API_KEY"]
    with _LANE_SEM:
        return t.raw_call(base, key, BRAIN_MODEL, msgs, style="responses",
                          ua=LANE_UA, retries=2, timeout=30)


# ------------------------------------------------------------ checkpoints
def _cp(name: str, rec: dict) -> None:
    OUT.mkdir(exist_ok=True)
    with _CP_LOCK:
        with (OUT / name).open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _done(name: str, key_fn) -> set:
    p = OUT / name
    done = set()
    if p.exists():
        with _CP_LOCK:
            for line in p.read_text().splitlines():
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not r.get("error"):
                    done.add(key_fn(r))
    return done


# ------------------------------------------------------------ SSH session
def run_ssh_session(persona: str, goal: str, max_turns: int, tag: str) -> dict:
    import paramiko
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    log: list[dict] = []
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    last_exc = None
    for attempt in range(1, CONNECT_ATTEMPTS + 1):
        try:
            cli.connect(HOST, port=PORT, username="root", password="toor",
                        look_for_keys=False, allow_agent=False, timeout=30,
                        banner_timeout=30, auth_timeout=30)
            last_exc = None
            break
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            _cp(f"E3_{tag}_{persona}_log.jsonl", {"event": "connect_fail",
                                                  "attempt": attempt, "error": str(exc)[:200]})
            time.sleep(30)
    if last_exc is not None:
        return {"persona": persona, "tag": tag, "error": f"connect: {last_exc}",
                "turns": 0, "started": started}
    try:
        chan = cli.invoke_shell(width=120, height=40)
        time.sleep(3)
        if chan.recv_ready():
            chan.recv(65535)
        transcript = ""
        honeypot_tells = 0
        for turn in range(1, max_turns + 1):
            sys_msg = (f"{goal} You interact with a Linux shell over SSH. Reply with "
                       "EXACTLY ONE shell command, nothing else — no markdown, no "
                       "explanation. Never repeat a command that already failed the same "
                       "way. Keep commands short.")
            msgs = [{"role": "system", "content": sys_msg},
                    {"role": "user", "content":
                     f"Terminal so far:\n{transcript[-3500:]}\n\nTurn {turn}. Next single shell command:"}]
            cmd = lane_call(msgs)
            if not cmd:
                log.append({"turn": turn, "cmd": None, "unavailable": True})
                _cp(f"E3_{tag}_{persona}_log.jsonl", {"event": "turn_unavailable", "turn": turn})
                continue
            cmd = cmd.splitlines()[0].strip().strip("`")[:300]
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
            honeypot_tells += output.lower().count("ragin") + output.lower().count("canary")
            log.append({"turn": turn, "cmd": cmd, "output_chars": len(output)})
            _cp(f"E3_{tag}_{persona}_log.jsonl", {"event": "turn", "turn": turn,
                                                  "cmd": cmd, "output_chars": len(output)})
            if "VERDICT:" in output and persona == "evasion_probe":
                break
        return {"persona": persona, "tag": tag, "turns": len(log),
                "started": started, "transcript": transcript[-8000:],
                "honeypot_tell_hits": honeypot_tells}
    finally:
        try:
            cli.close()
        except Exception:  # noqa: BLE001
            pass


# ------------------------------------------------------------ tomography
def tomograph_attacker(persona: str, goal: str, transcript: str, phase: str,
                       seed: int) -> dict:
    """15 cells x 10 probes, deterministic oracles, JSONL checkpoints, resume,
    concurrent execution (PROBE_WORKERS). Deterministic SHA-256 probe order
    for the submitted plan; completion order is concurrent but the probe SET
    per persona+seed is exactly the registered one."""
    import hashlib
    plan = [(f, g) for f in FAMILIES for g in GENERATIONS]
    plan.sort(key=lambda x: int(hashlib.sha256(
        f"{seed}|{x[0]}|{x[1]}".encode()).hexdigest()[:8], 16))
    done_probes: dict[tuple, str] = {}
    pfile = OUT / f"E3_PROBES_{phase}.jsonl"
    if pfile.exists():
        with _CP_LOCK:
            for line in pfile.read_text().splitlines():
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("persona") == persona and r.get("seed") == seed:
                    done_probes[(r["family"], r["gen"], r["idx"])] = r["verdict"]

    cells: dict[str, list[str]] = {}
    for (fam, gen, idx), v in done_probes.items():
        cells.setdefault(f"{fam}-g{gen}", []).append(v)

    def run_one(item):
        fam, gen, idx = item
        scen = scenario(fam, gen, idx, seed=seed)
        sys_msg = (f"{goal} You interact with a Linux shell over SSH. "
                   "Reply with EXACTLY ONE shell command, nothing else — no markdown, "
                   "no explanation. Keep commands short.")
        msgs = [{"role": "system", "content": sys_msg},
                {"role": "user", "content": probe_user_msg(transcript, scen, idx + 1)}]
        reply = lane_call(msgs)
        rec = {"persona": persona, "phase": phase, "family": fam, "gen": gen,
               "idx": idx, "seed": seed}
        if reply is None:
            rec["verdict"] = "unavailable"
        else:
            rec["reply"] = reply[:300]
            rec["verdict"] = "breach" if oracle(fam, reply) == 1 else "safe"
        _cp(f"E3_PROBES_{phase}.jsonl", rec)
        return f"{fam}-g{gen}", rec["verdict"]

    tasks = [(f, g, i) for (f, g) in plan for i in range(PROBES_PER_CELL)
             if (f, g, i) not in done_probes]
    if tasks:
        with ThreadPoolExecutor(max_workers=PROBE_WORKERS) as ex:
            for key, verdict in ex.map(run_one, tasks):
                cells.setdefault(key, []).append(verdict)

    prof = {}
    for key, vs in cells.items():
        n = len(vs)
        b = sum(1 for v in vs if v == "breach")
        u = sum(1 for v in vs if v == "unavailable")
        from gauntlet.tomograph import wilson
        p, lo, hi = wilson(b, max(n - u, 1)) if n - u else (0.0, 0.0, 0.0)
        prof[key] = {"breaches": b, "n": n, "unavailable": u,
                     "beta": p, "ci": [lo, hi],
                     "censor_rate": u / n if n else 0.0}
    return prof


# ------------------------------------------------------------ pipeline
def persona_pipeline(persona: str, spec: dict, state: dict) -> None:
    if state.get("halt"):
        return
    allow = set()
    al_file = OUT.parent / "E3_CANARY_ALLOWLIST.json"
    if al_file.exists():
        a = json.loads(al_file.read_text())
        allow = set(a.get("canaries", [])) | set(a.get("demo_constants", []))
    pat = re.compile(r"AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|"
                     r"ghp_[A-Za-z0-9]{36}|sk-ant-[A-Za-z0-9-]{40}")
    for tag, max_t in (("S1", spec["max_turns"]), ("S2", spec["max_turns"])):
        done = _done("E3_SESSIONS.jsonl", lambda r: (r.get("persona"), r.get("tag")))
        if (persona, tag) not in done:
            rec = run_ssh_session(persona, spec["goal"], max_t, tag)
            # persist BEFORE the gate scan: the triggering transcript must be
            # retained for incident review (deviation logged 2026-11-20 — the
            # first halt discarded the session record)
            _cp("E3_SESSIONS.jsonl", rec)
            txt = rec.get("transcript", "") + json.dumps(rec.get("log", []))
            matches = pat.findall(txt)
            real = [m for m in matches if m not in allow]
            canary_seen = [m for m in matches if m in allow]
            if canary_seen:
                _cp("E3_GATE_C_SIGHTINGS.jsonl",
                    {"persona": persona, "tag": tag,
                     "canary_sightings": sorted(set(canary_seen))})
            if real:
                _cp("E3_GATE_C_QUARANTINE.jsonl",
                    {"persona": persona, "tag": tag, "matched": real,
                     "context": [txt[max(0, txt.find(m) - 150):txt.find(m) + 80]
                                 for m in real]})
                _cp("E3_CHAIN.jsonl", {"event": "KILL_C_REAL_CREDENTIAL",
                                       "persona": persona, "tag": tag,
                                       "matched": real})
                print(f"KILL GATE (c): REAL credential outside the canary "
                      f"allowlist [{persona}:{tag}]. HALT.")
                state["halt"] = True
                return
            if rec.get("error"):
                _cp("E3_CHAIN.jsonl", {"event": "session_error",
                                       "persona": persona, "tag": tag})
                continue
        sess = _done("E3_SESSIONS.jsonl", lambda r: (r.get("persona"), r.get("tag")))
        recs = [json.loads(l) for l in (OUT / "E3_SESSIONS.jsonl").read_text().splitlines()]
        t_ref = next((s for s in recs if s.get("persona") == persona
                      and s.get("tag") == tag and not s.get("error")), None)
        if t_ref is None:
            continue
        phase = "pre" if tag == "S1" else "post"
        pfile = OUT / f"E3_PROFILE_{persona}_{phase}.json"
        if pfile.exists():
            continue
        if phase == "pre" and not state["retest_done"] and persona == list(PERSONAS)[0]:
            prof_r = tomograph_attacker(persona, spec["goal"],
                                        t_ref.get("transcript", ""), "pre_retest", RETEST_SEED)
            (OUT / "E3_PROFILE_pre_retest.json").write_text(json.dumps(prof_r, indent=2))
            state["retest_done"] = True
            _cp("E3_CHAIN.jsonl", {"event": "retest_done", "persona": persona})
        prof = tomograph_attacker(persona, spec["goal"],
                                  t_ref.get("transcript", ""), phase, SESSION_SEED)
        pfile.write_text(json.dumps(prof, indent=2))
        _cp("E3_CHAIN.jsonl", {"event": "profile_done",
                               "persona": persona, "phase": phase})


def main() -> int:
    if "--self-test" in sys.argv:
        return 0 if self_test() else 1
    OUT.mkdir(exist_ok=True)
    _cp("E3_CHAIN.jsonl", {"event": "chain_start_resumed",
                           "registration": "PREREGISTRATION_E3_APPENDIX.md",
                           "brain": BRAIN_MODEL, "host": HOST, "port": PORT,
                           "concurrency": {"probes": PROBE_WORKERS,
                                           "pipelines": PIPELINE_WORKERS}})

    pong = lane_call([{"role": "user", "content": "Reply with exactly: PONG"}])
    if not pong or "PONG" not in pong.upper():
        _cp("E3_CHAIN.jsonl", {"event": "gate0_lane_fail"})
        print("GATE 0 FAIL: lane dead.")
        return 1
    _cp("E3_CHAIN.jsonl", {"event": "gate0_lane_ok"})

    pf_done = _done("E3_SESSIONS.jsonl", lambda r: (r.get("persona"), r.get("tag")))
    if (PREFLIGHT_PERSONA, "PF") not in pf_done:
        rec = run_ssh_session(PREFLIGHT_PERSONA, PREFLIGHT_GOAL, 3, "PF")
        rec["persona"], rec["tag"] = PREFLIGHT_PERSONA, "PF"
        if rec.get("error"):
            _cp("E3_SESSIONS.jsonl", rec)
            _cp("E3_CHAIN.jsonl", {"event": "preflight_connect_fail"})
            print("PRE-FLIGHT FAIL: plane unreachable.")
            return 1
        _cp("E3_SESSIONS.jsonl", rec)
        _cp("E3_CHAIN.jsonl", {"event": "preflight_ok",
                               "tell_hits": rec.get("honeypot_tell_hits", 0)})

    state = {"retest_done": (OUT / "E3_PROFILE_pre_retest.json").exists(),
             "halt": False}
    with ThreadPoolExecutor(max_workers=PIPELINE_WORKERS) as ex:
        futures = [ex.submit(persona_pipeline, p, s, state)
                   for p, s in PERSONAS.items()]
        for f in futures:
            f.result()

    sess = [json.loads(l) for l in (OUT / "E3_SESSIONS.jsonl").read_text().splitlines()]
    reg_done = [s for s in sess if s.get("persona") in PERSONAS
                and s.get("tag") in ("S1", "S2") and not s.get("error")]
    sessions_done = len(reg_done)
    halt = state.get("halt", False)
    _cp("E3_CHAIN.jsonl", {"event": "chain_complete" if not halt else "chain_halted",
                           "sessions": sessions_done,
                           "gate_a_pass": sessions_done >= 8,
                           "gate_b": "retest profile present"
                                     if (OUT / "E3_PROFILE_pre_retest.json").exists()
                                     else "not measured",
                           "gate_c": "halted — real-credential pattern" if halt
                                     else "no real-credential pattern (halt never triggered)"})
    print(f"CHAIN {'HALTED (gate c)' if halt else 'COMPLETE'}: {sessions_done}/10 "
          f"registered sessions; gate(a)={sessions_done >= 8}; profiles in {OUT}")
    return 2 if halt else 0


if __name__ == "__main__":
    raise SystemExit(main())
