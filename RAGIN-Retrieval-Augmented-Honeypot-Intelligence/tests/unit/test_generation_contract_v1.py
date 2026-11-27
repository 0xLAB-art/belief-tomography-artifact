"""Focused tests for the opt-in generation/decoding and model-exposure contract.

Everything here is offline:

* config resolution/validation is pure local computation;
* HTTP tests use ``monkeypatch`` on ``requests.post`` or a loopback fixture
  explicitly labelled ``MOCKED_PROVIDER_INTEGRATION``;
* no external provider, model, credential, or paid service is contacted.

A passing test is NOT evidence of model inference. It only proves that the
configured payload/digest/metadata plumbing behaves as documented.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

# Defensive import-time guard: these focused tests must never inherit the
# repository's historical session-log directory or host-fiction file, even if a
# broad pytest collection imports this module first. The supported invocation is
# still a fresh interpreter with both variables exported before imports.
_TEST_SCRATCH = Path(tempfile.mkdtemp(prefix="ragin-gencontract-v1-"))
os.environ.setdefault("RAGIN_SESSION_DIR", str(_TEST_SCRATCH / "sessions"))
os.environ.setdefault("RAGIN_HOST_FICTION_PATH", str(_TEST_SCRATCH / "host_fiction.json"))
Path(os.environ["RAGIN_SESSION_DIR"]).mkdir(parents=True, exist_ok=True)

from ragin.cycle.provider_transport import ProviderTransport, _safe_endpoint  # noqa: E402
from ragin.gateway.client import GatewayClient  # noqa: E402
from ragin.gateway.generation import (  # noqa: E402
    CONTRACT_VERSION,
    OBSERVATION_SCHEMA,
    SEED_EXPLICIT,
    SEED_OMITTED,
    SEED_UNSUPPORTED,
    GenerationConfig,
    GenerationConfigError,
    require_model_exposure,
    resolve_generation_config,
)
from ragin.hisoka.deceiver import AdaptiveDeceiver  # noqa: E402
from ragin.hisoka.deception import ResponseGenerator  # noqa: E402

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _valid_env(**overrides: str) -> dict[str, str]:
    env = {
        "RAGIN_GENERATION_CONTRACT": "1",
        "RAGIN_GEN_MODEL": "lab/mock-model",
        "RAGIN_GEN_TEMPERATURE": "0.0",
        "RAGIN_GEN_MAX_TOKENS": "64",
        "RAGIN_GEN_TOP_P": "0.95",
        "RAGIN_GEN_SEED": "7",
        "RAGIN_GEN_MAX_RETRIES": "0",
    }
    env.update(overrides)
    return env


def _cfg(**overrides: Any) -> GenerationConfig:
    values: dict[str, Any] = {
        "model": "lab/mock-model",
        "temperature": 0.0,
        "max_tokens": 64,
        "top_p": 0.95,
        "seed": 7,
        "seed_status": SEED_EXPLICIT,
        "max_retries": 0,
    }
    values.update(overrides)
    return GenerationConfig(**values)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class _FakeResponse:
    status_code = 200
    reason = "OK"

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        return None


def _completion(content: str, *, model: str = "lab/mock-model") -> dict[str, Any]:
    return {
        "id": "chatcmpl-offline-test",
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16},
    }


class _FakeGateway:
    """Fills the same observation shape the real GatewayClient fills."""

    def __init__(self, draft: str = "release-2026.09.30\nbuild 1042\n", *, error: Exception | None = None) -> None:
        self.draft = draft
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def generate(self, **kwargs: Any) -> tuple[str, dict[str, int]]:
        self.calls.append(dict(kwargs))
        observation = kwargs.get("observation")
        if isinstance(observation, dict):
            observation.update(
                {
                    "contract_active": True,
                    "requested_model": kwargs.get("model"),
                    "requested_decoding": {
                        "temperature": kwargs.get("temperature"),
                        "max_tokens": kwargs.get("max_tokens"),
                        "top_p": kwargs.get("top_p"),
                        "seed": kwargs.get("seed"),
                    },
                    "request_digest": "deadbeef",
                    "invocation_attempted": True,
                    "invocation_succeeded": self.error is None,
                    "model_response_received": self.error is None,
                    "provider_reported_model": kwargs.get("model") if self.error is None else None,
                    "raw_model_sha256": _sha(self.draft) if self.error is None else None,
                    "raw_model_text": None,
                    "usage_availability": "REPORTED" if self.error is None else "NOT_REPORTED",
                    "usage_prompt_tokens": 12 if self.error is None else None,
                    "usage_completion_tokens": 4 if self.error is None else None,
                    "usage_total_tokens": 16 if self.error is None else None,
                    "failure_reason": None,
                }
            )
        if self.error is not None:
            raise self.error
        return self.draft, {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16}


class _SequenceGateway(_FakeGateway):
    """Returns one draft per call and records each call observation."""

    def __init__(self, drafts: list[str]) -> None:
        super().__init__(draft=drafts[0])
        self._drafts = list(drafts)
        self._index = 0

    def generate(self, **kwargs: Any) -> tuple[str, dict[str, int]]:
        self.draft = self._drafts[min(self._index, len(self._drafts) - 1)]
        self._index += 1
        return super().generate(**kwargs)


class _TransportBoomError(RuntimeError):
    reason_code = "PROVIDER_TIMEOUT"


@pytest.fixture
def contract_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _valid_env().items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("RAGIN_GENERATION_CONFIG_PATH", raising=False)
    monkeypatch.delenv("RAGIN_REQUIRE_MODEL_EXPOSURE", raising=False)


@pytest.fixture
def exposure_env(contract_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAGIN_REQUIRE_MODEL_EXPOSURE", "1")


# ---------------------------------------------------------------------------
# config resolution and validation
# ---------------------------------------------------------------------------


def test_contract_disabled_returns_none():
    assert resolve_generation_config(environ={}) is None
    assert resolve_generation_config(environ={"RAGIN_GENERATION_CONTRACT": "0"}) is None


def test_valid_env_resolves_all_fields():
    cfg = resolve_generation_config(environ=_valid_env())
    assert cfg is not None
    assert cfg.model == "lab/mock-model"
    assert cfg.temperature == 0.0
    assert cfg.max_tokens == 64
    assert cfg.top_p == 0.95
    assert cfg.seed == 7
    assert cfg.seed_status == SEED_EXPLICIT
    assert cfg.max_retries == 0
    assert cfg.source == "ENV_VARS"
    assert cfg.snapshot()["version"] == CONTRACT_VERSION


def test_explicitly_omitted_seed_is_declared_not_inferred():
    env = _valid_env()
    env.pop("RAGIN_GEN_SEED")
    env["RAGIN_GEN_SEED_STATUS"] = SEED_OMITTED
    cfg = resolve_generation_config(environ=env)
    assert cfg is not None
    assert cfg.seed is None
    assert cfg.seed_status == SEED_OMITTED
    assert "seed" not in cfg.decoding_payload()


def test_decoding_payload_explicit_seed_includes_configured_seed():
    cfg = _cfg()  # SEED_EXPLICIT with seed=7
    payload = cfg.decoding_payload()
    assert payload["seed"] == 7
    assert payload["temperature"] == 0.0
    assert payload["max_tokens"] == 64
    assert payload["top_p"] == 0.95


def test_decoding_payload_explicitly_unsupported_seed_includes_null():
    # EXPLICITLY_UNSUPPORTED resolves the seed to an explicit null in the
    # contract's decoding view; the actual wire payload must omit the field
    # (see tests/unit/test_decoding_contract_v1.py::
    # test_unsupported_seed_is_absent_from_the_wire).
    cfg = _cfg(seed=None, seed_status=SEED_UNSUPPORTED)
    payload = cfg.decoding_payload()
    assert payload["seed"] is None
    assert payload["temperature"] == 0.0
    assert payload["max_tokens"] == 64
    assert payload["top_p"] == 0.95


def test_unresolved_seed_refuses():
    env = _valid_env()
    env.pop("RAGIN_GEN_SEED")
    with pytest.raises(GenerationConfigError) as excinfo:
        resolve_generation_config(environ=env)
    message = str(excinfo.value)
    assert "seed" in message
    # Field-only errors must not interpolate configured values.
    assert "lab/mock-model" not in message


def test_conflicting_seed_status_refuses():
    env = _valid_env(RAGIN_GEN_SEED_STATUS=SEED_OMITTED)
    with pytest.raises(GenerationConfigError):
        resolve_generation_config(environ=env)


@pytest.mark.parametrize(
    "override",
    [
        {"RAGIN_GEN_TEMPERATURE": "nan"},
        {"RAGIN_GEN_TEMPERATURE": "-0.1"},
        {"RAGIN_GEN_TOP_P": "0"},
        {"RAGIN_GEN_TOP_P": "1.1"},
        {"RAGIN_GEN_MAX_TOKENS": "0"},
        {"RAGIN_GEN_MAX_TOKENS": "not-a-number"},
        {"RAGIN_GEN_MAX_RETRIES": "4"},
        {"RAGIN_GEN_MODEL": ""},
        {"RAGIN_GEN_MODEL": "https://user:pass@example.invalid/model"},
    ],
)
def test_invalid_values_refuse(override: dict[str, str]):
    with pytest.raises(GenerationConfigError):
        resolve_generation_config(environ=_valid_env(**override))


def test_json_config_wins_and_unknown_fields_refuse(tmp_path: Path):
    good = tmp_path / "generation.json"
    good.write_text(
        json.dumps(
            {
                "model": "lab/from-file",
                "temperature": 0.2,
                "max_tokens": 32,
                "top_p": 0.5,
                "seed": 11,
                "max_retries": 1,
            }
        ),
        encoding="utf-8",
    )
    env = _valid_env(RAGIN_GENERATION_CONFIG_PATH=str(good))
    cfg = resolve_generation_config(environ=env)
    assert cfg is not None
    assert cfg.model == "lab/from-file"
    assert cfg.source == "ENV_CONFIG_FILE"

    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"model": "lab/x", "secret_extra": "do-not-echo"}), encoding="utf-8")
    with pytest.raises(GenerationConfigError) as excinfo:
        resolve_generation_config(environ=_valid_env(RAGIN_GENERATION_CONFIG_PATH=str(bad)))
    assert "do-not-echo" not in str(excinfo.value)


def test_unreadable_config_path_is_not_echoed(tmp_path: Path):
    secret = tmp_path / "secret-token-name"
    env = _valid_env(RAGIN_GENERATION_CONFIG_PATH=str(secret / "generation.json"))
    with pytest.raises(GenerationConfigError) as excinfo:
        resolve_generation_config(environ=env)
    assert "secret-token-name" not in str(excinfo.value)


def test_digest_is_source_independent():
    from_env = resolve_generation_config(environ=_valid_env())
    native = _cfg(source="EXPLICIT_NATIVE")
    assert from_env is not None
    assert from_env.config_sha256 == native.config_sha256


def test_request_digest_covers_seed_and_top_p():
    cfg = _cfg()
    payload = {"model": "lab/mock-model", "temperature": 0.0, "max_tokens": 64, "top_p": 0.95, "seed": 7, "stream": False}
    base = GenerationConfig.request_digest(payload)
    assert base == GenerationConfig.request_digest(dict(payload))
    assert base != GenerationConfig.request_digest({**payload, "seed": 8})
    assert base != GenerationConfig.request_digest({**payload, "top_p": 0.5})


def test_require_model_exposure_is_opt_in():
    assert require_model_exposure({}) is False
    assert require_model_exposure({"RAGIN_REQUIRE_MODEL_EXPOSURE": "1"}) is True
    assert require_model_exposure({"RAGIN_REQUIRE_MODEL_EXPOSURE": "off"}) is False


# ---------------------------------------------------------------------------
# HTTP payload enforcement
# ---------------------------------------------------------------------------


def test_legacy_client_payload_has_no_contract_fields(monkeypatch: pytest.MonkeyPatch):
    seen: list[dict[str, Any]] = []

    def fake_post(url, json=None, headers=None, timeout=None):
        seen.append(json)
        return _FakeResponse(_completion("ok"))

    monkeypatch.setattr("ragin.gateway.client.requests.post", fake_post)
    client = GatewayClient(gateway_url="http://127.0.0.1:9", api_key="k")
    content, _ = client.generate(messages=[{"role": "user", "content": "hi"}], temperature=0.3, max_tokens=10)
    assert content == "ok"
    assert seen[0]["temperature"] == 0.3
    assert seen[0]["max_tokens"] == 10
    assert "top_p" not in seen[0]
    assert "seed" not in seen[0]


def test_contract_payload_carries_seed_and_top_p(monkeypatch: pytest.MonkeyPatch):
    seen: list[dict[str, Any]] = []
    observation: dict[str, Any] = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        seen.append(json)
        return _FakeResponse(_completion("ok"))

    monkeypatch.setattr("ragin.gateway.client.requests.post", fake_post)
    cfg = _cfg()
    client = GatewayClient(gateway_url="http://127.0.0.1:9", api_key="secret-key-value", generation_config=cfg)
    content, _ = client.generate(
        messages=[{"role": "user", "content": "hi"}],
        temperature=1.5,
        max_tokens=9999,
        observation=observation,
    )
    assert content == "ok"
    wire = seen[0]
    assert wire["model"] == "lab/mock-model"
    assert wire["temperature"] == 0.0
    assert wire["max_tokens"] == 64
    assert wire["top_p"] == 0.95
    assert wire["seed"] == 7
    assert observation["request_digest"] == GenerationConfig.request_digest(wire)
    assert observation["requested_decoding"]["seed"] == 7
    assert observation["seed_status"] == SEED_EXPLICIT
    assert observation["provider_reported_model"] == "lab/mock-model"
    assert observation["invocation_succeeded"] is True
    assert observation["usage_total_tokens"] == 16
    # No endpoint or credential leaks into the observation.
    serialized = json.dumps(observation, default=str)
    assert "127.0.0.1" not in serialized
    assert "secret-key-value" not in serialized


def test_contract_rejects_conflicting_call_arguments():
    client = GatewayClient(gateway_url="http://127.0.0.1:9", api_key="k", generation_config=_cfg())
    with pytest.raises(GenerationConfigError):
        client.generate(messages=[{"role": "user", "content": "hi"}], model="other/model")
    with pytest.raises(GenerationConfigError):
        client.generate(messages=[{"role": "user", "content": "hi"}], top_p=0.1)
    with pytest.raises(GenerationConfigError):
        client.generate(messages=[{"role": "user", "content": "hi"}], seed=8)


def test_contract_zero_retries_makes_exactly_one_request(monkeypatch: pytest.MonkeyPatch):
    calls: list[dict[str, Any]] = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append(json)
        return _FakeResponse(_completion(""))

    monkeypatch.setattr("ragin.gateway.client.requests.post", fake_post)
    observation: dict[str, Any] = {}
    client = GatewayClient(gateway_url="http://127.0.0.1:9", api_key="k", generation_config=_cfg(max_retries=0))
    content, _ = client.generate(messages=[{"role": "user", "content": "hi"}], observation=observation)
    assert content == ""
    assert len(calls) == 1
    assert observation["failure_reason"] == "EMPTY_MODEL_CONTENT"


def test_contract_retry_replays_identical_decoding(monkeypatch: pytest.MonkeyPatch):
    calls: list[dict[str, Any]] = []
    responses = [_completion(""), _completion("ok")]

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append(json)
        return _FakeResponse(responses[len(calls) - 1])

    monkeypatch.setattr("ragin.gateway.client.requests.post", fake_post)
    client = GatewayClient(gateway_url="http://127.0.0.1:9", api_key="k", generation_config=_cfg(max_retries=1))
    content, _ = client.generate(messages=[{"role": "user", "content": "hi"}])
    assert content == "ok"
    assert len(calls) == 2
    for field in ("model", "temperature", "max_tokens", "top_p", "seed"):
        assert calls[0][field] == calls[1][field]


# ---------------------------------------------------------------------------
# generator metadata / exposure labelling
# ---------------------------------------------------------------------------


def test_model_draft_metadata_and_exposure(exposure_env: None):
    cfg = _cfg()
    gen = ResponseGenerator(gateway_url=None)
    fake = _FakeGateway()
    gen._gateway = fake
    meta: dict[str, Any] = {}
    text = gen.generate(
        skill_level="expert",
        user_input="tail -n 40 /opt/app/release/notes.txt",
        meta=meta,
    )
    assert text
    call = fake.calls[0]
    assert call["model"] == cfg.model
    assert call["temperature"] == cfg.temperature
    assert call["max_tokens"] == cfg.max_tokens
    assert call["top_p"] == cfg.top_p
    assert call["seed"] == cfg.seed
    assert meta["generation_observation_schema"] == OBSERVATION_SCHEMA
    assert meta["generation_contract_version"] == CONTRACT_VERSION
    assert meta["generation_config_sha256"] == cfg.config_sha256
    assert meta["generation_request_digest"] == "deadbeef"
    assert meta["requested_model"] == cfg.model
    assert meta["model_invocation_attempted"] is True
    assert meta["model_response_received"] is True
    assert meta["model_draft_used_in_candidate"] is True
    assert meta["raw_model_draft_sha256"] == _sha(fake.draft)
    assert meta["final_generation_sha256"] == _sha(text)
    assert meta["final_generation_source"] == "MODEL_POSTPROCESSED"
    assert meta["model_exposure_status"] == "MODEL_DRAFT_USED"
    assert meta["protocol_compliant"] is True
    assert meta["cost_usd"] is None
    assert meta["cost_availability"] == "NOT_MEASURED"


def test_template_anchor_is_not_labelled_model_draft(exposure_env: None):
    gen = ResponseGenerator(gateway_url=None)
    gen._gateway = _FakeGateway(draft="2")
    meta: dict[str, Any] = {}
    text = gen.generate(skill_level="expert", user_input="docker ps", meta=meta)
    assert text
    assert meta["template_anchored"] is True
    assert meta["model_draft_used_in_candidate"] is False
    assert meta["final_generation_source"] == "TEMPLATE_ANCHORED"
    assert meta["model_exposure_status"] == "MODEL_CALLED_DRAFT_NOT_USED"
    assert meta["protocol_compliant"] is False
    assert meta["final_generation_sha256"] == _sha(text)


def test_identity_command_replacement_is_not_model_use(exposure_env: None):
    """whoami/id/getent group sudo are RAGIN answers, not model drafts."""
    cases = [
        ("whoami", "root\n", "webapp"),
        ("whoami", "webapp\n", "webapp"),  # matching by chance is still deterministic
        ("getent group sudo", "sudo:x:27:webapp\n", "sudo:x:27:sysadmin,deploy-bot"),
    ]
    for user_input, raw, expected in cases:
        gen = ResponseGenerator(gateway_url=None)
        gen._gateway = _FakeGateway(draft=raw)
        meta: dict[str, Any] = {}
        text = gen.generate(skill_level="expert", user_input=user_input, meta=meta)
        assert text == expected
        assert meta["model_invocation_attempted"] is True
        assert meta["model_response_received"] is True
        assert meta["postprocess_provenance"] == "DETERMINISTIC_IDENTITY_REPLACEMENT"
        assert meta["final_generation_source"] == "DETERMINISTIC_IDENTITY_REPLACEMENT"
        assert meta["model_draft_used_in_candidate"] is False
        assert meta["model_exposure_status"] == "MODEL_CALLED_DRAFT_NOT_USED"
        assert meta["protocol_compliant"] is False
        assert meta["raw_model_draft_sha256"] == _sha(raw)
        assert meta["final_generation_sha256"] == _sha(expected)


def test_partial_postprocess_is_labelled_model_content(exposure_env: None):
    """A root-prompt rewrite keeps model bytes and must stay MODEL_POSTPROCESSED."""
    raw = (
        "root@core-lnx-03:~# systemctl status nginx\n"
        "● nginx.service - A high performance web server\n"
        "   Active: active (running)\n"
    )
    gen = ResponseGenerator(gateway_url=None)
    gen._gateway = _FakeGateway(draft=raw)
    meta: dict[str, Any] = {}
    text = gen.generate(skill_level="expert", user_input="systemctl status nginx", meta=meta)
    assert text.startswith("webapp@core-lnx-03:~#")
    assert meta["postprocess_provenance"] == "MODEL_CONTENT_POSTPROCESSED"
    assert meta["final_generation_source"] == "MODEL_POSTPROCESSED"
    assert meta["model_draft_used_in_candidate"] is True
    assert meta["protocol_compliant"] is True
    assert meta["raw_model_draft_sha256"] == _sha(raw)
    assert meta["postprocessed_candidate_sha256"] == _sha(text)
    assert meta["postprocessed_candidate_sha256"] != meta["raw_model_draft_sha256"]


def test_strict_retry_usage_is_last_request_only_and_not_a_turn_total(exposure_env: None):
    """The semantic strict retry resets observation; never sum the last usage."""
    safe = (
        "webapp@core-lnx-03:~$ systemctl status nginx\n"
        "● nginx.service - A high performance web server\n"
        "   Active: active (running)\n"
    )
    gen = ResponseGenerator(gateway_url=None)
    gen._gateway = _SequenceGateway(["", safe])
    meta: dict[str, Any] = {}
    text = gen.generate(skill_level="expert", user_input="systemctl status nginx", meta=meta)
    assert text
    assert meta["final_generation_source"] == "MODEL_STRICT_RETRY_POSTPROCESSED"
    assert meta["semantic_strict_retry_used"] is True
    assert meta["multiple_attempts_count"] == 2
    assert meta["attempt_count_scope"] == "GATEWAY_CALLS_EXCLUDES_TRANSPORT_RETRY_DETAIL"
    assert meta["usage_scope"] == "LAST_PROVIDER_REQUEST_ONLY"
    assert meta["aggregate_usage_availability"] == "NOT_MEASURED"
    assert meta["usage_total_tokens"] == 16
    assert meta["usage_total_tokens_is_turn_total"] is False
    assert meta["all_request_ledger_available"] is False
    assert meta["usage_semantics"] == "DO_NOT_SUM_LAST_USAGE_AS_TURN_TOTAL"
    assert len(gen._gateway.calls) == 2


def test_provider_failure_serves_template_with_honest_fields(exposure_env: None):
    gen = ResponseGenerator(gateway_url=None)
    gen._gateway = _FakeGateway(error=_TransportBoomError("boom"))
    meta: dict[str, Any] = {}
    text = gen.generate(skill_level="novice", user_input="uname -a", meta=meta)
    assert text
    assert meta["gateway_fallback"] is True
    assert meta["model_invocation_attempted"] is True
    assert meta["model_invocation_succeeded"] is False
    assert meta["model_response_received"] is False
    assert meta["model_draft_used_in_candidate"] is False
    assert meta["final_generation_source"] == "TEMPLATE_FALLBACK"
    assert meta["generation_failure_reason"] == "PROVIDER_TIMEOUT"
    assert meta["model_exposure_status"] == "MODEL_CALL_FAILED"
    assert meta["protocol_compliant"] is False
    assert meta["treatment_available"] is False
    assert meta["cost_usd"] is None


def test_no_gateway_in_exposure_mode_is_unavailable(exposure_env: None):
    gen = ResponseGenerator(gateway_url=None)
    meta: dict[str, Any] = {}
    text = gen.generate(skill_level="novice", user_input="uname -a", meta=meta)
    assert text
    assert meta["model_invocation_attempted"] is False
    assert meta["final_generation_source"] == "TEMPLATE_NO_GATEWAY"
    assert meta["model_exposure_status"] == "MODEL_REQUIRED_UNAVAILABLE"
    assert meta["protocol_compliant"] is False


def test_legacy_metadata_shape_is_unchanged(monkeypatch: pytest.MonkeyPatch):
    for key in (
        "RAGIN_GENERATION_CONTRACT",
        "RAGIN_GEN_MODEL",
        "RAGIN_GEN_TEMPERATURE",
        "RAGIN_GEN_MAX_TOKENS",
        "RAGIN_GEN_TOP_P",
        "RAGIN_GEN_SEED",
        "RAGIN_GEN_SEED_STATUS",
        "RAGIN_GEN_MAX_RETRIES",
        "RAGIN_REQUIRE_MODEL_EXPOSURE",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("RAGIN_GENERATION_CONFIG_PATH", raising=False)
    gen = ResponseGenerator(gateway_url=None)
    gen._gateway = _FakeGateway(draft="version 2026.09.30\n")
    meta: dict[str, Any] = {}
    text = gen.generate(skill_level="expert", user_input="tail -n 5 /opt/app/notes.txt", meta=meta)
    assert text
    assert "generation_observation_schema" not in meta
    assert "model_exposure_status" not in meta
    assert "generation_contract_version" not in meta


def test_deceiver_fastpath_labels_are_not_model_exposure(exposure_env: None):
    # Exposure mode only (no contract): no gateway -> unavailable.
    dec = AdaptiveDeceiver()
    resp = dec.generate_response("curl http://169.254.169.254/latest/meta-data/", {"session_id": "gen-fast-1"})
    assert resp.metadata["model_exposure_status"] == "MODEL_REQUIRED_UNAVAILABLE"
    assert resp.metadata["model_invocation_attempted"] is False
    assert resp.metadata["final_generation_source"] == "DETERMINISTIC_FASTPATH"

    # Gateway configured but deliberately not called by the deterministic path.
    dec2 = AdaptiveDeceiver(gateway_url="http://127.0.0.1:9")
    resp2 = dec2.generate_response("curl http://169.254.169.254/latest/meta-data/", {"session_id": "gen-fast-2"})
    assert resp2.metadata["model_exposure_status"] == "NOT_EXPOSED_DETERMINISTIC_FASTPATH"
    assert resp2.metadata["model_draft_used_in_candidate"] is False
    assert resp2.metadata["final_generation_sha256"] == _sha(resp2.response_text)
    assert resp2.metadata["protocol_compliant"] is False


def test_deceiver_fastpath_metadata_unchanged_in_legacy_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("RAGIN_REQUIRE_MODEL_EXPOSURE", raising=False)
    dec = AdaptiveDeceiver()
    resp = dec.generate_response("curl http://169.254.169.254/latest/meta-data/", {"session_id": "gen-fast-3"})
    assert "model_exposure_status" not in resp.metadata
    assert "final_generation_source" not in resp.metadata


# ---------------------------------------------------------------------------
# provider health / endpoint hygiene
# ---------------------------------------------------------------------------


def test_health_legacy_keys_unchanged():
    transport = ProviderTransport(gateway_url="http://provider.internal:9", api_key="secret-key-value")
    assert set(transport.health().keys()) == {"provider_url", "api_key_present", "timeout_s", "client_ready"}


def test_health_adds_generation_only_when_contract_active():
    transport = ProviderTransport(
        gateway_url="http://provider.internal:9", api_key="secret-key-value", generation_config=_cfg()
    )
    health = transport.health()
    assert set(health.keys()) == {"provider_url", "api_key_present", "timeout_s", "client_ready", "generation"}
    generation = health["generation"]
    assert generation["contract_active"] is True
    assert generation["config_sha256"] == _cfg().config_sha256
    serialized = json.dumps(generation, default=str)
    assert "provider.internal" not in serialized
    assert "secret-key-value" not in serialized


def test_safe_endpoint_drops_userinfo_and_query():
    assert _safe_endpoint("https://user:pass@example.invalid:8443/v1?token=secret#frag") == (
        "https://example.invalid:8443/v1"
    )
    assert _safe_endpoint("not a url") == "[invalid-endpoint]"


# ---------------------------------------------------------------------------
# loopback fixture (MOCKED_PROVIDER_INTEGRATION, never model inference)
# ---------------------------------------------------------------------------


class _RecordingHandler(BaseHTTPRequestHandler):
    requests: list[dict[str, Any]] = []

    def do_POST(self):  # noqa: N802 - stdlib handler name
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        type(self).requests.append({"payload": payload, "authorization": self.headers.get("Authorization")})
        body = json.dumps(_completion("mock output")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence the test server
        return None


def test_mocked_provider_integration_loopback():
    """MOCKED_PROVIDER_INTEGRATION: a loopback fixture, not model inference."""
    _RecordingHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _RecordingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        cfg = _cfg()
        observation: dict[str, Any] = {}
        client = GatewayClient(
            gateway_url=f"http://127.0.0.1:{server.server_port}",
            api_key="loopback-test-key",
            generation_config=cfg,
        )
        content, usage = client.generate(
            messages=[{"role": "user", "content": "synthetic lab command"}],
            observation=observation,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert content == "mock output"
    assert usage["total_tokens"] == 16
    assert len(_RecordingHandler.requests) == 1
    wire = _RecordingHandler.requests[0]["payload"]
    assert wire["model"] == cfg.model
    assert wire["temperature"] == cfg.temperature
    assert wire["max_tokens"] == cfg.max_tokens
    assert wire["top_p"] == cfg.top_p
    assert wire["seed"] == cfg.seed
    assert _RecordingHandler.requests[0]["authorization"] == "Bearer loopback-test-key"
    assert observation["request_digest"] == GenerationConfig.request_digest(wire)
    assert observation["provider_reported_model"] == "lab/mock-model"
    # The fixture is explicitly not a model measurement.
    assert observation["invocation_succeeded"] is True
