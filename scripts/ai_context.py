#!/usr/bin/env python3
"""Read-only, dependency-free task routing. Never execute the suggested commands."""

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import string
import sys

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = 'architecture/task-map.json'
TOKENS = {'section_id', 'book_id', 'section_path', 'output_dir'}
PATH_FIELDS = ('read', 'edit', 'outputs')
TEXT_FIELDS = ('commands', 'checks', 'warnings')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def relative_path(root, value):
    """Reject escaping paths on both POSIX and Windows, including symlinks."""
    path = PurePosixPath(value)
    if not value or '\\' in value or ':' in value or path.is_absolute() or '..' in path.parts:
        raise ValueError(f'not a safe project-relative path: {value}')
    resolved = (root / value).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f'path escapes project: {value}')
    return resolved


def section_context(root, section_id):
    if not re.fullmatch(r'(?:bx[123]|x[12])-[a-z0-9-]+', section_id):
        raise ValueError('invalid section ID')
    catalog = read_json(root / 'batch/manifests/catalog.json')
    matches = [(book, section) for book in catalog['books']
               for chapter in book['chapters'] for section in chapter['sections']
               if section['id'] == section_id]
    if len(matches) != 1:
        raise ValueError(f'section must match exactly one catalogue entry: {section_id}')
    book, section = matches[0]
    path = section['path']
    if book['id'] not in {'bx1', 'bx2', 'bx3', 'x1', 'x2'} or path != f"batch/sections/{book['id']}/{section_id}.json":
        raise ValueError('section path does not match its catalogue identity')
    if not relative_path(root, path).is_file():
        raise ValueError(f'section file missing: {path}')
    return {'section_id': section_id, 'book_id': book['id'], 'section_path': path,
            'output_dir': f"outputs/五册教材教参整合/{book['id']}/{section_id}"}


def expand(value, context):
    parts = list(string.Formatter().parse(value))
    if any(spec or conversion for _, _, spec, conversion in parts):
        raise ValueError('format modifiers are not supported')
    fields = {field for _, field, _, _ in parts if field is not None}
    if not fields.issubset(TOKENS):
        raise ValueError(f'unknown placeholders: {sorted(fields - TOKENS)}')
    if not fields.issubset(context):
        raise ValueError('this route needs --section')
    return value.format_map(context)


def validate_map(root, data):
    if data.get('schema_version') != 1 or not isinstance(data.get('routes'), dict) or not data['routes']:
        raise ValueError('unsupported or empty task map')
    for field in ('entrypoints', 'readonly_inputs', 'generated_outputs'):
        for value in data[field]:
            if not relative_path(root, value).exists():
                raise ValueError(f'mapped path missing: {value}')
    if not relative_path(root, data['source_of_truth']).is_dir():
        raise ValueError('source_of_truth is not a directory')
    sample = section_context(root, 'x1-2-2')
    for name, route in data['routes'].items():
        if not re.fullmatch(r'[a-z][a-z-]*', name):
            raise ValueError(f'invalid route ID: {name}')
        if not isinstance(route['requires_section'], bool) or not route['title'] or not route['scope']:
            raise ValueError(f'invalid route header: {name}')
        for field in PATH_FIELDS + TEXT_FIELDS:
            if not isinstance(route[field], list) or any(not isinstance(v, str) or not v for v in route[field]):
                raise ValueError(f'invalid {name}.{field}')
            for value in route[field]:
                expanded = expand(value, sample)
                if field in PATH_FIELDS:
                    path = relative_path(root, expanded)
                    if field != 'outputs' and not path.exists():
                        raise ValueError(f'mapped path missing: {expanded}')
        if not route['requires_section']:
            for field in PATH_FIELDS + TEXT_FIELDS:
                for value in route[field]:
                    expand(value, {})


def plan(root, data, task, section_id=None):
    if task not in data['routes']:
        raise ValueError(f'unknown task: {task}')
    route = data['routes'][task]
    if route['requires_section'] and not section_id:
        raise ValueError(f'task {task} requires --section')
    context = section_context(root, section_id) if section_id else {}
    result = {'task': task, 'title': route['title'], 'scope': route['scope'],
              'section_id': section_id, 'readonly': True,
              'notice': data['purpose'], 'entrypoints': data['entrypoints'],
              'source_of_truth': data['source_of_truth'],
              'readonly_inputs': data['readonly_inputs'],
              'generated_outputs': data['generated_outputs']}
    for field in PATH_FIELDS + TEXT_FIELDS:
        result[field] = [expand(value, context) for value in route[field]]
    if section_id and not route['requires_section']:
        result['read'] = list(dict.fromkeys([context['section_path'], *result['read']]))
        result['warnings'].append('指定一节仅缩小阅读起点，不缩小共享模块的实际影响范围。')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', help='content, guidance, reader, print, visuals, build, release, docs')
    parser.add_argument('--section', help='existing catalogue ID, e.g. x1-2-2')
    parser.add_argument('--json', action='store_true', help='emit machine-readable JSON')
    parser.add_argument('--check', action='store_true', help='validate map only; no writes or builds')
    args = parser.parse_args(argv)
    if not args.check and not args.task:
        parser.error('--task or --check is required')
    try:
        data = read_json(ROOT / MAP_PATH)
        validate_map(ROOT, data)
        if args.check:
            result = {'status': 'passed', 'routes': len(data['routes']), 'readonly': True,
                      'limits': 'Paths and routing structure only; not a complete dependency or teaching audit.'}
        else:
            result = plan(ROOT, data, args.task, args.section)
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f'ai_context: {error}', file=sys.stderr)
        return 2
    if args.json or args.check:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['title']} [{result['scope']}]\n{result['notice']}")
        print(f"\nsource_of_truth: {result['source_of_truth']}")
        for field in ('entrypoints', 'readonly_inputs', 'generated_outputs', *PATH_FIELDS, *TEXT_FIELDS):
            print(f'\n{field}:')
            for value in result[field]:
                print(f'  - {value}')
    return 0


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    sys.exit(main())
