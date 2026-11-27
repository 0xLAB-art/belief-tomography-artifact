import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "ragin.real_capture_manifest.v1"
# Digest kinds. "sha256" is the legacy unkeyed digest (an attacker with write
# access to the manifest file can recompute it, so it proves file↔manifest
# consistency only). "hmac-sha256" binds the digest to an out-of-band study
# secret: tampering — even by the file's owner — no longer validates without
# the key.
DIGEST_KIND_UNKEYED = "sha256"
DIGEST_KIND_KEYED = "hmac-sha256"
SOURCE_CLASSES = {"NATURAL_FIELD", "CONTROLLED_REAL_HONEYPOT", "CONTROLLED_REAL_ADMIN"}
REQUIRED_FIELDS = {
    "schema", "capture_id", "native_session_id", "source_class", "collector_name", "collector_version",
    "collector_sha256", "deployment_id", "environment_id", "capture_started_at_utc", "capture_ended_at_utc",
    "raw_log_path", "raw_log_sha256", "raw_log_size_bytes", "event_count", "input_event_count",
    "source_transport", "synthetic", "replay", "test_fixture", "eligible_for_real_evaluation",
    "ineligibility_reason", "capture_manifest_created_at_utc", "capture_manifest_sha256", "parent_capture_id",
}

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())

def seal_raw_capture(path):
    raw_path = Path(path)
    raw_path.chmod(raw_path.stat().st_mode & ~0o222)
    return raw_path.stat().st_mode & 0o222 == 0

def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def manifest_digest(manifest, *, signing_key: str | None = None):
    payload = dict(manifest)
    payload["capture_manifest_sha256"] = None
    canonical = canonical_json(payload)
    if signing_key:
        return hmac.new(signing_key.encode(), canonical, hashlib.sha256).hexdigest()
    return sha256_bytes(canonical)

def _manifest_digest_kind(manifest):
    value = manifest.get("capture_manifest_digest_kind") if isinstance(manifest, dict) else None
    return value if value in (DIGEST_KIND_UNKEYED, DIGEST_KIND_KEYED) else DIGEST_KIND_UNKEYED

