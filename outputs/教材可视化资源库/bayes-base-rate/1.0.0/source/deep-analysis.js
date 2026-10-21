(() => {
  'use strict';
  const pairs = repeat => Array.from({length: 6}, (_, i) => Array.from({length: 6}, (_, j) => [i + 1, j + 1])).flat().filter(([i, j]) => repeat || i !== j);
  const key = pair => pair.slice().sort((a, b) => a - b).join('-');
  const box = (x, y, w, h, fill, stroke = '#a6b8af') => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="4" fill="${fill}" stroke="${stroke}"/>`;
  const defs = {
    'parameter-cubic-roots': {
      model(s) {
        const a = Number(s.a);
        let roots;
        if (a === 2) roots = [{x: -1, multiplicity: 2}, {x: 2, multiplicity: 1}];
        else if (a === -2) roots = [{x: -2, multiplicity: 1}, {x: 1, multiplicity: 2}];
        else if (Math.abs(a) < 2) {
          const theta = Math.acos(a / 2) / 3;
          roots = [0, 1, 2].map(k => ({x: 2 * Math.cos(theta - 2 * Math.PI * k / 3), multiplicity: 1})).sort((p, q) => p.x - q.x);
        } else {
          const delta = Math.sqrt(a * a / 4 - 1);
          roots = [{x: Math.cbrt(a / 2 + delta) + Math.cbrt(a / 2 - delta), multiplicity: 1}];
        }
        return {a, roots, count: roots.length, realMultiplicity: roots.reduce((sum, r) => sum + r.multiplicity, 0), critical: Math.abs(a) === 2,
          derivative: '3(x²−1)', monotonicity: ['增', '减', '增'], extrema: [[-1, 2], [1, -2]]};
      },
      render(s, L) {
        const m = this.model(s), p = (x, y) => [300 + 94 * x, 177 - 25 * y], f = x => x ** 3 - 3 * x;
        let svg = L.line(p(-2.65, 0), p(2.65, 0), 'axis') + L.line(p(0, -5), p(0, 5), 'axis');
        for (const x of [-2, -1, 1, 2]) svg += L.text(p(x, 0)[0] - 5, 195, String(x));
        for (const y of [-4, -2, 2, 4]) svg += L.text(277, p(0, y)[1] + 4, String(y));
        const curve = fn => L.sample(x => [x, fn(x)], -2.5, 2.5, 400).filter(([, y]) => Math.abs(y) <= 5).map(([x, y]) => p(x, y));
        svg += L.path(curve(f), 'curve') + L.line(p(-2.65, m.a), p(2.65, m.a), 'highlight');
        if (s.showDerivative) svg += L.path(curve(x => 3 * (x * x - 1)), 'secondary');
        for (const [x, y] of m.extrema) svg += L.line(p(x, 0), p(x, y), 'dashed') + L.dot(p(x, y));
        m.roots.forEach((r, i) => { svg += L.dot(p(r.x, m.a), `x${i + 1}${r.multiplicity === 2 ? '（二重）' : ''}`, 'highlight'); });
        svg += L.text(30, 25, s.showDerivative ? '绿：f(x)；橙：y=a；蓝：f′(x)' : '绿：f(x)；橙：y=a') + L.text(540, 168, 'x') + L.text(309, 45, 'y');
        svg += L.text(45, 325, 'f′：正 → 0 → 负 → 0 → 正') + L.text(45, 347, 'f：增（x<−1）／减（−1<x<1）／增（x>1）');
        const roots = m.roots.map(r => `${L.fmt(r.x, 5)}${r.multiplicity === 2 ? '（二重）' : ''}`).join('，');
        return {svg, metrics: [['参数 a', L.fmt(m.a, 2)], ['不同实根数', String(m.count)], ['实根（近似）', roots], ['实根按重数计', String(m.realMultiplicity)]],
          note: `f′(x)=3(x−1)(x+1)，故三个单调区间依次增、减、增，且 f(−1)=2、f(1)=−2；再结合两端趋势可严格分类：−2<a<2 有三个不同实根，a=±2 有两个不同实根，其中一个为二重根，|a|>2 仅一个实根（另两根非实数）。${m.critical ? '当前恰在临界值，水平线在极值点相切。' : '将 a 调到精确的 −2 或 2，比较临界值两侧。'}图像用于观察，根数结论由单调性及各段值域保证，不靠屏幕采样。临界值的因式分解见“为什么成立 · 条件与推导”。`};
      }
    },
    'counting-equal-multiplicity': {
      model(s) {
        const dice = s.scenario === 'dice', ordered = pairs(dice), groups = [];
        for (const pair of ordered) {
          const k = key(pair); let g = groups.find(group => group.key === k);
          if (!g) {g = {key: k, pair: pair.slice().sort((a, b) => a - b), preimages: []}; groups.push(g);}
          g.preimages.push(pair);
        }
        groups.sort((a, b) => a.pair[0] - b.pair[0] || a.pair[1] - b.pair[1]);
        const selected = groups.find(g => g.key === s.result) || null;
        return {dice, ordered, groups, orderedCount: ordered.length, finalCount: groups.length, equalMultiplicity: !dice,
          selectedKey: s.result, selected, selectedExists: !!selected, multiplicity: selected ? selected.preimages.length : 0,
          selectedProbability: selected ? selected.preimages.length / ordered.length : 0};
      },
      render(s, L) {
        const m = this.model(s); let svg = L.text(28, 26, `有序过程：${m.orderedCount} 个`) + L.text(333, 26, `归并后：${m.finalCount} 个`);
        for (let i = 1; i <= 6; i++) for (let j = 1; j <= 6; j++) {
          const valid = m.dice || i !== j, active = valid && key([i, j]) === m.selectedKey, x = 28 + (j - 1) * 39, y = 52 + (i - 1) * 42;
          svg += box(x, y, 36, 34, active ? '#f2ccaa' : valid ? '#e1ede5' : '#f1f0eb');
          svg += L.text(x + 4, y + 21, valid ? `${i},${j}` : '—');
        }
        svg += L.line([270, 176], [312, 176], 'highlight') + L.text(275, 163, '归并');
        m.groups.forEach((g, index) => {
          const x = 333 + index % 3 * 83, y = 52 + Math.floor(index / 3) * 37;
          svg += box(x, y, 77, 30, g.key === m.selectedKey ? '#f2ccaa' : '#edf2ee', g.key === m.selectedKey ? '#a15b2b' : '#a6b8af');
          svg += L.text(x + 8, y + 20, `{${g.pair.join(',')}}`);
        });
        svg += L.text(28, 334, m.dice ? '先区分两枚骰子，再忽略顺序' : '从六个不同元素中依次取两个，不放回');
        const preimages = m.selected ? m.selected.preimages.map(p => `(${p.join(',')})`).join('、') : '不存在（不能两次选同一元素）';
        return {svg, metrics: [['对应的有序过程', preimages], ['当前结果被计次数', String(m.multiplicity)], ['每个结果重复次数相同？', m.equalMultiplicity ? '相同，均为2' : '不同：同点数1，异点数2'], ['当前结果概率', m.selected ? `${m.multiplicity}/${m.orderedCount}` : '0（不属于结果集）']],
          note: m.dice ? '两枚可区分的公平骰子独立投掷，36个有序结果等可能。忽略顺序后共有21组：6组同点数各对应1个过程，15组异点数各对应2个过程，因此36不能统一除以2；也不能把这21组视为等可能。当前高亮的左侧小格就是右侧选中结果的全部来源。'
            : '从1至6六个不同元素中依次等可能地不放回取两个，有30个有序过程。每组不同元素恰对应两种顺序，故组合数为30÷2=15；统一相除的依据是“每个结果被计次数都相同”，不只是结果忽略顺序。选择含相同元素的结果时，它在此场景中不存在；切换骰子场景后才允许重复。'};
      }
    },
    'bayes-base-rate': {
      model(s) {
        const n = 10000, prevalence = Number(s.prevalence) / 100, sensitivity = Number(s.sensitivity) / 100, falsePositive = Number(s.falsePositive) / 100;
        const disease = n * prevalence, healthy = n - disease, tp = disease * sensitivity, fn = disease - tp, fp = healthy * falsePositive, tn = healthy - fp, positive = tp + fp;
        return {n, prevalence, sensitivity, falsePositive, disease, healthy, tp, fn, fp, tn, positive,
          positiveRate: positive / n, posterior: positive > 0 ? tp / positive : null,
          conditionalDetection: disease > 0 ? sensitivity : null, conditionalFalsePositive: healthy > 0 ? falsePositive : null,
          integerCounts: [disease, healthy, tp, fn, fp, tn].every(x => Math.abs(x - Math.round(x)) < 1e-8)};
      },
      render(s, L) {
        const m = this.model(s), count = x => L.fmt(x, 3);
        let svg = L.text(26, 24, '10000人的模型期望频数；框与连线不按人数比例绘制');
        svg += L.dot([66, 155], '') + L.text(26, 178, '全体10000');
        svg += L.line([70, 155], [166, 83], 'aux') + L.line([70, 155], [166, 224], 'aux');
        const nodes = [[166, 56, '实际患病', m.disease, '#dbe9e0'], [166, 197, '实际未患病', m.healthy, '#e0e8ee']];
        for (const [x, y, label, value, fill] of nodes) svg += box(x, y, 136, 56, fill) + L.text(x + 10, y + 22, label) + L.text(x + 10, y + 44, count(value));
        const outcomes = [[371, 40, '阳性／真阳性', m.tp, '#efc8a4'], [371, 108, '阴性／漏检', m.fn, '#e6eee8'], [371, 181, '阳性／假阳性', m.fp, '#b5cddd'], [371, 249, '阴性／真阴性', m.tn, '#e6eee8']];
        for (const [x, y, label, value, fill] of outcomes) {
          const parentY = y < 170 ? 84 : 225;
          svg += L.line([302, parentY], [x, y + 23], 'aux') + box(x, y, 196, 47, fill) + L.text(x + 9, y + 19, label) + L.text(x + 9, y + 39, count(value));
        }
        if (m.posterior !== null) {
          svg += box(166, 319, 401 * m.posterior, 18, '#efc8a4') + box(166 + 401 * m.posterior, 319, 401 * (1 - m.posterior), 18, '#b5cddd');
          svg += L.text(26, 333, '只看阳性者') + L.text(166, 354, '橙：真阳性；蓝：假阳性（本条宽度按比例）');
        } else svg += L.text(166, 333, '阳性者为空：不能计算其内部比例');
        return {svg, metrics: [['P(阳性 | 患病)', m.conditionalDetection === null ? '未定义：患病组为空' : `${L.fmt(100 * m.sensitivity, 2)}%`], ['阳性者期望总数', count(m.positive)], ['P(患病 | 阳性)', m.posterior === null ? '未定义：阳性概率为0' : `${L.fmt(100 * m.posterior, 3)}%`], ['频数性质', '模型期望值，非实测人数']],
          note: `这是教学模型，不是医疗建议。三个参数 p、s、q 分别是患病率、模型检出率和模型误报率；改变患病率并不会改变后两项设定，却会改变阳性者构成。反向条件的分母是真阳性与假阳性之和，而不是全体患病者。${m.posterior === null ? '当前没有阳性者，条件概率的分母为0，故不显示为0%。' : '底部只在阳性者内重新计算比例，没有把漏检和真阴性计入分母。'}${m.prevalence === 0 ? '患病组为空时，设定的检出率仍是模型参数，但P(阳性|患病)本身未定义。' : ''}${m.prevalence === 1 ? '未患病组为空，误报率仅作为模型参数，其对应条件概率未定义。' : ''}频数均是10000人模型中的期望数，可为小数，显示值保留三位；不把它们伪装成一次真实观测。贝叶斯公式作为教师选学拓展，展开“为什么成立 · 条件与推导”核对条件与分母。`};
      }
    }
  };
  window.TEXTBOOK_EXPERIMENTS = Object.assign(window.TEXTBOOK_EXPERIMENTS || {}, defs);
})();
