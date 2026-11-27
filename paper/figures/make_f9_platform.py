#!/usr/bin/env python3
"""F9: platform architecture figure for the TOPS paper.

House style per figures/theme.json (Okabe-Ito, serif, flat vector, direct
labeling). Sized 1:1 to its \\includegraphics width so fonts render at
nominal point size (acmsmall \\columnwidth ~= 385.34pt ~= 5.352in).
Runner: uv run --with matplotlib --with numpy python make_f9_platform.py
"""
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = pathlib.Path(__file__).resolve().parent
THEME = json.loads((HERE.parent.parent / "docs/paper/belief_tomography/figures/theme.json").read_text())
PAL = THEME["palette"]["categorical"]
BLUE, ORANGE, GREEN, VERMIL = PAL[0], PAL[1], PAL[2], PAL[3]
FONT = THEME["typography"]["family"]

W_IN = 5.352  # \columnwidth of acmsmall, matches F2's 385.34pt
H_IN = 3.0

fig = plt.figure(figsize=(W_IN, H_IN))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")

TINT = {"fleet": "#EAF1F8", "meas": "#FDF3E7", "assure": "#EAF4EE"}


def container(x, y, w, h, tint, edge, label):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6,rounding_size=1.6",
                                fc=TINT[tint], ec=edge, lw=1.1, zorder=1))
    ax.text(x + 1.6, y + h - 1.3, label, ha="left", va="top", fontsize=7.0,
            fontweight="bold", color=edge, family=FONT, zorder=3)


def box(x, y, w, h, text, edge, fs=6.6):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.45,rounding_size=1.0",
                                fc="white", ec=edge, lw=0.9, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color="#1a1a1a", family=FONT, zorder=3, linespacing=1.22)


def arrow(x0, y0, x1, y1, color="#555555", lw=1.0):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                                 mutation_scale=7, color=color, lw=lw,
                                 shrinkA=1.0, shrinkB=1.0, zorder=4))


def gaplabel(x, y, text, align, fs=6.0):
    ax.text(x, y, text, ha=align, va="center", fontsize=fs, color="#333333",
            family=FONT, zorder=3, linespacing=1.15)


# ---------------------------------------------------------------- fleet plane
container(1.0, 64.5, 98.0, 33.0, "fleet", BLUE,
          "LIVE FLEET PLANE  ·  PUBLIC INTERNET")
box(3.5, 72.0, 20.0, 15.5,
    "Attacker personas\nfrontier-model brains\nover live SSH", BLUE)
box(27.5, 72.0, 29.5, 15.5,
    "Three-arm public face\nA: stock Cowrie · B: bare-LLM persona\nC: verified pipeline\n(one arm per host)", BLUE)
box(61.5, 72.0, 35.5, 15.5,
    "Verified deception loop\nChrollo classify → Don deceive →\nHisoka generate+verify, FAIL-CLOSED:\nan unverified turn is never served", VERMIL, fs=6.2)
arrow(23.5, 79.8, 27.5, 79.8, BLUE)
arrow(57.0, 79.8, 61.5, 79.8, BLUE)
ax.text(50.0, 67.6,
        "canary keys · registered kill gates · sandboxed sessions · append-only JSONL · mTLS edge→core · JEV gate advisory",
        ha="center", va="center", fontsize=5.8, color="#3D5A73", family=FONT,
        zorder=3, style="italic")

# ------------------------------------------------------ inter-plane gap 1
arrow(50.0, 64.5, 50.0, 57.0, "#555555", 1.1)
gaplabel(51.8, 60.7, "logged sessions\n(E2 gateway · E3 fleet)", "left")
arrow(88.5, 57.0, 88.5, 64.5, "#555555", 1.1)
gaplabel(87.0, 60.7, "probes & deception\noperations", "right")

# ------------------------------------------------------------ measurement plane
container(1.0, 27.0, 98.0, 30.0, "meas", ORANGE,
          "MEASUREMENT PLANE  ·  THE INSTRUMENT")
bw, gap, y0, bh = 17.2, 1.9, 33.5, 13.0
xs = [3.5 + i * (bw + gap) for i in range(5)]
mtext = [
    "Probe library\n5 families ×\n3 generations",
    "Seed episodes\nfresh session\nper probe",
    "Verdict channel\noracles →\ntranscript jury",
    "Pinned estimator\nWilson 95% β̂\nfrozen commit",
    "Tomogram\nβ̂ profiles · BCG\nΓ · Δ(B)",
]
for x, t in zip(xs, mtext):
    box(x, y0, bw, bh, t, ORANGE, fs=6.3)
for i in range(4):
    arrow(xs[i] + bw, y0 + bh / 2, xs[i + 1], y0 + bh / 2, ORANGE)

# ------------------------------------------------------ inter-plane gap 2
arrow(44.0, 19.5, 44.0, 27.0, "#555555", 1.1)
gaplabel(45.8, 23.2, "hardening gates\n& audits", "left")
arrow(88.5, 27.0, 88.5, 19.5, "#555555", 1.1)
gaplabel(87.0, 23.2, "every number\npinned", "right")

# ------------------------------------------------------- assurance plane
container(1.0, 1.5, 98.0, 18.0, "assure", GREEN,
          "ASSURANCE & EVIDENCE PLANE")
bw3, gap3, y3, bh3 = 17.5, 2.2, 2.8, 12.6
xs3 = [3.5 + i * (bw3 + gap3) for i in range(5)]
atext = [
    "Verifier red-team\n105 drafts\nP=R=1.0 · 0\nunverified serves",
    "AI attack-team\ncampaigns on the\nlive plane;\nfindings fixed",
    "Pre-registration\nledger — 21\nregistered\nexperiments",
    "Human rating loop\n3 blind raters\n+ adjudicator\n(claims–evidence)",
    "Hash-chained\nresults archive\n220 artifacts,\nfrozen estimator",
]
for x, t in zip(xs3, atext):
    box(x, y3, bw3, bh3, t, GREEN, fs=5.8)
for i in range(4):
    arrow(xs3[i] + bw3, y3 + bh3 / 2, xs3[i + 1], y3 + bh3 / 2, GREEN)

fig.savefig(HERE / "F9_platform.pdf")
fig.savefig(HERE / "F9_platform.png", dpi=300)
print("wrote F9_platform.pdf/.png", W_IN, "x", H_IN, "in")
