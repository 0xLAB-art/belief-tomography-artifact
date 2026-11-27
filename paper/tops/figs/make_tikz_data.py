#!/usr/bin/env python3
"""Emit pgfplots data tables from the frozen experiment artifacts.

Every number plotted by the TikZ figures (paper/tops/figs/*.tex) is read
from the frozen JSONs in gauntlet/demo/ — nothing hand-entered. Rerun this
script after any artifact change; the .tex figures are static and only
\\input the tables emitted here.

Run:  uv run python make_tikz_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DEMO = REPO / "gauntlet" / "demo"
OUT = HERE / "figdata"
OUT.mkdir(exist_ok=True)

FAM = ["authority_forgery", "state_deception", "goal_subversion",
       "epistemic_echo", "exfiltration_lure"]


def w(name: str, rows: list) -> None:
    (OUT / name).write_text("\n".join(rows) + "\n")
    print("wrote figdata/" + name, f"({len(rows)} rows)")


def fnum(x: float) -> str:
    return f"{x:.6g}"


# ---------------------------------------------------------------- F1 radar
profiles = json.loads((DEMO / "profile.json").read_text())
est = {p["target"]: {e["family"]: e for e in p["estimates"]}
       for p in profiles[:2]}
naive = est["DummyTarget (naive foil)"]
hard = est["HardenedDummy (graded foil)"]
rows = []
for i in range(len(FAM) + 1):
    f = FAM[i % len(FAM)]
    ang = (90 - 72 * i) % 360  # pgfplots polar: CCW from east, 0-360
    if i == len(FAM):
        ang = 90
    rows.append("\t".join(map(str, [
        ang, fnum(naive[f]["beta"]), fnum(naive[f]["ci"][0]),
        fnum(naive[f]["ci"][1]), fnum(hard[f]["beta"]),
        fnum(hard[f]["ci"][0]), fnum(hard[f]["ci"][1])])))
w("fig1_radar.dat", ["ang\tnb\tlb\tub\thb\tlh\tuh"] + rows)

# F1 profile trace: same frozen estimates, canonical family order on x
# (authority, state, goal, echo, exfiltration) for the line+ribbon design.
rows_p = ["x\tnb\tlb\tub\thb\tlh\tuh"]
for i, fam in enumerate(FAM):
    rows_p.append("\t".join([
        str(i),
        fnum(naive[fam]["beta"]), fnum(naive[fam]["ci"][0]),
        fnum(naive[fam]["ci"][1]),
        fnum(hard[fam]["beta"]), fnum(hard[fam]["ci"][0]),
        fnum(hard[fam]["ci"][1])]))
w("fig1_profile.dat", rows_p)

# ---------------------------------------------------------------- F2 onset
rows5 = json.loads((DEMO / "e5_onset.json").read_text())
for delta, tag in ((0.2, "d02"), (0.4, "d04")):
    known = [r for r in rows5 if r["cond"] == "known-onset"
             and abs(r["delta"] - delta) < 1e-9]
    birth = [r for r in rows5 if r["cond"].startswith("birth")
             and abs(r["delta"] - delta) < 1e-9]
    ms = sorted({r["m"] for r in known})
    a10 = {r["m"]: r["auc"] for r in known if r["n0"] == 10}
    a40 = {r["m"]: r["auc"] for r in known if r["n0"] == 40}
    known_rows = ["m\ta10\ta40"] + [
        f"{m}\t{fnum(a10[m])}\t{fnum(a40[m])}" for m in ms]
    w(f"fig2_{tag}_known.dat", known_rows)
    birth_rows = ["m\tauc"] + [
        f"{r['m']}\t{fnum(r['auc'])}"
        for r in sorted(birth, key=lambda r: r["m"])]
    w(f"fig2_{tag}_birth.dat", birth_rows)

# ---------------------------------------------------------------- F3 dose
dose = json.loads((DEMO / "dose_response.json").read_text())
stats = dose.get("stats", {})
mac = ["% per-family Pearson r for the F3 legend"]
for i, fam in enumerate(FAM, 1):
    r = stats.get(fam, {}).get("pearson_r")
    rname = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}[i]
    mac.append(f"\\def\\figThreeR{rname}{{{r:.3f}}}" if r is not None
               else f"\\def\\figThreeR{rname}{{}}")
    pts = dose["table"][fam]
    trows = ["d\tb\telo\tehi"] + [
        f"{fnum(p['dose'])}\t{fnum(p['beta'])}\t"
        f"{fnum(p['beta'] - p['ci'][0])}\t{fnum(p['ci'][1] - p['beta'])}"
        for p in pts]
    w(f"fig3_fam{i}.dat", trows)
(OUT / "fig3_r.tex").write_text("\n".join(mac) + "\n")
print("wrote figdata/fig3_r.tex")

# ---------------------------------------------------------------- F4 policy
pol = json.loads((DEMO / "policy_benchmark.json").read_text())
budgets = sorted(int(k) for k in pol["uniform"])
rows = ["n\tuni\tney\tucb\tpsi"] + [
    "\t".join(str(b) if i == 0 else fnum(pol[key][str(b)])
              for i, key in enumerate(("n", "uniform", "neyman", "ucb", "psi")))
    for b in budgets]
w("fig4_policy.dat", rows)

# ---------------------------------------------------------------- F5 field
files = sorted(DEMO.glob("E2V1_*_p20_s2718.profile.json"))
profs = []
for fp in files:
    p = json.loads(fp.read_text())
    if p.get("meta", {}).get("blocked_rate", 0) < 0.5:
        profs.append(p)
mac = ["% F5 macros: cap, rates, target names"]
hi_all = max(e["ci"][1] for p in profs for e in p["estimates"])
mac.append(f"\\def\\figFiveCap{{{hi_all:.3f}}}")
for i, p in enumerate(profs, 1):
    rname = {1: "One", 2: "Two"}[i]
    mac.append(f"\\def\\figFiveRate{rname}{{{p['meta']['blocked_rate'] * 100:.1f}}}")
    mac.append(f"\\def\\figFiveName{rname}{{{p['target'].replace('-sol', '')}}}")
rows_a = ["i\tb1\tl1\tu1\tb2\tl2\tu2"]
for i, fam in enumerate(FAM):
    cols = [str(i)]
    for p in profs[:2]:
        e = {x["family"]: x for x in p["estimates"]}[fam]
        cols += [fnum(e["beta"]), fnum(e["beta"] - e["ci"][0]),
                 fnum(e["ci"][1] - e["beta"])]
    rows_a.append("\t".join(cols))
w("fig5_field.dat", rows_a)
claims = ["confidentiality", "action_safety"]
rows_b = ["i\tg1\tg2"]
for i, cl in enumerate(claims):
    cols = [str(i)]
    for p in profs[:2]:
        cols.append(fnum(p["belief_claim_gap"][cl]["gap"]))
    rows_b.append("\t".join(cols))
w("fig5_bcg.dat", rows_b)
(OUT / "fig5_macros.tex").write_text("\n".join(mac) + "\n")
print("wrote figdata/fig5_macros.tex")

# ---------------------------------------------------------------- F6 cert
e4 = json.loads((DEMO / "e4_separation.json").read_text())
for name in e4["targets"]:
    run = e4["targets"][name][0]
    tag = name.replace("Dummy", "").strip().lower()
    rows = ["i\tb\tlo\tup"] + [
        "\t".join([str(i), fnum(run["betas"][i]),
                   fnum(run["betas"][i] - run["ci"][FAM[i]][0]),
                   fnum(run["ci"][FAM[i]][1] - run["betas"][i])])
        for i in range(len(FAM))]
    w(f"fig6_{tag}.dat", rows)

# ---------------------------------------------------------------- F7 gaming
e7 = json.loads((DEMO / "e7_gaming.json").read_text())
names = ["ProbeAwareFoil", "SemanticsOnlyFoil", "ResistantFoil"]
rows = ["i\tpub\theld"] + [
    "\t".join([str(i),
               fnum(e7["targets"][n]["2718"]["public"]["mean_beta"]),
               fnum(e7["targets"][n]["2718"]["held"]["mean_beta"])])
    for i, n in enumerate(names)]
w("fig7_gaming.dat", rows)

# ---------------------------------------------------------------- F8 release
e15 = json.loads((DEMO / "e15_deception_release.json").read_text())
sh = e15["targets"]["ShapingFoil"]["2718"]["policies"]
vals = [sh["honest_argmax"]["succ"] / 120.0, sh["uniform"]["succ"] / 120.0,
        sh["decoy_argmax"]["succ"] / 120.0]
w("fig8_release.dat", ["i\tv"] + [
    f"{i}\t{fnum(v)}" for i, v in enumerate(vals)])
e16 = json.loads((DEMO / "e16_query_complexity.json").read_text())
pts = sorted((float(m), r["n_min"]) for m, r in e16["closed_form"].items()
             if r["n_min"] is not None and float(m) >= 0.5)
w("fig8_frontier.dat", ["m\tnmin"] + [
    f"{fnum(m)}\t{n}" for m, n in pts])

print("done.")
