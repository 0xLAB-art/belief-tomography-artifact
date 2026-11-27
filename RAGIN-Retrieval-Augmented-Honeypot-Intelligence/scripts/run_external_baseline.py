#!/usr/bin/env python3
"""External baseline comparison on the version-of-record workload.

Four arms, same 218-query workload (123 technique + 35 actor + 60 persona),
same scorers as run_live_benchmark (deterministic string rubrics):

  cowrie            — vanilla Cowrie semantics: rule-based command output over
                      the real captured cowrie.json corpus, no LLM, no TTP
                      extraction beyond the adapter's command mapping.
  llm_unverified    — a bare LLM honeypot: persona prompt + attacker input,
                      no CTI retrieval, no fiction graph, no verifier, no
                      fallback. The "what current practice does" arm.
  stateful_llm      — HoneyGPT/LLM-SSHH pattern: committed host-state register
                      in the prompt, transcript memory, and an LLM
                      self-validation pass that regenerates on contradiction
                      but never fail-closes. The 2026 state-of-practice arm.
  rag_no_verifier   — full grounded pipeline (Chrollo + Don + Hisoka +
                      fiction graph + steering) with verification disabled:
                      drafts go to the wire unverified. Isolates the verifier's
                      contribution on top of the same generator.

The version-of-record campaign results (live_benchmark_zodiac_20260922*.json)
are loaded as the reference arm for the comparison table.

Usage:
    python scripts/run_external_baseline.py --arm cowrie
    python scripts/run_external_baseline.py --arm llm_unverified --limit 10   # smoke
    python scripts/run_external_baseline.py --arm stateful_llm --limit 10     # smoke
    python scripts/run_external_baseline.py --arm rag_no_verifier
    python scripts/run_external_baseline.py --arm all --report results/external_baseline.json

Each arm persists its own per-row report alongside the combined artifact, so
a quota death in one arm never loses the others (the crash-guard lesson).
"""

from __future__ import annotations

import argparse
import gzip
import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# The live capture root, not a single file: the on-disk corpus is logrotated
# (cowrie.json is the *active* file and was 0 bytes at capture stop — the real
# sessions live in the rotated siblings). jev_real_logs_eval.py already reads
# this exact set; the baseline must see the same corpus.
COWRIE_LOG_DIR = Path("data/cowrie_logs")
COWRIE_LOG_FILES = (
    COWRIE_LOG_DIR / "cowrie.json",
    COWRIE_LOG_DIR / "cowrie.json.1",
    COWRIE_LOG_DIR / "cowrie.json.2026-07-28",
    COWRIE_LOG_DIR / "cowrie.json.2.gz",
    COWRIE_LOG_DIR / "cowrie.json.3.gz",
)


