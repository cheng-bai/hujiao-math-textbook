import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const read = name => fs.readFileSync(new URL(name, import.meta.url), 'utf8');
const context = vm.createContext({window: {}, Math, Number, Array, Object, String});
for (const name of ['lab-core.js', 'deep-analysis.js']) vm.runInContext(read(name), context, {filename: name});
const defs = context.window.TEXTBOOK_EXPERIMENTS, L = context.window.LabTools;
const spec = JSON.parse(read('deep-analysis.json'));
let states = 0, relations = 0;
const near = (actual, expected, tolerance = 1e-9) => {relations++; assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} ≠ ${expected}`);};
function render(id, state) {
  const before = JSON.stringify(state), result = defs[id].render(state, L);
  states++;
  assert.equal(JSON.stringify(state), before, 'render must not mutate state');
  assert.ok(result.note.length > 30);
  assert.ok(result.svg.length > 100);
  assert.ok(!/NaN|Infinity|undefined/.test(result.svg));
  assert.ok(result.metrics.every(([key, value]) => typeof key === 'string' && typeof value === 'string'));
  return result;
}
assert.equal(spec.family, 'deep-analysis');
assert.equal(spec.assets.length, 3);
for (const asset of spec.assets) {
  assert.ok(defs[asset.id]);
  assert.match(asset.formula, /^<math xmlns="http:\/\/www.w3.org\/1998\/Math\/MathML"/);
  assert.match(asset.formula, /<\/(?:math)>$/);
  assert.match(asset.explanationHtml, /<p>/);
  assert.ok((asset.explanationHtml.match(/<math xmlns=/g) || []).length >= 4, 'derivation must actually render formulas');
  assert.ok(!/[²³₀-₉]/.test(asset.explanationHtml), 'use MathML powers/subscripts rather than Unicode formula substitutes');
  assert.deepEqual(Object.keys(asset.initial).sort(), asset.controls.map(c => c.key).sort());
  assert.deepEqual(Object.values(asset.stateKeys).flat().sort(), Object.keys(asset.initial).sort());
  for (const placement of asset.placements) {
    const section = JSON.parse(read(`../../batch/sections/x2/${placement.sectionId}.json`));
    const index = Number(placement.afterBlockId.match(/-b(\d+)$/)[1]);
    assert.equal(section.blocks[index].type, 'prose');
    assert.equal(placement.retainProse, true);
  }
  render(asset.id, asset.initial);
}
const cubic = defs['parameter-cubic-roots'];
for (const a of [...Array.from({length: 161}, (_, i) => (i - 80) / 20), -2 - 1e-10, -2 + 1e-10, 2 - 1e-10, 2 + 1e-10]) {
  const m = cubic.model({a});
  assert.equal(m.count, Math.abs(a) < 2 ? 3 : Math.abs(a) === 2 ? 2 : 1);
  for (const root of m.roots) {
    near(root.x ** 3 - 3 * root.x, a, 2e-12);
    if (root.multiplicity === 2) {near(3 * root.x ** 2 - 3, 0); assert.notEqual(6 * root.x, 0);}
    else assert.notEqual(3 * root.x ** 2 - 3, 0);
  }
  if (m.count === 3) {
    assert.ok(m.roots[0].x < -1 && m.roots[1].x > -1 && m.roots[1].x < 1 && m.roots[2].x > 1);
    near(m.roots.reduce((sum, root) => sum + root.x, 0), 0);
  }
  // Independently bracket roots on monotone pieces, without using the solver formula.
  const f = x => x ** 3 - 3 * x - a;
  const intervals = [[-4, -1], [-1, 1], [1, 4]];
  for (const [lo, hi] of intervals) {
    if (f(lo) * f(hi) < 0) {
      let l = lo, h = hi;
      for (let k = 0; k < 65; k++) {const mid = (l + h) / 2; if (f(l) * f(mid) <= 0) h = mid; else l = mid;}
      assert.ok(m.roots.some(root => Math.abs(root.x - (l + h) / 2) < 1e-8));
      relations++;
    }
  }
  render('parameter-cubic-roots', {a, showDerivative: false});
  const shown = cubic.model({a, showDerivative: true});
  assert.deepEqual(shown, m, 'lesson toggle cannot change roots');
  render('parameter-cubic-roots', {a, showDerivative: true});
}
const counting = defs['counting-equal-multiplicity'];
for (const scenario of ['distinct', 'dice']) {
  for (let i = 1; i <= 6; i++) for (let j = i; j <= 6; j++) {
    const state = {scenario, result: `${i}-${j}`}, m = counting.model(state), seen = new Set();
    assert.equal(m.orderedCount, scenario === 'dice' ? 36 : 30);
    assert.equal(m.finalCount, scenario === 'dice' ? 21 : 15);
    for (const g of m.groups) for (const [a, b] of g.preimages) {
      const orderedKey = `${a},${b}`;
      assert.ok(!seen.has(orderedKey)); seen.add(orderedKey);
      assert.equal([a, b].sort((x, y) => x - y).join('-'), g.key);
    }
    assert.equal(seen.size, m.orderedCount);
    const expected = scenario === 'distinct' && i === j ? 0 : i === j ? 1 : 2;
    assert.equal(m.multiplicity, expected);
    near(m.selectedProbability, expected / (scenario === 'dice' ? 36 : 30));
    near(m.groups.reduce((sum, g) => sum + g.preimages.length / m.orderedCount, 0), 1);
    if (m.selected) assert.ok(m.selected.preimages.every(([a, b]) => (a === i && b === j) || (a === j && b === i)));
    const result = render('counting-equal-multiplicity', state);
    // Active left sources and final tile are visibly linked, but inactive repeated selections stay honest.
    assert.equal((result.svg.match(/fill="#f2ccaa"/g) || []).length, expected ? expected + 1 : 0);
    relations++;
  }
}
const bayes = defs['bayes-base-rate'];
for (const prevalence of [0, .1, 1, 10, 50, 99.9, 100]) for (const sensitivity of [0, 1, 50, 99, 100]) for (const falsePositive of [0, .1, 5, 50, 100]) {
  const state = {prevalence, sensitivity, falsePositive}, m = bayes.model(state), p = prevalence / 100, s = sensitivity / 100, q = falsePositive / 100;
  near(m.tp + m.fn + m.fp + m.tn, 10000);
  near(m.tp + m.fn, m.disease);
  near(m.fp + m.tn, m.healthy);
  near(m.positiveRate, p * s + (1 - p) * q);
  if (m.positive === 0) assert.equal(m.posterior, null);
  else {near(m.posterior, p * s / (p * s + (1 - p) * q)); assert.ok(m.posterior >= 0 && m.posterior <= 1);}
  assert.equal(m.conditionalDetection, prevalence === 0 ? null : s);
  assert.equal(m.conditionalFalsePositive, prevalence === 100 ? null : q);
  const result = render('bayes-base-rate', state);
  if (m.positive === 0) {assert.match(result.note, /分母为0/); assert.ok(result.metrics.some(([, v]) => v === '未定义：阳性概率为0'));}
}
const rare = bayes.model({prevalence: 1, sensitivity: 99, falsePositive: 5}), common = bayes.model({prevalence: 50, sensitivity: 99, falsePositive: 5});
assert.ok(rare.posterior < .2 && common.posterior > .9);
near(rare.tp, 99); near(rare.fp, 495); near(rare.posterior, 1 / 6);
const fractional = bayes.model({prevalence: .1, sensitivity: 99, falsePositive: .1});
assert.equal(fractional.integerCounts, false);
console.log(JSON.stringify({family: 'deep-analysis', assets: 3, states, independentRelations: relations, realLabTools: true, status: 'passed'}));
