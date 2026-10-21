import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const base='scripts/textbook-labs/';
const context={window:{}}; vm.createContext(context);
vm.runInContext(fs.readFileSync(base+'lab-core.js','utf8')+fs.readFileSync(base+'deep-spatial.js','utf8'),context);
const e=context.window.TEXTBOOK_EXPERIMENTS['cube-plane-transitions'];
let checks=0;
const near=(a,b)=>{assert.ok(Math.abs(a-b)<1e-8,`${a} != ${b}`);checks++;};
for(const [offset,count] of [[6,3],[4,4],[2,5],[0,6],[9,1],[10,0],[-6,3],[-4,4],[-2,5]]){
 const m=e.model({direction:'general',offset,yaw:35});assert.equal(m.points.length,count);checks++;
}
for(const direction of ['general','diagonal','edge','face'])for(let offset=-10;offset<=10;offset+=.125){
 const s={direction,offset,yaw:35},m=e.model(s);
 assert.ok(m.points.length<=6);checks++;
 for(const p of m.points){
  near(p.reduce((a,x,i)=>a+x*m.normal[i],0),offset);
  assert.ok(p.every(x=>Math.abs(x)<=1+1e-9));checks++;
  assert.ok(p.filter(x=>Math.abs(Math.abs(x)-1)<1e-8).length>=2);checks++;
 }
 assert.equal(JSON.stringify(e.model({...s,yaw:175})),JSON.stringify(m));checks++;
 const svg=e.render(s,context.window.LabTools).svg;assert.ok(!/(NaN|Infinity|undefined)/.test(svg));checks++;
}
const central=e.model({direction:'diagonal',offset:0,yaw:0});
near(central.area,3*Math.sqrt(3));assert.equal(central.regular,true);checks++;
near(e.model({direction:'face',offset:1,yaw:0}).area,4);
near(e.model({direction:'edge',offset:0,yaw:0}).area,4*Math.sqrt(2));
assert.equal(e.model({direction:'edge',offset:2,yaw:0}).points.length,2);checks++;
assert.equal(e.model({direction:'general',offset:0,yaw:0}).regular,false);checks++;
const spec=JSON.parse(fs.readFileSync(base+'deep-spatial.json','utf8'));
for(const a of spec.assets)for(const p of a.placements){
 const section=JSON.parse(fs.readFileSync(`batch/sections/${p.sectionId.split('-')[0]}/${p.sectionId}.json`,'utf8'));
 assert.ok(section.blocks.some((b,i)=>b.type==='prose'&&(b.id||`${p.sectionId}-b${i}`)===p.afterBlockId));checks++;
}
console.log(JSON.stringify({status:'passed',checks,assets:spec.assets.length}));
