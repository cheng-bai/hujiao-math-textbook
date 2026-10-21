/* A shared reading gate, not authentication or protection for public files. */
(() => {
  'use strict';
  const key = ['hujiao', 'textbook', 'reading', 'gate', 'v1'].join('.');
  const passphrase = 'xdf3.1415926';
  const root = document.documentElement;
  let granted = false;
  try { granted = sessionStorage.getItem(key) === 'granted'; } catch (_) { /* File storage can be unavailable. */ }
  root.dataset.accessState = granted ? 'granted' : 'locked';

  function mount() {
    const gate = document.createElement('section');
    gate.id = 'site-access';
    gate.setAttribute('aria-labelledby', 'access-title');
    gate.innerHTML = `<div class="access-card"><p class="access-eyebrow">SHANGHAI MATHEMATICS</p>
      <div class="access-rule" aria-hidden="true"></div><h1 id="access-title">沪教数学<br><span>教材与交互阅读</span></h1>
      <p class="access-intro">教材、教参与数学图景，在同一处阅读。</p>
      <form id="access-form"><label for="access-passphrase">输入访问口令</label>
      <input id="access-passphrase" name="passphrase" type="password" autocomplete="off" required aria-describedby="access-error access-help">
      <p id="access-error" role="alert"></p><button type="submit">进入阅读 <span aria-hidden="true">→</span></button></form>
      <p id="access-help">本标签页通过后，可继续浏览各章节。关闭标签页后需重新输入。</p>
      <p class="access-boundary">简易阅读入口 · 非账号认证，不用于保护私密材料。</p></div>`;
    document.body.prepend(gate);
    const input = gate.querySelector('input');
    const error = gate.querySelector('#access-error');
    let previousFocus = null;

    function unlock() {
      try { sessionStorage.setItem(key, 'granted'); } catch (_) { /* Unlock this page even without storage. */ }
      root.dataset.accessState = 'granted';
      gate.hidden = true;
      input.value = '';
      input.removeAttribute('aria-invalid');
      error.textContent = '';
      const target = previousFocus?.isConnected ? previousFocus :
        document.querySelector('.book-shell main, body > main, .book-shell') ||
        [...document.querySelectorAll('h1')].find(el => !gate.contains(el));
      if (target) {
        if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
        target.focus({ preventScroll: true });
      }
      window.dispatchEvent(new Event('site-access-granted'));
      window.dispatchEvent(new Event('resize'));
    }

    gate.querySelector('form').addEventListener('submit', (event) => {
      event.preventDefault();
      if (input.value === passphrase) unlock();
      else {
        error.textContent = '口令不正确，请重新输入。';
        input.setAttribute('aria-invalid', 'true');
        input.focus();
        input.select();
      }
    });
    input.addEventListener('input', () => {
      error.textContent = '';
      input.removeAttribute('aria-invalid');
    });
    const lock = document.createElement('button');
    lock.type = 'button';
    lock.className = 'site-lock-action';
    lock.textContent = '锁定入口';
    lock.addEventListener('click', () => {
      previousFocus = document.activeElement;
      document.querySelectorAll('dialog[open]').forEach((dialog) => dialog.close());
      document.body.classList.remove('toc-open');
      try { sessionStorage.removeItem(key); } catch (_) { /* Same local fallback as above. */ }
      root.dataset.accessState = 'locked';
      gate.hidden = false;
      window.dispatchEvent(new Event('site-access-locked'));
      input.focus({ preventScroll: true });
    });
    (document.querySelector('.toolbar .controls') || document.body).append(lock);
    gate.hidden = granted;
    if (!granted) input.focus({ preventScroll: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
