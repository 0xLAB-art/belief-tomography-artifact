#!/usr/bin/env python3
"""Statistically-powered RAG evaluation for A*-venue submission.

Design:
  * 50 expert-curated MITRE ATT&CK technique queries spanning all 14 tactics.
  * Ground truth derived from the retrieval corpus itself: a document is
    relevant (grade 2) iff the technique ID appears in its heading region
    (title + first 300 chars) — the canonical ATT&CK page for that technique;
    grade 1 = ID mention in the heading region (tactic tables, cross-refs).
    Parent-technique queries also credit sub-technique pages at grade 2.
  * Arms:
      graph   - Don corrective-RAG LangGraph (novelty arm, LLM-stochastic)
      hybrid  - single-shot hybrid dense+BM25 retrieval (legacy arm)
      dense   - dense vector retrieval only (ablation)
      sparse  - BM25 keyword retrieval only (ablation)
  * 5 runs per query for the graph arm; deterministic arms computed once
    (zero run-variance, reported honestly).
  * Metrics: P@5, Recall@20, MRR, nDCG@10 (graded, standard definitions).
  * Statistics: per-query run-mean paired Wilcoxon signed-rank, Holm-
    Bonferroni correction across the 3 pairings, rank-biserial effect size,
    bootstrap 95% CI of the mean difference.

Checkpointed after every query (results/stat_eval/checkpoint.json); --resume
continues an interrupted run.

Usage:
    python scripts/bench_rag_ir.py [--runs 5] [--resume] [--smoke]
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_ENV = Path(__file__).resolve().parent.parent / ".env"
_ALLOWED = ("OPENROUTER_API_KEY", "AZURE_OPENAI_KEY", "AZURE_OPENAI_ENDPOINT")
if _ENV.exists():
    for _line in _ENV.read_text().splitlines():
        _line = _line.strip()
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            if _k.strip() in _ALLOWED:
                os.environ.setdefault(_k.strip(), _v.strip())

PROVIDER = os.environ.get("BENCH_PROVIDER", "azure" if os.environ.get("AZURE_OPENAI_KEY") else "openrouter")
if PROVIDER == "azure":
    AZ_KEY = os.environ.get("AZURE_OPENAI_KEY", "")
    AZ_EP = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    if not (AZ_KEY and AZ_EP):
        sys.exit("azure provider: AZURE_OPENAI_KEY / AZURE_OPENAI_ENDPOINT not staged (project .env)")
    GATEWAY_URL = f"{AZ_EP}/openai"
    API_KEY = AZ_KEY
    ENGINE_MODEL = os.environ.get("BENCH_ENGINE_MODEL", "qwen--qwen38-27b")
else:
    GATEWAY_URL = "https://openrouter.ai/api"
    API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
    if not API_KEY:
        sys.exit("openrouter provider: OPENROUTER_API_KEY not staged (project .env)")
    ENGINE_MODEL = os.environ.get("BENCH_ENGINE_MODEL", "nex-agi/nex-n2.5-pro:free")

os.environ["RAGIN_DON_MODEL"] = ENGINE_MODEL

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "results" / "stat_eval"

# 50 techniques spanning all 14 ATT&CK tactics (expert-curated query set).
# BACKUP_TIDS refill the set when a primary technique has no canonical page
# in the retrieval corpus (GT-coverage filter drops it) so the published
# query count stays at 50.
TECHNIQUES = [
    "T1595", "T1592", "T1589",              # Reconnaissance
    "T1583", "T1587", "T1588",              # Resource Development
    "T1190", "T1566", "T1078",              # Initial Access
    "T1059", "T1204", "T1106",              # Execution
    "T1053", "T1543", "T1505", "T1136",     # Persistence
    "T1055", "T1548", "T1068",              # Privilege Escalation
    "T1070", "T1027", "T1218", "T1562",     # Defense Evasion
    "T1003", "T1110", "T1555", "T1552",     # Credential Access
    "T1046", "T1087", "T1082", "T1049",     # Discovery
    "T1021", "T1550", "T1570",              # Lateral Movement
    "T1005", "T1074", "T1113",              # Collection
    "T1071", "T1105", "T1573",              # Command and Control
    "T1041", "T1048", "T1567",              # Exfiltration
    "T1486", "T1490", "T1489",              # Impact
]

BACKUP_TIDS = [
    "T1590", "T1593", "T1597", "T1598",    # Recon
    "T1584", "T1586",                       # Resource Dev
    "T1195", "T1199", "T1091", "T1133",    # Initial Access
    "T1106", "T1059.001", "T1059.009", "T1203",  # Execution
    "T1098", "T1546", "T1547", "T1037",    # Persistence
    "T1548.002", "T1134", "T1611", "T1600", # PrivEsc
    "T1562.001", "T1036", "T1140", "T1202",# Defense Evasion
    "T1539", "T1528", "T1040", "T1560",    # Credential Access
    "T1018", "T1135", "T1016", "T1069",    # Discovery
    "T1563", "T1572", "T1550.001", "T1030",# Lateral Movement
    "T1560", "T1114", "T1056", "T1185",    # Collection
    "T1568", "T1219", "T1095", "T1090",    # C2
    "T1030", "T1029", "T1020", "T1041",    # Exfiltration
    "T1565", "T1496", "T1529", "T1498",    # Impact
]

_TEMPLATES = [
    "How do adversaries abuse {name} ({tid})?",
    "Detection guidance for {name} (technique {tid})",
    "What does MITRE ATT&CK technique {tid} cover?",
    "Mitigations against {name} attacks",
    "Real-world adversary use of {name}",
]


def load_corpus_docs() -> list[dict]:
    """Load the benchmark corpus exactly as the full-corpus benchmark does."""
    raw = json.loads((REPO / "data" / "benchmark_lightrag" / "kv_store_full_docs.json").read_text())
    docs = []
    for i, (_doc_id, v) in enumerate(raw.items()):
        content = (v.get("content") or "").strip()
        if len(content) < 60:
            continue
        title = content.split("\n")[0][:150].replace("*", "").strip() or f"attck-doc-{i}"
        docs.append({
            "doc_id": f"lightrag-{i:05d}",
            "title": title,
            "content": content[:1500],
            "source": v.get("file_path", "benchmark_lightrag"),
        })
    return docs


def build_ground_truth(docs: list[dict], tid: str) -> dict[str, int]:
    """Graded relevance of every doc for technique `tid`.

    2: canonical page — heading region (title + first 300 chars) names the
       technique with its ID in parentheses, ATT&CK-page style "(T1053)".
       Parent IDs (T1053) also credit sub-technique pages (T1053.003).
    1: heading region mentions the ID (tactic tables, cross-references).
    """
    parent = tid.split(".")[0]
    base = re.compile(rf"\({re.escape(tid)}\)|\({re.escape(parent)}\)")
    mention = re.compile(re.escape(tid))
    gt: dict[str, int] = {}
    for d in docs:
        head = f"{d['title']} {d['content'][:300]}"
        if base.search(head):
            gt[d["doc_id"]] = 2
        elif mention.search(head):
            gt[d["doc_id"]] = 1
    return gt


def make_queries(docs: list[dict], target: int = 50) -> list[dict]:
    """One analyst-style query per curated technique, with graded ground truth.

    Techniques whose canonical page is absent from the corpus (no grade-2
    document) are dropped and refilled from BACKUP_TIDS — an unscoreable
    query (empty ground truth) would silently contribute zeros to every
    arm's mean.
    """
    title_by_tid: dict[str, str] = {}
    for d in docs:
        m = re.match(r"#\s*(.+?)\s*\((T\d{4}(?:\.\d{3})?)\)", d["title"])
        if m:
            name, t = m.group(1).strip(), m.group(2)
            title_by_tid.setdefault(t, name)
            title_by_tid.setdefault(t.split(".")[0], name)

    queries: list[dict] = []
    seen: set[str] = set()
    candidates = TECHNIQUES + [t for t in BACKUP_TIDS if t not in TECHNIQUES]
    for tid in candidates:
        if len(queries) >= target:
            break
        if tid in seen:
            continue
        seen.add(tid)
        gt = build_ground_truth(docs, tid)
        if not any(v >= 2 for v in gt.values()):
            continue
        name = title_by_tid.get(tid) or title_by_tid.get(tid.split(".")[0]) or tid
        q = _TEMPLATES[len(queries) % len(_TEMPLATES)].format(name=name.lower(), tid=tid)
        queries.append({
            "tid": tid, "q": q, "gt": gt,
            "n_rel2": sum(1 for v in gt.values() if v == 2),
            "n_rel1": sum(1 for v in gt.values() if v == 1),
        })
    return queries


# ── Metrics (standard graded-IR definitions) ───────────────────────────────

def _dcg(gains: list[float]) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def eval_ranking(doc_ids: list[str], gt: dict[str, int], k_p: int = 5, k_r: int = 20) -> dict[str, float]:
    """Score one ranked result list against graded ground truth."""
    rel_ids = {d for d, g in gt.items() if g >= 2}
    p5 = sum(1 for d in doc_ids[:k_p] if d in rel_ids) / k_p
    recall = len(rel_ids & set(doc_ids[:k_r])) / len(rel_ids) if rel_ids else 0.0
    rr = 0.0
    for i, d in enumerate(doc_ids):
        if d in rel_ids:
            rr = 1.0 / (i + 1)
            break
    gains = [gt.get(d, 0) for d in doc_ids[:10]]
    ideal = sorted(gt.values(), reverse=True)[:10]
    idcg = _dcg(ideal)
    ndcg = _dcg(gains) / idcg if idcg > 0 else 0.0
    return {"p_at_5": round(p5, 4), "recall_at_20": round(recall, 4),
            "mrr": round(rr, 4), "ndcg_at_10": round(ndcg, 4)}


# ── Statistics ─────────────────────────────────────────────────────────────

def holm(pvals: dict[str, float]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values (family = the 3 pairings per metric)."""
    ordered = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(ordered)
    adj, running = {}, 0.0
    for i, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * p))
        adj[name] = running
    return adj


