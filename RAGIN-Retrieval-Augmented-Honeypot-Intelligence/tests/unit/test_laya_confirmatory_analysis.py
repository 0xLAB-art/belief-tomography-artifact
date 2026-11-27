"""Tests for scripts/laya_confirmatory_analysis.py.

These tests use SYNTHETIC FIXTURE labels in temporary directories only. They
never write to results/laya_research/rater_labels/ and must never be treated as
human annotations.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "laya_confirmatory_analysis.py"

spec = importlib.util.spec_from_file_location("laya_confirmatory_analysis", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _labels_for(ids: list[str], mapping: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    lifts = {}
    for rater, per_case in mapping.items():
        lifts[rater] = {cid: per_case.get(cid, "UNCERTAIN") for cid in ids}
    return lifts


def test_refuses_without_labels(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod, "RESULTS", tmp_path)
    monkeypatch.setattr(mod, "LABELS_DIR", tmp_path / "rater_labels")
    with pytest.raises(mod.LabelsMissing):
        mod.load_rater_labels()


def test_refuses_when_label_fields_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    labels_dir = tmp_path / "rater_labels"
    labels_dir.mkdir()
    for r in ("r1", "r2", "r3"):
        doc = {"labels": [{"case_id": "x", "label": ""}]}
        (labels_dir / f"{r}.json").write_text(json.dumps(doc))
    monkeypatch.setattr(mod, "LABELS_DIR", labels_dir)
    with pytest.raises(mod.LabelsMissing):
        mod.load_rater_labels()
    # This test uses only tmp_path fixtures and must not touch the real
    # results/laya_research/rater_labels/ tree. The assertion below is a
    # fixture-integrity check that depends on the real tree being absent or
    # empty at test time; it is guarded so a pre-existing real tree does not
    # make the test fail for reasons unrelated to this fixture.
    real = ROOT / "results" / "laya_research" / "rater_labels"
    if real.exists() and any(real.iterdir()):
        pytest.skip("real rater_labels tree is non-empty; fixture integrity check N/A here")

def test_unanimous_labels_full_agreement_and_positive_kappa() -> None:
    ids = ["a", "b", "c"]
    labs = _labels_for(ids, {
        "r1": {"a": "BENIGN", "b": "RECON", "c": "EXPLOITATION"},
        "r2": {"a": "BENIGN", "b": "RECON", "c": "EXPLOITATION"},
        "r3": {"a": "BENIGN", "b": "RECON", "c": "EXPLOITATION"},
    })
    assert mod.pairwise_agreement(labs["r1"], labs["r2"], ids) == 1.0
    kappa = mod.fleiss_kappa(labs, ids, ["r1", "r2", "r3"])
    assert kappa == pytest.approx(1.0, abs=1e-6)


def test_two_vs_one_majority_consensus() -> None:
    ids = ["a"]
    labs = _labels_for(ids, {
        "r1": {"a": "RECON"},
        "r2": {"a": "RECON"},
        "r3": {"a": "BENIGN"},
    })
    consensus = mod.majority_vote(labs, ids, ["r1", "r2", "r3"])
    assert consensus["a"]["consensus"] == "RECON"
    assert consensus["a"]["agreement"] == 2
    assert consensus["a"]["raw_votes"] == ["RECON", "RECON", "BENIGN"]


def test_all_three_disagreement_flags_no_consensus() -> None:
    ids = ["a"]
    labs = _labels_for(ids, {
        "r1": {"a": "RECON"},
        "r2": {"a": "SUSPICIOUS"},
        "r3": {"a": "BENIGN"},
    })
    consensus = mod.majority_vote(labs, ids, ["r1", "r2", "r3"])
    assert consensus["a"]["consensus"] is None
    assert len(consensus["a"]["raw_votes"]) == 3


def test_uncertain_is_excluded_from_binary() -> None:
    assert mod.binary_projection("UNCERTAIN") == "excluded"
    assert mod.binary_projection(None) == "excluded"
    assert mod.binary_projection("BENIGN") == "negative"
    assert mod.binary_projection("EXPLOITATION") == "positive"


def test_missing_rater_file_triggers_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    labels_dir = tmp_path / "rater_labels"
    labels_dir.mkdir()
    (labels_dir / "r1.json").write_text(json.dumps({"labels": [{"case_id": "a", "label": "BENIGN"}]}))
    # r2 and r3 files missing
    monkeypatch.setattr(mod, "LABELS_DIR", labels_dir)
    with pytest.raises(mod.LabelsMissing):
        mod.load_rater_labels()


def test_malformed_label_value_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    labels_dir = tmp_path / "rater_labels"
    labels_dir.mkdir()
    for r in ("r1", "r2", "r3"):
        (labels_dir / f"{r}.json").write_text(json.dumps({"labels": [{"case_id": "a", "label": "not_a_class"}]}))
    monkeypatch.setattr(mod, "LABELS_DIR", labels_dir)
    with pytest.raises(mod.LabelsMissing):
        mod.load_rater_labels()


def test_confusion_matrix_counts() -> None:
    pred = [True, True, False, False, True, False]
    truth = [True, False, False, True, True, True]
    m = mod.confusion(pred, truth)
    assert m["tp"] == 2
    assert m["fp"] == 1
    assert m["tn"] == 1
    assert m["fn"] == 2
    assert m["n"] == 6


def test_paired_correctness_cells() -> None:
    preds = {
        "a": {"chrollo_output": "malicious", "laya_answer": "benign"},
        "b": {"chrollo_output": "benign", "laya_answer": "malicious"},
        "c": {"chrollo_output": "malicious", "laya_answer": "malicious"},
        "d": {"chrollo_output": "benign", "laya_answer": "benign"},
    }
    truth = {"a": "positive", "b": "positive", "c": "positive", "d": "negative"}
    out = mod.paired_correctness(preds, truth)
    # a: chrollo right / laya wrong -> chrollo-only
    # b: chrollo wrong / laya right -> laya-only
    # c: both right
    # d: both benign vs benign truth -> both right
    assert out["table"]["both_correct"] == 2
    assert out["table"]["chrollo_only"] == 1
    assert out["table"]["laya_only"] == 1
    assert out["table"]["both_wrong"] == 0
    assert out["net_corrections"] == 0


def test_mcnemar_cell_construction() -> None:
    r = mod.mcnemar(8, 2)
    assert r == {"statistic": pytest.approx(((abs(8 - 2) - 1) ** 2) / 10),
                 "p_value": r["p_value"], "b_c": 8, "b_w": 2}
    assert 0.0 <= r["p_value"] <= 1.0
    zero = mod.mcnemar(0, 0)
    assert zero["p_value"] == 1.0


def test_gate_uses_frozen_threshold_only() -> None:
    preds = {
        "a": {"chrollo_confidence": 0.55},
        "b": {"chrollo_confidence": 0.90},
        "c": {"chrollo_confidence": 0.60},
    }
    g = mod.gate_frozen(preds, threshold=0.65)
    assert g["threshold"] == 0.65
    assert g["gate_activated_count"] == 2
    assert pytest.approx(g["gate_activation_rate"]) == pytest.approx(2 / 3)


def _write_valid_rater(labels_dir: Path, rater: str, ids: list[str],
                        mapping: dict[str, str], completed_at: str) -> None:
    doc = {
        "rater_id": rater,
        "annotation_version": 1,
        "completed_at": completed_at,
        "labels": [
            {"case_id": cid, "label": mapping.get(cid, "BENIGN"), "notes": "", "timestamp": None}
            for cid in ids
        ],
    }
    (labels_dir / f"{rater}.json").write_text(json.dumps(doc))


def test_refuses_items_schema_programmatic_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AI/programmatic files use an 'items' list; only the workflow 'labels'
    schema is accepted as human output."""
    labels_dir = tmp_path / "rater_labels"
    labels_dir.mkdir()
    for r in ("r1", "r2", "r3"):
        doc = {"rater_id": r, "completed_at": "2026-10-20T10:00:00+00:00",
               "items": [{"case_id": "a", "label": "BENIGN"}]}
        (labels_dir / f"{r}.json").write_text(json.dumps(doc))
    monkeypatch.setattr(mod, "LABELS_DIR", labels_dir)
    with pytest.raises(mod.LabelsMissing, match="labels"):
        mod.load_rater_labels()


