#!/usr/bin/env python3
"""Generate a deterministic SHA-256 manifest for the pinned verifier red-team
artifacts + research-integrity provenance metadata.

Used by CI (artifact-integrity job) and reproducible locally by researchers.
No network, no LLM keys, no inference — pure local filesystem hashing.

Usage:
    python scripts/verifier_ci_manifest.py \
        --artifacts results/verifier_redteam.json \
                    results/verifier_redteam_live.json \
                    results/verifier_redteam_live_deepseek-v4-flash-free.json \
                    results/verifier_redteam_live_space-bunny-free_prefix.json \
        --out results/verifier_redteam_artifacts_manifest.json \
        --commit HEAD --branch main
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    """Return hex SHA-256 of *path*."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(head: str) -> tuple[str, str, str, bool, list[str]]:
    """Return (commit, branch, tree_status, is_dirty, status_lines)."""
    commit = subprocess.check_output(
        ["git", "rev-parse", head],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()
    branch = subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()
    raw = subprocess.check_output(
        ["git", "status", "--porcelain"],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()
    dirty = bool(raw)
    lines = raw.splitlines() if raw else []
    return commit, branch, raw, dirty, lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Deterministic SHA-256 manifest for verifier red-team artifacts."
    )
    ap.add_argument(
        "--artifacts",
        nargs="+",
        required=True,
        help="Artifact JSON files to fingerprint.",
    )
    ap.add_argument(
        "--out",
        default=Path("results/verifier_redteam_artifacts_manifest.json"),
        type=Path,
        help="Write manifest here.",
    )
    ap.add_argument(
        "--commit",
        default="HEAD",
        help="Git ref to fingerprint (default HEAD).",
    )
    ap.add_argument(
        "--branch",
        default=None,
        help="Expected branch name; defaults to `git branch --show-current`.",
    )
    args = ap.parse_args(argv)

    paths = []
    for p in args.artifacts:
        path = Path(p)
        if not path.is_file():
            print(f"ERROR: artifact not found: {path}", file=sys.stderr)
            return 1
        paths.append(path)

    commit, branch, tree, dirty, status_lines = git(args.commit)
    if args.branch:
        branch = args.branch

    entries: list[dict[str, Any]] = []
    for path in sorted(paths):
        size = path.stat().st_size
        entries.append(
            {
                "path": str(path),
                "sha256": sha256_file(path),
                "size_bytes": size,
                "checked_utc": datetime.now(timezone.utc).isoformat(),
            }
        )

    manifest = {
        "kind": "verifier_redteam_artifact_manifest",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "git_branch": branch,
        "git_dirty": dirty,
        "git_status_lines": status_lines,
        "artifacts": entries,
    }

    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest written: {out}")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
