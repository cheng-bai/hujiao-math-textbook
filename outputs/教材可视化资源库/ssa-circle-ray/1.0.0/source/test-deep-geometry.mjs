import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import vm from 'node:vm';
const here=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(here,'../..');
const spec=JSON.parse(readFileSync(path.join(here,'deep-geometry.json'),'utf8'));
const context=vm.createContext({window:{}});
for(const name of ['lab-core.js','deep-geometry.js'])vm.runInContext(readFileSync(path.join(here,name),'utf8'),context);
const E=context.window.TEXTBOOK_EXPERIMENTS,L=context.window.LabTools;
let checks=0,states=0;
const ok=(v,msg)=>{assert.ok(v,msg);checks++;};
const near=(a,b,msg,eps=1e-9)=>ok(Math.abs(a-b)<=eps*(1+Math.abs(b)),`${msg}: ${a} vs ${b}`);
const render=(id,s)=>{const r=E[id].render(s,L);ok(!/NaN|Infinity|undefined/.test(r.svg),'finite SVG');ok(r.note.length>100,'explanation substantial');states++;return r;};
const finite=x=>{if(typeof x==='number')ok(Number.isFinite(x),'finite model');else if(x&&typeof x==='object')Object.values(x).forEach(finite);};
for(const asset of spec.assets){
 ok(new Set(asset.controls.map(c=>c.key)).size===asset.controls.length,'unique controls');
 assert.deepEqual(Object.keys(asset.initial).sort(),asset.controls.map(c=>c.key).sort());
 ok(asset.formula.includes('<math '),'real MathML formula');
 for(const p of asset.placements){
  const sec=JSON.parse(readFileSync(path.join(root,`batch/sections/${p.sectionId.split('-')[0]}/${p.sectionId}.json`),'utf8'));
  const b=sec.blocks.find((b,i)=>(b.id||`${p.sectionId}-b${i}`)===p.afterBlockId);
  ok(b?.type==='prose'&&b.markdown.length>200,'real substantive prose placement');ok(p.retainProse===true,'original prose retained');
 }
 render(asset.id,asset.initial);
}
const chord=E['chord-midpoint-domain'];
for(let i=-140;i<=140;i++){
 const s={u:i/100,candidate:i%2===0},m=chord.model(s);finite(m);render('chord-midpoint-domain',s);
 near(m.center[1],-m.center[0]/4,'midpoint candidate line');
 ok(m.valid===(Math.abs(i)<100),'strict domain excludes tangent endpoints');
 if(m.valid){
  for(const [x,y] of m.endpoints){near(x*x/4+y*y,1,'ellipse intersection');near(y,x+m.t,'moving chord');}
  for(let k=0;k<2;k++)near((m.endpoints[0][k]+m.endpoints[1][k])/2,m.center[k],'midpoint');
  near(Math.hypot(m.endpoints[0][0]-m.endpoints[1][0],m.endpoints[0][1]-m.endpoints[1][1]),2*m.halfChord,'chord length');
 }else if(Math.abs(i)===100){ok(m.kind==='tangent','precise tangent');near(m.center[0]**2/4+m.center[1]**2,1,'excluded endpoint on ellipse');}
}
// Sufficiency independently reconstructs a chord from every tested open-segment point.
for(let i=-99;i<=99;i++){
 const x=(4/Math.sqrt(5))*i/100,t=-5*x/4,D=64*t*t-20*(4*t*t-4);
 ok(D>0,'every interior trajectory point constructs distinct real roots');
 near((-8*t/5)/2,x,'reconstructed midpoint');
}
const angle=E['line-plane-minimum-angle'];
for(let theta=0;theta<=90;theta+=5)for(let phi=0;phi<=180;phi+=5){
 const s={theta,phi,yaw:35},m=angle.model(s);finite(m);render('line-plane-minimum-angle',s);
 near(Math.hypot(...m.u),1,'space unit vector');near(Math.hypot(...m.v),1,'plane unit vector');
 const product=m.u.reduce((n,v,i)=>n+v*m.v[i],0);near(Math.cos(m.beta*Math.PI/180),Math.abs(product),'true line angle dot product');
 ok(m.beta+1e-8>=theta&&m.beta<=90+1e-8,'minimum angle inequality');
 if(phi===0||phi===180)near(m.beta,theta,'projection direction minimum');
 if(theta===90)near(m.beta,90,'normal line every direction perpendicular');
 if(phi===90)near(m.beta,90,'three-perpendicular direction');
 assert.deepEqual(angle.model({...s,yaw:165}),m);checks++;
}
const ssa=E['ssa-circle-ray'];
for(let A=20;A<=160;A+=5)for(const mode of ['explore','below','height','above','equal','long'])for(const ratio of mode==='explore'?[.5,.95,1,1.05,1.5,2,3]:[1.5]){
 const s={A,mode,ratio},m=ssa.model(s);finite(m);render('ssa-circle-ray',s);
 // Independent textbook classification, not the quadratic-root implementation.
 let n;
 if(A<90){n=m.a<m.h-1e-9?0:Math.abs(m.a-m.h)<1e-9?1:m.a<m.b-1e-9?2:1;}
 else n=m.a>m.b+1e-9?1:0;
 ok(m.count===n,`SSA classification at A=${A}, mode=${mode}, a/h=${ratio}`);
 for(const q of m.triangles){
  ok(q.c>0&&q.area>0,'positive side and nonzero area');near(Math.hypot(q.c-m.d,m.h),m.a,'candidate radius');
  near(m.A+q.B+q.C,180,'triangle angle sum');ok(q.B>0&&q.C>0,'all angles positive');
  near(m.a/Math.sin(m.A*Math.PI/180),m.b/Math.sin(q.B*Math.PI/180),'sine law independent check');
 }
 if(mode==='equal')ok(m.candidates.some(q=>Math.abs(q.c)<1e-9&&!q.valid),'a=b zero root excluded');
 if(mode==='height')ok(m.tangent&&m.count===(A<90?1:0),'tangent point must lie on positive ray');
}
console.log(JSON.stringify({status:'passed',assets:spec.assets.length,placements:spec.assets.reduce((n,a)=>n+a.placements.length,0),renderStates:states,checks}));
