#!/usr/bin/env python3
"""Full-corpus RAG benchmark: legacy single-shot vs LangGraph graph (LLM mode).

Corpus: the ~22k LightRAG benchmark documents (ATT&CK-derived, the
artifact's real retrieval corpus) loaded into ThreatRAGEngine's
VectorStore + BM25 index.

Engine LLM: the user's Azure OpenAI resource (deployment
``qwen--qwen38-27b``, a *reasoning* model) via GatewayClient's OpenAI
compatibility (gateway_url={endpoint}/openai), so the graph's
decompose/grade/rewrite nodes run their real LLM paths behind the same
safety guards as production.  Token budgets are raised for the panel
because reasoning models burn completion tokens before answering.

Panel: the Azure judge always runs (single deployment on the resource);
OpenRouter free judges are added best-effort when a key is staged and
quota allows — inter-judge Cohen's kappa is reported only when >= 2
judges produced enough overlapping scores, otherwise the panel is
labelled single-rater.

Outputs: results/model_quality/fullcorpus_graph_benchmark.json
"""

from __future__ import annotations

import json
import os
import re
import statistics
import sys
import time
from collections import Counter
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Load keys/endpoints from .env (allowlist; never printed) ────────────────
_ENV = Path(__file__).resolve().parent.parent / ".env"
_ALLOWED = (
    "OPENROUTER_API_KEY", "AZURE_OPENAI_KEY", "AZURE_OPENAI_ENDPOINT",
    "RAGIN_LLM_API_KEY", "RAGIN_LLM_BASE_URL",
)
if _ENV.exists():
    for _line in _ENV.read_text().splitlines():
        _line = _line.strip()
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            if _k.strip() in _ALLOWED:
                os.environ.setdefault(_k.strip(), _v.strip())

# ── Provider resolution (before ragin imports: engine model is read at
#    import time from RAGIN_DON_MODEL) ───────────────────────────────────────
_HAS_APMIX = bool(os.environ.get("RAGIN_LLM_API_KEY"))
_HAS_AZURE = bool(os.environ.get("AZURE_OPENAI_KEY"))
PROVIDER = os.environ.get(
    "BENCH_PROVIDER",
    "apmix" if _HAS_APMIX else ("azure" if _HAS_AZURE else "openrouter"),
)
if PROVIDER == "apmix":
    GATEWAY_URL = os.environ.get("RAGIN_LLM_BASE_URL", "https://api.apmix.ai/v1").rstrip("/")
    API_KEY = os.environ["RAGIN_LLM_API_KEY"]
    if not API_KEY:
        sys.exit("apmix provider: RAGIN_LLM_API_KEY not staged (project .env)")
    ENGINE_MODEL = os.environ.get("BENCH_ENGINE_MODEL", "glm-5.3-flash-free")
    JUDGE_MAX_TOKENS = 512  # reasoning model: leaves room for COT before the answer
elif PROVIDER == "azure":
    AZ_KEY = os.environ.get("AZURE_OPENAI_KEY", "")
    AZ_EP = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    if not (AZ_KEY and AZ_EP):
        sys.exit("azure provider: AZURE_OPENAI_KEY / AZURE_OPENAI_ENDPOINT not staged (project .env)")
    GATEWAY_URL = f"{AZ_EP}/openai"  # GatewayClient appends /v1/chat/completions
    API_KEY = AZ_KEY
    ENGINE_MODEL = os.environ.get("BENCH_ENGINE_MODEL", "qwen--qwen38-27b")
    JUDGE_MAX_TOKENS = 512  # reasoning model: leaves room for COT before the answer
else:
    GATEWAY_URL = "https://openrouter.ai/api"
    API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
    if not API_KEY:
        sys.exit("openrouter provider: OPENROUTER_API_KEY not staged (project .env)")
    ENGINE_MODEL = os.environ.get("BENCH_ENGINE_MODEL", "nex-agi/nex-n2.5-pro:free")
    JUDGE_MAX_TOKENS = 8

# Engine (graph LLM nodes) must use the same deployment.
os.environ["RAGIN_DON_MODEL"] = ENGINE_MODEL

from ragin.don.graph import DonRAGGraph  # noqa: E402
from ragin.don.rag_engine import ThreatRAGEngine  # noqa: E402
from ragin.gateway.client import GatewayClient  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "results" / "model_quality"

