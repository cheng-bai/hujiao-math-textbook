#!/usr/bin/env python3
"""Check the local review dossier against its official source snapshots."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name):
    return json.loads((HERE/name).read_text(encoding='utf-8'))


inventory = load('708张图片定位与分类.json')['items']
samples = load('10张重绘小样清单.json')
ratings = load('30题难度校准与独立复核.json')
snapshot = load('30题原始校准样本.json')['items']
assert len(inventory) == 708 and len({x['original_path'] for x in inventory}) == 708
assert len({x['package_path'] for x in inventory}) == 708
for item in inventory:
    path = ROOT/item['original_path']
    packaged = HERE/item['package_path']
    assert path.is_file(), item['original_path']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], item['original_path']
    assert Image.open(path).size == (item['width'], item['height'])
    assert packaged.is_file() and hashlib.sha256(packaged.read_bytes()).hexdigest() == item['sha256'], item['package_path']
    assert Image.open(packaged).size == (item['width'], item['height'])
assert len(samples) == 10 and len(ratings['items']) == 30 and len(snapshot) == 30
assert [r['question_id'] for r in ratings['items']] == [x['block']['id'] for x in snapshot]
for rating in ratings['items']:
    source = json.loads((ROOT/rating['source_json']).read_text(encoding='utf-8'))
    block = next(b for b in source['blocks'] if b.get('id') == rating['question_id'])
    actual = hashlib.sha256(json.dumps(block, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    assert actual == rating['source_block_sha256'], rating['question_id']
for sample in samples:
    src = ROOT/sample['original_path']
    svg = HERE/sample['svg']
    assert src.is_file() and svg.is_file()
    root = ET.parse(svg).getroot()
    assert root.tag.endswith('svg')
    assert not root.findall('.//{http://www.w3.org/2000/svg}image')
    assert root.findall('.//{http://www.w3.org/2000/svg}path')
assert ratings['agreement']['eligible'] == 26
assert ratings['agreement']['initial_same_star'] == 22
assert abs(ratings['agreement']['eligible_agreement']-22/26) < 1e-12
assert ratings['freeze_status'].startswith('未冻结')
class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.urls = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('src', 'href') and value:
                self.urls.append(value)

def check_local(base, url):
    parts = urlsplit(url)
    assert not parts.scheme and not parts.netloc, url
    if not parts.path:
        return
    path = (base/unquote(parts.path)).resolve()
    assert path.is_relative_to(HERE) and path.is_file(), url

link_count = 0
for page in ['index.html', 'images.html', 'difficulty.html']:
    parser = Links(); parser.feed((HERE/page).read_text(encoding='utf-8'))
    for url in parser.urls:
        check_local(HERE, url); link_count += 1
css = HERE/'assets/vendor-katex/katex.min.css'
font_urls = re.findall(r'url\(["\']?([^"\')]+)', css.read_text(encoding='utf-8'))
assert font_urls
for url in font_urls:
    check_local(css.parent, url)
assert (HERE/'assets/site-access.js').is_file()
print(json.dumps({'source_images':len(inventory), 'unique_source_images':len({x['original_path'] for x in inventory}),
                  'svg_samples':len(samples), 'calibration_questions':len(ratings['items']),
                  'eligible_initial_agreement':'22/26', 'freeze_status':ratings['freeze_status'],
                  'originals_and_packaged_hash_verified':True, 'all_svg_files_parse':True,
                  'local_page_links_checked':link_count, 'font_references_checked':len(font_urls)}, ensure_ascii=False, indent=2))
