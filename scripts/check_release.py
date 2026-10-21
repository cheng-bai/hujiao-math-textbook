#!/usr/bin/env python3
"""Dependency-free release audit. Does not rewrite website or historical evidence."""
from collections import Counter
import argparse
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import sys
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git', '.venv', '__pycache__', 'node_modules', 'release-checks', '_site'}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {'src', 'href', 'poster'} and value:
                self.urls.append(value)


def refs(name, text):
    if name.endswith('.html'):
        parser = Links()
        parser.feed(text)
        return parser.urls
    if name.endswith('.css'):
        return [x.strip(' \"\'') for x in re.findall(r'url\(([^)]+)\)', text)]
    return []


def local_url(raw):
    if not raw or raw.startswith('#'):
        return None
    url = urlsplit(raw)
    if url.scheme or url.netloc:
        return None
    return unquote(url.path) or None


def audit_site(root):
    """Check the exact deployed tree, not files left outside its document root."""
    root = Path(root).resolve()
    errors = []
    count = 0
    if not (root / 'index.html').is_file():
        errors.append({'missing': 'index.html'})
    for p in root.rglob('*'):
        if not p.is_file() or p.suffix not in {'.html', '.css'}:
            continue
        for raw in refs(p.name, p.read_text(encoding='utf-8')):
            path = local_url(raw)
            if path is None:
                continue
            target = (root / path.lstrip('/') if path.startswith('/') else p.parent / path).resolve()
            count += 1
            if not target.is_relative_to(root) or not target.exists():
                errors.append({'file': p.relative_to(root).as_posix(), 'missing': raw})
    result = {'status': 'passed' if not errors else 'failed',
              'local_references': count, 'errors': errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return bool(errors)


def audit():
    counts = Counter()
    errors = []
    files = [p for p in ROOT.rglob('*') if p.is_file()
             and not any(x in SKIP or 'verification' in x for x in p.relative_to(ROOT).parts)]
    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        if p.suffix in {'.html', '.css'} and not rel.startswith('sources/'):
            for raw in refs(p.name, p.read_text(encoding='utf-8')):
                path = local_url(raw)
                if path is None:
                    continue
                target = (ROOT / path.lstrip('/') if path.startswith('/') else p.parent / path).resolve()
                counts['local_references'] += 1
                if not target.is_relative_to(ROOT) or not target.exists():
                    errors.append({'file': rel, 'missing': raw})
        if p.suffix in {'.html', '.json', '.py', '.js', '.mjs', '.md', '.txt', '.css'}:
            text = p.read_text(encoding='utf-8')
            if re.search(r'/Users/[A-Za-z0-9_-]+/|C:\\Users\\[A-Za-z0-9_-]+\\', text):
                errors.append({'file': rel, 'error': 'machine-specific home path'})
            if re.search(r'gh[pousr]_[A-Za-z0-9]{25,}|sk-[A-Za-z0-9_-]{25,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----', text):
                errors.append({'file': rel, 'error': 'possible credential; inspect privately'})
        if p.name == 'student.zip':
            counts['student_zips'] += 1
            with zipfile.ZipFile(p) as archive:
                names = set(archive.namelist())
                if archive.testzip():
                    errors.append({'file': rel, 'error': 'ZIP CRC failure'})
                for name in names:
                    if name.startswith('/') or '..' in PurePosixPath(name).parts:
                        errors.append({'file': rel, 'error': 'unsafe ZIP entry'})
                    if not name.endswith(('.html', '.css')):
                        continue
                    for raw in refs(name, archive.read(name).decode('utf-8')):
                        path = local_url(raw)
                        if path is None:
                            continue
                        counts['zip_local_references'] += 1
                        target = posixpath.normpath(posixpath.join(posixpath.dirname(name), path))
                        if target not in names:
                            errors.append({'file': rel, 'entry': name, 'missing': raw})
        if p.name == 'manifest.json' and '教材可视化资源库' in rel:
            data = json.loads(p.read_text(encoding='utf-8'))
            counts['resource_packages'] += 1
            for item in data['files']:
                target = p.parent / item['path']
                if not target.is_file() or sha256(target.read_bytes()).hexdigest() != item['sha256']:
                    errors.append({'file': rel, 'error': 'manifest hash mismatch', 'entry': item['path']})
    catalog = json.loads((ROOT / 'batch/manifests/catalog.json').read_text(encoding='utf-8'))
    models = {}
    math_pattern = re.compile(r'\$\$[\s\S]*?\$\$|(?<!\$)\$(?!\$)[^$\n]+\$')
    for book in catalog['books']:
        for chapter in book['chapters']:
            for section in chapter['sections']:
                model = json.loads((ROOT / section['path']).read_text(encoding='utf-8'))
                models[section['id']] = model
                counts['sections'] += 1
                folder = ROOT / 'outputs/五册教材教参整合' / book['id'] / section['id']
                for name in ['teacher.html', 'student.html', 'student.zip']:
                    if not (folder / name).is_file():
                        errors.append({'section': section['id'], 'missing': name})
                build = json.loads((folder / 'build.json').read_text(encoding='utf-8'))
                for name, digest in build['artifact_hashes'].items():
                    counts['build_artifacts'] += 1
                    if sha256((folder / name).read_bytes()).hexdigest() != digest:
                        errors.append({'section': section['id'], 'artifact_hash_mismatch': name})
                for source, digest in model['source_hashes'].items():
                    p = ROOT / source
                    if not p.is_file() or sha256(p.read_bytes()).hexdigest() != digest:
                        errors.append({'section': section['id'], 'source_hash_mismatch': source})
                for block in model['blocks']:
                    text = block.get('markdown', '')
                    for mark in block.get('emphases', []):
                        counts['emphasis_ranges'] += 1
                        valid = 0 <= mark['start'] < mark['end'] <= len(text)
                        split_math = any(m.start() < mark[k] < m.end()
                                         for m in math_pattern.finditer(text) for k in ('start', 'end'))
                        if not valid or split_math:
                            errors.append({'section': section['id'], 'invalid_emphasis': mark.get('id')})
                    for field in ['markdown', 'answer', 'teacher_analysis']:
                        for image in re.findall(r'!\[[^\]]*\]\(((?:[^()]|\([^()]*\))+)\)', block.get(field, '')):
                            if not urlsplit(image).scheme and not (ROOT / image).is_file():
                                errors.append({'section': section['id'], 'missing_source_image': image})
    for book in catalog['books']:
        raw = (ROOT / 'scripts/visual-assets' / f'textbook-catalog-{book["id"]}.js').read_text(encoding='utf-8')
        assets = json.loads(raw.split('window.TEXTBOOK_LAB_CATALOG=', 1)[1].split(';\n', 1)[0])
        assets += json.loads(raw.split('window.TEXTBOOK_EXISTING=', 1)[1].split(';\n', 1)[0])
        for asset in assets:
            for placement in asset['placements']:
                sid = placement['sectionId']
                anchor = placement['afterBlockId']
                block = next(b for i, b in enumerate(models[sid]['blocks'])
                             if b.get('id', f'{sid}-b{i}') == anchor)
                digest = sha256(json.dumps(block, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
                counts['visual_anchors'] += 1
                if digest != placement['sourceSha256']:
                    errors.append({'section': sid, 'visual_anchor_hash_mismatch': anchor})
                for edition in ('teacher', 'student'):
                    page = ROOT / 'outputs/五册教材教参整合' / book['id'] / sid / f'{edition}.html'
                    if f'data-visual-source-sha="{digest}" id="{anchor}"' not in page.read_text(encoding='utf-8'):
                        errors.append({'section': sid, 'edition': edition, 'missing_visual_anchor': anchor})
    if counts['sections'] != 101 or counts['student_zips'] != 101:
        errors.append({'error': 'Expected 101 sections and 101 student ZIPs', 'counts': dict(counts)})
    result = {'status': 'passed' if not errors else 'failed', 'counts': dict(counts), 'errors': errors,
              'scope': 'Static file paths, source hashes, resource package hashes, and student ZIP integrity. Not mathematical or browser validation.'}
    dest = ROOT / 'release-checks'
    dest.mkdir(exist_ok=True)
    (dest / 'static.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return bool(errors)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-root', type=Path, help='Check only the exact static deployment tree')
    args = parser.parse_args()
    sys.exit(audit_site(args.site_root) if args.site_root else audit())
