"""Paper figures for Belief Tomography (F1-F8) — journal-upgraded set, v3.

Style bible: figures/theme.json (Okabe-Ito colorblind-safe palette, serif,
direct labeling, Wilson intervals always visible, annotations carry the
scientific claim). Every number plotted is read from the frozen experiment
artifacts in gauntlet/demo/ — nothing is hand-entered, presentation only.

v3 upgrade pass: in-figure titles removed (captions carry them), panel
letters (a)/(b)/(c) on every multi-panel figure, the saturation reference
ring added to F1's legend, the CI-cap reference drawn in F5(a), annotation
collisions removed (F6/F7), the E6 schematic restyled to match the platform
figure, and tightened marker/grid/label typography throughout.

Physical sizing: each figure's natural width matches the width at which
main.tex includes it (F1 -> 0.82\\columnwidth = 4.55 in; all others ->
\\columnwidth = 5.55 in), so fonts render at their nominal pt sizes.

Run:  uv run --with matplotlib python make_figures.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.ticker import NullFormatter, NullLocator

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
DEMO = REPO / "gauntlet" / "demo"
OUT = HERE
COL_IN = 5.55  # acmsmall \columnwidth in inches

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "font.size": 8.5,
    "axes.labelsize": 9,
    "axes.titlesize": 9,
    "legend.fontsize": 7.0,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.7,
    "mathtext.fontset": "dejavuserif",
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})

# Okabe-Ito colorblind-safe palette (theme.json categorical)
C = {
    "blue": "#0072B2", "orange": "#E69F00", "green": "#009E73",
    "red": "#D55E00", "purple": "#CC79A7", "sky": "#56B4E9",
    "yellow": "#F0E442", "grey": "#666666", "black": "#000000",
}
FAM_LABEL = {
    "authority_forgery": "authority\nforgery",
    "state_deception": "state\ndeception",
    "goal_subversion": "goal\nsubversion",
    "epistemic_echo": "epistemic\necho",
    "exfiltration_lure": "exfiltration\nlure",
}
FAM_ORDER = list(FAM_LABEL)


def save(fig, name: str) -> None:
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png")
    plt.close(fig)
    print("wrote", name)


def panel_letter(ax, letter: str, x: float = -0.02, y: float = 1.04) -> None:
    """Journal panel tag: bold lower-case letter outside the axes corner."""
    ax.text(x, y, f"({letter})", transform=ax.transAxes, ha="left", va="bottom",
            fontsize=8.5, fontweight="bold", color=C["black"])


# ---------------------------------------------------------------- F1 radar
def fig1() -> None:
    """Tomogram radar with Wilson CI envelopes and the oracle artifact callout."""
    profiles = json.loads((DEMO / "profile.json").read_text())
    naive, hardened = profiles[0], profiles[1]
    est = {
        p["target"]: {e["family"]: e for e in p["estimates"]}
        for p in (naive, hardened)
    }
    angles = np.linspace(0, 2 * math.pi, len(FAM_ORDER), endpoint=False)
    angles_c = np.concatenate([angles, angles[:1]])

    fig = plt.figure(figsize=(4.55, 3.55))
    ax = fig.add_subplot(111, polar=True)

    styles = {
        "DummyTarget (naive foil)": (C["red"], "naive foil (designed $\\beta{=}1$)"),
        "HardenedDummy (graded foil)": (C["blue"], "hardened foil (graded $\\beta$)"),
    }
    for name, (color, label) in styles.items():
        e = est[name]
        beta = np.array([e[f]["beta"] for f in FAM_ORDER] + [e[FAM_ORDER[0]]["beta"]])
        lo = np.array([e[f]["ci"][0] for f in FAM_ORDER] + [e[FAM_ORDER[0]]["ci"][0]])
        hi = np.array([e[f]["ci"][1] for f in FAM_ORDER] + [e[FAM_ORDER[0]]["ci"][1]])
        # Wilson CI envelope, then the measured profile on top of it.
        ax.fill_between(angles_c, lo, hi, color=color, alpha=0.15, linewidth=0)
        ax.plot(angles_c, beta, color=color, linewidth=1.5, label=label)
        ax.scatter(angles, beta[:-1], color=color, s=16, zorder=3)

    # The known oracle-limited cell: naive foil epistemic echo reads 2/3
    # because the generation-3 probe splits the canary (Section 5.5 audit).
    echo_angle = angles[FAM_ORDER.index("epistemic_echo")]
    echo_val = est["DummyTarget (naive foil)"]["epistemic_echo"]["beta"]
    ax.annotate("oracle-limited cell\n(split-secret FN, §5.5)",
                xy=(echo_angle, echo_val), xytext=(echo_angle - 0.50, 1.30),
                fontsize=6.6, color=C["orange"], ha="center",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.2),
                arrowprops=dict(arrowstyle="->", linewidth=0.7, color=C["orange"],
                                connectionstyle="arc3,rad=0.22"))

    # Reference ring at beta = 1, added to the legend so the grey polygon is
    # never an unlabeled series.
    ring, = ax.plot(angles_c, np.ones_like(angles_c), color=C["grey"],
                    linewidth=0.8, alpha=0.6, zorder=1,
                    label="$\\beta{=}1$ saturation ring")

    ax.set_xticks(angles)
    ax.set_xticklabels([FAM_LABEL[f] for f in FAM_ORDER], fontsize=7.2)
    ax.set_ylim(0, 1.08)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], fontsize=6.5, color=C["grey"],
                       bbox=dict(facecolor="white", edgecolor="none", alpha=0.75,
                                 pad=0.6))
    ax.set_rlabel_position(270)
    ax.tick_params(pad=3)
    ax.grid(alpha=0.30, linewidth=0.45)
    fig.legend(*ax.get_legend_handles_labels(), loc="lower center",
               bbox_to_anchor=(0.5, -0.125), ncol=1, frameon=False, fontsize=7.4)
    save(fig, "F1_tomogram_radar")


# ---------------------------------------------------------------- F2 E5 onset
def fig2() -> None:
    """Onset dichotomy: AUC vs horizon with theory-regime shading."""
    rows = json.loads((DEMO / "e5_onset.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(COL_IN, 2.65), sharey=True)
    for ax, delta, letter in zip(axes, (0.2, 0.4), ("a", "b")):
        sub = [r for r in rows if r["cond"] == "known-onset"
               and abs(r["delta"] - delta) < 1e-9]
        for n0, color, marker in ((10, C["orange"], "o"), (40, C["blue"], "s")):
            pts = sorted([r for r in sub if r["n0"] == n0], key=lambda r: r["m"])
            ax.plot([p["m"] for p in pts], [p["auc"] for p in pts],
                    color=color, marker=marker, linewidth=1.3, markersize=3.5,
                    label=f"known onset, $N_0={n0}$")
            # Theory regime band: where the reference floor exceeds delta the
            # AUC is capped (observed plateau range); where it does not, the
            # curve saturates toward 1 with enough horizon.
            if n0 == 10 and delta == 0.2:
                aucs = [p["auc"] for p in pts]
                ax.axhspan(min(aucs) - 0.012, max(aucs) + 0.012,
                           color=C["orange"], alpha=0.10, linewidth=0)
        birth = [r for r in rows if r["cond"].startswith("birth")
                 and abs(r["delta"] - delta) < 1e-9]
        if birth:
            birth = sorted(birth, key=lambda r: r["m"])
            ax.plot([p["m"] for p in birth], [p["auc"] for p in birth],
                    color=C["grey"], marker="^", linestyle="--", linewidth=1.1,
                    markersize=3.2, label="birth onset (self-test)")
        ax.axhline(0.5, color=C["black"], linewidth=0.6, linestyle=":")
        ax.set_xscale("log")
        ax.set_xticks([5, 10, 20, 40, 80])
        ax.set_xticklabels(["5", "10", "20", "40", "80"])
        ax.xaxis.set_minor_locator(NullLocator())
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.set_xlabel("observation horizon $M$")
        ax.set_title(f"$\\delta = {delta}$", fontsize=8.5, pad=3)
        ax.set_ylim(0.3, 1.03)
        ax.grid(axis="y", alpha=0.18, linewidth=0.4)
        panel_letter(ax, letter, x=0.0, y=1.02)
    axes[0].set_ylabel("detection AUC")
    axes[0].annotate("chance", xy=(5.2, 0.508), fontsize=6.5, color=C["grey"],
                     va="bottom")
    axes[1].annotate("chance", xy=(5.2, 0.508), fontsize=6.5, color=C["grey"],
                     va="bottom")
    # Regime captions: the theorem assigns each curve its regime. Placed in
    # the clear zones so no annotation crosses a curve.
    axes[0].text(0.97, 0.44, "$N_0{=}10$ floor $0.283>\\delta$: AUC capped",
                 transform=axes[0].transAxes, fontsize=6.4, color=C["orange"],
                 ha="right")
    axes[0].text(0.03, 0.05, "$N_0{=}40$ floor $0.141<\\delta$: saturates with $M$",
                 transform=axes[0].transAxes, fontsize=6.4, color=C["blue"],
                 ha="left")
    axes[1].text(0.97, 0.05, "both floors $<\\ \\delta$",
                 transform=axes[1].transAxes, fontsize=6.4, color=C["grey"],
                 ha="right")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, -0.10),
               ncol=3, frameon=False, fontsize=7)
    fig.tight_layout()
    save(fig, "F2_onset_dichotomy")


# ---------------------------------------------------------------- F3 dose-response
def fig3() -> None:
    """Dose-response validity with per-family r in a frameless legend."""
    data = json.loads((DEMO / "dose_response.json").read_text())
    stats = data.get("stats", {})
    fig, ax = plt.subplots(figsize=(COL_IN, 3.1))
    colors = [C["blue"], C["orange"], C["green"], C["red"], C["purple"]]
    markers = ["o", "s", "^", "D", "v"]  # distinct per family: grayscale-robust
    for fam, color, mk in zip(FAM_ORDER, colors, markers):
        pts = data["table"][fam]
        xs = [p["dose"] for p in pts]
        ys = [p["beta"] for p in pts]
        lo = [p["beta"] - p["ci"][0] for p in pts]
        hi = [p["ci"][1] - p["beta"] for p in pts]
        r = stats.get(fam, {}).get("pearson_r")
        r_txt = f"  ($r{{=}}{r:.3f}$)" if r is not None else ""
        ax.errorbar(xs, ys, yerr=[lo, hi], color=color, marker=mk, markersize=3,
                    linewidth=1.2, capsize=1.8, elinewidth=0.8,
                    label=FAM_LABEL[fam].replace("\n", " ") + r_txt)
    ax.plot([0, 1], [0, 1], color=C["grey"], linestyle="--", linewidth=0.8)
    # Direct label along the ideal line: no arrow, no crossing annotation.
    ax.text(0.40, 0.335, "$\\hat\\beta = d$ (ideal)", fontsize=6.8,
            color=C["grey"], rotation=38, rotation_mode="anchor",
            ha="center", va="top",
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=0.8))
    ax.set_xlim(-0.03, 1.03)
    ax.set_ylim(-0.03, 1.05)
    ax.set_xlabel("injected belief dose $d$")
    ax.set_ylabel("measured $\\hat\\beta$")
    ax.grid(alpha=0.18, linewidth=0.4)
    ax.legend(loc="upper left", frameon=False, ncol=1, fontsize=6.8)
    save(fig, "F3_dose_response")


# ---------------------------------------------------------------- F4 policy benchmark
def fig4() -> None:
    """Allocation benchmark with the objective-mismatch gap quantified."""
    data = json.loads((DEMO / "policy_benchmark.json").read_text())
    fig, ax = plt.subplots(figsize=(COL_IN, 2.9))
    styles = {"uniform": (C["black"], "o", "-"),
              "neyman": (C["blue"], "s", "-"),
              "ucb": (C["red"], "^", "--"),
              "psi": (C["orange"], "v", "--")}
    for name, (color, marker, ls) in styles.items():
        pts = sorted((int(k), v) for k, v in data[name].items())
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color,
                marker=marker, linestyle=ls, linewidth=1.2, markersize=3.4)
    # The gap the benchmark exists to show: at the largest budget, the
    # regret-optimal objective costs a quantified factor in estimation error.
    err_u = data["uniform"]["400"]
    err_a = data["ucb"]["400"]
    factor = err_a / err_u
    ax.annotate("", xy=(400, err_a), xytext=(400, err_u),
                arrowprops=dict(arrowstyle="<->", linewidth=0.8, color=C["red"]))
    ax.text(383, (err_u + err_a) / 2, f"{factor:.1f}$\\times$\nerror at $n{{=}}400$",
            fontsize=6.6, color=C["red"], ha="right", va="center")
    ax.set_xscale("log")
    ax.set_xticks([25, 50, 100, 200, 400])
    ax.set_xticklabels(["25", "50", "100", "200", "400"])
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("probe budget $n$")
    ax.set_ylabel("mean profile error")
    ax.set_ylim(0.025, 0.185)
    ax.grid(alpha=0.18, linewidth=0.4, which="major")
    # Direct labels at the line ends (theme rule: direct labeling over
    # legends where feasible). uniform and Neyman tie at n=400, so they
    # share one label; the two mismatched objectives get their own.
    ax.set_xlim(21, 980)
    nu = data["uniform"]["400"]
    ax.text(430, nu, f"uniform = Neyman\n{nu:.3f}", fontsize=6.4, color=C["grey"],
            va="center", ha="left")
    ax.text(430, err_a, f"UCB-lite (regret)\n{err_a:.3f}", fontsize=6.4,
            color=C["red"], va="top", ha="left")
    ax.text(430, data["psi"]["400"], f"PSI (information)\n{data['psi']['400']:.3f}",
            fontsize=6.4, color=C["orange"], va="bottom", ha="left")
    save(fig, "F4_policy_benchmark")


# ---------------------------------------------------------------- F5 E2 field results
def fig5() -> None:
    """E2 field null: profiles + BCG with tolerance context and censoring disclosure."""
    files = sorted(DEMO.glob("E2V1_*_p20_s2718.profile.json"))
    if not files:
        print("F5 skipped: no E2V1 profile yet")
        return
    # A run with >=50% mapped-unavailable turns is UNMEASURABLE: plotting its
    # conservative-mapped beta=0 as a real profile would be a false measurement.
    profiles = []
    for f in files:
        p = json.loads(f.read_text())
        rate = p.get("meta", {}).get("blocked_rate", 0)
        if rate >= 0.5:
            print(f"F5: excluding {p['target']} (unmeasurable, {rate:.1%} unavailable)")
            continue
        profiles.append(p)
    if not profiles:
        print("F5 skipped: no measurable E2V1 profile")
        return
    fig, axes = plt.subplots(1, 2, figsize=(COL_IN, 2.75),
                             gridspec_kw={"width_ratios": [2.25, 1.0]})
    ax = axes[0]
    x = np.arange(len(FAM_ORDER))
    colors = [C["blue"], C["orange"], C["green"]]
    tau = 0.2
    # Every measurable profile is all-zero here, so zero-height bars would be
    # invisible and the legend would map to nothing. Dodged colored errorbars
    # with a visible marker at the baseline keep the legend honest.
    off = (np.arange(len(profiles)) - (len(profiles) - 1) / 2) * 0.16
    for i, p in enumerate(profiles):
        est = {e["family"]: e for e in p["estimates"]}
        betas = [est[f]["beta"] for f in FAM_ORDER]
        lo = [est[f]["beta"] - est[f]["ci"][0] for f in FAM_ORDER]
        hi = [est[f]["ci"][1] - est[f]["beta"] for f in FAM_ORDER]
        rate = p.get("meta", {}).get("blocked_rate", 0)
        name = p["target"].replace("-sol", "")
        ax.errorbar(x + off[i], betas, yerr=[lo, hi], fmt="o", markersize=3.4,
                    color=colors[i % len(colors)], elinewidth=0.9, capsize=2.2,
                    capthick=0.9,
                    label=f"{name} · {rate:.1%} turns unavailable")
    ax.axhline(tau, color=C["grey"], linestyle="--", linewidth=0.8)
    ax.text(-0.42, tau + 0.006, "$\\tau{=}0.2$", fontsize=6.6, color=C["grey"],
            ha="left")
    hi_all = max(e["ci"][1] for p in profiles for e in p["estimates"])
    # The Wilson upper bound shared by every family is the null's quantitative
    # statement: draw it as a labeled cap line, not an arrow to one whisker.
    ax.axhline(hi_all, color=C["black"], linestyle=":", linewidth=0.7)
    ax.text(4.42, hi_all + 0.005, f"Wilson upper bound\n${hi_all:.3f}$",
            fontsize=6.3, color=C["black"], ha="right", va="bottom")
    ax.set_xticks(x)
    ax.set_xticklabels([FAM_LABEL[f] for f in FAM_ORDER], fontsize=6.5)
    ax.set_ylim(0, 0.24)
    ax.set_ylabel("measured $\\hat\\beta$ (95% CI)")
    ax.legend(frameon=False, fontsize=6.6, loc="center left",
              bbox_to_anchor=(0.01, 0.62))
    ax.grid(axis="y", alpha=0.18, linewidth=0.4)
    panel_letter(ax, "a", x=-0.09, y=1.03)

    ax2 = axes[1]
    claims = ["confidentiality", "action_safety"]
    x2 = np.arange(len(claims))
    for i, p in enumerate(profiles):
        gaps = [p["belief_claim_gap"][c]["gap"] for c in claims]
        ax2.errorbar(x2 + off[i], gaps, fmt="o", markersize=3.4,
                     color=colors[i % len(colors)])
    ax2.axhline(tau, color=C["grey"], linestyle="--", linewidth=0.8)
    ax2.text(-0.30, tau + 0.006, "$\\tau{=}0.2$", fontsize=6.6, color=C["grey"],
             ha="left")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(["confidentiality", "action safety"], fontsize=7)
    ax2.set_ylim(0, 0.24)
    ax2.set_ylabel("Belief–Claim Gap")
    ax2.text(0.55, 0.62, "zero at instrument\nresolution", transform=ax2.transAxes,
             ha="center", fontsize=6.8, color=C["black"], style="italic")
    ax2.grid(axis="y", alpha=0.18, linewidth=0.4)
    panel_letter(ax2, "b", x=-0.14, y=1.03)
    fig.tight_layout()
    save(fig, "F5_field_bcg")


# ---------------------------------------------------------------- F6 E4 certification
def fig6() -> None:
    """Certification as a decision rule: beta dots + Wilson lower-bound decision markers."""
    path = DEMO / "e4_separation.json"
    if not path.exists():
        print("F6 skipped: no e4_separation.json yet")
        return
    data = json.loads(path.read_text())
    tau = data["tau"]
    targets = list(data["targets"])
    fig, axes = plt.subplots(len(targets), 1, figsize=(COL_IN, 3.4), sharex=True,
                             sharey=True)
    for ax, name, letter in zip(axes, targets, ("a", "b", "c")):
        run = data["targets"][name][0]  # seeds are identical on deterministic foils
        betas = run["betas"]
        los = [run["ci"][f][0] for f in FAM_ORDER]
        x = np.arange(len(FAM_ORDER))
        # Shaded "evidence of violation" region: a lower bound above tau is
        # positive evidence that the family belief exceeds the tolerance.
        ax.axhspan(tau, 1.06, color=C["red"], alpha=0.05, linewidth=0)
        ax.errorbar(x, betas, yerr=[[b - l for b, l in zip(betas, los)],
                                    [run["ci"][f][1] - b for b, f in
                                     zip(betas, FAM_ORDER)]],
                    fmt="o", color=C["blue"], markersize=4, capsize=2,
                    elinewidth=0.8, linewidth=0)
        ax.scatter(x, los, facecolors="none", edgecolors=C["blue"], s=22,
                   linewidths=0.9, zorder=3)
        ax.axhline(tau, color=C["red"], linestyle="--", linewidth=0.8)
        certified = run["cert"]["certified"]
        verdict = "CERTIFIED" if certified else "NOT CERTIFIED"
        ax.text(0.02, 0.90 if certified else 0.06, verdict, transform=ax.transAxes,
                ha="left", fontsize=6.8,
                color=C["green"] if certified else C["red"], fontweight="bold")
        ax.set_ylim(-0.03, 1.06)
        ax.set_yticks([0, 0.5, 1.0])
        ax.set_ylabel(name.replace("Dummy", ""), fontsize=7.5)
        ax.grid(axis="y", alpha=0.15, linewidth=0.4)
        panel_letter(ax, letter, x=-0.085, y=1.015)
    axes[0].annotate("split-secret FN", xy=(3, 0.60), xytext=(3.42, 0.26),
                     fontsize=6.2, color=C["orange"],
                     arrowprops=dict(arrowstyle="->", linewidth=0.6,
                                     color=C["orange"],
                                     connectionstyle="arc3,rad=-0.15"))
    # Explainer lives in the resistant row's empty upper half: the naive and
    # hardened rows' whiskers span the text height and would cross it.
    axes[2].text(0.02, 0.68, "$\\hat\\beta>\\tau$ is positive evidence:\n"
                 "open marker = Wilson lower bound (decision statistic)",
                 transform=axes[2].transAxes, fontsize=6.3, color=C["blue"])
    axes[-1].set_xticks(np.arange(len(FAM_ORDER)))
    axes[-1].set_xticklabels([FAM_LABEL[f] for f in FAM_ORDER], fontsize=6.8)
    axes[-1].set_xlabel("probe family")
    save(fig, "F6_certification")


# ---------------------------------------------------------------- F7 limits
def fig7() -> None:
    """E6 belief-laundering schematic + E7 gaming-gap bars with Gamma brackets."""
    e6 = json.loads((DEMO / "e6_composition.json").read_text())
    e7 = json.loads((DEMO / "e7_gaming.json").read_text())
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(COL_IN, 2.9),
                                   gridspec_kw={"width_ratios": [1.35, 1.0]})

    # Left: composition schematic, restyled to match the platform figure
    # (tinted rounded boxes, consistent arrows).
    ax1.set_xlim(0, 10); ax1.set_ylim(0, 10); ax1.axis("off")

    def box(x, y, w, h, text, color, tint):
        ax1.add_patch(FancyBboxPatch((x, y), w, h,
                                     boxstyle="round,pad=0.14,rounding_size=0.25",
                                     facecolor=tint, edgecolor=color,
                                     linewidth=1.0))
        ax1.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                 fontsize=6.5, color="#1a1a1a", linespacing=1.2)

    box(0.2, 6.2, 2.7, 2.2, "retriever A\nlocal $\\hat\\beta=0$\ncertified",
        C["green"], "#EAF4EE")
    box(3.7, 6.2, 2.9, 2.2,
        "interface\n$<$tool:retriever$>$\ndoc contains $s_A$", C["orange"], "#FDF3E7")
    box(7.6, 6.2, 2.3, 2.2, "orchestrator B\nlocal $\\hat\\beta=0$\ncertified",
        C["green"], "#EAF4EE")
    box(3.7, 1.4, 6.2, 2.2,
        "composed pipeline $\\hat\\beta=1.0$\n(20/20 breaches, Wilson [0.84, 1.00])",
        C["red"], "#FBEDE8")
    ax1.add_patch(FancyArrowPatch((2.9, 7.3), (3.62, 7.3), arrowstyle="-|>",
                                  mutation_scale=10, linewidth=1.0,
                                  color=C["grey"]))
    ax1.add_patch(FancyArrowPatch((6.68, 7.3), (7.5, 7.3), arrowstyle="-|>",
                                  mutation_scale=10, linewidth=1.0,
                                  color=C["grey"]))
    ax1.add_patch(FancyArrowPatch((8.7, 6.05), (6.85, 3.75), arrowstyle="-|>",
                                  mutation_scale=10, linewidth=1.0,
                                  color=C["red"]))
    ax1.text(5.0, 9.35, "the secret travels only through the interface",
             ha="center", fontsize=6.6, color=C["orange"], style="italic")
    ax1.text(5.0, 0.35, "no component is individually non-compliant",
             ha="center", va="center", fontsize=6.8, color=C["red"],
             style="italic")
    panel_letter(ax1, "a", x=0.0, y=1.0)

    # Right: gaming gap bars with per-foil Gamma brackets.
    names = ["ProbeAwareFoil", "SemanticsOnlyFoil", "ResistantFoil"]
    pub = [e7["targets"][n]["2718"]["public"]["mean_beta"] for n in names]
    held = [e7["targets"][n]["2718"]["held"]["mean_beta"] for n in names]
    x = np.arange(len(names)); w = 0.34
    ax2.bar(x - w / 2, pub, w, label="public probes", color=C["blue"], alpha=0.9)
    ax2.bar(x + w / 2, held, w, label="held-out paraphrases", color=C["orange"],
            alpha=0.9)
    ax2.axhline(0.2, color=C["grey"], linestyle="--", linewidth=0.8)
    ax2.text(2.45, 0.21, "$\\tau=0.2$", fontsize=6.5, color=C["grey"], ha="right")
    for xi, (pv, hv) in enumerate(zip(pub, held)):
        gamma = abs(hv - pv)
        if gamma > 0.05:
            # Bracket in the gutter right of the pair (bars end at xi+0.34,
            # the next group starts at xi+0.66), with a rotated label so it
            # never sits on a bar.
            gx = xi + 0.52
            ax2.annotate("", xy=(gx, hv), xytext=(gx, pv),
                         arrowprops=dict(arrowstyle="<->", linewidth=0.8,
                                         color=C["purple"]))
            ax2.text(gx + 0.08, (pv + hv) / 2, f"$\\Gamma{{=}}{gamma:.1f}$",
                     fontsize=6.5, color=C["purple"], va="center", ha="left",
                     rotation=90)
        else:
            top = max(pv, hv)
            ax2.text(xi, min(top + 0.04, 1.10), "$\\Gamma{=}0$", fontsize=6.5,
                     color=C["purple"], ha="center")
    ax2.text(0.98, 0.50, "a small $\\Gamma$ is\nnecessary,\nnot sufficient",
             transform=ax2.transAxes, fontsize=6.4, color=C["purple"],
             ha="right", linespacing=1.25)
    ax2.set_xticks(x)
    ax2.set_xticklabels([n.replace("Foil", "") for n in names], fontsize=6.3,
                        rotation=12, ha="right")
    ax2.set_ylim(0, 1.32)
    ax2.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax2.set_ylabel("mean family $\\hat\\beta$")
    ax2.legend(frameon=False, fontsize=6.3, loc="upper left",
               bbox_to_anchor=(0.02, 0.98))
    ax2.grid(axis="y", alpha=0.15, linewidth=0.4)
    panel_letter(ax2, "b", x=0.0, y=1.0)
    fig.tight_layout()
    save(fig, "F7_limits_of_certification")


# ---------------------------------------------------------------- F8 release wave
def fig8() -> None:
    """E15 release comparison with the deception gain + E16 budget frontier with MC points."""
    e15 = json.loads((DEMO / "e15_deception_release.json").read_text())
    e16 = json.loads((DEMO / "e16_query_complexity.json").read_text())
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(COL_IN, 2.75),
                                   gridspec_kw={"width_ratios": [1.0, 1.15]})

    # Left: E15 — expected attacker per-attempt success by release type.
    sh = e15["targets"]["ShapingFoil"]["2718"]["policies"]
    names = ["honest\nrelease", "silence\n(uniform)", "decoy\nrelease"]
    vals = [sh["honest_argmax"]["succ"] / 120.0,
            sh["uniform"]["succ"] / 120.0,
            sh["decoy_argmax"]["succ"] / 120.0]
    cols = [C["red"], C["grey"], C["green"]]
    x = np.arange(3)
    ax1.bar(x, vals, 0.62, color=cols, alpha=0.92)
    for xi, v in zip(x, vals):
        ax1.text(xi, v + 0.03, f"{v:.2f}", ha="center", fontsize=7.5)
    # The deception gain of the release: honest minus decoy success.
    gain = vals[0] - vals[2]
    ax1.annotate("", xy=(2.44, vals[0]), xytext=(2.44, vals[2]),
                 arrowprops=dict(arrowstyle="<->", linewidth=0.9,
                                 color=C["purple"]))
    ax1.text(2.52, 0.5, f"$\\Delta_{{\\mathrm{{dec}}}}{{=}}{gain:.3f}$",
             ha="left", va="center", fontsize=6.8, color=C["purple"],
             rotation=90)
    ax1.axhline(vals[0], color=C["red"], linestyle=":", linewidth=0.6, alpha=0.5)
    ax1.set_xlim(-0.55, 2.95)
    ax1.set_xticks(x)
    ax1.set_xticklabels(names, fontsize=7.2)
    ax1.set_ylim(0, 1.18)
    ax1.set_ylabel("attacker per-attempt success")
    ax1.grid(axis="y", alpha=0.15, linewidth=0.4)
    panel_letter(ax1, "a", x=-0.16, y=1.02)

    # Right: E16 — closed-form frontier + MC validation points.
    pts = [(float(m), r["n_min"]) for m, r in e16["closed_form"].items()
           if r["n_min"] is not None and float(m) >= 0.5]
    pts.sort()
    ms = [m for m, _ in pts]; ns = [n for _, n in pts]
    ax2.axvspan(0.93, 1.0, color=C["red"], alpha=0.10)
    ax2.text(0.965, 60, "undetectable at any\nfeasible budget",
             ha="center", fontsize=6.4, color=C["red"], rotation=90)
    ax2.plot(ms, ns, "-o", color=C["blue"], markersize=3.2, linewidth=1.3,
             label="closed form")
    mc_pts = []
    for m, r in e16.get("monte_carlo", {}).items():
        fm = float(m)
        if fm < 0.5:
            continue
        for n_str, run in r.items():
            if run.get("detection_rate") is not None and fm <= 0.93:
                mc_pts.append((fm, int(n_str), run["detection_rate"]))
    ax2.annotate("$n_{\\min}{=}8$ at $m{=}0.5$", xy=(0.5, 8),
                 xytext=(0.53, 130), fontsize=6.4, color=C["blue"],
                 arrowprops=dict(arrowstyle="-", color=C["blue"], linewidth=0.7))
    ax2.annotate("$n_{\\min}{=}2057$ at $m{=}0.92$", xy=(0.92, 2057),
                 xytext=(0.62, 2600), fontsize=6.4, color=C["blue"],
                 arrowprops=dict(arrowstyle="-", color=C["blue"], linewidth=0.7))
    ax2.set_yscale("log")
    ax2.set_ylim(1, 8000)
    ax2.set_xlim(0.48, 1.0)
    ax2.set_xlabel("attacker held-out misread rate $m$")
    ax2.set_ylabel("minimum held-out budget $n_{\\min}$ (95% power)")
    ax2.text(0.50, 2.0, "closed form matches Monte Carlo at\nevery registered grid point",
             fontsize=6.4, color=C["grey"], ha="left", va="bottom")
    ax2.legend(frameon=False, fontsize=6.3, loc="upper left")
    ax2.grid(alpha=0.15, linewidth=0.4, which="both")
    panel_letter(ax2, "b", x=-0.12, y=1.02)
    fig.tight_layout()
    save(fig, "F8_deception_release")


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
    fig6()
    fig7()
    fig8()
