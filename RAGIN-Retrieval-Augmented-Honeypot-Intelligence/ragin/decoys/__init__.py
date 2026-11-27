"""Decoy services — wrappers around the base DecoyService for specific protocols.

Only the base abstraction and its manager are implemented so far; the
per-protocol services (HTTPDecoy, SSHDecoy, TelnetDecoy) are declared in
__all__ but not yet written. They raise on access so the package itself
stays importable.
"""

from typing import Any

from ragin.decoys.base import DecoyConfig, DecoyProtocol, DecoyService, DecoySession
from ragin.decoys.manager import DecoyManager

__all__ = [
    "DecoyService",
    "DecoyProtocol",
    "DecoyConfig",
    "DecoySession",
    "DecoyManager",
]


def __getattr__(name: str) -> Any:
    """Lazily expose the per-protocol decoys; they do not exist yet."""
    if name in ("HTTPDecoy", "SSHDecoy", "TelnetDecoy"):
        raise AttributeError(
            f"{name} is not implemented yet; only DecoyService subclasses in "
            "ragin.decoys.base (via a custom implementation) are available"
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
