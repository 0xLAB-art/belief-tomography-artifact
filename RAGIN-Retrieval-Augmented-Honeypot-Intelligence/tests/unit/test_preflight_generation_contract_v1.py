"""Focused, fully offline tests for ``scripts/preflight_generation_contract_v1.py``.

The runner is exercised against a loopback-only fixture bridge (127.0.0.1,
ephemeral port). No external endpoint, provider, credential, proxy, or bridge
process is used. A passing test proves runner bookkeeping only; it is not
evidence of model inference.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

# Defensive import-time guard: never inherit the repository's historical
# session-log directory or host-fiction file.
_SCRATCH = Path(tempfile.mkdtemp(prefix="ragin-preflight-v1-"))
os.environ.setdefault("RAGIN_SESSION_DIR", str(_SCRATCH / "sessions"))
os.environ.setdefault("RAGIN_HOST_FICTION_PATH", str(_SCRATCH / "host_fiction.json"))
Path(os.environ["RAGIN_SESSION_DIR"]).mkdir(parents=True, exist_ok=True)

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "scripts" / "preflight_generation_contract_v1.py"
BRIDGE_PATH = ROOT / "scripts" / "opencode_proxy.py"
SAFE_CONFIG_PATH = ROOT / "scripts" / "opencode_cli_bridge_safe_config.json"
REAL_PACKET = ROOT / "docs" / "research" / "generation_contract_v1" / "external_preflight_v1" / "REQUEST_MANIFEST.json"
MODEL = "opencode/deepseek-v4.1-flash-free"


def _load_runner() -> Any:
    spec = importlib.util.spec_from_file_location("preflight_generation_contract_v1", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


runner = _load_runner()


# ---------------------------------------------------------------------------
# loopback fixture bridge
# ---------------------------------------------------------------------------


class _FixtureHandler(BaseHTTPRequestHandler):
    server_version = "RAGIN-PreflightFixture/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _write(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        server = self.server
        server.get_count += 1
        if self.path != "/v1/models":
            self._write(404, b"{}")
            return
        self._write(server.models_status, server.models_body)

    def do_POST(self) -> None:
        server = self.server
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        server.post_bodies.append(self.rfile.read(length))
        index = server.post_count
        server.post_count += 1
        status, body = server.post_responses[min(index, len(server.post_responses) - 1)]
        self._write(status, body)


@contextlib.contextmanager
def _bridge(
    *,
    models_body: bytes | None = None,
    models_status: int = 200,
    post_responses: list[tuple[int, bytes]] | None = None,
) -> Iterator[ThreadingHTTPServer]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
    server.daemon_threads = True
    server.get_count = 0
    server.post_count = 0
    server.post_bodies = []
    server.models_status = models_status
    server.models_body = models_body if models_body is not None else _models([MODEL])
    server.post_responses = post_responses or [(200, _completion())]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _models(ids: list[str]) -> bytes:
    return json.dumps({"object": "list", "data": [{"id": item, "object": "model"} for item in ids]}).encode()


def _completion(content: str = "synthetic terminal output", *, model: str = MODEL, extra: dict[str, Any] | None = None) -> bytes:
    body: dict[str, Any] = {
        "id": "chatcmpl-fixture",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"completion_time_ms": 1.5},
    }
    if extra:
        body.update(extra)
    return json.dumps(body, separators=(",", ":")).encode()


# ---------------------------------------------------------------------------
# packet builders
# ---------------------------------------------------------------------------


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _immutable_rows() -> list[dict[str, Any]]:
    rows = []
    for role, path in (
        ("bridge", BRIDGE_PATH),
        ("safe_config", SAFE_CONFIG_PATH),
        ("runner", RUNNER_PATH),
    ):
        raw = path.read_bytes()
        rows.append(
            {
                "role": role,
                "path": str(path.relative_to(ROOT)),
                "sha256": _sha(raw),
                "bytes": len(raw),
            }
        )
    return rows


def _payload_bytes(name: str, max_tokens: int) -> bytes:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Synthetic lab fixture. Return plain text only."},
            {"role": "user", "content": f"Synthetic request {name}. Return raw terminal output only."},
        ],
        "max_tokens": max_tokens,
    }
    return json.dumps(payload, separators=(",", ":")).encode()


def _manifest(port: int, payload_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": runner.PACKET_SCHEMA,
        "packet_version": runner.PACKET_VERSION,
        "proposed_model_only": MODEL,
        "alternative_models_allowed": False,
        "paid_fallback_allowed": False,
        "approval_token_required": True,
        "approval_binding": runner.APPROVAL_BINDING,
        "immutable_sources": _immutable_rows(),
        "transport": {
            "host": "127.0.0.1",
            "port": port,
            "endpoint": f"http://127.0.0.1:{port}/v1/chat/completions",
            "contract_compatible": False,
            "model_identity_attestation": "BRIDGE_ECHO_ONLY",
            "decoding_attestation": "UNSUPPORTED",
        },
        "request_budget": {
            "max_http_generation_requests": 4,
            "retries_per_request": 0,
        },
        "decoding": {
            "temperature": "UNSUPPORTED_NOT_SENT",
            "top_p": "UNSUPPORTED_NOT_SENT",
            "seed": "UNSUPPORTED_NOT_SENT",
        },
        "payloads": payload_rows,
    }


def _seal(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest["packet_sha256"] = runner.canonical_manifest_sha256(manifest)
    return manifest


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _build_packet(tmp_path: Path, port: int, names: tuple[str, ...] = ("req_01.json",)) -> tuple[Path, dict[str, Any]]:
    packet_dir = tmp_path / "packet"
    payload_dir = packet_dir / "payloads"
    payload_dir.mkdir(parents=True)
    rows = []
    for index, name in enumerate(names, start=1):
        raw = _payload_bytes(name, 16 + index)
        (payload_dir / name).write_bytes(raw)
        rows.append(
            {
                "name": name,
                "path": f"payloads/{name}",
                "sha256": _sha(raw),
                "bytes": len(raw),
                "max_tokens": 16 + index,
            }
        )
    manifest = _seal(_manifest(port, rows))
    packet_path = packet_dir / "REQUEST_MANIFEST.json"
    _write_json(packet_path, manifest)
    return packet_path, manifest


def _run(mode: str, packet: Path, *extra: str) -> int:
    return runner.main([mode, "--packet", str(packet), *extra])


def _receipt(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# packet validation / tamper tests (offline, no bridge)
# ---------------------------------------------------------------------------


def test_real_packet_dry_run_is_ready(capsys: Any) -> None:
    assert REAL_PACKET.is_file()
    assert _run("--dry-run", REAL_PACKET) == 0
    out = capsys.readouterr()
    manifest = json.loads(REAL_PACKET.read_text(encoding="utf-8"))
    assert "PREFLIGHT_DRY_RUN_OK" in out.out
    assert f"packet_sha256={manifest['packet_sha256']}" in out.out
    assert "provider_calls=0" in out.out
    assert "generation_requests=4" in out.out


def test_manifest_tamper_rejected(tmp_path: Path, capsys: Any) -> None:
    with _bridge() as bridge:
        packet, manifest = _build_packet(tmp_path, bridge.server_address[1])
    manifest["expected_provider_cost_usd"] = 1
    _write_json(packet, manifest)  # digest intentionally not resealed
    assert _run("--dry-run", packet) == 2
    assert "digest mismatch" in capsys.readouterr().err


def test_payload_tamper_rejected(tmp_path: Path, capsys: Any) -> None:
    with _bridge() as bridge:
        packet, _ = _build_packet(tmp_path, bridge.server_address[1])
    payload = packet.parent / "payloads" / "req_01.json"
    payload.write_bytes(payload.read_bytes().replace(b"req_01", b"req_XX"))
    assert _run("--dry-run", packet) == 2
    assert "payload hash mismatch" in capsys.readouterr().err


def test_source_tamper_rejected(tmp_path: Path, capsys: Any) -> None:
    with _bridge() as bridge:
        packet, manifest = _build_packet(tmp_path, bridge.server_address[1])
    manifest["immutable_sources"][0]["sha256"] = "0" * 64
    _write_json(packet, _seal(manifest))
    assert _run("--dry-run", packet) == 2
    assert "immutable source hash mismatch" in capsys.readouterr().err


def test_missing_immutable_sources_rejected(tmp_path: Path, capsys: Any) -> None:
    with _bridge() as bridge:
        packet, manifest = _build_packet(tmp_path, bridge.server_address[1])
    manifest.pop("immutable_sources")
    _write_json(packet, _seal(manifest))
    assert _run("--dry-run", packet) == 2
    assert "immutable_sources is missing" in capsys.readouterr().err


def test_non_loopback_endpoint_rejected_even_when_resealed(tmp_path: Path, capsys: Any) -> None:
    with _bridge() as bridge:
        packet, manifest = _build_packet(tmp_path, bridge.server_address[1])
    manifest["transport"]["host"] = "10.1.2.3"
    manifest["transport"]["endpoint"] = "http://10.1.2.3:8731/v1/chat/completions"
    _write_json(packet, _seal(manifest))
    assert _run("--dry-run", packet) == 2
    assert "not loopback" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# execute-path tests against the loopback fixture
# ---------------------------------------------------------------------------


def test_no_approval_means_no_http(tmp_path: Path, capsys: Any) -> None:
    with _bridge() as bridge:
        packet, _ = _build_packet(tmp_path, bridge.server_address[1])
        output = tmp_path / "run.json"
        assert _run("--execute", packet, "--approval-sha256", "0" * 64, "--output", str(output)) == 2
        assert bridge.get_count == 0
        assert bridge.post_count == 0
    assert "PREFLIGHT_NOT_APPROVED" in capsys.readouterr().err
    assert not output.exists()


def test_success_preserves_exact_bytes_and_raw_bodies(tmp_path: Path) -> None:
    with _bridge(post_responses=[(200, _completion())]) as bridge:
        packet, manifest = _build_packet(tmp_path, bridge.server_address[1], ("req_01.json", "req_02.json"))
        output = tmp_path / "run.json"
        assert _run("--execute", packet, "--approval-sha256", manifest["packet_sha256"], "--output", str(output)) == 0
        assert bridge.get_count == 1
        assert bridge.post_count == 2
        sent = [row["path"].rsplit("/", 1)[-1] for row in manifest["payloads"]]
        for index, name in enumerate(sent):
            frozen = (packet.parent / "payloads" / name).read_bytes()
            assert bridge.post_bodies[index] == frozen

    receipt = _receipt(output)
    assert receipt["status"] == "COMPLETED"
    assert receipt["http_generation_requests_sent"] == 2
    assert receipt["retries"] == 0
    assert receipt["contract_compatible"] is False
    assert receipt["cost_usd"] is None
    assert receipt["cost_availability"] == "NOT_ATTESTED"
    raw_dir = output.parent / f"{output.name}.raw"
    assert (raw_dir / "models.body").is_file()
    for index, request in enumerate(receipt["requests"], start=1):
        raw_path = raw_dir / f"resp_{index:02d}_req_0{index}.body"
        assert raw_path.is_file()
        assert request["raw_body_sha256"] == _sha(raw_path.read_bytes())
        assert request["model_identity_status"] == "BRIDGE_ECHO_ONLY"


def test_failed_post_counts_attempt_one_and_preserves_raw(tmp_path: Path) -> None:
    with _bridge(post_responses=[(500, b'{"error":{"type":"fixture_failure"}}')]) as bridge:
        packet, manifest = _build_packet(tmp_path, bridge.server_address[1])
        output = tmp_path / "run.json"
        assert _run("--execute", packet, "--approval-sha256", manifest["packet_sha256"], "--output", str(output)) == 2
        assert bridge.post_count == 1  # exactly one attempt, no retry
    receipt = _receipt(output)
    assert receipt["http_generation_requests_sent"] == 1
    assert receipt["requests"][0]["attempt"] == 1
    assert receipt["abort_reason"].startswith("REQUEST_FAILED")
    raw = output.parent / f"{output.name}.raw" / "resp_01_req_01.body"
    assert raw.read_bytes() == b'{"error":{"type":"fixture_failure"}}'
    assert receipt["requests"][0]["raw_body_sha256"] == _sha(raw.read_bytes())


def test_non_json_response_aborts_and_preserves_raw(tmp_path: Path) -> None:
    with _bridge(post_responses=[(200, b"this is not json")]) as bridge:
        packet, manifest = _build_packet(tmp_path, bridge.server_address[1])
        output = tmp_path / "run.json"
        assert _run("--execute", packet, "--approval-sha256", manifest["packet_sha256"], "--output", str(output)) == 2
    receipt = _receipt(output)
    assert receipt["abort_reason"] == "NON_JSON_RESPONSE"
    raw = output.parent / f"{output.name}.raw" / "resp_01_req_01.body"
    assert raw.read_bytes() == b"this is not json"
    assert receipt["requests"][0]["raw_body_sha256"] == _sha(b"this is not json")


def test_malformed_json_shape_aborts(tmp_path: Path) -> None:
    with _bridge(post_responses=[(200, b'{"choices":[]}')]) as bridge:
        packet, manifest = _build_packet(tmp_path, bridge.server_address[1])
        output = tmp_path / "run.json"
        assert _run("--execute", packet, "--approval-sha256", manifest["packet_sha256"], "--output", str(output)) == 2
    assert _receipt(output)["abort_reason"] == "MALFORMED_RESPONSE_SHAPE"


def test_zero_cost_signal_passes(tmp_path: Path) -> None:
    with _bridge(post_responses=[(200, _completion(extra={"cost_usd": 0}))]) as bridge:
        packet, manifest = _build_packet(tmp_path, bridge.server_address[1])
        output = tmp_path / "run.json"
        assert _run("--execute", packet, "--approval-sha256", manifest["packet_sha256"], "--output", str(output)) == 0
    assert _receipt(output)["status"] == "COMPLETED"


def test_explicit_cost_signal_aborts_before_further_requests(tmp_path: Path) -> None:
    with _bridge(post_responses=[(200, _completion(extra={"cost_usd": 0.01}))]) as bridge:
        packet, manifest = _build_packet(tmp_path, bridge.server_address[1], ("req_01.json", "req_02.json"))
        output = tmp_path / "run.json"
        assert _run("--execute", packet, "--approval-sha256", manifest["packet_sha256"], "--output", str(output)) == 2
        assert bridge.post_count == 1
    receipt = _receipt(output)
    assert receipt["abort_reason"] == "OBSERVED_COST_OR_PAID_ROUTE_SIGNAL"
    assert receipt["requests"][0]["cost_signal_path"] == "cost_usd"
    assert receipt["cost_availability"] == "NOT_ATTESTED"


def test_allowlist_mismatch_aborts_before_post(tmp_path: Path) -> None:
    with _bridge(models_body=_models([MODEL, "opencode/paid-model"])) as bridge:
        packet, manifest = _build_packet(tmp_path, bridge.server_address[1])
        output = tmp_path / "run.json"
        assert _run("--execute", packet, "--approval-sha256", manifest["packet_sha256"], "--output", str(output)) == 2
        assert bridge.get_count == 1
        assert bridge.post_count == 0
    receipt = _receipt(output)
    assert receipt["abort_reason"] == "BRIDGE_ALLOWLIST_MISMATCH"
    assert receipt["http_generation_requests_sent"] == 0


def test_existing_receipt_is_not_overwritten(tmp_path: Path, capsys: Any) -> None:
    with _bridge() as bridge:
        packet, manifest = _build_packet(tmp_path, bridge.server_address[1])
        output = tmp_path / "run.json"
        output.write_text("old receipt\n", encoding="utf-8")
        assert _run("--execute", packet, "--approval-sha256", manifest["packet_sha256"], "--output", str(output)) == 2
        assert bridge.get_count == 0
        assert bridge.post_count == 0
    assert output.read_text(encoding="utf-8") == "old receipt\n"
    assert "PREFLIGHT_OUTPUT_EXISTS" in capsys.readouterr().err


def test_existing_raw_namespace_is_not_overwritten(tmp_path: Path, capsys: Any) -> None:
    with _bridge() as bridge:
        packet, manifest = _build_packet(tmp_path, bridge.server_address[1])
        output = tmp_path / "run.json"
        raw_dir = output.parent / f"{output.name}.raw"
        raw_dir.mkdir()
        (raw_dir / "old.body").write_bytes(b"old")
        assert _run("--execute", packet, "--approval-sha256", manifest["packet_sha256"], "--output", str(output)) == 2
        assert bridge.get_count == 0
        assert bridge.post_count == 0
        assert (raw_dir / "old.body").read_bytes() == b"old"
        assert not output.exists()
    assert "PREFLIGHT_OUTPUT_EXISTS" in capsys.readouterr().err
