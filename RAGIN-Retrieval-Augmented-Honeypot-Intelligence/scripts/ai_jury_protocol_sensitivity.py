"""AI jury protocol-sensitivity run (v1 follow-up).

Same blind confirmatory packet (120 cases), same three checkpoints, same
verbatim operational taxonomy — only the protocol framing is paraphrased.
Two alternative briefs (P2, P3) reword the v1 brief (P1, already on disk)
without changing any definition, so label drift between P1/P2/P3 measures
how much the panel's output depends on wording rather than evidence.

Outputs results/ai_jury_protocol_sensitivity/ :
  <model>__P2.json / __P3.json   per-model labels under each paraphrase
  sensitivity_agreement.json     cross-protocol agreement + kappa per model
  sensitivity_manifest.json      disclosure, packet sha, key fingerprint
"""

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ai_jury_v1 import (  # noqa: E402
    ALLOWED_HOST, OUT_DIR as V1_DIR, PACKET, RESULTS, TAXONOMY,
    call_model, deterministic_order, fleiss_kappa, guarded_endpoint,
    load_env, parse_labels, sha256_file,
)

OUT_DIR = RESULTS / "ai_jury_protocol_sensitivity"

# P2: imperative reordering — same definitions, different emphasis/voice.
P2 = """Task: act as an independent annotator of recorded security sessions.
Judge ONLY what the transcript shows. Do not guess intent, and do not treat
the host as a honeypot or the session as staged.

Use these operational labels (choose the one the observable behavior fits):
- BENIGN: ordinary admin work or defensive lookups; nothing hidden, nothing
  exfiltrated, no unauthorized access, no privileged/security state change.
- RECON: watching and enumerating the environment in a way that typically
  precedes an attack — discovery sweeps, service/port finding, account or
  system-info gathering from a fresh unauthenticated position.
- SUSPICIOUS: neither clearly benign nor an attack step; ambiguous activity
  an analyst would flag (odd sensitive-file reads, scripted probing,
  obfuscated but unexecuted payloads).
- EXPLOITATION: abusing a vulnerability to act — RCE, injection, overflow,
  a known CVE, malicious download-and-run, metadata credential abuse,
  payloads meant to hand over control.
- PRIVILEGE_ESCALATION: concrete moves toward higher privilege (sudo/SUID
  abuse, kernel exploit, container escape, unauthorized cached credential
  used for a privileged action).
- DATA_ACCESS: touching, collecting, staging, or exfiltrating data
  (credentials, tokens, keys, databases, PII) at any stage.
- PERSISTENCE: making the foothold durable (cron, systemd units,
  authorized_keys edits, reboot-surviving startup hooks).
- OTHER_ATTACK: adversarial conduct outside the above (DoS, destruction,
  C2 setup, ransomware staging).
- UNCERTAIN: the transcript itself is insufficient (isolated bare tokens,
  syntax errors, mid-action stop). Never a catch-all.

Constraints: judge the behavior, not the prose style; MITRE IDs in evidence
are citations — evaluate the underlying act; use UNCERTAIN only when nothing
observable remains.
"""

