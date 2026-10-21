#!/usr/bin/env python3
"""Targeted browser/offline/print regression checks for reused conic labs."""

from project_paths import use_project_root, launch_browser
use_project_root()
import json
import re
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright
from test_print import unlock_access

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / 'outputs/五册教材教参整合/x1'
EVIDENCE = BOOK / 'conic-verification' / datetime.now().strftime('%Y%m%d-%H%M%S')
CHECKS = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)


def ready(page):
    unlock_access(page)
    page.wait_for_function("document.documentElement.dataset.visualReady === 'true'")
    page.wait_for_function("[...document.querySelectorAll('.book-body .visual-frame-status')].every(el=>el.hidden)")


def main():
    EVIDENCE.mkdir(parents=True)
    errors = []
    with sync_playwright() as tool:
        browser = launch_browser(tool, headless=True)
        for kind, number in [('ellipse', 2), ('hyperbola', 3), ('parabola', 4)]:
            sid = f'x1-2-{number}'
            for mode in ['teacher', 'student']:
                context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto((BOOK / sid / f'{mode}.html').as_uri())
                ready(page)
                block = page.locator('.book-body .visual-block')
                check(f'{kind}/{mode}: one bundled module at definition-equation block', block.count() == 1 and block.evaluate('(el)=>el.previousElementSibling.id') == sid+'-b3')
                check(f'{kind}/{mode}: follows with example 1', block.evaluate('(el)=>el.nextElementSibling.id') == sid+'-ex-1')
                frame = page.frames[1]
                frame.wait_for_function('() => !!window.TixuPlugin')
                check(f'{kind}/{mode}: default definition, paused', frame.evaluate("window.TixuPlugin.getState().mode==='foci' && document.querySelector('#play').getAttribute('aria-pressed')==='false'"))
                check(f'{kind}/{mode}: extensions collapsed', not frame.locator('.mode-nav').is_visible())
                frame.locator('#textbook-more').click()
                modes = frame.locator('[data-mode]').evaluate_all('(els)=>els.map(el=>el.dataset.mode)')
                check(f'{kind}/{mode}: eight original scenes', len(modes) == 8)
                for scene in modes:
                    frame.locator(f'[data-mode="{scene}"]').click()
                    check(f'{kind}/{mode}/{scene}: live model and rendered formula', frame.locator('#diagram path').count() > 0 and frame.locator('#formula .katex').count() > 0)
                frame.locator('[data-mode="foci"]').click()
                if mode == 'student':
                    check(f'{kind}: student has no teacher proof or classroom answer', frame.locator('#proof summary').count() == 0 and frame.locator('#proof-body').inner_text() == '' and frame.locator('#question').inner_text() == '')
                else:
                    frame.locator('#proof summary').click()
                    page.wait_for_timeout(150)
                    check(f'{kind}: expanded teacher proof not clipped', frame.locator('main').evaluate('(el)=>el.getBoundingClientRect().height') < block.locator('iframe').evaluate('(el)=>el.clientHeight') + 3)
                    frame.locator('#proof summary').click()
                    if kind == 'hyperbola':
                        frame.locator('[data-branch="-1"]').click()
                        frame.locator('#boundary-case').select_option('limit')
                        page.wait_for_timeout(550)
                        page.reload(); ready(page); frame = page.frames[1]
                        check('hyperbola: branch and boundary restore after reload', frame.evaluate("window.TixuPlugin.getState().branch===-1 && window.TixuPlugin.getState().boundary==='limit'"))
                    if kind == 'ellipse':
                        frame.locator('[data-mode="compression"]').click()
                        frame.locator('#blend').evaluate("el=>{el.value='0.25';el.dispatchEvent(new Event('input',{bubbles:true}))}")
                        page.wait_for_timeout(550)
                        page.reload(); ready(page); frame = page.frames[1]
                        check('ellipse: extra state and selected mode restore', frame.evaluate("window.TixuPlugin.getState().blend===.25 && window.TixuPlugin.getState().mode==='compression'"))
                frame.locator('#textbook-more').click() if frame.locator('#textbook-more').get_attribute('aria-expanded') == 'true' else None
                # Prevent the outer sticky toolbar from covering a tall element screenshot.
                page.add_style_tag(content='.book-toolbar{position:static!important} .toolbar{position:static!important}')
                block.screenshot(path=str(EVIDENCE / f'{kind}-{mode}-desktop.png'))
                check(f'{kind}/{mode}: desktop no horizontal overflow', frame.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
                page.set_viewport_size({'width': 390, 'height': 844})
                # Chromium may suspend an offscreen child frame's animation-frame polling.
                for _ in range(30):
                    if frame.evaluate("document.querySelector('main').getBoundingClientRect().height <= innerHeight"):
                        break
                    page.wait_for_timeout(100)
                page.wait_for_timeout(250)
                check(f'{kind}/{mode}: mobile no horizontal overflow', frame.evaluate('document.documentElement.scrollWidth<=innerWidth+1') and page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
                check(f'{kind}/{mode}: mobile content height fully contained', frame.locator('main').evaluate('(el)=>el.getBoundingClientRect().height') <= block.locator('iframe').evaluate('(el)=>el.clientHeight'))
                block.screenshot(path=str(EVIDENCE / f'{kind}-{mode}-mobile.png'))
                if kind == 'parabola' and mode == 'student':
                    page.evaluate("scrollTo({top:document.querySelector('.book-body .visual-block').getBoundingClientRect().bottom+scrollY-innerHeight+20,behavior:'instant'})")
                    page.wait_for_timeout(200)
                    page.screenshot(path=str(EVIDENCE / 'parabola-student-mobile-bottom.png'))
                page.set_viewport_size({'width': 1440, 'height': 1000})
                for print_mode in ['questions', 'text', 'all']:
                    page.locator(f'[name="print-mode"][value="{print_mode}"]').evaluate('(el)=>el.checked=true')
                    page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
                    count = page.locator('#print-output .visual-print-fallback').count()
                    check(f'{kind}/{mode}: print {print_mode}', count == (1 if print_mode == 'all' else 0))
                    check(f'{kind}/{mode}: print does not clone live iframe', page.locator('#print-output iframe').count() == 0)
                if mode == 'teacher' and kind == 'parabola':
                    page.pdf(path=str(EVIDENCE / 'parabola-complete-print.pdf'), format='A4', print_background=True)
                    page.emulate_media(media='screen')
                    page.locator('.book-body [data-action="remove"]').click()
                    page.reload(); ready(page)
                    check('removed bundled module stays removed after reload', page.locator('.book-body .visual-block').count() == 0)
                context.close()
            with zipfile.ZipFile(BOOK / sid / 'student.zip') as archive:
                names = archive.namelist()
                check(f'{kind}: ZIP contains only student lab payload', f'visual-assets/conic-{kind}-student.js' in names and not any(name.endswith('-teacher.js') for name in names))
                with tempfile.TemporaryDirectory() as folder:
                    archive.extractall(folder)
                    context = browser.new_context()
                    page = context.new_page(); page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto((Path(folder) / 'student.html').as_uri()); ready(page)
                    check(f'{kind}: extracted student ZIP works offline', page.frames[1].evaluate('!!window.TixuPlugin'))
                    context.close()
        context = browser.new_context(accept_downloads=True)
        page = context.new_page(); page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto((BOOK / 'x1-2-2/teacher.html').as_uri()); ready(page)
        page.locator('#visual-open').click()
        page.locator('[data-asset="ellipse"] [data-action="insert"]').click(); ready(page)
        check('existing string ellipse still inserts alongside new lab', page.locator('.book-body .visual-block').count() == 2)
        with page.expect_download() as info:
            page.locator('#visual-export').click()
        exported = EVIDENCE / 'layout-roundtrip.json'
        info.value.save_as(exported)
        payload = json.loads(exported.read_text(encoding='utf-8'))
        check('exported layout preserves all three bundled section placements', len([p for p in payload['placements'] if p['assetId'].endswith('-lab')]) == 3)
        legacy = {**payload, 'placements': [item for item in payload['placements'] if item['assetId'] == 'ellipse']}
        legacy.pop('bundledDefaults', None)
        key = re.search(r"const STORAGE_KEY = '([^']+)'", (ROOT / 'scripts/visual-book.js').read_text(encoding='utf-8'))[1]
        page.evaluate('([key,data])=>localStorage.setItem(key,JSON.stringify(data))', [key, legacy])
        page.reload(); ready(page)
        check('legacy layout preserves existing module and adds default lab', page.locator('.book-body .visual-block').count() == 2)
        empty = EVIDENCE / 'explicit-empty-layout.json'
        empty.write_text(json.dumps({'schema': 'hujiao-x1-visual-layout/v1', 'sourceBook': 'x1', 'placements': []}), encoding='utf-8')
        page.locator('#visual-import-file').set_input_files(empty)
        page.wait_for_function("document.querySelectorAll('.book-body .visual-block').length===0")
        page.reload(); ready(page)
        check('explicit imported empty layout remains authoritative after reload', page.locator('.book-body .visual-block').count() == 0)
        context.close()
        check('no browser JS errors', not errors)
        browser.close()
    (EVIDENCE / 'results.json').write_text(json.dumps({'checks': CHECKS, 'errors': errors}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'passed': len(CHECKS), 'evidence': str(EVIDENCE), 'errors': errors}, ensure_ascii=False))


if __name__ == '__main__':
    main()
