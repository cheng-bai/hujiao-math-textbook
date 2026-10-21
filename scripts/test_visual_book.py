#!/usr/bin/env python3
"""Verify the X1 visualization add-on without changing textbook source content."""
from __future__ import annotations

from project_paths import use_project_root, launch_browser
use_project_root()

import json
import shutil
import zipfile
from pathlib import Path

import fitz
from playwright.sync_api import sync_playwright
from test_print import unlock_access

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'outputs/五册教材教参整合/x1'
EVIDENCE = OUTPUT / 'visual-verification'
TEACHER_ELLIPSE = OUTPUT / 'x1-2-2/teacher.html'
STUDENT_ELLIPSE = OUTPUT / 'x1-2-2/student.html'
TEACHER_PLANE = OUTPUT / 'x1-3-4/teacher.html'
STUDENT_ZIP = OUTPUT / 'x1-2-2/student.zip'
CHECKS: list[str] = []


def check(label: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)


def choose_print(page, mode: str) -> None:
    page.locator(f'[name="print-mode"][value="{mode}"]').evaluate('(el) => { el.checked = true; }')
    page.evaluate("window.dispatchEvent(new Event('beforeprint'))")


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for file in EVIDENCE.iterdir():
        if file.is_file():
            file.unlink()

    manifest = OUTPUT / '_shared/visual-assets/visual-manifest.js'
    manifest_text = manifest.read_text(encoding='utf-8')
    manifest_data = json.loads(manifest_text.removeprefix('window.VISUAL_MANIFEST = ').removesuffix(';\n'))
    check('全册可视化清单包含22个当前节点', len(manifest_data['sections']) == 22)
    check('椭圆与线面垂直映射至对应选必一真实章节', manifest_data['sections']['x1-2-2']['title'] == '椭圆' and manifest_data['sections']['x1-3-4']['title'] == '空间向量在立体几何中的应用')

    with zipfile.ZipFile(STUDENT_ZIP) as archive:
        names = set(archive.namelist())
        check('学生离线ZIP包含运行交互模块所需本地资产及许可', {'visual-book.js', 'visual-book.css', 'visual-assets/module-data.js', 'visual-assets/visual-manifest.js', 'visual-assets/ellipse-preview.png', 'visual-assets/Anatomy-LICENSE.txt', 'visual-assets/Question-Studio-LICENSE.txt'} <= names)
        check('学生ZIP CRC与路径均安全', archive.testzip() is None and all(not name.startswith(('/', '../')) for name in names))
        check('学生ZIP不含教师整合版或独立来源目录', not any(name in {'teacher.html', 'content.json'} or name.startswith(('_sources/', 'images/private-')) for name in names))

    errors: list[str] = []
    external_requests: list[str] = []
    config_path = EVIDENCE / 'teacher-config.json'
    report_pdf = EVIDENCE / 'complete-with-visuals.pdf'
    with sync_playwright() as playwright:
        browser = launch_browser(playwright, headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, offline=True, reduced_motion='reduce', accept_downloads=True)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: external_requests.append(request.url) if request.url.startswith(('http:', 'https:')) else None)
        page.goto(TEACHER_ELLIPSE.as_uri(), wait_until='load')
        unlock_access(page)
        page.wait_for_function('document.documentElement.dataset.visualReady === "true" && document.documentElement.dataset.math === "rendered"')
        page.evaluate('localStorage.removeItem("hujiao-x1-visual-layout-v1")')
        page.reload(wait_until='load')
        page.wait_for_function('document.documentElement.dataset.visualReady === "true"')
        original = page.locator('.book-body').evaluate("el => { const copy = el.cloneNode(true); copy.querySelectorAll('.visual-block').forEach(node => node.remove()); copy.querySelectorAll('.visual-target-active').forEach(node => node.classList.remove('visual-target-active')); return [...copy.children].map(child => child.outerHTML); }")
        question_count = page.locator('.book-body .question').count()
        answer_count = page.locator('.book-body .answer').count()

        page.locator('#visual-open').click()
        page.wait_for_selector('#visual-drawer.open')
        check('教師可视化资源库按当前真实章节筛选', page.locator('#visual-resource-list .visual-card').count() == 1)
        anchor = 'x1-2-2-ex-1'
        page.locator('#visual-anchor').select_option(anchor)
        page.locator('.visual-card [data-action="insert"]').click()
        page.wait_for_function('document.querySelectorAll(".visual-block").length === 1')
        page.wait_for_function('document.querySelector(".visual-frame-status").hidden')
        page.frame_locator('.visual-block iframe').get_by_role('button', name='更扁的椭圆', exact=True).click()
        page.wait_for_function('JSON.parse(localStorage.getItem("hujiao-x1-visual-layout-v1")).placements[0].state.c === 4.5')
        first_state = json.loads(page.evaluate('localStorage.getItem("hujiao-x1-visual-layout-v1")'))
        check('教师可用按钮插入椭圆交互，模块状态回传并本机暂存', page.locator('.visual-block').count() == 1 and first_state['placements'][0]['state']['c'] == 4.5)

        page.locator('#visual-anchor').select_option('x1-2-2-ex-3')
        page.locator('.visual-card [data-action="insert"]').click()
        page.wait_for_function('document.querySelectorAll(".visual-block").length === 2')
        page.wait_for_function('JSON.parse(localStorage.getItem("hujiao-x1-visual-layout-v1")).placements.length === 2')
        layout = json.loads(page.evaluate('localStorage.getItem("hujiao-x1-visual-layout-v1")'))
        check('同一可视化可以插入多个锚点且各实例参数独立', [item['state']['c'] for item in layout['placements']] == [4.5, 3] and [item['afterBlockId'] for item in layout['placements']] == ['x1-2-2-ex-1', 'x1-2-2-ex-3'])
        page.locator('#visual-close').click()
        page.locator('.visual-block').nth(1).get_by_label('学生页显示').uncheck()
        page.wait_for_function('JSON.parse(localStorage.getItem("hujiao-x1-visual-layout-v1")).placements[1].studentVisible === false')

        choose_print(page, 'all')
        check('完整内容打印预览纳入交互模块静态卡片而不克隆活动iframe', page.locator('#print-output .visual-module').count() == 2 and page.locator('#print-output iframe').count() == 0 and page.locator('#print-output .visual-print-fallback').count() == 2)
        check('新增可视化保持原有题目与答案数量', page.locator('.book-body .question').count() == question_count and page.locator('.book-body .answer').count() == answer_count)
        after_insert = page.locator('.book-body').evaluate("el => { const copy = el.cloneNode(true); copy.querySelectorAll('.visual-block').forEach(node => node.remove()); copy.querySelectorAll('.visual-target-active').forEach(node => node.classList.remove('visual-target-active')); return [...copy.children].map(child => child.outerHTML); }")
        check('插入模块未改变任何原正文/题块节点', after_insert == original)
        page.pdf(path=str(report_pdf), prefer_css_page_size=True, print_background=False)
        with fitz.open(report_pdf) as pdf:
            text = '\n'.join(item.get_text() for item in pdf)
            check('实际A4打印含静态模块说明与图，不裁交互卡片', len(pdf) > 0 and '交互图形仅可在网页中操作' in text and '椭圆' in text)
        choose_print(page, 'text')
        check('仅正文打印不包含交互模块', page.locator('#print-output .visual-module').count() == 0)
        choose_print(page, 'questions')
        check('仅试题打印不包含交互模块或答案', page.locator('#print-output .visual-module').count() == 0 and page.locator('#print-output .print-answer').count() == 0)
        page.locator('#visual-open').click()
        with page.expect_download() as download_info:
            page.locator('#visual-export').click()
        download_info.value.save_as(config_path)

        page.goto(TEACHER_PLANE.as_uri(), wait_until='load')
        unlock_access(page)
        page.wait_for_function('document.documentElement.dataset.visualReady === "true"')
        page.locator('#visual-open').click()
        check('跨章节页面读取同一册独立配置而不误用椭圆资源', page.locator('.visual-block').count() == 0 and page.locator('#visual-resource-list .visual-card').count() == 1)
        page.locator('#visual-anchor').select_option('x1-3-4-ex-1')
        page.locator('.visual-card [data-action="insert"]').click()
        page.wait_for_selector('.visual-block iframe')
        page.wait_for_function('document.querySelector(".visual-frame-status").hidden')
        page.frame_locator('.visual-block iframe').locator('#mode').select_option('parallel')
        page.wait_for_function('JSON.parse(localStorage.getItem("hujiao-x1-visual-layout-v1")).placements.find(item => item.assetId === "perpendicular").state.mode === "parallel"')
        check('线面垂直模型可接入真实3.4节并保留反例状态', True)
        check('模型CSP无外网请求', not external_requests)

        page.goto(STUDENT_ELLIPSE.as_uri(), wait_until='load')
        unlock_access(page)
        page.wait_for_function('document.documentElement.dataset.visualReady === "true"')
        check('真实学生版只显示被教师标记可见的1个模块', page.locator('.visual-block').count() == 1)
        check('学生版在插入后仍物理隔离全部答案与教师块', page.locator('.answer,.question-analysis,.teacher-only').count() == 0 and page.locator('.book-body .question').count() > 0)
        page.evaluate('localStorage.removeItem("hujiao-x1-visual-layout-v1")')
        page.reload(wait_until='load')
        page.wait_for_function('document.documentElement.dataset.visualReady === "true"')
        page.locator('#visual-open').click()
        page.locator('#visual-import-file').set_input_files(str(config_path))
        page.wait_for_function('document.querySelectorAll(".visual-block").length === 1')
        check('学生版可从教师独立JSON导入，且自动滤除未勾选实例', page.locator('.visual-block').count() == 1 and page.locator('.visual-block [data-action="remove"]').count() == 0 and page.locator('#visual-export').evaluate('(el) => el.hidden'))
        choose_print(page, 'all')
        check('学生版完整打印可包含静态模块但不带教师内容', page.locator('#print-output .visual-module').count() == 1 and page.locator('#print-output .answer,.print-commentary,.teacher').count() == 0)

        with zipfile.ZipFile(STUDENT_ZIP) as archive:
            archive.extractall(EVIDENCE / 'portable-student-package')
        portable = EVIDENCE / 'portable-student-package/student.html'
        page.goto(portable.as_uri(), wait_until='load')
        unlock_access(page)
        page.wait_for_function('document.documentElement.dataset.visualReady === "true" && document.documentElement.dataset.math === "rendered"')
        page.locator('#visual-open').click()
        page.locator('#visual-import-file').set_input_files(str(config_path))
        page.wait_for_function('document.querySelectorAll(".visual-block iframe").length === 1')
        page.wait_for_function('document.querySelector(".visual-frame-status").hidden')
        check('学生ZIP解压后直接离线导入配置并运行交互模块', page.locator('.visual-block iframe').count() == 1 and page.locator('.answer,.question-analysis,.teacher-only').count() == 0)
        check('模块沙箱运行未发起HTTP请求且页面无脚本错误', not external_requests and not errors)
        browser.close()

    result = {'status': 'passed', 'checks': CHECKS, 'count': len(CHECKS), 'page_errors': errors, 'external_requests': external_requests,
              'config': str(config_path), 'print_pdf': str(report_pdf)}
    (EVIDENCE / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'checks': len(CHECKS), 'evidence': str(EVIDENCE)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
