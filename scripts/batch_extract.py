#!/usr/bin/env python3
"""Extract source-preserving textbook/teacher section records (no mathematical rewriting)."""

from project_paths import use_project_root, launch_browser
use_project_root()
from pathlib import Path
from collections import defaultdict, Counter
import argparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('sources/textbooks')
BOOKS = [('x1', '选择性必修第一册'), ('bx1', '必修第一册'),
         ('bx2', '必修第二册'), ('bx3', '必修第三册'), ('x2', '选择性必修第二册')]
IMAGE = re.compile(r'!\[([^\]]*)\]\(((?:[^()]|\([^()]*\))+)\)')
NUMBER = re.compile(r'^\s*(\d+)\s*[.．、](?!\d)\s*')
SECTION = re.compile(r'^#{1,6}\s*\*?\s*(\d+\.\d+)\s+(.+)')
EXAMPLE = re.compile(r'^(?:#{1,6}\s*)?(?:\*\*|__)?例\s*(\d+)(?!\d)\s*(?:\*\*|__)?(.+)')
SOLUTION = re.compile(r'^(?:#{1,6}\s*)?(?:\*\*|__)?(?:解(?:法\s*[一二三123])?|证明|证|画法)(?:\*\*|__)?(?:\s|[：:(（]|$)')
X1_REVIEWED_HASHES = {
    '1': '7f3a7376e2317114a3606e908defc90e0a01db188ddcde0ea7025814f0496577',
    '2': 'f9a3bb0b1aae50a77724a0067d2a54459e56dae712b033b9938051dd996af7c4',
    '3': '1e3cd03d43dd2ceeb42039c755ee92003783dda82c509d0e747b4fd848d2b90f',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plain(line):
    line = re.sub(r'^#{1,6}\s*', '', line.strip())
    line = re.sub(r'\\[A-Za-z]+', '', line)
    return re.sub(r'[\s${}\\]', '', line).replace('（', '(').replace('）', ')')


def issue(code, message, **kw):
    return dict(code=code, severity=kw.pop('severity', 'blocking'), message=message, **kw)


class Source:
    def __init__(self, path, label):
        self.path, self.label = path, label
        self.lines = path.read_text(encoding='utf-8').splitlines()
        self.images = []
        self.repairs = []
        self.hash = sha(path)
        self.patch_valid = True

    def text(self, a, b, exclude=None):
        parts = []
        for i in range(a, b + 1):
            if exclude and i in exclude:
                continue
            def image(m):
                src = m[2]
                if src.startswith(('https:', 'http:')):
                    return m[0]
                p = (self.path.parent / src).resolve()
                if not p.exists():
                    p2 = (self.path.parent.parent / src).resolve()
                    if p2.exists():
                        p = p2
                self.images.append(dict(source=self.label, line=i, original=src,
                                        absolute=str(p.relative_to(ROOT)), exists=p.is_file()))
                return '![' + m[1] + '](' + str(p.relative_to(ROOT)) + ')'
            parts.append(IMAGE.sub(image, self.lines[i - 1]))
        return '\n'.join(parts).strip()

    def prov(self, a, b):
        return [dict(source=self.label, start=a, end=b)] if b >= a else []


def group_heading(line, sec, current=None):
    s = plain(line)
    if re.fullmatch(r'[ABＣC]组', s):
        return (current or '习题' + sec).rstrip('ABC') + s[0]
    m = re.fullmatch(r'(练习|习题)(\d+\.\d+)?(?:\((\d+)\))?', s)
    if m:
        return m[1] + (m[2] or sec) + ('(' + m[3] + ')' if m[3] else '')
    if s in ('复习题', '拓展与思考'):
        return s
    return None


def teacher_records(src):
    """Only enter numbered answer mode after the explicit reference-answer boundary."""
    answers, analyses, misc = defaultdict(list), {}, []
    mode = None
    sec, group, start, num = '', None, None, None
    analysis_start = None

    def flush(end):
        nonlocal start
        if start is not None:
            answers[(group, num)].append((start, end))
        start = None

    for i, line in enumerate(src.lines, 1):
        s = plain(line)
        if re.search(r'[二三四五六七八九]、.*(?:参考答案|答案或提示|习题解答)', s):
            if analysis_start:
                analyses[sec] = (analysis_start, i - 1)
            mode, group, analysis_start = 'answers', None, None
            continue
        if re.search(r'[二三四五六七八九]、.*(?:教材分析|教学建议)', s):
            mode = 'analysis'
            continue
        if re.match(r'[四五六七八九]、', s) and mode == 'answers':
            flush(i - 1)
            mode = None
        sm = SECTION.match(line)
        if sm:
            flush(i - 1)
            if mode == 'analysis' and analysis_start:
                analyses[sec] = (analysis_start, i - 1)
            sec, group = sm[1], None
            if mode == 'analysis':
                analysis_start = i
            continue
        if mode != 'answers':
            continue
        gh = group_heading(line, sec, group)
        if gh:
            flush(i - 1)
            group = gh
            continue
        nm = re.match(r'^\s*([1-9]\d*)\s*[.．、]\s*', line)
        patch_path = ROOT / 'batch/patches/x2-ch5-numbering-proposed.json'
        if patch_path.exists():
            patch = json.loads(patch_path.read_text(encoding='utf-8'))
            if not src.patch_valid:
                misc.append(issue('approved-patch-source-drift', '修复所绑定的教材源哈希不一致，拒绝应用', line=i))
            if (patch.get('status') == 'approved-independent-review' and patch.get('source') == str(src.path)
                    and any(sha(Path(name)) != digest for name, digest in patch.get('source_hashes', {}).items())):
                misc.append(issue('approved-patch-source-drift', '修复所绑定的任一源哈希不一致，拒绝应用', line=i))
            if (patch.get('status') == 'approved-independent-review'
                    and patch.get('source') == str(src.path)
                    and src.patch_valid
                    and patch.get('source_hashes', {}).get(str(src.path)) == src.hash):
                replacement = next((x for x in patch.get('renumber', []) if x['line'] == i), None)
                if replacement:
                    if line.strip() != replacement['anchor']:
                        misc.append(issue('patch-anchor-mismatch', '经复核的题号修复锚点改变，未应用',
                                          line=i, severity='blocking'))
                    elif replacement['group'] != group:
                        misc.append(issue('patch-group-mismatch', '经复核修复的题组与当前状态不符，未应用',
                                          line=i, group=group, severity='blocking'))
                    else:
                        flush(i - 1)
                        num, start = replacement['number'], i
                        src.repairs.append(dict(line=i, repair='应用经独立复核的教师答案编号修复',
                                                group=group, number=num,
                                                patch='batch/patches/x2-ch5-numbering-proposed.json',
                                                evidence=replacement['evidence']))
                        continue
        if (src.hash == 'd1c3551a471d0df8f1c423832d7b604a0e77f9e09cc22d731491f089cb6728c6' and i == 664
                and line.startswith('如,(1) ${5x} - y + 5 = 0.')):
            flush(i - 1)
            num, start = 9, i
            src.repairs.append(dict(line=i, repair='恢复OCR遗漏的1.2习题B组9题答案编号',
                                    evidence='独立复算截距和与面积，分别C=5与C=±10√2，吻合教材第9题'))
            continue
        if (src.hash == '955c9f50ad7cda82b9d3bd28bfabcfc8b11cb574e5aff5b0c61addbde6e61445' and i in (1150, 1152)
                and ((i == 1150 and line.startswith('3.')) or (i == 1152 and line.startswith('4.')))):
            flush(i - 1)
            num, start = (4 if i == 1150 else 5), i
            src.repairs.append(dict(line=i, repair='修复2.3习题A组OCR题号为' + str(num),
                                    evidence='独立复算m<-2及2x²-y²=1，与教材第4/5题逐题吻合'))
            continue
        if nm and group:
            flush(i - 1)
            num, start = int(nm[1]), i
    flush(len(src.lines))
    return answers, analyses, misc


def image_moves(src, a, b):
    """Relocate explicitly captioned exercise figures; never infer an unlabelled target."""
    excluded, figures = set(), defaultdict(list)
    for i in range(a, b + 1):
        if not IMAGE.search(src.lines[i - 1]):
            continue
        for j in range(i + 1, min(i + 5, b) + 1):
            text = plain(src.lines[j - 1])
            if not text:
                continue
            m = re.fullmatch(r'\(?第(\d+)题\)?', text)
            if m:
                figures[int(m[1])].append((i, j))
                excluded.update(range(i, j + 1))
            break
    return excluded, figures


def make_block(src, kind, title, a, b, **kw):
    return dict(type=kind, title=title, markdown=src.text(a, b),
                provenance=src.prov(a, b), **kw)


def remove_book_lines(blocks, book, removed):
    for block in blocks:
        for field, provenance in [('markdown', 'provenance_question' if block['type'] == 'question' else 'provenance'),
                                  ('answer', 'answer_provenance')]:
            refs = block.get(provenance, [])
            if not any(p['source'] == 'book' and any(i in removed for i in range(p['start'], p['end'] + 1)) for p in refs):
                continue
            kept = []
            for p in refs:
                if p['source'] != 'book':
                    kept.append(p)
                    continue
                start = None
                for i in range(p['start'], p['end'] + 2):
                    if i <= p['end'] and i not in removed:
                        start = i if start is None else start
                    elif start is not None:
                        kept.extend(book.prov(start, i - 1))
                        start = None
            block[provenance] = kept
            block[field] = '\n\n'.join(book.text(p['start'], p['end']) for p in kept if p['source'] == 'book')
            if field == 'markdown' and block['type'] == 'question':
                block['provenance'] = kept.copy()


def apply_reviewed_repairs(bid, sec, blocks, issues, book):
    """Small explicit OCR-order repairs confirmed by the independent x1 reviewer."""
    repairs = []
    if bid == 'x1' and sec.split('.')[0] in X1_REVIEWED_HASHES:
        if book.hash != X1_REVIEWED_HASHES[sec.split('.')[0]]:
            issues.append(issue('reviewed-patch-source-drift', '源哈希改变，禁止应用旧按行复核修复'))
            return repairs
    def example(n):
        return next(q for q in blocks if q['type'] == 'question' and q['category'] == '例题'
                    and q['title'] == '例题 ' + str(n))
    if bid == 'x1' and sec == '1.1':
        remove_book_lines(blocks, book, set(range(77, 82)))
        q = example(3)
        blocks.insert(blocks.index(q) + 1, make_block(book, 'prose', '一次函数的斜率', 79, 79))
        repairs.append(dict(line=79, repair='将OCR插入例3解答中的一般概念框归还教材正文'))
    if bid == 'x1' and sec == '2.1':
        remove_book_lines(blocks, book, set(range(209, 214)))
        q = example(5)
        blocks.insert(blocks.index(q) + 1, make_block(book, 'prose', '圆的一般方程判别式', 211, 211))
        remove_book_lines(blocks, book, set(range(335, 340)))
        q = example(8)
        q['markdown'] = book.text(341, 343) + '\n\n' + book.text(337, 339)
        q['provenance_question'] = book.prov(341, 343) + book.prov(337, 339)
        q['provenance'] = q['provenance_question'].copy()
        q['answer'] = book.text(335, 336) + '\n\n' + book.text(345, 399)
        q['answer_provenance'] = book.prov(335, 336) + book.prov(345, 399)
        issues[:] = [x for x in issues if not (x['code'] == 'example-answer-boundary' and x.get('line') == 341)]
        repairs.append(dict(line=335, repair='例8前置解与题图归位；211判别式一般概念框归正文'))
    if bid == 'x1' and sec == '2.5':
        remove_book_lines(blocks, book, set(range(1849, 1865)))
        q = example(1)
        blocks.insert(blocks.index(q) + 1, make_block(book, 'prose', '求轨迹方程的基本步骤', 1849, 1864))
        raw = book.lines[2094]
        marker = ' 径 '
        if marker not in raw:
            raise ValueError('Reviewed x1 2.5 source anchor changed')
        answer, public = raw.split(marker, 1)
        public = '径 ' + public
        remove_book_lines(blocks, book, set(range(2097, 2100)))
        for block in blocks:
            if block['type'] != 'question' and any(p['source'] == 'book' and p['start'] <= 2095 <= p['end'] for p in block['provenance']):
                block['markdown'] = block['markdown'].replace(raw, public)
        q = example(6)
        q['answer'], q['answer_provenance'] = answer, book.prov(2095, 2095)
        q['markdown'] += '\n\n' + book.text(2097, 2099)
        q['provenance_question'] += book.prov(2097, 2099)
        issues[:] = [x for x in issues if not (x['code'] == 'example-answer-boundary' and x.get('line') == 2101)]
        repairs.append(dict(line=2095, repair='分开OCR混行的例6前置答案与极坐标概念续文；图2097–2099归题干'))
    if bid == 'x1' and sec == '2.3':
        remove_book_lines(blocks, book, set(range(1167, 1172)))
        q = example(2)
        blocks.insert(blocks.index(q) + 1, make_block(book, 'teacher', '教材方法追问 · 双曲线的分支',
                                                   1169, 1169, teacher_only=True))
        repairs.append(dict(line=1169, repair='例2(1)中的追问不新建例题，隔离为教师提示'))
    if bid == 'x1' and sec == '3.1':
        remove_book_lines(blocks, book, set(range(207, 217)))
        q = example(3)
        blocks.insert(blocks.index(q) + 1, make_block(book, 'prose', '空间向量平行的充要条件', 207, 212))
        q = example(4)
        q['markdown'] += '\n\n' + book.text(213, 215)
        q['provenance_question'] += book.prov(213, 215)
        repairs.append(dict(line=207, repair='空间向量平行定理归正文；213–215图归例4题干'))
    if bid == 'x1' and sec == '3.4':
        remove_book_lines(blocks, book, set(range(817, 833)))
        q = example(2)
        q['markdown'] = book.text(833, 837) + '\n\n' + book.text(829, 831)
        q['provenance_question'] = book.prov(833, 837) + book.prov(829, 831)
        q['provenance'] = q['provenance_question'].copy()
        q['answer'] = book.text(827, 828) + '\n\n' + book.text(839, 874)
        q['answer_provenance'] = book.prov(827, 828) + book.prov(839, 874)
        blocks.insert(blocks.index(q), make_block(book, 'prose', '垂直于平面的判定', 817, 825))
        issues[:] = [x for x in issues if not (x['code'] == 'example-answer-boundary' and x.get('line') == 833)]
        repairs.append(dict(line=827, repair='例2证明前置与题图归位；817–825一般定理恢复教材正文',
                            evidence='独立点积复算为0并核对原文行段'))
    return repairs


def isolate_unattached_solutions(blocks, issues, book):
    """Unattached explicit solutions stay teacher-only instead of leaking to students."""
    updated = []
    for block in blocks:
        if block['type'] != 'prose' or len(block.get('provenance', [])) != 1:
            updated.append(block)
            continue
        p = block['provenance'][0]
        if p['source'] != 'book':
            updated.append(block)
            continue
        split = next((i for i in range(p['start'], p['end'] + 1)
                      if re.match(r'^解(?:\s|[：:(（]|$)', book.lines[i - 1].strip())
                      and book.lines[i - 1].strip() in block['markdown']), None)
        if split is None:
            updated.append(block)
            continue
        if split > p['start']:
            updated.append(make_block(book, 'prose', block['title'], p['start'], split - 1))
        updated.append(make_block(book, 'teacher', '教材证明或前置解答 · 待边界复核',
                                  split, p['end'], teacher_only=True))
        issues.append(issue('unattached-book-solution', '正文中检测到独立证明或解答，已隔离教师侧，需复核归属与正文续接', line=split))
    blocks[:] = updated


def emphasize_definitions(blocks, sid):
    for index, block in enumerate(blocks):
        if block['type'] != 'prose' or block.get('emphases'):
            continue
        text = block['markdown']
        marks = []
        # Mark only explicit public textbook definitions, never arbitrary solutions.
        for m in re.finditer(r'[^\n]+(?:\n(?!\n)[^\n]+)*', text):
            para = m[0]
            if not re.search(r'叫做|称为|定义为|充要条件', para) or len(para) > 850 or SOLUTION.match(para):
                continue
            if re.match(r'^(?:例\s*\d|[（(]?\d+[)）.])', para) or '例如' in para[:8]:
                continue
            marks.append(dict(start=m.start(), end=m.end(), kind='concept', title='教材概念与条件',
                              id=f'{sid}-definition-{index}-{len(marks)}', origin='editorial-emphasis'))
        # A displayed formula directly announced as a public formula is one unit.
        for m in re.finditer(r'(^|\n\n)((?:[^\n]*公式[^\n]*[:：为是]|综上所述[^\n]*为)\s*\n\n\$\$[\s\S]*?\$\$)', text):
            aa, ab = m.start(2), m.end(2)
            if not any(aa < z['end'] and ab > z['start'] for z in marks):
                marks.append(dict(start=aa, end=ab, kind='formula', title='教材公式',
                                  id=f'{sid}-formula-{index}-{len(marks)}', origin='editorial-emphasis'))
        if block['title'] == '求轨迹方程的基本步骤':
            aa = text.index('步骤 1')
            ab = text.index('\n\n这里', aa)
            marks = [z for z in marks if z['end'] <= aa or z['start'] >= ab]
            marks.append(dict(start=aa, end=ab, kind='method', title='求轨迹方程的基本步骤',
                              id=f'{sid}-method-{index}', origin='editorial-emphasis'))
        if marks:
            block['emphases'] = sorted(marks, key=lambda z: z['start'])


def parse_section(book, teacher, sec, title, a, b, sid, answers, analysis):
    blocks = [dict(type='section', title=title, markdown='', provenance=book.prov(a, a),
                   id=sid, number=sec, subtitle='教材与正式教参整合')]
    issues = []
    group = None
    cursor = a + 1
    current = None
    used_answers = set()

    def prose(lo, hi):
        if lo <= hi and book.text(lo, hi):
            blocks.append(make_block(book, 'prose', '', lo, hi))

    def question(lo, hi, kind, n):
        nonlocal current
        if kind == '例题':
            split = next((j for j in range(lo + 1, hi + 1)
                          if SOLUTION.match(book.lines[j - 1].strip())), None)
            # Commentary beginning with "example N in ..." resumes public exposition.
            tail = next((j for j in range((split or hi) + 1, hi + 1)
                         if re.match(r'^例\s*\d+\s*中', book.lines[j - 1])), hi + 1)
            qhi = (split - 1) if split else hi
            ans = book.text(split, tail - 1) if split else ''
            ap = book.prov(split, tail - 1) if split else []
            qp = book.prov(lo, qhi)
            text = book.text(lo, qhi)
            if not split:
                issues.append(issue('example-answer-boundary', '未找到例题解答起点，未猜分', line=lo))
        else:
            tail = hi + 1
            qhi = hi
            text, qp = book.text(lo, hi), book.prov(lo, hi)
            key = (kind, n)
            rows = answers.get(key, [])
            ans, ap = '', []
            if len(rows) == 1:
                aa, ab = rows[0]
                ans, ap = teacher.text(aa, ab), teacher.prov(aa, ab)
                used_answers.add(key)
                payload = re.sub(r'^\s*[1-9]\d*\s*[.．、]\s*', '', ans, count=1)
                if not payload.strip(' \t\n.．、:：'):
                    ans, ap = '', []
                    issues.append(issue('empty-answer-content', '正式教参只有编号，没有有效答案内容',
                                        group=kind, number=n, line=aa))
            else:
                issues.append(issue('missing-answer' if not rows else 'ambiguous-answer',
                                    '正式教参答案缺失或题号重复，未配对', group=kind, number=n, line=lo))
        qid = sid + '-' + ('ex' if kind == '例题' else re.sub(r'[^A-Za-z0-9]', '', kind.replace('练习', 'p').replace('习题', 'h').replace('复习题', 'r').replace('拓展与思考', 't'))) + '-' + str(n)
        blocks.append(dict(type='question', title=('例题 ' if kind == '例题' else kind + ' · ') + str(n),
                           markdown=text, provenance=qp, provenance_question=qp, id=qid,
                           category=kind, answer=ans, answer_provenance=ap,
                           teacher_analysis='', analysis_provenance=[]))
        if tail <= hi:
            prose(tail, hi)

    i = a + 1
    while i <= b:
        line = book.lines[i - 1].strip()
        gh = group_heading(line, sec, group)
        em = EXAMPLE.match(line)
        # Lookahead prevents regex backtracking from accepting commentary as an example.
        if em and re.match(r'^(?:\*\*|__)?例\s*\d+\s*(?:[中的是为也还可]|表明|展示|告诉|给我们|和例|为什么|的结果|从图像|[（(]\d+[)）]\s*(?:也|可|是|的|中))', line):
            em = None
        nm = NUMBER.match(line) if group else None
        heading = line.startswith('#')
        event = gh or em or nm or heading
        if event:
            if current:
                question(current[0], i - 1, current[1], current[2])
                current = None
            else:
                prose(cursor, i - 1)
            if gh:
                group = gh
                blocks.append(make_block(book, 'heading', re.sub(r'^#+\s*', '', line), i, i))
                cursor = i + 1
            elif em:
                group = None
                current = (i, '例题', int(em[1]))
                cursor = i
            elif nm:
                current = (i, group, int(nm[1]))
                cursor = i
            else:
                group = None
                blocks.append(make_block(book, 'heading', re.sub(r'^#+\s*', '', line), i, i))
                cursor = i + 1
        i += 1
    if current:
        question(current[0], b, current[1], current[2])
    else:
        prose(cursor, b)

    # Move captioned figures inside each original exercise group, including figures
    # OCR placed in an earlier question. Provenance remains the original line span.
    groups = defaultdict(list)
    for q in blocks:
        if q['type'] == 'question' and q['category'] != '例题':
            groups[q['category']].append(q)
    for key, qs in groups.items():
        lo = min(q['provenance_question'][0]['start'] for q in qs)
        hi = max(q['provenance_question'][0]['end'] for q in qs)
        # Include figure paragraphs between the group heading and first question.
        for k in range(lo - 1, a, -1):
            if group_heading(book.lines[k - 1], sec):
                lo = k + 1
                break
            if NUMBER.match(book.lines[k - 1]):
                break
        exclude, figures = image_moves(book, lo, hi)
        for q in qs:
            p = q['provenance_question'][0]
            q['markdown'] = book.text(p['start'], p['end'], exclude)
            for aa, ab in figures.get(int(q['title'].split(' · ')[-1]), []):
                q['markdown'] += '\n\n' + book.text(aa, ab)
                q['provenance_question'] += book.prov(aa, ab)
        for p in blocks:
            if p['type'] == 'prose' and p['provenance']:
                aa, ab = p['provenance'][0]['start'], p['provenance'][0]['end']
                if any(j in exclude for j in range(aa, ab + 1)):
                    p['markdown'] = book.text(aa, ab, exclude)

    if sec in analysis:
        aa, ab = analysis[sec]
        blocks.insert(1, make_block(teacher, 'teacher', '正式教参 · 教材分析与教学建议', aa, ab, teacher_only=True))
    for category, qs in groups.items():
        source_numbers = [n for (g, n), spans in answers.items() if g == category for _ in spans]
        question_numbers = [int(q['title'].split(' · ')[-1]) for q in qs]
        if (set(source_numbers) != set(question_numbers)
                or len(source_numbers) != len(set(source_numbers))):
            for q in qs:
                q['answer'], q['answer_provenance'] = '', []
            issues.append(issue('answer-group-numbering', '题组题号集合不一致或重复，整组停止自动配对以防错位',
                                group=category, question_numbers=question_numbers,
                                answer_numbers=source_numbers))
            ranges = [span for (g, _), spans in answers.items() if g == category for span in spans]
            if ranges:
                blocks.append(make_block(teacher, 'teacher', category + ' · 未配对参考答案原文（题号异常）',
                                         min(a for a, b in ranges), max(b for a, b in ranges), teacher_only=True))
    ids = [q['id'] for q in blocks if q['type'] == 'question']
    if len(ids) != len(set(ids)):
        issues.append(issue('duplicate-question-id', '同组题号重复，需要人工核查'))
        duplicates = {key for key, count in Counter(ids).items() if count > 1}
        for q in blocks:
            if q['type'] == 'question' and q['id'] in duplicates:
                q['id'] += '-L' + str(q['provenance_question'][0]['start'])
    return blocks, issues


def approved_section(sec):
    base = ROOT / 'designs/2026-10-19-沪教版教材教参整合样章'
    directory = base if sec == '8.1' else base / '8.2-向量的数量积'
    p = directory / 'content' / (sec + '-整合底稿.json')
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding='utf-8'))
    blocks = data if isinstance(data, list) else data.get('blocks')
    record = json.loads((directory / 'content/来源与编辑记录.json').read_text(encoding='utf-8'))
    assets = record.get('assets', {})
    def recurse(obj):
        if isinstance(obj, dict):
            mapped = {k: recurse(v) for k, v in obj.items()}
            # Replacing short sample image links moves every later text offset.
            if obj.get('emphases') and isinstance(obj.get('markdown'), str):
                for before, after in zip(obj['emphases'], mapped['emphases']):
                    for boundary in ('start', 'end'):
                        after[boundary] = len(recurse(obj['markdown'][:before[boundary]]))
            return mapped
        if isinstance(obj, list):
            return [recurse(v) for v in obj]
        if isinstance(obj, str):
            def replace(m):
                item = assets.get(m[2], {})
                path = item.get('source') if isinstance(item, dict) else None
                if not path:
                    path = str((directory / m[2]).resolve())
                return '![' + m[1] + '](' + path + ')'
            return IMAGE.sub(replace, obj)
        return obj
    return recurse(blocks)