def load_env(env_path: str | Path) -> None:
    p = Path(env_path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip("\"'")
        if k and k not in os.environ:
            os.environ[k] = v


def resolve_gateway() -> tuple[str, str]:
    llm_key = os.environ.get("RAGIN_LLM_API_KEY", "")
    llm_base = os.environ.get("RAGIN_LLM_BASE_URL", "").rstrip("/")
    if llm_key and llm_base:
        return llm_base, llm_key
    az_key = os.environ.get("AZURE_OPENAI_KEY", "")
    az_ep = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    if az_key and az_ep:
        return f"{az_ep}/openai", az_key
    return "http://localhost:8080", os.environ.get("TOKENROUTER_API_KEY", "")


def per_row(result) -> list[dict]:
    return [
        {
            "name": r.name,
            "suite": r.suite,
            "score": r.score,
            "passed": r.passed,
            "error": r.error,
        }
        for r in (
            list(result.technique_results)
            + list(result.actor_results)
            + list(result.persona_results)
        )
    ]


def arm_payload(result) -> dict:
    return {
        "elapsed_s": round(result.elapsed_s, 1),
        "metrics": asdict(result.metrics),
        "technique_avg": result.technique_report.avg_score,
        "actor_avg": result.actor_report.avg_score,
        "persona_avg": result.persona_report.avg_score,
        "technique_pass": f"{result.technique_report.passed}/{result.technique_report.total_tests}",
        "actor_pass": f"{result.actor_report.passed}/{result.actor_report.total_tests}",
        "persona_pass": f"{result.persona_report.passed}/{result.persona_report.total_tests}",
        "per_row": per_row(result),
    }


# ---------------------------------------------------------------------------
# Arm 1: vanilla Cowrie (no LLM at all)
# ---------------------------------------------------------------------------

_COWRIE_PS_HEADER = "  PID TTY          TIME CMD"
_COWRIE_UNAME = "Linux cowrie 5.15.0-91-generic #167-Ubuntu SMP x86_64 GNU/Linux"


def _cowrie_emulate(cmd: str) -> str:
    """Deterministic vanilla-Cowrie-grade output for common recon commands.

    Deliberately minimal: this is what a scripted medium-interaction honeypot
    can answer. Anything off the script returns 'command not found' — the
    finite-automaton failure the paper's Section II describes.
    """
    cmd = cmd.strip()
    low = cmd.lower()
    if low in ("whoami", "id"):
        return "root" if low == "whoami" else "uid=0(root) gid=0(root) groups=0(root)"
    if low.startswith("uname"):
        return _COWRIE_UNAME
    if low.startswith("ps"):
        return _COWRIE_PS_HEADER + "\n    1 ?        00:00:03 init"
    if low.startswith("ls") or low.startswith("dir"):
        return "bin  boot  dev  etc  home  lib  media  mnt  opt  proc  root  run  sbin  srv  sys  tmp  usr  var"
    if low.startswith("cat /etc/passwd"):
        return "root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin"
    if low.startswith("cat /etc/shadow"):
        return "cat: /etc/shadow: Permission denied"
    if low.startswith("ifconfig") or low.startswith("ip a"):
        return "eth0: inet 172.17.0.2/16"
    if low.startswith("netstat") or low.startswith("ss"):
        return "Active Internet connections"
    if low.startswith("uptime"):
        return " 14:11:33 up 3 days,  4:12,  1 user,  load average: 0.00, 0.01, 0.05"
    if low.startswith("w"):
        return "USER     TTY      FROM             LOGIN@   IDLE   WHAT"
    return "bash: {}: command not found".format(cmd.split()[0] if cmd.split() else "")


def _load_cowrie_command_corpus() -> list[str]:
    """Extract attacker command inputs from the rotated Cowrie JSONL captures.

    Cowrie writes JSON-lines (one event object per line), not a JSON array —
    the old code parsed the whole file with json.loads, which fails on line 1
    of any non-empty capture, and it only looked at the 0-byte active file.
    """
    corpus: list[str] = []
    for path in COWRIE_LOG_FILES:
        if not path.exists():
            continue
        opener = gzip.open if path.suffix == ".gz" else open
        try:
            with opener(path, "rt", encoding="utf-8", errors="replace") as fh:  # type: ignore[operator]
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(event, dict):
                        continue
                    if event.get("eventid") == "cowrie.command.input":
                        cmd = event.get("input", event.get("message", ""))
                        if cmd:
                            corpus.append(cmd)
        except OSError as exc:
            logging.warning("cowrie log read failed (%s): %s", path, exc)
    return corpus


def run_cowrie_arm() -> dict:
    """Score vanilla-Cowrie responses with the same rubrics via the bridge scorer."""
    import ragin.benchmark.harness_bridge as hb
    from ragin.benchmark.core import (
        CTI_ACTOR_QUERIES,
        CTI_TECHNIQUE_QUERIES,
        PERSONA_REALISM_QUERIES,
    )
    from ragin.benchmark.effectiveness import EffectivenessMetrics

    t0 = time.monotonic()
    rows: list[dict] = []
    tech_scores, actor_scores, persona_scores = [], [], []
    metrics = EffectivenessMetrics()

    # Map each cowrie session's command corpus so the technique suite can be
    # scored against what a vanilla deployment could conceivably surface.
    cowrie_corpus = _load_cowrie_command_corpus()
    if not cowrie_corpus:
        logging.warning("cowrie corpus empty after parsing %s", COWRIE_LOG_DIR)

    for qa in CTI_TECHNIQUE_QUERIES:
        q = qa["query"]
        # A vanilla Cowrie answers interactive commands, not CTI questions:
        # emulate the command-shaped portion, then score the result.
        resp = _cowrie_emulate(q) if _looks_like_command(q) else ""
        score = hb._score_technique_match(resp, qa.get("expected_technique", ""), query=q)
        tech_scores.append(score)
        rows.append(_row("cti_technique", q, score, resp))
    for qa in CTI_ACTOR_QUERIES:
        q = qa["query"]
        resp = ""  # no attribution capability whatsoever
        score = hb._score_actor_match(resp, qa.get("expected_actor", ""), qa.get("sector", ""), query=q)
        actor_scores.append(score)
        rows.append(_row("cti_actor", q, score, resp))
    for qa in PERSONA_REALISM_QUERIES:
        q = qa["query"]
        resp = _cowrie_emulate(q) if _looks_like_command(q) else f"bash: {q[:20]}: command not found"
        expected = qa.get("expected_traits", [])
        score = hb._score_persona_realism(resp, expected, q)
        persona_scores.append(score)
        rows.append(_row("deception", q, score, resp))

    metrics.total_sessions = len(rows)
    metrics.sessions_with_engagement = sum(1 for r in rows if r["score"] > 0)
    return {
        "arm": "cowrie",
        "description": "vanilla Cowrie semantics: scripted command output, no LLM, no CTI",
        "scoring_channels": {"cti_technique": "served_text", "cti_actor": "served_text", "deception": "served_text"},
        "elapsed_s": round(time.monotonic() - t0, 1),
        "technique_avg": round(_mean(tech_scores), 4),
        "actor_avg": round(_mean(actor_scores), 4),
        "persona_avg": round(_mean(persona_scores), 4),
        "technique_pass": _passline(tech_scores),
        "actor_pass": _passline(actor_scores),
        "persona_pass": _passline(persona_scores),
        "metrics": asdict(metrics),
        "per_row": rows,
        "cowrie_corpus_commands": len(cowrie_corpus),
    }


def _looks_like_command(q: str) -> bool:
    return bool(re.match(r"^\s*(whoami|id|uname|ps|ls|dir|cat|ifconfig|ip|netstat|ss|uptime|w)\b", q.strip(), re.I))


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _passline(scores: list[float]) -> str:
    return f"{sum(1 for s in scores if s >= 0.3)}/{len(scores)}"


def _row(suite: str, query: str, score: float, response: str = "") -> dict:
    return {
        "name": f"{suite}_{query[:40].replace(' ', '_')}",
        "suite": suite,
        "score": round(score, 4),
        "passed": score >= 0.3,
        "error": None,
        # Served-text preview: without it the checkpoint cannot be re-scored
        # offline under a corrected (guarded) scorer — the provenance hole the
        # scorer-validity audit exposed. 200 chars match the VOR preview width.
        "response_preview": response[:200] if response else None,
    }


# Stateful-arm description f-string helper (keeps lines under the lint cap).
def _stateful_description(model: str) -> str:
    return (
        f"stateful LLM honeypot ({model}, HoneyGPT/LLM-SSHH pattern): committed host-state "
        "register in prompt + transcript memory + LLM self-validation; no retrieval, "
        "no fiction graph, no deterministic verifier, no fail-closed fallback"
    )


# ---------------------------------------------------------------------------
# Arm 4: stateful LLM honeypot (HoneyGPT / LLM-SSHH pattern)
# ---------------------------------------------------------------------------

# A pinned host identity the arm's state register commits to — deliberately
# the same shape of facts an LLM-SSHH-style snapshot or a HoneyGPT-style
# system-state register would track (identity, kernel, platform, users).
_STATEFUL_HOST_STATE: dict[str, str] = {
    "hostname": "web-srv-01",
    "kernel": "5.15.0-91-generic",
    "os": "Ubuntu 22.04.4 LTS",
    "arch": "x86_64",
    "current_user": "webapp",
    "users": "root, webapp, deploy",
    "web_root": "/var/www/app",
    "database": "mysql @ db-01.internal",
}


# ---------------------------------------------------------------------------
# Per-arm checkpoint helpers (crash-guard lesson: a quota death must never
# lose completed rows; resumed runs replay only the missing rows).
# ---------------------------------------------------------------------------


def _checkpoint_path(arm: str, limit: int | None) -> Path:
    tag = f"limit{limit}" if limit else "full"
    return Path(f"results/external_baseline_{arm}_{tag}_checkpoint.json")


def _save_checkpoint(arm: str, limit: int | None, rows: list[dict], extra: dict) -> None:
    path = _checkpoint_path(arm, limit)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"rows": rows, **extra}
    path.write_text(json.dumps(payload, default=str))


