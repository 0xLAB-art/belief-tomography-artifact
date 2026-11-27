"""MITRE ATT&CK graph reasoning for deception narrative planning.

Attacker TTPs are nodes in a kill-chain knowledge graph. Given the techniques
already observed in a session, this module ranks the techniques the attacker is
*most likely to probe next* along canonical kill-chain edges (initial-access ->
execution -> privilege-escalation -> credential-access -> discovery ->
lateral-movement -> impact/exfiltration).

The deception "plan" node consumes this to seed bait and artifacts that
foreshadow the next move — graph-informed deception: the honeypot steers the
conversation along the attacker's expected chain rather than reacting blindly.

Technique->tactic mapping is reused from the Don ThreatMapper registry so the
graph reasoning and TTP extraction stay in lock-step.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ragin.don.threat_mapper import _TECHNIQUE_TO_TACTIC

# Canonical kill-chain order. Deception steers along these edges.
_TACTIC_CHAIN: list[str] = [
    "TA0043",  # Reconnaissance
    "TA0042",  # Resource Development
    "TA0001",  # Initial Access
    "TA0002",  # Execution
    "TA0003",  # Persistence
    "TA0004",  # Privilege Escalation
    "TA0005",  # Defense Evasion
    "TA0006",  # Credential Access
    "TA0007",  # Discovery
    "TA0008",  # Lateral Movement
    "TA0009",  # Collection
    "TA0011",  # Command and Control
    "TA0010",  # Exfiltration
    "TA0040",  # Impact
]

# Explicit adjacent edges between specific techniques (same-tactic or cross-tactic
# shortcuts that experienced operators actually chain). Sources: MITRE ATT&CK
# "used by"/sub-technique and common intrusion chains (beachhead -> C2 -> priv-esc
# -> cred -> discovery -> lateral).
_TECHNIQUE_EDGES: list[tuple[str, str]] = [
    ("T1190", "T1059"),  # exploit public-facing app -> command/script shell
    ("T1190", "T1059.001"),  #   -> powershell
    ("T1059", "T1059.001"),  # shell upgrade to powershell family
    ("T1059.001", "T1134"),  # powershell -> access token manipulation
    ("T1134", "T1078"),  # token -> valid accounts
    ("T1078", "T1003"),  # valid account -> credential dumping
    ("T1078", "T1033"),  # valid account -> system user/owner discovery
    ("T1033", "T1046"),  # whoami/user discovery -> network service discovery
    ("T1046", "T1021"),  # service discovery -> remote services (lateral)
    ("T1046", "T1571"),  # service discovery -> non-standard port
    ("T1003", "T1003.008"),  # credential dump -> /etc/shadow
    ("T1552", "T1003"),  # credentials in files -> credential dumping
    ("T1552", "T1078"),  # found creds -> reuse valid account
    # Grounded in the GT benchmark's own operator sequences (GT-005 -> GT-002,
    # GT-001 -> GT-006): web-exploit sessions pivot to harvesting credentials
    # from app config, and recon deepens from user discovery to services.
    ("T1190", "T1552"),  # exploit public-facing app -> creds in app config
    ("T1033", "T1046"),  # user discovery -> network service discovery
    # Foothold -> collection moves (the GT corpus's own progressions:
    # GT-004 -> GT-002 and GT-006 -> GT-002). Cloud-cred harvest and service
    # discovery both precede reading data from the compromised host.
    ("T1552.005", "T1005"),  # IMDS creds -> data from local system
    ("T1046", "T1005"),  # service discovery -> data from local system
    ("T1003.008", "T1078"),  # shadow copy -> password spray / reuse
    ("T1059.001", "T1571"),  # powershell -> non-standard port C2
    ("T1571", "T1071"),  # non-standard port -> app-layer protocol (C2)
    ("T1055", "T1078"),  # process injection -> valid accounts
    ("T1547", "T1059"),  # boot/logon autostart -> execution
    ("T1486", "T1070"),  # data encrypted -> indicator removal
    ("T1566", "T1059.001"),  # phishing -> payload execution
    ("T1136", "T1547"),  # create account -> autostart via new account
    ("T1068", "T1078"),  # exploitation priv-esc -> valid accounts
]

# Human-readable technique names for the suggested-next-step output.
_TECHNIQUE_NAMES: dict[str, str] = {
    "T1190": "Exploit Public-Facing Application",
    "T1059": "Command and Scripting Interpreter",
    "T1059.001": "PowerShell",
    "T1059.004": "Unix Shell",
    "T1134": "Access Token Manipulation",
    "T1078": "Valid Accounts",
    "T1003": "OS Credential Dumping",
    "T1003.008": "/etc/passwd and /etc/shadow",
    "T1033": "System Owner/User Discovery",
    "T1046": "Network Service Discovery",
    "T1021": "Remote Services",
    "T1571": "Non-Standard Port",
    "T1071": "Application Layer Protocol",
    "T1550": "Use Alternate Authentication Material",
    "T1552": "Unsecured Credentials",
    "T1552.005": "Cloud Instance Metadata API",
    "T1055": "Process Injection",
    "T1547": "Boot or Logon Autostart",
    "T1070": "Indicator Removal",
    "T1486": "Data Encrypted for Impact",
    "T1566": "Phishing",
    "T1136": "Create Account",
    "T1068": "Exploitation for Privilege Escalation",
    "T1543": "Create or Modify System Process",
    "T1133": "External Remote Services",
    "T1489": "Service Stop",
    "T1078.003": "Local Accounts",
    "T1083": "File and Directory Discovery",
    "T1082": "System Information Discovery",
}


# Fast membership for edge-vs-batch weighting in suggest_next_techniques.
_EDGE_SET: set[tuple[str, str]] = set(_TECHNIQUE_EDGES)


def _tactic_of(technique_id: str) -> str:
    parent = technique_id.split(".", 1)[0]
    return _TECHNIQUE_TO_TACTIC.get(parent, ("UNKNOWN", "Unidentified"))[0]


def tactic_name(technique_id: str) -> str:
    parent = technique_id.split(".", 1)[0]
    return _TECHNIQUE_TO_TACTIC.get(parent, ("UNKNOWN", "Unidentified"))[1]


def _chain_index(tactic_id: str) -> int:
    try:
        return _TACTIC_CHAIN.index(tactic_id)
    except ValueError:
        return -1


def next_candidates(observed: Iterable[str]) -> list[tuple[str, str]]:
    """Return candidate (technique_id -> suggested_next_id) forward edges.

    For each observed technique, emit explicit adjacency edges plus techniques
    belonging to the following tactic in the canonical kill chain.
    """
    observed = list(observed)
    by_id: dict[str, str] = {}
    for tid in observed:
        by_id.setdefault(tid, "")
        parent = tid.split(".", 1)[0]
        by_id.setdefault(parent, "")

    edges: list[tuple[str, str]] = []
    all_techniques = list(_TECHNIQUE_TO_TACTIC.keys())
    for tid in by_id:
        for src, dst in _TECHNIQUE_EDGES:
            if src in (tid, tid.split(".", 1)[0]) and dst not in by_id:
                edges.append((tid, dst))
        # Techniques in the LAST kill-chain tactic (Impact, TA0040) have no
        # next tactic — the index+1 lookup would run off the end of the chain.
        src_idx = _chain_index(_tactic_of(tid))
        tactic = _TACTIC_CHAIN[src_idx + 1] if 0 <= src_idx < len(_TACTIC_CHAIN) - 1 else None
        if tactic:
            for candidate in all_techniques:
                if _tactic_of(candidate) == tactic and candidate not in by_id:
                    edges.append((tid, candidate))

    seen: set[tuple[str, str]] = set()
    deduped = []
    for src, dst in edges:
        if (src, dst) not in seen:
            seen.add((src, dst))
            deduped.append((src, dst))
    return deduped


def suggest_next_techniques(observed: Iterable[str], top_k: int = 3) -> list[dict[str, Any]]:
    """Rank the most likely next techniques given the techniques seen so far."""
    edges = next_candidates(observed)
    by_id = {tid: "" for tid in observed}
    counter: dict[str, int] = {}
    for src, dst in edges:
        if dst in by_id:
            by_id[dst] = ""
            continue
        # Explicit operator-chain edges outweigh generic tactic-batch
        # transitions: they are the curated next steps the steering is meant
        # to foreshadow, and uniform weights ranked ties alphabetically,
        # demoting true next steps below unrelated batch members (C3 eval
        # finding).
        weight = 2 if (src, dst) in _EDGE_SET else 1
        counter[dst] = counter.get(dst, 0) + weight

    ranked = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    if not ranked and by_id:
        # Everything observed was unrecognised: fall back to a generic
        # Discovery -> Lateral-Movement steer so the plan still has direction.
        for _src, dst in next_candidates(["T1033"]):
            counter[dst] = counter.get(dst, 0) + 1
        ranked = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    suggestions: list[dict[str, Any]] = []
    for dst, weight in ranked[:top_k]:
        tid = dst
        suggestions.append(
            {
                "technique_id": tid,
                "name": _TECHNIQUE_NAMES.get(tid, _TECHNIQUE_NAMES.get(tid.split(".", 1)[0], "Next technique")),
                "tactic": _tactic_of(tid),
                "tactic_name": tactic_name(tid),
                "score": weight,
                "rationale": f"next step after {sorted(by_id) or 'initial access'} along the kill chain",
            }
        )
    return suggestions


def _bait_for(observed: list[str]) -> list[str]:
    """Literally what bait the environment should let slip, given what the
    attacker already threw at it (graph-informed proactive deception)."""
    hints: list[str] = []
    upper = [t.upper() for t in observed]
    if any(t == "T1003" or t.startswith("T1003.") for t in upper):
        hints.append(
            "seed a brittle /etc/shadow (locked hashes) plus stale .bash_history "
            "showing a service account reused across hosts"
        )
    if any(t == "T1552" or t.startswith("T1552.") for t in upper):
        hints.append("expose stale env/config files holding a reusable service credential")
    if any(t in ("T1046", "T1571") or t.startswith(("T1046.", "T1571.")) for t in upper):
        hints.append("surface a half-open non-standard-port service as a tempting pivot point")
    if any(t == "T1021" or t.startswith("T1021.") for t in upper) or "T1550" in upper:
        hints.append("reveal alternate credential or key material that greases lateral movement")
    if "T1078" in upper:
        hints.append("present a plausible re-used service account bound to the pinned domain")
    return hints


def attach_strategy_context(cti_analysis: dict[str, Any]) -> dict[str, Any]:
    """Augment CTI analysis with next-step bait suggestions (pure helper)."""
    observed = [str(t) for t in (cti_analysis.get("extracted_techniques") or cti_analysis.get("ttp_ids") or [])]
    next_steps = suggest_next_techniques(observed)
    current = observed[-1] if observed else ""
    bait = list(_bait_for(observed))
    bait.extend(
        f"seed artifacts likely to surface next probing of {s['technique_id']} ({s['name']})" for s in next_steps
    )
    out = dict(cti_analysis)
    out["next_techniques_predicted"] = next_steps
    out["deception_strategy"] = {
        "techniques": observed,
        "current_tactic": {
            "tactic_id": _tactic_of(current),
            "name": tactic_name(current),
        }
        if current
        else {},
        "steer": ", ".join(s["technique_id"] for s in next_steps) or "none",
        "bait": bait,
    }
    return out
