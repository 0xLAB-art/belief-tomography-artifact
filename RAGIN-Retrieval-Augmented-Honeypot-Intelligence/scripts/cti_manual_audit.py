"""218-row CTI manual audit (SP2027 plan advisory #5).

The paper previously admitted no manual audit of CTI outputs. This tool
implements the audit end-to-end:

  collect   run the 218-query VOR workload (123 technique + 35 actor + 60
            deception) through the ragin_full pipeline, persisting the FULL
            served text and Don's FULL cti_analysis per row (earlier
            checkpoints stored only scores, which cannot be manually audited)
  packet    build BLINDED annotation packets (opaque row ids, no gold answers,
            no pipeline scores) + a separate blinding key mapping row ids to
            workload rows
  annotate  two INDEPENDENT annotators (opencode free-tier models with fixed
            identities — no fallback chain, model identity is part of the
            annotation protocol) label every packet: requested technique/actor
            read from the query alone, what the analysis identifies, whether
            the served text addresses the query, realism for deception rows
  score     join annotations to gold via the blinding key; report per-suite
            precision/recall/F1 (strict + technique-family), inter-annotator
            Cohen's kappa on every judged column, adjudication of disagreement
            rows by a third annotator, and machine-vs-human agreement of the
            automated channel scores against the manual verdicts
  export-human
            de-identified markdown packet for the independent human raters
            (decision Q4) with instructions header

Mitre ATT&CK is PINNED to the vendored STIX bundle (data/mitre_stix/
enterprise-attack.json): the artifact records the collection version,
modified timestamp, technique-id set and intrusion-set alias table used for
every comparison.

Usage::

    python scripts/cti_manual_audit.py collect --budget-s 360
    python scripts/cti_manual_audit.py packet
    python scripts/cti_manual_audit.py annotate --annotator A --budget-s 360
    python scripts/cti_manual_audit.py annotate --annotator B --budget-s 360
    python scripts/cti_manual_audit.py score
    python scripts/cti_manual_audit.py adjudicate --budget-s 360   # C on disagreements
    python scripts/cti_manual_audit.py score                       # consensus rescore
    python scripts/cti_manual_audit.py export-human --n 60
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RESULTS = ROOT / "results"
CORPUS_OUT = RESULTS / "cti_manual_audit_corpus.json"
CORPUS_CKPT = RESULTS / "cti_manual_audit_corpus_checkpoint.json"
PACKETS_OUT = RESULTS / "cti_audit_packets.json"
PACKETS_MD = RESULTS / "cti_audit_packets.md"
BLINDING_KEY = RESULTS / "cti_audit_blinding_key.json"
def _ann_path(slot: str) -> Path:
    return RESULTS / f"cti_audit_annotations_{slot}.json"
AUDIT_OUT = RESULTS / "cti_manual_audit.json"
HUMAN_DIR = RESULTS / "cti_audit_human_packet"

STIX_BUNDLE = ROOT / "data" / "mitre_stix" / "enterprise-attack.json"
PACKET_SEED = 2027  # deterministic packet shuffling; recorded in the artifact

# Annotator identities — FIXED per slot (no cross-model fallback: mixing models
# inside one annotator slot would contaminate the independence protocol).
ANNOTATORS = {
    "A": "opencode/nemotron-3-ultra-free",
    "B": "opencode/mimo-v2.6-flash-free",
    "C": "opencode/ling-3.0-flash-fin-free",  # adjudicator only
}
ANNOTATOR_CALL_TIMEOUT_S = 120
ANNOTATOR_RETRIES = 2

TECH_SUITES = {"cti_technique", "cti_actor"}
VERDICTS_ID = ("correct", "partial", "incorrect", "not_attempted")
VERDICTS_TOPIC = ("yes", "partial", "no")
VERDICTS_REALISM = ("realistic", "partial", "unrealistic")

SENTINEL_RE = re.compile(r"<<<AUDIT\s*(\[.*?\])\s*AUDIT>>>", re.DOTALL)


# ─────────────────────────── ATT&CK pin ────────────────────────────

def load_attack_pin() -> dict[str, Any]:
    """Pin the vendored Enterprise ATT&CK STIX bundle (version + id sets)."""
    raw = STIX_BUNDLE.read_bytes()
    bundle = json.loads(raw)
    coll = next(o for o in bundle["objects"] if o.get("type") == "x-mitre-collection")
    techniques: dict[str, str] = {}  # id -> name (live, non-deprecated)
    aliases: dict[str, set[str]] = {}  # canonical intrusion-set name -> alias set
    for o in bundle["objects"]:
        if o.get("type") == "attack-pattern" and not o.get("revoked") and not o.get("x_mitre_deprecated"):
            for ref in o.get("external_references", []):
                tid = ref.get("external_id", "")
                if re.fullmatch(r"T\d{4}(?:\.\d{3})?", tid):
                    techniques[tid] = o.get("name", "")
        elif o.get("type") == "intrusion-set" and not o.get("revoked"):
            names = {o.get("name", "").lower()}
            names |= {a.lower() for a in o.get("aliases", [])}
            names |= {a.lower() for a in o.get("x_mitre_aliases", [])}
            names.discard("")
            if names:
                canon = o.get("name", "").lower()
                aliases[canon] = names
    return {
        "bundle_path": str(STIX_BUNDLE.relative_to(ROOT)),
        "collection": coll.get("name"),
        "attack_version": f"ATT&CK {coll.get('name')} v{coll.get('x_mitre_version')}",
        "x_mitre_version": coll.get("x_mitre_version"),
        "modified": coll.get("modified"),
        "bundle_sha256": hashlib.sha256(raw).hexdigest(),
        "live_technique_count": len(techniques),
        "technique_ids": sorted(techniques),
        "intrusion_sets": {k: sorted(v) for k, v in sorted(aliases.items())},
        "live_intrusion_set_count": len(aliases),
    }


def _norm_tid(tid: str) -> str:
    return (tid or "").strip().upper()


def _parent_tid(tid: str) -> str:
    t = _norm_tid(tid)
    return t.split(".")[0] if "." in t else t


def _alias_key(name: str, alias_map: dict[str, list[str]]) -> str | None:
    """Canonicalize a threat-actor name via the pinned STIX alias table."""
    n = (name or "").strip().lower()
    if not n:
        return None
    for canon, al in alias_map.items():
        if n == canon or n in al:
            return canon
    return None


# ─────────────────────────── corpus collection ───────────────────────────

def _attack_pin_summary(pin: dict[str, Any]) -> dict[str, Any]:
    return {k: pin[k] for k in (
        "bundle_path", "collection", "attack_version", "x_mitre_version",
        "modified", "bundle_sha256", "live_technique_count",
        "live_intrusion_set_count")}


def run_collect(budget_s: float | None, limit: int | None) -> int:
    """Run the workload through the ragin_full pipeline, persisting full text."""
    import ragin.benchmark.harness_bridge as hb
    from ragin.benchmark.core import (
        CTI_ACTOR_QUERIES,
        CTI_TECHNIQUE_QUERIES,
        PERSONA_REALISM_QUERIES,
    )
    from ragin.cycle.adapters import ChrolloAdapter, DonAdapter, HisokaAdapter
    from ragin.cycle.graph import DeceptionPipeline
    from ragin.cycle.session import Session
    from scripts.run_external_baseline import resolve_gateway

    pin = load_attack_pin()
    gateway_url, api_key = resolve_gateway()
    os_env_model = os.environ.get("RAGIN_HISOKA_MODEL")

    pipeline = DeceptionPipeline(
        classifier=ChrolloAdapter(),
        analyzer=DonAdapter(gateway_url=gateway_url, api_key=api_key),
        deceiver=HisokaAdapter(gateway_url=gateway_url, api_key=api_key),
        verifier=None,  # default FictionConsistencyVerifier (verified loop)
        approval_gateway=None,
        human_in_the_loop=False,
        max_retries=1,
    )

    workload: list[tuple[str, dict]] = []
    tech = CTI_TECHNIQUE_QUERIES[:limit] if limit else CTI_TECHNIQUE_QUERIES
    actor = CTI_ACTOR_QUERIES[:limit] if limit else CTI_ACTOR_QUERIES
    decoy = PERSONA_REALISM_QUERIES[:limit] if limit else PERSONA_REALISM_QUERIES
    workload += [("cti_technique", qa) for qa in tech]
    workload += [("cti_actor", qa) for qa in actor]
    workload += [("deception", qa) for qa in decoy]

    saved: dict[str, Any] = {"rows": []}
    if CORPUS_CKPT.exists():
        try:
            saved = json.loads(CORPUS_CKPT.read_text())
        except json.JSONDecodeError:
            saved = {"rows": []}
    prior: dict[str, dict] = {r["row_id"]: r for r in saved.get("rows", [])}

    rows: list[dict] = list(prior.values())
    t0 = time.monotonic()
    stopped_early = False
    for idx, (suite, qa) in enumerate(workload, start=1):
        row_id = f"R{idx:04d}"
        if row_id in prior:
            continue
        if budget_s is not None and (time.monotonic() - t0) > budget_s:
            stopped_early = True
            break
        query = qa["query"]
        session = Session.create(source_ip=f"ctiaudit-{idx}")
        row: dict[str, Any] = {
            "row_id": row_id,
            "suite": suite,
            "query": query,
            "gold": {k: qa.get(k) for k in
                     ("expected_technique", "expected_tactic", "expected_actor",
                      "sector", "category", "expected_traits") if qa.get(k) is not None},
        }
        try:
            pr = pipeline.process(session, query)
            outcome = hb.outcome_from_pipeline_result(pr, query)
            row.update({
                "error": None,
                "response_text": outcome.response_text,
                "cti_analysis": _jsonable_cti(outcome.cti_analysis),
                "ttps_extracted": outcome.ttps_extracted[:12],
                "serve_path": (outcome.deception or {}).get("serve_path", "")
                if isinstance(outcome.deception, dict) else "",
                # machine scores recorded for the audit's machine-vs-human check
                "machine_scores": {
                    "served_text": _machine_served_score(suite, outcome, qa),
                    "cti_analysis": _machine_analysis_score(suite, outcome, qa),
                },
            })
        except Exception as exc:  # noqa: BLE001 — a failed row is data, not a crash
            row.update({"error": f"{type(exc).__name__}: {exc}"[:200],
                        "response_text": "", "cti_analysis": {},
                        "ttps_extracted": [], "serve_path": "",
                        "machine_scores": {"served_text": None, "cti_analysis": None}})
        rows.append(row)
        CORPUS_CKPT.parent.mkdir(parents=True, exist_ok=True)
        CORPUS_CKPT.write_text(json.dumps({"rows": rows}, default=str))
        tail = (row["response_text"] or row["error"] or "")[:60].replace("\n", " ")
        print(f"  {row_id} {suite:<14} {tail}", flush=True)

    complete = len(rows) >= len(workload)
    artifact = {
        "what": "218-row CTI manual audit corpus — full served text + full cti_analysis per row",
        "attack_pin": _attack_pin_summary(pin),
        "config": {
            "pipeline": "ragin_full config (Chrollo+Don+Hisoka+fiction+verifier, store off)",
            "generator_model": os_env_model or "(gateway default glm-5.3-flash-free)",
            "matches_two_channel_metrics_config": True,
        },
        "workload_rows": len(workload),
        "rows_done": len(rows),
        "complete": complete,
        "stopped_early": stopped_early,
        "rows": rows,
    }
    out = CORPUS_OUT if limit is None else CORPUS_OUT.with_name(
        CORPUS_OUT.stem + f"_limit{limit}.json")
    out.write_text(json.dumps(artifact, indent=2, default=str))
    print("=" * 76)
    print(f"corpus rows: {len(rows)}/{len(workload)} complete={complete} -> {out.name}")
    return 0


def _jsonable_cti(cti: dict[str, Any]) -> dict[str, Any]:
    """Keep Don's full analysis but drop non-serializable noise."""
    if not isinstance(cti, dict):
        return {}
    keep: dict[str, Any] = {}
    for k, v in cti.items():
        try:
            json.dumps(v)
        except (TypeError, ValueError):
            keep[k] = str(v)[:400]
        else:
            keep[k] = v
    return keep


