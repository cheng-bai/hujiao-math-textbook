/* Independent geometry models; yaw affects projection only, never the mathematics. */
(() => {
  'use strict';
  const rad = x => x * Math.PI / 180;
  const clamp = x => Math.max(-1, Math.min(1, x));
  const open = (L,p) => `<circle cx="${L.fmt(p[0],2)}" cy="${L.fmt(p[1],2)}" r="5" fill="#fffef8" stroke="#ae6036" stroke-width="2"/>`;
  const title = (L,t,svg) => `<title>${L.escape(t)}</title>${svg}`;
  const experiments = {
    'chord-midpoint-domain': {
      model(s) {
        const u=Number(s.u), t=Math.sqrt(5)*u, center=[-4*t/5,t/5], abs=Math.abs(u);
        const kind=abs<1-1e-12?'secant':abs<=1+1e-12?'tangent':'outside';
        const d=kind==='secant'?2/5*Math.sqrt(5-t*t):0;
        const endpoints=kind==='secant'?[[-4*t/5-d,t/5-d],[-4*t/5+d,t/5+d]]:[];
        return {u,t,center,kind,endpoints,valid:kind==='secant',limits:[[-4/Math.sqrt(5),1/Math.sqrt(5)],[4/Math.sqrt(5),-1/Math.sqrt(5)]],halfChord:Math.SQRT2*d};
      },
      render(s,L) {
        const m=this.model(s),W=L.world(-3.2,3.2,-2.2,2.2),p=W.p;
        let svg=W.axes+L.path(L.sample(a=>p(2*Math.cos(a),Math.sin(a)),0,2*Math.PI),'curve');
        if(s.candidate) svg+=L.line(p(-3.2,.8),p(3.2,-.8),'dashed');
        svg+=L.line(p(...m.limits[0]),p(...m.limits[1]),'highlight');
        // Clip the moving infinite line to this mathematical plotting rectangle.
        const low=Math.max(-3.2,-2.2-m.t), high=Math.min(3.2,2.2-m.t);
        if(low<=high) svg+=L.line(p(low,low+m.t),p(high,high+m.t),'secondary');
        for(const point of m.limits) svg+=open(L,p(...point));
        if(m.valid) svg+=L.line(p(...m.endpoints[0]),p(...m.endpoints[1]),'secondary')+L.dot(p(...m.endpoints[0]),'P')+L.dot(p(...m.endpoints[1]),'Q')+L.dot(p(...m.center),'M','highlight');
        else if(m.kind==='tangent') svg+=open(L,p(...m.center))+L.text(350,74,'相切：P、Q合一，不是弦');
        else svg+=L.dot(p(...m.center),'消元候选点','secondary');
        svg+=L.text(22,25,'虚线：消元整线；实线：有效中点轨迹')+L.text(22,342,m.valid?'P、Q不同，M为真实弦中点':m.kind==='tangent'?'空心端点不取：题设要求两个不同交点':'直线与椭圆相离：候选点不是弦中点');
        return {svg:title(L,'弦中点轨迹与范围',svg),metrics:[['参数 t / √5',L.fmt(m.u)],['交点状态',m.kind==='secant'?'两个不同交点':m.kind==='tangent'?'一个相切点':'无交点'],['弦长',m.valid?L.fmt(2*m.halfChord):'不存在非退化弦'],['候选中点坐标',`(${L.fmt(m.center[0])}, ${L.fmt(m.center[1])})`]],note:'问题：消元得到一条直线，就能取整条吗？先拖到u=±1，再比较临界位置两侧。橙色开线段表示真实弦中点，虚线只是消元的候选整线。空心端点对应相切，两交点合一，不能算作非退化弦。下方“为什么成立”分别证明必要性与充分性，并解释端点为何不取。'};
      }
    },
    'line-plane-minimum-angle': {
      model(s) {
        const theta=Number(s.theta),phi=Number(s.phi),c=theta===90?0:Math.cos(rad(theta)),z=theta===0?0:Math.sin(rad(theta));
        const u=[c,0,z],v=[Math.cos(rad(phi)),Math.sin(rad(phi)),0];
        const cosine=c*Math.abs(v[0]),beta=Math.acos(clamp(cosine))*180/Math.PI;
        return {theta,phi,u,v,cosine,beta,projection:[c,0,0],projectionDefined:theta!==90,minimum:theta,allMinimum:theta===90};
      },
      render(s,L) {
        const m=this.model(s),P=q=>L.project(q,Number(s.yaw),25,43,[175,210]);
        let svg=L.polygon([[-2.5,-2.5,0],[2.5,-2.5,0],[2.5,2.5,0],[-2.5,2.5,0]].map(P),'area');
        const mul=(a,t)=>a.map(x=>x*t);
        svg+=L.line(P(mul(m.u,-1.3)),P(mul(m.u,3)),'curve')+L.line(P(mul(m.v,-2.6)),P(mul(m.v,2.6)),'highlight');
        if(m.projectionDefined){svg+=L.line(P([0,0,0]),P(mul(m.projection,3)),'secondary')+L.line(P(mul(m.projection,3)),P(mul(m.u,3)),'dashed');svg+=L.text(...P(mul(m.projection,3.25)),'射影');}
        svg+=L.dot(P([0,0,0]),'O')+L.dot(P(mul(m.u,3)),'P')+L.text(...P(mul(m.v,2.9)),'l');
        const graph=(phi,beta)=>[395+phi/180*180,268-beta/90*155];
        svg+=L.line(graph(0,0),graph(180,0),'axis')+L.line(graph(0,0),graph(0,90),'axis');
        svg+=L.path(L.sample(a=>graph(a,this.model({...s,phi:a}).beta),0,180),'highlight');
        svg+=L.line(graph(0,m.theta),graph(180,m.theta),'dashed')+L.dot(graph(m.phi,m.beta));
        svg+=L.text(402,87,'真实夹角 β')+L.text(374,113,'90°')+L.text(380,283,'0°')+L.text(528,283,'φ=180°')+L.text(405,313,`最低值：θ=${m.theta}°`);
        svg+=L.text(20,24,'固定空间直线，转动平面内的直线l')+L.text(20,342,m.allMinimum?'垂直边界：射影是点，所有方向都成90°':'三维投影不保角；右图与读数给出真实夹角');
        return {svg:title(L,'线面角为何是最小夹角',svg),metrics:[['线面角 θ',`${m.theta}°`],['平面方向 φ',`${m.phi}°`],['两直线真实夹角 β',`${L.fmt(m.beta)}°`],['最小值',`${m.minimum}°`]],note:'问题：为何用射影来衡量倾斜程度？固定空间直线，只转动平面内的l，比较右侧真实夹角曲线的最低值。再把线面角调到直角，观察射影退化后为什么所有方向都成为最小值。视角只改变屏幕投影，不改变数学读数。下方“为什么成立”用单位方向向量的数量积解释最小性与等号条件。'};
      }
    },
    'ssa-circle-ray': {
      model(s) {
        const A=Number(s.A),b=3,h=b*Math.sin(rad(A)),d=A===90?0:b*Math.cos(rad(A));
        const radii={height:h,equal:b,below:.95*h,above:1.05*h,long:1.2*b};
        const a=s.mode==='explore'?h*Number(s.ratio):radii[s.mode];
        const disc=a*a-h*h,roots=[];
        if(disc>=-1e-10){const r=Math.sqrt(Math.max(0,disc)); roots.push(d-r);if(r>1e-10)roots.push(d+r);}
        const candidates=roots.map(c=>({c,valid:c>1e-10,point:[c,0]}));
        const triangles=candidates.filter(q=>q.valid).map(q=>({c:q.c,point:q.point,area:q.c*h/2,B:Math.acos(clamp((q.c-d)/a))*180/Math.PI,C:180-A-Math.acos(clamp((q.c-d)/a))*180/Math.PI}));
        return {A,b,a,h,d,center:[d,h],disc,candidates,triangles,count:triangles.length,tangent:Math.abs(disc)<1e-10,mode:s.mode};
      },
      render(s,L) {
        const m=this.model(s),margin=.5,xmin=Math.min(-.5,m.d-m.a)-margin,xmax=Math.max(3,m.d+m.a)+margin,ymin=Math.min(-.5,m.h-m.a)-margin,ymax=m.h+m.a+margin;
        const W=L.world(xmin,xmax,ymin,ymax),p=W.p;
        let svg=L.line(p(0,0),p(xmax,0),'curve')+L.line(p(xmin,0),p(0,0),'dashed');
        svg+=L.path(L.sample(t=>p(m.d+m.a*Math.cos(t),m.h+m.a*Math.sin(t)),0,2*Math.PI),'secondary');
        svg+=L.line(p(0,0),p(...m.center),'curve')+L.line(p(...m.center),p(m.d,0),'dashed');
        svg+=L.dot(p(0,0),'A')+L.dot(p(...m.center),'C');
        for(const [i,q] of m.triangles.entries()) svg+=L.polygon([p(0,0),p(...m.center),p(...q.point)],i===0?'area':'highlight')+L.dot(p(...q.point),`B${i+1}`);
        for(const q of m.candidates.filter(q=>!q.valid)) svg+=open(L,p(...q.point));
        svg+=L.text(20,24,'固定AC=b=3；B必须位于正向射线上')+L.text(20,342,`有效三角形：${m.count}个；负向交点与B=A均剔除`);
        return {svg:title(L,'SSA的圆与射线：零个、一个或两个三角形',svg),metrics:[['角 A',`${m.A}°`],['半径 a=BC',L.fmt(m.a)],['到直线的高 h',L.fmt(m.h)],['有效解数',`${m.count}个`]],note:'教师拓展：不要求全体学生背完整分类。问题：同样的两边和一个对角，为何可能有两解？先看圆与整条直线的交点，再剔除反向交点和顶点重合的候选。切换精确相切预设，比较锐角、直角与钝角；切换已知两边相等预设，观察退化交点。临界预设优先于比例滑块，返回“自由探索”后滑块生效。下方“为什么成立”给出正根判定及充分性解释。'};
      }
    }
  };
  window.TEXTBOOK_EXPERIMENTS=Object.assign(window.TEXTBOOK_EXPERIMENTS||{},experiments);
})();
