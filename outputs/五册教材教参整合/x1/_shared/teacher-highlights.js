(() => {
  if (document.documentElement.dataset.mode !== 'teacher') return;

  const sectionId = document.documentElement.dataset.sectionId || '';
  const STORAGE_VERSION = 1;
  const storageKey = `hujiao-teacher-highlights-v${STORAGE_VERSION}:${sectionId}`;
  const body = document.querySelector('.book-body');
  if (!body || !sectionId) return;

  const popover = document.createElement('div');
  popover.id = 'teacher-highlight-popover';
  popover.hidden = true;
  popover.innerHTML = '<button type="button" class="primary" data-action="add">高亮</button><button type="button" data-action="block">高亮此段</button><button type="button" data-action="dismiss">取消</button>';
  document.body.append(popover);

  const dialog = document.createElement('dialog');
  dialog.id = 'teacher-highlights-dialog';
  dialog.innerHTML = `
    <div class="thl-head"><h2>我的高亮</h2><button type="button" data-close aria-label="关闭">×</button></div>
    <div class="thl-body">
      <p class="help">仅保存在本浏览器，按稳定题块/段落 ID 定位。换设备请导出 JSON 再导入。</p>
      <p class="help">公式内划选可能不稳定；可改用「高亮此段」。KaTeX 区域请高亮整段。</p>
      <ul class="thl-list" id="teacher-highlights-list"></ul>
    </div>
    <div class="thl-foot">
      <div><button type="button" id="thl-export">导出</button><label><button type="button" id="thl-import-btn">导入</button><input type="file" id="thl-import" accept="application/json"></label></div>
      <button type="button" data-close>关闭</button>
    </div>`;
  document.body.append(dialog);

  const list = dialog.querySelector('#teacher-highlights-list');
  const status = document.querySelector('#status');
  let saved = [];
  let pendingRange = null;
  let pendingBlockQuote = null;

  function announce(message) {
    if (!message) return;
    if (status) {
      status.textContent = message;
      status.classList.add('visible');
      setTimeout(() => status.classList.remove('visible'), 2200);
    }
  }

  try {
    const raw = localStorage.getItem(storageKey);
    saved = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(saved)) throw new Error('bad');
  } catch {
    saved = [];
    announce('无法读取已保存高亮，请勿清空浏览器数据。');
  }

  function textGroups(element) {
    const groups = [];
    let group = null;
    function visit(node, container) {
      if (node.nodeType === Node.ELEMENT_NODE) {
        if (node.matches('.katex,.math,script,style,img,br,svg,canvas,mark.teacher-highlight')) {
          group = null;
          return;
        }
        if (node.matches('p,li,td,th,h1,h2,h3,h4,h5,h6,.question-body,.question-label,.group-heading')) {
          container = node;
        }
      }
      if (node.nodeType === Node.TEXT_NODE && node.data) {
        if (!group || group.container !== container) {
          group = { container, nodes: [], text: '' };
          groups.push(group);
        }
        group.nodes.push({ node, start: group.text.length });
        group.text += node.data;
      }
      for (const child of node.childNodes) visit(child, container);
    }
    visit(element, element);
    return groups;
  }

  function stableBlock(node) {
    const block = node?.parentElement?.closest('[id]');
    if (!block?.closest('.book-body')) return null;
    return block;
  }

  function locate(item) {
    const block = document.getElementById(item.blockId);
    if (!block || !item.quote) return null;
    const matches = [];
    for (const group of textGroups(block)) {
      let index = group.text.indexOf(item.quote);
      while (index !== -1) {
        matches.push({ group, index });
        index = group.text.indexOf(item.quote, index + 1);
      }
    }
    if (matches.length !== 1) return null;
    const { group, index } = matches[0];
    const end = index + item.quote.length;
    return group.nodes
      .filter((part) => part.start < end && part.start + part.node.length > index)
      .map((part) => ({
        node: part.node,
        start: Math.max(0, index - part.start),
        end: Math.min(part.node.length, end - part.start),
      }));
  }

  function clearMarks() {
    document.querySelectorAll('mark.teacher-highlight').forEach((mark) => {
      const parent = mark.parentNode;
      parent?.replaceChild(document.createTextNode(mark.textContent), mark);
      parent?.normalize();
    });
  }

  function applyMarks() {
    clearMarks();
    for (const item of saved) {
      const parts = locate(item);
      if (!parts?.length) continue;
      for (const part of parts.slice().reverse()) {
        const range = document.createRange();
        range.setStart(part.node, part.start);
        range.setEnd(part.node, part.end);
        const mark = document.createElement('mark');
        mark.className = 'teacher-highlight';
        mark.dataset.highlightId = item.id;
        mark.dataset.color = item.color || 'warm';
        if (item.note?.trim()) {
          mark.classList.add('teacher-highlight-note');
          mark.title = item.note.trim();
        }
        mark.addEventListener('click', (event) => {
          event.preventDefault();
          openPanel();
          document.querySelector(`.thl-item[data-id="${item.id}"]`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        });
        try {
          range.surroundContents(mark);
        } catch {
          /* Range may split nodes after DOM updates; skip this mark. */
        }
      }
    }
  }

  function persist() {
    try {
      localStorage.setItem(storageKey, JSON.stringify(saved));
    } catch {
      announce('保存失败，请检查浏览器存储空间。');
    }
  }

  function renderList() {
    list.replaceChildren();
    if (!saved.length) {
      const empty = document.createElement('li');
      empty.textContent = '暂无高亮。划选正文或使用「高亮此段」。';
      empty.style.listStyle = 'none';
      list.append(empty);
      return;
    }
    for (const item of saved) {
      const li = document.createElement('li');
      li.className = 'thl-item';
      li.dataset.id = item.id;
      const quote = document.createElement('blockquote');
      quote.textContent = item.quote;
      const note = document.createElement('textarea');
      note.rows = 2;
      note.maxLength = 2000;
      note.value = item.note || '';
      note.placeholder = '备注（选填）';
      note.addEventListener('input', () => {
        item.note = note.value;
        persist();
        applyMarks();
      });
      const row = document.createElement('div');
      row.className = 'row';
      const jump = document.createElement('button');
      jump.type = 'button';
      jump.textContent = '定位';
      jump.addEventListener('click', () => {
        const mark = document.querySelector(`mark.teacher-highlight[data-highlight-id="${item.id}"]`);
        if (mark) mark.scrollIntoView({ block: 'center', behavior: 'smooth' });
        else announce('无法唯一定位；原文可能已更新。');
      });
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.textContent = '移除';
      remove.addEventListener('click', () => {
        saved = saved.filter((entry) => entry.id !== item.id);
        persist();
        applyMarks();
        renderList();
      });
      row.append(jump, remove);
      li.append(quote, note, row);
      if (!locate(item)) {
        const warn = document.createElement('p');
        warn.className = 'warn';
        warn.textContent = '无法唯一定位；未在正文高亮。';
        li.append(warn);
      }
      list.append(li);
    }
  }

  function openPanel() {
    renderList();
    dialog.showModal();
  }

  function hidePopover() {
    popover.hidden = true;
    pendingRange = null;
    pendingBlockQuote = null;
  }

  function selectionIsValid(range) {
    const node = range.startContainer;
    const endNode = range.endContainer;
    if (node.nodeType !== Node.TEXT_NODE || endNode.nodeType !== Node.TEXT_NODE) return false;
  const block = stableBlock(node);
    if (!block || block !== stableBlock(endNode)) return false;
    const paragraph = node.parentElement?.closest('p,li,td,th,h1,h2,h3,h4,h5,h6,.question-body,.question-label');
    const endParagraph = endNode.parentElement?.closest('p,li,td,th,h1,h2,h3,h4,h5,h6,.question-body,.question-label');
    if (!paragraph || paragraph !== endParagraph) return false;
    if (node.parentElement?.closest('.math,.katex,mark') || endNode.parentElement?.closest('.math,.katex,mark')) return false;
    const fragment = range.cloneContents();
    if (fragment.querySelector?.('.math,.katex,mark,img,br,svg,canvas')) return false;
    return true;
  }

  function addItem(blockId, quote) {
    const candidate = {
      id: crypto.randomUUID(),
      blockId,
      quote,
      note: '',
      color: 'warm',
      createdAt: new Date().toISOString(),
    };
    if (!quote.trim() || !locate(candidate)) {
      announce('文字为空或在该内容块中不唯一，请调整选区或使用「高亮此段」。');
      return false;
    }
    saved.push(candidate);
    persist();
    applyMarks();
    renderList();
    announce('已添加高亮');
    return true;
  }

  function addFromSelection() {
    if (!pendingRange) return;
    const range = pendingRange;
    const block = stableBlock(range.startContainer);
    if (!block) return;
    const quote = range.toString();
    window.getSelection()?.removeAllRanges();
    hidePopover();
    addItem(block.id, quote);
  }

  function addFromBlock() {
    if (!pendingBlockQuote) return;
    const { blockId, quote } = pendingBlockQuote;
    hidePopover();
    addItem(blockId, quote);
  }

  function showPopover(clientX, clientY) {
    const rect = popover.getBoundingClientRect();
    const left = Math.min(Math.max(12, clientX - rect.width / 2), innerWidth - rect.width - 12);
    const top = Math.min(Math.max(12, clientY - 48), innerHeight - rect.height - 12);
    popover.style.left = `${left}px`;
    popover.style.top = `${top}px`;
    popover.hidden = false;
  }

  function captureSelection(event) {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount !== 1 || selection.isCollapsed) {
      hidePopover();
      return;
    }
    const range = selection.getRangeAt(0);
    if (!body.contains(range.commonAncestorContainer)) {
      hidePopover();
      return;
    }
    if (selectionIsValid(range)) {
      pendingRange = range.cloneRange();
      pendingBlockQuote = null;
      showPopover(event.clientX || innerWidth / 2, event.clientY || innerHeight / 3);
      return;
    }
    const block = stableBlock(range.startContainer) || stableBlock(range.commonAncestorContainer);
    if (!block) {
      hidePopover();
      return;
    }
    const text = block.textContent?.replace(/\s+/g, ' ').trim() || '';
    if (text.length < 8 || text.length > 240) {
      hidePopover();
      return;
    }
    pendingRange = null;
    pendingBlockQuote = { blockId: block.id, quote: text.slice(0, Math.min(text.length, 160)) };
    showPopover(event.clientX || innerWidth / 2, event.clientY || innerHeight / 3);
  }

  body.addEventListener('mouseup', captureSelection);
  body.addEventListener('touchend', (event) => setTimeout(() => captureSelection(event), 80));
  popover.addEventListener('click', (event) => {
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'add') addFromSelection();
    else if (action === 'block') addFromBlock();
    else hidePopover();
  });
  document.addEventListener('mousedown', (event) => {
    if (!popover.hidden && !popover.contains(event.target)) hidePopover();
  });

  function exportFile() {
    const payload = {
      version: STORAGE_VERSION,
      sectionId,
      edition: 'teacher',
      exportedAt: new Date().toISOString(),
      annotations: saved.map(({ ...item }) => item),
    };
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${sectionId}-teacher-highlights.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 800);
    announce('已导出 JSON 文件');
  }

  function importFile(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(String(reader.result));
        if (data.version !== STORAGE_VERSION || data.sectionId !== sectionId || data.edition !== 'teacher') {
          throw new Error('文件与当前节不匹配');
        }
        if (!Array.isArray(data.annotations)) throw new Error('缺少 annotations');
        const incoming = data.annotations.filter((row) => row?.blockId && row?.quote);
        if (!incoming.length) throw new Error('没有可导入的高亮');
        if (!confirm(`导入 ${incoming.length} 条高亮？将覆盖本页当前记录。`)) return;
        saved = incoming.map((row) => ({
          id: row.id || crypto.randomUUID(),
          blockId: row.blockId,
          quote: row.quote,
          note: row.note || '',
          color: row.color || 'warm',
          createdAt: row.createdAt || new Date().toISOString(),
        }));
        persist();
        applyMarks();
        renderList();
        announce('导入完成');
      } catch (error) {
        announce(error.message || '导入失败');
      }
    };
    reader.readAsText(file, 'utf-8');
  }

  const openButton = document.querySelector('#highlights-open');
  openButton?.addEventListener('click', openPanel);
  dialog.querySelectorAll('[data-close]').forEach((node) => node.addEventListener('click', () => dialog.close()));
  dialog.querySelector('#thl-export')?.addEventListener('click', exportFile);
  dialog.querySelector('#thl-import-btn')?.addEventListener('click', () => dialog.querySelector('#thl-import')?.click());
  dialog.querySelector('#thl-import')?.addEventListener('change', (event) => {
    importFile(event.target.files?.[0]);
    event.target.value = '';
  });

  applyMarks();
  window.addEventListener('book-layout-updated', applyMarks);
})();
