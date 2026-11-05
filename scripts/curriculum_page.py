"""Build the offline curriculum reader without rebuilding textbook chapters."""
import argparse
import copy
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import subprocess

from bs4 import BeautifulSoup

from site_access import access_head

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'outputs/五册教材教参整合'
ASSETS = OUTPUT / 'curriculum-2025'


CASE_TITLE = re.compile(r'^案例\s*(\d+)\s+(.+)$')
CASE_REFERENCE = re.compile(r'参见案例\s*(\d+(?:\s*[，,、~～〜至\-]\s*\d+)*)')


def reviewed_source(raw):
    corrections = json.loads((ASSETS / 'corrections.json').read_text())
    if hashlib.sha256(raw).hexdigest() != corrections['source_sha256']:
        raise ValueError('原稿指纹与校订依据不符，请先核对并更新 corrections.json')
    text = raw.decode('utf-8')
    rows = corrections['case14_sample_rows']
    if len(rows) != 20 or any(len(row) != 10 for row in rows):
        raise ValueError('案例 14 应有 20 行、每行 10 个数据')
    table = '<table class="sample-data"><caption>200 户居民六月用电量（kW·h）</caption>' + ''.join(
        '<tr>' + ''.join(f'<td>{value}</td>' for value in row) + '</tr>' for row in rows) + '</table>'
    start = text.index('案例 14 阶梯电价的设计')
    end = text.index('案例 15 ', start)
    case = text[start:end]
    begin = case.index('数据如下:') + len('数据如下:')
    finish = case.index('根据以上数据')
    case = case[:begin] + '\n\n' + table + '\n\n' + case[finish:]
    text = text[:start] + case + text[end:]
    text = text.replace('案例 33 “互联网十”', '案例 33 “互联网+”')
    text = text.replace('学生学\n\n习的数据报告', '学生学习的数据报告')
    return text, corrections


def reference_numbers(text):
    numbers = []
    for part in re.split(r'\s*[，,、]\s*', text):
        bounds = re.split(r'\s*[~～〜至\-]\s*', part)
        if len(bounds) == 1:
            numbers.append(int(bounds[0]))
        elif len(bounds) == 2 and int(bounds[0]) <= int(bounds[1]):
            numbers.extend(range(int(bounds[0]), int(bounds[1]) + 1))
        else:
            raise ValueError(f'Unexpected case reference: {text}')
    return numbers


def place_cases(soup):
    appendix = next((node for node in soup.find_all('h2', recursive=False)
                     if node.get_text(' ', strip=True).startswith('附录 2 ')), None)
    if appendix is None:
        raise ValueError('未找到教学与评价案例附录')
    cases = {}
    case_nodes = []
    active = None
    for node in list(appendix.next_siblings):
        title = CASE_TITLE.match(node.get_text(' ', strip=True)) if getattr(node, 'name', None) in ('p', 'h2') else None
        if title:
            number = int(title.group(1))
            if number in cases:
                raise ValueError(f'重复的案例标题: {number}')
            cases[number] = {'title': title.group(2), 'nodes': []}
            active = cases[number]
        if active is not None:
            active['nodes'].append(node)
            case_nodes.append(node)
    if set(cases) != set(range(1, 34)):
        raise ValueError(f'案例编号不完整: {sorted(cases)}')

    case_node_ids = {id(node) for node in case_nodes}
    references = []
    for node in list(soup.descendants):
        if not isinstance(node, str) or not CASE_REFERENCE.search(node):
            continue
        if any(id(parent) in case_node_ids for parent in node.parents):
            continue
        anchor = node.parent if node.parent.name in ('p', 'td', 'th') else node.parent.find_parent(['p', 'td', 'th'])
        if anchor is None:
            raise ValueError(f'案例引用无法定位: {node}')
        for match in CASE_REFERENCE.finditer(node):
            numbers = reference_numbers(match.group(1))
            if any(number not in cases for number in numbers):
                raise ValueError(f'案例引用不存在: {match.group(0)}')
            references.append((anchor, match.group(1), numbers))

    for node in case_nodes:
        node.extract()
    seen = set()
    insertions = []
    for index, (anchor, label, numbers) in enumerate(references, 1):
        group = soup.new_tag('details', attrs={'class': 'case-group', 'data-case-reference': ','.join(map(str, numbers))})
        summary = soup.new_tag('summary')
        summary.string = f'就地阅读案例 {label}（{len(numbers)} 个）'
        group.append(summary)
        for number in numbers:
            first = number not in seen
            seen.add(number)
            article = soup.new_tag('article', attrs={'class': 'curriculum-case', 'data-case': str(number),
                                                    'data-case-primary': str(first).lower(),
                                                    'id': f'case-{number}' if first else f'case-{number}-copy-{index}'})
            for original in cases[number]['nodes']:
                node = copy.deepcopy(original)
                if getattr(node, 'name', None):
                    for element in [node, *node.find_all(id=True)]:
                        if element.has_attr('id') and not first:
                            element['id'] = f'case-copy-{index}-{number}-' + element['id']
                    if node.name == 'h2':
                        node.name = 'h4'
                article.append(node)
            for text in list(article.find_all(string=CASE_REFERENCE)):
                matches = list(CASE_REFERENCE.finditer(text))
                cursor = 0
                for match in matches:
                    text.insert_before(text[cursor:match.start()])
                    target = reference_numbers(match.group(1))
                    if len(target) == 1:
                        link = soup.new_tag('a', href=f'#case-{target[0]}')
                        link.string = match.group(0)
                        text.insert_before(link)
                    else:
                        text.insert_before(match.group(0))
                    cursor = match.end()
                text.replace_with(text[cursor:])
            group.append(article)
        insertions.append((anchor, group))
    if seen != set(cases):
        raise ValueError(f'以下案例未被正文引用: {sorted(set(cases) - seen)}')
    for anchor, group in reversed(insertions):
        if anchor.name in ('td', 'th'):
            anchor.append(group)
        else:
            anchor.insert_after(group)

    catalog = soup.new_tag('div', attrs={'class': 'case-catalog'})
    catalog.append('案例已移至正文对应引用处；以下目录可直接定位：')
    case_list = soup.new_tag('ol')
    for number, case in cases.items():
        item = soup.new_tag('li')
        link = soup.new_tag('a', href=f'#case-{number}')
        link.string = case['title']
        item.append(link)
        case_list.append(item)
    catalog.append(case_list)
    appendix.insert_after(catalog)
    return len(references), sum(len(numbers) for _, _, numbers in references)