def _machine_served_score(suite: str, outcome: Any, qa: dict[str, Any]) -> float | None:
    """The automated channel score for the row (as the machines scored it).

    Echo-guarded (2026-09-28): the served-text scorers receive the query so
    template-fallback echoes score 0 — see ragin.benchmark.core._is_query_echo.
    """
    import ragin.benchmark.harness_bridge as hb

    q = qa.get("query", "")
    if suite == "cti_technique":
        return round(hb._score_technique_match(
            outcome.response_text, qa.get("expected_technique", ""), query=q), 4)
    if suite == "cti_actor":
        return round(hb._score_actor_match(
            outcome.response_text, qa.get("expected_actor", ""), qa.get("sector", ""),
            query=q), 4)
    return round(hb._score_persona_realism(
        outcome.response_text, qa.get("expected_traits", []), qa.get("query", "")), 4)


def _machine_analysis_score(suite: str, outcome: Any, qa: dict[str, Any]) -> float | None:
    """The automated CTI-analysis channel score (None for deception rows)."""
    if suite == "deception":
        return None
    if suite == "cti_technique":
        analysis_text = _cti_text(outcome.cti_analysis)
        analysis = _score_tech_like_harness(analysis_text, qa.get("expected_technique", ""))
        expected = qa.get("expected_technique", "").upper()
        extracted = {t.upper() for t in outcome.ttps_extracted}
        if expected in extracted:
            return 1.0
        if _parent_tid(expected) in {_parent_tid(t) for t in extracted}:
            return 0.85
        return analysis
    analysis_text = _cti_text(outcome.cti_analysis)
    base = _score_actor_like_harness(
        analysis_text, qa.get("expected_actor", ""), qa.get("sector", ""))
    expected = qa.get("expected_actor", "").lower()
    named = {
        a.get("name", "").lower()
        for a in (outcome.cti_analysis or {}).get("candidate_actors", [])
        if isinstance(a, dict)
    }
    if any(expected == n or expected in n or n in expected for n in named):
        return 0.85
    return base


def _cti_text(cti: dict[str, Any]) -> str:
    import ragin.benchmark.harness_bridge as hb

    return hb._cti_analysis_text(cti)


