import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from scripts import bootstrap_ci as bci  # noqa: E402
from scripts.run_baseline_comparison import (  # noqa: E402
    assert_paired_rows,
    manifest_hash,
    provider_metadata,
    scenario_id,
)


def row(suite, name, score=0.5):
    return {"suite": suite, "name": name, "scenario_id": f"{suite}:{name}", "score": score}


def test_scenario_id_stable():
    assert scenario_id("cti_actor", "X") == "cti_actor:X"


def test_manifest_hash_deterministic_and_drift_sensitive():
    rows = [row("s1", "a"), row("s1", "b")]
    h1 = manifest_hash(rows)
    assert h1 == manifest_hash(list(reversed(rows)))
    assert h1 != manifest_hash(rows + [row("s2", "c")])


def test_provider_metadata_shape():
    m = provider_metadata()
    assert set(m) == {"gateway_source", "base_url", "model", "api_key_present"}
    assert isinstance(m["api_key_present"], bool)


def test_assert_paired_rows_ok():
    rows_a = [row("s1", "a"), row("s2", "b")]
    rows_b = [row("s2", "b"), row("s1", "a")]
    audit = assert_paired_rows(rows_a, rows_b)
    assert audit["ok"] and audit["exact_set_equal"]


def test_assert_paired_rows_duplicate():
    rows_a = [row("s1", "a"), row("s1", "a")]
    rows_b = [row("s1", "a")]
    with pytest.raises(AssertionError, match="duplicate"):
        assert_paired_rows(rows_a, rows_b)


def test_assert_paired_rows_asymmetric():
    with pytest.raises(AssertionError, match="asymmetric"):
        assert_paired_rows([row("s1", "a")], [row("s1", "b")])


def test_assert_paired_rows_suite_mismatch():
    with pytest.raises(AssertionError, match="suite membership"):
        assert_paired_rows([row("s1", "a")], [row("s2", "a")])


def test_pairing_audit_ok():
    a = [row("s1", "a"), row("s1", "b")]
    b = [row("s1", "b"), row("s1", "a")]
    audit = bci.pairing_audit(a, b)
    assert audit["ok"] and audit["symmetric_set"] and audit["suite_membership_ok"]
    assert audit["key"] == "scenario_id"


def test_pairing_audit_duplicate():
    audit = bci.pairing_audit([row("s1", "a"), row("s1", "a")], [row("s1", "a")])
    assert not audit["ok"] and audit["arm_a_duplicate_keys"] == ["s1:a"]


def test_pairing_audit_missing_asymmetric():
    audit = bci.pairing_audit([row("s1", "a")], [row("s1", "b")])
    assert not audit["ok"] and not audit["symmetric_set"]


def test_pairing_audit_suite_mismatch():
    audit = bci.pairing_audit([row("s1", "a")], [row("s2", "a")])
    assert not audit["ok"] and not audit["suite_membership_ok"]


def test_pairing_audit_legacy_name_fallback():
    a = [{"suite": "s1", "name": "a", "score": 0.1}]
    b = [{"suite": "s1", "name": "a", "score": 0.2}]
    audit = bci.pairing_audit(a, b)
    assert audit["ok"] and audit["key"] == "name"


def test_paired_diff_ci_suppressed_on_asymmetry():
    a = [row("s1", "a", 0.6), row("s1", "b", 0.7)]
    b = [row("s1", "a", 0.5)]
    assert bci._paired_diff_ci(a, b, seed=1) is None


def test_paired_diff_ci_computed_when_exact():
    a = [row("s1", "a", 0.6), row("s1", "b", 0.7)]
    b = [row("s1", "a", 0.5), row("s1", "b", 0.8)]
    ci = bci._paired_diff_ci(a, b, seed=1)
    assert ci is not None and ci["n"] == 2 and ci["unpaired_dropped"] == 0


def test_b4_section_audit_gate_on_real_artifact():
    out = bci.b4_section()
    assert out["pairing_audit"]["ok"], out["pairing_audit"]["problems"]
    assert out["paired_diff_ci"]["overall"]["n"] == 90
    print(json.dumps(out["pairing_audit"]))
