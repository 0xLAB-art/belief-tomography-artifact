#!/usr/bin/env python3
"""Figure geometry audit for the paper's five TikZ/pgfplots figures.

The figures are drawn from declared coordinates, so a class of rendering
defects is mechanically checkable from the compiled output alone:

  1. border bands  -- dense ink along the canvas edge (clipped content);
  2. node rects    -- solid borders via long horizontal runs, dashed
                      borders via periodic dash runs, then any continuous
                      ink run >= MIN_RUN px strictly inside a rect. Text
                      cannot produce such runs; only a crossing line can;
  3. run inventory -- every H/V run >= MIN_RUN px, which must resolve to
                      a declared path, data element, or axis line.

Each figure is re-rendered in isolation (standalone class, pdflatex,
300 dpi raster) so the audit never depends on the surrounding paper.
Writes results/figure_geometry_audit.json and prints a summary; exits 1
on any defect.

Usage:  python scripts/audit_figure_geometry.py
Needs:  pdflatex, pdftoppm, Pillow.
"""

import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
FIGDIR = REPO / "paper" / "figures"
OUT = REPO / "results" / "figure_geometry_audit.json"

DPI = 300
PX2MM = 25.4 / DPI
THR = 150  # gray < THR is ink
BORDER_FRAC = 0.45  # band density for a border-band failure
MIN_RUN = 60  # px of continuous ink (~5.1 mm) for crossings/inventory
RECT_RUN = 200  # px min horizontal run for a solid border edge
DASH_W = (3, 22)  # accepted widths of a single dash, px
DASH_SPREAD = 3  # max spread of interior dash widths in a row, px
DASH_GAP_MAX = 30  # max interior gap between dashes, px (word gaps are larger)
DASH_GAP_SPREAD = 4  # max spread of interior gaps in a row, px
DASH_N = 6  # dashes per row to call a row a dashed border
MARGIN = 6  # px inside a rect border treated as its interior

TIKZ_LIBS = "arrows.meta,positioning,calc,fit,backgrounds,shapes.geometric,patterns"

# Per-figure render notes. 'extra' is preamble text; 'pgfplots' loads the
# plots package (results); 'multirow' joins stacked panels with \\[2mm].
FIGURES = {
    "ladder": {"src": "ladder.tex"},
    "architecture": {
        "src": "architecture.tex",
        "extra": "\\usepackage{xspace}\n\\newcommand{\\attck}{ATT\\&CK\\xspace}\n",
    },
    "results": {
        "src": "results.tex",
        "pgfplots": True,
        "multirow": True,
        "width": "8.53cm",
    },  # 0.96 x IEEE column (8.89 cm)
    "grounding": {"src": "grounding.tex"},
    "funnel": {"src": "funnel.tex"},
}


def strip_to_tikzpictures(src: str) -> str:
    """Drop the figure float/caption; keep only tikzpicture blocks."""
    starts = [m.start() for m in re.finditer(r"\\begin\{tikzpicture\}", src)]
    ends = [m.end() for m in re.finditer(r"\\end\{tikzpicture\}", src)]
    if not starts:
        raise ValueError("no tikzpicture found")
    return src[starts[0] : ends[-1]]


def build_tex(name: str, cfg: dict) -> str:
    body = strip_to_tikzpictures((FIGDIR / cfg["src"]).read_text())
    generated = ""
    gen_path = FIGDIR / "generated_values.tex"
    if gen_path.exists():
        # Without these the standalone render compiles undefined macros, so the
        # audit would inspect a different drawing than the paper builds.
        generated = gen_path.read_text()
    if cfg.get("multirow"):
        body = body.replace("\\vspace{2mm}", "\\\\[2mm]")
        if "width" in cfg:  # \linewidth is undefined in standalone class
            body = re.sub(r"(?:0\.96)?\\linewidth", cfg["width"], body)
        body = "\\begin{tabular}{@{}c@{}}\n" + body + "\n\\end{tabular}"
    return (
        "\\documentclass[border=2mm]{standalone}\n"
        "\\usepackage{tikz}\n"
        "\\usetikzlibrary{"
        + TIKZ_LIBS
        + "}\n"
        + ("\\usepackage{pgfplots}\\pgfplotsset{compat=1.17}\n" if cfg.get("pgfplots") else "")
        + (cfg.get("extra", ""))
        + "\\begin{document}\n"
        + generated
        + body
        + "\n\\end{document}\n"
    )


def render(name: str, tex: str, workdir: Path) -> Image.Image:
    (workdir / f"{name}.tex").write_text(tex)
    r = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", f"{name}.tex"],
        cwd=workdir,
        capture_output=True,
        text=True,
        timeout=300,
    )
    log = workdir / f"{name}.log"
    log_text = log.read_text(errors="replace") if log.exists() else ""
    if r.returncode != 0 or re.search(r"^!", log_text, re.M):
        raise RuntimeError(f"pdflatex failed for {name}: see {log}")
    subprocess.run(
        ["pdftoppm", "-r", str(DPI), "-singlefile", "-png", f"{name}.pdf", name], cwd=workdir, check=True, timeout=120
    )
    return Image.open(workdir / f"{name}.png").convert("RGB")


