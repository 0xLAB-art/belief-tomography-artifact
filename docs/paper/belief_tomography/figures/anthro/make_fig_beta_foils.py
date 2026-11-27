#!/usr/bin/env python3
"""Fig. 1 (beta foils, two-panel reference form) from frozen artifacts.

Data: paper/tops/figs/figdata/fig1_profile.dat (emitted by paper/tops/figs/make_tikz_data.py
from gauntlet/demo/profile.json). n = 18 trials/cell is the cell size implied by the
frozen Wilson CIs (beta=1 -> lower bound 0.8241); counted trials x = round(beta*n).
Run:  uv run --with matplotlib --with numpy python3 make_fig_beta_foils.py
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
dat = (HERE / '..' / '..' / 'tops' / 'figs' / 'figdata' / 'fig1_profile.dat')
if not dat.exists():
    dat = Path('paper/tops/figs/figdata/fig1_profile.dat')
cols = dat.read_text().strip().split('\n')[0].split('\t')
rows = [r.split('\t') for r in dat.read_text().strip().split('\n')[1:]]
g = lambda k: np.array([float(r[cols.index(k)]) for r in rows])
nb, lb, ub, hb, lh, uh = g('nb'), g('lb'), g('ub'), g('hb'), g('lh'), g('uh')
FAM = ['Authority\nforgery', 'State\ndeception', 'Goal\nsubversion', 'Epistemic\necho', 'Exfiltration\nlure']
N = 18
x_n = np.round(nb*N).astype(int); x_h = np.round(hb*N).astype(int)
def wilson(x, n, z=1.96):
    p = x/n; d = 1 + z*z/n
    c = p + z*z/(2*n); r = z*np.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return (c-r)/d, (c+r)/d
pn = 84/90; pl, pu = wilson(84, 90)
ph = 54/90; hl_, hu_ = wilson(54, 90)
dbeta = hb - nb
sep = [ub[i] < lh[i] for i in range(5)]
CORAL, BLUE, INK = '#D2622A', '#2E6DA4', '#262523'
GREY, ZEBRA = '#BFBFBF', '#F2F2F2'

fig = plt.figure(figsize=(7.6, 4.25), dpi=300)
fig.patch.set_facecolor('white')
gs = fig.add_gridspec(1, 2, width_ratios=[1.72, 1.0], wspace=0.14, left=0.128, right=0.988, top=0.862, bottom=0.115)

ax = fig.add_subplot(gs[0, 0])
ax.set_xlim(0, 1.02); ax.set_ylim(-0.55, 6.55)
row_y = {i: 5.6 - i*1.05 for i in range(5)}
pool_y = row_y[4] - 1.35
for i in range(5):
    if i % 2 == 0:
        ax.add_patch(Rectangle((0, row_y[i]-0.42), 1.02, 0.84, fc=ZEBRA, ec='none', zorder=1))
ax.plot([0, 1.02], [(row_y[4]+pool_y)/2 + 0.04]*2, color='#D9D9D9', lw=0.8, zorder=2)
ax.axvline(1.0, color=CORAL, ls=(0, (2, 2.4)), lw=1.1, zorder=3)
ax.text(1.0, 6.28, 'design target $\\beta = 1$', ha='right', fontsize=7.2, color=CORAL, style='italic')
for i in range(5):
    y = row_y[i]
    x0, x1 = (uh[i], nb[i]) if sep[i] else (lh[i], min(ub[i], nb[i]))
    ax.plot([x0, x1], [y, y], color=GREY, lw=5, solid_capstyle='butt', alpha=0.85, zorder=3)
ax.plot([hu_, pn], [pool_y, pool_y], color=GREY, lw=5, solid_capstyle='butt', alpha=0.85, zorder=3)
for i in range(5):
    y = row_y[i]
    ax.plot([lb[i], ub[i]], [y+0.16]*2, color=CORAL, lw=1.6, zorder=5)
    ax.plot([nb[i]], [y+0.16], 'o', ms=4.5, color=CORAL, zorder=6)
    ax.plot([lh[i], uh[i]], [y-0.16]*2, color=BLUE, lw=1.6, zorder=5)
    ax.plot([hb[i]], [y-0.16], 'o', ms=4.5, color=BLUE, zorder=6)
ax.plot([pl, pu], [pool_y+0.16]*2, color=CORAL, lw=1.6, zorder=5)
ax.plot([pn], [pool_y+0.16], 'o', ms=4.5, color=CORAL, zorder=6)
ax.plot([hl_, hu_], [pool_y-0.16]*2, color=BLUE, lw=1.6, zorder=5)
ax.plot([ph], [pool_y-0.16], 'o', ms=4.5, color=BLUE, zorder=6)
ax.annotate('no separation', (0.62, row_y[3]+0.47), fontsize=7.2, color=CORAL, style='italic',
            ha='center', zorder=7,
            arrowprops=dict(arrowstyle='->', color=CORAL, lw=0.9, connectionstyle='arc3,rad=-0.25'))
ax.text(1.055, 6.28, '$\\Delta\\hat\\beta$', fontsize=8, color=INK)
for i in range(5):
    y = row_y[i]; val = dbeta[i]
    if abs(val) < 1e-9:
        ax.annotate('$0.00$', (1.075, y), fontsize=8.5, color=INK, ha='center', va='center',
                    bbox=dict(boxstyle='round,pad=0.28', fc='#FFF3C4', ec='#D9B93B', lw=1.1), zorder=7)
    else:
        ax.text(1.075, y, f'${val:+.2f}$', fontsize=8.5, color=CORAL, ha='center', va='center')
ax.text(1.075, pool_y, '$-0.33$', fontsize=8.5, color=CORAL, ha='center', va='center')
ax.set_yticks([row_y[i] for i in range(5)] + [pool_y])
ax.set_yticklabels(FAM + ['All families\n(pooled)'], fontsize=8)
ax.set_xticks([0, 0.25, 0.5, 0.75, 1])
ax.set_xticklabels(['0', '0.25', '0.5', '0.75', '1'], fontsize=8)
ax.set_xlabel('measured $\\hat\\beta$  (95% Wilson CI)', fontsize=8.5)
for sp in ['top', 'right']: ax.spines[sp].set_visible(False)
ax.spines[['left', 'bottom']].set_color('#B9B9B9')
ax.tick_params(length=2.5, colors=INK)
ax.set_title('(a)  Measured $\\hat\\beta$ per probe family', fontsize=8.8, loc='left', color=INK, pad=8)

ax2 = fig.add_subplot(gs[0, 1])
ax2.set_xlim(-0.30, 3.30); ax2.set_ylim(-0.90, 6.55); ax2.axis('off')
S, GX = 0.135, 0.148
for i in range(5):
    y = row_y[i]
    if i % 2 == 0:
        ax2.add_patch(Rectangle((-0.30, y-0.42), 3.60, 0.84, fc=ZEBRA, ec='none', zorder=1))
    for r, (cnt, c) in enumerate([(x_n[i], CORAL), (x_h[i], BLUE)]):
        yy = y + (0.16 if r == 0 else -0.16)
        for k in range(N):
            xx = 0.05 + k*GX
            filled = k < cnt
            ax2.add_patch(Rectangle((xx, yy-S/2), S*0.80, S, fc=c if filled else 'none',
                         ec=c if filled else '#B9B9B9', lw=0.7, zorder=4))
        ax2.text(0.05 + N*GX - 0.03, yy, f'{cnt}/{N}', fontsize=7.3, color=c, va='center', ha='left')
ax2.add_patch(Rectangle((0.05, pool_y+0.10), 2.50*84/90, 0.20, fc=CORAL, ec='none', zorder=4))
ax2.add_patch(Rectangle((0.05+2.50*84/90, pool_y+0.10), 2.50*(1-84/90), 0.20, fc='none', ec='#B9B9B9', lw=0.7, zorder=4))
ax2.text(2.62, pool_y+0.20, '84/90', fontsize=7.3, color=CORAL, va='center')
ax2.add_patch(Rectangle((0.05, pool_y-0.30), 2.50*54/90, 0.20, fc=BLUE, ec='none', zorder=4))
ax2.add_patch(Rectangle((0.05+2.50*54/90, pool_y-0.30), 2.50*(1-54/90), 0.20, fc='none', ec='#B9B9B9', lw=0.7, zorder=4))
ax2.text(2.62, pool_y-0.20, '54/90', fontsize=7.3, color=BLUE, va='center')
ax2.set_title('(b)  Per-trial outcomes  (18 trials/cell)', fontsize=8.8, loc='left', color=INK, pad=8)
ax2.add_patch(Rectangle((0.05, -0.72), 0.13, 0.13, fc='#8C8C8C', ec='none', zorder=4))
ax2.text(0.22, -0.655, 'trial counted toward $\\hat\\beta$', fontsize=6.8, color=INK, va='center')
ax2.add_patch(Rectangle((1.95, -0.72), 0.13, 0.13, fc='none', ec='#B9B9B9', lw=0.7, zorder=4))
ax2.text(2.12, -0.655, 'not counted', fontsize=6.8, color=INK, va='center')
fig.text(0.128, 0.945, '$\\bullet$— Naive foil (designed $\\beta = 1$)', fontsize=8.5, color=INK)
fig.text(0.435, 0.945, '$\\bullet$— Hardened foil (graded $\\beta$)', fontsize=8.5, color=INK)
fig.savefig(HERE / 'fig_beta_foils.pdf')
fig.savefig(HERE / 'fig_beta_foils.png', dpi=200)
print('written', HERE / 'fig_beta_foils.pdf')
