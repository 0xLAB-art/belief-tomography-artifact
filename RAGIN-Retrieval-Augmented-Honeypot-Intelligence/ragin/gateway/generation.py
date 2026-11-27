"""Versioned, validated generation/decoding contract for serving.

This module makes the previously *proposed* arm generator settings enforceable
without changing the legacy default path. It is deliberately transport-neutral:
it produces a validated :class:`GenerationConfig`, a canonical digest, and a
credential-free snapshot. :class:`ragin.gateway.client.GatewayClient` consumes
the config so the configured decoding values reach every generated HTTP
request.

Activation is opt-in and explicit:

* ``RAGIN_GENERATION_CONTRACT=1`` enables the contract. Without it this module
  returns ``None`` and the legacy call-site defaults are preserved.
* ``RAGIN_GENERATION_CONFIG_PATH`` points at a JSON object with the same fields
  as the environment variables below. The file wins over the individual vars.
* Individual variables (used when no config file is configured):

  - ``RAGIN_GEN_MODEL`` (required; the caller chooses the model)
  - ``RAGIN_GEN_TEMPERATURE`` (required; finite, ``0.0 <= t <= 2.0``)
  - ``RAGIN_GEN_MAX_TOKENS`` (required; integer ``1..131072``)
  - ``RAGIN_GEN_TOP_P`` (required; finite, ``0.0 < p <= 1.0``)
  - ``RAGIN_GEN_SEED`` (optional integer) **or**
    ``RAGIN_GEN_SEED_STATUS`` set to ``EXPLICITLY_OMITTED`` /
    ``EXPLICITLY_UNSUPPORTED``. A seed omission must be declared before the
    run; it is never inferred after an outcome.
  - ``RAGIN_GEN_MAX_RETRIES`` (required; integer ``0..3``). This is the fixed
    transport retry count; retries replay the same payload (same model,
    temperature, top_p, max_tokens, and seed).

Model exposure mode is separately opt-in through
``RAGIN_REQUIRE_MODEL_EXPOSURE=1``; see :func:`require_model_exposure`.

Error messages name the offending *field* only. They never interpolate a
configured value, file path, endpoint URL, or credential.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

CONTRACT_SCHEMA = "ragin.generation.contract.v1"
CONTRACT_VERSION = "generation-contract-v1"
OBSERVATION_SCHEMA = "ragin.generation.observation.v1"

SEED_EXPLICIT = "EXPLICIT"
SEED_OMITTED = "EXPLICITLY_OMITTED"
SEED_UNSUPPORTED = "EXPLICITLY_UNSUPPORTED"
_SEED_STATUSES = {SEED_EXPLICIT, SEED_OMITTED, SEED_UNSUPPORTED}

# Model identifiers are provider-opaque, but they must not be URLs or carry
# whitespace/control characters (which could smuggle a token into a log line).
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,255}$")

_MAX_TOKENS_LIMIT = 131_072
_MAX_RETRIES_LIMIT = 3
_SEED_MIN = -(2**63)
_SEED_MAX = 2**63 - 1

_TRUTHY = {"1", "true", "yes", "on"}


class GenerationConfigError(ValueError):
    """The requested generation/decoding contract is unresolved or invalid."""


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in _TRUTHY


def require_model_exposure(environ: Mapping[str, str] | None = None) -> bool:
    """Return True when the research model-exposure mode is explicitly enabled."""
    env = environ if environ is not None else os.environ
    return _truthy(env.get("RAGIN_REQUIRE_MODEL_EXPOSURE"))


def contract_enabled(environ: Mapping[str, str] | None = None) -> bool:
    env = environ if environ is not None else os.environ
    return _truthy(env.get("RAGIN_GENERATION_CONTRACT"))


def _field_error(field: str, detail: str) -> GenerationConfigError:
    return GenerationConfigError(f"invalid generation contract: {field} {detail}")


def _as_int(value: Any, field: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _field_error(field, "must be an integer")
    if value < minimum or value > maximum:
        raise _field_error(field, f"must be between {minimum} and {maximum}")
    return value


def _as_float(value: Any, field: str, *, minimum: float, maximum: float, exclusive_min: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _field_error(field, "must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise _field_error(field, "must be a finite number")
    in_range = number > minimum if exclusive_min else number >= minimum
    if not in_range or number > maximum:
        comparator = ">" if exclusive_min else ">="
        raise _field_error(field, f"must be {comparator} {minimum} and <= {maximum}")
    return number


def _as_model(value: Any) -> str:
    if not isinstance(value, str):
        raise _field_error("model", "must be a non-empty string")
    model = value.strip()
    if not model:
        raise _field_error("model", "is unresolved")
    if "://" in model:
        raise _field_error("model", "must not be a URL")
    if not _MODEL_RE.fullmatch(model):
        raise _field_error("model", "has an unsupported identifier format")
    return model


def _resolve_seed(seed_value: Any, seed_status_value: Any) -> tuple[int | None, str]:
    """Resolve seed + explicit status without inferring omission from outcomes."""
    has_seed = seed_value is not None and seed_value != ""
    status_raw = seed_status_value
    status = status_raw.strip().upper() if isinstance(status_raw, str) and status_raw.strip() else None
    if status is not None and status not in _SEED_STATUSES:
        raise _field_error("seed_status", "must be EXPLICIT, EXPLICITLY_OMITTED, or EXPLICITLY_UNSUPPORTED")
    if has_seed:
        seed = _as_int(seed_value, "seed", minimum=_SEED_MIN, maximum=_SEED_MAX)
        if status is not None and status != SEED_EXPLICIT:
            raise _field_error("seed_status", "conflicts with an explicit seed")
        return seed, SEED_EXPLICIT
    if status in (SEED_OMITTED, SEED_UNSUPPORTED):
        return None, status
    raise _field_error(
        "seed",
        "is unresolved: set RAGIN_GEN_SEED or declare RAGIN_GEN_SEED_STATUS "
        f"as {SEED_OMITTED}/{SEED_UNSUPPORTED} before the run",
    )


@dataclass(frozen=True)
class GenerationConfig:
    """A validated, immutable decoding contract.

    ``source`` is provenance for the snapshot only; it is not part of the
    decoding digest, so the same values resolve to the same digest whether they
    came from a native object, a JSON file, or the environment.
    """

    model: str
    temperature: float
    max_tokens: int
    top_p: float
    seed: int | None
    seed_status: str
    max_retries: int
    source: str = "UNKNOWN"
    schema: str = CONTRACT_SCHEMA

    def __post_init__(self) -> None:
        model = _as_model(self.model)
        temperature = _as_float(self.temperature, "temperature", minimum=0.0, maximum=2.0)
        max_tokens = _as_int(self.max_tokens, "max_tokens", minimum=1, maximum=_MAX_TOKENS_LIMIT)
        top_p = _as_float(self.top_p, "top_p", minimum=0.0, maximum=1.0, exclusive_min=True)
        max_retries = _as_int(
            self.max_retries, "max_retries", minimum=0, maximum=_MAX_RETRIES_LIMIT
        )
        seed, seed_status = _resolve_seed(self.seed, self.seed_status)
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "temperature", temperature)
        object.__setattr__(self, "max_tokens", max_tokens)
        object.__setattr__(self, "top_p", top_p)
        object.__setattr__(self, "max_retries", max_retries)
        object.__setattr__(self, "seed", seed)
        object.__setattr__(self, "seed_status", seed_status)

    # -- canonical, credential-free representations -------------------------

    def decoding_payload(self) -> dict[str, Any]:
        """The decoding fields that MUST accompany every generated request."""
        payload: dict[str, Any] = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
        }
        if self.seed_status == SEED_EXPLICIT and self.seed is not None:
            payload["seed"] = self.seed
        elif self.seed_status == SEED_UNSUPPORTED:
            # Explicitly unsupported seeds are represented as an explicit null
            # so the contract declares the decision, rather than inferring it.
            payload["seed"] = None
        return payload

    def canonical(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "seed": self.seed,
            "seed_status": self.seed_status,
            "max_retries": self.max_retries,
        }

    @property
    def config_sha256(self) -> str:
        material = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def snapshot(self) -> dict[str, Any]:
        """Credential-free effective-config snapshot for health/metadata."""
        return {
            "version": CONTRACT_VERSION,
            **self.canonical(),
            "config_sha256": self.config_sha256,
            "source": self.source,
            "enforced": True,
        }

    @staticmethod
    def request_digest(request_payload: Mapping[str, Any]) -> str:
        """Digest of the generation-relevant fields actually placed on the wire."""
        fields = ("model", "temperature", "max_tokens", "top_p", "seed", "stream")
        material = {key: request_payload.get(key) for key in fields if key in request_payload}
        encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _config_from_mapping(raw: Mapping[str, Any], *, source: str) -> GenerationConfig:
    allowed = {
        "model",
        "temperature",
        "max_tokens",
        "top_p",
        "seed",
        "seed_status",
        "max_retries",
    }
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise GenerationConfigError(
            "invalid generation contract: unknown field(s) present (values not shown)"
        )
    for field in ("model", "temperature", "max_tokens", "top_p", "max_retries"):
        if field not in raw:
            raise _field_error(field, "is unresolved")
    return GenerationConfig(
        model=raw["model"],
        temperature=raw["temperature"],
        max_tokens=raw["max_tokens"],
        top_p=raw["top_p"],
        seed=raw.get("seed"),
        seed_status=raw.get("seed_status"),
        max_retries=raw["max_retries"],
        source=source,
    )


def _parse_int_text(value: str, field: str) -> int:
    text = value.strip()
    try:
        return int(text, 10)
    except (TypeError, ValueError) as exc:
        raise _field_error(field, "must be an integer") from exc


def _parse_float_text(value: str, field: str) -> float:
    text = value.strip()
    try:
        return float(text)
    except (TypeError, ValueError) as exc:
        raise _field_error(field, "must be a finite number") from exc


def _config_from_env(env: Mapping[str, str], *, source: str) -> GenerationConfig:
    def required(name: str, field: str) -> str:
        value = str(env.get(name, "")).strip()
        if not value:
            raise _field_error(field, f"is unresolved (set {name})")
        return value

    model = required("RAGIN_GEN_MODEL", "model")
    temperature = _parse_float_text(required("RAGIN_GEN_TEMPERATURE", "temperature"), "temperature")
    max_tokens = _parse_int_text(required("RAGIN_GEN_MAX_TOKENS", "max_tokens"), "max_tokens")
    top_p = _parse_float_text(required("RAGIN_GEN_TOP_P", "top_p"), "top_p")
    max_retries = _parse_int_text(required("RAGIN_GEN_MAX_RETRIES", "max_retries"), "max_retries")

    seed_raw = str(env.get("RAGIN_GEN_SEED", "")).strip()
    seed: int | None = _parse_int_text(seed_raw, "seed") if seed_raw else None
    seed_status = str(env.get("RAGIN_GEN_SEED_STATUS", "")).strip() or None
    if seed is not None and seed_status is None:
        seed_status = SEED_EXPLICIT
    return GenerationConfig(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        seed=seed,
        seed_status=seed_status,
        max_retries=max_retries,
        source=source,
    )


def resolve_generation_config(
    explicit: GenerationConfig | None = None,
    environ: Mapping[str, str] | None = None,
) -> GenerationConfig | None:
    """Resolve the active generation contract.

    Resolution order:
      1. an explicit native :class:`GenerationConfig` (caller-owned);
      2. ``RAGIN_GENERATION_CONFIG_PATH`` JSON when ``RAGIN_GENERATION_CONTRACT``
         is enabled;
      3. individual ``RAGIN_GEN_*`` environment variables.

    Returns ``None`` when the contract is not enabled and no explicit config was
    supplied, which preserves the legacy path. An enabled but unresolved or
    invalid contract raises :class:`GenerationConfigError`; it never silently
    degrades to defaults.
    """
    env = environ if environ is not None else os.environ
    if explicit is not None:
        if not isinstance(explicit, GenerationConfig):
            raise GenerationConfigError("invalid generation contract: explicit config has the wrong type")
        # Re-run validation through the dataclass in case a subclass/attacker
        # bypassed __post_init__.
        return GenerationConfig(
            model=explicit.model,
            temperature=explicit.temperature,
            max_tokens=explicit.max_tokens,
            top_p=explicit.top_p,
            seed=explicit.seed,
            seed_status=explicit.seed_status,
            max_retries=explicit.max_retries,
            source=explicit.source or "EXPLICIT_NATIVE",
        )
    if not contract_enabled(env):
        return None

    path = str(env.get("RAGIN_GENERATION_CONFIG_PATH", "")).strip()
    if path:
        try:
            with open(path, encoding="utf-8") as handle:
                raw = json.load(handle)
        except OSError as exc:
            raise GenerationConfigError(
                "invalid generation contract: configured config file could not be read"
            ) from exc
        except json.JSONDecodeError as exc:
            raise GenerationConfigError(
                "invalid generation contract: configured config file is not valid JSON"
            ) from exc
        if not isinstance(raw, dict):
            raise GenerationConfigError("invalid generation contract: config file must be a JSON object")
        return _config_from_mapping(raw, source="ENV_CONFIG_FILE")

    return _config_from_env(env, source="ENV_VARS")
