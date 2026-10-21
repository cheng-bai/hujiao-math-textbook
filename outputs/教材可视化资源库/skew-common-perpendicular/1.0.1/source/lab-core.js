(() => {
  'use strict';
  const escape = value => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const fmt = (value, digits = 3) => Number.isFinite(value) ? String(Number(value.toFixed(digits))) : '不适用';
  const path = (points, cls = 'curve', close = false) => {
    const valid = points.filter(point => point && point.every(Number.isFinite));
    if (!valid.length) return '';
    return `<path class="${escape(cls)}" d="${valid.map((p, i) => (i ? 'L' : 'M') + p.map(n => n.toFixed(2)).join(',')).join(' ')}${close ? 'Z' : ''}"/>`;
  };
  const line = (p, q, cls = 'aux') => path([p, q], cls);
  const text = (x, y, value, cls = 'label') => `<text x="${fmt(x, 2)}" y="${fmt(y, 2)}" class="${escape(cls)}">${escape(value)}</text>`;
  const dot = (p, label = '', cls = 'point') => `<circle cx="${fmt(p[0], 2)}" cy="${fmt(p[1], 2)}" r="4" class="${escape(cls)}"/>` + (label ? text(p[0] + 7, p[1] - 8, label) : '');
  function world(xmin, xmax, ymin, ymax) {
    const scale = Math.min(516 / (xmax - xmin), 278 / (ymax - ymin));
    const ox = 300 - (xmin + xmax) * scale / 2, oy = 180 + (ymin + ymax) * scale / 2;
    const p = (x, y) => [ox + x * scale, oy - y * scale];
    let axes = '';
    const step = Math.pow(10, Math.floor(Math.log10(Math.max(xmax - xmin, ymax - ymin) / 7)));
    const increment = Math.max(step, 1e-4);
    let count = 0;
    for (let x = Math.ceil(xmin / increment) * increment; x <= xmax && count < 90; x += increment, count++) axes += line(p(x, ymin), p(x, ymax), 'grid');
    count = 0;
    for (let y = Math.ceil(ymin / increment) * increment; y <= ymax && count < 90; y += increment, count++) axes += line(p(xmin, y), p(xmax, y), 'grid');
    if (ymin <= 0 && ymax >= 0) axes += line(p(xmin, 0), p(xmax, 0), 'axis') + text(...p(xmax, 0), 'x');
    if (xmin <= 0 && xmax >= 0) axes += line(p(0, ymin), p(0, ymax), 'axis') + text(...p(0, ymax), 'y');
    if (xmin < 0 && xmax > 0 && ymin < 0 && ymax > 0) axes += text(ox - 14, oy + 17, 'O');
    return {p, axes, scale};
  }
  function project(point, yaw = 35, elevation = 25, scale = 34, origin = [300, 190]) {
    const a = yaw * Math.PI / 180, b = elevation * Math.PI / 180;
    const horizontal = point[0] * Math.cos(a) - point[1] * Math.sin(a);
    const depth = point[0] * Math.sin(a) + point[1] * Math.cos(a);
    return [origin[0] + horizontal * scale, origin[1] - (point[2] * Math.cos(b) - depth * Math.sin(b)) * scale];
  }
  window.LabTools = {escape, fmt, path, line, text, dot, world, project,
    polygon: (points, cls = 'area') => path(points, cls, true),
    sample: (fn, from, to, count = 120) => Array.from({length: count + 1}, (_, i) => fn(from + (to - from) * i / count))};
})();