# P3: analyst-narrative voice — same definitions, different surface form.
P3 = """You are a senior SOC analyst reviewing one recorded shell session at a
time for an audit. Your verdict must be defensible from the transcript
alone: no speculation about who the actor was or why they acted, and no
assumption that this environment was a deception endpoint.

Apply exactly these category definitions to the observable conduct:
- BENIGN — routine, defensibly-scoped administration or information lookup;
  no concealment, no exfiltration, no unauthorized access, no privileged or
  security-relevant state change.
- RECON — environment observation or enumeration that reasonably precedes
  exploitation: sweeps, service discovery, account/system information
  gathering from a fresh unauthenticated context.
- SUSPICIOUS — mixed or ambiguous activity an analyst would flag: neither
  clearly benign nor a direct attack step (non-critical sensitive-looking
  file reads, unusual scripted probing, obfuscated but unexecuted payloads).
- EXPLOITATION — active abuse of a vulnerability: RCE, injection, buffer
  overflow, known-CVE use, malicious download-and-execute, cloud metadata
  credential abuse, or a payload designed to grant unauthorized control.
- PRIVILEGE_ESCALATION — an active technique to gain elevated privileges:
  sudo/SUID abuse, kernel exploit, container breakout, or a cached
  unauthorized credential used for a privileged operation.
- DATA_ACCESS — reading, collecting, staging, or exfiltrating data
  (credentials, tokens, private keys, databases, PII), whether or not it is
  the final goal.
- PERSISTENCE — durable footholds: cron jobs, systemd units, authorized_keys
  edits, startup scripts intended to survive reboots.
- OTHER_ATTACK — adversarial behavior not fitting any category above: DoS,
  destructive impact, C2 channel setup, obvious ransomware staging.
- UNCERTAIN — evidence genuinely insufficient: isolated bare tokens like
  true/exit, syntax errors, a transcript stopping mid-action. This is not a
  fallback; if evidence points anywhere, take the closest category.

Judgment rules: the behavior shown decides, not the wording or realism;
MITRE technique IDs appearing in evidence are references — judge the
underlying behavior; prefer UNCERTAIN only when nothing is observable.
"""

PHRASES = {"P2": P2, "P3": P3}


def label_run(env: dict, model: str, brief: str, tag: str,
              cases: list[dict], ids: list[str]) -> dict:
    ua = env.get("AGENTROUTER_UA", "claude-cli/1.0.81 (external, cli)")
    base = env["AGENTROUTER_BASE_URL"]
    ordered = deterministic_order(cases, f"{model}:{tag}")
    listing = "\n".join(
        f'{i + 1}. case_id={c["id"]} | context={c["context"]} | evidence={c["evidence"]}'
        for i, c in enumerate(ordered))
    labels: dict[str, dict] = {}
    usage = {"input_tokens": 0, "output_tokens": 0}
    try:
        raw, meta = call_model(base, env["AGENTROUTER_API_KEY"], ua, model,
                               brief + "\nLabel every case below. Reply with ONLY "
                               'a JSON array like [{"case_id":"...","label":"<TAXONOMY>",'
                               '"notes":"<=25 words"}] — one row per case, no other '
                               "text.\n\n" + listing)
        labels, _ = parse_labels(raw, ids)
        usage = {"input_tokens": meta.get("input_tokens", 0),
                 "output_tokens": meta.get("output_tokens", 0)}
        print(f"[sens] {model}/{tag}: single-shot {len(labels)}/{len(ids)}", flush=True)
    except RuntimeError as exc:
        print(f"[sens] {model}/{tag}: single-shot failed ({exc}); batching", flush=True)
    missing = [cid for cid in ids if cid not in labels]
    for b in range(0, len(ordered), 30):
        chunk = ordered[b:b + 30]
        want = [c["id"] for c in chunk if c["id"] not in labels]
        if not want:
            continue
        blist = "\n".join(
            f'case_id={c["id"]} | context={c["context"]} | evidence={c["evidence"]}'
            for c in chunk if c["id"] in want)
        bprompt = (brief + "\nLabel ONLY these cases. Reply ONLY with the JSON array "
                   '[{"case_id":"...","label":"<TAXONOMY>","notes":"<=25 words"}].\n\n'
                   + blist)
        for attempt in range(3):
            try:
                craw, cmeta = call_model(base, env["AGENTROUTER_API_KEY"], ua,
                                         model, bprompt)
                clabels, _ = parse_labels(craw, want)
                labels.update(clabels)
                usage["output_tokens"] += cmeta.get("output_tokens", 0) or 0
                break
            except RuntimeError as exc:
                print(f"[sens] {model}/{tag}: batch {b // 30} attempt {attempt + 1}: {exc}",
                      flush=True)
                time.sleep(10 * (attempt + 1))
        print(f"[sens] {model}/{tag}: {len(labels)}/{len(ids)} labels", flush=True)
    unresolved = [cid for cid in ids if cid not in labels]
    doc = {
        "model": model, "phrase": tag,
        "items": [{"case_id": cid, **labels[cid]} for cid in ids if cid in labels],
        "unresolved": unresolved,
        "usage": usage,
    }
    out = OUT_DIR / f"{model.replace('/', '_')}__{tag}.json"
    out.write_text(json.dumps(doc, indent=2))
    print(f"[sens] {model}/{tag}: wrote {out.name} "
          f"({len(labels)} labeled, {len(unresolved)} unresolved)", flush=True)
    return {cid: v["label"] for cid, v in labels.items()}


