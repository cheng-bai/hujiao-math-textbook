#!/usr/bin/env python3
"""Exercise saved-layout compatibility and student visibility in the five-book host."""

from project_paths import use_project_root, launch_browser
use_project_root()
import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/五册教材教参整合'


def main():
    checks = []
    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
    def ready(page):
        page.wait_for_function("document.documentElement.dataset.visualReady==='true'")
        page.wait_for_function("[...document.querySelectorAll('.visual-block .visual-frame-status')].every(el=>el.hidden)")
    exports = []
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as tool:
        browser = launch_browser(tool, headless=True)
        for sid in ['bx1-2-3', 'bx2-6-1', 'bx3-10-2', 'x1-2-3', 'x2-5-1']:
            book = sid.split('-')[0]
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            page.goto((OUT / book / sid / 'teacher.html').as_uri()); ready(page)
            expected = page.locator('.visual-block').count()
            check(book + ': representative default present', expected == 1)
            page.locator('#visual-open').click()
            with page.expect_download() as event:
                page.locator('#visual-export').click()
            path = Path(tmp) / f'{book}.json'; event.value.save_as(path)
            config = json.loads(path.read_text(encoding='utf-8')); exports.append(path)
            check(book + ': exported identity and valid instance IDs', config['sourceBook'] == book and all(re.fullmatch(r'[a-zA-Z0-9-]{1,80}', p['instanceId']) for p in config['placements']))
            check(book + ': export contains no prose or source payload', '<html' not in path.read_text(encoding='utf-8') and '/Users/' not in path.read_text(encoding='utf-8'))
            page.locator('#visual-close').click()
            page.locator('.visual-block [data-action="remove"]').click()
            page.wait_for_function("document.querySelectorAll('.visual-block').length===0")
            check(book + ': removal unfolds untouched prose', page.locator('.visual-condensed').count() == 0)
            page.locator('#visual-open').click()
            page.locator('#visual-undo').click()
            page.wait_for_function("document.querySelectorAll('.visual-block').length===1"); ready(page)
            page.locator('#visual-close').click()
            check(book + ': undo reinstates diagram and condensation', page.locator('.visual-block').count() == expected and page.locator('.visual-condensed').count() == 1)
            page.locator('#visual-import-file').set_input_files(path)
            page.wait_for_function("document.querySelector('#visual-config-status').textContent.includes('已恢复全册')"); ready(page)
            page.reload(); ready(page)
            check(book + ': persisted layout survives validation and reload', page.locator('.visual-block').count() == expected)
            if len(exports) > 1:
                page.locator('#visual-import-file').set_input_files(exports[0])
                page.wait_for_function("document.querySelector('#visual-config-status').textContent.includes('不匹配')")
                check(book + ': other-book import rejected without replacing layout', '不匹配' in page.locator('#visual-config-status').inner_text() and page.locator('.visual-block').count() == expected)
            if book == 'x1':
                page.evaluate("""()=>{const key=Object.keys(localStorage).find(k=>{try{return JSON.parse(localStorage[k]).sourceBook==='x1'}catch(_){return false}});const value=JSON.parse(localStorage[key]);value.placements=value.placements.filter(p=>p.assetId!=='hyperbola-lab');value.bundledDefaults=value.bundledDefaults.filter(k=>!k.startsWith('hyperbola-lab'));value.bundledDefaults.push('hyperbola-lab');localStorage[key]=JSON.stringify(value)}""")
                page.reload(); ready(page)
                check('x1: legacy seed marker respects earlier explicit removal', page.locator('.visual-block').count() == 0 and page.locator('.visual-condensed').count() == 0)
                page.locator('#visual-import-file').set_input_files(path)
                page.wait_for_function("document.querySelectorAll('.visual-block').length===1"); ready(page)
            page.locator('.visual-block [data-action="student-visible"]').uncheck()
            page.wait_for_timeout(400)
            page.goto((OUT / book / sid / 'student.html').as_uri()); ready(page)
            check(book + ': student-hidden diagram restores full prose', page.locator('.visual-block,.visual-condensed').count() == 0)
            context.close()
            print(book, 'layout state passed', flush=True)
        browser.close()
    result = {'status': 'passed', 'checkedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), 'checks': len(checks), 'checksDetail': checks}
    dest = OUT / 'visual-verification/layout-state-results.json'
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': result['status'], 'checks': result['checks']}))


if __name__ == '__main__':
    main()
