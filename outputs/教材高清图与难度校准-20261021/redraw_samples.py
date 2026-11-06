#!/usr/bin/env python3
"""Rebuild ten source-linked SVG drawing prototypes; no textbook files are changed."""
import html
import json
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
BLUE, RED, INK, GRAY = '#1687a7', '#c34248', '#232c33', '#859099'


class Drawing:
    def __init__(self, title, w=680, h=430):
        self.w, self.h = w, h
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title">',
                      f'<title id="title">{html.escape(title)}</title>',
                      '<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0 L7 3.5 L0 7 Z" fill="#232c33"/></marker></defs>',
                      '<rect width="100%" height="100%" fill="white"/>',
                      '<g stroke-linecap="round" stroke-linejoin="round">']

    def line(self, a, b, color=INK, dash=False, width=2, arrow=False):
        self.parts.append(f'<path d="M{a[0]:.3f},{a[1]:.3f} L{b[0]:.3f},{b[1]:.3f}" fill="none" stroke="{color}" stroke-width="{width}"'+(' stroke-dasharray="6 5"' if dash else '')+(' marker-end="url(#arrow)"' if arrow else '')+'/>')

    def poly(self, points, color=INK, width=2.3, close=False, fill='none', dash=False):
        d='M'+' L'.join(f'{x:.3f},{y:.3f}' for x,y in points)+(' Z' if close else '')
        self.parts.append(f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{width}"'+(' stroke-dasharray="6 5"' if dash else '')+'/>')

    def text(self, p, text, size=23, anchor='middle', color=INK, raw=False):
        value = text if raw else html.escape(text)
        self.parts.append(f'<text x="{p[0]:.3f}" y="{p[1]:.3f}" fill="{color}" text-anchor="{anchor}" font-family="Georgia,Times New Roman,serif" font-size="{size}">{value}</text>')

    def dot(self, p, color=INK, radius=4):
        self.parts.append(f'<circle cx="{p[0]:.3f}" cy="{p[1]:.3f}" r="{radius}" fill="{color}"/>')

    def save(self, name):
        dest=OUT/'svg'/name
        dest.parent.mkdir(exist_ok=True)
        dest.write_text('\n'.join(self.parts+['</g></svg>']), encoding='utf-8')
        return dest


def sub(letter, n):
    return f'{letter}<tspan baseline-shift="sub" font-size="15">{n}</tspan>'


def exponent(base):
    return f'y = {base}<tspan baseline-shift="super" font-size="16">x</tspan>'


def axes(d, bounds, area=(75,45,585,350), xticks=(), yticks=()):
    xmin,xmax,ymin,ymax=bounds; l,t,r,b=area
    def pt(x,y):return (l+(x-xmin)/(xmax-xmin)*(r-l),b-(y-ymin)/(ymax-ymin)*(b-t))
    d.line(pt(xmin,0),pt(xmax,0),width=1.5,arrow=True)
    d.line(pt(0,ymin),pt(0,ymax),width=1.5,arrow=True)
    d.text((pt(xmax,0)[0]+16,pt(xmax,0)[1]+8),'x')
    d.text((pt(0,ymax)[0]-14,pt(0,ymax)[1]-10),'y')
    d.text((pt(0,0)[0]-16,pt(0,0)[1]+24),'O')
    for x,label in xticks:
        X,Y=pt(x,0);d.line((X,Y),(X,Y-6),width=1.2);d.text((X,Y+27),label,size=20)
    for y,label in yticks:
        X,Y=pt(0,y);d.line((X,Y),(X+6,Y),width=1.2);d.text((X-13,Y+7),label,size=20,anchor='end')
    return pt


def curve(d,pt,fn,a,b,color=INK,n=450):
    pts=[pt(a+(b-a)*i/n,fn(a+(b-a)*i/n)) for i in range(n+1)]
    d.poly(pts,color=color,width=2.8)


SAMPLES = [
 ('x1-2-2','图2-2-1','椭圆拉绳','bo_d4sln7jef24c73be0pd0_14_1111_1096_348_230_0.jpg', '数学结构重绘，省略手、笔和木板；不是像素级描摹。焦点由 c²=a²−b² 计算，M 位于椭圆上。'),
 ('x1-3-1','图3-1-2','长方体向量','bo_d4slnd3ef24c73be0pi0_2_1135_1534_301_290_0.jpg', '用三维顶点投影作图，保留原辅助线。C、C₁、E 共线且等距；投影中的长度与角度不作真实量读取。'),
 ('bx1-4-2','图4-2-1','指数函数2与3','bo_d4slocn7aajc73fspklg_8_1154_439_298_304_0.jpg', '曲线按函数值计算，不描摹像素；原图红蓝对应关系保持。'),
 ('bx1-4-3','图4-3-1','对数函数2与3','bo_d4slocn7aajc73fspklg_15_172_1013_348_270_0.jpg', '只绘制 x>0；共同点为 (1,0)，不跨越定义域边界。'),
 ('bx2-7-1','图7-1-4','正弦五点','bo_d5205277aajc73fu465g_2_352_1855_544_250_0.jpg', '五个关键点直接由正弦函数计算。保留闭区间端点与横轴刻度。'),
 ('bx2-8-1','图8-1-4','等边三角形中点','bo_d4sllcbef24c73be0n80_2_1144_1107_317_287_0.jpg', '等比例绘制等边三角形。D、E、F 分别为 BC、AB、AC 中点，不增添原图没有的向量箭头。'),
 ('bx3-10-1','图10-1-5','线面两种关系','bo_d4slm1v7aajc73fspjsg_3_708_399_630_240_0.jpg', '保留相交与无公共点两个子图。第二幅直线画在平面轮廓外；第一幅遮挡段使用虚线。'),
 ('bx3-11-1','图11-1-1','三种棱柱','bo_d4slmdf7aajc73fspjug_1_542_1495_967_337_0.jpg', '三维模型分别为斜三棱柱、直四棱柱、正六棱柱；保留对应顶点名和隐藏边。'),
 ('x2-5-1','图5-1-3','半圆割线','bo_d4slovref24c73be0r3g_5_192_1195_285_190_0.jpg', '等比例绘制上半圆 x²+y²=2。直线经过 P=(1,1)、Q=(0,√2)，是割线而非切线。'),
 ('x2-8-2','图8-2-1','散点与候选直线','bo_d4slp7f7aajc73fspkr0_9_577_1340_876_450_0.jpg', '10对散点读取表8-1原始数据；两条候选线来自正文，非从低清图片估读。保留原坐标单位。'),
]


def make_drawings():
    drawings=[]; checks=[]
    d=Drawing('椭圆的拉绳数学结构'); a,b=220,125;c=math.sqrt(a*a-b*b);cx,cy=340,220
    P=lambda x,y:(cx+x,cy-y)
    d.poly([P(a*math.cos(t*2*math.pi/500),b*math.sin(t*2*math.pi/500)) for t in range(501)])
    M=P(a*math.cos(1.12),b*math.sin(1.12)); F1=P(-c,0);F2=P(c,0)
    for F in [F1,F2]:d.line(F,M,BLUE,width=3);d.dot(F)
    d.dot(M);d.text((M[0]+12,M[1]-16),'M');d.text((F1[0],F1[1]+33),sub('F',1),raw=True);d.text((F2[0],F2[1]+33),sub('F',2),raw=True)
    checks.append({'sample':1,'focus_distance_sum':sum(math.dist(M,f) for f in [F1,F2]),'expected':2*a,'error':abs(sum(math.dist(M,f) for f in [F1,F2])-2*a)})
    drawings.append(d)

    d=Drawing('长方体中的向量'); V={'A':(0,0,0),'B':(2,0,0),'C':(2,1,0),'D':(0,1,0),'A1':(0,0,1),'B1':(2,0,1),'C1':(2,1,1),'D1':(0,1,1),'E':(2,1,2)}
    proj=lambda p:(160+130*p[0]+85*p[1],360-58*p[1]-125*p[2])
    edges=[('A','B'),('B','C'),('C','D'),('D','A'),('A1','B1'),('B1','C1'),('C1','D1'),('D1','A1'),('A','A1'),('B','B1'),('C','C1'),('D','D1'),('C1','E')]
    hidden={frozenset(x) for x in [('C','D'),('D','A'),('D','D1')]}
    for u,v in edges:d.line(proj(V[u]),proj(V[v]),dash=frozenset((u,v)) in hidden)
    for u,v in [('A','C1'),('D1','B'),('D1','B1')]:d.line(proj(V[u]),proj(V[v]),dash=(u,v)!=('D1','B1'),width=1.6)
    d.line(proj(V['A']),proj(V['E']),width=2.5)
    offsets={'A':(-17,18),'B':(10,24),'C':(18,10),'D':(-12,21),'A1':(-23,-4),'B1':(15,12),'C1':(22,5),'D1':(-18,-14),'E':(17,-8)}
    for name,p in V.items():
        q=proj(p);dx,dy=offsets[name];d.text((q[0]+dx,q[1]+dy),sub(name[0],1) if name.endswith('1') else name,raw=True)
    checks.append({'sample':2,'CC1':math.dist(V['C'],V['C1']),'C1E':math.dist(V['C1'],V['E'])});drawings.append(d)

    d=Drawing('指数函数 y=2^x 与 y=3^x');pt=axes(d,(-2.4,2.5,-.35,6.2),xticks=[(1,'1')],yticks=[(1,'1')])
    curve(d,pt,lambda x:2**x,-2.4,2.45,RED);curve(d,pt,lambda x:3**x,-2.4,math.log(5.8,3),BLUE)
    d.text((505,135),exponent(2),color=RED,raw=True);d.text((435,55),exponent(3),color=BLUE,raw=True);drawings.append(d)

    d=Drawing('对数函数 y=log₂x 与 y=log₃x');pt=axes(d,(-.35,5.2,-2,2.6),xticks=[(1,'1')],yticks=[(1,'1')])
    curve(d,pt,lambda x:math.log(x,2),.26,5,BLUE);curve(d,pt,lambda x:math.log(x,3),.12,5,RED)
    d.text((445,54),'y = log<tspan baseline-shift="sub" font-size="15">2</tspan>x',color=BLUE,raw=True)
    d.text((465,175),'y = log<tspan baseline-shift="sub" font-size="15">3</tspan>x',color=RED,raw=True);drawings.append(d)

    d=Drawing('正弦函数在一个周期内的五个关键点',800,390)
    pt=axes(d,(-.3,6.8,-1.45,1.55),area=(45,45,745,325),xticks=[(math.pi/2,'π/2'),(math.pi,'π'),(3*math.pi/2,'3π/2'),(2*math.pi,'2π')],yticks=[(-1,'−1'),(1,'1')])
    curve(d,pt,math.sin,0,2*math.pi)
    for x in [0,math.pi/2,math.pi,3*math.pi/2,2*math.pi]:d.dot(pt(x,math.sin(x)))
    d.text((445,35),'y = sin x,  x ∈ [0, 2π]',size=23);drawings.append(d)

    d=Drawing('等边三角形及三边中点');P={'A':(340,50),'B':(150,50+190*math.sqrt(3)),'C':(530,50+190*math.sqrt(3))}
    for n,a1,b1 in [('D','B','C'),('E','A','B'),('F','A','C')]:P[n]=tuple((a+b)/2 for a,b in zip(P[a1],P[b1]))
    d.poly([P[n] for n in ['A','B','C']],close=True);d.poly([P[n] for n in ['D','E','F']],close=True)
    for n,off in [('A',(0,-15)),('B',(-18,14)),('C',(18,14)),('D',(0,30)),('E',(-20,0)),('F',(20,0))]:d.text((P[n][0]+off[0],P[n][1]+off[1]),n)
    checks.append({'sample':6,'AB':math.dist(P['A'],P['B']),'BC':math.dist(P['B'],P['C']),'AC':math.dist(P['A'],P['C'])});drawings.append(d)

    d=Drawing('直线与平面的相交与平行',900,360)
    for shift in [0,440]:
        poly=[(50+shift,240),(310+shift,240),(400+shift,130),(140+shift,130)]
        d.poly(poly,close=True,fill='#f4f7f8',width=1.8);d.text((105+shift,222),'α',size=26)
    A=(230,196);d.line((155,55),A);d.line(A,(253.4,240),dash=True);d.line((253.4,240),(288,305));d.dot(A);d.text((250,183),'A');d.text((180,70),'l')
    d.line((540,100),(805,100));d.text((825,109),'l');d.text((230,340),'(1)');d.text((680,340),'(2)');drawings.append(d)

    d=Drawing('斜三棱柱、直四棱柱、正六棱柱',1150,430)
    visibility_checks=[]
    def prism(base,shift,project,names,hidden_edges,camera):
        vertices=base+[tuple(a+b for a,b in zip(p,shift)) for p in base];n=len(base)
        # Check hidden edges from face normals, not from screen appearance alone.
        def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
        facing=[]
        for i in range(n):
            edge=tuple(b-a for a,b in zip(base[i],base[(i+1)%n]))
            normal=cross(edge,shift)
            facing.append(sum(a*b for a,b in zip(normal,camera)))
        computed={frozenset((i,(i+1)%n)) for i in range(n) if facing[i]<0}
        computed|={frozenset((i,i+n)) for i in range(n) if facing[i]<0 and facing[(i-1)%n]<0}
        assert computed==hidden_edges,(names,computed,hidden_edges)
        visibility_checks.append({'base_vertices':base,'translation':shift,'camera_direction':camera,'side_face_normal_dot_camera':facing,'hidden_edges':[sorted(v) for v in sorted(computed,key=lambda v:sorted(v))]})
        es=[(i,(i+1)%n) for i in range(n)]+[(i+n,(i+1)%n+n) for i in range(n)]+[(i,i+n) for i in range(n)]
        for i,j in es:d.line(project(vertices[i]),project(vertices[j]),dash=frozenset((i,j)) in hidden_edges,width=1.8)
        for i,p in enumerate(vertices):
            q=project(p);name=names[i%n]+('′' if i>=n else ''); d.text((q[0]+(-10 if i%n==0 else 8),q[1]+(-12 if i>=n else 22)),name,size=20)
        return vertices
    p1=lambda p:(75+100*p[0]+38*p[1],325-32*p[1]-100*p[2])
    prism([(0,0,0),(1,-1,0),(2,0,0)],(.35,.1,1.55),p1,['A','B','C'],{frozenset((0,2))},(3800,-10000,3200))
    p2=lambda p:(450+100*p[0]+45*p[1],330-35*p[1]-120*p[2])
    prism([(0,0,0),(1.5,0,0),(1.5,1,0),(0,1,0)],(0,0,1.4),p2,['A','B','C','D'],{frozenset(v) for v in [(0,3),(2,3),(3,7)]},(5400,-12000,3500))
    # The hexagonal bases are vertical; the prism axis is horizontal in the model.
    base=[(0,math.cos(t),math.sin(t)) for t in [-2*math.pi/3,-math.pi/3,0,math.pi/3,2*math.pi/3,math.pi]]
    p3=lambda p:(855+115*p[0]+28*p[1],230-30*p[1]-95*p[2])
    prism(base,(1.65,0,0),p3,['A','B','C','D','E','F'],{frozenset(v) for v in [(0,1),(1,2),(2,3),(1,7),(2,8)]},(2660,-10925,3450))
    for x,txt in [(220,'(1)'),(560,'(2)'),(950,'(3)')]:d.text((x,405),txt)
    checks.append({'sample':8,'model':'Each top base is a translation of its bottom base; quadrilateral and hexagonal axes are perpendicular to the base planes.','visibility_checks':visibility_checks});drawings.append(d)

    d=Drawing('上半圆与割线 PQ');scale=145;pt=lambda x,y:(340+x*scale,330-y*scale)
    d.line(pt(-1.8,0),pt(1.9,0),width=1.5,arrow=True);d.line(pt(0,-.25),pt(0,1.95),width=1.5,arrow=True)
    d.text(pt(1.98,-.06),'x');d.text(pt(-.12,1.94),'y');d.text(pt(-.13,-.18),'O')
    d.poly([pt(math.sqrt(2)*math.cos(t*math.pi/400),math.sqrt(2)*math.sin(t*math.pi/400)) for t in range(401)],width=2.6)
    m=1-math.sqrt(2);d.line(pt(-.9,math.sqrt(2)-.9*m),pt(1.7,math.sqrt(2)+1.7*m))
    for name,p,offset in [('P',(1,1),(.15,.12)),('Q',(0,math.sqrt(2)),(-.18,-.13))]:d.dot(pt(*p));d.text(pt(p[0]+offset[0],p[1]+offset[1]),name)
    checks.append({'sample':9,'secant_slope':m,'P_on_circle_error':abs(1**2+1**2-2),'Q_on_circle_error':abs(math.sqrt(2)**2-2),'same_scale_xy':True});drawings.append(d)

    d=Drawing('表8-1散点及两条候选直线',820,460)
    pt=axes(d,(0,16,0,4.2),area=(95,55,745,370),xticks=[(5,'5'),(10,'10'),(15,'15')],yticks=[(.5,'0.5'),(1,'1'),(1.5,'1.5'),(2,'2'),(2.5,'2.5'),(3,'3'),(3.5,'3.5'),(4,'4')])
    xs=[4,4,4.6,5,5.2,5.6,6,6.6,7,10];ys=[3.5,3,2.7,2.4,2.5,2,1.5,1.2,1.2,1]
    curve(d,pt,lambda x:-.5*x+5,4,9,RED);curve(d,pt,lambda x:-.4*x+4.5,4,10,BLUE)
    for x,y in zip(xs,ys):
        X,Y=pt(x,y);d.poly([(X,Y-4.5),(X+4.5,Y),(X,Y+4.5),(X-4.5,Y)],close=True,fill='#334d7a',color='#334d7a',width=1)
    d.text((220,30),'年需求量 / 千克',size=22);d.text((600,430),'每千克价格 / 百元',size=22)
    checks.append({'sample':10,'data_points':list(zip(xs,ys)),'line_models':['y=-0.5x+5.0','y=-0.4x+4.5']});drawings.append(d)

    meta=[]
    for i,(spec,d) in enumerate(zip(SAMPLES,drawings),1):
        section,fig,title,source,note=spec;name=f'{section}_{fig}_{title}.svg';path=d.save(name)
        meta.append({'number':i,'section_id':section,'figure':fig,'title':title,'original_basename':source,'svg':'svg/'+name,'note':note,'printed_page':None,'status':'小样待用户审定'})
    (OUT/'10张重绘小样清单.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'图形模型核验.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    return meta


if __name__ == '__main__':
    make_drawings()