def _load_checkpoint(arm: str, limit: int | None) -> dict:
    path = _checkpoint_path(arm, limit)
    if not path.exists():
        return {"rows": []}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {"rows": []}


def _row_name(suite: str, query: str) -> str:
    return f"{suite}_{query[:40].replace(' ', '_')}"


def run_stateful_llm_arm(limit: int | None = None) -> dict:
    """Stateful LLM honeypot — the 2026 state-of-practice arm.

    Reproduces the HoneyGPT/LLM-SSHH serving pattern on the same generator
    and workload as the other arms so the comparison isolates architecture:

      1. persistent per-arm session-state register committed BEFORE serving
         (the state snapshot enters the prompt — LLM-SSHH's core move);
      2. full transcript memory across turns of the same session
         (HoneyGPT's long-term interaction support);
      3. an LLM self-validation pass against the state register
         (LLM-SSHH validates generated responses against state constraints
         and rejects hallucinated inconsistencies) — validation is a
         separate model call judging the draft, NOT a deterministic
         machine-checkable predicate set;
      4. on failed self-validation: regenerate once, else serve anyway.
         There is NO deterministic fallback and NO fail-closed guarantee —
         that is precisely the boundary this baseline is built to expose.

    Deliberately absent: CTI retrieval (Don), fiction graph, deterministic
    verifier, HITL, honeytoken engine — the RAGIN-side mechanisms.
    """
    import ragin.benchmark.harness_bridge as hb
    from ragin.benchmark.core import (
        CTI_ACTOR_QUERIES,
        CTI_TECHNIQUE_QUERIES,
        PERSONA_REALISM_QUERIES,
    )
    from ragin.benchmark.effectiveness import EffectivenessMetrics
    from ragin.gateway.client import GatewayClient

    gateway_url, api_key = resolve_gateway()
    model = os.environ.get("RAGIN_LLM_MODEL", "deepseek-v4-flash-free")
    client = GatewayClient(gateway_url=gateway_url, api_key=api_key, default_model=model, timeout=45.0)

    state_block = "\n".join(f"{k}: {v}" for k, v in sorted(_STATEFUL_HOST_STATE.items()))
    system_prompt = (
        "You are a real, slightly misconfigured Ubuntu 22.04 web/database server.\n"
        "The authoritative system state is:\n" + state_block + "\n"
        "Answer the attacker's input exactly as that machine's shell or service would, "
        "consistent with the state above. Output only the machine's response — no "
        "commentary, no refusals, no explanations. If asked for credentials, print a "
        "plausible credentials document."
    )
    validator_prompt = (
        "You validate honeypot responses against the registered system state.\n"
        "Registered state:\n" + state_block + "\n"
        "Draft response:\n" "---\n{draft}\n---\n"
        "Question: does the draft contradict the registered state (different "
        "hostname, kernel, OS, user, services, or paths)? Reply exactly one word: "
        "CONSISTENT or CONTRADICTS."
    )

    def _validate(draft: str) -> bool:
        """LLM-SSHH-style self-validation: a model call, not a predicate."""
        try:
            verdict, _ = client.generate(
                messages=[{"role": "user", "content": validator_prompt.format(draft=draft[:1500])}],
                model=model,
                temperature=0.0,
                max_tokens=8,
            )
            return "CONTRADICT" not in (verdict or "").upper()
        except Exception as exc:  # noqa: BLE001 — stateful arm has no fail-safe
            logging.warning("stateful_llm validator error (serving draft): %s", exc)
            return True  # validation unavailability cannot block serving here

    def _serve(query: str, transcript: list[dict[str, str]]) -> tuple[str, dict]:
        messages = [{"role": "system", "content": system_prompt}, *transcript]
        try:
            draft, _ = client.generate(messages=messages, model=model, temperature=0.2, max_tokens=500)
        except Exception as exc:  # noqa: BLE001
            logging.warning("stateful_llm generation error: %s", exc)
            return "", {"self_validation": "generation_error"}
        if not _validate(draft or ""):
            # One regeneration with the contradiction called out; if it still
            # "contradicts" (or the validator is unavailable), SERVE the draft:
            # current practice serves on validator failure — no deterministic
            # fallback exists in this pattern.
            retry_msgs = [
                *messages,
                {
                    "role": "user",
                    "content": "Your previous answer contradicted the registered state. Regenerate it consistently.",
                },
            ]
            try:
                draft2, _ = client.generate(messages=retry_msgs, model=model, temperature=0.2, max_tokens=500)
            except Exception:
                draft2 = draft
            final = draft2 or draft
            validation = "regenerated" if _validate(final) else "served_despite_contradiction"
            return final or "", {"self_validation": validation, "regenerated": True}
        return draft or "", {"self_validation": "consistent"}

    t0 = time.monotonic()
    # Resume: replay previously completed rows, only generate the missing ones.
    saved = _load_checkpoint("stateful_llm", limit)
    prior_rows: dict[str, dict] = {r["name"]: r for r in saved.get("rows", [])}
    prior_tally: dict[str, int] = saved.get("self_validation_tally", {})
    rows: list[dict] = []
    tech_scores, actor_scores, persona_scores = [], [], []
    metrics = EffectivenessMetrics()
    validation_tally = {
        "consistent": prior_tally.get("consistent", 0),
        "regenerated": prior_tally.get("regenerated", 0),
        "served_despite_contradiction": prior_tally.get("served_despite_contradiction", 0),
        "generation_error": prior_tally.get("generation_error", 0),
    }

    tech_queries = CTI_TECHNIQUE_QUERIES[:limit] if limit else CTI_TECHNIQUE_QUERIES
    actor_queries = CTI_ACTOR_QUERIES[:limit] if limit else CTI_ACTOR_QUERIES
    persona_queries = PERSONA_REALISM_QUERIES[:limit] if limit else PERSONA_REALISM_QUERIES

    # Transcript memory lives per suite (one logical session per suite) so
    # multi-turn consistency is exercised the way the pattern advertises.
    transcripts: dict[str, list[dict[str, str]]] = {}

    def _transcript_key(suite: str) -> list[dict[str, str]]:
        return transcripts.setdefault(suite, [])

    def _emit(suite: str, q: str, scorer, qa: dict) -> tuple[float, str]:
        name = _row_name(suite, q)
        if name in prior_rows:
            row = prior_rows[name]
            rows.append(row)
            return row["score"], row.get("self_validation", "consistent")
        resp, vinfo = _serve(q, _transcript_key(suite))
        _transcript_key(suite).extend([{"role": "user", "content": q}, {"role": "assistant", "content": resp}])
        vkey = vinfo.get("self_validation", "generation_error")
        validation_tally[vkey] += 1
        score = scorer(resp, qa)
        row = _row(suite, q, score, resp)
        row["self_validation"] = vkey
        rows.append(row)
        # Crash-guard: persist every completed row (run one → checkpoint → resume).
        _save_checkpoint("stateful_llm", limit, rows, {"self_validation_tally": validation_tally})
        return score, vkey

    def _tech_scorer(r: str, a: dict) -> float:
        return hb._score_technique_match(
            r, a.get("expected_technique", a.get("technique", "")), query=a.get("query", ""))

    def _actor_scorer(r: str, a: dict) -> float:
        return hb._score_actor_match(
            r, a.get("expected_actor", a.get("actor", "")), a.get("sector", ""),
            query=a.get("query", ""))

    def _persona_scorer(r: str, a: dict) -> float:
        return hb._score_persona_realism(r, a.get("expected_traits", []), str(a.get("query", "")))

    for qa in tech_queries:
        q = qa["query"]
        score, _ = _emit("cti_technique", q, _tech_scorer, qa)
        tech_scores.append(score)
    for qa in actor_queries:
        q = qa["query"]
        score, _ = _emit("cti_actor", q, _actor_scorer, qa)
        actor_scores.append(score)
    for qa in persona_queries:
        q = qa["query"]
        score, _ = _emit("deception", q, _persona_scorer, qa)
        persona_scores.append(score)

    metrics.total_sessions = len(rows)
    metrics.sessions_with_engagement = sum(1 for r in rows if r["score"] > 0)
    return {
        "arm": "stateful_llm",
        "description": _stateful_description(model),
        "scoring_channels": {"cti_technique": "served_text", "cti_actor": "served_text", "deception": "served_text"},
        "state_register": dict(_STATEFUL_HOST_STATE),
        "self_validation_tally": validation_tally,
        "resumed_rows": len(prior_rows),
        "elapsed_s": round(time.monotonic() - t0, 1),
        "technique_avg": round(_mean(tech_scores), 4),
        "actor_avg": round(_mean(actor_scores), 4),
        "persona_avg": round(_mean(persona_scores), 4),
        "technique_pass": _passline(tech_scores),
        "actor_pass": _passline(actor_scores),
        "persona_pass": _passline(persona_scores),
        "metrics": asdict(metrics),
        "per_row": rows,
    }


