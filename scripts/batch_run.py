#!/usr/bin/env python3
"""Run resumable section jobs without retaining book content in an AI context."""

from project_paths import use_project_root, launch_browser
use_project_root()
from pathlib import Path
import argparse
import datetime
import hashlib
import html
import json
import re
import time
import traceback
from site_access import install_project_pages

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / 'batch'
OUTPUT = ROOT / 'outputs/五册教材教参整合'
CATALOG = BATCH / 'manifests/catalog.json'
STATE = BATCH / 'state/sections'
PRIORITY = ['x1', 'bx1', 'bx2', 'bx3', 'x2']


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def jobs(catalog, book_ids=None):
    books = sorted(catalog['books'], key=lambda b: PRIORITY.index(b['id']))
    for book in books:
        if book_ids and book['id'] not in book_ids:
            continue
        for chapter in book['chapters']:
            for section in chapter['sections']:
                yield book, chapter, section


def fingerprint(path):
    digest = hashlib.sha256(path.read_bytes())
    for name in ['batch_render.py', 'batch_validate.py', 'book.css', 'book.js', 'build_sample.py',
                 'site_access.py', 'site-access.css', 'site-access.js', 'example_guidance.py']:
        dependency = ROOT / 'scripts' / name
        if dependency.is_file():
            digest.update(name.encode())
            digest.update(dependency.read_bytes())
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('book_id') in PRIORITY:
        for dependency in [ROOT / 'scripts/visual-book.css', ROOT / 'scripts/visual-book.js',
                           *sorted((ROOT / 'scripts/visual-assets').glob('*'))]:
            if dependency.is_file():
                digest.update(dependency.relative_to(ROOT).as_posix().encode())
                digest.update(dependency.read_bytes())
    for raw in sorted(data.get('source_hashes', {})):
        original = Path(raw)
        digest.update(raw.encode())
        digest.update(original.read_bytes() if original.is_file() else b'MISSING')
    images = {m for b in data['blocks'] for f in ['markdown', 'answer', 'teacher_analysis']
              for m in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', b.get(f, ''))}
    for raw in sorted(images):
        original = Path(raw)
        digest.update(raw.encode())
        digest.update(original.read_bytes() if original.is_file() else b'MISSING')
    return digest.hexdigest()


def review_state(section_id, model_path=None):
    repairs = BATCH / 'reviews/repair-final-receipts.json'
    if repairs.is_file() and model_path:
        receipt = json.loads(repairs.read_text(encoding='utf-8')).get('sections', {}).get(section_id)
        if receipt and receipt['model_sha256'] == hashlib.sha256(Path(model_path).read_bytes()).hexdigest():
            return {'file': receipt['report'], 'status': 'repair-reviewed',
                    'limits': ['Targeted repair review, not a fresh mathematical review of every question.']}
    candidates = [BATCH / 'reviews' / f'{section_id}.json', *sorted((BATCH / 'reviews').glob(f'*/{section_id}.json'))]
    if section_id.startswith('x2-5-') or section_id == 'x2-chapter-end-5':
        candidates.append(BATCH / 'reviews/x2-ch5-numbering.json')
    for path in candidates:
        if path.is_file():
            data = json.loads(path.read_text(encoding='utf-8'))
            stale = False
            if model_path and path.name == 'x2-ch5-numbering.json':
                patch = json.loads((BATCH / 'patches/x2-ch5-numbering-proposed.json').read_text(encoding='utf-8'))
                model = json.loads(Path(model_path).read_text(encoding='utf-8'))
                stale = (patch.get('status') != 'approved-independent-review' or
                         patch.get('source_hashes') != model.get('source_hashes'))
            elif model_path and data.get('model_sha256'):
                model = json.loads(Path(model_path).read_text(encoding='utf-8'))
                # Linking review metadata back into the model is not a content edit.
                model.pop('independent_review', None)
                current_review_hash = hashlib.sha256((json.dumps(model, ensure_ascii=False, indent=2) + '\n').encode()).hexdigest()
                stale = data['model_sha256'] != current_review_hash
            return {'file': str(path.relative_to(ROOT)), 'status': 'stale' if stale else data.get('status', 'unclassified'),
                    'limits': data.get('limits', [])}
    return {'status': 'pending'}


def write_portal(catalog):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    css = '''*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top right,#e5eadb,transparent 60%),#f6f3eb;color:#203a2b;font:17px/1.8 "Songti SC",serif}main{max-width:1080px;margin:auto;padding:40px 28px}h1{font-size:38px;margin:5px 0 12px}h2{border-top:2px solid #304f39;padding-top:18px;margin-top:32px}h3{font-size:19px;margin:20px 0 8px}a{color:#295c43;text-underline-offset:4px}small,.muted{color:#697667;font-size:13px}.row{display:flex;gap:15px;align-items:baseline;padding:9px 0;border-bottom:1px solid #d7ddcf;flex-wrap:wrap}.title{flex:1;min-width:230px}.status{font:12px/1.6 "PingFang SC",sans-serif;padding:2px 8px;background:#e5eadc}.warning{color:#975322;background:#eee2d4}.books{display:flex;gap:18px;flex-wrap:wrap;font-size:14px}.notice{padding:12px 17px;border-left:3px solid #a5683f;background:#ede8dd;font-size:14px}.metrics{font-family:"PingFang SC",sans-serif;font-size:13px}button{font:inherit}@media(max-width:600px){main{padding:24px 18px}h1{font-size:29px}.row{gap:8px}.title{min-width:100%;font-size:16px}}'''
    totals = {'sections': 0, 'validated': 0, 'blocked': 0, 'queued': 0, 'questions': 0}
    index_rows, book_summaries, pending_rows = [], [], []
    for book in sorted(catalog['books'], key=lambda b: PRIORITY.index(b['id'])):
        directory = OUTPUT / book['id']
        directory.mkdir(exist_ok=True)
        chapter_rows, stats = [], {'sections': 0, 'validated': 0, 'blocked': 0, 'queued': 0, 'questions': 0}
        for chapter in book['chapters']:
            rows = []
            for section in chapter['sections']:
                section_id = section['id']
                node = directory / section_id
                state_file = STATE / f'{section_id}.json'
                state = json.loads(state_file.read_text(encoding='utf-8')) if state_file.is_file() else {}
                validation_file = node / 'validation.json'
                validation = json.loads(validation_file.read_text(encoding='utf-8')) if validation_file.is_file() else {}
                build_file = node / 'metadata.json'
                build = json.loads(build_file.read_text(encoding='utf-8')) if build_file.is_file() else {}
                rendered_file = node / 'build.json'
                rendered_build = json.loads(rendered_file.read_text(encoding='utf-8')) if rendered_file.is_file() else {}
                current_validation = bool(rendered_build.get('fingerprint')) and validation.get('build_fingerprint') == rendered_build['fingerprint']
                passed = validation.get('status') == 'passed' and state.get('status') == 'validated' and current_validation
                blocked = state.get('status') == 'blocked'
                for target in [stats, totals]:
                    target['sections'] += 1
                    target['validated' if passed else 'blocked' if blocked else 'queued'] += 1
                    target['questions'] += section.get('question_count', build.get('counts', {}).get('questions', build.get('questions', 0)))
                label = '显示/打印通过' if passed else '需修复' if blocked else '待构建/检查'
                status_class = 'status' if passed else 'status warning'
                links = ''
                if (node / 'teacher.html').is_file():
                    links += f'<a href="{html.escape(section_id)}/teacher.html">教师阅读</a> <a href="{html.escape(section_id)}/student.html">学生预览</a> <a href="{html.escape(section_id)}/student.zip">学生包</a>'
                title = html.escape(section.get('display_title', section.get('title', section.get('section', section_id))))
                review = review_state(section_id, ROOT / section['path'])
                if not passed:
                    reasons = [x.get('code', x.get('message', '来源问题')) for x in section.get('issues', [])]
                    reasons += [x.get('name', '验证异常') for x in validation.get('errors', [])]
                    pending_rows.append(f'| {section_id} | {label} | {"、".join(dict.fromkeys(reasons)) or "尚未取得当前版本完整检查记录"} |')
                review_label = '修复项复核记录' if review['status'] == 'repair-reviewed' else '独立复核待完成' if review['status'] == 'pending' else '复核后模型有更新' if review['status'] == 'stale' else '独立复核记录'
                review_link = '' if review.get('status') in ('pending', 'stale') else f'<a href="../../../{html.escape(review["file"])}">{review_label}</a>'
                rows.append(f'<div class="row"><span class="title">{title}</span><span class="{status_class}">{label}</span>{links}{review_link or f"<small>{review_label}</small>"}</div>')
            chapter_rows.append(f'<section><h2>{html.escape(chapter["title"])}</h2>{"".join(rows)}</section>')
        title = html.escape(book['title'])
        document = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · 教材教参整合</title><style>{css}</style></head><body><main><small>沪教数学 / 教材 × 教参整合</small><h1>{title}</h1><p class="metrics">{stats['validated']} / {stats['sections']} 个节点显示与打印通过 · {stats['blocked']} 个需修复</p><p><a href="../index.html">← 五册总目录</a> · <a href="../visual-index.html">动态图总览</a> · <a href="../交付与核验说明.md">使用与核验说明</a></p><p class="notice">教师使用为主。只把各节的学生ZIP发给学生；教师页、整册目录及来源含答案。显示与打印通过不等于所有题目已重新计算，独立审校范围见交付说明和审校记录。</p>{''.join(chapter_rows)}</main></body></html>'''
        (directory / 'index.html').write_text(document, encoding='utf-8')
        index_rows.append(f'<div class="row"><a class="title" href="{book["id"]}/index.html">{title}</a><span class="status">{stats["validated"]}/{stats["sections"]} 节点通过</span><small>{stats["blocked"]} 需修复</small></div>')
        book_summaries.append({'id': book['id'], 'title': book['title'], **stats})
    now = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    index = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>沪教数学 · 五册教材教参整合</title><style>{css}</style></head><body><main><small>LOCAL EDITION · SOURCE-TRACEABLE</small><h1>教材与教参，一起读。</h1><p>保留教材主线、原题和原图，在需要的位置补入教师视角。</p><p class="notice"><a href="deep-index.html">新：7个深度探究 →</a> · <a href="visual-index.html">打开五册可视化总览 →</a> · 逐节筛选，只用动态图解释真正需要观察变化的内容；可查看每个插入位置与跳过理由。可视化专项验证与原题审校分开记录。</p><p class="notice">优先推进选择性必修第一册。其余为必修第一、二、三册及选择性必修第二册；两册数学建模活动册不在本批五册范围。每节可隐藏答案并按模块打印，学生分享使用独立ZIP。</p>{''.join(index_rows)}<p><a href="章节修复记录-20261020.md">查看章节修复记录与验收边界 →</a></p><h2>当前显示与打印核验</h2><p class="metrics">{totals['validated']}/{totals['sections']} 节点显示/打印通过；{totals['blocked']} 个需修复，{totals['queued']} 个待检查。</p><p><a href="交付与核验说明.md">使用说明 / 检查范围 / 未通过节点</a></p><p class="muted">这里的计数来自当前章节检查；显示与打印通过不等于全书逐题数学审定。已知章节修复与独立复核范围见修复记录，可视化专项检查见总览。最后更新 {now}。</p></main></body></html>'''
    (OUTPUT / 'index.html').write_text(index, encoding='utf-8')
    summary = {'updated_at': now, 'books': book_summaries, 'totals': totals}
    atomic_json(BATCH / 'state/progress.json', summary)
    table = '\n'.join(f'| {b["title"]} | {b["sections"]} | {b["questions"]} | {b["validated"]} | {b["blocked"]} | {b["queued"]} |' for b in book_summaries)
    notes = f'''# 五册教材教参网页版：交付与核验

更新：{now}。以下基础内容与题块分页计数为原有批次记录；当前可视化专项检查请查看 [五册可视化总览](visual-index.html)。不是正式出版数学审定。

## 从哪里打开

- [五册总目录](index.html)；优先册为[选择性必修第一册](x1/index.html)。直接打开，不必启动服务或联网。
- 教师页默认紧凑阅读，支持全部答案、教师批注分别隐藏；公式与重要概念以编辑标注框呈现。
- 按“按内容打印”选择正文、仅试题、试题＋答案或完整内容，再选例题／练习／习题分类、范围和是否附教师批注。先预览再打印。
- 学生分享只发送各节点的 `student.zip`，解压打开 `student.html`。不要把教师页、整册文件夹、content.json 或来源目录发给学生；隐藏答案按钮不是保密机制。
- 本批不接入题篮，也不修改另一个正在施工的项目，避免版本相互影响。

## 当前数量

| 册次 | 节与章末节点 | 题块 | 显示/打印通过 | 需修复 | 待检查 |
| --- | ---: | ---: | ---: | ---: | ---: |
{table}

“题块”按独立例题、练习或习题计数，不把每个小问另算一题。两册数学建模活动册不在这五册范围。

## 检查到底证明了什么

1. 来源结构：源文件哈希、题目ID、题答来源行号、图片可达与复制哈希、教材正文保留。明确错号/错序的修复另有记录；缺答与歧义不猜填。
2. 网页与分享：本地离线 Chrome 真实加载、公式渲染数量及错误、图片、手机视口、学生物理隔离、ZIP CRC 和独立解包运行。
3. 打印：共用打印组件的组合回归只测一次；逐节另做“仅试题”和“试题＋答案”两种 A4/100% PDF检查。诊断标记须与正常PDF页数和文字坐标一致，才能用于题块跨页判断。
4. 数学：独立复核范围写在项目 `batch/reviews/`。结构或显示通过不代表每道题已重算，也不代表原教参必然正确。原文冲突与不完整句子不擅自补造。

## 关于一道题不跨页

能放入一页打印区的题块，检查其起止标记是否同页。题干和长解析合计超过一页时，不能同时保证不跨页、字号可读和不删内容；此时保留全文，记录“长题续页”警告。第三方打印机缩放、浏览器页眉页脚和其他浏览器不在自动检查范围。

## 尚未通过的节点

| 节点 | 状态 | 原因（详细位置见该节 validation.json / 中间底稿 issues） |
| --- | --- | --- |
{chr(10).join(pending_rows) if pending_rows else '| 无 | 当前构建全部显示/打印通过 | 不等于全书数学审定 |'}

## 后续迭代

项目根目录 `batch/manifests/catalog.json` 管册次、章节和节点；`batch/sections/` 是可复核中间底稿；`batch/state/` 保存构建与来源保留检查；`batch/reviews/` 保存独立复核。修改只影响对应节点；源资料和已认可8.1/8.2样章保持只读。

批量脚本与恢复命令见项目 `batch/README.md`。不依赖聊天中保留全书上下文，不创建后台计划任务。
'''
    (OUTPUT / '交付与核验说明.md').write_text(notes, encoding='utf-8')
    install_project_pages()
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--book', action='append', choices=PRIORITY)
    parser.add_argument('--section')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--portal-only', action='store_true')
    parser.add_argument('--adopt-existing', action='store_true', help='Verify and import independently completed batch checks without reprinting')
    args = parser.parse_args()
    if not CATALOG.is_file():
        parser.error('Missing catalog; run scripts/batch_extract.py first')
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    if args.portal_only:
        print(json.dumps(write_portal(catalog), ensure_ascii=False))
        return
    STATE.mkdir(parents=True, exist_ok=True)
    if args.adopt_existing:
        from batch_render import fingerprint as render_fingerprint, sha
        from batch_validate import VERSION as validation_version
        for book, chapter, section in jobs(catalog, args.book):
            if args.section and section['id'] != args.section:
                continue
            source = ROOT / section['path']
            node = OUTPUT / book['id'] / section['id']
            if not (node / 'build.json').is_file() or not (node / 'validation.json').is_file():
                continue
            build = json.loads((node / 'build.json').read_text(encoding='utf-8'))
            validation = json.loads((node / 'validation.json').read_text(encoding='utf-8'))
            current = render_fingerprint(source, json.loads(source.read_text(encoding='utf-8')))
            expected = hashlib.sha256((validation_version + sha(ROOT / 'scripts/batch_validate.py') + current).encode()).hexdigest()
            hashes = build.get('artifact_hashes', {})
            intact = bool(hashes) and all((node / f).is_file() and sha(node / f) == value for f, value in hashes.items())
            status = 'validated' if intact and validation.get('status') == 'passed' and validation.get('fingerprint') == expected and build.get('fingerprint') == current else 'blocked' if validation.get('status') == 'failed' and validation.get('fingerprint') == expected else 'stale'
            atomic_json(STATE / f'{section["id"]}.json', {
                'id': section['id'], 'book_id': book['id'], 'fingerprint': fingerprint(source),
                'status': status, 'imported_existing': True, 'artifacts_intact': intact,
                'review': review_state(section['id'], source), 'validation_fingerprint': validation.get('fingerprint')})
        print(json.dumps(write_portal(catalog), ensure_ascii=False))
        return
    executed, skipped, blocked = 0, 0, 0
    from batch_validate import validate_section
    from playwright.sync_api import sync_playwright
    playwright = sync_playwright().start()
    browser = launch_browser(playwright, headless=True)
    for book, chapter, section in jobs(catalog, args.book):
        if args.section and section['id'] != args.section:
            continue
        if args.limit is not None and executed >= args.limit:
            break
        source = ROOT / section['path']
        state_path = STATE / f'{section["id"]}.json'
        key = fingerprint(source)
        state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.is_file() else {}
        node = OUTPUT / book['id'] / section['id']
        if not args.force and state.get('status') == 'validated' and state.get('fingerprint') == key and all((node / f).is_file() for f in ['teacher.html', 'student.html', 'student.zip', 'validation.json']):
            skipped += 1
            continue
        state = {'id': section['id'], 'book_id': book['id'], 'section_path': section['path'],
                 'fingerprint': key, 'status': 'running', 'review': review_state(section['id']), 'stages': []}
        atomic_json(state_path, state)
        start = time.monotonic()
        try:
            validation = validate_section(source, browser, args.force)
            state['status'] = 'validated' if validation.get('status') == 'passed' else 'blocked'
            state['stages'].append({'script': 'batch_validate.py', 'status': validation.get('status'),
                                    'counts': validation.get('counts'), 'cached': validation.get('cached', False)})
        except Exception:
            state['status'] = 'blocked'
            state['stages'].append({'script': 'batch_validate.py', 'error': traceback.format_exc()[-6000:]})
        state['elapsed_seconds'] = round(time.monotonic() - start, 2)
        state['finished_at'] = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
        atomic_json(state_path, state)
        executed += 1
        blocked += state['status'] == 'blocked'
        print(json.dumps({'id': state['id'], 'status': state['status'], 'seconds': state['elapsed_seconds']}, ensure_ascii=False), flush=True)
        write_portal(catalog)
    browser.close()
    playwright.stop()
    summary = write_portal(catalog)
    print(json.dumps({'executed': executed, 'skipped': skipped, 'blocked_this_run': blocked,
                      'totals': summary['totals']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
