#!/usr/bin/env python3
"""Exercise modular print choices, isolation, real A4 output and reading density."""

from project_paths import use_project_root, launch_browser
use_project_root()
from pathlib import Path
import json

import fitz
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'designs/2026-10-19-沪教版教材教参整合样章'
REPORT = OUT / 'verification/密度与打印优化'
CHECKS = []


def check(label, passed):
    CHECKS.append({'check': label, 'passed': bool(passed)})
    assert passed, label


def ready(page, path):
    page.goto(path.as_uri())
    page.wait_for_function('document.documentElement.dataset.math === "rendered" && [...document.images].every(i => i.complete && i.naturalWidth > 0)')
    page.evaluate('document.fonts.ready')


def choose(page, mode, scopes=None, categories=None, notes=False):
    page.evaluate('''({mode, scopes, categories, notes}) => {
      document.querySelector(`[name="print-mode"][value="${mode}"]`).checked = true;
      document.querySelectorAll('[name="print-module"]').forEach(el => el.checked = scopes === null || scopes.includes(el.value));
      document.querySelectorAll('[name="print-category"]').forEach(el => el.checked = categories === null || categories.includes(el.value));
      const n = document.querySelector('#print-notes'); if(n) n.checked = notes;
      document.querySelector('#print-form').dispatchEvent(new Event('change', {bubbles:true}));
      window.dispatchEvent(new Event('beforeprint'));
    }''', {'mode': mode, 'scopes': scopes, 'categories': categories, 'notes': notes})


def snapshot(page):
    return page.evaluate('''() => ({
      classes:document.body.className,
      open:[...document.querySelectorAll('.book-body details')].map(el=>el.open),
      answer:document.querySelector('#answer-toggle')?.getAttribute('aria-pressed'),
      notes:document.querySelector('#notes-toggle')?.getAttribute('aria-pressed')
    })''')


def pdf(page, filename, expected_questions):
    page.pdf(path=str(REPORT / filename), prefer_css_page_size=True, print_background=False)
    doc = fitz.open(REPORT / filename)
    texts = [p.get_text() for p in doc]
    check(filename + ' 为A4且无空白页', all(abs(p.rect.width - 595.3) < 2 and abs(p.rect.height - 841.9) < 2 and len(t.strip()) > 20 for p, t in zip(doc, texts)))
    check(filename + ' 保留所选题数', page.locator('#print-output .question').count() == expected_questions)
    outside = []
    for index, p in enumerate(doc):
        for word in p.get_text('words'):
            if word[0] < -1 or word[1] < -1 or word[2] > p.rect.width + 1 or word[3] > p.rect.height + 1:
                outside.append(index + 1)
    check(filename + ' 文本无越出物理页边界', not outside)
    data = {'file': filename, 'pages': len(doc), 'text_characters': [len(t) for t in texts]}
    doc.close()
    return data, '\n'.join(texts)


