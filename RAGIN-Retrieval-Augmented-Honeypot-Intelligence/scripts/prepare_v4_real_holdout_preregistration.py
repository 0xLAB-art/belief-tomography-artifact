from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/decision_fusion_v4"
NAMESPACE = "RAGIN_V4_REAL_HOLDOUT_V1"
ALLOWED_STRATEGIES = [
    "baseline",
    "maximize_recon_surface",
    "fake_success_and_return_visits",
    "steer_to_honeytoken_credentials",
    "expose_decoy_internal_topology",
    "contain_in_fiction_and_instrument",
    "low_intensity_administration",
]


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_json(value: Any) -> str:
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(errors="replace"))
    except Exception:
        return None


def nested_objects(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nested_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from nested_objects(child)


def collect_history() -> dict[str, set[str]]:
    sets = {name: set() for name in ("case", "session", "group", "source", "raw", "normalized")}
    roots = [ROOT / "results/laya_decision_v2", ROOT / "results/laya_decision_v3", ROOT / "results/decision_fusion_v4", ROOT / "results/laya_research"]
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl"}:
                continue
            if path.suffix.lower() == ".jsonl":
                try:
                    values = [json.loads(line) for line in path.read_text(errors="replace").splitlines() if line.strip()]
                except Exception:
                    values = []
            else:
                obj = read_json(path)
                values = obj if isinstance(obj, list) else [obj]
            for obj in nested_objects(values):
                for key, value in obj.items():
                    key_l = str(key).lower()
                    vals = value if isinstance(value, list) else [value]
                    for item in vals:
                        if not isinstance(item, (str, int)):
                            continue
                        text = str(item)
                        if key_l == "case_id":
                            sets["case"].add(text)
                        if key_l in {"session_id", "sessionid", "session"} or text.startswith("ses-"):
                            sets["session"].add(text)
                        if key_l in {"session_group_id", "group_id"}:
                            sets["group"].add(text)
                        if key_l in {"source_record_id", "record_id"}:
                            sets["source"].add(text)
                        if re.fullmatch(r"[0-9a-fA-F]{64}", text) and "input" in key_l:
                            if "normalized" in key_l:
                                sets["normalized"].add(text.lower())
                            else:
                                sets["raw"].add(text.lower())
    return sets


def tracked_paths(prefix: str) -> set[str]:
    result = subprocess.run(["git", "ls-files", prefix], cwd=ROOT, capture_output=True, text=True, check=True)
    return set(result.stdout.splitlines())


def candidate(case_id: str, group_id: str, family: str, record_id: str, raw_hash: str, context_hash: str, structural: dict[str, Any], raw_available: bool, constructible: bool, provenance: str) -> dict[str, Any]:
    sample_material = f"{NAMESPACE}{group_id}{raw_hash}".encode()
    return {
        "case_id": case_id,
        "session_group_id": group_id,
        "source_family": family,
        "source_record_id": record_id,
        "raw_input_sha256": raw_hash,
        "session_context_sha256": context_hash,
        "structural": structural,
        "provenance_class": provenance,
        "raw_evidence_available": raw_available,
        "don_input_constructible": constructible,
        "sampling_key": sha_bytes(sample_material),
    }


def parse_jsonl_session(path: Path, family: str, tracked: set[str]) -> dict[str, Any]:
    try:
        records = [json.loads(line) for line in path.read_text(errors="replace").splitlines() if line.strip()]
    except Exception:
        records = []
    eligible = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        event_type = str(record.get("event_type", ""))
        event_id = str(record.get("event_id", ""))
        if event_type == "attacker_input" or event_id == "attacker_input":
            data = record.get("data")
            if data is not None and str(data).strip():
                eligible.append((index, data))
    group = path.stem
    selected = eligible[-1][1] if eligible else ""
    raw_hash = sha_json(selected)
    context_hash = sha_bytes(path.read_bytes())
    provenance = "REAL_ELIGIBLE" if str(path.relative_to(ROOT)) in tracked else "PROVENANCE_UNCLEAR"
    return candidate(
        f"V4R-{group}",
        group,
        family,
        str(path.relative_to(ROOT)),
        raw_hash,
        context_hash,
        {"event_count": len(records), "attacker_input_event_count": len(eligible), "selected_event_index": eligible[-1][0] if eligible else None, "file_size_bytes": path.stat().st_size},
        bool(eligible),
        bool(eligible),
        provenance,
    )


def collect_candidates() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tracked = tracked_paths("data/sessions/")
    items: list[dict[str, Any]] = []
    source_meta: dict[str, Any] = {}
    sessions = ROOT / "data/sessions"
    for path in sorted(sessions.glob("*.jsonl")):
        items.append(parse_jsonl_session(path, "data_sessions", tracked))
    field = ROOT / "data/field"
    for path in sorted(field.glob("*.jsonl")):
        try:
            records = [json.loads(line) for line in path.read_text(errors="replace").splitlines() if line.strip()]
        except Exception:
            records = []
        group = path.stem
        items.append(candidate(f"V4R-{group}", group, "field_export", str(path.relative_to(ROOT)), sha_bytes(path.read_bytes()), sha_bytes(path.read_bytes()), {"record_count": len(records), "file_size_bytes": path.stat().st_size}, False, False, "REAL_ELIGIBLE"))
    linux = read_json(ROOT / "data/real_linux_transcripts.json")
    if isinstance(linux, list):
        for index, obj in enumerate(linux):
            transcript = obj.get("transcript") if isinstance(obj, dict) else None
            if transcript is None:
                continue
            items.append(candidate(f"V4R-real-linux-{index:04d}", f"real-linux-{index:04d}", "real_linux_transcripts", "data/real_linux_transcripts.json#" + str(index), sha_json(transcript), sha_json({"index": index, "transcript_length": len(str(transcript))}), {"record_index": index, "transcript_length": len(str(transcript))}, bool(str(transcript).strip()), bool(str(transcript).strip()), "REAL_ELIGIBLE"))
    source_meta["cowrie_note"] = "Cowrie logs are documented real controlled honeypot sessions; the current rotated logs are retained for audit but do not yield a stable command-session candidate without execution-time reconstruction."
    source_meta["field_note"] = "Field exports are documented natural collection, but current records expose no attacker-input field in the metadata-only structural contract and therefore fail input validation."
    return items, source_meta


def overlap_sets(history: dict[str, set[str]]) -> dict[str, set[str]]:
    old120: dict[str, set[str]] = {key: set() for key in history}
    old169: dict[str, set[str]] = {key: set() for key in history}
    for base_name, target in (("exploratory_120", old120), ("primary_169", old169)):
        roots = [ROOT / "results/laya_decision_v2"]
        for base in roots:
            for path in base.rglob("*"):
                if not path.is_file() or base_name not in path.name:
                    continue
                if path.suffix not in {".json", ".jsonl"}:
                    continue
                if path.suffix == ".jsonl":
                    try:
                        vals = [json.loads(line) for line in path.read_text(errors="replace").splitlines() if line.strip()]
                    except Exception:
                        vals = []
                else:
                    obj = read_json(path); vals = obj if isinstance(obj, list) else [obj]
                for obj in nested_objects(vals):
                    for key, value in obj.items():
                        key_l = str(key).lower(); seq = value if isinstance(value, list) else [value]
                        for item in seq:
                            text = str(item)
                            if key_l == "case_id": target["case"].add(text)
                            if key_l in {"session_id", "sessionid", "session"} or text.startswith("ses-"): target["session"].add(text)
                            if key_l in {"session_group_id", "group_id"}: target["group"].add(text)
                            if key_l in {"source_record_id", "record_id"}: target["source"].add(text)
                            if re.fullmatch(r"[0-9a-fA-F]{64}", text) and "input" in key_l: target["normalized" if "normalized" in key_l else "raw"].add(text.lower())
    return {"old_120": old120, "old_169": old169}


def exclude_reason(item: dict[str, Any], historical: dict[str, set[str]], scoped: dict[str, dict[str, set[str]]]) -> str | None:
    if item["provenance_class"] != "REAL_ELIGIBLE":
        return item["provenance_class"]
    if item["case_id"] in historical["case"] or item["session_group_id"] in historical["session"] or item["raw_input_sha256"] in historical["raw"] or item["source_record_id"] in historical["source"]:
        return "DEVELOPMENT_USED"
    for name, sets in scoped.items():
        if item["case_id"] in sets["case"] or item["session_group_id"] in sets["session"] or item["raw_input_sha256"] in sets["raw"] or item["source_record_id"] in sets["source"]:
            return name
    if item["case_id"].startswith("V4R-") and item["session_group_id"].startswith(("V4D-", "V4V-")):
        return "SYNTHETIC"
    if item["source_record_id"].startswith(("tests/", "test/")):
        return "TEST_FIXTURE"
    return None


def build_inventory(items: list[dict[str, Any]], history: dict[str, set[str]], scoped: dict[str, dict[str, set[str]]], source_meta: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    counts = Counter(); source_counts = Counter(); eligible=[]
    for item in items:
        reason = exclude_reason(item, history, scoped)
        if reason is None and not item["raw_evidence_available"]:
            reason = "UNUSABLE"
        item["inventory_status"] = "REAL_ELIGIBLE" if reason is None else reason
        counts[item["inventory_status"]] += 1
        source_counts[item["source_family"]] += 1
        if reason is None:
            eligible.append(item)
    inventory = {
        "schema": "ragin.v4.real_pool_inventory.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "metadata_only": True,
        "candidate_sources": [
            {"path": "data/sessions/*.jsonl", "classification": "REAL_ELIGIBLE", "provenance_basis": "repository independent-labeling source registry; tracked session event records"},
            {"path": "data/cowrie_logs/", "classification": "REAL_ELIGIBLE", "provenance_basis": "repository independent-labeling source registry; controlled Cowrie logs", "candidate_case_count": 0},
            {"path": "data/field/", "classification": "REAL_ELIGIBLE", "provenance_basis": "field export documentation", "input_contract_status": "not eligible in current structural form"},
            {"path": "data/real_linux_transcripts.json", "classification": "REAL_ELIGIBLE", "provenance_basis": "repository independent-labeling source registry"},
            {"path": "results/laya_research/", "classification": "DEVELOPMENT_USED", "provenance_basis": "historical study artifacts"},
            {"path": "results/decision_fusion_v4/", "classification": "SYNTHETIC/DEVELOPMENT_USED", "provenance_basis": "V4 synthetic benchmark and smoke artifacts"},
            {"path": "evidence/sessions/", "classification": "TEST_FIXTURE", "provenance_basis": "execution evidence directory"},
        ],
        "candidate_case_count": len(items),
        "unique_session_groups": len({item["session_group_id"] for item in items}),
        "status_counts": dict(counts),
        "source_counts": dict(source_counts),
        "eligible_unique_session_groups": len({item["session_group_id"] for item in eligible}),
        "excluded_old_120_overlap": sum(1 for item in items if item.get("inventory_status") == "old_120"),
        "excluded_old_169_overlap": sum(1 for item in items if item.get("inventory_status") == "old_169"),
        "excluded_synthetic": sum(1 for item in items if item.get("inventory_status") == "SYNTHETIC"),
        "excluded_test": sum(1 for item in items if item.get("inventory_status") == "TEST_FIXTURE"),
        "excluded_development": sum(1 for item in items if item.get("inventory_status") == "DEVELOPMENT_USED"),
        "provenance_unclear_count": sum(1 for item in items if item.get("inventory_status") == "PROVENANCE_UNCLEAR"),
        "source_notes": source_meta,
        "session_group_selection_rule": "one case per source-defined session group; for multi-turn records select the final non-empty attacker-input turn by record order, without content or outcome conditioning",
    }
    return inventory, eligible


def main() -> None:
    expected = {
        "v4_real_prototype_implementation_freeze_v1.json": "f2eef3bc30dd398023467a0c74002afc88b324d4d13b2d872909b016f4db33e2",
        "v4_future_evaluation_protocol_v1.json": "b719666320e3020815062d82aca38b9f8297296f78834d308bd22f8762c00f85",
    }
    for name, digest in expected.items():
        actual = sha_bytes((OUT / name).read_bytes())
        if actual != digest:
            raise SystemExit(f"FROZEN_ARTIFACT_HASH_MISMATCH:{name}:{actual}")
    history = collect_history()
    scoped = overlap_sets(history)
    items, source_meta = collect_candidates()
    inventory, eligible = build_inventory(items, history, scoped, source_meta)
    OUT.joinpath("v4_real_pool_inventory_v1.json").write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
    overlaps = {"old_120": scoped["old_120"], "old_169": scoped["old_169"]}
    overlap_records=[]
    for item in items:
        hits=[]
        for name, sets in overlaps.items():
            if item["session_group_id"] in sets["session"] or item["raw_input_sha256"] in sets["raw"] or item["source_record_id"] in sets["source"]:
                hits.append(name)
        if hits: overlap_records.append({"case_id": item["case_id"], "session_group_id": item["session_group_id"], "matches": hits})
    audit = {
        "schema": "ragin.v4.real_holdout_overlap_audit.v1",
        "metadata_only": True,
        "historical_set_sizes": {name: {key: len(values) for key, values in sets.items()} for name, sets in scoped.items()},
        "candidate_count": len(items),
        "old_120_overlap": sum(1 for item in items if "old_120" in next((x["matches"] for x in overlap_records if x["case_id"] == item["case_id"]), [])),
        "old_169_overlap": sum(1 for item in items if "old_169" in next((x["matches"] for x in overlap_records if x["case_id"] == item["case_id"]), [])),
        "synthetic_overlap": 0,
        "development_overlap": sum(1 for item in items if item.get("inventory_status") == "DEVELOPMENT_USED"),
        "unresolved_duplicates_conservatively_excluded": 0,
        "records": overlap_records,
        "hash": sha_json(overlap_records),
    }
    OUT.joinpath("v4_real_holdout_overlap_audit_v1.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    selected = sorted(eligible, key=lambda item: item["sampling_key"])
    if len(selected) >= 240:
        selected = selected[:240]
    elif len(selected) >= 180:
        selected = selected
    else:
        selected = []
    if selected:
        for rank, item in enumerate(selected, 1):
            item["selection_rank"] = rank
        manifest = {
            "schema": "ragin.v4.real_holdout_manifest.v1",
            "status": "FROZEN_BEFORE_EXECUTION",
            "N": len(selected),
            "selection_rule": "sort SHA256(RAGIN_V4_REAL_HOLDOUT_V1 || stable_session_group_id || raw_input_sha256) ascending; select first N",
            "cases": [{key: item[key] for key in ("case_id", "session_group_id", "source_family", "source_record_id", "raw_input_sha256", "session_context_sha256", "structural", "sampling_key", "selection_rank")} for item in selected],
            "reference_labels_exist": False,
            "policy_outputs_exist": False,
            "system_outputs_exist": False,
        }
        OUT.joinpath("v4_real_holdout_manifest_v1.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    summary = {"eligible": len(eligible), "selected": len(selected), "inventory": inventory, "audit": audit}
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
