"""Structural tests for the opt-in B1/B3 retrieval modes.

These tests use explicitly labelled fakes for the corpus, vector store, and
embedding runtime. They do not download a model, run embedding inference, or
open a provider socket. A real dense run remains model/store blocked; the
tests only pin the configuration and channel-separation contract.
"""

from __future__ import annotations

import sys
import types

import pytest

from ragin.cycle.adapters import DonAdapter
from ragin.decision_fusion_v4.evidence_export import build_evidence_bundle
from ragin.don.rag_engine import ThreatRAGEngine


class _FakeCorpus:
    def __init__(self, corpus_path=None):
        self._corpus_path = corpus_path
        self.documents = [
            {"doc_id": "T1003", "title": "whoami credential access", "text": "whoami credential access"}
        ]

    def load_corpus(self):
        return len(self.documents)


class _FakeVectorStore:
    def __init__(self, store_path=None, model_ref=None):
        self.store_path = store_path
        self.model_ref = model_ref
        self.document_count = 1

    def load(self, path=None):
        return None

    def search(self, query, top_k=10):
        return [{"doc_id": "DENSE_ONLY", "title": "dense", "text": query, "score": 1.0}]


class _EmptyVectorStore(_FakeVectorStore):
    def __init__(self, store_path=None, model_ref=None):
        super().__init__(store_path=store_path, model_ref=model_ref)
        self.document_count = 0

    def search(self, query, top_k=10):
        return []


class _EmptyCorpus:
    def __init__(self, corpus_path=None):
        self._corpus_path = corpus_path
        self.documents = []

    def load_corpus(self):
        return 0


class _Boom:
    def __init__(self, *args, **kwargs):
        raise AssertionError("this retriever must not be constructed")


def _fake_dense_runtime(monkeypatch):
    monkeypatch.setitem(sys.modules, "faiss", types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "sentence_transformers", types.SimpleNamespace())


def test_none_mode_constructs_no_retriever(monkeypatch):
    monkeypatch.setenv("RAGIN_RAG_MODE", "none")
    monkeypatch.setattr("ragin.don.rag_engine.IntelCorpus", _Boom)
    monkeypatch.setattr("ragin.don.rag_engine.VectorStore", _Boom)

    engine = ThreatRAGEngine(gateway_url="http://127.0.0.1:9")

    assert engine._retrieval_mode == "none"
    assert engine._vector_store is None
    assert engine._corpus is None
    assert engine.hybrid_search("whoami") == []
    assert engine.search_threat_intel("whoami") == []
    assert engine.keyword_search("whoami") == []
    provenance = engine.retrieval_provenance
    assert provenance["effective_backend"] == "none"
    assert provenance["sparse_constructed"] is False
    assert provenance["dense_constructed"] is False


def test_explicit_none_mode_rejects_lightrag_adapter(monkeypatch):
    monkeypatch.setenv("RAGIN_RAG_MODE", "none")

    with pytest.raises(ValueError, match="lightrag_adapter is incompatible"):
        ThreatRAGEngine(gateway_url="http://127.0.0.1:9", lightrag_adapter=object())


def test_bm25_mode_constructs_only_sparse_index(monkeypatch):
    monkeypatch.setenv("RAGIN_RAG_MODE", "bm25")
    monkeypatch.setattr("ragin.don.rag_engine.IntelCorpus", _FakeCorpus)
    monkeypatch.setattr("ragin.don.rag_engine.VectorStore", _Boom)

    engine = ThreatRAGEngine(gateway_url="http://127.0.0.1:9")

    assert engine._retrieval_mode == "bm25"
    assert engine._vector_store is None
    assert engine._corpus is not None
    assert engine.search_threat_intel("whoami") == []
    assert engine.hybrid_search("whoami")[0]["doc_id"] == "T1003"
    assert engine.retrieval_provenance["effective_backend"] == "bm25"


def test_dense_missing_store_fails_configuration(monkeypatch, tmp_path):
    monkeypatch.setenv("RAGIN_RAG_MODE", "dense")
    monkeypatch.setenv("RAGIN_VECTOR_STORE_PATH", str(tmp_path / "missing"))
    monkeypatch.setattr("ragin.don.rag_engine.IntelCorpus", _Boom)
    with pytest.raises(RuntimeError, match="exact store|requires"):
        ThreatRAGEngine(gateway_url="http://127.0.0.1:9")


def test_dense_missing_local_model_fails_configuration(monkeypatch, tmp_path):
    monkeypatch.setenv("RAGIN_RAG_MODE", "dense")
    store = tmp_path / "store"
    store.mkdir()
    (store / "index.faiss").write_bytes(b"fake")
    (store / "documents.json").write_text("[]", encoding="utf-8")
    monkeypatch.setenv("RAGIN_VECTOR_STORE_PATH", str(store))
    monkeypatch.delenv("RAGIN_EMBED_MODEL", raising=False)
    _fake_dense_runtime(monkeypatch)
    monkeypatch.setattr("ragin.don.rag_engine.IntelCorpus", _Boom)

    with pytest.raises(RuntimeError, match="local model directory"):
        ThreatRAGEngine(gateway_url="http://127.0.0.1:9")


