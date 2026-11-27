#!/usr/bin/env python3
"""The remaining seven paper figures as SVG generators — same design system as
make_fig3_platform_svg.py (Inter + Latin Modern math, ink/slate palette, cards,
pills, chips, hand-checked text widths). Every number is read from the frozen
artifact tables in paper/tops/figs/figdata/. Convert with rsvg-convert.
"""
import math
import re
from pathlib import Path
from xml.sax.saxutils import escape as esc
from PIL import ImageFont

HERE = Path(__file__).resolve().parent
FIGDATA = HERE / '..' / '..' / 'tops' / 'figs' / 'figdata'

FONTS = {
    'sans':  '/usr/share/fonts/opentype/inter/Inter-Regular.otf',
    'bold':  '/usr/share/fonts/opentype/inter/Inter-Bold.otf',
    'ital':  '/usr/share/fonts/opentype/inter/Inter-Italic.otf',
    'mathi': '/usr/share/texmf/fonts/opentype/public/lm/lmroman10-italic.otf',
    'mathr': '/usr/share/texmf/fonts/opentype/public/lm/lmroman10-regular.otf',
    'mono':  '/usr/share/texmf/fonts/opentype/public/lm/lmmono10-regular.otf',
    'lmmath': '/usr/share/texmf/fonts/opentype/public/lm-math/latinmodern-math.otf',
}
SANS = "Inter, 'Helvetica Neue', Arial, sans-serif"
LM = "'Latin Modern Roman', 'LM Roman 10', 'Times New Roman', serif"
LMM = "'Latin Modern Mono', 'LM Mono 10', monospace"
CSS = {
    'sans': (SANS, 400, 'normal'), 'bold': (SANS, 700, 'normal'), 'ital': (SANS, 400, 'italic'),
    'mathi': (LM, 400, 'italic'), 'mathr': (LM, 400, 'normal'), 'mono': (LMM, 400, 'normal'),
    'lmmath': ("'Latin Modern Math', 'LM Math', serif", 400, 'normal'),
}
_cache = {}
def F(kind, size):
    k = (kind, round(size, 2))
    if k not in _cache:
        _cache[k] = ImageFont.truetype(FONTS['lmmath' if kind == 'bhat' else kind], size)
    return _cache[k]
def msize(kind, size):
    return size * 1.14 if kind in ('mathi', 'mathr', 'bhat', 'lmmath') else size
def tw(s, kind, size):
    return F(kind, msize(kind, size)).getlength(s)

WARN = []
def chk(label, s, kind, size, maxw):
    w = tw(s, kind, size)
    if w > maxw:
        WARN.append(f'OVERFLOW {label}: "{s}" {w:.0f} > {maxw}')
    return w

INK, SLATE, MUTED = '#0F172A', '#334155', '#64748B'
BLUE = dict(hdr='#1E40AF', line='#3B63E8', band='#F2F6FF', tint='#DCE7FF', soft='#9DB6FF')
AMB  = dict(hdr='#9A5B0B', line='#D97706', band='#FFF8EB', tint='#FDE9C0', soft='#F5C16C')
GRN  = dict(hdr='#05694B', line='#0E9F6E', band='#EFFAF5', tint='#CFF1E2', soft='#6FCFA8')
ROSE = dict(hdr='#BE123C', line='#E11D48', band='#FFF1F4', tint='#FFD9E1', soft='#FDA4B8', dark='#9F1239')
VIO  = dict(hdr='#4C1D95', line='#7C3AED', band='#F5F3FF', tint='#E4DAFF', soft='#B49CF5')
GRID, AXIS = '#E2E8F0', '#94A3B8'

def txt(x, y, s, size=13, kind='sans', fill=INK, anchor='start', op=1):
    fam, w, st = CSS[kind]
    o = f' fill-opacity="{op}"' if op != 1 else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" font-weight="{w}" '
            f'font-style="{st}" fill="{fill}"{o} text-anchor="{anchor}" xml:space="preserve">{esc(s)}</text>')

def rich(x, y, parts, size=12.5, fill=INK, anchor='start', ang=None):
    """parts: [(text, kind[, fill])]. ang = rotation applied to the whole run."""
    parts = [('\U0001D6BF', 'bhat') + tuple(p[2:]) if p[1] == 'bhat' else p for p in parts]
    widths = [tw(p[0], p[1], size) for p in parts]
    total = sum(widths)
    cx = x if anchor == 'start' else (x - total / 2 if anchor == 'middle' else x - total)
    out = []
    for p, w in zip(parts, widths):
        t, kind = p[0], p[1]
        col = p[2] if len(p) > 2 else fill
        if kind == 'bhat':
            fs = msize('bhat', size)
            out.append(txt(cx, y, t, fs, 'lmmath', col))
            l, tp, r, b = F('bhat', fs).getbbox(t, anchor='ls')
            hx = cx + w * 0.58
            hy = y + tp - 1.6
            hh, hw = fs * 0.16, fs * 0.20
            out.append(f'<path d="M{hx-hw:.1f},{hy+hh:.1f} L{hx:.1f},{hy:.1f} L{hx+hw:.1f},{hy+hh:.1f}" '
                       f'fill="none" stroke="{col}" stroke-width="1.15" stroke-linecap="round" stroke-linejoin="round"/>')
        else:
            fs = msize(kind, size)
            out.append(txt(cx, y, t, fs, kind, col))
        cx += w
    body = ''.join(out)
    if ang:
        return f'<g transform="rotate({ang} {x:.1f} {y:.1f})">{body}</g>'
    return body

