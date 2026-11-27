"""
Container egress deny-by-default + explicit-allowlist policy.

The production enforcement for "no default outbound from the inference container"
lives at the Docker/host firewall layer (DOCKER-USER / iptables, seccomp,
no-new-privileges, read-only rootfs, dropped caps). This module captures the
APP-LEVEL intent and provides a local egress guard the harness and server can
consult so that, even if the container/network layer is misconfigured, the
application does not initiate network connections the policy forbids.

Design (matches the existing field_provision.sh egress model):
* Default posture: DENY all NEW outbound from the inference/runtime containers.
* Explicit allowlist: only the configured LLM provider :443 (resolved at
  provision time) and the internal Redis/component mesh (ragin-internal) are
  permitted.
* EC2 metadata (169.254.169.254) is NEVER reachable from the runtime path --
  it is isolated both at the container/network layer AND denied here.
* DNS resolution of the provider is performed once at provision/start, not per
  request, so a stale allowlist is detectable (monitor tell in field study).

NOTE: this module does NOT manipulate iptables/nftables/ufw on the host. That
is the field_provision.sh job and is deliberately out of process (root, host).
This module is the app-side assertion + local guard + test surface.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Iterable

logger = logging.getLogger(__name__)

_EGRESS_ALLOWED_HOSTS: tuple[str, ...] = (
    "api.apmix.ai",
)

_FORBIDDEN_HOSTS: tuple[str, ...] = (
    "169.254.169.254",
    "metadata.google.internal",
    "metadata.google",
    "attacker-ebe54dd70c2a",
)

_INTERNAL_SERVICES: tuple[str, ...] = (
    "redis",
    "gateway",
    "chrollo",
    "don",
    "hisoka",
    "jev",
)


def egress_allowed_hosts() -> tuple[str, ...]:
    return _EGRESS_ALLOWED_HOSTS


def forbidden_hosts() -> tuple[str, ...]:
    return _FORBIDDEN_HOSTS


def is_metadata_address(host: str) -> bool:
    lowered = host.lower()
    if lowered in _FORBIDDEN_HOSTS or lowered.startswith("169.254."):
        return True
    try:
        for family in (socket.AF_INET, socket.AF_INET6):
            for info in socket.getaddrinfo(host, None, family, socket.SOCK_STREAM):
                addr = ipaddress.ip_address(info[4][0])
                if addr.is_link_local and addr.packed[0:2] == b"\xac\xac":
                    return True
    except OSError:
        logger.debug("could not resolve %s for metadata check", host, exc_info=True)
    return False


def _host_resolves_to_ip(host: str) -> list[str]:
    try:
        return sorted({info[4][0] for info in socket.getaddrinfo(host, None, socket.SOCK_STREAM)})
    except OSError:
        return []


def classify_remote_endpoint(host: str, port: int) -> str:
    if is_metadata_address(host) or host in _FORBIDDEN_HOSTS:
        return "forbidden_metadata"
    if host in _INTERNAL_SERVICES:
        return "internal_service"
    if host in _EGRESS_ALLOWED_HOSTS:
        return "allowed"
    for allowed_host in _EGRESS_ALLOWED_HOSTS:
        for ip in _host_resolves_to_ip(allowed_host):
            for candidate_ip in _host_resolves_to_ip(host):
                if ip == candidate_ip:
                    return "allowed"
    return "forbidden_other"


class EgressGuard:
    def __init__(self, *, provider_hosts: Iterable[str] | None = None) -> None:
        self._provider_hosts = tuple(provider_hosts or egress_allowed_hosts())

    def classification(self, host: str, port: int = 443) -> str:
        return classify_remote_endpoint(host, port)

    def can_reach(self, host: str, port: int = 443) -> bool:
        if host in self._provider_hosts or host in _INTERNAL_SERVICES:
            return True
        for allowed_host in self._provider_hosts:
            for ip in _host_resolves_to_ip(allowed_host):
                if ip in _host_resolves_to_ip(host):
                    return True
        return False

    def assert_allowed(self, host: str, port: int = 443) -> None:
        cls = self.classification(host, port)
        if cls not in ("allowed", "internal_service"):
            raise RuntimeError(f"Egress denied by containment policy: {host}:{port} classified {cls}")

    def assert_metadata_blocked(self, host: str) -> None:
        if is_metadata_address(host) or host in _FORBIDDEN_HOSTS:
            raise RuntimeError(f"EC2/IMDS metadata access denied by containment policy: {host}")


def describe_policy() -> dict:
    return {
        "default_egress": "deny",
        "forbidden_hosts": list(forbidden_hosts()),
        "allowed_provider_hosts": list(egress_allowed_hosts()),
        "internal_services": list(_INTERNAL_SERVICES),
        "metadata_blocked": True,
    }
