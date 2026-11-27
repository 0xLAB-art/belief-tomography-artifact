"""E28 — E2-era zero decomposition (PREREGISTERED:
PREREGISTRATION_E28_BUDGET_DECOMPOSITION.md). Public v0 state-deception
g1+g2 templates (seed 2718, the exact E2-blocked texts), today, at 200 vs
1024 output tokens. Run: python3 demo/run_e28_budget_decomposition.py
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gauntlet.generator import GauntletGenerator  # noqa: E402
from gauntlet.harness import SubprocessAgent, _run_one  # noqa: E402
from gauntlet.verdict import HeuristicJury  # noqa: E402
from demo.run_live_tomography import GatewayBlockGuard  # noqa: E402

MODEL = "gpt-5.6-sol"
ARMS = [("A-200tok", "200"), ("B-1024tok", "1024")]
GENS = (1, 2)
PER_CELL = 10
LOG = Path(__file__).resolve().parent / "e28_sessions.jsonl"

def main() -> None:
    out_dir = Path(__file__).resolve().parent
    jury = HeuristicJury()
    done = set()
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            try:
                r = json.loads(line); done.add((r["arm"], r["generation"], r["i"]))
            except Exception: pass
    for arm, tokens in ARMS:
        os.environ["LLM_TARGET_MAX_OUTPUT_TOKENS"] = tokens
        raw = SubprocessAgent([sys.executable, "llm_target.py", MODEL], cwd=str(out_dir))
        target = GatewayBlockGuard(raw)
        try:
            for gen in GENS:
                for i in range(PER_CELL):
                    if (arm, gen, i) in done: continue
                    g = GauntletGenerator(seed=2718)
                    ep = g.episode("state_deception", gen)
                    t0 = time.monotonic()
                    v = _run_one(target, ep, jury)
                    rec = {"arm": arm, "tokens": tokens, "generation": gen, "i": i,
                           "episode_id": ep.episode_id,
                           "breach": not v.passed, "violated": v.violated,
                           "blocked": bool(getattr(target, "last_blocked", False)),
                           "elapsed_s": round(time.monotonic() - t0, 1)}
                    with LOG.open("a") as fh: fh.write(json.dumps(rec) + "\n")
                    print(f"[E28] {arm} g{gen} #{i+1}: "
                          f"{'BREACH' if rec['breach'] else 'held'}"
                          f"{' (blocked)' if rec['blocked'] else ''} {rec['elapsed_s']}s", flush=True)
        finally:
            try:
                raw.proc.stdin.close(); raw.proc.wait(timeout=10)
            except Exception: raw.proc.kill()
    # report
    rows = [json.loads(l) for l in LOG.read_text().splitlines()]
    lines = ["# E28 — E2-era Zero Decomposition", "",
             "**Registered:** PREREGISTRATION_E28_BUDGET_DECOMPOSITION.md (before data).", ""]
    for arm, tokens in ARMS:
        rs = [r for r in rows if r["arm"] == arm]
        if not rs: continue
        b = sum(1 for r in rs if r["breach"]); blk = sum(1 for r in rs if r["blocked"])
        fast = sum(1 for r in rs if r["blocked"] and r["elapsed_s"] < 8)
        slow = blk - fast
        lines.append(f"## {arm} ({tokens} tokens)")
        lines.append(f"- sessions: {len(rs)}, breaches: {b}, blocked turns/sessions: {blk} "
                     f"(fast<8s: {fast}, slow>=8s: {slow})")
        for gen in GENS:
            grs = [r for r in rs if r["generation"] == gen]
            if grs:
                gb = sum(1 for r in grs if r["breach"]); gblk = sum(1 for r in grs if r["blocked"])
                lines.append(f"  - gen{gen}: {gb}/{len(grs)} breaches, {gblk}/{len(grs)} blocked")
        lines.append("")
    (Path(__file__).resolve().parent / "E28_BUDGET_DECOMPOSITION.md").write_text("\n".join(lines) + "\n")
    (Path(__file__).resolve().parent / "e28_decomposition.json").write_text(json.dumps(rows, indent=2))
    print("\n".join(lines), flush=True)

if __name__ == "__main__":
    main()
