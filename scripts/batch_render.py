#!/usr/bin/env python3
"""Render contract-v1 sections with the approved offline book components."""

from project_paths import use_project_root, launch_browser, portable_record
use_project_root()
import argparse
import ast
import copy
import hashlib
import html
import json
import os
import re
import shutil
import traceback
import zipfile
from pathlib import Path
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'outputs/五册教材教参整合'
TEMPLATE = ROOT / 'scripts/build_sample.py'
VENDOR = ROOT / 'designs/2026-10-19-沪教版教材教参整合样章/8.2-向量的数量积/vendor-katex'
VERSION = 'batch-render-v1.4'
IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(((?:[^()]|\([^()]*\))+)\)')


class SafeMarkdown:
    tags = {'table', 'thead', 'tbody', 'tfoot', 'tr', 'td', 'th', 'caption', 'br'}
    tag_token = re.compile(r'<[^>\r\n]{1,512}>')
    tag_parts = re.compile(r'^\s*<(\/?)\s*([a-zA-Z][\w-]*)\b([^>]*)>\s*$')

    def __init__(self):
        self.md = MarkdownIt('commonmark', {'html': True}).enable('table')

    def render(self, text):
        def safe_tag(match):
            raw = match[0]
            parsed = self.tag_parts.match(raw)
            if not parsed:
                return raw.replace('<', '&lt;', 1)
            closing, tag, attrs = parsed.groups()
            tag = tag.lower()
            if tag not in self.tags:
                return raw.replace('<', '&lt;', 1)
            if closing:
                if tag == 'br':
                    return raw.replace('<', '&lt;', 1)
                return f'</{tag}>' + ('</div>' if tag == 'table' else '')
            allowed = ''
            if tag in {'td', 'th'}:
                for key, value in re.findall(r'\b(rowspan|colspan)\s*=\s*["\']?(\d+)["\']?', attrs, re.I):
                    if 0 < int(value) <= 100:
                        allowed += f' {key.lower()}="{int(value)}"'
            return ('<div class="source-table">' if tag == 'table' else '') + f'<{tag}{allowed}>'

        text = self.tag_token.sub(safe_tag, text)
        return self.md.render(text)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    temp.write_text(json.dumps(portable_record(value), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def safe(value):
    return re.sub(r'[/\\:*?"<>|\x00-\x1f]', '-', str(value)).strip('. ') or 'section'


def output_dir(data):
    return OUTPUT / safe(data['book_id']) / safe(data['id'])


def textbook_assets(book_id):
    path = ROOT / 'scripts/visual-assets' / f'textbook-catalog-{book_id}.js'
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding='utf-8').split('window.TEXTBOOK_LAB_CATALOG=', 1)[1].split(';\n', 1)[0])


def visual_files(data, student):
    names = [f"textbook-catalog-{data['book_id']}.js", 'visual-manifest.js']
    for asset in textbook_assets(data['book_id']):
        if data['id'] in asset['sections']:
            names.extend([asset['payload'], asset['preview']])
    if data['book_id'] == 'x1':
        names.extend(['module-data-student.js' if student else 'module-data.js', 'conic-catalog.js', 'ellipse-preview.png', 'Anatomy-LICENSE.txt', 'Question-Studio-LICENSE.txt'])
        kind = {'x1-2-2': 'ellipse', 'x1-2-3': 'hyperbola', 'x1-2-4': 'parabola'}.get(data['id'])
        if kind:
            names.extend([f'conic-{kind}-{"student" if student else "teacher"}.js', f'conic-{kind}-preview.svg'])
    return names


