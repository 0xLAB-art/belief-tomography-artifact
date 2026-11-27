"""Tests for the sequence-aware feature extractor (features_seq)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ragin.chrollo.features_seq import (
    N_BUCKETS,
    SEQ_FEATURE_NAMES,
    SeqFeatureExtractor,
    _verb,
    extract_seq_features,
)
from ragin.chrollo.models import CommandEntry, SessionLog

NOW = datetime.now(timezone.utc)


def _session(commands: list[str], dt: float = 1.0) -> SessionLog:
    return SessionLog(
        session_id=f"s-{abs(hash(tuple(commands)))}",
        start_time=NOW,
        commands=[CommandEntry(timestamp=NOW + timedelta(seconds=i * dt), command=c) for i, c in enumerate(commands)],
    )


class TestVerb:
    def test_strips_paths(self):
        assert _verb("/usr/bin/nmap -sV x") == "nmap"
        assert _verb("./payload.sh") == "payload.sh"

    def test_lowercase_and_clamp(self):
        assert _verb("NMAP") == "nmap"
        assert len(_verb("a" * 100)) == 24

    def test_empty(self):
        assert _verb("") == "<empty>"


class TestExtractSeqFeatures:
    def test_all_features_present_and_finite(self):
        s = _session(["whoami", "nmap -sV 10.0.0.1", "sudo -s", "crontab -e"])
        feats = extract_seq_features(s)
        assert list(feats) == SEQ_FEATURE_NAMES
        assert len(SEQ_FEATURE_NAMES) == 8 + N_BUCKETS
        for v in feats.values():
            assert isinstance(v, float)
            assert v == v  # not NaN

    def test_empty_session_zeros(self):
        feats = extract_seq_features(_session([]))
        assert all(v == 0.0 for v in feats.values())

    def test_phase_positions_monotone_semantics(self):
        # Recon at start (and nowhere else), persistence at end.
        # NB: bare 'ls' also matches the recon pattern, so avoid it here.
        s = _session(["whoami", "cat /tmp/notes.txt", "crontab -e"])
        f = extract_seq_features(s)
        assert 0.0 < f["phase_pos_recon"] <= 1 / 3
        assert f["phase_pos_persist"] == 1.0
        assert f["phase_pos_exfil"] == 0.0  # absent

    def test_timing_acceleration_sign(self):
        # Fast tail (machine-paced) => positive acceleration.
        cmds = ["ls"] * 4
        s = SessionLog(
            session_id="accel",
            start_time=NOW,
            commands=[CommandEntry(timestamp=NOW + timedelta(seconds=i * 10), command=cmds[i]) for i in range(4)]
            + [CommandEntry(timestamp=NOW + timedelta(seconds=40 + i * 0.1), command="id") for i in range(4)],
        )
        f = extract_seq_features(s)
        assert f["timing_acceleration"] > 0.5

    def test_ngram_buckets_stable(self):
        s1 = _session(["whoami", "nmap 10.0.0.1"])
        s2 = _session(["whoami", "nmap 10.0.0.9"])
        f1 = extract_seq_features(s1)
        f2 = extract_seq_features(s2)
        # Same verbs -> identical hashed n-gram buckets.
        for i in range(N_BUCKETS):
            assert f1[f"ngram_{i}"] == f2[f"ngram_{i}"]

    def test_ngram_l2_normalized(self):
        s = _session(["ls", "ls", "ls", "whoami", "id", "ps"])
        f = extract_seq_features(s)
        assert sum(f[f"ngram_{i}"] for i in range(N_BUCKETS)) > 0

    def test_seq_extractor_superset(self):
        from ragin.chrollo.features import FEATURE_NAMES as BASE_NAMES

        s = _session(["whoami", "sudo -s"])
        full = SeqFeatureExtractor().extract(s)
        assert set(full) == set(BASE_NAMES) | set(SEQ_FEATURE_NAMES)
