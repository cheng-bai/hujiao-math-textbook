window.__mathErrors = [];
window.__mathRendered = new Promise((resolve) => {
  document.querySelectorAll('[data-tex]').forEach((node) => {
    try {
      katex.render(node.dataset.tex, node, {
        throwOnError: true,
        displayMode: node.dataset.display === 'true',
        strict: 'ignore',
        trust: false,
      });
    } catch (error) {
      window.__mathErrors.push({ tex: node.dataset.tex, message: error.message });
      node.classList.add('katex-render-error');
      node.textContent = node.dataset.tex;
    }
  });
  document.documentElement.dataset.math = window.__mathErrors.length ? 'error' : 'rendered';
  resolve({ errors: window.__mathErrors });
});

const status = document.querySelector('#status');
let statusTimer;
function announce(message) {
  status.textContent = message;
  status.classList.add('visible');
  clearTimeout(statusTimer);
  statusTimer = setTimeout(() => status.classList.remove('visible'), 2200);
}

const answerToggle = document.querySelector('#answer-toggle');
answerToggle?.addEventListener('click', () => {
  const hide = answerToggle.getAttribute('aria-pressed') !== 'true';
  document.body.classList.toggle('answers-hidden', hide);
  document.querySelectorAll('.answer').forEach((node) => { node.open = !hide; });
  answerToggle.setAttribute('aria-pressed', String(hide));
  answerToggle.textContent = hide ? '显示全部答案' : '隐藏全部答案';
  announce(hide ? '已隐藏答案、解析与例题教学提示' : '已显示全部答案与解析');
});

const notesToggle = document.querySelector('#notes-toggle');
notesToggle?.addEventListener('click', () => {
  const hide = notesToggle.getAttribute('aria-pressed') !== 'true';
  document.body.classList.toggle('notes-hidden', hide);
  notesToggle.setAttribute('aria-pressed', String(hide));
  notesToggle.textContent = hide ? '显示教师批注' : '隐藏教师批注';
  announce(hide ? '已隐藏教师批注；学生分享请使用独立学生包' : '已显示教师批注');
});

const toc = document.querySelector('.page-toc');
const navLinks = [...document.querySelectorAll('nav a')];
const tocSearch = document.querySelector('#toc-search');
const tocFilter = document.querySelector('#toc-filter');
const tocToggle = document.querySelector('#toc-toggle');
const tocDismiss = document.querySelector('#toc-dismiss');
const tocBackdrop = document.querySelector('#toc-backdrop');
const sidebar = document.querySelector('#page-sidebar');
const readerToolbar = document.querySelector('.toolbar');
function syncReaderOffset() {
  document.documentElement.style.setProperty('--reader-offset', `${Math.ceil(readerToolbar?.getBoundingClientRect().height || 0) + 12}px`);
}
if (readerToolbar) new ResizeObserver(syncReaderOffset).observe(readerToolbar);
syncReaderOffset();