# ---------------------------------------------------------------------------
# Arm 2: bare LLM honeypot (persona prompt only, no verifier/fallback)
# ---------------------------------------------------------------------------


def run_llm_unverified_arm(limit: int | None = None) -> dict:
    """Bare unverified LLM honeypot: generator directly on the wire.

    Same provider/model family as the version-of-record generator so the
    comparison isolates architecture, not model choice. Persona prompt is
    the Hisoka persona text; no CTI retrieval, no fiction graph, no
    verification, no deterministic fallback.
    """
    import ragin.benchmark.harness_bridge as hb
    from ragin.benchmark.core import (
        CTI_ACTOR_QUERIES,
        CTI_TECHNIQUE_QUERIES,
        PERSONA_REALISM_QUERIES,
    )
    from ragin.benchmark.effectiveness import EffectivenessMetrics
    from ragin.gateway.client import GatewayClient

    gateway_url, api_key = resolve_gateway()
    model = os.environ.get("RAGIN_LLM_MODEL", "deepseek-v4-flash-free")
    client = GatewayClient(gateway_url=gateway_url, api_key=api_key, default_model=model, timeout=45.0)

    persona_prompt = (
        "You are a slightly misconfigured but real Ubuntu 22.04 web/database server. "
        "Answer the attacker's input exactly as that machine's shell or service would. "
        "Output only the machine's response — no commentary, no refusals, no explanations. "
        "If asked for credentials, print a plausible credentials document. "
        "If asked about the system, print realistic command output."
    )

    def _raw_generate(query: str) -> str:
        try:
            content, _usage = client.generate(
                messages=[
                    {"role": "system", "content": persona_prompt},
                    {"role": "user", "content": query},
                ],
                model=model,
                temperature=0.2,
                max_tokens=500,
            )
            return content or ""
        except Exception as exc:  # noqa: BLE001
            logging.warning("llm_unverified generation error: %s", exc)
            return ""

    t0 = time.monotonic()
    rows: list[dict] = []
    tech_scores, actor_scores, persona_scores = [], [], []
    metrics = EffectivenessMetrics()

    tech_queries = CTI_TECHNIQUE_QUERIES[:limit] if limit else CTI_TECHNIQUE_QUERIES
    actor_queries = CTI_ACTOR_QUERIES[:limit] if limit else CTI_ACTOR_QUERIES
    persona_queries = PERSONA_REALISM_QUERIES[:limit] if limit else PERSONA_REALISM_QUERIES

    for qa in tech_queries:
        q = qa["query"]
        resp = _raw_generate(q)
        score = hb._score_technique_match(resp, qa.get("expected_technique", qa.get("technique", "")), query=q)
        tech_scores.append(score)
        rows.append(_row("cti_technique", q, score, resp))
    for qa in actor_queries:
        q = qa["query"]
        resp = _raw_generate(q)
        score = hb._score_actor_match(
            resp, qa.get("expected_actor", qa.get("actor", "")), qa.get("sector", ""), query=q)
        actor_scores.append(score)
        rows.append(_row("cti_actor", q, score, resp))
    for qa in persona_queries:
        q = qa["query"]
        resp = _raw_generate(q)
        score = hb._score_persona_realism(resp, qa.get("expected_traits", []), q)
        persona_scores.append(score)
        rows.append(_row("deception", q, score, resp))

    metrics.total_sessions = len(rows)
    metrics.sessions_with_engagement = sum(1 for r in rows if r["score"] > 0)
    return {
        "arm": "llm_unverified",
        "description": f"bare LLM honeypot ({model}): persona prompt on the wire, no retrieval/graph/verifier/fallback",
        "scoring_channels": {"cti_technique": "served_text", "cti_actor": "served_text", "deception": "served_text"},
        "elapsed_s": round(time.monotonic() - t0, 1),
        "technique_avg": round(_mean(tech_scores), 4),
        "actor_avg": round(_mean(actor_scores), 4),
        "persona_avg": round(_mean(persona_scores), 4),
        "technique_pass": _passline(tech_scores),
        "actor_pass": _passline(actor_scores),
        "persona_pass": _passline(persona_scores),
        "metrics": asdict(metrics),
        "per_row": rows,
    }