def is_dark(p) -> bool:
    return (p[0] + p[1] + p[2]) / 3 < THR


def runs_in_line(vals, min_len, gap_tol=2):
    """Maximal dark runs along a 1-D bit line, tolerating small gaps."""
    out, start, last = [], None, -(10**9)
    for i, v in enumerate(vals):
        if v:
            if start is None:
                start = i
            last = i
        elif start is not None and i - last > gap_tol:
            if last - start + 1 >= min_len:
                out.append((start, last))
            start = None
    if start is not None and last - start + 1 >= min_len:
        out.append((start, last))
    return out


def solid_rects(rows, w, h):
    edges = []  # clusters of consecutive rows sharing a long horizontal run
    for y in range(h):
        for x0, x1 in runs_in_line(rows[y], RECT_RUN):
            for e in edges:
                if abs(e[0] - x0) <= 6 and abs(e[1] - x1) <= 6 and y - e[3] <= 2:
                    e[3] = y
                    break
            else:
                edges.append([x0, x1, y, y])
    rects, used = [], [False] * len(edges)
    for i, e in enumerate(edges):
        if used[i]:
            continue
        for j in range(i + 1, len(edges)):
            f = edges[j]
            if not used[j] and abs(e[0] - f[0]) <= 4 and abs(e[1] - f[1]) <= 4 and 20 <= f[2] - e[3] <= 1200:
                rects.append((e[0], e[1], e[2], f[3]))
                used[i] = used[j] = True
                break
    return rects


def dashed_rects(rows, w, h):
    """Dash sequences spanning >= 150 px pair into dashed rects (dashed
    node borders). A candidate row segment is a maximal run sequence not
    interrupted by a gap > DASH_GAP_MAX (so unrelated ink on the same row
    starts a new sequence), with >= DASH_N runs of uniform interior width
    and uniform interior gaps. Text rows fail on run-width spread or
    sequence span; solid borders on run width; a lone dashed line has no
    partner row and never forms a rect."""
    cand = []
    for y in range(h):
        rr = runs_in_line(rows[y], 1, gap_tol=1)  # bridges AA-pinholes in dashes
        if len(rr) < DASH_N:
            continue
        # split into maximal sequences at gaps > DASH_GAP_MAX
        segs, start = [], 0
        for i in range(1, len(rr)):
            if rr[i][0] - rr[i - 1][1] - 1 > DASH_GAP_MAX:
                segs.append(rr[start:i])
                start = i
        segs.append(rr[start:])
        for s in segs:
            if len(s) < DASH_N or s[-1][1] - s[0][0] < 150:
                continue
            widths = [b - a + 1 for a, b in s[1:-1]]
            if (
                not widths
                or min(widths) < DASH_W[0]
                or max(widths) > DASH_W[1]
                or max(widths) - min(widths) > DASH_SPREAD
            ):
                continue
            gaps = [s[i + 1][0] - s[i][1] - 1 for i in range(len(s) - 1)]
            gaps = [g for g in gaps if g > 0]
            if len(gaps) < DASH_N - 2 or max(gaps) > DASH_GAP_MAX or max(gaps) - min(gaps) > DASH_GAP_SPREAD:
                continue
            cand.append([s[0][0], s[-1][1], y, y])
    edges = []
    for c in cand:
        for e in edges:
            if abs(e[0] - c[0]) <= 6 and abs(e[1] - c[1]) <= 6 and c[2] - e[3] <= 3:
                e[3] = c[2]
                break
        else:
            edges.append(c)
    rects, used = [], [False] * len(edges)
    for i, e in enumerate(edges):
        if used[i]:
            continue
        for j in range(i + 1, len(edges)):
            f = edges[j]
            if not used[j] and abs(e[0] - f[0]) <= 6 and abs(e[1] - f[1]) <= 6 and 20 <= f[2] - e[3] <= 400:
                rects.append((min(e[0], f[0]), max(e[1], f[1]), e[2], f[3]))
                used[i] = used[j] = True
                break
    return rects


