(() => {
  'use strict';
  const spec = window.LAB_SPEC, experiment = window.TEXTBOOK_EXPERIMENTS[spec.id], L = window.LabTools;
  let state = {...spec.initial};
  const $ = selector => document.querySelector(selector);
  const controls = $('#controls');
  controls.innerHTML = spec.controls.map(control => {
    const label = L.escape(control.label), key = L.escape(control.key);
    if (control.type === 'select') return `<label>${label}<select data-key="${key}">${control.options.map(option => `<option value="${L.escape(option.value)}">${L.escape(option.label)}</option>`).join('')}</select></label>`;
    if (control.type === 'checkbox') return `<label class="check"><input data-key="${key}" type="checkbox">${label}</label>`;
    return `<label>${label}<output data-output="${key}"></output><input data-key="${key}" type="range" min="${control.min}" max="${control.max}" step="${control.step}"></label>`;
  }).join('');
  function render() {
    const result = experiment.render({...state}, L);
    $('#diagram').innerHTML = result.svg;
    $('#metrics').innerHTML = (result.metrics || []).map(([label, value]) => `<div><small>${L.escape(label)}</small><strong>${L.escape(value)}</strong></div>`).join('');
    $('#note').textContent = result.note || '';
    for (const control of spec.controls) {
      const input = controls.querySelector(`[data-key="${control.key}"]`);
      if (control.type === 'checkbox') input.checked = state[control.key];
      else input.value = state[control.key];
      const output = controls.querySelector(`[data-output="${control.key}"]`);
      if (output) output.textContent = L.fmt(state[control.key], 4);
    }
    window.__textbookLab = {id: spec.id, state: {...state}, model: experiment.model({...state})};
  }
  controls.addEventListener('input', event => {
    const input = event.target, control = spec.controls.find(item => item.key === input.dataset.key);
    if (!control) return;
    state[control.key] = control.type === 'checkbox' ? input.checked
      : control.type === 'select' ? control.options.find(option => String(option.value) === input.value).value : Number(input.value);
    render();
  });
  $('#reset').addEventListener('click', () => {state = {...spec.initial}; render();});
  function validState(next) {
    return next && typeof next === 'object' && Object.keys(next).length === spec.controls.length && spec.controls.every(c => {
      const value = next[c.key];
      return c.type === 'checkbox' ? typeof value === 'boolean' : c.type === 'select'
        ? c.options.some(option => option.value === value) : Number.isFinite(value) && value >= c.min && value <= c.max && Math.abs((value-c.min)/c.step-Math.round((value-c.min)/c.step)) < 1e-7;
    });
  }
  function restoreScene() {
    const hash = new URLSearchParams(location.hash.slice(1)), scene = hash.get('scene'), encoded = hash.get('state');
    if (!scene && !encoded) return;
    state = {...spec.initial};
    try {
      if (scene && scene !== 'explore') throw Error('未知场景');
      if (encoded) {
        const overlay = JSON.parse(encoded);
        if (!overlay || typeof overlay !== 'object' || Array.isArray(overlay) || Object.keys(overlay).some(key => !['math', 'view', 'lesson'].includes(key))) throw Error('状态分组不合法');
        const next = {...spec.initial};
        for (const [group, values] of Object.entries(overlay)) {
          if (!values || typeof values !== 'object' || Array.isArray(values)) throw Error('状态分组不合法');
          for (const [key, value] of Object.entries(values)) {
            if (!spec.stateKeys[group].includes(key)) throw Error('未知或错组参数');
            next[key] = value;
          }
        }
        if (!validState(next)) throw Error('参数超出范围');
        state = next;
      }
      render();
    } catch (error) {
      state = {...spec.initial}; render();
      $('#note').textContent = error.message + '，已恢复默认探索状态。' + $('#note').textContent;
    }
  }
  addEventListener('hashchange', restoreScene);
  window.TixuPlugin = {
    getState: () => ({...state}),
    setState: next => {if (!validState(next)) throw Error('模块参数超出定义范围'); state = {...next}; render();},
    pause: () => {},
  };
  render();
  restoreScene();
})();