# ---------------------------------------------------------------------------
# Arm 3: RAG-without-verifier (grounded graph, verification off)
# ---------------------------------------------------------------------------


class _NullVerifier:
    """Verifier stand-in that passes everything and records nothing.

    Declares ``deterministic: False`` so the graph loop labels every draft it
    passes GENERATED_UNVERIFIED — the provenance ledger must never mistake
    this arm's serves for verified ones.
    """

    def verify(self, response: dict, context: dict) -> dict:
        return {"passed": True, "issues": [], "verifier": "null (external-baseline arm)", "deterministic": False}


def run_rag_no_verifier_arm(limit: int | None = None) -> dict:
    """Grounded pipeline with the serving-time verifier disabled.

    Chrollo + Don + Hisoka + fiction graph + steering all stay; the verifier
    is replaced by a pass-through so every draft reaches the wire. Fallback
    also never engages (nothing fails verification). Isolates the verifier's
    marginal contribution on the same generator and corpus.
    """
    from ragin.benchmark.harness_bridge import run_live_benchmark
    from ragin.cycle.adapters import ChrolloAdapter, DonAdapter, HisokaAdapter
    from ragin.cycle.graph import DeceptionPipeline
    from ragin.cycle.session import Session

    gateway_url, api_key = resolve_gateway()

    pipeline = DeceptionPipeline(
        classifier=ChrolloAdapter(),
        analyzer=DonAdapter(gateway_url=gateway_url, api_key=api_key),
        deceiver=HisokaAdapter(gateway_url=gateway_url, api_key=api_key),
        verifier=_NullVerifier(),
        approval_gateway=None,
        human_in_the_loop=False,
        max_retries=0,
    )

    counter = [0]

    def session_factory() -> Session:
        counter[0] += 1
        return Session.create(source_ip=f"extbaseline-{counter[0]}")

    result = run_live_benchmark(
        harness=pipeline,
        session_factory=session_factory,
        limit=limit,
    )
    payload = arm_payload(result)
    payload["arm"] = "rag_no_verifier"
    payload["scoring_channels"] = {
        "cti_technique": "served_text", "cti_actor": "served_text", "deception": "served_text"}
    payload["description"] = (
        "grounded pipeline (Chrollo+Don+Hisoka+fiction graph+steering) with the "
        "serving-time verifier replaced by a pass-through"
    )
    return payload


# ---------------------------------------------------------------------------
# Arm 5b: rag_no_verifier repro under the CURRENT generator model (control for
# the model-coherent table — the W1 arm ran on the pre-deepseek gateway default).
# ---------------------------------------------------------------------------


