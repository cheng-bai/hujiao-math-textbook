#!/usr/bin/env python3
"""Check section 8.2 sources, offline editions, modular printing and real pagination."""

from project_paths import use_project_root, launch_browser
use_project_root()
from pathlib import Path
import hashlib
import itertools
import json
import re
import tempfile
import zipfile

import fitz
from playwright.sync_api import sync_playwright

from build_section82 import OUT, PARENT, STEM
from test_print import choose, ready

REPORT = OUT / 'verification'
MODEL = json.loads((OUT / 'content/8.2-整合底稿.json').read_text(encoding='utf-8'))
SOURCE = json.loads((OUT / 'content/来源与编辑记录.json').read_text(encoding='utf-8'))
QUESTIONS = [b for b in MODEL if b['type'] == 'question']
CHECKS = []


def check(label, condition):
    CHECKS.append({'check': label, 'passed': bool(condition)})
    assert condition, label


def formula_count(student=False):
    strings = []
    for block in MODEL:
        if student and (block.get('teacher_only') or block['type'] in ['intro', 'teacher', 'editor']):
            continue
        strings.append(block['markdown'])
        if block['type'] == 'question' and not student:
            strings.extend([block['answer'], block['teacher_analysis']])
    return sum(len(re.findall(r'\$\$[\s\S]*?\$\$|(?<!\$)\$(?!\$)[^$\n]+\$', text)) for text in strings)


def source_checks():
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    old = json.loads((PARENT / 'verification/8.2/8.1-existing-assets-before.json').read_text(encoding='utf-8'))
    check('8.1原成品、底稿与资源均未修改', all(sha(PARENT / p) == digest for p, digest in old.items()))
    check('源教材与教参哈希未变', all(sha(p) == digest for p, digest in SOURCE['source_hashes'].items()))
    check('两份来源快照与原文件一致', sorted(sha(p) for p in (OUT / 'sources').glob('*.md')) == sorted(SOURCE['source_hashes'].values()))
    check('7张原图复制哈希一致', len(SOURCE['assets']) == 7 and all(sha(OUT / p) == data['sha256'] for p, data in SOURCE['assets'].items()))
    check('6例题26练习习题且32个唯一题目ID', len(QUESTIONS) == len({q['id'] for q in QUESTIONS}) == 32 and sum(q['category'] == '例题' for q in QUESTIONS) == 6)
    check('源正文与教参实质行覆盖无缺口', not any(SOURCE['coverage']['missing_substantive_lines'].values()))
    check('32道题的题干、答案和出处齐全', all(q['markdown'].strip() and q['answer'].strip() and q['provenance_question'] and q['answer_provenance'] for q in QUESTIONS))
    check('所有来源行号都在章节相应范围内', all(481 <= ref['start'] <= ref['end'] <= 806 for q in QUESTIONS for ref in q['provenance_question']))
    laws = next(b['markdown'] for b in MODEL if b['type'] == 'prose' and '若 $\\lambda  > 0$' in b['markdown'])
    positive, negative = laws.split('若 $\\lambda  > 0$')[1].split('若 $\\lambda  < 0$')
    check('数乘证明正负分类修复且负系数模长式未丢失', '=  - \\lambda' not in positive and '=  - \\lambda' in negative)
    by_id = {q['id']: q for q in QUESTIONS}
    check('B5和B8点积已显式恢复', '$ . $' not in by_id['bx2-c8-s82-b-q5']['markdown'] and '$ . $' not in by_id['bx2-c8-s82-b-q8']['markdown'])
    check('保留略证而不冒充补写完整解答', any('证明略' in q['answer'] for q in QUESTIONS))
    check('7处编辑变化有明确记录', len(SOURCE['edits']) == 7 and all(e['before'] and e['after'] and e['reason'] for e in SOURCE['edits']))
    student = (OUT / f'{STEM}-s.html').read_text(encoding='utf-8')
    check('学生HTML物理排除教师答案、背景、追溯与教师入口', all(x not in student for x in ['class="answer"', 'teacher-only', 'question-analysis', 'sources/', 'images/teacher-', f'href="{STEM}.html"', '隐藏全部答案', '零向量与夹角公式的边界']))
    with zipfile.ZipFile(OUT / '8.2-学生阅读包.zip') as archive:
        check('学生ZIP CRC通过', archive.testzip() is None)
        check('学生包无来源底稿、教师页面或教师图片', all(not n.startswith(('sources/', 'content/', 'verification/', 'images/teacher-')) and n != f'{STEM}.html' for n in archive.namelist()))


