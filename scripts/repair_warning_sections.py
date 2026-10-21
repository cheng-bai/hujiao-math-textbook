#!/usr/bin/env python3
"""Repair exactly two documented nonblocking content/render warnings."""

from project_paths import use_project_root, launch_browser
use_project_root()
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / 'batch/patches/repair-warnings-v1.json'
REPORT = ROOT / 'batch/reviews/repair-warnings-author.json'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def build():
    files = []
    for sid in ['x1-4-4', 'bx2-7-3']:
        path = ROOT / 'batch/sections' / sid.split('-')[0] / (sid + '.json')
        before = json.loads(path.read_text(encoding='utf-8'))
        data = copy.deepcopy(before)
        for i, block in enumerate(data['blocks']):
            block.setdefault('id', sid + f'-b{i}')
        if sid == 'x1-4-4':
            q = next(b for b in data['blocks'] if b.get('id') == 'x1-4-4-p441-1')
            q['editor_original_answer'] = q['answer']
            original_first = q['answer'].split('\n\n(2)', 1)[0]
            q['answer'] = original_first + r'''

(2)【编辑补全原教参残句】原教参指出递推论证未使用归纳假设，随后止于“这意味”，此处据完整题面补全并说明逻辑边界：题中的步骤直接调用等比数列求和公式，没有展示怎样从 $n=k$ 时的等式递推到 $n=k+1$ 时的等式。若该求和公式已经独立证明，所列计算本身正确，可构成直接证明，不能只因没有使用归纳假设就说结论错误；但若正在用数学归纳法证明这一求和公式，就不能再把待证公式作为依据。

按题目要求写出归纳递推，应由归纳假设得到
$$
1+2+2^2+\cdots+2^{k-1}+2^k
=(2^k-1)+2^k=2^{k+1}-1.
$$
这里把前 $k$ 项的和替换为 $2^k-1$，才明确使用了归纳假设。结合已验证的 $n=1$，便完成数学归纳法证明。'''
            q['answer_editorial'] = {
                'kind': 'source-fragment-completed',
                'reason': '教参510行以“这意味”结束；按原题补全递推并区分直接证明与归纳证明。',
                'original_preserved_field': 'editor_original_answer',
            }
            resolved = [i for i in data['issues'] if i.get('code') == 'source-answer-sentence-truncated']
            data['issues'] = [i for i in data['issues'] if i.get('code') != 'source-answer-sentence-truncated']
            action = '补全数学归纳法残句；保留原教参参考记录，并明确已知求和公式的直接证明不等于错误证明。'
        else:
            original_title = data['title']
            data['editor_original_title'] = original_title
            data['title'] = '正弦型函数的图像'
            section = data['blocks'][0]
            assert section['type'] == 'section'
            section['editor_original_title'] = section['title']
            section['title'] = data['title']
            # Section titles are plain-text UI fields; preserve the full mathematical
            # title in a public Markdown block handled by the existing math renderer.
            # The existing concept block is a visualization SHA target. Keep its
            # original object and index, including its implicit renderer ID.
            data['blocks'][2] = copy.deepcopy(before['blocks'][2])
            data['blocks'].insert(3, {
                'id': sid + '-repair-math-title', 'type': 'prose', 'title': '',
                'markdown': '**原教材节题：** ' + original_title,
                'provenance': copy.deepcopy(section['provenance']),
                'editorial_note': '数学题名移入已有公式渲染通道；原教材题名及全部数学内容未改。',
            })
            resolved = [{'code': 'visible-dollar-delimiters', 'severity': 'warning',
                         'cause': 'section title is an escaped plain-text UI field, not a multiline delimiter error',
                         'previous_count_each_edition': 2}]
            action = 'UI节标题采用同义纯文字，完整原题名以公共Markdown公式呈现；既有正文和可视化锚点不动。'
        data.setdefault('repair_history', []).append({
            'id': 'repair-warnings-v1', 'action': action, 'resolved_warnings': resolved,
            'evidence': 'batch/patches/repair-warnings-v1.json',
        })
        files.append({'path': str(path.relative_to(ROOT)), 'before': before, 'after': data,
                      'before_sha256': digest(before), 'after_sha256': digest(data), 'action': action})
    return {'id': 'repair-warnings-v1', 'files': files}


def main():
    PATCH.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    patch = json.loads(PATCH.read_text(encoding='utf-8')) if PATCH.exists() else build()
    if not PATCH.exists():
        PATCH.write_text(json.dumps(patch, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report = []
    for entry in patch['files']:
        path = ROOT / entry['path']
        current = json.loads(path.read_text(encoding='utf-8'))
        known = {entry['before_sha256'], entry['after_sha256'], *entry.get('superseded_after_sha256', [])}
        if digest(current) not in known:
            raise RuntimeError(f'Concurrent edit detected: {path}')
        after = entry['after'];sid = after['id']
        old_ids = {b.get('id', sid + f'-b{i}') for i,b in enumerate(entry['before']['blocks'])}
        new_ids = [b.get('id', sid + f'-b{i}') for i,b in enumerate(after['blocks'])]
        assert old_ids <= set(new_ids) and len(new_ids) == len(set(new_ids))
        if sid == 'bx2-7-3':
            assert after['blocks'][2] == entry['before']['blocks'][2]
            concept_sha = hashlib.sha256(json.dumps(after['blocks'][2], ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
            assert concept_sha == 'ae17064108d977a9362009b3c3e56ee35789c604bce45cdb89fbc3a94a390e7b'
        assert after['source_hashes'] == entry['before']['source_hashes']
        for source, sha in after['source_hashes'].items():
            assert hashlib.sha256(Path(source).read_bytes()).hexdigest() == sha
        path.write_text(json.dumps(after, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        report.append({'section': sid, 'action': entry['action'], 'source_hashes_unchanged': True,
                       'old_ids_preserved': True, 'after_sha256': entry['after_sha256']})
    REPORT.write_text(json.dumps({'status': 'awaiting-independent-and-final-render-verification',
                                 'sections': report}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