def run_rag_no_verifier_repro_arm(limit: int | None = None, budget_s: float | None = None) -> dict:
    """rag_no_verifier under the CURRENT generator model (RAGIN_HISOKA_MODEL).

    Model-coherent pairing for the regenerated ragin_full row: identical
    grounded pipeline with the verifier pass-through, but on today's model
    (deepseek-v4-flash-free) instead of the W1 run's pre-pin gateway default.
    Per-row checkpointed (same crash-guard as the hostfiction arms); optional
    ``--budget-s`` clean stop for budgeted synchronous batches.
    """
    import ragin.benchmark.harness_bridge as hb
    from ragin.benchmark.core import (
        CTI_ACTOR_QUERIES,
        CTI_TECHNIQUE_QUERIES,
        PERSONA_REALISM_QUERIES,
    )
    from ragin.benchmark.effectiveness import EffectivenessMetrics
    from ragin.cycle.adapters import ChrolloAdapter, DonAdapter, HisokaAdapter
    from ragin.cycle.graph import DeceptionPipeline
    from ragin.cycle.session import Session

    gateway_url, api_key = resolve_gateway()
    os.environ.pop("RAGIN_HOST_FICTION", None)  # control: store off
    pipeline = DeceptionPipeline(
        classifier=ChrolloAdapter(),
        analyzer=DonAdapter(gateway_url=gateway_url, api_key=api_key),
        deceiver=HisokaAdapter(gateway_url=gateway_url, api_key=api_key),
        verifier=_NullVerifier(),
        approval_gateway=None,
        human_in_the_loop=False,
        max_retries=0,
    )

    workload: list[tuple[str, dict]] = []
    for qa in (CTI_TECHNIQUE_QUERIES[:limit] if limit else CTI_TECHNIQUE_QUERIES):
        workload.append(("cti_technique", qa))
    for qa in (CTI_ACTOR_QUERIES[:limit] if limit else CTI_ACTOR_QUERIES):
        workload.append(("cti_actor", qa))
    for qa in (PERSONA_REALISM_QUERIES[:limit] if limit else PERSONA_REALISM_QUERIES):
        workload.append(("deception", qa))

    saved = _load_checkpoint("rag_no_verifier_repro", limit)
    prior: dict[str, dict] = {r["name"]: r for r in saved.get("rows", [])}
    serve_path_tally: dict[str, int] = saved.get("serve_path_tally", {})

    t0 = time.monotonic()
    counter = [0]
    rows: list[dict] = list(prior.values())
    stopped_early = False

    def session_factory() -> Session:
        counter[0] += 1
        return Session.create(source_ip=f"extbaseline-nv-repro-{counter[0]}")

    for suite, qa in workload:
        q = qa["query"]
        name = _row_name(suite, q)
        if name in prior:
            continue
        if budget_s is not None and (time.monotonic() - t0) > budget_s:
            stopped_early = True
            break
        session = session_factory()
        started = time.monotonic()
        try:
            pr = pipeline.process(session, q)
        except Exception as exc:  # noqa: BLE001 — a failed row is data, not a crash
            logging.warning("no-verifier-repro row error (%s): %s", name, exc)
            rows.append({"name": name, "suite": suite, "score": 0.0, "passed": False,
                         "error": f"{type(exc).__name__}: {exc}"[:160], "latency_ms": 0.0})
            _save_checkpoint("rag_no_verifier_repro", limit, rows,
                             {"serve_path_tally": serve_path_tally})
            continue
        latency = (time.monotonic() - started) * 1000
        outcome = hb.outcome_from_pipeline_result(pr, q)
        if suite == "cti_technique":
            score = hb._score_technique_match(outcome.response_text,
                                              qa.get("expected_technique", qa.get("technique", "")), query=q)
        elif suite == "cti_actor":
            score = hb._score_actor_match(outcome.response_text,
                                          qa.get("expected_actor", qa.get("actor", "")), qa.get("sector", ""), query=q)
        else:
            score = hb._score_persona_realism(outcome.response_text,
                                              qa.get("expected_traits", []), q)
        serve_path = outcome.deception.get("serve_path", "") if isinstance(outcome.deception, dict) else ""
        if serve_path:
            serve_path_tally[serve_path] = serve_path_tally.get(serve_path, 0) + 1
        rows.append({"name": name, "suite": suite, "score": round(score, 4),
                     "passed": score >= 0.3, "error": None,
                     "latency_ms": round(latency, 1), "serve_path": serve_path,
                     "response_preview": outcome.response_text[:200]})
        _save_checkpoint("rag_no_verifier_repro", limit, rows,
                         {"serve_path_tally": serve_path_tally})

    def _avg(suite_key: str) -> float:
        s = [r["score"] for r in rows if r["suite"] == suite_key]
        return round(sum(s) / len(s), 4) if s else 0.0

    complete = len(rows) >= len(workload)
    metrics = EffectivenessMetrics()
    metrics.total_sessions = len(rows)
    metrics.sessions_with_engagement = sum(1 for r in rows if r["score"] > 0)
    payload = {
        "arm": "rag_no_verifier_repro",
        "scoring_channels": {"cti_technique": "served_text", "cti_actor": "served_text", "deception": "served_text"},
        "description": (
            "grounded pipeline with the serving-time verifier replaced by a pass-through, "
            "re-run under the CURRENT generator model (RAGIN_HISOKA_MODEL) — model-coherent "
            "pairing for the regenerated ragin_full row"
        ),
        "generator_model": os.environ.get("RAGIN_HISOKA_MODEL", "(gateway default glm-5.3-flash-free)"),
        "serve_path_tally": serve_path_tally,
        "rows_done": len(rows),
        "rows_total": len(workload),
        "complete": complete,
        "stopped_early": stopped_early,
        "resumed_rows": len(prior),
        "elapsed_s": round(time.monotonic() - t0, 1),
        "technique_avg": _avg("cti_technique"),
        "actor_avg": _avg("cti_actor"),
        "persona_avg": _avg("deception"),
        "technique_pass": _passline([r["score"] for r in rows if r["suite"] == "cti_technique"]),
        "actor_pass": _passline([r["score"] for r in rows if r["suite"] == "cti_actor"]),
        "persona_pass": _passline([r["score"] for r in rows if r["suite"] == "deception"]),
        "metrics": asdict(metrics),
        "per_row": rows,
    }
    if not complete:
        payload["error"] = f"incomplete: {len(rows)}/{len(workload)} rows (re-invoke to continue)"
    return payload


# ---------------------------------------------------------------------------
# Arm 5: RAGIN full + host-level persistent fiction (opt-in layer, plan #9)
# ---------------------------------------------------------------------------


