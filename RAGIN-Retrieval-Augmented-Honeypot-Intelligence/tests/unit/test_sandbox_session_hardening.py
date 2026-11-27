"""Regression tests for the sandbox/session hardening fixes.

Covers the post-pentest findings on ragin/cycle/sandbox.py and
ragin/cycle/session.py:

- [1a-HIGH] per-session lock shards: two sessions must not contend; one
  session holding its lock must not freeze another (the old single global
  RLock serialized every session).
- [5a-MED] a per-session SandboxConfig.max_commands passed at
  create_session() is enforced for that session only.
- [6a-MED] a session closed by the limit is removed from ``_sessions`` and
  later commands get an explicit error response — never a RuntimeError from
  Session.emit on a closed session.
- [7-MED] session_id path-traversal defence: ids must match
  ^[A-Za-z0-9_-]{1,128}$ (Session.__init__ / wake / Sandbox paths), else
  ValueError before any path is touched.
- [10b-MED] Sandbox.wake_session / replay_session run under the session's
  lock shard, and replay is read-only (repeated replays never grow the log).
"""

import json
import threading
from typing import Any
from unittest.mock import MagicMock

import pytest

from ragin.cycle.harness import Harness
from ragin.cycle.sandbox import Sandbox, SandboxConfig
from ragin.cycle.session import EventType, Session


# ── Mock pipeline components (mirrors tests/unit/test_cycle.py) ──────────────


def _mock_classifier() -> MagicMock:
    c = MagicMock()
    c.classify.return_value = {"skill_level": "intermediate", "confidence": 0.8}
    return c


def _mock_deceiver() -> MagicMock:
    d = MagicMock()
    d.generate_response.return_value = {
        "response_text": "Welcome to Ubuntu 20.04 LTS",
        "persona_used": "novice_linux_admin",
        "engagement_score": 0.75,
        "artifacts_injected": [],
    }
    return d


def _hardened_harness() -> Harness:
    return Harness(classifier=_mock_classifier(), deceiver=_mock_deceiver())


def _sandbox(tmp_path, **config_kwargs: Any) -> Sandbox:
    config_kwargs.setdefault("session_dir", str(tmp_path))
    return Sandbox(harness=_hardened_harness(), config=SandboxConfig(**config_kwargs))


# ═══════════════════════════════════════════════════════════════════════════════
# [1a-HIGH] Lock sharding
# ═══════════════════════════════════════════════════════════════════════════════


class TestLockSharding:
    def test_two_sessions_get_distinct_lock_shards(self, tmp_path):
        sandbox = _sandbox(tmp_path)
        sid_a = sandbox.create_session().session_id
        sid_b = sandbox.create_session().session_id
        assert sandbox._session_lock(sid_a) is not sandbox._session_lock(sid_b)
        # Same session always maps to the same shard object.
        assert sandbox._session_lock(sid_a) is sandbox._session_lock(sid_a)

    def test_one_session_holding_its_lock_does_not_freeze_another(self, tmp_path):
        """The old global RLock made B's command wait behind A's held lock.

        Regression: with lock sharding, a command on session B completes while
        session A's shard is deliberately held in the main thread. Under the
        pre-fix global lock this test deadlocked until the join timeout.
        """
        sandbox = _sandbox(tmp_path)
        sid_a = sandbox.create_session().session_id
        sid_b = sandbox.create_session().session_id

        lock_a = sandbox._session_lock(sid_a)
        lock_a.acquire()
        try:
            done = threading.Event()
            box: dict[str, Any] = {}

            def worker() -> None:
                box["resp"] = sandbox.handle_command("10.0.0.2", "whoami", session_id=sid_b)
                done.set()

            t = threading.Thread(target=worker, daemon=True)
            t.start()
            assert done.wait(timeout=15.0), (
                "session B blocked while session A's lock was held: "
                "locks are not sharded per session"
            )
            assert box["resp"].status == "ok"
            t.join(timeout=1.0)
        finally:
            lock_a.release()

    def test_concurrent_commands_on_one_session_are_serialized(self, tmp_path):
        """All commands for the SAME session run under its shard: no lost
        count increments, no exceptions, and every log line stays a complete
        JSON object (no interleaved/torn events).
        """
        sandbox = _sandbox(tmp_path)
        sid = sandbox.create_session().session_id

        n_threads, per_thread = 8, 5
        errors: list[BaseException] = []

        def worker(i: int) -> None:
            try:
                for j in range(per_thread):
                    resp = sandbox.handle_command("10.0.0.1", f"cmd-{i}-{j}", session_id=sid)
                    assert resp.status == "ok", resp.error
            except BaseException as exc:  # noqa: BLE001 — collected for the assert
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30.0)
        assert not errors, errors
        # Exactly n_threads*per_thread increments survived: proof that the
        # shard serialized the read-modify-write of _command_count.
        total = n_threads * per_thread
        assert sandbox._sessions[sid]._command_count == total  # type: ignore[attr-defined]
        log_lines = (tmp_path / f"{sid}.jsonl").read_text().splitlines()
        # At least SESSION_START + one event per command, and every line is a
        # complete JSON object: no torn/interleaved writes.
        assert len(log_lines) >= 1 + total
        for line in log_lines:
            json.loads(line)  # must not raise

    def test_lock_shard_is_cleaned_up_on_session_close(self, tmp_path):
        sandbox = _sandbox(tmp_path)
        sid = sandbox.handle_command("10.0.0.1", "c1").session_id
        # Shard is created on demand by the first command that names the id.
        sandbox.handle_command("10.0.0.1", "c2", session_id=sid)
        assert sid in sandbox._session_locks
        sandbox.close_session(sid)
        assert sid not in sandbox._session_locks


