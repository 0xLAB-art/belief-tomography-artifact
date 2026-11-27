"""Sequence-aware features for Chrollo: session-phase and command n-gram signals.

Extends the 10-feature baseline in ragin.chrollo.features with two
families motivated by the learning-curve finding that accuracy is
representation-bound:

* Session-phase features (7, interpretable): where in the session the
  exploit/persistence/lateral/exfil phases occur (attack chains unfold
  in a characteristic order — recon early, persistence/exfil late),
  plus timing acceleration (late-session speedup) and error decay.
* Command n-gram features (32, hashed): uni- and bi-grams over the
  first token ("verb") of each command, hashed into 32 buckets
  (the hashing-trick; no fitted vocabulary, no state to persist).

All features are float and finite; empty sessions produce all zeros.
"""

from __future__ import annotations

import hashlib
import math
import re

from ragin.chrollo.features import FeatureExtractor
from ragin.chrollo.models import SessionLog

N_BUCKETS = 32

# Normalized-position features: position of the LAST command matching the
# phase pattern, divided by session length (0.0 = session start,
# 1.0 = session end; 0.0 sentinel when the phase never occurs).
_PHASE_PATTERNS: dict[str, re.Pattern[str]] = {
    "recon": re.compile(
        r"\b(whoami|uname|id|ifconfig|ip\s+a|netstat|ss\s|ps\s|ls|cat\s/etc/passwd|w)\b",
        re.IGNORECASE,
    ),
    "scan": re.compile(
        r"\b(nmap|masscan|zmap|rustscan|nikto|gobuster|dirb|ffuf|wfuzz|whatweb)\b",
        re.IGNORECASE,
    ),
    "exploit": re.compile(
        r"(/dev/tcp|msfvenom|msfconsole|reverse_tcp|dup2|\|\s*(ba)?sh|meterpreter|\.\/[a-z0-9_-]*\.(sh|py|elf))",
        re.IGNORECASE,
    ),
    "privesc": re.compile(
        r"\b(sudo|chmod\s+[47]|setuid|getcap|pkexec|find\s+/.*-perm)\b",
        re.IGNORECASE,
    ),
    "persist": re.compile(
        r"\b(crontab|systemctl\s+enable|update-rc\.d|chkconfig|authorized_keys|rc\.local)\b",
        re.IGNORECASE,
    ),
    "lateral": re.compile(
        r"\b(ssh\s+-[JN]|sshpass|smbclient|crackmapexec|evil-winrm|wmiexec|psexec|smbexec)\b",
        re.IGNORECASE,
    ),
    "exfil": re.compile(
        r"\b(scp\s|rsync\s|curl\s+-T|nc\s+\S+\s+\d+\s*<|7z\s+a|tar\s+czf)\b",
        re.IGNORECASE,
    ),
}

# Token normalization: map the first token of a command to a coarse verb so
# that hashed n-grams generalize across tool variants/paths.
_ALIAS = re.compile(r"^(?:/usr/(?:local/)?(?:s?bin|bin)/|\./)")


def _verb(command: str) -> str:
    """Coarse verb for a command: normalized first token."""
    first = command.strip().split()
    if not first:
        return "<empty>"
    tok = _ALIAS.sub("", first[0]).rsplit("/", 1)[-1].lower()
    return tok[:24]


def _bucket(gram: str) -> int:
    """Stable 32-bucket hash for one n-gram."""
    return int.from_bytes(hashlib.md5(gram.encode(), usedforsecurity=False).digest()[:4], "little") % N_BUCKETS


def extract_seq_features(session: SessionLog) -> dict[str, float]:
    """Extract the 7 phase features + 32 hashed n-gram features."""
    cmds = [c.command for c in session.commands]
    n = len(cmds)
    feats: dict[str, float] = {f"phase_pos_{name}": 0.0 for name in _PHASE_PATTERNS}
    feats["timing_acceleration"] = 0.0
    for i in range(N_BUCKETS):
        feats[f"ngram_{i}"] = 0.0
    if n == 0:
        return feats

    # ── Phase positions ──────────────────────────────────────────────────
    for name, pattern in _PHASE_PATTERNS.items():
        last_idx = -1
        for i, cmd in enumerate(cmds):
            if pattern.search(cmd):
                last_idx = i
        if last_idx >= 0:
            feats[f"phase_pos_{name}"] = round((last_idx + 1) / n, 6)

    # ── Timing acceleration: slope of normalized time vs command index ──
    ts = sorted(c.timestamp for c in session.commands)
    if n >= 3:
        total = (ts[-1] - ts[0]).total_seconds()
        if total > 0:
            # Split session into halves; compare mean inter-command gap.
            mid = n // 2
            gaps = [(ts[i + 1] - ts[i]).total_seconds() for i in range(n - 1)]
            first_half = gaps[: max(mid - 1, 1)]
            second_half = gaps[mid:]
            m1 = sum(first_half) / len(first_half) if first_half else 0.0
            m2 = sum(second_half) / len(second_half) if second_half else 0.0
            # >0 means the session speeds up (machine-paced tail);
            # clamp to [-1, 1].
            feats["timing_acceleration"] = round(max(-1.0, min(1.0, (m1 - m2) / (m1 + m2 + 1e-9))), 6)

    # ── Hashed n-grams over command verbs (uni + bi) ─────────────────────
    verbs = [_verb(c) for c in cmds]
    grams: list[str] = []
    grams.extend(verbs)
    grams.extend(f"{verbs[i]}_{verbs[i + 1]}" for i in range(n - 1))
    # Repetition weight: rarer, structured sequences (bi-grams) carry the
    # signal; simple counting with L2-style normalization by session length.
    for g in grams:
        feats[f"ngram_{_bucket(g)}"] += 1.0
    norm = 1.0 / math.sqrt(max(len(grams), 1))
    for i in range(N_BUCKETS):
        feats[f"ngram_{i}"] = round(feats[f"ngram_{i}"] * norm, 6)

    return feats


SEQ_FEATURE_NAMES: list[str] = (
    [f"phase_pos_{name}" for name in _PHASE_PATTERNS]
    + ["timing_acceleration"]
    + [f"ngram_{i}" for i in range(N_BUCKETS)]
)
PHASE_FEATURE_NAMES: list[str] = [f"phase_pos_{name}" for name in _PHASE_PATTERNS] + ["timing_acceleration"]
NGRAM_FEATURE_NAMES: list[str] = [f"ngram_{i}" for i in range(N_BUCKETS)]


class SeqFeatureExtractor:
    """Combines the 10-feature baseline with sequence-aware features."""

    def __init__(self) -> None:
        self._base = FeatureExtractor()

    def extract(self, session: SessionLog) -> dict[str, float]:
        feats = self._base.extract(session)
        feats.update(extract_seq_features(session))
        return feats
