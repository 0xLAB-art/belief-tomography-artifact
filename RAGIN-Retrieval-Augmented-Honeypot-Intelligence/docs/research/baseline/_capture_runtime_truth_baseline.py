#!/usr/bin/env python3
"""Additive Phase-0 baseline capture for the runtime-truth audit.

Writes only under docs/research/baseline/. Never modifies source, data, or
results. Hashes tracked files, inventories untracked files without copying
attacker records, and records a redacted tracked diff.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/home/elaref/Documents/research/ragin/RAGIN-Retrieval-Augmented-Honeypot-Intelligence")
OUT = REPO / "docs" / "research" / "baseline"
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
OUT.mkdir(parents=True, exist_ok=True)


def run(*args: str) -> str:
    return subprocess.run(
        args, cwd=REPO, check=True, capture_output=True, text=True,
    ).stdout


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def is_probably_text(path: Path, sample: int = 4096) -> bool:
    try:
        with path.open("rb") as fh:
            chunk = fh.read(sample)
    except OSError:
        return False
    if b"\x00" in chunk:
        return False
    try:
        chunk.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


tracked = [line for line in run("git", "ls-files", "-z").split("\0") if line]
tracked_rows = []
for rel in tracked:
    p = REPO / rel
    if not p.is_file():
        tracked_rows.append({"path": rel, "exists": False})
        continue
    st = p.stat()
    tracked_rows.append({
        "path": rel,
        "exists": True,
        "size_bytes": st.st_size,
        "sha256": sha256_file(p),
    })

tracked_map_path = OUT / f"tracked_sha256_{TS}.jsonl"
with tracked_map_path.open("w", encoding="utf-8") as fh:
    for row in tracked_rows:
        fh.write(json.dumps(row, sort_keys=True) + "\n")

aggregate = hashlib.sha256()
for row in sorted((r for r in tracked_rows if r.get("exists")), key=lambda r: r["path"]):
    aggregate.update(f"{row['path']}\t{row['sha256']}\n".encode())
tracked_total_bytes = sum(r.get("size_bytes", 0) for r in tracked_rows if r.get("exists"))

status_lines = [ln for ln in run("git", "status", "--porcelain=v1").splitlines() if ln]

untracked_rows = []
for line in status_lines:
    if not line.startswith("?? "):
        continue
    rel = line[3:]
    p = REPO / rel
    if not p.exists():
        untracked_rows.append({"path": rel, "exists": False})
        continue
    if p.is_dir():
        count = 0
        total = 0
        for root, _dirs, files in os.walk(p):
            for name in files:
                fp = Path(root) / name
                try:
                    total += fp.stat().st_size
                    count += 1
                except OSError:
                    continue
        untracked_rows.append({"path": rel, "kind": "dir", "files": count, "size_bytes": total})
        continue
    st = p.stat()
    row = {"path": rel, "kind": "file", "size_bytes": st.st_size}
    if st.st_size <= 1 << 20 and is_probably_text(p):
        row["sha256"] = sha256_file(p)
    else:
        row["sha256"] = None
        row["hash_skipped"] = "large_or_binary"
    untracked_rows.append(row)

untracked_map_path = OUT / f"untracked_inventory_{TS}.jsonl"
with untracked_map_path.open("w", encoding="utf-8") as fh:
    for row in untracked_rows:
        fh.write(json.dumps(row, sort_keys=True) + "\n")

EXCLUDE_PREFIXES = ("data/sessions/", "results/")
diff_path = OUT / f"tracked_diff_redacted_{TS}.patch"
diff_lines = run("git", "diff", "HEAD", "--").splitlines(keepends=True)
kept: list[str] = []
included_files: list[str] = []
current_keep = True
for line in diff_lines:
    if line.startswith("diff --git "):
        target = line.split(" b/", 1)[-1].strip()
        current_keep = not target.startswith(EXCLUDE_PREFIXES)
        if current_keep:
            included_files.append(target)
            kept.append(line)
        continue
    if current_keep:
        kept.append(line)
diff_path.write_text("".join(kept), encoding="utf-8")

critical = [
    ".env.example", ".env.field.example",
    "data/corpus/command_aware_v2.jsonl", "data/corpus/mitre_attack.jsonl",
    "data/host_fiction.json", "data/mitre_stix/enterprise-attack.json",
    "docker-compose.field.yml", "docker-compose.yml", "pyproject.toml",
    "Makefile", "requirements-runtime.txt", "uv.lock",
    "ragin/server_v2.py", "ragin/cycle/harness.py", "ragin/cycle/sandbox.py",
    "ragin/cycle/session.py", "ragin/cycle/adapters.py", "ragin/cycle/verifier.py",
    "ragin/cycle/graph.py", "ragin/cycle/approval.py",
    "ragin/graph/host_fiction.py", "ragin/gateway/client.py",
    "ragin/decision_fusion_v4/runtime_mode.py", "ragin/decision_fusion_v4/config.py",
    "ragin/decision_fusion_v4/policy.py", "ragin/decision_fusion_v4/evidence_export.py",
    "ragin/decision/laya_runtime.py", "ragin/decision/laya_decision.py",
    "ragin/don/rag_engine.py", "ragin/don/pipeline.py", "ragin/don/evidence_judge.py",
    "ragin/don/command_aware_v2.py", "ragin/don/vector_store.py", "ragin/don/intel_corpus.py",
    "ragin/hisoka/deceiver.py", "ragin/hisoka/deception.py", "ragin/hisoka/memory.py",
    "tests/integration/test_runtime_truth_p0.py",
    "docs/baseline_freeze/baseline_manifest.json",
    "results/vor_guarded_served_text_lower_bounds.json",
    "results/cti_manual_audit.json",
    "results/two_channel_metrics.json",
    "results/live_benchmark_zodiac_20260922.json",
    "results/jev_ab_eval.json",
    "results/stability_run1_vs_run2.json",
    "docs/SP2027_HARD_REVIEW_2026-10-08_POSTFIX.md",
]
critical_hashes = {}
for rel in critical:
    p = REPO / rel
    if p.is_file():
        critical_hashes[rel] = {
            "exists": True,
            "size_bytes": p.stat().st_size,
            "sha256": sha256_file(p),
        }
    else:
        critical_hashes[rel] = {"exists": False}

env_names = [
    "RAGIN_RUNTIME_MODE", "RAGIN_DECISION_ARM", "RAGIN_V4_ENABLED", "RAGIN_V4_SELECTOR",
    "RAGIN_DON_RETRIEVAL_VERSION", "RAGIN_RAG_MODE",
    "RAGIN_EVIDENCE_JUDGE_ENABLED", "RAGIN_EVIDENCE_JUDGE_FILTERING_ENABLED",
    "RAGIN_LAYA_ENABLED", "RAGIN_LAYA_MODEL", "RAGIN_LAYA_REVISION", "RAGIN_LAYA_DEVICE",
    "GATEWAY_URL", "RAGIN_LLM_BASE_URL", "RAGIN_PROVIDER_URL", "RAGIN_GATEWAY_URL",
    "RAGIN_PROVIDER_ENABLED", "RAGIN_REQUIRE_PROVIDER",
    "RAGIN_PROVIDER_API_KEY", "RAGIN_HISOKA_API_KEY", "RAGIN_LLM_API_KEY",
    "OPENROUTER_API_KEY", "AZURE_OPENAI_KEY", "OPENAI_API_KEY",
    "RAGIN_REQUIRE_AUTH", "RAGIN_BIND_HOST", "PORT",
    "RAGIN_HOST_FICTION_PATH", "RAGIN_HOST_KEY", "RAGIN_HOST_FICTION_POLICY",
    "RAGIN_FIELD_EXPORT_DIR", "RAGIN_MAX_REQUEST_BYTES", "RAGIN_GATEWAY_TIMEOUT",
]
env_presence = {name: (name in os.environ) for name in env_names}

manifest = {
    "schema": "ragin.runtime_truth_baseline.v1",
    "captured_at_utc": datetime.now(timezone.utc).isoformat(),
    "purpose": "Additive Phase-0 freeze before any runtime repair; does not modify or supersede docs/baseline_freeze/.",
    "repository": str(REPO),
    "git": {
        "head": run("git", "rev-parse", "HEAD").strip(),
        "branch": run("git", "branch", "--show-current").strip(),
        "porcelain_total": len(status_lines),
        "modified_tracked": sum(1 for ln in status_lines if ln.startswith("M")),
        "untracked_top_level_entries": sum(1 for ln in status_lines if ln.startswith("??")),
    },
    "tracked_files": {
        "count": len(tracked_rows),
        "existing": sum(1 for r in tracked_rows if r.get("exists")),
        "total_bytes": tracked_total_bytes,
        "aggregate_sha256_of_path_and_hash_lines": aggregate.hexdigest(),
        "per_file_map": str(tracked_map_path.relative_to(REPO)),
    },
    "untracked_inventory": {
        "entries": len(untracked_rows),
        "hashed_small_text_files": sum(1 for r in untracked_rows if r.get("sha256")),
        "hash_skipped": sum(1 for r in untracked_rows if r.get("sha256") is None and r.get("kind") == "file"),
        "path": str(untracked_map_path.relative_to(REPO)),
        "policy": "metadata for every untracked entry; sha256 only for <=1 MiB text files; no file contents copied.",
    },
    "critical_input_hashes": critical_hashes,
    "redacted_tracked_diff": {
        "path": str(diff_path.relative_to(REPO)),
        "excluded_prefixes": list(EXCLUDE_PREFIXES),
        "reason": "data/sessions/** holds attacker session records and results/** holds probe artifacts; their contents are not copied into audit artifacts.",
        "included_files": included_files,
    },
    "environment_presence_only": env_presence,
    "runtime_resolution_without_process_override": {
        "runtime_mode": "RAGIN_BASELINE",
        "decision_arm": "RAGIN_BASELINE",
        "mandatory_verification_at_composition_root": True,
        "v4_policy_gate": "disabled (arm == RAGIN_BASELINE)",
        "deceiver_default": "HisokaAdapter -> AdaptiveDeceiver -> GatewayClient",
        "provider_default_gateway_url": "http://localhost:8080",
        "server_default_bind": "127.0.0.1:8080",
        "don_command_aware_v2": "disabled unless RAGIN_DON_RETRIEVAL_VERSION=DON_COMMAND_AWARE_V2",
        "don_retrieval_default": "hybrid (dense + BM25 reciprocal-rank fusion)",
        "evidence_judge": "disabled unless RAGIN_EVIDENCE_JUDGE_ENABLED=1",
        "evidence_judge_filtering": "disabled unless RAGIN_EVIDENCE_JUDGE_FILTERING_ENABLED=1",
        "laya_decision": "disabled unless RAGIN_LAYA_ENABLED=1",
        "laya_served_checkpoint": "upstream_base only; fine-tuned dirs are not loadable",
        "authentication_default": "open unless RAGIN_REQUIRE_AUTH=1 (warning logged)",
    },
    "exclusions": [
        ".venv/ (2.1 GiB) not inventoried",
        "models/ weights not re-hashed except the Laya checkpoints recorded in the audit",
        "data/ and results/ file contents not copied; only metadata/hashes",
        "secrets and dotenv values never read or printed",
    ],
}

manifest_path = OUT / f"RUNTIME_TRUTH_BASELINE_{TS}.json"
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

print(json.dumps({
    "manifest": str(manifest_path),
    "tracked_map": str(tracked_map_path),
    "untracked_inventory": str(untracked_map_path),
    "diff": str(diff_path),
    "tracked_count": len(tracked_rows),
    "tracked_bytes": tracked_total_bytes,
    "tracked_aggregate": aggregate.hexdigest(),
    "untracked_entries": len(untracked_rows),
    "diff_included_files": len(included_files),
}, indent=2))
