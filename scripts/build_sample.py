#!/usr/bin/env python3
"""Build a source-traceable teacher web chapter and a physically isolated student copy."""

from project_paths import use_project_root, launch_browser
use_project_root()
from pathlib import Path
from collections import defaultdict
import hashlib
import html
import json
import re
import shutil
import zipfile

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'designs/2026-10-19-沪教版教材教参整合样章'
AUDIT = Path('sources/paired/第8章平面向量教材教参配对-20261009')
MANIFEST = json.loads((AUDIT / '配对清单.json').read_text(encoding='utf-8'))
BOOK = Path(next(p for p in MANIFEST['source_hashes'] if '第8章平面向量-dollar' in p))
TEACHER = Path(next(p for p in MANIFEST['source_hashes'] if '分章' in p))
SOURCES = {'book': BOOK, 'teacher': TEACHER}
LINES = {k: p.read_text(encoding='utf-8').splitlines() for k, p in SOURCES.items()}
MD = MarkdownIt('commonmark', {'html': False}).enable('table')
BLOCKS = []
ASSETS = {}
EDITS = []


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def span(source, a, b):
    return '\n'.join(LINES[source][a - 1:b]).strip()


def edit(text, before, after, reason):
    if before in text:
        EDITS.append({'before': before, 'after': after, 'reason': reason})
        return text.replace(before, after)
    return text


def normalize(text, source):
    text = re.sub(r'^\s*(Q|\?)\s*$', '', text, flags=re.M)
    text = re.sub(r'^---\s*$', '', text, flags=re.M)
    text = edit(text, '$\\overrightarrow{a} + \\overrightarrow{b}$ + 己',
                '$\\overrightarrow{a} + \\overrightarrow{b} + \\overrightarrow{c}$', '连加末项的OCR符号恢复')
    text = edit(text, '和 4.5v，', '和 $4.5\\overrightarrow{v}$，', '速度向量记号恢复')
    text = edit(text, '$\\angle {ADB}$ 是菱形', '四边形 ${CADB}$ 是菱形', '由所作平行四边形及等边条件校正对象类型')
    # The source OCR joins point names into arrows; the exercise is about points, not these vectors.
    text = edit(text, '$A\\text{ 、 }B\\text{ 、 }\\overrightarrow{C}\\text{ 、 }\\overrightarrow{D}\\text{ 、 }E$',
                '$A\\text{ 、 }B\\text{ 、 }C\\text{ 、 }D\\text{ 、 }E$', '将点名C、D与向量箭头分离')
    text = edit(text, '$A\\text{ 、 }B\\text{ 、 }\\overrightarrow{C\\text{ 、 }D}\\text{ 、 }E$',
                '$A\\text{ 、 }B\\text{ 、 }C\\text{ 、 }D\\text{ 、 }E$', '将点名C、D与向量箭头分离')

    def image(m):
        original = (SOURCES[source].parent / m[2]).resolve()
        assert original.is_file(), original
        ref = 'images/' + source + '-' + original.name
        target = OUT / ref
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)
        ASSETS[ref] = {'source': str(original), 'sha256': digest(original)}
        return '![](' + ref + ')'
    return re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', image, text)


def block(kind, title='', text='', source=None, ranges=None, **kwargs):
    provenance = []
    if source:
        text = '\n\n'.join(span(source, a, b) for a, b in ranges)
        provenance = [{'source': source, 'start': a, 'end': b} for a, b in ranges]
        text = normalize(text, source)
    item = {'type': kind, 'title': title, 'markdown': text, 'provenance': provenance, **kwargs}
    BLOCKS.append(item)
    return item


def records(key, kind):
    return [r for r in MANIFEST['records'] if r['key'] == key and r['kind'] == kind]


def record_text(key, kind, source):
    rs = records(key, kind)
    text = '\n\n'.join(r['original'] for r in rs)
    return normalize(text, source), [dict(source=source, start=r['start'], end=r['end']) for r in rs]


