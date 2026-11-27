"""Decoding-contract trace tests: wire truth, call sites, publisher (offline).

Three gaps these close, none of which the earlier contract tests covered:

1. wire truth — what the generation client actually serializes (including
   extension fields such as ``reasoning_effort``) versus what the observation
   records, so "configured" and "sent" can be compared without re-deriving
   payloads from code;
2. the Hisoka call site — the legacy ``0.7/4096`` request (documented
   historical default) versus the contract-owned decoding values;
3. the effective-config artifact publisher and its consumption by the
   ablation preflight, which is what unblocks ``BLOCKED_GENERATION_CONFIG``.

Everything here is offline: HTTP is monkeypatched on ``requests.post``, the
publisher opens no socket, and no model or weights are loaded. A passing test
is NOT evidence of model inference, and it is NOT evidence that a backend
honors ``top_p``/``seed`` — it proves configuration plumbing only.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

# Defensive import-time guard (same as test_generation_contract_v1): these
# focused tests must never inherit the repository's session-log directory.
_TEST_SCRATCH = Path(tempfile.mkdtemp(prefix="ragin-decoding-v1-"))
os.environ.setdefault("RAGIN_SESSION_DIR", str(_TEST_SCRATCH / "sessions"))
os.environ.setdefault("RAGIN_HOST_FICTION_PATH", str(_TEST_SCRATCH / "host_fiction.json"))
Path(os.environ["RAGIN_SESSION_DIR"]).mkdir(parents=True, exist_ok=True)

from ragin.evaluation.ablation_contract import _check_generation  # noqa: E402
from ragin.gateway.client import GatewayClient  # noqa: E402
from ragin.gateway.generation import (  # noqa: E402
    SEED_EXPLICIT,
    SEED_UNSUPPORTED,
    GenerationConfig,
    GenerationConfigError,
)
from ragin.hisoka.deception import ResponseGenerator  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PUBLISHER = ROOT / "scripts" / "publish_effective_generation_config_v1.py"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _load_publisher():
    spec = importlib.util.spec_from_file_location(
        "ragin_publish_effective_generation_config_v1", PUBLISHER
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _contract_env(**overrides: str) -> dict[str, str]:
    env = {
        "RAGIN_GENERATION_CONTRACT": "1",
        "RAGIN_GEN_MODEL": "lab/mock-model",
        "RAGIN_GEN_TEMPERATURE": "0.0",
        "RAGIN_GEN_MAX_TOKENS": "512",
        "RAGIN_GEN_TOP_P": "1.0",
        "RAGIN_GEN_SEED": "0",
        "RAGIN_GEN_MAX_RETRIES": "0",
    }
    env.update(overrides)
    return env


def _apply_env(monkeypatch: pytest.MonkeyPatch, env: dict[str, str]) -> None:
    for key, value in env.items():
        monkeypatch.setenv(key, value)


def _cfg(**overrides: Any) -> GenerationConfig:
    values: dict[str, Any] = {
        "model": "lab/mock-model",
        "temperature": 0.0,
        "max_tokens": 512,
        "top_p": 1.0,
        "seed": 0,
        "seed_status": SEED_EXPLICIT,
        "max_retries": 0,
    }
    values.update(overrides)
    return GenerationConfig(**values)


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.reason = "OK" if status_code == 200 else "Bad Request"

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"{self.status_code}", response=self)


def _completion(content: str) -> dict[str, Any]:
    return {
        "id": "chatcmpl-offline",
        "model": "lab/mock-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
    }


def _capture_posts(monkeypatch: pytest.MonkeyPatch, responses: list[_FakeResponse]) -> list[dict]:
    payloads: list[dict] = []
    iterator = iter(responses)

    def fake_post(url, json=None, headers=None, timeout=None):  # noqa: A002 - requests kwarg
        payloads.append(json)
        return next(iterator)

    monkeypatch.setattr("ragin.gateway.client.requests.post", fake_post)
    return payloads


def _client(generation_config: GenerationConfig | None) -> GatewayClient:
    return GatewayClient(
        gateway_url="http://127.0.0.1:9/v1",
        api_key="offline-test-key",
        generation_config=generation_config,
    )


# ---------------------------------------------------------------------------
# 1. wire truth
# ---------------------------------------------------------------------------


def test_contract_wire_fields_match_serialized_decoding(monkeypatch: pytest.MonkeyPatch) -> None:
    payloads = _capture_posts(monkeypatch, [_FakeResponse(_completion("webapp"))])
    observation: dict[str, Any] = {}
    _client(_cfg()).generate(messages=[{"role": "user", "content": "whoami"}], observation=observation)

    payload = payloads[0]
    assert payload["temperature"] == 0.0
    assert payload["max_tokens"] == 512
    assert payload["top_p"] == 1.0
    assert payload["seed"] == 0
    assert observation["decoding_wire_fields"] == {
        "temperature": 0.0,
        "max_tokens": 512,
        "top_p": 1.0,
        "seed": 0,
        "stream": False,
    }
    assert observation["payload_extension_fields"] == []
    assert observation["request_digest"] == GenerationConfig.request_digest(payload)


def test_unsupported_seed_is_absent_from_the_wire(monkeypatch: pytest.MonkeyPatch) -> None:
    payloads = _capture_posts(monkeypatch, [_FakeResponse(_completion("webapp"))])
    observation: dict[str, Any] = {}
    config = _cfg(seed=None, seed_status=SEED_UNSUPPORTED)
    _client(config).generate(messages=[{"role": "user", "content": "whoami"}], observation=observation)

    assert "seed" not in payloads[0]
    assert "seed" not in observation["decoding_wire_fields"]
    assert observation["seed_status"] == SEED_UNSUPPORTED


def test_reasoning_effort_injection_is_recorded_not_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    # The client injects reasoning_effort for reasoning deployments on short
    # calls. That changes provider behaviour but is not a contract field, so it
    # must surface in the observation instead of riding silently.
    payloads = _capture_posts(monkeypatch, [_FakeResponse(_completion("webapp"))])
    observation: dict[str, Any] = {}
    config = _cfg(model="lab/glm-5-flash")  # matches the reasoning-model pattern
    _client(config).generate(messages=[{"role": "user", "content": "whoami"}], observation=observation)

    assert payloads[0]["reasoning_effort"] == "low"
    assert observation["payload_extension_fields"] == ["reasoning_effort"]
    assert "reasoning_effort" not in observation["decoding_wire_fields"]


def test_400_extension_retry_refreshes_wire_truth_and_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        _FakeResponse({"error": "unknown field"}, status_code=400),
        _FakeResponse(_completion("webapp")),
    ]
    payloads = _capture_posts(monkeypatch, responses)
    observation: dict[str, Any] = {}
    config = _cfg(model="lab/glm-5-flash")
    content, _ = _client(config).generate(
        messages=[{"role": "user", "content": "whoami"}], observation=observation
    )

    assert content == "webapp"
    assert observation["extension_body_dropped"] is True
    # The second (successful) request is the one that must be described.
    assert "reasoning_effort" not in payloads[1]
    assert observation["payload_extension_fields"] == []
    assert observation["decoding_wire_fields"] == {
        "temperature": 0.0,
        "max_tokens": 512,
        "top_p": 1.0,
        "seed": 0,
        "stream": False,
    }
    assert observation["request_digest"] == GenerationConfig.request_digest(payloads[1])


def test_legacy_retry_inflation_is_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        _FakeResponse(_completion("")),
        _FakeResponse(_completion("webapp")),
    ]
    payloads = _capture_posts(monkeypatch, responses)
    observation: dict[str, Any] = {}
    _client(None).generate(
        messages=[{"role": "user", "content": "whoami"}],
        model="lab/mock-model",
        temperature=0.3,
        max_tokens=1024,
        observation=observation,
    )

    # Documented legacy behaviour: the empty-content retry inflates the budget.
    assert payloads[1]["max_tokens"] == 4096 == min(12_800, max(1024, 1024 * 4))
    assert observation["cot_retry_attempted"] is True
    assert observation["cot_retry_decoding"]["max_tokens"] == 4096
    # The first request's wire truth stays the first request's values.
    assert observation["decoding_wire_fields"]["max_tokens"] == 1024


def test_contract_retry_replays_identical_decoding(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        _FakeResponse(_completion("")),
        _FakeResponse(_completion("webapp")),
    ]
    payloads = _capture_posts(monkeypatch, responses)
    observation: dict[str, Any] = {}
    config = _cfg(max_retries=1)
    _client(config).generate(messages=[{"role": "user", "content": "whoami"}], observation=observation)

    assert payloads[1] == payloads[0]
    assert observation["cot_retry_decoding"]["max_tokens"] == 512


# ---------------------------------------------------------------------------
# 2. Hisoka call site
# ---------------------------------------------------------------------------


class _RecordingGateway:
    """Minimal gateway stand-in that records the call kwargs."""

    def __init__(self, draft: str = "webapp\n") -> None:
        self.draft = draft
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
                    "request_digest": "offline",
                    "invocation_attempted": True,
                    "invocation_succeeded": True,
                    "model_response_received": True,
                    "provider_reported_model": kwargs.get("model"),
                    "usage_availability": "NOT_REPORTED",
                    "failure_reason": None,
                }
            )
        return self.draft, {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}


def test_hisoka_legacy_call_site_requests_0_7_4096(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAGIN_GENERATION_CONTRACT", raising=False)
    generator = ResponseGenerator()
    assert generator.generation_config is None
    gateway = _RecordingGateway()
    generator._gateway = gateway

    generator._generate_via_gateway("novice", "whoami", "")

    call = gateway.calls[0]
    assert call["temperature"] == 0.7
    assert call["max_tokens"] == 4096
    assert "top_p" not in call
    assert "seed" not in call


def test_hisoka_contract_call_site_uses_contract_decoding(monkeypatch: pytest.MonkeyPatch) -> None:
    _apply_env(monkeypatch, _contract_env())
    generator = ResponseGenerator()
    config = generator.generation_config
    assert config is not None
    gateway = _RecordingGateway()
    generator._gateway = gateway

    generator._generate_via_gateway("novice", "whoami", "")

    call = gateway.calls[0]
    assert call["temperature"] == 0.0
    assert call["max_tokens"] == 512
    assert call["top_p"] == 1.0
    assert call["seed"] == 0
    assert call["model"] == config.model


def test_hisoka_unresolved_contract_refuses_instead_of_falling_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _apply_env(monkeypatch, _contract_env())
    monkeypatch.delenv("RAGIN_GEN_SEED", raising=False)
    monkeypatch.delenv("RAGIN_GEN_SEED_STATUS", raising=False)
    with pytest.raises(GenerationConfigError):
        ResponseGenerator()


# ---------------------------------------------------------------------------
# 3. effective-config publisher
# ---------------------------------------------------------------------------


def _frozen_decoding() -> dict[str, Any]:
    return json.loads(
        (ROOT / "configs" / "ablation" / "eval_v1" / "run_contract_v1.json").read_text()
    )["generation"]["decoding"]


def _write_run_contract(tmp_path: Path, decoding: dict[str, Any]) -> Path:
    path = tmp_path / "run_contract.json"
    path.write_text(json.dumps({"generation": {"decoding": decoding}}))
    return path


def test_publisher_writes_artifact_matching_the_frozen_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    module = _load_publisher()
    _apply_env(monkeypatch, _contract_env())
    contract = _write_run_contract(tmp_path, _frozen_decoding())
    out = tmp_path / "effective.json"

    rc = module.main(["--contract", str(contract), "--out", str(out)])

    assert rc == 0
    artifact = json.loads(out.read_text())
    assert artifact["schema"] == "ragin.generation.effective_config.v1"
    assert artifact["applied_decoding"] == {
        "temperature": 0.0,
        "max_tokens": 512,
        "top_p": 1.0,
        "seed": 0,
    }
    assert artifact["seed_status"] == SEED_EXPLICIT
    assert artifact["model_exposure"]["require_model_exposure"] is False
    assert artifact["model_exposure"]["status"] == "DISABLED"
    printed = json.loads(capsys.readouterr().out)
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    assert printed["artifact_sha256"] == digest


def test_publisher_refuses_when_contract_not_activated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _load_publisher()
    monkeypatch.delenv("RAGIN_GENERATION_CONTRACT", raising=False)
    out = tmp_path / "effective.json"

    rc = module.main(["--contract", str(tmp_path / "run_contract.json"), "--out", str(out)])

    assert rc == 2
    assert not out.exists()


def test_publisher_refuses_on_decoding_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _load_publisher()
    _apply_env(monkeypatch, _contract_env())
    requested = _frozen_decoding()
    requested["temperature"] = 0.7
    contract = _write_run_contract(tmp_path, requested)
    out = tmp_path / "effective.json"

    rc = module.main(["--contract", str(contract), "--out", str(out)])

    assert rc == 3
    assert not out.exists()


def test_publisher_refuses_overwrite_without_force(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _load_publisher()
    _apply_env(monkeypatch, _contract_env())
    contract = _write_run_contract(tmp_path, _frozen_decoding())
    out = tmp_path / "effective.json"
    out.write_text("{}")

    rc = module.main(["--contract", str(contract), "--out", str(out)])

    assert rc == 2
    assert out.read_text() == "{}"


def test_ablation_contract_consumes_the_published_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _load_publisher()
    _apply_env(monkeypatch, _contract_env())
    _apply_env(monkeypatch, {"RAGIN_REQUIRE_MODEL_EXPOSURE": "1"})
    contract_path = _write_run_contract(tmp_path, _frozen_decoding())
    out = tmp_path / "effective.json"
    assert module.main(["--contract", str(contract_path), "--out", str(out)]) == 0
    artifact_sha = hashlib.sha256(out.read_bytes()).hexdigest()

    contract = {
        "generation": {
            "model_id": "lab/mock-model",
            "decoding": _frozen_decoding(),
            # The stale adapter claims are exactly what the artifact supersedes:
            # preflight must prefer the effective config over this block.
            "adapter": {
                "name": "hisoka",
                "supported_decoding": ["temperature", "max_tokens"],
                "hardcoded_decoding": {"temperature": 0.7, "max_tokens": 4096},
                "config_enforced": False,
                "seed_supported": False,
                "top_p_supported": False,
            },
            "effective_config": {"path": str(out), "sha256": artifact_sha},
        }
    }
    blockers: list = []
    resolved: dict[str, Any] = {}
    _check_generation(contract, ROOT, blockers, resolved)

    codes = {blocker.code for blocker in blockers}
    # The artifact clears the effective-config blocker and the adapter-path
    # exposure blocker it resolves. The remaining blockers belong to sections
    # this synthetic contract deliberately leaves unresolved (prompt id,
    # invocation kind, fallback switch, exposure_contract), which is the honest
    # state for a contract whose generator is still UNRESOLVED.
    assert "UNRESOLVED_EFFECTIVE_GENERATION_CONFIG" not in codes
    assert "BLOCKED_GENERATION_CONFIG" not in codes
    assert resolved["generation_config"]["applied_decoding"]["temperature"] == 0.0
    assert resolved["generation_config"]["require_model_exposure"] is True

    # Without the artifact the same contract blocks on the adapter claims —
    # i.e. the artifact is what actually clears the blocker.
    without_artifact = json.loads(json.dumps(contract))
    without_artifact["generation"].pop("effective_config")
    bare_blockers: list = []
    _check_generation(without_artifact, ROOT, bare_blockers, {})
    assert "BLOCKED_GENERATION_CONFIG" in {b.code for b in bare_blockers}


def test_ablation_contract_blocks_when_artifact_hash_does_not_match(
    tmp_path: Path,
) -> None:
    out = tmp_path / "effective.json"
    out.write_text(json.dumps({"applied_decoding": {"temperature": 0.0}}))
    contract = {
        "generation": {
            "model_id": "lab/mock-model",
            "decoding": _frozen_decoding(),
            "adapter": {"name": "hisoka", "supported_decoding": ["temperature", "max_tokens"]},
            "effective_config": {"path": str(out), "sha256": "0" * 64},
        }
    }
    blockers: list = []
    resolved: dict[str, Any] = {}
    _check_generation(contract, ROOT, blockers, resolved)

    assert "UNRESOLVED_EFFECTIVE_GENERATION_CONFIG" in {blocker.code for blocker in blockers}


# ---------------------------------------------------------------------------
# 4. arm-config consistency
# ---------------------------------------------------------------------------


def test_b1_b2_b3_agree_on_decoding_and_runtime_defaults() -> None:
    arms = ["b1_no_retrieval", "b2_bm25", "b3_dense"]
    generators = [
        json.loads((ROOT / "configs" / "ablation" / f"{name}.json").read_text())["generator"]
        for name in arms
    ]
    # Comparable LLM arms must not drift apart silently.
    assert generators[0]["decoding"] == generators[1]["decoding"] == generators[2]["decoding"]
    assert (
        generators[0]["runtime_observed_defaults"]
        == generators[1]["runtime_observed_defaults"]
        == generators[2]["runtime_observed_defaults"]
        == {"temperature": 0.7, "max_tokens": 4096}
    )
    for generator in generators:
        assert generator["settings_status"] == "PROPOSED_NOT_ENFORCED"
        assert generator["not_exposed_by_runtime"] == ["seed", "top_p"]
    # And the arms' proposed decoding is the run contract's proposed decoding.
    frozen = _frozen_decoding()
    for key in ("temperature", "top_p", "max_tokens", "seed"):
        assert generators[0]["decoding"][key] == frozen[key], key
