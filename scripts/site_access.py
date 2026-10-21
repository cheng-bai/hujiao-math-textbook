#!/usr/bin/env python3
"""Install the explicitly non-secure reading gate on first-party static pages."""
from pathlib import Path
import os
import shutil

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'outputs' / '_shared'
NAMES = ('site-access.css', 'site-access.js')
FIRST_PARTY_OUTPUTS = ('五册教材教参整合', '教材可视化编排小样',
                       '空间向量基本定理-最小试作', '教材高清图与难度校准-20261021')


def access_head(prefix):
    return (f'<link rel="stylesheet" href="{prefix}site-access.css">'
            f'<script defer src="{prefix}site-access.js"></script>')


def install_assets(destination=PUBLIC):
    destination.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        source, target = ROOT / 'scripts' / name, destination / name
        if not target.exists() or source.read_bytes() != target.read_bytes():
            shutil.copy2(source, target)


def install_page(path):
    text = path.read_text(encoding='utf-8')
    if 'site-access.js' in text:
        return False
    prefix = Path(os.path.relpath(PUBLIC, path.parent)).as_posix() + '/'
    text = text.replace('</head>', access_head(prefix) + '</head>', 1)
    if '<body' in text:
        start = text.index('>', text.index('<body')) + 1
        text = text[:start] + '<noscript><p>请启用 JavaScript，再输入访问口令进入阅读。</p></noscript>' + text[start:]
    path.write_text(text, encoding='utf-8')
    return True


def main():
    print(f'Reading gate installed on {install_project_pages()} additional pages (not authentication).')


def install_project_pages():
    install_assets()
    count = 0
    # Sealed visualization packages retain their original manifest hashes.
    for folder in FIRST_PARTY_OUTPUTS:
        for path in sorted((ROOT / 'outputs' / folder).rglob('*.html')):
            count += install_page(path)
    return count


if __name__ == '__main__':
    main()
