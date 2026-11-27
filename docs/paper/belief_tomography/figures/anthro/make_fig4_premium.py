import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle, Polygon, Arc
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap, to_rgb
plt.rcParams.update({"font.family":"Inter","mathtext.fontset":"stix","mathtext.default":"regular",
 "font.size":7,"pdf.fonttype":42,"svg.fonttype":"none"})
INK="#0B1020"; SUB="#5B6478"; LINE="#D9DDE7"
GRN="#12A37F"; GRNL="#E6F6F0"; RED="#E11D48"; REDL="#FFE4EA"
BLU="#3B63F5"; ORG="#F08A0C"; PUR="#7C3AED"; NAVY="#12152B"; NAVY2="#2B1330"

fig=plt.figure(figsize=(7.0,3.35),dpi=300,facecolor="white")
a=fig.add_axes([0,0,0.585,0.925]); a.set_xlim(0,100); a.set_ylim(0,100*0.925*3.35/(0.585*7.0)); a.axis("off")
YM=a.get_ylim()[1]

def rbox(x,y,w,h,r=2.4,**k):
    return FancyBboxPatch((x,y),w,h,boxstyle=f"round,pad=0,rounding_size={r}",**k)
def shadow(x,y,w,h,r=2.4,n=7,col="#1B2440",s=0.18):
    for i in range(n):
        d=i*0.45
        a.add_patch(rbox(x-d*0.5,y-0.8-d,w+d,h+d*0.9,r+d*0.3,fc=col,ec="none",alpha=s/(i+1.6)*0.9,zorder=1))
def gradbox(x,y,w,h,c1,c2,r=2.4,ec="none",lw=1,ls="-",vertical=True,z=2):
    p=rbox(x,y,w,h,r,fc="none",ec=ec,lw=lw,ls=ls,zorder=z+0.1); a.add_patch(p)
    cm=LinearSegmentedColormap.from_list("g",[c1,c2])
    g=np.linspace(0,1,128).reshape(-1,1) if vertical else np.linspace(0,1,128).reshape(1,-1)
    im=a.imshow(g,extent=(x,x+w,y,y+h),origin="upper",cmap=cm,aspect="auto",zorder=z,interpolation="bilinear")
    im.set_clip_path(p); return p
def glow_line(xs,ys,col,w=2,layers=5,z=3):
    for i in range(layers,0,-1):
        a.plot(xs,ys,color=col,lw=w+i*2.2,alpha=0.07,solid_capstyle="round",zorder=z)
    a.plot(xs,ys,color=col,lw=w,solid_capstyle="round",zorder=z+1)

for gx in np.arange(1,100,3.6):
    for gy in np.arange(1,YM,3.6):
        a.add_patch(Circle((gx,gy),0.16,fc="#C9CFDD",ec="none",alpha=0.55,zorder=0))

fig.text(0.012,0.962,"a",fontsize=10,fontweight="bold",color="white",
  bbox=dict(boxstyle="round,pad=0.28",fc=INK,ec="none"),va="center")
fig.text(0.04,0.962,"Local certification does not compose",fontsize=8.2,fontweight="semibold",color=INK,va="center")

def ic_docs(cx,cy,c):
    for dx,dy,al in [(0.6,-0.6,0.35),(0,0,1)]:
        a.add_patch(rbox(cx-1.3+dx,cy-1.7+dy,2.6,3.4,0.35,fc="white",ec=c,lw=0.9,alpha=al,zorder=6))
    for k in range(3): a.plot([cx-0.7,cx+0.7],[cy+0.7-k*0.7]*2,color=c,lw=0.7,zorder=7)
def ic_plug(cx,cy,c):
    a.text(cx,cy-0.1,r"$\{\ \}$",ha="center",va="center",color=c,fontsize=6.6,zorder=7)
def ic_graph(cx,cy,c):
    pts=[(cx-1.3,cy-0.9),(cx+1.3,cy-0.9),(cx,cy+1.3)]
    for i in range(3):
        for j in range(i+1,3): a.plot(*zip(pts[i],pts[j]),color=c,lw=0.8,zorder=6)
    for p in pts: a.add_patch(Circle(p,0.55,fc="white",ec=c,lw=0.9,zorder=7))

W=26; Y=51; H=16.5
cards=[(2,"Retriever A",GRN,"#F2FBF7","#DDF3EA","-",ic_docs),
       (37,"Interface",SUB,"#F6F7FA","#E9ECF3",(0,(3,2)),ic_plug),
       (72,"Orchestrator B",GRN,"#F2FBF7","#DDF3EA","-",ic_graph)]