# ═══════════════════════════════════════════════════════════════════════════════
# [5a-MED] Per-session max_commands
# ═══════════════════════════════════════════════════════════════════════════════


class TestPerSessionMaxCommands:
    def test_create_session_config_max_commands_is_enforced(self, tmp_path):
        sandbox = _sandbox(tmp_path)  # sandbox default stays 1000
        limited_cfg = SandboxConfig(source_ip="10.0.0.9", max_commands=2, session_dir=str(tmp_path))
        sid = sandbox.create_session(limited_cfg).session_id

        r1 = sandbox.handle_command("10.0.0.9", "c1", session_id=sid)
        r2 = sandbox.handle_command("10.0.0.9", "c2", session_id=sid)
        r3 = sandbox.handle_command("10.0.0.9", "c3", session_id=sid)

        assert r1.status == "ok"
        assert r2.status == "ok"
        assert r3.status == "error"
        assert r3.error == "max_commands_reached"

    def test_other_sessions_keep_their_own_limit(self, tmp_path):
        sandbox = _sandbox(tmp_path)
        limited_cfg = SandboxConfig(source_ip="10.0.0.9", max_commands=1, session_dir=str(tmp_path))
        limited_sid = sandbox.create_session(limited_cfg).session_id
        default_sid = sandbox.create_session(
            SandboxConfig(source_ip="10.0.0.1", session_dir=str(tmp_path))
        ).session_id

        # Limited session is cut off after its own first command...
        assert sandbox.handle_command("10.0.0.9", "c1", session_id=limited_sid).status == "ok"
        assert (
            sandbox.handle_command("10.0.0.9", "c2", session_id=limited_sid).error
            == "max_commands_reached"
        )
        # ...while the default session is unaffected (sandbox default = 1000).
        resp = sandbox.handle_command("10.0.0.1", "c1", session_id=default_sid)
        assert resp.status == "ok"

    def test_unknown_session_falls_back_to_sandbox_default(self, tmp_path):
        """A session woken from disk (never created via create_session here)
        uses the sandbox-wide limit, not another session's per-session one."""
        creator = _sandbox(tmp_path)
        sid = creator.create_session().session_id

        sandbox = _sandbox(tmp_path, max_commands=2)
        assert sandbox.handle_command("10.0.0.1", "c1", session_id=sid).status == "ok"
        assert sandbox.handle_command("10.0.0.1", "c2", session_id=sid).status == "ok"
        r3 = sandbox.handle_command("10.0.0.1", "c3", session_id=sid)
        assert r3.error == "max_commands_reached"


