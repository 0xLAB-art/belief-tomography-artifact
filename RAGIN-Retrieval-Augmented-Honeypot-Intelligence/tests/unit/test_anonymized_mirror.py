"""The anonymised mirror must satisfy the appendix it ships beside.

R3-2 and R3-3 in the round-3 audit were the same defect twice: the mirror's
verification was correct and available, but nothing ran it, so a bundle went
stale against the appendix and kept a PASS it had stopped earning. Round 1 had
already flagged unresolved appendix paths as reviewer friction, so this asserts
the *cause* rather than the instance: every ``\\path{}`` target the shipped
appendix names must be inside the mirror's allowlist.

These tests read the allowlist and the appendix. They build nothing, so they are
fast and safe to run in any suite; ``--check`` on the builder covers the bundle
itself.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts" / "build_anonymized_mirror.py"
APPENDIX = ROOT / "paper" / "sections" / "sp_appendix.tex"


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_anonymized_mirror", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def builder():
    return _load_builder()


@pytest.fixture(scope="module")
def appendix_targets() -> set[str]:
    return set(re.findall(r"\\path\{([^}]+)\}", APPENDIX.read_text()))


def test_appendix_declares_targets(appendix_targets):
    assert appendix_targets, "appendix names no artifact paths; the contract is vacuous"


def test_every_appendix_path_is_in_the_mirror(builder, appendix_targets):
    allowlist = (
        set(builder.PAPER_FILES)
        | set(builder.SCRIPT_FILES)
        | set(builder.RESULT_FILES)
        | set(builder.DOC_FILES)
        | set(builder.SUPPORT_FILES)
    )
    missing = sorted(appendix_targets - allowlist)
    assert not missing, (
        "appendix names paths the mirror does not contain: "
        f"{missing}. A reviewer following the appendix finds a dangling reference."
    )


def test_builder_is_part_of_its_own_version_of_record(builder):
    assert "scripts/build_anonymized_mirror.py" in builder.SCRIPT_FILES, (
        "the appendix names the builder, so the bundle must contain it; "
        "removing it makes the mirror fail its own path contract"
    )


def test_no_excluded_name_can_enter_via_the_allowlist(builder):
    allowlist = (
        set(builder.PAPER_FILES)
        | set(builder.SCRIPT_FILES)
        | set(builder.RESULT_FILES)
        | set(builder.DOC_FILES)
        | set(builder.SUPPORT_FILES)
    )
    for rel in allowlist:
        assert not builder.is_excluded(rel), f"{rel} is allowlisted but excluded by policy"
        assert (ROOT / rel).is_file(), f"{rel} is allowlisted but does not exist"


def test_unblinding_key_is_never_shipped(builder):
    assert "cti_audit_blinding_key.json" in builder.EXCLUDE_NAMES
    allowlist = set(builder.RESULT_FILES)
    assert not any("blinding_key" in rel for rel in allowlist)
