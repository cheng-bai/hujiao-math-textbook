import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import vm from 'node:vm';
const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'../..');
const spec=JSON.parse(readFileSync(path.join(here,'space-sequence.json'),'utf8'));
const context=vm.createContext({window:{}});
vm.runInContext(readFileSync(path.join(here,'lab-core.js'),'utf8'),context);
vm.runInContext(readFileSync(path.join(here,'space-sequence.js'),'utf8'),context);
const E=context.window.TEXTBOOK_EXPERIMENTS,L=context.window.LabTools;
let assertions=0,states=0;
const check=(value,msg)=>{assert.ok(value,msg);assertions++;};
const near=(a,b,msg,eps=1e-9)=>check(Math.abs(a-b)<eps*(1+Math.abs(b)),`${msg}: ${a} vs ${b}`);
const numTree=o=>{if(typeof o==='number')check(Number.isFinite(o),'finite model scalar');else if(o&&typeof o==='object')Object.values(o).forEach(numTree);};
const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const norm=a=>Math.hypot(...a);
const expectedSections=[];
for(const book of JSON.parse(readFileSync(path.join(root,'batch/manifests/catalog.json'),'utf8')).books)
 for(const chapter of book.chapters)
  if(book.id==='x1'||(book.id==='bx3'&&['bx3-c10','bx3-c11'].includes(chapter.id)))expectedSections.push(...chapter.sections.map(s=>s.id));
