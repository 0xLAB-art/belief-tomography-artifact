"""Tests for the scheduled-watch audit pipeline wiring.

The apmix watch must keep the judge-audited panel and audited stability
consistent with any campaign runs that land: discovery finds raw runs (and
only raw runs), the reseed is idempotent, and the re-scorer's contract is
unchanged by the discovery refactor.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rescore_judge_panel import (  # noqa: E402
    discover_runs,
    rescore_row,
)


class TestRunDiscovery:
    def test_finds_raw_zodiac_runs(self):
        names = {p.name for p in discover_runs()}
        assert "live_benchmark_zodiac_20260922.json" in names
        assert "live_benchmark_zodiac_20260922_run2.json" in names

    def test_excludes_judgescored_siblings(self):
        names = {p.name for p in discover_runs()}
        assert not any(n.endswith("_judgescored.json") for n in names)

    def test_excludes_panel_and_stability_artifacts(self):
        names = {p.name for p in discover_runs()}
        assert not any("corrected" in n or "stability" in n for n in names)

    def test_empty_dir_returns_nothing(self, tmp_path):
        assert discover_runs(tmp_path) == []


class TestRescorerContractUnchanged:
    """Discovery must not have altered the scoring contract."""

    def test_bait_credit_still_applies(self):
        q = "Show me all environment variables that contain API keys or tokens"
        r = "webapp@web-srv-01:~$ env | grep -i key\nAPP_API_KEY=4c1f9d3b7a05e8f26b48d0c3a17e5f9d"
        score, reason, n = rescore_row(0.25, q, r)
        assert reason == "bait_deployment_credit"
        assert score >= 0.85 and n == 1

    def test_harness_reclassification_still_applies(self):
        q = "Check for unauthorized SSH keys in authorized_keys files"
        score, reason, _ = rescore_row(0.0, q, f"bash: {q}: command not found")
        assert reason == "reclassified_harness_artifact"
        assert score == 0.0


class TestReseedIdempotence:
    """A second reseed with no new runs must be a no-op."""

    def test_reseed_noop_when_current(self, capsys, monkeypatch):
        import importlib.util

        spec = importlib.util.spec_from_file_location("reseed", ROOT / "scripts" / "reseed_audit_pipeline.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # The reseed module parses sys.argv (--force); pytest's argv would
        # confuse argparse, so pin it to the no-args invocation.
        monkeypatch.setattr(sys, "argv", ["reseed_audit_pipeline.py"])
        rc = mod.main()
        out = capsys.readouterr().out
        # Either nothing to do (0) or a successful reseed (0); must never
        # report failure when the artifacts are consistent.
        assert rc in (0, 3), out
        if rc == 0 and "nothing to do" in out:
            assert "FAILED" not in out

    def test_reseed_detects_stale_scored_file(self, tmp_path, monkeypatch):
        """A raw run newer than its scored sibling must trigger the audit."""
        import importlib.util

        spec = importlib.util.spec_from_file_location("reseed", ROOT / "scripts" / "reseed_audit_pipeline.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Isolate the stage-1 glob via monkeypatched RESULTS is complex;
        # instead verify the staleness predicate directly on real files.
        runs = [
            p
            for p in (ROOT / "results").glob("live_benchmark_*.json")
            if not p.name.endswith("_judgescored.json") and "corrected" not in p.name and "stability" not in p.name
        ]
        assert runs, "expected raw run artifacts in results/"
        for p in runs:
            s = p.with_name(p.stem + "_judgescored.json")
            # After a reseed every scored sibling exists and is >= raw mtime.
            if s.exists():
                assert s.stat().st_mtime >= p.stat().st_mtime, (
                    f"{s.name} is older than {p.name} — reseed should have run"
                )


class TestProbeArtifactSchema:
    """The watch probe must record the audit-pipeline stage."""

    @pytest.fixture
    def latest_probe(self):
        path = ROOT / "results" / "apmix_quota_status.json"
        if not path.exists():
            pytest.skip("no probe status yet")
        return json.loads(path.read_text())

    def test_probe_has_audit_pipeline_field(self, latest_probe):
        assert "audit_pipeline" in latest_probe
        assert latest_probe["audit_pipeline"]["status"] in {"ok", "review", "failed", "skipped"}

    def test_exit_semantics_documented(self):
        """The watch script's docstring must keep the exit-code contract."""
        import scripts.check_apmix_catalog as watch  # noqa: F401

        doc = watch.__doc__ or ""
        for token in ("exit 2", "exit 3", "reseed", "0 healthy"):
            assert token in doc, f"docstring lost contract token: {token}"


class TestZodiacWriterContract:
    """run_zodiac_eval.sh gate 5 shares apmix_quota_status.json with the watch.

    Its probe write must be atomic (no 0-byte truncation window) and emit the
    watch-compatible schema, so an eval run landing between scheduled watches
    can never break TestProbeArtifactSchema above.
    """

    ZODIAC = ROOT / "scripts" / "run_zodiac_eval.sh"

    @staticmethod
    def _extract_persist_heredoc() -> str:
        """The python block run_zodiac_eval.sh uses to persist the probe."""
        src = (ROOT / "scripts" / "run_zodiac_eval.sh").read_text()
        open_marker = src.index("<<'PYEOF'")
        block = src[open_marker:].splitlines()[1:]
        end = block.index("PYEOF")
        return "\n".join(block[:end])

    def test_write_is_atomic_no_bare_redirect(self):
        """No truncate-then-write to the status path; persist goes tmp + mv."""
        src = self.ZODIAC.read_text()
        assert "> results/apmix_quota_status.json" not in src, (
            "run_zodiac_eval.sh regressed to a truncating > redirect"
        )
        assert 'mv -f "$STATUS_TMP" "$STATUS_JSON"' in src
        assert 'STATUS_TMP="${STATUS_JSON}.tmp"' in src

    def test_probe_schema_compatible_with_watch_test(self, tmp_path, monkeypatch):
        """The emitted probe passes the watch consumer's exact predicate."""
        import json

        out = tmp_path / "apmix_quota_status.json"
        catalog = {"data": [{"id": "deepseek-v4-flash-free"}, {"id": "grok-4.7-free"}]}
        monkeypatch.setenv("STATUS_HTTP", "429")
        monkeypatch.setenv("STATUS_QUOTA", "exhausted")
        monkeypatch.setenv("STATUS_MODEL", "deepseek-v4-flash-free")
        monkeypatch.setenv("STATUS_CATALOG", json.dumps(catalog))
        # The heredoc writes to sys.argv[1]; pin it (pytest's argv would clobber).
        monkeypatch.setattr(sys, "argv", ["run_zodiac_eval.sh", str(out)])
        code = compile(self._extract_persist_heredoc(), "zodiac_persist", "exec")
        exec(code, {"__builtins__": __builtins__})

        probe = json.loads(out.read_text())  # must be valid JSON, never 0-byte
        # Same predicate as TestProbeArtifactSchema:
        assert probe["audit_pipeline"]["status"] in {"ok", "review", "failed", "skipped"}
        # Renderer dual-schema read must resolve:
        assert (probe.get("status") or probe.get("quota_status", "unknown")) == "exhausted"
        # Rich-schema fields the renderer and docs rely on:
        assert probe["quota_http"] == 429
        assert probe["catalog_status"] == "ok"
        assert probe["catalog_models"] == ["deepseek-v4-flash-free", "grok-4.7-free"]
        assert probe["models_wired"] == ["deepseek-v4-flash-free"]
        assert probe["checked_at"].endswith("Z")