def inject_markers(page):
    page.evaluate('''() => {
      window.paginationMarkers = false;
      addEventListener('beforeprint', () => {
        if (!window.paginationMarkers) return;
        document.querySelectorAll('#print-output .question').forEach((q, i) => {
          const leaves = [...q.querySelectorAll('p,li,h4,.question-label')];
          for (const [suffix, host] of [['START',leaves[0]], ['END',leaves.at(-1)]]) {
            const marker = document.createElement('span');
            marker.textContent = `ZQ${String(i+1).padStart(2,'0')}${suffix}`;
            host.style.position = 'relative';
            marker.style.cssText = `position:absolute;left:0;${suffix==='START'?'top:2px':'bottom:2px'};font:2px/2px Arial;letter-spacing:0;white-space:nowrap`;
            host.append(marker);
          }
        });
      });
    }''')


def print_pdf(page, name, expected, paginate=True):
    normal = REPORT / f'{name}.pdf'
    page.pdf(path=str(normal), prefer_css_page_size=True, print_background=False)
    with fitz.open(normal) as pdf:
        metadata = pdf.metadata
        metadata['author'] = 'chengbai'
        pdf.set_metadata(metadata)
        pdf.saveIncr()
        pages = len(pdf)
        texts = [p.get_text() for p in pdf]
        check(name + ' 署名仅存于作者元数据', pdf.metadata['author'] == 'chengbai' and all('chengbai' not in text for text in texts))
        check(name + ' A4且无空白页', all(abs(p.rect.width - 595.3) < 2 and abs(p.rect.height - 841.9) < 2 and len(text.strip()) > 20 for p, text in zip(pdf, texts)))
        check(name + ' 文字无超出纸面', all(w[0] >= -1 and w[1] >= -1 and w[2] <= p.rect.width + 1 and w[3] <= p.rect.height + 1 for p in pdf for w in p.get_text('words')))
        check(name + ' 正确8.2标题且无8.1误标', '8.2 向量的数量积' in texts[0] and '8.1 向量的概念和线性运算' not in texts[0])
        check(name + ' 保留所选题数', page.locator('#print-output .question').count() == expected)
        if paginate and expected:
            page.evaluate('window.paginationMarkers = true')
            diagnostic = REPORT / f'{name}-diagnostic.pdf'
            page.pdf(path=str(diagnostic), prefer_css_page_size=True)
            page.evaluate('window.paginationMarkers = false')
            with fitz.open(diagnostic) as marked:
                check(name + ' 诊断不改变页数', len(marked) == len(pdf))
                def words(p):
                    return sorted((tuple(round(v, 2) for v in w[:4]), w[4]) for w in p.get_text('words') if 'ZQ' not in w[4])
                check(name + ' 诊断不改变每页正文坐标', all(words(a) == words(b) for a, b in zip(pdf, marked)))
                positions = {}
                for index, p in enumerate(marked, 1):
                    for token in re.findall(r'ZQ\d{2}(?:START|END)', p.get_text()):
                        positions.setdefault(token, []).append(index)
                for i in range(1, expected + 1):
                    start, end = positions.get(f'ZQ{i:02d}START', []), positions.get(f'ZQ{i:02d}END', [])
                    check(f'{name} 第{i}题完整同页', len(start) == len(end) == 1 and start == end)
    return {'file': normal.name, 'pages': pages, 'questions': expected}, '\n'.join(texts)