# Best-effort OpenRouter free judges (skipped silently on quota/transport
# failure — the Azure judge keeps the panel alive either way).
OPENROUTER_JUDGES = [
    os.environ.get("BENCH_JUDGE1", "nvidia/nemotron-3-super-120b-a12b:free"),
    os.environ.get("BENCH_JUDGE2", "poolside/laguna-s-2.1:free"),
    os.environ.get("BENCH_JUDGE3", "inclusionai/ling-3.0-flash-vl:free"),
]
PANEL_MAX_QUERIES = int(os.environ.get("BENCH_PANEL_QUERIES", "5"))

RUBRIC = (
    "Rate 1-5 how well the CONTEXT grounds the ANALYSIS. 1=no relevant intel; "
    "2=tangential only; 3=general domain support; 4=directly relevant techniques/"
    "actors cited; 5=directly relevant + actionable detail (procedures, tooling, "
    "mitigations). Answer with ONLY the integer."
)

# 10 analysis queries derived from real campaign/session patterns in the repo.
# Each names the ATT&CK topic its relevant docs must match (substring on title).
QUERIES: list[dict] = [
    {"q": "scheduled task persistence via crontab and systemd timers", "must": ["Scheduled Task"]},
    {"q": "credential dumping from LSASS with mimikatz", "must": ["LSASS", "Credential"]},
    {"q": "ssh brute force password spraying against exposed services", "must": ["Brute Force", "Password"]},
    {"q": "lateral movement via SMB and remote services", "must": ["SMB", "Lateral"]},
    {"q": "reverse shell payload delivery and execution", "must": ["Command", "Execution"]},
    {"q": "network service scanning and port discovery", "must": ["Network Service", "Discovery"]},
    {"q": "web shell deployment on internet-facing servers", "must": ["Web Shell", "Server"]},
    {"q": "data exfiltration over encrypted channels", "must": ["Exfiltration"]},
    {"q": "defense evasion via file deletion and log clearing", "must": ["Indicator Removal", "Defense"]},
    {"q": "exploitation of public-facing application vulnerabilities", "must": ["Exploit Public-Facing"]},
]


def load_corpus(engine: ThreatRAGEngine) -> int:
    """Load the LightRAG benchmark docs into the engine's stores.

    The vector index is persisted under data/vector_store_bench, so only
    the first run pays the ~20k-document embedding cost.
    """
    docs_path = REPO / "data" / "benchmark_lightrag" / "kv_store_full_docs.json"
    store_path = REPO / "data" / "vector_store_bench"
    if (store_path / "index.faiss").exists() and (store_path / "documents.json").exists():
        engine._vector_store.load(str(store_path))
        n = engine._vector_store.document_count
        if n >= 20_000:
            print(f"vector store reloaded from disk ({n} docs) — skipping embedding", flush=True)
            # BM25/doc store are rebuilt cheaply from the same source.
            raw = json.loads(docs_path.read_text())
            docs = []
            for i, (_doc_id, v) in enumerate(raw.items()):
                content = (v.get("content") or "").strip()
                if len(content) < 60:
                    continue
                title = content.split("\n")[0][:100].replace("*", "").strip() or f"attck-doc-{i}"
                docs.append({
                    "doc_id": f"lightrag-{i:05d}",
                    "title": title,
                    "content": content[:1500],
                    "source": v.get("file_path", "benchmark_lightrag"),
                })
            engine._build_index(docs)
            return n
        print(f"persisted store looks wrong ({n} docs) — rebuilding", flush=True)
    raw = json.loads(docs_path.read_text())
    docs = []
    for i, (_doc_id, v) in enumerate(raw.items()):
        content = (v.get("content") or "").strip()
        if len(content) < 60:
            continue
        title = content.split("\n")[0][:100].replace("*", "").strip() or f"attck-doc-{i}"
        docs.append({
            "doc_id": f"lightrag-{i:05d}",
            "title": title,
            "content": content[:1500],
            "source": v.get("file_path", "benchmark_lightrag"),
        })
    engine._build_index(docs)          # BM25 + doc store
    engine._vector_store.add_documents(docs)
    engine._vector_store.save(str(store_path))
    return len(docs)


def legacy_context(engine: ThreatRAGEngine, query: str) -> tuple[str, float, int]:
    t0 = time.perf_counter()
    hits = engine.hybrid_search(query, alpha=0.7)
    ctx = engine._build_context(hits)
    return ctx, (time.perf_counter() - t0) * 1000, len(hits)