def test_dense_mode_uses_only_dense_channel(monkeypatch, tmp_path):
    store = tmp_path / "store"
    store.mkdir()
    (store / "index.faiss").write_bytes(b"fake")
    (store / "documents.json").write_text("[]", encoding="utf-8")
    model = tmp_path / "model"
    model.mkdir()
    monkeypatch.setenv("RAGIN_RAG_MODE", "dense")
    monkeypatch.setenv("RAGIN_VECTOR_STORE_PATH", str(store))
    monkeypatch.setenv("RAGIN_EMBED_MODEL", str(model))
    _fake_dense_runtime(monkeypatch)
    monkeypatch.setattr("ragin.don.rag_engine.IntelCorpus", _Boom)
    monkeypatch.setattr("ragin.don.rag_engine.VectorStore", _FakeVectorStore)

    engine = ThreatRAGEngine(gateway_url="http://127.0.0.1:9")

    def _forbidden_keyword(query):
        raise AssertionError("dense-only mode must not call BM25")

    engine.keyword_search = _forbidden_keyword
    hits = engine.hybrid_search("whoami")
    assert [hit["doc_id"] for hit in hits] == ["DENSE_ONLY"]
    assert engine.retrieval_provenance["effective_backend"] == "dense"
    assert engine.retrieval_provenance["configured_mode"] == "dense"
    assert engine.retrieval_provenance["dense_constructed"] is True
    assert engine.retrieval_provenance["sparse_constructed"] is False
    assert engine._vector_store.model_ref == str(model)
    assert (
        engine.retrieval_provenance["encoder_binding"]
        == "EXPLICIT_VALIDATED_MODEL_DIR_NOT_RUNTIME_VERIFIED"
    )


def test_default_mode_remains_hybrid(monkeypatch, tmp_path):
    monkeypatch.delenv("RAGIN_RAG_MODE", raising=False)
    monkeypatch.setattr("ragin.don.rag_engine.IntelCorpus", _FakeCorpus)
    monkeypatch.setattr("ragin.don.rag_engine.VectorStore", _FakeVectorStore)

    engine = ThreatRAGEngine(gateway_url="http://127.0.0.1:9", vector_store_path=str(tmp_path))
    assert engine._retrieval_mode == "hybrid"
    assert engine.retrieval_provenance["effective_backend"] == "hybrid"
    assert engine.retrieval_provenance["sparse_constructed"] is True
    assert engine.retrieval_provenance["dense_constructed"] is True


@pytest.mark.parametrize(
    ("corpus_cls", "store_cls", "expected_backend", "expected_sparse", "expected_dense"),
    [
        pytest.param(
            _FakeCorpus,
            _EmptyVectorStore,
            "bm25",
            True,
            False,
            id="empty-hybrid-dense-populated-sparse",
        ),
        pytest.param(
            _EmptyCorpus,
            _EmptyVectorStore,
            "none",
            False,
            False,
            id="hybrid-both-empty",
        ),
    ],
)
def test_hybrid_effective_backend_uses_observed_documents(
    monkeypatch,
    tmp_path,
    corpus_cls,
    store_cls,
    expected_backend,
    expected_sparse,
    expected_dense,
):
    """An empty dense half must never be labelled hybrid.

    These are labelled fakes: no model is loaded, downloaded, or queried.
    """
    monkeypatch.setenv("RAGIN_RAG_MODE", "hybrid")
    monkeypatch.setattr("ragin.don.rag_engine.IntelCorpus", corpus_cls)
    monkeypatch.setattr("ragin.don.rag_engine.VectorStore", store_cls)

    engine = ThreatRAGEngine(
        gateway_url="http://127.0.0.1:9",
        vector_store_path=str(tmp_path / "store"),
    )

    provenance = engine.retrieval_provenance
    assert provenance["requested_mode"] == "hybrid"
    assert provenance["configured_mode"] == "hybrid"
    assert provenance["effective_backend"] == expected_backend
    assert provenance["sparse_documents"] == (1 if expected_sparse else 0)
    assert provenance["dense_documents"] == 0
    assert provenance["sparse_constructed"] is expected_sparse
    assert provenance["dense_constructed"] is expected_dense
    assert provenance["sparse_configured"] is True
    assert provenance["dense_configured"] is True
    assert provenance["encoder_binding"] == "MODULE_IMPORT_ENCODER_CONSTANT_NOT_VERIFIED"
    assert provenance["observed_query_execution"] == "NOT_OBSERVED_AT_INIT"
    assert provenance["dense_query_observed"] is False
    assert provenance["retrieval_execution_claim"] == "CONFIGURED_CAPABILITY_ONLY"

    hits = engine.hybrid_search("whoami")
    if expected_sparse:
        assert [hit["doc_id"] for hit in hits] == ["T1003"]
    else:
        assert hits == []

    after = engine.retrieval_provenance
    assert after["effective_backend"] == expected_backend
    assert after["dense_query_observed"] is True
    assert after["observed_query_execution"] == "DENSE_QUERY_EXECUTED"
    assert after["dense_query_returned_documents"] == 0
    assert after["retrieval_execution_claim"] == "QUERY_OBSERVED_EMPTY"


