"""Blinded human-annotation proxy labeling for evaluation-set construction.

This implements the LABELING protocol from the research plan, using an LLM + rubric
as a resource-limited proxy for human annotators. It is strictly a limitation:
we have no independent human-labeled malicious/benign labels for the Cowrie-derived
sessions; the proxy labels are used only to form an evaluation set shape and measure
relative behavior, and the protocol's limitation is documented in the research report.

Two categories get proxy labels:
- "attack-patterned" sessions (>=2 commands matching known attack signatures)
- "recon" sessions (recon-patterned commands like whoami/id/echo sequences)

For each session we generate:
1. A blinded command sequence (command text only, no metadata)
2. An LLM-proxy label using a strict rubric (malicious/benign, attack_stage, confidence)
3. The label+reasoning is saved for auditing

Run with the existing venv:
    .venv/bin/python scripts/laya_label_pipeline.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO / "results" / "laya_research"
OUT = RESULTS_DIR / "proxy_labeled_sessions.json"
SCRIPTS_DIR = REPO / "scripts"

SESSION_FILES = list(Path("data/sessions").glob("*.jsonl"))
SESSION_MAP = {p.stem: p for p in SESSION_FILES}

ATTACK_SIDS = [
    "ses-2eccff4828454032",
    "sup-vote",
    "ses-1dc7f26f324d4688",
    "ses-454d015a585b4191",
]
RECON_SIDS = [
    "ses-afc6f65328e945af",
    "ses-b45f6af1f2164217",
    "ses-41a2bed9333e41e8",
    "ses-a45ebdabc4844916",
    "ses-c640b0753e6a4aa2",
    "ses-05caf136052d4da6",
    "ses-afc8d498504e4630",
    "ses-47d4f7d40c8b4293",
]

existing_labels = {}
for p in RESULTS_DIR.glob("external_baseline_*.json"):
    try:
        d = json.loads(p.read_text())
    except Exception:
        continue
    arm = d.get("arm")
    if arm in ("cowrie",) and isinstance(d.get("per_row"), list) and d["per_row"]:
        for row in d["per_row"]:
            commands = row.get("commands") or []
            if commands:
                sid = row.get("session_id") or "unknown"
                existing_labels[sid] = {
                    "label": row.get("best_label") or row.get("label") or "unknown",
                    "attack_stage": row.get("attack_stage") or row.get("stage") or "unknown",
                    "confidence": float(row.get("confidence", 0.5)),
                    "reasoning": row.get("reasoning") or row.get("note") or "label from existing external baseline run",
                    "source_run": p.name,
                }
        break

print(f"Existing labeled evaluation dataset found: {len(existing_labels)} sessions with labels")
if existing_labels:
    for sid, lab in sorted(existing_labels.items()):
        print(f"  {sid}: {lab['label']} / {lab['attack_stage']} (from {lab['source_run']})")
print()


def extract_session_cmds(path: Path) -> list[str]:
    out = []
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return out
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("event_type") == "attacker_input":
            out.append(str(obj.get("data", {}).get("command", "")))
    return out


def build_labeling_payload(session_id: str, cmds: list[str]) -> dict:
    return {
        "session_id": session_id,
        "n_commands": len(cmds),
        "commands": cmds,
        "rubric": """
You are a blind code reviewer for a cybersecurity research evaluation.
Given the command sequence below from an SSH session, assign a label WITHOUT
knowing the attacker, source IP, timestamps, or any metadata.

Label rules:
- Malicious: the session contains exploits, scanning, exfiltration, credential theft,
  persistence, lateral movement, data theft, or evidence erasure.
- Benign: ordinary administrative activity, reconnaissance that does not cross into
  exploitation or credential theft, or automated/red-team probing with no real harm.
- Attack stage: one of {recon, credential_theft, persistence, lateral_movement,
  exfiltration, exploitation, cleanup, benign_administration}. Use "benign_administration"
  only if the session is fully benign.
- Confidence: 0.0-1.0 estimating how sure you are of the label.
- Reasoning: brief explanation.

