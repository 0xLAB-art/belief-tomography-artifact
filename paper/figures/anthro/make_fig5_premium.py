import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path
plt.rcParams.update({"font.family":"Inter","mathtext.fontset":"stix","mathtext.default":"regular",
 "font.size":7,"pdf.fonttype":42,"svg.fonttype":"none"})
INK="#0B1020"; SUB="#5B6478"; LINE="#D9DDE7"
GRN="#12A37F"; RED="#E11D48"; BLU="#3B63F5"; PUR="#7C3AED"; SLATE="#64708A"; AMB="#F08A0C"

# frozen artifact data (fig8_frontier.dat: closed-form n_min per misread rate m,
# emitted by make_tikz_data.py from gauntlet/demo/e16_query_complexity.json)
_fd = (Path(__file__).resolve().parent / '..' / '..' / 'tops' / 'figs' / 'figdata' / 'fig8_frontier.dat').read_text().strip().split('\n')
_m = [float(r.split('\t')[0]) for r in _fd[1:]]
_n = [float(r.split('\t')[1]) for r in _fd[1:]]

fig=plt.figure(figsize=(7.0,3.25),dpi=300,facecolor="white")
def chip(x,t):
    fig.text(x,0.962,t,fontsize=10,fontweight="bold",color="white",bbox=dict(boxstyle="round,pad=0.28",fc=INK,ec="none"),va="center")
chip(0.012,"a"); fig.text(0.042,0.962,"A decoy release zeroes the attacker",fontsize=8.2,fontweight="semibold",color=INK,va="center")
chip(0.556,"b"); fig.text(0.586,0.962,"Detection budget diverges with attacker error",fontsize=8.2,fontweight="semibold",color=INK,va="center")
fig.add_artist(Line2D([0.538,0.538],[0.06,0.93],color=LINE,lw=0.8,transform=fig.transFigure))

# ============ (a)
a=fig.add_axes([0.095,0.20,0.40,0.62])
a.set_xlim(-0.6,3.25); a.set_ylim(0,1.28)
a.axhspan(0,1.28,color="#FAFBFE",zorder=0)
for y in (0.25,0.5,0.75): a.axhline(y,color="#EEF0F6",lw=0.6,zorder=1)
a.axhline(1.0,color=SUB,lw=0.8,ls=(0,(2,2)),zorder=2)
data=[("Honest\nrelease",1.00,RED,"#FF8FA6"),("Silence\n(uniform)",0.20,SLATE,"#A9B2C6"),("Decoy\nrelease",0.00,GRN,GRN)]
cmapf=lambda c1,c2: LinearSegmentedColormap.from_list("g",[c1,c2])
for i,(lab,v,c,c2) in enumerate(data):
    x=i*1.0; w=0.52
    if v>0:
        for k in range(6):
            a.add_patch(FancyBboxPatch((x-w/2-0.012*k,0),w+0.024*k,v+0.003*k,boxstyle="round,pad=0,rounding_size=0.05",
                fc=c,ec="none",alpha=0.05,zorder=2))
        p=FancyBboxPatch((x-w/2,0),w,v,boxstyle="round,pad=0,rounding_size=0.05",fc="none",ec="none",zorder=3); a.add_patch(p)
        im=a.imshow(np.linspace(0,1,64).reshape(-1,1),extent=(x-w/2,x+w/2,0,v),origin="upper",cmap=cmapf(c,c2),aspect="auto",zorder=3)
        im.set_clip_path(p)
    else:
        a.add_patch(Rectangle((x-w/2,0),w,0.012,fc=c,ec="none",zorder=4))
        a.scatter([x],[0.0],s=46,color="white",edgecolor=c,linewidth=1.7,zorder=8,clip_on=False)
    a.text(x,v+0.07,f"{v:.2f}",ha="center",va="bottom",fontsize=9.5,fontweight="bold",color=c,zorder=6)
    a.text(x,-0.07,lab,ha="center",va="top",fontsize=6.9,fontweight="semibold",color=INK,linespacing=1.15,clip_on=False)
a.set_xlim(-0.6,3.0)
bx=2.62
for k in range(5,0,-1): a.plot([bx,bx],[0.02,0.98],color=PUR,lw=1.6+k*1.8,alpha=0.06,solid_capstyle="round",zorder=3)
a.add_patch(FancyArrowPatch((bx,0.02),(bx,0.98),arrowstyle="<|-|>",mutation_scale=8,lw=1.5,color=PUR,zorder=5))
a.text(bx,0.5,r"$\Delta_{\mathrm{dec}}=1.000$",rotation=90,ha="center",va="center",fontsize=7.4,fontweight="bold",color="white",zorder=6,
       bbox=dict(boxstyle="round,pad=0.35,rounding_size=0.8",fc=PUR,ec="none"))