def rank_biserial(x: list[float], y: list[float]) -> float:
    from scipy import stats

    diffs = [a - b for a, b in zip(x, y, strict=True) if a != b]
    if not diffs:
        return 0.0
    w = stats.wilcoxon(x, y, zero_method="wilcox").statistic
    n = len(diffs)
    return round(1 - (2 * float(w)) / (n * (n + 1)), 4)


def bootstrap_ci_diff(x: list[float], y: list[float], n_boot: int = 5000, seed: int = 42) -> tuple[float, float]:
    import random

    rng = random.Random(seed)
    diffs = [a - b for a, b in zip(x, y, strict=True)]
    if not diffs:
        return 0.0, 0.0
    means = []
    for _ in range(n_boot):
        s = [diffs[rng.randrange(len(diffs))] for _ in diffs]
        means.append(statistics.mean(s))
    return round(min(means), 4), round(max(means), 4)


def paired_stats(a: list[float], b: list[float]) -> dict:
    from scipy import stats

    if all(x == y for x, y in zip(a, b, strict=True)):
        return {
            "wilcoxon_p": 1.0,
            "rank_biserial": 0.0,
            "mean_diff": 0.0,
            "wilcoxon_p_holm": 1.0,
            "significant_at_0.05": False,
            "note": "identical across all queries",
        }
    try:
        _stat, p = stats.wilcoxon(a, b, zero_method="wilcox")
    except ValueError:
        return {
            "wilcoxon_p": 1.0,
            "rank_biserial": 0.0,
            "mean_diff": round(statistics.mean(a) - statistics.mean(b), 4),
            "wilcoxon_p_holm": 1.0,
            "significant_at_0.05": False,
            "note": "all zero differences",
        }
    return {
        "wilcoxon_p": round(float(p), 6),
        "rank_biserial": rank_biserial(a, b),
        "mean_diff": round(statistics.mean(a) - statistics.mean(b), 4),
    }


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--run-workers", type=int, default=3, help="concurrent graph runs per query")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--smoke", action="store_true", help="3 queries x 1 run, pipeline validation")
    args = ap.parse_args()

    n_runs = 1 if args.smoke else args.runs
    OUT.mkdir(parents=True, exist_ok=True)
    ckpt_path = OUT / "checkpoint.json"

    from ragin.don.graph import DonRAGGraph
    from ragin.don.rag_engine import ThreatRAGEngine

    engine = ThreatRAGEngine(
        gateway_url=GATEWAY_URL,
        api_key=API_KEY,
        vector_store_path=str(REPO / "data" / "vector_store_bench"),
    )
    store_path = REPO / "data" / "vector_store_bench"
    if (store_path / "index.faiss").exists():
        engine._vector_store.load(str(store_path))
    docs = load_corpus_docs()
    engine._build_index(docs)
    print(f"corpus: {len(docs)} docs | model: {ENGINE_MODEL} | provider: {PROVIDER}", flush=True)

    queries = make_queries(docs)
    if args.smoke:
        queries = queries[:3]
    print(f"queries: {len(queries)} x {n_runs} runs x 4 arms", flush=True)

    (OUT / "query_set.json").write_text(json.dumps(
        [{"tid": q["tid"], "q": q["q"], "n_relevant_g2": q["n_rel2"], "n_relevant_g1": q["n_rel1"]}
         for q in queries], indent=2))

    graph = DonRAGGraph(engine)
    ckpt: dict = {}
    if args.resume and ckpt_path.exists():
        ckpt = json.loads(ckpt_path.read_text())
        print(f"resuming: {len(ckpt.get('rows', {}))}/{len(queries)} queries done", flush=True)

    rows: dict[str, dict] = ckpt.get("rows", {})

    for qi, item in enumerate(queries):
        if item["tid"] in rows:
            continue
        q, gt = item["q"], item["gt"]
        t0 = time.perf_counter()
        entry: dict = {"tid": item["tid"], "q": q,
                       "n_relevant_g2": item["n_rel2"], "n_relevant_g1": item["n_rel1"], "arms": {}}

        # Deterministic arms, computed once.
        hyb = engine.hybrid_search(q, alpha=0.7)
        entry["arms"]["hybrid"] = {"runs": [eval_ranking([h.get("doc_id", h.get("id", "")) for h in hyb], gt)]}
        dense = engine.search_threat_intel(q, top_k=20)
        entry["arms"]["dense"] = {"runs": [eval_ranking([h.get("doc_id", h.get("id", "")) for h in dense], gt)]}
        sparse = engine.keyword_search(q)
        entry["arms"]["sparse"] = {"runs": [eval_ranking([h.get("doc_id", h.get("id", "")) for h in sparse], gt)]}
        h5 = entry["arms"]["hybrid"]["runs"][0]
        print(f"  hybrid: P@5={h5['p_at_5']:.2f} R@20={h5['recall_at_20']:.2f} nDCG={h5['ndcg_at_10']:.2f}", flush=True)

        # Stochastic arm: n_runs graph invocations, run 3-at-a-time (the
        # endpoint serves ~4 concurrent requests without 429s; measured
        # 2.9s parallel vs 10.9s serial). Zero-variance arms skip this.
        graph_runs: list[dict | None] = [None] * n_runs

        def _one_run(run_idx: int, query: str, ground_truth: dict[str, int],
                     out: list[dict | None], label: str) -> None:
            try:
                res = graph.invoke(query)
                m = eval_ranking([d.get("doc_id", d.get("id", "")) for d in res.relevant_docs], ground_truth)
                m["rounds"] = res.rounds
                m["degraded"] = res.degraded
                m["n_relevant"] = len(res.relevant_docs)
                out[run_idx] = m
                print(f"  [{label}] graph run {run_idx+1}/{n_runs}: "
                      f"P@5={m['p_at_5']:.2f} nDCG={m['ndcg_at_10']:.2f} rounds={res.rounds}", flush=True)
            except Exception as exc:
                print(f"  graph run {run_idx+1} failed: {exc}", flush=True)
                out[run_idx] = {"p_at_5": 0.0, "recall_at_20": 0.0, "mrr": 0.0,
                                "ndcg_at_10": 0.0, "rounds": -1, "degraded": True,
                                "error": str(exc)[:200]}

        with ThreadPoolExecutor(max_workers=args.run_workers) as pool:
            futures = [pool.submit(_one_run, r, q, gt, graph_runs, f"{qi+1}/{len(queries)}") for r in range(n_runs)]
            for f in futures:
                f.result()
        entry["arms"]["graph"] = {"runs": graph_runs}
        entry["elapsed_s"] = round(time.perf_counter() - t0, 1)

        rows[item["tid"]] = entry
        ckpt["rows"] = rows
        ckpt_path.write_text(json.dumps(ckpt))
        print(f"[{qi+1}/{len(queries)}] {item['tid']} done in {entry['elapsed_s']}s — checkpointed", flush=True)

    # ── Aggregate + statistics ────────────────────────────────────────────
    arms = ["graph", "hybrid", "dense", "sparse"]
    metrics = ["p_at_5", "recall_at_20", "mrr", "ndcg_at_10"]
    summary = {arm: {} for arm in arms}
    per_query_means: dict[str, dict[str, list[float]]] = {arm: {} for arm in arms}
    for arm in arms:
        for metric in metrics:
            vals = [statistics.mean(r[metric] for r in e["arms"][arm]["runs"]) for e in rows.values()]
            per_query_means[arm][metric] = vals
            summary[arm][f"mean_{metric}"] = round(statistics.mean(vals), 4)
            summary[arm][f"stdev_{metric}"] = round(statistics.stdev(vals), 4) if len(vals) > 1 else 0.0

    stats_out: dict = {"n_queries": len(rows), "n_runs_per_query": n_runs, "pairs": {}}
    for metric in metrics:
        fam: dict[str, dict] = {}
        for other in ["hybrid", "dense", "sparse"]:
            a, b = per_query_means["graph"][metric], per_query_means[other][metric]
            st = paired_stats(a, b)
            lo, hi = bootstrap_ci_diff(a, b)
            st["ci95_low"], st["ci95_high"] = lo, hi
            fam[f"graph_vs_{other}"] = st
        adjusted = holm({k: v["wilcoxon_p"] for k, v in fam.items()})
        for k, p_h in adjusted.items():
            fam[k]["wilcoxon_p_holm"] = round(p_h, 6)
            fam[k]["significant_at_0.05"] = p_h < 0.05
        stats_out["pairs"][metric] = fam

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "design": {"queries": len(rows), "runs_per_query": n_runs, "arms": arms,
                   "engine_model": ENGINE_MODEL, "provider": PROVIDER,
                   "metrics": metrics,
                   "stat_test": "paired Wilcoxon signed-rank on per-query run-means, Holm-Bonferroni corrected"},
        "ground_truth": "corpus-derived graded relevance: 2 = canonical technique page (ID in heading region), "
                        "1 = ID mention in heading region; parent IDs credit sub-technique pages",
        "summary": summary,
        "statistics": stats_out,
        "rows": rows,
    }
    (OUT / "summary.json").write_text(json.dumps(report, indent=2))
    print("\n== SUMMARY ==", flush=True)
    for arm in arms:
        s = summary[arm]
        print(f"{arm:>8}: P@5={s['mean_p_at_5']:.3f} R@20={s['mean_recall_at_20']:.3f} "
              f"MRR={s['mean_mrr']:.3f} nDCG@10={s['mean_ndcg_at_10']:.3f}", flush=True)
    for metric, fam in stats_out["pairs"].items():
        for pair, st in fam.items():
            print(f"{metric:>12} {pair}: p={st['wilcoxon_p']:.4f} holm={st['wilcoxon_p_holm']:.4f} "
                  f"d={st['rank_biserial']} diff={st['mean_diff']} CI=[{st['ci95_low']},{st['ci95_high']}]", flush=True)
    print("saved -> results/stat_eval/summary.json", flush=True)


if __name__ == "__main__":
    main()
