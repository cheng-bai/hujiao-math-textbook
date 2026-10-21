#!/usr/bin/env python3
"""Build bounded, chapter-loaded offline experiments and an exhaustive selection audit."""

from project_paths import use_project_root, launch_browser
use_project_root()
import hashlib
import html
import json
import subprocess
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'scripts/textbook-labs'
DEST = ROOT / 'scripts/visual-assets'


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def main():
    from bs4 import BeautifulSoup

    legacy = json.loads((DEST / 'module-data.js').read_text(encoding='utf-8').split('=', 1)[1].strip().removesuffix(';'))
    student_ellipse = BeautifulSoup(legacy['ellipseHtml'], 'html.parser')
    for node in student_ellipse.select('.teacher, .teacher-only, .answer'):
        node.decompose()
    legacy['ellipseHtml'] = str(student_ellipse)
    # Retain fixed source identity for teacher-layout compatibility; role payloads differ by design.
    (DEST / 'module-data-student.js').write_text('window.MODULE_DATA = ' + compact(legacy).replace('<', '\\u003c') + ';\n', encoding='utf-8')
    catalog = json.loads((ROOT / 'batch/manifests/catalog.json').read_text(encoding='utf-8'))
    sections = {s['id']: (b['id'], json.loads((ROOT / s['path']).read_text(encoding='utf-8')))
                for b in catalog['books'] for c in b['chapters'] for s in c['sections']}
    selection, assets, existing = [], [], []
    css = (SOURCE / 'lab.css').read_text(encoding='utf-8')
    core = (SOURCE / 'lab-core.js').read_text(encoding='utf-8')
    runtime = (SOURCE / 'lab-runtime.js').read_text(encoding='utf-8')
    for family in ['foundations', 'space-sequence', 'calculus-stats',
                   'deep-geometry', 'deep-analysis', 'deep-spatial']:
        spec = json.loads((SOURCE / f'{family}.json').read_text(encoding='utf-8'))
        code = (SOURCE / f'{family}.js').read_text(encoding='utf-8')
        selection.extend(spec['selection'])
        existing.extend(spec.get('existing', []))
        for asset in spec['assets']:
            params = {}
            for c in asset['controls']:
                params[c['key']] = ({'enum': [o['value'] for o in c['options']]} if c['type'] == 'select'
                                    else {'type': 'boolean'} if c['type'] == 'checkbox'
                                    else {'minimum': c['min'], 'maximum': c['max'], 'step': c['step']})
            assert set(params) == set(asset['initial']), asset['id']
            for p in asset['placements']:
                _, section = sections[p['sectionId']]
                targets = [b for i, b in enumerate(section['blocks'])
                           if b.get('id', f'{p["sectionId"]}-b{i}') == p['afterBlockId']]
                assert len(targets) == 1 and targets[0]['type'] == 'prose', p
                p['sourceSha256'] = hashlib.sha256(compact(targets[0]).encode()).hexdigest()
            safe_spec = {k: asset[k] for k in ['id', 'title', 'goal', 'summary', 'formula', 'controls', 'initial']}
            safe_spec['stateKeys'] = asset.get('stateKeys') or {group: [c['key'] for c in asset['controls'] if ('view' if c['key'] == 'yaw' else 'lesson' if c['key'] in ['progress', 'stage'] else 'math') == group] for group in ['math', 'view', 'lesson']}
            grouped = [key for keys in safe_spec['stateKeys'].values() for key in keys]
            assert set(safe_spec['stateKeys']) == {'math', 'view', 'lesson'}
            assert len(grouped) == len(params) and set(grouped) == set(params), asset['id']
            explanation = ''
            proof_style = ''
            if asset.get('explanationHtml'):
                explanation = ('<details class="lab-proof"><summary>为什么成立 · 条件与推导</summary>'
                               '<div>' + asset['explanationHtml'] + '</div></details>')
                proof_style = ('.lab-proof{margin-top:10px;border-top:1px solid #d8ded1;padding-top:7px}'
                               '.lab-proof summary{cursor:pointer;color:#27685c;font-weight:600}'
                               '.lab-proof p{margin:8px 0}.lab-proof math{max-width:100%;overflow-x:auto;padding:5px 0}')
            spec_json = compact(safe_spec).replace('</', '<\\/')
            document = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
                        '<meta name="viewport" content="width=device-width,initial-scale=1">'
                        f'<title>{html.escape(asset["title"])}</title><style>{css}{proof_style}</style></head><body><main>'
                        f'<div class="formula">{asset["formula"]}</div><div class="lab-grid"><div class="figure"><svg id="diagram" viewBox="0 0 600 360" role="img" aria-label="{html.escape(asset["title"])}"></svg></div>'
                        '<div>'
                        '<div id="metrics" aria-live="polite"></div><p id="note"></p></div></div><div id="controls"></div>'
                        f'{explanation}<div class="bottom"><span>改变参数，观察关系；图形取样不能替代证明。</span><button id="reset">恢复初始状态</button></div>'
                        f'</main><script>window.LAB_SPEC={spec_json};</script>'
                        f'<script>{core}</script><script>{code}</script><script>{runtime}</script></body></html>')
            digest = hashlib.sha256(document.encode()).hexdigest()
            filename = f'textbook-{asset["id"]}'
            (DEST / f'{filename}.html').write_text(document, encoding='utf-8')
            (DEST / f'{filename}.js').write_text('window.TEXTBOOK_LAB_HTML=window.TEXTBOOK_LAB_HTML||{};window.TEXTBOOK_LAB_HTML[' + compact(asset['id']) + ']=' + compact(document) + ';\n', encoding='utf-8')
            # Render the same pure initial model, not a decorative placeholder thumbnail.
            js = ('const vm=require("vm");const c={window:{}};vm.createContext(c);'
                  + f'vm.runInContext({compact(core + code)},c);'
                  + f'process.stdout.write(c.window.TEXTBOOK_EXPERIMENTS[{compact(asset["id"])}].render({compact(asset["initial"])},c.window.LabTools).svg);')
            svg = subprocess.check_output(['node', '-e', js], text=True)
            if svg.lstrip().startswith('<svg'):
                svg = svg[svg.index('>')+1:svg.rfind('</svg>')]
            (DEST / f'{filename}-preview.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 360"><style>{css}</style><rect width="600" height="360" fill="#fffef8"/>{svg}</svg>', encoding='utf-8')
            assets.append({**{k: asset[k] for k in ['id', 'title', 'goal', 'summary', 'initial', 'placements']},
                           'sections': sorted({p['sectionId'] for p in asset['placements']}),
                           'category': '动态解释', 'scene': 'explore', 'version': 'textbook-lab-v1-' + digest[:12],
                           'hash': digest, 'parameters': params, 'payload': filename + '.js',
                           'preview': filename + '-preview.svg', 'sourceReuse': asset.get('sourceReuse', ''),
                           'resourceId': str(uuid.uuid5(uuid.NAMESPACE_URL, 'hujiao-textbook:' + asset['id']))})
    # Keep both orientations visible when the lengthy coordinate derivation is folded.
    square = lambda name: f'<msup><mi>{name}</mi><mn>2</mn></msup>'
    fraction = lambda top, bottom: f'<mfrac>{square(top)}{square(bottom)}</mfrac>'
    for item in existing:
        for placement in item['placements']:
            _, section = sections[placement['sectionId']]
            target = next(b for i, b in enumerate(section['blocks']) if b.get('id', f'{placement["sectionId"]}-b{i}') == placement['afterBlockId'])
            placement['sourceSha256'] = hashlib.sha256(compact(target).encode()).hexdigest()
        if item['assetId'] in ['ellipse-lab', 'hyperbola-lab']:
            sign = '+' if item['assetId'] == 'ellipse-lab' else '−'
            equations = [fraction('x', 'a') + f'<mo>{sign}</mo>' + fraction('y', 'b'), fraction('y', 'a') + f'<mo>{sign}</mo>' + fraction('x', 'b')]
            item['formula'] = ''.join('<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>' + eq + '<mo>=</mo><mn>1</mn></mrow></math>' for eq in equations)
            conditions = '<mi>a</mi><mo>&gt;</mo><mi>b</mi><mo>&gt;</mo><mn>0</mn>' if sign == '+' else '<mi>a</mi><mo>&gt;</mo><mn>0</mn><mo>，</mo><mi>b</mi><mo>&gt;</mo><mn>0</mn>'
            item['formula'] += '<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>' + conditions + '</mrow></math>'
        else:
            item['formula'] = ''.join(f'<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>{square(u)}<mo>=</mo><mo>±</mo><mn>2</mn><mi>p</mi><mi>{v}</mi><mo>，</mo><mi>p</mi><mo>&gt;</mo><mn>0</mn></mrow></math>' for u, v in [('y', 'x'), ('x', 'y')])
    # Preserve one exhaustive decision per section while promoting deeper topics.
    decisions = {item['sectionId']: item for item in selection}
    deep_ids = {a['id'] for family in ['deep-geometry', 'deep-analysis', 'deep-spatial']
                for a in json.loads((SOURCE / f'{family}.json').read_text(encoding='utf-8'))['assets']}
    for asset in assets:
        if asset['id'] not in deep_ids:
            continue
        for placement in asset['placements']:
            decision = decisions[placement['sectionId']]
            decision['status'] = 'selected'
            decision['reason'] += ' 深度探究：' + placement['rationale']
    counts = {sid: sum(x['sectionId'] == sid for x in selection) for sid in sections}
    assert set(x['sectionId'] for x in selection) == set(sections), 'selection coverage differs'
    assert all(n == 1 for n in counts.values()), counts
    assert all(x['status'] in ['selected', 'skip', 'existing'] and x['reason'] for x in selection)
    assert len({a['id'] for a in assets}) == len(assets)
    for b in catalog['books']:
        subset = [a for a in assets if any(p['sectionId'].startswith(b['id'] + '-') for p in a['placements'])]
        subset = [{**a, 'sections': [s for s in a['sections'] if s.startswith(b['id'] + '-')],
                   'placements': [p for p in a['placements'] if p['sectionId'].startswith(b['id'] + '-')]} for a in subset]
        public_subset = [{k: v for k, v in a.items() if k != 'sourceReuse'} for a in subset]
        (DEST / f'textbook-catalog-{b["id"]}.js').write_text('window.TEXTBOOK_LAB_CATALOG=' + compact(public_subset) + ';\nwindow.TEXTBOOK_EXISTING=' + compact(existing if b['id'] == 'x1' else []) + ';\n', encoding='utf-8')
    audit = {'schema': 'textbook-visual-selection/v1', 'nodeCount': len(sections), 'assetCount': len(assets),
             'placementCount': sum(len(a['placements']) for a in assets) + sum(len(a['placements']) for a in existing),
             'selection': selection, 'assets': assets, 'existing': existing}
    (ROOT / 'docs/textbook-visual-selection.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(compact({k: audit[k] for k in ['nodeCount', 'assetCount', 'placementCount']}))


if __name__ == '__main__':
    main()
