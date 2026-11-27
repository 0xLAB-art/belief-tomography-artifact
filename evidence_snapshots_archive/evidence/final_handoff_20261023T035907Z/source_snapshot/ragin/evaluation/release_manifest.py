"""Immutable SHA-256 release manifest builder.

The manifest records *what was actually used*: git revision and dirty-source
hash, configs, model/checkpoint, data, prompts, allocation seeds, cost and
latency artifacts, and raw served transcripts. Missing categories make the
package ``INCOMPLETE`` and a strict build fails.

The manifest stores paths and hashes only. It never embeds credentials, raw
private attacker data, or file contents.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CATEGORIES = (
    "git",
    "source",
    "configs",
    "model",
    "data",
    "prompts",
    "seeds",
    "costs",
    "latency",
    "raw_served",
)
SAFE_ID_RE = re.compile(r"[A-Za-z0-9._-]+")
FORBIDDEN_NAME_RE = re.compile(r"(secret|credential|password|token|api[_-]?key)", re.IGNORECASE)


class ManifestIncomplete(RuntimeError):  # noqa: N818 - public API name is already frozen
    """Raised when a strict package is missing required artifacts."""


@dataclass
class Artifact:
    category: str
    path: str
    sha256: str
    bytes: int
    status: str = "PRESENT"

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "path": self.path,
            "sha256": self.sha256,
            "bytes": self.bytes,
            "status": self.status,
        }


@dataclass
class Manifest:
    release_id: str
    status: str
    created_utc: str
    git: dict[str, Any]
    artifacts: list[Artifact] = field(default_factory=list)
    missing_categories: list[str] = field(default_factory=list)
    unavailable: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "ragin.ablation.release_manifest.v1",
            "release_id": self.release_id,
            "status": self.status,
            "created_utc": self.created_utc,
            "immutable": True,
            "git": self.git,
            "categories": list(CATEGORIES),
            "missing_categories": self.missing_categories,
            "unavailable": self.unavailable,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "metadata": self.metadata,
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    return proc.stdout


def git_state(root: Path) -> dict[str, Any]:
    status = _git(root, "status", "--porcelain=v1")
    diff = _git(root, "diff")
    head = _git(root, "rev-parse", "HEAD").strip()
    return {
        "head": head,
        "dirty": bool(status.strip() or diff.strip()),
        "status_sha256": hashlib.sha256(status.encode()).hexdigest(),
        "diff_sha256": hashlib.sha256(diff.encode()).hexdigest(),
        "status_line_count": len(status.splitlines()),
    }


def _validate_release_id(release_id: str) -> None:
    if not SAFE_ID_RE.fullmatch(release_id) or release_id in {".", ".."}:
        raise ValueError(f"unsafe release id: {release_id!r}")


def _collect(
    category: str,
    paths: list[Path],
    *,
    root: Path,
    artifacts: list[Artifact],
    missing: list[str],
) -> None:
    present = 0
    missing_any = False
    for path in paths:
        if not path.exists():
            artifacts.append(
                Artifact(
                    category=category,
                    path=str(path),
                    sha256="",
                    bytes=0,
                    status="MISSING",
                )
            )
            missing_any = True
            continue
        try:
            relative = str(path.resolve().relative_to(root.resolve()))
        except ValueError:
            relative = str(path.resolve())
        if FORBIDDEN_NAME_RE.search(path.name):
            raise ValueError(f"refusing to manifest a credential-looking filename: {path.name}")
        artifacts.append(
            Artifact(
                category=category,
                path=relative,
                sha256=sha256_file(path),
                bytes=path.stat().st_size,
            )
        )
        present += 1
    # A category with one present and one missing required file is INCOMPLETE.
    # Presence of any single file must never mask a missing peer artifact.
    if present == 0 or missing_any:
        missing.append(category)


def build_manifest(
    *,
    root: Path,
    release_id: str,
    artifacts_by_category: dict[str, list[Path]],
    out_root: Path,
    metadata: dict[str, Any] | None = None,
    unavailable: dict[str, str] | None = None,
    strict: bool = False,
) -> Manifest:
    _validate_release_id(release_id)
    unknown = set(artifacts_by_category) - set(CATEGORIES)
    if unknown:
        raise ValueError(f"unknown artifact categories: {sorted(unknown)}")
    target_dir = out_root / release_id
    if target_dir.exists():
        raise FileExistsError(f"immutable release namespace already exists: {target_dir}")

    git = git_state(root)
    artifacts: list[Artifact] = []
    missing: list[str] = []
    for category in CATEGORIES:
        if category == "git":
            continue
        _collect(
            category,
            list(artifacts_by_category.get(category, [])),
            root=root,
            artifacts=artifacts,
            missing=missing,
        )
    manifest = Manifest(
        release_id=release_id,
        status="COMPLETE" if not missing else "INCOMPLETE",
        created_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        git=git,
        artifacts=artifacts,
        missing_categories=missing,
        unavailable=dict(unavailable or {}),
        metadata=dict(metadata or {}),
    )
    if strict and missing:
        raise ManifestIncomplete(f"missing artifact categories: {missing}")
    if manifest.status == "INCOMPLETE" and strict:
        raise ManifestIncomplete(f"manifest is INCOMPLETE: {missing}")

    # Recompute every hash immediately before writing; a changed input is a
    # hard failure, not a silently stale manifest.
    for artifact in artifacts:
        if artifact.status != "PRESENT":
            continue
        path = (root / artifact.path) if not Path(artifact.path).is_absolute() else Path(artifact.path)
        current = sha256_file(path)
        if current != artifact.sha256:
            raise RuntimeError(f"artifact changed while building the manifest: {artifact.path}")

    target_dir.mkdir(parents=True, exist_ok=False)
    manifest_path = target_dir / "manifest.json"
    payload = json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n"
    with manifest_path.open("x", encoding="utf-8") as handle:
        handle.write(payload)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    sidecar = target_dir / "manifest.sha256"
    with sidecar.open("x", encoding="utf-8") as handle:
        handle.write(f"{digest}  manifest.json\n")
    os.chmod(manifest_path, 0o444)
    os.chmod(sidecar, 0o444)
    return manifest


def verify_manifest(path: Path, *, root: Path) -> dict[str, Any]:
    payload = path.read_text(encoding="utf-8")
    manifest = json.loads(payload)
    failures: list[str] = []
    checked = 0
    for artifact in manifest.get("artifacts", []):
        if artifact.get("status") != "PRESENT":
            failures.append(f"missing artifact: {artifact.get('category')} {artifact.get('path')}")
            continue
        target = Path(artifact["path"])
        if not target.is_absolute():
            target = root / target
        if not target.exists():
            failures.append(f"artifact disappeared: {artifact['path']}")
            continue
        checked += 1
        if sha256_file(target) != artifact["sha256"]:
            failures.append(f"artifact changed: {artifact['path']}")
    for category in manifest.get("missing_categories", []):
        failures.append(f"category absent at build time: {category}")
    return {
        "status": "VERIFIED" if not failures else "CHANGED_OR_INCOMPLETE",
        "checked": checked,
        "failures": failures,
        "manifest_sha256": hashlib.sha256(payload.encode()).hexdigest(),
    }