def audit_image(img: Image.Image):
    w, h = img.size
    pix = img.load()
    rows = [[is_dark(pix[x, y]) for x in range(w)] for y in range(h)]
    cols = [[rows[y][x] for y in range(h)] for x in range(w)]
    res = {"render_px": [w, h], "size_mm": [round(w * PX2MM, 1), round(h * PX2MM, 1)], "defects": []}

    # 1. border bands
    bands = []
    for y in (0, 1, h - 2, h - 1):
        if sum(rows[y]) > w * BORDER_FRAC:
            bands.append(f"row y={y}")
    for x in (0, 1, w - 2, w - 1):
        if sum(cols[x]) > h * BORDER_FRAC:
            bands.append(f"col x={x}")
    res["border_bands"] = "clean" if not bands else "ink at: " + ", ".join(bands)
    if bands:
        res["defects"].append("content clipped at canvas border")

    # 2. rects + interior crossing runs
    rects = solid_rects(rows, w, h)
    dashed = dashed_rects(rows, w, h)
    res["rects_solid"] = len(rects)
    res["rects_dashed"] = len(dashed)
    res["rect_coords_solid"] = [list(r) for r in rects]
    res["rect_coords_dashed"] = [list(r) for r in dashed]
    crossings = []

    def scan(rx0, rx1, ry0, ry1, tag):
        for y in range(ry0 + MARGIN, ry1 - MARGIN + 1):
            for a, b in runs_in_line(rows[y][rx0 + MARGIN : rx1 - MARGIN + 1], MIN_RUN):
                crossings.append(
                    f"{tag}: H run y={y} x={rx0 + MARGIN + a}..{rx0 + MARGIN + b} ({(b - a + 1) * PX2MM:.1f}mm)"
                )
        for x in range(rx0 + MARGIN, rx1 - MARGIN + 1):
            for a, b in runs_in_line(cols[x][ry0 + MARGIN : ry1 - MARGIN + 1], MIN_RUN):
                crossings.append(
                    f"{tag}: V run x={x} y={ry0 + MARGIN + a}..{ry0 + MARGIN + b} ({(b - a + 1) * PX2MM:.1f}mm)"
                )

    for r in rects:
        scan(*r, "solid")
    for r in dashed:
        scan(*r, "dashed")
    res["interior_crossings"] = crossings
    if crossings:
        res["defects"].append(f"{len(crossings)} crossing run(s) inside node(s)")

    # 3. inventory of every long run outside rect interiors
    def in_rect(x, y):
        return any(r[0] - MARGIN <= x <= r[1] + MARGIN and r[2] - MARGIN <= y <= r[3] + MARGIN for r in rects + dashed)

    inv = []
    for y in range(h):
        for a, b in runs_in_line(rows[y], MIN_RUN):
            if not in_rect((a + b) // 2, y):
                inv.append(f"H y={y} x={a}..{b} ({(b - a + 1) * PX2MM:.1f}mm)")
    for x in range(w):
        for a, b in runs_in_line(cols[x], MIN_RUN):
            if not in_rect(x, (a + b) // 2):
                inv.append(f"V x={x} y={a}..{b} ({(b - a + 1) * PX2MM:.1f}mm)")
    res["long_run_inventory"] = inv
    res["verdict"] = "pass" if not res["defects"] else "FAIL"
    return res


def run_audit(figure_names=None):
    """Audit FIGURES (or a named subset) and return {name: result dict}.

    Per-figure failures (including render errors) are reported in the
    result as verdict "ERROR" rather than raised, so one broken figure
    does not hide the verdicts of the others. Rendering happens in a
    private temp directory; nothing is written to the repository.
    """
    names = list(FIGURES) if figure_names is None else list(figure_names)
    figures = {}
    with tempfile.TemporaryDirectory(prefix="ragin_figaudit_") as tmp:
        workdir = Path(tmp)
        for name in names:
            cfg = FIGURES[name]
            try:
                img = render(name, build_tex(name, cfg), workdir)
                figures[name] = {"file": f"paper/figures/{cfg['src']}", **audit_image(img)}
            except Exception as exc:  # noqa: BLE001 - report, keep auditing
                figures[name] = {"file": f"paper/figures/{cfg['src']}", "error": str(exc), "verdict": "ERROR"}
    return figures


def main():
    figures = run_audit()
    for name, res in figures.items():
        print(
            f"{name:14s} {res.get('verdict', '?'):5s} "
            f"rects={res.get('rects_solid', '-')}+"
            f"{res.get('rects_dashed', '-')}d "
            f"crossings={len(res.get('interior_crossings', []))} "
            f"defects={res.get('defects', [])}"
        )
    failed = any(r["verdict"] != "pass" for r in figures.values())

    # This audit renders whatever numbers it is handed, so it structurally
    # cannot see a stale generated file; keeping the check here makes one
    # command responsible for the figure surface.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from gen_sp_figures import main as gen_main  # noqa: PLC0415

    sys.argv = [sys.argv[0], "--check"]
    values_current = gen_main() == 0
    print(f"{'figure values':14s} {'OK' if values_current else 'STALE':5s} generated_values.tex vs artifacts")
    failed = failed or not values_current

    OUT.write_text(
        json.dumps(
            {
                "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "method": {
                    "dpi": DPI,
                    "ink_threshold": THR,
                    "border_band_density": BORDER_FRAC,
                    "min_run_px": MIN_RUN,
                    "min_run_mm": round(MIN_RUN * PX2MM, 1),
                    "solid_border_run_px": RECT_RUN,
                    "dash_width_px": DASH_W,
                    "dashes_per_row": DASH_N,
                    "interior_margin_px": MARGIN,
                },
                "figures": figures,
            },
            indent=2,
        )
    )
    print(f"\nwrote {OUT}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
