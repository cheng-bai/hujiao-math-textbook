#!/usr/bin/env python3
"""Extend the approved web-book design to section 8.2 without rebuilding 8.1."""

from project_paths import use_project_root, launch_browser
use_project_root()
from pathlib import Path
import hashlib
import json
import re
import shutil
import zipfile

import build_sample as book

PARENT = book.OUT
OUT = PARENT / '8.2-向量的数量积'
STEM = '8.2-向量的数量积'
BASE_NORMALIZE = book.normalize


def normalize(text, source):
    corrections = [
        (r'若 $\lambda  > 0$ ,则 $\left| {\lambda \overrightarrow{a}}\right|  =  - \lambda \left| \overrightarrow{a}\right|$ , ',
         r'若 $\lambda  > 0$ ,则 ', 'λ>0段删除重复且符号错误的模长式，保留λ<0段及紧随其后的正确式'),
        (r'$\overrightarrow{AB}$ . $\overrightarrow{AC} =$',
         r'$\overrightarrow{AB} \cdot \overrightarrow{AC} =$', 'B组第5题恢复数量积点，不把点积断成两段公式'),
        (r'$\overrightarrow{a} \cdot  \overrightarrow{b} = \overrightarrow{b}$ . $\overrightarrow{c} = \overrightarrow{c} \cdot  \overrightarrow{d} = \overrightarrow{d} \cdot  \overrightarrow{a}$',
         r'$\overrightarrow{a} \cdot \overrightarrow{b} = \overrightarrow{b} \cdot \overrightarrow{c} = \overrightarrow{c} \cdot \overrightarrow{d} = \overrightarrow{d} \cdot \overrightarrow{a}$',
         'B组第8题恢复数量积点及连续等式'),
        ('证明 (1)的证明如下: ?', '证明 (1)的证明如下:', '删除例4证明首句末尾孤立OCR问号'),
        ('6.27.', '6. $27$.', '教参A组第6题分开题号与答案，不改数值'),
        ('4.10.', '4. $10$.', '教参B组第4题分开题号与答案，不改数值'),
    ]
    for before, after, reason in corrections:
        start = len(book.EDITS)
        text = book.edit(text, before, after, reason)
        for entry in book.EDITS[start:]:
            entry['source'] = source
            entry['source_lines'] = [i for i, line in enumerate(book.LINES[source], 1) if before in line]

    # Reflow the same teacher equation at equalities, not by shrinking the formula.
    original = book.LINES['teacher'][212]
    if original in text:
        reflow = r'''\begin{aligned}
&\left|\overrightarrow{b}+\overrightarrow{c}\right|\cos\langle\overrightarrow{a},\overrightarrow{b}+\overrightarrow{c}\rangle\overrightarrow{a_0}\\
&=\left|\overrightarrow{b}\right|\cos\langle\overrightarrow{a},\overrightarrow{b}\rangle\overrightarrow{a_0}
+\left|\overrightarrow{c}\right|\cos\langle\overrightarrow{a},\overrightarrow{c}\rangle\overrightarrow{a_0}\\
&=\left(\left|\overrightarrow{b}\right|\cos\langle\overrightarrow{a},\overrightarrow{b}\rangle
+\left|\overrightarrow{c}\right|\cos\langle\overrightarrow{a},\overrightarrow{c}\rangle\right)\overrightarrow{a_0}.
\end{aligned}'''
        text = book.edit(text, original, reflow, '教参分配律推导按等号换行，数学含义不变')
        book.EDITS[-1].update(source='teacher', source_lines=[213])
    return BASE_NORMALIZE(text, source)


def example(n):
    book.example(n, section='8.2')


def exercises(code, title):
    book.exercise_group(code, title, section='8.2')