Return JSON exactly:
{"label": "malicious"|"benign", "attack_stage": "...", "confidence": 0.0-1.0, "reasoning": "..."}
""".strip(),
        "task": "Return ONLY the JSON label object (no preamble, no markdown).",
    }


def run_llm_proxy(payload: dict) -> dict | None:
    script = SCRIPTS_DIR / "llm_proxy_label.py"
    if not script.exists():
        print("  llm_proxy_label.py missing — skip LLM proxy labeling")
        return None
    try:
        r = subprocess.run(
            [sys.executable, str(script), json.dumps(payload)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(REPO),
        )
        if r.returncode != 0:
            print(f"    LLM proxy returned nonzero rc {r.returncode}: {r.stderr[-200:]}")
            return None
        parsed = json.loads(r.stdout.strip())
        parsed["_elapsed_s"] = round(time.time() - (payload.get("_t0") or time.time()), 2)
        parsed["_raw"] = r.stdout.strip()
        return parsed
    except Exception as e:
        print(f"    LLM proxy exception: {e}")
        return None


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_records = []

    if existing_labels:
        print("=== Using existing independent labels from external_baseline_cowrie ===")
        for sid, lab in sorted(existing_labels.items()):
            sp = SESSION_MAP.get(sid)
            if not sp:
                continue
            cmds = extract_session_cmds(sp)
            if not cmds:
                continue
            record = {
                "session_id": sid,
                "category": "cowrie_labeled",
                "command_count": len(cmds),
                "commands": cmds,
                "source_file": str(sp.relative_to(REPO)),
                "label_source": "external_baseline_cowrie",
                "label": lab["label"],
                "attack_stage": lab["attack_stage"],
                "confidence": lab["confidence"],
                "reasoning": lab["reasoning"],
                "source_run": lab["source_run"],
            }
            out_records.append(record)
            print(f"  {sid}: {lab['label']} / {lab['attack_stage']} ({len(cmds)} commands)")

    for category, sids in [("attack_patterned", ATTACK_SIDS), ("recon", RECON_SIDS)]:
        sessions = [SESSION_MAP[sid] for sid in sids if sid in SESSION_MAP]
        if not sessions:
            continue
        print(f"\n=== {category} (LLM proxy if needed) ===")
        for sp in sessions:
            sid = sp.stem
            cmds = extract_session_cmds(sp)
            if not cmds:
                continue
            existing = existing_labels.get(sid)
            if existing:
                record = {
                    "session_id": sid,
                    "category": category,
                    "command_count": len(cmds),
                    "commands": cmds,
                    "source_file": str(sp.relative_to(REPO)),
                    "label_source": "existing_independent",
                    "label": existing["label"],
                    "attack_stage": existing["attack_stage"],
                    "confidence": existing["confidence"],
                    "reasoning": existing["reasoning"],
                }
                out_records.append(record)
                print(f"  {sid}: using existing label {existing['label']} (skip proxy)")
                continue
            print(f"  {sid}: {len(cmds)} commands, first: {cmds[0][:60]}")
            payload = build_labeling_payload(sid, cmds)
            payload["_t0"] = time.time()
            t0 = time.time()
            label = run_llm_proxy(payload)
            elapsed = round(time.time() - t0, 1)
            if label:
                record = {
                    "session_id": sid,
                    "category": category,
                    "command_count": len(cmds),
                    "commands": cmds,
                    "source_file": str(sp.relative_to(REPO)),
                    "label_source": "llm_proxy_rubric",
                    "label": label.get("label", "unknown"),
                    "attack_stage": label.get("attack_stage", "unknown"),
                    "confidence": float(label.get("confidence", 0.5)),
                    "reasoning": label.get("reasoning", ""),
                    "proxy_elapsed_s": elapsed,
                    "proxy_raw": label.get("_raw", ""),
                }
            else:
                record = {
                    "session_id": sid,
                    "category": category,
                    "command_count": len(cmds),
                    "commands": cmds,
                    "source_file": str(sp.relative_to(REPO)),
                    "label_source": "none",
                    "label": "unknown",
                    "attack_stage": "unknown",
                    "confidence": 0.0,
                    "reasoning": "LLM proxy unavailable; no independent label exists",
                }
            out_records.append(record)
            if label:
                print(f"    -> label={label.get('label')}, stage={label.get('attack_stage')}, conf={label.get('confidence')}")
            else:
                print("    -> NO PROXY LABEL (LLM proxy unavailable)")
            print()

    OUT.write_text(json.dumps(out_records, indent=1, default=str))
    print(f"\nSaved {len(out_records)} records to {OUT}")
    print()
    n_layable = sum(1 for r in out_records if r["label"] in ("malicious", "benign"))
    print(f"Of {len(out_records)} total, {n_layable} have a usable label for eval-set shaping.")


if __name__ == "__main__":
    main()
