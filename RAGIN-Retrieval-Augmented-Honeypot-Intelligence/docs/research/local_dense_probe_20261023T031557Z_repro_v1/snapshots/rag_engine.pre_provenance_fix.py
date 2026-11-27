"""ThreatRAGEngine — hybrid RAG engine combining vector similarity and BM25 keyword search."""

from __future__ import annotations

import hashlib
import logging
import math
import os
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import requests

from ragin.gateway.client import GatewayClient
from ragin.utils import CircuitBreaker, CostTracker, PromptTokenLimiter, _redact_pii

from .command_aware_v2 import VERSION as COMMAND_AWARE_V2_VERSION
from .command_aware_v2 import CommandAwareRetrieverV2
from .intel_corpus import IntelCorpus
from .models import (
    AnalysisRequest,
    GatewayMessage,
    GatewayRequest,
    SeverityLevel,
    ThreatAnalysis,
)
from .vector_store import VectorStore

if TYPE_CHECKING:
    from .lightrag_adapter import LightRAGAdapter

logger = logging.getLogger(__name__)

_DEFAULT_GATEWAY_URL = os.environ.get("RAGIN_GATEWAY_URL", "http://localhost:8080")
_DEFAULT_MODEL = os.environ.get("RAGIN_DON_MODEL", "glm-5.3-flash-free")