assert.deepEqual(spec.selection.map(s=>s.sectionId).sort(),expectedSections.sort());
check(spec.assets.length===12,'twelve high-value labs');
check(spec.selection.every(s=>s.reason&&['selected','existing','skip'].includes(s.status)),'all decisions have reasons');
for(const item of [...spec.assets,...spec.existing]){
 check(item.summary.length>30,'substantive condition-preserving summary');
 for(const placement of item.placements){
  const sid=placement.sectionId;
  const section=JSON.parse(readFileSync(path.join(root,`batch/sections/${sid.split('-')[0]}/${sid}.json`),'utf8'));
  const match=placement.afterBlockId.match(/-b(\d+)$/);check(Boolean(match),'stable block id');
  const block=section.blocks[Number(match[1])];check(block?.type==='prose','placement is a prose block');check(block.markdown.length>200,'placement replaces substantial prose');
 }
}
const verify={
 'skew-common-perpendicular':m=>{
  const difference=m.footB.map((v,i)=>v-m.footA[i]);
  near(dot(difference,[1,0,0]),0,'AB perpendicular to first direction');near(dot(difference,m.direction),0,'AB perpendicular to second direction');near(norm(difference),m.distance,'distance via foot separation');
  const triple=dot(difference,cross([1,0,0],m.direction));
  if(m.type==='异面')check(Math.abs(triple)>1e-8,'skew lines must be noncoplanar');
  if(m.type==='相交'||m.type==='重合')near(m.distance,0,'intersecting or coincident distance zero');
 },
 'two-directions-normal':m=>{
  near(norm(m.n),1,'candidate unit direction');near(dot(m.n,m.u),m.dotU,'u dot readout');near(dot(m.n,m.v),m.dotV,'v dot readout');
  if(m.independent&&Math.abs(m.dotU)<1e-9&&Math.abs(m.dotV)<1e-9)check(m.normal,'two independent orthogonality conditions imply normal');
  if(!m.independent)near(norm(cross(m.u,m.v)),0,'dependent directions');
 },
 'dihedral-normal-section':m=>{
  near(dot(m.u,[1,0,0]),0,'first section ray perpendicular to edge');near(dot(m.v,[1,0,0]),0,'second section ray perpendicular to edge');
  const cosine=Math.max(-1,Math.min(1,dot(m.u,m.v)/(norm(m.u)*norm(m.v))));near(Math.acos(cosine)*180/Math.PI,m.angle,'dihedral via actual angle',1e-7);
 },
 'prism-cavalieri':m=>{near(m.sectionArea,m.baseArea,'all level sections congruent');near(m.volume,9*3,'volume base times height');near(m.sectionOffset,m.t*m.shift,'linear interpolation of slice displacement');},
 'pyramid-parallel-slices':m=>{
  const base=[[-2,-2],[2,-2],[2,2],[-2,2]];
  const q=base.map(([x,y])=>[(1-m.t)*x+m.t*m.shift,(1-m.t)*y]);
  const area=Math.abs(q.reduce((sum,p,i)=>sum+p[0]*q[(i+1)%4][1]-p[1]*q[(i+1)%4][0],0))/2;
  near(m.sectionArea,area,'slice area independently computed by shoelace');near(m.volume,m.baseArea*m.height/3,'volume');near(m.remainingTopVolume,m.volume*m.ratio**3,'similar top volume');
 },
 'revolving-generator':m=>{near(m.volume,m.cone?Math.PI*m.radius*m.radius*m.height/3:Math.PI*m.radius*m.radius*m.height,'full solid volume');check(m.full===(m.sweep===360),'full sweep classified');},
 'sphere-moving-section':m=>{
  if(m.radius!==null)near(m.radius*m.radius+m.h*m.h,m.R*m.R,'right triangle radius relation');
  else check(Math.abs(m.h)>m.R,'no circle beyond sphere');
  if(m.type==='相切于一点')near(m.radius,0,'tangent radius zero');
 },
 'hemisphere-cavalieri':m=>{near(m.hemisphereArea,Math.PI*m.r*m.r,'sphere disk area');near(m.hemisphereArea,m.annulusArea,'Cavalieri at any height');near(m.volume,2*Math.PI*m.R**3/3,'hemisphere volume');},
 'space-basis-collapse':m=>{
  const determinant=dot(m.u,cross(m.v,m.w));near(m.det,determinant,'determinant independently via triple product');near(m.volume,Math.abs(determinant),'basis parallelepiped volume');
  check(m.independent===(Math.abs(determinant)>1e-10),'noncoplanar condition');near(m.target[2],m.c*m.h,'target height');
 },
 'arithmetic-reverse-pairs':m=>{near(m.sum,m.terms.reduce((a,b)=>a+b,0),'sum independently enumerated');m.terms.forEach((v,i)=>near(v+m.reversed[i],m.pair,'pair is constant'));},
 'geometric-shift-cancel':m=>{near(m.lhs,m.rhs,'cancel identity');near(m.sum,m.constant?m.n:(1-m.q**m.n)/(1-m.q),'sum formula including q=1');},
 'sqrt2-iteration-compare':m=>{
  near(m.terms[0],m.initial,'initial restored');
  for(let i=0;i<m.steps;i++){
   const x=m.terms[i],y=m.terms[i+1];
   if(m.method==='babylon'){near(2*x*y,x*x+2,'Babylon recurrence identity');check(y>=Math.sqrt(2)-1e-12,'Babylon after one step above root');if(i>0)check(y<=x+1e-12,'Babylon monotone after first step');}
   else if(m.method==='reciprocal'){near(x*y,2,'reciprocal products');if(i>0)near(y,m.terms[i-1],'two-cycle');}
   else {near((y-1)*(x+1),1,'slow recurrence');if(Math.abs(x-Math.sqrt(2))>1e-12)check((x-Math.sqrt(2))*(y-Math.sqrt(2))<=0,'slow method alternates');}
  }
  near(m.error,Math.abs(m.last-Math.sqrt(2)),'reported floating error');
 }
};
for(const asset of spec.assets){
 const exp=E[asset.id];check(Boolean(exp),'model registered');check(asset.formula.startsWith('<math '),'native mathml');
 const variants=[asset.initial];
 for(const c of asset.controls){
  const values=c.type==='select'?c.options.map(o=>o.value):c.type==='checkbox'?[true,false]:[c.min,c.max,(c.min+c.max)/2];
  for(const v of values)variants.push({...asset.initial,[c.key]:v});
 }
 // All control endpoint combinations exercise simultaneous geometric degeneracies.
 let corners=[{...asset.initial}];
 for(const c of asset.controls){const values=c.type==='select'?c.options.map(o=>o.value):[c.min,c.max];corners=corners.flatMap(s=>values.map(v=>({...s,[c.key]:v})));}
 for(const state of [...variants,...corners]){
  const before=JSON.stringify(state),m=exp.model(state);numTree(m);verify[asset.id](m);
  const result=exp.render(state,L);check(result.svg.length>80,'nonempty figure');check(!/NaN|Infinity|undefined/.test(result.svg),'finite SVG');check(!/<svg\b/.test(result.svg),'inner SVG contract');check(result.note.length>20,'honest explanation');
  check(JSON.stringify(state)===before,'pure model does not mutate state');
  const other={...state,yaw:123};check(JSON.stringify(exp.model(other))===JSON.stringify(m),'camera does not change math');
  states++;
 }
}
// Explicit counterexample: one repeated direction does not force a line normal to the plane.
const degenerate=E['two-directions-normal'].model({separation:0,tilt:45});near(degenerate.dotU,0,'degenerate first condition');near(degenerate.dotV,0,'degenerate second condition');check(!degenerate.normal,'counterexample remains oblique');
console.log(`space-sequence: ${spec.assets.length} models; ${states} boundary/typical states; ${assertions} assertions passed; ${spec.selection.length} section decisions validated.`);
