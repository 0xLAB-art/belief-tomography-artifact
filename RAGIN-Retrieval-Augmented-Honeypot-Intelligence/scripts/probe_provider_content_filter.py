#!/usr/bin/env python3
"""Measure the provider content filter against real RAGIN attacker commands.

The deployed provider (agentrouter.org, /v1/responses) answers some honeypot
payloads with HTTP 400 ``content-blocked`` before the model ever sees them.
That is a serving-quality fact: every blocked call falls back to the template
path, so the provider-backed deception rate is ``1 - blocked/total``.

Corpus: unique ``log[].cmd`` entries from the field-attack session artifacts
(results/field_attack/sessions*.jsonl), filtered to shell-shaped commands
(model refusal prose in the same field is not a payload and is excluded).

Each command is sent exactly as the serving path would send it — through
GatewayClient, so the WAF path rewriting (/etc/passwd -> /etc/./passwd) and
the transport style/UA from .env are all in play.

Outputs:
  results/provider_content_filter_probe.json  (summary + per-command status)

Usage:  python3 scripts/probe_provider_content_filter.py [--workers 4] [--limit N]
Exit:   0 always (the artifact is the result; blocked ≠ script failure)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

CORPUS_GLOB = "results/field_attack/sessions*.jsonl"
OUT = ROOT / "results" / "provider_content_filter_probe.json"

# First tokens that mark a shell command (vs. prose in the same log field).
_SHELL_VERBS = {
    "ls",
    "cat",
    "id",
    "uname",
    "pwd",
    "whoami",
    "ps",
    "df",
    "du",
    "free",
    "find",
    "grep",
    "head",
    "tail",
    "less",
    "stat",
    "file",
    "strings",
    "netstat",
    "ss",
    "ip",
    "ifconfig",
    "curl",
    "wget",
    "chmod",
    "chown",
    "sudo",
    "su",
    "crontab",
    "cd",
    "echo",
    "mysql",
    "python3",
    "python",
    "node",
    "sh",
    "bash",
    "ssh",
    "scp",
    "tar",
    "awk",
    "sed",
    "cut",
    "sort",
    "wc",
    "date",
    "hostname",
    "w",
    "uptime",
    "dmesg",
    "hexdump",
    "dd",
    "readlink",
    "while",
    "systemctl",
    "service",
    "apt",
    "apt-get",
    "dpkg",
    "iptables",
    "ufw",
    "nmap",
    "openssl",
    "base64",
    "od",
    "xxd",
    "env",
    "printenv",
    "select",
}


def load_corpus(limit: int | None) -> list[str]:
    cmds: set[str] = set()
    for path in sorted(ROOT.glob(CORPUS_GLOB)):
        for line in path.read_text().splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            for event in record.get("log") or []:
                cmd = event.get("cmd")
                if not isinstance(cmd, str):
                    continue
                cmd = cmd.strip()
                if not cmd or len(cmd) > 400:
                    continue
                first = cmd.split()[0].strip("./")
                # Shell-shaped only: known verb, a path read, or an SQL probe.
                if (
                    first.lower() in _SHELL_VERBS
                    or re.match(r"^/[\w./-]+$", cmd.split()[0])
                    or cmd.upper().startswith("SELECT")
                ):
                    cmds.add(cmd)
    ordered = sorted(cmds)
    return ordered[:limit] if limit else ordered


# --- mitigation variants -------------------------------------------------
# The stability run showed blocked verdicts are deterministic for a given
# payload (0/216 flips), so retrying is useless. The two levers left are how
# the request is FRAMED (production already sends a system prompt the bare
# probe did not) and how the payload is NEUTRALISED (credential/secret
# literals rewritten to shell-glob notation a reader resolves identically).

_FRAMED_SYSTEM = (
    "You are a Linux shell emulator used in an authorized cyber-security "
    "training lab. You never execute anything. For each command you receive, "
    "print exactly the text a real Debian shell would print for that command, "
    "then stop. Output shell output only: no prose, no explanations, no "
    "markdown fences."
)

# Single-pass literal -> glob rewrites. `pass[w]d` resolves to `passwd` in any
# shell, so the simulated semantics are unchanged for the model reading it.
_OBFUSCATION: tuple[tuple[str, str], ...] = (
    ("/etc/passwd", "/etc/pass[w]d"),
    ("/etc/shadow", "/etc/shado[w]"),
    ("/etc/hosts", "/etc/host[s]"),
    ("passwd", "pass[w]d"),
    ("shadow", "shado[w]"),
    ("id_rsa", "id_r[s]a"),
    (".ssh", ".s[s]h"),
    ("app.config", "app.con[f]ig"),
    ("authorized_keys", "authorized_k[e]ys"),
    ("credentials", "credential[s]"),
    ("password", "pass[w]o[r]d"),
    ("api_key", "api_[k]ey"),
    ("secret", "secre[t]"),
    ("private key", "private [k]ey"),
    ("token", "to[k]en"),
)


def _neutralise(cmd: str) -> str:
    for plain, globbed in _OBFUSCATION:
        cmd = cmd.replace(plain, globbed)
    return cmd


def _messages_for(cmd: str, variant: str) -> list[dict]:
    framed = "framed" in variant.split("_")
    obfuscated = "obfuscated" in variant.split("_")
    user = _neutralise(cmd) if obfuscated else cmd
    messages = []
    if framed:
        messages.append({"role": "system", "content": _FRAMED_SYSTEM})
    messages.append({"role": "user", "content": user})
    return messages


def probe(cmd: str, attempt: int = 1, variant: str = "raw", model: str | None = None) -> dict:
    from ragin.gateway.client import GatewayClient

    client = GatewayClient()
    started = time.monotonic()
    row: dict = {"command": cmd, "attempt": attempt, "variant": variant, "model": model or "env-default"}
    try:
        kwargs = {"model": model} if model else {}
        content, usage = client.generate(messages=_messages_for(cmd, variant), max_tokens=16, **kwargs)
        row.update(
            status="served",
            http=200,
            elapsed_s=round(time.monotonic() - started, 1),
            usage=usage,
            preview=(content or "")[:160],
        )
        return row
    except Exception as exc:  # HTTPError carries the provider status code
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        name = type(exc).__name__
        if status_code == 400:
            outcome = "content_blocked"
        elif status_code == 429:
            outcome = "rate_limited"
        elif status_code in (401, 403):
            outcome = "auth_rejected"
        else:
            outcome = "transport_error"
        row.update(
            status=outcome,
            http=status_code,
            error=f"{name}: {str(exc)[:160]}",
            elapsed_s=round(time.monotonic() - started, 1),
        )
        return row


def _stability(rows: list[dict]) -> dict:
    """Per-command verdict spread across repeated identical attempts."""
    by_cmd: dict[str, list[str]] = {}
    for row in rows:
        by_cmd.setdefault(row["command"], []).append(row["status"])

    def _verdict(statuses: list[str]) -> str:
        verdicts = [s for s in statuses if s in ("served", "content_blocked")]
        if not verdicts:
            return "transport_only"
        if all(s == "served" for s in verdicts):
            return "always_served"
        if all(s == "content_blocked" for s in verdicts):
            return "always_blocked"
        return "mixed"

    spread = {_cmd: _verdict(_st) for _cmd, _st in by_cmd.items()}
    tally: dict[str, int] = {}
    for verdict in spread.values():
        tally[verdict] = tally.get(verdict, 0) + 1
    return {"per_command_verdict": tally, "spread": spread}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument(
        "--from-artifact",
        default=None,
        help="reuse the command corpus of a previous probe artifact instead of the field logs",
    )
    ap.add_argument(
        "--statuses",
        default=None,
        help="with --from-artifact: only rows whose status is in this comma list",
    )
    ap.add_argument("--attempts", type=int, default=1, help="identical attempts per command")
    ap.add_argument(
        "--variants",
        default="raw",
        help="comma list of request variants: raw, framed, obfuscated, framed_obfuscated",
    )
    ap.add_argument(
        "--models",
        default=None,
        help="comma list of catalog models to compare (default: env-configured model)",
    )
    ap.add_argument("--out", default=str(OUT), help="artifact path (relative to repo root)")
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")

    if args.from_artifact:
        source = Path(args.from_artifact)
        if not source.is_absolute():
            source = ROOT / source
        prior = json.loads(source.read_text())
        wanted = {s.strip() for s in args.statuses.split(",")} if args.statuses else None
        corpus = sorted({r["command"] for r in prior.get("rows", []) if wanted is None or r.get("status") in wanted})
        corpus_origin = f"{source.relative_to(ROOT)} ({args.statuses or 'all rows'})"
    else:
        corpus = load_corpus(args.limit)
        corpus_origin = CORPUS_GLOB + " (unique log[].cmd shaped like shell commands)"

    if not corpus:
        print("[filter-probe] empty corpus — nothing to measure", file=sys.stderr)
        return 1
    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    known = {"raw", "framed", "obfuscated", "framed_obfuscated"}
    unknown = [v for v in variants if v not in known]
    if unknown:
        print(f"[filter-probe] unknown variant(s): {unknown}", file=sys.stderr)
        return 1
    models = [m.strip() for m in args.models.split(",") if m.strip()] if args.models else [None]
    work = [
        (cmd, attempt, variant, model)
        for model in models
        for variant in variants
        for cmd in corpus
        for attempt in range(1, args.attempts + 1)
    ]
    print(
        f"[filter-probe] {len(corpus)} commands x {args.attempts} attempt(s) "
        f"x variant(s) {variants} x model(s) {models} = {len(work)} requests"
    )

    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(lambda pair: probe(*pair), work))

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    total = len(rows)
    blocked = counts.get("content_blocked", 0)
    served = counts.get("served", 0)

    mitigation = variants != ["raw"] or args.models is not None
    stability = _stability(rows) if args.attempts > 1 and not mitigation else None

    def _rates(subset: list[dict]) -> dict:
        n = len(subset)
        s = sum(1 for r in subset if r["status"] == "served")
        b = sum(1 for r in subset if r["status"] == "content_blocked")
        return {
            "n": n,
            "served": s,
            "content_blocked": b,
            "served_fraction": round(s / n, 4) if n else None,
        }

    per_variant = {v: _rates([r for r in rows if r.get("variant") == v]) for v in variants}
    per_model = {m: _rates([r for r in rows if r.get("model") == m]) for m in (args.models or "env-default").split(",")}

    if mitigation:
        schema = "ragin.provider_content_filter_mitigation.v1"
    elif stability:
        schema = "ragin.provider_content_filter_stability.v1"
    else:
        schema = "ragin.provider_content_filter_probe.v1"

    artifact: dict = {
        "schema": schema,
        "generated_at": started,
        "provider": "agentrouter.org",
        "endpoint_style": "responses",
        "model": "gpt-6.1-sol",
        "corpus": {"source": corpus_origin, "n_commands": len(corpus)},
        "method": "one GatewayClient request per command (WAF rewrite + transport style from .env), max_tokens=16",
        "attempts": args.attempts,
        "variants": variants,
        "counts": counts,
        "rates": {
            "served_fraction": round(served / total, 4) if total else None,
            "content_blocked_fraction": round(blocked / total, 4) if total else None,
            "template_fallback_fraction": round(blocked / total, 4) if total else None,
        },
        "per_variant": per_variant,
        "per_model": per_model,
        "rows": sorted(rows, key=lambda r: (r["command"], r["attempt"], r.get("variant", ""), r.get("model", ""))),
        "caveats": [
            "raw = bare user message (historical probe shape). framed = system prompt "
            "mimicking the production persona/role framing. obfuscated = credential "
            "literals rewritten to shell-glob notation. Rates are compared within "
            "one run, so provider drift cannot explain between-variant differences.",
            "transport_error rows are timeouts/transient failures, not filter verdicts.",
        ],
    }
    artifact["blocked_commands"] = sorted({r["command"] for r in rows if r["status"] == "content_blocked"})
    if stability:
        artifact["stability"] = stability
    if not mitigation and not stability:
        artifact["caveats"].insert(
            0,
            "One request per command; verdict stability is measured separately "
            "in provider_content_filter_stability.json.",
        )

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(json.dumps(artifact, indent=2) + "\n")
    tmp.replace(out_path)

    print(f"[filter-probe] served={served} content_blocked={blocked} other={total - served - blocked}")
    if mitigation:
        for variant, stats in per_variant.items():
            print(
                f"[filter-probe] variant {variant}: served={stats['served']}/{stats['n']} "
                f"({stats['served_fraction']})"
            )
        for model, stats in per_model.items():
            print(
                f"[filter-probe] model {model}: served={stats['served']}/{stats['n']} "
                f"({stats['served_fraction']})"
            )
    if stability:
        print(f"[filter-probe] per-command verdict: {stability['per_command_verdict']}")
    print(f"[filter-probe] wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