def rotg(x, y, ang, inner):
    return f'<g transform="rotate({ang} {x:.1f} {y:.1f})">{inner}</g>'

def rect(x, y, w, h, rx=8, fill='none', stroke='none', sw=1.5, extra=''):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'

def card(x, y, w, h, stroke, fill='#FFFFFF', sw=1.6, rx=10):
    return rect(x, y + 2.5, w, h, rx, '#0F172A', 'none', 0, 'fill-opacity="0.09"') + \
           rect(x, y, w, h, rx, fill, stroke, sw)

def arrow(pts, color, sw=2.0, head=7.5, dash=None):
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    d = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / d, (y1 - y0) / d
    bx, by = x1 - ux * head, y1 - uy * head
    px, py = -uy, ux
    path = 'M' + ' L'.join(f'{a:.1f},{b:.1f}' for a, b in pts[:-1]) + f' L{bx + ux*1.2:.1f},{by + uy*1.2:.1f}'
    da = f' stroke-dasharray="{dash}"' if dash else ''
    return (f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"{da}/>'
            f'<path d="M{x1:.1f},{y1:.1f} L{bx+px*head*0.48:.1f},{by+py*head*0.48:.1f} '
            f'L{bx-px*head*0.48:.1f},{by-py*head*0.48:.1f} Z" fill="{color}"/>')

def pill(cx, cy, text, size=12.5, pad=16, bg='#FFFFFF', ec='#94A3B8', tc=None, bold=False):
    w = tw(text, 'sans', size) + 2 * pad
    o = rect(cx - w / 2, cy - 13, w, 26, 13, bg, ec, 1.2)
    o += txt(cx, cy + 4.4, text, size, 'bold' if bold else 'sans', tc or SLATE, 'middle')
    return o

def line(x0, y0, x1, y1, color, sw=1.5, dash=None, cap='round'):
    da = f' stroke-dasharray="{dash}"' if dash else ''
    return f'<path d="M{x0:.1f},{y0:.1f} L{x1:.1f},{y1:.1f}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="{cap}"{da}/>'

def capsule(x0, x1, y, color, sw=7, op=0.85):
    return f'<path d="M{x0:.1f},{y:.1f} L{x1:.1f},{y:.1f}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-opacity="{op}"/>'

def dot(x, y, color, r=4.5, ring=False):
    if ring:
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#FFFFFF" stroke="{color}" stroke-width="1.7"/>'
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" stroke="#FFFFFF" stroke-width="1.4"/>'

def msquare(x, y, color, s=8):
    return f'<rect x="{x-s/2:.1f}" y="{y-s/2:.1f}" width="{s}" height="{s}" fill="{color}" stroke="#FFFFFF" stroke-width="1.3"/>'

def mtri(x, y, color, s=8.5):
    return (f'<path d="M{x:.1f},{y-s/2:.1f} L{x+s/2:.1f},{y+s/2:.1f} L{x-s/2:.1f},{y+s/2:.1f} Z" '
            f'fill="{color}" stroke="#FFFFFF" stroke-width="1.3"/>')

def mdiamond(x, y, color, s=9):
    return (f'<path d="M{x:.1f},{y-s/2:.1f} L{x+s/2:.1f},{y:.1f} L{x:.1f},{y+s/2:.1f} L{x-s/2:.1f},{y:.1f} Z" '
            f'fill="{color}" stroke="#FFFFFF" stroke-width="1.3"/>')

def mring(x, y, color, s=9):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{s/2}" fill="#FFFFFF" stroke="{color}" stroke-width="1.7"/>'

def read_dat(name):
    lines = (FIGDATA / (name + '.dat')).read_text().strip().split('\n')
    hdr = lines[0].split('\t')
    return hdr, [{k: v for k, v in zip(hdr, ln.split('\t'))} for ln in lines[1:]]

def rv(name):
    m = re.search(r'\\def\\%s\{([\d.]+)\}' % name, (FIGDATA / 'fig3_r.tex').read_text())
    return m.group(1) if m else ''

def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w*0.5074:.1f}pt" height="{h*0.5074:.1f}pt">' + body + '</svg>')

