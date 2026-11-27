#!/usr/bin/env python3
"""Fig. 3 (F9_platform) — platform architecture schematic.

Rebuilt with the figures:svg-primitives skill (Canvas / LabeledBox /
Arrow.connect / Annotation): mm-precise layout, text auto-fitted to boxes
with real DejaVu metrics, tangent-correct arrowheads, strict Canvas
validation (text-overflow, arrow-tip-distance, marker-orient,
sibling-overlap). Palette from figures/theme.json (Okabe-Ito). Canvas
136 mm = acmsmall \\columnwidth (385.34 pt), so the PDF includes 1:1.

Inter-plane arrows run between invisible "port" rects on the background
layer (exempt from sibling-overlap) so each connector is a straight
vertical at a fixed x instead of a kinked via path.

Runner:
  uv run --with drawsvg --with svgpathtools --with Pillow --with fonttools \
      --with cairosvg --with lxml python make_f9_platform_svg.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SKILL_SCRIPTS = Path.home() / ".claude/skills/svg-primitives/scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from svg_primitives import Annotation, Arrow, Canvas, LabeledBox  # noqa: E402

HERE = Path(__file__).resolve().parent
THEME = json.loads((HERE.parent.parent / "docs/paper/belief_tomography/figures/theme.json").read_text())
CAT = THEME["palette"]["categorical"]
BLUE, ORANGE, GREEN, VERMIL = CAT[0], CAT[1], CAT[2], CAT[3]
GREY = "#3D5A73"
INK = "#1a1a1a"
TINT = {"fleet": "#EAF1F8", "meas": "#FDF3E7", "assure": "#EAF4EE"}
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

OUT_SVG = HERE / "F9_platform.svg"

c = Canvas(width_mm=136, height_mm=78)
c.layer("background")   # z=0: invisible arrow ports
c.layer("bands")        # z=1: band containers + their own labels
c.layer("connectors")   # z=2: arrows pass under boxes
c.layer("boxes")        # z=3: content boxes

# ------------------------------------------------------------- band containers
fleet = c.layer("bands").add(LabeledBox(
    x=0.8, y=1.2, text="", min_width=134.4, min_height=25.8,
    fill=TINT["fleet"], stroke=BLUE, stroke_width=0.8, rx=2.0, padding=0))
meas = c.layer("bands").add(LabeledBox(
    x=0.8, y=30.2, text="", min_width=134.4, min_height=22.5,
    fill=TINT["meas"], stroke=ORANGE, stroke_width=0.8, rx=2.0, padding=0))
assure = c.layer("bands").add(LabeledBox(
    x=0.8, y=55.6, text="", min_width=134.4, min_height=21.5,
    fill=TINT["assure"], stroke=GREEN, stroke_width=0.8, rx=2.0, padding=0))

bands = c.layer("bands")
# NOTE: the text-overflow validator measures every <text> bbox as centered on
# its x, so all annotations are placed middle-anchored at bbox centres.
bands.add(Annotation(x=28.4, y=5.2, text="LIVE FLEET PLANE  ·  PUBLIC INTERNET",
                     font_size=7.2, font_path=FONT, text_anchor="middle", fill=BLUE))
bands.add(Annotation(x=28.4, y=34.0, text="MEASUREMENT PLANE  ·  THE INSTRUMENT",
                     font_size=7.2, font_path=FONT, text_anchor="middle", fill="#B8860B"))
bands.add(Annotation(x=21.4, y=59.6, text="ASSURANCE & EVIDENCE PLANE",
                     font_size=7.2, font_path=FONT, text_anchor="middle", fill=GREEN))
bands.add(Annotation(
    x=68, y=26.0,
    text="canary keys · registered kill gates · sandboxed sessions · "
         "append-only JSONL · mTLS edge→core · JEV gate advisory",
    font_size=6.0, font_path=FONT, text_anchor="middle", fill=GREY))

# Inter-plane arrow labels: inside band rects (validator containment),
# clear of the band titles.
bands.add(Annotation(x=66.0, y=34.0, text="logged sessions",
                     font_size=6.0, font_path=FONT, text_anchor="middle", fill=INK))
bands.add(Annotation(x=66.0, y=32.3, text="(E2 gateway · E3 fleet)",
                     font_size=5.8, font_path=FONT, text_anchor="middle", fill=GREY))
bands.add(Annotation(x=95.0, y=32.6, text="probes & deception operations",
                     font_size=6.0, font_path=FONT, text_anchor="middle", fill=INK))
bands.add(Annotation(x=57.5, y=58.9, text="hardening gates & audits",
                     font_size=6.0, font_path=FONT, text_anchor="middle", fill=INK))
bands.add(Annotation(x=93.0, y=58.9, text="every number pinned",
                     font_size=6.0, font_path=FONT, text_anchor="middle", fill=INK))

# ------------------------------------------------- invisible inter-plane ports
def port(x: float, y: float) -> LabeledBox:
    return c.layer("background").add(LabeledBox(
        x=x, y=y, text="", min_width=2.0, min_height=0.7,
        fill="none", stroke="none", padding=0))

p_fleet_down = port(57.0, 26.1)   # inside fleet, bottom
p_meas_down  = port(57.0, 30.5)   # inside meas, top
p_meas_up    = port(96.0, 30.5)
p_fleet_up   = port(96.0, 26.1)
p_meas_b1    = port(50.0, 51.9)   # inside meas, bottom
p_assure_up  = port(50.0, 55.8)   # inside assure, top
p_meas_b2    = port(94.0, 51.9)
p_assure_dn  = port(94.0, 55.8)

# ------------------------------------------------------------------ fleet row
b1 = c.layer("boxes").add(LabeledBox(
    x=8.5, y=7.0,
    text="Attacker personas\nfrontier-model brains\nover live SSH",
    font_size=6.6, font_path=FONT, padding=1.6, fill="white", stroke=BLUE))
b2 = c.layer("boxes").add(LabeledBox(
    x=40.0, y=7.0,
    text="Three-arm public face\nA: stock Cowrie · B: bare-LLM\nC: verified pipeline\n(one arm per host)",
    font_size=6.6, font_path=FONT, padding=1.6, fill="white", stroke=BLUE))
b3 = c.layer("boxes").add(LabeledBox(
    x=81.5, y=7.0,
    text="Verified deception loop\nChrollo classify → Don deceive\nHisoka generate+verify\nFAIL-CLOSED: an unverified\nturn is never served",
    font_size=6.6, font_path=FONT, padding=1.6, fill="white", stroke=VERMIL))

c.layer("connectors").add(Arrow.connect(b1, b2, stroke=BLUE, stroke_width=0.7))
c.layer("connectors").add(Arrow.connect(b2, b3, stroke=BLUE, stroke_width=0.7))

# ------------------------------------------------------- inter-plane arrows 1
c.layer("connectors").add(Arrow.connect(
    p_fleet_down, p_meas_down, stroke="#555555", stroke_width=0.7))
c.layer("connectors").add(Arrow.connect(
    p_meas_up, p_fleet_up, stroke="#555555", stroke_width=0.7))

# ----------------------------------------------------------- measurement row
mtexts = [
    "Probe library\n5 families ×\n3 generations",
    "Seed episodes\nfresh session\nper probe",
    "Verdict channel\noracles →\ntranscript jury",
    "Pinned estimator\nWilson 95% β̂\nfrozen commit",
    "Tomogram\nβ̂ profiles · BCG\nΓ · Δ(B)",
]
mboxes = []
mx = 6.0
for t in mtexts:
    m = c.layer("boxes").add(LabeledBox(
        x=mx, y=35.2, text=t, font_size=6.4, font_path=FONT, padding=1.6,
        fill="white", stroke=ORANGE))
    mboxes.append(m)
    mx = m.right + 4.2
for a, b in zip(mboxes, mboxes[1:]):
    c.layer("connectors").add(Arrow.connect(a, b, stroke=ORANGE, stroke_width=0.7))

# ------------------------------------------------------- inter-plane arrows 2
c.layer("connectors").add(Arrow.connect(
    p_assure_up, p_meas_b1, stroke="#555555", stroke_width=0.7))
c.layer("connectors").add(Arrow.connect(
    p_meas_b2, p_assure_dn, stroke="#555555", stroke_width=0.7))

# ------------------------------------------------------------- assurance row
atexts = [
    "Verifier red-team\n105 drafts · P=R=1.0\n0 unverified serves",
    "AI attack-team\ncampaigns on the\nplane; findings fixed",
    "Pre-registration\nledger — 21 registered\nexperiments",
    "Human rating loop\n3 blind raters +\nadjudicator",
    "Hash-chained archive\n220 artifacts ·\nfrozen estimator",
]
aboxes = []
ax = 3.0
for t in atexts:
    a = c.layer("boxes").add(LabeledBox(
        x=ax, y=61.5, text=t, font_size=6.0, font_path=FONT, padding=1.5,
        fill="white", stroke=GREEN))
    aboxes.append(a)
    ax = a.right + 1.8
for a, b in zip(aboxes, aboxes[1:]):
    c.layer("connectors").add(Arrow.connect(a, b, stroke=GREEN, stroke_width=0.7))

# ------------------------------------------------------------------- export
findings = c.save(str(OUT_SVG), validate="strict", output_png=False)
print("validation findings:", len(findings))
for f in findings:
    print("  -", f.category, f.message)

import cairosvg  # noqa: E402

cairosvg.svg2pdf(url=str(OUT_SVG), write_to=str(HERE / "F9_platform.pdf"))
cairosvg.svg2png(url=str(OUT_SVG), write_to=str(HERE / "F9_platform.png"),
                 output_width=1800)
print("wrote F9_platform.svg/.pdf/.png (136mm canvas)")