def shared_assets(book_id):
    dest = OUTPUT / safe(book_id) / '_shared'
    dest.mkdir(parents=True, exist_ok=True)
    for name in ['book.css', 'book.js']:
        source, target = ROOT / 'scripts' / name, dest / name
        if not target.exists() or sha(source) != sha(target):
            shutil.copy2(source, target)
    for source in VENDOR.rglob('*'):
        if not source.is_file():
            continue
        target = dest / 'vendor-katex' / source.relative_to(VENDOR)
        if not target.exists() or sha(source) != sha(target):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    if book_id in ['bx1', 'bx2', 'bx3', 'x1', 'x2']:
        for name in ['visual-book.css', 'visual-book.js']:
            source, target = ROOT / 'scripts' / name, dest / name
            if not target.exists() or sha(source) != sha(target):
                shutil.copy2(source, target)
        visual_dir = dest / 'visual-assets'
        visual_dir.mkdir(exist_ok=True)
        names = []
        if book_id == 'x1':
            names.extend(['module-data.js', 'module-data-student.js', 'ellipse-preview.png', 'Anatomy-LICENSE.txt', 'Question-Studio-LICENSE.txt'])
            names.extend(p.name for p in (ROOT / 'scripts/visual-assets').glob('conic-*'))
        catalog_file = ROOT / 'scripts/visual-assets' / f'textbook-catalog-{book_id}.js'
        if catalog_file.exists():
            names.append(catalog_file.name)
            for asset in textbook_assets(book_id):
                names.extend([asset['payload'], asset['preview']])
        for name in names:
            source, target = ROOT / 'scripts/visual-assets' / name, visual_dir / name
            if not target.exists() or sha(source) != sha(target):
                shutil.copy2(source, target)
        manifest = {'schema': 'hujiao-visual-manifest/v1', 'sourceBook': book_id, 'sections': {}}
        catalog = json.loads((ROOT / 'batch/manifests/catalog.json').read_text(encoding='utf-8'))
        book = next(item for item in catalog['books'] if item['id'] == book_id)
        for chapter in book['chapters']:
            for section in chapter['sections']:
                source = ROOT / section['path']
                if not source.is_file():
                    continue
                section_data = json.loads(source.read_text(encoding='utf-8'))
                anchors = [block.get('id', safe(section['id']) + f'-b{index}') for index, block in enumerate(section_data['blocks'])
                           if block['type'] in ['section', 'heading', 'prose', 'question', 'key-point']
                           and not block.get('teacher_only')]
                manifest['sections'][section['id']] = {
                    'title': section.get('title', section['id']),
                    'chapter': chapter['title'],
                    'anchors': anchors,
                }
        manifest_path = visual_dir / 'visual-manifest.js'
        manifest_source = 'window.VISUAL_MANIFEST = ' + json.dumps(manifest, ensure_ascii=False, separators=(',', ':')) + ';\n'
        if not manifest_path.exists() or manifest_path.read_text(encoding='utf-8') != manifest_source:
            manifest_path.write_text(manifest_source, encoding='utf-8')
    return dest


def fingerprint(path, data):
    parts = [VERSION, sha(__file__), sha(path), sha(TEMPLATE)]
    extras = [ROOT / 'scripts/book.css', ROOT / 'scripts/book.js', *sorted(VENDOR.rglob('*'))]
    if data['book_id'] in ['bx1', 'bx2', 'bx3', 'x1', 'x2']:
        extras.extend([ROOT / 'scripts/visual-book.css', ROOT / 'scripts/visual-book.js', *sorted((ROOT / 'scripts/visual-assets').glob('*'))])
    for p in extras:
        if p.is_file():
            parts.extend([p.name, sha(p)])
    for p, expected in sorted(data.get('source_hashes', {}).items()):
        parts.extend([p, expected, sha(p) if Path(p).is_file() else 'MISSING'])
    # A changed/deleted original figure invalidates a previously passed build too.
    for b in data['blocks']:
        for field in ['markdown', 'answer', 'teacher_analysis']:
            for _, source in IMAGE_RE.findall(b.get(field, '')):
                p = Path(source)
                parts.extend([source, sha(p) if p.is_file() else 'MISSING'])
    return hashlib.sha256('\n'.join(parts).encode()).hexdigest()


