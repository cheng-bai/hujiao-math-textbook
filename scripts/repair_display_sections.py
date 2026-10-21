#!/usr/bin/env python3
"""Restore sample emphasis spans after image-link expansion; keep source text."""

from project_paths import use_project_root, launch_browser
use_project_root()
import copy
import json
from pathlib import Path

from batch_extract import approved_section

ROOT = Path(__file__).resolve().parents[1]


def main():
    changes = []
    staged = []
    for section in ('8.1', '8.2'):
        sid = 'bx2-' + section.replace('.', '-')
        path = ROOT / 'batch/sections/bx2' / (sid + '.json')
        data = json.loads(path.read_text(encoding='utf-8'))
        approved = approved_section(section)
        for index, block in enumerate(data['blocks']):
            if not block.get('emphases'):
                continue
            candidates = [b for b in approved if b.get('markdown') == block['markdown']
                          and b.get('emphases')]
            assert len(candidates) == 1, (sid, index)
            marks = candidates[0]['emphases']
            if block['emphases'] != marks:
                changes.append({'sectionId': sid, 'blockIndex': index,
                                'before': copy.deepcopy(block['emphases']),
                                'after': copy.deepcopy(marks),
                                'reason': 'Rebase emphasis offsets after sample image URLs become absolute; no prose or formula edits.'})
                block['emphases'] = copy.deepcopy(marks)
        staged.append((path, json.dumps(data, ensure_ascii=False, indent=2) + '\n'))
    evidence = ROOT / 'batch/patches/repair-display-emphases.json'
    if changes:
        assert not evidence.exists(), 'Keep the original before/after evidence'
        evidence.write_text(json.dumps(changes, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        for path, payload in staged:
            path.write_text(payload, encoding='utf-8')
    print(json.dumps({'changedBlocks': len(changes)}))


if __name__ == '__main__':
    main()