def _score_tech_like_harness(response: str, expected: str) -> float:
    import ragin.benchmark.harness_bridge as hb

    return hb._score_technique_match(response or "", expected)


def _score_actor_like_harness(response: str, expected: str, sector: str) -> float:
    import ragin.benchmark.harness_bridge as hb

    return hb._score_actor_match(response or "", expected, sector)


def run_rescore_machine() -> int:
    """Recompute the audit corpus's machine scores under the echo-guarded
    scorers, update the blinding key, and record the pre/post correction.

    Fully offline (no gateway calls): the corpus stores the full served text,
    and the analysis channel is unchanged by the guard (it is never fed the
    attacker-visible text). The pre-guard snapshot is preserved inside the
    audit artifact as ``echo_guard_correction``; re-run ``score`` afterwards
    so the canonical machine-vs-human and echo-diagnosis fields reflect the
    corrected scores.
    """
    import json as _json
    from types import SimpleNamespace

    if not CORPUS_OUT.exists():
        print("no corpus to rescore — run collect first", file=sys.stderr)
        return 1
    corpus = _json.loads(CORPUS_OUT.read_text())
    pre_audit = _json.loads(AUDIT_OUT.read_text()) if AUDIT_OUT.exists() else {}

    # Workload gold per row (query + expected fields) from the source suites.
    from ragin.benchmark.core import (
        CTI_ACTOR_QUERIES,
        CTI_TECHNIQUE_QUERIES,
        PERSONA_REALISM_QUERIES,
    )
    gold_by_name: dict[str, dict] = {}
    for suite, bank in (("cti_technique", CTI_TECHNIQUE_QUERIES),
                        ("cti_actor", CTI_ACTOR_QUERIES),
                        ("deception", PERSONA_REALISM_QUERIES)):
        for qa in bank:
            gold_by_name[f"{suite}_{qa['query'][:40].replace(' ', '_')}"] = {"suite": suite, **qa}

    rows = corpus["rows"]
    pre_avg: dict[str, list[float]] = {"cti_technique": [], "cti_actor": [], "deception": []}
    post_avg: dict[str, list[float]] = {"cti_technique": [], "cti_actor": [], "deception": []}
    n_changed = 0
    for r in rows:
        if r.get("error"):
            continue
        name = f"{r['suite']}_{r['query'][:40].replace(' ', '_')}"
        qa = gold_by_name.get(name)
        if qa is None:
            continue
        outcome = SimpleNamespace(
            response_text=r.get("response_text") or "",
            cti_analysis=r.get("cti_analysis") or {},
            ttps_extracted=r.get("ttps_extracted") or [],
        )
        # Idempotent re-runs: after the first pass machine_scores holds the
        # CORRECTED values, so the pre-guard snapshot must come from the
        # preserved initial copy (fall back to machine_scores on first run).
        pre_ms = r.get("machine_scores_initial") or r.get("machine_scores") or {}
        if pre_ms.get("served_text") is not None:
            pre_avg[r["suite"]].append(pre_ms["served_text"])
        post = {
            "served_text": _machine_served_score(r["suite"], outcome, qa),
            "cti_analysis": _machine_analysis_score(r["suite"], outcome, qa),
        }
        if pre_ms.get("served_text") != post["served_text"]:
            n_changed += 1
        post_avg[r["suite"]].append(post["served_text"])
        if "machine_scores_initial" not in r:
            r["machine_scores_initial"] = pre_ms
        r["machine_scores"] = post

    corpus["echo_guard_applied"] = True
    CORPUS_OUT.write_text(_json.dumps(corpus, indent=2, default=str))

    # Blinding key must carry the corrected scores — run_score reads them there.
    if BLINDING_KEY.exists():
        kd = _json.loads(BLINDING_KEY.read_text())
        by_name = {
            f"{r['suite']}_{r['query'][:40].replace(' ', '_')}": r for r in rows}
        for _rid, k in kd["row_map"].items():
            name = f"{k['suite']}_{k['query'][:40].replace(' ', '_')}"
            match = by_name.get(name)
            if match is not None:
                k["machine_scores"] = match["machine_scores"]
                k["machine_scores_initial"] = match.get("machine_scores_initial", {})
        BLINDING_KEY.write_text(_json.dumps(kd, indent=2))

    correction = {
        "what": (
            "echo-guard correction (2026-09-28): served-text machine scores were "
            "crediting the technique ID / actor name inside echoed fallback queries; "
            "all scores recomputed with the guarded scorers (analysis channel unchanged)"),
        "rows_changed": n_changed,
        "pre_correction": {
            "machine_vs_human": pre_audit.get("machine_vs_human"),
            "echo_diagnosis": pre_audit.get("echo_diagnosis"),
            "served_avg": {s: (round(sum(v) / len(v), 4) if v else None)
                           for s, v in pre_avg.items()},
        },
        "post_correction_served_avg": {
            s: (round(sum(v) / len(v), 4) if v else None) for s, v in post_avg.items()},
        "note": (
            "re-run `score` to refresh machine_vs_human and echo_diagnosis from the "
            "corrected blinding key; the per-row corrected scores live in the corpus "
            "artifact (machine_scores_initial preserves the pre-guard values)"),
    }
    if AUDIT_OUT.exists():
        audit = _json.loads(AUDIT_OUT.read_text())
        audit["echo_guard_correction"] = correction
        AUDIT_OUT.write_text(_json.dumps(audit, indent=2))
    else:
        AUDIT_OUT.write_text(_json.dumps({"echo_guard_correction": correction}, indent=2))

    print("ECHO-GUARD RESCORE (offline)")
    print(f"  rows changed: {n_changed}")
    for s in ("cti_technique", "cti_actor", "deception"):
        pre = correction["pre_correction"]["served_avg"][s]
        post = correction["post_correction_served_avg"][s]
        print(f"  {s:<14} served avg {pre} -> {post}")
    return 0


# ─────────────────────────── packet builder ───────────────────────────

def _analysis_for_packet(cti: dict[str, Any]) -> dict[str, Any]:
    """Compact, packet-safe view of Don's analysis (no gold leakage — Don's
    analysis is a genuine system OUTPUT, which is exactly what is audited)."""
    if not isinstance(cti, dict):
        return {}
    return {
        "summary": cti.get("threat_summary") or cti.get("summary") or "",
        "candidate_actors": [
            a.get("name", "") if isinstance(a, dict) else str(a)
            for a in cti.get("candidate_actors", [])
        ][:6],
        "ttps_seen": cti.get("ttps_seen", [])[:8],
        "extracted_techniques": cti.get("extracted_techniques", [])[:8],
        "tactics": [t.get("id", "") if isinstance(t, dict) else str(t)
                    for t in cti.get("tactics", [])][:6],
    }


