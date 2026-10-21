#!/usr/bin/env python3
"""Replay narrowly scoped editorial repairs; original source files stay read-only."""

from project_paths import use_project_root, launch_browser
use_project_root()
import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / 'batch/patches/repair-bx3-before.json'
REPORT = ROOT / 'batch/reviews/repair-bx3-evidence.json'
IDS = ['bx3-10-1', 'bx3-10-3', 'bx3-12-1', 'bx3-12-3',
       'bx3-chapter-end-12', 'bx3-13-1', 'bx3-13-2', 'bx3-13-3', 'bx3-13-5']
TAG = 'repair-bx3-v1'


def digest(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def line_ref(source, start, end):
    return [{'source': source, 'start': start, 'end': end}]


def set_answer(block, text, provenance=None, authored=False):
    block['answer'] = ('【编辑补写】\n\n' if authored else '') + text
    block['answer_provenance'] = provenance or []
    if authored:
        block['editorial_answer'] = {'status': 'authored', 'by': TAG,
                                     'basis': copy.deepcopy(block.get('provenance_question', []))}


def questionize(block, category, title):
    block.update(type='question', category=category, title=title,
                 provenance_question=copy.deepcopy(block['provenance']),
                 answer='', answer_provenance=[], teacher_analysis='', analysis_provenance=[])
    block.pop('teacher_only', None)


def by_id(data, qid):
    return next(b for b in data['blocks'] if b.get('id') == qid)


def restore_group(data, category):
    archive = next(b for b in data['blocks']
                   if b.get('title', '').startswith(category + ' · 未配对'))
    text = archive['markdown']
    # Original references may put several numbered answers on one line.
    pieces = re.split(r'(?<![\d.])(?=[1-9]\.\s*(?:[$(（]|[A-Z\u4e00-\u9fff]))', text)
    parsed = {}
    for piece in pieces:
        m = re.match(r'(\d+)\.(.*)', piece, re.S)
        if m:
            parsed[int(m[1])] = piece.strip()
    # Use line-leading numbered boundaries for multi-paragraph geometry proofs.
    if category == '习题10.1B':
        pieces = re.split(r'\n\n(?=\d+\.)', text)
        parsed = {int(re.match(r'(\d+)\.', p)[1]): p.strip() for p in pieces}
    for q in data['blocks']:
        if q.get('category') != category:
            continue
        n = int(q['title'].split(' · ')[-1])
        if n in parsed:
            set_answer(q, parsed[n], archive['provenance'])
    archive['title'] = category + ' · 原始参考答案留存（已人工归位）'
    archive['editorial_note'] = '原稿留存用于复核；各题答案已按题意逐题配对，不再作为未归属内容。'


def detach_example(data, phrase, title):
    ai = next(i for i, b in enumerate(data['blocks'])
              if b.get('title') == '教材证明或前置解答 · 待边界复核')
    prose, answer = data['blocks'][ai - 1:ai + 1]
    at = prose['markdown'].index(phrase)
    stem = prose['markdown'][at:].strip()
    source_lines = Path(data['sources']['book']).read_text(encoding='utf-8').splitlines()
    start = next(i + 1 for i, line in enumerate(source_lines) if line.startswith(phrase))
    end = prose['provenance'][-1]['end']
    prose['markdown'] = prose['markdown'][:at].rstrip()
    prose['provenance'][-1]['end'] = start - 1
    if 'emphases' in prose:
        prose['emphases'] = [e for e in prose['emphases'] if e['end'] <= len(prose['markdown'])]
    old_answer, old_ref = answer['markdown'], copy.deepcopy(answer['provenance'])
    answer['markdown'] = stem
    answer['provenance'] = line_ref('book', start, end)
    questionize(answer, '例题', title)
    set_answer(answer, old_answer, old_ref)


def repair(data):
    sid = data['id']
    for i, block in enumerate(data['blocks']):
        block.setdefault('id', sid + f'-b{i}')
    if sid == 'bx3-10-1':
        q = data['blocks'][43]
        questionize(q, '习题10.1B', '习题10.1B · 1')
        # The OCR joined the exercise number to the opening number.
        q['editorial_original_markdown'] = q['markdown']
        q['markdown'] = q['markdown'].replace('1.1 个平面', '1. 1 个平面', 1)
        restore_group(data, '习题10.1B')
        set_answer(q, r'''三个不同平面可把空间分成 $4,6,7,8$ 部分。

第三个平面若与前两个平面都平行，就新增一个区域，共有 $4$ 个区域；三个平面中恰有两个平行时，第三个平面横截它们，共有 $6$ 个区域；三平面共一条交线时，共有 $6$ 个区域；三平面两两相交且三条交线互相平行而不重合时，共有 $7$ 个区域；三平面两两相交且三条不同交线交于一点时，共有 $8$ 个区域。

也可统一计数：加入第三个平面时，它与前两个平面的交线在该平面内把它分成几部分，空间就新增几部分。前两平面平行时，原有 $3$ 区，新增 $1$ 或 $3$ 区；前两平面相交时，原有 $4$ 区，新增 $2,3,4$ 区。于是只有上述四种结果。''', authored=True)
    elif sid == 'bx3-10-3':
        p = data['blocks'][4]
        at = p['markdown'].index('证明 如图 10-3-2')
        answer = p['markdown'][at:].strip()
        p['markdown'] = p['markdown'][:at].rstrip()
        p['provenance'][-1]['end'] = 752
        q = by_id(data, 'bx3-10-3-ex-1')
        set_answer(q, answer, line_ref('book', 753, 758))
        q['teacher_analysis'] = '编辑归位：原OCR把本例证明排在题干之前；依题设及同名点线关系恢复归属。原图与图号均保留。'
        q = by_id(data, 'bx3-10-3-ex-6')
        at = q['markdown'].index('(1)因为')
        tail = q['markdown'][at:]
        image_at = tail.index('![')
        proof, diagram = tail[:image_at].strip(), tail[image_at:].strip()
        q['markdown'] = q['markdown'][:at].rstrip() + '\n\n' + diagram
        q['answer'] = q['answer'].replace('\n\n(2)', '\n\n' + proof + '\n\n(2)', 1)
        q['answer_provenance'].insert(0, line_ref('book', 1005, 1006)[0])
        q['editorial_boundary_note'] = '将误混入题干的(1)证明移回答案；保留题设、图形和完整原解。'
        # OCR reading order put each next-example diagram before its actual stem.
        q1, q2 = by_id(data, 'bx3-10-3-ex-1'), by_id(data, 'bx3-10-3-ex-2')
        at = q1['markdown'].index('\n\n![')
        figure3 = q1['markdown'][at:]
        q1['markdown'] = q1['markdown'][:at]
        at = q1['answer'].index('\n\n![')
        figure2 = q1['answer'][at:]
        q1['answer'] = q1['answer'][:at]
        q1['markdown'] += figure2
        q2['markdown'] += figure3
        q1['provenance'] = q1['provenance_question'] = line_ref('book', 759, 760) + line_ref('book', 755, 758)
        q1['answer_provenance'] = line_ref('book', 753, 754)
        q2['provenance'] = q2['provenance_question'] = line_ref('book', 765, 770) + line_ref('book', 761, 764)
        q1['teacher_analysis'] = '【编辑归位】原OCR把本例证明及图10-3-2排在题干之前，现将长方体图移至例1题干，证明归入例1答案；误附的空间四边形图10-3-3转归例2。图像、图号与来源原件未改。'
        q2['teacher_analysis'] = '【编辑图属校注】图10-3-3中的空间四边形ABCD及中点E、F对应本例，现从例1题干移来；保留原图与原图号。'
        q6, q7 = by_id(data, 'bx3-10-3-ex-6'), by_id(data, 'bx3-10-3-ex-7')
        at = q6['answer'].index('\n\n![')
        figure17 = q6['answer'][at:]
        q6['answer'] = q6['answer'][:at]
        q7['markdown'] += figure17
        q6['answer_provenance'] = line_ref('book', 1005, 1006) + line_ref('book', 1011, 1014)
        q7['provenance'] = q7['provenance_question'] = copy.deepcopy(q7['provenance_question']) + line_ref('book', 1015, 1018)
        q6['teacher_analysis'] = '【编辑图属校注】本例使用图10-3-16的P、O、A、B及垂线段/斜线段。误收在本例答案尾部的图10-3-17涉及l、投影及夹角，已归入例7题干；原图与图号未改。'
        q7['teacher_analysis'] = '【编辑图属校注】图10-3-17中的l、投影l′、另一条平面直线l″及θ、μ对应本例，现移至本题题干，学生可见；保留原图与原图号。'
        original_q7_answer = q7['answer']
        q7['answer'] = r'''【编辑补证：角度边界】题中 $l$ 是平面 $\alpha$ 的斜线，即它与平面相交但不垂直于平面，故它与投影所成的角满足 $0<\theta<\frac\pi2$，不包含 $\theta=0$ 或 $\theta=\frac\pi2$。$l$ 与平面内过 $O$ 的直线 $l^{\prime\prime}$ 不重合，所以两直线所成的角满足 $0<\mu\le\frac\pi2$。

若 $\mu=\frac\pi2$，直接由 $\theta<\frac\pi2=\mu$ 得结论。此时原解中从 $A$ 向 $l^{\prime\prime}$ 作垂线的垂足 $C$ 就是 $O$，不能把 $\triangle ACO$ 当作非退化直角三角形。下列原解的三角形比较步骤只用于余下的 $0<\mu<\frac\pi2$ 情形；此时 $\theta,\mu$ 都在正弦函数的严格增区间内，推理成立。这样两种情形覆盖了题面允许的全部角度。

【教材原解（保留）】

''' + original_q7_answer
        q7['editorial_boundary_note'] = '在answer中补齐μ=90°的直接证明；由斜线定义明确0<θ<90°。原解完整保留，非退化三角形证明限定μ为锐角。'
    elif sid == 'bx3-12-1':
        restore_group(data, '习题12.1A')
        set_answer(by_id(data, sid + '-h121A-1'),
                   '(1)是确定的事件（必然事件）；(2)(3)是不确定的事件（随机事件）。在通常地面环境下石块必下落；是否接到推销电话、彩票是否中奖事先不能确定。', authored=True)
    elif sid == 'bx3-12-3':
        detach_example(data, '例 某药物公司', '例题 · 新药试验的经验概率')
    elif sid == 'bx3-13-1':
        detach_example(data, '例 为客观了解', '例题 · 家庭存书量调查')
    elif sid == 'bx3-13-5':
        detach_example(data, '例 2 为了解某体校', '例题 2')
    elif sid == 'bx3-13-2':
        restore_group(data, '练习13.2')
        set_answer(by_id(data, sid + '-p132-1'),
                   '(1)观测数据；(2)观测数据；(3)实验数据。计算机水平测试用来测量已有水平，旅游偏好调查记录已有意愿；新型除草剂的检测是在施用药剂后研究其效果，研究者施加了处理。', authored=True)
        set_answer(by_id(data, sid + '-p132-3'),
                   '示例：调查本校高一年级学生每天的课外阅读时长。总体是该校高一年级全体学生每天的课外阅读时长，样本是随机抽取的学生对应的阅读时长。可按班级人数比例分层，在各班随机抽人，统一记录同一周的日均时长。这样可避免只调查阅读兴趣小组或某一个班造成的明显偏向；仍应检查未应答及自报误差，不能把随机抽样等同于必然具有代表性。', authored=True)
    elif sid == 'bx3-13-3':
        q = by_id(data, sid + '-p1331-1')
        set_answer(q, '(1)不是。参加问卷由客户自愿选择，各客户被选入的机会不一定相同。\n\n(2)不是本节所指的不放回简单随机抽样。同一个零件可能被重复抽取，10次检验不保证得到10个不同的样本个体。这里应区别“有放回随机抽取”与本节抽取不同个体组成样本的要求。', line_ref('teacher', 412, 412))
        q['editorial_answer'] = {'status': 'expanded', 'by': TAG, 'note': '依据教参判断补足理由'}
        q = by_id(data, sid + '-p1331-2')
        set_answer(q, '可自选10首歌曲，依次编号1至10。例如《茉莉花》《小星星》《送别》《童年》《歌声与微笑》《让我们荡起双桨》《春天在哪里》《蜗牛与黄鹂鸟》《外婆的澎湖湾》《明天会更好》。把10个编号写在外观相同的号签上，放入容器混合均匀，每次不放回地抽1张，连续抽3次；所得编号对应的3首歌曲就是所抽样本。抽取结果并不唯一，不能预先指定某3首必被抽中。', line_ref('teacher', 414, 414), authored=True)
        set_answer(by_id(data, sid + '-p1331-3'), r'''把水笔编号为 $001,002,\ldots,500$。从随机数表中随机选定起点和阅读方向，按三位一组读取：保留 $001$ 至 $500$ 的编号，舍去 $000$、大于 $500$ 的数及已保留的重复编号，直到得到10个不同编号。对应的10支水笔即为样本。

也可用计算机产生同样的均匀随机数，按上述规则拒绝无效与重复编号。每一步对尚未入选的编号一视同仁，因而不会因舍弃重复编号而偏向某支水笔。抽取结果具有随机性，不存在唯一正确的10个编号。''', authored=True)
    elif sid == 'bx3-chapter-end-12':
        restore_group(data, '复习题B')
        answers = {
            1: r'两道题的选项对共有 $4\times4=16$ 种等可能结果，每道题有3个错误选项，故都错的结果有 $3\times3=9$ 种，所求概率为 $\frac9{16}$。',
            2: r'按先后顺序共有 $3\times3=9$ 种等可能结果。十位确定后，个位有2种不同的选择，故符合条件的结果有 $3\times2=6$ 种，所求概率为 $\frac69=\frac23$。',
            3: r'''(1)一次抽取3张共有4种等可能组合：$\{1,2,3\},\{1,2,4\},\{1,3,4\},\{2,3,4\}$，和依次为 $6,7,8,9$。其中2种的和大于7，所求概率为 $\frac24=\frac12$。

(2)有放回抽取，按先后顺序共有 $4\times4=16$ 种等可能结果。两数之和大于7仅有 $(4,4)$ 一种，故所求概率为 $\frac1{16}$。''',
            4: r'''若仅按互斥事件加法公式作形式运算，“两粒都是黑子”与“两粒都是白子”的并是“同一颜色”，于是得到原题预期值 $\frac17+\frac16=\frac{13}{42}$。

【编辑校注：原题数据存在模型冲突】在通常的有限盒中不放回任取两粒的模型下，实际上不存在满足这两个概率条件的黑白棋子数量，不能把上面的形式运算值当作可实现模型的概率。

设黑、白棋子数分别为 $b,w$，总数为 $n=b+w$。因两种同色事件的概率均为正，故 $b,w\ge2$，从而 $n\ge4$。同色概率应为
$$P=\frac{b(b-1)+w(w-1)}{n(n-1)}.$$
由 $(b-w)^2\ge0$ 得 $b^2+w^2\ge n^2/2$，因此
$$P\ge\frac{n^2/2-n}{n(n-1)}=\frac{n-2}{2(n-1)}\ge\frac13,$$
最后一个不等式等价于 $n\ge4$。但题设相加所得 $13/42<1/3$，矛盾。

综上，$13/42$ 是题设数值相加的预期形式答案；原题的两项概率不能同时来自所描述的有限黑白棋子盒。此处保留原题与预期值，并标明数据冲突，不擅改任一分数。'''
        }
        for n, text in answers.items():
            set_answer(by_id(data, sid + f'-hB-{n}'), text, authored=True)
        by_id(data, sid + '-hB-4')['editorial_conflict'] = {
            'kind': 'source-model-inconsistency', 'status': 'disclosed-with-proof',
            'formal_expected_answer': '13/42',
            'reason': 'Finite black-white population with both colors at least 2 has same-color probability at least 1/3.',
            'source_question_preserved': True,
        }
    old_issues = copy.deepcopy(data['issues'])
    data['issues'] = []
    data.setdefault('editorial_repairs', []).append({'id': TAG, 'resolved_issues': old_issues,
        'note': '人工依据题意、相邻源行与教参复配；缺失内容显式标为编辑补写。原来源未改。'})


def main():
    PATCH.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    if PATCH.exists():
        before = json.loads(PATCH.read_text(encoding='utf-8'))
    else:
        before = {sid: json.loads((ROOT / f'batch/sections/bx3/{sid}.json').read_text(encoding='utf-8')) for sid in IDS}
        PATCH.write_text(json.dumps(before, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    evidence = []
    for sid in IDS:
        data = copy.deepcopy(before[sid])
        repair(data)
        path = ROOT / f'batch/sections/bx3/{sid}.json'
        current = json.loads(path.read_text(encoding='utf-8'))
        admissible = {digest(before[sid]), digest(data)}
        for previous_path in (ROOT / 'batch/patches').glob('repair-bx3-v*-applied-shas.json'):
            admissible.add(json.loads(previous_path.read_text(encoding='utf-8')).get(sid))
        if digest(current) not in admissible:
            raise RuntimeError(f'Unexpected concurrent edit: {sid}; refusing to overwrite')
        assert len({b['id'] for b in data['blocks']}) == len(data['blocks'])
        assert all(q.get('answer') for q in data['blocks'] if q['type'] == 'question')
        assert data['source_hashes'] == before[sid]['source_hashes']
        for source, expected in data['source_hashes'].items():
            assert hashlib.sha256(Path(source).read_bytes()).hexdigest() == expected, source
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        changes = []
        old_by_id = {b.get('id', sid + f'-b{i}'): b for i, b in enumerate(before[sid]['blocks'])}
        for b in data['blocks']:
            old = old_by_id[b['id']]
            fields = [k for k in set(b) | set(old) if k != 'id' and b.get(k) != old.get(k)]
            if fields:
                changes.append({'block': b['id'], 'fields': sorted(fields), 'before': old, 'after': b})
        evidence.append({'section': sid, 'issues_before': before[sid]['issues'], 'issues_after': data['issues'],
                         'questions_before': sum(b['type'] == 'question' for b in before[sid]['blocks']),
                         'questions_after': sum(b['type'] == 'question' for b in data['blocks']),
                         'source_hashes_unchanged': True, 'changes': changes})
    REPORT.write_text(json.dumps({'repair': TAG, 'sections': evidence}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'sections': len(evidence), 'resolved_issue_count': sum(len(e['issues_before']) for e in evidence),
                      'report': str(REPORT)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