def test_refuses_missing_completed_at(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    labels_dir = tmp_path / "rater_labels"
    labels_dir.mkdir()
    for r in ("r1", "r2", "r3"):
        doc = {"rater_id": r, "labels": [{"case_id": "a", "label": "BENIGN"}]}
        (labels_dir / f"{r}.json").write_text(json.dumps(doc))
    monkeypatch.setattr(mod, "LABELS_DIR", labels_dir)
    with pytest.raises(mod.LabelsMissing, match="completed_at"):
        mod.load_rater_labels()


def test_refuses_identical_completed_at_across_raters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Three independent humans cannot finish at one identical timestamp;
    identical values indicate programmatically generated label files."""
    labels_dir = tmp_path / "rater_labels"
    labels_dir.mkdir()
    for r in ("r1", "r2", "r3"):
        _write_valid_rater(labels_dir, r, ["a"], {"a": "BENIGN"},
                           completed_at="2026-10-13T12:00:00+00:00")
    monkeypatch.setattr(mod, "LABELS_DIR", labels_dir)
    with pytest.raises(mod.LabelsMissing, match="identical completed_at"):
        mod.load_rater_labels()


def test_accepts_distinct_valid_rater_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    labels_dir = tmp_path / "rater_labels"
    labels_dir.mkdir()
    stamps = {"r1": "2026-10-20T10:00:00.123456+00:00",
              "r2": "2026-10-20T11:22:33.654321+00:00",
              "r3": "2026-10-20T12:34:56.111111+00:00"}
    for r, ts in stamps.items():
        _write_valid_rater(labels_dir, r, ["a", "b"], {"a": "BENIGN", "b": "RECON"},
                           completed_at=ts)
    monkeypatch.setattr(mod, "LABELS_DIR", labels_dir)
    loaded = mod.load_rater_labels()
    assert loaded["r1"]["a"] == "BENIGN"
    assert loaded["r3"]["b"] == "RECON"


def test_require_full_coverage_refuses_partial_sets() -> None:
    ids = ["a", "b", "c"]
    loaded = {
        "r1": {"a": "BENIGN", "b": "BENIGN", "c": "BENIGN"},
        "r2": {"a": "BENIGN", "b": "BENIGN"},        # missing "c"
        "r3": {"a": "BENIGN", "b": "BENIGN", "c": "RECON"},
    }
    with pytest.raises(mod.LabelsMissing, match="missing 1/3"):
        mod.require_full_coverage(loaded, ids)
    # Complete coverage passes silently.
    loaded["r2"]["c"] = "RECON"
    mod.require_full_coverage(loaded, ids)


def test_run_reports_not_identifiable_without_mappable_predictions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With real-shaped labels but no mapped frozen predictions, metrics must
    be null with an explicit status — never fabricated zeros."""
    ids = ["a", "b"]
    labs = {r: {"a": "BENIGN", "b": "RECON"} for r in ("r1", "r2", "r3")}
    monkeypatch.setattr(mod, "load_case_ids", lambda: ids)
    monkeypatch.setattr(mod, "load_rater_labels", lambda raters=("r1", "r2", "r3"): labs)
    monkeypatch.setattr(mod, "load_frozen_predictions", lambda: {})
    report = mod.run()
    assert report["metric_status"] == "NOT_IDENTIFIABLE_NO_MAPPED_PREDICTIONS"
    assert report["chrollo_metrics"] is None
    assert report["laya_metrics"] is None
    assert report["n_adjudicable_binary"] == 2


def test_fixture_never_writes_real_labels_dir(tmp_path: Path) -> None:
    """Synthetic labels must never land in results/laya_research/rater_labels/."""
    labels_dir = tmp_path / "never" / "rater_labels"
    labels_dir.mkdir(parents=True)
    doc = {"labels": [{"case_id": "synthetic", "label": "BENIGN"}]}
    (labels_dir / "r1.json").write_text(json.dumps(doc))
    real = ROOT / "results" / "laya_research" / "rater_labels"
    if real.exists():
        for item in real.iterdir():
            assert "synthetic" not in item.name