def run_packet(limit: int | None) -> int:
    corpus_p = CORPUS_OUT if limit is None else CORPUS_OUT.with_name(
        CORPUS_OUT.stem + f"_limit{limit}.json")
    corpus = json.loads(corpus_p.read_text())
    rows = corpus["rows"]
    pin = load_attack_pin()

    packets = []
    key: dict[str, dict] = {}
    for r in rows:
        if r.get("error"):
            continue  # failed rows are excluded from annotation (counted in score)
        packets.append({
            "row_id": r["row_id"],
            "suite": r["suite"],
            "query": r["query"],
            "served_text": (r.get("response_text") or "")[:1600],
            "analysis": _analysis_for_packet(r.get("cti_analysis") or {}),
        })
        key[r["row_id"]] = {"suite": r["suite"], "query": r["query"],
                            "gold": r.get("gold", {}),
                            "machine_scores": r.get("machine_scores", {}),
                            "serve_path": r.get("serve_path", "")}
    rng = random.Random(PACKET_SEED)
    rng.shuffle(packets)

    PACKETS_OUT.write_text(json.dumps({
        "what": "BLINDED annotation packets — no gold answers, no pipeline scores",
        "packet_seed": PACKET_SEED,
        "attack_pin": _attack_pin_summary(pin),
        "n_packets": len(packets),
        "packets": packets,
    }, indent=2))
    BLINDING_KEY.write_text(json.dumps({
        "what": "blinding key — join annotations to gold ONLY at scoring time",
        "row_map": key,
    }, indent=2))
    _write_packets_md(packets, pin)
    print(f"packets: {len(packets)} (blinded, seed={PACKET_SEED}) -> {PACKETS_OUT.name}")
    print(f"blinding key: {len(key)} rows -> {BLINDING_KEY.name}")
    return 0


def _write_packets_md(packets: list[dict], pin: dict[str, Any]) -> None:
    lines = [
        "# CTI Manual Audit — Annotation Packet",
        "",
        f"Reference taxonomy: {pin['attack_version']} "
        f"(bundle sha256 {pin['bundle_sha256'][:16]}…, modified {pin['modified']}).",
        "",
        "For each item below, record independently:",
        "1. **requested** — the ATT&CK technique ID (or threat actor) the QUERY is about,",
        "   judged from the query text alone; `unclear` if genuinely ambiguous.",
        "2. **identified** — the technique IDs / actor names present in the ANALYSIS record.",
        "3. **identification** — correct / partial / incorrect / not_attempted",
        "   (partial = right family but not the precise sub-technique, or the right",
        "   technique buried among unrelated extras).",
        "4. **served_on_topic** — yes / partial / no: does the SERVED TEXT by itself",
        "   address the query (a machine transcript, refusal, or explanation all count;",
        "   judge topical relevance, not style).",
        "5. For deception items: **realism** — realistic / partial / unrealistic, and",
        "   whether the text reads like authentic machine output.",
        "",
        "---",
        "",
    ]
    for p in packets:
        lines.append(f"## {p['row_id']} ({p['suite']})")
        lines.append(f"**QUERY:** {p['query']}")
        lines.append("")
        lines.append("**SERVED_TEXT:**")
        lines.append("```")
        lines.append(p["served_text"] or "(empty)")
        lines.append("```")
        an = p["analysis"]
        if any(an.values()):
            lines.append("**ANALYSIS:**")
            lines.append("```json")
            lines.append(json.dumps(an, indent=1)[:1200])
            lines.append("```")
        else:
            lines.append("**ANALYSIS:** (empty)")
        lines.append("")
    PACKETS_MD.write_text("\n".join(lines))


# ─────────────────────────── annotation ───────────────────────────

def _annotator_prompt(batch: list[dict]) -> str:
    items = []
    for p in batch:
        items.append(json.dumps({
            "row_id": p["row_id"],
            "suite": p["suite"],
            "query": p["query"],
            "served_text": p["served_text"][:1500],
            "analysis": p["analysis"],
        }, default=str))
    return (
        "You are an independent CTI annotation expert auditing a cyber-deception\n"
        "research system. You will see audit items as JSON. For each item judge,\n"
        "using ONLY the item text:\n"
        "- requested: the single MITRE ATT&CK technique ID (cti_technique items) or\n"
        "  threat actor name (cti_actor items) the QUERY is about, read from the query\n"
        "  alone; use the precise sub-technique ID when the query names one;\n"
        "  'unclear' only if genuinely ambiguous.\n"
        "- identified: the technique IDs / actor names actually present in the\n"
        "  ANALYSIS record (NOT what you infer from the served text). List form.\n"
        "- identification: 'correct' if identified covers the requested technique or\n"
        "  actor; 'partial' if identified names the right family/tactic but not the\n"
        "  precise id, or the right one buried among unrelated extras; 'incorrect' if\n"
        "  identified names something different; 'not_attempted' if the analysis\n"
        "  identifies nothing relevant.\n"
        "- served_on_topic: 'yes'/'partial'/'no' — does the SERVED_TEXT by itself\n"
        "  address the query (machine transcript, refusal, or explanation all count;\n"
        "  judge topical relevance, not style).\n"
        "- realism (deception items only): 'realistic'/'partial'/'unrealistic' — does\n"
        "  the served text read like authentic output of a real (slightly misconfig-\n"
        "  ured) machine answering the question.\n"
        "- notes: one short sentence.\n\n"
        "Reply with exactly one JSON array in this shape and NOTHING else:\n"
        "<<<AUDIT\n"
        '[{"row_id":"R0001","requested":"T1190","identified":["T1190"],'
        '"identification":"correct","served_on_topic":"yes","notes":"..."},\n'
        '{"row_id":"R0002",...,"realism":"realistic"}]\n'
        "AUDIT>>>\n\n"
        "ITEMS:\n" + "\n".join(items)
    )


def _clean_json_block(text: str) -> str:
    block = text.strip()
    if block.startswith("```"):
        block = block.strip("`")
        if block.lower().startswith("json\n"):
            block = block.split("\n", 1)[1]
    return block.strip()


def _parse_annotation(text: str) -> list[dict] | None:
    """Layered parser: sentinel block → whole-text JSON → bracket slice →
    flat-object scan. Annotator models differ wildly in wrapper discipline
    (some drop the sentinel entirely — observed 2026-09-27 with mimo), so a
    bare array must still parse."""
    text = text or ""
    m = SENTINEL_RE.search(text)
    candidates = []
    if m:
        candidates.append(m.group(1))
    raw = _clean_json_block(text)
    if raw:
        candidates.append(raw)
        i, j = raw.find("["), raw.rfind("]")
        if 0 <= i < j:
            candidates.append(raw[i:j + 1])
    fixed_add = []
    for cand in candidates:
        for attempt in (cand, re.sub(r",\s*([\]}])", r"\1", cand).replace("'", '"')):
            if attempt in fixed_add:
                continue
            fixed_add.append(attempt)
            try:
                data = json.loads(attempt)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                data = [data]
            if isinstance(data, list):
                rows = [d for d in data if isinstance(d, dict) and d.get("row_id")]
                if rows:
                    return rows
    # last resort: every flat {...} object in the text (handles two concatenated
    # arrays or prose around the payload)
    objs = []
    for blob in re.findall(r"\{[^{}]*\}", text):
        try:
            d = json.loads(re.sub(r",\s*([}\]])", r"\1", blob).replace("'", '"'))
        except json.JSONDecodeError:
            continue
        if isinstance(d, dict) and d.get("row_id"):
            objs.append(d)
    return objs or None


