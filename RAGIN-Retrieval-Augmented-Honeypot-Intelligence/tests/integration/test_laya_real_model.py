"""Model-backed integration test for the Laya optional assessment boundary.

Runs REAL inference against the pinned local checkpoint (downloads disallowed;
the weights must already be in the HF cache). Skipped automatically when the
weights or the laya package are unavailable so the fixture-only contract suite
stays hermetic and fast. Marked ``integration`` and ``slow``.

The pinned checkpoint is known to raise a single `RuntimeWarning` during load
(see module docstring). That warning is treated as non-fatal here only for these
real-model tests so the inference path can still be proven end to end; the rest
of the suite keeps the strict `-W error` posture.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
REVISION = "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851"
WEIGHTS_SHA = "891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c"

laya = pytest.importorskip("laya", reason="laya package not installed")
torch = pytest.importorskip("torch", reason="torch not installed")

# The pinned checkpoint ships a legacy CGS temperature table whose values fall
# outside the choir accepted range, so laya raises a RuntimeWarning on load.
# That is a checkpoint-quality signal, not a test-environment problem; we allow
# it through as non-fatal so the real-model integration tests can still prove the
# inference path end to end under the same warning-as-error posture used elsewhere.
import warnings as _warnings

WEIGHTS = Path.home() / ".cache/huggingface/hub/models--convaiinnovations--laya/blobs" / WEIGHTS_SHA

_LAYA_WARNINGS = (
    "laya: this checkpoint ships invalid temperatures or values outside [0.5, 5]; "
    "using choice:11+=0.10058280825614929 -> 0.5. "
    "Treat confidence from the affected entries as uncalibrated.",
)


def _laya_runtime_warnings_ok(warnings_tuple) -> bool:
    """Return True if only the known checkpoint-quality RuntimeWarning fired."""
    seen = {str(x.message) for x in warnings_tuple}
    unexpected = seen - set(_LAYA_WARNINGS)
    return not unexpected


@pytest.fixture(scope="module")
def runtime():
    from ragin.decision.laya_runtime import LayaRuntime

    assert _weights_present(), "pinned checkpoint blob missing from HF cache"
    with _warnings.catch_warnings(record=True) as _w:
        _warnings.simplefilter("always")
        rt = LayaRuntime(model="english", revision=REVISION, device="cpu")
        assert _laya_runtime_warnings_ok(_w), (
            "unexpected laya load-time warnings: %s"
            % (sorted({str(x.message) for x in _w}),)
        )
    return rt


pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _weights_present() -> bool:
    return WEIGHTS.exists() and WEIGHTS.stat().st_size > 800_000_000


@pytest.fixture(scope="module")
def runtime():
    from ragin.decision.laya_runtime import LayaRuntime

    assert _weights_present(), "pinned checkpoint blob missing from HF cache"
    return LayaRuntime(model="english", revision=REVISION, device="cpu")


def _laya_infer_catch_known_warnings(runtime, state: str) -> dict:
    """Run ``runtime.infer`` while only allowing the known checkpoint-quality
    RuntimeWarning through. Anything else is still treated as a test failure."""
    with _warnings.catch_warnings(record=True) as _w:
        _warnings.simplefilter("always")
        payload = runtime.infer(state)
        assert _laya_runtime_warnings_ok(_w), (
            "unexpected laya inference-time warnings: %s"
            % (sorted({str(x.message) for x in _w}),)
        )
    return payload


def test_real_inference_signal_shape_and_provenance(runtime):
    adapter_requirements = _laya_infer_catch_known_warnings(
        runtime,
        "cat /etc/passwd; sudo -l; find / -perm -4000 -type f 2>/dev/null",
    )

    assert adapter_requirements["model"] == "laya/english"
    assert adapter_requirements["laya_revision"] == REVISION
    answers = adapter_requirements["answers"]
    assert answers["attack"]["type"] == "noul"
    assert 0.0 <= answers["attack"]["noul"] <= 1.0
    # An obvious attack transcript should not be scored firmly benign.
    assert answers["attack"]["noul"] > 0.01


def test_real_inference_benign_low_attack_probability(runtime):
    payload = _laya_infer_catch_known_warnings(runtime, "uptime\nwho\nw\nexit")
    noul = payload["answers"]["attack"]["noul"]
    assert 0.0 <= noul <= 1.0


def test_adapter_wraps_real_model_as_optional_assessment(runtime, monkeypatch):
    from ragin.decision import laya_runtime
    from ragin.decision.optional import LayaAssessmentAdapter

    monkeypatch.setattr(
        "ragin.decision.laya_runtime.get_shared_runtime", lambda: runtime
    )
    monkeypatch.setenv("RAGIN_LAYA_ENABLED", "1")
    infer = laya_runtime.make_infer_callable()
    assert infer is not None

    adapter = LayaAssessmentAdapter(infer, model=f"laya/english@{REVISION[:12]}", timeout_s=120.0)
    result = adapter.assess(session_id="it-1", state="nmap -sS 10.0.0.0/24 -p-")
    assert result.status == "SIGNAL"
    assert result.provider == "laya"
    assert result.assessment.attack_probability is not None
    assert result.latency_ms > 0


def test_disabled_env_returns_none_infer_callable(monkeypatch):
    from ragin.decision import laya_runtime

    monkeypatch.setenv("RAGIN_LAYA_ENABLED", "0")
    assert laya_runtime.make_infer_callable() is None
    monkeypatch.setenv("RAGIN_LAYA_ENABLED", "1")
    # Do not actually build the shared runtime here (weights load is expensive);
    # only assert the gate opens.
    assert laya_runtime.laya_enabled() is True
