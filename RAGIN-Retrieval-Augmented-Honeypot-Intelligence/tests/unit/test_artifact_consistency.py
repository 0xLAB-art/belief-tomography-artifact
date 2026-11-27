"""Regression locks for the artifact-consistency checker (§VI-C / App. A).

The paper prints three decimals; the artifacts store four-decimal raws.  The
first manual paper<->artifact cross-check produced seven false failures from
exactly that gap (exact equality vs printed values, and ``cases`` field
semantics: the offline artifact stores a LIST of per-case dicts, the live
artifacts an INT).  ``scripts/verifier_redteam_check.py`` encodes the
corrected logic; these tests pin it so paper<->artifact drift fails loudly
and permanently.

Pinned here:

AC1  the checker passes on the repo's committed artifacts (exit 0);
AC2  tampering with any pinned value flips the exit code to 1 and names
     the drift (rounded metric, count, list length, missing field);
AC3  internal-consistency checking catches counts edited inconsistently
     with the stored rates;
AC4  the ``r3`` rounding helper maps the exact raws that broke the manual
     pass to the paper's printed values (0.9306→0.931, 0.9415→0.942,
     0.9767→0.977, 0.9938→0.994, 0.9945→0.995).

Fully offline: the checker reads local JSONs only and must never touch the
live harness's network path.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import verifier_redteam_check as chk  # noqa: E402

SCRIPT = ROOT / "scripts" / "verifier_redteam_check.py"

# The four artifacts the paper's §VI-C census and App. A index cite.
ARTIFACTS = (
    "verifier_redteam.json",
    "verifier_redteam_live_deepseek-v4-flash-free.json",
    "verifier_redteam_live.json",
    "verifier_redteam_live_space-bunny-free_prefix.json",
)


@pytest.fixture
def results_copy(tmp_path: Path) -> Path:
    """A writable copy of the committed red-team artifacts."""
    dst = tmp_path / "results"
    dst.mkdir()
    for name in ARTIFACTS:
        shutil.copy(ROOT / "results" / name, dst / name)
    return dst


def _tamper(results: Path, name: str, mutate) -> None:
    path = results / name
    doc = json.loads(path.read_text(encoding="utf-8"))
    mutate(doc)
    path.write_text(json.dumps(doc), encoding="utf-8")


# ── AC1: repo artifacts pass ────────────────────────────────────────────────
def test_checker_passes_on_repo_artifacts() -> None:
    assert chk.main([]) == 0


def test_checker_cli_exits_zero(results_copy: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--results-dir", str(results_copy)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS: all" in proc.stdout


# ── AC2: tampering is caught ────────────────────────────────────────────────
def test_tampered_precision_fails(results_copy: Path) -> None:
    # A drift that still prints to 3 decimals the paper does not claim.
    _tamper(
        results_copy,
        "verifier_redteam_live_deepseek-v4-flash-free.json",
        lambda d: d["overall"].__setitem__("recall", 0.9306 + 0.001),
    )
    assert chk.main(["--results-dir", str(results_copy)]) == 1


def test_tampered_count_fails(results_copy: Path) -> None:
    _tamper(
        results_copy,
        "verifier_redteam_live.json",
        lambda d: d["overall"].__setitem__("false_positives", 0),
    )
    assert chk.main(["--results-dir", str(results_copy)]) == 1


def test_tampered_cases_int_fails(results_copy: Path) -> None:
    _tamper(
        results_copy,
        "verifier_redteam_live.json",
        lambda d: d.__setitem__("cases", 80),
    )
    assert chk.main(["--results-dir", str(results_copy)]) == 1


def test_tampered_cases_list_fails(results_copy: Path) -> None:
    _tamper(
        results_copy,
        "verifier_redteam.json",
        lambda d: d["cases"].pop(),
    )
    assert chk.main(["--results-dir", str(results_copy)]) == 1


def test_cases_list_semantics_guarded(results_copy: Path) -> None:
    # The live artifacts store cases as an INT; only the offline artifact is
    # a list.  A list/INT mixup is exactly the class of bug the first manual
    # pass hit, so pin that the checker accepts each artifact's real shape.
    assert isinstance(
        json.loads((results_copy / "verifier_redteam.json").read_text())["cases"],
        list,
    )
    for name in ARTIFACTS[1:]:
        assert isinstance(json.loads((results_copy / name).read_text())["cases"], int), name


def test_missing_artifact_fails(results_copy: Path) -> None:
    (results_copy / "verifier_redteam.json").unlink()
    assert chk.main(["--results-dir", str(results_copy)]) == 1


# ── AC3: internal consistency ───────────────────────────────────────────────
def test_internally_inconsistent_counts_fail(results_copy: Path) -> None:
    # Bump false_negatives alone: the count sum (tp+fn != should_reject) AND
    # the stored recall rate (no longer tp/(tp+fn)) both drift, so a
    # corrupted count fails even if headline metrics were left alone.
    def mutate(d):
        d["overall"]["false_negatives"] += 1

    _tamper(results_copy, "verifier_redteam_live.json", mutate)
    assert chk.main(["--results-dir", str(results_copy)]) == 1


# ── AC4: rounding contract ──────────────────────────────────────────────────
@pytest.mark.parametrize(
    "raw,printed",
    [
        (0.9306, 0.931),  # deepseek recall
        (0.9415, 0.942),  # prefix recall
        (0.9767, 0.977),  # deepseek Wilson P lo
        (0.9938, 0.994),  # prefix precision
        (0.9945, 0.995),  # post-fix precision
        (0.9875, 0.988),  # deepseek agreement rate
    ],
)
def test_r3_matches_paper_printing(raw: float, printed: float) -> None:
    assert chk.r3(raw) == printed


def test_r3_is_stable_for_exact_values() -> None:
    assert chk.r3(1.0) == 1.0
    assert chk.r3(0.943) == 0.943
    assert chk.r3(1) == 1.0


# ── AC5: JEV hard-subset artifact interpretation lock ──────────────────────
def test_jev_hard_subset_counts_and_resolution_consistent() -> None:
    doc = json.loads((ROOT / "results" / "jev_hard_subset.json").read_text(encoding="utf-8"))
    assert doc["ceiling"]["base_incorrect_informative"] == 6
    assert len(doc["informative_rows"]) == 6
    assert doc["jev_arm"]["assessed"] == 1
    assert doc["jev_arm"]["unavailable"] == 5
    assert doc["jev_arm"]["rescued"] == 1
    assert "stratum is empty" not in doc["resolution_statement"]