def _opencode_call(model: str, prompt: str) -> tuple[str | None, str | None]:
    try:
        proc = subprocess.run(
            ["opencode", "run", "-m", model, "--pure", prompt],
            capture_output=True, text=True,
            timeout=ANNOTATOR_CALL_TIMEOUT_S, cwd=str(ROOT),
        )
    except subprocess.TimeoutExpired:
        return None, f"TimeoutExpired after {ANNOTATOR_CALL_TIMEOUT_S}s"
    except FileNotFoundError:
        return None, "opencode CLI not found"
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        return None, f"opencode exit {proc.returncode}: {tail[-1][:120] if tail else '(no output)'}"
    return proc.stdout, None


def _clamp_verdict(v: Any, allowed: tuple[str, ...]) -> str | None:
    s = str(v or "").strip().lower()
    return s if s in allowed else None


def _norm_annotation(item: dict, suite: str) -> dict:
    """Normalize one annotator item to the audit schema; invalid fields → None."""
    out: dict[str, Any] = {"row_id": item.get("row_id"), "notes": str(item.get("notes", ""))[:300]}
    if suite in TECH_SUITES:
        req = item.get("requested")
        req = _norm_tid(req) if req and str(req).lower() != "unclear" else "unclear"
        ident = item.get("identified", [])
        if isinstance(ident, str):
            tids = re.findall(r"T\d{4}(?:\.\d{3})?", ident)
            ident = tids if tids else [ident.strip()]
        if not isinstance(ident, list):
            ident = []
        out.update({
            "requested": req,
            "identified": [_norm_tid(t) if _norm_tid(t).startswith("T") else str(t).strip().lower()
                           for t in ident][:8],
            "identification": _clamp_verdict(item.get("identification"), VERDICTS_ID),
            "served_on_topic": _clamp_verdict(item.get("served_on_topic"), VERDICTS_TOPIC),
        })
    else:
        out.update({
            "realism": _clamp_verdict(item.get("realism"), VERDICTS_REALISM),
            "served_on_topic": _clamp_verdict(item.get("served_on_topic"), VERDICTS_TOPIC),
        })
    return out


def run_annotate(annotator: str, budget_s: float | None, batch_size: int,
                 suite_filter: str | None, only: str | None = None) -> int:
    if annotator not in ANNOTATORS:
        print(f"unknown annotator {annotator!r} (choose from {sorted(ANNOTATORS)})", file=sys.stderr)
        return 1
    model = ANNOTATORS[annotator]
    packets = json.loads(PACKETS_OUT.read_text())["packets"]
    if suite_filter:
        packets = [p for p in packets if p["suite"] == suite_filter]
    if only:
        want = {r.strip() for r in only.split(",") if r.strip()}
        packets = [p for p in packets if p["row_id"] in want]
    out_path = _ann_path(annotator)
    state: dict[str, Any] = {"annotator": annotator, "model": model, "annotations": {}}
    if out_path.exists():
        try:
            state = json.loads(out_path.read_text())
            if state.get("model") != model:
                print(f"refusing to mix models inside annotator slot {annotator}", file=sys.stderr)
                return 1
        except json.JSONDecodeError:
            state = {"annotator": annotator, "model": model, "annotations": {}}
    done: dict[str, dict] = state["annotations"]

    # Resume semantics: annotate everything not yet done, RETRY rows whose
    # previous pass errored (transient parse/refusal failures must not
    # silently become permanent holes in the audit).
    todo = [p for p in packets if p["row_id"] not in done or not done[p["row_id"]].get("ok")]
    t0 = time.monotonic()
    stopped = False
    i = 0
    while i < len(todo):
        if budget_s is not None and (time.monotonic() - t0) > budget_s:
            stopped = True
            break
        batch = todo[i:i + batch_size]
        i += len(batch)
        parsed, err = _annotate_batch(batch, model)
        if parsed is None:
            # batch failed → fall back to per-row single asks (keeps row-level resume)
            for p in batch:
                if budget_s is not None and (time.monotonic() - t0) > budget_s:
                    stopped = True
                    break
                one, err1 = _annotate_batch([p], model)
                done[p["row_id"]] = (
                    {"ok": True, **_norm_annotation(one[0], p["suite"])}
                    if one else {"ok": False, "error": (err1 or "parse failure")[:200]})
                _persist_annotations(out_path, state)
                flag = "ok" if one else "ERR " + str(done[p["row_id"]].get("error"))[:60]
                print(f"  [{annotator}] {p['row_id']} {flag}", flush=True)
                if stopped:
                    break
            if stopped:
                break
            continue
        by_id = {d["row_id"]: d for d in parsed}
        for p in batch:
            if p["row_id"] in by_id:
                done[p["row_id"]] = {"ok": True, **_norm_annotation(by_id[p["row_id"]], p["suite"])}
            else:
                done[p["row_id"]] = {"ok": False, "error": "row missing from batch reply"}
        _persist_annotations(out_path, state)
        got = sum(1 for p in batch if done[p["row_id"]].get("ok"))
        print(f"  [{annotator}] batch {batch[0]['row_id']}–{batch[-1]['row_id']}: {got}/{len(batch)} ok", flush=True)

    _persist_annotations(out_path, state)
    n_ok = sum(1 for v in done.values() if v.get("ok"))
    print(f"[{annotator}] {n_ok}/{len(packets)} annotated ({model})"
          f"{' — stopped early, re-invoke to continue' if stopped else ''}")
    return 0


def _annotate_batch(batch: list[dict], model: str) -> tuple[list[dict] | None, str | None]:
    prompt = _annotator_prompt(batch)
    err: str | None = None
    for _ in range(ANNOTATOR_RETRIES):
        out, err = _opencode_call(model, prompt)
        if out is None:
            continue
        parsed = _parse_annotation(out)
        if parsed:
            return parsed, None
        err = f"annotation parse failure; raw head: {(out or '').strip()[:140]!r}"
    return None, err


def _persist_annotations(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=1))


# ─────────────────────────── scoring ───────────────────────────

def cohens_kappa(a: list[str], b: list[str]) -> float | None:
    """Cohen's κ for two aligned label lists (None when empty)."""
    if not a or len(a) != len(b):
        return None
    n = len(a)
    po = sum(1 for x, y in zip(a, b, strict=False) if x == y) / n
    labels = set(a) | set(b)
    pe = sum((a.count(lab) / n) * (b.count(lab) / n) for lab in labels)
    if pe >= 1.0:
        return 1.0 if po >= 1.0 else 0.0
    return round((po - pe) / (1 - pe), 4)


def _prf(tp: int, fp: int, fn: int) -> dict[str, float | None]:
    p = tp / (tp + fp) if (tp + fp) else None
    r = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * p * r / (p + r)) if (p and r and (p + r)) else (0.0 if p == 0 or r == 0 else None)
    return {"precision": round(p, 4) if p is not None else None,
            "recall": round(r, 4) if r is not None else None,
            "f1": round(f1, 4) if f1 is not None else None,
            "tp": tp, "fp": fp, "fn": fn}


