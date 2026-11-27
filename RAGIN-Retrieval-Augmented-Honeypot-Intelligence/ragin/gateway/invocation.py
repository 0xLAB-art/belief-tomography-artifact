"""Declared-invocation validation: fail explicitly, never substitute a backend.

The run contract declares how a model arm is supposed to invoke its generator
(``generation.invocation.kind``). Nothing in the serving path read that
declaration before this module existed, so a run whose declared local model
was missing would have silently fallen through to whatever
``RAGIN_LLM_BASE_URL`` happened to be — a template fallback, an unrelated
loopback bridge, or (as observed on this machine) an Ollama *cloud alias*
that egresses to a provider.

This module makes the declaration enforceable and is strictly opt-in:

* No ``RAGIN_INVOCATION_KIND`` in the environment → returns ``None`` and the
  legacy path is untouched (every existing test and script behaves as before).
* A declared kind is validated eagerly at generator construction. An invalid
  declaration raises :class:`InvocationContractError`; a declaration whose
  model/backend is unavailable raises :class:`ModelInvocationUnavailableError`.
  Neither exception is caught here, and no alternative backend, model, or
  fixture is ever substituted — the caller must fix the declaration.
* ``EXTERNAL_PROVIDER`` is refused unless ``RAGIN_ALLOW_EXTERNAL_PROVIDER=1``
  is set explicitly. An unset flag never means "allowed".

Kinds mirror ``run_contract_v1.json``'s ``generation.invocation.kind``:
``LOCAL_FILE_MODEL``, ``LOCAL_HTTP_LOOPBACK``, ``EXTERNAL_PROVIDER``.

No network traffic is produced unless ``RAGIN_INVOCATION_PROBE=1`` is set,
in which case only a TCP connect to the *declared loopback* endpoint is made.
A probe never contacts a provider: it refuses before connecting if the model
identifier looks like an Ollama ``:cloud`` alias.
"""

from __future__ import annotations

import os
import socket
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ragin.evaluation.ablation_contract import LOOPBACK_HOSTS

INVOCATION_KIND_ENV = "RAGIN_INVOCATION_KIND"
INVOCATION_PATH_ENV = "RAGIN_INVOCATION_PATH"
INVOCATION_SHA_ENV = "RAGIN_INVOCATION_SHA256"
ALLOW_EXTERNAL_ENV = "RAGIN_ALLOW_EXTERNAL_PROVIDER"
PROBE_ENV = "RAGIN_INVOCATION_PROBE"

LOCAL_FILE_MODEL = "LOCAL_FILE_MODEL"
LOCAL_HTTP_LOOPBACK = "LOCAL_HTTP_LOOPBACK"
EXTERNAL_PROVIDER = "EXTERNAL_PROVIDER"
_KINDS = {LOCAL_FILE_MODEL, LOCAL_HTTP_LOOPBACK, EXTERNAL_PROVIDER}

# Ollama serves locally but transparently proxies `*:cloud` tags to a remote
# provider (12 such aliases are installed on this machine, all with zero local
# bytes). A declared local invocation must never reach one of those silently.
_CLOUD_ALIAS_SUFFIX = ":cloud"

_TRUTHY = {"1", "true", "yes", "on"}


class InvocationContractError(ValueError):
    """The declared invocation is invalid or ambiguous."""


class ModelInvocationUnavailableError(RuntimeError):
    """The declared local model/backend is not available; nothing substitutes it."""


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in _TRUTHY


def _model_identifier(env: Mapping[str, str]) -> str | None:
    for key in ("RAGIN_GEN_MODEL", "RAGIN_LLM_MODEL", "RAGIN_HISOKA_MODEL"):
        value = str(env.get(key, "")).strip()
        if value:
            return value
    return None


