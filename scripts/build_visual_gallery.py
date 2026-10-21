#!/usr/bin/env python3
"""Build a local, navigable gallery for the textbook visualization audit."""
from __future__ import annotations

from project_paths import use_project_root, launch_browser
use_project_root()

import argparse
import html
import json
import os
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT = ROOT / 'docs/textbook-visual-selection.json'
DEFAULT_CATALOG = ROOT / 'batch/manifests/catalog.json'
DEFAULT_OUTPUT = ROOT / 'outputs/五册教材教参整合/visual-index.html'

BOOK_NAMES = {
    'bx1': '必修第一册', 'bx2': '必修第二册', 'bx3': '必修第三册',
    'x1': '选择性必修第一册', 'x2': '选择性必修第二册',
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def local_href(source: Path, destination: Path) -> str:
    return quote(Path(os.path.relpath(destination, source.parent)).as_posix(), safe='/%.-_')


def load_verification(path: Path | None) -> dict | None:
    if path is None:
        return None
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('--verification must point to a JSON object')
    return value


def verification_html(value: dict | None, source_path: Path | None) -> str:
    if value is None:
        return ('<p class="muted">未提供验证 JSON；此索引只说明资源与落点，不代表数学、题答或版面已验收。</p>')
    rows = []
    for key in ('status', 'count', 'checks', 'assets', 'placementSections', 'nodes', 'errors'):
        if key not in value or isinstance(value[key], dict):
            continue
        display = len(value[key]) if key == 'errors' and isinstance(value[key], list) else value[key]
        rows.append(f'<div class="verify-stat"><span>{esc(key + " (count)" if key == "errors" else key)}</span><strong>{esc(display)}</strong></div>')
    details = value.get('checksDetail')
    if isinstance(details, list):
        if all(isinstance(item, dict) and 'passed' in item for item in details):
            passed = sum(bool(item['passed']) for item in details)
            rows.append(f'<div class="verify-stat"><span>checksDetail通过项</span><strong>{passed} / {len(details)}</strong></div>')
        else:
            rows.append(f'<div class="verify-stat"><span>checksDetail记录数</span><strong>{len(details)}</strong></div>')
    limitations = value.get('limitations', value.get('limits', []))
    limitation_html = ''.join(f'<li>{esc(item)}</li>' for item in limitations if isinstance(item, (str, int, float))) if isinstance(limitations, list) else ''
    source = esc(source_path.name if source_path else 'verification.json')
    return (f'<p>读取记录 <code>{source}</code>，仅展示其实际字段与计数；状态标签不外推为全书完成。</p>'
            + (f'<div class="verify-stats">{"".join(rows)}</div>' if rows else '<p class="muted">此文件没有可摘要的状态或计数。</p>')
            + (f'<ul class="limits">{limitation_html}</ul>' if limitation_html else '')
            + '<p class="caveat">代码检查、结构覆盖与浏览器抽查均不等于全书数学审定。题答完整性、来源问题与未完成节点，应以各自核验记录为准。</p>')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, default=DEFAULT_AUDIT, help='textbook-visual-selection.json')
    parser.add_argument('--catalog', type=Path, default=DEFAULT_CATALOG, help='batch section catalog')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT, help='gallery HTML output path')
    parser.add_argument('--verification', type=Path, help='optional verification-result JSON to summarize')
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text(encoding='utf-8'))
    catalog = json.loads(args.catalog.read_text(encoding='utf-8'))
    verification = load_verification(args.verification)
    if audit.get('schema') != 'textbook-visual-selection/v1':
        raise ValueError('unexpected visualization audit schema')

    selections = {item['sectionId']: item for item in audit['selection']}
    assets = audit['assets']
    existing = audit.get('existing', [])
    section_assets: dict[str, list[tuple[dict, dict, bool]]] = {}
    for asset in assets:
        for placement in asset['placements']:
            section_assets.setdefault(placement['sectionId'], []).append((asset, placement, False))
    for asset in existing:
        for placement in asset['placements']:
            section_assets.setdefault(placement['sectionId'], []).append((asset, placement, True))

    section_total = sum(len(chapter['sections']) for book in catalog['books'] for chapter in book['chapters'])
    if len(selections) != section_total or set(selections) != {
        section['id'] for book in catalog['books'] for chapter in book['chapters'] for section in chapter['sections']
    }:
        raise ValueError('audit selections do not cover the catalog exactly')
    if any(not section_assets.get(section_id) for section_id, result in selections.items() if result['status'] == 'selected'):
        raise ValueError('selected section has no visualization placement')
    skip_total = sum(item['status'] == 'skip' for item in selections.values())
    selected_sections = sum(item['status'] == 'selected' for item in selections.values())
    visible_sections = sum(bool(section_assets.get(section_id)) for section_id in selections)
    unique_placements = sum(len(items) for items in section_assets.values())
    mixed_visible_blocks = sum(
        bool(placement.get('retainProse'))
        for items in section_assets.values() for _, placement, _ in items
    )
    inserted_assets = len(assets) + len(existing)

    groups = []
    missing_previews = []
    missing_pages = []
    for book in catalog['books']:
        book_id = book['id']
        chapter_groups = []
        for chapter in book['chapters']:
            cards = []
            skipped = []
            for section in chapter['sections']:
                section_id = section['id']
                result = selections[section_id]
                node_title = f"{section['section']}　{section.get('display_title', section['title'])}"
                if result['status'] == 'skip':
                    skipped.append(f'<li><strong>{esc(node_title)}</strong><span>{esc(result["reason"])}</span></li>')
                    continue
                if result['status'] == 'existing' and not section_assets.get(section_id):
                    skipped.append(f'<li><strong>{esc(node_title)}</strong><span>标记为已有资源，但目录未提供可展示的placement。{esc(result["reason"])}</span></li>')
                    continue
                entries = []
                for asset, placement, is_existing in section_assets.get(section_id, []):
                    if is_existing:
                        asset_id = asset['assetId']
                        title = {'ellipse-lab': '椭圆 · 定义实验', 'hyperbola-lab': '双曲线 · 定义实验', 'parabola-lab': '抛物线 · 定义实验'}.get(asset_id, asset_id)
                        summary = asset['summary']
                        formula = asset.get('formula', '')
                        preview_name = f'conic-{asset_id.removesuffix("-lab").replace("-", "")}-preview.svg'
                        # Existing conic preview names use the kind, with the natural word retained.
                        preview_name = f'conic-{asset_id.removesuffix("-lab")}-preview.svg'
                        preview = args.output.parent / book_id / '_shared' / 'visual-assets' / preview_name
                        goal = '复用已有圆锥曲线定义实验；不另造重复模型。'
                    else:
                        asset_id, title, summary = asset['id'], asset['title'], asset['summary']
                        formula = ''
                        goal = asset.get('goal', '')
                        preview = args.output.parent / book_id / '_shared' / 'visual-assets' / asset.get('preview', '')
                    if not preview.is_file():
                        missing_previews.append(f'{book_id}/{section_id}: {preview_name if is_existing else asset.get("preview", "")}')
                        preview_html = '<div class="preview-missing">缩略图待统一重建</div>'
                    else:
                        preview_html = f'<img class="preview" loading="lazy" src="{local_href(args.output, preview)}" alt="{esc(title)}动态图静态缩略图">'
                    teacher = args.output.parent / book_id / section_id / 'teacher.html'
                    student = args.output.parent / book_id / section_id / 'student.html'
                    for page in (teacher, student):
                        if not page.is_file():
                            missing_pages.append(str(page.relative_to(args.output.parent)))
                    teacher_link = local_href(args.output, teacher)
                    student_link = local_href(args.output, student)
                    goal_html = f'<p class="why"><b>动态图的价值</b>{esc(goal)}</p>' if goal else ''
                    formula_html = f'<div class="formula">{formula}</div>' if formula else ''
                    rationale = f'<p class="placement">教材位置：{esc(placement["afterBlockId"])}。{esc(placement.get("rationale", ""))}</p>'
                    entries.append(f'''<article class="asset-card {'existing' if is_existing else ''}">
                      {preview_html}<div class="asset-content"><div class="asset-title"><h4>{esc(title)}</h4><span class="badge">{'已有资源' if is_existing else '新模块'}</span></div>
                      {goal_html}<p class="summary">{esc(summary)}</p>{formula_html}{rationale}
                      <div class="entry-links"><a href="{teacher_link}">教师版</a><a href="{student_link}">学生版</a></div></div></article>''')
                cards.append(f'''<section class="node"><div class="node-head"><h3>{esc(node_title)}</h3><span class="status">{'已有资产' if result['status'] == 'existing' else '已接入'}</span></div>{''.join(entries)}</section>''')
            skip_html = (f'<details class="skipped"><summary>查看本章跳过的 {len(skipped)} 个节点及理由</summary><ul>{"".join(skipped)}</ul></details>' if skipped else '')
            chapter_groups.append(f'<section class="chapter"><h2>{esc(chapter["title"])}</h2><div class="nodes">{"".join(cards)}</div>{skip_html}</section>')
        groups.append(f'<section class="book" id="{esc(book_id)}"><header class="book-head"><span>{esc(BOOK_NAMES.get(book_id, book_id))}</span><h1>{esc(book["title"])}</h1></header>{"".join(chapter_groups)}</section>')

    verification = verification_html(verification, args.verification)
    generated_missing = ''
    if missing_previews or missing_pages:
        warnings = []
        if missing_previews:
            warnings.append(f'<li>{len(missing_previews)} 个缩略图尚未生成；卡片保留资源标题与解释。</li>')
        if missing_pages:
            warnings.append(f'<li>{len(set(missing_pages))} 个教师或学生入口文件当前不存在。</li>')
        generated_missing = f'<p class="build-warning">本地构建状态：{"".join(warnings)}</p>'

    html_doc = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>沪教版教材 · 可视化索引</title><style>
