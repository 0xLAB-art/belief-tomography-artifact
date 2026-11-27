"""Focused tests for the server_v2 optional Laya config surface.

These test the NEW server_v2 first-class config helper only. They do NOT touch
the existing mandatory verifier / HITL / fiction-commit path, and they do NOT
add a second serving path.

Current intended behavior (documented in server_v2.py):
- Default OFF.
- Explicit opt-in values: "1", "true", "yes", "on" (case-insensitive).
- Invalid / non-standard values treated as OFF safely.
- Missing Laya runtime --> NO_SIGNAL, not a crash (covered by the existing
  optional-assessment / adapter tests; here we only assert the server_v2 config
  predicate and that invalid config fails safely).
"""
from __future__ import annotations

import importlib
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _reload_server_v2() -> object:
    import ragin.server_v2 as sv2
    importlib.reload(sv2)
    return sv2


@pytest.fixture(autouse=True)
def _clean_laya_env():
    os.environ.pop("RAGIN_LAYA_ENABLED", None)
    os.environ.pop("RAGIN_LAYA_TIMEOUT_S", None)
    yield
    os.environ.pop("RAGIN_LAYA_ENABLED", None)
    os.environ.pop("RAGIN_LAYA_TIMEOUT_S", None)
    _reload_server_v2()


def _sv2() -> object:
    import importlib

    import ragin.server_v2 as _sv2
    importlib.reload(_sv2)
    return _sv2


def test_default_disabled():
    sv = _sv2()
    assert sv.laya_enabled() is False
    assert sv.laya_enabled_str() == "0"


def test_explicit_opt_in_1():
    os.environ["RAGIN_LAYA_ENABLED"] = "1"
    sv = _reload_server_v2()
    assert sv.laya_enabled() is True
    assert sv.laya_enabled_str() == "1"


def test_explicit_opt_in_true():
    os.environ["RAGIN_LAYA_ENABLED"] = "true"
    sv = _reload_server_v2()
    assert sv.laya_enabled() is True
    assert sv.laya_enabled_str() == "true"


def test_explicit_opt_in_yes():
    os.environ["RAGIN_LAYA_ENABLED"] = "yes"
    sv = _reload_server_v2()
    assert sv.laya_enabled() is True
    assert sv.laya_enabled_str() == "yes"


def test_explicit_opt_in_on():
    os.environ["RAGIN_LAYA_ENABLED"] = "on"
    sv = _reload_server_v2()
    assert sv.laya_enabled() is True
    assert sv.laya_enabled_str() == "on"


def test_case_insensitive_opt_in():
    os.environ["RAGIN_LAYA_ENABLED"] = "TRUE"
    sv = _reload_server_v2()
    assert sv.laya_enabled() is True
    assert sv.laya_enabled_str() == "true"


def test_invalid_value_stays_off():
    os.environ["RAGIN_LAYA_ENABLED"] = "yesplease"
    sv = _reload_server_v2()
    assert sv.laya_enabled() is False
    assert sv.laya_enabled_str() == "yesplease"


def test_empty_string_stays_off():
    os.environ["RAGIN_LAYA_ENABLED"] = ""
    sv = _reload_server_v2()
    assert sv.laya_enabled() is False
    assert sv.laya_enabled_str() == ""


def test_whitespace_only_stays_off():
    os.environ["RAGIN_LAYA_ENABLED"] = "   \t  "
    sv = _reload_server_v2()
    assert sv.laya_enabled() is False
    assert sv.laya_enabled_str() == ""


def test_timeout_default():
    sv = _reload_server_v2()
    assert sv.laya_timeout_s() == 30.0


def test_timeout_custom():
    os.environ["RAGIN_LAYA_TIMEOUT_S"] = "12.5"
    sv = _reload_server_v2()
    assert sv.laya_timeout_s() == 12.5


def test_symbol_name_constant():
    sv = _reload_server_v2()
    assert sv.laya_symbol_name() == "laya"


def test_invalid_config_does_not_raise():
    # Invalid config must fail safely, not crash the server startup path.
    os.environ["RAGIN_LAYA_ENABLED"] = "definitely-not-a-boolean"
    sv = _reload_server_v2()
    # The predicate must still be callable and return a bool.
    enabled = sv.laya_enabled()
    assert isinstance(enabled, bool)
    assert enabled is False