def _validate_local_file(env: Mapping[str, str]) -> dict[str, Any]:
    raw_path = str(env.get(INVOCATION_PATH_ENV, "")).strip()
    if not raw_path:
        raise ModelInvocationUnavailableError(
            f"{INVOCATION_KIND_ENV}={LOCAL_FILE_MODEL} requires {INVOCATION_PATH_ENV} "
            "to name the local model directory or file"
        )
    path = Path(raw_path).expanduser()
    if not path.exists():
        raise ModelInvocationUnavailableError(
            f"declared local model path does not exist: {path.name}"
        )
    # Verify identity WITHOUT loading weights: config presence, plus an
    # optional pinned SHA-256 for file checkpoints.
    if path.is_dir() and not (path / "config.json").is_file():
        raise ModelInvocationUnavailableError(
            "declared local model directory has no config.json (no loadable model identity)"
        )
    declared_sha = str(env.get(INVOCATION_SHA_ENV, "")).strip().lower()
    if declared_sha:
        if not path.is_file():
            raise InvocationContractError(
                f"{INVOCATION_SHA_ENV} pins a single file; the declared path is a directory"
            )
        import hashlib

        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != declared_sha:
            raise ModelInvocationUnavailableError(
                "declared local model file hash does not match the pinned digest"
            )
    model = _model_identifier(env)
    if model and model.lower().endswith(_CLOUD_ALIAS_SUFFIX):
        raise ModelInvocationUnavailableError(
            "declared model identifier is a remote cloud alias, not a local model"
        )
    return {
        "kind": LOCAL_FILE_MODEL,
        "path": str(path),
        "sha256_pinned": bool(declared_sha),
        "model": model,
    }


def _validate_loopback(env: Mapping[str, str]) -> dict[str, Any]:
    base_url = str(env.get("RAGIN_LLM_BASE_URL", "")).strip()
    if not base_url:
        raise ModelInvocationUnavailableError(
            f"{INVOCATION_KIND_ENV}={LOCAL_HTTP_LOOPBACK} requires RAGIN_LLM_BASE_URL"
        )
    parsed = urlparse(base_url if "://" in base_url else f"http://{base_url}")
    host = (parsed.hostname or "").strip()
    if host not in LOOPBACK_HOSTS:
        raise InvocationContractError(
            f"declared local loopback invocation but RAGIN_LLM_BASE_URL host is not loopback ({host!r}); "
            f"declare {EXTERNAL_PROVIDER} explicitly if a remote backend is intended"
        )
    model = _model_identifier(env)
    if model and model.lower().endswith(_CLOUD_ALIAS_SUFFIX):
        # Reachable over loopback, but the backend proxies to a provider:
        # exactly the silent-substitution case this gate exists to stop.
        raise ModelInvocationUnavailableError(
            "declared local model identifier is a remote cloud alias; a loopback "
            "endpoint in front of it is not local inference"
        )
    declaration: dict[str, Any] = {
        "kind": LOCAL_HTTP_LOOPBACK,
        "loopback_host": host,
        "model": model,
        "probe": False,
    }
    if _truthy(env.get(PROBE_ENV)):
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            with socket.create_connection((host, port), timeout=0.5):
                pass
        except OSError as exc:
            raise ModelInvocationUnavailableError(
                f"declared local loopback endpoint is not accepting connections ({type(exc).__name__})"
            ) from None
        declaration["probe"] = True
    return declaration


def validate_invocation(environ: Mapping[str, str] | None = None) -> dict[str, Any] | None:
    """Validate the declared invocation; ``None`` means undeclared (legacy).

    Raises :class:`InvocationContractError` for an invalid or ambiguous
    declaration and :class:`ModelInvocationUnavailableError` when the declared
    model/backend is not available. Never substitutes, never falls back, and
    (unless ``RAGIN_INVOCATION_PROBE=1``) never opens a socket.
    """
    env = environ if environ is not None else os.environ
    raw_kind = str(env.get(INVOCATION_KIND_ENV, "")).strip()
    if not raw_kind:
        return None
    if raw_kind not in _KINDS:
        raise InvocationContractError(
            f"{INVOCATION_KIND_ENV} must be one of {sorted(_KINDS)}; unknown declaration refused"
        )
    if raw_kind == LOCAL_FILE_MODEL:
        return _validate_local_file(env)
    if raw_kind == LOCAL_HTTP_LOOPBACK:
        return _validate_loopback(env)
    if not _truthy(env.get(ALLOW_EXTERNAL_ENV)):
        raise InvocationContractError(
            f"{INVOCATION_KIND_ENV}={EXTERNAL_PROVIDER} is refused: set "
            f"{ALLOW_EXTERNAL_ENV}=1 to authorize an external provider explicitly"
        )
    model = _model_identifier(env)
    return {"kind": EXTERNAL_PROVIDER, "authorized": True, "model": model}


def describe(declaration: dict[str, Any] | None) -> dict[str, Any]:
    """Credential-free provenance record for a serving/health trace."""
    if declaration is None:
        return {"declared": False, "kind": None, "status": "UNDECLARED_LEGACY_PATH"}
    return {
        "declared": True,
        "kind": declaration.get("kind"),
        "status": "DECLARED_AND_VALIDATED",
        "model": declaration.get("model"),
        "probe": declaration.get("probe", False),
    }
