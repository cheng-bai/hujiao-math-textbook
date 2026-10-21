(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const clone = value => JSON.parse(JSON.stringify(value));
  const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const CACHE_KEY = 'hujiao-visual-layout-prototype-v1';
  const SCHEMA = 'hujiao-visual-layout/v1';
  const modules = {
    ellipse: {
      id: 'ellipse', title: '椭圆 · 拉绳与距离和', category: '圆锥曲线', section: 'x1-2-2', scene: 'string',
      goal: '移动笔尖，再改变焦距：什么在变，什么始终不变？',
      version: 'local-snapshot-20261019', versionLabel: '已有场景 · 固定本地快照',
      sourceHash: MODULE_DATA.hashes.ellipse, initial: {c: 3, degrees: 40},
      thumbnail: 'assets/ellipse-preview.png',
    },
    perpendicular: {
      id: 'perpendicular', title: '线面垂直 · 条件与反例', category: '空间几何', section: 'x1-3-4', scene: 'criterion',
      goal: '两条线都与它垂直，就够了吗？对比相交与平行的情形。',
      version: MODULE_DATA.perpendicular.version, versionLabel: `已有插件 · v${MODULE_DATA.perpendicular.version}`,
      sourceHash: MODULE_DATA.hashes.perpendicular, initial: clone(MODULE_DATA.perpendicular.defaultState),
      thumbnail: MODULE_DATA.perpendicular.fallback.dataUrl,
    },
  };
  const sections = {
    'x1-2-2': {
      number: '2.2', title: '椭圆', chapter: '第 2 章 / 圆锥曲线', subtitle: '从距离约束，到点的轨迹',
      lead: '先读懂定义，再让图中的点动起来。这里保留教材的概念主线，把观察与操作放在定义之后。',
      blocks: [
        {id: 'ellipse-definition', name: '椭圆定义后', html: `<h2><span class="ordinal">01</span> 椭圆的定义</h2><p>取一段绳子，把两端固定在两个定点。用笔尖将绳拉紧，顺势移动一周，笔尖画出的图形就是一个椭圆。</p><div class="definition"><small>关键概念 · 距离之和保持不变</small>平面上到两个定点的距离之和等于常数，且这个常数大于两定点间距离的点的轨迹，叫做椭圆。<div class="formula-line"><math><mrow><mi>M</mi><msub><mi>F</mi><mn>1</mn></msub><mo>+</mo><mi>M</mi><msub><mi>F</mi><mn>2</mn></msub><mo>=</mo><mn>2</mn><mi>a</mi><mo>&gt;</mo><mn>2</mn><mi>c</mi></mrow></math></div></div>`},
        {id: 'ellipse-equation', name: '标准方程后', html: `<h2><span class="ordinal">02</span> 建立坐标与标准方程</h2><p>以两个焦点所在直线为横轴，以两焦点的中点为原点建立平面直角坐标系。将距离条件转化为坐标关系，得到标准方程：</p><div class="formula-line"><math><mrow><mfrac><msup><mi>x</mi><mn>2</mn></msup><msup><mi>a</mi><mn>2</mn></msup></mfrac><mo>+</mo><mfrac><msup><mi>y</mi><mn>2</mn></msup><msup><mi>b</mi><mn>2</mn></msup></mfrac><mo>=</mo><mn>1</mn><mo>，</mo><mi>a</mi><mo>&gt;</mo><mi>b</mi><mo>&gt;</mo><mn>0</mn></mrow></math></div><p>其中 <math><mrow><msup><mi>b</mi><mn>2</mn></msup><mo>=</mo><msup><mi>a</mi><mn>2</mn></msup><mo>−</mo><msup><mi>c</mi><mn>2</mn></msup></mrow></math>。长轴不变时，焦点离得越远，椭圆就越扁。</p><p class="source-note">内容依据：选择性必修第一册 2.2。此处为编排演示的概念摘编，不替代整节教材、例题与证明。</p>`},
      ],
    },
    'x1-3-4': {
      number: '3.4', title: '空间向量的应用', chapter: '第 3 章 / 空间向量及其应用', subtitle: '看清几何条件，再转化为向量关系',
      lead: '平面的法向量把空间位置关系转化为向量关系。回看线面垂直的判定，先辨明每一个条件。',
      blocks: [
        {id: 'space-directions', name: '方向向量与法向量后', html: `<h2><span class="ordinal">01</span> 方向向量与法向量</h2><p>直线的方向向量，是与直线平行的任何非零向量。平面的法向量，是垂直于平面的任何非零向量。</p><div class="definition"><small>回看已学 · 线面垂直的判定</small>如果一条直线与一个平面内的两条相交直线都垂直，那么这条直线与该平面垂直。</div><p>“在平面内”“两条直线相交”“都垂直”，每一个条件都承担着作用。下面的交互场景可用来对比：去掉“相交”，结论还成立吗？</p>`},
        {id: 'space-relations', name: '向量判定关系后', html: `<h2><span class="ordinal">02</span> 把几何问题转成向量问题</h2><p>用向量方法解决有关直线和平面的问题，一般先把相应的问题化为关于方向向量、法向量的问题，再加以解决。</p><div class="definition"><small>关系辨析</small>直线与平面垂直，当且仅当直线的方向向量与平面的法向量平行。<br>若直线不在平面内，直线与平面平行，当且仅当直线的方向向量与平面的法向量垂直。</div><p class="source-note">内容依据：选择性必修第一册 3.4；判定定理衔接必修第三册 10.3。此处为概念摘编与编排辅助问题。</p>`},
      ],
    },
  };

  function uuid() { return crypto.randomUUID ? crypto.randomUUID() : Array.from(crypto.getRandomValues(new Uint32Array(4))).join('-'); }
  const newPlacement = (assetId, sectionId, afterBlockId) => ({instanceId: uuid(), assetId, assetVersion: modules[assetId].version, assetSha256: modules[assetId].sourceHash, sceneId: modules[assetId].scene, sectionId, afterBlockId, state: clone(modules[assetId].initial), studentVisible: true});
  const initialLayout = () => ({schema: SCHEMA, sourceBook: 'hujiao-five-books', currentSection: 'x1-2-2', placements: [newPlacement('ellipse', 'x1-2-2', 'ellipse-definition')]});
  function validState(id, state) {
    if (!state || typeof state !== 'object' || Array.isArray(state)) return false;
    if (id === 'ellipse') return Object.keys(state).sort().join(',') === 'c,degrees' && Number.isFinite(state.c) && state.c >= 0 && state.c <= 6 && Number.isFinite(state.degrees) && state.degrees >= 0 && state.degrees <= 360;
    const props = MODULE_DATA.perpendicular.parameters.properties;
    return Object.keys(state).length === Object.keys(props).length && Object.entries(props).every(([k, spec]) => {
      const value = state[k];
      if (spec.enum) return spec.enum.includes(value);
      if (spec.type === 'boolean') return typeof value === 'boolean';
      return Number.isFinite(value) && value >= spec.minimum && value <= spec.maximum;
    });
  }
  function validateLayout(data) {
    if (!data || data.schema !== SCHEMA || data.sourceBook !== 'hujiao-five-books' || !sections[data.currentSection] || !Array.isArray(data.placements) || data.placements.length > 50) throw Error('不是本小样支持的编排文件，或模块数量超过50个。');
    const ids = new Set();
    for (const item of data.placements) {
      const asset = modules[item.assetId], section = sections[item.sectionId];
      if (!asset || item.assetVersion !== asset.version || item.assetSha256 !== asset.sourceHash || item.sceneId !== asset.scene) throw Error('文件中的资源版本与本地副本不一致，未导入。');
      if (!section || !section.blocks.some(b => b.id === item.afterBlockId)) throw Error('找不到对应正文插入位置，未导入。');
      if (typeof item.instanceId !== 'string' || !/^[a-zA-Z0-9-]{1,80}$/.test(item.instanceId) || ids.has(item.instanceId) || typeof item.studentVisible !== 'boolean' || !validState(item.assetId, item.state)) throw Error('模块ID、参数或可见性数据不合法，未导入。');
      ids.add(item.instanceId);
    }
    // Project only known fields: imported text never becomes HTML or executable code.
    return {schema: SCHEMA, sourceBook: 'hujiao-five-books', currentSection: data.currentSection, placements: data.placements.map(p => ({instanceId: p.instanceId, assetId: p.assetId, assetVersion: p.assetVersion, assetSha256: p.assetSha256, sceneId: p.sceneId, sectionId: p.sectionId, afterBlockId: p.afterBlockId, state: clone(p.state), studentVisible: p.studentVisible}))};
  }
  let layout = initialLayout(), cacheAvailable = true, cacheRestored = false;
  try { const cached = localStorage.getItem(CACHE_KEY); if (cached) { layout = validateLayout(JSON.parse(cached)); cacheRestored = true; } } catch (_) { cacheAvailable = false; }
  let selectedAnchor = sections[layout.currentSection].blocks[0].id;
  let filter = 'all', mode = 'edit', previewAsset = null, toastTimer;
  const history = [], frames = new Map(), requests = new Map();
  function notify(text) { const toast = $('#toast'); toast.textContent = text; toast.classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => toast.classList.remove('show'), 3600); }
  function cache() {
    try { localStorage.setItem(CACHE_KEY, JSON.stringify(layout)); } catch (_) { cacheAvailable = false; }
    $('#save-status').textContent = cacheAvailable ? '已暂存本机 · 请导出备份' : '请导出 JSON 保存编排';
  }
  function checkpoint() { history.push(clone(layout)); if (history.length > 30) history.shift(); $('#undo').disabled = false; }
  function counts() {
    $('#total-count').textContent = layout.placements.length;
    document.querySelectorAll('[data-section]').forEach(btn => { btn.classList.toggle('active', btn.dataset.section === layout.currentSection); });
    $('#section-select').value = layout.currentSection;
    $('#section-breadcrumb').textContent = `${sections[layout.currentSection].number} ${sections[layout.currentSection].title}`;
  }
  function clearBookFrames() { for (const [token, frame] of frames) if (frame.instanceId) frames.delete(token); }
  function renderBook() {
    clearBookFrames();
    const section = sections[layout.currentSection];
    $('#paper').innerHTML = `<div class="paper-top"><span>沪教版高中数学 · 选择性必修第一册</span><span class="edition-label">概念摘编样片</span></div><div class="chapter-title"><span>${section.number}</span><div><h1>${section.title}</h1><div class="subtitle">${section.subtitle}</div></div></div><p class="paper-lead">${section.lead}</p>`;
    for (const block of section.blocks) {
      const prose = document.createElement('section'); prose.className = 'text-block'; prose.id = block.id; prose.innerHTML = block.html; $('#paper').append(prose);
      for (const placement of layout.placements.filter(p => p.sectionId === layout.currentSection && p.afterBlockId === block.id)) renderInstance(placement);
      const zone = document.createElement('div'); zone.className = 'drop-zone'; zone.dataset.anchor = block.id; zone.tabIndex = 0; zone.setAttribute('role', 'button'); zone.setAttribute('aria-label', `选定插入位置：${block.name}`); zone.innerHTML = `<span class="plus">+</span><span>${block.name} · 点击选定 / 拖到此处</span>`;
      zone.addEventListener('click', () => selectAnchor(block.id));
      zone.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectAnchor(block.id); } });
      zone.addEventListener('dragover', e => { if (mode !== 'edit') return; e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; zone.classList.add('drag-over'); });
      zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
      zone.addEventListener('drop', e => { e.preventDefault(); zone.classList.remove('drag-over'); const id = e.dataTransfer.getData('application/x-hujiao-asset'); if (modules[id] && mode === 'edit') insertAsset(id, block.id); });
      $('#paper').append(zone);
    }
    selectAnchor(selectedAnchor, false); counts(); renderLibrary();
  }
  function selectAnchor(id, showToast = true) {
    if (!sections[layout.currentSection].blocks.some(b => b.id === id)) id = sections[layout.currentSection].blocks[0].id;
    selectedAnchor = id;
    document.querySelectorAll('.drop-zone').forEach(z => { z.classList.toggle('selected', z.dataset.anchor === id); z.setAttribute('aria-pressed', String(z.dataset.anchor === id)); });
    if (showToast) notify(`已选定：${sections[layout.currentSection].blocks.find(b => b.id === id).name}`);
  }
  function renderInstance(placement) {
    const module = modules[placement.assetId], element = document.createElement('section');
    element.className = 'interactive-block'; element.id = `instance-${placement.instanceId}`; element.dataset.instance = placement.instanceId;
    element.innerHTML = `<div class="interactive-head"><span class="interactive-icon" aria-hidden="true">◇</span><h3>${module.title}</h3><small>交互场景</small><div class="interactive-tools"><button data-action="reset" aria-label="重置${module.title}的参数">重置</button><button data-action="remove" aria-label="移除${module.title}">移除</button></div></div><p class="interactive-description">${module.goal}</p><div class="frame-status" role="status">正在加载本地模型…</div><div class="frame-container"></div><div class="interactive-foot"><span>${module.versionLabel} · 参数仅属于此处</span><label><input type="checkbox" ${placement.studentVisible ? 'checked' : ''}> 标记学生可见</label></div>`;
    element.querySelector('[data-action="remove"]').addEventListener('click', async () => { const synced = await flushFrames(); if (!synced && !window.confirm('部分模块未完成状态同步。是否保留最后成功保存的参数，并移除此模块？尚未同步的调整可能丢失；移除操作仍可撤销，原资源不会删除。')) return; checkpoint(); layout.placements = layout.placements.filter(p => p.instanceId !== placement.instanceId); cache(); renderBook(); notify('已移除，可点击撤销。原资源未删除。'); });
    element.querySelector('[data-action="reset"]').addEventListener('click', async () => { if (!await flushFrames()) return notify('模块尚未同步完成，未重置。请稍候重试。'); checkpoint(); placement.state = clone(module.initial); const frame = Array.from(frames.values()).find(f => f.instanceId === placement.instanceId); if (frame) { frame.ready = false; post(frame, 'restore', {state: placement.state}); } cache(); notify('本处参数已重置，其他实例不受影响。'); });
    element.querySelector('input').addEventListener('change', e => { checkpoint(); placement.studentVisible = e.target.checked; cache(); });
    $('#paper').append(element);
    const frame = mountFrame(placement.assetId, placement.state, placement.instanceId, element.querySelector('.frame-container'), element.querySelector('.frame-status'));
    frame.element.title = module.title;
  }
  async function insertAsset(id, anchor = selectedAnchor) {
    if (mode !== 'edit') return notify('请先切换到编排模式。');
    if (layout.placements.length >= 50) return notify('小样最多保存50个模块。');
    if (!await flushFrames()) return notify('已有模块尚未同步完成，未插入新模块。请稍候重试。');
    checkpoint(); selectedAnchor = anchor;
    const placement = newPlacement(id, layout.currentSection, anchor); layout.placements.push(placement); cache(); renderBook();
    closeLibrary(); notify('已插入。可以继续操作图形，或撤销本次编排。');
    requestAnimationFrame(() => document.getElementById(`instance-${placement.instanceId}`).scrollIntoView({behavior: 'smooth', block: 'start'}));
  }
  function renderLibrary() {
    const query = $('#search').value.trim().toLowerCase();
    const visible = Object.values(modules).filter(m => (filter !== 'recommended' || m.section === layout.currentSection) && `${m.title} ${m.category} ${m.goal}`.toLowerCase().includes(query));
    $('#resource-list').innerHTML = '';
    for (const [index, module] of visible.entries()) {
      const card = document.createElement('article'); card.className = 'resource-card'; card.dataset.asset = module.id; card.draggable = true;
      card.innerHTML = `<div class="resource-image"><img src="${module.thumbnail}" alt="${module.title}的已有场景预览" draggable="false"><span class="scene-index">0${index + 1}</span><span class="drag-handle" aria-hidden="true">⠿</span></div><div class="resource-details"><div class="resource-tags"><span>${module.category}</span>${module.section === layout.currentSection ? '<span class="recommended">本节推荐</span>' : '<span>适用 ' + sections[module.section].number + '</span>'}</div><h3>${module.title}</h3><p>${module.goal}</p><div class="resource-actions"><button data-action="preview">预览</button><button class="insert-button" data-action="insert">＋ 插入</button></div><div class="resource-version">${module.versionLabel}</div></div>`;
      card.addEventListener('dragstart', e => { e.dataTransfer.setData('application/x-hujiao-asset', module.id); e.dataTransfer.setData('text/plain', module.id); e.dataTransfer.effectAllowed = 'copy'; card.classList.add('dragging'); });
      card.addEventListener('dragend', () => { card.classList.remove('dragging'); document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over')); });
      card.querySelector('[data-action="preview"]').addEventListener('click', () => preview(module.id));
      card.querySelector('[data-action="insert"]').addEventListener('click', () => insertAsset(module.id));
      $('#resource-list').append(card);
    }
    if (!visible.length) $('#resource-list').innerHTML = '<p class="empty-resources">没有匹配资源。试试“椭圆”或“垂直”。</p>';
  }
  function frameHTML(id, token) {
    const source = id === 'ellipse' ? MODULE_DATA.ellipseHtml : MODULE_DATA.perpendicular.html;
    const csp = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'";
    const embedCSS = id === 'ellipse' ? `<style>.iso-page{margin:0!important;width:100%!important;padding:8px 12px!important}.iso-page>header,.experiment,.teacher,footer{display:none!important}.iso-figure{margin:0!important}.iso-svg{max-height:300px!important}.iso-plate{padding:0!important}.iso-legend{font-size:10px!important;line-height:1.6!important}.iso-caption{display:none!important}.controls{padding:7px 0!important}.control-row{grid-template-columns:115px 1fr!important;gap:10px!important;margin:4px 0!important;font-size:11px!important}.buttons,.presets{margin-top:5px!important;gap:5px!important}button{padding:5px 9px!important;font-size:10px!important}.status{font-size:11px!important;min-height:0!important;padding:9px 0!important}.metrics>div{padding:8px 12px!important}.metrics small{font-size:9px!important;margin-bottom:3px!important}.metrics strong{font-size:18px!important}.live-math{font-size:10px!important;padding:8px 0!important}.iso-plate-corner{font-size:8px!important}#theme{display:none!important}body{background:#fffef8!important}@media(max-width:420px){.iso-svg{max-height:240px!important}.iso-plate-corner[data-corner=hint]{display:none!important}.metrics{grid-template-columns:repeat(2,1fr)!important}}</style>` : `<style>body{background:#fffef8!important;font-family:"PingFang SC","Microsoft YaHei",sans-serif!important}main{padding:8px 12px!important}.tools{font-size:11px!important;gap:7px!important}button{font-size:11px!important}</style>`;
    // A separate token and source-window check isolate each embedded instance.
    const bridge = `<script>(()=>{const token=${JSON.stringify(token)},kind=${JSON.stringify(id)};let ready=false,applying=false,timer;const send=(type,data={})=>parent.postMessage({channel:'hujiao-module',token,type,...data},'*');const api=()=>kind==='ellipse'?{getState:()=>window.__tixuApi.getState(),setState:s=>window.__tixuApi.applyState(s),pause:()=>window.__tixuApi.pause()}:window.TixuPlugin;const state=()=>JSON.parse(JSON.stringify(api().getState()));const publish=()=>{if(ready&&!applying)try{send('state',{state:state()})}catch(e){send('error',{message:e.message})}};const size=()=>{const main=document.querySelector('main');send('height',{height:Math.ceil((main?main.getBoundingClientRect().height:document.body.scrollHeight)+18)})};addEventListener('message',async e=>{const d=e.data;if(e.source!==parent||!d||d.channel!=='hujiao-module'||d.token!==token)return;try{if(d.type==='init'||d.type==='restore'){applying=true;await api().setState(d.state);await api().pause?.();applying=false;ready=true;publish();size()}if(d.type==='get-state'){await api().pause?.();send('state-response',{requestId:d.requestId,state:state()})}if(d.type==='pause'){await api().pause?.();publish()}}catch(e){applying=false;send('error',{message:e.message,requestId:d.requestId})}});for(const name of ['input','change','click','pointerup','keyup'])document.addEventListener(name,()=>{clearTimeout(timer);timer=setTimeout(publish,35)});addEventListener('tixu:state',publish);addEventListener('error',e=>send('error',{message:e.message}));addEventListener('unhandledrejection',e=>send('error',{message:String(e.reason)}));const boot=async()=>{try{await api().init?.();await api().pause?.();send('ready');new ResizeObserver(size).observe(document.body);size()}catch(e){send('error',{message:e.message})}};document.readyState==='loading'?addEventListener('DOMContentLoaded',boot,{once:true}):boot();})();<\/script>`;
    let html = source.replace(/<!doctype[^>]*>/ig, '');
    html = html.replace(/<head([^>]*)>/i, `<head$1><meta http-equiv="Content-Security-Policy" content="${csp}"><meta name="referrer" content="no-referrer">`);
    html = html.replace('</head>', embedCSS + '</head>');
    // The reused source contains HTML-generating template strings; append at the real body end.
    const end = html.lastIndexOf('</body>');
    return '<!doctype html>' + (end < 0 ? html + bridge : html.slice(0, end) + bridge + html.slice(end));
  }
  function mountFrame(id, state, instanceId, container, status) {
    const token = uuid(), element = document.createElement('iframe');
    element.setAttribute('sandbox', 'allow-scripts'); element.setAttribute('referrerpolicy', 'no-referrer'); element.title = modules[id].title; element.srcdoc = frameHTML(id, token);
    const info = {token, id, element, state: clone(state), instanceId, status, ready: false}; frames.set(token, info); container.append(element); return info;
  }
  function post(frame, type, data = {}) { frame.element.contentWindow?.postMessage({channel: 'hujiao-module', token: frame.token, type, ...data}, '*'); }
  window.addEventListener('message', event => {
    const message = event.data;
    if (!message || message.channel !== 'hujiao-module') return;
    const frame = frames.get(message.token);
    if (!frame || event.source !== frame.element.contentWindow) return;
    if (message.type === 'ready') post(frame, 'init', {state: frame.state});
    if (message.type === 'height' && Number.isFinite(message.height)) frame.element.style.height = `${Math.max(300, Math.min(1600, message.height))}px`;
    if (message.type === 'state' || message.type === 'state-response') {
      if (!validState(frame.id, message.state)) return;
      frame.ready = true;
      if (frame.status) { frame.status.textContent = '本地模型已载入'; frame.status.hidden = true; }
      frame.state = clone(message.state);
      if (frame.instanceId) { const placement = layout.placements.find(p => p.instanceId === frame.instanceId); if (placement) { placement.state = clone(message.state); cache(); } }
      const pending = requests.get(message.requestId); if (pending && pending.token === frame.token) { clearTimeout(pending.timer); pending.resolve(true); requests.delete(message.requestId); }
    }
    if (message.type === 'error') { if (frame.status) { frame.status.hidden = false; frame.status.classList.add('error'); frame.status.textContent = '模块运行问题：' + String(message.message).slice(0, 150); } }
  });
  async function flushFrames() {
    const active = Array.from(frames.values()).filter(f => f.instanceId);
    if (active.some(frame => !frame.ready)) return false;
    const results = await Promise.all(active.map(frame => new Promise(resolve => {
      const requestId = uuid(); const timer = setTimeout(() => { requests.delete(requestId); resolve(false); }, 1500);
      requests.set(requestId, {token: frame.token, resolve, timer}); post(frame, 'get-state', {requestId});
    })));
    return results.every(Boolean);
  }
  async function changeSection(id) {
    if (!sections[id] || id === layout.currentSection) return;
    if (!await flushFrames()) { counts(); return notify('当前模块尚未同步完成，仍停留在本节。请稍候重试。'); }
    layout.currentSection = id; selectedAnchor = sections[id].blocks[0].id; cache(); renderBook(); window.scrollTo({top: 0, behavior: 'smooth'});
  }
  function preview(id) {
    previewAsset = id; const module = modules[id];
    $('#preview-title').textContent = module.title; $('#preview-goal').textContent = module.goal; $('#preview-content').innerHTML = '';
    const status = document.createElement('div'); status.className = 'frame-status'; status.textContent = '正在加载已有模块…'; $('#preview-content').append(status);
    mountFrame(id, module.initial, null, $('#preview-content'), status); $('#preview-dialog').showModal();
  }
  function closePreview() { $('#preview-dialog').close(); }
  $('#preview-dialog').addEventListener('close', () => { for (const [token, frame] of frames) if (!frame.instanceId) frames.delete(token); $('#preview-content').innerHTML = ''; previewAsset = null; });
  function closeLibrary() { document.body.classList.remove('library-open'); $('#library-toggle').setAttribute('aria-expanded', 'false'); }
  function setMode(next) { mode = next; document.body.classList.toggle('read-mode', next === 'read'); $('#edit-mode').classList.toggle('active', next === 'edit'); $('#read-mode').classList.toggle('active', next === 'read'); $('#edit-mode').setAttribute('aria-pressed', String(next === 'edit')); $('#read-mode').setAttribute('aria-pressed', String(next === 'read')); closeLibrary(); }

  document.querySelectorAll('[data-section]').forEach(btn => btn.addEventListener('click', () => changeSection(btn.dataset.section)));
  $('#section-select').addEventListener('change', e => changeSection(e.target.value));
  $('#edit-mode').addEventListener('click', () => setMode('edit')); $('#read-mode').addEventListener('click', () => setMode('read'));
  $('#library-toggle').addEventListener('click', () => { const open = document.body.classList.toggle('library-open'); $('#library-toggle').setAttribute('aria-expanded', String(open)); });
  $('#library-close').addEventListener('click', closeLibrary); $('#drawer-scrim').addEventListener('click', closeLibrary);
  $('#search').addEventListener('input', renderLibrary);
  document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => { filter = button.dataset.filter; document.querySelectorAll('[data-filter]').forEach(b => { b.classList.toggle('active', b === button); b.setAttribute('aria-pressed', String(b === button)); }); renderLibrary(); }));
  $('#preview-close').addEventListener('click', closePreview);
  $('#preview-insert').addEventListener('click', () => { const id = previewAsset; closePreview(); insertAsset(id); });
  $('#undo').addEventListener('click', async () => { if (!history.length) return; if (!await flushFrames()) return notify('当前模块尚未同步完成，未撤销。请稍候重试。'); layout = history.pop(); selectedAnchor = sections[layout.currentSection].blocks[0].id; $('#undo').disabled = !history.length; cache(); renderBook(); notify('已撤销上一次编排操作。'); });
  $('#export').addEventListener('click', async () => {
    const result = await flushFrames();
    if (!result) return notify('模块状态尚未就绪，暂未导出。请稍候重试。');
    const payload = {...validateLayout(layout), exportedAt: new Date().toISOString(), note: '仅保存本小样的编排位置、固定资源版本和参数；不是完整教材或独立学生版。'};
    const blob = new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'}), url = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = url; a.download = '沪教数学-可视化编排.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); notify('编排 JSON 已导出，可在本小样中重新导入。');
  });
  $('#import').addEventListener('click', () => $('#import-file').click());
  $('#import-file').addEventListener('change', async event => {
    const file = event.target.files[0]; if (!file) return;
    try { if (file.size > 2000000) throw Error('编排文件过大。'); const incoming = validateLayout(JSON.parse(await file.text())); if (!await flushFrames()) throw Error('当前模块尚未同步完成，导入已取消。请稍候重试。'); checkpoint(); layout = incoming; selectedAnchor = sections[layout.currentSection].blocks[0].id; cache(); renderBook(); notify('已恢复编排、版本和每个实例的参数。可撤销。'); } catch (error) { notify(error.message || '导入失败，当前编排未改变。'); }
    event.target.value = '';
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) for (const frame of frames.values()) post(frame, 'pause'); });
  const observer = new IntersectionObserver(entries => { for (const entry of entries) if (!entry.isIntersecting) { const frame = Array.from(frames.values()).find(f => f.element === entry.target); if (frame) post(frame, 'pause'); } });
  const observeFrames = new MutationObserver(() => document.querySelectorAll('.interactive-block iframe').forEach(frame => observer.observe(frame)));
  observeFrames.observe($('#paper'), {childList: true, subtree: true});
  renderBook();
  if (!cacheRestored) $('#save-status').textContent = '初始示例 · 已插入1个场景';
  // Expose read-only state for local acceptance checks, never module source or DOM mutation.
  window.bookComposer = Object.freeze({getLayout: () => clone(layout), validateLayout, getFrameCount: () => frames.size});
})();
