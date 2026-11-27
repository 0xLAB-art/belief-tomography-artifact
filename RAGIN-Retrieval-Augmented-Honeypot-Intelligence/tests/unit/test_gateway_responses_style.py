"""Tests for the optional OpenAI Responses transport style and UA override.

Some providers only route their current models through /v1/responses and
reject /v1/chat/completions for them (observed on agentrouter.org, 2026-10-27:
"model does not support this interface"). The chat-shaped payload every caller
builds must be translated at the transport boundary, and the observation
ledger must record what actually went on the wire.

Also covered: RAGIN_LLM_USER_AGENT, because some gateways only answer
requests identifying as one of their supported clients.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ragin.gateway.client import (
    GatewayClient,
    _normalize_reply,
    _to_responses_payload,
)

pytestmark = pytest.mark.unit


def _responses_reply(text: str | None = "OK", usage: dict | None = None) -> MagicMock:
    content = [] if text is None else [{"type": "output_text", "text": text}]
    resp = MagicMock()
    resp.json.return_value = {
        "id": "resp_123",
        "status": "completed",
        "model": "gpt-6.1-sol",
        "output": [
            {"type": "reasoning", "summary": [{"type": "summary_text", "text": "hidden cot"}]},
            {"type": "message", "role": "assistant", "content": content},
        ],
        "usage": usage if usage is not None else {"input_tokens": 11, "output_tokens": 7, "total_tokens": 18},
    }
    return resp


def _post_call(mock_post: MagicMock, index: int = 0) -> tuple[str, dict, dict]:
    call = mock_post.call_args_list[index]
    return call[0][0], call[1]["json"], call[1]["headers"]


class TestPayloadTranslation:
    def test_maps_chat_fields_to_responses_shape(self):
        wire, dropped = _to_responses_payload(
            {
                "model": "gpt-6.1-sol",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 128,
                "stream": False,
            }
        )
        assert wire == {
            "model": "gpt-6.1-sol",
            "input": [{"role": "user", "content": "hi"}],
            "max_output_tokens": 128,
            "stream": False,
        }
        assert dropped == []

    def test_drops_decoding_fields_the_endpoint_rejects(self):
        wire, dropped = _to_responses_payload(
            {
                "model": "m",
                "messages": [],
                "max_tokens": 8,
                "temperature": 0.3,
                "top_p": 1.0,
                "seed": 42,
            }
        )
        assert "temperature" not in wire
        assert "top_p" not in wire
        assert "seed" not in wire
        assert set(dropped) >= {"temperature", "top_p", "seed"}

    def test_reports_unknown_extension_fields_as_dropped(self):
        wire, dropped = _to_responses_payload({"model": "m", "messages": [], "max_tokens": 8, "some_vendor_field": 1})
        assert "some_vendor_field" not in wire
        assert "some_vendor_field" in dropped

    def test_maps_reasoning_effort_extension(self):
        wire, _ = _to_responses_payload({"model": "m", "messages": [], "max_tokens": 8, "reasoning_effort": "low"})
        assert wire["reasoning"] == {"effort": "low"}


class TestReplyNormalization:
    def test_extracts_text_and_maps_usage(self):
        data = _normalize_reply(_responses_reply("hello").json.return_value)
        assert data["choices"][0]["message"]["content"] == "hello"
        assert data["model"] == "gpt-6.1-sol"
        assert data["id"] == "resp_123"
        assert data["usage"] == {
            "prompt_tokens": 11,
            "completion_tokens": 7,
            "total_tokens": 18,
        }

    def test_never_returns_reasoning_items(self):
        data = _normalize_reply(_responses_reply("visible").json.return_value)
        assert "hidden cot" not in repr(data)

    def test_empty_output_becomes_none_content(self):
        data = _normalize_reply(_responses_reply(None).json.return_value)
        assert data["choices"][0]["message"]["content"] is None

    def test_chat_shaped_and_nondict_replies_pass_through(self):
        chat = {"choices": [{"message": {"content": "x"}}]}
        assert _normalize_reply(chat) is chat
        assert _normalize_reply(["not", "a", "dict"]) == ["not", "a", "dict"]
        assert _normalize_reply({"model": "m"}) == {"model": "m"}


class TestResponsesStyleClient:
    @pytest.fixture(autouse=True)
    def _style(self, monkeypatch):
        monkeypatch.setenv("RAGIN_LLM_API_STYLE", "responses")
        monkeypatch.setenv("RAGIN_LLM_USER_AGENT", "claude-cli/2.1.310 (external, cli)")

    def test_posts_to_responses_endpoint_with_translated_payload(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = _responses_reply()
            client = GatewayClient(gateway_url="https://gw.example/v1", api_key="k")
            content, usage = client.generate(
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-6.1-sol",
                max_tokens=128,
            )
            url, payload, headers = _post_call(mock_post)
            assert url == "https://gw.example/v1/responses"
            assert payload["input"] == [{"role": "user", "content": "hi"}]
            assert payload["max_output_tokens"] == 128
            assert "temperature" not in payload
            assert "messages" not in payload
            assert headers["User-Agent"] == "claude-cli/2.1.310 (external, cli)"
            assert content == "OK"
            assert usage["total_tokens"] == 18

    def test_observation_records_the_wire_payload(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = _responses_reply()
            client = GatewayClient(gateway_url="https://gw.example", api_key="k")
            obs: dict = {}
            client.generate(
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-6.1-sol",
                max_tokens=64,
                observation=obs,
            )
            wire = obs["decoding_wire_fields"]
            assert wire["max_output_tokens"] == 64
            assert "temperature" not in wire
            assert "max_tokens" not in wire
            assert obs["invocation_succeeded"] is True
            assert obs["provider_reported_model"] == "gpt-6.1-sol"
            assert obs["usage_availability"] == "PROVIDER_REPORTED"
            assert obs["raw_model_text"] is not None

    def test_empty_content_retry_inflates_max_output_tokens(self):
        empty = _responses_reply(None)
        filled = _responses_reply("second try")
        with patch("requests.post") as mock_post:
            mock_post.side_effect = [empty, filled]
            client = GatewayClient(gateway_url="https://gw.example", api_key="k")
            content, _ = client.generate(
                messages=[{"role": "user", "content": "hi"}],
                model="gpt-6.1-sol",
                max_tokens=256,
            )
            assert content == "second try"
            first = _post_call(mock_post, 0)[1]
            second = _post_call(mock_post, 1)[1]
            assert first["max_output_tokens"] == 256
            assert second["max_output_tokens"] == 1024  # legacy inflation: max(1024, 256*4)
            assert "max_tokens" not in second


class TestChatStyleUnchanged:
    def test_default_style_keeps_chat_endpoint_and_no_ua_override(self, monkeypatch):
        monkeypatch.delenv("RAGIN_LLM_API_STYLE", raising=False)
        monkeypatch.delenv("RAGIN_LLM_USER_AGENT", raising=False)
        resp = MagicMock()
        resp.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "hi"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        with patch("requests.post") as mock_post:
            mock_post.return_value = resp
            client = GatewayClient(gateway_url="https://gw.example/v1", api_key="k")
            content, _ = client.generate(messages=[{"role": "user", "content": "hi"}], model="m", max_tokens=16)
            url, payload, headers = _post_call(mock_post)
            assert url == "https://gw.example/v1/chat/completions"
            assert payload["messages"] == [{"role": "user", "content": "hi"}]
            assert payload["max_tokens"] == 16
            assert payload["temperature"] == 0.3
            assert "User-Agent" not in headers
            assert content == "hi"

    def test_invalid_style_is_rejected(self, monkeypatch):
        monkeypatch.setenv("RAGIN_LLM_API_STYLE", "bogus")
        with pytest.raises(ValueError):
            GatewayClient(gateway_url="https://gw.example", api_key="k")


class TestContractVsTransport:
    def test_contract_fails_closed_when_transport_cannot_send_decoding(self, monkeypatch):
        """A contract asserts temperature/top_p on the wire; Responses refuses
        them. Serving anyway would report a contract the provider never got,
        so the client must refuse before the first request."""
        monkeypatch.setenv("RAGIN_LLM_API_STYLE", "responses")
        monkeypatch.delenv("RAGIN_LLM_USER_AGENT", raising=False)
        from ragin.gateway.generation import GenerationConfig, GenerationConfigError

        contract = GenerationConfig(
            model="gpt-6.1-sol",
            temperature=0.0,
            max_tokens=64,
            top_p=1.0,
            seed=None,
            seed_status="EXPLICITLY_UNSUPPORTED",
            max_retries=0,
        )
        with patch("requests.post") as mock_post:
            client = GatewayClient(gateway_url="https://gw.example", api_key="k", generation_config=contract)
            with pytest.raises(GenerationConfigError, match="cannot send"):
                client.generate(messages=[{"role": "user", "content": "hi"}], max_tokens=64)
            mock_post.assert_not_called()

    def test_chat_transport_still_enforces_the_contract(self, monkeypatch):
        monkeypatch.delenv("RAGIN_LLM_API_STYLE", raising=False)
        monkeypatch.delenv("RAGIN_LLM_USER_AGENT", raising=False)
        from ragin.gateway.generation import GenerationConfig

        contract = GenerationConfig(
            model="gpt-6.1-sol",
            temperature=0.0,
            max_tokens=64,
            top_p=1.0,
            seed=None,
            seed_status="EXPLICITLY_UNSUPPORTED",
            max_retries=0,
        )
        resp = MagicMock()
        resp.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        with patch("requests.post") as mock_post:
            mock_post.return_value = resp
            client = GatewayClient(gateway_url="https://gw.example", api_key="k", generation_config=contract)
            content, _ = client.generate(messages=[{"role": "user", "content": "hi"}])
            payload = _post_call(mock_post)[1]
            assert content == "ok"
            assert payload["temperature"] == 0.0
            assert payload["top_p"] == 1.0
