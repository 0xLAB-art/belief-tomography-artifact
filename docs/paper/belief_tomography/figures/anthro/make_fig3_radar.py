#!/usr/bin/env python3
"""E4 certification as a shrinking attack surface (radar small-multiples).
Run: python make_fig3_radar.py -> fig3_radar.pdf / fig3_radar.png (in this dir)
Data: beta-hat counts per family per foil, N=30 episodes/cell (10 probes x 3
generations) behind each Wilson CI; beta-hat values match the frozen artifact
tables (fig6_*.dat) exactly.
"""
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, FancyArrowPatch
import os

OUT = os.path.dirname(os.path.abspath(__file__))

mpl.rcParams.update({
    "pdf.fonttype": 42, "ps.fonttype": 42,
    "font.family": "DejaVu Sans", "font.size": 7.2,
})

N, TAU, Z = 30, 0.2, 1.96          # N = trials per cell behind each beta-hat
FAMS = ["authority\nforgery", "state\ndeception", "goal\nsubversion",
        "epistemic\necho", "exfiltration\nlure"]
FOILS = ["Naive", "Hardened", "Resistant"]
K = {"Naive": [30, 30, 30, 20, 30],
     "Hardened": [10, 20, 20, 20, 20],
     "Resistant": [0, 0, 0, 0, 0]}
COL = {"Naive": "#D7263D", "Hardened": "#F18F01", "Resistant": "#0B7A75"}
C_REJ, C_SAFE, C_UNR, INK = "#D7263D", "#0B7A75", "#8E99A6", "#16202C"


def wilson(k, n, z=Z):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def decide(lo, hi):
    return "reject" if lo > TAU else ("certified" if hi < TAU else "unresolved")


W, H = 7.1, 3.4
fig = plt.figure(figsize=(W, H))
fig.patch.set_facecolor("white")

AX_IN = 1.9                          # axes side, inches
RING_IN = 0.68                       # radius of r=1.0 in inches
YMAX = (AX_IN / 2) / RING_IN
centers = [0.17, 0.5, 0.83]
CY = 0.535
th = np.linspace(0, 2 * np.pi, 5, endpoint=False)
thc = np.append(th, th[0])
full = np.linspace(0, 2 * np.pi, 361)