def _suite_verdicts(ann: dict[str, dict], suite: str, key: dict[str, dict],
                    alias_map: dict[str, list[str]]) -> dict[str, Any]:
    """Set-based P/R/F1 for one annotator on one suite, from their own reading.

    strict:  hit iff the annotator's requested id/actor is in their identified set.
    family:  hit iff requested's parent technique matches any identified parent
             (technique rows) — captures 'right family, wrong sub-technique'.
    Rows the annotator could not request ('unclear') are excluded and counted
    as workload_flags.
    """
    tp = fp = fn = fam_tp = fam_fp = fam_fn = 0
    strict_rows: list[dict] = []
    for row_id, a in sorted(ann.items()):
        if key.get(row_id, {}).get("suite") != suite or not a.get("ok"):
            continue
        req = a.get("requested", "unclear")
        ident = [i for i in a.get("identified", []) if i]
        if req == "unclear":
            continue  # counted separately as workload_flags, not a miss
        if suite == "cti_technique":
            hit = _norm_tid(req) in {_norm_tid(t) for t in ident}
            fam_hit = hit or _parent_tid(req) in {_parent_tid(t) for t in ident}
        else:  # actor: alias-normalize both sides via the pinned table
            rq = _alias_key(req, alias_map)
            hits = {_alias_key(t, alias_map) for t in ident}
            hit = rq is not None and rq in hits
            fam_hit = hit  # no family tier for actors
        # single-gold set semantics (standard IR accounting): a miss misses the
        # gold (FN, always) and, if something was identified, also predicts
        # wrongly (FP) — so recall's denominator is exactly the audited rows.
        if hit:
            tp += 1
        else:
            fn += 1
            if ident:
                fp += 1
        if fam_hit:
            fam_tp += 1
        else:
            fam_fn += 1
            if ident:
                fam_fp += 1
        strict_rows.append({"row_id": row_id, "requested": req, "identified": ident,
                            "hit_strict": hit, "hit_family": fam_hit})
    return {
        "strict": _prf(tp, fp, fn),
        "family": _prf(fam_tp, fam_fp, fam_fn),
        "rows": strict_rows,
    }


def run_score() -> int:
    pin = load_attack_pin()
    key = json.loads(BLINDING_KEY.read_text())["row_map"]
    alias_map = pin["intrusion_sets"]
    corpus = json.loads(CORPUS_OUT.read_text()) if CORPUS_OUT.exists() else {"rows": []}
    errors = {r["row_id"]: r["error"] for r in corpus["rows"] if r.get("error")}

    anns: dict[str, dict[str, dict]] = {}
    for slot in ("A", "B"):
        p = _ann_path(slot)
        if not p.exists():
            print(f"missing annotations for annotator {slot} ({p})", file=sys.stderr)
            return 1
        state = json.loads(p.read_text())
        anns[slot] = {rid: a for rid, a in state["annotations"].items() if a.get("ok")}
    adj_path = _ann_path("C")
    adjudicated: dict[str, dict] = {}
    if adj_path.exists():
        adj_state = json.loads(adj_path.read_text())
        adjudicated = {rid: a for rid, a in adj_state["annotations"].items() if a.get("ok")}

    suites = ("cti_technique", "cti_actor", "deception")
    per_suite: dict[str, Any] = {}
    disagreement_rows: list[str] = []
    for suite in suites:
        sinfo: dict[str, Any] = {"suite": suite, "n_rows": sum(
            1 for k in key.values() if k["suite"] == suite)}
        # inter-annotator κ on every judged column
        ids = [rid for rid in anns["A"] if rid in anns["B"]
               and key.get(rid, {}).get("suite") == suite]
        kappas: dict[str, float | None] = {}
        for col, _allowed in (
            ("identification", VERDICTS_ID), ("served_on_topic", VERDICTS_TOPIC),
            ("realism", VERDICTS_REALISM),
        ):
            a = [anns["A"][rid].get(col) for rid in ids]
            b = [anns["B"][rid].get(col) for rid in ids]
            valid = [(x, y) for x, y in zip(a, b, strict=False) if x is not None and y is not None]
            kappas[col] = (cohens_kappa([x for x, _ in valid], [y for _, y in valid])
                           if len(valid) >= 10 else None)
            kappas[f"{col}_n"] = len(valid)
        sinfo["kappa_A_vs_B"] = kappas
        # set-based P/R/F1 per annotator
        for slot in ("A", "B"):
            if suite in TECH_SUITES:
                sinfo[f"prf_{slot}"] = {
                    k: v for k, v in _suite_verdicts(anns[slot], suite, key, alias_map).items()
                    if k != "rows"}
            else:
                vals = [anns[slot][rid].get("realism") for rid in ids
                        if anns[slot][rid].get("realism")]
                dist = {v: vals.count(v) for v in VERDICTS_REALISM}
                sinfo[f"realism_dist_{slot}"] = dist
        # consensus (A, else adjudicated C) and disagreement list
        dis, consensus_ids = [], 0
        for rid in ids:
            va, vb = anns["A"][rid], anns["B"][rid]
            col = "realism" if suite == "deception" else "identification"
            xa, xb = va.get(col), vb.get(col)
            if xa is None or xb is None:
                continue
            if xa == xb:
                consensus_ids += 1
            else:
                dis.append({"row_id": rid, "A": xa, "B": xb,
                            "C": adjudicated.get(rid, {}).get(col)})
        sinfo["agreement_n"] = consensus_ids
        sinfo["kappa_pair_n"] = len(ids)
        sinfo["disagreements"] = dis
        disagreement_rows += [d["row_id"] for d in dis if d["C"] is None]
        per_suite[suite] = sinfo

    unresolved = len(disagreement_rows)
    adjudication_summary = {
        suite: {
            "n": len(s.get("disagreements", [])),
            "C_sides_with_A": sum(1 for d in s.get("disagreements", [])
                                  if d.get("C") is not None and d["C"] == d["A"]),
            "C_sides_with_B": sum(1 for d in s.get("disagreements", [])
                                  if d.get("C") is not None and d["C"] == d["B"]),
            "C_neither": sum(1 for d in s.get("disagreements", [])
                             if d.get("C") is not None
                             and d["C"] not in (d["A"], d["B"])),
        }
        for suite, s in per_suite.items()
    }
    artifact = {
        "what": "218-row CTI manual audit — double-annotated, P/R/F1 + Cohen's kappa (advisory #5)",
        "attack_pin": _attack_pin_summary(pin),
        "annotators": {slot: ANNOTATORS[slot] for slot in ("A", "B", "C")},
        "annotation_protocol": (
            "two independent LLM annotators label blinded packets (no gold, no pipeline "
            "scores); requested is read from the query alone, identified from the analysis "
            "record; a third annotator adjudicates disagreements; human raters (decision Q4) "
            "receive the same packets via export-human"),
        "rows_total": len(key),
        "annotation_errors": errors,
        "per_suite": per_suite,
        "adjudication_summary": adjudication_summary,
        "unresolved_disagreements": unresolved,
        "machine_vs_human": _machine_vs_human(key, anns, adjudicated),
        "echo_diagnosis": _echo_diagnosis(key, anns, corpus.get("rows", [])),
        "served_text_row_identity_vs_two_channel": _row_identity_vs_two_channel(key, corpus.get("rows", [])),
        "workload_quality_flags": _workload_flags(anns, key),
    }
    # rescore-machine writes the echo-guard correction into this artifact;
    # preserve it across score re-runs (run_score rebuilds the artifact fresh).
    if AUDIT_OUT.exists():
        with contextlib.suppress(json.JSONDecodeError, OSError):
            prior_audit = json.loads(AUDIT_OUT.read_text())
            if prior_audit.get("echo_guard_correction"):
                artifact["echo_guard_correction"] = prior_audit["echo_guard_correction"]
    AUDIT_OUT.write_text(json.dumps(artifact, indent=2))
    print("=" * 76)
    print("CTI MANUAL AUDIT")
    print("=" * 76)
    for suite, s in per_suite.items():
        k_id = s["kappa_A_vs_B"].get("identification") or s["kappa_A_vs_B"].get("realism")
        line = f"  {suite:<14} n={s['n_rows']:>3} kappa={k_id}"
        if "prf_A" in s:
            line += (f" | A strict P/R/F1 = {s['prf_A']['strict']['precision']}/"
                     f"{s['prf_A']['strict']['recall']}/{s['prf_A']['strict']['f1']}")
        print(line)
    print(f"  unresolved disagreements: {unresolved}")
    print(f"  artifact: {AUDIT_OUT.name}")
    return 0