# ═══════════════════════════════════════════════════════════════════════════════
# [6a-MED] Closed sessions: clear error response, never RuntimeError
# ═══════════════════════════════════════════════════════════════════════════════


class TestClosedSessionResponses:
    def test_command_after_limit_close_is_error_not_exception(self, tmp_path):
        sandbox = _sandbox(tmp_path, max_commands=1)
        r1 = sandbox.handle_command("10.0.0.1", "c1")
        sid = r1.session_id

        # The command that crosses the limit gets the explicit limit error...
        r2 = sandbox.handle_command("10.0.0.1", "c2", session_id=sid)
        assert r2.status == "error"
        assert r2.error == "max_commands_reached"
        # ...and the closed session is removed from _sessions.
        assert sid not in sandbox._sessions

        # The NEXT command must be a clean limit/closed response — pre-fix it
        # raised RuntimeError from session.emit (closed session) → HTTP 500.
        r3 = sandbox.handle_command("10.0.0.1", "c3", session_id=sid)
        assert r3.status == "error"
        assert r3.error == "session_closed:max_commands_reached"
        assert r3.response_text == "Session is closed."

        # ...and it is durable: even a fresh sandbox sees the closed state.
        fresh = _sandbox(tmp_path, max_commands=1)
        r4 = fresh.handle_command("10.0.0.1", "c4", session_id=sid)
        assert r4.status == "error"
        assert r4.error == "session_closed:max_commands_reached"

    def test_command_after_manual_close_is_error_not_exception(self, tmp_path):
        sandbox = _sandbox(tmp_path)
        r1 = sandbox.handle_command("10.0.0.1", "c1")
        sid = r1.session_id
        assert sandbox.close_session(sid) is True

        r2 = sandbox.handle_command("10.0.0.1", "c2", session_id=sid)
        assert r2.status == "error"
        assert r2.error == "session_closed:normal"

    def test_limit_closed_session_lock_shard_is_dropped(self, tmp_path):
        sandbox = _sandbox(tmp_path, max_commands=1)
        r1 = sandbox.handle_command("10.0.0.1", "c1")
        sid = r1.session_id
        sandbox.handle_command("10.0.0.1", "c2", session_id=sid)  # crosses the limit
        assert sid not in sandbox._session_locks

    def test_wake_of_limit_closed_session_stays_closed(self, tmp_path):
        """Closure is durable: Session.wake restores the closed state from the
        meta file and must NOT append a SESSION_RESUME to a closed log."""
        sandbox = _sandbox(tmp_path, max_commands=1)
        r1 = sandbox.handle_command("10.0.0.1", "c1")
        sid = r1.session_id
        sandbox.handle_command("10.0.0.1", "c2", session_id=sid)  # close by limit
        closed_count = Session(sid, session_dir=str(tmp_path)).event_count

        woken = Session.wake(sid, session_dir=str(tmp_path))
        assert woken.is_closed
        assert woken.closed_reason == "max_commands_reached"
        assert woken.event_count == closed_count  # no event appended by wake


# ═══════════════════════════════════════════════════════════════════════════════
# [7-MED] session_id path-traversal defence
# ═══════════════════════════════════════════════════════════════════════════════