def content():
    b, e = book.block, book.emphasize
    b('intro', '本节阅读主线', text='先分清“投影向量”与“数量投影”，再从做功情境进入数量积。通过投影的线性性质理解分配律，最后把模、夹角和垂直关系联结起来。教材保留原有次序，教参分析就近出现，超出本节的背景材料放在备课附记。', teacher_only=True)
    b('section', '向量的投影', id='projection', number='01', subtitle='投影是向量，数量投影是有正负的实数')
    b('prose', source='book', ranges=[(481, 487)])
    b('editor', '做功情境中的“大小”如何理解', text=r'原文在示意图情境下把 $|\overrightarrow{f}|\cos\theta$ 称为分力的“大小”。推广到钝角时，它是沿位移方向的有符号分量，可以为负；投影向量的模是 $|\overrightarrow{f}|\,|\cos\theta|$，不能为负。功也可以为负，不要把数量投影与长度混同。', teacher_only=True)
    projection = b('prose', source='book', ranges=[(491, 535)])
    e(projection, 'key-projection-definition', 'concept', '投影向量：投影两个端点，再确定方向',
      '如果向量', '\n\n![](images/book-bo_d4sllcbef24c73be0n80_13_210')
    e(projection, 'key-vector-angle', 'condition', '向量夹角：先把两个非零向量移到同一起点',
      '以一点 $O$', '\n\n![](images/book-bo_d4sllcbef24c73be0n80_13_604')
    e(projection, 'key-projection-formula', 'formula', '投影公式：目标方向必须由非零向量确定',
      '容易看出,', '\n\n在上式中')
    e(projection, 'key-signed-projection', 'concept', '数量投影有正负；它的绝对值才是投影的模',
      '在上式中,', '\n\n由投影的定义')
    b('teacher', '教参视角 · 为什么以投影向量为主线', source='teacher', ranges=[(180, 190)])
    example(1)
    example(2)
    linear = b('prose', source='book', ranges=[(549, 549)])
    e(linear, 'key-projection-linearity', 'method', '把“和”与“数乘”放在同一条投影主线')
    exercises('practice-1', '练习8.2（1）')

    b('section', '数量积的定义与运算律', id='product', number='02', subtitle='运算结果是实数；先核对运算类型，再迁移数的运算经验')
    definition = b('prose', source='book', ranges=[(573, 593)])
    e(definition, 'key-dot-definition', 'formula', '数量积：模长相乘，再乘夹角余弦',
      '模仿功的定义,', '\n\n数量积又称')
    e(definition, 'key-zero-dot', 'condition', '零向量单独规定：不需要给它指定一个夹角',
      '我们还规定零向量')
    b('teacher', '教参视角 · 参与运算与运算结果的类型', source='teacher', ranges=[(204, 208)])
    b('editor', '零向量与夹角公式的边界', text=r'上方教参将零向量的夹角表述为可取任意角，这是使数量积表达式相容的一种约定，不是由两条射线确定的几何夹角。本页不据此给零向量指定夹角：遇到零向量时直接使用数量积为 $0$ 的规定；反求夹角以及用夹角判断垂直时，先检查两个向量均非零。', teacher_only=True)
    example(3)
    laws = b('prose', source='book', ranges=[(613, 643)])
    e(laws, 'key-dot-laws', 'formula', '交换律、对数乘的结合律、对加法的分配律',
      '类比数的乘法', '\n\n证明(1)')
    e(laws, 'key-no-cancellation', 'condition', '不能照搬：数量积没有向量间的结合律，也不能消去',
      '对向量的数量积谈结合律', '\n\n(2)如果')
    b('teacher', '教参视角 · 分配律的投影依据', source='teacher', ranges=[(210, 228)])
    b('editor', '分配律：把未定义的夹角和循环推理都避开', text=r'''固定非零向量 $\overrightarrow{a}$，记其单位向量为 $\overrightarrow{a_0}$。把任意向量 $\overrightarrow{x}$ 在该方向上的投影写成 $p(\overrightarrow{x})\overrightarrow{a_0}$，其中 $p(\overrightarrow{0})=0$。由例2的投影等式，比较同一非零向量 $\overrightarrow{a_0}$ 的系数，得

$$p(\overrightarrow{b}+\overrightarrow{c})=p(\overrightarrow{b})+p(\overrightarrow{c}).$$

又由数量积定义及零向量的规定，对任意 $\overrightarrow{x}$ 都有 $\overrightarrow{a}\cdot\overrightarrow{x}=|\overrightarrow{a}|p(\overrightarrow{x})$。两边乘以 $|\overrightarrow{a}|$，即得分配律。这也覆盖 $\overrightarrow{b}$、$\overrightarrow{c}$ 或其和为零的情况；若 $\overrightarrow{a}=\overrightarrow{0}$，等式两边直接为零。不能在尚未证明分配律时，把“与一个和作数量积”直接展开；教参原式先合并为同一单位向量的倍数，或采用这里的系数论证，便无此问题。''', teacher_only=True)
    b('prose', source='book', ranges=[(645, 645)])
    example(4)
    b('prose', source='book', ranges=[(729, 729)])
    b('teacher', '教参视角 · 公式的教学地位与运算边界', source='teacher', ranges=[(230, 238)])
    geometry = b('prose', source='book', ranges=[(681, 695)])
    e(geometry, 'key-angle-formula', 'formula', '反求夹角：分母的两个模长均不能为零',
      '若 $', '\n\n在 8.3')
    e(geometry, 'key-dot-geometry', 'condition', '非零向量的垂直判定；不等式中的两类绝对值',
      '\n\n由向量的数量积的定义,')
    b('editor', '两个条件，不要在迁移时丢失', text=r'把 $\overrightarrow{a}\cdot\overrightarrow{b}=0$ 与“夹角为直角”互相转化时，明确限定两个向量非零。若采用零向量与任意向量正交的代数约定，也不能说零向量因此有一个确定的直角。式 $|\overrightarrow{a}\cdot\overrightarrow{b}|\leq |\overrightarrow{a}|\,|\overrightarrow{b}|$ 左端是实数的绝对值，右端是两个向量模长的乘积；含零向量时不等式及等号仍成立，而“同向或反向”的文字解释只用于两个非零向量。', teacher_only=True)
    example(5)
    example(6)
    exercises('practice-2', '练习8.2（2）')
    b('section', '课后习题', id='homework', number='03', subtitle='保留教材A、B组及小问顺序，不另行分级或改编')
    exercises('homework-a', '习题8.2 A组')
    exercises('homework-b', '习题8.2 B组')
    b('section', '备课附记与来源', id='sources', number='04', subtitle='教学重点、概念推广与课堂取舍', teacher_only=True)
    b('teacher', '本节教学重点', source='teacher', ranges=[(176, 176)])
    b('teacher', '背景阅读 · 从直线投影到平面投影', source='teacher', ranges=[(192, 202)])
    b('teacher', '注意事项', source='teacher', ranges=[(252, 256)])
    b('teacher', '教学建议', source='teacher', ranges=[(260, 270)])
    b('editor', '本节编辑与保留边界', text='本页整合教材8.2的概念、推导、6个例题和26道练习习题，保留教参的“证明略”“理由略”。恢复数量积点、删除确定的重复错误式等修改均写入编辑记录。教参背景中的空间、欧氏结构只供教师理解，不作为学生证明所需知识；本轮不提前展开8.3的坐标公式。', teacher_only=True)


