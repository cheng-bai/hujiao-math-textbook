#!/usr/bin/env python3
"""Verify real Chrome pagination with out-of-flow start/end diagnostic markers."""

from project_paths import use_project_root, launch_browser
use_project_root()
from pathlib import Path
import json
import re
import shutil

import fitz
from playwright.sync_api import sync_playwright

from test_print import OUT, ready, choose

REPORT = OUT / 'verification/打印紧凑与整题分页'
CHECKS = []


def check(label, passed):
    CHECKS.append({'check': label, 'passed': bool(passed)})
    assert passed, label


def marker_pages(path):
    with fitz.open(path) as doc:
        texts = [page.get_text() for page in doc]
    positions = {}
    for page_no, text in enumerate(texts, 1):
        for token in re.findall(r'ZQ\d{2}(?:HEADSTART|HEADEND|START|END)', text):
            positions.setdefault(token, []).append(page_no)
    return texts, positions


def main():
    REPORT.mkdir(exist_ok=True)
    runs = []
    with sync_playwright() as pw:
        browser = launch_browser(pw, headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, offline=True)
        ready(page, OUT / '8.1-向量的概念和线性运算.html')
        page.evaluate('''() => {
          window.paginationFixture = {markers:false, oversized:false};
          addEventListener('beforeprint', () => {
            const fixture = window.paginationFixture;
            const questions = [...document.querySelectorAll('#print-output .question')];
            if (fixture.oversized) {
              const answer = questions[0].querySelector('.answer-body');
              for (let i=1; i<=100; i++) {
                const p = document.createElement('p');
                p.textContent = `LONGANSWER${String(i).padStart(3,'0')} 用于验证超过一页的解析自然续页，不能裁切或丢失内容。`;
                answer.append(p);
              }
            }
            if (!fixture.markers) return;
            questions.forEach((q, i) => {
              const head = q.querySelector('.print-question-head');
              const leaves = root => [...root.querySelectorAll('p,li,h4,.question-label')];
              const wholeLeaves = leaves(q), headLeaves = leaves(head);
              for (const [suffix, target, start] of [
                ['START',wholeLeaves[0],true], ['END',wholeLeaves.at(-1),false],
                ['HEADSTART',headLeaves[0],true], ['HEADEND',headLeaves.at(-1),false]
              ]) {
                const marker = document.createElement('span');
                marker.textContent = `ZQ${String(i+1).padStart(2,'0')}${suffix}`;
                target.style.position = 'relative';
                marker.style.cssText = `position:absolute;${start ? 'top:2px' : 'bottom:2px'};left:${suffix.startsWith('HEAD') ? 30 : 0}px;font:2px/2px Arial;letter-spacing:0;white-space:nowrap;margin:0;padding:0;border:0`;
                target.append(marker);
              }
            });
          });
        }''')
        for mode, notes in [('questions', False), ('answers', False), ('all', True)]:
            choose(page, mode, notes=notes)
            labels = page.locator('#print-output .question-label').all_text_contents()
            normal = REPORT / f'compact-{mode}{"-notes" if notes else ""}.pdf'
            page.pdf(path=str(normal), prefer_css_page_size=True)
            page.evaluate('window.paginationFixture.markers = true')
            diagnostic = REPORT / f'diagnostic-{mode}.pdf'
            page.pdf(path=str(diagnostic), prefer_css_page_size=True)
            page.evaluate('window.paginationFixture.markers = false')
            texts, positions = marker_pages(diagnostic)
            with fitz.open(normal) as doc:
                check(mode + ' 诊断标记不改变页数', len(doc) == len(texts))
                check(mode + ' 正式PDF不含诊断标记', all('ZQ01START' not in p.get_text() for p in doc))
                with fitz.open(diagnostic) as marked:
                    def words(pdf_page):
                        return sorted((tuple(round(v, 2) for v in w[:4]), w[4])
                                      for w in pdf_page.get_text('words') if 'ZQ' not in w[4])
                    check(mode + ' 诊断标记不改变每页正文及坐标', all(words(a) == words(b) for a, b in zip(doc, marked)))
            assignments = []
            for i, label in enumerate(labels, 1):
                prefix = f'ZQ{i:02d}'
                locations = {key: positions.get(prefix + key, []) for key in ['START', 'END', 'HEADSTART', 'HEADEND']}
                check(f'{mode} 第{i}题四个标记均唯一', all(len(v) == 1 for v in locations.values()))
                check(f'{mode} 第{i}题整题与所选答案批注同页', locations['START'] == locations['END'])
                check(f'{mode} 第{i}题题号题干同页', locations['HEADSTART'] == locations['HEADEND'])
                assignments.append({'index': i, 'label': label, 'pages': locations})
            runs.append({'mode': mode, 'notes': notes, 'pages': len(texts), 'questions': assignments})

        choose(page, 'answers', scopes=['concept'], categories=['example'])
        page.evaluate('window.paginationFixture = {markers:true,oversized:true}')
        oversized = REPORT / 'diagnostic-oversized-answer.pdf'
        page.pdf(path=str(oversized), prefer_css_page_size=True)
        texts, positions = marker_pages(oversized)
        check('超长解析允许跨页而非强行缩小', positions['ZQ01START'][0] < positions['ZQ01END'][0])
        check('超长解析仍保持题号题干完整同页', positions['ZQ01HEADSTART'] == positions['ZQ01HEADEND'])
        check('超长解析全部100段均保留且各出现一次', all('\n'.join(texts).count(f'LONGANSWER{i:03d}') == 1 for i in range(1, 101)))
        browser.close()

    baseline = json.loads((REPORT / 'before-pages.json').read_text(encoding='utf-8'))
    latest = json.loads((OUT / 'verification/密度与打印优化/browser-print-report.json').read_text(encoding='utf-8'))
    comparison = []
    for old, new in zip(baseline, latest['pdfs']):
        check(new['file'] + ' 紧凑版页数不增加', new['pages'] <= old['pages'])
        shutil.copy2(OUT / 'verification/密度与打印优化' / new['file'], REPORT / new['file'])
        comparison.append({'file': new['file'], 'before': old['pages'], 'after': new['pages']})
    result = {'passed': len(CHECKS), 'checks': CHECKS, 'comparison': comparison, 'pagination': runs,
              'limits': ['Chrome A4 100% CSS分页；不保证其他纸型、缩放和浏览器相同',
                         '标记仅用于独立诊断PDF；正式PDF和网页不含标记',
                         '超出一页的题干或解析只能合理续页，不能承诺任意长题整题同页']}
    (REPORT / 'pagination-report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': len(CHECKS), 'comparison': comparison}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
