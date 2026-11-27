import math
from xml.sax.saxutils import escape as esc
from PIL import ImageFont

W, H = 1000, 724
S = []
add = S.append

# ------------------------------------------------------------------ fonts
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

# ------------------------------------------------------------------ palette
INK, SLATE, MUTED = '#0F172A', '#334155', '#64748B'
BLUE = dict(hdr='#1E40AF', line='#3B63E8', band='#F2F6FF', tint='#DCE7FF', soft='#9DB6FF')
AMB  = dict(hdr='#9A5B0B', line='#D97706', band='#FFF8EB', tint='#FDE9C0', soft='#F5C16C')
GRN  = dict(hdr='#05694B', line='#0E9F6E', band='#EFFAF5', tint='#CFF1E2', soft='#6FCFA8')
ROSE = dict(hdr='#BE123C', line='#E11D48', band='#FFF1F4', tint='#FFD9E1', soft='#FDA4B8', dark='#9F1239')

# ------------------------------------------------------------------ primitives
def txt(x, y, s, size=13, kind='sans', fill=INK, anchor='start', op=1):
    fam, w, st = CSS[kind]
    o = f' fill-opacity="{op}"' if op != 1 else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" font-weight="{w}" '
            f'font-style="{st}" fill="{fill}"{o} text-anchor="{anchor}" xml:space="preserve">{esc(s)}</text>')

def rich(x, y, parts, size=12.5, fill=INK, anchor='start'):
    """parts: [(text, kind[, fill])]  -- absolute-positioned runs (so hats/maths never drift)."""
    parts = [('\U0001D6FD', 'bhat') + tuple(p[2:]) if p[1] == 'bhat' else p for p in parts]
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
    return ''.join(out)

def rect(x, y, w, h, rx=8, fill='none', stroke='none', sw=1.5, extra=''):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'

def card(x, y, w, h, stroke, fill='#FFFFFF', sw=1.6, rx=10):
    add(rect(x, y + 2.5, w, h, rx, '#0F172A', 'none', 0, 'fill-opacity="0.09"'))
    add(rect(x, y, w, h, rx, fill, stroke, sw))