def _parse_timestamp(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp must be UTC ISO-8601 ending in Z")
    return datetime.fromisoformat(value[:-1] + "+00:00")

def create_manifest(raw_log_path, *, capture_id, native_session_id, source_class, collector_name,
                    collector_version, collector_sha256, deployment_id, environment_id,
                    capture_started_at_utc, capture_ended_at_utc, event_count, input_event_count,
                    source_transport, synthetic=False, replay=False, test_fixture=False,
                    eligible_for_real_evaluation=True, ineligibility_reason=None,
                    parent_capture_id=None, created_at_utc=None, signing_key=None):
    raw_path = Path(raw_log_path)
    raw_bytes = raw_path.read_bytes()
    started = _parse_timestamp(capture_started_at_utc)
    ended = _parse_timestamp(capture_ended_at_utc)
    if ended < started:
        raise ValueError("capture end precedes capture start")
    flags = bool(synthetic), bool(replay), bool(test_fixture)
    eligible = bool(eligible_for_real_evaluation) and not any(flags)
    reason = ineligibility_reason
    if not eligible and not reason:
        reason = "synthetic/replay/test_fixture capture" if any(flags) else "caller-marked ineligible"
    if eligible and reason:
        raise ValueError("eligible capture cannot have an ineligibility reason")
    manifest = {
        "schema": SCHEMA,
        "capture_id": str(capture_id),
        "native_session_id": str(native_session_id),
        "source_class": source_class,
        "collector_name": str(collector_name),
        "collector_version": str(collector_version),
        "collector_sha256": str(collector_sha256),
        "deployment_id": str(deployment_id),
        "environment_id": str(environment_id),
        "capture_started_at_utc": capture_started_at_utc,
        "capture_ended_at_utc": capture_ended_at_utc,
        "raw_log_path": str(raw_path),
        "raw_log_sha256": sha256_bytes(raw_bytes),
        "raw_log_size_bytes": len(raw_bytes),
        "event_count": int(event_count),
        "input_event_count": int(input_event_count),
        "source_transport": str(source_transport),
        "synthetic": bool(synthetic),
        "replay": bool(replay),
        "test_fixture": bool(test_fixture),
        "eligible_for_real_evaluation": eligible,
        "ineligibility_reason": reason,
        "capture_manifest_created_at_utc": created_at_utc or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "capture_manifest_sha256": None,
        "parent_capture_id": parent_capture_id,
    }
    if source_class not in SOURCE_CLASSES:
        manifest["eligible_for_real_evaluation"] = False
        manifest["ineligibility_reason"] = "unpermitted source class"
    if not manifest["collector_name"] or not manifest["collector_version"] or not manifest["collector_sha256"]:
        manifest["eligible_for_real_evaluation"] = False
        manifest["ineligibility_reason"] = "missing collector identity"
    if event_count < 1 or input_event_count < 1:
        manifest["eligible_for_real_evaluation"] = False
        manifest["ineligibility_reason"] = "missing usable input event"
    digest_kind = DIGEST_KIND_KEYED if signing_key else DIGEST_KIND_UNKEYED
    manifest["capture_manifest_digest_kind"] = digest_kind
    manifest["capture_manifest_sha256"] = manifest_digest(manifest, signing_key=signing_key)
    return manifest

def validate_manifest(manifest, *, require_raw=True, signing_key=None):
    errors = []
    if not isinstance(manifest, dict):
        return {"valid": False, "eligible": False, "errors": ["manifest is not an object"]}
    errors.extend(sorted(REQUIRED_FIELDS - set(manifest)))
    if manifest.get("schema") != SCHEMA:
        errors.append("invalid schema")
    if manifest.get("source_class") not in SOURCE_CLASSES:
        errors.append("unpermitted source class")
    for key in ("capture_id", "native_session_id", "collector_name", "collector_version", "collector_sha256", "deployment_id", "environment_id"):
        if not manifest.get(key):
            errors.append(f"missing {key}")
    try:
        started = _parse_timestamp(manifest.get("capture_started_at_utc"))
        ended = _parse_timestamp(manifest.get("capture_ended_at_utc"))
        if ended < started:
            errors.append("capture end precedes capture start")
    except (TypeError, ValueError) as exc:
        errors.append(str(exc))
    digest_kind = _manifest_digest_kind(manifest)
    if signing_key and digest_kind != DIGEST_KIND_KEYED:
        # A validator holding the signing key refuses unkeyed digests: the
        # owner of the files could otherwise strip the keyed marker, edit the
        # manifest and recompute a plain sha256 ("digest downgrade").
        errors.append("manifest digest is unkeyed; validator requires keyed digest")
    elif digest_kind == DIGEST_KIND_KEYED and not signing_key:
        # Fail closed: a keyed manifest cannot be verified without the key,
        # so an unkeyed recomputation must never be mistaken for a match.
        errors.append("manifest digest is keyed; signing key required to validate")
    else:
        expected_digest = manifest_digest(manifest, signing_key=signing_key if digest_kind == DIGEST_KIND_KEYED else None)
        if manifest.get("capture_manifest_sha256") != expected_digest:
            errors.append("manifest hash mismatch")
    raw_path = Path(manifest.get("raw_log_path", ""))
    if require_raw and not raw_path.is_file():
        errors.append("raw log missing")
    if raw_path.is_file():
        if sha256_file(raw_path) != manifest.get("raw_log_sha256"):
            errors.append("raw log hash mismatch")
        if raw_path.stat().st_size != manifest.get("raw_log_size_bytes"):
            errors.append("raw log size mismatch")
    flags = any(manifest.get(key) is True for key in ("synthetic", "replay", "test_fixture"))
    if flags and manifest.get("eligible_for_real_evaluation"):
        errors.append("eligible flag contradicts synthetic/replay/test_fixture capture")
    if manifest.get("input_event_count", 0) < 1:
        errors.append("missing usable input event")
    if manifest.get("eligible_for_real_evaluation") and errors:
        errors.append("eligible flag contradicts validation errors")
    eligible = bool(manifest.get("eligible_for_real_evaluation")) and not errors and not flags
    return {"valid": not errors, "eligible": eligible, "errors": sorted(set(errors))}
