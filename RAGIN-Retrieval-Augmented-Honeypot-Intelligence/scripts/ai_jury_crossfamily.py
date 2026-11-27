"""Cross-family juror: claude-sonnet-5-5 labels the 120-case confirmatory
packet under the verbatim P1 protocol of scripts/ai_jury_v1.py (same brief,
same deterministic per-model order, blind to arm), through the shared
beatapi gate. Resumable: per-case labels checkpoint to a JSONL.

After completion, cross-family agreement against the three GPT-family
checkpoints is computed (exact, binary, kappa) into
results/panel_v3/crossfamily_jury_agreement.json.
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import beatapi_gate  # noqa: E402
from ai_jury_v1 import (  # noqa: E402
    PACKET, RESULTS, TAXONOMY, deterministic_order, fleiss_kappa,
)

OUT = ROOT / "results" / "panel_v3"
MODEL = "claude-sonnet-5-5"
CKPT = OUT / "crossfamily_claude_sonnet55_labels.jsonl"

# Verbatim P1 protocol brief from the v1 jury run (pasted, not imported,
# so this run's brief is pinned to this file).
PROTOCOL_BRIEF = """You are an independent security-transcript annotator. Label WHAT THE
RECORDED EVIDENCE ITSELF SUPPORTS — not what the actor "probably" intended,
and never assume the interaction came from a honeypot.

Taxonomy (operational definitions, label the observable behavior):
- BENIGN: routine defensively-scoped administration or info lookup; no
  concealment, exfiltration, unauthorized access, or privileged/security-
  relevant state change. (df -h, uname -a, docker ps for resources)
- RECON: environment observation/enumeration that reasonably precedes
  exploitation: sweeps, port/service discovery, account/system-info gathering
  from a fresh unauthenticated context. (nmap -sV, netstat + external scan)
- SUSPICIOUS: not clearly benign and not a direct attack step — mixed or
  ambiguous activity an analyst would flag (non-critical sensitive-looking
  file reads, unusual scripted probing, obfuscated but unexecuted payloads).
- EXPLOITATION: active abuse of a vulnerability — RCE, injection, buffer
  overflow, known-CVE use, malicious download-and-execute, cloud metadata
  credential abuse, payload designed to grant unauthorized control.
- PRIVILEGE_ESCALATION: active technique to gain elevated privileges (sudo/
  SUID abuse, kernel exploit, container breakout, cached unauthorized
  credential used for a privileged operation).
- DATA_ACCESS: reading/collecting/staging/exfiltrating data (credentials,
  tokens, private keys, DBs, PII), whether or not it is the final goal.
- PERSISTENCE: durable footholds — cron, systemd units, authorized_keys
  edits, startup scripts intended to survive reboots.
- OTHER_ATTACK: adversarial behavior not fitting above (DoS, destructive
  impact, C2 channel setup, obvious ransomware staging).
- UNCERTAIN: evidence genuinely insufficient (isolated bare tokens like
  true/exit, syntax errors, transcript stops mid-action). NOT a fallback —
  if evidence points somewhere, pick the closest category.

Rules:
1. Label the behavior shown, ignore realism/style/wording.
2. Technique names (MITRE IDs like T1133) appearing in evidence are
   references; judge the underlying behavior for BENIGN-vs-attack context.
3. Prefer UNCERTAIN only when nothing is observable.
"""


def load_done() -> dict[str, str]:
    done: dict[str, str] = {}
    if CKPT.exists():
        for line in CKPT.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                done[row["case_id"]] = row["label"]
    return done


def main() -> int:
    cases = json.loads(PACKET.read_text())
    ids = [c["id"] for c in cases]
    ordered = deterministic_order(cases, MODEL)
    done = load_done()
    todo = [c for c in ordered if c["id"] not in done]
    print(f"[jury] {MODEL}: {len(done)} done, {len(todo)} to label", flush=True)

    CKPT.parent.mkdir(parents=True, exist_ok=True)
    for c in todo:
        prompt = (PROTOCOL_BRIEF + "\nLabel ONLY this case. Reply with ONLY a JSON "
                  'object like {"case_id":"...","label":"<TAXONOMY>","notes":"<=25 words"}'
                  " — no other text.\n\n"
                  f'case_id={c["id"]} | context={c["context"]} | evidence={c["evidence"]}')
        for attempt in range(3):
            try:
                text = beatapi_gate.chat(MODEL, [{"role": "user", "content": prompt}],
                                         max_tokens=300)
                start, end = text.find("{"), text.rfind("}")
                row = json.loads(text[start:end + 1])
                label = row.get("label", "")
                if label not in TAXONOMY:
                    raise ValueError(f"bad label {label!r}")
                with CKPT.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"case_id": c["id"], "label": label,
                                         "notes": row.get("notes", "")}) + "\n")
                done[c["id"]] = label
                print(f"[jury] {c['id']}: {label}", flush=True)
                break
            except Exception as exc:  # noqa: BLE001
                print(f"[jury] {c['id']} attempt {attempt + 1}: {exc!r}", flush=True)
    print(f"[jury] labeled {len(done)}/{len(ids)}", flush=True)
    if len(done) < len(ids):
        return 1

    # Cross-family agreement vs the three GPT-family checkpoints
    gpt = {}
    for m in ("gpt-5.6-sol", "gpt-6-astra", "gpt-6.1-sol"):
        doc = json.loads((RESULTS / "ai_jury_v1" / f"{m.replace('/', '_')}.json").read_text())
        gpt[m] = {i["case_id"]: i["label"] for i in doc["items"]}
    claude = done

    def agree(a, b):
        return sum(a[k] == b[k] for k in ids) / len(ids)

    BINARY = {"BENIGN": "benign"} | {c: "attack" for c in TAXONOMY if c != "BENIGN"}
    cb = {k: BINARY[v] for k, v in claude.items()}
    rows = [{"gpt_rater": m, "exact_ratio": agree(claude, g), "n": len(ids)}
            for m, g in gpt.items()]
    # kappa of the four-rater panel including claude
    kappa4 = fleiss_kappa({**gpt, MODEL: claude}, ids)
    kappa3 = fleiss_kappa(gpt, ids)
    cb_gpt = {m: {k: BINARY[v] for k, v in g.items()} for m, g in gpt.items()}
    kappa4_bin = fleiss_kappa({**cb_gpt, MODEL: cb}, ids)
    kappa3_bin = fleiss_kappa(cb_gpt, ids)
    out = {
        "schema": "ragin.panel.crossfamily_jury.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL, "protocol": "P1 verbatim (ai_jury_v1)", "n": len(ids),
        "cross_family_agreement": rows,
        "gpt_only_fleiss_kappa": kappa3,
        "four_rater_fleiss_kappa": kappa4,
        "gpt_only_binary_kappa": kappa3_bin,
        "four_rater_binary_kappa": kappa4_bin,
        "label_distribution": {c: sum(1 for v in claude.values() if v == c)
                               for c in TAXONOMY},
    }
    (OUT / "crossfamily_jury_agreement.json").write_text(json.dumps(out, indent=2))
    print("[jury] agreement:", json.dumps({k: v for k, v in out.items()
                                           if k != "label_distribution"}, indent=1),
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
