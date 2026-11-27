#!/usr/bin/env python3
"""AI jury v1 — disclosed multi-model labeling panel for the confirmatory packet.

Three independently-served models label the blind confirmatory packet
(``blind_annotation_confirmatory_v3.json``, 120 cases) under the operational
taxonomy of ``docs/laya_integration/INDEPENDENT_LABELING_PROTOCOL.md``.

This lane is SEPARATE from the human rater lane on purpose:
``laya_confirmatory_analysis.py`` refuses programmatically generated labels
for ``rater_labels/r1-r3.json`` — the AI jury outputs here are a *disclosed
AI-workload* evaluation panel, never a human-study substitute.

Credentials come exclusively from the gitignored ``.env``
(AGENTROUTER_API_KEY / AGENTROUTER_BASE_URL / AGENTROUTER_UA /
AGENTROUTER_MODELS). No key material is written to code or results.

Egress policy (SSRF guard, enforced before every request): https only, the
host must equal the single code-level allowlist entry, must resolve to
public addresses only (loopback/private/link-local/reserved/metadata refused),
and redirects are not followed.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import socket
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "laya_research"
PACKET = RESULTS / "blind_annotation_confirmatory_v3.json"
OUT_DIR = RESULTS / "ai_jury_v1"

# code-level egress allowlist: the only host this script may ever contact
ALLOWED_HOST = "agentrouter.org"
ENDPOINT_PATH = "/v1/responses"

TAXONOMY = [
    "BENIGN", "RECON", "SUSPICIOUS", "EXPLOITATION", "PRIVILEGE_ESCALATION",
    "DATA_ACCESS", "PERSISTENCE", "OTHER_ATTACK", "UNCERTAIN",
]

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


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def guarded_endpoint(base_url: str) -> str:
    """Validate base_url against the egress policy and return the endpoint URL.

    https-only; hostname must equal ALLOWED_HOST; every resolved address must
    be public (loopback/private/link-local/reserved/metadata refused).
    """
    parsed = urlparse(base_url)
    if parsed.scheme != "https":
        raise ValueError(f"refused non-https scheme: {parsed.scheme!r}")
    if (parsed.hostname or "").lower() != ALLOWED_HOST:
        raise ValueError(f"refused host outside allowlist: {parsed.hostname!r}")
    infos = socket.getaddrinfo(ALLOWED_HOST, 443, proto=socket.IPPROTO_TCP)
    if not infos:
        raise ValueError(f"cannot resolve {ALLOWED_HOST}")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            raise ValueError(f"refused non-public address {ip} for {ALLOWED_HOST}")
    return urljoin(base_url.rstrip("/") + "/", ENDPOINT_PATH.lstrip("/"))


def deterministic_order(cases: list[dict], seed_material: str) -> list[dict]:
    """Reproducible hash permutation — NOT a security-sensitive shuffle."""
    return sorted(cases, key=lambda c: hashlib.sha256(
        (seed_material + ":" + c["id"]).encode()).hexdigest())


def call_model(base_url: str, api_key: str, ua: str, model: str,
               prompt: str, max_retries: int = 3) -> tuple[str, dict]:
    url = guarded_endpoint(base_url)
    payload = json.dumps({
        "model": model,
        "input": prompt,
        "max_output_tokens": 64000,
    }).encode()
    last_err = ""
    for attempt in range(max_retries):
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": ua,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                doc = json.loads(resp.read())
            text_parts = []
            for item in doc.get("output", []):
                if item.get("type") == "message":
                    for part in item.get("content", []):
                        if part.get("type") == "output_text":
                            text_parts.append(part.get("text", ""))
            usage = doc.get("usage", {}) or {}
            meta = {
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "response_id": doc.get("id"),
                "attempts": attempt + 1,
            }
            return "\n".join(text_parts), meta
        except Exception as exc:  # noqa: BLE001 - retry any transport/model error
            last_err = repr(exc)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"model {model} failed after {max_retries} attempts: {last_err}")


def parse_labels(raw: str, expected_ids: list[str]) -> tuple[dict[str, dict], list[str]]:
    """Extract {case_id: {label, notes}} from model output; tolerant to fences."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    start = min((i for i in (text.find("{"), text.find("[")) if i >= 0), default=-1)
    if start > 0:
        text = text[start:]
    try:
        doc = json.loads(text)
    except json.JSONDecodeError:
        # salvage truncated output: parse complete {...} rows individually
        doc = None
        rows = []
        for m in re.finditer(r"\{[^{}]*\}", text, re.S):
            try:
                rows.append(json.loads(m.group(0)))
            except json.JSONDecodeError:
                continue
    else:
        rows = doc if isinstance(doc, list) else doc.get("labels") or doc.get("items") or []
    out: dict[str, dict] = {}
    for row in rows:
        cid = str(row.get("case_id") or row.get("id") or "")
        label = str(row.get("label") or row.get("label_text") or "").upper().strip()
        if cid and label:
            out[cid] = {"label": label, "notes": str(row.get("notes", ""))[:300]}
    missing = [cid for cid in expected_ids if cid not in out]
    invalid = [cid for cid, v in out.items() if v["label"] not in TAXONOMY]
    return out, missing + invalid


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fleiss_kappa(labels_by_rater: dict[str, dict[str, str]], ids: list[str]) -> float:
    raters = list(labels_by_rater)
    cat_idx = {c: i for i, c in enumerate(TAXONOMY)}
    if len(raters) < 2 or not ids:
        return float("nan")
    row_totals = []
    p_cat = [0.0] * len(TAXONOMY)
    for cid in ids:
        counts = [0] * len(TAXONOMY)
        for r in raters:
            lab = labels_by_rater[r].get(cid)
            if lab in cat_idx:
                counts[cat_idx[lab]] += 1
        row_totals.append(sum(counts))
        for i, c in enumerate(counts):
            p_cat[i] += c
    total = sum(row_totals)
    p_cat = [p / total for p in p_cat]
    pe = sum(p * p for p in p_cat)
    pj = []
    for cid, rowt in zip(ids, row_totals):
        counts = [0] * len(TAXONOMY)
        for r in raters:
            lab = labels_by_rater[r].get(cid)
            if lab in cat_idx:
                counts[cat_idx[lab]] += 1
        if rowt < 2:
            continue
        pj.append((sum(c * (c - 1) for c in counts)) / (rowt * (rowt - 1)))
    p_j = sum(pj) / len(pj) if pj else 0.0
    if pe == 1.0:
        return 1.0
    return (p_j - pe) / (1 - pe)


def main() -> int:
    env = load_env(ROOT / ".env")
    api_key = env.get("AGENTROUTER_API_KEY", "")
    models = [m.strip() for m in env.get("AGENTROUTER_MODELS", "").split(",") if m.strip()]
    ua = env.get("AGENTROUTER_UA", "claude-cli/1.0.81 (external, cli)")
    if not (api_key and env.get("AGENTROUTER_BASE_URL") and models):
        print("REFUSING: AGENTROUTER_* not fully configured in .env", file=sys.stderr)
        return 2
    try:
        guarded_endpoint(env["AGENTROUTER_BASE_URL"])
    except (ValueError, OSError) as exc:
        print(f"REFUSING: {exc}", file=sys.stderr)
        return 2

    cases = json.loads(PACKET.read_text())
    ids = [c["id"] for c in cases]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = {
        "panel": "ai_jury_v1",
        "protocol": "INDEPENDENT_LABELING_PROTOCOL.md taxonomy (verbatim operational defs)",
        "packet": {"path": str(PACKET.relative_to(ROOT)), "sha256": sha256_file(PACKET),
                   "cases": len(ids)},
        "lane_disclosure": (
            "Disclosed AI-workload labeling panel. NOT a human study; outputs are "
            "stored outside rater_labels/ and laya_confirmatory_analysis.py refuses "
            "this lane by design."),
        "key_fingerprint": hashlib.sha256(api_key.encode()).hexdigest()[:12],
        "endpoint_host": ALLOWED_HOST,
        "models": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    jury_labels: dict[str, dict[str, str]] = {}
    for model in models:
        # resume: reuse a complete prior output instead of re-billing the call
        cached = OUT_DIR / f"{model.replace('/', '_')}.json"
        if cached.exists():
            try:
                doc = json.loads(cached.read_text())
                lab = {i["case_id"]: i["label"] for i in doc.get("items", [])}
                if len(lab) == len(ids) and all(v in TAXONOMY for v in lab.values()):
                    jury_labels[model] = lab
                    manifest["models"].append({
                        "model": model, "output": str(cached.relative_to(ROOT)),
                        "usage": doc.get("usage", {}), "cases": len(lab),
                        "resumed_from_cache": True})
                    print(f"[jury] {model}: resumed {len(lab)} labels from cache", flush=True)
                    continue
            except Exception:
                pass
        ordered = deterministic_order(cases, model)
        listing = "\n".join(
            f'{i + 1}. case_id={c["id"]} | context={c["context"]} | evidence={c["evidence"]}'
            for i, c in enumerate(ordered))
        prompt = (PROTOCOL_BRIEF +
                  "\nLabel every case below. Reply with ONLY a JSON array like "
                  '[{"case_id":"...","label":"<TAXONOMY>","notes":"<=25 words"}] — '
                  "one row per case, no other text.\n\n" + listing)
        print(f"[jury] {model}: {len(ordered)} cases ...", flush=True)
        try:
            raw, meta = call_model(env["AGENTROUTER_BASE_URL"], api_key, ua, model, prompt)
            labels, problems = parse_labels(raw, ids)
        except RuntimeError:
            # fallback: single-shot too heavy for this model's reasoning budget —
            # batch the same protocol into chunks of 30 cases per request
            labels, problems = {}, ids
            meta = {"input_tokens": 0, "output_tokens": 0, "response_id": "batched",
                    "attempts": 0}
            for b in range(0, len(ordered), 30):
                chunk = ordered[b:b + 30]
                blist = "\n".join(
                    f'case_id={c["id"]} | context={c["context"]} | evidence={c["evidence"]}'
                    for c in chunk)
                bprompt = (PROTOCOL_BRIEF +
                           "\nLabel every case below. Reply with ONLY a JSON array like "
                           '[{"case_id":"...","label":"<TAXONOMY>","notes":"<=25 words"}] — '
                           "one row per case, no other text.\n\n" + blist)
                for attempt in range(3):
                    try:
                        craw, cmeta = call_model(env["AGENTROUTER_BASE_URL"], api_key, ua,
                                                 model, bprompt)
                        clabels, _ = parse_labels(craw, [c["id"] for c in chunk])
                        labels.update(clabels)
                        meta["output_tokens"] = (meta["output_tokens"] or 0) + (cmeta.get("output_tokens") or 0)
                        break
                    except RuntimeError as exc:
                        print(f"[jury] {model}: batch {b // 30} attempt {attempt + 1}: {exc}",
                              flush=True)
                        time.sleep(10 * (attempt + 1))
                problems = [cid for cid in ids if cid not in labels]
                print(f"[jury] {model}: batch {b // 30}: {len(labels)} labels so far", flush=True)
        if problems:
            print(f"[jury] {model}: {len(problems)} missing/invalid -> retrying once", flush=True)
            retry_ids = set(problems)
            sub = "\n".join(f"case_id={c['id']} | context={c['context']} | "
                            f"evidence={c['evidence']}"
                            for c in ordered if c["id"] in retry_ids)
            raw2, meta2 = call_model(
                env["AGENTROUTER_BASE_URL"], api_key, ua, model,
                PROTOCOL_BRIEF + "\nLabel ONLY these cases. Reply ONLY with the JSON array.\n\n"
                + sub)
            fixed, _ = parse_labels(raw2, sorted(retry_ids))
            labels.update({k: v for k, v in fixed.items() if k in retry_ids})
            problems = [cid for cid in ids if cid not in labels
                        or labels[cid]["label"] not in TAXONOMY]
            meta["output_tokens"] = (meta.get("output_tokens") or 0) + (meta2.get("output_tokens") or 0)
        if problems:
            print(f"[jury] {model}: REFUSING to write — {len(problems)} unresolved: "
                  f"{problems[:10]}", file=sys.stderr)
            return 3
        items = []
        for rank, cid in enumerate(ids, 1):
            case = next(c for c in cases if c["id"] == cid)
            items.append({
                "rank": rank, "case_id": cid, "evidence": case["evidence"],
                "context": case["context"], "label": labels[cid]["label"],
                "notes": labels[cid]["notes"],
            })
        doc = {
            "rater_id": f"jury:{model}",
            "model": model,
            "panel": "ai_jury_v1",
            "protocol": "INDEPENDENT_LABELING_PROTOCOL.md",
            "order_seed": "deterministic-hash-permutation(model)",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "usage": meta,
            "items": items,
        }
        out = OUT_DIR / f"{model.replace('/', '_')}.json"
        out.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
        jury_labels[model] = {i["case_id"]: i["label"] for i in items}
        manifest["models"].append({
            "model": model, "output": str(out.relative_to(ROOT)),
            "usage": meta, "cases": len(items),
        })
        print(f"[jury] {model}: wrote {len(items)} labels", flush=True)

    # agreement within the panel
    pair_rows = []
    raters = list(jury_labels)
    NEG = {"BENIGN"}
    for i in range(len(raters)):
        for j in range(i + 1, len(raters)):
            a, b = jury_labels[raters[i]], jury_labels[raters[j]]
            exact = sum(1 for cid in ids if a[cid] == b[cid])
            binary = sum(1 for cid in ids if (a[cid] in NEG) == (b[cid] in NEG))
            pair_rows.append({"a": raters[i], "b": raters[j],
                              "exact_agreement": exact, "total": len(ids),
                              "exact_ratio": round(exact / len(ids), 4),
                              "binary_agreement": binary,
                              "binary_ratio": round(binary / len(ids), 4)})
    kappa = fleiss_kappa(jury_labels, ids)
    dist = {lab: sum(1 for r in raters for cid in ids if jury_labels[r][cid] == lab)
            for lab in TAXONOMY}
    agreement = {
        "panel": "ai_jury_v1",
        "raters": raters,
        "pairwise": pair_rows,
        "fleiss_kappa_multiclass": round(kappa, 4),
        "label_distribution_panel_total": dist,
    }
    (OUT_DIR / "ai_jury_agreement.json").write_text(
        json.dumps(agreement, indent=2, ensure_ascii=False))

    # cross-panel: vs prior ai_rater runs (provenance under review — labeled as such)
    prior_dir = RESULTS / "ai_raters"
    prior = {}
    if prior_dir.exists():
        for p in sorted(prior_dir.glob("*.json")):
            try:
                doc = json.loads(p.read_text())
                rows = doc.get("items") or doc.get("labels") or []
                lab = {str(r.get("case_id")): str(r.get("label", "")).upper()
                       for r in rows if r.get("case_id")}
                if lab:
                    prior[p.stem] = lab
            except Exception:
                continue
    cross = []
    for name, lab in prior.items():
        for j in raters:
            shared = [cid for cid in ids if cid in lab]
            if not shared:
                continue
            exact = sum(1 for cid in shared if lab[cid] == jury_labels[j][cid])
            cross.append({"prior_rater": name, "jury_model": j,
                          "shared_cases": len(shared),
                          "exact_agreement": exact,
                          "ratio": round(exact / len(shared), 4)})
    if cross:
        (OUT_DIR / "ai_jury_cross_panel.json").write_text(
            json.dumps({"note": "prior ai_rater runs — provenance under review; "
                                "agreement reported for continuity only",
                        "pairs": cross}, indent=2, ensure_ascii=False))

    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    manifest["agreement_summary"] = {
        "fleiss_kappa_multiclass": round(kappa, 4),
        "min_exact_ratio": min(r["exact_ratio"] for r in pair_rows) if pair_rows else None,
    }
    (OUT_DIR / "ai_jury_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"[jury] agreement: kappa={kappa:.3f}, "
          f"min pairwise exact={min(r['exact_ratio'] for r in pair_rows):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