def render(source):
    raw = source.read_bytes()
    reviewed, corrections = reviewed_source(raw)
    converted = subprocess.run(
        ['pandoc', '--from=markdown', '--to=html', '--katex'], input=reviewed,
        check=True, capture_output=True, text=True).stdout
    soup = BeautifulSoup(converted, 'html.parser')
    original_title = soup.h1.get_text(' ', strip=True)
    soup.h1.decompose()
    reference_count, placement_count = place_cases(soup)
    images = []
    for image in soup.find_all('img'):
        relative = Path(image['src'])
        if relative.is_absolute() or '..' in relative.parts or relative.parts[0] != 'images':
            raise ValueError(f'Unexpected image path: {relative}')
        target = ASSETS / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if (source.parent / relative).resolve() != target.resolve():
            shutil.copy2(source.parent / relative, target)
        image['src'] = 'curriculum-2025/' + relative.as_posix()
        image['alt'] = image.get('alt') or f'课标原图 {len(images) + 1}'
        images.append(relative.as_posix())
    for table in list(soup.find_all('table')):
        wrapper = soup.new_tag('div', attrs={'class': 'table-scroll', 'tabindex': '0', 'role': 'region', 'aria-label': '课标表格，可横向滚动'})
        table.wrap(wrapper)
    sections = []
    current = None
    source_toc = soup.new_tag('details', attrs={'class': 'source-toc'})
    summary = soup.new_tag('summary')
    summary.string = '原稿页码目录'
    source_toc.append(summary)
    for node in list(soup.contents):
        if getattr(node, 'name', None) == 'h2':
            title = node.get_text(' ', strip=True)
            if title.replace(' ', '') == '目录':
                node.decompose()
                continue
            if re.match(r'^[一二三四五六七]、|^附录', title):
                current = soup.new_tag('section', attrs={'class': 'reading-section'})
                sections.append((title, node['id'], current))
            elif re.match(r'^[（(][一二三四五六七八九十]+[）)]', title):
                node.name = 'h3'
            else:
                node.name = 'h4'
        (current if current is not None else source_toc).append(node)
    navigation = []
    for number, (title, anchor, section) in enumerate(sections, 1):
        children = ''.join(f'<a href="#{heading["id"]}">{html.escape(heading.get_text(" ", strip=True))}</a>' for heading in section.find_all('h3'))
        child_links = f'<div class="sub-links">{children}</div>' if children else ''
        navigation.append(f'<div class="toc-group"><a class="chapter-link" href="#{anchor}"><span>{number:02d}</span>{html.escape(title)}</a>{child_links}</div>')
    css = (ROOT / 'scripts/curriculum_reader.css').read_text()
    script = (ROOT / 'scripts/curriculum_reader.js').read_text()
    page = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>课程标准 · 沪教数学</title><link rel="stylesheet" href="bx1/_shared/vendor-katex/katex.min.css"><style>{css}</style>{access_head('../_shared/')}<script defer src="bx1/_shared/vendor-katex/katex.min.js"></script><script defer src="curriculum-2025/reader.js"></script></head><body><a class="skip" href="#content">跳到正文</a><header class="topline"><a href="index.html">← 教材与教参</a><span>沪教数学 · 课程依据</span><a href="curriculum-2025/source.md" download>原稿 ↓</a></header><div class="layout"><aside id="directory"><div class="directory-head"><strong>阅读目录</strong><button id="close-directory" type="button" aria-label="关闭目录">×</button></div><label class="search-label" for="search">全文定位</label><div class="search-box"><input id="search" type="search" placeholder="搜索关键词，如：核心素养" autocomplete="off"><button id="clear-search" type="button" aria-label="清空搜索">×</button></div><p id="search-status" role="status" aria-live="polite">输入关键词，定位到原文段落</p><div id="search-results"></div><nav aria-label="课标章节目录">{''.join(navigation)}</nav><div class="sidebar-note">2017 年版 · 2025 年修订<br>全文阅读 / 本地公式与图片</div></aside><main id="content"><div class="eyebrow">CURRICULUM / 数学课程标准</div><h1>普通高中数学<br>课程标准</h1><div class="edition"><span>2017 年版 · 2025 年修订</span><a href="#一课程性质">开始阅读 ↓</a></div><p class="intro">从课程目标到教学实施，沿着学科核心素养，查阅课程内容、学业要求与评价建议。</p><details class="source-note"><summary>来源与阅读说明 <span>OCR 转录，非官方发布页</span></summary><p>原稿名称：{html.escape(original_title)}。本页保留所提供转录稿的正文、图表与公式；案例可在正文引用处展开，同一案例多次引用时重复呈现。未逐条校订 OCR，亦未核验是否为官方最新版本。原稿第 1077 行列联表及案例 14 表格有识别或排版异常，案例 33 在原稿末尾截断；正式引用请核对权威原件。</p><a href="curriculum-2025/source.md" download>下载可编辑 Markdown 原稿</a><p id="math-status" role="status">公式准备中。</p></details>{source_toc}{''.join(str(section) for _, _, section in sections)}<footer class="reader-foot"><span>全文完 · 回到课程与教学本身</span><a href="index.html">返回教材主页 →</a></footer></main></div><div class="mobile-tools"><button id="open-directory" type="button" aria-controls="directory" aria-expanded="false">目录 / 搜索</button><a href="#content">回到顶部 ↑</a></div><button id="directory-backdrop" type="button" aria-label="关闭目录" hidden></button><noscript><p>请启用 JavaScript，以使用全文定位、公式渲染与站内访问入口。</p></noscript></body></html>'''
    page = page.replace('原稿第 1077 行列联表及案例 14 表格有识别或排版异常，案例 33 在原稿末尾截断；正式引用请核对权威原件。', '已对照用户提供的同版本 PDF：案例 14 的 200 项原始数据已补齐并与排序表逐项核对（PDF 第 126—128 页，印刷页 123—125）；案例 33 在印刷页 167 正常结束，无缺文，已修正标题中的加号及跨页断行。其他内容未逐条审校，原稿第 1077 行列联表仍待核。')
    page = page.replace('<p id="math-status"', '<p><a href="curriculum-2025/reviewed.md" download>下载局部校订版 Markdown</a> · <a href="curriculum-2025/corrections.json">查看校订依据</a></p><p id="math-status"')
    ASSETS.mkdir(parents=True, exist_ok=True)
    if source.resolve() != (ASSETS / 'source.md').resolve():
        shutil.copy2(source, ASSETS / 'source.md')
    (ASSETS / 'reader.js').write_text(script)
    (ASSETS / 'reviewed.md').write_text(reviewed)
    (OUTPUT / 'curriculum-2025.html').write_text(page)
    metadata = {'source_title': original_title, 'source_sha256': hashlib.sha256(raw).hexdigest(), 'images': images, 'tables': len(soup.find_all('table')) + sum(len(section.find_all('table')) for _, _, section in sections), 'math': sum(len(section.select('.math')) for _, _, section in sections), 'chapters': len(sections), 'case_references': reference_count, 'case_placements': placement_count}
    metadata.update({'reviewed_sha256': hashlib.sha256(reviewed.encode('utf-8')).hexdigest(), 'corrections_sha256': hashlib.sha256((ASSETS / 'corrections.json').read_bytes()).hexdigest(), 'reference_pdf_sha256': corrections['pdf_sha256']})
    (ASSETS / 'build.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(metadata, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ASSETS / 'source.md')
    render(parser.parse_args().source)
