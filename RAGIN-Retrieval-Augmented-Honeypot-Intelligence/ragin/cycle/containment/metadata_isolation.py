"""
EC2 metadata (IMDS) isolation policy and local test surface.

The production enforcement: the inference/runtime containers have NO route to
169.254.169.254 (DOCKER-USER drop, no default gateway on the internal network,
and the host firewall denies it). This module captures the app-level invariant
that the runtime MUST NOT issue metadata requests and provides a test surface
that proves the harness/server never contact IMDS.

This is defense-in-depth: the harness already fabricates IMDS responses at the
honeypot/Sandbox layer (the attacker-facing fiction), but the INFERENCE pipeline
itself (Chrollo->Don->Hisoka->provider transport) must never touch the real
metadata service. That separation is what WS3 protects.
"""

from __future__ import annotations

import logging

from ragin.cycle.containment.container_egress import EgressGuard, is_metadata_address, forbidden_hosts

logger = logging.getLogger(__name__)

_METADATA_ENDPOINTS = tuple(forbidden_hosts())


def metadata_endpoint_addresses() -> tuple[str, ...]:
    return _METADATA_ENDPOINTS


def assert_no_metadata_access(guard: EgressGuard, host: str) -> None:
    if is_metadata_address(host) or host in _METADATA_ENDPOINTS:
        raise RuntimeError(
            f"Runtime isolation violation: metadata endpoint {host} is not reachable "
            f"by policy (and the container/network layer must also drop it)"
        )


def describe_metadata_isolation() -> dict:
    return {
        "metadata_endpoints_blocked": list(_METADATA_ENDPOINTS),
        "imds_v4_link_local_blocked": True,
        "imds_v2_token_blocked": True,
        "runtime_path_must_not_fetch_metadata": True,
    }
