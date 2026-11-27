from __future__ import annotations

from unittest.mock import patch

import pytest

from ragin.transport.mtls import (
    MTLSConfigError,
    build_server_context,
    build_server_context_from_env,
    peer_certificate_authorized,
    peer_certificate_identities,
)


def test_peer_authorization_uses_san_not_common_name() -> None:
    certificate = {
        "subject": ((("commonName", "ragin-edge"),),),
        "subjectAltName": (("URI", "spiffe://ragin/edge"),),
    }
    assert peer_certificate_identities(certificate) == frozenset({"spiffe://ragin/edge"})
    assert peer_certificate_authorized(certificate, {"spiffe://ragin/edge"})
    assert not peer_certificate_authorized(certificate, {"ragin-edge"})


def test_missing_peer_certificate_is_rejected() -> None:
    assert not peer_certificate_authorized(None, {"spiffe://ragin/edge"})


def test_mtls_environment_requires_a_complete_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAGIN_MTLS_REQUIRED", "1")
    monkeypatch.delenv("RAGIN_MTLS_CERT_FILE", raising=False)
    monkeypatch.delenv("RAGIN_MTLS_KEY_FILE", raising=False)
    monkeypatch.delenv("RAGIN_MTLS_CA_FILE", raising=False)
    with pytest.raises(MTLSConfigError, match="RAGIN_MTLS_CERT_FILE"):
        build_server_context_from_env()


def test_mtls_context_requires_existing_certificate_files(tmp_path) -> None:
    with pytest.raises(MTLSConfigError, match="does not exist"):
        build_server_context(
            certificate_file=str(tmp_path / "server.crt"),
            private_key_file=str(tmp_path / "server.key"),
            ca_file=str(tmp_path / "ca.crt"),
        )


def test_no_profile_keeps_offline_http_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAGIN_MTLS_REQUIRED", raising=False)
    for name in ("RAGIN_MTLS_CERT_FILE", "RAGIN_MTLS_KEY_FILE", "RAGIN_MTLS_CA_FILE"):
        monkeypatch.delenv(name, raising=False)
    assert build_server_context_from_env() is None


def test_server_creation_fails_closed_without_mtls_context(monkeypatch: pytest.MonkeyPatch) -> None:
    import ragin.server_v2 as server

    original_key = server.API_KEY
    original_require_auth = server.REQUIRE_AUTH
    server.API_KEY = "service-key"
    server.REQUIRE_AUTH = True
    monkeypatch.setenv("RAGIN_MTLS_REQUIRED", "1")
    monkeypatch.setenv("RAGIN_MTLS_ALLOWED_IDENTITIES", "spiffe://ragin/edge")
    for name in ("RAGIN_MTLS_CERT_FILE", "RAGIN_MTLS_KEY_FILE", "RAGIN_MTLS_CA_FILE"):
        monkeypatch.delenv(name, raising=False)
    try:
        with patch.object(server, "_init_pipeline"), pytest.raises(MTLSConfigError):
            server.create_app(mode="pipeline")
    finally:
        server.API_KEY = original_key
        server.REQUIRE_AUTH = original_require_auth
