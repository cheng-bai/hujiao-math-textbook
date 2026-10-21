(() => {
  'use strict';
  if (!window.VISUAL_MANIFEST || document.documentElement.dataset.visualReady === 'true') return;

  const TEACHER = document.documentElement.dataset.mode !== 'student';
  const MANIFEST = window.VISUAL_MANIFEST;
  const BOOK = MANIFEST.sourceBook;
  const STORAGE_KEY = 'hujiao-x1-visual-layout-v1' + (BOOK === 'x1' ? '' : ':' + BOOK);
  const SCHEMA = `hujiao-${BOOK}-visual-layout/v1`;
  const DATA = window.MODULE_DATA;
  const pluginScript = [...document.scripts].find(script => script.src.includes('visual-book.js'));
  const visualAssetBase = pluginScript ? new URL('visual-assets/', pluginScript.src).href : '';
  const clone = value => JSON.parse(JSON.stringify(value));
  const escapeHTML = value => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const modules = DATA ? {
    ellipse: {
      id: 'ellipse', title: '椭圆 · 拉绳与距离和', category: '圆锥曲线', sections: ['x1-2-2'],
      scene: 'string', version: 'local-snapshot-20261019', hash: DATA.hashes.ellipse,
      goal: '改变焦距并移动笔尖：两段长度在变，距离和始终保持不变。',
      html: DATA.ellipseHtml, initial: {c: 3, degrees: 40},
      thumbnail: visualAssetBase + 'ellipse-preview.png',
    },
    perpendicular: {
      id: 'perpendicular', title: '线面垂直 · 条件与反例', category: '空间几何', sections: ['x1-3-4'],
      scene: 'criterion', version: DATA.perpendicular.version, hash: DATA.hashes.perpendicular,
      goal: '比较相交直线与平行直线，辨析线面垂直判定中的必要条件。',
      html: DATA.perpendicular.html, initial: clone(DATA.perpendicular.defaultState),
      thumbnail: DATA.perpendicular.fallback.dataUrl,
    },
  } : {};
  for (const lab of window.CONIC_LAB_CATALOG || []) {
    modules[lab.id] = {...lab, html: window.CONIC_LAB_HTML?.[lab.id],
      thumbnail: visualAssetBase + `conic-${lab.kind}-preview.svg`};
  }
  for (const lab of window.TEXTBOOK_LAB_CATALOG || []) {
    modules[lab.id] = {...lab, html: window.TEXTBOOK_LAB_HTML?.[lab.id],
      thumbnail: visualAssetBase + lab.preview};
  }
  for (const item of window.TEXTBOOK_EXISTING || []) {
    if (modules[item.assetId]) Object.assign(modules[item.assetId], item);
  }
  const bundleKeys = module => module.placements?.length
    ? module.placements.map(placement => `${module.id}@${placement.sectionId}`)
    : module.defaultAfter ? [module.id] : [];
  const bundledIds = Object.values(modules).flatMap(bundleKeys);
  const moduleIds = Object.keys(modules);
  const ids = Object.keys(modules);
  const pageModule = document.querySelector('.book-body');
  const sectionId = document.documentElement.dataset.sectionId || pageModule?.querySelector('.content-module')?.dataset.module || '';
  const sectionInfo = MANIFEST.sections[sectionId];
  if (!sectionInfo) return;

  function validState(id, state) {
    if (!state || typeof state !== 'object' || Array.isArray(state)) return false;
    if (id === 'ellipse') return Object.keys(state).sort().join(',') === 'c,degrees'
      && Number.isFinite(state.c) && state.c >= 0 && state.c <= 6
      && Number.isFinite(state.degrees) && state.degrees >= 0 && state.degrees <= 360;
    const properties = modules[id]?.parameters || DATA.perpendicular.parameters.properties;
    return Object.keys(state).length === Object.keys(properties).length && Object.entries(properties).every(([key, rule]) => {
      const value = state[key];
      if (rule.enum) return rule.enum.includes(value);
      if (rule.type === 'boolean') return typeof value === 'boolean';
      return Number.isFinite(value) && value >= rule.minimum && value <= rule.maximum && (!rule.step || Math.abs((value-rule.minimum)/rule.step-Math.round((value-rule.minimum)/rule.step)) < 1e-7);
    });
  }
  function validate(data) {
    if (!data || data.schema !== SCHEMA || data.sourceBook !== BOOK || !Array.isArray(data.placements) || data.placements.length > 100) throw Error('文件格式或册次不匹配，未导入。');
    const seen = new Set();
    const placements = data.placements.map(item => {
      const module = modules[item.assetId];
      const page = MANIFEST.sections[item.sectionId];
      if (!module || !page || !module.sections.includes(item.sectionId)
        || item.assetVersion !== module.version || item.assetSha256 !== module.hash || item.sceneId !== module.scene) throw Error('资源与本地固定版本不匹配，未导入。');
      if (!page.anchors.includes(item.afterBlockId)) throw Error('插入位置不属于选定章节，未导入。');
      if (typeof item.instanceId !== 'string' || !/^[a-zA-Z0-9-]{1,80}$/.test(item.instanceId)
        || seen.has(item.instanceId) || typeof item.studentVisible !== 'boolean' || !validState(item.assetId, item.state)) throw Error('实例ID、参数或可见性数据不合法，未导入。');
      seen.add(item.instanceId);
      return {instanceId: item.instanceId, assetId: item.assetId, assetVersion: item.assetVersion, assetSha256: item.assetSha256,
        sceneId: item.sceneId, sectionId: item.sectionId, afterBlockId: item.afterBlockId, state: clone(item.state), studentVisible: item.studentVisible};
    });
    const bundledDefaults = data.bundledDefaults || [];
    // Accept legacy module-only seed markers while preserving old user-edited layouts.
    if (!Array.isArray(bundledDefaults) || bundledDefaults.some(id => !bundledIds.includes(id) && !moduleIds.includes(id))) throw Error('内置模块配置标记不合法。');
    return {schema: SCHEMA, sourceBook: BOOK, placements, bundledDefaults: [...new Set(bundledDefaults)]};
  }
  function uuid() { return crypto.randomUUID ? crypto.randomUUID() : Array.from(crypto.getRandomValues(new Uint32Array(4))).join('-'); }
  function makePlacement(assetId, anchor) {
    const module = modules[assetId];
    return {instanceId: uuid(), assetId, assetVersion: module.version, assetSha256: module.hash, sceneId: module.scene,
      sectionId, afterBlockId: anchor, state: clone(module.initial), studentVisible: true};
  }
  function loadLayout() {
    let saved;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      saved = raw ? validate(JSON.parse(raw)) : null;
    } catch (_) {
      saved = null;
    }
    saved ||= {schema: SCHEMA, sourceBook: BOOK, placements: [], bundledDefaults: []};
    // Seed once per asset, keeping existing placements and respecting later removals.
    for (const module of Object.values(modules)) {
      const defaults = module.placements?.length ? module.placements
        : module.defaultAfter ? [{sectionId: module.sections[0], afterBlockId: module.defaultAfter}] : [];
      if (!defaults.length) continue;
      if (module.placements?.length && saved.bundledDefaults.includes(module.id)) continue;
      for (const [index, placement] of defaults.entries()) {
        const seedKey = module.placements?.length ? `${module.id}@${placement.sectionId}` : module.id;
        if (saved.bundledDefaults.includes(seedKey)) continue;
        if (!saved.placements.some(item => item.assetId === module.id && item.sectionId === placement.sectionId) && saved.placements.length < 100) {
          saved.placements.push({...makePlacement(module.id, placement.afterBlockId), sectionId: placement.sectionId, instanceId: 'bundled-' + module.id + '-' + placement.sectionId + (index ? '-' + index : '')});
        }
        saved.bundledDefaults.push(seedKey);
      }
    }
    return saved;
  }
  let layout = loadLayout();
  let selectedAnchor = '';
  let toastTimer, saveTimer;
  const frames = new Map(), requests = new Map(), history = [];
  // Offscreen iframes can throttle their own resize observers; measure from the host too.
  const frameWidths = new ResizeObserver(entries => {
    for (const entry of entries) {
      const info = [...frames.values()].find(frame => frame.element === entry.target);
      if (info && info.width !== entry.contentRect.width) {
        info.width = entry.contentRect.width;
        post(info, 'measure');
      }
    }
  });
  const frameVisibility = new IntersectionObserver(entries => {
    for (const entry of entries) {
      const info = [...frames.values()].find(frame => frame.element === entry.target);
      if (info && entry.isIntersecting) post(info, 'measure');
    }
  });
  const drawer = document.createElement('aside');
  drawer.id = 'visual-drawer'; drawer.className = 'visual-drawer';
  drawer.setAttribute('aria-label', '教材可视化资源与编排');
  drawer.setAttribute('aria-hidden', 'true');
  drawer.innerHTML = `<div class="visual-drawer-head"><div><small>${escapeHTML(BOOK.toUpperCase())} · LOCAL ASSETS</small><h2>${TEACHER ? '可视化模块编排' : '已选可视化模块'}</h2></div><button type="button" id="visual-close" aria-label="关闭可视化资源">×</button></div>
    <p>${TEACHER ? '拖动资源卡到正文的标题、知识段或题目上；也可选定插入位置后点击“插入”。内容与答案原文不改写，配置单独保存。' : '交互模块由教师编排。若没有显示，请导入教师导出的可视化编排 JSON。'}</p>
    <label class="visual-anchor-label" id="visual-anchor-wrap">插入到正文位置<select id="visual-anchor"></select></label>
    <div class="visual-toolbar-actions"><button type="button" id="visual-undo" ${TEACHER ? '' : 'hidden'} disabled>撤销上次编排</button><button type="button" id="visual-export" ${TEACHER ? '' : 'hidden'}>导出全册配置 JSON</button><button type="button" id="visual-import">导入编排 JSON</button><input id="visual-import-file" type="file" accept="application/json,.json" hidden></div>
    <p id="visual-config-status" role="status" aria-live="polite"></p><div id="visual-resource-list"></div>`;
  document.body.append(drawer);
  const $ = selector => drawer.querySelector(selector);

  function announce(message) {
    const status = $('#visual-config-status');
    status.textContent = message;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { if (status.textContent === message) status.textContent = ''; }, 4500);
  }
  let unsavedFrameState = false, storageConflict = false;
  function persist() {
    if (!TEACHER) return;
    if (storageConflict) return announce('检测到另一页面的编排冲突，本页自动保存已暂停；请先导出本页配置，再刷新或导入选定版本。');
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
      unsavedFrameState = false;
      announce('已暂存本浏览器；要跨设备或交给学生，请导出 JSON。');
    }
    catch (_) { announce('本机暂存不可用，请导出 JSON 备份。'); }
  }
  function persistSoon() {
    if (!TEACHER) return;
    clearTimeout(saveTimer);
    saveTimer = setTimeout(persist, 250);
  }
  function checkpoint() {
    history.push(clone(layout));
    if (history.length > 30) history.shift();
    $('#visual-undo').disabled = false;
  }
  function getAnchor(id) {
    const element = document.getElementById(id);
    return element && pageModule.contains(element) && sectionInfo.anchors.includes(id) ? element : null;
  }
  function anchorLabel(element) {
    let label = element.matches('.section-heading') ? element.querySelector('h2')?.textContent
      : element.matches('.question') ? element.querySelector('.question-label')?.textContent
        : element.matches('.prose') ? element.innerText
          : element.textContent;
    label = (label || element.id).replace(/\s+/g, ' ').trim();
    return label.length > 64 ? label.slice(0, 61) + '…' : label;
  }
  function initializeAnchorSelect() {
    const available = sectionInfo.anchors.map(id => getAnchor(id)).filter(Boolean);
    $('#visual-anchor').innerHTML = available.map((el, index) => `<option value="${escapeHTML(el.id)}">${index + 1}. ${escapeHTML(anchorLabel(el))}</option>`).join('');
    selectedAnchor = available.find(el => el.matches('.prose'))?.id || available[0]?.id || '';
    $('#visual-anchor').value = selectedAnchor;
    $('#visual-anchor-wrap').hidden = !TEACHER || !available.length;
  }
  function compatibleModules() { return ids.map(id => modules[id]).filter(module => module.sections.includes(sectionId)); }
  function assetLabel(module) {
    return module.kind ? '已有概念实验室 · 固定本地副本'
      : module.version === 'local-snapshot-20261019' ? '已有场景 · 固定本地快照' : '已有插件 · v' + module.version;
  }
  function renderLibrary() {
    const resources = $('#visual-resource-list');
    if (!TEACHER) {
      const placements = layout.placements.filter(item => item.sectionId === sectionId && item.studentVisible);
      resources.innerHTML = placements.length
        ? `<div class="visual-empty">此节已载入 ${placements.length} 个学生可见模块。参数更改只在本页临时生效。</div>`
        : '<div class="visual-empty">本节尚无学生可见模块。请教师先导出此册配置，并在本页导入 JSON。</div>';
      return;
    }
    const available = compatibleModules();
    resources.innerHTML = available.length ? available.map(module => `<article class="visual-card" draggable="true" data-asset="${module.id}">
      <img src="${module.thumbnail}" alt="${escapeHTML(module.title)} 静态预览" draggable="false"><div><h3>${escapeHTML(module.title)}</h3><p>${escapeHTML(module.goal)}</p>
      <button type="button" data-action="preview">预览</button> <button type="button" data-action="insert">＋ 插入</button><small>${assetLabel(module)}</small></div></article>`).join('')
      : '<div class="visual-empty">当前节没有已接入的可视化资产。简单定义、直接代入和重复总结不强行添加动态图。</div>';
    resources.querySelectorAll('.visual-card').forEach(card => {
      const id = card.dataset.asset;
      card.addEventListener('dragstart', event => { event.dataTransfer.setData('application/x-hujiao-x1-visual', id); event.dataTransfer.effectAllowed = 'copy'; });
      card.querySelector('[data-action="insert"]').addEventListener('click', () => insert(id, $('#visual-anchor').value));
      card.querySelector('[data-action="preview"]').addEventListener('click', () => preview(id));
    });
  }
  function frameHTML(id, token) {
    const source = modules[id].html;
    const csp = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'";
    const compactCSS = id === 'ellipse' ? `<style>.iso-page{margin:0!important;width:100%!important;padding:8px 12px!important}.iso-page>header,.experiment,.teacher,footer{display:none!important}.iso-figure{margin:0!important}.iso-svg{max-height:300px!important}.iso-plate{padding:0!important}.iso-legend{font-size:10px!important;line-height:1.6!important}.iso-caption{display:none!important}.controls{padding:7px 0!important}.control-row{grid-template-columns:115px 1fr!important;gap:10px!important;margin:4px 0!important;font-size:11px!important}.buttons,.presets{margin-top:5px!important;gap:5px!important}button{padding:5px 9px!important;font-size:10px!important}.status{font-size:11px!important;min-height:0!important;padding:9px 0!important}.metrics>div{padding:8px 12px!important}.metrics small{font-size:9px!important;margin-bottom:3px!important}.metrics strong{font-size:18px!important}.live-math{font-size:10px!important;padding:8px 0!important}.iso-plate-corner{font-size:8px!important}#theme{display:none!important}body{background:#fffef8!important}@media(max-width:420px){.iso-svg{max-height:240px!important}.iso-plate-corner[data-corner=hint]{display:none!important}.metrics{grid-template-columns:repeat(2,1fr)!important}}</style>` : '<style>body{background:#fffef8!important;font-family:"PingFang SC","Microsoft YaHei",sans-serif!important}main{padding:8px 12px!important}.tools{font-size:11px!important;gap:7px!important}button{font-size:11px!important}</style>';
    const bridge = `<script>(()=>{const token=${JSON.stringify(token)},kind=${JSON.stringify(id)};let ready=false,applying=false,timer;const send=(type,data={})=>parent.postMessage({channel:'hujiao-module',token,type,...data},'*');const api=()=>kind==='ellipse'?{getState:()=>window.__tixuApi.getState(),setState:s=>window.__tixuApi.applyState(s),pause:()=>window.__tixuApi.pause()}:window.TixuPlugin;const state=()=>JSON.parse(JSON.stringify(api().getState()));const publish=()=>{if(ready&&!applying)try{send('state',{state:state()})}catch(e){send('error',{message:e.message})}};const size=()=>{const main=document.querySelector('main');send('height',{height:Math.ceil((main?main.getBoundingClientRect().height:document.body.scrollHeight)+18)})};addEventListener('message',async e=>{const d=e.data;if(e.source!==parent||!d||d.channel!=='hujiao-module'||d.token!==token)return;try{if(d.type==='init'||d.type==='restore'){applying=true;await api().setState(d.state);await api().pause?.();applying=false;ready=true;publish();size()}if(d.type==='measure')size();if(d.type==='get-state'){await api().pause?.();send('state-response',{requestId:d.requestId,state:state()})}if(d.type==='pause'){await api().pause?.();publish()}}catch(e){applying=false;send('error',{message:e.message,requestId:d.requestId})}});for(const name of ['input','change','click','pointerup','keyup'])document.addEventListener(name,()=>{if(!ready||applying)return;send('dirty');clearTimeout(timer);timer=setTimeout(publish,35)});addEventListener('tixu:state',publish);addEventListener('error',e=>send('error',{message:e.message}));addEventListener('unhandledrejection',e=>send('error',{message:String(e.reason)}));const boot=async()=>{try{await api().init?.();await api().pause?.();send('ready');const resize=new ResizeObserver(size);resize.observe(document.body);const main=document.querySelector('main');if(main)resize.observe(main);addEventListener('resize',size);document.fonts?.ready.then(size);size()}catch(e){send('error',{message:e.message})}};document.readyState==='loading'?addEventListener('DOMContentLoaded',boot,{once:true}):boot();})();<\/script>`;
    let html = source.replace(/<!doctype[^>]*>/ig, '');
    html = html.replace(/<head([^>]*)>/i, `<head$1><meta http-equiv="Content-Security-Policy" content="${csp}"><meta name="referrer" content="no-referrer">`);
    html = html.replace('</head>', compactCSS + '</head>');
    const end = html.lastIndexOf('</body>');
    return '<!doctype html>' + (end < 0 ? html + bridge : html.slice(0, end) + bridge + html.slice(end));
  }
  function mountFrame(id, state, instanceId, target, status) {
    const token = uuid(), frame = document.createElement('iframe');
    frame.setAttribute('sandbox', 'allow-scripts'); frame.setAttribute('referrerpolicy', 'no-referrer'); frame.title = modules[id].title;
    frame.srcdoc = frameHTML(id, token);
    const info = {token, id, element: frame, state: clone(state), instanceId, status, ready: false, dirtyGeneration: 0};
    frames.set(token, info); target.append(frame);
    frameWidths.observe(frame); frameVisibility.observe(frame);
    return info;
  }
  function post(frame, type, data = {}) { frame.element.contentWindow?.postMessage({channel: 'hujiao-module', token: frame.token, type, ...data}, '*'); }
  function clearFrames() { frameWidths.disconnect(); frameVisibility.disconnect(); frames.clear(); }
  function createInstance(item) {
    const module = modules[item.assetId];
    const block = document.createElement('section');
    block.className = 'visual-module visual-block'; block.dataset.instance = item.instanceId; block.dataset.title = module.title; block.dataset.thumbnail = module.thumbnail; block.setAttribute('aria-busy', 'true');
    block.innerHTML = `<header class="visual-block-head"><span aria-hidden="true">◇</span><strong>${escapeHTML(module.title)}</strong><small>交互场景 · 参数仅属于此处</small>${TEACHER ? '<button type="button" data-action="reset">重置</button><button type="button" data-action="remove">移除</button>' : ''}</header>
      <p class="visual-block-intro">${escapeHTML(module.goal)}</p><div class="visual-frame-status" role="status">正在载入本地模型…</div><div class="visual-frame-container"></div>
      <footer class="visual-block-foot"><span>${assetLabel(module)}</span>${TEACHER ? `<label><input type="checkbox" data-action="student-visible" ${item.studentVisible ? 'checked' : ''}> 学生页显示</label>` : '<span>学生阅读版交互内容</span>'}</footer>`;
    block.querySelector('[data-action="remove"]')?.addEventListener('click', async () => {
      const synced = await flushFrames();
      if (!synced && !window.confirm('有模块未同步完成。是否保留最后成功保存的参数并移除此模块？尚未同步的调整可能丢失；可撤销。')) return;
      checkpoint(); layout.placements = layout.placements.filter(p => p.instanceId !== item.instanceId); persist(); renderCurrent();
    });
    block.querySelector('[data-action="reset"]')?.addEventListener('click', async () => {
      if (!await flushFrames()) return announce('模块状态尚未同步，未重置。请稍后重试。');
      checkpoint(); item.state = clone(module.initial); const frame = [...frames.values()].find(value => value.instanceId === item.instanceId);
      if (frame) { frame.ready = false; post(frame, 'restore', {state: item.state}); }
      persist(); announce('当前实例参数已重置。');
    });
    block.querySelector('[data-action="student-visible"]')?.addEventListener('change', event => {
      checkpoint(); item.studentVisible = event.target.checked; persist();
    });
    const status = block.querySelector('.visual-frame-status');
    mountFrame(item.assetId, item.state, item.instanceId, block.querySelector('.visual-frame-container'), status);
    block.setAttribute('aria-busy', 'false');
    return block;
  }
  function renderCurrent() {
    document.querySelectorAll('.visual-preview-dialog[open]').forEach(dialog => dialog.close());
    clearFrames();
    document.querySelectorAll('.visual-block').forEach(node => node.remove());
    document.querySelectorAll('.prose.visual-condensed').forEach(node => {
      const original = node.querySelector(':scope > .visual-original > .visual-original-body');
      if (original) node.replaceChildren(...original.childNodes);
      node.classList.remove('visual-condensed');
    });
    const placements = layout.placements.filter(item => item.sectionId === sectionId && (TEACHER || item.studentVisible));
    const anchors = new Map();
    placements.forEach(item => {
      const anchor = getAnchor(item.afterBlockId);
      if (!anchor) return;
      const module = modules[item.assetId];
      // Fold only the author-audited prose placement; custom drag placements never hide unrelated text.
      const audited = module.placements?.some(p => p.sectionId === sectionId && p.afterBlockId === anchor.id && !p.retainProse && p.sourceSha256 === anchor.dataset.visualSourceSha);
      if (module.summary && audited && anchor.matches('.prose:not(.visual-condensed)')) {
        const details = document.createElement('details'); details.className = 'visual-original';
        const label = document.createElement('summary'); label.textContent = '展开原文解释与完整推导（打印保留）';
        const body = document.createElement('div'); body.className = 'visual-original-body';
        body.append(...anchor.childNodes); details.append(label, body);
        const summary = document.createElement('p'); summary.className = 'visual-reading-summary'; summary.textContent = module.summary;
        const keypoints = [...body.querySelectorAll('.key-point, .definition')].filter(node => !node.parentElement.closest('.key-point, .definition')).map(node => node.cloneNode(true));
        keypoints.forEach(node => {node.removeAttribute('id'); node.querySelectorAll('[id]').forEach(el => el.removeAttribute('id'));});
        const formula = document.createElement('div'); formula.className = 'visual-reading-formula';
        if (module.formula) formula.innerHTML = module.formula;
        anchor.replaceChildren(summary, ...keypoints, ...(module.formula ? [formula] : []), details); anchor.classList.add('visual-condensed');
      }
      const placementBlock = createInstance(item);
      const previous = anchors.get(item.afterBlockId) || anchor;
      previous.insertAdjacentElement('afterend', placementBlock);
      anchors.set(item.afterBlockId, placementBlock);
    });
    $('#visual-undo').disabled = !history.length;
    renderLibrary();
  }
  function renderAnchorOptions() {
    initializeAnchorSelect();
  }
  async function flushFrames({suppressPersist = false} = {}) {
    const active = [...frames.values()].filter(frame => frame.instanceId);
    if (active.some(frame => !frame.ready)) return false;
    const results = await Promise.all(active.map(frame => new Promise(resolve => {
      const requestId = uuid();
      const timer = setTimeout(() => { requests.delete(requestId); resolve(false); }, 1500);
      requests.set(requestId, {token: frame.token, resolve, timer, dirtyGeneration: frame.dirtyGeneration, suppressPersist});
      post(frame, 'get-state', {requestId});
    })));
    return results.every(Boolean);
  }
  function targetFromEvent(event) {
    const target = event.target.closest('[id]');
    return target && pageModule.contains(target) && sectionInfo.anchors.includes(target.id) ? target : null;
  }
  async function insert(assetId, anchorId) {
    if (!TEACHER || !modules[assetId]?.sections.includes(sectionId)) return;
    if (!getAnchor(anchorId)) return announce('请先选择本节的正文插入位置。');
    if (layout.placements.length >= 100) return announce('每册最多编排100个可视化实例。');
    if (!await flushFrames()) return announce('当前模块尚未同步，未插入新模块。请稍后重试。');
    checkpoint(); layout.placements.push(makePlacement(assetId, anchorId)); persist(); renderCurrent();
    announce('可视化模块已插入。');
  }
  function openDrawer() {
    renderAnchorOptions(); renderLibrary();
    drawer.classList.add('open'); drawer.setAttribute('aria-hidden', 'false');
    $('#visual-close').focus();
  }
  function closeDrawer() {
    drawer.classList.remove('open'); drawer.setAttribute('aria-hidden', 'true');
    document.querySelector('#visual-open')?.focus({preventScroll: true});
  }
  function preview(assetId) {
    const module = modules[assetId];
    const dialog = document.createElement('dialog'); dialog.className = 'visual-preview-dialog';
    dialog.innerHTML = `<header><div><small>本地交互资源预览</small><h2>${escapeHTML(module.title)}</h2><p>${escapeHTML(module.goal)}</p></div><button type="button" aria-label="关闭预览">×</button></header><div class="visual-preview-frame"></div>`;
    document.body.append(dialog);
    const status = document.createElement('div'); status.className = 'visual-frame-status'; status.textContent = '正在载入本地模型…';
    dialog.querySelector('.visual-preview-frame').append(status);
    const info = mountFrame(assetId, module.initial, null, dialog.querySelector('.visual-preview-frame'), status);
    dialog.querySelector('button').addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => { frameWidths.unobserve(info.element); frameVisibility.unobserve(info.element); frames.delete(info.token); dialog.remove(); });
    dialog.showModal();
  }
  async function exportConfig() {
    if (!await flushFrames()) return announce('当前模块参数尚未同步，未导出。请稍后重试。');
    const payload = {...validate(layout), exportedAt: new Date().toISOString(), note: '只包含本册的模块位置、固定资源版本、参数和学生页可见标记；不含教材正文、答案、教师批注或模块源代码。'};
    const blob = new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = '沪教-' + BOOK + '-可视化编排.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    announce('已导出全册配置 JSON。可导入另一章节或学生阅读包。');
  }
  async function importConfig(file) {
    if (!file) return;
    try {
      if (file.size > 2000000) throw Error('编排文件超过2 MB。');
      const incoming = validate(JSON.parse(await file.text()));
      if (TEACHER) {
        const synced = await flushFrames();
        if (!synced && !window.confirm('当前模块有参数尚未同步。继续导入会保留最后成功状态并替换全册配置；可撤销。')) return;
        checkpoint();
      }
      storageConflict = false;
      layout = {...incoming, bundledDefaults: [...bundledIds]}; persist(); renderCurrent();
      announce(TEACHER ? '已恢复全册模块位置、参数与学生可见设置。' : '已导入教师编排；仅显示标记为学生可见的模块。');
    } catch (error) { announce(error.message || '导入失败，当前配置未改变。'); }
    finally { $('#visual-import-file').value = ''; }
  }
  function undo() {
    if (!history.length) return;
    flushFrames().then(synced => {
      if (!synced) return announce('当前模块尚未同步，未撤销。');
      layout = history.pop(); persist(); renderCurrent(); announce('已撤销上一次可视化编排更改。');
    });
  }

  window.addEventListener('message', event => {
    const message = event.data;
    if (!message || message.channel !== 'hujiao-module') return;
    const frame = frames.get(message.token);
    if (!frame || event.source !== frame.element.contentWindow) return;
    if (message.type === 'ready') post(frame, 'init', {state: frame.state});
    if (message.type === 'dirty' && frame.instanceId) frame.dirtyGeneration++;
    if (message.type === 'height' && Number.isFinite(message.height)) frame.element.style.height = `${Math.max(280, Math.min(5000, message.height))}px`;
    if (message.type === 'state' || message.type === 'state-response') {
      if (!validState(frame.id, message.state)) return;
      const pending = requests.get(message.requestId);
      frame.ready = true; frame.state = clone(message.state);
      if (frame.status) { frame.status.hidden = true; frame.status.classList.remove('error'); }
      if (frame.instanceId) {
        const placement = layout.placements.find(item => item.instanceId === frame.instanceId);
        if (placement) {
          const changed = JSON.stringify(placement.state) !== JSON.stringify(message.state);
          const interactionDuringSync = message.type === 'state-response' && pending?.dirtyGeneration !== frame.dirtyGeneration;
          placement.state = clone(message.state);
          if (changed || interactionDuringSync) unsavedFrameState = true;
          if ((changed || interactionDuringSync) && !pending?.suppressPersist) persistSoon();
        }
      }
      if (pending && pending.token === frame.token) { clearTimeout(pending.timer); pending.resolve(true); requests.delete(message.requestId); }
    }
    if (message.type === 'error' && frame.status) {
      frame.status.hidden = false; frame.status.classList.add('error'); frame.status.textContent = '模块运行问题：' + String(message.message).slice(0, 140);
    }
  });
  pageModule.addEventListener('dragover', event => {
    if (!TEACHER || !drawer.classList.contains('open') || !event.dataTransfer.types.includes('application/x-hujiao-x1-visual')) return;
    const target = targetFromEvent(event);
    if (!target) return;
    event.preventDefault(); event.dataTransfer.dropEffect = 'copy'; target.classList.add('visual-target-active');
  });
  pageModule.addEventListener('dragleave', event => {
    const target = targetFromEvent(event); if (target && !target.contains(event.relatedTarget)) target.classList.remove('visual-target-active');
  });
  pageModule.addEventListener('drop', event => {
    const target = targetFromEvent(event); pageModule.querySelectorAll('.visual-target-active').forEach(el => el.classList.remove('visual-target-active'));
    if (!target || !TEACHER) return;
    const assetId = event.dataTransfer.getData('application/x-hujiao-x1-visual');
    if (!modules[assetId]?.sections.includes(sectionId)) return;
    event.preventDefault(); $('#visual-anchor').value = target.id; selectedAnchor = target.id; insert(assetId, target.id);
  });
  pageModule.addEventListener('pointerover', event => {
    const target = targetFromEvent(event); if (target && drawer.classList.contains('open')) target.classList.add('visual-target-active');
  });
  pageModule.addEventListener('pointerout', event => {
    const target = targetFromEvent(event); if (target && !target.contains(event.relatedTarget)) target.classList.remove('visual-target-active');
  });
  document.querySelector('#visual-open')?.addEventListener('click', openDrawer);
  $('#visual-close').addEventListener('click', closeDrawer);
  $('#visual-undo').addEventListener('click', undo);
  $('#visual-export').addEventListener('click', exportConfig);
  $('#visual-import').addEventListener('click', () => $('#visual-import-file').click());
  $('#visual-import-file').addEventListener('change', event => importConfig(event.target.files[0]));
  $('#visual-anchor').addEventListener('change', event => { selectedAnchor = event.target.value; });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && drawer.classList.contains('open')) closeDrawer(); });
  document.addEventListener('visibilitychange', () => { if (document.hidden) frames.forEach(frame => post(frame, 'pause')); });
  let resizeFrame = 0;
  window.addEventListener('resize', () => {
    if (resizeFrame) return;
    resizeFrame = requestAnimationFrame(() => {
      resizeFrame = 0;
      frames.forEach(frame => post(frame, 'measure'));
    });
  });
  window.addEventListener('storage', async event => {
    if (event.key !== STORAGE_KEY || !event.newValue || !TEACHER) return;
    try {
      const incoming = validate(JSON.parse(event.newValue));
      storageConflict = true;
      clearTimeout(saveTimer);
      if (!await flushFrames({suppressPersist: true})) {
        announce('另一页面有编排更新，但本页模块尚未同步；已暂停本页自动保存以避免覆盖外页。请先导出本页配置，再刷新或导入选定版本。');
        return;
      }
      if (unsavedFrameState) {
        storageConflict = true;
        announce('另一页面有编排更新；本页模块参数与其冲突，未覆盖本页且已暂停自动保存。请先导出本页配置，再刷新或导入选定版本。');
        return;
      }
      layout = incoming;
      storageConflict = false;
      renderCurrent();
      announce('已同步本册其他页面保存的编排。');
    } catch (_) { /* Ignore incompatible older data. */ }
  });

  renderAnchorOptions();
  const printHelp = document.querySelector('.print-help');
  if (printHelp) printHelp.append(' 可视化模块仅在“完整内容”中以静态代表图打印，交互操作请使用网页。');
  renderCurrent();
  document.documentElement.dataset.visualReady = 'true';
})();
