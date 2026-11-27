"""Figure geometry audit as a regression gate (paper Appendix F).

Each paper figure must re-render in isolation and pass the pixel-level
scan: no ink run may cross a node interior, nothing may be clipped at
the canvas border. A figure regression therefore fails CI instead of
waiting for a sharp-eyed reader. Skips cleanly when the TeX toolchain
or Pillow is absent (e.g. CI runners without TeX Live get the dedicated
``paper-figures`` job instead); results are cached per figure-source
hash, so repeat local runs are instant.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("PIL")

REPO = Path(__file__).resolve().parents[2]
AUDITOR = REPO / "scripts" / "audit_figure_geometry.py"
CACHE_DIR = Path(tempfile.gettempdir()) / "ragin_figaudit_cache"

EXPECTED_FIGURES = ("ladder", "architecture", "results", "grounding", "funnel")


def _load_auditor():
    spec = importlib.util.spec_from_file_location("audit_figure_geometry", AUDITOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tool_missing() -> str | None:
    for tool in ("pdflatex", "pdftoppm"):
        if shutil.which(tool) is None:
            return tool
    return None


@pytest.fixture(scope="session")
def figure_audit():
    """Audit result dict for all five figures, cached by source hash."""
    missing = _tool_missing()
    if missing:
        pytest.skip(f"TeX toolchain not available ({missing} not on PATH)")
    mod = _load_auditor()

    hasher = hashlib.sha256()
    for name in EXPECTED_FIGURES:
        hasher.update((REPO / "paper" / "figures" / f"{name}.tex").read_bytes())
    hasher.update(AUDITOR.read_bytes())
    cache_file = CACHE_DIR / f"{hasher.hexdigest()[:24]}.json"

    if cache_file.exists():
        return json.loads(cache_file.read_text())

    # pdflatex writes progress banners to the captured stdout; silence the
    # lookups so failing test output stays readable.
    real_which = shutil.which

    def quiet_which(cmd, *a, **kw):
        if cmd in ("pdflatex", "pdftoppm"):
            return "/usr/bin/" + cmd
        return real_which(cmd, *a, **kw)

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(shutil, "which", quiet_which)
        results = mod.run_audit()
    finally:
        monkeypatch.undo()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(results))
    return results


def test_audit_covers_all_five_paper_figures():
    """Every figure shipped in paper/figures/ is covered by the auditor."""
    mod = _load_auditor()
    audited = set(mod.FIGURES)
    missing = audited.symmetric_difference(EXPECTED_FIGURES)
    assert not missing, f"auditor/figure drift: {sorted(missing)}"


def test_each_figure_passes_geometry_audit(figure_audit):
    """No clipped content, no ink run crossing any node interior."""
    failures = []
    for name, res in figure_audit.items():
        if res["verdict"] != "pass":
            detail = res.get("defects") or res.get("error", "unknown failure")
            failures.append(f"{name}: {detail}")
    assert not failures, "figure geometry regression:\n" + "\n".join(failures)


def test_interior_scan_ran_on_every_rendered_figure(figure_audit):
    """The mechanical check must actually have scanned each render."""
    for name, res in figure_audit.items():
        assert res["verdict"] != "ERROR", f"{name}: {res.get('error')}"
        assert "interior_crossings" in res, name
        assert "long_run_inventory" in res, name
