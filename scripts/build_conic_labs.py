#!/usr/bin/env python3
"""Adapt the user's existing self-contained conic labs, without altering originals."""

from project_paths import use_project_root, launch_browser
use_project_root()
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('sources/visuals/圆锥曲线实验室.html')
OUT = ROOT / 'scripts/visual-assets'

COMPACT_CSS = '''<style>
body{background:#fffef8!important} .masthead,.intro,#instrument,main>footer{display:none!important}
main{max-width:none!important;padding:8px 12px!important}.shared{padding:5px 0!important;margin:0!important}
.mode-nav{display:none!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:4px!important;margin:5px 0 9px!important}
body[data-textbook-more="true"] .mode-nav{display:grid!important}
.mode-nav button{padding:6px!important;min-width:0!important;min-height:32px!important;gap:5px!important}.mode-nav b{font-size:11px!important}.mode-nav small{display:none!important}
.mode-nav .nav-number{font-size:9px!important}.experiment-grid{grid-template-columns:minmax(0,1.25fr) minmax(0,1fr)!important;gap:13px!important}
.drawing{padding:0!important}.drawing svg{display:block;width:100%!important;height:auto!important;max-height:300px!important}
.figure-heading,.figure-bottom,.legend{font-size:10px!important;padding:6px 10px!important}.figure-bottom{gap:6px!important;flex-wrap:wrap!important;min-height:0!important}
.controls{padding:7px 0!important;margin:0!important}.sliders{gap:9px!important}.sliders label{font-size:10px!important}
.button-row{gap:5px!important;margin-top:6px!important}button{font-size:10px!important;padding:5px 7px!important}
.explanation h2{font-size:19px!important;margin:4px 0!important}.explanation p{font-size:11px!important;line-height:1.65!important;margin:7px 0!important}
.formula{padding:8px!important;margin:7px 0!important;font-size:13px!important;overflow:auto!important}.observe{padding:7px!important}
.metrics{gap:5px!important}.metric{padding:6px!important}.metric small{font-size:9px!important}.metric strong{font-size:16px!important}
.lesson-grid{margin-top:8px!important;padding:8px 0!important;gap:12px!important}.lesson-grid h3{font-size:14px!important;margin:5px 0!important}.lesson-grid li,.lesson-grid p{font-size:11px!important}.lesson-grid li{margin:3px 0!important}
.shared{gap:12px!important;align-items:center!important}.shared h3{font-size:15px!important;margin:5px 0!important}.shared p{font-size:10px!important;margin:5px 0!important}.shared-math{font-size:12px!important}.shared .katex-display{margin:4px 0!important}
.proof{margin-top:9px!important}.proof summary{font-size:11px!important}.proof p{font-size:12px!important}
.textbook-lab-note{font:10px/1.6 "PingFang SC",sans-serif;color:#62785c;margin:0 0 7px;border-left:2px solid #9aaf88;padding-left:8px}.textbook-lab-note button{margin-left:7px}
@media(max-width:600px){.experiment-grid{grid-template-columns:minmax(0,1fr)!important}.mode-nav{grid-template-columns:repeat(2,minmax(0,1fr))!important}.drawing svg{max-height:270px!important}.lesson-grid{grid-template-columns:1fr!important}.explanation{border:0!important;padding:0!important}.sliders{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
</style>'''

SPECS = {
    'ellipse': ('2', '椭圆', '双焦点距离和', '改变轴比并拖动点，观察两段距离的和；其他入口可用于后续拓展。',
                dict(mode='foci', a=5, ratio=.8, degrees=35, blend=1, yaw=32, boundary=False)),
    'hyperbola': ('3', '双曲线', '双焦点距离差的绝对值', '切换左右支，区分有向差与差的绝对值，并比较距离差的边界。',
                  dict(mode='foci', size=3, ratio=.75, q=.8, branch=1, yaw=32, rotation=1,
                       envelope=False, conjugate=False, boundary='normal', degenerate=False, rays=False)),
    'parabola': ('4', '抛物线', '焦点—准线等距', '拖动曲线上一点，比较到焦点与到准线的距离；p 表示焦点到准线的距离。',
                 dict(mode='foci', size=2, ratio=.75, q=.8, branch=1, yaw=32, rotation=1,
                      envelope=False, conjugate=False, boundary='normal', degenerate=False, rays=False)),
}


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def thumbnail(kind):
    paths = []
    for branch in ([-1, 1] if kind == 'hyperbola' else [1]):
        points = []
        for i in range(121):
            t = i / 120
            if kind == 'ellipse':
                x, y = 80 * math.cos(t * math.tau), 53 * math.sin(t * math.tau)
            elif kind == 'hyperbola':
                q = (t - .5) * 3.6
                x, y = branch * 40 * math.hypot(1, q), 32 * q
            else:
                q = (t - .5) * 4
                x, y = 21 * q*q - 36, 30 * q
            points.append(f'{150+x:.2f},{85-y:.2f}')
        paths.append('<path d="M'+' L'.join(points)+'"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 175"><rect width="300" height="175" fill="#fffef8"/>'
            '<path d="M15 85H285M150 10V160" stroke="#c3cabb" fill="none"/>'
            '<g fill="none" stroke="#355d4b" stroke-width="2.5">'+''.join(paths)+'</g></svg>')


def json_value(text, marker):
    start = text.index(marker) + len(marker)
    value, length = json.JSONDecoder().raw_decode(text[start:])
    return value, start, start + length