for x,t,ec,c1,c2,ls,ico in cards:
    shadow(x,Y,W,H)
    gradbox(x,Y,W,H,c1,c2,ec=ec,lw=1.1,ls=ls)
    a.add_patch(Circle((x+4.4,Y+H-4.0),2.7,fc="white",ec=ec,lw=0.9,zorder=5))
    ico(x+4.4,Y+H-4.0,ec)
    a.text(x+8.4,Y+H-4.0,t,ha="left",va="center",fontsize=6.9,fontweight="bold",color=INK,zorder=6)
for x in (2,72):
    a.text(x+13,Y+7.2,r"local $\hat{\beta}=0$",ha="center",va="center",color=INK,fontsize=7.4,zorder=6)
    a.add_patch(rbox(x+6.2,Y+1.6,13.6,3.6,1.8,fc=GRN,ec="none",zorder=5))
    a.plot([x+8.0,x+8.8,x+10.1],[Y+3.5,Y+2.8,Y+4.2],color="white",lw=1.0,solid_capstyle="round",zorder=7)
    a.text(x+14.8,Y+3.4,"certified",ha="center",va="center",color="white",fontsize=6.2,fontweight="semibold",zorder=7)
a.text(50,Y+7.6,"tool: retriever",ha="center",va="center",family="DejaVu Sans Mono",fontsize=6.0,color=SUB,zorder=6)
a.add_patch(rbox(41.5,Y+1.6,17,3.8,1.9,fc=REDL,ec=RED,lw=0.7,zorder=5))
a.text(50,Y+3.5,r"doc $\ni$ $s_A$",ha="center",va="center",color=RED,fontsize=6.9,fontweight="semibold",zorder=7)
for x0,x1 in [(28.4,36.6),(63.4,71.6)]:
    a.add_patch(FancyArrowPatch((x0,Y+H/2),(x1,Y+H/2),arrowstyle="-|>",mutation_scale=7,lw=1.0,color=INK,zorder=6))

glow_line([50,50],[Y-0.5,39.4],RED,w=1.8)
a.add_patch(FancyArrowPatch((50,41.2),(50,37.6),arrowstyle="-|>",mutation_scale=11,lw=1.8,color=RED,zorder=6))
a.add_patch(rbox(53,43.4,13.5,4.4,2.2,fc=RED,ec="none",zorder=6))
a.text(59.75,45.6,r"secret $s_A$",ha="center",va="center",color="white",fontsize=6.6,fontweight="semibold",zorder=7)
a.text(46.2,45.6,"leaks across\nthe interface",ha="right",va="center",color=RED,fontsize=6.4,style="italic",linespacing=1.15,zorder=6)

px,py,pw,ph=5,3.2,90,34.2
shadow(px,py,pw,ph,r=2.8,s=0.35)
gradbox(px,py,pw,ph,NAVY,NAVY2,r=2.8,ec=RED,lw=1.3,vertical=False,z=2)
a.add_patch(rbox(px+3,py+ph-6.2,11,3.8,1.9,fc=RED,ec="none",zorder=6))
a.text(px+8.5,py+ph-4.3,"BREACH",ha="center",va="center",color="white",fontsize=5.9,fontweight="bold",zorder=7)
a.text(px+17,py+ph-4.3,r"Composed pipeline  $A\!\rightarrow\!B$",ha="left",va="center",color="white",fontsize=7.8,fontweight="bold",zorder=7)
a.text(px+4,py+15.5,r"$\hat{\beta}$",ha="left",va="center",color="#FF7A97",fontsize=25,zorder=7)
a.text(px+14.2,py+15.5,"= 1.0",ha="left",va="center",color="white",fontsize=21,fontweight="bold",zorder=7)
sx=px+44; sy=py+19.6
a.text(sx,sy+6.6,"breaches   20 / 20",ha="left",va="center",color="#E5E7F0",fontsize=7,fontweight="semibold",zorder=7)
for i in range(20):
    xx=sx+i*2.05
    for gl,al in [(0.9,0.12),(0.45,0.22)]:
        a.add_patch(rbox(xx-gl,sy-gl,1.7+2*gl,4.4+2*gl,0.5,fc=RED,ec="none",alpha=al,zorder=6))
    a.add_patch(rbox(xx,sy,1.7,4.4,0.4,fc="#FF3B5F",ec="none",zorder=7))
x0=sx; x1=sx+19*2.05+1.7; ay=py+11.6
a.plot([x0,x1],[ay,ay],color="#8A91A8",lw=0.9,zorder=7)
for t in (0,0.5,1):
    xx=x0+t*(x1-x0); a.plot([xx,xx],[ay-0.8,ay+0.8],color="#8A91A8",lw=0.9,zorder=7)
    a.text(xx,ay-2.6,f"{t:g}",ha="center",va="center",fontsize=5.6,color="#9AA1B8",zorder=7)