def example(n, section='8.1'):
    key = f'{section}·例{n}'
    q, qp = record_text(key, 'example_question', 'book')
    fig, fp = record_text(key, 'example_figure', 'book')
    sol, sp = record_text(key, 'example_solution', 'book')
    analysis, ap = record_text(key, 'example_analysis', 'teacher')
    if section == '8.1' and n in (1, 2):
        # Restore the exploratory prompt and concept statement to public textbook prose.
        line = 69 if n == 1 else 83
        sol = normalize(span('book', line, line), 'book')
        sp = [dict(source='book', start=line, end=line)]
    if section == '8.1' and n == 3:
        sol = normalize(span('book', 157, 173), 'book')
        sp = [dict(source='book', start=157, end=173)]
    if section == '8.1' and n == 4:
        analysis = '本例采用作用于同一点的两个力的合成模型。题干未显式写出“作用于同一点”，应结合原图与教材解答明确此前提；不将本节模型外推为关于一般力系的结论。'
    block('question', f'例题 {n:02}', text=q + '\n\n' + fig,
          id=f'bx2-c8-s{section.replace(".", "")}-ex{n}', provenance_question=qp + fp,
          answer=sol, answer_provenance=sp, teacher_analysis=analysis,
          analysis_provenance=ap, category='例题', edited_analysis=(section == '8.1' and n == 4))


def exercise_group(code, title, section='8.1'):
    block('heading', title, id=code)
    for p in MANIFEST['pairs']:
        if p['section'] != section or p['group'] != title:
            continue
        q, qp = record_text(p['heading'], 'question', 'book')
        f, fp = record_text(p['heading'], 'question_figure', 'book')
        a, ap = record_text(p['heading'], 'answer', 'teacher')
        # The old manifest already repositions figures; avoid duplicating any inline copy.
        q = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)\s*\n*(?:图 [^\n]+)?', '', q)
        block('question', f'{title} · {p["number"]}', text=q + '\n\n' + f,
              id=p['block_id'], provenance_question=qp + fp,
              answer=a, answer_provenance=ap, teacher_analysis='', category=title)


def emphasize(item, key, kind, title, start='', end=None):
    """Store editorial emphasis separately; preserve the source Markdown verbatim."""
    text = item['markdown']
    assert not start or text.count(start) == 1, (key, 'start anchor')
    a = text.index(start) if start else 0
    assert end is None or text[a:].count(end) == 1, (key, 'end anchor')
    b = text.index(end, a) if end else len(text)
    assert a < b, key
    spans = item.setdefault('emphases', [])
    assert all(b <= s['start'] or a >= s['end'] for s in spans), key
    spans.append({'id': key, 'kind': kind, 'title': title, 'start': a, 'end': b,
                  'origin': 'editorial-emphasis'})


