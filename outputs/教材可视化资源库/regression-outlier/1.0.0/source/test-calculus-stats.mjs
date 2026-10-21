import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const context=vm.createContext({window:{},Math,Number,Array,Object,String});
for(const file of ['lab-core.js','calculus-stats.js'])vm.runInContext(fs.readFileSync(new URL('./'+file,import.meta.url),'utf8'),context,{filename:file});
const defs=context.window.TEXTBOOK_EXPERIMENTS,L=context.window.LabTools;
const specs=JSON.parse(fs.readFileSync(new URL('./calculus-stats.json',import.meta.url),'utf8'));
let states=0,relations=0;
const near=(a,b,tol=1e-9)=>{relations++;assert.ok(Math.abs(a-b)<tol,`${a} != ${b}`);};
const fact=n=>{let v=1n;for(let i=2n;i<=BigInt(n);i++)v*=i;return v;};
const C=(n,k)=>k<0||k>n?0:Number(fact(n)/(fact(k)*fact(n-k)));
assert.equal(specs.family,'calculus-stats');assert.equal(specs.selection.length,30);assert.equal(specs.assets.length,13);
function check(asset,s){
 const e=defs[asset.id],m=e.model(s),r=e.render(s,L);states++;
 assert.ok(typeof r.svg==='string'&&r.svg.length>60);assert.ok(Array.isArray(r.metrics));assert.ok(r.note.length>15);
 assert.ok(!/NaN|Infinity|undefined/.test(r.svg),asset.id+' invalid geometry');
 switch(asset.id){
 case 'secant-tangent':if(s.h===0)assert.equal(m.slope,null);else near(m.slope,((m.a+m.h)**2-m.a*m.a)/m.h);near(m.tangent,2*m.a);break;
 case 'derivative-extrema':assert.equal(m.points.length,s.case==='sin'?2:1);break;
 case 'binomial-paths':assert.equal(m.coefficient,C(m.n,m.k));if(m.k>m.n){assert.equal(m.valid,false);assert.equal(m.coefficient,0);assert.ok(r.metrics.some(x=>String(x[1]).includes('无法')));}break;
 case 'conditional-space':near(m.joint,m.a*m.conditional);near(m.b,m.joint+(1-m.a)*m.outside);assert.ok(m.joint<=m.a&&m.joint<=m.b);near((r.svg.match(/fill="#c4743c"/g)||[]).length/100,m.joint);near((r.svg.match(/fill="#a9c5df"/g)||[]).length/100,(1-m.a)*m.outside);break;
 case 'distribution-moments':near(m.p.reduce((a,b)=>a+b,0),1);near(m.mean,0);near(m.variance,Number(s.spread));near(m.variance,m.x.reduce((sum,x,i)=>sum+x*x*m.p[i],0)-m.mean*m.mean);break;
 case 'binomial-distribution':near(m.q.reduce((a,b)=>a+b,0),1);near(m.q.reduce((sum,q,k)=>sum+k*q,0),m.mean);near(m.q.reduce((sum,q,k)=>sum+(k-m.mean)**2*q,0),m.variance);for(let k=0;k<=m.n;k++)near(m.q[k],C(m.n,k)*Number(s.p)**k*(1-Number(s.p))**(m.n-k));break;
 case 'regression-outlier':near(m.pts.reduce((sum,[x,y])=>sum+y-(m.slope*x+m.intercept),0),0);near(m.pts.reduce((sum,[x,y])=>sum+x*(y-m.slope*x-m.intercept),0),0);break;
 case 'contingency-independent':near(m.expected.flat().reduce((a,b)=>a+b,0),1);near(m.expected[0][0]+m.expected[0][1],m.r);near(m.expected[0][0]+m.expected[1][0],m.c);near(m.counts.flat().reduce((a,b)=>a+b,0),m.n);break;
 case 'frequency-fluctuation':assert.equal(m.values.length,m.n);for(let i=0;i<m.values.length;i++){const count=m.values[i]*(i+1);near(count,Math.round(count));if(i){const prior=m.values[i-1]*i;assert.ok(Math.abs(count-prior)<1e-8||Math.abs(count-prior-1)<1e-8);}}assert.deepEqual(e.model(s).values,m.values);break;
 case 'independent-area':near(m.joint,m.a*m.b);assert.ok(m.joint<=Math.min(m.a,m.b));break;
 case 'stratified-sampling':near(m.bias,m.sample-m.population);break;
 case 'histogram-area':near(m.height*m.width,Number(s.frequency));near(m.area,Number(s.frequency));assert.ok(m.height<=1.4);break;
 case 'sampling-mean':assert.equal(m.means.length,80);assert.ok(m.means.every(x=>x>=0&&x<=1));near(m.mean,m.means.reduce((a,b)=>a+b,0)/80);near(m.sd**2,m.means.reduce((a,b)=>a+(b-m.mean)**2,0)/80);near(m.theory**2,1/(12*m.n));assert.deepEqual(e.model(s).means,m.means);break;
 }
}
for(const a of specs.assets){
 assert.ok(defs[a.id]);assert.ok(a.formula.startsWith('<math '));
 for(const p of a.placements){const d=JSON.parse(fs.readFileSync(new URL(`../../batch/sections/${p.sectionId.split('-')[0]}/${p.sectionId}.json`,import.meta.url),'utf8'));const i=Number(p.afterBlockId.split('-b').at(-1));assert.equal(d.blocks[i].type,'prose');}
 check(a,a.initial);let all=[{...a.initial}];for(const c of a.controls){const choices=c.type==='select'?c.options.map(x=>x.value):[c.min,(c.min+c.max)/2,c.max];all=all.flatMap(s=>choices.map(x=>({...s,[c.key]:x})));}for(const s of all)check(a,s);
}
const asset=id=>specs.assets.find(a=>a.id===id);
for(const h of [-.001,0,.001])check(asset('secant-tangent'),{h});
for(const p of [0,1])check(asset('binomial-distribution'),{n:20,p});
const short=defs['frequency-fluctuation'].model({n:40,p:.5,seed:3}),long=defs['frequency-fluctuation'].model({n:500,p:.5,seed:3});assert.deepEqual(short.values,long.values.slice(0,40));
const curve=defs['frequency-fluctuation'].render({n:500,p:.5,seed:3},L).svg.match(/class="curve" d="([^"]+)"/)[1];
const ys=[...curve.matchAll(/[ML][\d.-]+,([\d.-]+)/g)].map(m=>Number(m[1]));assert.ok(Math.max(...ys)-Math.min(...ys)>20,'probability curve must use readable independent vertical scale');
console.log(JSON.stringify({family:'calculus-stats',assets:specs.assets.length,sections:specs.selection.length,states,independentRelations:relations,realLabTools:true,status:'passed'}));
