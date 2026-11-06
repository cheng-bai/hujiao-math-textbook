(() => {
  const key = 'annotation-pilot-bx1-5-3-teacher-v1';
  const frame = document.querySelector('#book');
  const list = document.querySelector('#list');
  const status = document.querySelector('#status');
  const edit = document.querySelector('#edit');
  const save = document.querySelector('#save');
  const cancel = document.querySelector('#cancel');
  const exportButton = document.querySelector('#export');
  const upload = document.querySelector('#upload');
  const localEditor = location.origin === 'http://127.0.0.1:8875';
  const publishedUrl = 'https://raw.githubusercontent.com/cheng-bai/hujiao-math-annotations/main/bx1-5-3-teacher.json';
  let saved;
  let working = null;
  if (localEditor) {
    try {
      saved = JSON.parse(localStorage.getItem(key) || '[]');
      if (!Array.isArray(saved)) throw new Error();
    } catch {
      status.textContent = '本机批注无法读取，请勿覆盖浏览器数据。';
      edit.disabled = exportButton.disabled = upload.disabled = true;
      return;
    }
  }
  if (!localEditor) {
    saved = [];
    edit.hidden = exportButton.hidden = upload.hidden = true;
    document.querySelector('#instructions').textContent = '此页面展示教师公开的批注。';
    fetch(`${publishedUrl}?t=${Date.now()}`, {cache:'no-store'}).then(response => {
      if (!response.ok) throw new Error('读取失败');
      return response.json();
    }).then(data => {
      if (data.section !== 'bx1-5-3' || data.edition !== 'teacher' || !Array.isArray(data.annotations)) throw new Error('数据不匹配');
      saved = data.annotations;
      render();
      status.textContent = `已读取 ${saved.length} 条公开批注。`;
    }).catch(() => { status.textContent = '公开批注暂时无法加载，请稍后重试。'; });
  }

  function validSection() {
    const root = frame.contentDocument?.documentElement;
    return root?.dataset.sectionId === 'bx1-5-3' && root.dataset.mode === 'teacher';
  }

  function textGroups(element) {
    const groups = [];
    let group = null;
    function visit(node, container) {
      if (node.nodeType === Node.ELEMENT_NODE) {
        if (node.matches('.katex,.math,script,style,img,br,svg,canvas')) { group = null; return; }
        if (node.matches('p,li,td,th,h1,h2,h3,h4,h5,h6')) container = node;
      }
      if (node.nodeType === Node.TEXT_NODE && node.data) {
        if (!group || group.container !== container) {
          group = {container, nodes: [], text: ''};
          groups.push(group);
        }
        group.nodes.push({node, start: group.text.length});
        group.text += node.data;
      }
      for (const child of node.childNodes) visit(child, container);
    }
    visit(element, element);
    return groups;
  }

  function locate(item) {
    const block = frame.contentDocument.getElementById(item.blockId);
    if (!block || !item.quote) return null;
    const matches = [];
    for (const group of textGroups(block)) {
      let index = group.text.indexOf(item.quote);
      while (index !== -1) {
        matches.push({group, index});
        index = group.text.indexOf(item.quote, index + 1);
      }
    }
    if (matches.length !== 1) return null;
    const {group, index} = matches[0];
    const end = index + item.quote.length;
    const parts = group.nodes.filter(part => part.start < end && part.start + part.node.length > index)
      .map(part => ({node: part.node, start: Math.max(0, index - part.start), end: Math.min(part.node.length, end - part.start)}));
    return parts.some(part => part.node.parentElement.closest('mark[data-pilot]')) ? null : parts;
  }

  function render() {
    const doc = frame.contentDocument;
    if (!doc?.body) return;
    if (!validSection()) {
      list.replaceChildren();
      status.textContent = '当前不是 5.3 教师版，请返回试点章节后再编辑或导出。';
      return;
    }
    doc.querySelectorAll('.book-body .teacher-only').forEach((block, index) => {
      if (!block.id) block.id = `annotation-teacher-block-${index}`;
    });
    doc.querySelectorAll('mark[data-pilot]').forEach(mark => {
      const parent = mark.parentNode;
      mark.replaceWith(doc.createTextNode(mark.textContent));
      parent.normalize();
    });
    list.replaceChildren();
    const items = working || saved;
    items.forEach(item => {
      const found = locate(item);
      if (found) {
        for (const part of found.reverse()) {
          const range = doc.createRange();
          range.setStart(part.node, part.start);
          range.setEnd(part.node, part.end);
          const mark = doc.createElement('mark');
          mark.dataset.pilot = item.id;
          mark.style.background = {yellow:'#ffe78b',green:'#bfe7ba',blue:'#b8def3'}[item.color] || '#ffe78b';
          mark.title = '查看对应批注';
          mark.onclick = () => document.getElementById(`annotation-${item.id}`)?.scrollIntoView({block:'center',behavior:'smooth'});
          range.surroundContents(mark);
        }
      }
      const card = document.createElement('div');
      card.className = 'item';
      card.id = `annotation-${item.id}`;
      const quote = document.createElement('blockquote');
      quote.textContent = item.quote;
      card.append(quote);
      if (working) {
        const label = document.createElement('label');
        label.textContent = '备注（选填）';
        const note = document.createElement('textarea');
        note.rows = 2;
        note.maxLength = 2000;
        note.value = item.note || '';
        note.oninput = () => { item.note = note.value; };
        label.append(note);
        card.append(label);
      } else if (localEditor) {
        const label = document.createElement('label');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = Boolean(item.selected);
        checkbox.onchange = () => { item.selected = checkbox.checked; };
        label.append(checkbox, ' 选择导出');
        card.prepend(label);
        if (item.note) {
          const note = document.createElement('p');
          note.textContent = item.note;
          card.append(note);
        }
      } else if (item.note) {
        const note = document.createElement('p');
        note.textContent = item.note;
        card.append(note);
      }
      if (!found) {
        const warning = document.createElement('p');
        warning.className = 'warning';
        warning.textContent = '无法唯一定位，未高亮；请重新添加后再导出。';
        card.append(warning);
      }
      const actions = document.createElement('div');
      actions.className = 'actions';
      const jump = document.createElement('button');
      jump.textContent = '定位原文';
      jump.disabled = !found;
      jump.onclick = () => [...doc.querySelectorAll('mark[data-pilot]')].find(mark => mark.dataset.pilot === item.id)?.scrollIntoView({block:'center',behavior:'smooth'});
      actions.append(jump);
      if (working) {
        const remove = document.createElement('button');
        remove.textContent = '移除';
        remove.onclick = () => { working = working.filter(entry => entry.id !== item.id); render(); };
        actions.append(remove);
      }
      card.append(actions);
      list.append(card);
    });
    if (!items.length) list.textContent = '暂无批注';
  }

  function updateButtons() {
    edit.hidden = Boolean(working);
    save.hidden = !working;
    cancel.hidden = !working;
    exportButton.disabled = Boolean(working);
    upload.disabled = Boolean(working);
  }

  function addSelection() {
    if (!working || !validSection()) return;
    const selection = frame.contentWindow.getSelection();
    if (!selection || selection.rangeCount !== 1 || selection.isCollapsed) return;
    const range = selection.getRangeAt(0);
    const node = range.startContainer;
    const endNode = range.endContainer;
    const block = node.parentElement?.closest('[id]');
    const paragraph = node.parentElement?.closest('p,li,td,th,h1,h2,h3,h4,h5,h6');
    const fragment = range.cloneContents();
    if (node.nodeType !== Node.TEXT_NODE || endNode.nodeType !== Node.TEXT_NODE || !block?.closest('.book-body') || block !== endNode.parentElement?.closest('[id]') || !paragraph || paragraph !== endNode.parentElement?.closest('p,li,td,th,h1,h2,h3,h4,h5,h6') || node.parentElement.closest('.math,.katex,mark') || endNode.parentElement.closest('.math,.katex,mark') || fragment.querySelector('.math,.katex,mark,img,br,svg,canvas')) {
      status.textContent = '请选择同一段内的文字；公式、图片、换行和已有高亮暂不支持。';
      return;
    }
    const quote = range.toString();
    const candidate = {id:crypto.randomUUID(), blockId:block.id, quote, note:'', color:'yellow', createdAt:new Date().toISOString(), selected:false};
    if (!quote.trim() || !locate(candidate)) {
      status.textContent = '文字为空或在该内容块中不唯一，请调整选区。';
      return;
    }
    selection.removeAllRanges();
    working.push(candidate);
    render();
    status.textContent = '已添加高亮，继续划选或点击保存。';
  }

  frame.addEventListener('load', () => {
    render();
    if (validSection()) {
      const doc = frame.contentDocument;
      doc.addEventListener('mouseup', addSelection);
      doc.addEventListener('keyup', event => { if (event.shiftKey) addSelection(); });
      doc.addEventListener('touchend', () => setTimeout(addSelection, 100));
    }
  });
  edit.onclick = () => {
    if (!validSection()) { status.textContent = '请先返回 5.3 教师版。'; return; }
    working = saved.map(item => ({...item}));
    updateButtons();
    render();
    status.textContent = '编辑模式：划选文字即可高亮，备注可选。';
  };
  save.onclick = () => {
    if (!working || !validSection()) { status.textContent = '请先返回 5.3 教师版。'; return; }
    try { localStorage.setItem(key, JSON.stringify(working)); }
    catch { status.textContent = '保存失败，请检查浏览器存储空间。'; return; }
    saved = working;
    working = null;
    updateButtons();
    render();
    status.textContent = '已保存到本浏览器，未上传或发布。';
  };
  cancel.onclick = () => {
    if (!working || !confirm('放弃本轮未保存的高亮和备注修改？')) return;
    working = null;
    updateButtons();
    render();
    status.textContent = '已取消本轮修改。';
  };
  exportButton.onclick = () => {
    if (!validSection()) { status.textContent = '请先返回 5.3 教师版。'; return; }
    const selected = saved.filter(item => item.selected);
    if (!selected.length) { status.textContent = '请先勾选需要导出的批注。'; return; }
    const marks = [...frame.contentDocument.querySelectorAll('mark[data-pilot]')];
    if (selected.some(item => !marks.some(mark => mark.dataset.pilot === item.id))) { status.textContent = '有批注无法定位，请先重新添加。'; return; }
    if (!confirm(`将导出 ${selected.length} 条批注。导出包含所选原文，可能涉及教参或答案，请勿未经核查公开。`)) return;
    const data = {version:1, section:'bx1-5-3', edition:'teacher', annotations:selected.map(({selected, ...item}) => item)};
    const url = URL.createObjectURL(new Blob([JSON.stringify(data,null,2)], {type:'application/json'}));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'bx1-5-3-teacher-annotations.json';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    status.textContent = '已导出文件；尚未上传或发布。';
  };
  upload.onclick = async () => {
    if (!validSection() || working) return;
    const marks = [...frame.contentDocument.querySelectorAll('mark[data-pilot]')];
    if (saved.some(item => !marks.some(mark => mark.dataset.pilot === item.id))) { status.textContent = '有批注无法定位，请先检查。'; return; }
    if (!confirm(`将公开当前浏览器中全部 ${saved.length} 条已保存批注，包括原文和备注。${saved.length ? '' : '注意：0 条将清空线上批注。'}确认上传？`)) return;
    const data = {version:1, section:'bx1-5-3', edition:'teacher', annotations:saved.map(({selected, ...item}) => item)};
    upload.disabled = true;
    status.textContent = '正在上传批注...';
    try {
      const response = await fetch('http://127.0.0.1:8876/publish', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      status.textContent = '上传成功，正在核对线上数据...';
      const online = await fetch(`${publishedUrl}?t=${Date.now()}`, {cache:'no-store'});
      if (!online.ok || JSON.stringify(await online.json()) !== JSON.stringify(data)) throw new Error('上传成功，但线上数据尚未刷新');
      status.textContent = `线上批注数据已更新：${saved.length} 条。请打开公开页面检查显示。`;
    } catch (error) { status.textContent = `未完成线上核对：${error.message}。本机批注仍保留。`; }
    finally { upload.disabled = false; }
  };
  window.addEventListener('beforeunload', event => {
    if (working) { event.preventDefault(); event.returnValue = ''; }
  });
})();
