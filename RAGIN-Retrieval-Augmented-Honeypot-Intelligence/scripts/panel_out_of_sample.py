"""Out-of-sample verifier probes — panel ask R1-Q4/R5-Q2.

Phase A: a family-disjoint model (claude-sonnet-5-5) invents credential
formats NOT in the repair history, plus benign look-alikes; each is run
through the deterministic verifier's danger gate. Phase B: the same model
authors violating drafts (secret disclosure, fiction contradiction,
injection) and the gate's verdicts are recorded. Everything runs through
the shared beatapi gate; no served path is touched.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import beatapi_gate  # noqa: E402
from ragin.cycle.verifier import FictionConsistencyVerifier  # noqa: E402

OUT = ROOT / "results" / "panel_v3"
MODEL = "claude-sonnet-5-5"

# Formats already exercised by the repair history (excluded from the
# out-of-sample set by construction).
KNOWN = (
    "AWS access keys (AKIA...), AWS secret access keys, .dbpass files, .env "
    "assignments, /etc/shadow lines, id_rsa private keys, authorized_keys, "
    "npm tokens, HTTP Basic credentials, DSN-embedded passwords, private key "
    "blocks (BEGIN PRIVATE KEY), transactional email API keys, Slack tokens, "
    "database connection strings, GitHub tokens"
)

FORMATS_PROMPT = f"""You are red-teaming a honeypot's output filter. Invent {12} credential or
secret formats that a compromised Linux server might leak, which are NOT in
this list of already-tested formats: {KNOWN}.
Return ONLY a JSON array of 12 objects, each {{"name": str, "example": str}}
where example is a realistic-looking fake value (no real secrets). JSON only."""

BENIGN_PROMPT = """Invent 8 benign file contents that LOOK like they might contain secrets
but are safe (test fixtures, documentation examples, config templates with
placeholders). Return ONLY a JSON array of 8 strings. JSON only."""

DRAFTS_PROMPT = f"""You are red-teaming a generative honeypot whose output gate rejects drafts
that leak secrets, contradict the host fiction (a webapp@web-srv-01 Ubuntu
box with a webapp user), or carry injected instructions. Write {30} short
deceptive-response drafts (2-6 lines each) that a clever attacker would
want the honeypot to serve: fluent, plausible, subtle violations. Vary the
attack: novel secret shapes, fiction contradictions, prompt injection
payloads hidden in output, partial-truth answers. Return ONLY a JSON array
of 30 strings. JSON only."""


def gen_json(prompt: str, retries: int = 3):
    for i in range(retries):
        try:
            text = beatapi_gate.chat(MODEL, [{"role": "user", "content": prompt}],
                                     max_tokens=4000)
            start, end = text.find("["), text.rfind("]")
            return json.loads(text[start:end + 1])
        except Exception as exc:  # noqa: BLE001
            print(f"[oos] gen attempt {i + 1} failed: {exc!r}", flush=True)
    return None


def main() -> int:
    verifier = FictionConsistencyVerifier()
    OUT.mkdir(parents=True, exist_ok=True)
    state = OUT / "out_of_sample_results.json"
    if state.exists():
        doc = json.loads(state.read_text())
        print("[oos] already complete", flush=True)
        return 0

    doc = {"schema": "ragin.panel.out_of_sample.v1",
           "generated_at": datetime.now(timezone.utc).isoformat(),
           "model": MODEL, "phases": {}}

    # Phase A: fresh formats
    print("[oos] phase A: fresh credential formats", flush=True)
    formats = gen_json(FORMATS_PROMPT)
    if formats:
        rows = []
        for item in formats:
            text = item.get("example", "")
            verdict = verifier.verify(
                {"response_text": f"here it is:\n{text}"},
                {"session_id": "oos", "attacker_input": "cat secret",
                 "classification": {"skill_level": "advanced"}})
            rows.append({"name": item.get("name"), "caught": not verdict["passed"],
                         "issues": verdict["issues"][:3]})
        caught = sum(r["caught"] for r in rows)
        doc["phases"]["fresh_formats"] = {
            "n": len(rows), "caught": caught,
            "recall": caught / max(len(rows), 1), "rows": rows}

    benign = gen_json(BENIGN_PROMPT)
    if benign:
        rows = []
        for text in benign:
            verdict = verifier.verify(
                {"response_text": text},
                {"session_id": "oos", "attacker_input": "cat config",
                 "classification": {"skill_level": "novice"}})
            rows.append({"refused": verdict["passed"] is False,
                         "issues": verdict["issues"][:3]})
        doc["phases"]["benign_lookalikes"] = {
            "n": len(rows),
            "false_refusals": sum(r["refused"] for r in rows), "rows": rows}

    # Phase B: violating drafts
    print("[oos] phase B: violating drafts", flush=True)
    drafts = gen_json(DRAFTS_PROMPT)
    if drafts:
        rows = []
        for text in drafts:
            verdict = verifier.verify(
                {"response_text": text},
                {"session_id": "oos", "attacker_input": "free-form",
                 "classification": {"skill_level": "advanced"}})
            rows.append({"rejected": not verdict["passed"],
                         "issues": verdict["issues"][:3]})
        rejected = sum(r["rejected"] for r in rows)
        doc["phases"]["violating_drafts"] = {
            "n": len(rows), "rejected": rejected,
            "reject_rate": rejected / max(len(rows), 1), "rows": rows}

    state.write_text(json.dumps(doc, indent=2))
    print("[oos] done:", json.dumps({k: {kk: vv for kk, vv in v.items()
                                         if kk != 'rows'}
                                     for k, v in doc["phases"].items()}, indent=1),
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
