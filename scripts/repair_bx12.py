#!/usr/bin/env python3
"""Apply audited, replayable content repairs; original textbook sources stay read-only."""

from project_paths import use_project_root, launch_browser
use_project_root()
import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / 'batch/patches/repair-bx12-content.json'
REPORT = ROOT / 'batch/reviews/repair-bx12-content.json'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def build():
    edits = []
    for sid in ['bx1-2-2', 'bx1-chapter-end-5', 'bx2-6-1', 'bx2-7-1', 'bx2-chapter-end-7']:
        path = ROOT / 'batch/sections' / sid.split('-')[0] / (sid + '.json')
        before = json.loads(path.read_text(encoding='utf-8'))
        data = copy.deepcopy(before)
        # Preserve the renderer's previous default anchors before inserting any block.
        for index, block in enumerate(data['blocks']):
            block.setdefault('id', sid + '-b' + str(index))
        by_id = {b['id']: b for b in data['blocks']}
        notes = []

        def authored(qid, answer, reason, reference=None):
            b = by_id[qid]
            b['answer'] = '【编辑补写／校订】\n\n' + answer
            b['answer_provenance'] = []
            b['answer_editorial'] = {'kind': 'independently-derived', 'reason': reason,
                                     'source_reference': reference or [], 'review_status': 'pending-independent-review'}
            notes.append({'question_id': qid, 'action': 'author-or-correct', 'reason': reason})

        def matched(qid, start, end):
            b = by_id[qid]
            source = Path(data['sources']['teacher'])
            text = ''.join(source.read_text(encoding='utf-8').splitlines(keepends=True)[start-1:end]).strip()
            text = re.sub(r'(!\[[^\]]*\]\()([^\)]+)(\))',
                          lambda m: m[1] + str((source.parent / m[2]).resolve()) + m[3]
                          if not m[2].startswith(('/', 'http:', 'https:')) else m[0], text)
            b['answer'] = text
            b['answer_provenance'] = [{'source': 'teacher', 'start': start, 'end': end}]
            b['answer_editorial'] = {'kind': 'manual-source-match', 'reason': '逐题核对教材题面与教参实际内容，恢复因OCR题号缺失而停止的整组配对。'}
            notes.append({'question_id': qid, 'action': 'manual-source-match', 'teacher_lines': [start, end]})

        if sid == 'bx1-2-2':
            authored(sid+'-p222-1', r'''(1) $x^2+x+2=(x+\frac12)^2+\frac74>0$，解集为 $\mathbf R$。

(2) $-x^2+3x-4=-(x-\frac32)^2-\frac74<0$，解集为 $\varnothing$。

(3) $9x^2-6x+1=(3x-1)^2$，解集为 $(-\infty,\frac13)\cup(\frac13,+\infty)$。

(4) $4x-x^2-4=-(x-2)^2\le0$，解集为 $\varnothing$。

(5) $2x^2-x+1=2(x-\frac14)^2+\frac78>0$，解集为 $\mathbf R$。

(6) $x^2-\frac23x+\frac19=(x-\frac13)^2\ge0$，解集为 $\mathbf R$。''', '教参第662—664行缺题号和第(1)问，按完整题面补写六问。', [662,664])
            authored(sid+'-p222-2', r'''可分别写为：

(1) $x^2-6x+7<0$；(2) $x^2-6x+7\ge0$；

(3) $x^2+1>0$；(4) $x^2<0$。

前两式的左边为 $(x-3)^2-2$，零点为 $3\pm\sqrt2$；后二式分别对所有实数成立、对所有实数不成立。答案不唯一。''', '教参第666—668行缺主编号，依题面校订并补验解集。', [666,668])

        if sid == 'bx1-chapter-end-5':
            combined = by_id[sid+'-t-3']
            first, fourth = combined['markdown'].split('\n\n*4.', 1)
            combined['markdown'] = first
            combined['provenance'] = combined['provenance_question'] = [{'source':'book','start':1343,'end':1344}]
            q4 = copy.deepcopy(combined)
            q4.update(id=sid+'-t-4', title='拓展与思考 · *4', markdown='*4.'+fourth,
                      provenance=[{'source':'book','start':1345,'end':1349}],
                      provenance_question=[{'source':'book','start':1345,'end':1349}])
            position = data['blocks'].index(combined)
            data['blocks'].insert(position+1, q4)
            by_id[q4['id']] = q4
            notes.append({'action':'split-swallowed-starred-question','question_id':q4['id'], 'source_lines':[1345,1349]})
            authored(sid+'-t-1', r'''定义域为 $\mathbf R\setminus\{-1,1\}$，函数在 $(-\infty,-1)$、$(-1,1)$、$(1,+\infty)$ 上分别严格递增。

证明：在上述任一区间任取 $u<v$，则
$$f(v)-f(u)=\frac{(v-u)(1+uv)}{(1-u^2)(1-v^2)}.$$
同一区间内分母恒为正。在外侧两个区间，$uv>1$；在中间区间，$uv>-1$，故分子也为正。因此 $f(v)>f(u)$。三个区间不可跨越无定义点合并。''', '保留教参624行结论，补上必修阶段作差证明。', [624,624])
            matched(sid+'-t-2', 626,634)
            by_id[sid+'-t-2']['answer'] += r'''

【编辑补证】函数为偶函数，经过 $(0,0)$、$(\pm1,-1)$，两端趋于 $+\infty$。令 $u=x^2\ge0$，则 $y=(u-1)^2-1$ 在 $u\in[0,1]$ 上严格递减、在 $u\in[1,+\infty)$ 上严格递增；$x^2$ 在 $(-\infty,0]$ 上递减、在 $[0,+\infty)$ 上递增。按两个变化的方向复合，即得减区间 $(-\infty,-1]$、$[0,1]$，增区间 $[-1,0]$、$[1,+\infty)$，补全教参略去的其余三段证明。'''
            matched(sid+'-t-3', 636,636)
            by_id[sid+'-t-3']['answer'] += r'''

【编辑补证】将原式中的 $x$ 换为 $-x$，利用奇偶性得 $f(x)-g(x)=x^2+2|x+1|+3$。与原式相加、相减即得上述表达式，代回可验证成立。'''
            matched(sid+'-t-4', 638,644)

        if sid == 'bx2-6-1':
            authored(sid+'-h61A-1', r'''(1) D；(2) C；(3) C。

(1)同终边角相差 $360^\circ$ 的整数倍。A、B、C两角分别相差 $720^\circ$、$2160^\circ$、$1080^\circ$，D两角相差 $480^\circ$。

(2)相同始边且相等的角有相同终边；负角给出A的反例，$480^\circ$ 给出B的反例，$0^\circ$ 与 $360^\circ$ 给出D的反例。

(3)由 $0^\circ<\alpha<90^\circ$，得 $0^\circ<2\alpha<180^\circ$，但不能确定属于第一或第二象限，也可能恰为 $90^\circ$。''', '教参346行只存(2)(3)，补写第(1)问及判别依据。', [346,346])
            ranges={2:(348,348),3:(350,352),4:(354,354),5:(356,358),6:(360,360),7:(362,362),8:(364,366),9:(368,370),10:(372,374),11:(376,376),12:(378,378),13:(380,382),14:(384,384)}
            for n,(a,z) in ranges.items(): matched(sid+'-h61A-'+str(n),a,z)
            by_id[sid+'-h61A-3']['answer'] += r'''

【编辑补写第(4)问】$-216^\circ=-\frac{6\pi}{5}$，与 $144^\circ$ 终边重合，属于第二象限。'''
            # The sidebar beginning “例14(1)与(2)” is not a second exercise.
            duplicate = by_id[sid+'-ex-14-L495']
            duplicate.update(type='editor', title='例14侧注的编校说明', markdown='原OCR把“例14(1)与(2)中的公式……”侧注误识别为第二道例14。相关题面与证明已完整保留在前一题，本处不重复计为试题。', teacher_only=True)
            for field in ['answer','teacher_analysis','answer_provenance','analysis_provenance','category','provenance_question']:
                duplicate.pop(field,None)
            notes.append({'action':'remove-false-question-classification','question_id':duplicate['id'],'reason':'侧注重复，前一题已含(1)—(4)完整题面与证明。'})
            # This nearby teacher answer also lost one subquestion in OCR.
            partial = by_id[sid+'-p611-3']
            partial['answer'] = r'''【编辑校订】(1) $45^\circ$，第一象限；(2) $185.3^\circ$，第三象限；(3) $350^\circ$，第四象限；(4) $170^\circ$，第二象限。各角分别加减 $360^\circ$ 的整数倍化至 $[0^\circ,360^\circ)$。'''
            partial['answer_provenance'] = []
            partial['answer_editorial'] = {'kind':'independently-derived','source_reference':[270,273],'reason':'教参OCR漏第(2)问且第(1)问排版损坏。'}
            notes.append({'action':'complete-nearby-partial-answer','question_id':partial['id']})

        if sid == 'bx2-7-1':
            for n,(a,z) in {2:(320,320),3:(322,322),4:(324,330),6:(334,334),7:(336,338),8:(340,342),9:(344,344)}.items():
                matched(sid+'-h71A-'+str(n), a,z)
            authored(sid+'-h71A-1', r'''(1) 将 $y=\sin x$ 在 $[0,2\pi]$ 上的图像向上平移1个单位，依次描点 $(0,1)$、$(\frac\pi2,2)$、$(\pi,1)$、$(\frac{3\pi}2,0)$、$(2\pi,1)$，用正弦曲线平滑连接。

(2) 保留 $y=\sin x$ 在 $x$ 轴上方的部分，把下方的部分关于 $x$ 轴翻折。图像始终非负，每一段 $[k\pi,(k+1)\pi]$ 都是一条上拱的半波，端点值为0、中点值为1，最小正周期为 $\pi$，其中 $k\in\mathbf Z$。''', '教参318行仅写略，补足可以直接作图的关键点与变换。', [318,318])
            authored(sid+'-h71A-5', r'''(1) 奇函数。定义域为 $\mathbf R$，且 $f(-x)=2\sin x=-f(x)$。

(2) 偶函数。定义域为 $\mathbf R\setminus\{0\}$，关于原点对称，且 $f(-x)=\frac{-\sin x}{-x}=f(x)$。

(3) 非奇非偶。定义域为 $\mathbf R\setminus\{-\frac\pi2+2k\pi:k\in\mathbf Z\}$，不关于原点对称，例如 $\frac\pi2$ 在定义域内而 $-\frac\pi2$ 不在定义域内，因此不满足奇函数或偶函数的定义。''', '教参332行只保留第(3)问且丢主编号，补全定义域与三问理由。', [332,332])

        if sid == 'bx2-chapter-end-7':
            authored(sid+'-hA-1', r'''(1) $T=\frac{2\pi}{1/2}=4\pi$；(2) $T=\frac{2\pi}{3}$。相位平移和非零振幅不改变最小正周期。''', '教参462行缺主编号及第(1)问。', [462,462])
            authored(sid+'-hA-2', r'''(1) 偶函数，定义域为 $\mathbf R$，$f(-x)=\sin|{-2x}|=f(x)$。

(2) 奇函数，定义域为 $\mathbf R\setminus\{\frac\pi{10}+\frac{k\pi}{5}:k\in\mathbf Z\}$，关于原点对称，且 $\tan(-5x)=-\tan5x$。

(3) 偶函数，定义域为 $\mathbf R\setminus\{\frac\pi2+k\pi:k\in\mathbf Z\}$，关于原点对称，且 $1/\cos(-x)=1/\cos x$。

(4) 非奇非偶。$f(0)=1/2\ne0$，不可能是奇函数；$f(\pi/2)=\sqrt3/2$ 而 $f(-\pi/2)=-\sqrt3/2$，也不是偶函数。''', '教参464行只存第(4)问，补齐四问及定义域。', [464,464])
            for n,(a,z) in {3:(466,466),4:(468,474),6:(478,478),7:(480,486),8:(488,490)}.items():
                matched(sid+'-hA-'+str(n),a,z)
            authored(sid+'-hA-5', r'''令 $u=2x+\frac\pi3$，取 $u=0,\frac\pi2,\pi,\frac{3\pi}2,2\pi$，得到一周期内五个关键点：
$$(-\frac\pi6,0),\quad(\frac\pi{12},2),\quad(\frac\pi3,0),\quad(\frac{7\pi}{12},-2),\quad(\frac{5\pi}6,0).$$
按正弦曲线平滑连接，并以 $\pi$ 为周期向左右延伸。图像振幅为2，最小正周期为 $\pi$，相当于将 $y=2\sin2x$ 的图像向左平移 $\pi/6$。''', '教参476行只写略，补足五点作图和周期延拓说明。', [476,476])

        # Keep the old unpaired block/anchor but move the full original text to audit history.
        for b in data['blocks']:
            if '未配对参考答案原文' in b.get('title',''):
                b['title'] = b['title'].replace('未配对参考答案原文（题号异常）', '题答配对修订说明')
                b['markdown'] = '已按实际题面逐题恢复参考答案，并对缺失小问明确标注编辑补写。原始未配对内容及修订前底稿完整保存在本节修订记录与 repair-bx12-content.json 中，未改动来源文件。'
                b['type'] = 'editor'
                b['teacher_only'] = True
        original_issues = data['issues']
        data['issues'] = []
        data.setdefault('repair_history', []).append({'id':'repair-bx12-content-v1', 'original_issues':original_issues,
             'actions':notes, 'evidence':'batch/patches/repair-bx12-content.json',
             'scope':'只修复列明题答内容与假重复；不声称全节所有原答案已全面数学审定。'})
        edits.append({'section_id':sid, 'path':str(path.relative_to(ROOT)),
                      'before_sha256':digest(before), 'after_sha256':digest(data),
                      'before':before, 'after':data, 'actions':notes})
    return {'schema_version':1, 'patch_id':'repair-bx12-content-v1', 'sections':edits}


