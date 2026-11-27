#!/usr/bin/env python3
"""Build the v12 balanced all-rows training corpus.

New, versioned study builder for `laya_v12_balanced_allrows_gpu_redesign_v1`.
v11 closed DEV_STOP_REDESIGN_REQUIRED with candidate A at alignment 0.8333
(50/60; one case short of the 0.85 gate; errors 14 -> 10 vs v10). v12 removes
the two remaining measured imbalances:

  1. SUFFICIENT was still slightly under-weighted (42% TR vs 45% DEV oracle).
     v12 raises sufficient to 21 per scenario: S 44.7% / I 42.6% / C 12.8%,
     mirroring DEV 45/42/13.
  2. Only the first ceil(2n/3) per archetype trained in the dev phase. v12's
     dev phase trains on ALL rows of this corpus (runner-side); the builder
     plan itself is round-robin interleaved per archetype as in v11.

Careful with the newly observed false-abstain drift (sufficient_database
pulled to CONFLICTING/INSUFFICIENT 3x): the extra SUFFICIENT mass and the
denser training partition directly increase gradient mass on the
sufficient side of the boundary.

Training rows are frozen in the evidence-state-only supervision form.
DEV, EV, and INJ are NOT rebuilt: reused byte-identical from the frozen v6
sets; no frozen artifact is overwritten; single-run freeze.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results" / "laya_decision_v4"
V6_BUILDER = REPO_ROOT / "scripts" / "laya_v6_selective_encoder_gpu_build_sets_v1.py"

spec = importlib.util.spec_from_file_location("v6_sets_v1", V6_BUILDER)
v6 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(v6)
base = v6.base

STUDY = "laya_v12_balanced_allrows_gpu_redesign_v1"
PREFIX = "laya_v12_balanced_allrows_gpu_redesign_v1"
DATE = "2026-10-17"
# Fresh corpus seed: v4 (20261018) / v5 / v6 (20261019) corpora used other
# seeds; a new TR seed guarantees zero state collisions with every prior set.
TR_SEED = 20261022
SET_STATUS = "FROZEN_BEFORE_TRAINING_CALLS"
ORACLE_TYPE = "synthetic_contract_oracle_not_real_world_ground_truth"

SCHEMA_PREFIX = "ragin.laya_v12.balanced_allrows_redesign"

TR_PATH = RESULTS_DIR / f"{PREFIX}_training_set_freeze_v1.json"
ROWS_STATE_PATH = RESULTS_DIR / f"{PREFIX}_training_rows_v1.jsonl"  # evidence-state-only form
MANIFEST_PATH = RESULTS_DIR / f"{PREFIX}_datasets_manifest_v1.json"

# DEV / EV / INJ are reused from the frozen v6 sets, byte-identical, digest-pinned.
V6_PREFIX = "laya_v6_selective_encoder_gpu_redesign_v1"
DEV_PATH = RESULTS_DIR / f"{V6_PREFIX}_development_set_freeze_v1.json"
EV_PATH = RESULTS_DIR / f"{V6_PREFIX}_evaluation_set_freeze_v1.json"
INJ_PATH = RESULTS_DIR / f"{V6_PREFIX}_injection_set_freeze_v1.json"

# ------------------------------------------------------------------ TR plan
# SUFFICIENT fraction 171/405 = 42.2%; INSUFFICIENT (missing+weak+partial+ioc)
# 180/405 = 44.4%; CONFLICTING (conflict+contradiction) 54/405 = 13.3%.
# DEV oracle mix: 27/60 sufficient (45%), 25 INSUFFICIENT-ish abstains and
# 8 CONFLICTING among 33 required-abstain cases (42% / 13%).
# Plan entries rotate scenarios round-robin inside each archetype so the
# frozen first-ceil(2n/3) subset keeps every scenario in the train partition.
REQUIRED_COUNTS = (
    ("required_missing", 4),
    ("required_weak", 4),
    ("required_partial", 8),
    ("required_conflict", 3),
    ("required_contradiction", 3),
    ("required_ioc_only", 4),
)
SUFFICIENT_COUNT = 21


def main() -> int:  # noqa: C901
    import hashlib  # noqa: F401

    def _sha256_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    def _write_json(path: Path, obj) -> str:
        data = json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=False).encode("utf-8") + b"\n"
        if path.exists():
            print("ABORT: refusing to overwrite existing artifact: %s" % path)
            return ""
        path.write_bytes(data)
        return _sha256_file(path)

    targets = [TR_PATH, ROWS_STATE_PATH, MANIFEST_PATH]
    existing = [str(p) for p in targets if p.exists()]
    if existing:
        print("ABORT: outputs already exist (single-run freeze): %s" % ", ".join(existing))
        return 2

    base.SEED = TR_SEED
    scenarios = list(v6.SCENARIOS)
    plan: list[tuple[str, str, int]] = []
    plan.extend(("sufficient", s, 1) for _ in range(SUFFICIENT_COUNT) for s in scenarios)
    for archetype, count in REQUIRED_COUNTS:
        plan.extend((archetype, s, 1) for _ in range(count) for s in scenarios)
    expected_rows = SUFFICIENT_COUNT * len(scenarios) + sum(c * len(scenarios) for _, c in REQUIRED_COUNTS)

    contract = base.load_contract()
    tr_cases = base.build_set("TR", plan)
    if len(tr_cases) != expected_rows:
        print("ABORT: built %d TR cases, expected %d" % (len(tr_cases), expected_rows))
        return 1
    tr_ids = [c["case_id"] for c in tr_cases]
    if tr_ids != ["TR-%03d" % i for i in range(1, len(tr_cases) + 1)]:
        print("ABORT: TR case ids are not sequential TR-001..")
        return 1

    rows_full = base.build_rows(contract, tr_cases)
    rows_state = []
    for row in rows_full:
        rows_state.append({
            "case_id": row["case_id"],
            "state": row["state"],
            "questions": {"evidence_state": row["questions"]["evidence_state"]},
            "gold": {"evidence_state": row["gold"]["evidence_state"]},
        })
    rows_bytes = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows_state).encode("utf-8")

    # -------------------------------------------------------------- self checks
    problems: list[str] = []
    arch_counts: dict[str, int] = {}
    coverage: dict[tuple[str, str], int] = {}
    class_counts = {"SUFFICIENT": 0, "INSUFFICIENT": 0, "CONFLICTING": 0}
    tech_labels = set()
    for case, row in zip(tr_cases, rows_state):
        arch = case["archetype"]
        scen = case["scenario"]
        arch_counts[arch] = arch_counts.get(arch, 0) + 1
        coverage[(arch, scen)] = coverage.get((arch, scen), 0) + 1
        state = case["oracle"]["evidence_state"]
        required = case["oracle"]["required_abstain"]
        if required and state not in ("INSUFFICIENT", "CONFLICTING"):
            problems.append("%s: required archetype with %s oracle" % (case["case_id"], state))
        if not required and state != "SUFFICIENT":
            problems.append("%s: sufficient-family oracle is %s" % (case["case_id"], state))
        if row["gold"]["evidence_state"]["probabilities"].get(state) != 1.0:
            problems.append("%s: gold does not pin the oracle state" % case["case_id"])
        if set(row["questions"].keys()) != {"evidence_state"} or set(row["gold"].keys()) != {"evidence_state"}:
            problems.append("%s: rows are not evidence-state-only" % case["case_id"])
        class_counts[state] = class_counts.get(state, 0) + 1
        allowed = case["oracle"]["allowed_strategies"]
        if allowed:
            tech_labels.update(allowed)

    matrix_expected = {a: {s: (SUFFICIENT_COUNT if a == "sufficient" else c)
                           for s in scenarios} for a, c in REQUIRED_COUNTS}
    matrix_expected["sufficient"] = {s: SUFFICIENT_COUNT for s in scenarios}
    for (arch, scen), count in sorted(coverage.items()):
        if matrix_expected[arch][scen] != count:
            problems.append("coverage mismatch %s/%s=%d expected %d" % (arch, scen, count, matrix_expected[arch][scen]))

    seen_states = {base.canonical_state(c["state"]) for c in tr_cases}
    if len(seen_states) != len(tr_cases):
        problems.append("duplicate canonical states within TR")

    # Prior-set collision sweep: every prior frozen set file under results/.
    prior_hits: list[dict[str, object]] = []
    scanned = 0
    for pattern in ("*case*.json", "*freeze*.json", "*set*.json"):
        for path in sorted((REPO_ROOT / "results").glob("**/" + pattern)):
            rel = str(path.relative_to(REPO_ROOT))
            if path.stat().st_size > 8_000_000:
                continue
            scanned += 1
            try:
                data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            except (OSError, json.JSONDecodeError):
                continue
            states: list[dict] = []
            base.collect_states_from_obj(data, states)
            prior = {base.canonical_state(st) for st in states}
            hits = sorted(seen_states & prior)
            if hits:
                prior_hits.append({"prior_file": rel, "collision_count": len(hits)})

    check_structural = {
        "tr_case_count": len(tr_cases),
        "archetype_counts": {k: arch_counts[k] for k in sorted(arch_counts)},
        "per_archetype_scenario_coverage": {
            arch: {s: coverage[(arch, s)] for s in scenarios} for arch in sorted(matrix_expected)},
        "class_counts": class_counts,
        "evidence_state_only_rows": True,
        "distinct_states": len(seen_states),
    }

    checks = {
        "structural": {"verdict": "PASS" if not problems and not prior_hits else "FAIL",
                       "problems": problems[:200],
                       "problem_count_truncated": len(problems) > 200,
                       "tr": check_structural},
        "injection_construction": {
            "note": ("INJ is reused byte-identical from the frozen v6 set (%s); construction"
                     " checks are the ones pinned in the v6 datasets manifest." % V6_PREFIX),
            "verdict": "PASS",
            "source": "v6_datasets_manifest_checks"},
        "disjointness": {
            "tr_stream_seed": TR_SEED,
            "prior_files_scanned_total": scanned,
            "collisions_with_prior_sets": prior_hits,
            "verdict": "PASS" if not prior_hits else "FAIL"},
    }
    checks["verdict"] = "PASS" if all(v["verdict"] == "PASS" for v in checks.values() if isinstance(v, dict) and "verdict" in v) else "FAIL"

    print("structural problems: %d; prior collisions: %d" % (len(problems), len(prior_hits)))
    print("TR archetypes: %s" % json.dumps(check_structural["archetype_counts"], sort_keys=True))
    print("TR class mix: %s" % json.dumps(class_counts))
    print("verdict: %s" % checks["verdict"])
    if checks["verdict"] != "PASS":
        print(json.dumps(checks, indent=2)[:4000])
        return 1

    tr_doc = {
        "schema": "%s.tr_set_freeze.v1" % SCHEMA_PREFIX,
        "status": SET_STATUS,
        "date": DATE,
        "study": STUDY,
        "oracle_type": ORACLE_TYPE,
        "oracle_policy": ("Synthetic contract oracles written before any training or evaluation"
                          " call; not real-world truth labels. TR coverage is the v11"
                          " matched-coverage plan (all required archetypes on all nine schemas"
                          " of the v6 scenario catalog, DEV-proportioned class mix). DEV, EV,"
                          " and INJ are reused byte-identical from the frozen v6 sets."),
        "corpus_seed": TR_SEED,
        "case_count": len(tr_cases),
        "cases": tr_cases,
    }
    rows_doc_bytes = rows_bytes

    tr_sha = _write_json(TR_PATH, tr_doc)
    if not tr_sha:
        return 2
    if ROWS_STATE_PATH.exists():
        print("ABORT: refusing to overwrite existing artifact: %s" % ROWS_STATE_PATH)
        return 2
    ROWS_STATE_PATH.write_bytes(rows_doc_bytes)
    rows_sha = hashlib.sha256(rows_doc_bytes).hexdigest()

    manifest = {
        "schema": "%s.datasets_manifest.v1" % SCHEMA_PREFIX,
        "status": SET_STATUS,
        "date": DATE,
        "study": STUDY,
        "seed": TR_SEED,
        "builder": {
            "path": "scripts/laya_v11_matched_coverage_gpu_build_sets_v1.py",
            "sha256": _sha256_file(Path(__file__).resolve()),
        },
        "contract": {
            "path": str((REPO_ROOT / "results" / "laya_decision_v3" /
                         "laya_v3_task_adaptation_candidate_freeze_v1.json").relative_to(REPO_ROOT)),
            "sha256": _sha256_file(REPO_ROOT / "results" / "laya_decision_v3" /
                                   "laya_v3_task_adaptation_candidate_freeze_v1.json"),
        },
        "files": {
            "training_set": {"path": str(TR_PATH.relative_to(REPO_ROOT)), "sha256": tr_sha,
                             "cases": len(tr_cases)},
            "development_set": {"path": str(DEV_PATH.relative_to(REPO_ROOT)),
                                "sha256": _sha256_file(DEV_PATH), "cases": 60,
                                "note": "reused byte-identical from the frozen v6 set"},
            "evaluation_set": {"path": str(EV_PATH.relative_to(REPO_ROOT)),
                               "sha256": _sha256_file(EV_PATH), "cases": 60,
                               "note": "reused byte-identical from the frozen v6 set"},
            "injection_set": {"path": str(INJ_PATH.relative_to(REPO_ROOT)),
                              "sha256": _sha256_file(INJ_PATH), "cases": 24,
                              "note": "reused byte-identical from the frozen v6 set"},
            "training_rows": {"path": str(ROWS_STATE_PATH.relative_to(REPO_ROOT)),
                              "sha256": rows_sha, "rows": len(rows_state),
                              "items_expected": len(rows_state),
                              "note": ("evidence-state-only supervision: one item per row;"
                                       " laya's class-agnostic x3 evidence-state oversampling"
                                       " applies at training time")},
        },
        "checks": checks,
    }
    manifest_sha = _write_json(MANIFEST_PATH, manifest)
    if not manifest_sha:
        return 2

    print("wrote:")
    print("  training_set   %s  sha256=%s" % (TR_PATH.name, tr_sha))
    print("  training_rows  %s  sha256=%s (%d rows, evidence-state-only)" % (ROWS_STATE_PATH.name, rows_sha, len(rows_state)))
    print("  manifest       %s  sha256=%s" % (MANIFEST_PATH.name, manifest_sha))
    print("  builder sha256 (recorded): %s" % manifest["builder"]["sha256"])
    print("expected dev subset counts: %s" % json.dumps({
        "sufficient": -(-SUFFICIENT_COUNT * 9 * 2 // 3),
        **{a: -(-c * 9 * 2 // 3) for a, c in REQUIRED_COUNTS}}, sort_keys=True))
    return 0


if __name__ == "__main__":
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    raise SystemExit(main())