# ======================================================================
# FIG 2 — onset dichotomy
# ======================================================================
def fig2():
    S = []; add = S.append
    W, H = 780, 430
    add(rect(0, 0, W, H, 0, '#FFFFFF'))
    panels = [('a', 'δ = 0.2', 'd02', 48, 375), ('b', 'δ = 0.4', 'd04', 425, 750)]
    ymap = lambda v: 320 - (v - 0.30) / (1.03 - 0.30) * 245
    xmap = lambda m, x0, x1: x0 + (math.log10(m) - math.log10(4.2)) / (math.log10(100) - math.log10(4.2)) * (x1 - x0)
    for letter, title, tag, x0, x1 in panels:
        add(txt((x0+x1)/2, 42, title, 14, 'mathr', INK, 'middle'))
        add(txt(x0 + 6, 66, f'({letter})', 13, 'bold', INK))
        add(rect(x0, 75, x1 - x0, 250, 0, 'none', AXIS, 1.1))
        for gv in (0.4, 0.6, 0.8, 1.0):
            add(line(x0, ymap(gv), x1, ymap(gv), GRID, 1))
            add(txt(x0 - 8, ymap(gv) + 4, f'{gv:.1f}', 10.5, 'sans', SLATE, 'end'))
        add(txt(x0 - 8, ymap(0.3) + 4, '0.3', 10.5, 'sans', SLATE, 'end'))
        for tv in (5, 10, 20, 40, 80):
            xx = xmap(tv, x0, x1)
            add(line(xx, 325, xx, 330, AXIS, 1.1))
            add(txt(xx, 346, str(tv), 10.5, 'sans', SLATE, 'middle'))
        add(rotg((x0+x1)/2, 362, 0, txt((x0+x1)/2, 362, 'observation horizon ', 12, 'sans', INK, 'middle') +
                 rich(0, 0, [('M', 'mathi')], 12.5, INK) if False else ''))
        add(rich((x0+x1)/2, 366, [('observation horizon ', 'sans'), ('M', 'mathi')], 12.5, INK, 'middle'))
        add(line(x0, ymap(0.5), x1, ymap(0.5), MUTED, 1, dash='1.5 2.5'))
        if letter == 'a':
            add(txt(x0 + 10, ymap(0.5) - 5, 'chance', 10, 'ital', MUTED))
        add(rect(x0, ymap(0.44), x1 - x0, ymap(0.335) - ymap(0.44), 4, AMB['tint'], 'none', 0))
        if letter == 'a':
            add(txt((x0+x1)/2, ymap(0.335) - 6, 'N₀ = 10 floor regime', 10, 'ital', AMB['hdr'], 'middle'))
        else:
            add(txt(x1 - 8, ymap(0.335) - 6, 'both floors < δ', 10, 'ital', MUTED, 'end'))
    for letter, tag, x0, x1 in [('a', 'd02', 48, 375), ('b', 'd04', 425, 750)]:
        hdr, known = read_dat(f'fig2_{tag}_known')
        _, birth = read_dat(f'fig2_{tag}_birth')
        px = [xmap(float(r['m']), x0, x1) for r in known]
        for key, c, mk in (('a10', AMB['line'], 'o'), ('a40', BLUE['line'], 's')):
            py = [ymap(float(r[key])) for r in known]
            add(line(px[0], py[0], px[-1], py[-1], c, 2.2))
            for xx, yy in zip(px, py):
                add(dot(xx, yy, c, 4.2) if mk == 'o' else msquare(xx, yy, c, 7.6))
        px = [xmap(float(r['m']), x0, x1) for r in birth]
        py = [ymap(float(r['auc'])) for r in birth]
        add(line(px[0], py[0], px[-1], py[-1], MUTED, 1.8, dash='5 3.5'))
        for xx, yy in zip(px, py):
            add(mtri(xx, yy, MUTED, 7.6))
        ep = known[-1]
        add(txt(px[-1] - 9, ymap(float(ep['a40'])) + 3.5, f"{float(ep['a40']):.2f}", 10, 'bold', BLUE['line'], 'end'))
        add(txt(px[-1] - 9, ymap(float(ep['a10'])) - 2, f"{float(ep['a10']):.2f}", 10, 'bold', AMB['line'], 'end'))
    add(rotg(22, 200, -90, txt(22, 200, 'detection AUC', 12.5, 'sans', INK, 'middle')))
    ly = 405
    lx = 150
    add(line(lx, ly, lx + 34, ly, AMB['line'], 2.2)); add(dot(lx + 17, ly, AMB['line'], 4.2))
    add(txt(lx + 42, ly + 4, 'known onset, N₀ = 10', 11.5, 'sans', INK)); lx += 210
    add(line(lx, ly, lx + 34, ly, BLUE['line'], 2.2)); add(msquare(lx + 17, ly, BLUE['line'], 7.6))
    add(txt(lx + 42, ly + 4, 'known onset, N₀ = 40', 11.5, 'sans', INK)); lx += 210
    add(line(lx, ly, lx + 34, ly, MUTED, 1.8, dash='5 3.5')); add(mtri(lx + 17, ly, MUTED, 7.6))
    add(txt(lx + 42, ly + 4, 'birth onset (self-test)', 11.5, 'sans', INK))
    return svg(W, H, ''.join(S))

