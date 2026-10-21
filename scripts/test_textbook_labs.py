#!/usr/bin/env python3
"""Serial real-browser acceptance for every audited placement, print and offline packages."""

from project_paths import use_project_root, launch_browser
use_project_root()
import json
import argparse
import re
import urllib.parse
import hashlib
from datetime import timezone
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/五册教材教参整合'
EVIDENCE = OUT / 'visual-verification' / datetime.now().strftime('%Y%m%d-%H%M%S')
CHECKS, ERRORS = [], []


def check(name, value):
    if not value:
        raise AssertionError(name)
    CHECKS.append(name)


def ready(page):
    page.wait_for_function("document.documentElement.dataset.visualReady === 'true'")
    page.wait_for_function("[...document.querySelectorAll('.book-body .visual-frame-status')].every(el=>el.hidden)", timeout=15000)


def choose_print(page, mode):
    page.locator(f'[name="print-mode"][value="{mode}"]').evaluate('(el)=>el.checked=true')
    page.evaluate("window.dispatchEvent(new Event('beforeprint'))")


def original_prose(page):
    return page.locator('.book-body .prose').evaluate_all("els=>els.map(el=>(el.querySelector(':scope > .visual-original > .visual-original-body')||el).textContent.replace(/\\s+/g,''))")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--families', nargs='+', help='Only affected sections and artifacts from these source families')
    args = parser.parse_args()
    EVIDENCE.mkdir(parents=True)
    audit = json.loads((ROOT / 'docs/textbook-visual-selection.json').read_text(encoding='utf-8'))
    assets = {a['id']: a for a in audit['assets']}
    requested = set(assets)
    if args.families:
        requested = {a['id'] for family in args.families
                     for a in json.loads((ROOT / 'scripts/textbook-labs' / f'{family}.json').read_text(encoding='utf-8'))['assets']}
        check('requested families exist in compiled audit', bool(requested) and requested <= set(assets))
    affected = {p['sectionId'] for asset_id in requested for p in assets[asset_id]['placements']}
    if not args.families:
        affected.update(p['sectionId'] for a in audit['existing'] for p in a['placements'])
    placements = {}
    for a in list(assets.values()) + audit['existing']:
        for p in a['placements']:
            if p['sectionId'] in affected:
                placements.setdefault(p['sectionId'], []).append((a, p))
    check('all101 nodes have exactly one explained decision', audit['nodeCount'] == 101 and len({x['sectionId'] for x in audit['selection']}) == 101)
    with sync_playwright() as tool:
        browser = launch_browser(tool, headless=True)
        for sid, entries in placements.items():
            book = sid.split('-')[0]
            for mode in ['teacher', 'student']:
                context = browser.new_context(viewport={'width': 1440, 'height': 1000})
                page = context.new_page()
                page.on('pageerror', lambda e: ERRORS.append(str(e)))
                page.goto((OUT / book / sid / f'{mode}.html').as_uri())
                ready(page)
                prefix = f'{sid}/{mode}'
                check(prefix + ': expected modules', page.locator('.book-body .visual-block').count() == len(entries))
                check(prefix + ': audited prose collapsed', page.locator('.visual-condensed').count() == len({p['afterBlockId'] for _, p in entries if not p.get('retainProse')}))
                check(prefix + ': exact original retained', page.locator('.visual-original-body').count() == sum(not p.get('retainProse') for _, p in entries))
                original = original_prose(page)
                for a, p in entries:
                    if p.get('retainProse'):
                        continue
                    anchor = page.locator('[id="' + p['afterBlockId'] + '"]')
                    check(prefix + ': original initially collapsed', not anchor.locator('.visual-original').evaluate('(el)=>el.open'))
                    anchor.locator('.visual-original > summary').click()
                    check(prefix + ': original can expand', anchor.locator('.visual-original-body').is_visible())
                    anchor.locator('.visual-original > summary').click()
                for a, p in entries:
                    if a.get('id') not in assets:
                        continue
                    frame = next(f for f in page.frames if f != page.main_frame and f.evaluate('window.__textbookLab?.id || null') == a['id'])
                    check(prefix + '/' + a['id'] + ': formula actually rendered', frame.locator('math').count() > 0 and frame.locator('math').first.bounding_box()['height'] > 0)
                    if mode == 'teacher':
                        spec = frame.evaluate('window.LAB_SPEC')
                        for control in spec['controls']:
                            values = [o['value'] for o in control['options']] if control['type'] == 'select' else [False, True] if control['type'] == 'checkbox' else [control['min'], control['max']]
                            for value in values:
                                state = {**spec['initial'], control['key']: value}
                                frame.evaluate('s=>window.TixuPlugin.setState(s)', state)
                                check(prefix + '/' + a['id'] + '/' + control['key'] + '=' + str(value), frame.evaluate("!/(NaN|Infinity|undefined)/.test(document.querySelector('#diagram').innerHTML) && document.querySelector('#diagram').childElementCount > 0"))
                        frame.evaluate('s=>window.TixuPlugin.setState(s)', spec['initial'])
                        # Exercise the actual native control, not only its state API.
                        control = spec['controls'][0]
                        frame.locator('[data-key="' + control['key'] + '"]').evaluate("el=>{if(el.type==='range')el.value=el.value===el.max?el.min:el.max;else if(el.type==='checkbox')el.checked=!el.checked;else el.selectedIndex=(el.selectedIndex+1)%el.options.length;el.dispatchEvent(new Event('input',{bubbles:true}))}")
                        check(prefix + ': native control updates state', frame.evaluate('JSON.stringify(window.TixuPlugin.getState()) !== JSON.stringify(window.LAB_SPEC.initial)'))
                        frame.locator('#reset').click()
                    block = page.locator('.visual-block').filter(has=page.locator('iframe[title="' + a['title'] + '"]'))
                    if mode == 'teacher':
                        block.screenshot(path=str(EVIDENCE / f'{sid}-{a["id"]}-desktop.png'))
                if mode == 'student':
                    check(prefix + ': no teacher answer blocks', page.locator('.book-body .answer,.book-body .question-analysis,.book-body .teacher').count() == 0)
                if page.locator('#print-sources').count():
                    page.locator('#print-sources').evaluate('(el)=>el.checked=true')
                choose_print(page, 'text')
                printed = page.locator('#print-output .prose').evaluate_all("els=>els.map(el=>el.textContent.replace(/\\s+/g,''))")
                check(prefix + ': print restores complete original prose exactly', original == printed)
                check(prefix + ': no duplicate summary in text print', page.locator('#print-output .visual-original,#print-output .visual-reading-summary,#print-output iframe').count() == 0)
                choose_print(page, 'questions')
                check(prefix + ': questions print excludes diagrams prose answers', page.locator('#print-output .prose,#print-output .visual-module,#print-output .answer,#print-output .print-answer').count() == 0)
                choose_print(page, 'all')
                check(prefix + ': full print uses real static SVG', page.locator('#print-output .visual-print-fallback img').count() == len(entries))
                if sid in ['bx1-2-3', 'bx2-6-2', 'bx3-10-2', 'x1-2-3', 'x2-5-1'] and mode == 'teacher':
                    page.pdf(path=str(EVIDENCE / f'{sid}-complete.pdf'), format='A4', print_background=True)
                page.set_viewport_size({'width': 390, 'height': 844})
                for index, block in enumerate(page.locator('.book-body .visual-block').all()):
                    block.scroll_into_view_if_needed()
                    page.wait_for_timeout(180)
                    check(prefix + ': mobile host no horizontal overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
                    frame = block.locator('iframe').content_frame
                    check(prefix + ': mobile frame no horizontal overflow', frame.locator('body').evaluate('el=>el.scrollWidth <= innerWidth + 2'))
                    check(prefix + ': no iframe vertical clipping', block.locator('iframe').evaluate('el=>el.clientHeight') >= frame.locator('main').evaluate('el=>el.getBoundingClientRect().height'))
                    if mode == 'teacher':
                        block.screenshot(path=str(EVIDENCE / f'{sid}-{index}-mobile.png'))
                context.close()
            # Every modified student archive is checked and exercised via file:// after extraction.
            with zipfile.ZipFile(OUT / book / sid / 'student.zip') as archive:
                names = archive.namelist()
                check(sid + ': ZIP CRC/path and isolation', archive.testzip() is None and all(not n.startswith(('/', '../')) for n in names) and 'teacher.html' not in names and not any(n.endswith('-teacher.js') for n in names))
                with tempfile.TemporaryDirectory() as tmp:
                    archive.extractall(tmp)
                    context = browser.new_context()
                    page = context.new_page()
                    page.on('pageerror', lambda e: ERRORS.append(str(e)))
                    page.goto((Path(tmp) / 'student.html').as_uri())
                    ready(page)
                    check(sid + ': extracted student package offline', page.locator('.visual-block').count() == len(entries))
                    context.close()
            print(sid, 'passed', flush=True)
        (EVIDENCE / 'section-phase-results.json').write_text(json.dumps({'status':'passed','checksDetail':CHECKS,'sectionCount':len(placements)}, ensure_ascii=False, indent=2), encoding='utf-8')
        # Verify hash-json scene, grouped state, malformed state and hashchange for every artifact.
        for asset_id, asset in assets.items():
            if asset_id not in requested:
                continue
            spec_path = ROOT / 'scripts/visual-assets' / asset['payload'].replace('.js', '.html')
            context = browser.new_context(viewport={'width': 900, 'height': 850})
            page = context.new_page(); page.goto(spec_path.as_uri())
            spec = page.evaluate('window.LAB_SPEC')
            control = spec['controls'][0]
            if control['type'] == 'range': value = control['max'] if control['max'] != spec['initial'][control['key']] else control['min']
            elif control['type'] == 'checkbox': value = not spec['initial'][control['key']]
            else: value = next(o['value'] for o in control['options'] if o['value'] != spec['initial'][control['key']])
            group = next(group for group, keys in spec['stateKeys'].items() if control['key'] in keys)
            sparse = {'math': {}, 'view': {}, 'lesson': {}}; sparse[group][control['key']] = value
            page.evaluate('(s)=>location.hash = "#scene=explore&state=" + encodeURIComponent(JSON.stringify(s))', sparse)
            page.wait_for_function('(x)=>window.TixuPlugin.getState()[x.key] === x.value', arg={'key': control['key'], 'value': value})
            check(asset_id + ': grouped hash state restores', page.evaluate('(x)=>window.TixuPlugin.getState()[x.key] === x.value', {'key': control['key'], 'value': value}))
            page.evaluate("location.hash='#scene=explore&state=%7B%22math%22%3A%7B%22not-a-control%22%3A4%7D%7D'")
            page.wait_for_function('document.querySelector("#note").textContent.includes("未知或错组参数")')
            check(asset_id + ': invalid hash restores defaults', page.evaluate('(s)=>JSON.stringify(window.TixuPlugin.getState()) === JSON.stringify(s)', spec['initial']))
            page.evaluate("location.hash='#scene=unknown'")
            page.wait_for_function('document.querySelector("#note").textContent.includes("未知场景")')
            check(asset_id + ': unknown scene is explicit and safe', page.evaluate('(s)=>JSON.stringify(window.TixuPlugin.getState()) === JSON.stringify(s)', spec['initial']))
            context.close()
        # Read pages excluded by pedagogical selection, confirming no accidental universal insertion.
        for item in audit['selection']:
            if args.families or item['sectionId'] in placements:
                continue
            sid = item['sectionId']
            context = browser.new_context()
            page = context.new_page()
            page.on('pageerror', lambda e: ERRORS.append(str(e)))
            page.goto((OUT / sid.split('-')[0] / sid / 'teacher.html').as_uri())
            ready(page)
            check(sid + ': intentionally no diagram or hidden prose', page.locator('.visual-block,.visual-condensed').count() == 0)
            context.close()
        browser.close()
    check('no browser JavaScript exceptions across five books', not ERRORS)
    assets_validation = {}
    for asset_id, asset in assets.items():
        if asset_id not in requested:
            continue
        page = ROOT / 'scripts/visual-assets' / asset['payload'].replace('.js', '.html')
        assets_validation[asset_id] = {'htmlSha256': hashlib.sha256(page.read_bytes()).hexdigest(), 'checkedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), 'interaction': 'pass', 'offline': 'pass', 'sceneRestore': True, 'stateRestore': True}
    result = {'status': 'passed', 'checks': len(CHECKS), 'assets': len(requested), 'placementSections': len(placements), 'nodes': audit['nodeCount'], 'errors': ERRORS, 'assetValidation': assets_validation, 'checksDetail': CHECKS,
              'scope': 'affected sections and requested artifacts' if args.families else 'all visualization placements',
              'limitations': ['桌面与390px视口检查不等于真实触摸设备验收。', '模型检查与交互验收不替代全书数学审定。']}
    (EVIDENCE / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ['status', 'checks', 'assets', 'placementSections', 'nodes']}, ensure_ascii=False))
    print(EVIDENCE)


if __name__ == '__main__':
    main()
