"""Focused tests for ``scripts/validate_release_artifacts.py`` (SP2027 F3/F10).

Covered:

T1 ``extract_references`` pulls every ``\\path{...}`` payload from the real
   canonical appendix, in order, deduplicated.
T2 Bare references are flagged as missing ``results/`` prefix.
T3 Prefixed references that resolve are accepted.
T4 Prefixed references that do not resolve are flagged missing_file.
T5 Bare references whose payload is absent under ``results/`` are flagged
   as both missing_prefix and missing_file.
T6 ``main`` exit code is 1 on defects and 0 when clean.
T7 Real-repo state after the F10 repair: the canonical appendix carries
   repository-root-resolvable artifact names and the validator reports no
   defects.

Fully offline; the validator is read-only.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import validate_release_artifacts as vra  # noqa: E402

APPENDIX = ROOT / "paper" / "sections" / "sp_appendix.tex"


# ── T1: extraction on the real appendix ─────────────────────────────────────
def test_extract_references_from_real_appendix() -> None:
    refs = vra.extract_references(APPENDIX.read_text(encoding="utf-8"))
    expected = {
        "results/b4_baseline_zodiac_20260922.json",
        "results/external_baseline_model_coherent.json",
        "results/verifier_redteam.json",
        "results/verifier_redteam_supported_claims.json",
        "results/verifier_redteam_cross_family.json",
        "results/live_benchmark_zodiac_20260922.json",
        "results/live_benchmark_zodiac_20260922_run2.json",
        "results/stability_run1_vs_run2.json",
        "results/hitl_audit_bench.jsonl",
        "results/sp2027_rescue/behavior_trajectory_benchmark.json",
        "scripts/audit_figure_geometry.py",
    }
    assert expected.issubset(set(refs)), sorted(set(expected) - set(refs))
    # deduplicated and non-empty
    assert len(refs) == len(set(refs)) and refs


# ── T2: bare name → missing-prefix ──────────────────────────────────────────
def test_bare_reference_flagged_missing_prefix(tmp_path: Path) -> None:
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "x.json").write_text("{}", encoding="utf-8")
    findings = vra.validate_references(["x.json"], root=tmp_path, results_dir=tmp_path / "results")
    assert any(f.kind == "missing_prefix" and f.reference == "x.json" for f in findings)
    assert not any(f.kind == "missing_file" for f in findings)


# ── T3: canonical prefix resolves → clean ───────────────────────────────────
def test_prefixed_reference_resolves(tmp_path: Path) -> None:
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "x.json").write_text("{}", encoding="utf-8")
    findings = vra.validate_references(["results/x.json"], root=tmp_path, results_dir=tmp_path / "results")
    assert findings == []


# ── T4: canonical prefix but absent file → missing_file ─────────────────────
def test_prefixed_reference_missing_file(tmp_path: Path) -> None:
    (tmp_path / "results").mkdir()
    findings = vra.validate_references(["results/nope.json"], root=tmp_path, results_dir=tmp_path / "results")
    assert len(findings) == 1
    assert findings[0].kind == "missing_file"


# ── T5: bare name whose payload is absent → both defects ────────────────────
def test_bare_reference_absent_payload_flags_both(tmp_path: Path) -> None:
    (tmp_path / "results").mkdir()
    findings = vra.validate_references(["ghost.json"], root=tmp_path, results_dir=tmp_path / "results")
    kinds = {f.kind for f in findings}
    assert kinds == {"missing_prefix", "missing_file"}


# ── T6: CLI exit codes ──────────────────────────────────────────────────────
def test_main_exit_codes(tmp_path: Path) -> None:
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "ok.json").write_text("{}", encoding="utf-8")
    good = tmp_path / "good.tex"
    good.write_text(r"\path{results/ok.json}", encoding="utf-8")
    bad = tmp_path / "bad.tex"
    bad.write_text(r"\path{ok.json}", encoding="utf-8")
    assert vra.main(["--tex", str(good), "--root", str(tmp_path), "--results-dir", str(tmp_path / "results")]) == 0
    assert vra.main(["--tex", str(bad), "--root", str(tmp_path), "--results-dir", str(tmp_path / "results")]) == 1


def test_real_appendix_state_is_clean() -> None:
    report = vra.validate(APPENDIX, root=ROOT, results_dir=ROOT / "results")
    assert report.ok, report.findings
    assert report.by_kind("missing_prefix") == []
    assert report.by_kind("missing_file") == []


def test_real_validator_cli_passes_on_repaired_appendix() -> None:
    rc = vra.main(["--tex", str(APPENDIX), "--root", str(ROOT), "--results-dir", str(ROOT / "results")])
    assert rc == 0