def reuse_paired_records(chapter, sec, blocks, issues, book, teacher):
    audit = Path('sources/paired')
    candidates = list(audit.glob(f'第{chapter}章*教材教参配对-20261009/配对清单.json'))
    if len(candidates) != 1:
        return []
    data = json.loads(candidates[0].read_text(encoding='utf-8'))
    if any(data['source_hashes'].get(str(s.path)) != sha(s.path) for s in (book, teacher)):
        issues.append(issue('paired-source-drift', '旧配对清单源哈希不匹配，禁止复用'))
        return []
    repairs = []
    for q in [b for b in blocks if b['type'] == 'question' and b['category'] == '例题']:
        n = int(q['title'].split()[-1])
        key = sec + '·例' + str(n)
        records = [r for r in data['records'] if r['key'] == key]
        figures = [r for r in records if r['kind'] == 'example_figure']
        if figures:
            remove_book_lines(blocks, book, {i for r in figures for i in range(r['start'], r['end'] + 1)})
            q['markdown'] += '\n\n' + '\n\n'.join(book.text(r['start'], r['end']) for r in figures)
            q['provenance_question'] += [p for r in figures for p in book.prov(r['start'], r['end'])]
        analyses = [r for r in records if r['kind'] == 'example_analysis']
        if analyses:
            q['teacher_analysis'] = '\n\n'.join(teacher.text(r['start'], r['end']) for r in analyses)
            q['analysis_provenance'] = [p for r in analyses for p in teacher.prov(r['start'], r['end'])]
        if not q['answer']:
            answers = [r for r in records if r['kind'] == 'example_solution']
            questions = [r for r in records if r['kind'] == 'example_question']
            if answers and questions:
                q['answer'] = '\n\n'.join(book.text(r['start'], r['end']) for r in answers)
                q['answer_provenance'] = [p for r in answers for p in book.prov(r['start'], r['end'])]
                q['markdown'] = '\n\n'.join(book.text(r['start'], r['end']) for r in questions + figures)
                q['provenance_question'] = [p for r in questions + figures for p in book.prov(r['start'], r['end'])]
                issues[:] = [x for x in issues if not (x['code'] == 'example-answer-boundary'
                                                      and x.get('line') == questions[0]['start'])]
        repairs.append(dict(repair='复用哈希一致的既有例题配对记录（题图、教参分析及缺失解答边界）',
                            key=key, paired_manifest=str(candidates[0])))
    return repairs