a.set_yticks([0,0.5,1.0]); a.set_yticklabels(["0.0","0.5","1.0"],fontsize=6.6,color=SUB)
a.set_xticks([]); a.tick_params(axis="y",length=0)
for s in ("top","right","left"): a.spines[s].set_visible(False)
a.spines["bottom"].set_color(LINE)
a.set_ylabel("attacker per-attempt success",fontsize=7.2,color=INK,labelpad=4)
a.set_xlabel("release policy",fontsize=7.2,color=INK,labelpad=32)

# ============ (b) — data from the frozen artifact table
b=fig.add_axes([0.655,0.20,0.325,0.62])
m=np.array(_m); n=np.array(_n)
b.set_yscale("log"); b.set_xlim(0.48,1.0); b.set_ylim(1,1e4)
b.axvspan(0.94,1.0,color="#FFE9EE",zorder=0)
b.add_patch(Rectangle((0.94,1),0.06,1e4,fc="none",ec="#FFB3C2",hatch="////",lw=0,alpha=0.55,zorder=1))
b.axvline(0.94,color=RED,lw=1.0,ls=(0,(3,2)),zorder=2)
b.text(0.97,100,"undetectable",rotation=90,ha="center",va="center",fontsize=7.6,fontweight="bold",color=RED,zorder=3,
       bbox=dict(boxstyle="round,pad=0.3,rounding_size=0.5",fc="white",ec="none",alpha=0.85))
b.text(0.97,3.2,r"$m\geq0.94$",ha="center",va="center",fontsize=6.2,color=RED,fontweight="semibold",zorder=4,bbox=dict(boxstyle="round,pad=0.25,rounding_size=0.5",fc="white",ec="none",alpha=0.9))
b.fill_between(m,1,n,color=BLU,alpha=0.07,zorder=1)
for k in range(5,0,-1): b.plot(m,n,color=BLU,lw=1.6+k*1.8,alpha=0.06,zorder=3)
b.plot(m,n,color=BLU,lw=1.7,zorder=4)
b.scatter(m,n,s=11,color="white",edgecolor=BLU,linewidth=1.0,zorder=5)
b.scatter([m[0],m[-1]],[n[0],n[-1]],s=42,color=BLU,edgecolor="white",linewidth=1.0,zorder=6)
b.annotate(r"$n_{\min}=8$ at $m=0.5$",xy=(0.5,8),xytext=(0.52,2.0),fontsize=6.4,color=BLU,fontweight="semibold",
   arrowprops=dict(arrowstyle="-",color=BLU,lw=0.7),zorder=7,
   bbox=dict(boxstyle="round,pad=0.3,rounding_size=0.6",fc="white",ec=BLU,lw=0.7))
b.annotate(r"$n_{\min}=2057$ at $m=0.92$",xy=(0.92,2057),xytext=(0.66,2600),fontsize=6.4,color="white",fontweight="semibold",
   arrowprops=dict(arrowstyle="-",color=BLU,lw=0.7),zorder=7,
   bbox=dict(boxstyle="round,pad=0.3,rounding_size=0.6",fc=BLU,ec="none"))
b.set_yticks([1,10,100,1000,10000]); b.set_yticklabels([r"$10^{0}$",r"$10^{1}$",r"$10^{2}$",r"$10^{3}$",r"$10^{4}$"],fontsize=6.6,color=SUB)
b.set_xticks([0.5,0.6,0.7,0.8,0.9,1.0]); b.set_xticklabels(["0.5","0.6","0.7","0.8","0.9","1.0"],fontsize=6.6,color=SUB)
b.yaxis.set_minor_locator(matplotlib.ticker.NullLocator())
b.grid(axis="y",color="#EEF0F6",lw=0.6,zorder=0); b.set_axisbelow(True)
for s in ("top","right"): b.spines[s].set_visible(False)
for s in ("left","bottom"): b.spines[s].set_color(LINE)
b.tick_params(length=2.5,color=LINE)
b.set_xlabel(r"attacker held-out misread rate $m$",fontsize=7.2,color=INK,labelpad=3)
b.set_ylabel(r"minimum held-out budget $n_{\min}$"+"\n(95% power)",fontsize=7.0,color=INK,labelpad=3,linespacing=1.2)
fig.legend(handles=[Line2D([],[],color=BLU,marker="o",markerfacecolor="white",markersize=4.5,lw=1.6,label="closed form (Monte Carlo\u2011validated)")],
   loc="lower center",bbox_to_anchor=(0.82,-0.012),frameon=False,fontsize=6.6,handletextpad=0.5)
for ext in ("pdf","svg","png"): fig.savefig(f"fig5_premium.{ext}",dpi=400)
