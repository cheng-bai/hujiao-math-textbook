document.addEventListener('DOMContentLoaded', () => {
  let errors = 0;
  const formulas = [...document.querySelectorAll('.math')];
  formulas.forEach(element => {
    const expression = element.textContent;
    try {
      if (!window.katex) throw new Error('本地公式库未加载');
      window.katex.render(expression, element, {
        displayMode: element.classList.contains('display'),
        throwOnError: true, strict: 'ignore', trust: false
      });
    } catch (error) {
      errors += 1;
      element.textContent = expression;
      element.classList.add('math-unverified');
      element.title = '原稿公式未能渲染，请核对原件';
      const warning = document.createElement('span');
      warning.className = 'math-warning';
      warning.textContent = '〔原稿公式待核〕';
      element.after(warning);
    }
  });
  document.querySelector('#math-status').textContent = `${formulas.length} 处公式已处理，${errors} 处保留源码并标注待核。渲染检查不等于数学审校。`;
  document.documentElement.dataset.mathReady = 'true';
  const directory = document.querySelector('#directory');
  const toggle = document.querySelector('#open-directory');
  const setDirectory = open => {
    document.body.classList.toggle('directory-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    if (open) document.querySelector('#search').focus();
    else if (matchMedia('(max-width:800px)').matches) toggle.focus();
  };
  toggle.addEventListener('click', () => setDirectory(true));
  document.querySelector('#close-directory').addEventListener('click', () => setDirectory(false));
  document.querySelector('#directory-backdrop').addEventListener('click', () => setDirectory(false));
  directory.querySelectorAll('nav a').forEach(link => link.addEventListener('click', () => setDirectory(false)));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && document.body.classList.contains('directory-open')) setDirectory(false);
  });
  const reveal = element => {
    for (let parent = element.parentElement; parent; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS') parent.open = true;
    }
  };
  const revealHash = () => {
    if (!location.hash) return;
    const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (target) { reveal(target); target.scrollIntoView({ block: 'start' }); }
  };
  window.addEventListener('hashchange', revealHash);
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#case-"]');
    if (link && link.hash === location.hash) revealHash();
  });
  revealHash();
  const entries = [...document.querySelectorAll('.reading-section p,.reading-section h2,.reading-section h3,.reading-section h4,.reading-section td,.reading-section th,.reading-section li')].filter(element => !element.closest('.curriculum-case[data-case-primary="false"]') && (!element.matches('td,th,li') || !element.querySelector(':scope > p,:scope > li'))).map((element, index) => {
    element.id ||= `passage-${index}`;
    const copy = element.cloneNode(true);
    copy.querySelectorAll('.katex-mathml').forEach(node => node.remove());
    copy.querySelectorAll('.case-group').forEach(node => node.remove());
    return { element, text: copy.textContent.replace(/\s+/g, ' ').trim(), chapter: element.closest('section').querySelector('h2').textContent };
  });
  const search = document.querySelector('#search');
  const results = document.querySelector('#search-results');
  const status = document.querySelector('#search-status');
  const find = () => {
    results.replaceChildren();
    document.querySelectorAll('.search-hit').forEach(node => node.classList.remove('search-hit'));
    const query = search.value.trim().toLocaleLowerCase();
    if (!query) {
      status.textContent = '输入关键词，定位到原文段落';
      return;
    }
    const matches = entries.filter(entry => entry.text.toLocaleLowerCase().includes(query));
    status.textContent = matches.length ? `找到 ${matches.length} 处${matches.length > 40 ? '，显示前 40 处；可输入更具体关键词' : '，点击跳到原文'}` : '没有匹配结果，试试更短的关键词';
    matches.slice(0, 40).forEach(entry => {
      const button = document.createElement('button');
      button.type = 'button';
      const chapter = document.createElement('small');
      chapter.textContent = entry.chapter;
      const start = Math.max(0, entry.text.toLocaleLowerCase().indexOf(query) - 22);
      button.append(chapter, document.createTextNode(`${start ? '…' : ''}${entry.text.slice(start, start + 85)}${entry.text.length > start + 85 ? '…' : ''}`));
      button.addEventListener('click', () => {
        document.querySelectorAll('.search-hit').forEach(node => node.classList.remove('search-hit'));
        entry.element.classList.add('search-hit');
        setDirectory(false);
        reveal(entry.element);
        location.hash = entry.element.id;
        entry.element.scrollIntoView({ block: 'start' });
      });
      results.append(button);
    });
  };
  search.addEventListener('input', find);
  document.querySelector('#clear-search').addEventListener('click', () => { search.value = ''; find(); search.focus(); });
  const links = [...document.querySelectorAll('.chapter-link')];
  const observer = new IntersectionObserver(records => {
    const visible = records.filter(record => record.isIntersecting).sort((first, second) => first.boundingClientRect.top - second.boundingClientRect.top)[0];
    if (!visible) return;
    links.forEach(link => {
      const active = link.hash === `#${visible.target.id}` || decodeURIComponent(link.hash) === `#${visible.target.id}`;
      link.classList.toggle('active', active);
      if (active) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  }, { rootMargin: '-70px 0px -55% 0px' });
  document.querySelectorAll('.reading-section h2').forEach(heading => observer.observe(heading));
});
