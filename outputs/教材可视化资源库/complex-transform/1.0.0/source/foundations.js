(function () {
  'use strict';
  const tau = 2 * Math.PI;
  const rad = d => Number(d) * Math.PI / 180;
  const circle = (L, w, x, y, r, cls = 'aux') => L.path(Array.from({length: 181}, (_, i) => w.p(x + r * Math.cos(tau * i / 180), y + r * Math.sin(tau * i / 180))), cls, true);
  const graph = (L, w, fn, lo, hi, cls = 'curve') => L.path(Array.from({length: 181}, (_, i) => {const x = lo + (hi - lo) * i / 180; return w.p(x, fn(x));}), cls);
  const E = {};
  E['amgm-square'] = {
    model(s) {const a=Number(s.a),b=8-a; return {a,b,sum:8,area:a*b,maximum:16,defect:(a-b)**2/4,am:4,gm:Math.sqrt(a*b)};},
    render(s,L) {const m=this.model(s),w=L.world(-.8,9,-.8,8),p=(x,y)=>w.p(x,y);
      return {svg:w.axes+L.polygon([p(0,0),p(m.a,0),p(m.a,m.b),p(0,m.b)],'area')+L.line(p(4,0),p(4,4),'dashed')+L.line(p(0,4),p(4,4),'dashed')+L.text(...p(m.a/2,-.35),'a = '+L.fmt(m.a))+L.text(...p(m.a+.15,m.b/2),'b = '+L.fmt(m.b)),metrics:[['a + b', '8（固定）'],['矩形面积 ab（近似）',L.fmt(m.area)],['正方形面积', '16'],['面积差（近似）',L.fmt(m.defect)],['算术均值 / 几何均值（近似）',L.fmt(m.am)+' / '+L.fmt(m.gm)]],note:'虚线为边长 4 的正方形参考，不表示原矩形始终包含于其中。和固定时 ab ≤ 16；面积差等于 (a-b)²/4，且仅 a=b=4 时为零。一般证明见公式与原文，动态取样不是证明。'};}
  };
  E['exponential-base'] = {
    model(s) {const a=Number(s.base),x=Number(s.x); return {a,x,y:a**x,reciprocal:(1/a)**x,kind:a>1?'严格增':a<1?'严格减':'常函数（排除的边界）'};},
    render(s,L) {const m=this.model(s),w=L.world(-3.5,3.5,-.6,5.4);let lo=-3.2,hi=3.2;
      if(m.a>1) hi=Math.min(hi,Math.log(5.2)/Math.log(m.a));
      if(m.a<1) lo=Math.max(lo,Math.log(5.2)/Math.log(m.a));
      return {svg:w.axes+graph(L,w,x=>m.a**x,lo,hi)+L.dot(w.p(0,1),'(0,1)')+(m.y<=5.2?L.dot(w.p(m.x,m.y),'P'):'')+L.text(35,35,'y = a 的 x 次幂'),metrics:[['底数 a',L.fmt(m.a)],['单调性',m.kind],['函数值（近似）',L.fmt(m.y)]],note:'a > 0 且 a ≠ 1 才称本节的指数函数；a=1 可单独观察常函数边界。所有点在 x 轴上方，并过 (0,1)。视窗外的曲线不绘制，不代表函数存在上界；趋近 x 轴而不相交。'};}
  };
  E['logarithm-reflection'] = {
    model(s) {const a=Number(s.base),t=Number(s.t),u=a**t;return {a,t,u,inverse:Math.log(u)/Math.log(a),kind:a>1?'严格增':'严格减'};},
    render(s,L) {const m=this.model(s),w=L.world(-2.7,5.5,-2.7,5.5);const bound=Math.min(2.5,Math.log(5.2)/Math.abs(Math.log(m.a)));const lo=-bound,hi=bound;
      const pts=Array.from({length:181},(_,i)=>{const t=lo+(hi-lo)*i/180;return [t,m.a**t];});
      return {svg:w.axes+L.line(w.p(-2.5,-2.5),w.p(5.2,5.2),'dashed')+L.path(pts.map(([x,y])=>w.p(x,y)),'secondary')+L.path(pts.map(([x,y])=>w.p(y,x)))+L.line(w.p(m.t,m.u),w.p(m.u,m.t),'aux')+L.dot(w.p(m.t,m.u),'P')+L.dot(w.p(m.u,m.t),'Q')+L.text(35,35,'实线：对数；虚线：y = x；蓝线：指数'),metrics:[['底数 a',L.fmt(m.a)],['P = (t,a 的 t 次幂)（近似）',`(${L.fmt(m.t)}, ${L.fmt(m.u)})`],['Q 交换坐标（近似）',`(${L.fmt(m.u)}, ${L.fmt(m.t)})`],['对数单调性',m.kind]],note:'对数定义域为正实数，值域为全体实数，过 (1,0)，以 y 轴为渐近线。a>1 时 x>1 为正、0<x<1 为负；0<a<1 时相反。互为倒数的底数对应图像关于 x 轴对称；本图重点展示同底指数与对数关于 y=x 对称。'};}
  };
  E['monotonic-two-points'] = {
    model(s) {const kind=s.kind,x1=Number(s.left),gap=Number(s.gap),x2=x1+gap;const f=kind==='square'?x=>x*x:kind==='cube'?x=>x*x*x/3:kind==='decreasing'?x=>-x:x=>1;return {kind,x1,x2,y1:f(x1),y2:f(x2),delta:f(x2)-f(x1),f};},
    render(s,L) {const m=this.model(s),w=L.world(-3.3,3.3,-3.3,5.8);
      const points=Array.from({length:181},(_,i)=>{const x=-2.6+5.2*i/180;return [x,m.f(x)];}).filter(([,y])=>y>=-3.2&&y<=5.6);
      return {svg:w.axes+L.path(points.map(p=>w.p(...p)))+L.dot(w.p(m.x1,m.y1),'P₁')+L.dot(w.p(m.x2,m.y2),'P₂')+L.line(w.p(m.x1,m.y1),w.p(m.x2,m.y2),'secondary'),metrics:[['x₁ < x₂（近似）',L.fmt(m.x1)+' < '+L.fmt(m.x2)],['f(x₂) - f(x₁)（近似）',L.fmt(m.delta)],['这两个点',m.delta>0?'函数值上升':m.delta<0?'函数值下降':'函数值相等']],note:'定义要求区间内任意 x₁<x₂ 都成立，单看两个点不能证明单调性。平方函数的差为 (x₂-x₁)(x₁+x₂)，故在负半轴严格减、正半轴严格增；常函数同时是增函数和减函数，但均不严格。图像超出视窗部分不绘制。'};}
  };
  E['inverse-domain'] = {
    model(s) {const x=Number(s.x),branch=s.branch,t=branch==='negative'?-x:x;return {x:t,y:t*t,inverse:branch==='negative'?-Math.sqrt(t*t):Math.sqrt(t*t),branch};},
    render(s,L) {const m=this.model(s),w=L.world(-3,5,-3,5),lo=m.branch==='negative'?-2:0,hi=m.branch==='negative'?0:2;const pts=Array.from({length:121},(_,i)=>{const x=lo+(hi-lo)*i/120;return [x,x*x];});
      return {svg:w.axes+L.line(w.p(-2.7,-2.7),w.p(4.7,4.7),'dashed')+L.path(pts.map(p=>w.p(...p)),'secondary')+L.path(pts.map(([x,y])=>w.p(y,x)))+L.line(w.p(m.x,m.y),w.p(m.y,m.x),'aux')+L.dot(w.p(m.x,m.y),'P')+L.dot(w.p(m.y,m.x),'P′'),metrics:[['原函数定义域',m.branch==='negative'?'(-∞,0]':'[0,+∞)'],['P 近似坐标',`(${L.fmt(m.x)}, ${L.fmt(m.y)})`],['反函数取值（近似）',L.fmt(m.inverse)]],note:'同一平方值通常对应正负两个数；必须先限制原函数定义域，才能取一个反函数分支。交换坐标使两图关于 y=x 对称：PP′ 中点在 y=x 上，PP′ 与 y=x 垂直（重合点除外）。反函数定义域是原函数值域。'};}
  };
  E['unit-circle-projection'] = {
    model(s) {const theta=rad(s.angle),cos=Math.cos(theta),sin=Math.sin(theta);return {theta,cos,sin,tan:Math.abs(cos)<1e-12?null:sin/cos,cot:Math.abs(sin)<1e-12?null:cos/sin};},
    render(s,L) {const m=this.model(s),w=L.world(-1.8,1.8,-1.8,1.8),p=w.p(m.cos,m.sin);return {svg:w.axes+circle(L,w,0,0,1)+L.line(w.p(0,0),p,'curve')+L.line(w.p(m.cos,0),p,'highlight')+L.line(w.p(0,0),w.p(m.cos,0),'secondary')+L.dot(p,'P')+L.text(35,35,'单位圆：横坐标 cos，纵坐标 sin'),metrics:[['角度',String(s.angle)+'°'],['cos（近似）',L.fmt(m.cos)],['sin（近似）',L.fmt(m.sin)],['tan（近似）',m.tan===null?'未定义':L.fmt(m.tan)],['cot（近似）',m.cot===null?'未定义':L.fmt(m.cot)]],note:'终边上任意非原点 P(x,y)，r>0，sin=y/r，cos=x/r；单位圆取 r=1。投影是带符号坐标，不能用无符号线段长度代替。tan 要求横坐标非零；cot 要求纵坐标非零。转过整周坐标不变。'};}
  };
  E['sine-unroll'] = {
    model(s) {const theta=rad(s.angle);return {theta,x:Math.cos(theta),y:Math.sin(theta),period:tau};},
    render(s,L) {const m=this.model(s),w=L.world(-4,7.3,-2.8,2.8),cx=-2.3;const pp=w.p(cx+m.x,m.y),q=w.p(m.theta,m.y);return {svg:w.axes+circle(L,w,cx,0,1)+L.line(w.p(cx,0),pp,'secondary')+L.line(pp,q,'dashed')+graph(L,w,Math.sin,0,tau,'aux')+graph(L,w,Math.sin,0,m.theta,'curve')+[0,Math.PI/2,Math.PI,3*Math.PI/2,tau].map(a=>L.dot(w.p(a,Math.sin(a)),'','point')).join('')+L.dot(pp,'P')+L.dot(q,'M')+L.text(35,35,'同一高度：圆上纵坐标 → 曲线上函数值'),metrics:[['横坐标 / 弧度（近似）',L.fmt(m.theta)],['纵坐标 sin（近似）',L.fmt(m.y)],['一周', '2π 弧度']],note:'曲线横坐标是弧度数，而不是圆上点的横坐标。五个关键点依次为 (0,0)、(π/2,1)、(π,0)、(3π/2,-1)、(2π,0)；连续取角得到光滑曲线，再平移整周期扩展。控制器角度用度显示，模型先转换为弧度。'};}
  };
  E['sine-transform'] = {
    model(s) {const A=Number(s.amplitude),omega=Number(s.omega),phi=rad(s.phase),x=Number(s.x);return {A,omega,phi,x,y:A*Math.sin(omega*x+phi),period:tau/omega,shift:-phi/omega,frequency:omega/tau};},
    render(s,L) {const m=this.model(s),w=L.world(-6.6,6.6,-4,4);return {svg:w.axes+graph(L,w,Math.sin,-6.3,6.3,'aux')+graph(L,w,x=>m.A*Math.sin(m.omega*x+m.phi),-6.3,6.3)+L.line(w.p(-6.3,m.A),w.p(6.3,m.A),'dashed')+L.line(w.p(-6.3,-m.A),w.p(6.3,-m.A),'dashed')+L.dot(w.p(m.x,m.y),'P'),metrics:[['振幅 A',L.fmt(m.A)],['周期 T（近似）',L.fmt(m.period)],['频率 f（近似）',L.fmt(m.frequency)],['水平位移 -φ/ω（近似）',L.fmt(m.shift)],['当前函数值（近似）',L.fmt(m.y)]],note:'灰线为 y=sin x，实线为改变后的函数，虚线为上下振幅界。A>0、ω>0；相位为 ωx+φ，初相为 φ。改变 ω 时周期与水平位移都会变化，不可把 φ 直接当作横移量。负 A 或负 ω 可用诱导公式化归；时钟顺时针转动的原情境详见保留原文。'};}
  };
  E['tangent-branches'] = {
    model(s) {const theta=rad(s.angle),cos=Math.cos(theta);return {theta,defined:Math.abs(cos)>1e-12,value:Math.abs(cos)>1e-12?Math.sin(theta)/cos:null};},
    render(s,L) {const m=this.model(s),w=L.world(-5.2,5.2,-3.2,3.2);let svg=w.axes;
      for(let k=-1;k<=1;k++){const c=k*Math.PI;svg+=graph(L,w,Math.tan,c-Math.atan(3),c+Math.atan(3));}
      for(const x of [-1.5*Math.PI,-.5*Math.PI,.5*Math.PI,1.5*Math.PI])svg+=L.line(w.p(x,-3),w.p(x,3),'dashed');
      if(m.defined&&Math.abs(m.value)<=3)svg+=L.dot(w.p(m.theta,m.value),'P');
      return {svg,metrics:[['x / 弧度（近似）',L.fmt(m.theta)],['tan x（近似）',m.defined?L.fmt(m.value):'未定义'],['显示状态',!m.defined?'渐近线处无点':Math.abs(m.value)>3?'点超出纵向视窗':'点在视窗内']],note:'虚线为 x=π/2+kπ，不是函数图像。每一支仅在自己的区间内严格增，相邻支相隔 π；不同分支不能连线。读数可趋向很大，但渐近线处没有无穷大的函数值。图中曲线只绘出纵坐标在 [-3,3] 内的部分。'};}
  };
  E['dot-projection'] = {
    model(s) {const a=Number(s.a),b=Number(s.b),theta=rad(s.angle),bx=b*Math.cos(theta),by=b*Math.sin(theta);return {a,b,theta,bx,by,dot:a*bx,projection:[bx,0],length:Math.abs(bx)};},
    render(s,L) {const m=this.model(s),w=L.world(-5.2,5.2,-1,5.3),o=w.p(0,0),B=w.p(m.bx,m.by);return {svg:w.axes+L.line(o,w.p(m.a,0),'curve')+L.line(o,B,'secondary')+L.line(B,w.p(m.bx,0),'dashed')+L.line(o,w.p(m.bx,0),'highlight')+L.dot(w.p(m.a,0),'A')+L.dot(B,'B')+L.dot(w.p(m.bx,0),'B′')+L.text(35,35,'a 沿 x 正方向；高亮线是 b 的投影向量'),metrics:[['数量投影（近似，可为负）',L.fmt(m.bx)],['投影向量长度（近似）',L.fmt(m.length)],['a·b（近似）',L.fmt(m.dot)],['夹角',m.b===0?'零向量：未定义':String(s.angle)+'°']],note:'方向向量 a 非零。锐角时投影同向、钝角时反向、直角时为零；数量投影是带符号的数，其绝对值才是投影向量的模。b=0 时投影和数量积均为零，不给零向量定义夹角。'};}
  };
  E['complex-transform'] = {
    model(s) {const r=Number(s.r),scale=Number(s.scale),alpha=rad(s.alpha),beta=rad(s.beta),divide=s.operation==='divide',factor=divide?1/scale:scale,angle=divide?alpha-beta:alpha+beta;return {r,scale,alpha,beta,divide,factor,angle,z:[r*Math.cos(alpha),r*Math.sin(alpha)],w:[scale*Math.cos(beta),scale*Math.sin(beta)],result:[r*factor*Math.cos(angle),r*factor*Math.sin(angle)],modulus:r*factor};},
    render(s,L) {const m=this.model(s),w=L.world(-5.2,5.2,-5.2,5.2),o=w.p(0,0);return {svg:w.axes+circle(L,w,0,0,m.r,'aux')+circle(L,w,0,0,m.modulus,'dashed')+L.line(o,w.p(...m.z),'secondary')+L.line(o,w.p(...m.w),'aux')+L.line(o,w.p(...m.result),'curve')+L.dot(w.p(...m.z),'z')+L.dot(w.p(...m.w),'w')+L.dot(w.p(...m.result),m.divide?'z/w':'zw'),metrics:[['模的变化（近似）',L.fmt(m.r)+' → '+L.fmt(m.modulus)],['旋转角',String(m.divide?-Number(s.beta):Number(s.beta))+'°'],['结果坐标（近似）',m.result.map(v=>L.fmt(v)).join(', ')]],note:'乘以非零 w：模乘 |w|、辐角加 arg(w)；除以 w：模除 |w|、辐角减 arg(w)。辐角只在模 2π 的意义下确定，零复数不定义辐角。模型允许 z=0，此时原点不动；除数模始终严格正。公式由两角和公式展开得到，不以图形采样代替证明。'};}
  };
  window.TEXTBOOK_EXPERIMENTS=Object.assign(window.TEXTBOOK_EXPERIMENTS||{},E);
}());
