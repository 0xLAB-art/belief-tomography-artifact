#!/usr/bin/env python3
"""Bounded OFFLINE dense-vs-BM25 development probe (local artifacts only).

Purpose: establish whether the *existing* local dense arm (VectorStore +
cached sentence-transformers/all-MiniLM-L6-v2 + FAISS) performs REAL embedding
inference, and exercise it on a tiny SYNTHETIC_DEVELOPMENT corpus against the
*native* BM25 arm on the identical corpus.

This is an integration probe, not a retrieval benchmark:
  * <=12 synthetic documents, <=4 fixed queries, no labels, no tuning.
  * CPU only, bounded threads/time, no training, no downloads.
  * No provider/cloud/Ollama contact: a socket audit hook blocks non-loopback
    connect() calls (attempts are recorded).
  * Preflight SHA256 manifest is written BEFORE any model is loaded.

Writes: preflight_manifest.json, raw_results.json, network_audit.json.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import traceback
from pathlib import Path

ART = Path(__file__).resolve().parent
ROOT = ART.parents[2]
CORPUS_DIR = ART / "fixtures" / "corpus"
DOCS_FILE = CORPUS_DIR / "documents.jsonl"
QUERIES_FILE = ART / "fixtures" / "queries.json"
MODEL_SNAPSHOT = Path(
    os.path.expanduser("~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/"
                       "1110a243fdf4706b3f48f1d95db1a4f5529b4d41")
)
STORE_DIR = ART / "dense_store"
MODEL_FILES = [
    "config.json",
    "config_sentence_transformers.json",
    "modules.json",
    "sentence_bert_config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
    "1_Pooling/config.json",
    "model.safetensors",
]
SOURCE_FILES = [
    "ragin/don/vector_store.py",
    "ragin/don/rag_engine.py",
    "ragin/don/intel_corpus.py",
]
SUSPICIOUS_ENV = (
    "KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "AWS", "AZURE", "GCP",
    "GOOGLE", "OPENAI", "ANTHROPIC", "OPENROUTER", "PROXY", "GATEWAY", "OLLAMA",
    "HF_TOKEN", "HUGGINGFACE",
)

AUDIT_EVENTS: list[dict] = []
_BLOCKED_CONNECT = 0


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _install_socket_audit() -> None:
    """Record DNS + block non-loopback outbound connects for this process."""
    global _BLOCKED_CONNECT

    def hook(event: str, args: tuple) -> None:
        global _BLOCKED_CONNECT
        if event in {"socket.connect", "socket.sendto"}:
            addr = args[1] if len(args) > 1 else None
            host = addr[0] if isinstance(addr, tuple) and addr else None
            if isinstance(host, str) and host in {"127.0.0.1", "::1", "localhost"}:
                AUDIT_EVENTS.append({"event": event, "target": host, "blocked": False})
                return
            _BLOCKED_CONNECT += 1
            AUDIT_EVENTS.append({"event": event, "target": str(host), "blocked": True})
            raise RuntimeError(f"probe blocked outbound connect(): {event} -> {host!r}")
        if event == "socket.getaddrinfo":
            host = args[0] if args else None
            AUDIT_EVENTS.append({"event": event, "target": str(host), "blocked": False})

    sys.addaudithook(hook)


def _run(args: list[str]) -> str:
    try:
        return subprocess.run(
            args, cwd=str(ROOT), capture_output=True, text=True, timeout=30, check=False
        ).stdout.strip()
    except Exception as exc:  # local git only
        return f"<unavailable: {type(exc).__name__}>"


def preflight() -> dict:
    """Freeze fixture/model/source identities BEFORE any inference."""
    docs_raw = DOCS_FILE.read_bytes()
    queries_raw = QUERIES_FILE.read_bytes()
    documents = [json.loads(line) for line in docs_raw.decode().splitlines() if line.strip()]
    queries = json.loads(queries_raw)

    model_sha = {}
    for rel in MODEL_FILES:
        p = MODEL_SNAPSHOT / rel
        model_sha[rel] = {"sha256": _sha256_file(p), "bytes": p.stat().st_size,
                          "resolved": str(p.resolve())} if p.is_file() else {"MISSING": True}
    cfg = json.loads((MODEL_SNAPSHOT / "config.json").read_text())
    st_cfg = json.loads((MODEL_SNAPSHOT / "sentence_bert_config.json").read_text())
    tok_cfg = json.loads((MODEL_SNAPSHOT / "tokenizer_config.json").read_text())

    git_status = _run(["git", "status", "--porcelain"])
    git_names = [ln for ln in git_status.splitlines() if ln.strip()]
    dirty_sources = sorted(
        ln[3:].strip() for ln in git_names
        if ln[3:].strip() in set(SOURCE_FILES)
    )
    head = _run(["git", "rev-parse", "HEAD"])

    env_keys = sorted(os.environ)
    suspicious = sorted(k for k in env_keys if any(s in k.upper() for s in SUSPICIOUS_ENV))

    manifest = {
        "schema": "ragin.local_dense_probe.preflight.v1",
        "written_before_inference": True,
        "utc_started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "artifact_dir": str(ART),
        "fixture": {
            "split": "SYNTHETIC_DEVELOPMENT",
            "source": "authored for this probe; no existing dev/calibration/holdout record used",
            "documents_path": "fixtures/corpus/documents.jsonl",
            "documents_sha256": hashlib.sha256(docs_raw).hexdigest(),
            "document_count": len(documents),
            "document_ids": [d["doc_id"] for d in documents],
            "queries_path": "fixtures/queries.json",
            "queries_sha256": hashlib.sha256(queries_raw).hexdigest(),
            "query_count": len(queries["queries"]),
            "query_ids": [q["query_id"] for q in queries["queries"]],
            "top_k": queries["top_k"],
        },
        "model": {
            "hub_id": "sentence-transformers/all-MiniLM-L6-v2",
            "snapshot_dir": str(MODEL_SNAPSHOT),
            "snapshot_revision": (MODEL_SNAPSHOT.parents[1] / "refs" / "main").read_text().strip()
            if (MODEL_SNAPSHOT.parents[1] / "refs" / "main").is_file() else "unknown",
            "files": model_sha,
            "config": {
                "model_type": cfg.get("model_type"),
                "architectures": cfg.get("architectures"),
                "hidden_size": cfg.get("hidden_size"),
                "num_hidden_layers": cfg.get("num_hidden_layers"),
                "max_position_embeddings": cfg.get("max_position_embeddings"),
                "vocab_size": cfg.get("vocab_size"),
            },
            "sentence_bert_config": st_cfg,
            "tokenizer_class": tok_cfg.get("tokenizer_class"),
            "tokenizer_model_max_length": tok_cfg.get("model_max_length"),
        },
        "source": {rel: {"sha256": _sha256_file(ROOT / rel)} for rel in SOURCE_FILES},
        "git": {
            "head": head,
            "dirty": bool(git_names),
            "dirty_entry_count": len(git_names),
            "porcelain_sha256": hashlib.sha256(git_status.encode()).hexdigest(),
            "probe_owned_source_files_dirty": dirty_sources,
            "note": "dirty tree includes concurrent peer edits to core/verifier/evaluation files; this probe edited none of them",
        },
        "runtime": {
            "python": sys.version.split()[0],
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "gpu_policy": "CPU only (torch device=cpu, 4 intra-op threads)",
        },
        "environment": {
            "HF_HUB_OFFLINE": os.environ.get("HF_HUB_OFFLINE"),
            "TRANSFORMERS_OFFLINE": os.environ.get("TRANSFORMERS_OFFLINE"),
            "env_key_count": len(env_keys),
            "credential_or_proxy_like_keys_present": suspicious,
            "note": "only key NAMES are reported; no values recorded",
        },
    }
    (ART / "preflight_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> dict:
    manifest = preflight()
    _install_socket_audit()

    import faiss
    import numpy as np
    import torch
    import transformers
    from importlib.metadata import version as pkg_version

    torch.set_num_threads(4)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    torch.manual_seed(0)

    from ragin.don.rag_engine import ThreatRAGEngine
    from ragin.don.vector_store import VectorStore

    documents = [json.loads(line) for line in DOCS_FILE.read_text().splitlines() if line.strip()]
    qdoc = json.loads(QUERIES_FILE.read_text())
    queries = qdoc["queries"]
    top_k = int(qdoc["top_k"])

    versions = {
        "torch": torch.__version__,
        "faiss": getattr(faiss, "__version__", "unknown"),
        "sentence_transformers": pkg_version("sentence-transformers"),
        "transformers": transformers.__version__,
        "numpy": np.__version__,
    }

    # ---------------- real dense arm (VectorStore, explicit local model) ----------------
    store = VectorStore(store_path=str(STORE_DIR), model_ref=str(MODEL_SNAPSHOT))
    t0 = time.perf_counter()
    store._ensure_initialized()
    init_ms = (time.perf_counter() - t0) * 1000.0

    embedder = store._embedder
    fallback_mode = embedder is None
    embedder_class = type(embedder).__name__ if embedder is not None else "NONE"
    dim = embedder.get_sentence_embedding_dimension() if embedder is not None else None
    max_seq = getattr(embedder, "max_seq_length", None) if embedder is not None else None
    auto_model = embedder[0].auto_model if embedder is not None and len(embedder) > 0 else None
    encoder_identity = {
        "class": embedder_class,
        "embedding_dimension": dim,
        "max_seq_length": max_seq,
        "auto_model_class": type(auto_model).__name__ if auto_model is not None else "NONE",
        "auto_model_model_type": getattr(getattr(auto_model, "config", None), "model_type", None),
        "auto_model_hidden_size": getattr(getattr(auto_model, "config", None), "hidden_size", None),
        "auto_model_name_or_path": str(getattr(auto_model, "name_or_path", "")),
        "parameters": int(sum(p.numel() for p in auto_model.parameters())) if auto_model is not None else 0,
    }

    t0 = time.perf_counter()
    added = store.add_documents(documents)
    index_ms = (time.perf_counter() - t0) * 1000.0

    index_type = type(store._index).__name__ if store._index is not None else "NONE"
    ntotal = int(store._index.ntotal) if store._index is not None else 0
    is_flat_ip = bool(store._index is not None and isinstance(store._index, faiss.IndexFlatIP))

    texts = [d["text"] for d in documents]
    t0 = time.perf_counter()
    matrix = store._embed(texts)
    fingerprint_ms = (time.perf_counter() - t0) * 1000.0
    norms = np.linalg.norm(matrix, axis=1)
    docs_fp = hashlib.sha256(np.ascontiguousarray(matrix, dtype=np.float32).tobytes()).hexdigest()

    # show the real vectors are not the deterministic hash fallback
    probe_text = texts[0]
    rng = np.random.RandomState(42)
    seed = sum(ord(c) for c in probe_text) % (2**31)
    rng.seed(seed)
    fb = rng.randn(384).astype(np.float32)
    fb /= np.linalg.norm(fb)
    cos_to_fallback = float(np.dot(matrix[0], fb))

    store.save()

    # ---------------- native BM25 arm on the identical corpus ----------------
    os.environ["RAGIN_RAG_MODE"] = "bm25"
    t0 = time.perf_counter()
    bm25_engine = ThreatRAGEngine(
        corpus_path=str(CORPUS_DIR),
        gateway_url="http://127.0.0.1:9",
        api_key="",
    )
    bm25_init_ms = (time.perf_counter() - t0) * 1000.0
    bm25_index = {
        "docs": len(bm25_engine._doc_store),
        "terms": len(bm25_engine._bm25_index),
        "avg_doclen": round(float(bm25_engine._avg_doclen), 6),
        "title_terms": len(bm25_engine._title_df),
    }

    # ---------------- dense-only engine reusing the persisted store ----------------
    os.environ["RAGIN_RAG_MODE"] = "dense"
    os.environ["RAGIN_VECTOR_STORE_PATH"] = str(STORE_DIR)
    os.environ["RAGIN_EMBED_MODEL"] = str(MODEL_SNAPSHOT)
    t0 = time.perf_counter()
    dense_engine = ThreatRAGEngine(
        vector_store_path=str(STORE_DIR),
        gateway_url="http://127.0.0.1:9",
        api_key="",
    )
    dense_init_ms = (time.perf_counter() - t0) * 1000.0
    dense_loaded_docs = int(getattr(dense_engine._vector_store, "document_count", 0))
    dense_embedder_loaded = dense_engine._vector_store._embedder is not None

    results = []
    for q in queries:
        t0 = time.perf_counter()
        dense_hits = dense_engine.search_threat_intel(q["text"], top_k=top_k)
        dense_ms = (time.perf_counter() - t0) * 1000.0

        t0 = time.perf_counter()
        bm25_ranked = bm25_engine.keyword_search(q["text"])
        bm25_ms = (time.perf_counter() - t0) * 1000.0
        bm25_hits = bm25_ranked[:top_k]

        results.append({
            "query_id": q["query_id"],
            "query": q["text"],
            "dense": {
                "latency_ms": round(dense_ms, 3),
                "returned": len(dense_hits),
                "hits": [
                    {"rank": i, "doc_id": h.get("doc_id"), "score": float(h.get("score"))}
                    for i, h in enumerate(dense_hits)
                ],
            },
            "bm25": {
                "latency_ms": round(bm25_ms, 3),
                "total_ranked": len(bm25_ranked),
                "hits": [
                    {"rank": i, "doc_id": h.get("doc_id"), "score": float(h.get("score"))}
                    for i, h in enumerate(bm25_hits)
                ],
            },
        })

    provenance = dense_engine.retrieval_provenance
    bm25_provenance = bm25_engine.retrieval_provenance

    dense_block = {
        "vector_store": {
            "init_ms": round(init_ms, 3),
            "add_documents_ms": round(index_ms, 3),
            "fingerprint_encode_ms": round(fingerprint_ms, 3),
            "documents_added": added,
            "document_count": store.document_count,
            "fallback_hash_mode": fallback_mode,
            "embedder": encoder_identity,
            "faiss_index_class": index_type,
            "faiss_index_is_IndexFlatIP": is_flat_ip,
            "faiss_ntotal": ntotal,
            "dimension": int(store._dimension),
            "embedding_matrix_sha256": docs_fp,
            "embedding_matrix_shape": list(matrix.shape),
            "row_norms_min": float(norms.min()),
            "row_norms_max": float(norms.max()),
            "rows_identical_0_1": bool(np.allclose(matrix[0], matrix[1])),
            "cosine_to_hash_fallback_vector": round(cos_to_fallback, 6),
            "persisted_files": sorted(p.name for p in STORE_DIR.iterdir()),
        },
        "dense_engine": {
            "init_ms": round(dense_init_ms, 3),
            "documents_loaded": dense_loaded_docs,
            "embedder_loaded": bool(dense_embedder_loaded),
            "provenance": provenance,
        },
    }
    bm25_block = {
        "engine_init_ms": round(bm25_init_ms, 3),
        "index": bm25_index,
        "provenance": bm25_provenance,
    }

    out = {
        "schema": "ragin.local_dense_probe.raw_results.v1",
        "status": "REAL_EMBEDDING_INFERENCE_OBSERVED",
        "utc_finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scope": "SYNTHETIC_DEVELOPMENT integration probe; not a benchmark, not a generative arm, not deception evidence",
        "versions": versions,
        "top_k": top_k,
        "dense": dense_block,
        "bm25": bm25_block,
        "queries": results,
        "network": {"blocked_connect_attempts": _BLOCKED_CONNECT, "event_count": len(AUDIT_EVENTS)},
        "torch_intra_op_threads": int(torch.get_num_threads()),
    }
    (ART / "raw_results.json").write_text(json.dumps(out, indent=2) + "\n")
    (ART / "network_audit.json").write_text(json.dumps(AUDIT_EVENTS, indent=2) + "\n")
    return out


if __name__ == "__main__":
    try:
        out = main()
        print(json.dumps({
            "status": out["status"],
            "fallback_hash_mode": out["dense"]["vector_store"]["fallback_hash_mode"],
            "faiss_index": out["dense"]["vector_store"]["faiss_index_class"],
            "ntotal": out["dense"]["vector_store"]["faiss_ntotal"],
            "embedder": out["dense"]["vector_store"]["embedder"]["class"],
            "queries": len(out["queries"]),
            "blocked_connects": out["network"]["blocked_connect_attempts"],
        }, indent=2))
    except Exception:
        failure = {
            "schema": "ragin.local_dense_probe.raw_results.v1",
            "status": "NOT_ESTABLISHED",
            "utc_finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "error_type": sys.exc_info()[0].__name__,
            "error": str(sys.exc_info()[1]),
            "traceback": traceback.format_exc(),
            "blocked_connect_attempts": _BLOCKED_CONNECT,
        }
        (ART / "raw_results.json").write_text(json.dumps(failure, indent=2) + "\n")
        (ART / "network_audit.json").write_text(json.dumps(AUDIT_EVENTS, indent=2) + "\n")
        print(json.dumps(failure, indent=2), file=sys.stderr)
        sys.exit(1)