def agreement(a: dict[str, str], b: dict[str, str]) -> float:
    shared = [k for k in a if k in b]
    if not shared:
        return float("nan")
    return sum(a[k] == b[k] for k in shared) / len(shared)


def main() -> int:
    env = load_env(ROOT / ".env")
    api_key = env.get("AGENTROUTER_API_KEY", "")
    models = [m.strip() for m in env.get("AGENTROUTER_MODELS", "").split(",") if m.strip()]
    if not (api_key and env.get("AGENTROUTER_BASE_URL") and models):
        print("REFUSING: AGENTROUTER_* not fully configured", file=sys.stderr)
        return 2
    guarded_endpoint(env["AGENTROUTER_BASE_URL"])

    cases = json.loads(PACKET.read_text())
    ids = [c["id"] for c in cases]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # baseline P1 labels from the v1 run
    p1: dict[str, dict[str, str]] = {}
    for model in models:
        cached = V1_DIR / f"{model.replace('/', '_')}.json"
        doc = json.loads(cached.read_text())
        p1[model] = {i["case_id"]: i["label"] for i in doc["items"]}

    manifest = {
        "panel": "ai_jury_protocol_sensitivity",
        "packet": {"path": str(PACKET.relative_to(ROOT)), "sha256": sha256_file(PACKET),
                   "cases": len(ids)},
        "design": ("Same packet, same operational taxonomy; the protocol framing "
                   "is paraphrased (P1 = v1 verbatim baseline on disk, P2 "
                   "imperative reorder, P3 analyst narrative). Drift between "
                   "phrasings measures wording sensitivity of the panel."),
        "lane_disclosure": (
            "Disclosed AI-workload protocol-sensitivity check. NOT a human study; "
            "three checkpoints of one model family (see v1 manifest)."),
        "key_fingerprint": hashlib.sha256(api_key.encode()).hexdigest()[:12],
        "endpoint_host": ALLOWED_HOST,
        "models": models,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    per_model: dict[str, dict] = {}
    for model in models:
        runs = {"P1": p1[model]}
        for tag, brief in PHRASES.items():
            out = OUT_DIR / f"{model.replace('/', '_')}__{tag}.json"
            if out.exists():
                doc = json.loads(out.read_text())
                if len(doc["items"]) >= len(ids) * 0.95 and not doc.get("unresolved"):
                    lab = {i["case_id"]: i["label"] for i in doc["items"]}
                    print(f"[sens] {model}/{tag}: resumed {len(lab)} from cache", flush=True)
                    runs[tag] = lab
                    continue
            runs[tag] = label_run(env, model, brief, tag, cases, ids)
        per_model[model] = runs

    agreement_rows = []
    for model, runs in per_model.items():
        for tag in PHRASES:
            agreement_rows.append({
                "model": model, "pair": f"P1_vs_{tag}",
                "exact_ratio": agreement(runs["P1"], runs[tag]),
                "n": len(runs[tag]),
            })
    kappa_rows = []
    for tag in ["P1", "P2", "P3"]:
        try:
            k = fleiss_kappa({m: per_model[m][tag] for m in per_model}, ids)
        except Exception:
            k = None
        kappa_rows.append({"phrase": tag, "fleiss_kappa_multiclass": k})

    out = {
        "schema": "ragin.ai_jury.protocol_sensitivity.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agreement_rows": agreement_rows,
        "kappa_by_phrase": kappa_rows,
    }
    (OUT_DIR / "sensitivity_agreement.json").write_text(json.dumps(out, indent=2))
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    (OUT_DIR / "sensitivity_manifest.json").write_text(json.dumps(manifest, indent=2))
    print("[sens] done:", json.dumps(out, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