def adapt(source, kind, student):
    # The redundant nested instrument is already an independently reusable asset.
    if kind == 'ellipse':
        _, start, end = json_value(source, 'const INSTRUMENT=')
        source = source[:start] + '""' + source[end:]
        source = re.sub(r"^\$\('#instrument'\)\.addEventListener[^\n]*", '', source, flags=re.M)
        source = re.sub(r'<details id="instrument">.*?</details>', '', source, flags=re.S)
    content, start, end = json_value(source, 'CONTENT=')
    if student:
        for item in content:
            item['proof'] = []
            item['question'] = ''
        source = source[:start] + json.dumps(content, ensure_ascii=True, separators=(',', ':')) + source[end:]
        source = re.sub(r'<details id="proof".*?</details>',
                        '<div id="proof" hidden><div id="proof-body"></div><p id="boundary"></p></div>', source, flags=re.S)
        source = re.sub(r'<section class="question">.*?</section>', '<section hidden><h3 id="question"></h3></section>', source, flags=re.S)
    source = source.replace("window.addEventListener('beforeprint',()=>$('#proof').open=true);", '')
    controls = 'controls' if kind == 'ellipse' else 'modeControls'
    adapter = f'''window.TixuPlugin={{
getState:()=>{{const {{playing,...saved}}=state;return JSON.parse(JSON.stringify(saved));}},
setState:next=>{{play(false);Object.assign(state,next,{{playing:false}});switchMode(state.mode,false);{controls}();render();if(state.mode!=='foci')setMore(true);}},
pause:()=>play(false)
}};
const moreButton=document.querySelector('#textbook-more');
function setMore(value){{document.body.dataset.textbookMore=String(value);moreButton.setAttribute('aria-expanded',String(value));moreButton.textContent=value?'收起实验入口':'展开7项拓展';}}
moreButton.addEventListener('click',()=>setMore(document.body.dataset.textbookMore!=='true'));
setMore(false);
'''
    # Insert inside the original closure to preserve its math model and full state.
    marker = 'readHash();motionSetting();'
    assert source.count(marker) == 1
    source = source.replace(marker, marker + adapter)
    note = f'<p class="textbook-lab-note">教材主入口：{SPECS[kind][2]}。其余为可选拓展，不作并列必学定义。<button id="textbook-more" aria-expanded="false" aria-controls="textbook-modes">展开7项拓展</button></p>'
    source = source.replace('<nav class="mode-nav"', note + '<nav class="mode-nav"', 1)
    source = source.replace('<nav class="mode-nav"', '<nav id="textbook-modes" class="mode-nav"', 1)
    return source.replace('</head>', COMPACT_CSS + '</head>', 1), content


def main():
    original = SOURCE.read_text(encoding='utf-8')
    pages, _, _ = json_value(original, 'const PAGES=')
    catalog = []
    provenance = {'source': str(SOURCE), 'source_sha256': digest(original), 'adaptation': 'hujiao-conic-labs/v1', 'assets': {}}
    ellipse_reference = Path('sources/visuals/ellipse-definitions.html')
    provenance['ellipse_reference'] = {
        'requested_url': 'http://127.0.0.1:53015/ellipse-definitions.html',
        'local_file': str(ellipse_reference),
        'matches_embedded_ellipse': ellipse_reference.is_file() and digest(ellipse_reference.read_text(encoding='utf-8')) == digest(pages['ellipse']),
        'runtime_requires_server': False,
    }
    for kind, (section, title, concept, goal, initial) in SPECS.items():
        asset_id = kind + '-lab'
        (OUT / f'conic-{kind}-preview.svg').write_text(thumbnail(kind), encoding='utf-8')
        hashes = {}
        for mode in ['teacher', 'student']:
            html, content = adapt(pages[kind], kind, mode == 'student')
            target = OUT / f'conic-{kind}-{mode}.js'
            target.write_text('window.CONIC_LAB_HTML = window.CONIC_LAB_HTML || {};\nwindow.CONIC_LAB_HTML['
                              + json.dumps(asset_id) + '] = ' + json.dumps(html, ensure_ascii=True) + ';\n', encoding='utf-8')
            hashes[mode] = digest(target.read_text(encoding='utf-8'))
        rules = {}
        ranges = dict(a=(3, 7), ratio=(.2, 1) if kind == 'ellipse' else (.35, 1.5), degrees=(0, 360),
                      blend=(0, 1), yaw=(-80, 80), size=(1.5, 5) if kind == 'hyperbola' else (.8, 4),
                      q=(-2.4, 2.4), rotation=(0, 1))
        for key, value in initial.items():
            if key == 'mode':
                rules[key] = {'enum': [item['id'] for item in content]}
            elif key == 'branch':
                rules[key] = {'enum': [-1, 1]}
            elif isinstance(value, bool):
                rules[key] = {'type': 'boolean'}
            elif key == 'boundary':
                rules[key] = {'enum': ['normal', 'zero', 'limit', 'empty']}
            else:
                rules[key] = {'minimum': ranges[key][0], 'maximum': ranges[key][1]}
        catalog.append(dict(id=asset_id, kind=kind, title=title+' · 定义与拓展实验', category='圆锥曲线',
                            sections=['x1-2-'+section], scene='foci', version='conic-snapshot-20261019-v1',
                            hash=digest(pages[kind]), initial=initial, goal=goal, parameters=rules,
                            defaultAfter='x1-2-'+section+'-b3'))
        provenance['assets'][asset_id] = {'original_html_sha256': digest(pages[kind]), 'derived_files_sha256': hashes,
                                        'default_location': '定义与标准方程正文之后、例1之前', 'math_model': 'unchanged'}
    (OUT / 'conic-catalog.js').write_text('window.CONIC_LAB_CATALOG = ' + json.dumps(catalog, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
    dest = ROOT / 'docs/conic-labs-integration.json'
    dest.write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Built 3 existing labs, with separate teacher/student assets and fixed source hashes.')


if __name__ == '__main__':
    main()
