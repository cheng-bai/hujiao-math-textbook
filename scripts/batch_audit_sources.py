#!/usr/bin/env python3
"""Audit chapter-level source retention, independently of the extraction parser."""

from project_paths import use_project_root, launch_browser
use_project_root()
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def normalize(text):
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', 'IMAGE', text)
    return re.sub(r'\s+', '', text)


def main():
    catalog = json.loads((ROOT / 'batch/manifests/catalog.json').read_text(encoding='utf-8'))
    result = {'scope': 'Original nonempty textbook lines, source-reference bounds, source hashes, stable question IDs. Not mathematical review or classification correctness.', 'chapters': []}
    for book in catalog['books']:
        for chapter in book['chapters']:
            models = [json.loads((ROOT / s['path']).read_text(encoding='utf-8')) for s in chapter['sections']]
            sources = models[0]['sources']
            original = {kind: Path(path).read_text(encoding='utf-8').splitlines() for kind, path in sources.items()}
            coverage, content, bounds, ids = defaultdict(set), defaultdict(str), [], []
            model_hashes = {}
            for section, model in zip(chapter['sections'], models):
                model_hashes[section['id']] = hashlib.sha256((ROOT / section['path']).read_bytes()).hexdigest()
                for block in model['blocks']:
                    if block['type'] == 'question':
                        ids.append(block['id'])
                    fields = [('markdown', 'provenance_question' if block['type'] == 'question' else 'provenance'), ('answer', 'answer_provenance'), ('teacher_analysis', 'analysis_provenance')]
                    for field, provenance in fields:
                        refs = block.get(provenance, [])
                        for ref in refs:
                            kind, a, b = ref['source'], ref['start'], ref['end']
                            if kind not in original or a < 1 or b > len(original[kind]) or a > b:
                                bounds.append({'section': section['id'], 'ref': ref})
                                continue
                            coverage[kind].update(range(a, b+1))
                            content[kind] += normalize(block.get(field, '')) + '\n'
            missing = []
            altered = []
            for i, line in enumerate(original['book'], 1):
                value = normalize(line)
                if not value or re.match(r'^(?:#{1,6}|---+$)', value):
                    continue
                if i not in coverage['book']:
                    missing.append(i)
                elif value not in content['book']:
                    altered.append({'line': i, 'excerpt': line[:100]})
            row = {'id': chapter['id'], 'book_id': book['id'], 'model_hashes': model_hashes, 'questions': len(ids), 'unique_ids': len(set(ids)), 'source_reference_bounds_errors': bounds, 'uncovered_book_lines': missing, 'book_lines_requiring_manual_comparison': altered, 'source_hashes_current': all(Path(p).is_file() and hashlib.sha256(Path(p).read_bytes()).hexdigest() == expected for model in models for p,expected in model['source_hashes'].items()), 'limits': ['A source-span being retained does not prove the correct public/answer role.', 'Explicit OCR repairs and curated accepted samples can cause legitimate line-level differences.']}
            result['chapters'].append(row)
    output = ROOT / 'batch/state/source-retention-audit.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'chapters': len(result['chapters']), 'questions': sum(r['questions'] for r in result['chapters']), 'uncovered_lines': sum(len(r['uncovered_book_lines']) for r in result['chapters']), 'manual_comparisons': sum(len(r['book_lines_requiring_manual_comparison']) for r in result['chapters']), 'reference_errors': sum(len(r['source_reference_bounds_errors']) for r in result['chapters']), 'duplicate_ids': sum(r['questions']-r['unique_ids'] for r in result['chapters'])},ensure_ascii=False))


if __name__ == '__main__':
    main()