def make_content():
    block('intro', '本节阅读主线', text='从“有大小与方向的量”出发，用有向线段建立几何表示，再把加法、减法和数乘组织成线性运算。教材正文构成阅读主线，教参的编写意图与教学边界在对应位置出现。', teacher_only=True)
    block('section', '向量的概念', id='concept', number='01', subtitle='从实际的量，到可以平移的数学对象')
    concept = block('prose', source='book', ranges=[(9, 62)])
    emphasize(concept, 'key-vector-equality', 'concept', '相等向量：比较模与方向',
              '如果两个向量同方向且具有相同的模', '![](images/book-bo_d4sllcbef24c73be0n80_2_1128')
    block('teacher', '教参视角 · 先抽象，再严密', source='teacher', ranges=[(102, 108)])
    block('editor', '讲解边界', text='这里的向量不记录起点的位置。比较两个向量，核对的是模与方向，而不是它们画在哪里。零向量“具有任意方向”是教材的约定，不应解释为零向量有一个确定的方向。', teacher_only=True)
    example(1)
    block('prose', source='book', ranges=[(73, 79)])
    example(2)
    block('prose', source='book', ranges=[(85, 85)])
    exercise_group('practice-1', '练习8.1（1）')
    block('editor', '看图枚举的口径', text='练习8.1（1）第3题的教参答案按图示箭头方向列举。若改成“由全部已标点构成的向量”，候选会增加，不能直接沿用原答案的枚举范围。', teacher_only=True)
    block('section', '向量的加法和减法', id='addition', number='02', subtitle='让不同方向的量进入同一套运算')
    addition = block('prose', source='book', ranges=[(113, 154)])
    emphasize(addition, 'key-addition-laws', 'formula', '加法交换律与结合律',
              '向量加法满足如下运算律', '由结合律,')
    block('teacher', '教参视角 · 同一法则，包含退化情形', source='teacher', ranges=[(110, 126)])
    example(3)
    tail = block('prose', source='book', ranges=[(175, 175)])
    emphasize(tail, 'key-head-tail', 'method', '首尾相接：把多段位移合成一段')
    example(4)
    subtraction = block('prose', source='book', ranges=[(191, 225)])
    emphasize(subtraction, 'key-subtraction', 'method', '转化思想：减法化为加法',
              '数的运算的经验使我们容易想到', '![](images/')
    example(5)
    exercise_group('practice-2', '练习8.1（2）')
    block('section', '实数与向量的乘法', id='multiplication', number='03', subtitle='用一个系数，统一表达伸缩与反向')
    multiplication = block('prose', source='book', ranges=[(247, 294)])
    emphasize(multiplication, 'key-scalar-product', 'formula', '数乘：模的变化与方向',
              '实数 $\\lambda$ 与向量', '暂不考虑有关量的单位')
    emphasize(multiplication, 'key-parallel-condition', 'condition', '平行的代数表示：基准向量必须非零',
              '\n\n向量 $\\overrightarrow{b}$ 与非零向量', '同学们可以验证')
    emphasize(multiplication, 'key-scalar-laws', 'formula', '数乘运算律',
              '设 $\\overrightarrow{a}\\text{ 、 }\\overrightarrow{b}$ 是向量', '与非零向量')
    emphasize(multiplication, 'key-unit-vector', 'condition', '单位化：先检查向量非零',
              '与非零向量 $\\overrightarrow{a}$ 同方向的单位向量', '向量的加法、减法以及')
    block('teacher', '教参视角 · 数乘与线性运算', source='teacher', ranges=[(128, 142)])
    block('editor', '备课时守住三个条件', text='平行向量的表示 $\\overrightarrow{b}=\\lambda\\overrightarrow{a}$ 以 $\\overrightarrow{a}\\ne\\overrightarrow{0}$ 为前提；单位化 $\\overrightarrow{a}/|\\overrightarrow{a}|$ 也只对非零向量使用。教参借相似三角形说明分配律，属于几何直观：不能把一幅非退化图直接当作所有实数系数及平行情形的完整证明。', teacher_only=True)
    for n in (6, 7, 8):
        example(n)
    exercise_group('practice-3', '练习8.1（3）')
    block('section', '课后习题', id='homework', number='04', subtitle='保留教材A、B组顺序，不另行分级或改编')
    exercise_group('homework-a', '习题8.1 A组')
    exercise_group('homework-b', '习题8.1 B组')
    block('section', '备课附记与来源', id='sources', number='05', subtitle='来源、编辑边界与尚待完成的复核', teacher_only=True)
    block('teacher', '教学建议与背景材料', source='teacher', ranges=[(156, 170)], teacher_only=True)
    block('editor', '物理模型的使用边界', text='教参原文中“不同作用点的力无法合成”等措辞过于绝对。本样章仅采用共点力的合成情境，不对一般力系作此断言；备课引用时应保留这个限定。上方原文作为来源材料保留，不作为本书新增的物理结论。', teacher_only=True)
    block('editor', '本轮编辑与保留边界', text='本页保留8个例题和29道练习、习题，补入旧配对稿尚未收入的教材概念与推导正文。原文中的“图略”“证明略”仍保留，未冒充补齐全部详解。符号与明确OCR勘误另列于编辑记录；原始快照保持不变。', teacher_only=True)


def render_md(text):
    math = []

    def protect(m):
        token = f'BOOKMATHPLACEHOLDER{len(math)}TOKEN'
        display = m[0].startswith('$$')
        tex = m[0][2:-2] if display else m[0][1:-1]
        tag = 'div' if display else 'span'
        math.append(f'<{tag} class="math{ " display" if display else ""}" data-tex="{html.escape(tex.strip(), quote=True)}" data-display="{str(display).lower()}"></{tag}>')
        return '\n\n' + token + '\n\n' if display else token

    protected = re.sub(r'\$\$[\s\S]*?\$\$|(?<!\$)\$(?!\$)[^$\n]+\$', protect, text)
    rendered = MD.render(protected)
    for i, markup in enumerate(math):
        token = f'BOOKMATHPLACEHOLDER{i}TOKEN'
        rendered = rendered.replace('<p>' + token + '</p>', markup).replace(token, markup)
    rendered = re.sub(r'<img src="([^"]+)" alt="[^\"]*"\s*/?>', r'<img src="\1" alt="教材或教参原图" loading="eager">', rendered)
    return rendered


