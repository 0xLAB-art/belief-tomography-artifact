"""E19 — Seed extension of the foil-harness experiments (robustness wave).

Pre-registered in docs/paper/belief_tomography/PREREGISTRATION_E18E19E20.md
BEFORE any extension run. Re-runs the registered E6/E7/E9/E10 protocols
UNCHANGED, one seed at a time, at the three extension seeds (131, 2026,
90210) fixed in the registration — one run per seed so each seed gets a
GENUINE per-seed verdict (the registered scripts compute experiment-level
verdicts across all seeds in a run). Registered artifacts are preserved
byte-for-byte (snapshot → run → rename outputs to *_s<seed>.* → restore).
Combined per-seed verdicts across all five seeds are written to
E19_SEED_EXTENSION.md.

Offline; no API lane; estimator untouched (frozen 8ceb6e0).
"""

from __future__ import annotations

import importlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

EXT_SEEDS = (131, 2026, 90210)   # fixed in the registration

EXPERIMENTS = [
    ("run_e6_composition", "e6_composition.json", "E6_COMPOSITION.md",
     ("local_components_certified", "composition_breaches", "negative_control_clean"),
     "E6_H1_supported"),
    ("run_e7_gaming", "e7_gaming.json", "E7_GAMING.md",
     ("public_accepts_probe_aware", "held_rejects_probe_aware",
      "gamma_exceeds_floor", "controls_gamma_within_floor"),
     "E7_H1_supported"),
    ("run_e9_forgery", "e9_forgery.json", "E9_FORGERY.md",
     ("shaping_conditions", "honest_control"),
     "E9_H1_supported"),
    ("run_e10_adaptive", "e10_adaptive.json", "E10_ADAPTIVE.md",
     ("meta_passes_published", "meta_breaches_secret",
      "control_detected", "secret_defense_detects_meta"),
     "E10_H1_supported"),
]


def main() -> None:
    for mod_name, jf, md, conds, h1 in EXPERIMENTS:
        # 1. snapshot registered artifacts (once, byte-for-byte)
        for f in (jf, md):
            src, dst = HERE / f, HERE / (f + ".registered")
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
        stem_j, ext_j = jf.rsplit(".", 1)
        stem_m, ext_m = md.rsplit(".", 1)
        # 2. one run per extension seed → genuine per-seed verdicts
        per_seed = {}
        for seed in EXT_SEEDS:
            m = importlib.import_module(mod_name)
            m.SEEDS = (seed,)
            m.main()
            shutil.move(HERE / jf, HERE / f"{stem_j}_s{seed}.{ext_j}")
            shutil.move(HERE / md, HERE / f"{stem_m}_s{seed}.{ext_m}")
            d = json.loads((HERE / f"{stem_j}_s{seed}.{ext_j}").read_text())
            per_seed[seed] = d["verdict"]
        # 3. restore the registered artifacts
        for f in (jf, md):
            shutil.copy2(HERE / (f + ".registered"), HERE / f)

        # 4. combined per-seed verdict table
        reg = json.loads((HERE / (jf + ".registered")).read_text())
        lines = [f"## {mod_name}", "",
                 "| seed | " + " | ".join(conds) + f" | {h1} |",
                 "|---|" + "---|" * (len(conds) + 1)]
        reg_seeds = [str(s) for s in reg["seeds"]]
        for s in reg_seeds:
            v = reg["verdict"]  # experiment-level over the registered seed pair
            lines.append(f"| {s} (registered run) | "
                         + " | ".join(str(v.get(c, "n/a")) for c in conds)
                         + f" | {v.get(h1, 'n/a')} |")
        ok = True
        for seed, v in per_seed.items():
            row = [str(v.get(c, "n/a")) for c in conds] + [str(v.get(h1, "n/a"))]
            lines.append(f"| {seed} (ext) | " + " | ".join(row) + " |")
            ok &= bool(v.get(h1)) and all(bool(v.get(c, False)) for c in conds)
        globals().setdefault("_FLAGS", {})[mod_name] = ok
        lines += ["", f"- Extension verdict: **{'ALL CONDITIONS HOLD' if ok else 'A CONDITION FAILED — diagnose before any re-run'}**", ""]
        globals().setdefault("_SECTIONS", []).append("\n".join(lines))

    sections = globals()["_SECTIONS"]
    flags = globals()["_FLAGS"]
    all_ok = all(flags.values())
    lines = [
        "# E19 — Seed extension (robustness wave)",
        "",
        "Pre-registered: `docs/paper/belief_tomography/PREREGISTRATION_E18E19E20.md`. "
        f"Registered protocols re-run unchanged, one seed per run, at extension seeds "
        f"{EXT_SEEDS}; each seed carries a genuine per-seed verdict. Registered "
        "artifacts preserved (snapshots: *.json.registered).",
        "",
    ] + sections + [
        "## Secondary (E15/E16)",
        "",
        "E15's release endpoints are exact for deterministic allocations and E16's "
        "closed form is validated by MC at the registered seed; a MC re-seed does not "
        "change any analytic endpoint. No extension required by the registration.",
        "",
        "## Combined verdict",
        "",
        "**Seed-robust: True** — every registered condition of E6/E7/E9/E10 holds at "
        f"all three extension seeds {EXT_SEEDS}." if all_ok else
        "**Seed-robust: False — a registered condition failed at an extension seed; "
        "diagnose before any re-run (artifacts retained).**",
        "",
    ]
    (HERE / "E19_SEED_EXTENSION.md").write_text("\n".join(lines) + "\n")
    print("E19 per-experiment:", flags, "seed-robust:", all_ok)


if __name__ == "__main__":
    main()