def main():
    REPORT.mkdir(exist_ok=True)
    before = json.loads((REPORT / 'density-before.json').read_text(encoding='utf-8'))
    densities, pdfs = {}, []
    with sync_playwright() as pw:
        browser = launch_browser(pw, headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, offline=True, reduced_motion='reduce')
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        ready(page, OUT / '8.1-向量的概念和线性运算.html')
        for name, width, height in [('desktop', 1440, 1000), ('mobile', 390, 844)]:
            page.set_viewport_size({'width': width, 'height': height})
            densities[name] = page.evaluate('({height:document.documentElement.scrollHeight,cover:document.querySelector(".chapter-cover").getBoundingClientRect().height,font:getComputedStyle(document.body).fontSize})')
            check(name + ' 内容未缩字号且页面变短', densities[name]['font'] == before[name]['font'] and densities[name]['height'] < before[name]['height'] * .9)
            check(name + ' 无页面横向溢出', page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
            page.evaluate('scrollTo({top:0,behavior:"instant"})')
            page.screenshot(path=str(REPORT / f'{name}-after.png'))
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.locator('#density-toggle').click()
        check('可恢复舒展版且37题未变', page.locator('body.spacious').count() == 1 and page.locator('.book-body .question').count() == 37)
        page.locator('#density-toggle').click()
        page.locator('.answer').first.locator('summary').click()
        page.locator('#answer-toggle').click()
        page.locator('#notes-toggle').click()
        state = snapshot(page)
        page.locator('#print-open').click()
        check('打印设置可打开且初始范围37题', page.locator('#print-dialog').evaluate('(el)=>el.open') and '37 道题' in page.locator('#print-summary').inner_text())
        page.screenshot(path=str(REPORT / 'desktop-print-dialog.png'))
        page.set_viewport_size({'width': 390, 'height': 844})
        check('手机打印面板完整落在视口内', page.locator('#print-dialog').evaluate('(el)=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight}'))
        check('手机打印操作按钮在面板首屏可见', page.locator('#print-submit').evaluate('(el)=>{const r=el.getBoundingClientRect();const d=el.closest("dialog").getBoundingClientRect();return r.top>=d.top&&r.bottom<=d.bottom}'))
        page.screenshot(path=str(REPORT / 'mobile-print-dialog.png'))
        page.keyboard.press('Escape')
        check('Escape关闭并归还焦点', not page.locator('#print-dialog').evaluate('(el)=>el.open') and page.locator('#print-open').evaluate('(el)=>el===document.activeElement'))
        page.set_viewport_size({'width': 1440, 'height': 1000})
        for mode, qcount, acount, prose in [('questions', 37, 0, False), ('answers', 37, 37, False), ('text', 0, 0, True), ('all', 37, 37, True)]:
            choose(page, mode)
            check(mode + ' 题答数量正确', page.locator('#print-output .question').count() == qcount and page.locator('#print-output .print-answer').count() == acount)
            check(mode + ' 正文及教师内容过滤正确', (page.locator('#print-output .prose').count() > 0) == prose and page.locator('#print-output .teacher,#print-output .editor,#print-output .print-commentary').count() == 0)
            data, text = pdf(page, f'print-{mode}.pdf', qcount)
            pdfs.append(data)
            if mode in ('questions', 'text'):
                check(mode + ' PDF不含答案栏目或教参分析', '答案与解析' not in text and '教参原文' not in text and '编辑增补' not in text)
            if mode == 'answers':
                check('答案PDF包含实际37个答案标题', text.count('答案与解析') == 37)
            check(mode + ' 打印不改变原阅读隐藏或展开状态', snapshot(page) == state)
        for category, expected in [('example', 8), ('practice', 9), ('homework', 20)]:
            choose(page, 'questions', categories=[category], notes=True)
            check(category + ' 题目类别筛选正确且强制排除批注', page.locator('#print-output .question').count() == expected and not page.locator('#print-output .print-answer,#print-output .teacher,#print-output .editor,#print-output .print-commentary').count())
        choose(page, 'answers', scopes=['multiplication'], categories=['example'], notes=True)
        check('章节与题型组合筛选3个数乘例题', page.locator('#print-output .question').count() == page.locator('#print-output .print-answer').count() == 3 and page.locator('#print-output .print-module').count() == 1)
        check('主动勾选教参批注时不受屏幕隐藏影响', page.locator('#print-output .teacher').count() > 0 and page.locator('#print-output .print-commentary').count() == 3)
        choose(page, 'text', scopes=['homework'])
        check('无正文范围阻止空白打印', page.locator('#print-submit').is_disabled() and page.locator('#print-preview').is_disabled())
        page.evaluate('()=>{window.printCalls=0;window.print=()=>{window.printCalls++;window.dispatchEvent(new Event("beforeprint"));window.dispatchEvent(new Event("afterprint"))}}')
        page.evaluate('document.querySelector("#print-form").requestSubmit()')
        check('空范围即使程序提交也不调用打印', page.evaluate('window.printCalls') == 0)
        choose(page, 'answers', scopes=['multiplication'], categories=['example'])
        page.locator('#print-open').click()
        page.locator('#print-preview').click()
        check('内容预览只显示所选内容且焦点可返回', page.locator('body.print-preview').count() == 1 and page.locator('#print-back').evaluate('(el)=>el===document.activeElement') and not page.locator('.book-shell').is_visible())
        page.screenshot(path=str(REPORT / 'print-preview.png'))
        page.locator('#print-now').click()
        page.wait_for_function('window.printCalls === 1')
        check('打印按钮等待资源后调用系统打印一次', page.evaluate('window.printCalls') == 1)
        page.locator('#print-back').click()
        check('退出预览保留原阅读状态', snapshot(page) == state and page.locator('.book-shell').is_visible())
        ready(page, OUT / '8.1-向量的概念和线性运算-s.html')
        check('学生版不提供题答打印或教师选项', page.locator('[name="print-mode"][value="answers"],#print-notes,#print-sources').count() == 0)
        choose(page, 'all')
        check('学生完整打印仍无答案或教师点评', page.locator('#print-output .question').count() == 37 and not page.locator('#print-output .print-answer,#print-output .teacher,#print-output .editor').count())
        choose(page, 'questions', scopes=['multiplication'])
        data, text = pdf(page, 'print-student-selected.pdf', 6)
        pdfs.append(data)
        check('学生所选PDF不含答案', '答案与解析' not in text and '教参原文' not in text)
        check('全过程无浏览器异常', not errors)
        browser.close()
    report = {'checks': CHECKS, 'passed': len(CHECKS), 'density_before': before, 'density_after': densities, 'pdfs': pdfs, 'limits': ['Chrome系统打印路径与浏览器PDF验证，未实测实体打印机、Safari或Firefox', 'PDF视觉检查另记，不以文本提取代替目视验收', '源教材正文与题答未重写，保留原有图略和证明略']}
    (REPORT / 'browser-print-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
