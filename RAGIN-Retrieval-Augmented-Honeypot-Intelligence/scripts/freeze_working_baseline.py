#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import importlib.metadata


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/baseline_freeze/worktree_manifest.jsonl"
SUMMARY = ROOT / "docs/baseline_freeze/baseline_manifest.json"
ALLOWLIST = (
    "RAGIN_RUNTIME_MODE", "RAGIN_DECISION_ARM", "RAGIN_V4_ENABLED", "RAGIN_V4_SELECTOR",
    "RAGIN_EVIDENCE_JUDGE_ENABLED", "RAGIN_EVIDENCE_JUDGE_FILTERING_ENABLED",
    "RAGIN_LAYA_ENABLED", "RAGIN_LAYA_EVAL_REQUIRE_REAL_MODEL", "RAGIN_LAYA_MODEL",
    "RAGIN_LAYA_REVISION", "RAGIN_LAYA_DEVICE", "RAGIN_LAYA_TIMEOUT_S",
    "RAGIN_PROVIDER_ENABLED", "RAGIN_REQUIRE_AUTH", "RAGIN_RAG_MODE",
    "RAGIN_DON_RETRIEVAL_VERSION", "RAGIN_DON_V2_CORPUS_PATH", "RAGIN_HOST_FICTION_PATH",
    "RAGIN_CORPUS_PATH", "RAGIN_VECTOR_STORE_PATH", "RAGIN_EMBED_MODEL",
    "RAGIN_DON_MODEL", "RAGIN_GATEWAY_TIMEOUT", "RAGIN_HOST_FICTION_POLICY",
    "RAGIN_LAYA_CHECKPOINT_SHA256", "HF_HOME", "HF_HUB_CACHE", "HF_HUB_OFFLINE",
)
INPUTS = (
    "ragin/server_v2.py", "ragin/cycle/sandbox.py", "ragin/cycle/harness.py",
    "ragin/cycle/adapters.py", "ragin/don/rag_engine.py", "ragin/don/evidence_judge.py",
    "ragin/don/intel_corpus.py", "ragin/don/vector_store.py", "ragin/don/command_aware_v2.py", "ragin/decision/laya_runtime.py",
    "ragin/decision/laya_decision.py", "ragin/decision_fusion_v4/runtime_mode.py",
    "ragin/decision_fusion_v4/config.py", "ragin/decision_fusion_v4/evidence_export.py",
    "pyproject.toml", "uv.lock", "requirements-runtime.txt", "docker-compose.yml",
    "docker-compose.field.yml", ".env.example", ".env.field.example",
    "data/mitre_stix/enterprise-attack.json", "data/corpus/mitre_attack.jsonl", "data/corpus/command_aware_v2.jsonl",
    "data/host_fiction.json",
)
PACKAGES = ("laya", "torch", "transformers", "sentence-transformers", "scikit-learn", "pydantic", "fastapi", "uvicorn", "numpy", "pandas", "aiohttp")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    captured_at = datetime.now(timezone.utc).isoformat()
    raw = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=ROOT
    )
    items = raw.split(b"\0")
    records: list[dict[str, object]] = []
    index = 0
    while index < len(items):
        item = items[index]
        index += 1
        if not item:
            continue
        status = item[:2].decode("ascii", errors="replace")
        path_bytes = item[3:]
        path = os.fsdecode(path_bytes)
        if "R" in status or "C" in status:
            previous = os.fsdecode(items[index]) if index < len(items) else ""
            index += 1
        else:
            previous = None
        target = ROOT / path
        record: dict[str, object] = {
            "path": path,
            "status": status,
            "previous_path": previous,
            "captured_at_utc": captured_at,
        }
        try:
            stat = target.lstat()
            record["kind"] = "symlink" if target.is_symlink() else "file" if target.is_file() else "directory" if target.is_dir() else "other"
            record["size_bytes"] = stat.st_size
            if target.is_symlink():
                link = os.fsencode(os.readlink(target))
                record["sha256"] = sha256_bytes(link)
                record["hash_basis"] = "symlink_target_bytes"
            elif target.is_file() and target in {OUT, SUMMARY}:
                record["sha256"] = None
                record["hash_basis"] = "snapshot_self_reference_excluded"
            elif target.is_file():
                record["sha256"] = sha256_file(target)
                record["hash_basis"] = "file_bytes"
            else:
                record["sha256"] = None
                record["hash_basis"] = "not_regular_file"
        except FileNotFoundError:
            record["kind"] = "missing"
            record["size_bytes"] = None
            record["sha256"] = None
            record["hash_basis"] = "missing_at_capture"
        except OSError as exc:
            record["kind"] = "unreadable"
            record["size_bytes"] = None
            record["sha256"] = None
            record["hash_basis"] = f"error:{type(exc).__name__}"
        records.append(record)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    inputs = {}
    for name in INPUTS:
        path = ROOT / name
        inputs[name] = {"exists": path.is_file(), "size_bytes": path.stat().st_size if path.is_file() else None, "sha256": sha256_file(path) if path.is_file() else None}
    checkpoint = Path(os.environ.get("HF_HUB_CACHE", Path(os.environ.get("HF_HOME", Path.home() / ".cache/huggingface")) / "hub")) / "models--convaiinnovations--laya" / "snapshots" / os.environ.get("RAGIN_LAYA_REVISION", "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851") / "model.safetensors"
    checkpoint_info = {"path": str(checkpoint), "exists": checkpoint.is_file(), "size_bytes": checkpoint.stat().st_size if checkpoint.is_file() else None, "sha256": sha256_file(checkpoint) if checkpoint.is_file() else None}
    embed_model = os.environ.get("RAGIN_EMBED_MODEL", "all-MiniLM-L6-v2")
    embed_model_id = "sentence-transformers/all-MiniLM-L6-v2" if embed_model == "all-MiniLM-L6-v2" else embed_model
    hub_cache = Path(os.environ.get("HF_HUB_CACHE", Path(os.environ.get("HF_HOME", Path.home() / ".cache/huggingface")) / "hub"))
    embed_cache = hub_cache / ("models--" + embed_model_id.replace("/", "--"))
    embed_ref = embed_cache / "refs/main"
    embed_revision = embed_ref.read_text(encoding="utf-8").strip() if embed_ref.is_file() else None
    embed_snapshot = embed_cache / "snapshots" / embed_revision if embed_revision else None
    embed_assets = {}
    if embed_snapshot and embed_snapshot.is_dir():
        for path in sorted(p for p in embed_snapshot.rglob("*") if p.is_file()):
            embed_assets[path.relative_to(embed_snapshot).as_posix()] = {"size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
    embedding_checkpoint = {"model": embed_model, "repository_id": embed_model_id, "cache_path": str(embed_cache), "revision": embed_revision, "snapshot_exists": bool(embed_snapshot and embed_snapshot.is_dir()), "assets": embed_assets}
    vector_store_path = Path(os.environ.get("RAGIN_VECTOR_STORE_PATH", "data/vector_store"))
    versions = {}
    for package in PACKAGES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    project_python = ROOT / ".venv/bin/python"
    project_environment = None
    if project_python.is_file():
        code = "import sys,importlib.metadata as m,json; ns=" + repr(list(PACKAGES)) + "; ds={str(d.metadata.get('Name','')).lower():d.version for d in m.distributions()}; print(json.dumps({'python':sys.version,'packages':{n:ds.get(n.lower()) for n in ns}},sort_keys=True))"
        project_environment = json.loads(subprocess.check_output([str(project_python), "-c", code], cwd=ROOT, text=True))
    summary = {
        "captured_at_utc": captured_at,
        "repository": str(ROOT),
        "git_head": head,
        "git_branch": branch,
        "porcelain_v1_status_entries": len(records),
        "worktree_manifest": {"path": str(OUT.relative_to(ROOT)), "entries": len(records), "hashed": sum(bool(r.get("sha256")) for r in records), "self_reference_excluded": 2},
        "process_environment_allowlist": {key: os.environ[key] for key in ALLOWLIST if key in os.environ},
        "runtime_resolution_without_process_override": {"runtime_mode": "RAGIN_BASELINE", "decision_arm": "RAGIN_BASELINE", "evidence_judge": "disabled", "evidence_judge_adapter": "DETERMINISTIC_COMMAND_GROUNDED_V1", "evidence_judge_filtering": "disabled", "laya_decision": "disabled", "laya_model": "english", "laya_revision": "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851", "laya_device": "cpu", "laya_timeout_s": 30, "provider_transport": "disabled", "rag_mode": "hybrid", "rag_corpus_directory": "data/corpus", "vector_store_directory": "data/vector_store", "embedding_model": "all-MiniLM-L6-v2", "don_command_aware_v2": "disabled"},
        "python": sys.version,
        "installed_package_versions": versions,
        "project_venv": {"interpreter": str(project_python) if project_python.is_file() else None, "observed_versions": project_environment},
        "critical_input_hashes": inputs,
        "laya_checkpoint": checkpoint_info,
        "embedding_checkpoint": embedding_checkpoint,
        "vector_store_state": {"path": str(vector_store_path), "exists": vector_store_path.exists()},
        "limitations": ["No live server process configuration was observed; effective server configuration is recorded from the current process allowlist and code defaults.", "Local dotenv files such as .env and .env.field are not read or included; only allowlisted process variables and checked-in environment examples are recorded."]
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(OUT.relative_to(ROOT)), "summary": str(SUMMARY.relative_to(ROOT)), "entries": len(records), "hashed": sum(bool(r.get("sha256")) for r in records), "missing_or_unreadable": sum(r.get("kind") in {"missing", "unreadable"} for r in records)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
