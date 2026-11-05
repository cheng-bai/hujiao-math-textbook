#!/usr/bin/env python3
"""Exercise reading controls against generated pages, including offline delivery."""
import functools
import http.server
import json
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright
from project_paths import launch_browser
from test_print import choose, unlock_access
from batch_validate import formula_count, rendered_source_formula_count

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'outputs/五册教材教参整合'


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class TestServer(http.server.ThreadingHTTPServer):
    # Long textbook pages request many local images and scripts concurrently.
    request_queue_size = 128


class ReaderExperienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = TestServer(
            ('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}/outputs/五册教材教参整合/'
        cls.playwright = sync_playwright().start()
        cls.browser = launch_browser(cls.playwright)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width':390, 'height':844})
        self.page = self.context.new_page()

    def tearDown(self):
        self.context.close()

    def ready(self, url):
        self.page.goto(url)
        unlock_access(self.page)
        self.page.wait_for_function('document.documentElement.dataset.math !== undefined')
        self.page.locator('.toolbar').wait_for(state='visible')
        self.assertEqual(self.page.evaluate('window.__mathErrors'), [])

    def test_gate_password_and_previous_session(self):
        self.page.add_init_script("sessionStorage.setItem('hujiao.textbook.reading.gate.v1', 'granted')")
        self.page.goto(self.base + 'bx1/bx1-1-1/teacher.html')
        self.assertTrue(self.page.locator('#access-form').is_visible())
        self.page.locator('#access-passphrase').fill('incorrect')
        self.page.locator('#access-form button[type="submit"]').click()
        self.assertEqual(self.page.locator('#access-passphrase').get_attribute('aria-invalid'), 'true')
        self.assertTrue(self.page.locator('#access-form').is_visible())
        unlock_access(self.page)
        self.assertEqual(self.page.evaluate('document.documentElement.dataset.accessState'), 'granted')
        self.page.goto(self.base + 'bx1/bx1-1-1/student.html')
        self.assertEqual(self.page.evaluate('document.documentElement.dataset.accessState'), 'granted')

    def test_guidance_index_and_print(self):
        for section in ['bx3/bx3-11-4', 'x1/x1-2-2', 'bx1/bx1-4-3']:
            with self.subTest(section=section):
                self.ready(self.base + section + '/teacher.html')
                note = self.page.locator('.teacher-guidance-source')
                self.assertEqual(note.count(), 1)
                self.assertIsNone(note.get_attribute('open'))
                note.locator('summary').click()
                source = note.inner_text().replace('展开完整教参说明', '').strip()
                note.locator('summary').click()
                self.assertEqual(self.page.locator('.toc-preview').count(), 0)
                choose(self.page, 'all', notes=True)
                printed = self.page.locator('#print-output .teacher').first
                self.assertEqual(printed.locator('.teacher-brief,details').count(), 0)
                self.assertIn(source.splitlines()[0], printed.inner_text())
                self.assertGreater(len(printed.inner_text()), len(source) * .9)
                choose(self.page, 'questions', notes=True)
                self.assertEqual(self.page.locator('#print-output .teacher').count(), 0)

    def test_mobile_menu_density_and_lock(self):
        self.ready(self.base + 'bx3/bx3-11-4/teacher.html')
        for width in [320, 390, 720]:
            self.page.set_viewport_size({'width':width, 'height':844})
            self.assertLessEqual(self.page.locator('.toolbar').bounding_box()['height'], 62)
            self.assertFalse(self.page.locator('#density-toggle').is_visible())
            self.page.locator('.reader-more summary').click()
            self.assertTrue(self.page.locator('.site-lock-action').is_visible())
            self.page.keyboard.press('Escape')
            self.assertTrue(self.page.locator('.reader-more summary').evaluate('(el)=>el===document.activeElement'))
        self.page.locator('.reader-more summary').click()
        self.page.locator('#density-toggle').click()
        self.ready(self.base + 'x1/x1-2-2/student.html')
        self.assertEqual(self.page.locator('body.spacious').count(), 1)
        self.assertEqual(self.page.locator('.teacher-only,.teacher-guidance-source,.answer').count(), 0)
        self.page.locator('.reader-more summary').click()
        self.page.locator('.site-lock-action').click()
        self.assertTrue(self.page.locator('#access-form').is_visible())
        unlock_access(self.page)
        self.page.set_viewport_size({'width':1440, 'height':900})
        self.assertTrue(self.page.locator('#density-toggle').is_visible())

    def test_exercise_groups_and_search(self):
        self.page.set_viewport_size({'width':1440, 'height':900})
        self.ready(self.base + 'bx3/bx3-chapter-end-10/teacher.html')
        group = self.page.locator('.review-toc-group').first
        toggle = group.locator('.review-toc-toggle')
        self.assertEqual(toggle.get_attribute('aria-expanded'), 'false')
        toggle.click()
        self.assertEqual(toggle.get_attribute('aria-expanded'), 'true')
        toggle.click()
        search = self.page.locator('#toc-search')
        child = group.locator('.review-toc-children .toc-link').first
        search.fill(child.inner_text().strip())
        self.assertEqual(toggle.get_attribute('aria-expanded'), 'true')
        search.fill('')
        self.assertEqual(toggle.get_attribute('aria-expanded'), 'false')
        toggle.click()
        child.click()
        self.page.wait_for_timeout(500)
        self.assertTrue(child.get_attribute('href').endswith(self.page.evaluate('location.hash')))
        self.assertEqual(child.get_attribute('aria-current'), 'location')

    def test_storage_failure_is_nonfatal(self):
        self.page.add_init_script("Object.defineProperty(window, 'localStorage', {get(){throw new Error('blocked')}})")
        self.ready(self.base + 'bx3/bx3-11-4/student.html')
        self.page.locator('.reader-more summary').click()
        self.page.locator('#density-toggle').click()
        self.assertEqual(self.page.locator('body.spacious').count(), 1)

    def test_formula_briefs_do_not_duplicate_source_counts(self):
        for section in ['bx1/bx1-4-3', 'bx2/bx2-7-3', 'bx2/bx2-7-4', 'x2/x2-5-2']:
            with self.subTest(section=section):
                self.ready(self.base + section + '/teacher.html')
                self.page.wait_for_function("document.documentElement.dataset.visualReady === 'true'")
                blocks = json.loads((OUTPUT / section / 'content.json').read_text(encoding='utf-8'))
                self.assertEqual(rendered_source_formula_count(self.page), formula_count(blocks))

    def test_invalid_preference_falls_back_to_compact(self):
        self.page.add_init_script("localStorage.setItem('hujiao-reading-density-v1', 'invalid')")
        self.ready(self.base + 'bx3/bx3-11-4/student.html')
        self.assertEqual(self.page.locator('body.spacious').count(), 0)

    def test_versioned_assets_work_in_offline_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            with zipfile.ZipFile(OUTPUT / 'bx3/bx3-11-4/student.zip') as archive:
                archive.extractall(directory)
            self.ready((Path(directory) / 'student.html').as_uri())
            self.assertEqual(self.page.locator('.teacher-only,.answer').count(), 0)
            refs = self.page.locator('link[href^="book.css?v="],script[src^="book.js?v="],script[src^="site-access.js?v="]')
            self.assertEqual(refs.count(), 3)
            for ref in refs.all():
                self.assertIn('?v=', ref.get_attribute('href') or ref.get_attribute('src'))
            self.assertEqual(self.page.evaluate('getComputedStyle(document.body).fontSize'), '16px')


if __name__ == '__main__':
    unittest.main()