def _echo_diagnosis(key: dict[str, dict], anns: dict[str, dict[str, dict]],
                    corpus_rows: list[dict]) -> dict[str, Any]:
    """Attribute machine/human served-text conflicts to template-fallback echoes.

    A row is an echo when the served text contains 'command not found' or
    re-emits the query verbatim (the deterministic fallback shape). The 2026-09-27
    audit found EVERY machine-on-topic/human-off-topic conflict on technique rows
    was an echo: the string-matching served-text scorer credits the technique ID
    inside the echoed query. This is a machine-scorer validity finding, not a
    pipeline failure.
    """
    text_by_row = {r["row_id"]: (r.get("response_text") or "") for r in corpus_rows}
    out: dict[str, Any] = {}
    for suite in ("cti_technique", "cti_actor", "deception"):
        conf: dict[str, int] = {}
        for rid, k in key.items():
            if k["suite"] != suite or not anns["A"].get(rid, {}).get("ok"):
                continue
            ms = (k.get("machine_scores") or {}).get("served_text")
            m = 1 if (ms is not None and ms >= 0.3) else 0
            h = 1 if anns["A"][rid].get("served_on_topic") in ("yes", "partial") else 0
            rt = text_by_row.get(rid, "").lower()
            q = (k["query"] or "").lower().strip(" .?!")
            is_echo = ("command not found" in rt) or (bool(q) and q in rt)
            conf[f"({m},{h}){':echo' if is_echo else ''}"] = conf.get(
                f"({m},{h}){':echo' if is_echo else ''}", 0) + 1
        m_yes_h_no_echo = conf.get("(1,0):echo", 0)
        m_yes_h_no = m_yes_h_no_echo + conf.get("(1,0)", 0)
        out[suite] = {
            "confusion": conf,
            "machine_yes_human_no_total": m_yes_h_no,
            "machine_yes_human_no_that_are_echoes": m_yes_h_no_echo,
            "all_conflicts_are_echoes": m_yes_h_no > 0 and m_yes_h_no_echo == m_yes_h_no,
        }
    return out


def _row_identity_vs_two_channel(key: dict[str, dict], corpus_rows: list[dict]) -> dict[str, Any]:
    """Cross-artifact check: are the audited served texts row-identical to the
    two-channel reference run? Exact score equality on every row under identical
    scorers means the serve path is deterministic (template fallback dominance)
    — the audit audited the SAME transcript surface as the §VI tables."""
    ckpt = RESULTS / "external_baseline_two_channel_metrics_full_checkpoint.json"
    if not ckpt.exists():
        return {"checked": False, "reason": "two-channel checkpoint not found"}
    tc = {r["name"]: r for r in json.loads(ckpt.read_text()).get("rows", [])}
    by_id = {r["row_id"]: r for r in corpus_rows}
    match = differ = post_guard_changed = 0
    for rid, k in key.items():
        nm = f"{k['suite']}_{k['query'][:40].replace(' ', '_')}"
        if nm not in tc or rid not in by_id:
            continue
        row = by_id[rid]
        # Pre-guard scores are the surface-identity test: under identical
        # (pre-guard) scorers, served_text score is a deterministic function of
        # the transcript, so exact score equality on every row means the two
        # runs served the same text surface. The checkpoint stores scores, not
        # transcripts, so score equality under the shared scorer is the
        # available identity evidence.
        pre = (row.get("machine_scores_initial") or row.get("machine_scores") or {})
        a = pre.get("served_text")
        b = tc[nm].get("served_text")
        if (a or 0) == (b or 0):
            match += 1
        else:
            differ += 1
        cur = (row.get("machine_scores") or {}).get("served_text")
        if row.get("machine_scores_initial") is not None and (cur or 0) != (a or 0):
            post_guard_changed += 1
    return {
        "checked": True,
        "method": ("score-equality under identical pre-guard scorers: served_text score is a "
                   "deterministic function of the transcript, so per-row exact score equality "
                   "between independent runs means the runs served the same text surface "
                   "(the checkpoint stores scores, not transcripts)"),
        "rows_compared": match + differ,
        "identical_pre_guard": match,
        "differing_pre_guard": differ,
        "deterministic_serve_surface": match > 0 and differ == 0,
        "post_guard_score_changes": post_guard_changed,
        "post_guard_note": ("post_guard_score_changes counts rows whose score changed under the "
                            "echo-guarded scorer — an expected correction artifact, not a text "
                            "difference between runs"),
    }


def _machine_vs_human(key: dict[str, dict], anns: dict[str, dict[str, dict]],
                      adjudicated: dict[str, dict]) -> dict[str, Any]:
    """Agreement between the automated channel scores and the manual verdicts.

    Dichotomizations (pre-declared):
      machine served_text >= 0.3 (the harness pass threshold) vs manual
      served_on_topic in {yes, partial}; cti_analysis >= 0.85 vs manual
      identification == correct (technique rows); realism score >= 0.3 vs
      manual realism in {realistic, partial} (deception rows).
    """
    out: dict[str, Any] = {}
    for suite in ("cti_technique", "cti_actor", "deception"):
        pairs: list[tuple[int, int]] = []
        for rid, k in key.items():
            if k["suite"] != suite:
                continue
            a = anns["A"].get(rid) or {}
            if not a.get("ok"):
                continue
            ms = (k.get("machine_scores") or {})
            mscore = ms.get("served_text")
            if suite == "deception":
                mv = 1 if (mscore is not None and mscore >= 0.3) else 0
                hv = 1 if a.get("realism") in ("realistic", "partial") else 0
            else:
                mv = 1 if (mscore is not None and mscore >= 0.3) else 0
                hv = 1 if a.get("served_on_topic") in ("yes", "partial") else 0
            pairs.append((mv, hv))
            if suite in TECH_SUITES and a.get("identification") is not None:
                ascore = ms.get("cti_analysis")
                am = 1 if (ascore is not None and ascore >= 0.85) else 0
                ah = 1 if a.get("identification") == "correct" else 0
                pairs.append((am, ah))
        if pairs:
            agree = sum(1 for m, h in pairs if m == h)
            k = cohens_kappa([str(m) for m, _ in pairs], [str(h) for _, h in pairs])
            out[suite] = {"n_pairs": len(pairs), "agreement": round(agree / len(pairs), 4),
                          "kappa": k}
    return out