def arrow(pts, color, sw=2.0, head=7.5, dash=None):
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    d = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / d, (y1 - y0) / d
    bx, by = x1 - ux * head, y1 - uy * head
    px, py = -uy, ux
    path = 'M' + ' L'.join(f'{a:.1f},{b:.1f}' for a, b in pts[:-1]) + f' L{bx + ux*1.2:.1f},{by + uy*1.2:.1f}'
    da = f' stroke-dasharray="{dash}"' if dash else ''
    add(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"{da}/>')
    add(f'<path d="M{x1:.1f},{y1:.1f} L{bx+px*head*0.48:.1f},{by+py*head*0.48:.1f} '
        f'L{bx-px*head*0.48:.1f},{by-py*head*0.48:.1f} Z" fill="{color}"/>')

def pill(cx, cy, text, size=12.5, pad=18):
    w = tw(text, 'sans', size) + 2 * pad
    add(rect(cx - w / 2, cy - 13, w, 26, 13, '#FFFFFF', '#94A3B8', 1.2))
    add(txt(cx, cy + 4.4, text, size, 'sans', SLATE, 'middle'))
    return cx - w / 2, cx + w / 2

# ------------------------------------------------------------------ icons
def g(tx, ty, body, sc=1):
    return f'<g transform="translate({tx},{ty}) scale({sc})">{body}</g>'
def st(c, w=1.7):
    return f'fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"'

def tile(x, y, C, body):
    add(rect(x, y, 32, 32, 8, C['tint'], C['soft'], 1))
    add(g(x, y, body))

def ic_list(c):
    return (''.join(f'<circle cx="9" cy="{y}" r="1.9" fill="{c}"/><path d="M14,{y} H24" {st(c)}/>' for y in (10, 16, 22)))
def ic_seed(c):
    return (f'<path d="M16,25 V15" {st(c)}/><path d="M16,18 C10,18 8,14 8,9.5 C13,9.5 16,12.5 16,18 Z" {st(c,1.5)}/>'
            f'<path d="M16,14.5 C16,10.5 19,7 24,7 C24,12 21,15 16,14.5 Z" {st(c,1.5)}/><path d="M10,25.5 H22" {st(c)}/>')
def ic_gavel(c):
    return (f'<g transform="rotate(-38 16 16)"><rect x="8.5" y="7" width="15" height="7.5" rx="2" {st(c,1.6)}/>'
            f'<rect x="14.4" y="14.5" width="3.2" height="12" rx="1.6" fill="{c}"/></g><path d="M7,27 H19" {st(c)}/>')
def ic_pin(c):
    return (f'<path d="M16,5.5 C11,5.5 8,9 8,13.2 C8,19 16,26.5 16,26.5 C16,26.5 24,19 24,13.2 C24,9 21,5.5 16,5.5 Z" {st(c,1.6)}/>'
            f'<circle cx="16" cy="13" r="3" fill="{c}"/>')
def ic_heat(c):
    vals = [['#FDE68A', '#FBBF24', '#F59E0B', '#FBBF24'],
            ['#FBBF24', '#F59E0B', '#B45309', '#F59E0B'],
            ['#FDE68A', '#FBBF24', '#F59E0B', '#FDE68A']]
    o = ''
    for r, row in enumerate(vals):
        for k, v in enumerate(row):
            o += f'<rect x="{5.2 + k*5.6:.1f}" y="{8.2 + r*5.6:.1f}" width="4.8" height="4.8" rx="1" fill="{v}"/>'
    return o
def ic_target(c):
    return (f'<circle cx="16" cy="16" r="8" {st(c,1.6)}/><circle cx="16" cy="16" r="2.2" fill="{c}"/>'
            f'<path d="M16,4.5 V9.5 M16,22.5 V27.5 M4.5,16 H9.5 M22.5,16 H27.5" {st(c,1.6)}/>')
def ic_bot(c):
    return (f'<rect x="8" y="11" width="16" height="12.5" rx="3.2" {st(c,1.6)}/><path d="M16,11 V7.2" {st(c,1.6)}/>'
            f'<circle cx="16" cy="6" r="1.5" fill="{c}"/><circle cx="12.4" cy="17" r="1.9" fill="{c}"/><circle cx="19.6" cy="17" r="1.9" fill="{c}"/>'
            f'<path d="M5.5,15.5 V19 M26.5,15.5 V19" {st(c,1.6)}/>')
def ic_ledger(c):
    return (f'<rect x="8.5" y="7" width="15" height="19" rx="2.4" {st(c,1.6)}/><rect x="12.5" y="5" width="7" height="4.2" rx="1.2" fill="{c}"/>'
            f'<path d="M11.5,14 l1.6,1.6 l3,-3.2 M11.5,20.5 l1.6,1.6 l3,-3.2" {st(c,1.5)}/><path d="M18.5,14.6 H21 M18.5,21 H21" {st(c,1.5)}/>')
def ic_person(c):
    return (f'<circle cx="14" cy="11.5" r="4.2" {st(c,1.6)}/><path d="M6.5,26 C6.5,19.5 10,17.5 14,17.5 C18,17.5 21.5,19.5 21.5,26" {st(c,1.6)}/>'
            f'<circle cx="23.5" cy="21.5" r="4.6" fill="{c}"/><path d="M21.2,21.6 l1.7,1.7 l3,-3.3" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>')
def ic_chain(c):
    o = ''
    for k, x in enumerate((3, 12.5, 22)):
        o += f'<rect x="{x}" y="12.5" width="7" height="7" rx="1.6" {st(c,1.6)}/>'
    o += f'<path d="M10,16 H12.5 M19.5,16 H22" {st(c,1.6)}/><path d="M6.5,21.5 V25 H25.5 V21.5" {st(c,1.2)} stroke-dasharray="1.5 2.2"/>'
    return o

def small_globe(cx, cy, c, w=1.5, s=1.0):
    return g(cx, cy, f'<circle r="7.5" {st(c,w)}/><ellipse rx="3.2" ry="7.5" {st(c,w)}/><path d="M-7.5,0 H7.5" {st(c,w)}/>', s)
def small_shield(cx, cy, c, w=1.5, s=1.0, fill='none'):
    return g(cx, cy, f'<path d="M0,-8.5 L7.5,-5.5 V0 C7.5,4.8 4,7.8 0,9.5 C-4,7.8 -7.5,4.8 -7.5,0 V-5.5 Z" fill="{fill}" stroke="{c}" stroke-width="{w}" stroke-linejoin="round"/>'
             f'<path d="M-3.2,0.4 L-0.8,2.8 L3.6,-2.2" {st(c,w)}/>', s)
def small_gauge(cx, cy, c, w=1.5):
    return g(cx, cy, f'<path d="M-7.5,4.5 A8,8 0 1 1 7.5,4.5" {st(c,w)}/><path d="M0,2 L3.8,-3.6" {st(c,w)}/><circle r="1.4" cy="2" fill="{c}"/>')
def hood(cx, cy, eye, sc=1.0):
    body = ('<path d="M-16,22 C-17,4 -11,-18 0,-18 C11,-18 17,4 16,22 Z" fill="#1E3A8A"/>'
            '<path d="M-16,22 C-17,4 -11,-18 0,-18 C11,-18 17,4 16,22" fill="none" stroke="#0B1B5C" stroke-width="1"/>'
            '<ellipse cx="0" cy="2" rx="8.6" ry="10.6" fill="#0B1220"/>'
            f'<circle cx="-3.4" cy="0.6" r="1.8" fill="{eye}"/><circle cx="3.4" cy="0.6" r="1.8" fill="{eye}"/>')
    return g(cx, cy, body, sc)

# ------------------------------------------------------------------ bands
def band(y, h, C, title, sub, icon):
    add(rect(24, y, 952, h, 14, C['band'], C['hdr'], 1.6))
    add(f'<path d="M24,{y+30} V{y+14} Q24,{y} 38,{y} H962 Q976,{y} 976,{y+14} V{y+30} Z" fill="{C["hdr"]}"/>')
    add(icon(46, y + 15))
    add(txt(64, y + 20, title, 14, 'bold', '#FFFFFF'))
    add(txt(956, y + 20, sub, 12, 'ital', '#FFFFFF', 'end', 0.93))

# ====================================================================== PLANE 1
y1 = 24
band(y1, 226, BLUE, 'Live Fleet Plane · Public Internet', 'a three-arm public deception fleet',
     lambda cx, cy: small_globe(cx, cy, '#fff', 1.5))
cy_ = 70; ch = 164
# -- attacker personas
ax, aw = 36, 210
card(ax, cy_, aw, ch, BLUE['line'])
add(hood(ax + 24, cy_ + 22, '#60A5FA', 0.40))
add(txt(ax + 40, cy_ + 26, 'Attacker personas', 14.5, 'bold'))
chk('attackers title', 'Attacker personas', 'bold', 14.5, aw - 50)
for cx_, eye in ((ax + 43, '#60A5FA'), (ax + 105, '#C084FC'), (ax + 167, '#22D3EE')):
    add(hood(cx_, cy_ + 60, eye))
add(txt(ax + 105, cy_ + 108, 'frontier-model brains', 13, 'sans', SLATE, 'middle'))
chk('brains', 'frontier-model brains', 'sans', 13, aw - 20)
add(rect(ax + 14, cy_ + 120, aw - 28, 28, 6, INK))
add(rich(ax + 28, cy_ + 138.5, [('>_ ', 'mono', '#4ADE80'), ('over live SSH', 'mono', '#E2E8F0')], 12.5))

# -- three-arm public face
fx, fw = 286, 270
card(fx, cy_, fw, ch, BLUE['line'])
add(small_globe(fx + 24, cy_ + 21, BLUE['line'], 1.5, 0.95))
add(txt(fx + 40, cy_ + 26, 'Three-arm public face', 14.5, 'bold'))
chk('face title', 'Three-arm public face', 'bold', 14.5, fw - 50)
rows = [('A', 'stock Cowrie', False), ('B', 'bare-LLM', False), ('C', 'verified pipeline', True)]
row_y = [cy_ + 38, cy_ + 72, cy_ + 106]
for (lab, name, hot), ry in zip(rows, row_y):
    rx0 = fx + 10
    rw = fw - 20 + (10 if hot else 0)
    if hot:
        add(rect(rx0, ry, rw, 28, 7, ROSE['band'], ROSE['line'], 2.0))
        add(f'<circle cx="{rx0+17}" cy="{ry+14}" r="9" fill="{ROSE["line"]}"/>')
        add(txt(rx0 + 17, ry + 18.4, lab, 12.5, 'bold', '#fff', 'middle'))
        add(txt(rx0 + 34, ry + 18.6, name, 13.5, 'bold', ROSE['dark']))
    else:
        add(rect(rx0, ry, rw, 28, 7, BLUE['band'], BLUE['soft'], 1.3))
        add(f'<circle cx="{rx0+17}" cy="{ry+14}" r="9" fill="{BLUE["hdr"]}"/>')
        add(txt(rx0 + 17, ry + 18.4, lab, 12.5, 'bold', '#fff', 'middle'))
        add(txt(rx0 + 34, ry + 18.6, name, 13.5, 'sans', INK))
    # tiny host glyph (one arm per host)
    hx = fx + fw - 40
    c = ROSE['line'] if hot else BLUE['line']
    add(f'<rect x="{hx}" y="{ry+7}" width="16" height="6" rx="1.8" {st(c,1.3)}/><rect x="{hx}" y="{ry+15}" width="16" height="6" rx="1.8" {st(c,1.3)}/>'
        f'<circle cx="{hx+4}" cy="{ry+10}" r="0.9" fill="{c}"/><circle cx="{hx+4}" cy="{ry+18}" r="0.9" fill="{c}"/>')
add(txt(fx + fw / 2, cy_ + 154, 'one arm per host', 12.5, 'ital', MUTED, 'middle'))

# attackers -> three arms (fan-out)
add(f'<path d="M{ax+aw},{row_y[1]+14} H{ax+aw+20} M{ax+aw+20},{row_y[0]+14} V{row_y[2]+14}" fill="none" stroke="{SLATE}" stroke-width="2" stroke-linecap="round"/>')
for ry in row_y:
    arrow([(ax + aw + 20, ry + 14), (fx + 20, ry + 14)], SLATE, 2, 7)

# -- verified deception loop
lx, lw = 626, 338
card(lx, cy_, lw, ch, ROSE['line'], ROSE['band'], 2.3)
add(small_shield(lx + 24, cy_ + 21, ROSE['line'], 1.6, 1.0))
add(txt(lx + 40, cy_ + 26, 'Verified deception loop', 14.5, 'bold', ROSE['dark']))
chk('loop title', 'Verified deception loop', 'bold', 14.5, lw - 50)
chips = ['Chrollo', 'Don', 'Hisoka']
cxs = [lx + 20 + i * 106 for i in range(3)]
for nm, x0 in zip(chips, cxs):
    add(rect(x0, cy_ + 40, 84, 26, 7, '#FFFFFF', ROSE['line'], 1.7))
    add(txt(x0 + 42, cy_ + 57.4, nm, 13, 'bold', ROSE['dark'], 'middle'))
for i in range(2):
    arrow([(cxs[i] + 86, cy_ + 53), (cxs[i + 1] - 2, cy_ + 53)], ROSE['line'], 1.8, 6.5)
# cycle arc (generate + verify)
x_end, x_start = cxs[2] + 42, cxs[0] + 42
add(f'<path d="M{x_end},{cy_+68} C{x_end},{cy_+96} {x_start},{cy_+96} {x_start},{cy_+72}" fill="none" stroke="{ROSE["line"]}" stroke-width="1.7" stroke-dasharray="4 3" stroke-linecap="round"/>')
add(f'<path d="M{x_start},{cy_+68} L{x_start-3.6},{cy_+75} L{x_start+3.6},{cy_+75} Z" fill="{ROSE["line"]}"/>')
add(txt(lx + lw / 2, cy_ + 101, 'generate + verify', 12.5, 'ital', ROSE['dark'], 'middle'))
# fail-closed gate badge
add(rect(lx + 20, cy_ + 112, lw - 40, 44, 9, ROSE['line']))
add(f'<rect x="{lx+34}" y="{cy_+129}" width="16" height="12" rx="2.4" fill="#fff"/>'
    f'<path d="M{lx+37.5},{cy_+129} V{cy_+125.5} C{lx+37.5},{cy_+119} {lx+46.5},{cy_+119} {lx+46.5},{cy_+125.5} V{cy_+129}" fill="none" stroke="#fff" stroke-width="2.1" stroke-linecap="round"/>'
    f'<circle cx="{lx+42}" cy="{cy_+135}" r="1.7" fill="{ROSE["line"]}"/>')
add(txt(lx + 62, cy_ + 131, 'FAIL-CLOSED', 14, 'bold', '#fff'))
add(txt(lx + 62, cy_ + 147, 'an unverified turn is never served', 12.5, 'sans', '#fff', op=0.96))
chk('failclosed', 'an unverified turn is never served', 'sans', 12.5, lw - 40 - 52)

# face <-> loop: request out, verified-only back
c_y = row_y[2] + 14
fx_r = fx + fw + 10
arrow([(fx_r + 2, c_y - 7), (lx - 3, c_y - 7)], SLATE, 1.8, 6.5, dash='4 3')
arrow([(lx - 3, c_y + 7), (fx_r + 2, c_y + 7)], ROSE['line'], 2.5, 7.5)
add(txt((fx_r + lx) / 2 - 0.5, c_y - 12, 'request', 12, 'sans', SLATE, 'middle'))
add(txt((fx_r + lx) / 2 - 0.5, c_y + 22, 'verified', 12, 'bold', ROSE['dark'], 'middle'))

# ====================================================================== connector 1
y_gap1 = 250
a1, a2 = 150, 850
arrow([(a1, y_gap1 + 3), (a1, y_gap1 + 49)], SLATE, 2.2, 8)
arrow([(a2, y_gap1 + 3), (a2, y_gap1 + 49)], SLATE, 2.2, 8)
l, r = pill(500, y_gap1 + 25, 'logged sessions · E2 gateway · E3 fleet · every call append-only')
add(f'<path d="M{a1+8},{y_gap1+25} H{l} M{r},{y_gap1+25} H{a2-8}" stroke="#94A3B8" stroke-width="1.2" stroke-dasharray="3 3" fill="none"/>')

# ====================================================================== PLANE 2
y2 = 300
band(y2, 170, AMB, 'Measurement Plane · The Instrument',
     'runs unchanged across foils, gateway models and the fleet', lambda cx, cy: small_gauge(cx, cy, '#fff', 1.5))
GX = [36 + i * 190 for i in range(5)]
CW = 168
cy2, ch2 = y2 + 44, 112
M = [
    ('Probe library', ic_list, [[('5 families ×', 'sans')], [('3 generations', 'sans')]]),
    ('Seed episodes', ic_seed, [[('fresh session', 'sans')], [('per probe', 'sans')]]),
    ('Verdict channel', ic_gavel, [[('oracles →', 'sans')], [('transcript jury', 'sans')]]),
    ('Pinned estimator', ic_pin, [[('Wilson 95% ', 'sans'), ('β', 'bhat')], [('frozen commit', 'sans')]]),
    ('Tomogram', ic_heat, [[('β', 'bhat'), (' profiles · BCG', 'sans')],
                           [('Γ', 'mathr'), (' · ', 'sans'), ('Λ', 'mathr'), ('(', 'mathr'), ('B', 'mathi'), (')', 'mathr')]]),
]
for i, (title, ic, det) in enumerate(M):
    x = GX[i]
    hero = (i == 4)
    card(x, cy2, CW, ch2, AMB['line'], AMB['tint'] if hero else '#FFFFFF', 2.2 if hero else 1.6)
    tile(x + 14, cy2 + 12, dict(tint='#FFFFFF' if hero else AMB['tint'], soft=AMB['soft']), ic(AMB['hdr']))
    add(txt(x + 14, cy2 + 66, title, 14.5, 'bold'))
    chk('m-title', title, 'bold', 14.5, CW - 28)
    for k, parts in enumerate(det):
        add(rich(x + 14, cy2 + 86 + k * 17.5, parts, 12.5, SLATE))
        chk('m-det', ''.join(p[0] for p in parts), 'sans', 12.5, CW - 28)
    if i < 4:
        arrow([(x + CW + 3, cy2 + 56), (GX[i + 1] - 3, cy2 + 56)], AMB['line'], 2.2, 7)

# ====================================================================== connector 2
y_gap2 = 470
b1, b2 = 140, 860
arrow([(b1, y_gap2 + 49), (b1, y_gap2 + 3)], GRN['hdr'], 2.4, 8)       # gates (up)
arrow([(b2, y_gap2 + 3), (b2, y_gap2 + 49)], GRN['hdr'], 2.4, 8)       # pins (down)
pl1 = 'hardening gates & audits'
pl2 = 'every number pinned to a frozen artifact'
w1 = tw(pl1, 'sans', 12.5) + 36
w2 = tw(pl2, 'sans', 12.5) + 36
c1x, c2x = b1 + 22 + w1 / 2, b2 - 22 - w2 / 2
pill(c1x, y_gap2 + 25, pl1)
pill(c2x, y_gap2 + 25, pl2)
add(f'<path d="M{b1+8},{y_gap2+25} H{c1x-w1/2}" stroke="#94A3B8" stroke-width="1.2" stroke-dasharray="3 3" fill="none"/>')
add(f'<path d="M{c2x+w2/2},{y_gap2+25} H{b2-8}" stroke="#94A3B8" stroke-width="1.2" stroke-dasharray="3 3" fill="none"/>')
add(txt(c1x + w1 / 2 + 8, y_gap2 + 29.4, '', 12))

# ====================================================================== PLANE 3
y3 = 520
band(y3, 188, GRN, 'Assurance & Evidence Plane', 'gates the platform · pins every number',
     lambda cx, cy: small_shield(cx, cy, '#fff', 1.5, 1.0))
cy3, ch3 = y3 + 44, 130
A = [
    ('Verifier red-team', ic_target, '105', [['drafts · P=R=1.0,'], ['0 unverified serves']]),
    ('AI attack-team', ic_bot, None, [['campaigns on the'], ['plane; findings fixed']]),
    ('Pre-registration ledger', ic_ledger, '21', [['registered'], ['experiments']]),
    ('Human rating loop', ic_person, '3', [['blind raters +'], ['adjudicator']]),
    ('Hash-chained archive', ic_chain, '220', [['artifacts']]),
]
for i, (title, ic, big, det) in enumerate(A):
    x = GX[i]
    card(x, cy3, CW, ch3, GRN['line'])
    tile(x + 14, cy3 + 12, GRN, ic(GRN['hdr']))
    if big:
        add(txt(x + CW - 14, cy3 + 38, big, 30, 'bold', GRN['hdr'], 'end'))
    else:
        add(f'<circle cx="{x+CW-27}" cy="{cy3+28}" r="13" fill="{GRN["hdr"]}"/>'
            f'<path d="M{x+CW-33},{cy3+28.5} l4.4,4.4 l8,-8.6" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>')
    # title: wrap to <=2 lines, last line pinned to the same baseline
    tl = [title]
    if tw(title, 'bold', 14) > CW - 24:
        a, b = title.split(' ', 1)
        tl = [a, b]
    for k, t in enumerate(reversed(tl)):
        add(txt(x + 14, cy3 + 84 - k * 16.5, t, 14, 'bold'))
        chk('a-title', t, 'bold', 14, CW - 24)
    for k, ln in enumerate(det):
        add(txt(x + 14, cy3 + 103 + k * 17, ln[0], 12.5, 'sans', SLATE))
        chk('a-det', ln[0], 'sans', 12.5, CW - 24)

# ------------------------------------------------------------------ write
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W*0.504:.1f}pt" height="{H*0.504:.1f}pt">'
       '<title>Belief-tomography platform</title>'
       '<desc>Three planes: live deception fleet, measurement instrument, assurance and evidence.</desc>'
       + ''.join(S) + '</svg>')
open('/home/elaref/Documents/research/ragin/paper/figures/anthro/fig3_platform.svg', 'w', encoding='utf-8').write(svg)
print('\n'.join(WARN) or 'fit OK')