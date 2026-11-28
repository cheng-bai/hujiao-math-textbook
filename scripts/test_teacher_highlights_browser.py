#!/usr/bin/env python3
"""Check saved highlights against a built teacher page in Chromium."""
import functools
import http.server
import json
import threading
import unittest
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from project_paths import launch_browser
from teacher_highlights_schema import storage_key
from test_print import unlock_access

ROOT = Path(__file__).resolve().parents[1]
SECTION = 'x1-1-2'
EXAMPLE = f'{SECTION}-ex-4'
PLAIN_QUOTE = '本章 1.1 节中例 3 得到的方程'
FORMULA_QUOTE = '现在我们讨论, 在平面直角坐标系中'


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class TeacherHighlightBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
        cls.addClassCleanup(server.server_close)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        cls.addClassCleanup(server.shutdown)
        playwright = sync_playwright().start()
        cls.addClassCleanup(playwright.stop)
        cls.browser = launch_browser(playwright)
        cls.addClassCleanup(cls.browser.close)
        cls.url = f'http://127.0.0.1:{server.server_port}/outputs/五册教材教参整合/x1/{SECTION}/teacher.html'

    def setUp(self):
        context = self.browser.new_context(viewport={'width': 390, 'height': 844})
        self.addCleanup(context.close)
        quotes = ['的横坐标相等,所以', '例 3 与例 4 是为了巩固', '已从原文移除的测试短语']
        items = [dict(id=f'test-{index}', blockId=EXAMPLE, quote=quote, note='', color='warm')
                 for index, quote in enumerate(quotes)]
        key = json.dumps(storage_key(SECTION))
        value = json.dumps(json.dumps(items, ensure_ascii=False))
        context.add_init_script(f'if (!localStorage.getItem({key})) localStorage.setItem({key}, {value});')
        self.page = context.new_page()
        self.page.goto(self.url)
        unlock_access(self.page)
        self.popover = self.page.locator('#teacher-highlight-popover')
        self.dialog = self.page.locator('#teacher-highlights-dialog')

    def open_panel(self):
        button = self.page.locator('#highlights-open')
        if not button.is_visible():
            self.page.locator('.reader-more summary').click()
        button.click()
        expect(self.dialog).to_be_visible()

    def select_paragraph_text(self, paragraph, length=None):
        paragraph.scroll_into_view_if_needed()
        paragraph.evaluate('''(element, length) => {
            const range = document.createRange();
            range.setStart(element.firstChild, 0);
            if (length === null) range.setEnd(element.lastChild, element.lastChild.length);
            else range.setEnd(element.firstChild, length);
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);
            const { x, y } = range.getBoundingClientRect();
            element.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, clientX: x, clientY: y }));
        }''', length)

    def test_plain_paragraph_and_text_highlight_are_independent(self):
        paragraph = self.page.locator('.book-body p').filter(has_text=PLAIN_QUOTE)
        self.select_paragraph_text(paragraph, len(PLAIN_QUOTE))
        text_button = self.popover.get_by_role('button', name='高亮', exact=True)
        expect(text_button).to_be_visible()
        self.popover.get_by_role('button', name='高亮此段').click()
        expect(paragraph).to_have_css('background-color', 'rgb(246, 230, 168)')
        expect(paragraph.locator('mark')).to_have_count(0)
        self.page.reload()
        expect(paragraph).to_have_css('background-color', 'rgb(246, 230, 168)')
        self.select_paragraph_text(paragraph, len(PLAIN_QUOTE))
        text_button.click()
        expect(paragraph.locator('mark.teacher-highlight')).to_have_text(PLAIN_QUOTE)
        self.open_panel()
        self.dialog.locator('.thl-item').filter(has_text='就是一个点斜式方程').get_by_role('button', name='移除').click()
        expect(paragraph).not_to_have_class('teacher-highlight-paragraph')
        expect(paragraph.locator('mark.teacher-highlight')).to_have_text(PLAIN_QUOTE)

    def test_formula_paragraph_keeps_katex_and_round_trips(self):
        paragraph = self.page.locator('.book-body p').filter(has_text=FORMULA_QUOTE)
        expect(paragraph.locator('.katex').first).to_be_visible()
        original = paragraph.evaluate('element => element.innerHTML')
        self.select_paragraph_text(paragraph)
        expect(self.popover.get_by_role('button', name='高亮', exact=True)).to_be_hidden()
        self.popover.get_by_role('button', name='高亮此段').click()
        expect(paragraph).to_have_css('background-color', 'rgb(246, 230, 168)')
        self.assertEqual(paragraph.evaluate('element => element.innerHTML'), original)
        self.page.reload()
        expect(paragraph).to_have_css('background-color', 'rgb(246, 230, 168)')

        self.open_panel()
        row = self.dialog.locator('.thl-item').filter(has_text=FORMULA_QUOTE)
        row.get_by_role('button', name='定位').click()
        expect(paragraph).to_be_focused()
        expect(paragraph).to_be_in_viewport()
        self.open_panel()
        with self.page.expect_download() as exported:
            self.dialog.get_by_role('button', name='导出').click()
        row.get_by_role('button', name='移除').click()
        expect(paragraph).not_to_have_class('teacher-highlight-paragraph')

        self.page.once('dialog', lambda dialog: dialog.accept())
        self.dialog.locator('#thl-import').set_input_files(exported.value.path())
        expect(paragraph).to_have_css('background-color', 'rgb(246, 230, 168)')
        self.assertEqual(paragraph.evaluate('element => element.innerHTML'), original)

    def test_hidden_answer_keeps_setting_and_folded_answer_opens_at_mark(self):
        answer = self.page.locator(f'#{EXAMPLE} details.answer')
        self.page.locator('.reader-more summary').click()
        toggle = self.page.locator('#answer-toggle')
        toggle.click()
        self.open_panel()
        row = self.dialog.locator('[data-id="test-0"]')
        expect(row.get_by_role('status')).to_be_empty()
        row.get_by_role('button', name='定位').click()
        expect(row.get_by_role('status')).to_contain_text('请先显示答案')
        expect(self.dialog).to_be_visible()
        expect(toggle).to_have_attribute('aria-pressed', 'true')
        expect(answer).to_be_hidden()
        self.dialog.get_by_role('button', name='关闭', exact=True).last.click()
        if not toggle.is_visible():
            self.page.locator('.reader-more summary').click()
        toggle.click()
        answer.locator('summary').click()
        self.open_panel()
        row.get_by_role('button', name='定位').click()
        expect(self.dialog).to_be_hidden()
        mark = answer.locator('mark.teacher-highlight[data-highlight-id="test-0"]')
        expect(mark).to_be_visible()
        expect(mark).to_be_focused()
        expect(mark).to_be_in_viewport()

    def test_stale_and_hidden_teacher_highlights_are_distinguished(self):
        self.page.locator('.reader-more summary').click()
        toggle = self.page.locator('#notes-toggle')
        toggle.click()
        self.open_panel()
        stale = self.dialog.locator('[data-id="test-2"]')
        expect(stale.get_by_role('status')).to_contain_text('无法唯一定位')
        hidden = self.dialog.locator('[data-id="test-1"]')
        expect(hidden.get_by_role('status')).to_be_empty()
        hidden.get_by_role('button', name='定位').click()
        expect(hidden.get_by_role('status')).to_contain_text('请先显示教师批注')
        expect(toggle).to_have_attribute('aria-pressed', 'true')
        expect(self.dialog).to_be_visible()


if __name__ == '__main__':
    unittest.main()
