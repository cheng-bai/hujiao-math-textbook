#!/usr/bin/env python3
"""Offline browser checks, source integrity checks and physical student isolation."""

from project_paths import use_project_root, launch_browser
use_project_root()
from pathlib import Path
import hashlib
import json
import re
import tempfile
import zipfile

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'designs/2026-10-19-沪教版教材教参整合样章'
REPORT = OUT / 'verification'
REPORT.mkdir(exist_ok=True)
MODEL = json.loads((OUT / 'content/8.1-整合底稿.json').read_text(encoding='utf-8'))
SOURCE = json.loads((OUT / 'content/来源与编辑记录.json').read_text(encoding='utf-8'))
TEACHER = OUT / '8.1-向量的概念和线性运算.html'
STUDENT = OUT / '8.1-向量的概念和线性运算-s.html'
CHECKS = []


def check(label, condition):
    CHECKS.append({'check': label, 'passed': bool(condition)})
    assert condition, label


def formula_count(student=False):
    count = 0
    for b in MODEL:
        if student and (b.get('teacher_only') or b['type'] in ['intro', 'teacher', 'editor']):
            continue
        strings = [b['markdown']]
        if b['type'] == 'question' and not student:
            strings += [b['answer'], b['teacher_analysis']]
        count += sum(len(re.findall(r'\$\$[\s\S]*?\$\$|(?<!\$)\$(?!\$)[^$\n]+\$', s)) for s in strings)
    return count


def load_images(page):
    page.evaluate('document.querySelectorAll("img").forEach(i => i.loading = "eager")')
    page.wait_for_function('[...document.images].every(i => i.complete)', timeout=20000)
    return page.evaluate('[...document.images].every(i => i.naturalWidth > 0)')


def screenshot_at(page, selector, filename):
    page.evaluate('document.querySelector("#status").classList.remove("visible")')
    page.locator(selector).evaluate('(el) => el.scrollIntoView({block:"start", behavior:"instant"})')
    page.screenshot(path=str(REPORT / filename))