def approved_components(blocks, source_links):
    # Load only pure renderer functions: importing the sample executes chapter-8 I/O.
    tree = ast.parse(TEMPLATE.read_text(encoding='utf-8'))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {'render_md', 'render_block', 'print_panel'}]
    scope = {'html': html, 're': re, 'MD': SafeMarkdown(), 'BLOCKS': blocks}

    def provenance(items):
        links = []
        for p in items:
            label = '教材' if p['source'] == 'book' else '教参'
            links.append(f'<a href="{html.escape(source_links[p["source"]], quote=True)}" target="_blank" rel="noopener">{label} L{p["start"]}–{p["end"]}</a>')
        return '<div class="provenance teacher-only">' + ' · '.join(links) + '</div>' if links else ''

    scope['provenance'] = provenance
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(TEMPLATE), 'exec'), scope)

    base_render_block = scope['render_block']

    def render_block_with_math_titles(block, student=False):
        rendered = base_render_block(block, student)
        title = block.get('title', '')
        if not title or block['type'] == 'section':
            return rendered
        inline = scope['render_md'](html.escape(title, quote=False)).strip()
        inline = re.sub(r'^<p>|</p>$', '', inline)
        kind, title_tag = block['type'], None
        if kind == 'heading':
            title_tag = ('<h3 class="group-heading" id="' + html.escape(block.get('id',''), quote=True) + '">' + title + '</h3>')
        elif kind == 'question':
            title_tag = '<div class="question-label">' + title + '</div>'
        elif kind in ['teacher', 'editor', 'intro']:
            title_tag = '<h3>' + title + '</h3>'
        if title_tag and title in title_tag:
            rendered = rendered.replace(title_tag, title_tag.replace(title, inline), 1)
        return rendered

    scope['render_block'] = render_block_with_math_titles
    return scope


