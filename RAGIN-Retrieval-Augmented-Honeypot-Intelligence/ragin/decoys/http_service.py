"""Unimplemented stub: HTTPDecoy (protocol HTTP).

This per-protocol decoy service was never written — the file has been an empty
placeholder since the initial "field validation wip" commit, and no full version
exists anywhere in the workspace (verified 2026-10-24). It is not imported by
ragin.decoys at runtime; ragin.decoys.__init__ documents that only the base
DecoyService abstraction and its manager are implemented. This stub exists so
the module is self-describing instead of a silent 0-byte file.
"""

__all__ = ["HTTPDecoy"]