def main():
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    baseline = json.loads((REPORT / 'highlight-baseline.json').read_text(encoding='utf-8'))
    clean = [{k: v for k, v in b.items() if k != 'emphases'} for b in MODEL]
    check('醒目标注不改变已有正文、题答与来源', hashlib.sha256(json.dumps(clean, ensure_ascii=False, sort_keys=True).encode()).hexdigest() == baseline['content_sha256'])
    check('原教材、教参源文件哈希未变', all(sha(p) == v for p, v in SOURCE['source_hashes'].items()))
    check('图片复制哈希一致', all(sha(OUT / p) == v['sha256'] for p, v in SOURCE['assets'].items()))
    qs = [b for b in MODEL if b['type'] == 'question']
    check('8例题29练习习题，37个唯一稳定题目ID', len(qs) == 37 and len({q['id'] for q in qs}) == 37 and sum(q['category'] == '例题' for q in qs) == 8)
    text = STUDENT.read_text(encoding='utf-8')
    check('学生HTML不含答案、教师块、来源快照链接或教师页入口', all(s not in text for s in ['class="answer"', 'class="teacher ', 'class="editor ', 'question-analysis', 'sources/', '隐藏全部答案', '8.1-向量的概念和线性运算.html']))
    with zipfile.ZipFile(OUT / '8.1-学生阅读包.zip') as z:
        check('学生包CRC通过', z.testzip() is None)
        names = z.namelist()
        check('学生包不含教师页面、私有底稿或来源', all(not n.startswith(('sources/', 'content/')) and n != TEACHER.name for n in names))
        check('学生包不含教参专属图片', not any(n.startswith('images/teacher-') for n in names))
    with sync_playwright() as pw:
        browser = launch_browser(pw, headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1, offline=True, reduced_motion='reduce')
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(TEACHER.as_uri())
        page.wait_for_function('!!window.__mathRendered')
        result = page.evaluate('async()=>{await window.__mathRendered;await document.fonts.ready;return {errors:window.__mathErrors, rendered:document.querySelectorAll(".katex").length, source:document.querySelectorAll("[data-tex]").length}}')
        (REPORT / 'math-initial.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        check('教师公式渲染无错误', not result['errors'])
        check('教师公式数量等于底稿独立统计', result['rendered'] == result['source'] == formula_count())
        check('教师题目和答案各37块', page.locator('.question').count() == page.locator('.answer').count() == 37)
        check('教师默认答案可见', page.locator('.answer[open]').count() == 37)
        check('8处醒目标注含概念、公式、方法与条件四类', page.locator('.key-point').count() == 8 and set(page.locator('.key-point').evaluate_all('(els)=>els.map(e=>e.dataset.emphasis)')) == {'concept', 'formula', 'method', 'condition'})
        check('教师全部原图离线加载完整', load_images(page))
        first = page.locator('.answer').first
        first.locator('summary').click()
        check('单题折叠可用', first.get_attribute('open') is None)
        first.locator('summary').click()
        page.locator('#answer-toggle').click()
        check('一键隐藏全部答案与例题提示', page.locator('.answer:visible').count() == page.locator('.question-analysis:visible').count() == 0)
        page.locator('#answer-toggle').click()
        check('一键恢复全部答案', page.locator('.answer[open]:visible').count() == 37)
        page.locator('#notes-toggle').click()
        check('隐藏教师批注', page.locator('.teacher-only:visible').count() == 0)
        page.locator('#notes-toggle').click()
        screenshot_at(page, 'body', 'desktop-cover.png')
        screenshot_at(page, '#bx2-c8-s81-ex5', 'desktop-example5.png')
        screenshot_at(page, '#multiplication', 'desktop-concept3.png')
        screenshot_at(page, '#key-scalar-laws', 'desktop-key-formulas.png')
        check('教师桌面无页面横向溢出', page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
        page.set_viewport_size({'width': 390, 'height': 844})
        screenshot_at(page, 'body', 'mobile-cover.png')
        check('移动端无页面横向溢出', page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
        screenshot_at(page, '#bx2-c8-s81-ex6', 'mobile-example6.png')
        screenshot_at(page, '#key-parallel-condition', 'mobile-key-conditions.png')
        check('手机重点框无页面横向溢出', page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
        page.set_viewport_size({'width': 1440, 'height': 1000})
        page.goto(STUDENT.as_uri())
        page.wait_for_function('document.documentElement.dataset.math === "rendered"')
        result_s = page.evaluate('({errors:window.__mathErrors,rendered:document.querySelectorAll(".katex").length})')
        check('学生公式数与底稿独立统计一致且无错误', not result_s['errors'] and result_s['rendered'] == formula_count(True))
        check('学生DOM真实不存在答案或教师内容', page.locator('.answer,.teacher-only,.question-analysis').count() == 0)
        check('学生仍保留37道完整题块', page.locator('.question').count() == 37)
        check('学生保留8个通用知识标注而非题后提示', page.locator('.key-point').count() == 8 and page.locator('.question .key-point').count() == 0)
        check('学生原图加载完整', load_images(page))
        page.screenshot(path=str(REPORT / 'student-cover.png'))
        with tempfile.TemporaryDirectory(prefix='hujiao-student-test-') as tmp:
            with zipfile.ZipFile(OUT / '8.1-学生阅读包.zip') as z:
                z.extractall(tmp)
            page.goto((Path(tmp) / STUDENT.name).as_uri())
            page.wait_for_function('document.documentElement.dataset.math === "rendered"')
            check('学生ZIP解压后独立离线打开且无答案', page.locator('.katex').count() == formula_count(True) and page.locator('.answer,.teacher-only,.question-analysis').count() == 0 and load_images(page))
        check('浏览器无脚本运行异常', not errors)
        context.close()
        browser.close()
    report = {'checks': CHECKS, 'passed': len(CHECKS), 'teacher_formulas': formula_count(), 'student_formulas': formula_count(True), 'limitations': ['截图为抽查，不是逐屏视觉验收', '未测试所有浏览器或屏幕宽度', '保留原解中的图略、证明略，不等于已补全逐题详解']}
    (REPORT / 'browser-and-integrity.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