def provenance(items):
    labels = []
    for p in items:
        label = '教材' if p['source'] == 'book' else '教参'
        file = 'textbook-ch8.md' if p['source'] == 'book' else 'teacher-ch8.md'
        labels.append(f'<a href="sources/{file}" target="_blank" rel="noopener">{label} L{p["start"]}–{p["end"]}</a>')
    return '<div class="provenance teacher-only">' + ' · '.join(labels) + '</div>' if labels else ''


def render_block(b, student=False):
    if student and (b.get('teacher_only') or b['type'] in ['intro', 'teacher', 'editor']):
        return ''
    kind = b['type']
    text = render_md(b['markdown'])
    if kind == 'section':
        private_class = ' teacher-only' if b.get('teacher_only') else ''
        return f'<section class="section-heading{private_class}" id="{b["id"]}"><span class="section-number">{b["number"]}</span><div><h2>{b["title"]}</h2><p>{b["subtitle"]}</p></div></section>'
    if kind == 'heading':
        return f'<h3 class="group-heading" id="{b["id"]}">{b["title"]}</h3>'
    if kind == 'question':
        answer = ''
        if not student:
            analysis = ''
            if b['teacher_analysis']:
                label = '编辑整合 · 情境限定' if b.get('edited_analysis') else '教参 · 例题分析'
                analysis = f'<aside class="question-analysis teacher-only"><span class="eyebrow">{label}</span>{render_md(b["teacher_analysis"])}{provenance(b["analysis_provenance"])}</aside>'
            answer = f'<details class="answer" open><summary>答案与解析<span>收起 / 展开</span></summary><div class="answer-body">{render_md(b["answer"])}{provenance(b["answer_provenance"])}{analysis}</div></details>'
        category = 'example' if b['category'] == '例题' else ('practice' if b['category'].startswith('练习') else 'homework')
        return f'<article class="question" id="{b["id"]}" data-question-id="{b["id"]}" data-category="{category}"><div class="question-label">{b["title"]}</div><div class="question-body">{text}</div>{"" if student else provenance(b["provenance_question"])}{answer}</article>'
    if kind in ['teacher', 'editor', 'intro']:
        label = '编辑增补' if kind == 'editor' else ('教参原文' if kind == 'teacher' else '阅读导引')
        return f'<aside class="{kind} teacher-only"><div class="eyebrow">{label}</div><h3>{b["title"]}</h3>{text}{provenance(b["provenance"])}</aside>'
    if b.get('emphases'):
        labels = {'concept': '关键概念', 'formula': '重要公式', 'method': '思想方法', 'condition': '条件提醒'}
        parts, cursor = [], 0
        for mark in sorted(b['emphases'], key=lambda s: s['start']):
            parts.append(render_md(b['markdown'][cursor:mark['start']]))
            parts.append(f'<aside class="key-point key-{mark["kind"]}" id="{mark["id"]}" data-emphasis="{mark["kind"]}"><div class="key-label">编辑标注 · {labels[mark["kind"]]}</div><h3>{html.escape(mark["title"])}</h3>{render_md(b["markdown"][mark["start"]:mark["end"]])}</aside>')
            cursor = mark['end']
        parts.append(render_md(b['markdown'][cursor:]))
        text = ''.join(parts)
    return f'<div class="prose" id="{b["id"]}">{text}{"" if student else provenance(b["provenance"])}</div>'