def main():
    PATCH.parent.mkdir(parents=True, exist_ok=True)
    if PATCH.exists():
        patch = json.loads(PATCH.read_text(encoding='utf-8'))
    else:
        patch = build()
        PATCH.write_text(json.dumps(patch, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    report=[]
    for entry in patch['sections']:
        path=ROOT/entry['path']
        current=json.loads(path.read_text(encoding='utf-8'))
        if digest(current)==entry['after_sha256']:
            status='already-applied'
        elif digest(current)==entry['before_sha256']:
            path.write_text(json.dumps(entry['after'],ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
            status='applied'
        else:
            raise RuntimeError(f'{path}: content drift; refusing to overwrite concurrent edits')
        data=entry['after']
        ids=[b['id'] for b in data['blocks']]
        assert len(ids)==len(set(ids)), entry['section_id']
        assert all(b.get('answer') for b in data['blocks'] if b['type']=='question')
        report.append({'section_id':entry['section_id'],'status':status,'actions':entry['actions'],
                       'question_count_before':sum(b['type']=='question' for b in entry['before']['blocks']),
                       'question_count_after':sum(b['type']=='question' for b in data['blocks']),
                       'blocking_before':len(entry['before']['issues']),'blocking_after':len(data['issues'])})
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps({'scope':'content-only', 'review_status':'pending-independent-review','sections':report},ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
