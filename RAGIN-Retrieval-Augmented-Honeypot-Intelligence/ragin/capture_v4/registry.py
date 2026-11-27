import json
from pathlib import Path

REGISTRY_FIELDS = (
    "capture_id", "native_session_id", "source_class", "deployment_id", "capture_started_at_utc",
    "capture_ended_at_utc", "raw_log_sha256", "capture_manifest_sha256", "canonical_record_sha256",
    "source_cluster_id", "eligible_for_real_evaluation", "ineligibility_reason",
)

def read_registry(path):
    registry = Path(path)
    if not registry.exists():
        return []
    rows = []
    for line in registry.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows

def append_registry_record(path, record):
    registry = Path(path)
    registry.parent.mkdir(parents=True, exist_ok=True)
    row = {field: record.get(field) for field in REGISTRY_FIELDS}
    if not row["capture_id"] or not row["native_session_id"]:
        raise ValueError("capture and native session IDs are required")
    existing = read_registry(registry)
    if any(item.get("capture_id") == row["capture_id"] or item.get("native_session_id") == row["native_session_id"] for item in existing):
        raise ValueError("duplicate capture_id or native_session_id")
    with registry.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    return row
