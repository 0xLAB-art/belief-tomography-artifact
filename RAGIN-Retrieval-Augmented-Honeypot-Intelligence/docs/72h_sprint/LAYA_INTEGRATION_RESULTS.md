# Laya Integration Results

Status: **DEFERRED / NOT IMPLEMENTED**.

Laya is not integrated in this sprint. No local GPU inference endpoint was opened, no model was downloaded, and no attacker-facing path was connected to the workstation. The existing application contract keeps optional decision assessment separate from Hisoka generation and the deterministic verifier.

The required future contract is:

1. A provider-neutral assessment adapter returns a typed signal or `NO_SIGNAL`.
2. Timeout, refusal, disconnection, or malformed output returns `NO_SIGNAL`.
3. `NO_SIGNAL` never bypasses authentication, HITL, verification, fallback, or state-commit rules.
4. Laya-specific results are stored separately from historical JEV/OpenCode artifacts.

No Laya feasibility, latency, memory, or quality result is claimed. The sprint can proceed with deterministic baseline behavior while this optional provider remains absent.
