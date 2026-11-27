"""E14 — Reconnaissance externality of a published tomogram (T14).

Pre-analysis registered in docs/paper/belief_tomography/PREREGISTRATION_E14.md
BEFORE any reconnaissance quantity was computed. Uses only the frozen E4
artifacts (e4_separation.json, commit 0888540). Offline decision analysis:
no new behavioral measurement, no API calls.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAMS = ("authority_forgery", "state_deception", "goal_subversion",
        "epistemic_echo", "exfiltration_lure")


def main() -> None:
    data = json.loads((HERE / "e4_separation.json").read_text())
    out = {"source": "e4_separation.json (pre-existing, frozen)", "targets": {},
           "verdict": {}}
    for name, runs in data["targets"].items():
        out["targets"][name] = {}
        for r in runs:
            betas = {f: b for f, b in zip(FAMS, r["betas"])}
            mean = sum(betas.values()) / len(betas)
            fstar = max(FAMS, key=lambda f: (betas[f], -FAMS.index(f)))
            adv = betas[fstar] - mean
            lo_all = min(r["ci"][f][0] for f in FAMS)
            hi_all = max(r["ci"][f][1] for f in FAMS)
            out["targets"][name][str(r["seed"])] = {
                "betas": {f: round(b, 4) for f, b in betas.items()},
                "uniform_success": round(mean, 4),
                "informed_success": round(betas[fstar], 4),
                "chosen_family": fstar,
                "recon_advantage": round(adv, 4),
                "ci_worst_case_range": [round(lo_all, 4), round(hi_all, 4)],
                "minimax_certificate_Umax": round(hi_all, 4),
                "distinguishable_families": len({round(b, 2) for b in betas.values()}),
            }
    graded = out["targets"]["HardenedDummy"]
    resistant = out["targets"]["ResistantDummy"]
    naive = out["targets"]["NaiveDummy"]
    out["verdict"] = {
        "graded_advantage_positive": all(r["recon_advantage"] > 0 for r in graded.values()),
        "resistant_advantage_zero": all(r["recon_advantage"] == 0 for r in resistant.values()),
        "naive_advantage_zero_as_registered": all(r["recon_advantage"] == 0 for r in naive.values()),
        "minimax_computable": all("minimax_certificate_Umax" in r
                                  for runs in out["targets"].values() for r in runs.values()),
    }
    out["verdict"]["E14_supported"] = bool(
        out["verdict"]["graded_advantage_positive"]
        and out["verdict"]["resistant_advantage_zero"]
        and out["verdict"]["minimax_computable"])
    (HERE / "e14_recon.json").write_text(json.dumps(out, indent=2))

    lines = [
        "# E14 — Reconnaissance externality of a published tomogram (T14)",
        "",
        "Pre-analysis registered: `docs/paper/belief_tomography/PREREGISTRATION_E14.md`. "
        "Derived from frozen E4 profiles only; not a new behavioral measurement.",
        "",
        "| foil | seed | uniform success | informed success | chosen family | A_rec | U_max |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, runs in out["targets"].items():
        for seed, r in runs.items():
            lines.append(f"| {name} | {seed} | {r['uniform_success']:.3f} | "
                         f"{r['informed_success']:.3f} | {r['chosen_family']} | "
                         f"{r['recon_advantage']:.3f} | {r['minimax_certificate_Umax']:.3f} |")
    v = out["verdict"]
    lines += [
        "", "## Verdict", "",
        f"- Graded foil has positive targeting advantage: **{v['graded_advantage_positive']}**",
        f"- Resistant (flat) foil has zero advantage: **{v['resistant_advantage_zero']}**",
        f"- Naive foil flat as registered: **{v['naive_advantage_zero_as_registered']}**",
        f"- Minimax certificate computable: **{v['minimax_computable']}**",
        "",
        f"**E14 supported: {v['E14_supported']}.** "
        + ("A published profile hands an attacker a targeting advantage: choosing "
           "the highest-$\\hat\\beta$ family raises expected success from the mean "
           "to the max. The advantage is zero only when the profile is flat. "
           "Publishing the scalar worst-family upper bound $U_{\\max}$ instead of "
           "the vector removes the ranking (reverting the attacker to mean success) "
           "at the cost of the defender's family-level allocation information. "
           "Decision analysis on frozen E4 profiles, not a measured attacker; the "
           "naive foil's small measured advantage is the known split-secret oracle "
           "false negative, disclosed in E4."
           if v["E14_supported"] else
           "One or more registered conditions failed; report the table as observed."),
        "",
    ]
    (HERE / "E14_RECONNAISSANCE.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