def page(data, blocks, components, student=False):
    esc = lambda s: html.escape(str(s), quote=True)
    section, title = esc(data['section']), esc(data['title'])
    questions = [b for b in blocks if b['type'] == 'question' and not b.get('teacher_only')]
    parts, active = [], False
    source_hashes = {b.get('id', safe(data['id']) + f'-b{i}'): hashlib.sha256(json.dumps(b, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest() for i, b in enumerate(data['blocks'])}
    for b in blocks:
        if student and (b.get('teacher_only') or b['type'] in ['intro', 'teacher', 'editor']):
            continue
        if b['type'] == 'section':
            if active:
                parts.append('</section>')
            parts.append(f'<section class="content-module" data-module="{esc(b["id"])}" data-title="{esc(b["title"])}">')
            active = True
        rendered = components['render_block'](b, student)
        if b['type'] == 'prose' and b['id'] in source_hashes:
            rendered = rendered.replace(' id="' + esc(b['id']) + '"', ' data-visual-source-sha="' + source_hashes[b['id']] + '" id="' + esc(b['id']) + '"', 1)
        parts.append(rendered)
    if active:
        parts.append('</section>')
    modules = [b for b in blocks if b['type'] == 'section' and not (student and b.get('teacher_only'))]
    nav = ''.join(f'<a href="#{esc(b["id"])}"><span>{esc(b["number"])}</span>{esc(b["title"])}</a>' for b in modules)
    controls = '<span class="student-tag">学生阅读版 · 不含题答与教师内容</span>' if student else '<button id="answer-toggle" aria-pressed="false">隐藏全部答案</button><button id="notes-toggle" aria-pressed="false">隐藏教师批注</button><a class="mode-link" href="student.html">学生预览 ↗</a><a class="package-link" href="student.zip" download>学生包 ↓</a>'
    controls += '<button id="density-toggle" aria-pressed="false">舒展阅读</button><button id="print-open">按内容打印</button>'
    visual_assets = ''
    controls += '<button id="visual-open">可视化模块</button>'
    names = visual_files(data, student)
    visual_assets = '<link rel="stylesheet" href="../_shared/visual-book.css">'
    visual_assets += ''.join(f'<script defer src="../_shared/visual-assets/{name}"></script>' for name in names if name.endswith('.js'))
    visual_assets += '<script defer src="../_shared/visual-book.js"></script>'
    examples = sum(q['category'] == '例题' for q in questions)
    foot = '本文件为独立学生阅读版，不含答案、解析与教师材料。' if student else '原始教材与教参只读保留；缺答、来源疑点与校核状态见本节检查记录。结构、离线渲染和打印检查不代替数学复核。'
    mode = 'student' if student else 'teacher'
    blocking = [i for i in data.get('issues', []) if isinstance(i, dict) and i.get('severity') in ['blocking', 'error', 'critical']]
    warning = ''
    if blocking and not student:
        items = ''.join('<li>' + esc(i.get('code', 'source-issue')) + ' · ' + esc(i.get('question', i.get('group', ''))) + ' ' + esc(i.get('message', '待核对来源或答案')) + '</li>' for i in blocking)
        warning = '<aside class="editor teacher-only source-warning"><h2>来源 / 题答待核，非完成稿</h2><p>下列来源缺口尚未解决。本页仅供核对，不代表已通过验收。</p><ul>' + items + '</ul></aside>'
    extra_style = '''<style>
.source-warning{border-color:#a43825;background:#fff0e5;color:#702b20}.source-warning h2{font-size:22px}
.source-table{max-width:100%;overflow-x:auto;margin:16px 0}.source-table table{border-collapse:collapse;min-width:60%;font-size:.94em}.source-table td,.source-table th{border:1px solid var(--rule);padding:6px 10px;vertical-align:top}.source-table th{background:#edf0e7}
@media screen and (max-width:720px){.math:not(.display){display:inline-block;max-width:100%;overflow-x:auto;vertical-align:middle}.source-table table{min-width:100%}}
@media print{.source-table{overflow:visible}.source-table table{max-width:100%;font-size:9pt}.source-table tr{break-inside:avoid}#print-output .question p:has(>img){break-after:auto}#print-output .print-module:last-child>.question:last-child{margin-top:-1mm!important;margin-bottom:0!important}}
</style>'''
    return f'''<!doctype html>
<html lang="zh-CN" data-mode="{mode}" data-section-id="{esc(data['id'])}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="author" content="chengbai"><title>{section} {title} · {'学生阅读版' if student else '教师整合版'}</title><link rel="stylesheet" href="../_shared/vendor-katex/katex.min.css"><link rel="stylesheet" href="../_shared/book.css">{visual_assets}{extra_style}<script defer src="../_shared/vendor-katex/katex.min.js"></script><script defer src="../_shared/book.js"></script></head>
<body><a class="skip" href="#reading">跳到正文</a><div class="reading-progress" aria-hidden="true"></div><aside class="sidebar"><a class="brand" href="{'#top' if student else '../index.html'}">沪教数学<span>教材 × 教参 · 整合书</span></a><div class="volume-label">{esc(data['book_title'])} / {esc(data.get('chapter_title', ''))}</div><div class="spine-number">{section}</div><nav aria-label="本节目录">{nav}</nav><div class="sidebar-foot">沪教数学讲义<br>{'学生独立文件' if student else '教师阅读 / 备课'}</div></aside>
<div class="book-shell"><header class="toolbar"><span class="toolbar-label">{'学生阅读' if student else '教师阅读'} <span class="subtle">/ {section}</span></span><div class="controls">{controls}</div></header><main id="reading">{warning}<header class="chapter-cover" id="top"><div class="eyebrow">SHANGHAI MATHEMATICS · SECTION {section}</div><p class="edition">{'学生阅读版' if student else '教师整合版'} / 沪教版高中数学</p><h1>{title}<span class="cover-dot">.</span></h1><p class="cover-deck">{esc(data['book_title'])}<br>{esc(data.get('chapter_title',''))} · 保留教材主线与原题</p><div class="chapter-meta"><span>{len(modules)} 个阅读模块</span><span>{examples} 个例题</span><span>{len(questions)-examples} 道练习与习题</span></div></header><div class="book-body">{''.join(parts)}</div><footer class="book-footer"><p>{foot}</p><a href="#top">返回本节开头 ↑</a></footer></main></div>{components['print_panel'](student)}<div id="status" role="status" aria-live="polite"></div></body></html>'''


def render_section(path, force=False):
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding='utf-8'))
    out = output_dir(data)
    out.mkdir(parents=True, exist_ok=True)
    build_path = out / 'build.json'
    fp = fingerprint(path, data)
    shared = shared_assets(data['book_id'])
    if not force and build_path.exists():
        previous = json.loads(build_path.read_text(encoding='utf-8'))
        if previous.get('fingerprint') == fp and previous.get('artifact_hashes') and all((out / n).is_file() and sha(out / n) == digest for n, digest in previous['artifact_hashes'].items()):
            previous['output'] = str(ROOT / previous['output'])
            return {**previous, 'cached': True}
    issues = list(data.get('issues', []))
    for source, expected in data.get('source_hashes', {}).items():
        if not Path(source).is_file() or sha(source) != expected:
            issues.append({'severity': 'blocking', 'code': 'source-drift', 'source': source})
    source_links = {}
    for key, raw in data.get('sources', {}).items():
        original = Path(raw)
        if not original.is_file():
            issues.append({'severity': 'blocking', 'code': 'missing-source', 'source': raw})
            source_links[key] = '#missing-source'
            continue
        target = shared.parent / '_sources' / (sha(original)[:16] + '-' + safe(original.name))
        target.parent.mkdir(exist_ok=True)
        if not target.exists():
            shutil.copy2(original, target)
        source_links[key] = Path(os.path.relpath(target, out)).as_posix()
    blocks = copy.deepcopy(data['blocks'])
    for index, block in enumerate(blocks):
        block.setdefault('id', safe(data['id']) + f'-b{index}')
    if not blocks or blocks[0]['type'] != 'section':
        blocks.insert(0, {'type': 'section', 'id': safe(data['id']) + '-reading', 'title': data['title'], 'number': '01', 'subtitle': '', 'markdown': '', 'provenance': []})
    assets = {}
    for index, b in enumerate(blocks):
        b.setdefault('markdown', '')
        b.setdefault('title', '')
        b.setdefault('provenance', [])
        b.setdefault('id', safe(data['id']) + f'-b{index}')
        for mark in b.get('emphases', []):
            if mark.get('kind') == 'definition':
                mark['kind'] = 'concept'
        if b['type'] == 'section':
            b.setdefault('number', str(index+1).zfill(2))
            b.setdefault('subtitle', '')
        if b['type'] == 'question':
            for field, default in [('answer', ''), ('teacher_analysis', ''), ('answer_provenance', []), ('analysis_provenance', []), ('provenance_question', b['provenance']), ('category', '习题')]:
                b.setdefault(field, default)
            if not b['answer'].strip():
                issues.append({'severity': 'blocking', 'code': 'missing-answer', 'question': b['id']})
        for field in ['markdown', 'answer', 'teacher_analysis']:
            original_text = b.get(field, '')
            def image(m):
                raw = ROOT / m[2]
                if not raw.is_file():
                    issues.append({'severity': 'blocking', 'code': 'missing-image', 'block': b['id'], 'source': str(raw)})
                    return m[0]
                image_hash = sha(raw)
                private = b.get('teacher_only') or b['type'] in ['teacher', 'editor', 'intro'] or field != 'markdown'
                ref = 'images/' + ('private-' if private else 'book-') + image_hash[:20] + raw.suffix.lower()
                target = out / ref
                target.parent.mkdir(exist_ok=True)
                if not target.exists() or sha(target) != image_hash:
                    shutil.copy2(raw, target)
                assets[ref] = {'source': str(raw), 'sha256': image_hash, 'private': bool(private)}
                return f'![{m[1]}]({ref})'
            b[field] = IMAGE_RE.sub(image, original_text)
            # Image-link length changes must not displace editorial emphasis boundaries.
            if field == 'markdown' and b.get('emphases'):
                for mark in b['emphases']:
                    for boundary in ['start', 'end']:
                        mark[boundary] = len(IMAGE_RE.sub(image, original_text[:mark[boundary]]))
    components = approved_components(blocks, source_links)
    view_data = {**data, 'issues': issues}
    teacher, student = page(view_data, blocks, components), page(view_data, blocks, components, True)
    (out / 'teacher.html').write_text(teacher, encoding='utf-8')
    (out / 'student.html').write_text(student, encoding='utf-8')
    # Only this explicit allowlist goes into the distributable student archive.
    student_images = sorted(set(re.findall(r'<img src="([^"]+)"', student)))
    standalone = student.replace('../_shared/', '').replace('href="../index.html"', 'href="#top"')
    with zipfile.ZipFile(out / 'student.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('student.html', standalone)
        for name in ['book.css', 'book.js']:
            z.write(shared / name, name)
        for name in ['visual-book.css', 'visual-book.js']:
            z.write(shared / name, name)
        for name in visual_files(data, True):
            z.write(shared / 'visual-assets' / name, 'visual-assets/' + name)
        for item in (shared / 'vendor-katex').rglob('*'):
            if item.is_file():
                z.write(item, item.relative_to(shared).as_posix())
        for ref in student_images:
            if (out / ref).is_file():
                z.write(out / ref, ref)
    question_blocks = [b for b in blocks if b['type'] == 'question']
    report = {'schema_version': 1, 'version': VERSION, 'id': data['id'], 'book_id': data['book_id'], 'section': data['section'], 'title': data['title'], 'section_json': str(path), 'output': str(out), 'fingerprint': fp, 'status': 'rendered_with_issues' if issues else 'rendered', 'questions': len(question_blocks), 'answers': sum(bool(q['answer'].strip()) for q in question_blocks), 'teacher_file': 'teacher.html', 'student_file': 'student.html', 'student_zip': 'student.zip', 'assets': assets, 'issues': issues, 'source_hashes': data.get('source_hashes', {}), 'student_images': student_images, 'math_review': 'separate'}
    save_json(out / 'content.json', blocks)
    report['artifact_hashes'] = {name: sha(out / name) for name in ['teacher.html', 'student.html', 'student.zip', 'content.json']}
    save_json(build_path, report)
    save_json(out / 'metadata.json', report)
    return report


def section_paths(catalog, book=None):
    data = json.loads(Path(catalog).read_text(encoding='utf-8'))
    return [ROOT / s['path'] for b in data['books'] if book is None or b['id'] == book for c in b['chapters'] for s in c['sections']]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--section', type=Path)
    source.add_argument('--catalog', type=Path)
    parser.add_argument('--book')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    paths = [args.section] if args.section else section_paths(args.catalog, args.book)
    failures = 0
    for path in paths:
        try:
            result = render_section(path, args.force)
            failures += any(isinstance(i, dict) and i.get('severity') in ['blocking', 'error', 'critical'] for i in result.get('issues', []))
            print(json.dumps(portable_record({k: result.get(k) for k in ['id', 'status', 'questions', 'answers', 'cached', 'output']}), ensure_ascii=False), flush=True)
        except Exception as error:
            failures += 1
            try:
                failed_data = json.loads(Path(path).read_text(encoding='utf-8'))
                failure_out = output_dir(failed_data)
                failure_out.mkdir(parents=True, exist_ok=True)
                save_json(failure_out / 'render-error.json', {'status': 'render_error', 'section_json': str(path), 'error': str(error), 'traceback': traceback.format_exc()})
            except Exception:
                pass
            print(json.dumps({'section_json': str(path), 'status': 'render_error', 'error': str(error)}, ensure_ascii=False), flush=True)
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
