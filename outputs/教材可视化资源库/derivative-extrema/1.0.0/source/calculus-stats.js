(() => {
  'use strict';
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const choose = (n, k) => { if (k < 0 || k > n) return 0; let r = 1; for (let i = 1; i <= k; i++) r = r * (n - i + 1) / i; return r; };
  // Statistical axes have different units; do not flatten a 500-trial path to one pixel.
  const chart = (L,xmin,xmax,ymin,ymax) => {
    const p=(x,y)=>[42+516*(x-xmin)/(xmax-xmin),319-278*(y-ymin)/(ymax-ymin)];
    const axes=L.line(p(xmin,ymin),p(xmax,ymin),'axis')+L.line(p(xmin,ymin),p(xmin,ymax),'axis')
      +L.text(42,340,L.fmt(xmin))+L.text(530,340,L.fmt(xmax))+L.text(8,319,L.fmt(ymin))+L.text(8,43,L.fmt(ymax));
    return {p,axes};
  };
  const defs = {
    'secant-tangent': {
      model(s) {const a=.5,h=Number(s.h);return {a,h,slope:h===0?null:1+h,tangent:1};},
      render(s,L) {const m=this.model(s),{p,axes}=L.world(-2,3,-1,8),f=x=>x*x,A=p(m.a,f(m.a)),B=p(m.a+m.h,f(m.a+m.h));
        let svg=axes+L.path(L.sample(x=>p(x,f(x)),-2,2.7),'curve')+L.path(L.sample(x=>p(x,x-.25),-2,3),'highlight')+L.dot(A,'P');
        if(m.slope!==null)svg+=L.path(L.sample(x=>p(x,.25+m.slope*(x-.5)),-2,3),'secondary')+L.dot(B,'Q');
        return {svg,metrics:[['割线斜率（近似）',m.slope===null?'h=0 时未定义':L.fmt(m.slope)],['切线斜率','1'],['固定点横坐标 a','0.5']],note:'绿线是函数，蓝线是割线，橙线是切线。h≠0 时斜率为 1+h；从正负两侧趋零时均趋于 1，h=0 时只保留切线而不伪造割线。'};}
    },
    'derivative-extrema': {
      model(s) {const name=s.case,points=name==='sin'?[-Math.PI/2,Math.PI/2]:[0];return {type:name,points,stationary:name==='x3'?'非极值驻点':name==='x4'?'极小值':'极小与极大交替'};},
      render(s,L) {const m=this.model(s),f=s.case==='x3'?x=>x*x*x:s.case==='x4'?x=>x**4:Math.sin,d=s.case==='x3'?x=>3*x*x:s.case==='x4'?x=>4*x**3:Math.cos,{p,axes}=L.world(-2.2,2.2,-2.2,3.2);
        const curve=fn=>L.sample(x=>[x,fn(x)],-2,2,180).filter(([,y])=>y>=-2.1&&y<=3.1).map(([x,y])=>p(x,y));
        return {svg:axes+L.path(curve(f),'curve')+L.path(curve(d),'secondary')+m.points.map(x=>L.dot(p(x,f(x)),'驻点')).join('')+L.text(45,28,'绿：f；蓝：f′；圆点：驻点'),metrics:[['两侧导数符号',s.case==='x3'?'+ → +（0处为零）':s.case==='x4'?'− → +':'− → + → −'],['驻点判别',m.stationary]],note:'在函数连续且两侧可导的邻域，导数由正到负得到极大，由负到正得到极小。x³ 的导数在0两侧均正，故驻点不是极值点。极值是局部概念，与整个定义域的最值不同；视窗外曲线不绘制。'};}
    },
    'binomial-paths': {
      model(s) {const n=Math.round(s.n),k=Math.round(s.k);return {n,k,valid:k>=0&&k<=n,coefficient:choose(n,k)};},
      render(s,L) {const m=this.model(s),rows=[];for(let r=0;r<=m.n;r++)rows.push(Array.from({length:r+1},(_,j)=>choose(r,j)));
        let svg='';for(let r=0;r<m.n;r++)for(let j=0;j<=r;j++){const a=[300+(j-r/2)*Math.min(52,300/m.n),28+r*300/m.n];for(const offset of [0,1])svg+=L.line(a,[300+(j+offset-(r+1)/2)*Math.min(52,300/m.n),28+(r+1)*300/m.n],'aux');}
        svg+=rows.map((row,r)=>row.map((v,j)=>L.dot([300+(j-r/2)*Math.min(52,300/m.n),28+r*300/m.n],String(v),r===m.n&&j===m.k?'highlight':'point')).join('')).join('');
        return {svg,metrics:[['目标系数',String(m.coefficient)],['目标位置',`n=${m.n}, k=${m.k}`],['可选性',m.valid?'合法：0≤k≤n':'k>n，无法从n个因子中选出k个b']],note:'边线表示每一步选 a 或 b。每个内部节点的数等于两上邻数之和；第 n 行第 k 位统计恰选 k 个 b 的路径。k>n 时系数为0，不把滑块值偷偷截成另一个k。'};}
    },
    'conditional-space': {
      model(s) {const a=Number(s.a),conditional=Number(s.overlap),outside=Number(s.outside??.2);return {a,conditional,outside,joint:a*conditional,b:a*conditional+(1-a)*outside};},
      render(s,L) {const m=this.model(s),{p,axes}=L.world(0,1,0,1);let cells='';for(let i=0;i<10;i++)for(let j=0;j<10;j++){const x=(i+.5)/10,y=(j+.5)/10,insideA=x<m.a,insideB=y<(insideA?m.conditional:m.outside),corner=p(i/10,(j+1)/10);cells+=`<rect x="${corner[0]}" y="${corner[1]}" width="${L.fmt(p((i+1)/10,0)[0]-p(i/10,0)[0],2)}" height="${L.fmt(p(0,j/10)[1]-p(0,(j+1)/10)[1],2)}" fill="${insideA&&insideB?'#c4743c':insideA?'#d4e8dc':insideB?'#a9c5df':'#fffef8'}" stroke="#bdcbbf" stroke-width="0.5"/>`;}
        return {svg:axes+cells+L.line(p(m.a,0),p(m.a,1),'curve')+L.text(35,28,'绿：A；橙：A∩B；蓝：B在A之外的部分'),metrics:[['P(A)',L.fmt(m.a)],['P(A∩B)',L.fmt(m.joint)],['P(B)',L.fmt(m.b)],['P(B|A)=交集÷A',L.fmt(m.conditional)]],note:'100个等可能格子，滑块按0.1调整，填色与格子数严格一致。给定A后只在绿/橙区域内重新计算比例；蓝区不计入条件分母。P(B|A)一般不等于P(B)；本图要求P(A)>0。'};}
    },
    'distribution-moments':{model:s=>{let t=Number(s.spread),x=[-1,0,1],p=[t/2,1-t,t/2],mean=x.reduce((a,v,i)=>a+v*p[i],0),variance=x.reduce((a,v,i)=>a+(v-mean)**2*p[i],0);return{x,p,mean,variance};},render(s,L){let m=this.model(s),{p,axes}=chart(L,-1.5,1.5,0,1);let bars=m.x.map((x,i)=>{let a=p(x-.18,0),b=p(x+.18,m.p[i]);return `<rect class="${i===1?'highlight':'secondary'}" fill="#a9c5df" x="${a[0]}" y="${b[1]}" width="${b[0]-a[0]}" height="${p(0,0)[1]-b[1]}"/>`}).join('');return{svg:axes+bars+L.line(p(m.mean,0),p(m.mean,.92),'highlight')+L.text(p(m.mean,0)[0]+4,40,'E(X)'),metrics:[['E(X)',L.fmt(m.mean)],['D(X)',L.fmt(m.variance)]],note:'此对称三点分布的均值为0；spread增大时质量移向两端，方差增大。'};}},
    'binomial-distribution':{model:s=>{let n=Math.round(s.n),p=Number(s.p),q=Array.from({length:n+1},(_,k)=>choose(n,k)*p**k*(1-p)**(n-k));return{n,p,q,sum:q.reduce((a,b)=>a+b,0),mean:n*p,variance:n*p*(1-p)};},render(s,L){let m=this.model(s),{p,axes}=chart(L,-1,m.n+1,0,Math.max(...m.q)*1.2);let svg=axes+m.q.map((v,k)=>L.line(p(k,0),p(k,v),'highlight')+L.dot(p(k,v),'','point')).join('');return{svg,metrics:[['概率和',L.fmt(m.sum)],['均值 np',L.fmt(m.mean)],['方差 np(1−p)',L.fmt(m.variance)]],note:'仅当试验相互独立且成功概率固定为p时适用二项分布。'};}},
    'regression-outlier':{model:s=>{let pts=[[-2,0],[-1,-.2],[0,.1],[1,.3],[2,.6],[2.5,Number(s.outlier)]],n=pts.length,mx=pts.reduce((a,p)=>a+p[0],0)/n,my=pts.reduce((a,p)=>a+p[1],0)/n,c=pts.reduce((a,p)=>a+(p[0]-mx)*(p[1]-my),0),v=pts.reduce((a,p)=>a+(p[0]-mx)**2,0),slope=v?c/v:null;return{pts,mx,my,slope,intercept:slope===null?null:my-slope*mx};},render(s,L){let m=this.model(s),{p,axes}=L.world(-3,3,-3,9),line=m.slope===null?[]:L.sample(x=>p(x,m.slope*x+m.intercept),-3,3);return{svg:axes+L.path(line,'highlight')+m.pts.map(([x,y],i)=>L.dot(p(x,y),i===5?'离群点':'')).join(''),metrics:[['回归斜率',m.slope===null?'不适用':L.fmt(m.slope)]],note:'离群点位置会影响最小二乘拟合；先核查数据，不据相关关系推出因果。'};}},
    'contingency-independent': {
      model(s) {const r=Number(s.row),c=Number(s.col),n=Number(s.total??100),expected=[[r*c,r*(1-c)],[(1-r)*c,(1-r)*(1-c)]];return {r,c,n,expected,counts:expected.map(row=>row.map(v=>v*n))};},
      render(s,L) {const m=this.model(s),xs=[150,150+280*m.c,430],ys=[40,40+280*m.r,320];let svg='';for(let i=0;i<2;i++)for(let j=0;j<2;j++){const x=xs[j],y=ys[i],w=xs[j+1]-x,h=ys[i+1]-y;svg+=`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${(i+j)%2?'#a9c5df':'#d4e8dc'}" stroke="#27685c"/><text class="label" x="${x+w/2}" y="${y+h/2+4}" text-anchor="middle">E${i+1}${j+1}</text>`;}
        return {svg:svg+L.text(35,28,'格面积 = 独立假设下期望比例'),metrics:[['总样本数',String(m.n)],...m.counts.flatMap((row,i)=>row.map((v,j)=>[`E${i+1}${j+1}（近似）`,L.fmt(v)]))],note:'行高与行边际比例对应，列宽与列边际比例对应，每格面积是两边际比例的积。期望频数=面积×总样本数，可不是整数；期望数不是观察数。实际独立性检验还需观察频数、统计量与适用条件。'};}
    },
    'frequency-fluctuation': {
      model(s) {const n=Math.round(s.n),p=Number(s.p),seed=Number(s.seed??3);let x=(seed*2654435761)>>>0;const rand=()=>{x=(1664525*x+1013904223)>>>0;return x/4294967296;};let hits=0,values=[];for(let i=1;i<=n;i++){if(rand()<p)hits++;values.push(hits/i);}return {n,p,seed,values,final:hits/n};},
      render(s,L) {const m=this.model(s),{p,axes}=chart(L,0,m.n,0,1);return {svg:axes+L.path(m.values.map((v,i)=>p(i+1,v)),'curve')+L.line(p(0,m.p),p(m.n,m.p),'dashed')+L.text(35,28,'横轴：累计次数；纵轴：累计频率'),metrics:[['末次频率（近似）',L.fmt(m.final)],['理论概率',L.fmt(m.p)]],note:'相同种子下增加次数沿用同一条轨迹的前缀，不重新抽样。频率波动不保证单调，有限次数下末次频率通常不等于p。种子控制可复现伪随机模拟，不把一条样本路径当成大数定律的证明。'};}
    },
    'independent-area': {
      model(s) {return {a:Number(s.a),b:Number(s.b),joint:Number(s.a)*Number(s.b)};},
      render(s,L) {const m=this.model(s),{p,axes}=L.world(0,1,0,1),box=(x,y,w,h,fill)=>{const q=p(x,y+h);return `<rect x="${q[0]}" y="${q[1]}" width="${w*(p(1,0)[0]-p(0,0)[0])}" height="${h*(p(0,0)[1]-p(0,1)[1])}" fill="${fill}" fill-opacity=".55" stroke="#9cae9e"/>`;};
        return {svg:axes+box(0,0,1,1,'#fffef8')+box(0,0,m.a,1,'#d4e8dc')+box(0,0,1,m.b,'#a9c5df')+box(0,0,m.a,m.b,'#c4743c')+L.text(35,28,'绿条：A；蓝条：B；橙色交集：A∩B'),metrics:[['P(A)',L.fmt(m.a)],['P(B)',L.fmt(m.b)],['P(A∩B)=面积',L.fmt(m.joint)]],note:'单位正方形中横纵坐标独立且均匀，交集面积为 a×b。独立事件的概率满足乘法关系；本面积示意来自具体模型，不能把任意两事件都画成这种矩形后假定独立。'};}
    },
    'stratified-sampling': {
      model(s) {return {population:Number(s.population),sample:Number(s.sample),bias:Number(s.sample)-Number(s.population)};},
      render(s,L) {const m=this.model(s),x0=100,w=420,h=65;const bar=(fraction,y,label)=>`<rect x="${x0}" y="${y}" width="${fraction*w}" height="${h}" fill="#c4743c"/><rect x="${x0+fraction*w}" y="${y}" width="${(1-fraction)*w}" height="${h}" fill="#a9c5df"/>`+L.text(30,y+h/2,label)+L.text(x0+8,y+h/2,'层1')+L.text(x0+fraction*w+8,y+h/2,'层2');return {svg:bar(m.population,65,'总体')+bar(m.sample,205,'样本')+L.text(35,28,'比较两层的相对构成，而不是人数总量'),metrics:[['总体第一层占比',L.fmt(m.population)],['样本第一层占比',L.fmt(m.sample)],['构成差',L.fmt(m.bias)]],note:'按比例分层时两条分界线对齐，各层内部仍要随机抽取，比例匹配不保证任何一个具体样本完全代表总体。不同抽样比例可采用，但总体均值须用总体层权重汇总，不能直接不加权混合。'};}
    },
    'histogram-area': {
      model(s) {return {width:Number(s.width),frequency:Number(s.frequency),height:Number(s.frequency)/Number(s.width),area:Number(s.frequency)};},
      render(s,L) {const m=this.model(s),{p,axes}=L.world(0,5,0,1.4);return {svg:axes+L.polygon([p(.5,0),p(.5+m.width,0),p(.5+m.width,m.height),p(.5,m.height)],'area')+L.text(35,28,'横：数据值；纵：频率密度；面积：频率'),metrics:[['组距',L.fmt(m.width)],['柱高=频率密度（近似）',L.fmt(m.height)],['柱面积=频率',L.fmt(m.area)]],note:'频率密度×组距=频率。固定频率只改组距时，柱高反向变化、面积不变；改变频率会改变面积。不等宽直方图不能只看柱高比较频数；此处只演示一组，不声称单柱构成完整分布。'};}
    },
    'sampling-mean':{model(s){let n=Math.round(s.n),seed=Math.round(s.seed),x=(seed*2654435761)>>>0,rand=()=>{x^=x<<13;x^=x>>>17;x^=x<<5;return(x>>>0)/4294967296;},means=[];for(let j=0;j<80;j++){let sum=0;for(let i=0;i<n;i++)sum+=rand();means.push(sum/n);}let mean=means.reduce((a,b)=>a+b,0)/means.length,sd=Math.sqrt(means.reduce((a,b)=>a+(b-mean)**2,0)/means.length);return{n,means,mean,sd,theory:1/Math.sqrt(12*n)};},render(s,L){let m=this.model(s),{p,axes}=chart(L,0,1,0,1),bins=Array(12).fill(0);m.means.forEach(v=>bins[Math.min(11,Math.floor(v*12))]++);let svg=axes+bins.map((b,i)=>{let x=i/12,y=b/80,a=p(x,0),z=p(x+1/12,y);return `<rect class="secondary" fill="#a9c5df" x="${a[0]}" y="${z[1]}" width="${z[0]-a[0]}" height="${p(0,0)[1]-z[1]}"/>`}).join('');return{svg,metrics:[['模拟均值',L.fmt(m.mean)],['模拟标准差',L.fmt(m.sd)],['理论标准误',L.fmt(m.theory)]],note:'横轴为样本均值，纵轴为80组样本中落入对应区间的比例。总体为U(0,1)，均值1/2、方差1/12。固定种子的伪随机模拟只展示波动，不保证这80组的经验标准差等于理论标准误，也不构成区间估计。'};}}
  };
  window.TEXTBOOK_EXPERIMENTS = Object.assign(window.TEXTBOOK_EXPERIMENTS || {}, defs);
})();
