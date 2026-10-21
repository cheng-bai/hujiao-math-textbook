#!/usr/bin/env python3
"""Check all shipped reading indices, note placement and gated student packages."""
import json
from pathlib import Path
import unittest
import zipfile
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/五册教材教参整合'


class ReadingFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog = json.loads((ROOT / 'batch/manifests/catalog.json').read_text(encoding='utf-8'))
        cls.sections = [(book['id'], section['id']) for book in catalog['books']
                        for chapter in book['chapters'] for section in chapter['sections']]

    def test_all_indices_resolve_and_cover_questions(self):
        self.assertEqual(len(self.sections), 101)
        for book, sid in self.sections:
            for edition in ['teacher', 'student']:
                path = OUT / book / sid / f'{edition}.html'
                soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
                ids = [node['id'] for node in soup.select('[id]')]
                self.assertEqual(len(ids), len(set(ids)), str(path))
                index = soup.select('.page-toc a')
                self.assertTrue(index, str(path))
                anchors = [node['href'][1:] for node in index]
                self.assertTrue(set(anchors) <= set(ids), str(path))
                questions = soup.select('.book-body .question')
                self.assertTrue({node['id'] for node in questions} <= set(anchors), str(path))
                self.assertTrue(soup.select_one('#toc-search') and soup.select_one('#toc-filter'), str(path))

    def test_teacher_notes_live_in_answers_and_students_exclude_them(self):
        for book, sid in self.sections:
            for edition in ['teacher', 'student']:
                soup = BeautifulSoup((OUT / book / sid / f'{edition}.html').read_text(encoding='utf-8'), 'html.parser')
                if edition == 'student':
                    self.assertFalse(soup.select('.answer,.question-analysis,.teacher-only'))
                else:
                    for analysis in soup.select('.question-analysis'):
                        self.assertIsNotNone(analysis.find_parent(class_='answer-body'), sid)
                        self.assertIsNotNone(analysis.find_parent(class_='question'), sid)

    def test_gate_assets_and_student_zips_are_local_and_current(self):
        for book, sid in self.sections:
            folder = OUT / book / sid
            for edition in ['teacher', 'student']:
                soup = BeautifulSoup((folder / f'{edition}.html').read_text(encoding='utf-8'), 'html.parser')
                self.assertEqual(len(soup.select('script[src$="site-access.js"]')), 1, sid)
                self.assertEqual(len(soup.select('link[href$="site-access.css"]')), 1, sid)
            with zipfile.ZipFile(folder / 'student.zip') as archive:
                self.assertIsNone(archive.testzip(), sid)
                self.assertIn('site-access.js', archive.namelist())
                self.assertIn('site-access.css', archive.namelist())
                self.assertEqual(archive.read('site-access.js'), (ROOT / 'scripts/site-access.js').read_bytes())
                self.assertNotIn('../', archive.read('student.html').decode('utf-8'))
            for name in ['book.js', 'book.css', 'visual-book.js', 'site-access.js', 'site-access.css']:
                self.assertEqual((OUT / book / '_shared' / name).read_bytes(), (ROOT / 'scripts' / name).read_bytes())


if __name__ == '__main__':
    unittest.main()