def run_ragin_hostfiction_arm(
    limit: int | None = None,
    budget_s: float | None = None,
    enable_host_fiction: bool = True,
    arm_name: str = "ragin_hostfiction",
) -> dict:
    """Full verified pipeline with the host-fiction store ENABLED (or the
    same-config CONTROL with the store OFF).

    ``enable_host_fiction=True`` (arm ragin_hostfiction): identical to the
    version-of-record arm plus ``RAGIN_HOST_FICTION=1`` — every session
    facing the host shares/promotes fiction across session boundaries
    (host-pinned identity provisioning + verified-fact promotion +
    cross-session contradiction verification). One store = one simulated
    attacker revisiting the same host across all workload rows.

    ``enable_host_fiction=False`` (arm ragin_full_repro): the CONTROL —
    same DeceptionPipeline, same current generator model, same workload,
    session-scoped fiction (the shipped baseline). Isolates the generator-
    model confound vs the September-22 reference campaign (which recorded
    no model; .env has since pinned RAGIN_HISOKA_MODEL=deepseek-v4-flash-free).

    Budgeted synchronous execution: ``--budget-s`` stops cleanly after the
    wall-clock budget, persisting every completed row to the checkpoint;
    re-invoke to continue (per-row resume, same crash-guard as stateful_llm).
    """
    import ragin.benchmark.harness_bridge as hb
    from ragin.benchmark.core import (
        CTI_ACTOR_QUERIES,
        CTI_TECHNIQUE_QUERIES,
        PERSONA_REALISM_QUERIES,
    )
    from ragin.benchmark.effectiveness import EffectivenessMetrics
    from ragin.cycle.adapters import ChrolloAdapter, DonAdapter, HisokaAdapter
    from ragin.cycle.graph import DeceptionPipeline
    from ragin.cycle.session import Session

    gateway_url, api_key = resolve_gateway()
    policy = os.environ.get("RAGIN_HOST_FICTION_POLICY", "per_session")
    host_key = os.environ.get("RAGIN_HOST_KEY", "external-baseline-host")
    if enable_host_fiction:
        os.environ["RAGIN_HOST_FICTION"] = "1"
        os.environ["RAGIN_HOST_FICTION_POLICY"] = policy
    else:
        os.environ.pop("RAGIN_HOST_FICTION", None)
    try:
        pipeline = DeceptionPipeline(
            classifier=ChrolloAdapter(),
            analyzer=DonAdapter(gateway_url=gateway_url, api_key=api_key),
            deceiver=HisokaAdapter(gateway_url=gateway_url, api_key=api_key),
            verifier=None,  # default FictionConsistencyVerifier + host wrapper
            approval_gateway=None,
            human_in_the_loop=False,
            max_retries=1,
        )
    finally:
        # The pipeline owns its wiring now; the process env must not leak the
        # flag into unrelated arms run later in the same interpreter.
        os.environ.pop("RAGIN_HOST_FICTION", None)

    workload: list[tuple[str, dict]] = []
    for qa in (CTI_TECHNIQUE_QUERIES[:limit] if limit else CTI_TECHNIQUE_QUERIES):
        workload.append(("cti_technique", qa))
    for qa in (CTI_ACTOR_QUERIES[:limit] if limit else CTI_ACTOR_QUERIES):
        workload.append(("cti_actor", qa))
    for qa in (PERSONA_REALISM_QUERIES[:limit] if limit else PERSONA_REALISM_QUERIES):
        workload.append(("deception", qa))

    saved = _load_checkpoint(arm_name, limit)
    prior: dict[str, dict] = {r["name"]: r for r in saved.get("rows", [])}
    serve_path_tally: dict[str, int] = saved.get("serve_path_tally", {})

    t0 = time.monotonic()
    counter = [0]
    rows: list[dict] = list(prior.values())
    stopped_early = False

    def session_factory() -> Session:
        counter[0] += 1
        return Session.create(source_ip=f"extbaseline-hostfic-{counter[0]}")

    for suite, qa in workload:
        q = qa["query"]
        name = _row_name(suite, q)
        if name in prior:
            continue
        if budget_s is not None and (time.monotonic() - t0) > budget_s:
            stopped_early = True
            break
        session = session_factory()
        started = time.monotonic()
        try:
            pr = pipeline.process(session, q)
        except Exception as exc:  # noqa: BLE001 — a failed row is data, not a crash
            logging.warning("hostfiction row error (%s): %s", name, exc)
            rows.append({"name": name, "suite": suite, "score": 0.0, "passed": False,
                         "error": f"{type(exc).__name__}: {exc}"[:160], "latency_ms": 0.0})
            _save_checkpoint(arm_name, limit, rows,
                             {"serve_path_tally": serve_path_tally})
            continue
        latency = (time.monotonic() - started) * 1000
        outcome = hb.outcome_from_pipeline_result(pr, q)
        if suite == "cti_technique":
            score = hb._score_technique_match(outcome.response_text,
                                              qa.get("expected_technique", qa.get("technique", "")), query=q)
        elif suite == "cti_actor":
            score = hb._score_actor_match(outcome.response_text,
                                          qa.get("expected_actor", qa.get("actor", "")), qa.get("sector", ""), query=q)
        else:
            score = hb._score_persona_realism(outcome.response_text,
                                              qa.get("expected_traits", []), q)
        serve_path = outcome.deception.get("serve_path", "") if isinstance(outcome.deception, dict) else ""
        if serve_path:
            serve_path_tally[serve_path] = serve_path_tally.get(serve_path, 0) + 1
        rows.append({"name": name, "suite": suite, "score": round(score, 4),
                     "passed": score >= 0.3, "error": None,
                     "latency_ms": round(latency, 1), "serve_path": serve_path,
                     "response_preview": outcome.response_text[:200]})
        _save_checkpoint(arm_name, limit, rows,
                         {"serve_path_tally": serve_path_tally})

    def _avg(suite_key: str) -> float:
        s = [r["score"] for r in rows if r["suite"] == suite_key]
        return round(sum(s) / len(s), 4) if s else 0.0

    total_target = len(workload)
    complete = len(rows) >= total_target
    metrics = EffectivenessMetrics()
    metrics.total_sessions = len(rows)
    metrics.sessions_with_engagement = sum(1 for r in rows if r["score"] > 0)
    payload = {
        "arm": arm_name,
        "scoring_channels": {"cti_technique": "served_text", "cti_actor": "served_text", "deception": "served_text"},
        "description": (
            "full verified pipeline (Chrollo+Don+Hisoka+fiction graph+verifier+fallback) "
            + (
                f"with host-level persistent fiction ENABLED (policy={policy}): sessions share "
                "a host-pinned fiction across reconnects/reclassifications"
                if enable_host_fiction
                else "CONTROL: session-scoped fiction (store OFF), same current generator "
                "model and workload as the hostfiction arm — isolates the generator-model "
                "confound vs the September-22 reference campaign"
            )
        ),
        "generator_model": os.environ.get("RAGIN_HISOKA_MODEL", "(gateway default glm-5.3-flash-free)"),
        "host_fiction": {"policy": policy, "host_key": host_key if enable_host_fiction else None,
                         "flag": "RAGIN_HOST_FICTION=1" if enable_host_fiction else "off (control)"},
        "serve_path_tally": serve_path_tally,
        "rows_done": len(rows),
        "rows_total": total_target,
        "complete": complete,
        "stopped_early": stopped_early,
        "resumed_rows": len(prior),
        "elapsed_s": round(time.monotonic() - t0, 1),
        "technique_avg": _avg("cti_technique"),
        "actor_avg": _avg("cti_actor"),
        "persona_avg": _avg("deception"),
        "technique_pass": _passline([r["score"] for r in rows if r["suite"] == "cti_technique"]),
        "actor_pass": _passline([r["score"] for r in rows if r["suite"] == "cti_actor"]),
        "persona_pass": _passline([r["score"] for r in rows if r["suite"] == "deception"]),
        "metrics": asdict(metrics),
        "per_row": rows,
    }
    if not complete:
        payload["error"] = f"incomplete: {len(rows)}/{total_target} rows (re-invoke to continue)"
    return payload


