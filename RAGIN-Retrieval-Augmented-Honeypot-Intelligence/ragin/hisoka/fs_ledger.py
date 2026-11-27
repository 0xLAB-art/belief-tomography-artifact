"""Per-session filesystem fiction ledger — consistency for repeated reads.

Why this exists: in the dwell-time replay A/B (results/
jev_dwell_replay_llm_REPORT.md), nearly every simulated-attacker leave
reason cited *inconsistent filesystem fiction* — the same read command
(``ls -la /var/tmp``) returning different listings on each ask. A cautious
attacker reads that as a trap signal, and it caps dwell time regardless of
how good the deception strategy is.

Design:
  * ``replay_for`` — exact, verbatim replay. If the attacker repeats a
    read that this session already answered, return the previously shown
    text byte-for-byte (optionally re-capped to a session-stable fact
    block that is itself frozen after first use).
  * ``remember`` — after every response, record (command → shown output).
  * ``invalidate`` — mutating commands (writes, deletes, chmod, crontab…)
    drop remembered state for touched paths; later reads of those paths
    regenerate instead of replaying (the attacker *changed* the box).
  * ``fact_block`` — a small, frozen prompt block of session facts
    (hostname, user, listing summaries) so LLM regeneration anchors on
    the same fiction each turn.

Standalone by design: no LLM, no gateway, no imports from the deception
stack. Also usable by the graph pipeline, not just the replay scripts.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

# Mutating commands: first word (and optional sudo prefix) that changes the
# filesystem. Kept conservative — everything else is treated as a read.
_MUTATING_VERBS = frozenset(
    {
        "rm",
        "mv",
        "cp",
        "touch",
        "mkdir",
        "rmdir",
        "chmod",
        "chown",
        "chgrp",
        "ln",
        "tee",
        "truncate",
        "shred",
        "install",
        "dd",
        "crontab",
        "systemctl",
        "useradd",
        "usermod",
        "groupadd",
        "wget",
        "curl",
    }
)

_WRITE_REDIRECT_RE = re.compile(r"(>>?|&>>?)\s*\S+")

# Read commands whose stdout is a listing we should replay verbatim.
_READABLE_VERBS = frozenset({"cat", "ls", "head", "tail", "less", "find", "grep", "stat", "file"})

_MAX_REMEMBERED = 64  # bound memory per session

# ── Ambient dynamism ────────────────────────────────────────────────────────
# Why: the v2 verbatim replay fixed the "inconsistent listings" tell, but the
# v5 replay showed the OPPOSITE failure — a /var/tmp listing that never
# changes across minutes reads as "canned/scripted shell" to a cautious
# attacker. Real boxes have ambient churn: transient files appear and vanish
# in tmp dirs while core entries stay stable.
#
# Design: deterministic time-bucketed drift. A repeat of an ambient read
# within the same bucket returns byte-identical output (consistency kept);
# across buckets a small number of TRANSIENT entries appear/vanish while
# every base entry is preserved byte-for-byte. Drift is a pure function of
# (session, command, bucket) — no LLM, no randomness at serve time.
_AMBIENT_BUCKET_S = 90

# Directory path fragments whose listings plausibly churn on a live box.
_AMBIENT_DIR_FRAGMENTS = ("/tmp", "/var/tmp", "/dev/shm", "/var/run", "/run/")

# Realistic transient tmp clutter: systemd private dirs, partial wget
# downloads, JVM perf files, editor leftovers. Seeded hex makes each unique.
_TRANSIENT_NAME_TEMPLATES = (
    "tmp.{hex8}",
    ".sshmux-{hex6}",
    "wget-hkst{hex6}",
    "systemd-private-{hex8}-systemd-logind.service-{hex8}",
    "vmware-root-{hex6}",
    ".X0-lock-{hex4}",
    "hsperfdata_root_{hex4}",
)

_TRANSIENT_PERMS = (
    "-rw-------",
    "-rw-r--r--",
    "drwx------",
    "-rw-rw----",
    "srw-rw-rw-",
)
_TRANSIENT_OWNERS = (("webapp", "webapp"), ("root", "root"), ("syslog", "adm"))

_MONTH_ABBR = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


@dataclass
class FilesystemLedger:
    """Per-session ledger of filesystem fiction shown to the attacker."""

    session_id: str
    _remembered: dict[str, str] = field(default_factory=dict)
    _frozen_facts: list[str] = field(default_factory=list)
    # command → number of trailing lines added by ambient drift (kept out of
    # the visible output — markers in-band would be their own honeypot tell).
    _ambient_added: dict[str, int] = field(default_factory=dict)
    # command → time bucket in which the remembered output was captured.
    # A repeat within the same bucket is byte-identical; only a repeat in a
    # NEW bucket drifts (and re-stamps). None/missing = never stamped.
    _ambient_bucket_of: dict[str, int] = field(default_factory=dict)
    mutations: int = 0

    # ── classification ──────────────────────────────────────────────────

    @staticmethod
    def is_read_command(command: str) -> bool:
        verb = command.strip().split(None, 1)[0].lower() if command.strip() else ""
        if verb not in _READABLE_VERBS:
            return False
        # `> file` or `>> file` turns a read verb into a mutation.
        return not _WRITE_REDIRECT_RE.search(command)

    @staticmethod
    def is_mutating_command(command: str) -> bool:
        stripped = command.strip()
        if stripped.startswith("sudo "):
            stripped = stripped[5:]
        verb = stripped.split(None, 1)[0].lower() if stripped else ""
        if verb in _MUTATING_VERBS:
            return True
        return bool(_WRITE_REDIRECT_RE.search(command))

    # ── core API ────────────────────────────────────────────────────────

    def replay_for(self, command: str) -> str | None:
        """Return the previously-shown output for this exact read, if any.

        Only exact-match replays are served: `ls -la /var/tmp` twice gives
        byte-identical output; `ls -la /var/tmp/` (trailing slash) is a
        different query the LLM may answer fresh — but then it is remembered
        under its own key, so a repeat of *that* form is also consistent.
        """
        if self.is_mutating_command(command):
            return None
        return self._remembered.get(command.strip())

    def remember(self, command: str, output: str, now: float | None = None) -> None:
        """Record the output shown for a command (read commands only).

        ``now`` stamps the capture bucket for ambient paths so the first
        repeat inside the same bucket stays byte-identical.
        """
        if not self.is_read_command(command) or not output:
            return
        if len(self._remembered) >= _MAX_REMEMBERED:
            self._remembered.pop(next(iter(self._remembered)))
        key = command.strip()
        self._remembered[key] = output
        if now is not None and self.is_ambient_target(command):
            self._ambient_bucket_of[key] = self.ambient_bucket(now)

    # ── ambient dynamism ────────────────────────────────────────────────

    @staticmethod
    def ambient_bucket(now: float) -> int:
        """Time bucket index for ambient drift (deterministic per bucket)."""
        return int(max(0.0, now) // _AMBIENT_BUCKET_S)

    @staticmethod
    def is_ambient_target(command: str) -> bool:
        """True for read commands on paths that plausibly churn on a live box."""
        if not FilesystemLedger.is_read_command(command):
            return False
        low = command.lower()
        return any(frag in low for frag in _AMBIENT_DIR_FRAGMENTS)

    @staticmethod
    def _seed_hex(seed: str, nbytes: int) -> str:
        digest = hashlib.sha256(seed.encode("utf-8", "replace")).hexdigest()
        return digest[: max(1, nbytes)]

    @staticmethod
    def _transient_entry(seed: str) -> str:
        """Render one realistic `ls -la` line for a transient tmp file."""
        digest = hashlib.sha256(seed.encode("utf-8", "replace")).hexdigest()
        tmpl = _TRANSIENT_NAME_TEMPLATES[int(digest[0], 16) % len(_TRANSIENT_NAME_TEMPLATES)]
        name = tmpl.replace("{hex8}", digest[1:9]).replace("{hex6}", digest[10:16]).replace("{hex4}", digest[17:21])
        perms = _TRANSIENT_PERMS[int(digest[22], 16) % len(_TRANSIENT_PERMS)]
        owner, group = _TRANSIENT_OWNERS[int(digest[23], 16) % len(_TRANSIENT_OWNERS)]
        size = 0 + (int(digest[24:26], 16) % 4096)
        month = _MONTH_ABBR[int(digest[26], 16) % 12]
        day = 1 + (int(digest[27], 16) % 28)
        hh = int(digest[28], 16) % 24
        mm = int(digest[29], 16) % 60
        return f"{perms} 1 {owner} {group} {size:8d} {month} {day:2d} {hh:02d}:{mm:02d} {name}"

    def ambient_rewrite(self, command: str, previous_output: str, now: float) -> str:
        """Evolve a remembered ambient listing across bucket boundaries.

        Preserves every previously shown base line byte-for-byte (consistency
        contract) and swaps a small deterministic set of transient entries
        derived from (session, command, bucket). Within the same bucket the
        output is untouched. Only targets ambient paths — anything else is
        returned unchanged.
        """
        key = command.strip()
        if not self.is_ambient_target(command):
            return previous_output
        bucket = self.ambient_bucket(now)
        # Same bucket as the capture/drift stamp → byte-identical.
        if self._ambient_bucket_of.get(key) == bucket:
            return previous_output
        seed = f"{self.session_id}|{key}|{bucket}"
        lines = previous_output.splitlines()
        prev_added = self._ambient_added.get(key, 0)
        base = lines[: len(lines) - prev_added] if 0 < prev_added < len(lines) else lines
        if not base or len(base) > 40:
            self._ambient_added.pop(key, None)
            return previous_output
        # 1-2 transient entries appear this bucket; 0-1 of the previous
        # bucket's entries would have "expired" by now (already dropped).
        digest = hashlib.sha256(seed.encode("utf-8", "replace")).hexdigest()
        count = 1 + (int(digest[0], 16) % 2)
        fresh = [self._transient_entry(f"{seed}|{i}") for i in range(count)]
        self._ambient_added[key] = count
        self._ambient_bucket_of[key] = bucket
        return "\n".join(base + fresh)

    def invalidate(self, command: str) -> None:
        """Forget fiction for paths a mutating command plausibly touched.

        Directory-aware: touching ``/var/tmp/newfile`` must also invalidate
        remembered listings of ``/var/tmp`` and ``/var`` (a new file changes
        directory listings). Over-invalidation is safe — it just forces
        fresh (consistent-from-there-on) fiction. Direct API: the caller
        decides what counts as a mutation (any state change invalidates;
        commands with no path targets clear everything).
        """
        self.mutations += 1
        tokens = [tok for tok in re.findall(r"[\w./-]{2,}", command) if "/" in tok or "." in tok]
        targets: set[str] = set()
        for tok in tokens:
            low = tok.lower()
            targets.add(low)
            if "/" in low:
                parts = [p for p in low.split("/") if p]
                for i in range(1, len(parts) + 1):
                    targets.add("/" + "/".join(parts[:i]))
        if not targets:
            self._remembered.clear()
            return
        self._remembered = {
            cmd: out for cmd, out in self._remembered.items() if not any(t in cmd.lower() for t in targets)
        }

    # ── prompt anchoring ────────────────────────────────────────────────

    def note_fact(self, fact: str) -> None:
        """Add a session fact to the frozen fact block.

        First fact per path-key wins: facts are keyed by their leading path
        token, so a caller that re-describes an already-frozen path cannot
        inject a contradiction into the prompt block.
        """
        fact = fact.strip()
        if not fact or len(self._frozen_facts) >= 12:
            return
        key = fact.split(None, 1)[0].lower()
        for existing in self._frozen_facts:
            if existing.split(None, 1)[0].lower() == key:
                return
        self._frozen_facts.append(fact)

    def fact_block(self) -> str:
        """Frozen facts for prompt injection — identical every turn."""
        if not self._frozen_facts:
            return ""
        lines = "\n".join(f"  - {f}" for f in self._frozen_facts)
        return (
            "Session filesystem facts (FROZEN — repeat these exactly if asked again; "
            "never contradict them):\n" + lines + "\n"
        )

    def summary(self) -> dict:
        return {
            "session_id": self.session_id,
            "remembered_reads": len(self._remembered),
            "frozen_facts": list(self._frozen_facts),
            "ambient_paths": len(self._ambient_added),
            "mutations": self.mutations,
        }
