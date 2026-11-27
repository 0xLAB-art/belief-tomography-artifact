"""Score the independent re-adjudication against the author's frozen labels.

Outputs agreement.json and disagreements.md. Reports raw agreement, Cohen's
kappa, and a Wilson 95% interval for raw agreement, overall and per coder.
For a coder whose own model family produced part of the sample (MiniMax), the
conflict-free subset excludes those items and is reported separately.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLASSES = ["genuine", "false_positive"]


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def kappa(pairs):
    n = len(pairs)
    if n == 0:
        return float("nan")
    po = sum(a == b for a, b in pairs) / n
    pa = {c: sum(a == c for a, _ in pairs) / n for c in CLASSES}
    pc = {c: sum(b == c for _, b in pairs) / n for c in CLASSES}
    pe = sum(pa[c] * pc[c] for c in CLASSES)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def load(path: Path):
    return {json.loads(l)["id"]: json.loads(l) for l in path.read_text().splitlines() if l.strip()}


def evaluate(name: str, key: dict, cod: dict, exclude_panel: str | None = None):
    ids = [i for i in sorted(key) if i in cod and cod[i].get("decision")]
    if exclude_panel:
        ids = [i for i in ids if key[i]["panel"] != exclude_panel]
    # Raw agreement over every response; an "ambiguous" response is not agreement.
    k = sum(cod[i]["decision"] == key[i]["author_label"] for i in ids)
    lo, hi = wilson(k, len(ids))
    # Cohen's kappa on decisive responses only (two classes).
    dec = [(key[i]["author_label"], cod[i]["decision"]) for i in ids if cod[i]["decision"] in CLASSES]
    return {
        "coder": name,
        "n": len(ids),
        "excluded_panel": exclude_panel,
        "agreement": k,
        "raw": round(k / len(ids), 4) if ids else None,
        "wilson95": [round(lo, 4), round(hi, 4)],
        "kappa_decisive": round(kappa(dec), 4) if dec else None,
        "n_decisive": len(dec),
        "decisions": {c: sum(cod[i]["decision"] == c for i in ids) for c in CLASSES},
        "ambiguous": sum(1 for i in ids if cod[i]["decision"] == "ambiguous"),
    }


def main() -> None:
    key = load(HERE / "key_author_labels.jsonl")
    coders = {}
    for p in sorted(HERE.glob("coder_*.jsonl")):
        coders[p.stem.replace("coder_", "")] = load(p)

    results, disagreements = [], {}
    for name, cod in coders.items():
        exclude = "E31-MiniMax" if "minimax" in name.lower() else None
        results.append(evaluate(name, key, cod, exclude_panel=exclude))
        results.append(evaluate(name + " (full sample)", key, cod))
        bad = []
        for i in sorted(cod):
            if not cod[i].get("decision"):
                continue
            if cod[i]["decision"] != key[i]["author_label"]:
                bad.append({
                    "id": i, "panel": key[i]["panel"], "session_id": key[i]["session_id"],
                    "flag": key[i]["uint_flag"], "author": key[i]["author_label"],
                    "coder": cod[i]["decision"], "reason": cod[i]["reason"],
                })
        disagreements[name] = bad

    # coder-vs-coder agreement on the intersection
    names = list(coders)
    pairwise = {}
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            ca, cb = coders[names[a]], coders[names[b]]
            common = [i for i in ca if i in cb and ca[i]["decision"] in CLASSES and cb[i]["decision"] in CLASSES]
            if common:
                k = sum(ca[i]["decision"] == cb[i]["decision"] for i in common)
                pairwise[f"{names[a]} vs {names[b]}"] = {
                    "n": len(common), "agreement": k, "raw": round(k / len(common), 4),
                    "kappa": round(kappa([(ca[i]["decision"], cb[i]["decision"]) for i in common]), 4),
                }

    out = {"results": results, "pairwise": pairwise,
           "note": "Author labels: all unauthorized_action flags are refusal-quote false positives; all secret_leak flags are genuine echoes. Coders were blind to panel, model, session id, and label."}
    (HERE / "agreement.json").write_text(json.dumps(out, indent=2) + "\n")

    lines = ["# Independent re-adjudication — disagreements", ""]
    for name, bad in disagreements.items():
        lines.append(f"## {name}: {len(bad)} disagreement(s)")
        for r in bad:
            lines.append(f"- **{r['id']}** ({r['panel']}, {r['session_id']}, {r['flag']}): "
                         f"author `{r['author']}` vs coder `{r['coder']}` — {r['reason']}")
        lines.append("")
    (HERE / "disagreements.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
