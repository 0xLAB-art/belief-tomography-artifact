import hashlib
import json
from datetime import datetime, timezone

def _event_input(event):
    if not isinstance(event, dict):
        return None
    for key in ("input", "command", "attacker_input", "operator_input"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value
    data = event.get("data")
    if isinstance(data, dict):
        for key in ("input", "command", "attacker_input", "operator_input"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None

def select_final_input_event(events):
    selected = None
    for index, event in enumerate(events):
        if _event_input(event) is not None:
            selected = (index, event)
    return selected

def canonical_digest(value):
    payload = dict(value)
    payload["canonical_record_sha256"] = None
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

def seal_canonical_record(record):
    output = dict(record)
    output["canonical_record_sha256"] = canonical_digest(output)
    return output

def derive_canonical_record(events, manifest, *, derivation_tool, derivation_version, derivation_tool_sha256, source_cluster_id=None):
    validation = select_final_input_event(events)
    if validation is None:
        raise ValueError("no usable input event")
    index, selected = validation
    record = {
        "schema": "ragin.real_canonical_session.v1",
        "native_session_id": manifest["native_session_id"],
        "capture_id": manifest["capture_id"],
        "independence_group_id": manifest["native_session_id"],
        "source_cluster_id": source_cluster_id,
        "selected_input_event_index": index,
        "selected_input": _event_input(selected),
        "prior_session_context": events[:index],
        "raw_parent_sha256": manifest["raw_log_sha256"],
        "derivation_tool": derivation_tool,
        "derivation_version": derivation_version,
        "derivation_tool_sha256": derivation_tool_sha256,
        "derived_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    return seal_canonical_record(record)

def verify_canonical_record(record, manifest):
    errors = []
    if record.get("native_session_id") != manifest.get("native_session_id"):
        errors.append("native session mismatch")
    if record.get("capture_id") != manifest.get("capture_id"):
        errors.append("capture ID mismatch")
    if record.get("raw_parent_sha256") != manifest.get("raw_log_sha256"):
        errors.append("raw parent hash mismatch")
    if record.get("canonical_record_sha256") != canonical_digest(record):
        errors.append("canonical record hash mismatch")
    for key in ("derivation_tool", "derivation_version", "derivation_tool_sha256", "derived_at_utc"):
        if not record.get(key):
            errors.append(f"missing {key}")
    return {"valid": not errors, "errors": sorted(set(errors))}
