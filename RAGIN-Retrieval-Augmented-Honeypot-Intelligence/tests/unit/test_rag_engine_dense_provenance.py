"""Focused tests for post-query dense encoder provenance.

These pin one contract only: after a dense query actually returns documents,
`retrieval_provenance` must describe what was OBSERVED, without (a) claiming
an encoder load that never happened, or (b) reporting hash-fallback vectors as
real sentence-transformers inference.

All stores here are explicitly labelled fakes. No model is loaded, no
embedding inference runs, no network or provider is contacted.
"""

from __future__ import annotations

import pytest

from ragin.don.rag_engine import ThreatRAGEngine

pytestmark = pytest.mark.unit

INIT_BINDING = "EXPLICIT_VALIDATED_MODEL_DIR_NOT_RUNTIME_VERIFIED"
INIT_NOTE = "init-only placeholder: encoder load and embedding inference were not executed"


class _Index:
    def __init__(self, ntotal: int) -> None:
        self.ntotal = ntotal


class _RealEncoderStore:
    """Fake VectorStore that has completed init with a (fake) encoder loaded."""

    _initialized = True
    _dimension = 384

    def __init__(self) -> None:
        self._embedder = object()
        self._index = _Index(3)

    def search(self, query, top_k=10):
        return [{"doc_id": "d1", "score": 0.9}, {"doc_id": "d2", "score": 0.4}]


class _HashFallbackStore:
    """Fake VectorStore initialised WITHOUT an encoder (documented fallback)."""

    _initialized = True
    _dimension = 384
    _embedder = None
    _index = None

    def search(self, query, top_k=10):
        return [{"doc_id": "d1", "score": 0.9}]


class _EmptyRealEncoderStore(_RealEncoderStore):
    def search(self, query, top_k=10):
        # VectorStore.search returns before encoding when it holds no docs.
        return []


class _OpaqueStore:
    """Test double exposing neither encoder nor initialisation state."""

    def search(self, query, top_k=10):
        return [{"doc_id": "d1", "score": 0.9}]


def _engine(store) -> ThreatRAGEngine:
    engine = object.__new__(ThreatRAGEngine)
    engine._lightrag_adapter = None
    engine._retrieval_mode = "dense"
    engine._vector_store = store
    engine._retrieval_provenance = {
        "schema": "ragin.retrieval_provenance.v1",
        "requested_mode": "dense",
        "configured_mode": "dense",
        "effective_backend": "dense",
        "encoder_binding": INIT_BINDING,
        "encoder_binding_note": INIT_NOTE,
        "observed_query_execution": "NOT_OBSERVED_AT_INIT",
        "dense_query_observed": False,
        "dense_query_returned_documents": None,
        "retrieval_execution_claim": "CONFIGURED_CAPABILITY_ONLY",
    }
    return engine


def test_real_encoder_binding_upgraded_only_after_observed_dense_query():
    engine = _engine(_RealEncoderStore())
    assert engine.retrieval_provenance["encoder_binding"] == INIT_BINDING

    hits = engine.search_threat_intel("whoami", top_k=2)

    assert [h["doc_id"] for h in hits] == ["d1", "d2"]
    p = engine.retrieval_provenance
    assert p["observed_query_execution"] == "DENSE_QUERY_EXECUTED"
    assert p["dense_query_returned_documents"] == 2
    assert p["retrieval_execution_claim"] == "QUERY_OBSERVED_RETURNED_DOCUMENTS"
    assert p["encoder_binding"] == "LOCAL_ENCODER_RUNTIME_VERIFIED"
    assert "no hash-fallback" in p["encoder_binding_note"]
    assert p["encoder_inference_claim"] == "OBSERVED_REAL_ENCODER_DENSE_QUERY"
    assert p["encoder_observed"]["observability"] == "OBSERVED_REAL_ENCODER"
    assert p["encoder_observed"]["embedder_loaded"] is True
    assert p["encoder_observed"]["index_ntotal"] == 3
    assert p["encoder_observed"]["dimension"] == 384


def test_hash_fallback_is_never_reported_as_real_encoder_inference():
    engine = _engine(_HashFallbackStore())

    engine.search_threat_intel("whoami", top_k=2)

    p = engine.retrieval_provenance
    assert p["encoder_binding"] == "HASH_FALLBACK_EMBEDDINGS_OBSERVED"
    assert p["encoder_binding"] != "LOCAL_ENCODER_RUNTIME_VERIFIED"
    assert "no sentence-transformers encoder was loaded" in p["encoder_binding_note"]
    assert p["encoder_inference_claim"] == "OBSERVED_HASH_FALLBACK_DENSE_QUERY"
    assert p["encoder_observed"]["observability"] == "OBSERVED_HASH_FALLBACK"
    assert p["encoder_observed"]["embedder_loaded"] is False


def test_empty_store_does_not_claim_embedding_inference():
    engine = _engine(_EmptyRealEncoderStore())

    assert engine.search_threat_intel("whoami", top_k=2) == []

    p = engine.retrieval_provenance
    assert p["dense_query_returned_documents"] == 0
    assert p["retrieval_execution_claim"] == "QUERY_OBSERVED_EMPTY"
    assert p["encoder_inference_claim"] == "NO_DOCUMENTS_NO_INFERENCE"
    # Conservative init label is retained: an empty store proves no encoding.
    assert p["encoder_binding"] == INIT_BINDING


def test_unobservable_store_keeps_conservative_binding():
    engine = _engine(_OpaqueStore())

    engine.search_threat_intel("whoami", top_k=2)

    p = engine.retrieval_provenance
    assert p["encoder_inference_claim"] == "NOT_OBSERVABLE_AT_STORE"
    assert p["encoder_observed"]["observability"] == "NOT_OBSERVABLE_AT_STORE"
    assert p["encoder_observed"]["embedder_loaded"] is False
    # Absence of attributes is not evidence of fallback or of inference.
    assert p["encoder_binding"] == INIT_BINDING