# Query-side stopwords: high-frequency, zero-discriminative-value terms that
# would otherwise dominate BM25 scoring on analyst-style queries ("what does
# technique X cover?").
_QUERY_STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "how",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "via",
        "what",
        "when",
        "where",
        "which",
        "with",
        "does",
        "do",
        "cover",
        "covers",
        "attack",
        "technique",
        "mitre",
        "guidance",
        "use",
        "uses",
        "against",
    ]
)


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokens with '&' normalised ('ATT&CK' → 'attack')."""
    return re.findall(r"\w+", text.replace("&", ""))


class ThreatRAGEngine:
    """Hybrid RAG engine for threat intelligence analysis."""

    def __init__(
        self,
        vector_store_path: str | None = None,
        gateway_url: str | None = None,
        corpus_path: str | None = None,
        api_key: str | None = None,
        lightrag_adapter: LightRAGAdapter | None = None,
    ) -> None:
        self._gateway_url = (gateway_url or _DEFAULT_GATEWAY_URL).rstrip("/")
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self._model = _DEFAULT_MODEL

        # Production infrastructure
        self._circuit_breaker = CircuitBreaker(threshold=5, timeout_s=60.0)
        self._cost_tracker = CostTracker(daily_budget_usd=100.0, monthly_budget_usd=2000.0, per_request_budget_usd=0.10)
        self._prompt_limiter = PromptTokenLimiter(max_prompt_tokens=32_000)

        self._lightrag_adapter = lightrag_adapter
        self._bm25_index: dict[str, list[str]] = {}  # term → [doc_ids]
        self._doc_store: dict[str, dict[str, Any]] = {}
        self._bm25_tf: dict[str, dict[str, int]] = {}  # doc_id → {term: tf}
        self._bm25_doclen: dict[str, int] = {}  # doc_id → token count
        self._avg_doclen: float = 0.0
        self._title_df: dict[str, int] = {}  # term → docs whose title contains it
        self._command_aware_v2 = None
        requested_env_mode = os.environ.get("RAGIN_RAG_MODE", "hybrid").strip().lower()
        if lightrag_adapter is not None and requested_env_mode not in {"hybrid", ""}:
            # An explicit ablation mode must not be silently overridden by a
            # LightRAG adapter. This is a configuration error, not a fallback.
            raise ValueError(
                "lightrag_adapter is incompatible with explicit "
                f"RAGIN_RAG_MODE={requested_env_mode!r}; use RAGIN_RAG_MODE=hybrid "
                "or remove the adapter"
            )
        if lightrag_adapter is not None:
            logger.info("ThreatRAGEngine using LightRAG adapter")
            self._vector_store = None
            self._corpus = None
            self._retrieval_mode = "hybrid"
            self._retrieval_provenance = {
                "schema": "ragin.retrieval_provenance.v1",
                "requested_mode": "lightrag",
                "effective_backend": "lightrag",
                "backend_source": "ENGINE_OBSERVED",
                "vector_store_path": "",
                "sparse_documents": 0,
                "dense_documents": 0,
                "sparse_constructed": False,
                "dense_constructed": False,
            }
        else:
            # Explicit ablation modes. The historical default remains hybrid
            # vector+BM25. ``bm25`` (and its legacy aliases ``sparse`` /
            # ``offline``) constructs only the sparse index; ``none`` builds no
            # retriever at all; ``dense`` requires an exact persisted store and
            # a local embedding model and never falls back to BM25.
            requested_mode = os.environ.get("RAGIN_RAG_MODE", "hybrid").strip().lower()
            aliases = {"sparse": "bm25", "offline": "bm25"}
            resolved_mode = aliases.get(requested_mode, requested_mode)
            if resolved_mode not in {"none", "bm25", "dense", "hybrid"}:
                # Preserve the historical behavior: an unknown value is not a
                # new mode and must not break the legacy hybrid serving path.
                logger.warning(
                    "Unknown RAGIN_RAG_MODE=%r; preserving legacy fallback to hybrid",
                    requested_mode,
                )
                resolved_mode = "hybrid"
            self._retrieval_mode = resolved_mode
            self._vector_store = None
            self._corpus = None
            dense_docs = 0
            dense_configured = False
            sparse_configured = False
            encoder_binding = "NOT_APPLICABLE"
            encoder_binding_note = "no dense channel is configured"
            if self._retrieval_mode == "none":
                logger.info("ThreatRAGEngine retrieval disabled (RAGIN_RAG_MODE=none)")
            elif self._retrieval_mode == "bm25":
                self._corpus = IntelCorpus(corpus_path=corpus_path)
                self._load_corpus_and_index()
                sparse_configured = True
                logger.info("ThreatRAGEngine sparse-only mode enabled (BM25; no sentence-transformer initialization)")
            elif self._retrieval_mode == "dense":
                store_path, model_ref = self._require_dense_configuration(vector_store_path)
                self._vector_store = VectorStore(store_path=store_path, model_ref=model_ref)
                self._vector_store.load(store_path)
                dense_configured = True
                dense_docs = int(getattr(self._vector_store, "document_count", 0))
                if dense_docs <= 0:
                    raise RuntimeError(
                        f"dense retrieval configured but the exact store at {store_path!r} contains no documents"
                    )
                # The model directory was validated and passed explicitly, but
                # no encoder was loaded or queried in this process. That is a
                # capability binding, not a measured dense-search result.
                encoder_binding = "EXPLICIT_VALIDATED_MODEL_DIR_NOT_RUNTIME_VERIFIED"
                encoder_binding_note = (
                    "RAGIN_EMBED_MODEL was validated as a local directory and passed to "
                    "VectorStore; encoder load and embedding inference were not executed"
                )
                logger.info("ThreatRAGEngine dense-only mode enabled (store=%s, docs=%d)", store_path, dense_docs)
            else:
                self._vector_store = VectorStore(store_path=vector_store_path)
                dense_configured = self._vector_store is not None
                if self._vector_store is not None and vector_store_path:
                    persisted = Path(vector_store_path) / "index.faiss"
                    if persisted.exists():
                        self._vector_store.load(vector_store_path)
                # Inspect the loaded store, not the requested mode. An empty
                # dense half must not be labelled "hybrid".
                dense_docs = int(getattr(self._vector_store, "document_count", 0))
                encoder_binding = "MODULE_IMPORT_ENCODER_CONSTANT_NOT_VERIFIED"
                encoder_binding_note = (
                    "VectorStore resolves its encoder from the module-import constant; "
                    "no embedding search was executed or verified at initialization"
                )
                self._corpus = IntelCorpus(corpus_path=corpus_path)
                self._load_corpus_and_index()
                sparse_configured = True

            sparse_docs = len(self._doc_store)
            # Effective backend is the data-bearing backend observed after
            # construction/loading. Configured capability is reported
            # separately so initialization is never mistaken for a successful
            # embedding query.
            if dense_docs > 0 and sparse_docs > 0:
                effective_backend = "hybrid"
            elif sparse_docs > 0:
                effective_backend = "bm25"
            elif dense_docs > 0:
                effective_backend = "dense"
            else:
                effective_backend = "none"

            self._retrieval_provenance = {
                "schema": "ragin.retrieval_provenance.v1",
                "requested_mode": requested_mode,
                "configured_mode": self._retrieval_mode,
                "effective_backend": effective_backend,
                "backend_source": "ENGINE_OBSERVED",
                "vector_store_path": str(vector_store_path or os.environ.get("RAGIN_VECTOR_STORE_PATH", "") or ""),
                "sparse_documents": sparse_docs,
                "dense_documents": dense_docs,
                "sparse_configured": sparse_configured,
                "dense_configured": dense_configured,
                "sparse_constructed": sparse_docs > 0,
                "dense_constructed": dense_docs > 0,
                "encoder_binding": encoder_binding,
                "encoder_binding_note": encoder_binding_note,
                "observed_query_execution": "NOT_OBSERVED_AT_INIT",
                "dense_query_observed": False,
                "dense_query_returned_documents": None,
                "retrieval_execution_claim": "CONFIGURED_CAPABILITY_ONLY",
            }

        if (
            os.environ.get("RAGIN_DON_RETRIEVAL_VERSION", "").strip() == COMMAND_AWARE_V2_VERSION
            and getattr(self, "_retrieval_mode", "hybrid") == "hybrid"
        ):
            self._command_aware_v2 = CommandAwareRetrieverV2()

        self._gateway = GatewayClient(
            gateway_url=self._gateway_url,
            api_key=self._api_key,
            timeout=float(os.environ.get("RAGIN_GATEWAY_TIMEOUT", "600.0")),
            default_model=self._model,
        )

        parsed_gateway = urlparse(self._gateway_url)
        safe_gateway = f"{parsed_gateway.scheme}://{parsed_gateway.hostname or ''}"
        if parsed_gateway.port:
            safe_gateway += f":{parsed_gateway.port}"
        logger.info("ThreatRAGEngine initialised (gateway=%s)", safe_gateway)

    @staticmethod
    def _require_dense_configuration(vector_store_path: str | None) -> tuple[str, str]:
        """Validate dense-only prerequisites without downloading anything.

        A dense request is a configuration error, not an invitation to fall
        back to BM25. The exact persisted index and a local embedding-model
        directory must exist before the engine is constructed. Model weights
        are never fetched here. Returns ``(store_path, model_ref)`` so the
        validated directory can be bound explicitly to VectorStore instead of
        relying on the module-import encoder constant.
        """
        store_path = str(vector_store_path or os.environ.get("RAGIN_VECTOR_STORE_PATH", "") or "").strip()
        if not store_path:
            raise RuntimeError(
                "RAGIN_RAG_MODE=dense requires RAGIN_VECTOR_STORE_PATH (or an explicit vector_store_path)"
            )
        store = Path(store_path)
        missing = [name for name in ("index.faiss", "documents.json") if not (store / name).is_file()]
        if missing:
            raise RuntimeError(
                f"RAGIN_RAG_MODE=dense requires the exact store at {store_path!r}; missing {missing}"
            )
        try:
            import faiss  # noqa: F401
            import sentence_transformers  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "RAGIN_RAG_MODE=dense requires faiss and sentence-transformers to be installed"
            ) from exc
        model_ref = os.environ.get("RAGIN_EMBED_MODEL", "").strip()
        if not model_ref or not Path(model_ref).is_dir():
            raise RuntimeError(
                "RAGIN_RAG_MODE=dense requires RAGIN_EMBED_MODEL to be a local model directory; "
                "no model download is attempted"
            )
        return store_path, model_ref

    @property
    def retrieval_provenance(self) -> dict[str, Any]:
        """Observed retrieval configuration for this engine instance."""
        return dict(getattr(self, "_retrieval_provenance", {}))

    # ------------------------------------------------------------------
    # Main analysis entry point
    # ------------------------------------------------------------------

    def analyze_graph(
        self,
        classification_result: AnalysisRequest,
        session_log: list[dict[str, Any]],
    ) -> ThreatAnalysis:
        """LangGraph-orchestrated analysis (corrective-RAG pattern).

        Pipeline: query decomposition -> parallel hybrid retrieval ->
        LLM relevance grading (heuristic fallback) -> sufficiency check
        with bounded query-rewrite loop -> composed context. The graph's
        graded, fused context replaces the single-shot context of
        analyze(); everything downstream (threat mapping, severity,
        model shape) is identical. Degrades gracefully to heuristic
        retrieval when the LLM gateway is unavailable.
        """
        from .graph import DonRAGGraph

        if getattr(self, "_rag_graph", None) is None:
            self._rag_graph = DonRAGGraph(self)

        query = self._build_query(classification_result)
        result = self._rag_graph.invoke(query)

        # Keep the composed context for generate_report() — same channel
        # the legacy path uses.
        self._last_intel_context = result.context
        self._last_graph_result = result

        from .threat_mapper import ThreatMapper

        mapper = ThreatMapper()
        tactics = mapper.map_to_mitre(classification_result.features)
        iocs = mapper.generate_ioc_list(session_log)
        actors = mapper.identify_actor(
            tactics, iocs, attacker_input=classification_result.features.get("attacker_input")
        )
        soph = mapper.calculate_sophistication_score(classification_result.features)
        severity = self._derive_severity(
            classification_result.classification.value,
            classification_result.confidence,
            soph,
        )
        return ThreatAnalysis(
            analysis_id=_make_id(classification_result.session_id),
            session_id=classification_result.session_id,
            classification=classification_result.classification,
            severity=severity,
            confidence=classification_result.confidence,
            tactics=tactics,
            threat_actors=actors,
            iocs=iocs,
            sophistication_score=soph,
            intel_documents=[self._hit_to_intel_doc(d) for d in result.relevant_docs[:10]],
            raw_features=classification_result.features,
        )

    def _load_corpus_and_index(self) -> None:
        """Load the intel corpus and build the BM25 index from it.

        Without this, keyword_search()/hybrid_search() silently degrade to
        vector-only because _bm25_index is never populated.
        """
        try:
            if self._corpus is None:
                raise FileNotFoundError("corpus not configured")
            count = self._corpus.load_corpus()
            docs = self._corpus.documents if hasattr(self._corpus, "documents") else self._corpus._documents
            if docs:
                self._build_index(docs)
                logger.info("Don BM25 index built: %d docs, %d terms", len(docs), len(self._bm25_index))
            else:
                # Fall back to the vector store's persisted documents so the
                # BM25 half of hybrid_search is not silently empty when the
                # flat corpus directory is absent.
                vs_docs = list(getattr(self._vector_store, "_documents", []) or [])
                if vs_docs:
                    self._build_index(vs_docs)
                    logger.info(
                        "Don corpus empty — BM25 index built from vector store: %d docs, %d terms",
                        len(vs_docs),
                        len(self._bm25_index),
                    )
                else:
                    logger.warning("Don corpus loaded %d docs — BM25 index empty", count)
        except FileNotFoundError:
            vs_docs = list(getattr(self._vector_store, "_documents", []) or [])
            if vs_docs:
                self._build_index(vs_docs)
                logger.info("Don corpus missing — BM25 index built from vector store: %d docs", len(vs_docs))
            else:
                logger.warning(
                    "Don corpus not found at %s — BM25 index empty", getattr(self._corpus, "_corpus_path", "<unset>")
                )
        except Exception:
            logger.exception("Failed to build Don BM25 index — hybrid search degrades to vector-only")

    def analyze(
        self,
        classification_result: AnalysisRequest,
        session_log: list[dict[str, Any]],
    ) -> ThreatAnalysis:
        """Full threat analysis pipeline."""
        if self._command_aware_v2 is not None:
            return self._analyze_command_aware_v2(classification_result, session_log)
        analysis_id = _make_id(classification_result.session_id)

        # 1. Build query from classification
        query = self._build_query(classification_result)

        # 2. Hybrid search
        intel_hits = self.hybrid_search(query, alpha=0.7)

        # 3. Build LLM context from hits (kept on the instance so
        # generate_report() can ground the narrative in retrieved intel)
        self._last_intel_context = self._build_context(intel_hits)

        # 4. Map tactics and identify actors
        from .threat_mapper import ThreatMapper

        mapper = ThreatMapper()
        tactics = mapper.map_to_mitre(classification_result.features)
        iocs = mapper.generate_ioc_list(session_log)
        actors = mapper.identify_actor(
            tactics, iocs, attacker_input=classification_result.features.get("attacker_input")
        )
        soph = mapper.calculate_sophistication_score(classification_result.features)

        # 5. Determine severity
        severity = self._derive_severity(
            classification_result.classification.value,
            classification_result.confidence,
            soph,
        )

        return ThreatAnalysis(
            analysis_id=analysis_id,
            session_id=classification_result.session_id,
            classification=classification_result.classification,
            severity=severity,
            confidence=classification_result.confidence,
            tactics=tactics,
            threat_actors=actors,
            iocs=iocs,
            sophistication_score=soph,
            intel_documents=[self._hit_to_intel_doc(h) for h in intel_hits[:10]],
            raw_features=classification_result.features,
        )

    def _analyze_command_aware_v2(
        self,
        classification_result: AnalysisRequest,
        session_log: list[dict[str, Any]],
    ) -> ThreatAnalysis:
        attacker_commands = [
            str(item.get("content", ""))
            for item in session_log
            if item.get("role") == "attacker" and isinstance(item.get("content"), str)
        ]
        current_command = str(classification_result.features.get("attacker_input") or (attacker_commands[-1] if attacker_commands else ""))
        preceding_commands = attacker_commands[:-1] if attacker_commands and attacker_commands[-1] == current_command else attacker_commands
        if self._command_aware_v2 is None:
            raise RuntimeError("command-aware v2 retriever is not initialized")
        result = self._command_aware_v2.retrieve(
            current_command,
            preceding_commands,
            session_id=classification_result.session_id,
            classification=classification_result.classification.value,
        )
        hits = result["documents"]
        self._last_intel_context = self._build_context(hits)
        from .threat_mapper import ThreatMapper

        mapper = ThreatMapper()
        iocs = mapper.generate_ioc_list(session_log)
        sophistication = mapper.calculate_sophistication_score(classification_result.features)
        trace = result["trace"]
        raw_features = {
            **classification_result.features,
            "command_aware_v2": {
                "implementation_version": COMMAND_AWARE_V2_VERSION,
                "command_features": trace["context_projection"]["features"],
                "retrieval_trace": trace,
            },
        }
        return ThreatAnalysis(
            analysis_id=_make_id(classification_result.session_id),
            session_id=classification_result.session_id,
            classification=classification_result.classification,
            severity=self._derive_severity(classification_result.classification.value, classification_result.confidence, sophistication),
            confidence=classification_result.confidence,
            tactics=[],
            threat_actors=[],
            iocs=iocs,
            sophistication_score=sophistication,
            intel_documents=[self._hit_to_intel_doc(hit) for hit in hits],
            raw_features=raw_features,
        )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_threat_intel(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Vector similarity search — routes to LightRAG adapter or VectorStore."""
        if self._lightrag_adapter is not None:
            return self._lightrag_adapter.search(query, top_k=top_k)
        if getattr(self, "_retrieval_mode", "hybrid") in {"none", "bm25"}:
            return []
        if self._vector_store is None:
            logger.warning("search_threat_intel: no vector store configured")
            return []
        results = self._vector_store.search(query, top_k=top_k)
        provenance = getattr(self, "_retrieval_provenance", None)
        if isinstance(provenance, dict):
            # Record observed execution separately from configured capability.
            # Initialization alone is never evidence that embedding search
            # succeeded; an empty store executes and returns zero documents.
            provenance["observed_query_execution"] = "DENSE_QUERY_EXECUTED"
            provenance["dense_query_observed"] = True
            provenance["dense_query_returned_documents"] = len(results)
            provenance["retrieval_execution_claim"] = (
                "QUERY_OBSERVED_RETURNED_DOCUMENTS" if results else "QUERY_OBSERVED_EMPTY"
            )
        return results

    def keyword_search(self, query: str) -> list[dict[str, Any]]:
        """Okapi BM25 keyword search with title-field boosting.

        Falls back to shared-term counting when the index was built
        without frequency statistics (legacy callers in tests).
        """
        if getattr(self, "_retrieval_mode", "hybrid") in {"none", "dense"}:
            return []
        terms = _tokenize(query.lower())
        # Drop generic stopwords that carry no discriminative weight.
        terms = [t for t in terms if t not in _QUERY_STOPWORDS]
        if not terms:
            return []

        if not self._bm25_tf:
            return self._legacy_keyword_search(terms)

        n_docs = len(self._bm25_doclen)
        avgdl = self._avg_doclen or 1.0
        k1, b = 1.5, 0.75
        scores: dict[str, float] = {}
        for term in set(terms):
            doc_ids = self._bm25_index.get(term, [])
            df = len(doc_ids)
            if df == 0:
                continue
            idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
            for doc_id in doc_ids:
                tf = self._bm25_tf[doc_id].get(term, 0)
                if tf == 0:
                    continue
                dl = self._bm25_doclen[doc_id] or 1
                scores[doc_id] = scores.get(doc_id, 0.0) + idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
        # Title evidence: a query term appearing in the doc's title is a
        # strong relevance signal (ATT&CK canonical pages carry the
        # technique name/ID in their title).
        for term in set(terms):
            if self._title_df.get(term, 0) > 0:
                idf_title = math.log((n_docs - self._title_df[term] + 0.5) / (self._title_df[term] + 0.5) + 1.0)
                for doc_id in self._bm25_index.get(term, []):
                    title_text = self._doc_store[doc_id].get("title", "").lower()
                    if term in title_text:
                        scores[doc_id] = scores.get(doc_id, 0.0) + 2.0 * idf_title

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results: list[dict[str, Any]] = []
        for doc_id, score in ranked:
            if doc_id in self._doc_store:
                entry = {**self._doc_store[doc_id], "score": score}
                results.append(entry)
        return results

    def _legacy_keyword_search(self, terms: list[str]) -> list[dict[str, Any]]:
        """Shared-term-count ranking (pre-BM25 fallback)."""
        scores: dict[str, float] = {}
        for term in set(terms):
            for doc_id in self._bm25_index.get(term, []):
                scores[doc_id] = scores.get(doc_id, 0.0) + 1.0
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [{**self._doc_store[doc_id], "score": score} for doc_id, score in ranked if doc_id in self._doc_store]

    def hybrid_search(self, query: str, alpha: float = 0.25) -> list[dict[str, Any]]:
        """Combine vector and keyword results with reciprocal-rank fusion.

        alpha is the dense-arm weight; the sparse/BM25 arm carries
        (1 - alpha). The empirical optimum on the 50-query ATT&CK IR
        benchmark is alpha≈0.15–0.25: exact-match evidence (technique IDs,
        titles) is the dominant signal over this corpus.

        When a LightRAG adapter is configured, delegates entirely to it
        (adapter handles its own hybrid scoring).
        """
        if self._lightrag_adapter is not None:
            return self._lightrag_adapter.hybrid_search(query, alpha=alpha)

        mode = getattr(self, "_retrieval_mode", "hybrid")
        if mode == "none":
            return []
        if mode == "bm25":
            return self.keyword_search(query)
        if mode == "dense":
            return self.search_threat_intel(query, top_k=20)

        vec_results = self.search_threat_intel(query, top_k=20)
        kw_results = self.keyword_search(query)

        # Reciprocal-rank fusion (RRF): rank-based, so the incomparable
        # cosine-similarity and BM25 score scales never need normalising.
        # min-max normalisation of unbounded BM25 scores against dense
        # cosine scores systematically starved the exact-match evidence.
        k = 60
        merged: dict[str, dict[str, Any]] = {}
        for rank, r in enumerate(kw_results[:50]):
            doc_id = r.get("doc_id", r.get("id", ""))
            merged[doc_id] = {**r, "hybrid_score": (1 - alpha) / (k + rank + 1)}
        for rank, r in enumerate(vec_results[:20]):
            doc_id = r.get("doc_id", r.get("id", ""))
            if doc_id in merged:
                merged[doc_id]["hybrid_score"] += alpha / (k + rank + 1)
            else:
                merged[doc_id] = {**r, "hybrid_score": alpha / (k + rank + 1)}

        ranked = sorted(merged.values(), key=lambda x: x.get("hybrid_score", 0), reverse=True)
        return ranked

    def _build_index(self, docs: list[dict[str, Any]]) -> None:
        """Build BM25 inverted index from docs.

        Maintains full Okapi-BM25 statistics (term frequencies, document
        lengths, document frequencies) plus a separate title field so
        keyword_search() can rank with IDF and title evidence instead of
        raw shared-term counts, which let common corpus terms swamp rare
        technique identifiers.
        """
        self._bm25_index.clear()
        self._doc_store.clear()
        self._bm25_tf.clear()
        self._bm25_doclen.clear()
        title_counts: dict[str, int] = {}
        for doc in docs:
            doc_id = doc.get("doc_id", doc.get("id", ""))
            if not doc_id:
                continue
            self._doc_store[doc_id] = doc
            text = doc.get("text", doc.get("content", doc.get("title", "")))
            terms = _tokenize(text.lower())
            self._bm25_doclen[doc_id] = len(terms)
            tf: dict[str, int] = {}
            for term in terms:
                tf[term] = tf.get(term, 0) + 1
            self._bm25_tf[doc_id] = tf
            for term in tf:
                self._bm25_index.setdefault(term, []).append(doc_id)
            title_terms = set(_tokenize(doc.get("title", "").lower()))
            for term in title_terms:
                title_counts[term] = title_counts.get(term, 0) + 1
        self._avg_doclen = sum(self._bm25_doclen.values()) / len(self._bm25_doclen) if self._bm25_doclen else 0.0
        self._title_df = title_counts

    # ------------------------------------------------------------------
    # LLM report generation
    # ------------------------------------------------------------------

    def generate_report(self, analysis: ThreatAnalysis) -> str:
        """Generate a human-readable threat report via the LLM Gateway.

        Grounds the report in the intel documents retrieved during analyze()
        when available, so the retrieved context actually reaches the LLM.
        """
        system_prompt = (
            "You are a cybersecurity threat intelligence analyst. "
            "Write a concise threat analysis report based on the provided data. "
            "Include: threat summary, MITRE ATT&CK mapping, threat actor attribution, "
            "IOCs, and recommended countermeasures. Be factual — cite document sources."
        )

        context_parts = [
            f"Classification: {analysis.classification.value}",
            f"Severity: {analysis.severity.value}",
            f"Confidence: {analysis.confidence:.0%}",
            f"Sophistication: {analysis.sophistication_score:.0%}",
            "",
            "MITRE Tactics:",
        ]
        for t in analysis.tactics:
            context_parts.append(f"  - {t.tactic_id} ({t.tactic_name}) conf={t.confidence:.0%}")

        if analysis.threat_actors:
            context_parts.append("")
            context_parts.append("Suspected Threat Actors:")
            for a in analysis.threat_actors:
                context_parts.append(f"  - {a.name} (conf={a.confidence:.0%})")

        if analysis.iocs:
            context_parts.append("")
            context_parts.append("IOCs:")
            for ioc in analysis.iocs[:20]:
                context_parts.append(f"  - [{ioc.type.value}] {ioc.value}")

        intel_context = getattr(self, "_last_intel_context", "")
        if intel_context:
            context_parts.append("")
            context_parts.append("Retrieved threat-intelligence documents:")
            context_parts.append(intel_context)
            context_parts.append("")
            context_parts.append("Cite the [document titles] above where they support your claims.")

        request = GatewayRequest(
            model=self._model,
            messages=[
                GatewayMessage(role="system", content=system_prompt),
                GatewayMessage(role="user", content="\n".join(context_parts)),
            ],
            # Explicit: the pydantic defaults (0.3 / 2048), stated here so
            # the generation parameters of the CTI-augmented call are
            # visible at the call site.
            temperature=0.3,
            max_tokens=2048,
        )

        return self._call_gateway(request)

    def _call_gateway(self, request: GatewayRequest) -> str:
        """Call the LLM Gateway via shared GatewayClient.

        Applies: PII redaction, circuit breaker, budget enforcement,
        prompt token limiting, cost tracking on response.
        """
        if not self._cost_tracker.check_budget("don"):
            logger.warning("Don budget exhausted — refusing LLM call")
            return "[Budget exhausted — report generation skipped]"

        if not self._circuit_breaker.allow():
            logger.warning("Don circuit breaker open — skipping LLM call")
            return "[Gateway circuit breaker open — report generation deferred]"

        messages = [{"role": m.role, "content": _redact_pii(m.content)} for m in request.messages]

        full_prompt = "\n".join(m["content"] for m in messages)
        if not self._prompt_limiter.check(full_prompt):
            messages[-1]["content"] = self._prompt_limiter.truncate(full_prompt)
            logger.warning("Don prompt truncated to fit token budget")

        try:
            content, usage = self._gateway.generate(
                messages=messages,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            self._circuit_breaker.record_success()

            if usage:
                cost = self._cost_tracker.record("don", self._model, usage)
                if cost > 0:
                    logger.info("Don LLM cost: $%.6f", cost)

            return content
        except requests.RequestException as exc:
            self._circuit_breaker.record_failure()
            logger.error("Gateway call failed: %s", exc)
            return f"[Report generation failed: {exc}]"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_query(self, req: AnalysisRequest) -> str:
        parts = [
            req.classification.value,
            " ".join(req.features.get("observed_techniques", [])),
            " ".join(str(c) for c in req.features.get("commands", [])[:5]),
        ]
        return " ".join(parts).strip()

    def _build_context(self, hits: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        for h in hits[:10]:
            title = h.get("title", h.get("doc_id", ""))
            content = h.get("content", h.get("text", ""))
            parts.append(f"[{title}] {content[:500]}")
        return "\n---\n".join(parts)

    def _hit_to_intel_doc(self, hit: dict[str, Any]) -> Any:
        from .models import IntelDocument

        return IntelDocument(
            doc_id=hit.get("doc_id", hit.get("id", "")),
            title=hit.get("title", "Unknown"),
            content=hit.get("content", hit.get("text", ""))[:2000],
            source=hit.get("source", ""),
            score=hit.get("hybrid_score", hit.get("score", 0.0)),
            metadata={key: hit[key] for key in ("source_version", "license_or_permissions", "provenance_hash", "command_patterns", "behavior_tags", "techniques", "relevance_grade") if key in hit},
        )

    def _derive_severity(self, classification: str, confidence: float, sophistication: float) -> SeverityLevel:
        if classification == "malicious":
            if confidence > 0.8 and sophistication > 0.6:
                return SeverityLevel.CRITICAL
            if confidence > 0.6:
                return SeverityLevel.HIGH
            return SeverityLevel.MEDIUM
        if classification == "suspicious":
            if confidence > 0.7 and sophistication > 0.5:
                return SeverityLevel.HIGH
            return SeverityLevel.MEDIUM
        return SeverityLevel.INFO


def _make_id(session_id: str) -> str:
    ts = str(time.time_ns())
    raw = f"{session_id}:{ts}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