def print_panel(student):
    modes = [('all', '正文＋试题' if student else '完整内容'), ('text', '仅正文'), ('questions', '仅试题')]
    if not student:
        modes.append(('answers', '试题＋答案'))
    radios = ''.join(f'<label class="print-choice"><input type="radio" name="print-mode" value="{value}" {"checked" if value == "all" else ""}><span>{label}</span></label>' for value, label in modes)
    scopes = ''.join(f'<label><input type="checkbox" name="print-module" value="{b["id"]}" checked>{b["title"]}</label>' for b in BLOCKS if b['type'] == 'section' and not (student and b.get('teacher_only')))
    teacher_options = '' if student else '<label><input type="checkbox" id="print-notes">附带教参分析与教师批注</label><label><input type="checkbox" id="print-sources">保留来源行号</label>'
    return f'''<dialog id="print-dialog" aria-labelledby="print-dialog-title"><div class="dialog-heading"><div><span class="eyebrow">PRINT EDITION</span><h2 id="print-dialog-title">按内容打印</h2></div><button type="button" id="print-close" aria-label="关闭打印设置">×</button></div>
<p class="dialog-description">选择需要的内容，独立排为 A4。不会改变阅读页的展开状态。</p>
<form id="print-form"><fieldset><legend>01 / 内容组合</legend><div class="print-modes">{radios}</div></fieldset>
<fieldset><legend>02 / 章节范围</legend><div class="scope-actions"><button type="button" id="scope-all">全选</button><button type="button" id="scope-none">清空</button></div><div class="print-scopes">{scopes}</div></fieldset>
<fieldset><legend>03 / 题目范围</legend><div class="print-scopes"><label><input type="checkbox" name="print-category" value="example" checked>例题</label><label><input type="checkbox" name="print-category" value="practice" checked>课内练习</label><label><input type="checkbox" name="print-category" value="homework" checked>课后习题 A / B</label></div></fieldset>
<div class="print-options">{teacher_options}</div><p id="print-summary" role="status" aria-live="polite"></p><p class="print-help">{'' if student else '教师批注按勾选附带。'}“仅正文”不含例题、练习和题后解析；“仅试题”排除答案与批注。能放入一页的整题（含所选答案）尽量不跨页；超过一页的长题或解析允许续页。题图按原教材保留。建议A4、100%缩放，实际分页以系统打印预览为准。</p>
<div class="dialog-actions"><button type="button" id="print-preview">内容预览</button><button type="submit" id="print-submit">打印 / 另存 PDF</button></div></form></dialog>
<div id="print-preview-bar"><span>打印内容预览 <small>· 实际分页见系统打印</small></span><div><button id="print-back">返回阅读</button><button id="print-settings">调整范围</button><button id="print-now">打印 / 另存 PDF</button></div></div><div id="print-output"></div>'''


