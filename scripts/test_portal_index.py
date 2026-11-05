import json
import unittest
import tempfile
from html.parser import HTMLParser
from pathlib import Path

from portal_index import render_portal_index
from site_access import access_version, install_page

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'outputs/五册教材教参整合'


class PortalParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.details = 0
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'details':
            self.details += 1
        if tag == 'a':
            self.links.append(attrs['href'])


class PortalIndexTest(unittest.TestCase):
    def test_catalog_links_and_access(self):
        catalog = json.loads((ROOT / 'batch/manifests/catalog.json').read_text(encoding='utf-8'))
        state = json.loads((ROOT / 'batch/state/progress.json').read_text(encoding='utf-8'))
        page = render_portal_index(catalog, state['books'], state['totals'], state['updated_at'], OUTPUT)
        parser = PortalParser()
        parser.feed(page)
        self.assertEqual(parser.details, len(catalog['books']))
        book_links = [target for target in parser.links if target.endswith('/index.html')]
        self.assertEqual(book_links, [f'{book_id}/index.html' for book_id in ['bx1', 'bx2', 'bx3', 'x1', 'x2']])
        sections = [section for book in catalog['books'] for chapter in book['chapters'] for section in chapter['sections']]
        self.assertEqual(len(sections), 101)
        for book in catalog['books']:
            for chapter in book['chapters']:
                for section in chapter['sections']:
                    target = f'{book["id"]}/{section["id"]}/teacher.html'
                    self.assertEqual(target in parser.links, (OUTPUT / target).is_file())
        for target in parser.links:
            self.assertTrue((OUTPUT / target).is_file(), target)
        self.assertIn(f'../_shared/site-access.js?v={access_version()}', page)
        self.assertEqual('curriculum-2025.html' in parser.links, (OUTPUT / 'curriculum-2025.html').is_file())
        self.assertEqual('grid-template-columns:repeat(3,minmax(0,1fr))' in page,
                         (OUTPUT / 'curriculum-2025.html').is_file())
        self.assertIn('不等于全书逐题数学审定', page)

    def test_existing_gate_reference_gets_current_version(self):
        for suffix in ['', '?v=previous']:
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as directory:
                page = Path(directory) / 'index.html'
                page.write_text(f'<script defer src="../_shared/site-access.js{suffix}"></script>', encoding='utf-8')
                self.assertTrue(install_page(page))
                self.assertIn(f'site-access.js?v={access_version()}"', page.read_text(encoding='utf-8'))
                self.assertFalse(install_page(page))


if __name__ == '__main__':
    unittest.main()