def build_book(bid, title, chapter_filter=None):
    chapters = []
    for path in sorted((SOURCE / title).glob('*/*-dollar.md'), key=lambda p: int(re.search(r'第(\d+)章', p.name)[1])):
        chapter = re.search(r'第(\d+)章', path.name)[1]
        if chapter_filter and chapter not in chapter_filter:
            continue
        teacher_candidates = [p for p in (SOURCE / '教参与课标' / ('沪教版教参' + title)).glob('*分章/*.md')
                              if re.search(r'第\s*' + chapter + r'\s*章', p.name) and '·' not in p.name]
        if len(teacher_candidates) != 1:
            raise RuntimeError(f'{bid} c{chapter}: teacher candidates {teacher_candidates}')
        book, teacher = Source(path, 'book'), Source(teacher_candidates[0], 'teacher')
        patch_path = ROOT / 'batch/patches/x2-ch5-numbering-proposed.json'
        if bid == 'x2' and chapter == '5' and patch_path.exists():
            patch = json.loads(patch_path.read_text(encoding='utf-8'))
            expected = patch.get('source_hashes', {})
            teacher.patch_valid = (patch.get('status') == 'approved-independent-review'
                                   and expected.get(str(book.path)) == book.hash
                                   and expected.get(str(teacher.path)) == teacher.hash)
        answers, analyses, teacher_parse_issues = teacher_records(teacher)
        boundaries = [(i, m[1], m[2]) for i, l in enumerate(book.lines, 1)
                      if (m := SECTION.match(l)) and m[1].split('.')[0] == chapter]
        last_start = boundaries[-1][0]
        last_section = boundaries[-1][1]
        last_exercise = max([last_start] + [i for i in range(last_start + 1, len(book.lines) + 1)
                            if plain(book.lines[i - 1]).startswith('习题' + last_section)])
        end_start = next((i for i in range(last_exercise + 1, len(book.lines) + 1)
                          if re.match(r'^#{1,6}\s+(?:课后阅读|阅读|内容提要|复习题|本章小结)', book.lines[i - 1])), None)
        if end_start:
            boundaries.append((end_start, 'chapter-end-' + chapter, '章末阅读、内容提要与复习题'))
        entries = []
        for ix, (a, sec, name) in enumerate(boundaries):
            book.images, teacher.images = [], []
            b = boundaries[ix + 1][0] - 1 if ix + 1 < len(boundaries) else len(book.lines)
            sid = bid + '-' + sec.replace('.', '-')
            blocks, issues = parse_section(book, teacher, sec, name, a, b, sid, answers, analyses)
            issues.extend(x for x in teacher_parse_issues if x.get('line', 0) in range(a, b + 1))
            if bid == 'bx2' and sec in ('8.1', '8.2'):
                approved = approved_section(sec)
                if approved:
                    blocks, issues = approved, []
            if ix == 0 and a > 1:
                blocks.insert(1, make_block(book, 'prose', '章导语', 1, a - 1))
            overview = [i for i, l in enumerate(teacher.lines, 1) if re.match(r'一、', plain(l))]
            analysis_heading = [i for i, l in enumerate(teacher.lines, 1) if re.match(r'二、', plain(l))]
            if ix == 0 and overview and analysis_heading:
                blocks.insert(2, make_block(teacher, 'teacher', '正式教参 · 本章概述',
                                           overview[0], analysis_heading[0] - 1, teacher_only=True))
            related = [i for i, l in enumerate(teacher.lines, 1)
                       if re.match(r'[四五六七]、.*(?:阅读|资料|文献)', plain(l))]
            if sec.startswith('chapter-end') and related:
                blocks.append(make_block(teacher, 'teacher', '正式教参 · 相关阅读材料',
                                         related[0], len(teacher.lines), teacher_only=True))
            repairs = apply_reviewed_repairs(bid, sec, blocks, issues, book)
            if bid == 'bx2' and sec not in ('8.1', '8.2'):
                repairs += reuse_paired_records(chapter, sec, blocks, issues, book, teacher)
            if bid == 'x2' and chapter == '5':
                patch = json.loads((ROOT / 'batch/patches/x2-ch5-numbering-proposed.json').read_text(encoding='utf-8'))
                for extra in patch.get('extra_issues', []):
                    if extra.get('section') == sid:
                        issues.append(dict(code=extra['code'], severity=extra['severity'],
                                            message=extra['message'], book_line=extra['book_line'],
                                            teacher_line=extra['teacher_line']))
            if not (bid == 'bx2' and sec in ('8.1', '8.2')):
                isolate_unattached_solutions(blocks, issues, book)
                emphasize_definitions(blocks, sid)
            content = dict(schema_version=1, id=sid, book_id=bid, book_title=title,
                           chapter=chapter, chapter_title=path.parent.name, section=sec,
                           title=name, sources=dict(book=str(book.path), teacher=str(teacher.path)),
                           source_hashes={str(s.path): sha(s.path) for s in (book, teacher)},
                           blocks=blocks, issues=issues,
                           parser_version='batch-extract-v1', review_status='pending-independent-review')
            content['editorial_repairs'] = teacher.repairs + repairs
            content['image_references'] = list({(im['source'], im['line'], im['original']): im
                                               for s in (book, teacher) for im in s.images}.values())
            for im in content['image_references']:
                if not im['exists']:
                    issues.append(issue('missing-image', '原图路径不可达', **im))
            review_path = ROOT / 'batch/reviews' / (sid + '.json')
            content['issues'][:] = [x for x in content['issues'] if x.get('origin') != 'independent-review']
            content.pop('independent_review', None)
            question_count = sum(x['type'] == 'question' for x in blocks)
            model_bytes = (json.dumps(content, ensure_ascii=False, indent=2) + '\n').encode()
            if review_path.exists():
                review = json.loads(review_path.read_text(encoding='utf-8'))
                reviewed = (review.get('model_sha256') == hashlib.sha256(model_bytes).hexdigest()
                            and review.get('coverage', {}).get('source_hashes') == content['source_hashes']
                            and review.get('coverage', {}).get('question_count') == question_count)
                if reviewed:
                    content['independent_review'] = dict(status=review['status'], reviewer='batch/reviews/' + review_path.name,
                                                         question_count=question_count,
                                                         limits=review.get('limits', []))
                    for note in review.get('issues', []):
                        if note.get('status', 'open') == 'open':
                            content['issues'].append(dict(origin='independent-review', code=note['code'],
                                                          severity=note['severity'], message=note['message'],
                                                          source=note.get('source'), line=note.get('line')))
            relative = Path('batch/sections') / bid / (sid + '.json')
            dest = ROOT / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(content, ensure_ascii=False, indent=2) + '\n'
            if not dest.exists() or dest.read_text(encoding='utf-8') != payload:
                dest.write_text(payload, encoding='utf-8')
            entries.append(dict(id=sid, section=sec, title=name, path=str(relative),
                                status='blocked' if any(x['severity'] == 'blocking' for x in issues) else 'extracted',
                                issues=issues,
                                question_count=sum(x['type'] == 'question' for x in blocks)))
            print(bid, sec, 'questions', entries[-1]['question_count'], 'issues', len(issues), flush=True)
        chapters.append(dict(id=bid + '-c' + chapter, title=path.parent.name,
                             book_source=str(book.path), teacher_source=str(teacher.path), sections=entries))
    return dict(id=bid, title=title, chapters=chapters)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--books', nargs='+', default=[b[0] for b in BOOKS])
    ap.add_argument('--chapters', nargs='+')
    args = ap.parse_args()
    target = ROOT / 'batch/manifests/catalog.json'
    old = json.loads(target.read_text(encoding='utf-8')) if target.exists() else dict(schema_version=1, books=[])
    by_id = {b['id']: b for b in old['books']}
    for bid, title in BOOKS:
        if bid in args.books:
            result = build_book(bid, title, args.chapters)
            if args.chapters and bid in by_id:
                merged = {c['id']: c for c in by_id[bid]['chapters']}
                merged.update({c['id']: c for c in result['chapters']})
                result['chapters'] = sorted(merged.values(), key=lambda c: int(c['id'].split('-c')[-1]))
            by_id[bid] = result
            old['books'] = [by_id[x] for x, _ in BOOKS if x in by_id]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(old, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    checks = dict(schema_version=1, checks=[], scope='source hashes, image reachability, IDs, spans, emphasis offsets; not mathematical approval')
    ids = set()
    for volume in old['books']:
        for chapter in volume['chapters']:
            for entry in chapter['sections']:
                data = json.loads((ROOT / entry['path']).read_text(encoding='utf-8'))
                errors = []
                sources = {k: Path(v) for k, v in data['sources'].items()}
                line_counts = {k: len(p.read_text(encoding='utf-8').splitlines()) for k, p in sources.items()}
                for name, expected in data['source_hashes'].items():
                    if sha(Path(name)) != expected:
                        errors.append('source-hash-mismatch:' + name)
                for block in data['blocks']:
                    if block['type'] == 'question':
                        if block['id'] in ids:
                            errors.append('duplicate-id:' + block['id'])
                        ids.add(block['id'])
                    for field in ['markdown', 'answer', 'teacher_analysis']:
                        for match in IMAGE.finditer(block.get(field, '')):
                            if not Path(match[2]).is_file():
                                errors.append('missing-image:' + match[2])
                    for field in ['provenance', 'provenance_question', 'answer_provenance', 'analysis_provenance']:
                        for span in block.get(field, []):
                            if not (1 <= span['start'] <= span['end'] <= line_counts.get(span['source'], 0)):
                                errors.append('invalid-span:' + repr(span))
                    for mark in block.get('emphases', []):
                        if not (0 <= mark['start'] < mark['end'] <= len(block['markdown'])):
                            errors.append('invalid-emphasis:' + mark['id'])
                        if mark['kind'] not in ('concept', 'formula', 'method', 'condition'):
                            errors.append('invalid-emphasis-kind:' + mark['kind'])
                checks['checks'].append(dict(id=data['id'], status='pass' if not errors else 'fail', errors=errors,
                                             questions=sum(b['type'] == 'question' for b in data['blocks']),
                                             unanswered=sum(b['type'] == 'question' and not b.get('answer') for b in data['blocks']),
                                             issue_count=len(data['issues'])))
    checks['summary'] = dict(nodes=len(checks['checks']), passed=sum(c['status'] == 'pass' for c in checks['checks']),
                             questions=sum(c['questions'] for c in checks['checks']),
                             unanswered=sum(c['unanswered'] for c in checks['checks']),
                             issues=sum(c['issue_count'] for c in checks['checks']))
    (target.parent / 'extraction-checks.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('STATIC', json.dumps(checks['summary']), flush=True)


if __name__ == '__main__':
    main()
