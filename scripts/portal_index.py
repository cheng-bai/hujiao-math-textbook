"""Render the five-book landing page from the existing catalog."""
import html

from site_access import access_head


def add_curriculum_link(page):
    marker = '<nav class="tools" aria-label="专题入口">'
    link = ('<a class="tool" href="curriculum-2025.html"><span><strong>课程标准</strong>'
            '<small>2017 年版 · 2025 年修订</small></span><span aria-hidden="true">↗</span></a>')
    if page.count(marker) != 1:
        raise ValueError('Cannot identify the portal tools navigation')
    if 'href="curriculum-2025.html"' in page:
        return page
    page = page.replace(marker, marker + link, 1)
    return page.replace('.tools{display:grid;grid-template-columns:1fr 1fr;',
                        '.tools{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));', 1)


def render_portal_index(catalog, book_summaries, totals, updated_at, output):
    page = _render_portal_index(catalog, book_summaries, totals, updated_at, output)
    return add_curriculum_link(page) if (output / 'curriculum-2025.html').is_file() else page


def _render_portal_index(catalog, book_summaries, totals, updated_at, output):
    escape = html.escape
    summaries = {book['id']: book for book in book_summaries}
    order = ['bx1', 'bx2', 'bx3', 'x1', 'x2']
    books = []
    for number, book in enumerate(sorted(catalog['books'], key=lambda item: order.index(item['id'])), 1):
        book_id = book['id']
        chapters = []
        for chapter in book['chapters']:
            sections = []
            for section in chapter['sections']:
                section_id = section['id']
                title = section.get('display_title', section.get('title', section.get('section', section_id)))
                label = section.get('section', '')
                if label and label[0].isdigit() and not title.startswith(label):
                    title = f'{label} {title}'
                title = escape(title)
                target = f'{book_id}/{section_id}/teacher.html'
                if (output / target).is_file():
                    sections.append(f'<li><a href="{escape(target, quote=True)}">{title}<span aria-hidden="true">↗</span></a></li>')
                else:
                    sections.append(f'<li><span class="unavailable">{title}<small>待构建</small></span></li>')
            chapters.append(f'<section class="chapter"><h3>{escape(chapter["title"])}</h3><ul>{"".join(sections)}</ul></section>')
        summary = summaries[book_id]
        books.append(f'''<details class="book"><summary><span class="book-number">{number:02d}</span><span class="book-name">{escape(book['title'])}<small>{len(book['chapters'])} 章 · {summary['sections']} 个节点</small></span><span class="toggle" aria-hidden="true"></span></summary><div class="book-body"><div class="book-actions"><span>选择章节，直接进入教师阅读</span><a href="{escape(book_id, quote=True)}/index.html">打开整册目录 →</a></div><div class="chapters">{''.join(chapters)}</div></div></details>''')
    css = '''
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f5f4ee;color:#243b31;font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}a{color:inherit;text-underline-offset:4px}a:focus-visible,summary:focus-visible{outline:3px solid #b46b45;outline-offset:4px}main{max-width:1080px;margin:auto;padding:0 32px 70px}.topline{display:flex;justify-content:space-between;align-items:center;padding:23px 0;border-bottom:1px solid #ced8cd;font-size:12px;letter-spacing:.12em;color:#607367}.topline strong{font-size:14px;letter-spacing:.04em;color:#294e3d}.hero{display:grid;grid-template-columns:1fr auto;gap:40px;align-items:end;padding:56px 0 48px}.eyebrow{color:#9d6549;font-size:12px;letter-spacing:.16em;font-weight:700}.hero h1{font:600 clamp(36px,5vw,57px)/1.2 "Songti SC","Noto Serif CJK SC",serif;letter-spacing:.05em;margin:14px 0 18px}.hero p{color:#65766b;margin:0;max-width:560px}.hero-mark{font:italic 76px/1 Georgia,serif;color:#c5d1c4}.tools{display:grid;grid-template-columns:1fr 1fr;border:1px solid #cbd6ca;background:#e8eee5}.tool{padding:19px 24px;text-decoration:none;display:flex;justify-content:space-between;gap:16px;align-items:center}.tool+.tool{border-left:1px solid #cbd6ca}.tool:hover{background:#dce8dc}.tool strong{display:block;font-size:15px}.tool small{display:block;color:#6b7c70;font-size:12px}.section-head{display:flex;justify-content:space-between;align-items:end;gap:20px;margin:55px 0 17px}.section-head h2{font:600 27px/1.3 "Songti SC",serif;margin:0}.section-head p{margin:0;color:#758277;font-size:13px}.book{border-top:1px solid #bbcbbd}.book:last-child{border-bottom:1px solid #bbcbbd}.book summary{list-style:none;display:flex;align-items:center;gap:25px;cursor:pointer;padding:22px 5px}.book summary::-webkit-details-marker{display:none}.book summary:hover .book-name{color:#437759}.book-number{font:italic 15px Georgia,serif;color:#ad7456}.book-name{font:600 22px/1.4 "Songti SC",serif;flex:1}.book-name small{display:block;margin-top:3px;font:12px/1.5 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;color:#849186}.toggle{width:26px;height:26px;border:1px solid #a9bbac;border-radius:50%;position:relative;flex:none}.toggle:before,.toggle:after{content:"";position:absolute;background:#4c6a57;left:7px;right:7px;top:11px;height:1px}.toggle:after{transform:rotate(90deg)}details[open] .toggle:after{display:none}.book-body{padding:0 5px 30px 44px}.book-actions{display:flex;justify-content:space-between;gap:15px;font-size:13px;color:#718074;border-bottom:1px solid #e0e6dc;padding:0 0 14px}.book-actions a{color:#38694d;white-space:nowrap}.chapters{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 44px}.chapter{padding:22px 0 4px}.chapter h3{font-size:15px;margin:0 0 8px;color:#304d3b}.chapter ul{list-style:none;margin:0;padding:0}.chapter li{border-bottom:1px solid #e4e9e1}.chapter li a,.unavailable{display:flex;justify-content:space-between;gap:12px;padding:8px 0;text-decoration:none;color:#596f60;font-size:14px}.chapter li a:hover{color:#1d6140}.chapter li a span{color:#91a494}.unavailable{color:#98a39b}.unavailable small{white-space:nowrap}.foot{margin-top:55px;padding:25px 0;border-top:1px solid #cbd6ca;display:grid;grid-template-columns:1fr 1fr;gap:28px;color:#718074;font-size:12px}.foot strong{color:#435c4b;font-size:13px}.foot p{margin:6px 0}.foot a{color:#416e50}.foot-links{display:flex;gap:16px;flex-wrap:wrap}.foot time{overflow-wrap:anywhere}@media(max-width:650px){main{padding:0 20px 50px}.topline{padding:18px 0}.topline span{font-size:10px}.hero{padding:42px 0 34px}.hero-mark{display:none}.tools{grid-template-columns:1fr}.tool+.tool{border-left:0;border-top:1px solid #cbd6ca}.section-head{align-items:start;flex-direction:column;gap:5px;margin-top:42px}.book summary{gap:14px}.book-name{font-size:19px}.book-body{padding-left:28px}.book-actions{align-items:start;flex-direction:column;gap:5px}.chapters,.foot{grid-template-columns:1fr}.foot{gap:12px}}
    '''
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>沪教数学 · 五册教材教参整合</title><style>{css}</style>{access_head('../_shared/')}</head><body><noscript><p>请启用 JavaScript，再输入访问口令进入阅读。</p></noscript><main><header class="topline"><strong>沪教数学 · 教材教参</strong><span>LOCAL READING / 本地阅读</span></header><section class="hero"><div><div class="eyebrow">TEXTBOOK & TEACHING NOTES</div><h1>教材与教参，一起读。</h1><p>沿着教材的章节脉络，找到原题、原图与教师视角。展开册次，即可跳转到需要的内容。</p></div><div class="hero-mark" aria-hidden="true">05.</div></section><nav class="tools" aria-label="专题入口"><a class="tool" href="deep-index.html"><span><strong>深度探究</strong><small>走进值得细看的数学问题</small></span><span aria-hidden="true">↗</span></a><a class="tool" href="visual-index.html"><span><strong>可视化总览</strong><small>用动态图观察与理解</small></span><span aria-hidden="true">↗</span></a></nav><section aria-labelledby="books-title"><div class="section-head"><div><div class="eyebrow">THE COLLECTION</div><h2 id="books-title">五册目录</h2></div><p>点击册名展开大纲 · 节名直达教师阅读</p></div><div class="book-list">{''.join(books)}</div></section><footer class="foot"><div><strong>关于本套内容</strong><p>包含必修三册与选择性必修两册，不含数学建模活动册。教师页含答案，学生分享请使用整册目录中的独立学生包。</p><div class="foot-links"><a href="章节修复记录-20261020.md">章节修复记录</a><a href="交付与核验说明.md">使用与核验说明</a></div></div><div><strong>显示与打印检查</strong><p>{totals['validated']} / {totals['sections']} 个节点通过；{totals['blocked']} 个需修复，{totals['queued']} 个待检查。显示与打印通过不等于全书逐题数学审定；可视化专项检查另见总览。</p><p>检查记录更新：<time>{escape(updated_at)}</time></p></div></footer></main></body></html>'''