def test_unknown_mode_falls_back_to_legacy_hybrid_and_preserves_requested(monkeypatch, tmp_path):
    monkeypatch.setenv("RAGIN_RAG_MODE", "not-a-mode")
    monkeypatch.setattr("ragin.don.rag_engine.IntelCorpus", _FakeCorpus)
    monkeypatch.setattr("ragin.don.rag_engine.VectorStore", _FakeVectorStore)

    engine = ThreatRAGEngine(gateway_url="http://127.0.0.1:9", vector_store_path=str(tmp_path))

    assert engine._retrieval_mode == "hybrid"
    provenance = engine.retrieval_provenance
    assert provenance["requested_mode"] == "not-a-mode"
    assert provenance["configured_mode"] == "hybrid"
    assert provenance["effective_backend"] == "hybrid"


def test_don_adapter_passes_store_path_and_provenance(monkeypatch, tmp_path):
    store = tmp_path / "store"
    store.mkdir()
    (store / "index.faiss").write_bytes(b"fake")
    (store / "documents.json").write_text("[]", encoding="utf-8")
    model = tmp_path / "model"
    model.mkdir()
    monkeypatch.setenv("RAGIN_RAG_MODE", "dense")
    monkeypatch.setenv("RAGIN_EMBED_MODEL", str(model))
    _fake_dense_runtime(monkeypatch)
    monkeypatch.setattr("ragin.don.rag_engine.IntelCorpus", _Boom)
    monkeypatch.setattr("ragin.don.rag_engine.VectorStore", _FakeVectorStore)

    adapter = DonAdapter(gateway_url="http://127.0.0.1:9", vector_store_path=str(store))
    assert adapter._engine.retrieval_provenance["effective_backend"] == "dense"


def test_evidence_bundle_reports_observed_backend_not_static_hybrid():
    class _Analysis:
        intel_documents = []
        classification = types.SimpleNamespace(value="malicious")
        severity = types.SimpleNamespace(value="high")
        confidence = 0.5
        tactics = []
        iocs = []

    bundle = build_evidence_bundle(
        _Analysis(),
        {
            "session_id": "s1",
            "classification": {"skill_level": "expert", "confidence": 0.9},
            "retrieval_provenance": {
                "effective_backend": "dense",
                "backend_source": "ENGINE_OBSERVED",
                "requested_mode": "dense",
                "sparse_documents": 0,
                "dense_documents": 7,
            },
        },
        "whoami",
    )
    retrieval = bundle["retrieval"]
    assert retrieval["backend"] == "dense"
    assert retrieval["backend_source"] == "ENGINE_OBSERVED"
    assert retrieval["mode"] == "dense"
    assert retrieval["dense_documents"] == 7
    assert retrieval["retrieval_status"] == "SUCCESS"


def test_evidence_bundle_marks_disabled_retrieval():
    class _Analysis:
        intel_documents = []
        classification = types.SimpleNamespace(value="malicious")
        severity = types.SimpleNamespace(value="high")
        confidence = 0.5
        tactics = []
        iocs = []

    bundle = build_evidence_bundle(
        _Analysis(),
        {
            "session_id": "s1",
            "classification": {"skill_level": "expert"},
            "retrieval_provenance": {"effective_backend": "none", "requested_mode": "none"},
        },
        "whoami",
    )
    assert bundle["retrieval"]["backend"] == "none"
    assert bundle["retrieval"]["retrieval_status"] == "DISABLED"
    assert bundle["retrieval"]["trace_summary"]["usable_successful_retrieval"] is False


def test_evidence_bundle_empty_configured_hybrid_is_not_disabled():
    class _Analysis:
        intel_documents = []
        classification = types.SimpleNamespace(value="malicious")
        severity = types.SimpleNamespace(value="high")
        confidence = 0.5
        tactics = []
        iocs = []

    bundle = build_evidence_bundle(
        _Analysis(),
        {
            "session_id": "s1",
            "classification": {"skill_level": "expert"},
            "retrieval_provenance": {
                "effective_backend": "none",
                "requested_mode": "hybrid",
                "configured_mode": "hybrid",
                "backend_source": "ENGINE_OBSERVED",
                "sparse_documents": 0,
                "dense_documents": 0,
            },
        },
        "whoami",
    )
    retrieval = bundle["retrieval"]
    assert retrieval["backend"] == "none"
    assert retrieval["mode"] == "hybrid"
    assert retrieval["configured_mode"] == "hybrid"
    assert retrieval["retrieval_status"] == "EMPTY"
    assert retrieval["retrieval_status"] != "DISABLED"
    assert retrieval["trace_summary"]["usable_successful_retrieval"] is False