def page(student=False, section='8.1', title='向量的概念和线性运算',
         cover_title='向量的概念<br>和线性运算',
         deck='把“方向”引入运算。<br>从几何表示出发，建立可推演、可应用的向量语言。',
         knowledge_topics=3):
    mode = 'student' if student else 'teacher'
    stem = f'{section}-{title}'
    questions = [b for b in BLOCKS if b['type'] == 'question']
    examples = sum(b['category'] == '例题' for b in questions)
    parts, in_module = [], False
    for b in BLOCKS:
        if student and b.get('teacher_only'):
            continue
        if b['type'] == 'section':
            if in_module:
                parts.append('</section>')
            parts.append(f'<section class="content-module" data-module="{b["id"]}" data-title="{b["title"]}">')
            in_module = True
        parts.append(render_block(b, student))
    if in_module:
        parts.append('</section>')
    body = '\n'.join(parts)
    nav = ''.join(f'<a href="#{b["id"]}"><span>{b["number"]}</span>{b["title"]}</a>' for b in BLOCKS if b['type'] == 'section' and not (student and b.get('teacher_only')))
    controls = '<span class="student-tag">学生阅读版 · 不含题答与教师内容</span>' if student else f'''<button id="answer-toggle" aria-pressed="false">隐藏全部答案</button><button id="notes-toggle" aria-pressed="false">隐藏教师批注</button><a class="mode-link" href="{stem}-s.html">学生预览 ↗</a><a class="package-link" href="{section}-学生阅读包.zip" download>学生包 ↓</a>'''
    controls += '<button id="density-toggle" aria-pressed="false">舒展阅读</button><button id="print-open">按内容打印</button>'
    foot = '<p>本文件为独立学生阅读版，不含题目答案、解析、教参分析或教师背景材料。</p>' if student else f'''<p>本页范围为{section}，不代表全书已完成。原版出版信息尚未据版权页核验；不将目录中的“2026”直接当作版次。</p><p>原始资料只读保留。本轮保留原解与省略处，编辑勘误和新增说明可追溯。数学复核与网页测试范围详见同目录交付说明。</p>'''
    return f'''<!doctype html>
<html lang="zh-CN" data-mode="{mode}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="author" content="chengbai"><title>{section} {title} · {'学生阅读版' if student else '教师整合样章'}</title><link rel="stylesheet" href="vendor-katex/katex.min.css"><link rel="stylesheet" href="book.css"><script defer src="vendor-katex/katex.min.js"></script><script defer src="book.js"></script></head>
<body><a class="skip" href="#reading">跳到正文</a><div class="reading-progress" aria-hidden="true"></div>
<aside class="sidebar"><a class="brand" href="#top">沪教数学<span>教材 × 教参 · 整合书</span></a><div class="volume-label">必修第二册 / 第八章</div><div class="spine-number">{section}</div><nav aria-label="本节目录">{nav}</nav><div class="sidebar-foot">chengbai 数学讲义<br>网页版样章 · 2026.10.19<br>{'学生独立文件' if student else '教师阅读 / 备课'}</div></aside>
<div class="book-shell"><header class="toolbar"><span class="toolbar-label">{'学生阅读' if student else '教师阅读'} <span class="subtle">/ {section}</span></span><div class="controls">{controls}</div></header>
<main id="reading"><header class="chapter-cover" id="top"><div class="eyebrow">PLANE VECTORS · SECTION {section}</div><p class="edition">{'学生阅读版' if student else '教师整合样章'} / 沪教版高中数学</p><h1>{cover_title}<span class="cover-dot">.</span></h1><p class="cover-deck">{deck}</p><div class="chapter-meta"><span>{knowledge_topics} 个知识主题</span><span>{examples} 个例题</span><span>{len(questions) - examples} 道练习与习题</span></div></header>
<div class="book-body">{body}</div><footer class="book-footer">{foot}<a href="#top">返回本节开头 ↑</a></footer></main></div>{print_panel(student)}<div id="status" role="status" aria-live="polite"></div></body></html>'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for p, expected in MANIFEST['source_hashes'].items():
        assert digest(p) == expected, 'Source drift: ' + p
    make_content()
    # Clear the one embedded inline figure copy when the manifest also supplies its relocated version.
    for b in BLOCKS:
        if b['type'] == 'question':
            seen = set()
            def unique_image(m):
                if m[0] in seen:
                    return ''
                seen.add(m[0])
                return m[0]
            b['markdown'] = re.sub(r'!\[\]\([^)]+\)', unique_image, b['markdown'])
    (OUT / 'sources').mkdir(exist_ok=True)
    shutil.copy2(BOOK, OUT / 'sources/textbook-ch8.md')
    shutil.copy2(TEACHER, OUT / 'sources/teacher-ch8.md')
    (OUT / '8.1-向量的概念和线性运算.html').write_text(page(), encoding='utf-8')
    student_html = page(True)
    (OUT / '8.1-向量的概念和线性运算-s.html').write_text(student_html, encoding='utf-8')
    (OUT / 'content').mkdir(exist_ok=True)
    (OUT / 'content/8.1-整合底稿.json').write_text(json.dumps(BLOCKS, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT / 'content/来源与编辑记录.json').write_text(json.dumps({'source_hashes': MANIFEST['source_hashes'], 'assets': ASSETS, 'edits': EDITS}, ensure_ascii=False, indent=2), encoding='utf-8')
    for name in ['book.css', 'book.js']:
        shutil.copy2(ROOT / 'scripts' / name, OUT / name)
    student_images = set(re.findall(r'<img src="([^"]+)"', student_html))
    with zipfile.ZipFile(OUT / '8.1-学生阅读包.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for name in ['8.1-向量的概念和线性运算-s.html', 'book.css', 'book.js', *sorted(student_images)]:
            z.write(OUT / name, name)
        for p in (OUT / 'vendor-katex').rglob('*'):
            if p.is_file():
                z.write(p, p.relative_to(OUT))
    print(json.dumps({'output': str(OUT), 'questions': sum(b['type'] == 'question' for b in BLOCKS), 'assets': len(ASSETS), 'edits': EDITS}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
