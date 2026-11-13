#!/usr/bin/env python3
"""Catalog, chapter-end titles, student isolation, and highlight JSON contract."""
from __future__ import annotations

import json
import re
import unittest
import zipfile
from html.parser import HTMLParser
from pathlib import Path

from portal_index import render_portal_index
from teacher_highlights_schema import export_document, storage_key, validate_import

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'outputs/五册教材教参整合'


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.append(dict(attrs).get('href', ''))


class TeacherHighlightsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog = json.loads((ROOT / 'batch/manifests/catalog.json').read_text(encoding='utf-8'))
        state = json.loads((ROOT / 'batch/state/progress.json').read_text(encoding='utf-8'))
        cls.portal = render_portal_index(catalog, state['books'], state['totals'], state['updated_at'], OUTPUT)
        parser = LinkParser()
        parser.feed(cls.portal)
        cls.portal_links = parser.links

    def test_catalog_bx1_5_3_defaults_to_teacher_html(self):
        teacher = [link for link in self.portal_links if link == 'bx1/bx1-5-3/teacher.html']
        pilot = [link for link in self.portal_links if link == 'bx1/bx1-5-3/annotation-teacher-pilot.html']
        self.assertEqual(len(teacher), 1)
        self.assertEqual(len(pilot), int((OUTPUT / 'bx1/bx1-5-3/annotation-teacher-pilot.html').is_file()))
        default_links = [
            link for link in self.portal_links
            if link.startswith('bx1/bx1-5-3/') and 'pilot' not in link
        ]
        self.assertEqual(default_links, ['bx1/bx1-5-3/teacher.html'])

    def test_chapter_end_titles_have_no_internal_prefix(self):
        pattern = re.compile(r'chapter-end-\d')
        for path in OUTPUT.glob('*/*chapter-end*/teacher.html'):
            text = path.read_text(encoding='utf-8')
            title = re.search(r'<title>([^<]+)</title>', text)
            self.assertIsNotNone(title, path)
            self.assertNotRegex(title.group(1), pattern, path)
            h1 = re.search(r'<h1>([^<]+)', text)
            self.assertIsNotNone(h1, path)
            self.assertNotRegex(h1.group(1), pattern, path)
        for path in OUTPUT.glob('*/*chapter-end*/student.html'):
            title = re.search(r'<title>([^<]+)</title>', path.read_text(encoding='utf-8'))
            self.assertIsNotNone(title, path)
            self.assertNotRegex(title.group(1), pattern, path)

    def test_student_outputs_exclude_highlight_ui(self):
        for path in [OUTPUT / 'bx1/bx1-1-1/student.html', OUTPUT / 'bx1/bx1-5-3/student.html']:
            html = path.read_text(encoding='utf-8')
            for token in ['teacher-highlights', 'highlights-open', 'teacher-highlight', '我的高亮']:
                self.assertNotIn(token, html, path)
        for path in [OUTPUT / 'bx1/bx1-1-1/student.zip', OUTPUT / 'bx1/bx1-5-3/student.zip']:
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                self.assertNotIn('teacher-highlights.js', names)
                self.assertNotIn('teacher-highlights.css', names)
                self.assertNotIn('teacher-highlights', archive.read('student.html').decode('utf-8'))

    def test_teacher_pages_ship_highlight_assets(self):
        for sid in ['bx1-1-1', 'bx1-5-3']:
            html = (OUTPUT / 'bx1' / sid / 'teacher.html').read_text(encoding='utf-8')
            self.assertIn('teacher-highlights.js', html)
            self.assertIn('id="highlights-open"', html)

    def test_storage_export_import_contract(self):
        section_id = 'sample-section-a'
        items = [{
            'id': '00000000-0000-4000-8000-000000000001',
            'blockId': 'sample-section-a-b3',
            'quote': '示例重点短语',
            'note': '本页备注',
            'color': 'warm',
            'createdAt': '2026-01-01T00:00:00+08:00',
        }]
        payload = export_document(section_id, items)
        self.assertEqual(payload['sectionId'], section_id)
        imported, errors = validate_import(payload, section_id)
        self.assertEqual(errors, [])
        self.assertEqual(imported[0]['quote'], '示例重点短语')
        wrong, errors = validate_import(payload, 'other-section')
        self.assertTrue(errors)
        self.assertEqual(storage_key(section_id), 'hujiao-teacher-highlights-v1:sample-section-a')


if __name__ == '__main__':
    unittest.main()