:root{{--paper:#f5f3e9;--card:#fffef9;--ink:#283c31;--muted:#697769;--line:#d6ddcf;--green:#41664c;--mint:#e8efe5;--sand:#eee9d9;--amber:#96733a}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;color:var(--ink);background:linear-gradient(180deg,#ecefe5 0,var(--paper) 270px);font:15px/1.65 "PingFang SC","Microsoft YaHei",sans-serif}}
.wrap{{max-width:1420px;margin:auto;padding:30px clamp(15px,3vw,42px) 70px}}.hero{{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:end;gap:24px;border-bottom:1px solid #c9d1c3;padding:12px 0 22px}}
.eyebrow{{font-size:11px;letter-spacing:.13em;color:var(--green);font-weight:700}}h1,h2,h3,h4,p{{margin-top:0}}.hero h1{{font:500 clamp(30px,4vw,49px)/1.2 "Songti SC","STSong",serif;margin:7px 0}}.hero p{{color:var(--muted);max-width:760px;margin:0}}.counts{{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px}}.count{{padding:6px 11px;border:1px solid var(--line);border-radius:99px;background:#ffffff91;font-size:12px;white-space:nowrap}}.count b{{color:var(--green);font-size:15px}}
.book-nav{{display:flex;gap:8px;flex-wrap:wrap;padding:17px 0}}.book-nav a,.entry-links a{{color:var(--green);text-decoration:none;border:1px solid #bdcbb9;background:#fbfcf6;padding:6px 11px;border-radius:4px;font-size:12px}}.book-nav a:hover,.entry-links a:hover{{background:var(--mint)}}.principle,.verify{{background:var(--card);border:1px solid var(--line);padding:14px 17px;margin:10px 0 22px;border-radius:5px}}.principle strong{{color:var(--green)}}.principle p,.verify p:last-child{{margin-bottom:0}}.verify h2{{font:500 21px "Songti SC","STSong",serif;margin-bottom:4px}}.verify-stats{{display:flex;gap:8px;flex-wrap:wrap;margin:11px 0}}.verify-stat{{display:grid;padding:7px 12px;background:#f2f4eb;border:1px solid #e0e5da;border-radius:3px;font-size:11px;color:var(--muted)}}.verify-stat strong{{font-size:15px;color:var(--ink)}}.caveat,.build-warning{{background:#f5eedf;border-left:3px solid var(--amber);padding:9px 12px;color:#594a30}}.limits{{font-size:12px;color:var(--muted)}}
.book{{padding-top:16px;scroll-margin-top:12px}}.book-head{{display:flex;align-items:baseline;gap:13px;border-bottom:2px solid var(--green);padding:12px 0 8px;margin:20px 0 14px}}.book-head span{{color:var(--green);font-size:11px;font-weight:700;letter-spacing:.1em}}.book-head h1{{font:500 27px "Songti SC","STSong",serif;margin:0}}.chapter{{margin:0 0 25px}}.chapter>h2{{font:500 21px "Songti SC","STSong",serif;margin:16px 0 11px;color:#3c5842}}
.nodes{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr));gap:12px;align-items:start}}.node{{background:var(--card);border:1px solid var(--line);border-radius:5px;overflow:hidden;box-shadow:0 2px 8px #34492b08}}.node-head{{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:9px 12px;background:#f0f2e9;border-bottom:1px solid var(--line)}}.node-head h3{{font-size:14px;margin:0;font-weight:600}}.status,.badge{{font-size:10px;color:#536d52;background:#e5ede1;padding:2px 7px;border-radius:99px;white-space:nowrap}}.asset-card{{display:grid;grid-template-columns:minmax(105px,31%) minmax(0,1fr);gap:11px;padding:11px;border-bottom:1px solid #e6e9df}}.asset-card:last-child{{border-bottom:0}}.preview{{width:100%;aspect-ratio:3/2;object-fit:contain;background:#f2f1e8;border:1px solid #e3e4da;border-radius:3px}}.preview-missing{{aspect-ratio:3/2;display:grid;place-items:center;background:#f2f1e8;color:var(--muted);font-size:11px}}.asset-content{{min-width:0}}.asset-title{{display:flex;justify-content:space-between;align-items:flex-start;gap:7px}}.asset-title h4{{font:600 15px/1.45 "Songti SC","STSong",serif;margin:0 0 5px}}.why,.summary,.placement{{font-size:11px;line-height:1.55;margin:5px 0;color:#58685b}}.why b{{color:var(--green);margin-right:4px}}.summary{{color:var(--ink)}}.placement{{color:#788276;font-size:10px}}.formula{{display:flex;flex-wrap:wrap;gap:4px 9px;color:#345744;font-size:14px;overflow-x:auto}}.formula math{{display:inline-block;white-space:nowrap}}.entry-links{{display:flex;gap:6px;margin-top:7px}}.entry-links a{{padding:4px 9px}}
.skipped{{margin:13px 0;background:#f2f0e7;border:1px solid #e2dfd2;border-radius:4px;font-size:12px}}.skipped summary{{padding:8px 11px;cursor:pointer;color:#62705f}}.skipped ul{{margin:0;padding:0 17px 9px 32px;list-style:disc}}.skipped li{{padding:4px 0;border-top:1px solid #e7e4da}}.skipped li strong{{display:block;font-size:11px;color:var(--ink)}}.skipped li span{{color:var(--muted);font-size:11px}}.muted{{color:var(--muted)}}footer{{border-top:1px solid var(--line);padding-top:13px;margin-top:32px;color:var(--muted);font-size:11px}}
@media(max-width:650px){{.wrap{{padding-top:18px}}.hero{{grid-template-columns:1fr;align-items:start;gap:13px}}.counts{{justify-content:flex-start}}.book-head{{align-items:flex-start;flex-direction:column;gap:2px}}.nodes{{grid-template-columns:1fr}}.asset-card{{grid-template-columns:102px minmax(0,1fr);gap:9px;padding:9px}}.asset-title h4{{font-size:14px}}.preview{{aspect-ratio:1/1}}}}
@media print{{body{{background:white}}.wrap{{max-width:none;padding:0 8mm}}.book-nav{{display:none}}.chapter,.node,.asset-card{{break-inside:avoid}}.nodes{{grid-template-columns:repeat(2,minmax(0,1fr))}}.skipped:not([open]){{display:none}}a{{color:inherit}}}}
</style></head><body><main class="wrap"><header class="hero"><div><div class="eyebrow">SHANGHAI MATHEMATICS · INTERACTIVE INDEX</div><h1>把静止教材，变成可观察的数学</h1><p>五册教材的高价值动态图索引。只选动态画面确实能替代冗长解释、呈现变化或边界的内容；简单定义与公式保留清晰静态表达。</p></div><div class="counts"><span class="count"><b>{section_total}</b> 阅读节点</span><span class="count"><b>{inserted_assets}</b> 模块</span><span class="count"><b>{unique_placements}</b> 落点</span><span class="count"><b>{visible_sections}</b> 接入阅读节点（含复用）</span><span class="count"><b>{skip_total}</b> 有理由跳过</span></div></header>
<nav class="book-nav" aria-label="按册跳转">{''.join(f'<a href="#{esc(book["id"])}">{esc(BOOK_NAMES.get(book["id"], book["id"]))}</a>' for book in sorted(catalog['books'], key=lambda item: ('bx1', 'bx2', 'bx3', 'x1', 'x2').index(item['id'])))}</nav>
<section class="principle"><strong>阅读方式</strong><p>动态图旁保留必要条件与结论；被替代的教材解释仍可展开，打印时恢复原文。另有 <b>{mixed_visible_blocks}</b> 个混合内容段落含题设、数据或其他未被可视化的解释链，保持正文常显；旧圆锥曲线模块另有常显标准方程卡。教师版、学生版均从本地教材页面进入，学生资源与教师推导分开提供。</p></section>
<section class="verify"><h2>验证记录与边界</h2>{verification}{generated_missing}</section>{''.join(groups)}
<footer>本索引根据可视化选择清单与教材章节目录生成。页面与缩略图使用本地相对链接；资源未生成时显示待重建提示。可视化交互用于解释数学关系，不替代完整证明、题答校核或全书内容审定。</footer></main></body></html>'''
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_doc, encoding='utf-8')
    print(json.dumps({'output': str(args.output), 'nodes': section_total, 'newModules': len(assets),
                      'existingConicModules': len(existing), 'placements': unique_placements,
                      'visualizedSections': visible_sections, 'newModuleSections': selected_sections,
                      'mixedVisibleBlocks': mixed_visible_blocks, 'skippedSections': skip_total,
                      'missingPreviews': len(missing_previews), 'missingPages': len(set(missing_pages))}, ensure_ascii=False))


if __name__ == '__main__':
    main()