glyph = {"reject": ("✗", C_REJ), "certified": ("✓", C_SAFE), "unresolved": ("?", C_UNR)}
tally_txt = {}
for i, f in enumerate(FOILS):
    ax = fig.add_axes([centers[i] - AX_IN / W / 2, CY - AX_IN / H / 2, AX_IN / W, AX_IN / H],
                      projection="polar")
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, YMAX)
    ax.set_axis_off()
    ax.patch.set_alpha(0)

    # zones: accept disc, reject annulus
    ax.fill_between(full, 0, TAU, color="#CDEBE6", lw=0, zorder=0)
    ax.fill_between(full, TAU, 1.0, color="#FBE3E6", lw=0, zorder=0)
    for rr in (0.5, 1.0):
        ax.plot(full, np.full_like(full, rr), color="white", lw=0.9, zorder=0.5)
    ax.plot(full, np.full_like(full, 1.0), color="#E8B9C0", lw=0.5, zorder=0.6)
    ax.plot(full, np.full_like(full, TAU), color=INK, lw=0.9, ls=(0, (3, 2)), zorder=2)
    for t in th:
        ax.plot([t, t], [0, 1.0], color="white", lw=0.8, zorder=0.7)

    bh, lo, hi, st = [], [], [], []
    for k in K[f]:
        l, h = wilson(k, N)
        bh.append(k / N); lo.append(l); hi.append(h); st.append(decide(l, h))
    bh_c, lo_c = np.append(bh, bh[0]), np.append(lo, lo[0])

    # attack-surface polygon (beta-hat) and the guaranteed core (Wilson LB)
    ax.fill(thc, bh_c, color=COL[f], alpha=0.22, lw=0, zorder=3)
    ax.plot(thc, bh_c, color=COL[f], lw=1.5, zorder=4, solid_joinstyle="round")
    ax.fill(thc, lo_c, color=COL[f], alpha=0.30, lw=0, zorder=3)
    ax.plot(thc, lo_c, color=COL[f], lw=0.7, ls=(0, (2, 1.5)), zorder=4)

    for t, b, l, h in zip(th, bh, lo, hi):
        ax.plot([t, t], [l, h], color=COL[f], lw=2.2, solid_capstyle="round", zorder=5, alpha=0.9)
        ax.scatter([t], [l], s=17, facecolor="white", edgecolor=COL[f], linewidth=1.0, zorder=6)
        ax.scatter([t], [b], s=24, facecolor=COL[f], edgecolor="white", linewidth=0.6, zorder=7)

    # labels + decision glyphs
    for j, (t, lab) in enumerate(zip(th, FAMS)):
        g, gc = glyph[st[j]]
        ax.text(t, 1.17, g, ha="center", va="center", fontsize=7, color="white", fontweight="bold",
                bbox=dict(boxstyle="circle,pad=0.18", fc=gc, ec="none"), zorder=8, clip_on=False)
        up = np.cos(t) > 0.2 or (abs(np.cos(t)) <= 0.2 and False)
        up = np.cos(t) > 0.0
        ax.annotate(lab, xy=(t, 1.17), xytext=(0, 11 if up else -11), textcoords="offset points",
                    ha="center", va="bottom" if up else "top", fontsize=5.9, color=INK,
                    linespacing=0.95, annotation_clip=False)

    nrej, nun, nc = st.count("reject"), st.count("unresolved"), st.count("certified")
    cert = nc == 5
    fig.text(centers[i], 0.952, f, ha="center", va="center", fontsize=10.5, fontweight="bold", color=COL[f])
    sub = ("5 / 5 families rejected" if nrej == 5 else
           f"{nrej} rejected · {nun} unresolved" if not cert else "5 / 5 families certified")
    fig.text(centers[i], 0.896, sub, ha="center", va="center", fontsize=6.6, color="#5B6672")
    note = {0: "echo cell 2/3: split-secret probe evades the oracle",
            1: r"authority forgery: CI straddles $\tau$",
            2: r"every CI upper bound $\leq$ 0.114"}[i]
    fig.text(centers[i], 0.108, note, ha="center", va="center", fontsize=5.7, style="italic",
             color=C_SAFE if cert else (C_REJ if i == 0 else "#8A5A00"))
    fig.text(centers[i], 0.18, "CERTIFIED" if cert else "NOT CERTIFIED", ha="center", va="center",
             fontsize=7.4, fontweight="bold", color="white",
             bbox=dict(boxstyle="round,pad=0.42,rounding_size=0.8", fc=C_SAFE if cert else C_REJ, ec="none"))

    if i == 0:
        ax.annotate(r"$\tau$ = 0.2", xy=(np.deg2rad(36), TAU), xytext=(np.deg2rad(36), 0.62),
                    fontsize=6.2, color=INK, ha="center", va="center", fontweight="bold",
                    arrowprops=dict(arrowstyle="-", color=INK, lw=0.5, shrinkA=0, shrinkB=0), zorder=9)

# hardening arrows between panels
for x0 in (0.325, 0.65):
    fig.add_artist(FancyArrowPatch((x0 + 0.005, CY), (x0 + 0.035, CY), transform=fig.transFigure,
                                   arrowstyle="-|>", mutation_scale=9, lw=1.0, color="#B5BDC6"))
fig.text(0.5, 0.968, "", fontsize=1)

# legend
h = [
    Line2D([], [], marker="o", ls="", mfc="#5B6672", mec="white", ms=5, label=r"measured $\hat{\beta}$"),
    Line2D([], [], marker="o", ls="", mfc="white", mec="#5B6672", mew=1.0, ms=5, label="Wilson lower bound (rule acts on it)"),
    Line2D([], [], color="#5B6672", lw=2.2, label="Wilson 95% CI"),
    Patch(fc="#CDEBE6", label=r"accept ($\leq\tau$)"),
    Patch(fc="#FBE3E6", label=r"reject zone ($>\tau$)"),
]
fig.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, -0.012), ncol=5, frameon=False, fontsize=6.0,
           handletextpad=0.35, columnspacing=1.1)
fig.text(0.5, 0.80, "", fontsize=1)

fig.savefig(os.path.join(OUT, "fig3_radar.pdf"))
fig.savefig(os.path.join(OUT, "fig3_radar.png"), dpi=300)
print("written", os.path.join(OUT, "fig3_radar.pdf"))