function setTocOpen(open, restoreFocus = false) {
  document.body.classList.toggle('toc-open', open);
  tocToggle?.setAttribute('aria-expanded', String(open));
  if (tocBackdrop) tocBackdrop.hidden = !open;
  const concealed = innerWidth <= 720 && !open;
  if (sidebar) {
    sidebar.inert = concealed;
    if (concealed) sidebar.setAttribute('aria-hidden', 'true');
    else sidebar.removeAttribute('aria-hidden');
  }
  if (open) tocSearch?.focus({ preventScroll: true });
  else if (restoreFocus) tocToggle?.focus({ preventScroll: true });
}
setTocOpen(false);
tocToggle?.addEventListener('click', () => setTocOpen(!document.body.classList.contains('toc-open')));
tocDismiss?.addEventListener('click', () => setTocOpen(false, true));
tocBackdrop?.addEventListener('click', () => setTocOpen(false, true));
document.addEventListener('keydown', (event) => {
  if (!document.body.classList.contains('toc-open')) return;
  if (event.key === 'Escape') setTocOpen(false, true);
  if (event.key === 'Tab') {
    const stops = [...sidebar.querySelectorAll('a,button,input,select')].filter(el => !el.hidden && el.getClientRects().length);
    const first = stops[0], last = stops.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
});
function revealAnchor(hash, scroll = true) {
  let id;
  try { id = decodeURIComponent(hash.slice(1)); } catch (_) { return; }
  const target = document.getElementById(id);
  if (target) {
    syncReaderOffset();
    for (let ancestor = target.parentElement; ancestor; ancestor = ancestor.parentElement) {
      if (ancestor.matches('details')) ancestor.open = true;
    }
    target.setAttribute('tabindex', '-1');
    if (scroll) requestAnimationFrame(() => {
      target.focus({ preventScroll: true });
      target.scrollIntoView({ block: 'start', behavior: 'instant' });
    });
  }
}
navLinks.forEach(link => link.addEventListener('click', () => {
  setTocOpen(false);
  revealAnchor(link.hash);
}));
addEventListener('hashchange', () => revealAnchor(location.hash));
addEventListener('book-layout-updated', () => {
  // Re-open a directly linked concept if visualization layout folds its source again.
  revealAnchor(location.hash, false);
  scheduleToc();
});
function filterToc() {
  const normalize = text => text.toLocaleLowerCase().replace(/例题/g, '例').replace(/[\s·]/g, '');
  const query = normalize((tocSearch?.value || '').trim());
  const kind = tocFilter?.value || 'all';
  let count = 0;
  navLinks.forEach(link => {
    link.hidden = !(kind === 'all' || link.dataset.tocKind === kind) ||
      !normalize(link.dataset.tocLabel || link.textContent).includes(query);
    if (!link.hidden) count++;
  });
  const status = document.querySelector('#toc-count');
  if (status) status.textContent = count ? `${count} 处可跳转位置` : '没有匹配位置，请调整关键词或筛选';
}
tocSearch?.addEventListener('input', filterToc);
tocFilter?.addEventListener('change', filterToc);
filterToc();
const tocTargets = navLinks.map(link => ({ link, target: document.getElementById(decodeURIComponent(link.hash.slice(1))) }))
  .filter(item => item.target);
let activeToc;
let tocScheduled = false;
function updateToc() {
  tocScheduled = false;
  const threshold = (document.querySelector('.toolbar')?.getBoundingClientRect().height || 0) + 35;
  let current = tocTargets[0];
  for (const item of tocTargets) {
    if (!item.target.getClientRects().length || item.target.closest('details:not([open])')) continue;
    if (item.target.getBoundingClientRect().top <= threshold) current = item;
    else break;
  }
  if (current?.link === activeToc) return;
  activeToc?.classList.remove('active');
  activeToc?.removeAttribute('aria-current');
  activeToc = current?.link;
  activeToc?.classList.add('active');
  activeToc?.setAttribute('aria-current', 'location');
  if (toc && activeToc && !activeToc.hidden && !toc.matches(':hover') && !sidebar?.contains(document.activeElement)) {
    const box = activeToc.getBoundingClientRect(), bounds = toc.getBoundingClientRect();
    if (box.top < bounds.top || box.bottom > bounds.bottom) toc.scrollTop += box.top - bounds.top - toc.clientHeight / 3;
  }
}
function scheduleToc() { if (!tocScheduled) { tocScheduled = true; requestAnimationFrame(updateToc); } }
addEventListener('scroll', scheduleToc, { passive: true });
addEventListener('resize', () => {
  setTocOpen(innerWidth <= 720 && document.body.classList.contains('toc-open'));
  scheduleToc();
});
addEventListener('site-access-granted', () => { revealAnchor(location.hash); scheduleToc(); });
addEventListener('site-access-locked', () => setTocOpen(false));
if (document.documentElement.dataset.accessState === 'granted') revealAnchor(location.hash);
scheduleToc();
function updateProgress() {
  const max = document.documentElement.scrollHeight - innerHeight;
  document.querySelector('.reading-progress').style.width = `${max > 0 ? scrollY / max * 100 : 0}%`;
}
addEventListener('scroll', updateProgress, { passive: true });
addEventListener('resize', updateProgress);
updateProgress();

document.querySelector('#density-toggle').addEventListener('click', (event) => {
  const atTop = scrollY < 30;
  const anchor = [...document.querySelectorAll('.content-module > *')]
    .find(el => el.getBoundingClientRect().bottom > 140);
  const previousTop = anchor?.getBoundingClientRect().top;
  const spacious = document.body.classList.toggle('spacious');
  event.currentTarget.setAttribute('aria-pressed', String(spacious));
  event.currentTarget.textContent = spacious ? '紧凑阅读' : '舒展阅读';
  if (!atTop && anchor) scrollBy({ top: anchor.getBoundingClientRect().top - previousTop, behavior: 'instant' });
  updateProgress();
});

const printDialog = document.querySelector('#print-dialog');
const printForm = document.querySelector('#print-form');
const printOutput = document.querySelector('#print-output');
const printSummary = document.querySelector('#print-summary');
const isStudent = document.documentElement.dataset.mode === 'student';

function printSelection() {
  const mode = printForm.elements['print-mode'].value;
  const scopes = new Set([...printForm.querySelectorAll('[name="print-module"]:checked')].map(el => el.value));
  const categories = new Set([...printForm.querySelectorAll('[name="print-category"]:checked')].map(el => el.value));
  const notes = mode !== 'questions' && !!document.querySelector('#print-notes')?.checked && !isStudent;
  const withQuestions = mode !== 'text';
  const modules = [...document.querySelectorAll('.book-body .content-module')]
    .filter(el => scopes.has(el.dataset.module)).map(el => {
      const children = [...el.children];
      const allowed = node => node.matches('.prose') ? mode === 'all' || mode === 'text'
        : node.matches('.visual-module') ? mode === 'all'
        : node.matches('.question') ? withQuestions && categories.has(node.dataset.category)
          : node.matches('.teacher,.editor,.intro') && notes;
      const items = children.filter((node, index) => {
        if (allowed(node)) return true;
        if (!node.matches('.group-heading') || !withQuestions) return false;
        const next = children.slice(index + 1).find(sibling => sibling.matches('.question,.group-heading'));
        return next?.matches('.question') && allowed(next);
      });
      return { source: el, items };
    }).filter(module => module.items.length);
  const questionCount = modules.flatMap(module => module.items).filter(el => el.matches('.question')).length;
  return { mode, notes, modules, questionCount, answers: !isStudent && (mode === 'all' || mode === 'answers') };
}

function updatePrintSummary() {
  const selection = printSelection();
  const empty = !selection.modules.length;
  printSummary.textContent = empty ? '当前范围没有可打印的内容，请调整组合或章节。'
    : `${selection.modules.length} 个章节模块 · ${selection.questionCount} 道题${selection.questionCount ? selection.answers ? ' · 含答案与解析' : ' · 不含答案' : ''}${selection.notes ? ' · 含教师批注' : ''}`;
  document.querySelector('#print-preview').disabled = empty;
  document.querySelector('#print-submit').disabled = empty;
  printForm.querySelectorAll('[name="print-category"]').forEach(el => { el.disabled = selection.mode === 'text'; });
  const notes = document.querySelector('#print-notes');
  if (notes) notes.disabled = selection.mode === 'questions';
  return selection;
}

function buildPrintOutput() {
  const selection = updatePrintSummary();
  const fragment = document.createDocumentFragment();
  const header = document.createElement('header');
  header.className = 'print-title';
  const title = document.createElement('h1');
  title.textContent = document.title.split(' · ')[0];
  const subtitle = document.createElement('p');
  const label = { all: isStudent ? '正文与试题' : '完整内容', text: '正文', questions: '试题', answers: '试题与答案' };
  subtitle.textContent = `${label[selection.mode]} / ${selection.modules.map(module => module.source.dataset.title).join('、')}${selection.questionCount ? ` / ${selection.questionCount}题` : ''}`;
  header.append(title, subtitle);
  fragment.append(header);
  for (const module of selection.modules) {
    const section = document.createElement('section');
    section.className = 'print-module';
    const heading = module.source.querySelector('.section-heading').cloneNode(true);
    section.append(heading);
    for (const item of module.items) {
      const copy = item.cloneNode(true);
      // Printing uses the untouched original, not both summary and original prose.
      if (copy.matches('.visual-condensed')) {
        const original = copy.querySelector(':scope > .visual-original > .visual-original-body');
        if (original) copy.replaceChildren(...original.childNodes);
        copy.classList.remove('visual-condensed');
      }
      if (!selection.answers) copy.querySelectorAll('.answer').forEach(el => el.remove());
      if (!selection.notes) copy.querySelectorAll('.question-analysis').forEach(el => el.remove());
      copy.querySelectorAll('details.answer').forEach(el => {
        const answer = document.createElement('section');
        answer.className = 'print-answer';
        const label = document.createElement('h4');
        label.textContent = '答案与解析';
        answer.append(label, el.querySelector('.answer-body'));
        el.replaceWith(answer);
      });
      if (copy.matches('.question')) {
        if (copy.querySelectorAll('.question-body img').length >= 4) {
          copy.classList.add('print-compact-figures');
        }
        // Keep the label and stem together even when an oversized answer must flow.
        const head = document.createElement('div');
        head.className = 'print-question-head';
        head.append(...copy.querySelectorAll(':scope > .question-label, :scope > .question-body'));
        copy.prepend(head);
      }
      if (copy.matches('.visual-module')) {
        const host = copy.querySelector('.visual-frame-container');
        const figure = document.createElement('figure');
        figure.className = 'visual-print-fallback';
        const image = document.createElement('img');
        image.src = copy.dataset.thumbnail;
        image.alt = copy.dataset.title + '交互模块静态预览';
        const caption = document.createElement('figcaption');
        caption.textContent = `${copy.dataset.title} · 交互图形仅可在网页中操作；打印图为模块代表状态。`;
        figure.append(image, caption);
        host?.replaceWith(figure);
      }
      if (!document.querySelector('#print-sources')?.checked || isStudent) copy.querySelectorAll('.provenance').forEach(el => el.remove());
      section.append(copy);
    }
    // Clones must not inherit screen answer/note visibility or duplicate reading anchors.
    section.querySelectorAll('[id]').forEach(el => el.removeAttribute('id'));
    section.querySelectorAll('.teacher-only').forEach(el => el.classList.remove('teacher-only'));
    section.querySelectorAll('.question-analysis').forEach(el => { el.classList.replace('question-analysis', 'print-commentary'); });
    section.querySelectorAll('img').forEach(el => { el.loading = 'eager'; });
    fragment.append(section);
  }
  printOutput.replaceChildren(fragment);
  printOutput.dataset.mode = selection.mode;
  return selection;
}

function openPrintSettings() {
  if (!document.body.classList.contains('print-preview')) readingPosition = scrollY;
  updatePrintSummary();
  printDialog.showModal();
}
document.querySelector('#print-open').addEventListener('click', openPrintSettings);
document.querySelector('#print-close').addEventListener('click', () => printDialog.close());
printForm.addEventListener('change', updatePrintSummary);
for (const [id, checked] of [['scope-all', true], ['scope-none', false]]) {
  document.querySelector('#' + id).addEventListener('click', () => {
    printForm.querySelectorAll('[name="print-module"]').forEach(el => { el.checked = checked; });
    updatePrintSummary();
  });
}
document.querySelector('#print-preview').addEventListener('click', () => {
  if (!buildPrintOutput().modules.length) return;
  printDialog.close();
  document.body.classList.add('print-preview');
  scrollTo({ top: 0, behavior: 'instant' });
  document.querySelector('#print-back').focus({ preventScroll: true });
});
let readingPosition = 0;
printDialog.addEventListener('close', () => {
  if (!document.body.classList.contains('print-preview')) document.querySelector('#print-open').focus({ preventScroll: true });
});
document.querySelector('#print-back').addEventListener('click', () => {
  document.body.classList.remove('print-preview');
  scrollTo({ top: readingPosition, behavior: 'instant' });
  document.querySelector('#print-open').focus({ preventScroll: true });
});
document.querySelector('#print-settings').addEventListener('click', openPrintSettings);

let printing = false;
async function printNow() {
  if (printing) return;
  printing = true;
  try {
    await window.__mathRendered;
    if (window.__mathErrors.length) throw new Error('公式尚未正确渲染，请先检查页面。');
    if (!buildPrintOutput().modules.length) return;
    await document.fonts.ready;
    await Promise.all([...printOutput.querySelectorAll('img')].map(img => new Promise((resolve, reject) => {
      if (img.complete) return img.naturalWidth ? resolve() : reject(new Error('题图未加载，请重新打开页面。'));
      const timer = setTimeout(() => reject(new Error('题图加载超时，未开始打印。')), 15000);
      img.onload = () => { clearTimeout(timer); img.naturalWidth ? resolve() : reject(new Error('题图未加载。')); };
      img.onerror = () => { clearTimeout(timer); reject(new Error('题图加载失败，未开始打印。')); };
    })));
    printDialog.close();
    window.print();
  } catch (error) {
    printSummary.textContent = error.message;
    announce(error.message);
  } finally {
    printing = false;
  }
}
printForm.addEventListener('submit', event => { event.preventDefault(); printNow(); });
document.querySelector('#print-now').addEventListener('click', printNow);
addEventListener('beforeprint', buildPrintOutput);
