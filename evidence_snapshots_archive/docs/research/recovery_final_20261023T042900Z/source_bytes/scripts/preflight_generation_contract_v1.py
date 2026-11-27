#!/usr/bin/env python3
"""Bounded external-preflight runner for the RAGIN generation contract v1.

This runner is intentionally small. It does not start a bridge, proxy, server,
or model. It validates the frozen packet and, only when explicitly approved,
sends the packet's payloads to an *already running* loopback OpenCode CLI bridge.

It is NOT a decoding-controlled transport. The existing bridge does not pass
temperature/top_p/seed to the CLI, and ``max_tokens`` is prompt text only. The
runner therefore records ``contract_compatible: false`` and
``model_identity_status: BRIDGE_ECHO_ONLY`` and must never be used for B1-B3
treatment generation.

Dry-run is offline and is the only supported review mode until a human approval
record exists. ``--execute`` requires a digest over the entire canonical
manifest (excluding the digest field itself) and re-checks every payload byte
and the bridge/config/runner source hashes immediately before any transport
object is created. The manifest embeds the runner hash; the runner never embeds
the manifest digest, so this binding is one-way and not circular.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACKET_SCHEMA = "ragin.external_preflight.packet.v1"
PACKET_VERSION = "external-preflight-v1"
PROPOSED_MODEL = "opencode/deepseek-v4.1-flash-free"
MAX_HTTP_GENERATION_REQUESTS = 4
ALLOWED_PAYLOAD_KEYS = {"model", "messages", "max_tokens"}
SAFE_CONFIG = Path("scripts/opencode_cli_bridge_safe_config.json")
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
APPROVAL_DIGEST_FIELD = "packet_sha256"
APPROVAL_BINDING = "SHA256_OF_CANONICAL_MANIFEST_EXCLUDING_PACKET_SHA256"
REQUIRED_IMMUTABLE_SOURCES = {
    "bridge": "scripts/opencode_proxy.py",
    "safe_config": "scripts/opencode_cli_bridge_safe_config.json",
    "runner": "scripts/preflight_generation_contract_v1.py",
}
_COST_KEYS = frozenset(
    {
        "billed",
        "billing",
        "charge",
        "charged",
        "cost",
        "cost_usd",
        "credits",
        "credits_used",
        "invoice",
        "paid",
        "price",
        "quota",
    }
)

# A small, explicit secret-looking-value screen for the frozen payload bytes.
_SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ASIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\b(api[_-]?key|secret|password|token)\s*[:=]\s*\S{8,}"),
    re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"),  # avoids shipping real addresses
)


class PacketError(RuntimeError):
    """The packet is malformed, tampered with, or unsafe to send."""


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_manifest_sha256(manifest: dict[str, Any]) -> str:
    """Hash the entire canonical manifest except the approval digest field.

    The digest therefore binds route, model, request budget, decoding claims,
    data-sharing flags, tool-denial metadata, payload hashes, and immutable
    source hashes. Canonical JSON is sorted-key, compact, UTF-8.
    """

    body = dict(manifest)
    body.pop(APPROVAL_DIGEST_FIELD, None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_immutable_sources(manifest: dict[str, Any], root: Path) -> None:
    rows = manifest.get("immutable_sources")
    if not isinstance(rows, list):
        raise PacketError("immutable_sources is missing")
    by_role: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("role"), str):
            raise PacketError("immutable source row is malformed")
        role = row["role"]
        if role in by_role:
            raise PacketError(f"immutable source role is duplicated: {role}")
        by_role[role] = row
    missing = set(REQUIRED_IMMUTABLE_SOURCES) - set(by_role)
    if missing:
        raise PacketError("immutable source coverage is incomplete")
    for role, expected_path in REQUIRED_IMMUTABLE_SOURCES.items():
        row = by_role[role]
        if row.get("path") != expected_path:
            raise PacketError(f"immutable source path mismatch: {role}")
        expected_sha = row.get("sha256")
        expected_bytes = row.get("bytes")
        if not isinstance(expected_sha, str) or not isinstance(expected_bytes, int):
            raise PacketError(f"immutable source record is malformed: {role}")
        path = root / expected_path
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise PacketError(f"immutable source is unreadable: {role}") from exc
        if len(raw) != expected_bytes:
            raise PacketError(f"immutable source byte count mismatch: {role}")
        if hashlib.sha256(raw).hexdigest() != expected_sha:
            raise PacketError(f"immutable source hash mismatch: {role}")


def _response_content(body: Any) -> tuple[str | None, str | None]:
    """Return ``(content, error)`` with a stable error for malformed shapes."""

    if not isinstance(body, dict):
        return None, "MALFORMED_RESPONSE_BODY"
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        return None, "MALFORMED_RESPONSE_SHAPE"
    choice = choices[0]
    if not isinstance(choice, dict):
        return None, "MALFORMED_RESPONSE_SHAPE"
    message = choice.get("message")
    if not isinstance(message, dict):
        return None, "MALFORMED_RESPONSE_SHAPE"
    content = message.get("content")
    if not isinstance(content, str):
        return None, "MALFORMED_RESPONSE_CONTENT"
    return content, None


def _is_cost_signal(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "0.0", "free", "none", "false", "no"}
    if isinstance(value, (dict, list)):
        return bool(value)
    return True


def _find_cost_signal(value: Any, path: str = "") -> str | None:
    """Find explicit known billing/cost/quota fields; hidden charges are unseen."""

    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text.lower() in _COST_KEYS and _is_cost_signal(child):
                return child_path
            found = _find_cost_signal(child, child_path)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = _find_cost_signal(child, f"{path}[{index}]")
            if found is not None:
                return found
    return None


def _store_raw_body(raw_dir: Path, stem: str, body: bytes) -> dict[str, Any]:
    path = raw_dir / f"{stem}.body"
    with open(path, "xb") as handle:
        handle.write(body)
    return {
        "raw_body_path": str(path),
        "raw_body_sha256": hashlib.sha256(body).hexdigest(),
        "raw_body_bytes": len(body),
    }


def _validate_safe_config(root: Path) -> None:
    path = root / SAFE_CONFIG
    if not path.is_file():
        raise PacketError("safe OpenCode agent configuration is missing")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PacketError("safe OpenCode agent configuration is not valid JSON") from exc
    agent = (config.get("agent") or {}).get("ragin-safe")
    if not isinstance(agent, dict):
        raise PacketError("safe agent 'ragin-safe' is not configured")
    tools = agent.get("tools")
    if not isinstance(tools, dict) or tools.get("*") is not False:
        raise PacketError("safe agent does not deny all tools")
    permissions = agent.get("permission")
    if not isinstance(permissions, dict) or permissions.get("*") != "deny":
        raise PacketError("safe agent does not deny all permissions")


def load_and_validate(packet_path: Path, root: Path) -> tuple[dict[str, Any], list[tuple[dict[str, Any], bytes]]]:
    try:
        manifest = json.loads(packet_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PacketError("packet manifest is unreadable or invalid JSON") from exc
    if not isinstance(manifest, dict):
        raise PacketError("packet manifest is not a JSON object")
    if manifest.get("schema") != PACKET_SCHEMA:
        raise PacketError("unexpected packet schema")
    if manifest.get("packet_version") != PACKET_VERSION:
        raise PacketError("unexpected packet version")
    if manifest.get("proposed_model_only") != PROPOSED_MODEL:
        raise PacketError("packet proposes an unapproved model")
    if manifest.get("alternative_models_allowed") is not False:
        raise PacketError("packet permits alternative models")
    if manifest.get("paid_fallback_allowed") is not False:
        raise PacketError("packet permits a paid fallback")
    if manifest.get("approval_token_required") is not True:
        raise PacketError("packet must require an approval token")
    if manifest.get("approval_binding") != APPROVAL_BINDING:
        raise PacketError("packet approval binding is not canonical-manifest-wide")
    if manifest.get("packet_sha256") != canonical_manifest_sha256(manifest):
        raise PacketError("packet digest mismatch")
    transport = manifest.get("transport")
    if not isinstance(transport, dict):
        raise PacketError("transport is missing or malformed")
    if transport.get("contract_compatible") is not False:
        raise PacketError("packet must state contract_compatible=false for this bridge")
    if transport.get("model_identity_attestation") != "BRIDGE_ECHO_ONLY":
        raise PacketError("packet must mark model identity as BRIDGE_ECHO_ONLY")
    if transport.get("decoding_attestation") != "UNSUPPORTED":
        raise PacketError("packet must mark decoding attestation as UNSUPPORTED")
    # Validate loopback binding during dry-run too, not only before transport.
    _loopback_endpoint(transport)

    budget = manifest.get("request_budget")
    if not isinstance(budget, dict):
        raise PacketError("request budget is missing or malformed")
    max_requests = budget.get("max_http_generation_requests")
    retries = budget.get("retries_per_request")
    if max_requests != MAX_HTTP_GENERATION_REQUESTS or retries != 0:
        raise PacketError("request budget must be exactly 4 requests and 0 retries")

    decoding = manifest.get("decoding")
    if not isinstance(decoding, dict):
        raise PacketError("decoding block is missing or malformed")
    if decoding.get("temperature") != "UNSUPPORTED_NOT_SENT":
        raise PacketError("packet must not imply temperature support")
    if decoding.get("top_p") != "UNSUPPORTED_NOT_SENT":
        raise PacketError("packet must not imply top_p support")
    if decoding.get("seed") != "UNSUPPORTED_NOT_SENT":
        raise PacketError("packet must not imply seed support")

    rows = manifest.get("payloads")
    if not isinstance(rows, list) or not rows:
        raise PacketError("packet has no payloads")
    if len(rows) > MAX_HTTP_GENERATION_REQUESTS:
        raise PacketError("packet exceeds the hard request cap")

    packet_hashes: dict[str, str] = {}
    payloads: list[tuple[dict[str, Any], bytes]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise PacketError("payload row is malformed")
        name = row.get("name")
        rel = row.get("path")
        expected_sha = row.get("sha256")
        expected_bytes = row.get("bytes")
        if not isinstance(name, str) or not isinstance(rel, str) or not isinstance(expected_sha, str):
            raise PacketError("payload row is malformed")
        if name in packet_hashes:
            raise PacketError(f"payload name is duplicated: {name}")
        if Path(rel).name != name:
            raise PacketError("payload name/path mismatch")
        path = packet_path.parent / rel
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise PacketError(f"payload is unreadable: {name}") from exc
        if hashlib.sha256(raw).hexdigest() != expected_sha:
            raise PacketError(f"payload hash mismatch: {name}")
        if len(raw) != expected_bytes:
            raise PacketError(f"payload byte count mismatch: {name}")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise PacketError(f"payload is not valid JSON: {name}") from exc
        if not isinstance(payload, dict):
            raise PacketError(f"payload is not a JSON object: {name}")
        extra = set(payload) - ALLOWED_PAYLOAD_KEYS
        if extra:
            raise PacketError(f"payload carries unsupported fields: {name}")
        if payload.get("model") != PROPOSED_MODEL:
            raise PacketError(f"payload model is not the approved model: {name}")
        if not isinstance(payload.get("messages"), list) or not payload["messages"]:
            raise PacketError(f"payload has no messages: {name}")
        if not isinstance(payload.get("max_tokens"), int) or payload["max_tokens"] < 1:
            raise PacketError(f"payload max_tokens is invalid: {name}")
        text = raw.decode("utf-8")
        for pattern in _SECRET_PATTERNS:
            if pattern.search(text):
                raise PacketError(f"payload contains a forbidden secret/address pattern: {name}")
        packet_hashes[name] = expected_sha
        payloads.append((row, raw))

    _validate_immutable_sources(manifest, root)
    _validate_safe_config(root)
    return manifest, payloads


def _loopback_endpoint(transport: dict[str, Any]) -> str:
    host = str(transport.get("host", ""))
    port = transport.get("port")
    endpoint = str(transport.get("endpoint", ""))
    if host not in LOOPBACK_HOSTS:
        raise PacketError("bridge host is not loopback")
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise PacketError("bridge port is invalid")
    expected = f"http://{host}:{port}/v1/chat/completions"
    if endpoint != expected:
        raise PacketError("bridge endpoint does not match the loopback host/port")
    return endpoint


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _execute(manifest: dict[str, Any], payloads: list[tuple[dict[str, Any], bytes]], output: Path) -> int:
    import requests  # lazy: dry-run must not require or exercise transport

    endpoint = _loopback_endpoint(manifest["transport"])
    base = endpoint.rsplit("/v1/chat/completions", 1)[0]
    session = requests.Session()
    session.trust_env = False

    raw_dir = output.parent / f"{output.name}.raw"
    try:
        raw_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    except FileExistsError:
        print("PREFLIGHT_OUTPUT_EXISTS: raw response namespace already exists", file=sys.stderr)
        return 2

    receipt: dict[str, Any] = {
        "schema": "ragin.external_preflight.receipt.v1",
        "packet_sha256": manifest["packet_sha256"],
        "started_utc": _now(),
        "raw_response_dir": str(raw_dir),
        "contract_compatible": False,
        "decoding_attestation": "UNSUPPORTED",
        "model_identity_status": "BRIDGE_ECHO_ONLY",
        "cost_usd": None,
        "cost_availability": "NOT_ATTESTED",
        "cost_observability": {
            "explicit_known_fields_checked": sorted(_COST_KEYS),
            "hidden_charges_detectable": False,
            "cost_abort_scope": "EXPLICIT_KNOWN_FIELDS_ONLY",
        },
        "http_generation_requests_sent": 0,
        "retries": 0,
        "budget_scope": "HTTP_PREFLIGHT_ONLY_NOT_EXPERIMENT_SESSION_BUDGET",
        "cli_internal_retries_attested": False,
        "upstream_provider_call_count_attested": False,
        "native_retry_layers_in_scope": False,
        "status": "ABORTED",
        "requests": [],
    }

    # A single local metadata GET is not a model-generation request. Its raw
    # body is still preserved so an allowlist mismatch is reviewable.
    try:
        models_resp = session.get(f"{base}/v1/models", timeout=10, allow_redirects=False)
        models_raw_bytes = models_resp.content
        if isinstance(models_raw_bytes, str):
            models_raw_bytes = models_raw_bytes.encode("utf-8")
        if not isinstance(models_raw_bytes, bytes):
            raise TypeError("response content is not bytes")
        receipt["models_response"] = _store_raw_body(raw_dir, "models", models_raw_bytes)
    except Exception as exc:  # noqa: BLE001 - receipt must record a stable reason
        receipt["abort_reason"] = f"BRIDGE_MODELS_UNAVAILABLE:{type(exc).__name__}"
        _write_receipt(output, receipt)
        return 2
    try:
        models_resp.raise_for_status()
        models_payload = models_resp.json()
        models_data = models_payload.get("data") if isinstance(models_payload, dict) else None
        if not isinstance(models_data, list):
            raise ValueError("models payload has no data list")
        listed = [item.get("id") if isinstance(item, dict) else None for item in models_data]
    except Exception as exc:  # noqa: BLE001 - stable abort, never a raw parser traceback
        receipt["abort_reason"] = f"BRIDGE_MODELS_MALFORMED:{type(exc).__name__}"
        _write_receipt(output, receipt)
        return 2
    if listed != [PROPOSED_MODEL]:
        receipt["abort_reason"] = "BRIDGE_ALLOWLIST_MISMATCH"
        receipt["listed_models"] = listed
        _write_receipt(output, receipt)
        return 2
    receipt["listed_models"] = listed

    for index, (row, raw) in enumerate(payloads, start=1):
        if receipt["http_generation_requests_sent"] >= MAX_HTTP_GENERATION_REQUESTS:
            receipt["abort_reason"] = "REQUEST_CAP_REACHED"
            _write_receipt(output, receipt)
            return 2
        # Count the attempt BEFORE the transport call. A failed POST still
        # consumed one attempt and must not be reported as zero.
        receipt["http_generation_requests_sent"] += 1
        entry: dict[str, Any] = {
            "index": index,
            "name": row["name"],
            "request_sha256": row["sha256"],
            "attempt": receipt["http_generation_requests_sent"],
            "sent_utc": _now(),
        }
        try:
            response = session.post(
                endpoint,
                data=raw,
                headers={"Content-Type": "application/json"},
                timeout=120,
                allow_redirects=False,
            )
        except Exception as exc:  # noqa: BLE001 - one attempt only, then abort
            entry["error"] = type(exc).__name__
            receipt["requests"].append(entry)
            receipt["abort_reason"] = f"REQUEST_FAILED:{type(exc).__name__}"
            _write_receipt(output, receipt)
            return 2

        try:
            raw_response_bytes = response.content
            if isinstance(raw_response_bytes, str):
                raw_response_bytes = raw_response_bytes.encode("utf-8")
            if not isinstance(raw_response_bytes, bytes):
                raise TypeError("response content is not bytes")
            entry.update(_store_raw_body(raw_dir, f"resp_{index:02d}_{Path(row['name']).stem}", raw_response_bytes))
        except Exception as exc:  # noqa: BLE001 - no silent loss of the response
            entry["raw_body_capture_error"] = type(exc).__name__
            receipt["requests"].append(entry)
            receipt["abort_reason"] = f"RAW_BODY_CAPTURE_FAILED:{type(exc).__name__}"
            _write_receipt(output, receipt)
            return 2

        entry["http_status"] = getattr(response, "status_code", None)
        try:
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001 - body is already preserved above
            entry["error"] = type(exc).__name__
            receipt["requests"].append(entry)
            receipt["abort_reason"] = f"REQUEST_FAILED:{type(exc).__name__}"
            _write_receipt(output, receipt)
            return 2

        try:
            body = response.json()
        except Exception as exc:  # noqa: BLE001 - non-JSON body is already preserved
            entry["json_parse_error"] = type(exc).__name__
            receipt["requests"].append(entry)
            receipt["abort_reason"] = "NON_JSON_RESPONSE"
            _write_receipt(output, receipt)
            return 2

        cost_path = _find_cost_signal(body)
        if cost_path is not None:
            entry["cost_signal_path"] = cost_path
            receipt["requests"].append(entry)
            receipt["abort_reason"] = "OBSERVED_COST_OR_PAID_ROUTE_SIGNAL"
            _write_receipt(output, receipt)
            return 2

        if isinstance(body, dict) and "error" in body:
            entry["error"] = "PROVIDER_ERROR_OBJECT"
            receipt["requests"].append(entry)
            receipt["abort_reason"] = "PROVIDER_ERROR_OBJECT"
            _write_receipt(output, receipt)
            return 2

        content, shape_error = _response_content(body)
        if shape_error is not None:
            entry["error"] = shape_error
            receipt["requests"].append(entry)
            receipt["abort_reason"] = shape_error
            _write_receipt(output, receipt)
            return 2

        echo_model = body.get("model") if isinstance(body, dict) else None
        if not isinstance(echo_model, str):
            entry["error"] = "MALFORMED_RESPONSE_MODEL"
            receipt["requests"].append(entry)
            receipt["abort_reason"] = "MALFORMED_RESPONSE_MODEL"
            _write_receipt(output, receipt)
            return 2

        entry.update(
            {
                "bridge_echo_model": echo_model,
                "model_identity_status": "BRIDGE_ECHO_ONLY",
                "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "content_chars": len(content),
                "content_received": bool(content),
                "usage": body.get("usage") if isinstance(body, dict) else None,
            }
        )
        receipt["requests"].append(entry)
        if echo_model != PROPOSED_MODEL:
            receipt["abort_reason"] = "MODEL_ECHO_MISMATCH"
            _write_receipt(output, receipt)
            return 2
        if not content.strip():
            receipt["abort_reason"] = "EMPTY_CONTENT"
            _write_receipt(output, receipt)
            return 2

    receipt["status"] = "COMPLETED"
    receipt["finished_utc"] = _now()
    _write_receipt(output, receipt)
    return 0


def _write_receipt(output: Path, receipt: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "x", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="validate the packet offline; never sends")
    mode.add_argument("--execute", action="store_true", help="send frozen payloads to a running loopback bridge")
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--approval-sha256", default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    packet_path = args.packet.resolve()
    try:
        manifest, payloads = load_and_validate(packet_path, root)
    except PacketError as exc:
        print(f"PREFLIGHT_PACKET_REJECTED: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print("PREFLIGHT_DRY_RUN_OK")
        print(f"packet_sha256={manifest['packet_sha256']}")
        print(f"approval_binding={manifest['approval_binding']}")
        print(f"immutable_sources={len(manifest['immutable_sources'])}")
        print(f"model={manifest['proposed_model_only']}")
        print(f"generation_requests={len(payloads)}")
        print(f"retries={manifest['request_budget']['retries_per_request']}")
        print("contract_compatible=false")
        print("decoding_attestation=UNSUPPORTED")
        print("model_identity_status=BRIDGE_ECHO_ONLY")
        print("provider_calls=0")
        return 0

    if args.approval_sha256 != manifest["packet_sha256"]:
        print("PREFLIGHT_NOT_APPROVED: --approval-sha256 does not match the packet", file=sys.stderr)
        return 2
    if args.output is None:
        print("PREFLIGHT_OUTPUT_REQUIRED: --output is required for --execute", file=sys.stderr)
        return 2
    if args.output.exists():
        print("PREFLIGHT_OUTPUT_EXISTS: refusing to overwrite an existing receipt", file=sys.stderr)
        return 2

    # Re-read and re-hash every payload and immutable source immediately before
    # any transport object is constructed. This is still fully offline.
    try:
        rechecked, rechecked_payloads = load_and_validate(packet_path, root)
    except PacketError as exc:
        print(f"PREFLIGHT_SOURCE_RECHECK_REJECTED: {exc}", file=sys.stderr)
        return 2
    if rechecked["packet_sha256"] != args.approval_sha256:
        print("PREFLIGHT_SOURCE_RECHECK_REJECTED: packet digest changed", file=sys.stderr)
        return 2
    try:
        return _execute(rechecked, rechecked_payloads, args.output)
    except PacketError as exc:
        print(f"PREFLIGHT_EXECUTION_REJECTED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
