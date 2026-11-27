"""Release-manifest completeness and strict-build refusal tests.

The interpreter must be started with unique RAGIN_SESSION_DIR and
RAGIN_HOST_FICTION_PATH values; these assignments are a defensive fallback and
never point at the repository's historical/default session directory.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("RAGIN_SESSION_DIR", tempfile.mkdtemp(prefix="ragin-ablation-manifest-session-"))
os.environ.setdefault(
    "RAGIN_HOST_FICTION_PATH",
    str(Path(tempfile.mkdtemp(prefix="ragin-ablation-manifest-fiction-")) / "host_fiction.json"),
)

from ragin.evaluation.release_manifest import (  # noqa: E402
    CATEGORIES,
    ManifestIncomplete,
    build_manifest,
)


def populated_categories(root: Path) -> dict[str, list[Path]]:
    """One present artifact for every non-git category."""
    artifact = root / "artifact.txt"
    artifact.write_text("frozen artifact\n", encoding="utf-8")
    return {category: [artifact] for category in CATEGORIES if category != "git"}


def test_one_present_and_one_missing_file_makes_category_incomplete(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    artifacts = populated_categories(root)
    present = root / "artifact.txt"
    missing = root / "missing_required.txt"
    artifacts["data"] = [present, missing]

    out_root = tmp_path / "out"
    manifest = build_manifest(
        root=root,
        release_id="rel-partial",
        artifacts_by_category=artifacts,
        out_root=out_root,
    )

    assert manifest.status == "INCOMPLETE"
    assert manifest.missing_categories == ["data"]
    data_artifacts = [artifact for artifact in manifest.artifacts if artifact.category == "data"]
    assert {artifact.status for artifact in data_artifacts} == {"PRESENT", "MISSING"}
    payload = json.loads((out_root / "rel-partial" / "manifest.json").read_text(encoding="utf-8"))
    assert payload["status"] == "INCOMPLETE"
    assert payload["missing_categories"] == ["data"]

    strict_out = tmp_path / "strict-out"
    with pytest.raises(ManifestIncomplete, match="data"):
        build_manifest(
            root=root,
            release_id="rel-strict-partial",
            artifacts_by_category=artifacts,
            out_root=strict_out,
            strict=True,
        )
    assert not (strict_out / "rel-strict-partial").exists()


def test_empty_category_is_incomplete_and_strict_build_refuses(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    artifacts = populated_categories(root)
    artifacts["prompts"] = []

    out_root = tmp_path / "out"
    manifest = build_manifest(
        root=root,
        release_id="rel-empty",
        artifacts_by_category=artifacts,
        out_root=out_root,
    )

    assert manifest.status == "INCOMPLETE"
    assert manifest.missing_categories == ["prompts"]
    assert not [artifact for artifact in manifest.artifacts if artifact.category == "prompts"]

    strict_out = tmp_path / "strict-out"
    with pytest.raises(ManifestIncomplete, match="prompts"):
        build_manifest(
            root=root,
            release_id="rel-strict-empty",
            artifacts_by_category=artifacts,
            out_root=strict_out,
            strict=True,
        )
    assert not (strict_out / "rel-strict-empty").exists()


def test_every_category_present_produces_complete_manifest(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    artifacts = populated_categories(root)

    manifest = build_manifest(
        root=root,
        release_id="rel-complete",
        artifacts_by_category=artifacts,
        out_root=tmp_path / "out",
        strict=True,
    )

    assert manifest.status == "COMPLETE"
    assert manifest.missing_categories == []
    assert {artifact.category for artifact in manifest.artifacts} == set(CATEGORIES) - {"git"}