cx=x0+0.84*(x1-x0)
a.add_patch(rbox(cx,ay-0.9,x1-cx,1.8,0.9,fc="#FF3B5F",ec="none",zorder=8))
a.text(x1,ay+3.1,"Wilson 95% CI  [0.84, 1.00]",ha="right",va="center",fontsize=5.9,color="#FFB3C2",zorder=7)
a.plot([px+4,px+pw-4],[py+7.2,py+7.2],color="#FFFFFF",alpha=0.12,lw=0.6,zorder=6)
a.text(px+4,py+3.9,"No component is individually non-compliant.",ha="left",va="center",fontsize=6.3,style="italic",color="#C9CEE0",zorder=7)

fig.text(0.612,0.962,"b",fontsize=10,fontweight="bold",color="white",bbox=dict(boxstyle="round,pad=0.28",fc=INK,ec="none"),va="center")
fig.text(0.640,0.962,"Public certification can be gamed",fontsize=8.2,fontweight="semibold",color=INK,va="center")
b=fig.add_axes([0.765,0.20,0.215,0.57])
b.set_xlim(-0.06,1.36); b.set_ylim(-0.55,2.55)
cm=LinearSegmentedColormap.from_list("z",["#D5F2E6","#F6FCF9"])
b.imshow(np.linspace(0,1,64).reshape(1,-1),extent=(-0.06,0.2,-0.55,2.55),cmap=cm,aspect="auto",zorder=0)
b.axvline(0.2,color=GRN,lw=1.0,ls=(0,(3,2)),zorder=1)
b.text(0.2,2.62,r"$\tau=0.2$",ha="center",va="bottom",fontsize=6.6,color=GRN,fontweight="semibold",clip_on=False)
b.text(0.07,-0.45,"pass",ha="center",va="center",fontsize=6,color=GRN,fontweight="semibold")
rows=[("Probe-aware","passes public, fails held-out",0.0,1.0),
      ("Semantics-only","fails both",1.0,1.0),
      ("Resistant","passes both",0.0,0.0)]
ys=[2,1,0]
for (n,sub,p,h),y in zip(rows,ys):
    b.plot([0,1],[y,y],color="#E7EAF2",lw=6,solid_capstyle="round",zorder=2)
    if p!=h:
        for i in range(5,0,-1): b.plot([p,h],[y,y],color=PUR,lw=2+i*2,alpha=0.06,solid_capstyle="round",zorder=3)
        b.plot([p,h],[y,y],color=PUR,lw=2.4,solid_capstyle="round",zorder=4)
    b.scatter([p],[y],s=140 if p==h else 72,color=BLU,edgecolor="white",linewidth=1.1,zorder=6)
    b.scatter([h],[y],s=64,color=ORG,marker="D",edgecolor="white",linewidth=1.0,zorder=7)
    b.text(-0.12,y+0.10,n,ha="right",va="center",fontsize=7.4,fontweight="bold",color=INK,clip_on=False)
    b.text(-0.12,y-0.20,sub,ha="right",va="center",fontsize=5.4,color=SUB,clip_on=False)
    g=h-p
    b.text(1.25,y,rf"$\Gamma={g:.0f}$",ha="center",va="center",fontsize=6.9,fontweight="bold",color="white" if g else SUB,zorder=7,clip_on=False,
        bbox=dict(boxstyle="round,pad=0.38,rounding_size=0.9",fc=PUR if g else "#EEF0F5",ec="none"))
b.set_yticks([]); b.set_xticks([0,0.2,0.5,1.0]); b.set_xticklabels(["0","0.2","0.5","1.0"],fontsize=6.4,color=SUB)
b.set_xlabel(r"mean family score $\hat{\Phi}$",fontsize=7.2,color=INK,labelpad=3)
for s in ("top","right","left"): b.spines[s].set_visible(False)
b.spines["bottom"].set_color(LINE); b.tick_params(axis="x",length=2.5,color=LINE)
b.text(1.25,2.52,"gaming gap",ha="center",va="bottom",fontsize=5.8,color=PUR,fontweight="semibold",clip_on=False)
h=[Line2D([],[],marker="o",color="none",markerfacecolor=BLU,markeredgecolor="white",markersize=6,label="public probes"),
   Line2D([],[],marker="D",color="none",markerfacecolor=ORG,markeredgecolor="white",markersize=5.2,label="held-out paraphrases")]
fig.legend(handles=h,loc="lower center",bbox_to_anchor=(0.795,-0.015),ncol=2,frameon=False,fontsize=6.6,handletextpad=0.1,columnspacing=1.2)
fig.add_artist(Line2D([0.598,0.598],[0.05,0.93],color=LINE,lw=0.8,transform=fig.transFigure))
for ext in ("pdf","svg","png"):
    fig.savefig(f"fig4_premium.{ext}",dpi=400)
