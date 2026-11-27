from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "artifact_audit"
SCIENTIFIC_ROOTS = (ROOT / "results", ROOT / "evidence")
TEXT_SUFFIXES = {".md", ".txt", ".log", ".tex", ".fail"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def family_for(rel: str) -> str:
    parts = Path(rel).parts
    if parts[0] == "evidence":
        return "evidence_and_operational_capture"
    if len(parts) <= 2:
        return "results_root_mixed_legacy_and_baseline"
    if parts[1] == "laya_decision_v2":
        if parts[2].startswith(tuple(f"{i:03d}_" for i in range(170))):
            return "laya_decision_v2/runtime_case_sessions"
        return f"laya_decision_v2/{parts[2]}"
    if parts[1] == "laya_research":
        return f"laya_research/{parts[2]}"
    return parts[1]


def initial_status(rel: str) -> str:
    low = rel.lower()
    if "laya_research/ai_raters" in low or "laya_research/rater_labels_v3_ai" in low or "laya_research/expert_ai_labels" in low or "laya_research/expert_ai_run_provenance" in low:
        return "AI-derived exploratory annotation/provenance; not human ground truth and not joinable to frozen predictions"
    if "laya_research/human_rater_packets" in low or "laya_research/rater_packets" in low or "laya_research/human_reference" in low:
        return "reference packet/template; no frozen independent reference claim without completed provenance and adjudication"
    if "laya_research/codex_redteam" in low or "laya_research/blind" in low:
        return "blinding/red-team audit support; not performance evidence"
    if "_primary_169" in low:
        return "frozen V2b primary execution/reference/analysis support; AI-derived single-family reference; no workflow gain"
    if "exploratory_120" in low:
        return "frozen exploratory Laya V2 cohort; AI-derived reference; do not reuse as fresh confirmatory holdout"
    if "_runtime_sessions_smoke" in low:
        return "runtime smoke only; not efficacy evidence"
    if "attempt_002" in low and "decision_fusion_v4" in low:
        return "aborted/incomplete V4 attempt; excluded from complete attempt 003"
    if any(s in low for s in ("smoke", "probe", "quota", "catalog", "execution_log", "pytest", "local_inference", "provider_selection", "wire", "correlation")):
        return "operational/provider-unavailable or smoke; inspect before any scientific use"
    if any(s in low for s in ("checkpoint", "partial", "pilot", "pre_repair", "pre-prompt", "pre-fqdn", "run1", "chunk", "history")):
        return "historical/intermediate; supersession unresolved by filename alone"
    if "evidence_judge_paired_validation" in low:
        return "synthetic-contract"
    if "evidence_judge_real_data" in low or "evidence_judge_filtering" in low:
        return "reference-pending/descriptive; accuracy not established"
    if "laya_decision_v2" in low:
        return "exploratory or confirmatory frozen study; see Laya registry"
    if "laya_decision_v3" in low or "laya_research" in low:
        return "synthetic-contract/exploratory; inspect family-specific gate"
    if "decision_fusion_v4" in low:
        return "supporting retrospective runtime; policy correctness unresolved"
    if "before_openrouter" in low:
        return "historical pre-provider migration artifacts; excluded from current headline results"
    if "human_eval_scored_20260922_180637_consensus" in low:
        return "bounded single-model-family evaluator-persona consistency result; not independent human agreement"
    if "human_eval" in low or "human_blind" in low or "cti_audit_human_packet" in low:
        return "annotation/reference artifact; inspect blinding, completion, provenance, and freeze before accuracy use"
    if "verifier_redteam" in low or "verifier_harm_probe" in low:
        return "bounded deterministic or model-authored verifier stress test; not full attacker-session effectiveness"
    if "live_benchmark" in low or "b4_baseline" in low or "bootstrap_ci" in low or "two_channel" in low:
        return "archived baseline campaign evidence; interpretation must follow current scorer-channel and provenance corrections"
    if "jev" in low:
        return "bounded/provider-sensitive Jev result or replay; identify exact cohort, availability, and estimand"
    return "unclassified pending artifact-level scientific review"


def walk_files() -> Iterator[Path]:
    seen: set[Path] = set()
    for base in SCIENTIFIC_ROOTS:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


def inspect_json(path: Path) -> dict[str, Any]:
    if path.suffix == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
        rows = [value]
    else:
        rows = []
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except Exception as exc:
                try:
                    whole = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    return {"parse_status": "invalid_jsonl", "parse_error": f"line {line_no}: {type(exc).__name__}: {exc}", "rows": len(rows)}
                rows = [whole]
                suffix_mismatch = True
                break
    keys: Counter[str] = Counter()
    values: dict[str, set[str]] = defaultdict(set)
    key_re = re.compile(r"(model|provider|reference|cohort|dataset|source|experiment|run|status|verdict|arm|mode|seed|timestamp|generated|count|total|accuracy|precision|recall|metric|decision|coverage)", re.I)
    def visit(obj: Any, depth: int = 0) -> None:
        if depth > 5:
            return
        if isinstance(obj, dict):
            for key, item in obj.items():
                skey = str(key)
                keys[skey] += 1
                if key_re.search(skey) and isinstance(item, (str, int, float, bool)):
                    sval = str(item).replace("\n", " ")[:180]
                    if sval:
                        values[skey].add(sval)
                visit(item, depth + 1)
        elif isinstance(obj, list):
            for item in obj[:3000]:
                visit(item, depth + 1)
    for row in rows:
        visit(row)
    return {
        "parse_status": "valid_json" if path.suffix == ".json" else ("valid_json_document_suffix_mismatch" if locals().get("suffix_mismatch", False) else "valid_jsonl"),
        "rows": len(rows),
        "top_level_type": type(rows[0]).__name__ if rows else "empty",
        "line_count": len(path.read_text(encoding="utf-8").splitlines()) if locals().get("suffix_mismatch", False) else None,
        "observed_keys": sorted(keys),
        "metadata_values": {k: sorted(v)[:12] for k, v in sorted(values.items()) if v},
    }


def inspect(path: Path) -> dict[str, Any]:
    rel = path.relative_to(ROOT).as_posix()
    stat = path.stat()
    suffix = path.suffix.lower()
    item: dict[str, Any] = {
        "path": rel,
        "size_bytes": stat.st_size,
        "format": suffix.lstrip(".") or "no_extension",
        "sha256": sha256(path),
        "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "experiment_family": family_for(rel),
        "initial_scientific_status": initial_status(rel),
        "producer": "not reliably encoded at file level; see experiment registry and source references",
        "input_cohort": "not reliably encoded at file level; inspect structured metadata where available",
        "model_identity": "not asserted unless present in metadata_values",
        "reference_type": "not asserted unless present in metadata_values",
        "parent_artifacts": "not inferred from filename",
    }
    if suffix in {".json", ".jsonl"}:
        try:
            item.update(inspect_json(path))
        except Exception as exc:
            item.update({"parse_status": "invalid_or_unreadable", "parse_error": f"{type(exc).__name__}: {exc}"})
    elif suffix == ".csv":
        try:
            with path.open(encoding="utf-8", newline="") as stream:
                reader = csv.reader(stream)
                header = next(reader, [])
                row_count = sum(1 for _ in reader)
            item.update({"parse_status": "valid_csv", "rows": row_count, "columns": header})
        except Exception as exc:
            item.update({"parse_status": "invalid_or_unreadable", "parse_error": f"{type(exc).__name__}: {exc}"})
    elif suffix in TEXT_SUFFIXES:
        try:
            text = path.read_text(encoding="utf-8")
            item.update({"parse_status": "readable_text", "line_count": len(text.splitlines())})
        except Exception as exc:
            item.update({"parse_status": "invalid_or_unreadable", "parse_error": f"{type(exc).__name__}: {exc}"})
    else:
        item.update({"parse_status": "binary_or_unparsed"})
    return item


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    entries = [inspect(path) for path in walk_files()]
    with (OUTPUT / "artifact_manifest.jsonl").open("w", encoding="utf-8") as stream:
        for entry in entries:
            stream.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        groups[entry["experiment_family"]].append(entry)
    registry = []
    for family, members in sorted(groups.items()):
        parses = Counter(m.get("parse_status", "not_applicable") for m in members)
        statuses = Counter(m["initial_scientific_status"] for m in members)
        registry.append({
            "experiment_family": family,
            "artifact_count": len(members),
            "bytes": sum(m["size_bytes"] for m in members),
            "format_parse_counts": dict(sorted(parses.items())),
            "initial_status_counts": dict(sorted(statuses.items())),
            "review_status": "triage grouping; consult accompanying audit report; unresolved files are explicitly marked in the manifest",
        })
    (OUTPUT / "experiment_registry.json").write_text(json.dumps({
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": ["results/**", "evidence/**"],
        "artifact_count": len(entries),
        "families": registry,
        "note": "Parser success is format inspection only and does not establish provenance, validity, independence, or paper eligibility.",
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    failures = [e for e in entries if e.get("parse_status", "").startswith("invalid")]
    print(json.dumps({
        "artifact_count": len(entries),
        "families": len(groups),
        "parse_status_counts": dict(Counter(e.get("parse_status", "not_applicable") for e in entries)),
        "parse_failures": [{"path": e["path"], "error": e.get("parse_error")} for e in failures],
        "output_dir": str(OUTPUT),
    }, indent=2))


if __name__ == "__main__":
    main()
