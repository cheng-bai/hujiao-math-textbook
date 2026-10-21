import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const dir=path.dirname(fileURLToPath(import.meta.url));
const context=vm.createContext({window:{},Math,Number,Object,Array,String});
for(const file of ['lab-core.js','foundations.js']) vm.runInContext(fs.readFileSync(path.join(dir,file),'utf8'),context,{filename:file});
const {TEXTBOOK_EXPERIMENTS:E,LabTools:L}=context.window;
const data=JSON.parse(fs.readFileSync(path.join(dir,'foundations.json'),'utf8'));
const root=path.resolve(dir,'../..');
let states=0,checks=0;
function near(a,b,tol=1e-9){checks++;assert.ok(Math.abs(a-b)<=tol,`${a} differs from ${b}`);}
function checkAsset(a,s){
 const m=E[a.id].model(s), r=E[a.id].render(s,L);
 assert.equal(typeof r.svg,'string');assert.ok(r.svg.length>100);assert.ok(r.metrics.length>0);assert.ok(r.note.length>20);
 assert.ok(!/NaN|Infinity|undefined/.test(r.svg),a.id+' invalid SVG');
 const d=Number(s.angle)*Math.PI/180;
 switch(a.id){
 case 'absolute-distance': assert.equal(m.holds,s.mode==='inside' ? -s.a<s.x&&s.x<s.a : s.x< -s.a||s.x>s.a);break;
 case 'amgm-square': near(m.area+m.defect,16);near(m.gm**2,m.area);assert.ok(m.am>=m.gm-1e-10);assert.equal(m.defect===0,m.a===m.b);break;
 case 'exponential-base': near(m.y,Math.exp(Number(s.x)*Math.log(Number(s.base))));near(m.y*m.reciprocal,1);break;
 case 'logarithm-reflection': near(m.inverse,Number(s.t));near(Number(s.base)**m.t,m.u);break;
 case 'monotonic-two-points':
   assert.ok(m.x1<m.x2);if(s.kind==='square')near(m.delta,(m.x2-m.x1)*(m.x2+m.x1));
   if(s.kind==='cube')near(m.delta,(m.x2-m.x1)*(m.x2*m.x2+m.x1*m.x2+m.x1*m.x1)/3);
   if(s.kind==='constant')near(m.delta,0);if(s.kind==='decreasing')near(m.delta,-Number(s.gap));break;
 case 'inverse-domain':near(m.inverse,m.x);near(m.y,m.x*m.x);assert.ok(s.branch==='negative'?m.x<=0:m.x>=0);break;
 case 'unit-circle-projection':near(m.sin*m.sin+m.cos*m.cos,1);if(m.tan!==null)near(m.tan*m.cos,m.sin);if(m.cot!==null)near(m.cot*m.sin,m.cos);break;
 case 'sine-unroll':near(m.x*m.x+m.y*m.y,1);near(m.y,Math.sin(d));near(Math.sin(m.theta+2*Math.PI),m.y);break;
 case 'sine-transform':near(m.y,Number(s.amplitude)*Math.sin(Number(s.omega)*Number(s.x)+Number(s.phase)*Math.PI/180));near(Math.sin(m.omega*(m.x+m.period)+m.phi)*m.A,m.y);near(m.omega*m.shift+m.phi,0);near(m.frequency*m.period,1);break;
 case 'tangent-branches':if(m.defined){near(m.value*Math.cos(d),Math.sin(d));near(Math.tan(d+Math.PI),m.value,1e-8);}else near(Math.cos(d),0);break;
 case 'dot-projection':near(m.bx*m.bx+m.by*m.by,m.b*m.b);near(m.dot,m.a*m.projection[0]);near(m.length,Math.hypot(...m.projection));near(m.by*Math.cos(d)-m.bx*Math.sin(d),0);if(Number(s.b)===0)near(m.dot,0);break;
 case 'complex-transform':{
   const [x,y]=m.z,[u,v]=m.w,den=u*u+v*v;
   const expected=s.operation==='divide'?[(x*u+y*v)/den,(y*u-x*v)/den]:[x*u-y*v,x*v+y*u];
   near(m.result[0],expected[0]);near(m.result[1],expected[1]);near(Math.hypot(...m.result),m.modulus);break;}
 }
 states++;
}
assert.equal(data.selection.length,38);assert.equal(data.assets.length,11);
assert.equal(new Set(data.selection.map(s=>s.sectionId)).size,38);
for(const a of data.assets){
 assert.ok(E[a.id]);assert.ok(a.formula.startsWith('<math '));assert.ok(!a.formula.includes('\\'));
 for(const p of a.placements){const section=JSON.parse(fs.readFileSync(path.join(root,'batch/sections',p.sectionId.slice(0,3),p.sectionId+'.json'),'utf8'));const i=Number(p.afterBlockId.match(/-b(\d+)$/)[1]);assert.equal(section.blocks[i].type,'prose');assert.ok(section.blocks[i].markdown.length>400);}
 let combos=[{...a.initial}];
 for(const c of a.controls){const choices=c.type==='select'?c.options.map(x=>x.value):c.type==='checkbox'?[false,true]:[c.min,(c.min+c.max)/2,c.max];combos=combos.flatMap(s=>choices.map(v=>({...s,[c.key]:v})));}
 checkAsset(a,a.initial);for(const s of combos)checkAsset(a,s);
}
// Include exact transition values not guaranteed to coincide with slider endpoints.
for(const angle of [-270,-180,-90,0,90,180,270]){
 const a=data.assets.find(x=>x.id==='tangent-branches');checkAsset(a,{angle});
 assert.equal(E[a.id].model({angle}).defined,angle%180===0);
}
near(E['amgm-square'].model({a:4}).defect,0);
near(E['dot-projection'].model({a:3,b:4,angle:90}).dot,0);
const w=L.world(-4,4,-3,3);near(Math.abs(w.p(1,0)[0]-w.p(0,0)[0]),Math.abs(w.p(0,1)[1]-w.p(0,0)[1]));
console.log(JSON.stringify({family:'foundations',sections:data.selection.length,assets:data.assets.length,states,independentRelations:checks,status:'passed'}));
