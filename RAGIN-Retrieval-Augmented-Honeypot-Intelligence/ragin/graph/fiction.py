"""Fiction graph — keeps fabricated honeypot facts mutually consistent.

The fake environment is modeled as a small property graph: (subject, predicate,
value) triples asserted across the session. Every generated reply is observed;
new facts are extracted and asserted into the graph, and in-session
contradictions are recorded as *graph inconsistencies* — the single most
decoy-revealing behavioral signal (an adversary who queries the same server
twice and gets two different kernels/users/IPs has detected the honeypot).

The consistent fact block is re-injected into the deceiver prompt on every turn
so the LLM cannot drift. This is the "verified deception memory" / consistency
invariant of the TDSC novelty plan: fabricated state is graph-derived, checked,
and monotonic within a session (source-ranked).

Deterministic and dependency-free by design.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_HOSTNAME_RE = re.compile(r"\b[A-Za-z0-9_-]+(?:\.[a-z0-9_-]+)+\b")
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
# L3 red-team fix (third-family llama drafts): `kernel version:` and
# `kernel: version` labels capture the LABEL TAIL ("version:") as the kernel
# value — a garbage fact that contradicted the pinned kernel on benign
# ss -tlnp / uname prose (C-neg-ports-unstable, C-neg-hostname-remention FPs).
# A kernel release is a version-like token: digits first, dotted, then a
# suffix; "version:" has no digits and is not a value.
_KERNEL_RE = re.compile(r"kernel(?:\s+version)?\s*[:=]?\s*(\d[\w.:+~-]*\w)", re.IGNORECASE)
# Bare kernel release token (`uname -r` output): a dotted, hyphen-suffixed
# version with NO letters in the dotted head (so the hostname gate excludes
# it) and not an IPv4 quad. Anchored to a line start because the graph must
# not read kernel-like substrings out of prose (red-team finding V2: `uname
# -r` replies were never observed, so kernel drift passed verification).
_BARE_KERNEL_RE = re.compile(r"^\s*(\d{1,3}\.\d{1,3}[\.\d]*-\w[\w.~-]*)\s*$", re.MULTILINE)
# Host-OWNED interface addresses: the `inet <ip>/<prefix>` shape that
# `ip addr`/`ifconfig` print for this machine's interfaces (red-team V1
# semantics). Bare IP tokens in prose/configs (DB_HOST=, `Connection received
# on`, IMDS endpoints) belong to OTHER machines or protocol endpoints — the
# fiction legitimately serves decoy addresses — so they are recorded as
# non-stable `ip_seen` mentions, never as the host's address.
_IFACE_IP_RE = re.compile(r"\binet\s+(\d{1,3}(?:\.\d{1,3}){3})/\d{1,2}", re.IGNORECASE)
# `ip addr` interface headers: "2: eth0:", "3: docker0:@" — attribute each
# `inet` line to its interface so only the PRIMARY interface's address is the
# host's `ip` fact. Cross-session benchmark finding (2026-09-27): the old
# interface-blind extraction shoved loopback (127.0.0.1) and bridge
# (docker0 172.17.0.1) addresses into the single stable `ip` predicate, so a
# TRUTHFUL full `ip addr` reply self-contradicted the pinned host address —
# a guaranteed false rejection on the most common recon command.
_IFACE_HEADER_RE = re.compile(r"\d+:\s+([A-Za-z0-9@.\-]+?)[:@]")
# Interfaces that are never the host's primary address (loopback/bridge/veth
# families): their addresses become `ip:<iface>` facts instead of `ip`.
_NON_PRIMARY_IFACE_EXACT = {"lo", "docker0"}
_NON_PRIMARY_IFACE_PREFIX = ("veth", "br-", "virbr", "docker", "tun", "tap")


def _iface_for_pos(text: str, pos: int) -> str | None:
    """Interface name of the `inet` block at pos: the last `N: name:` header before it."""
    iface = None
    for m in _IFACE_HEADER_RE.finditer(text[:pos]):
        iface = m.group(1)
    return iface


def _is_primary_iface(iface: str) -> bool:
    base = iface.split("@", 1)[0].lower()
    return base not in _NON_PRIMARY_IFACE_EXACT and not base.startswith(_NON_PRIMARY_IFACE_PREFIX)


# Distro requires a VERSION-LIKE token after the name: `Ubuntu\s+\S+` also
# matched the '#167-Ubuntu SMP' banner inside every real `uname -a` output,
# extracting os="Ubuntu SMP " and contradicting the pinned identity — a
# guaranteed false contradiction on the single most common fingerprint probe
# (C1 battery finding). L3 fix: the version gap matches spaces/tabs ONLY —
# `\s` also matches newlines, so llama drafts wrapping `Ubuntu\n5.15.0` minted
# os="Ubuntu \n5.15.0" from kernel prose (C-neg-hostname-remention FP).
_DISTRO_RE = re.compile(
    r"(?:\bUbuntu[ \t]+\d[\w.]*\s*(?:LTS)?\b|Red Hat(?:\s+Enterprise)?(?:\s+Linux)?|CentOS(?:\s+Linux)?|Debian)",
    re.IGNORECASE,
)
_PORT_RE = re.compile(r"\bport\s+(\d{1,5})\b", re.IGNORECASE)
# Group 1 = prose "user: webapp"; group 3 = name in "uid=1001(webapp)" transcripts.
# L3 red-team fix: the value must sit on the SAME LINE as the keyword —
# `web-srv-01 login: \nwelcome to ...` matched with `\s*` crossing the newline
# and captured "welcome" as the session user (live FP, third-family drafts).
# The keyword–value gap is now [ \t]* (no newline crossing).
_USER_RE = re.compile(
    r"\b(?:user|username|login|account)\s*(?:is|:|=)[ \t]*`?([a-z_][a-z0-9_-]{1,31})`?"
    r"|\b(?:uid|gid)=(\d+)\(([a-z_][a-z0-9_-]{1,31})\)",
    re.IGNORECASE,
)
# V15b (live round 5): SQL prose like ``user IS NOT NULL`` matches the
# keyword form and captures ``NOT`` as a username — a false user fact that
# contradicted the pinned identity on the mysql REPL fiction. Reserved SQL
# words after is/=/: are operators, not names. V20 (live round 6, second
# author model): ``session identity: uid=1001(webapp)`` captured ``uid`` —
# the alias/keyword value must not be a uid/gid token either.
_USER_RESERVED = {"not", "null", "in", "like", "between", "is", "true", "false", "uid", "gid"}
# V23a (live round 7, second author model): "The active account is webapp"
# — the determiner-keyword form captures the ADJECTIVE before "account".
# Closed-group adjective stoplist; a real username in that slot
# ("the svc_backup account") is untouched.
_USER_ADJ_STOP = {
    "active",
    "inactive",
    "current",
    "previous",
    "same",
    "different",
    "entire",
    "whole",
    "local",
    "remote",
    "single",
    "only",
    "first",
    "last",
    "next",
    "other",
    "new",
    "old",
    "main",
    "primary",
    "secondary",
    "admin",
    "service",
    "user",
    "guest",
    "shared",
    "locked",
    "disabled",
    "known",
    "unknown",
    "given",
    "correct",
}
# Live red-team finding V10: drafts phrase the session account without a
# colon/equals after the keyword. Two alias shapes: keyword-first
# ("account is svc_backup") and determiner-guarded keyword-after
# ("running as the svc_backup account") — the determiner keeps generic
# prose like "no user account found" from planting a user fact.
_USER_ALIAS_RE = re.compile(
    r"\baccount\s+(?:is|:|=)\s*`?([a-z_][a-z0-9_-]{1,31})`?"
    r"|\b(?:the|your|this)\s+`?([a-z_][a-z0-9_-]{1,31})`?\s+account\b"
    # V10b (live): `service identity: svc_backup` — identity vocabulary
    # without the account/user keyword.
    r"|\b(?:service|session|login)\s+identity\s*(?:is|:|=)\s*`?([a-z_][a-z0-9_-]{1,31})`?",
    re.IGNORECASE,
)


def _is_hostname_like(candidate: str) -> bool:
    """True for dotted names whose head segment contains a letter (so version
    strings like 5.15.0-91-generic and bare IPs are excluded)."""
    head = candidate.split(".", 1)[0]
    return any(ch.isalpha() for ch in head)


def _inside_parens(text: str, pos: int) -> bool:
    """True when ``pos`` sits inside an unmatched ( ... ) span of ``text``.

    Cheap scan (no nesting depth tracking): a distro token with ANY opening
    paren before it and no intervening close is treated as parenthesized —
    good enough for the banner shapes that motivated it.
    """
    open_before = text.rfind("(", 0, pos)
    if open_before == -1:
        return False
    close_between = text.rfind(")", open_before, pos)
    return close_between == -1 or open_before > close_between


# Dotted tokens that are NOT hostnames even though they look like them:
# systemd unit names (nginx.service), file names (app.conf, data.json),
# python packages, LDAP paths, etc. Recording any of these as the session's
# hostname produced false fiction-contradictions that rejected truthful
# transcripts (GT-006 `systemctl list-units` reply).
_NON_HOSTNAME_SUFFIXES = (
    ".service",
    ".socket",
    ".timer",
    ".target",
    ".mount",
    ".path",
    ".conf",
    ".cfg",
    ".ini",
    ".yaml",
    ".yml",
    ".toml",
    ".log",
    ".py",
    ".deb",
    ".rpm",
    ".txt",
    ".xml",
    ".so",
    ".sh",
    ".localdomain",  # covered by domain handling, kept for clarity
)

# Plausible top-level domains for infrastructure hostnames in the fiction.
# The suffix blocklist alone let SQL qualifiers (mysql.user), file names
# (deploy.env), latin abbreviations (i.e) and shell prompts (sh-5.1) through
# as "hostnames" — each planted a false hostname contradiction and voided a
# truthful transcript (ablation-battery finding). Requiring a plausible TLD
# closes that class; over-blocking is safe (fewer false contradictions, and
# fiction hosts always use the pinned domain).
_PLAUSIBLE_HOSTNAME_TLDS = {
    "local",
    "localdomain",
    "corp",
    "internal",
    "intranet",
    "io",
    "dev",
    "cloud",
    "aws",
    "azure",
    "lan",
    "lab",
}


def _is_system_entity(candidate: str) -> bool:
    lower = candidate.lower()
    return any(lower.endswith(suffix) for suffix in _NON_HOSTNAME_SUFFIXES)


# Subject+predicate pairs that must never change within a session.
# `ip` is stable (red-team finding V1): the identity seeds one interface, so
# a second address on the wire is the §"second network interface" fabrication
# the verified-deception design exists to reject — without `ip` here, `observe`
# silently absorbed every drifted address and the consistency check never fired.
_STABLE_PREDICATES: set[str] = {"os", "kernel", "hostname", "domain", "user", "ip"}


def _normalize_hostname(value: str) -> str:
    """Canonicalize a hostname so FQDN and short forms compare equal.

    `web-srv-01` and `web-srv-01.corp.local` are the SAME machine: the short
    form is the FQDN's first label (or vice versa when the domain matches the
    pinned identity). Without normalization, honest FQDN replies would be
    recorded as contradictions of the short-form identity seed — a false
    positive that would reject truthful transcripts.
    """
    if not value:
        return value
    return value.lower().rstrip(".")


@dataclass
class ObservationResult:
    """Outcome of observing a generated reply for new facts."""

    added: list[tuple[str, str, Any, str]] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    mentions: list[dict[str, Any]] = field(default_factory=list)

    @property
    def consistent(self) -> bool:
        return not self.contradictions


@dataclass
class FictionGraph:
    """Session-scoped property graph of fabricated environment facts."""

    session_id: str
    identity: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        self._facts: dict[tuple[str, str], tuple[str, Any]] = {}  # (subj,pred) -> (value, source)
        self._mentions: list[dict[str, Any]] = []
        self._contradictions: list[dict[str, Any]] = []
        if self.identity:
            self._seed_from_identity()

    def clone(self, *, session_id: str | None = None) -> FictionGraph:
        """Return an isolated staged copy of this graph.

        Verification must inspect a candidate without making rejected facts
        visible to a later turn.  The graph is deliberately dependency-free,
        so an explicit copy is safer than sharing the mutable fact/diagnostic
        collections with the serving transaction.
        """
        staged = FictionGraph(session_id=session_id or self.session_id, identity=None)
        staged.identity = dict(self.identity) if self.identity else None
        staged._pinned_domain = self._pinned_domain
        staged._facts = dict(self._facts)
        staged._mentions = [dict(item) for item in self._mentions]
        staged._contradictions = [dict(item) for item in self._contradictions]
        return staged

    def replace_from(self, other: FictionGraph) -> None:
        """Commit a staged graph into this graph after acceptance."""
        if self.session_id != other.session_id:
            raise ValueError("cannot commit a fiction graph for another session")
        self.identity = dict(other.identity) if other.identity else None
        self._pinned_domain = other._pinned_domain
        self._facts = dict(other._facts)
        self._mentions = [dict(item) for item in other._mentions]
        self._contradictions = [dict(item) for item in other._contradictions]

    # Pinned domain of this graph. Stored on the INSTANCE by
    # _seed_from_identity; the class-level mirror exists only because
    # _same_value is a @staticmethod called deep inside triple comparison.
    # Session graphs are per-session by construction and each process seeds
    # one identity per session, so the class-level mirror is single-valued in
    # practice; a None default keeps standalone graphs comparison-safe. The
    # instance attribute is what per-instance gates read — as a dataclass
    # field it would otherwise be stamped None by the generated __init__ and
    # shadow the class mirror (live red-team finding V15's fix initially
    # no-op'd on exactly that).
    _pinned_domain: str | None = None

    # ── construction ───────────────────────────────────────────────────────

    def _seed_from_identity(self) -> None:
        ident = self.identity
        if ident is None:  # only reached via __init__ when identity is truthy
            return
        FictionGraph._pinned_domain = str(ident.get("domain", "") or "") or None
        # Instance attribute too: as a dataclass field the class-level value
        # is shadowed by the __init__-stamped None on every instance.
        self._pinned_domain = FictionGraph._pinned_domain
        self.declare("env", "user", ident.get("user", "webapp"), "identity")
        self.declare("env", "hostname", ident.get("host", ""), "identity")
        self.declare("env", "domain", ident.get("domain", ""), "identity")
        self.declare("env", "os", ident.get("distro", ""), "identity")
        self.declare("env", "kernel", ident.get("kernel", ""), "identity")
        self.declare("env", "ip", ident.get("ip", ""), "identity")

    @staticmethod
    def _same_value(predicate: str, a: Any, b: Any) -> bool:
        """Equality with FQDN-aware hostname comparison.

        `web-srv-01` and `web-srv-01.corp.local` are the SAME machine: the
        short form is the FQDN's first label. Without this, honest FQDN
        replies would be recorded as contradictions of the short-form
        identity seed — a false positive that rejects truthful transcripts.

        Domain mismatch (red-team finding V4): equivalence is accepted only
        when the shared domain is the PINNED one. A sibling-domain FQDN
        (web-srv-01.dmz.internal vs the pinned corp.local) is a different
        machine wearing a compatible name — an extraction-evasion shape the
        old startswith rule admitted as equal.
        """
        if predicate == "hostname" and isinstance(a, str) and isinstance(b, str):
            na, nb = _normalize_hostname(a), _normalize_hostname(b)
            if na == nb:
                return True
            short, long = (na, nb) if len(na) <= len(nb) else (nb, na)
            if long.startswith(short + "."):
                # Only trust the suffix when it is the identity's own domain.
                pinned_domain = (FictionGraph._pinned_domain or "").lower().rstrip(".")
                return bool(pinned_domain) and long[len(short) + 1 :] == pinned_domain
            return False
        return a == b

    def declare(self, subject: str, predicate: str, value: Any, source: str = "assumed") -> None:
        """Assert a fact. Stable predicates reject contradicting re-assertions."""
        key = (subject, predicate)
        existing = self._facts.get(key)
        if (
            existing is not None
            and not self._same_value(predicate, existing[0], value)
            and predicate in _STABLE_PREDICATES
        ):
            self._contradictions.append(
                {
                    "subject": subject,
                    "predicate": predicate,
                    "before": existing[0],
                    "after": value,
                    "source": source,
                }
            )
            return
        self._facts[key] = (value, source)

    # ── observation ---------------------------------------------------------

    def observe(self, text: str, source: str = "llm") -> ObservationResult:
        """Extract candidate facts from a reply and assert them into the graph."""
        result = ObservationResult()
        if not text:
            return result
        # IP extraction prefilter (red-team findings, precision side): broadcast
        # addresses (`brd 10.0.0.255`) and the wildcard listen address
        # (0.0.0.0) are interface-adjacent context, not the host's address —
        # observing them planted false contradictions on truthful `ip addr`
        # and `ss -tlnp` replies once `ip` became a stable predicate.
        ip_scan = re.sub(r"brd\s+\d{1,3}(?:\.\d{1,3}){3}", "brd", text)
        ip_scan = re.sub(r"0\.0\.0\.0(:\d+)?", " ", ip_scan)
        claimed_primary = False  # first primary-eligible iface takes the host `ip` slot
        m: re.Match[str] | None  # reused below for searches that may not match
        for m in _IFACE_IP_RE.finditer(ip_scan):
            value = m.group(1)
            if value == "127.0.0.1":
                # Loopback exists on every host — never the host address.
                continue
            iface = _iface_for_pos(ip_scan, m.start())
            pinned_ip = str((self._facts.get(("env", "ip")) or ("",))[0])
            if iface is None:
                # No interface header (plain inet mention): only the first
                # non-loopback address may claim the host `ip` slot.
                predicate = None if claimed_primary else "ip"
            elif not _is_primary_iface(iface):
                predicate = f"ip:{iface}"  # bridge/veth address: scoped fact
            elif value == pinned_ip or not claimed_primary:
                predicate = "ip"  # primary interface: must match the pinned address
            else:
                predicate = f"ip:{iface}"  # secondary address on a primary iface
            if predicate is None:
                self._add_extracted(result, "env", "ip_seen", value, source, stable=False)
                continue
            if predicate == "ip":
                claimed_primary = True
            if self._add_extracted(result, "env", predicate, value, source):
                result.mentions.append({"predicate": predicate, "value": value})
        for value in _IP_RE.findall(ip_scan):
            self._add_extracted(result, "env", "ip_seen", value, source, stable=False)
        for host in _HOSTNAME_RE.findall(text):
            if not (
                "." in host
                and _is_hostname_like(host)
                and not _is_system_entity(host)
                and not host.lower().endswith((".png", ".jpg", ".com", ".html", ".js"))
            ):
                continue
            # Plausible-infrastructure-TLD gate: the identity seeds every
            # fiction hostname with the pinned domain (corp.local etc.), so
            # anything outside the plausible-TLD set is noise (mysql.user,
            # deploy.env, i.e, sh-5.1) — not a competing hostname.
            if host.lower().rsplit(".", 1)[1] not in _PLAUSIBLE_HOSTNAME_TLDS:
                continue
            # V15 (live red-team): the pinned DOMAIN itself (corp.local in an
            # email row like admin@corp.local) is not a competing hostname —
            # observing it as one planted a false contradiction against the
            # pinned host on every db-dump draft.
            if host.lower() == str(self._pinned_domain or "").lower():
                continue
            if self._add_extracted(result, "env", "hostname", host, source):
                result.mentions.append({"predicate": "hostname", "value": host})
        m = _KERNEL_RE.search(text)
        if m and self._add_extracted(result, "env", "kernel", m.group(1), source):
            result.mentions.append({"predicate": "kernel", "value": m.group(1)})
        else:
            # `uname -r` prints a bare release token with no surrounding prose
            # (red-team finding V2); observe it too, or kernel drift passes
            # verification on the most common kernel probe.
            m = _BARE_KERNEL_RE.search(text)
            if m and self._add_extracted(result, "env", "kernel", m.group(1), source):
                result.mentions.append({"predicate": "kernel", "value": m.group(1)})
        m = _DISTRO_RE.search(text)
        # L3 red-team fix: distro-shaped strings inside PARENTHESES are build
        # provenance, not OS assertions — `(gcc (Ubuntu 9.4.0-1ubuntu1~20.04.1))`
        # in every real gcc-v version banner. Observing it minted os="Ubuntu
        # 9.4.0" and contradicted the pinned OS on benign uname prose (live FP,
        # C-neg-hostname-remention[1]). A parenthesized distro mention is
        # skipped; bare distro strings (os-release, lsb_release) still extract.
        while m and (_inside_parens(text, m.start()) or "\n" in m.group(0)):
            m = _DISTRO_RE.search(text, m.end())
        if m and self._add_extracted(result, "env", "os", m.group(0), source):
            result.mentions.append({"predicate": "os", "value": m.group(0)})
        for m in _PORT_RE.finditer(text):
            self._add_extracted(result, "env", f"port:{m.group(1)}", m.group(1), source, stable=False)
        for m in _USER_RE.finditer(text):
            user = m.group(1) or m.group(3)
            if user and user.lower() not in _USER_RESERVED and self._add_extracted(result, "env", "user", user, source):
                result.mentions.append({"predicate": "user", "value": user})
        # V10b refinement (live round 5): the alias scan runs ALWAYS, not
        # only when the keyword form is absent — a draft may assert the
        # pinned user in keyword form AND a different account in alias form
        # ("user: webapp ... current service identity: svc_backup"), and
        # only the second mention is the drift. _add_extracted handles
        # precedence: the first assertion stands, later ones contradict.
        # L3 red-team fix: dotted hostname tokens (e.g. "to web-srv-01") are
        # not users — filter only DOTTED tokens through _is_hostname_like
        # (the bare-name call is vacuously True and would drop real users).
        for m in _USER_ALIAS_RE.finditer(text):
            user = m.group(1) or m.group(2) or m.group(3)
            if (
                user
                and user.lower() not in _USER_RESERVED
                and user.lower() not in _USER_ADJ_STOP
                and not ("." in user and _is_hostname_like(user))
                and self._add_extracted(result, "env", "user", user, source)
            ):
                result.mentions.append({"predicate": "user", "value": user})
        result.contradictions = list(result.contradictions)
        self._contradictions.extend(result.contradictions)
        return result

    def _add_extracted(
        self,
        result: ObservationResult,
        subject: str,
        predicate: str,
        value: Any,
        source: str,
        stable: bool = True,
    ) -> bool:
        key = (subject, predicate)
        existing = self._facts.get(key)
        if existing is not None and not self._same_value(predicate, existing[0], value):
            if stable and (predicate in _STABLE_PREDICATES or predicate.startswith("ip:")):
                result.contradictions.append(
                    {
                        "subject": subject,
                        "predicate": predicate,
                        "before": existing[0],
                        "after": value,
                        "source": source,
                    }
                )
                return False
            return False
        if existing is None:
            self._facts[key] = (value, source)
            result.added.append((subject, predicate, value, source))
            return True
        return False

    # ── reads ------------------------------------------------------------------

    def facts(self) -> list[tuple[str, str, Any, str]]:
        """Flattened (subject, predicate, value, source) triples."""
        return [(s, p, v, src) for (s, p), (v, src) in sorted(self._facts.items())]

    def contradictions(self) -> list[dict[str, Any]]:
        return list(self._contradictions)

    def fact_block(self, cap: int = 10) -> str:
        """A short prompt block of consistent facts established so far in this session."""
        triples = self.facts()
        if not triples:
            return ""
        lines = []
        for subject, predicate, value, _src in triples[:cap]:
            if value:
                lines.append(f"  {subject}.{predicate} = {value}")
        if not lines:
            return ""
        return (
            "Environment state established earlier in this session "
            "(keep responses consistent with it):\n" + "\n".join(lines) + "\n"
        )

    def summary(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "facts": [{"subject": s, "predicate": p, "value": v, "source": src} for s, p, v, src in self.facts()],
            "contradictions": self.contradictions(),
            "consistent": not self._contradictions,
        }

    def to_dict(self) -> dict[str, Any]:
        return self.summary()
