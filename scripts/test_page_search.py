#!/usr/bin/env python3
"""Check page search against real teacher and student pages without rebuilding them."""
import functools
import http.server
import os
import threading
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright
from project_paths import launch_browser
from test_print import unlock_access

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class PageSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.playwright = sync_playwright().start()
        cls.browser = launch_browser(cls.playwright)
        cls.base = f'http://127.0.0.1:{cls.server.server_port}/outputs/五册教材教参整合/bx1/bx1-5-1/'

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 390, 'height': 844})
        if os.environ.get('HUJIAO_TEST_BUILT_ASSETS') != '1':
            self.context.route('**/book.js?*', lambda route: route.fulfill(
                path=str(ROOT / 'scripts/book.js'), content_type='application/javascript'))
        self.page = self.context.new_page()

    def tearDown(self):
        self.context.close()

    def open_page(self, name):
        self.page.goto(self.base + name)
        unlock_access(self.page)
        self.page.wait_for_function('document.documentElement.dataset.math !== undefined')
        self.page.locator('#toc-toggle').click()

    def test_teacher_search_reveals_hidden_teacher_content(self):
        self.open_page('teacher.html')
        self.page.locator('#toc-dismiss').click()
        self.page.locator('.reader-more summary').click()
        self.page.locator('#notes-toggle').click()
        self.page.locator('#toc-toggle').click()
        self.page.locator('#toc-search').fill('课时安排建议')
        result = self.page.locator('.toc-search-result').filter(has_text='课时安排建议').first
        self.assertTrue(result.is_visible())
        excerpts = self.page.locator('.toc-search-result').all_text_contents()
        self.assertTrue(any('{10} + 2 + 1' in excerpt for excerpt in excerpts))
        self.assertTrue(all('10+2+1' not in excerpt for excerpt in excerpts))
        result.click()
        self.assertFalse(self.page.locator('body').evaluate("el => el.classList.contains('notes-hidden')"))
        self.assertEqual(self.page.evaluate('document.activeElement.textContent.trim()'), '课时安排建议')
        self.assertTrue(self.page.locator('#reading h3').filter(has_text='课时安排建议').is_visible())

    def test_student_search_excludes_teacher_content_and_filters(self):
        self.open_page('student.html')
        self.page.locator('#toc-search').fill('课时安排建议')
        self.assertIn('没有匹配', self.page.locator('#toc-count').inner_text())
        self.page.locator('#toc-search').fill('函数')
        self.assertGreater(self.page.locator('.toc-search-result').count(), 0)
        self.page.locator('#toc-filter').select_option('example')
        self.assertTrue(self.page.locator('.toc-search-result').count() <= 40)
        self.page.locator('#toc-search').fill('')
        self.assertEqual(self.page.locator('.toc-search-result').count(), 0)

    def test_question_filters_and_hidden_answer_navigation(self):
        self.open_page('teacher.html')
        self.page.locator('#toc-search').fill('求下列函数的定义域')
        self.page.locator('#toc-filter').select_option('example')
        example = self.page.locator('.toc-search-result').filter(has_text='求下列函数的定义域').first
        self.assertTrue(example.is_visible())
        example.click()
        self.page.wait_for_function("document.activeElement.closest('.question')?.id === 'bx1-5-1-ex-1'")
        self.assertEqual(self.page.evaluate("document.activeElement.closest('.question').id"), 'bx1-5-1-ex-1')
        self.assertEqual(self.page.evaluate('location.hash'), '')
        self.page.locator('#toc-toggle').click()
        self.page.locator('#toc-filter').select_option('exercise')
        exercise = self.page.locator('.toc-search-result').filter(has_text='求下列函数的定义域').first
        self.assertTrue(exercise.is_visible())
        exercise.click()
        self.page.wait_for_function("document.activeElement.closest('.question')?.id === 'bx1-5-1-p511-1'")
        self.assertEqual(self.page.evaluate("document.activeElement.closest('.question').id"), 'bx1-5-1-p511-1')
        self.page.locator('.reader-more summary').click()
        self.page.locator('#answer-toggle').click()
        self.page.locator('#toc-toggle').click()
        self.page.locator('#toc-filter').select_option('example')
        self.page.locator('#toc-search').fill('负数不属于')
        self.page.locator('.toc-search-result').filter(has_text='负数不属于').first.click()
        self.page.wait_for_function("document.activeElement.textContent.includes('负数不属于')")
        self.assertFalse(self.page.locator('body').evaluate("el => el.classList.contains('answers-hidden')"))
        self.assertTrue(self.page.locator('#bx1-5-1-ex-2 .answer').evaluate('el => el.open'))
        self.assertIn('负数不属于', self.page.evaluate('document.activeElement.textContent'))


if __name__ == '__main__':
    unittest.main()
