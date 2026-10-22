"""Tests for the read-only architecture routing tool; standard library only."""

import copy
import io
import json
import os
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import ai_context as ai


class TaskContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = ai.read_json(ai.ROOT / ai.MAP_PATH)

    def test_current_map_is_valid(self):
        ai.validate_map(ai.ROOT, self.data)

    def test_content_requires_existing_section(self):
        with self.assertRaisesRegex(ValueError, 'requires --section'):
            ai.plan(ai.ROOT, self.data, 'content')
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            ai.plan(ai.ROOT, self.data, 'content', 'x1-999-999')

    def test_content_has_concrete_current_commands(self):
        result = ai.plan(ai.ROOT, self.data, 'content', 'x1-2-2')
        self.assertEqual(result['edit'], ['batch/sections/x1/x1-2-2.json'])
        self.assertTrue(result['readonly'])
        self.assertIn('--adopt-existing --section x1-2-2', result['commands'][2])
        self.assertNotIn('{section', json.dumps(result))

    def test_plan_includes_truth_and_safety_boundaries(self):
        result = ai.plan(ai.ROOT, self.data, 'content', 'x1-2-2')
        self.assertEqual(result['source_of_truth'], 'batch/sections/')
        self.assertIn('sources/', result['readonly_inputs'])
        self.assertIn('outputs/教材可视化资源库/', result['readonly_inputs'])
        self.assertIn('batch/state/', result['generated_outputs'])
        self.assertIn('batch/state/', result['outputs'])
        self.assertIn('outputs/_shared/', result['outputs'])

    def test_shared_section_does_not_claim_local_impact(self):
        result = ai.plan(ai.ROOT, self.data, 'reader', 'bx3-10-3')
        self.assertEqual(result['scope'], 'shared')
        self.assertEqual(result['read'][0], 'batch/sections/bx3/bx3-10-3.json')
        self.assertIn('不缩小共享模块', result['warnings'][-1])

    def test_all_routes_work_without_unresolved_templates(self):
        for name, route in self.data['routes'].items():
            result = ai.plan(ai.ROOT, self.data, name, 'x1-2-2' if route['requires_section'] else None)
            self.assertNotIn('{section', json.dumps(result))

    def test_invalid_tasks_and_section_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unknown task'):
            ai.plan(ai.ROOT, self.data, 'anything')
        for bad in ('../../x', 'x1-2-2;echo', '/x1-2-2', 'x1-2-2\\x'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ai.section_context(ai.ROOT, bad)

    def test_unsafe_paths_rejected(self):
        for path in ('../outside', '/tmp/outside', 'C:/outside', 'a\\b', ''):
            with self.subTest(path=path), self.assertRaises(ValueError):
                ai.relative_path(ai.ROOT, path)

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'root'
            root.mkdir()
            try:
                (root / 'escape').symlink_to(Path(temp), target_is_directory=True)
            except OSError:
                self.skipTest('symlinks not permitted on this host')
            with self.assertRaisesRegex(ValueError, 'escapes'):
                ai.relative_path(root, 'escape/file')

    def test_unknown_or_decorated_templates_rejected(self):
        for text in ('{missing}', '{section_id!r}', '{section_id:>8}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                ai.expand(text, {'section_id': 'x1-2-2'})

    def test_map_drift_is_detected(self):
        data = copy.deepcopy(self.data)
        data['routes']['docs']['read'].append('missing-current-file.md')
        with self.assertRaisesRegex(ValueError, 'mapped path missing'):
            ai.validate_map(ai.ROOT, data)

    def test_optional_route_cannot_hide_section_requirement(self):
        data = copy.deepcopy(self.data)
        data['routes']['docs']['read'].append('{section_path}')
        with self.assertRaisesRegex(ValueError, 'needs --section'):
            ai.validate_map(ai.ROOT, data)

    def test_bad_map_version_fails(self):
        data = copy.deepcopy(self.data)
        data['schema_version'] = 2
        with self.assertRaises(ValueError):
            ai.validate_map(ai.ROOT, data)

    def test_cli_check_and_errors(self):
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(ai.main(['--check']), 0)
        self.assertEqual(json.loads(output.getvalue())['status'], 'passed')
        with redirect_stderr(errors):
            self.assertEqual(ai.main(['--task', 'no-such-task']), 2)
        self.assertIn('unknown task', errors.getvalue())

    def test_cli_from_another_directory_creates_no_files(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run([sys.executable, str(ai.ROOT / 'scripts/ai_context.py'),
                                     '--task', 'content', '--section', 'x1-2-2', '--json'],
                                    cwd=temp, capture_output=True, text=True, encoding='utf-8',
                                    env={**os.environ, 'PYTHONIOENCODING': 'ascii'})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)['readonly'])
            self.assertEqual(list(Path(temp).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