def graph_context(graph: DonRAGGraph, query: str) -> tuple[str, float, int, dict, list[str], list[str]]:
    """Run the graph once and return everything the benchmark needs from it
    (single invocation — LLM mode is too expensive to invoke twice per query)."""
    t0 = time.perf_counter()
    res = graph.invoke(query)
    ms = (time.perf_counter() - t0) * 1000
    meta = {
        "sub_queries": res.sub_queries,
        "rounds": res.rounds,
        "degraded": res.degraded,
        "n_relevant": len(res.relevant_docs),
        "n_candidates": res.trace[1].get("n_docs") if len(res.trace) > 1 else None,
    }
    titles = [d.get("title", "") for d in res.relevant_docs]
    contents = [d.get("content", d.get("text", ""))[:300] for d in res.relevant_docs]
    return res.context, ms, len(res.relevant_docs), meta, titles, contents


def precision_at_k(titles: list[str], must: list[str], k: int = 5, contents: list[str] | None = None) -> float:
    """P@k over doc titles, with a per-doc fallback to the retrieval text.

    A large slice of the corpus consists of ATT&CK-derived docs whose first
    line (and hence stored title) is anonymized ("attck-doc-NNNNN"), so
    title-only matching systematically under-credits relevant documents.
    When no title term matches, the doc's content[:300] is consulted —
    this measures what the engine actually retrieved, not what the corpus
    titling convention happened to preserve.
    """
    if not titles:
        return 0.0
    contents = contents or [""] * len(titles)

    def _match(title: str, content: str) -> bool:
        t = title.lower()
        c = content.lower()
        return any(m.lower() in t or m.lower() in c for m in must)

    hits = sum(1 for title, content in zip(titles[:k], contents[:k], strict=False) if _match(title, content))
    return hits / k


def call_model(client: GatewayClient, model: str, system: str, user: str,
               max_tokens: int | None = None) -> str | None:
    try:
        content, _ = client.generate(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            model=model, temperature=0.0,
            max_tokens=max_tokens if max_tokens is not None else JUDGE_MAX_TOKENS,
        )
        return content or None
    except Exception:
        return None


def panel_score(clients: list[tuple[GatewayClient, str, int | None]], query: str,
                context: str) -> dict:
    """Grade one context with every available judge.

    clients: list of (GatewayClient, model, max_tokens or None-for-default).
    """
    scores: dict[str, int | None] = {}
    for client, judge, mt in clients:
        out = call_model(client, judge, RUBRIC,
                         f"ANALYSIS: {query}\n\nCONTEXT:\n{context[:6000]}", max_tokens=mt)
        if out:
            m = re.search(r"[1-5]", out)
            scores[judge] = int(m.group()) if m else None
        else:
            scores[judge] = None
    valid = [v for v in scores.values() if v is not None]
    return {"per_judge": scores, "mean": round(statistics.mean(valid), 2) if valid else None}


