(() => {
  if (document.documentElement.dataset.mode !== 'teacher') return;

  const sectionId = document.documentElement.dataset.sectionId || '';
  const STORAGE_VERSION = 1;
  const storageKey = `hujiao-teacher-highlights-v${STORAGE_VERSION}:${sectionId}`;
  const body = document.querySelector('.book-body');
  if (!body || !sectionId) return;
  const paragraphSelector = 'p,li,td,th,h1,h2,h3,h4,h5,h6,.question-body,.question-label,.group-heading,.math.display';

  const popover = document.createElement('div');
  popover.id = 'teacher-highlight-popover';
  popover.hidden = true;
  popover.innerHTML = '<button type="button" class="primary" data-action="add">高亮</button><button type="button" data-action="block">高亮此段</button><button type="button" data-action="dismiss">取消</button>';
  document.body.append(popover);
  const textAction = popover.querySelector('[data-action="add"]');
  const paragraphAction = popover.querySelector('[data-action="block"]');

  const dialog = document.createElement('dialog');
  dialog.id = 'teacher-highlights-dialog';
  dialog.innerHTML = `
    <div class="thl-head"><h2>我的高亮</h2><button type="button" data-close aria-label="关闭">×</button></div>
    <div class="thl-body">
      <p class="help">仅保存在本浏览器，按稳定题块/段落 ID 定位。换设备请导出 JSON 再导入。</p>
      <p class="help">划选文字可高亮选区；选区含公式时可用「高亮此段」。</p>
      <ul class="thl-list" id="teacher-highlights-list"></ul>
    </div>
    <div class="thl-foot">
      <div><button type="button" id="thl-export">导出</button><label><button type="button" id="thl-import-btn">导入</button><input type="file" id="thl-import" accept="application/json"></label></div>
      <button type="button" data-close>关闭</button>
    </div>`;
  document.body.append(dialog);

  const list = dialog.querySelector('#teacher-highlights-list');
  const status = document.querySelector('#status');
  const placedMarks = new Map();
  let saved = [];
  let pendingText = null;
  let pendingParagraph = null;

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
        if (node.matches(paragraphSelector)) {
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
    const block = elementFor(node)?.closest('[id]');
    if (!block || !body.contains(block)) return null;
    return block;
  }

  function elementFor(node) {
    return node?.nodeType === Node.ELEMENT_NODE ? node : node?.parentElement;
  }

  function paragraphQuote(paragraph) {
    const clone = paragraph.cloneNode(true);
    const formulas = clone.matches('[data-tex]') ? [clone] : clone.querySelectorAll('[data-tex]');
    for (const formula of formulas) formula.textContent = ` $${formula.dataset.tex}$ `;
    return clone.textContent.replace(/\s+/g, ' ').trim();
  }

  function locateParagraph(item) {
    const block = document.getElementById(item.blockId);
    if (!block || !body.contains(block)) return null;
    const candidates = [...block.querySelectorAll(paragraphSelector)];
    if (block.matches(paragraphSelector)) candidates.unshift(block);
    const matches = candidates.filter((paragraph) => paragraph.localName === item.paragraphTag
      && stableBlock(paragraph) === block && paragraphQuote(paragraph) === item.quote);
    return matches.length === 1 ? matches[0] : null;
  }

  function locateText(item) {
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
    body.querySelectorAll('.teacher-highlight-paragraph').forEach((paragraph) => {
      paragraph.classList.remove('teacher-highlight-paragraph');
      delete paragraph.dataset.paragraphHighlightColor;
    });
    document.querySelectorAll('mark.teacher-highlight').forEach((mark) => {
      const parent = mark.parentNode;
      parent?.replaceChild(document.createTextNode(mark.textContent), mark);
      parent?.normalize();
    });
  }

  function applyMarks() {
    clearMarks();
    placedMarks.clear();
    for (const item of saved) {
      if (item.paragraphTag) {
        const paragraph = locateParagraph(item);
        if (paragraph) {
          paragraph.classList.add('teacher-highlight-paragraph');
          paragraph.dataset.paragraphHighlightColor = item.color || 'warm';
          placedMarks.set(item, paragraph);
        }
        continue;
      }
      const parts = locateText(item);
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
          placedMarks.set(item, mark);
        } catch {
          /* Range may split nodes after DOM updates; skip this mark. */
        }
      }
    }
  }

  function persist(items = saved) {
    try {
      localStorage.setItem(storageKey, JSON.stringify(items));
      return true;
    } catch {
      announce('保存失败，请检查浏览器存储空间。');
      return false;
    }
  }

  function jumpToMark(item) {
    const mark = placedMarks.get(item);
    const unavailable = '无法唯一定位；未在正文高亮。';
    if (!mark?.isConnected) return unavailable;
    if (mark.closest('.notes-hidden .teacher-only')) return '这处高亮在隐藏的教师批注中，请先显示教师批注。';
    if (mark.closest('.answers-hidden .answer, .answers-hidden .question-analysis')) {
      return '这处高亮在隐藏的答案或解析中，请先显示答案。';
    }
    for (let ancestor = mark.parentElement; ancestor; ancestor = ancestor.parentElement) {
      if (ancestor.matches('details')) ancestor.open = true;
    }
    if (!mark.getClientRects().length) return '这处高亮当前未显示，请检查阅读设置。';
    dialog.close();
    mark.tabIndex = -1;
    mark.focus({ preventScroll: true });
    mark.scrollIntoView({ block: 'center', behavior: 'instant' });
    return '';
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
      const warn = document.createElement('p');
      warn.className = 'warn';
      warn.setAttribute('role', 'status');
      if (!placedMarks.has(item)) warn.textContent = '无法唯一定位；未在正文高亮。';
      jump.addEventListener('click', () => {
        warn.textContent = jumpToMark(item);
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
      li.append(quote, note, row, warn);
      list.append(li);
    }
  }

  function openPanel() {
    renderList();
    dialog.showModal();
  }

  function hidePopover() {
    popover.hidden = true;
    pendingText = null;
    pendingParagraph = null;
  }

  function selectionIsValid(range) {
    const node = range.startContainer;
    const endNode = range.endContainer;
    if (node.nodeType !== Node.TEXT_NODE || endNode.nodeType !== Node.TEXT_NODE) return false;
    const block = stableBlock(node);
    if (!block || block !== stableBlock(endNode)) return false;
    if (node.parentElement?.closest('.math,.katex,mark') || endNode.parentElement?.closest('.math,.katex,mark')) return false;
    const fragment = range.cloneContents();
    if (fragment.querySelector?.('.math,.katex,mark,img,br,svg,canvas')) return false;
    return true;
  }

  function addItem(anchor) {
    const candidate = {
      id: crypto.randomUUID(),
      ...anchor,
      note: '',
      color: 'warm',
      createdAt: new Date().toISOString(),
    };
    if (candidate.paragraphTag) {
      const paragraph = locateParagraph(candidate);
      if (!paragraph) {
        announce('这段内容无法唯一定位，未添加高亮。');
        return;
      }
      if (paragraph.classList.contains('teacher-highlight-paragraph')) {
        announce('这段已高亮。');
        return;
      }
    } else if (!locateText(candidate)) {
      announce('文字为空或在该内容块中不唯一，请调整选区或使用「高亮此段」。');
      return;
    }
    const updated = [...saved, candidate];
    if (!persist(updated)) return;
    saved = updated;
    applyMarks();
    renderList();
    announce('已添加高亮');
  }

  function addFromSelection(anchor) {
    if (!anchor) return;
    window.getSelection()?.removeAllRanges();
    hidePopover();
    addItem(anchor);
  }

  function showPopover(clientX, clientY) {
    textAction.hidden = !pendingText;
    paragraphAction.hidden = !pendingParagraph;
    popover.hidden = false;
    const rect = popover.getBoundingClientRect();
    const left = Math.min(Math.max(12, clientX - rect.width / 2), innerWidth - rect.width - 12);
    const top = Math.min(Math.max(12, clientY - 48), innerHeight - rect.height - 12);
    popover.style.left = `${left}px`;
    popover.style.top = `${top}px`;
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
    const paragraph = elementFor(range.startContainer)?.closest(paragraphSelector);
    const block = stableBlock(paragraph);
    const selected = range.toString();
    if (!block || paragraph !== elementFor(range.endContainer)?.closest(paragraphSelector) || !selected.trim()) {
      hidePopover();
      return;
    }
    const quote = paragraphQuote(paragraph);
    pendingParagraph = quote ? { blockId: block.id, paragraphTag: paragraph.localName, quote } : null;
    pendingText = selectionIsValid(range) ? { blockId: stableBlock(range.startContainer).id, quote: selected } : null;
    if (!pendingText && !pendingParagraph) {
      hidePopover();
      return;
    }
    showPopover(event.clientX || innerWidth / 2, event.clientY || innerHeight / 3);
  }

  body.addEventListener('mouseup', captureSelection);
  body.addEventListener('touchend', (event) => setTimeout(() => captureSelection(event), 80));
  popover.addEventListener('click', (event) => {
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'add') addFromSelection(pendingText);
    else if (action === 'block') addFromSelection(pendingParagraph);
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
        if (incoming.some((row) => 'paragraphTag' in row
          && (typeof row.paragraphTag !== 'string' || !/^[a-z][a-z0-9]*$/.test(row.paragraphTag)))) {
          throw new Error('段落高亮格式无效');
        }
        if (!confirm(`导入 ${incoming.length} 条高亮？将覆盖本页当前记录。`)) return;
        const updated = incoming.map((row) => ({
          id: row.id || crypto.randomUUID(),
          blockId: row.blockId,
          quote: row.quote,
          ...(row.paragraphTag ? { paragraphTag: row.paragraphTag } : {}),
          note: row.note || '',
          color: row.color || 'warm',
          createdAt: row.createdAt || new Date().toISOString(),
        }));
        if (!persist(updated)) return;
        saved = updated;
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
