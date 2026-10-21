#!/usr/bin/env python3
"""Verify final repair receipts and visual/source integration, without redoing model tests."""

from project_paths import use_project_root, launch_browser
use_project_root()
import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from batch_render import fingerprint, sha
from batch_validate import VERSION, ready

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/五册教材教参整合'


def main():
    checks = []

    def check(name, passed):
        checks.append({'name': name, 'passed': bool(passed)})
        assert passed, name

    baseline = json.loads((ROOT / 'batch/patches/repair-run-baseline.json').read_text(encoding='utf-8'))
    catalog = json.loads((ROOT / 'batch/manifests/catalog.json').read_text(encoding='utf-8'))
    sources, sections, warnings = {}, [], []
    for book in catalog['books']:
        for chapter in book['chapters']:
            for section in chapter['sections']:
                sid = section['id']
                path = ROOT / section['path']
                data = json.loads(path.read_text(encoding='utf-8'))
                folder = OUT / book['id'] / sid
                build = json.loads((folder / 'build.json').read_text(encoding='utf-8'))
                validation = json.loads((folder / 'validation.json').read_text(encoding='utf-8'))
                current = fingerprint(path, data)
                expected = hashlib.sha256((VERSION + sha(ROOT / 'scripts/batch_validate.py') + current).encode()).hexdigest()
                check(sid + ': current browser/PDF receipt', validation['status'] == 'passed' and validation['fingerprint'] == expected and build['fingerprint'] == current)
                check(sid + ': artifacts intact', bool(build.get('artifact_hashes')) and all(sha(folder / p) == value for p, value in build['artifact_hashes'].items()))
                check(sid + ': no unresolved blocking issue', not any(i.get('severity') in ('blocking', 'error', 'critical') for i in data.get('issues', [])))
                sources.update(data['source_hashes'])
                warnings.extend({'section': sid, **w} for w in validation.get('warnings', []))
                sections.append({'id': sid, 'modelSha256': sha(path), 'validationSha256': sha(folder / 'validation.json'), 'checks': len(validation['checks']), 'questions': build['questions']})
    check('all original blocked sections repaired', set(baseline['scope']) <= {s['id'] for s in sections})
    check('all original sources unchanged', all(sha(p) == h for p, h in sources.items()))

    audit = json.loads((ROOT / 'docs/textbook-visual-selection.json').read_text(encoding='utf-8'))
    placements = [p for a in audit['assets'] + audit['existing'] for p in a['placements']]
    for p in placements:
        sid = p['sectionId']
        for edition in ('teacher', 'student'):
            soup = BeautifulSoup((OUT / sid.split('-')[0] / sid / (edition + '.html')).read_text(encoding='utf-8'), 'html.parser')
            node = soup.find(id=p['afterBlockId'])
            check(sid + '/' + edition + ': visual source aligned', node is not None and node.get('data-visual-source-sha') == p['sourceSha256'])

    # Boundary repairs and legacy sample offsets changed, but the interactive models did not.
    examples = ['bx2-7-3', 'bx2-8-2', 'bx3-10-3', 'x2-5-1']
    screenshots = OUT / 'repair-verification'
    screenshots.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser = launch_browser(pw, headless=True)
        for sid in examples:
            expected = [p for p in placements if p['sectionId'] == sid]
            for edition in ('teacher', 'student'):
                context = browser.new_context(offline=True, viewport={'width': 1440, 'height': 1000})
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                ready(page, OUT / sid.split('-')[0] / sid / (edition + '.html'))
                check(sid + '/' + edition + ': visuals retained', page.locator('.book-body .visual-block').count() == len(expected))
                check(sid + '/' + edition + ': expected prose folding', page.locator('.visual-condensed').count() == sum(not p.get('retainProse') for p in expected))
                original = page.locator('.book-body .prose').evaluate_all("els=>els.map(el=>(el.querySelector(':scope > .visual-original > .visual-original-body')||el).textContent.replace(/\\s+/g,''))")
                if page.locator('#print-sources').count():
                    page.locator('#print-sources').evaluate('(el)=>el.checked=true')
                page.locator('[name="print-mode"][value="text"]').evaluate('(el)=>el.checked=true')
                page.evaluate("dispatchEvent(new Event('beforeprint'))")
                printed = page.locator('#print-output .prose').evaluate_all("els=>els.map(el=>el.textContent.replace(/\\s+/g,''))")
                check(sid + '/' + edition + ': exact prose restored for print', original == printed)
                if sid == 'bx3-10-3':
                    for number in (1, 2, 6, 7):
                        question = page.locator(f'[data-question-id="bx3-10-3-ex-{number}"]').first
                        check(sid + '/' + edition + f': example {number} image publicly visible', question.locator('.question-body img').count() == 1)
                    page.locator('[data-question-id="bx3-10-3-ex-1"]').first.screenshot(path=str(screenshots / (edition + '-example1.png')))
                page.set_viewport_size({'width': 390, 'height': 844})
                check(sid + '/' + edition + ': mobile fits', page.evaluate('document.documentElement.scrollWidth <= innerWidth+1'))
                check(sid + '/' + edition + ': no JS errors', not errors)
                context.close()
        browser.close()
    report = {'status': 'passed', 'originalBlockedNodes': baseline['count'], 'validatedNodes': len(sections), 'sourceFilesUnchanged': len(sources), 'browserPdfChecks': sum(s['checks'] for s in sections), 'verificationChecks': len(checks), 'sections': sections, 'warnings': warnings, 'checks': checks, 'limits': ['Checks do not constitute a fresh mathematical review of all existing questions.', 'Questions taller than one A4 printable page may continue onto the next page.']}
    target = screenshots / 'repair-results.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if not isinstance(v, list)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