def cohens_kappa(a: list, b: list) -> float | None:
    pairs = [(x, y) for x, y in zip(a, b, strict=False) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    xa, xb = zip(*pairs, strict=True)
    n = len(pairs)
    po = sum(1 for x, y in pairs if x == y) / n
    ca, cb = Counter(xa), Counter(xb)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return round((po - pe) / (1 - pe), 3) if pe < 1 else 1.0


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    print(f"provider={PROVIDER} gateway={GATEWAY_URL} engine_model={ENGINE_MODEL}", flush=True)
    client = GatewayClient(gateway_url=GATEWAY_URL, api_key=API_KEY, timeout=180.0,
                           default_model=ENGINE_MODEL)

    engine = ThreatRAGEngine(
        gateway_url=GATEWAY_URL,
        api_key=API_KEY,
        vector_store_path=str(REPO / "data" / "vector_store_bench"),
    )
    n_docs = load_corpus(engine)
    print(f"corpus loaded: {n_docs} docs (BM25 + vector)", flush=True)

    graph = DonRAGGraph(engine)

    # Judges: Azure deployment always; OpenRouter free models best-effort.
    judges: list[tuple[GatewayClient, str, int | None]] = [(client, ENGINE_MODEL, JUDGE_MAX_TOKENS)]
    if PROVIDER == "azure" and os.environ.get("OPENROUTER_API_KEY"):
        or_client = GatewayClient(gateway_url="https://openrouter.ai/api",
                                  api_key=os.environ["OPENROUTER_API_KEY"], timeout=120.0)
        judges.extend((or_client, jm, 8) for jm in OPENROUTER_JUDGES)

    rows = []
    contexts: dict[str, dict[str, str]] = {}
    for item in QUERIES:
        q = item["q"]
        print(f"\n== {q}", flush=True)
        l_ctx, l_ms, l_n = legacy_context(engine, q)
        g_ctx, g_ms, g_n, g_meta, g_titles, g_contents = graph_context(graph, q)
        contexts[q] = {"legacy": l_ctx, "graph": g_ctx}
        print(f"   legacy: {l_n} hits, {l_ms:.0f}ms, ctx {len(l_ctx)}B", flush=True)
        print(f"   graph:  {g_n} relevant, {g_ms:.0f}ms, ctx {len(g_ctx)}B, "
              f"subQ={g_meta['sub_queries']} rounds={g_meta['rounds']} degraded={g_meta['degraded']}",
              flush=True)
        l_hits = engine.hybrid_search(q, alpha=0.7)
        l_titles = [h.get("title", "") for h in l_hits]
        l_contents = [h.get("content", h.get("text", ""))[:300] for h in l_hits]
        p_l = precision_at_k(l_titles, item["must"], contents=l_contents)
        p_g = precision_at_k(g_titles, item["must"], contents=g_contents)
        print(f"   P@5: legacy={p_l:.2f} graph={p_g:.2f}", flush=True)
        rows.append({
            "query": q, "must": item["must"],
            "legacy": {"ctx_bytes": len(l_ctx), "latency_ms": round(l_ms), "n_hits": l_n, "p_at_5": p_l,
                       "top_titles": l_titles[:5]},
            "graph": {"ctx_bytes": len(g_ctx), "latency_ms": round(g_ms), "n_relevant": g_n,
                      "p_at_5": p_g, "top_titles": g_titles[:5], **g_meta},
        })

    # Panel grading on the first PANEL_MAX_QUERIES queries, reusing contexts.
    panel_rows = rows[:PANEL_MAX_QUERIES]
    print(f"\n== LLM panel grading ({len(judges)} judges, {len(panel_rows)} queries) ==", flush=True)
    for row in panel_rows:
        q = row["query"]
        l_scores = panel_score(judges, q, contexts[q]["legacy"])
        g_scores = panel_score(judges, q, contexts[q]["graph"])
        row["panel"] = {"legacy": l_scores, "graph": g_scores}
        print(f"   {q[:44]:<46} legacy={l_scores['mean']}  graph={g_scores['mean']}", flush=True)

    # Judge agreement (only meaningful with >= 2 judges producing scores).
    kappas: dict[str, float] = {}
    n_judges = len(judges)
    for ja, jb in combinations(range(n_judges), 2):
        ka = [r["panel"]["legacy"]["per_judge"].get(judges[ja][1]) for r in panel_rows]
        kb = [r["panel"]["legacy"]["per_judge"].get(judges[jb][1]) for r in panel_rows]
        k = cohens_kappa(ka, kb)
        if k is not None:
            kappas[f"judge{ja}_judge{jb}"] = k
    panel_type = "multi-judge" if len(kappas) >= 1 and n_judges >= 2 else "single-rater"

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "corpus": {"docs": n_docs, "source": "data/benchmark_lightrag/kv_store_full_docs.json"},
        "provider": PROVIDER,
        "engine_model": ENGINE_MODEL,
        "panel_models": [j[1] for j in judges],
        "panel_type": panel_type,
        "panel_queries": len(panel_rows),
        "rows": rows,
        "panel_kappa_legacy_arm": kappas,
        "summary": {
            "mean_p5_legacy": round(statistics.mean(r["legacy"]["p_at_5"] for r in rows), 3),
            "mean_p5_graph": round(statistics.mean(r["graph"]["p_at_5"] for r in rows), 3),
            "mean_latency_legacy_ms": round(statistics.mean(r["legacy"]["latency_ms"] for r in rows)),
            "mean_latency_graph_ms": round(statistics.mean(r["graph"]["latency_ms"] for r in rows)),
            "mean_ctx_legacy_bytes": round(statistics.mean(r["legacy"]["ctx_bytes"] for r in rows)),
            "mean_ctx_graph_bytes": round(statistics.mean(r["graph"]["ctx_bytes"] for r in rows)),
            "graph_degraded_runs": sum(1 for r in rows if r["graph"]["degraded"]),
            "graph_total_llm_rounds": sum(r["graph"]["rounds"] for r in rows),
        },
    }
    out = RESULTS / "fullcorpus_graph_benchmark.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\nsummary: {json.dumps(report['summary'], indent=2)}", flush=True)
    print(f"panel: {panel_type} kappa={kappas}", flush=True)
    print(f"saved -> {out.relative_to(REPO)}", flush=True)


if __name__ == "__main__":
    main()
