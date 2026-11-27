"""Host-level persistent fiction — cross-session consistency layer (plan #9).

Gap (TDSC → S&P, advisory #9): ``FictionGraph`` is session-scoped by
construction. Facts served and verified in session A die with it, so:

  - a RECONNECTING attacker (new session, same skill) can be served facts
    that contradict what they were told before — the per-session verifier
    re-seeds from identity and never sees session A's facts;
  - beyond-identity facts (a docker0 address, an extra listening port) are
    re-minted per session instead of staying stable across the attack;
  - a SIMULTANEOUS multi-session attacker can be told two different stories
    about the same box at the same wall-clock time;
  - a RETURNING attacker whose classification changed is seeded with a
    DIFFERENT pinned host (per-skill identities name different machines),
    which the per-session verifier cannot even notice.

This module adds a HOST-scoped fiction store over the session graph — the
same host key faces every session an attacker opens against it:

  - ``reconnect``  every session for the same host SHARES ONE graph
                   (reconnect = resume). Strictest consistency.
  - ``per_session  each session keeps its own graph, but every observed
                   draft is ALSO checked against the host-level facts
                   (verified-session promotion + cross-session
                   contradiction verification).

Verified-fact promotion: facts observed in a session that PASSED verification
are promoted into the host store (stable predicates only), so what the
attacker was already TOLD binds every future session on that host. Unverified
sessions promote nothing — consistent with the serve-gate philosophy.

The session graph itself is unchanged; the store is strictly additive
(default ``per_session``, the honest middle ground), so existing callers and
benchmarks behave identically until a store is installed.

Usage::

    store = HostFictionStore(host_key="10.0.0.12", policy="per_session")
    session_graph = store.session_graph("sess-1", identity=identity_for("novice"))
    ...  # generate/verify with session_graph as today
    store.promote_verified("sess-1")        # bind told-facts to the host
    result = store.verify("sess-2", text)   # cross-session check in session 2
    store.save(path); store = HostFictionStore.load(path)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ragin.graph.fiction import FictionGraph, _normalize_hostname  # noqa: F401

# Predicates the HOST binds across sessions. Superset of the graph's stable
# set: it additionally pins beyond-identity environment facts (extra
# interfaces/ports established by verified transcripts), which a per-session
# graph re-mints freely. Port predicates are stored under their own keys
# ("port:22", "port:5355") and all share the host-stable "port" family.
HOST_STABLE_PREDICATE_FAMILIES: frozenset[str] = frozenset({"os", "kernel", "hostname", "domain", "user", "ip", "port"})


def _is_host_stable(predicate: str) -> bool:
    # `ip:<iface>` scoped facts (interface addresses observed in `ip addr`)
    # are host-stable too — the beyond-identity drift class the per-session
    # graph cannot see (a re-minted docker0 address across sessions).
    return predicate in HOST_STABLE_PREDICATE_FAMILIES or predicate.startswith("port:") or predicate.startswith("ip:")


def _same_host_value(predicate: str, a: Any, b: Any, pinned_domain: str | None) -> bool:
    """FQDN-aware fact comparison across sessions, mirroring the session
    graph's ``_same_value``: `web-srv-01` and `web-srv-01.corp.local` are the
    SAME machine when the suffix is the pinned domain. Raw string comparison
    here false-flagged every draft that re-mentioned the host as an FQDN
    (`hostname -f`) after a prior session promoted the short-form identity
    seed — 26 deterministic fallback serves in the external-baseline
    hostfiction run (2026-09-27)."""
    if predicate == "hostname":
        na, nb = _normalize_hostname(str(a)), _normalize_hostname(str(b))
        if na == nb:
            return True
        short, long = (na, nb) if len(na) <= len(nb) else (nb, na)
        if long.startswith(short + "."):
            domain = (pinned_domain or "").lower().rstrip(".")
            return bool(domain) and long[len(short) + 1 :] == domain
        return False
    return str(a) == str(b)


@dataclass
class CrossSessionCheck:
    """Result of verifying a session's facts against the host store."""

    contradictions: list[dict[str, Any]] = field(default_factory=list)
    promoted: list[tuple[str, str, Any]] = field(default_factory=list)
    checked_against: int = 0  # host facts the session was checked against

    @property
    def consistent(self) -> bool:
        return not self.contradictions

    def to_dict(self) -> dict[str, Any]:
        return {
            "consistent": self.consistent,
            "contradictions": self.contradictions,
            "promoted": [{"subject": s, "predicate": p, "value": v} for s, p, v in self.promoted],
            "checked_against": self.checked_against,
        }