def browser_checks():
    pdfs = []
    with sync_playwright() as pw:
        browser = launch_browser(pw, headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, offline=True, reduced_motion='reduce')
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        ready(page, OUT / f'{STEM}.html')
        check('教师公式按底稿独立统计且无渲染错误', not page.evaluate('window.__mathErrors') and page.locator('.katex').count() == formula_count())
        check('教师32题32答案且默认展开', page.locator('.book-body .question').count() == page.locator('.book-body .answer[open]').count() == 32)
        check('11个重点框覆盖概念公式方法与条件', page.locator('.key-point').count() == 11 and set(page.locator('.key-point').evaluate_all('(els)=>els.map(el=>el.dataset.emphasis)')) == {'concept', 'formula', 'method', 'condition'})
        page.locator('.answer summary').first.click()
        check('单题可折叠', page.locator('.answer[open]').count() == 31)
        page.locator('.answer summary').first.click()
        page.locator('#answer-toggle').click()
        check('一键隐藏全部答案及题后分析', page.locator('.answer:visible,.question-analysis:visible').count() == 0)
        page.locator('#answer-toggle').click()
        page.locator('#notes-toggle').click()
        check('教师批注可整体隐藏', page.locator('.teacher-only:visible').count() == 0)
        page.locator('#notes-toggle').click()
        for name, width, height, selector in [
            ('desktop-cover', 1440, 1000, '#top'),
            ('desktop-projection', 1440, 1000, '#key-projection-formula'),
            ('desktop-laws', 1440, 1000, '#key-dot-laws'),
            ('mobile-cover', 390, 844, '#top'),
            ('mobile-projection', 390, 844, '#key-signed-projection'),
            ('mobile-example', 390, 844, '#bx2-c8-s82-ex4')]:
            page.set_viewport_size({'width': width, 'height': height})
            page.locator(selector).evaluate('(el)=>el.scrollIntoView({block:"start",behavior:"instant"})')
            page.evaluate('document.querySelector("#status").classList.remove("visible")')
            page.screenshot(path=str(REPORT / f'{name}.png'))
            check(name + ' 无页面横向溢出', page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
        page.locator('#print-open').click()
        check('手机打印弹窗与操作按钮可达', page.locator('#print-submit').evaluate('(el)=>{const a=el.getBoundingClientRect(),b=el.closest("dialog").getBoundingClientRect();return a.top>=b.top&&a.bottom<=b.bottom&&b.left>=0&&b.right<=innerWidth}'))
        page.keyboard.press('Escape')
        page.set_viewport_size({'width': 1440, 'height': 1000})
        original = page.locator('.book-body').inner_html()
        modules = ['projection', 'product', 'homework', 'sources']
        question_modules, active = {}, None
        for block in MODEL:
            if block['type'] == 'section':
                active = block['id']
            if block['type'] == 'question':
                question_modules[block['id']] = active
        for mode, scope, category, notes in itertools.product(
            ['all', 'text', 'questions', 'answers'], [None, [], *[[m] for m in modules]],
            [None, ['example'], ['practice'], ['homework']], [False, True]):
            choose(page, mode, scopes=scope, categories=category, notes=notes)
            selected = [] if mode == 'text' else [q for q in QUESTIONS if (scope is None or question_modules[q['id']] in scope)
                and (category is None or ('example' if q['category'] == '例题' else 'practice' if q['category'].startswith('练习') else 'homework') in category)]
            check(f'组合 {mode}/{scope}/{category}/{notes}', page.locator('#print-output .question').count() == len(selected)
                  and page.locator('#print-output .print-answer').count() == (len(selected) if mode in ['all', 'answers'] else 0)
                  and (mode != 'questions' or page.locator('#print-output .teacher,#print-output .editor,#print-output .print-commentary').count() == 0))
        check('全部192组合不改阅读正文DOM', page.locator('.book-body').inner_html() == original)
        inject_markers(page)
        for mode, notes in [('questions', False), ('answers', False), ('text', False), ('all', False), ('all', True)]:
            choose(page, mode, notes=notes)
            row, text = print_pdf(page, f'print-{mode}{"-notes" if notes else ""}', 0 if mode == 'text' else 32)
            pdfs.append(row)
            if mode in ['questions', 'text']:
                check(mode + ' PDF不含答案标题', '答案与解析' not in text)
        choose(page, 'answers', scopes=['projection'], categories=['example'], notes=True)
        row, _ = print_pdf(page, 'print-projection-examples', 2)
        pdfs.append(row)
        check('打印后阅读正文保持原状', page.locator('.book-body').inner_html() == original)
        check('空范围阻止页面打印按钮', (choose(page, 'questions', scopes=[]) is None) and page.locator('#print-submit').is_disabled())
        ready(page, OUT / f'{STEM}-s.html')
        check('学生公式计数一致且无错误', page.locator('.katex').count() == formula_count(True) and not page.evaluate('window.__mathErrors'))
        check('学生DOM不存在答案教师内容并保留32题11重点', page.locator('.answer,.teacher-only,.question-analysis').count() == 0 and page.locator('.question').count() == 32 and page.locator('.key-point').count() == 11)
        check('学生不提供答案及教参打印选项', page.locator('[name="print-mode"][value="answers"],#print-notes,#print-sources').count() == 0)
        inject_markers(page)
        choose(page, 'questions')
        row, text = print_pdf(page, 'print-student-questions', 32)
        pdfs.append(row)
        check('学生打印无答案标题和教师视角', '答案与解析' not in text and '教参视角' not in text)
        with tempfile.TemporaryDirectory(prefix='hujiao82-student-') as temp:
            with zipfile.ZipFile(OUT / '8.2-学生阅读包.zip') as archive:
                archive.extractall(temp)
            ready(page, Path(temp) / f'{STEM}-s.html')
            check('学生ZIP独立离线打开资源完整且无答案', page.locator('.katex').count() == formula_count(True) and page.locator('.question').count() == 32 and page.locator('.answer,.teacher-only').count() == 0)
        check('浏览器全过程无JS异常', not errors)
        browser.close()
    return pdfs


def main():
    REPORT.mkdir(exist_ok=True)
    source_checks()
    pdfs = browser_checks()
    report = {'checks': CHECKS, 'passed': len(CHECKS), 'teacher_formulas': formula_count(),
              'student_formulas': formula_count(True), 'pdfs': pdfs,
              'limits': ['Chrome离线网页与A4/100%打印；未实测其他浏览器及实体打印机',
                         '标记仅存在于diagnostic测试PDF；已核对不改变正常PDF逐页正文坐标',
                         '能在单页容纳的整题整体排；任意超长解析仍需续页',
                         '数学审校另记；结构与渲染通过不代替出版终审']}
    (REPORT / 'browser-and-print-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'checks'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
