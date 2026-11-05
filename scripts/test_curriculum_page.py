import ast
import contextlib
import hashlib
import io
import json
import re
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup
from curriculum_page import reviewed_source
import curriculum_page

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'outputs/五册教材教参整合'


class CurriculumPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = OUTPUT / 'curriculum-2025'
        cls.page = BeautifulSoup((OUTPUT / 'curriculum-2025.html').read_text(encoding='utf-8'), 'html.parser')
        cls.build = json.loads((cls.assets / 'build.json').read_text(encoding='utf-8'))
        original = subprocess.run(['pandoc', '--from=markdown', '--to=html', '--katex', str(cls.assets / 'reviewed.md')], check=True, capture_output=True, text=True).stdout
        cls.original = BeautifulSoup(original, 'html.parser')

    def test_source_fingerprint_and_complete_content(self):
        self.assertEqual(hashlib.sha256((self.assets / 'source.md').read_bytes()).hexdigest(), self.build['source_sha256'])
        original = BeautifulSoup(str(self.original), 'html.parser')
        appendix = next(node for node in original.find_all('h2', recursive=False) if node.get_text(' ', strip=True).startswith('附录 2 '))
        cases = {}
        number = None
        for node in list(appendix.next_siblings):
            title = re.match(r'^案例\s*(\d+)\s+(.+)$', node.get_text(' ', strip=True)) if getattr(node, 'name', None) in ('p', 'h2') else None
            if title:
                number = int(title.group(1))
                cases[number] = []
            if number is not None:
                cases[number].append(node.extract())
        self.assertEqual(set(cases), set(range(1, 34)))
        for article in self.page.select('.curriculum-case'):
            source = cases[int(article['data-case'])]
            source_text = ''.join(node.get_text(' ', strip=True) if getattr(node, 'name', None) else str(node) for node in source)
            self.assertEqual(re.sub(r'\s+', '', source_text), re.sub(r'\s+', '', article.get_text(' ', strip=True)), article['data-case'])
            images = [image['src'] for node in source if getattr(node, 'name', None) for image in node.select('img')]
            self.assertEqual(images, [image['src'].removeprefix('curriculum-2025/') for image in article.select('img')])
            formulas = [math.get_text() for node in source if getattr(node, 'name', None) for math in node.select('.math')]
            self.assertEqual(formulas, [math.get_text() for math in article.select('.math')])
        page = BeautifulSoup(str(self.page), 'html.parser')
        for node in page.select('.case-group,.case-catalog'):
            node.decompose()
        for selector in ['p', 'li', 'td', 'th', '.math']:
            expected = [element.get_text(' ', strip=True) for element in original.select(selector)]
            actual = [element.get_text(' ', strip=True) for element in page.select(f'.reading-section {selector},.source-toc {selector}')]
            self.assertEqual(actual, expected, selector)
        self.assertEqual(len(self.page.select('.reading-section')), 10)

    def test_case_references(self):
        groups = self.page.select('.case-group')
        self.assertEqual(len(groups), 26)
        self.assertEqual(len(self.page.select('.curriculum-case')), 51)
        self.assertEqual({int(node['data-case']) for node in self.page.select('.curriculum-case[data-case-primary="true"]')}, set(range(1, 34)))
        for group in groups:
            self.assertEqual(group['data-case-reference'].split(','), [node['data-case'] for node in group.select(':scope > .curriculum-case')])
        references = [group['data-case-reference'] for group in groups]
        self.assertEqual(references.count(','.join(map(str, range(20, 32)))), 2)
        self.assertIn('24,26,28', references)

    def test_verified_corrections(self):
        reviewed, corrections = reviewed_source((self.assets / 'source.md').read_bytes())
        self.assertEqual(reviewed, (self.assets / 'reviewed.md').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256(reviewed.encode()).hexdigest(), self.build['reviewed_sha256'])
        self.assertEqual(hashlib.sha256((self.assets / 'corrections.json').read_bytes()).hexdigest(), self.build['corrections_sha256'])
        self.assertEqual(corrections['pdf_sha256'], self.build['reference_pdf_sha256'])
        for article in self.page.select('[data-case="14"]'):
            tables = article.select('table')
            self.assertEqual(len(tables), 3)
            rows = tables[0].select('tr')
            self.assertEqual(len(rows), 20)
            self.assertTrue(all(len(row.select('td')) == 10 for row in rows))
            sample = [int(cell.get_text()) for cell in tables[0].select('td')]
            ordered = [int(cell.get_text()) for table in tables[1:] for cell in table.select('td')]
            self.assertEqual(sorted(sample), ordered)
            self.assertEqual((ordered[149] + ordered[150]) / 2, 178)
            self.assertEqual((ordered[189] + ordered[190]) / 2, 296.5)
        for article in self.page.select('[data-case="33"]'):
            text = article.get_text(' ', strip=True)
            self.assertIn('“互联网+”', text)
            self.assertIn('学生学习的数据报告', text)
            self.assertTrue(text.endswith('改进教学方式。'))
        self.assertNotIn('案例 33 在原稿末尾截断', self.page.get_text())
        with self.assertRaisesRegex(ValueError, '指纹'):
            reviewed_source(b'changed source')

    def test_local_resources_and_navigation(self):
        identifiers = [node['id'] for node in self.page.select('[id]')]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        for node in self.page.select('a[href],img[src],script[src],link[href]'):
            target = node.get('href', node.get('src'))
            if target.startswith('#'):
                self.assertIn(unquote(target[1:]), identifiers)
            else:
                self.assertNotIn('://', target)
                self.assertTrue((OUTPUT / unquote(urlsplit(target).path)).is_file(), target)
        self.assertEqual(len(set(image['src'] for image in self.page.select('img'))), 53)
        self.assertIn('非官方发布页', self.page.get_text())
        self.assertIn('未逐条校订 OCR', self.page.get_text())

    def test_rebuild_from_repository_sources(self):
        ast.parse((ROOT / 'scripts/curriculum_page.py').read_text(encoding='utf-8'), feature_version=(3, 10))
        with tempfile.TemporaryDirectory(prefix='curriculum-test-') as temporary:
            output = Path(temporary)
            assets = output / 'curriculum-2025'
            assets.mkdir()
            shutil.copy2(self.assets / 'corrections.json', assets / 'corrections.json')
            with patch.object(curriculum_page, 'OUTPUT', output), patch.object(curriculum_page, 'ASSETS', assets):
                with contextlib.redirect_stdout(io.StringIO()):
                    curriculum_page.render(self.assets / 'source.md')
            for filename in ('reader.js', 'reviewed.md', 'build.json'):
                self.assertEqual((assets / filename).read_bytes(), (self.assets / filename).read_bytes(), filename)
            # The shared access script may acquire a cache key after an existing page was built.
            normalize = lambda page: re.sub(r'(site-access\.js)(?:\?v=[a-f0-9]+)?', r'\1', page)
            self.assertEqual(normalize((output / 'curriculum-2025.html').read_text(encoding='utf-8')),
                             normalize((OUTPUT / 'curriculum-2025.html').read_text(encoding='utf-8')))
            self.assertTrue(all((assets / name).is_file() for name in self.build['images']))


if __name__ == '__main__':
    unittest.main()
