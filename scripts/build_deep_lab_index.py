#!/usr/bin/env python3
"""A compact, single-active-frame entry for the seven deep textbook investigations."""

from project_paths import use_project_root, launch_browser
use_project_root()
import html
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/五册教材教参整合/deep-index.html'
FAMILIES = ('deep-geometry', 'deep-analysis', 'deep-spatial')
ORDER = ('chord-midpoint-domain', 'parameter-cubic-roots', 'line-plane-minimum-angle',
         'counting-equal-multiplicity', 'bayes-base-rate', 'ssa-circle-ray', 'cube-plane-transitions')

def main():
    assets = {a['id']: a for family in FAMILIES for a in json.loads((ROOT / f'scripts/textbook-labs/{family}.json').read_text(encoding='utf-8'))['assets']}
    items = []
    for asset_id in ORDER:
        a = assets[asset_id]
        placements = []
        for p in a['placements']:
            sid = p['sectionId']; book = sid.split('-')[0]
            section = json.loads((ROOT / f'batch/sections/{book}/{sid}.json').read_text(encoding='utf-8'))
            placements.append({'label': section['book_title'] + ' ' + section['section'] + ' ' + section['title'],
                               'teacher': f'{book}/{sid}/teacher.html#{p["afterBlockId"]}',
                               'student': f'{book}/{sid}/student.html#{p["afterBlockId"]}'})
        items.append({'id': asset_id, 'title': a['title'], 'goal': a['goal'], 'placements': placements,
                      'html': (ROOT / f'scripts/visual-assets/textbook-{asset_id}.html').read_text(encoding='utf-8')})
    buttons = ''.join(f'<button class="topic" data-index="{i}" aria-pressed="false"><span class="num">{i+1:02}</span><span>{html.escape(a["title"].replace("深度探究 · ", ""))}</span></button>' for i,a in enumerate(items))
    document = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>七个深度探究 · 沪教教材交互</title><style>
:root{--paper:#f6f4e9;--ink:#243b31;--muted:#677668;--line:#d7dfd0;--green:#315e4b;--rust:#a55b35}*{box-sizing:border-box}body{margin:0;background:linear-gradient(115deg,#eeefe3,#fffdf4 65%,#edf2e9);color:var(--ink);font:14px/1.65 "PingFang SC","Microsoft YaHei",sans-serif}main{max-width:1420px;margin:auto;padding:25px 30px}header{display:flex;align-items:baseline;justify-content:space-between;gap:20px;border-bottom:1px solid var(--line);padding-bottom:14px}h1{font:600 29px/1.3 "Songti SC","STSong",serif;margin:5px 0}small,.muted{color:var(--muted)}.overline{letter-spacing:.16em;font-size:11px;color:var(--rust)}a{color:var(--green);text-underline-offset:4px}header nav{display:flex;gap:16px;white-space:nowrap}.layout{display:grid;grid-template-columns:260px minmax(0,1fr);gap:24px;margin-top:20px}.topics{display:grid;gap:7px;align-content:start}.topic{display:flex;text-align:left;gap:12px;align-items:center;border:1px solid var(--line);background:#fffdf6;padding:13px 10px;color:var(--ink);cursor:pointer;font:13px/1.55 "PingFang SC",sans-serif}.topic[aria-pressed=true]{background:var(--green);border-color:var(--green);color:#fffdf6}.num{font:italic 20px "Songti SC",serif;opacity:.6}.topic:focus-visible,a:focus-visible{outline:2px solid var(--rust);outline-offset:3px}.usage{font-size:12px;border-left:2px solid var(--rust);padding-left:10px;margin-top:14px}.stage{min-width:0;background:#fffef8;border:1px solid var(--line)}.stage-head{padding:17px 20px 12px;border-bottom:1px solid var(--line)}h2{font:600 22px/1.4 "Songti SC",serif;margin:0 0 5px}.stage-head p{margin:0;font-size:13px;color:var(--muted)}#chapter-links{padding:12px 20px;border-top:1px solid var(--line);font-size:12px}#chapter-links div{display:flex;gap:12px;flex-wrap:wrap;margin:4px 0}iframe{display:block;width:100%;border:0;height:630px}footer{font-size:11px;color:var(--muted);margin-top:16px}@media(max-width:850px){main{padding:18px 14px}.layout{grid-template-columns:1fr;gap:14px}.topics{grid-template-columns:1fr 1fr}.usage{grid-column:1/-1;margin:4px 0}.topic{padding:10px 8px}header{display:block}header nav{margin-top:10px}h1{font-size:25px}h2{font-size:20px}.stage-head{padding:14px}#chapter-links{padding:10px 14px}}@media print{.topics,iframe{display:none}.layout{display:block}.stage{border:0}}
</style></head><body><main><header><div><div class="overline">HUJIAO / DEEP INVESTIGATIONS</div><h1>让条件、临界与反例动起来</h1><small>7个主题 · 8处教材落点 · 每次只加载一个实验</small></div><nav><a href="index.html">五册教材</a><a href="visual-index.html">全部可视化</a></nav></header><div class="layout"><aside class="topics">BUTTONS<div class="usage">先动参数，看临界状态；再展开“条件与推导”。<br>这里的变动不修改教材编排。需打印或查看完整正文，请进入对应章节。</div></aside><section class="stage"><div class="stage-head"><h2 id="title"></h2><p id="goal"></p></div><iframe id="experiment" title="深度探究" sandbox="allow-scripts"></iframe><div id="chapter-links"></div></section></div><footer>概念实验不等于习题答案。选学与教师拓展不提升为统一必学要求；可动图像辅助理解，不替代证明。</footer></main><script>
const items=PAYLOAD, frame=document.querySelector('#experiment');let current;
const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function select(index){const item=items[index];current=item.id;document.querySelector('#title').textContent=item.title;document.querySelector('#goal').textContent=item.goal;document.querySelectorAll('[data-index]').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.index===index)));document.querySelector('#chapter-links').innerHTML=item.placements.map(p=>`<div><span>${esc(p.label)}</span><a href="${esc(p.teacher)}">进入教师版</a><a href="${esc(p.student)}">进入学生版</a></div>`).join('');const bridge='<script>(()=>{const report=()=>parent.postMessage({channel:"deep-gallery",id:'+JSON.stringify(item.id)+',height:Math.ceil(document.querySelector("main").getBoundingClientRect().height)+8},"*");new ResizeObserver(report).observe(document.querySelector("main"));addEventListener("load",report);report();})();<'+ '/script>';frame.title=item.title;frame.style.height='630px';frame.srcdoc=item.html.replace('</body>',bridge+'</body>');history.replaceState(null,'','#'+item.id)}
addEventListener('message',event=>{if(event.source===frame.contentWindow&&event.data?.channel==='deep-gallery'&&event.data.id===current&&Number.isFinite(event.data.height)){frame.style.height=Math.max(200,Math.min(4000,event.data.height))+'px'}});
document.querySelectorAll('[data-index]').forEach(b=>b.addEventListener('click',()=>select(+b.dataset.index)));select(Math.max(0,items.findIndex(a=>a.id===location.hash.slice(1))));
</script></body></html>'''.replace('BUTTONS',buttons).replace('PAYLOAD',json.dumps(items,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c'))
    OUT.write_text(document, encoding='utf-8')
    print(OUT)
if __name__ == '__main__':main()
