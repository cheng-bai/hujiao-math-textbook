#!/usr/bin/env python3
"""Small, dependency-free regression checks for release portability."""
import ast
from contextlib import redirect_stdout
import io
import os
from pathlib import Path, PureWindowsPath
import tempfile
import unittest
from unittest.mock import Mock, patch

from check_release import audit_site
from project_paths import ROOT, launch_browser, portable_record


class PortabilityTests(unittest.TestCase):
    def test_text_io_uses_explicit_encoding(self):
        for path in (ROOT / 'scripts').rglob('*.py'):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                if node.func.attr not in {'read_text', 'write_text'}:
                    continue
                positional_encoding = len(node.args) > (0 if node.func.attr == 'read_text' else 1)
                self.assertTrue(positional_encoding or any(k.arg == 'encoding' for k in node.keywords),
                                f'{path.name}:{node.lineno}')

    def test_build_paths_are_portable(self):
        value = {'output': str(ROOT / 'outputs' / 'chapter'),
                 'assets': {str(ROOT / 'sources' / 'image.png'): ['sources/image.png']}}
        self.assertEqual(portable_record(value), {
            'output': 'outputs/chapter', 'assets': {'sources/image.png': ['sources/image.png']}})

    def test_browser_falls_back_when_headless_shell_is_missing(self):
        pw = Mock()
        pw.chromium.launch.side_effect = [RuntimeError('headless shell missing'), 'chrome']
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(launch_browser(pw, headless=True), 'chrome')
        self.assertEqual(pw.chromium.launch.call_args_list[1].kwargs,
                         {'channel': 'chrome', 'headless': True})

    def test_windows_paths_do_not_corrupt_math(self):
        with patch('project_paths.ROOT', PureWindowsPath('C:/checkout')):
            self.assertEqual(portable_record('C:\\checkout\\outputs\\chapter'), 'outputs/chapter')
            self.assertEqual(portable_record(r'$\sin x$'), r'$\sin x$')

    def test_browser_explicit_channel_is_respected(self):
        pw = Mock()
        with patch.dict(os.environ, {'HUJIAO_BROWSER_CHANNEL': 'chrome'}):
            launch_browser(pw, headless=True)
        pw.chromium.launch.assert_called_once_with(channel='chrome', headless=True)

    def test_site_closure_detects_missing_review_link(self):
        with tempfile.TemporaryDirectory() as folder, redirect_stdout(io.StringIO()):
            root = Path(folder)
            (root / 'index.html').write_text('<a href="batch/reviews/review.json">review</a>', encoding='utf-8')
            self.assertTrue(audit_site(root))
            review = root / 'batch/reviews/review.json'
            review.parent.mkdir(parents=True)
            review.write_text('{}', encoding='utf-8')
            self.assertFalse(audit_site(root))


if __name__ == '__main__':
    unittest.main()
