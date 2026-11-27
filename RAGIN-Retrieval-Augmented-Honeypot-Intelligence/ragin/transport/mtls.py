from __future__ import annotations

import os
import ssl
from typing import Any


class MTLSConfigError(RuntimeError):
    pass


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise MTLSConfigError(f"{name} is required when mTLS is enabled")
    return value


def build_server_context(
    *,
    certificate_file: str,
    private_key_file: str,
    ca_file: str,
) -> ssl.SSLContext:
    for name, path in (
        ("certificate_file", certificate_file),
        ("private_key_file", private_key_file),
        ("ca_file", ca_file),
    ):
        if not os.path.isfile(path):
            raise MTLSConfigError(f"mTLS {name} does not exist")

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = False
    context.load_cert_chain(certfile=certificate_file, keyfile=private_key_file)
    context.load_verify_locations(cafile=ca_file)
    return context


def build_server_context_from_env() -> ssl.SSLContext | None:
    enabled = os.environ.get("RAGIN_MTLS_REQUIRED", "0").strip().lower() in {"1", "true", "yes", "on"}
    names = ("RAGIN_MTLS_CERT_FILE", "RAGIN_MTLS_KEY_FILE", "RAGIN_MTLS_CA_FILE")
    configured = [bool(os.environ.get(name, "").strip()) for name in names]
    if not enabled and not any(configured):
        return None
    if not enabled:
        raise MTLSConfigError("mTLS certificate variables are set but RAGIN_MTLS_REQUIRED is disabled")
    return build_server_context(
        certificate_file=_required_env(names[0]),
        private_key_file=_required_env(names[1]),
        ca_file=_required_env(names[2]),
    )


def peer_certificate_identities(certificate: dict[str, Any] | None) -> frozenset[str]:
    if not certificate:
        return frozenset()
    identities: set[str] = set()
    for kind, value in certificate.get("subjectAltName", ()):
        if kind in {"DNS", "IP Address", "URI"} and value:
            identities.add(str(value))
    return frozenset(identities)


def peer_certificate_authorized(
    certificate: dict[str, Any] | None,
    allowed_identities: frozenset[str] | set[str],
) -> bool:
    return bool(peer_certificate_identities(certificate) & set(allowed_identities))
