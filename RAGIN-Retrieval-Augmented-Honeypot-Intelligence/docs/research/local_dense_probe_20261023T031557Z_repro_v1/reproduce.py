#!/usr/bin/env python3
"""Versioned reproduction wrapper for the frozen local dense probe.

Defect this repairs (erratum, see erratum.md):
    The origin report's "Reproduce" command re-ran probe.py *inside* the
    immutable evidence directory, overwriting raw_results.json,
    preflight_manifest.json, network_audit.json and dense_store/. That
    contradicted the artifact's frozen-evidence claim.

Contract of this wrapper:
    * --out is REQUIRED and must NOT already exist (no overwrite, ever).
    * --out may not be, contain, or sit inside the origin namespace or this
      reproduction namespace.
    * frozen probe.py + fixtures are copied into --out and hash-verified first.
    * origin hashes are re-verified read-only and recorded in
      <out>/origin_hashes.json BEFORE any inference runs.
    * the child runs with a sanitized, credential-free, offline environment.
    * deterministic content invariants are checked against
      EXPECTED_INVARIANTS.json and recorded in <out>/invariant_check.json.
    * <out>/result_sha256.txt seals the new run (excludes itself).

The origin directory is only ever opened for reads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

NS = Path(__file__).resolve().parent
REPO = NS.parents[2]
ORIGIN = REPO / "docs" / "research" / "local_dense_probe_20261023T031557Z"
ORIGIN_SHA_FILE = NS / "ORIGIN.sha256"
ORIGIN_MANIFEST = NS / "frozen" / "origin_manifest.json"
FROZEN_PROBE = NS / "frozen" / "probe.py"
FROZEN_FIXTURES = NS / "frozen" / "fixtures"
EXPECTED = NS / "EXPECTED_INVARIANTS.json"

LAUNCHER = '''\
"""Generated launcher: run the byte-frozen probe with the repo root pinned."""
import runpy
import sys
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
probe = Path(sys.argv[2]).resolve()
ns = runpy.run_path(str(probe), run_name="ragin_local_dense_probe")
main = ns["main"]
# run_path returns a copy of the module globals; patch the function's actual
# globals so probe.py hashes the repo sources instead of "/".
main.__globals__["ROOT"] = repo
main()
'''


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def refuse_out(out: Path) -> None:
    if os.path.lexists(str(out)):
        raise SystemExit(f"refusing: --out already exists: {out}")
    if is_within(out, ORIGIN) or is_within(out, NS):
        raise SystemExit(f"refusing: --out is inside immutable evidence tree: {out}")
    if is_within(ORIGIN, out) or is_within(NS, out):
        raise SystemExit(f"refusing: --out would contain existing evidence: {out}")


def verify_frozen() -> dict:
    man = json.loads(ORIGIN_MANIFEST.read_text())
    actual = sha256(ORIGIN_SHA_FILE)
    ok = actual == man["origin_sha256sums_sha256"]
    if not ok:
        raise SystemExit("refusing: ORIGIN.sha256 does not match the pinned origin manifest")
    frozen = {rel: sha256(NS / rel) for rel in man["frozen_copies"]}
    bad = {rel: (man["frozen_copies"][rel], got) for rel, got in frozen.items() if got != man["frozen_copies"][rel]}
    if bad:
        raise SystemExit(f"refusing: frozen copy drift: {bad}")
    return {"origin_manifest": man, "ORIGIN_sha256_sha256": actual, "frozen_verified": frozen}


def verify_origin(man: dict) -> dict:
    rows = {}
    for rel, expected in sorted(man["origin_file_hashes"].items()):
        p = ORIGIN / rel
        if not p.is_file():
            rows[rel] = {"status": "ORIGIN_FILE_ABSENT", "expected_sha256": expected}
            continue
        got = sha256(p)
        rows[rel] = {
            "status": "MATCH" if got == expected else "MISMATCH",
            "expected_sha256": expected,
            "actual_sha256": got,
        }
    return rows


def source_hashes() -> dict:
    out = {}
    for rel in ("ragin/don/vector_store.py", "ragin/don/rag_engine.py", "ragin/don/intel_corpus.py"):
        p = REPO / rel
        out[rel] = sha256(p) if p.is_file() else "MISSING"
    return out


def sanitized_env() -> dict:
    return {
        "HOME": os.environ.get("HOME", ""),
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": str(REPO),
        "PYTHONDONTWRITEBYTECODE": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "OMP_NUM_THREADS": "4",
    }


def check_invariants(raw: dict, expected: dict) -> dict:
    dv = raw.get("dense", {}).get("vector_store", {})
    hits = {q.get("query_id"): q for q in raw.get("queries", [])}
    checks = {
        "status": raw.get("status") == expected["status"],
        "top_k": raw.get("top_k") == expected["top_k"],
        "fallback_hash_mode": dv.get("fallback_hash_mode") == expected["dense"]["fallback_hash_mode"],
        "faiss_index_class": dv.get("faiss_index_class") == expected["dense"]["faiss_index_class"],
        "faiss_ntotal": dv.get("faiss_ntotal") == expected["dense"]["faiss_ntotal"],
        "dimension": dv.get("dimension") == expected["dense"]["dimension"],
        "embedding_matrix_sha256": dv.get("embedding_matrix_sha256") == expected["dense"]["embedding_matrix_sha256"],
        "embedding_matrix_shape": dv.get("embedding_matrix_shape") == expected["dense"]["embedding_matrix_shape"],
        "bm25_terms": raw.get("bm25", {}).get("index", {}).get("terms") == expected["bm25"]["terms"],
        "blocked_connect_attempts": raw.get("network", {}).get("blocked_connect_attempts")
        == expected["blocked_connect_attempts"],
    }
    rank0 = {}
    for qid, want in expected["rank0_doc_ids"].items():
        q = hits.get(qid, {})
        got = {
            "dense": (q.get("dense", {}).get("hits") or [{}])[0].get("doc_id"),
            "bm25": (q.get("bm25", {}).get("hits") or [{}])[0].get("doc_id"),
        }
        rank0[qid] = {"expected": want, "observed": got, "pass": got == want}
    return {
        "schema": "ragin.local_dense_probe.repro.invariant_check.v1",
        "checks": checks,
        "rank0": rank0,
        "all_pass": all(checks.values()) and all(r["pass"] for r in rank0.values()),
        "note": "latencies/timings/provenance strings are not invariants",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="fresh output directory (must not exist)")
    ap.add_argument("--python", default=str(REPO / ".venv" / "bin" / "python"))
    args = ap.parse_args()

    out = Path(args.out).expanduser()
    if not out.is_absolute():
        out = (Path.cwd() / out)
    refuse_out(out)
    if not Path(args.python).is_file():
        raise SystemExit(f"refusing: interpreter not found: {args.python}")

    frozen = verify_frozen()
    man = frozen["origin_manifest"]
    origin_rows = verify_origin(man)

    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(FROZEN_PROBE, out / "probe.py")
    (out / "fixtures" / "corpus").mkdir(parents=True)
    shutil.copyfile(FROZEN_FIXTURES / "corpus" / "documents.jsonl", out / "fixtures" / "corpus" / "documents.jsonl")
    shutil.copyfile(FROZEN_FIXTURES / "queries.json", out / "fixtures" / "queries.json")
    (out / "run_probe.py").write_text(LAUNCHER)

    provenance = {
        "schema": "ragin.local_dense_probe.repro.out_provenance.v1",
        "utc_started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "out_dir": str(out),
        "origin_artifact_dir": str(ORIGIN),
        "origin_sha256sums_sha256": frozen["ORIGIN_sha256_sha256"],
        "origin_file_verification": origin_rows,
        "frozen_copy_hashes": frozen["frozen_verified"],
        "pre_edit_source_snapshot": man["pre_edit_snapshot"],
        "current_source_hashes": source_hashes(),
        "source_drift_note": (
            "The origin run used the pre-fix rag_engine.py recorded in origin_run.source_sha256; "
            "a re-run uses current working-tree sources. Compare deterministic invariants, "
            "not raw file hashes."
        ),
        "copied_into_out": {
            "probe.py": sha256(out / "probe.py"),
            "fixtures/corpus/documents.jsonl": sha256(out / "fixtures" / "corpus" / "documents.jsonl"),
            "fixtures/queries.json": sha256(out / "fixtures" / "queries.json"),
        },
        "network_policy": "sanitized env; driver installs a socket audit hook that blocks non-loopback connect()",
    }
    (out / "origin_hashes.json").write_text(json.dumps(provenance, indent=2) + "\n")

    started = time.time()
    print(f"[repro] origin verified read-only; running frozen probe in {out}", file=sys.stderr)
    print(f"[repro] origin mismatches: {sum(1 for r in origin_rows.values() if r['status'] != 'MATCH')}", file=sys.stderr)
    try:
        proc = subprocess.run(
            [args.python, str(out / "run_probe.py"), str(REPO), str(out / "probe.py")],
            cwd=str(REPO),
            env=sanitized_env(),
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        rc, timed_out = proc.returncode, False
        (out / "probe_stdout.txt").write_text(proc.stdout)
        (out / "probe_stderr.txt").write_text(proc.stderr)
    except subprocess.TimeoutExpired as exc:
        rc, timed_out = 124, True
        (out / "probe_stdout.txt").write_text((exc.stdout or "") if isinstance(exc.stdout, str) else "")
        (out / "probe_stderr.txt").write_text("TIMEOUT after 300s\n")

    status = {
        "schema": "ragin.local_dense_probe.repro.run_status.v1",
        "utc_finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "wall_seconds": round(time.time() - started, 3),
        "returncode": rc,
        "timed_out": timed_out,
        "invocation": "run_probe.py <repo> <out>/probe.py",
        "origin_untouched": True,
    }

    raw_path = out / "raw_results.json"
    if raw_path.is_file():
        try:
            check = check_invariants(json.loads(raw_path.read_text()), json.loads(EXPECTED.read_text()))
        except Exception as exc:  # record, do not mask the run
            check = {"all_pass": False, "error": f"{type(exc).__name__}: {exc}"}
        (out / "invariant_check.json").write_text(json.dumps(check, indent=2) + "\n")
        status["invariants_all_pass"] = check.get("all_pass")
    else:
        status["invariants_all_pass"] = None
        status["raw_results"] = "ABSENT (run failed before writing)"

    (out / "run_status.json").write_text(json.dumps(status, indent=2) + "\n")

    sealed = []
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "result_sha256.txt":
            sealed.append(f"{sha256(p)}  {p.relative_to(out)}")
    (out / "result_sha256.txt").write_text("\n".join(sealed) + "\n")

    print(json.dumps({
        "out": str(out),
        "returncode": rc,
        "invariants_all_pass": status.get("invariants_all_pass"),
        "origin_files_checked": len(origin_rows),
        "origin_mismatches": [r for r, row in origin_rows.items() if row["status"] != "MATCH"],
        "sealed_files": len(sealed),
    }, indent=2))
    return 0 if rc == 0 else rc


if __name__ == "__main__":
    sys.exit(main())