def _workload_flags(anns: dict[str, dict[str, dict]], key: dict[str, dict],
                    alias_map: dict[str, list[str]] | None = None) -> list[dict]:
    """Rows where annotator A's independent reading disagrees with the workload's
    embedded gold — candidate workload-label errors (an audit by-product)."""
    if alias_map is None:
        alias_map = load_attack_pin()["intrusion_sets"]
    flags: list[dict] = []
    for rid, a in anns["A"].items():
        if not a.get("ok"):
            continue
        k = key.get(rid, {})
        gold = k.get("gold", {})
        if k.get("suite") == "cti_technique" and a.get("requested") not in (None, "unclear"):
            g = _norm_tid(str(gold.get("expected_technique", "")))
            r = _norm_tid(a["requested"])
            if g and r != g and _parent_tid(r) != _parent_tid(g):
                flags.append({"row_id": rid, "kind": "technique", "gold": g, "annotator": r})
        elif k.get("suite") == "cti_actor" and a.get("requested") not in (None, "unclear"):
            g = _alias_key(str(gold.get("expected_actor", "")), alias_map)
            r = _alias_key(a["requested"], alias_map)
            if g and r and g != r:
                flags.append({"row_id": rid, "kind": "actor", "gold": g, "annotator": r})
    return flags


# ─────────────────────────── adjudication ───────────────────────────

def run_adjudicate(budget_s: float | None) -> int:
    """Third annotator (C) labels only the rows where A and B disagree."""
    if not AUDIT_OUT.exists():
        print("run score first (it computes the disagreement set)", file=sys.stderr)
        return 1
    audit = json.loads(AUDIT_OUT.read_text())
    packets = {p["row_id"]: p for p in json.loads(PACKETS_OUT.read_text())["packets"]}
    todo: list[dict] = []
    for _suite, s in audit["per_suite"].items():
        for d in s.get("disagreements", []):
            if d.get("C") is None and d["row_id"] in packets:
                todo.append(packets[d["row_id"]])
    if not todo:
        print("no unresolved disagreements — nothing to adjudicate")
        return 0
    out_path = _ann_path("C")
    state = {"annotator": "C", "model": ANNOTATORS["C"], "annotations": {}}
    if out_path.exists():
        with contextlib.suppress(json.JSONDecodeError):
            state = json.loads(out_path.read_text())
    done = state["annotations"]
    t0 = time.monotonic()
    stopped = False
    for p in todo:
        if p["row_id"] in done:
            continue
        if budget_s is not None and (time.monotonic() - t0) > budget_s:
            stopped = True
            break
        parsed, err = _annotate_batch([p], ANNOTATORS["C"])
        if parsed:
            done[p["row_id"]] = {"ok": True, **_norm_annotation(parsed[0], p["suite"])}
        else:
            done[p["row_id"]] = {"ok": False, "error": (err or "parse failure")[:200]}
        _persist_annotations(out_path, state)
        print(f"  [C] {p['row_id']} {'ok' if parsed else 'ERR'}", flush=True)
    print(f"[C] adjudication {'incomplete — re-invoke' if stopped else 'done'}")
    return 0


# ─────────────────────────── human export ───────────────────────────

def run_export_human(n: int) -> int:
    packets = json.loads(PACKETS_OUT.read_text())["packets"]
    by_suite: dict[str, list[dict]] = {"cti_technique": [], "cti_actor": [], "deception": []}
    for p in packets:
        by_suite.setdefault(p["suite"], []).append(p)
    # stratified sample in packet order (packets are already seed-shuffled)
    tech_n = min(n * 123 // 218, len(by_suite["cti_technique"]))
    act_n = min(n * 35 // 218, len(by_suite["cti_actor"]))
    dec_n = min(n - tech_n - act_n, len(by_suite["deception"]))
    sample = (by_suite["cti_technique"][:tech_n] + by_suite["cti_actor"][:act_n]
              + by_suite["deception"][:dec_n])
    HUMAN_DIR.mkdir(parents=True, exist_ok=True)
    header = [
        "# Blind Annotation Task — Independent Rater Packet",
        "",
        "You are rating outputs of a research cyber-deception system. Packets are",
        "blinded: no system labels, no gold answers, no model names. Work alone.",
        f"Reference taxonomy: {load_attack_pin()['attack_version']}.",
        "Time budget ≈ 2–3 min/item. Record your independent judgment per the",
        "instructions; there is no reward for agreeing with any prior label.",
        "Consent: docs/HUMAN_EVAL_CONSENT.md must be signed before this packet.",
        "",
        "---",
        "",
    ]
    (HUMAN_DIR / "rater_packet.md").write_text("\n".join(header) + _packets_md_body(sample))
    (HUMAN_DIR / "rater_answer_sheet.csv").write_text(
        "row_id,suite,requested,identified,identification,served_on_topic,realism,notes\n"
        + "\n".join(f"{p['row_id']},{p['suite']},,,,,," for p in sample))
    print(f"human packet: {len(sample)} items ({tech_n} tech / {act_n} actor / {dec_n} deception)"
          f" -> {HUMAN_DIR}/")
    return 0


def _packets_md_body(packets: list[dict]) -> str:
    lines: list[str] = []
    for p in packets:
        lines += [f"## {p['row_id']} ({p['suite']})", f"**QUERY:** {p['query']}", "",
                  "**SERVED_TEXT:**", "```", p["served_text"] or "(empty)", "```"]
        an = p["analysis"]
        if any(an.values()):
            lines += ["**ANALYSIS:**", "```json", json.dumps(an, indent=1)[:1200], "```"]
        else:
            lines.append("**ANALYSIS:** (empty)")
        lines.append("")
    return "\n".join(lines)


# ─────────────────────────── CLI ───────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="218-row CTI manual audit (advisory #5)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("collect", "packet"):
        sp = sub.add_parser(name)
        if name == "collect":
            sp.add_argument("--budget-s", type=float, default=None)
            sp.add_argument("--limit", type=int, default=None)
        else:
            sp.add_argument("--limit", type=int, default=None)
    ap = sub.add_parser("annotate")
    ap.add_argument("--annotator", required=True, choices=sorted(ANNOTATORS))
    ap.add_argument("--budget-s", type=float, default=None)
    ap.add_argument("--batch", type=int, default=5)
    ap.add_argument("--suite", choices=("cti_technique", "cti_actor", "deception"), default=None)
    ap.add_argument("--only", default=None, help="comma-separated row_ids (pilot/smoke runs)")
    ap2 = sub.add_parser("adjudicate")
    ap2.add_argument("--budget-s", type=float, default=None)
    sub.add_parser("score")
    ep = sub.add_parser("export-human")
    ep.add_argument("--n", type=int, default=60)
    sub.add_parser("rescore-machine")
    args = parser.parse_args()

    if args.cmd == "collect":
        return run_collect(args.budget_s, args.limit)
    if args.cmd == "packet":
        return run_packet(args.limit)
    if args.cmd == "annotate":
        return run_annotate(args.annotator, args.budget_s, args.batch, args.suite, args.only)
    if args.cmd == "adjudicate":
        return run_adjudicate(args.budget_s)
    if args.cmd == "score":
        return run_score()
    if args.cmd == "rescore-machine":
        return run_rescore_machine()
    return run_export_human(args.n)


if __name__ == "__main__":
    raise SystemExit(main())