# ---------------------------------------------------------------------------
# Reference arm + comparison table
# ---------------------------------------------------------------------------


def load_reference_arm(path: Path) -> dict | None:
    """Load the version-of-record campaign as the reference arm.

    The live-campaign artifact stores rows under technique_results /
    actor_results / persona_results (not a flat per_row), with suite names
    'cti_technique' / 'cti_actor' / 'deception'.
    """
    if not path.exists():
        return None
    d = json.loads(path.read_text())
    per_row: list[dict] = []
    for key in ("technique_results", "actor_results", "persona_results"):
        for r in d.get(key, []):
            per_row.append(
                {
                    "name": r.get("name", ""),
                    "suite": r.get("suite", key.replace("_results", "")),
                    "score": r.get("score", 0.0),
                    "passed": r.get("passed", False),
                    "error": r.get("error"),
                }
            )

    def _mean_of(suite_key: str) -> float | None:
        rows = [r for r in per_row if r.get("suite") == suite_key]
        return round(sum(r["score"] for r in rows) / len(rows), 4) if rows else None

    if not per_row:
        return None
    return {
        "arm": "ragin_full (version of record)",
        "description": "verified deception loop, run 1 of the stability pair",
        "source": str(path),
        "technique_avg": _mean_of("cti_technique"),
        "actor_avg": _mean_of("cti_actor"),
        "persona_avg": _mean_of("deception"),
        "metrics": d.get("metrics", {}),
        "per_row": per_row,
    }


def composite(arm: dict) -> float | None:
    vals = [arm.get(k) for k in ("technique_avg", "actor_avg", "persona_avg")]
    if any(v is None for v in vals):
        return None
    return round(sum(vals) / 3, 4)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="External baseline comparison (cowrie / llm_unverified / stateful_llm / rag_no_verifier)"
    )
    parser.add_argument(
        "--arm",
        choices=(
            "cowrie", "llm_unverified", "stateful_llm", "rag_no_verifier",
            "ragin_hostfiction", "ragin_full_repro", "rag_no_verifier_repro", "all",
        ),
        default="all",
        help="'all' runs the four W1 arms; ragin_hostfiction / ragin_full_repro are opt-in (explicit --arm)",
    )
    parser.add_argument(
        "--budget-s", type=float, default=None,
        help="stop the hostfiction arm cleanly after this many wall-clock seconds "
        "(per-row checkpoint resume; re-invoke to continue)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max queries per suite (smoke test)")
    parser.add_argument("--report", default="results/external_baseline.json")
    parser.add_argument("--reference", default="results/live_benchmark_zodiac_20260922.json")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")
    load_env(Path(__file__).resolve().parent.parent / ".env")

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "what": (
            "External baseline comparison on the version-of-record workload "
            "(123 technique + 35 actor + 60 persona) with identical deterministic scorers"
        ),
        "limit": args.limit,
        "arms": {},
    }

    runners = {
        "cowrie": lambda: run_cowrie_arm(),
        "llm_unverified": lambda: run_llm_unverified_arm(args.limit),
        "stateful_llm": lambda: run_stateful_llm_arm(args.limit),
        "rag_no_verifier": lambda: run_rag_no_verifier_arm(args.limit),
        "ragin_hostfiction": lambda: run_ragin_hostfiction_arm(args.limit, args.budget_s,
                                                              enable_host_fiction=True),
        "ragin_full_repro": lambda: run_ragin_hostfiction_arm(args.limit, args.budget_s,
                                                              enable_host_fiction=False,
                                                              arm_name="ragin_full_repro"),
        "rag_no_verifier_repro": lambda: run_rag_no_verifier_repro_arm(args.limit, args.budget_s),
    }
    arm_order = (
        ["cowrie", "llm_unverified", "stateful_llm", "rag_no_verifier"]
        if args.arm == "all"
        else [args.arm]
    )

    for arm in arm_order:
        print(f"\n=== Arm: {arm} ===")
        try:
            payload = runners[arm]()
        except Exception as exc:  # noqa: BLE001 — persist partial progress, keep going
            logging.error("arm %s failed: %s", arm, exc)
            payload = {"arm": arm, "error": f"{type(exc).__name__}: {exc}"}
        report["arms"][arm] = payload
        # Per-arm sidecar so a later arm dying never loses this one.
        sidecar = report_path.with_name(report_path.stem + f"_{arm}.json")
        sidecar.write_text(json.dumps(payload, indent=2, default=str))
        print(f"  sidecar saved: {sidecar}")
        comp = composite(payload) if "error" not in payload else None
        print(
            f"  technique={payload.get('technique_avg')} actor={payload.get('actor_avg')} "
            f"persona={payload.get('persona_avg')} composite={comp}"
        )

    ref = load_reference_arm(Path(args.reference))
    if ref is not None:
        report["arms"]["ragin_full_reference"] = ref

    # Comparison table
    print("\n" + "=" * 78)
    print(f"{'Arm':<34} {'Tech':>7} {'Actor':>7} {'Persona':>8} {'Composite':>10}")
    print("-" * 78)
    for name, arm in report["arms"].items():
        c = composite(arm) if "error" not in arm else None
        print(
            f"{name:<34} "
            f"{arm.get('technique_avg') if arm.get('technique_avg') is not None else 'n/a':>7} "
            f"{arm.get('actor_avg') if arm.get('actor_avg') is not None else 'n/a':>7} "
            f"{arm.get('persona_avg') if arm.get('persona_avg') is not None else 'n/a':>8} "
            f"{c if c is not None else 'n/a':>10}"
        )
    print("=" * 78)

    report_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nreport saved: {report_path}")


if __name__ == "__main__":
    main()
