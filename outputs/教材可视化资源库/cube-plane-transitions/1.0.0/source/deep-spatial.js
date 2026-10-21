/* Plane/edge intersections are computed in space; the camera only projects them. */
(() => {
  'use strict';
  const dot = (a,b) => a.reduce((v,x,i)=>v+x*b[i],0);
  const sub = (a,b) => a.map((x,i)=>x-b[i]);
  const mul = (a,t) => a.map(x=>x*t);
  const cross = (a,b) => [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const unit = a => mul(a,1/Math.hypot(...a));
  const vertices = Array.from({length:8},(_,i)=>[i&1?1:-1,i&2?1:-1,i&4?1:-1]);
  const edges = vertices.flatMap((p,i)=>[1,2,4].filter(k=>!(i&k)).map(k=>[p,vertices[i|k]]));
  const normals = {general:[2,3,4],diagonal:[1,1,1],edge:[1,1,0],face:[0,0,1]};
  function model(s) {
    const n=normals[s.direction],d=Number(s.offset),eps=1e-9,points=[];
    function add(p){if(!points.some(q=>Math.hypot(...sub(p,q))<eps))points.push(p);}
    for(const [p,q] of edges){
      const a=dot(n,p)-d,b=dot(n,q)-d;
      if(Math.abs(a)<eps)add([...p]);
      if(Math.abs(b)<eps)add([...q]);
      if(a*b<0){const t=a/(a-b);add(p.map((x,i)=>x+t*(q[i]-x)));}
    }
    const center=points.length?points.reduce((a,p)=>a.map((x,i)=>x+p[i]/points.length),[0,0,0]):mul(n,d/dot(n,n));
    const u=unit(cross(n,Math.abs(n[2])<.9*Math.hypot(...n)?[0,0,1]:[0,1,0])),v=unit(cross(n,u));
    const local=p=>[dot(sub(p,center),u),dot(sub(p,center),v)];
    points.sort((a,b)=>Math.atan2(...local(a).reverse())-Math.atan2(...local(b).reverse()));
    const flat=points.map(local);
    const area=Math.abs(flat.reduce((a,p,i)=>{const q=flat[(i+1)%flat.length];return a+p[0]*q[1]-p[1]*q[0];},0))/2;
    const lengths=points.length>=3?points.map((p,i)=>Math.hypot(...sub(p,points[(i+1)%points.length]))):[];
    const angles=points.length>=3?points.map((p,i)=>{
      const a=sub(points[(i+points.length-1)%points.length],p),b=sub(points[(i+1)%points.length],p);
      return Math.acos(Math.max(-1,Math.min(1,dot(a,b)/Math.hypot(...a)/Math.hypot(...b))));
    }):[];
    const regular=lengths.length>=3&&Math.max(...lengths)-Math.min(...lengths)<eps&&Math.max(...angles)-Math.min(...angles)<eps;
    const type=points.length<3?['空集','一个顶点','一条棱或线段'][points.length]:`${points.length}边形`;
    return {normal:n,offset:d,points,flat,area,lengths,angles,regular,type,center};
  }
  function render(s,L){
    const m=model(s),P=p=>L.project(p,Number(s.yaw),25,71,[168,180]);
    const Q=p=>[445+59*p[0],180-59*p[1]];
    let svg=L.text(27,29,'空间求交：只连接同一面上的截线')+L.text(358,29,'截面正视图（等比例）');
    svg+=edges.map(([p,q])=>L.line(P(p),P(q),'aux')).join('');
    if(m.points.length>=3)svg+=L.polygon(m.points.map(P),'area')+L.path(m.points.map(P),'highlight',true)+L.polygon(m.flat.map(Q),'area')+L.path(m.flat.map(Q),'highlight',true);
    if(m.points.length===2)svg+=L.line(...m.points.map(P),'highlight')+L.line(...m.flat.map(Q),'highlight');
    m.points.forEach((p,i)=>{svg+=L.dot(P(p),String(i+1))+L.dot(Q(m.flat[i]),String(i+1));});
    if(!m.points.length)svg+=L.text(385,180,'切平面未接触立方体');
    svg+=L.text(27,321,'左图仅为投影，屏幕角度不是空间角度')+L.text(27,343,'临界位置：平面经过顶点 / 包含棱 / 与面重合');
    const counts=m.normal.join(' : ');
    return {svg,metrics:[['截面类型',m.type],['真实截面积',L.fmt(m.area,4)],['法向量分量',counts],['是否正多边形',m.points.length>=3?(m.regular?'是':'否'):'不适用']],
      note:'先选“一般斜切”，将偏移量依次设为6、4、2、0，观察三、四、五、六边形。沿每个面连接交点，才能得到真实截线。切平面不与任何面重合时，每个面至多贡献一条截面边，故至多六边；与某面重合时直接得到正方形。过顶点时可能换边，不一定改变边数。体对角方向、偏移0得到正六边形；一般斜切、偏移0虽也是六边形，却不是正六边形。切到一个顶点或一条棱时不再是多边形截面。旋转视角不改变求交与面积。'};
  }
  window.TEXTBOOK_EXPERIMENTS=Object.assign(window.TEXTBOOK_EXPERIMENTS||{}, {'cube-plane-transitions':{model,render}});
})();