# ======================================================================
# FIG 4 — dose-response (E1)
# ======================================================================
def fig4():
    S = []; add = S.append
    W, H = 780, 500
    add(rect(0, 0, W, H, 0, '#FFFFFF'))
    x0, x1, y0, y1 = 92, 740, 70, 415
    X = lambda v: x0 + v * (x1 - x0)
    Y = lambda v: y1 - v * (y1 - y0)
    add(rect(x0, y0, x1 - x0, y1 - y0, 0, 'none', AXIS, 1.1))
    for gv in (0, 0.2, 0.4, 0.6, 0.8, 1.0):
        add(line(x0, Y(gv), x1, Y(gv), GRID, 1))
        add(txt(x0 - 10, Y(gv) + 4, f'{gv:.1f}', 10.5, 'sans', SLATE, 'end'))
    for tv in (0, 0.25, 0.5, 0.75, 1.0):
        add(line(X(tv), y1, X(tv), y1 + 5, AXIS, 1.1))
        add(txt(X(tv), y1 + 24, f'{tv:g}', 10.5, 'sans', SLATE, 'middle'))
    add(rich((x0+x1)/2, y1 + 48, [('injected belief dose ', 'sans'), ('d', 'mathi')], 12.5, INK, 'middle'))
    add(rotg(26, (y0+y1)/2, -90, rich(26, (y0+y1)/2, [('measured ', 'sans'), ('β', 'bhat')], 12.5, INK, 'middle')))
    add(line(X(0), Y(0), X(1), Y(1), MUTED, 1.6, dash='6 4'))
    fams = [('authority forgery', 'fig3_fam1', BLUE['line'], 'o', 'One'),
            ('state deception', 'fig3_fam2', AMB['line'], 's', 'Two'),
            ('goal subversion', 'fig3_fam3', GRN['line'], 't', 'Three'),
            ('epistemic echo', 'fig3_fam4', ROSE['line'], 'd', 'Four'),
            ('exfiltration lure', 'fig3_fam5', VIO['line'], 'p', 'Five')]
    mk = {'o': lambda x, y, c: dot(x, y, c, 4.6), 's': lambda x, y, c: msquare(x, y, c, 8),
          't': lambda x, y, c: mtri(x, y, c, 8.5), 'd': lambda x, y, c: mdiamond(x, y, c, 9),
          'p': lambda x, y, c: f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.6" fill="{c}" stroke="#FFFFFF" stroke-width="1.4"/>'
                               f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.8" fill="#FFFFFF"/>'}
    ly = y0 + 22
    for name, t, c, m, rn in fams:
        add(line(x0 + 16, ly, x0 + 52, ly, c, 2.2))
        add(mk[m](x0 + 34, ly, c))
        add(rich(x0 + 60, ly + 4, [(f'{name}  (', 'sans'), ('r', 'mathi'), (' = ', 'mathr'),
                                   (rv(f'figThreeR{rn}'), 'mathr'), (')', 'sans')], 12, INK))
        ly += 20
    add(line(x0 + 16, ly, x0 + 52, ly, MUTED, 1.6, dash='6 4'))
    add(rich(x0 + 60, ly + 4, [('ideal ', 'sans'), ('β', 'bhat'), (' = ', 'mathr'), ('d', 'mathi')], 12, SLATE))
    add(rect(x0 + 8, y0 + 12, 240, ly - y0 - 2, 8, '#FFFFFF', GRID, 1.1))
    ly = y0 + 22
    for name, t, c, m, rn in fams:
        add(line(x0 + 16, ly, x0 + 52, ly, c, 2.2))
        add(mk[m](x0 + 34, ly, c))
        add(rich(x0 + 60, ly + 4, [(f'{name}  (', 'sans'), ('r', 'mathi'), (' = ', 'mathr'),
                                   (rv(f'figThreeR{rn}'), 'mathr'), (')', 'sans')], 12, INK))
        ly += 20
    add(line(x0 + 16, ly, x0 + 52, ly, MUTED, 1.6, dash='6 4'))
    add(rich(x0 + 60, ly + 4, [('ideal ', 'sans'), ('β', 'bhat'), (' = ', 'mathr'), ('d', 'mathi')], 12, SLATE))
    for name, t, c, m, rn in fams:
        hdr, pts = read_dat(t)
        px = [X(float(r['d'])) for r in pts]
        py = [Y(float(r['b'])) for r in pts]
        add(line(px[0], py[0], px[-1], py[-1], c, 2.0))
        for r, xx, yy in zip(pts, px, py):
            elo, ehi = float(r['elo']), float(r['ehi'])
            add(line(xx, Y(float(r['b']) - elo), xx, Y(float(r['b']) + ehi), c, 1.3))
            add(mk[m](xx, yy, c))
    return svg(W, H, ''.join(S))

# ======================================================================
# FIG 5 — policy benchmark (T3)
# ======================================================================
def fig5():
    S = []; add = S.append
    W, H = 780, 445
    add(rect(0, 0, W, H, 0, '#FFFFFF'))
    x0, x1, y0, y1 = 92, 740, 65, 350
    X = lambda v: x0 + (math.log10(v) - math.log10(21)) / (math.log10(1050) - math.log10(21)) * (x1 - x0)
    Y = lambda v: y1 - (v - 0.02) / (0.19 - 0.02) * (y1 - y0)
    add(rect(x0, y0, x1 - x0, y1 - y0, 0, 'none', AXIS, 1.1))
    for gv in (0.05, 0.10, 0.15):
        add(line(x0, Y(gv), x1, Y(gv), GRID, 1))
        add(txt(x0 - 10, Y(gv) + 4, f'{gv:.2f}', 10.5, 'sans', SLATE, 'end'))
    for tv in (25, 50, 100, 200, 400):
        add(line(X(tv), y1, X(tv), y1 + 5, AXIS, 1.1))
        add(txt(X(tv), y1 + 24, str(tv), 10.5, 'sans', SLATE, 'middle'))
    add(rich((x0+x1)/2, y1 + 46, [('probe budget ', 'sans'), ('n', 'mathi')], 12.5, INK, 'middle'))
    add(rotg(26, (y0+y1)/2, -90, txt(26, (y0+y1)/2, 'mean profile error', 12.5, 'sans', INK, 'middle')))
    hdr, pts = read_dat('fig4_policy')
    px = [X(float(r['n'])) for r in pts]
    series = [('uni', INK, 'o', 'uniform', None), ('ney', BLUE['line'], 's', 'Neyman (variance-equal)', None),
              ('ucb', ROSE['line'], 't', 'UCB-lite (regret)', '6 4'), ('psi', AMB['line'], 'o', 'PSI (information)', '6 4')]
    for key, c, m, lab, dash in series:
        py = [Y(float(r[key])) for r in pts]
        add(line(px[0], py[0], px[-1], py[-1], c, 2.2, dash=dash))
        for xx, yy in zip(px, py):
            add(dot(xx, yy, c, 4.2) if m == 'o' else (msquare(xx, yy, c, 7.6) if m == 's' else mtri(xx, yy, c, 8)))
    last = pts[-1]
    add(txt(px[-1], Y(float(last['psi'])) - 11, '0.129', 10, 'bold', AMB['line'], 'middle'))
    add(txt(px[-1] + 10, Y(float(last['ucb'])), '0.121', 10, 'bold', ROSE['line']))
    add(txt(px[-1] + 4, Y(float(last['uni'])) + 16, '0.035', 10, 'bold', SLATE))
    bx = px[-1] + 30
    add(arrow([(bx, Y(0.035)), (bx, Y(0.121))], ROSE['line'], 1.8, 7))
    add(txt(bx + 10, (Y(0.035)+Y(0.121))/2 + 4, '3.5×', 11, 'bold', ROSE['line']))
    lx, ly = x1 - 216, y0 + 22
    add(rect(lx - 10, ly - 14, 226, len(series)*19 + 10, 8, '#FFFFFF', GRID, 1.1))
    for key, c, m, lab, dash in series:
        add(line(lx, ly, lx + 34, ly, c, 2.2, dash=dash))
        add(dot(lx + 17, ly, c, 4.2) if m == 'o' else (msquare(lx + 17, ly, c, 7.6) if m == 's' else mtri(lx + 17, ly, c, 8)))
        add(txt(lx + 42, ly + 4, lab, 11.5, 'sans', INK))
        ly += 19
    return svg(W, H, ''.join(S))

# ======================================================================
# FIG 6 — field null horizontal intervals (E2)
# ======================================================================
def fig6():
    S = []; add = S.append
    W, H = 780, 470
    add(rect(0, 0, W, H, 0, '#FFFFFF'))
    x0, x1 = 205, 745
    X = lambda v: x0 + v / 0.25 * (x1 - x0)
    hdr, pts = read_dat('fig5_field')
    _, bcg = read_dat('fig5_bcg')
    cap = 0.0601739
    FAMS = ['authority forgery', 'state deception', 'goal subversion', 'epistemic echo', 'exfiltration lure']
    ys = {i: 88 + i * 54 for i in range(5)}
    by1 = ys[4] + 54 + 30
    by2 = by1 + 42
    ymin, ymax = by2 + 26, ys[0] - 46
    add(rect(X(0), ys[0] - 24, X(cap) - X(0), ys[4] + 24 - (ys[0] - 24), 10, BLUE['band'], 'none', 0))
    for tv in (0, 0.05, 0.10, 0.15, 0.20, 0.25):
        add(line(X(tv), ymin, X(tv), ymax + 8, GRID if tv else AXIS, 1 if tv else 1.2))
        add(txt(X(tv), ymax + 24, f'{tv:.2f}', 10.5, 'sans', SLATE, 'middle'))
    add(txt((x0+x1)/2, ymax + 50, 'measured value (95% CI)', 12.5, 'sans', INK, 'middle'))
    add(line(X(cap), ys[0] - 30, X(cap), ys[4] + 26, INK, 1.2, dash='1.5 2.5'))
    add(txt(X(cap) + 6, ys[0] - 34, 'Wilson upper bound 0.060', 9.5, 'sans', SLATE))
    add(line(X(0.2), ymin, X(0.2), ymax + 8, MUTED, 1.3, dash='5 3.5'))
    add(rich(X(0.2) - 7, ymin - 2, [('τ', 'mathr'), (' = 0.2', 'sans')], 10, SLATE, 'end'))
    add(arrow([(X(0), ys[0] - 26), (X(cap), ys[0] - 26)], BLUE['line'], 1.4, 6))
    add(txt((X(0)+X(cap))/2, ys[0] - 34, '0.060', 9.5, 'bold', BLUE['line'], 'middle'))
    for i, y in ys.items():
        add(txt(x0 - 14, y + 4, FAMS[i], 11, 'bold', INK, 'end'))
        for off, v, up, c in [(14, float(pts[i]['b1']), float(pts[i]['u1']), BLUE['line']),
                              (-14, float(pts[i]['b2']), float(pts[i]['u2']), AMB['line'])]:
            yy = y + off
            add(capsule(X(v), X(up), yy, c, 8, 0.9))
            add(dot(X(v), yy, c, 4.6))
    add(line(x0 - 14, (ys[4] + 24 + by1 - 14) / 2 + 4, x1 + 10, (ys[4] + 24 + by1 - 14) / 2 + 4, '#D9D9D9', 1))
    for j, y in enumerate([by1, by2]):
        nm = ['confidentiality', 'action safety'][j]
        add(txt(x0 - 14, y + 4, nm, 10.5, 'ital', SLATE, 'end'))
        for off, c in [(14, BLUE['line']), (-14, AMB['line'])]:
            add(dot(X(0), y + off, c, 4.6))
    mac = (FIGDATA / 'fig5_macros.tex').read_text()
    r1 = re.search(r'figFiveRateOne\{([\d.]+)\}', mac).group(1)
    r2 = re.search(r'figFiveRateTwo\{([\d.]+)\}', mac).group(1)
    lx = 230
    add(line(lx, 30, lx + 34, 30, BLUE['line'], 2.2)); add(dot(lx + 17, 30, BLUE['line'], 4.4))
    add(txt(lx + 42, 34, f'gpt-5.6 · {r1}% turns unavailable', 11, 'sans', INK))
    lx2 = lx + 42 + tw(f'gpt-5.6 · {r1}% turns unavailable', 'sans', 11) + 28
    add(line(lx2, 30, lx2 + 34, 30, AMB['line'], 2.2)); add(dot(lx2 + 17, 30, AMB['line'], 4.4))
    add(txt(lx2 + 42, 34, f'gpt-6.1 · {r2}% turns unavailable', 11, 'sans', INK))
    return svg(W, H, ''.join(S))

# ======================================================================
# FIG 7 — certification strips (E4)
# ======================================================================
def fig7():
    S = []; add = S.append
    W, H = 780, 640
    add(rect(0, 0, W, H, 0, '#FFFFFF'))
    strips = [('Naive', 'fig6_naive', ROSE, 'NOT CERTIFIED', 45),
              ('Hardened', 'fig6_hardened', ROSE, 'NOT CERTIFIED', 240),
              ('Resistant', 'fig6_resistant', GRN, 'CERTIFIED', 435)]
    SH = 135
    x0, x1 = 125, 755
    X = lambda i: x0 + (i + 0.4) / 4.8 * (x1 - x0)
    for name, t, C, verdict, y0 in strips:
        hdr, pts = read_dat(t)
        y1 = y0 + SH
        tau = y1 - 0.2 / 1.09 * SH
        add(rect(x0, y0, x1 - x0, SH, 8, ROSE['band'], 'none', 0))
        add(rect(x0, tau - (y1 - y0) + SH if False else y0, x1 - x0, tau - y0, 0, ROSE['tint'], 'none', 0))
        add(line(x0, tau, x1, tau, MUTED, 1.3, dash='5 3.5'))
        for gv in (0.5, 1.0):
            gy = y1 - gv / 1.09 * SH
            add(line(x0, gy, x1, gy, GRID, 1))
            add(txt(x0 - 8, gy + 4, f'{gv:.1f}', 10, 'sans', SLATE, 'end'))
        add(txt(x0 - 8, y1 + 4, '0.0', 10, 'sans', SLATE, 'end'))
        for r in pts:
            i = int(r['i']); b = float(r['b']); lo = float(r['lo']); up = float(r['up'])
            xx = X(i); lob = b - lo
            add(line(xx, y1 - lob / 1.09 * SH, xx, y1 - min(b + up, 1.06) / 1.09 * SH, BLUE['line'], 1.6))
            add(dot(xx, y1 - b / 1.09 * SH, BLUE['line'], 4.6))
            add(dot(xx, y1 - lob / 1.09 * SH, BLUE['line'], 4.2, ring=True))
        if verdict != 'CERTIFIED':
            vx = x0 + 14 if name == 'Naive' else None
            if vx:
                add(txt(vx, tau - 16, verdict, 12.5, 'bold', C['hdr']))
            else:
                add(txt(x1 - 14, tau - 16, verdict, 12.5, 'bold', C['hdr'], 'end'))
        else:
            add(txt(x0 + 14, y1 - 14, verdict, 12.5, 'bold', GRN['hdr']))
            add(txt(x0 + 150, y0 + 24, 'open marker = Wilson lower bound', 10, 'sans', SLATE))
        add(txt(92, (y0+y1)/2 + 4, name, 12.5, 'bold', INK, 'end'))
    FAMS = ['authority\nforgery', 'state\ndeception', 'goal\nsubversion', 'epistemic\necho', 'exfiltration\nlure']
    for i in range(5):
        for k, w in enumerate(FAMS[i].split('\n')):
            add(txt(X(i), 580 + k * 13, w, 9.5, 'bold', INK, 'middle'))
    add(txt((x0+x1)/2, 614, 'probe family', 12, 'sans', INK, 'middle'))
    return svg(W, H, ''.join(S))

# ======================================================================
# FIG 8 — limits of certification (E6 schematic + E7 bars)
# ======================================================================
def fig8():
    S = []; add = S.append
    W, H = 780, 400
    add(rect(0, 0, W, H, 0, '#FFFFFF'))
    add(txt(30, 34, '(a)', 13, 'bold', INK))
    def cbox(x, y, w, h, C, title, lines, hot=False):
        o = card(x, y, w, h, ROSE['line'] if hot else GRN['line'], ROSE['band'] if hot else '#FFFFFF', 2.0 if hot else 1.5)
        o += txt(x + 14, y + 24, title, 13, 'bold', ROSE['dark'] if hot else INK)
        o += ''.join(txt(x + 14, y + 42 + k * 16, ln, 11.5, 'sans', SLATE) for k, ln in enumerate(lines))
        return o
    add(cbox(28, 60, 118, 76, GRN, 'retriever A', ['local β̂ = 0', 'certified']))
    add(cbox(166, 60, 130, 76, AMB, 'interface', ['(tool:retriever)', 'doc contains sA']))
    add(cbox(316, 60, 124, 76, GRN, 'orchestrator B', ['local β̂ = 0', 'certified']))
    add(arrow([(146, 98), (164, 98)], SLATE, 1.8, 6.5))
    add(arrow([(296, 98), (314, 98)], SLATE, 1.8, 6.5))
    add(arrow([(231, 138), (231, 196)], ROSE['line'], 2.2, 7.5))
    add(txt(242, 172, 'sA', 12, 'mathi', ROSE['dark']))
    add(cbox(100, 200, 266, 62, ROSE, 'composed pipeline  β̂ = 1.0',
             ['(20/20 breaches, Wilson [0.84, 1.00])'], hot=True))
    add(txt(233, 284, 'no component is individually non-compliant', 11, 'ital', MUTED, 'middle'))
    # ---- bars
    bx0, bx1, by0, by1 = 505, 760, 70, 300
    add(txt(470, 34, '(b)', 13, 'bold', INK))
    X = lambda i: bx0 + 50 + i * 92
    Y = lambda v: by1 - v / 1.32 * (by1 - by0)
    add(rect(bx0, by0, bx1 - bx0, by1 - by0, 0, 'none', AXIS, 1.1))
    for gv in (0, 0.4, 0.8, 1.2):
        add(line(bx0, Y(gv), bx1, Y(gv), GRID, 1))
        add(txt(bx0 - 8, Y(gv) + 4, f'{gv:.1f}', 10, 'sans', SLATE, 'end'))
    _, pts = read_dat('fig7_gaming')
    BW = 26
    for r in pts:
        i = int(r['i']); pub = float(r['pub']); held = float(r['held'])
        if pub > 0:
            add(rect(X(i) - BW - 3, Y(pub), BW, by1 - Y(pub), 3, BLUE['line'], 'none', 0))
        if held > 0:
            add(rect(X(i) + 3, Y(held), BW, by1 - Y(held), 3, AMB['line'], 'none', 0))
    add(line(bx0, Y(0.2), bx1, Y(0.2), MUTED, 1.3, dash='5 3.5'))
    add(rich(bx1 - 6, Y(0.2) - 7, [('τ', 'mathr'), (' = 0.2', 'sans')], 10, SLATE, 'end'))
    for r, nm in zip(pts, ['Probe\nAware', 'Semantics\nOnly', 'Resistant']):
        i = int(r['i'])
        for k, w in enumerate(nm.split('\n')):
            add(txt(X(i), by1 + 16 + k * 13, w, 9.5, 'bold', INK, 'middle'))
    add(txt((bx0+bx1)/2, by1 + 52, 'foil', 12, 'sans', INK, 'middle'))
    add(rotg(bx0 - 30, (by0+by1)/2, -90, rich(bx0 - 30, (by0+by1)/2, [('mean family ', 'sans'), ('β', 'bhat')], 12, INK, 'middle')))
    add(arrow([(X(0) + BW + 12, Y(0)), (X(0) + BW + 12, Y(1.0))], '#9333EA', 1.6, 6.5))
    add(rotg(X(0) + BW + 12 - 14, (Y(0)+Y(1.0))/2, -90,
             rich(X(0) + BW + 12 - 14, (Y(0)+Y(1.0))/2, [('Γ', 'mathr'), (' = 1.0', 'sans')], 10, '#9333EA', 'middle')))
    add(rich(X(1), Y(1.06), [('Γ', 'mathr'), (' = 0', 'sans')], 10, '#9333EA', 'middle'))
    add(rich(X(2), Y(1.06), [('Γ', 'mathr'), (' = 0', 'sans')], 10, '#9333EA', 'middle'))
    ly = by1 + 76
    add(rect(bx0 + 22, ly - 8, 14, 14, 3, BLUE['line'], 'none', 0))
    add(txt(bx0 + 42, ly + 4, 'public probes', 11, 'sans', INK))
    add(rect(bx0 + 124, ly - 8, 14, 14, 3, AMB['line'], 'none', 0))
    add(txt(bx0 + 144, ly + 4, 'held-out paraphrases', 11, 'sans', INK))
    return svg(W, H, ''.join(S))

# ======================================================================
# FIG 9 — deception release (E15 bars + E16 frontier)
# ======================================================================
def fig9():
    S = []; add = S.append
    W, H = 780, 435
    add(rect(0, 0, W, H, 0, '#FFFFFF'))
    add(txt(30, 34, '(a)', 13, 'bold', INK))
    bx0, bx1, by0, by1 = 62, 350, 70, 300
    X = lambda i: bx0 + 58 + i * 95
    Y = lambda v: by1 - v / 1.18 * (by1 - by0)
    add(rect(bx0, by0, bx1 - bx0, by1 - by0, 0, 'none', AXIS, 1.1))
    for gv in (0, 0.5, 1.0):
        add(line(bx0, Y(gv), bx1, Y(gv), GRID, 1))
        add(txt(bx0 - 8, Y(gv) + 4, f'{gv:.1f}', 10, 'sans', SLATE, 'end'))
    add(line(bx0, Y(1.0), bx1 + 12, Y(1.0), '#B9B4AC', 1.2, dash='1.5 2.5'))
    _, pts = read_dat('fig8_release')
    BW = 30
    cols = [BLUE['line'], '#64748B', GRN['line']]
    names = ['honest\nrelease', 'silence\n(uniform)', 'decoy\nrelease']
    for r, c, nm in zip(pts, cols, names):
        i = int(r['i']); v = float(r['v'])
        if v > 0:
            add(rect(X(i) - BW/2, Y(v), BW, by1 - Y(v), 4, c, 'none', 0))
        add(txt(X(i), Y(max(v, 0)) - 8, f'{v:.2f}', 10, 'bold', c, 'middle'))
        for k, w in enumerate(nm.split('\n')):
            add(txt(X(i), by1 + 16 + k * 13, w, 9.5, 'bold', INK, 'middle'))
    add(arrow([(X(2) + 42, Y(0.02)), (X(2) + 42, Y(1.0))], '#9333EA', 1.6, 6.5))
    add(rotg(X(2) + 50, (Y(0.02)+Y(1.0))/2, -90,
             rich(X(2) + 50, (Y(0.02)+Y(1.0))/2, [('Δ', 'mathr'), ('dec', 'sans'), (' = 1.000', 'sans')], 10, '#9333EA', 'middle')))
    add(txt((bx0+bx1)/2, by1 + 52, 'release policy', 12, 'sans', INK, 'middle'))
    add(rotg(28, (by0+by1)/2, -90, txt(28, (by0+by1)/2, 'attacker per-attempt success', 11, 'sans', INK, 'middle')))
    # ---- (b) frontier
    add(txt(430, 34, '(b)', 13, 'bold', INK))
    cx0, cx1, cy0, cy1 = 505, 762, 70, 300
    CX = lambda m: cx0 + (m - 0.48) / (1.0 - 0.48) * (cx1 - cx0)
    CY = lambda v: cy1 - (math.log10(max(v, 1.0))) / (math.log10(8000)) * (cy1 - cy0)
    add(rect(cx0, cy0, cx1 - cx0, cy1 - cy0, 0, 'none', AXIS, 1.1))
    add(rect(CX(0.93), cy0, cx1 - CX(0.93), cy1 - cy0, 8, ROSE['band'], 'none', 0))
    add(rotg(CX(0.965), (cy0+cy1)/2, -90, txt(CX(0.965), (cy0+cy1)/2, 'undetectable', 10, 'bold', ROSE['line'], 'middle')))
    for gv in (1, 10, 100, 1000):
        add(line(cx0, CY(gv), cx1, CY(gv), GRID, 1))
        add(txt(cx0 - 8, CY(gv) + 4, ['1', '10', '10²', '10³'][(0 if gv == 1 else int(math.log10(gv)))], 9.5, 'sans', SLATE, 'end'))
    for tv in (0.5, 0.6, 0.8, 1.0):
        add(line(CX(tv), cy1, CX(tv), cy1 + 5, AXIS, 1.1))
        add(txt(CX(tv), cy1 + 22, f'{tv:g}', 10, 'sans', SLATE, 'middle'))
    add(rich((cx0+cx1)/2, cy1 + 44, [('attacker held-out misread rate ', 'sans'), ('m', 'mathi')], 11.5, INK, 'middle'))
    add(rotg(452, (cy0+cy1)/2 - 12, -90, txt(452, (cy0+cy1)/2 - 12, 'minimum held-out budget', 10, 'sans', INK, 'middle')))
    add(rotg(466, (cy0+cy1)/2 + 6, -90, rich(466, (cy0+cy1)/2 + 6, [('(', 'sans'), ('n', 'mathi'), ('min', 'sans'), (', 95% power)', 'sans')], 9.5, SLATE, 'middle')))
    _, pts = read_dat('fig8_frontier')
    px = [CX(float(r['m'])) for r in pts]
    py = [CY(float(r['nmin'])) for r in pts]
    add('<path d="M' + ' L'.join(f'{a:.1f},{b:.1f}' for a, b in zip(px, py)) +
        '" fill="none" stroke="' + BLUE['line'] + '" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>')
    for xx, yy in zip(px, py):
        add(dot(xx, yy, BLUE['line'], 3.6))
    add(txt(CX(0.5) + 6, CY(8) + 18, 'n_min = 8 at m = 0.5', 9.5, 'bold', BLUE['line']))
    add(txt(CX(0.92) - 6, CY(2057) - 10, 'n_min = 2057', 9.5, 'bold', BLUE['line'], 'end'))
    add(line(cx0 + 16, cy0 + 20, cx0 + 50, cy0 + 20, BLUE['line'], 2.2)); add(dot(cx0 + 33, cy0 + 20, BLUE['line'], 4))
    add(txt(cx0 + 58, cy0 + 24, 'closed form', 11, 'sans', INK))
    return svg(W, H, ''.join(S))

outs = {
    'fig2_onset': fig2(), 'fig4_dose': fig4(), 'fig5_policy': fig5(),
    'fig6_field': fig6(), 'fig7_cert': fig7(), 'fig8_limits': fig8(),
    'fig9_release': fig9(),
}
for name, body in outs.items():
    (HERE / (name + '.svg')).write_text(body, encoding='utf-8')
    print('wrote', name + '.svg')
print('\n'.join(WARN) or 'fit OK')
