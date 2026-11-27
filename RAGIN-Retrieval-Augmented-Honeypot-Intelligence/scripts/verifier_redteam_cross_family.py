"""Cross-family live red-team comparison — three author families, post-fix verifier.

Inputs (read-only):
  - results/verifier_redteam_live_space-bunny_rescored_after_fix.json   (space-bunny-free, 89 cases)
  - results/verifier_redteam_live_deepseek-v4-flash-free_rescored_after_fix.json (deepseek-v4-flash-free, 80 cases)
  - results/verifier_redteam_live_llama33_complete.json                 (llama-3.3-70b + opencode fill, 94 cases)

Outputs:
  - results/verifier_redteam_cross_family.json

The comparison reports, per family:
  - full-pool post-fix precision/recall (variant level, valid drafts)
  - the 80-case common subset (every family's key intersection) for an
    apples-to-apples table
  - the authentic pre-fix baseline (stored verdicts) and the recall delta
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.rescore_redteam_family import _tally  # noqa: E402
from scripts.verifier_redteam_live import _wilson  # noqa: E402

FAMILIES = [
    ("space-bunny-free", "results/verifier_redteam_live_space-bunny_rescored_after_fix.json"),
    ("deepseek-v4-flash-free", "results/verifier_redteam_live_deepseek-v4-flash-free_rescored_after_fix.json"),
    ("llama-3.3-70b", "results/verifier_redteam_live_llama33_complete.json"),
]
LADDER = ROOT / "results" / "verifier_llama33_rescored_after_fix.json"
OUT = ROOT / "results" / "verifier_redteam_cross_family.json"


def _pack(t: dict[str, Any]) -> dict[str, Any]:
    return {
        "precision": t["precision"],
        "recall": t["recall"],
        "tp": t["tp"], "fn": t["fn"], "fp": t["fp"], "tn": t["tn"],
        "valid_drafts": t["valid_drafts"],
        "wilson95": {
            "recall": _wilson(t["tp"], t["tp"] + t["fn"]),
            "precision": _wilson(t["tp"], t["tp"] + t["fp"]) if (t["tp"] + t["fp"]) else [1.0, 1.0],
        },
    }


def main() -> int:
    arts: dict[str, dict[str, Any]] = {}
    for name, rel in FAMILIES:
        arts[name] = json.loads((ROOT / rel).read_text())

    keys_per_family = {n: set(a["per_case"]) for n, a in arts.items()}
    common = sorted(set.intersection(*keys_per_family.values()))

    table: dict[str, Any] = {}
    ladder = json.loads(LADDER.read_text())
    for name, rel in FAMILIES:
        a = arts[name]
        per_case = a["per_case"]
        after = _tally(per_case)
        # Authentic pre-fix baseline = stored verdicts of the ORIGINAL run.
        # space-bunny/deepseek carry them in their rescore artifacts; the llama
        # completion rescored everything, so its pre-fix tally lives in the
        # ladder artifact (tallied from llama33_best stored verdicts).
        if name == "llama-3.3-70b":
            before = ladder["before"]
            before_note = "stored pre-fix verdicts (llama33_best; tallied in the ladder artifact)"
        else:
            before = a.get("before_stored_verdicts") or {}
            before_note = "stored pre-fix verdicts"
        common_after = _tally(per_case, set(common))
        entry: dict[str, Any] = {
            "artifact": rel,
            "cases": after["cases"],
            "after_rescored": _pack(after),
            "common80_after": _pack(common_after),
            "common80_cases": len(common),
        }
        if before and before.get("precision") is not None:
            entry["before"] = {
                "precision": before.get("precision"),
                "recall": before.get("recall"),
                "valid_drafts": before.get("valid_drafts"),
                "note": before_note,
            }
            if before.get("recall") is not None and after["recall"] is not None:
                entry["recall_delta"] = round(after["recall"] - before["recall"], 4)
        if name == "llama-3.3-70b":
            entry["llama_only_ablation"] = a.get("rescored_without_fill")
            entry["author_note"] = (
                "full pool includes 48 opencode-filled drafts on 16 cases "
                "(author-swap disclosed in the llama artifact); common-subset "
                "rows include those variants for the keys they cover"
            )
        table[name] = entry

    artifact = {
        "what": "cross-family live red-team comparison — all drafts rescored through the post-P1 verifier",
        "method": (
            "per-family artifacts produced by scripts/rescore_redteam_family.py "
            "(space-bunny, deepseek) and scripts/merge_llama33_matrix.py (llama); "
            "identical run_case scoring path; variant-level P/R over valid drafts"
        ),
        "families": table,
        "common_subset": {
            "cases": len(common),
            "note": "case-key intersection across all three families (apples-to-apples table)",
        },
        "headline": {
            "space-bunny-free": "P 0.9945→1.0, R 0.943→0.9585 (0 new FPs, 0 regressed catches)",
            "deepseek-v4-flash-free": "P 1.0→1.0, R 0.9306→0.9827 (0 new FPs, 0 regressed catches)",
            "llama-3.3-70b": "P 0.8862→0.9158, R 0.8757→0.8981 all-authors (llama-only ablation P 0.9091 R 0.9091)",
        },
        "cross_family_reading": (
            "Post-fix, the verifier holds precision at 0.92–1.0 and recall at 0.90–0.98 "
            "across three author families with per-check P/R proven on the 105-case "
            "deterministic suite at 1.0/1.0. Residual live misses concentrate in "
            "author-side consistency drift and author-specific tell vocabulary "
            "(cross-author variance — the filled llama cases and the deepseek "
            "vocabulary shows the same pattern from opposite directions)."
        ),
    }
    OUT.write_text(json.dumps(artifact, indent=2))

    print("=" * 76)
    print("CROSS-FAMILY COMPARISON (post-P1 verifier rescore)")
    print("=" * 76)
    print(f"  common subset: {len(common)} cases")
    for name, _ in FAMILIES:
        e = table[name]
        a, c = e["after_rescored"], e["common80_after"]
        b = e.get("before", {})
        delta = e.get("recall_delta")
        print(f"  {name:<22} before P={b.get('precision')} R={b.get('recall')} -> "
              f"after P={a['precision']:.4f} R={a['recall']:.4f} (dR={delta}) "
              f"| common80 R={c['recall']:.4f}")
    print(f"  artifact: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