def coverage():
    covered = {'book': set(), 'teacher': set()}
    for item in book.BLOCKS:
        for field in ['provenance', 'provenance_question', 'answer_provenance', 'analysis_provenance']:
            for ref in item.get(field, []):
                covered[ref['source']].update(range(ref['start'], ref['end'] + 1))
    ranges = {'book': (481, 806), 'teacher': (174, 270)}
    missing = {}
    for source, (a, z) in ranges.items():
        missing[source] = [{'line': i, 'text': line} for i in range(a, z + 1)
                           if (line := book.LINES[source][i - 1].strip())
                           and i not in covered[source]
                           and not re.match(r'^(#{1,6} |---$|B 组$)', line)]
    assert not any(missing.values()), missing
    return {'ranges': ranges, 'missing_substantive_lines': missing,
            'boundary': '教材标题重建为网页语义层级；旁注549与729分别归入相应例题之后；例题图按配对清单就近放置。'}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for path, expected in book.MANIFEST['source_hashes'].items():
        assert book.digest(path) == expected, 'Source drift: ' + path
    book.OUT = OUT
    book.BLOCKS.clear()
    book.ASSETS.clear()
    book.EDITS.clear()
    book.normalize = normalize
    content()
    report = coverage()
    options = dict(section='8.2', title='向量的数量积', cover_title='向量的<br>数量积',
                   deck='从投影出发，连接方向与数量。<br>用数量积刻画模、夹角和垂直关系。', knowledge_topics=2)
    for student in [False, True]:
        text = book.page(student, **options).replace('chengbai 数学讲义<br>', '')
        if not student:
            text = text.replace('<footer class="book-footer">', '<footer class="book-footer"><p><a href="../8.1-向量的概念和线性运算.html">← 上一节：8.1 向量的概念和线性运算</a></p>')
        (OUT / f'{STEM}{"-s" if student else ""}.html').write_text(text, encoding='utf-8')
    for name in ['book.css', 'book.js']:
        shutil.copy2(book.ROOT / 'scripts' / name, OUT / name)
    shutil.copytree(PARENT / 'vendor-katex', OUT / 'vendor-katex', dirs_exist_ok=True)
    (OUT / 'sources').mkdir(exist_ok=True)
    shutil.copy2(book.BOOK, OUT / 'sources/textbook-ch8.md')
    shutil.copy2(book.TEACHER, OUT / 'sources/teacher-ch8.md')
    (OUT / 'content').mkdir(exist_ok=True)
    (OUT / 'content/8.2-整合底稿.json').write_text(json.dumps(book.BLOCKS, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT / 'content/来源与编辑记录.json').write_text(json.dumps({
        'source_hashes': book.MANIFEST['source_hashes'], 'assets': book.ASSETS,
        'edits': book.EDITS, 'coverage': report}, ensure_ascii=False, indent=2), encoding='utf-8')
    student_html = (OUT / f'{STEM}-s.html').read_text(encoding='utf-8')
    images = set(re.findall(r'<img src="([^"]+)"', student_html))
    with zipfile.ZipFile(OUT / '8.2-学生阅读包.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in [f'{STEM}-s.html', 'book.css', 'book.js', *sorted(images)]:
            archive.write(OUT / name, name)
        for path in (OUT / 'vendor-katex').rglob('*'):
            if path.is_file():
                archive.write(path, path.relative_to(OUT))
    (OUT / 'verification').mkdir(exist_ok=True)
    summary = {'output': str(OUT), 'questions': sum(b['type'] == 'question' for b in book.BLOCKS),
               'assets': len(book.ASSETS), 'emphases': sum(len(b.get('emphases', [])) for b in book.BLOCKS),
               'coverage': report, 'edits': book.EDITS}
    (OUT / 'verification/build-report.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