class TestSessionIdValidation:
    TRAVERSAL_IDS = [
        "../../etc/passwd",
        "../sibling-session",
        "a/../b",
        "..",
        "ses/../evil",
        "ses/../../evil",
        "with space",
        "semi;colon",
        "",
        "a" * 129,
    ]

    @pytest.mark.parametrize("bad_id", TRAVERSAL_IDS)
    def test_session_constructor_rejects_bad_ids(self, tmp_path, bad_id):
        with pytest.raises(ValueError):
            Session(bad_id, session_dir=str(tmp_path))
        with pytest.raises(ValueError):
            Session.wake(bad_id, session_dir=str(tmp_path))

    def test_boundary_lengths(self, tmp_path):
        assert Session("a" * 128, session_dir=str(tmp_path)).session_id == "a" * 128
        with pytest.raises(ValueError):
            Session("a" * 129, session_dir=str(tmp_path))

    def test_generated_and_hyphenated_ids_are_accepted(self, tmp_path):
        s = Session.create(session_dir=str(tmp_path))
        assert s.session_id.startswith("ses-")
        assert Session("ses-abc_XYZ-123", session_dir=str(tmp_path)).session_id == "ses-abc_XYZ-123"

    def test_sandbox_handle_command_rejects_traversal_id(self, tmp_path):
        sandbox = _sandbox(tmp_path)
        before = sorted(p.name for p in tmp_path.iterdir())
        with pytest.raises(ValueError):
            sandbox.handle_command("10.0.0.1", "cat /etc/passwd", session_id="../../attacker")
        # Nothing was written outside (or inside) the session dir for that id.
        assert sorted(p.name for p in tmp_path.iterdir()) == before

    def test_sandbox_context_and_replay_reject_traversal_id(self, tmp_path):
        sandbox = _sandbox(tmp_path)
        with pytest.raises(ValueError):
            sandbox.get_session_context("../../attacker")
        with pytest.raises(ValueError):
            sandbox.replay_session("../../attacker")

    def test_unknown_id_wake_path_still_raises_filenotfound(self, tmp_path):
        """A well-formed but unknown id keeps the FileNotFoundError contract
        (locked behaviour in test_cycle.py::test_wake_nonexistent_raises)."""
        with pytest.raises(FileNotFoundError):
            Session.wake("ses-nonexistent", session_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            _sandbox(tmp_path).replay_session("ses-nonexistent")


# ═══════════════════════════════════════════════════════════════════════════════
# [10b-MED] wake/replay under the session lock, read-only replay
# ═══════════════════════════════════════════════════════════════════════════════


class TestWakeReplayWrappers:
    def test_replay_session_never_grows_the_log(self, tmp_path):
        """Regression for the wake-per-replay pattern: replay used to append a
        SESSION_RESUME on every call, so n replay calls grew the log by n."""
        sandbox = _sandbox(tmp_path)
        sid = sandbox.handle_command("10.0.0.1", "c1").session_id
        log_path = tmp_path / f"{sid}.jsonl"
        before_size = log_path.stat().st_size
        before_count = Session(sid, session_dir=str(tmp_path)).event_count

        first = sandbox.replay_session(sid)
        second = sandbox.replay_session(sid)

        assert len(first) == len(second) == before_count
        assert Session(sid, session_dir=str(tmp_path)).event_count == before_count
        assert log_path.stat().st_size == before_size  # byte-identical log

    def test_replay_session_since_is_read_only(self, tmp_path):
        sandbox = _sandbox(tmp_path)
        sid = sandbox.handle_command("10.0.0.1", "c1").session_id
        log_path = tmp_path / f"{sid}.jsonl"
        before_size = log_path.stat().st_size
        events = sandbox.replay_session(sid)
        after = sandbox.replay_session(sid, after_event_id=events[0].event_id)
        assert 0 < len(after) < len(events)
        assert log_path.stat().st_size == before_size

    def test_wake_session_registers_and_reports_context(self, tmp_path):
        sandbox = _sandbox(tmp_path)
        sid = sandbox.handle_command("10.0.0.1", "whoami").session_id

        other = _sandbox(tmp_path)
        session, context = other.wake_session(sid)
        assert session.session_id == sid
        assert sid in other._sessions  # registered for subsequent handle_command
        assert set(context) == {"total_events", "interaction_count"}
        assert context["interaction_count"] == 1
        assert context["total_events"] == session.event_count

    def test_wake_session_unknown_raises_filenotfound(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _sandbox(tmp_path).wake_session("ses-nonexistent")

    def test_session_wake_appends_exactly_one_resume_event(self, tmp_path):
        """Documented/locked option B of [10b]: wake emits ONE SESSION_RESUME
        per call (locked by test_cycle.py::test_crash_recovery), never one per
        replayed line — a 3-event log stays 4 events after wake."""
        s1 = Session.create(session_dir=str(tmp_path))
        s1.emit(EventType.ATTACKER_INPUT, {"command": "whoami"})
        s1.emit(EventType.SYSTEM_RESPONSE, {"text": "root"})
        woken = Session.wake(s1.session_id, session_dir=str(tmp_path))
        assert woken.event_count == 4
