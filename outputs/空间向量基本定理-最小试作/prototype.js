(() => {
  'use strict';

  const M = window.BasisModel = {
    e1: [1.6, 0, 0],
    e2: [0, 1.5, 0],
    e3: [0.45, 0.35, 1.35],
    q0: [1.12, 0.75, 0],
    point(q, n) { return this.q0.map((x, i) => q * x + n * this.e3[i]); },
    split(q, n) {
      const Q = this.q0.map(x => q * x);
      const R = [Q[0], 0, 0];
      const P = this.point(q, n);
      return { O: [0, 0, 0], P, Q, R, OR: R, RQ: Q.map((x, i) => x - R[i]), QP: P.map((x, i) => x - Q[i]) };
    }
  };

  const NS = 'http://www.w3.org/2000/svg';
  const colors = { ink: '#1b292c', blue: '#176b78', red: '#c4553d', gold: '#b28b3c', green: '#477c63', white: '#fffefa' };
  const projection = ([x, y, z]) => [280 + 92 * x + 46 * y, 330 - 16 * x - 45 * y - 110 * z];
  const el = (tag, attrs = {}, text = '') => {
    const node = document.createElementNS(NS, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
    if (text) node.textContent = text;
    return node;
  };
  const line = (svg, a, b, attrs = {}) => {
    const [x1, y1] = projection(a), [x2, y2] = projection(b);
    svg.append(el('line', { x1, y1, x2, y2, ...attrs }));
  };
  const point = (svg, v, label, color = colors.ink, dx = 8, dy = -8) => {
    const [cx, cy] = projection(v);
    svg.append(el('circle', { cx, cy, r: 5.5, fill: color, class: 'point' }));
    svg.append(el('text', { x: cx + dx, y: cy + dy }, label));
  };
  const vector = (svg, a, b, color, marker, width = 3, zeroLabel = '0') => {
    if (Math.hypot(...a.map((x, i) => b[i] - x)) < 1e-8) {
      if (!zeroLabel) return;
      const [cx, cy] = projection(b);
      svg.append(el('circle', { cx, cy, r: 4, fill: color }));
      svg.append(el('text', { x: cx + 7, y: cy - 5, class: 'tiny' }, zeroLabel));
      return;
    }
    line(svg, a, b, { stroke: color, 'stroke-width': width, 'marker-end': `url(#${marker})` });
  };
  function defs(svg, prefix) {
    const defsNode = el('defs');
    for (const [name, color] of Object.entries({ blue: colors.blue, red: colors.red, green: colors.green, gold: colors.gold })) {
      const marker = el('marker', { id: `${prefix}-${name}`, markerWidth: 8, markerHeight: 8, refX: 7, refY: 4, orient: 'auto', markerUnits: 'strokeWidth' });
      marker.append(el('path', { d: 'M0,0 L8,4 L0,8 z', fill: color }));
      defsNode.append(marker);
    }
    svg.append(defsNode);
  }

  function drawPlane(svg) {
    const vertices = [[-.55, -.45, 0], [2.15, -.45, 0], [2.15, 1.7, 0], [-.55, 1.7, 0]].map(projection);
    svg.append(el('polygon', { points: vertices.map(p => p.join(',')).join(' '), class: 'plane-fill' }));
    const [x, y] = [24, 408];
    svg.append(el('text', { x, y, class: 'tiny' }, '平面 α · 局部示意，边界不是条件'));
  }

  function scene(svg, q, n, stage, prefix) {
    svg.replaceChildren();
    svg.setAttribute('class', `figure stage-${stage}`);
    defs(svg, prefix);
    drawPlane(svg);
    const s = M.split(q, n), { O, P, Q, R } = s;
    const axisA = [-.5, 0, 0], axisB = [2.05, 0, 0], axisC = [0, -.45, 0], axisD = [0, 1.7, 0];
    line(svg, axisA, axisB, { stroke: '#87928e', 'stroke-width': 1.3 });
    line(svg, axisC, axisD, { stroke: '#87928e', 'stroke-width': 1.3 });
    vector(svg, O, M.e1, colors.blue, `${prefix}-blue`);
    vector(svg, O, M.e2, colors.blue, `${prefix}-blue`);
    vector(svg, O, M.e3, colors.blue, `${prefix}-blue`);
    svg.append(el('text', { x: projection(M.e1)[0] + 4, y: projection(M.e1)[1] + 16 }, 'e₁'));
    svg.append(el('text', { x: projection(M.e2)[0] - 20, y: projection(M.e2)[1] - 4 }, 'e₂'));
    svg.append(el('text', { x: projection(M.e3)[0] + 9, y: projection(M.e3)[1] - 2 }, 'e₃'));
    const targetAtO = Math.hypot(...P) < 1e-8;
    if (!targetAtO) vector(svg, O, P, colors.red, `${prefix}-red`, 3.4);
    point(svg, O, targetAtO ? 'O = P' : 'O');
    if (!targetAtO) point(svg, P, 'P', colors.red, 9, -9);

    if (stage >= 1) {
      const tail = Q.map((x, i) => x - .54 * M.e3[i]);
      const head = P.map((x, i) => x + .34 * M.e3[i]);
      line(svg, tail, head, { class: 'aux' });
      if (Math.abs(n) > 1e-8 && Math.abs(q) > 1e-8) point(svg, Q, 'Q', colors.gold, 8, 15);
      else if (Math.abs(q) < 1e-8 && Math.abs(n) > 1e-8 && stage === 1) svg.append(el('text', { x: projection(O)[0] + 8, y: projection(O)[1] + 16, class: 'tiny' }, 'Q = O'));
      else if (Math.abs(n) < 1e-8 && Math.abs(q) > 1e-8) svg.append(el('text', { x: projection(P)[0] + 8, y: projection(P)[1] + 14, class: 'tiny' }, 'Q = P'));
      if (stage === 1) vector(svg, O, Q, colors.green, `${prefix}-green`, 2.8, Math.abs(q) < 1e-8 ? '' : 'OQ = 0');
      vector(svg, Q, P, colors.green, `${prefix}-green`, 3.1, Math.abs(n) < 1e-8 ? '' : 'QP = 0');
      const lp = projection(head);
      svg.append(el('text', { x: lp[0] - 16, y: lp[1] - 8, class: 'tiny' }, 'g ∥ e₃'));
    }
    if (stage >= 2) {
      const left = Q.map((x, i) => x - .5 * M.e2[i]);
      const right = Q.map((x, i) => x + .5 * M.e2[i]);
      line(svg, left, right, { class: 'aux' });
      if (Math.abs(q) > 1e-8) point(svg, R, 'R', colors.gold, 8, 15);
      else svg.append(el('text', { x: projection(O)[0] + 8, y: projection(O)[1] + 16, class: 'tiny' }, 'Q = R = O'));
      vector(svg, O, R, colors.green, `${prefix}-green`, 3.1, Math.abs(q) < 1e-8 ? '' : 'OR = 0');
      vector(svg, R, Q, colors.green, `${prefix}-green`, 3.1, Math.abs(q) < 1e-8 ? '' : 'RQ = 0');
      vector(svg, Q, P, colors.green, `${prefix}-green`, 3.1, Math.abs(n) < 1e-8 ? '' : 'QP = 0');
      const lp = projection(right);
      svg.append(el('text', { x: lp[0] + 4, y: lp[1] - 4, class: 'tiny' }, '∥ e₂'));
    }
  }

  const planeSvg = document.querySelector('#plane-handle');
  const qRange = [-.25, 1.35], nRange = [-.45, 1.2];
  const origin = [111, 126], uq = [176, -23], un = [82, -76];
  const planePoint = (q, n) => [origin[0] + uq[0] * q + un[0] * n, origin[1] + uq[1] * q + un[1] * n];
  let q = 1, n = .8, stage = 0, completeView = false, dragging = false;
  function drawHandle() {
    planeSvg.replaceChildren();
    const markers = el('defs');
    for (const [name, color] of [['green', colors.green], ['blue', colors.blue]]) {
      const marker = el('marker', { id: `handle-${name}`, markerWidth: 8, markerHeight: 8, refX: 7, refY: 4, orient: 'auto', markerUnits: 'strokeWidth' });
      marker.append(el('path', { d: 'M0,0 L8,4 L0,8 z', fill: color }));
      markers.append(marker);
    }
    planeSvg.append(markers);
    const polygon = [planePoint(qRange[0], nRange[0]), planePoint(qRange[1], nRange[0]), planePoint(qRange[1], nRange[1]), planePoint(qRange[0], nRange[1])];
    planeSvg.append(el('polygon', { points: polygon.map(p => p.join(',')).join(' '), fill: '#e2e9df', stroke: '#a9b7aa', 'stroke-width': 1.2 }));
    for (let k = -2; k <= 6; k++) {
      const v = k * .25;
      if (v >= qRange[0] && v <= qRange[1]) {
        const a = planePoint(v, nRange[0]), b = planePoint(v, nRange[1]);
        planeSvg.append(el('line', { x1: a[0], y1: a[1], x2: b[0], y2: b[1], stroke: '#cbd5ca', 'stroke-width': 1 }));
      }
    }
    for (let k = -2; k <= 5; k++) {
      const v = k * .25;
      if (v >= nRange[0] && v <= nRange[1]) {
        const a = planePoint(qRange[0], v), b = planePoint(qRange[1], v);
        planeSvg.append(el('line', { x1: a[0], y1: a[1], x2: b[0], y2: b[1], stroke: '#cbd5ca', 'stroke-width': 1 }));
      }
    }
    const o = planePoint(0, 0), qe = planePoint(.58, 0), ne = planePoint(0, .58);
    planeSvg.append(el('line', { x1: o[0], y1: o[1], x2: qe[0], y2: qe[1], stroke: colors.green, 'stroke-width': 2, 'marker-end': 'url(#handle-green)' }));
    planeSvg.append(el('line', { x1: o[0], y1: o[1], x2: ne[0], y2: ne[1], stroke: colors.blue, 'stroke-width': 2, 'marker-end': 'url(#handle-blue)' }));
    planeSvg.append(el('text', { x: qe[0] - 16, y: qe[1] + 19, class: 'tiny' }, '沿 OQ₀'));
    planeSvg.append(el('text', { x: ne[0] + 3, y: ne[1] - 6, class: 'tiny' }, '沿 OC（e₃）'));
    const [px, py] = planePoint(q, n);
    planeSvg.append(el('circle', { cx: px, cy: py, r: 9, fill: colors.red, stroke: '#fffefa', 'stroke-width': 3, class: 'handle-target' }));
    planeSvg.append(el('text', { x: px + 10, y: py - 8, fill: colors.red }, 'P'));
    const [ox, oy] = planePoint(0, 0);
    planeSvg.append(el('circle', { cx: ox, cy: oy, r: 3, fill: colors.ink }));
  }
  function solvePlane(px, py) {
    const x = px - origin[0], y = py - origin[1];
    const det = uq[0] * un[1] - un[0] * uq[1];
    const nextQ = (x * un[1] - un[0] * y) / det;
    const nextN = (uq[0] * y - x * uq[1]) / det;
    q = Math.max(qRange[0], Math.min(qRange[1], nextQ));
    n = Math.max(nRange[0], Math.min(nRange[1], nextN));
    update();
  }
  function localPoint(event) {
    const box = planeSvg.getBoundingClientRect();
    return [(event.clientX - box.left) * 460 / box.width, (event.clientY - box.top) * 168 / box.height];
  }
  function update() {
    const shownStage = completeView ? 2 : stage;
    scene(document.querySelector('#dynamic-scene'), q, n, shownStage, 'dynamic');
    drawHandle();
    const label = document.querySelector('#stage-label');
    const cap = document.querySelector('#dynamic-caption');
    const formula = document.querySelector('#dynamic-formula');
    const captions = [
      ['先看目标', '前两个方向只在平面 α 内；目标 P 在平面外。', '问题：要怎样把“空间”这一段单独取出来？'],
      ['唯一落点 Q', '沿 e₃ 方向过 P 作直线，落回 α 的点只能是 Q。', 'e₃ 不在 α 内，因此该直线不平行 α，只交一次。QP 不是垂足。'],
      ['平面内再拆', '过 Q 作平行 e₂ 的线，交 e₁ 所在直线于 R。', 'e₁、e₂ 不共线，两直线只交一次；Q 固定后，R 也唯一。']
    ][shownStage];
    if (Math.abs(q) < 1e-8 && Math.abs(n) < 1e-8) {
      captions[0] = '零向量目标 P=O；三个分量都为零。';
      captions[1] = '此状态下 Q=R=O，三段位移全为零。';
      captions[2] = '分解仍成立，零向量不需要画成有长度的箭头。';
    } else if (Math.abs(q) < 1e-8) {
      captions[0] = '目标 P 在第三方向所在直线上；平面内两段为零。';
      captions[1] = '落点 Q=O；目标只需沿第三方向到达。';
      captions[2] = 'Q=R=O，前两段为零，分解仍成立。';
    } else if (Math.abs(n) < 1e-8 && shownStage === 0) {
      captions[1] = '此刻目标 P 已在平面 α 内。';
      captions[2] = '把 P 移到 α 外，观察缺少的空间方向。';
    } else if (Math.abs(n) < 1e-8 && shownStage > 0) {
      captions[1] = '目标 P 已在 α 内，落点 Q 与 P 重合，第三段为零。';
      captions[2] = '此状态下第三个系数 ν=0，不是构造失败。';
    } else if (n < 0 && q < 0 && shownStage > 0) {
      captions[1] = '第三段与平面内两段都要反向取；图中始终按有向向量相加。';
      captions[2] = '负分量表示反向，不需要把向量限制成射线。';
    } else if (n < 0 && shownStage > 0) {
      captions[1] = 'P 在落点 Q 的反方向一侧；QP 仍沿 e₃ 所在直线，但有向位移反向。';
      captions[2] = '负分量表示反向，不需要把向量限制成射线。';
    } else if (q < 0 && shownStage > 0) {
      captions[1] = 'Q 在平面内相反一侧，OR 与 RQ 的有向位移同时反向。';
      captions[2] = '反向是负分量，不需要把向量限制成射线。';
    }
    label.textContent = captions[0];
    cap.replaceChildren(document.createTextNode(captions[1]));
    const small = document.createElement('small'); small.textContent = captions[2]; cap.append(small);
    formula.innerHTML = shownStage === 0 ? '' : shownStage === 1
      ? '<math><mover><mi>OP</mi><mo>→</mo></mover><mo>=</mo><mover><mi>OQ</mi><mo>→</mo></mover><mo>+</mo><mover><mi>QP</mi><mo>→</mo></mover></math>'
      : '<math><mover><mi>OP</mi><mo>→</mo></mover><mo>=</mo><mover><mi>OR</mi><mo>→</mo></mover><mo>+</mo><mover><mi>RQ</mi><mo>→</mo></mover><mo>+</mo><mover><mi>QP</mi><mo>→</mo></mover><mo>=</mo><mi>λ</mi><msub><mi>e</mi><mn>1</mn></msub><mo>+</mo><mi>μ</mi><msub><mi>e</mi><mn>2</mn></msub><mo>+</mo><mi>ν</mi><msub><mi>e</mi><mn>3</mn></msub></math>';
    document.querySelectorAll('.step').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.stage) === stage)));
    const displayToggle = document.querySelector('[data-display-toggle]');
    displayToggle.setAttribute('aria-pressed', String(completeView));
    displayToggle.textContent = completeView ? '回到分步构造' : '显示完整构造';
  }

  planeSvg.addEventListener('pointerdown', event => {
    if (!event.target.classList.contains('handle-target')) return;
    dragging = true; planeSvg.setPointerCapture(event.pointerId); solvePlane(...localPoint(event)); event.preventDefault();
  });
  planeSvg.addEventListener('pointermove', event => { if (dragging) solvePlane(...localPoint(event)); });
  planeSvg.addEventListener('pointerup', () => { dragging = false; });
  planeSvg.addEventListener('pointercancel', () => { dragging = false; });
  planeSvg.addEventListener('keydown', event => {
    const delta = event.shiftKey ? .1 : .025;
    if (event.key === 'ArrowLeft') q -= delta;
    else if (event.key === 'ArrowRight') q += delta;
    else if (event.key === 'ArrowDown') n -= delta;
    else if (event.key === 'ArrowUp') n += delta;
    else return;
    event.preventDefault();
    q = Math.max(qRange[0], Math.min(qRange[1], q));
    n = Math.max(nRange[0], Math.min(nRange[1], n));
    update();
    planeSvg.focus();
  });
  document.querySelectorAll('[data-preset]').forEach(button => button.addEventListener('click', () => {
    if (button.dataset.preset === 'plane') n = 0;
    else if (button.dataset.preset === 'e3') q = 0;
    else { q = 1; n = .8; }
    update();
  }));
  document.querySelectorAll('.step').forEach(button => button.addEventListener('click', () => { stage = Number(button.dataset.stage); completeView = false; update(); }));
  document.querySelector('[data-display-toggle]').addEventListener('click', () => { completeView = !completeView; update(); });
  update();
})();