class HostFictionVerifier:
    """Verifier wrapper adding cross-session fact checks to C2.

    Wraps the standard ``FictionConsistencyVerifier``: the session-level
    checks run exactly as before, then the host store checks the response's
    observed facts against what PRIOR verified sessions on the same host
    established. A draft that passes all session checks but contradicts a
    previously SERVED fact is rejected — the cross-session gap closed.
    """

    def __init__(self, inner: Any, store: HostFictionStore) -> None:
        self._inner = inner
        self._store = store

    @property
    def profile(self) -> str:
        """Claim-contract profile of the wrapped verifier (legacy by default)."""
        return str(getattr(self._inner, "profile", "legacy"))

    def verify(self, response: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        result = self._inner.verify(response, ctx)
        session_id = str(ctx.get("session_id", "unknown"))
        # NOTE: host-identity consistency is enforced at PROVISIONING time —
        # the store pins the host identity at first contact and every later
        # session is seeded with it (see HostFictionStore.session_graph), so
        # a reclassified session generates and verifies against the pinned
        # machine. A draft naming a different host therefore fails SESSION-
        # level verification; no classification-based swap check here.
        # Only cross-check sessions that passed the inner (session-level)
        # verification — the fail-closed story stays session-first.
        if result.get("passed", True):
            text = str(response.get("response_text", "") or "")
            probe = FictionGraph(session_id=f"hostcheck:{session_id}")
            probe.observe(text, source="host-verify")
            cross = self._store.check_against_host(session_id, probe)
            if not cross.consistent:
                result = dict(result)
                result["passed"] = False
                previews = "; ".join(
                    f"host {c['subject']}.{c['predicate']}: previously served {c['before']!r} -> now {c['after']!r}"
                    for c in cross.contradictions[:3]
                )
                result["issues"] = list(result.get("issues") or []) + [f"cross-session-contradiction: {previews}"]
        return result


class HostFictionStore:
    """Host-keyed fiction continuity across attacker sessions.

    One store per TARGET HOST (keyed by the facing host's identity — e.g.
    its pinned IP or hostname). All sessions an attacker opens against that
    host share the store, so the fiction survives reconnects, revisits, and
    simultaneous connections.
    """

    def __init__(self, host_key: str, policy: str = "per_session") -> None:
        if policy not in ("reconnect", "per_session"):
            raise ValueError(f"unknown host fiction policy: {policy!r}")
        self.host_key = host_key
        self.policy = policy
        self._shared_graph: FictionGraph | None = None
        # host-level facts: (subject, predicate) -> {value: [session_ids]}
        # multi-map: two sessions legitimately observing the same fact must
        # not shadow each other; a CONTRADICTION shows as a second value.
        self._host_facts: dict[tuple[str, str], dict[str, list[str]]] = {}
        # Per-session graphs (per_session policy) + their verification state.
        self._sessions: dict[str, dict[str, Any]] = {}
        # The host's pinned identity, frozen at FIRST contact. Per-skill
        # identities name different machines (novice web-srv-01 vs
        # intermediate app-db-02); without a host-level pin, a returning
        # attacker whose classification changed is shown a different box —
        # a cross-session break no per-session verifier can notice.
        self._host_identity: dict[str, Any] | None = None

    # ── graph provisioning ────────────────────────────────────────────────

    def session_graph(self, session_id: str, identity: dict[str, Any] | None = None) -> FictionGraph:
        """The FictionGraph generation/verification should use for a session.

        reconnect policy: the SAME graph instance every time — a reconnect is
        a resume, and session A's facts bind session B word for word.
        per_session policy: a fresh graph, cross-checked by the store.
        """
        if self._host_identity is None and identity:
            self._host_identity = dict(identity)
        # Enforce the pin at PROVISIONING time: every session after first
        # contact is seeded with the PINNED identity, regardless of what the
        # caller's per-skill classification would produce (per-skill
        # identities name different machines — a reclassified returning
        # attacker must still face the same box).
        seed = self._host_identity or identity
        if self.policy == "reconnect":
            if self._shared_graph is None:
                self._shared_graph = FictionGraph(session_id=f"{self.host_key}:shared", identity=seed)
            return self._shared_graph
        graph = FictionGraph(session_id=session_id, identity=seed)
        self._sessions[session_id] = {"graph": graph, "verified": False}
        return graph

    def identity_mismatch(self, identity: dict[str, Any] | None) -> dict[str, Any] | None:
        """Describe a host-identity swap, or None when consistent.

        A session whose seed identity names a DIFFERENT machine (host/ip/
        domain) than the one pinned at first contact is a cross-session
        break: the same facing host must always present the same box,
        regardless of how the attacker's skill classification changed.
        """
        pinned = self._host_identity
        if not pinned or not identity:
            return None
        for field_name in ("host", "ip", "domain"):
            pinned_v, new_v = str(pinned.get(field_name, "") or ""), str(identity.get(field_name, "") or "")
            if not pinned_v or not new_v:
                continue
            if field_name == "host":
                same = (
                    _normalize_hostname(pinned_v) == _normalize_hostname(new_v)
                    or pinned_v.split(".")[0] == new_v.split(".")[0]
                )
            else:
                same = pinned_v == new_v
            if not same:
                return {
                    "field": field_name,
                    "pinned": pinned_v,
                    "offered": new_v,
                }
        return None

    @property
    def pinned_identity(self) -> dict[str, Any] | None:
        return dict(self._host_identity) if self._host_identity else None

    def mark_verified(self, session_id: str) -> None:
        """Flag a session as verification-passed (its facts may promote)."""
        state = self._sessions.get(session_id)
        if state is None:
            if self.policy == "reconnect":
                return  # shared graph: facts are already host-level
            raise KeyError(f"unknown session: {session_id}")
        state["verified"] = True

    # ── promotion: told-facts bind the host ───────────────────────────────

    def promote_verified(self, session_id: str) -> int:
        """Promote a VERIFIED session's stable facts into the host store.

        Only verification-passed sessions promote — unverified content must
        never bind the host (fail-closed, same as the serve gate).
        Returns the number of facts promoted (new host facts only).
        """
        state = self._sessions.get(session_id)
        if state is None or not state.get("verified"):
            return 0
        graph: FictionGraph = state["graph"]
        promoted = 0
        for subject, predicate, value, _src in graph.facts():
            if not _is_host_stable(predicate) or not value:
                continue
            values = self._host_facts.setdefault((subject, predicate), {})
            key = str(value)
            sessions = values.setdefault(key, [])
            if session_id not in sessions:
                sessions.append(session_id)
            if len(sessions) == 1:
                promoted += 1
        return promoted

    # ── cross-session checking ────────────────────────────────────────────

    def check_against_host(self, session_id: str, graph: FictionGraph) -> CrossSessionCheck:
        """Check a session's observed facts against previously served host facts.

        A contradiction is a stable-predicate fact the session asserts that
        DIFFERS from a value already established by a DIFFERENT verified
        session on this host. Same-session self-shadows are excluded (the
        session graph handles those).
        """
        check = CrossSessionCheck()
        pinned_domain = str((self._host_identity or {}).get("domain", "") or "")
        for subject, predicate, value, _src in graph.facts():
            if not _is_host_stable(predicate):
                continue
            values = self._host_facts.get((subject, predicate))
            if not values:
                continue
            check.checked_against += 1
            for prior_value, sessions in values.items():
                if session_id in sessions:
                    continue  # this session's own earlier fact
                if not _same_host_value(predicate, value, prior_value, pinned_domain):
                    check.contradictions.append(
                        {
                            "subject": subject,
                            "predicate": predicate,
                            "before": prior_value,
                            "after": value,
                            "prior_sessions": list(sessions),
                        }
                    )
        return check

    # ── persistence ───────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "host_key": self.host_key,
            "policy": self.policy,
            "host_identity": self._host_identity,
            "host_facts": [
                {"subject": s, "predicate": p, "values": values} for (s, p), values in sorted(self._host_facts.items())
            ],
            "sessions": {sid: {"verified": st.get("verified", False)} for sid, st in self._sessions.items()},
        }

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.tmp")
        temporary.write_text(json.dumps(self.to_dict(), indent=2))
        temporary.replace(target)

    def restore_from_dict(self, data: dict[str, Any]) -> None:
        """Restore durable host facts after a failed serving transaction."""
        if data.get("host_key") != self.host_key or data.get("policy") != self.policy:
            raise ValueError("host-fiction snapshot does not match this store")
        self._host_identity = data.get("host_identity")
        self._host_facts = {}
        for row in data.get("host_facts", []):
            self._host_facts[(row["subject"], row["predicate"])] = {
                value: list(seen) for value, seen in row["values"].items()
            }
        for _session_id, state in self._sessions.items():
            state["verified"] = False
        for session_id, state in data.get("sessions", {}).items():
            current = self._sessions.setdefault(session_id, {"graph": None, "verified": False})
            current["verified"] = bool(state.get("verified", False))

    @classmethod
    def load(cls, path: str | Path) -> HostFictionStore:
        d = json.loads(Path(path).read_text())
        store = cls(host_key=d["host_key"], policy=d["policy"])
        store._host_identity = d.get("host_identity")
        for row in d.get("host_facts", []):
            store._host_facts[(row["subject"], row["predicate"])] = {v: list(seen) for v, seen in row["values"].items()}
        for sid, st in d.get("sessions", {}).items():
            store._sessions[sid] = {"graph": None, "verified": bool(st.get("verified", False))}
        return store
