#!/usr/bin/env python3
"""Build the local review dossier. Rating judgements are explicit, not auto-inferred."""
import csv
import hashlib
import html
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

from PIL import Image
from redraw_samples import make_drawings

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from batch_render import approved_components

render_md = approved_components([], {})['render_md']


def save_json(name, data):
    (OUT/name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def md(text):
    return render_md(text.replace('](sources/textbooks/', '](assets/source-images/'))


def make_inventory(samples):
    catalog=json.loads((ROOT/'batch/manifests/catalog.json').read_text(encoding='utf-8'))
    sample_by_name={s['original_basename']:s for s in samples}
    source_cache={};rows=[]
    for book in catalog['books']:
        for ch in book['chapters']:
            for section in ch['sections']:
                d=json.loads((ROOT/section['path']).read_text(encoding='utf-8'))
                for i,ref in enumerate(d.get('image_references', []),1):
                    path=ROOT/ref['absolute'];raw=path.read_bytes();width,height=Image.open(path).size
                    source=d['sources'][ref['source']]
                    if source not in source_cache:source_cache[source]=(ROOT/source).read_text(encoding='utf-8').splitlines()
                    lines=source_cache[source];ln=ref['line']
                    context='\n'.join(lines[max(0,ln-4):ln+5])
                    uses=[]
                    for block in d['blocks']:
                        for field in ['markdown','answer','teacher_analysis']:
                            if path.name in block.get(field,''):
                                kind={'answer':'答案解析','teacher_analysis':'教学分析'}.get(field,{'question':'题目配图','teacher':'教学建议','prose':'正文插图'}.get(block['type'],'正文插图'))
                                uses.append({'block_id':block.get('id'),'block_title':block.get('title'),'field':field,'usage':kind})
                    s=sample_by_name.get(path.name)
                    if s: content_type='数学结构图（小样已逐图核对）'
                    elif width>=1500 and height>=900:content_type='大幅插图候选（可能含章首照片）'
                    elif width/height>=4.5:content_type='横向图组／表格／文字条候选'
                    else:content_type='一般插图（内容类型待视觉确认）'
                    role='教材' if ref['source']=='book' else '教参'
                    proposed=(Path(s['svg']).name if s else f'{section["id"]}_{role}_节内插图{i:03}.svg')
                    row={'asset_id':'img-'+hashlib.sha256(raw).hexdigest()[:16], 'book_id':book['id'],'book_title':book['title'],
                         'chapter_title':ch['title'],'section_id':section['id'],'section_title':section['title'],'source_role':role,
                         'original_path':ref['absolute'],'package_path':str(Path('assets/source-images')/Path(ref['absolute']).relative_to('sources/textbooks')),'source_markdown':source,'source_line':ln,'printed_page':None,
                         'verified_figure':s['figure'] if s else None,'width':width,'height':height,'bytes':len(raw),
                         'short_edge_band':'<300' if min(width,height)<300 else ('300–599' if min(width,height)<600 else '≥600'),
                         'sha256':hashlib.sha256(raw).hexdigest(),'usage':sorted({u['usage'] for u in uses}), 'uses':uses,
                         'classification':content_type,'classification_status':'小样人工核对' if s else '位置已核对；内容初分待视觉核验',
                         'proposed_svg_name':proposed,'sample_svg':s['svg'] if s else None,'context_excerpt':context}
                    rows.append(row)
                    if s:s.update({'original_path':ref['absolute'],'package_path':row['package_path'],'source_markdown':source,'source_line':ln,'book_title':book['title'],'section_title':section['title'],'asset_id':row['asset_id']})
    assert len(rows)==708 and len({r['original_path'] for r in rows})==708
    assert {str(p.relative_to(ROOT)) for p in (ROOT/'sources/textbooks').rglob('*.jpg')}=={r['original_path'] for r in rows}
    save_json('708张图片定位与分类.json', {'scope':'正式目录引用图片；708张的语义分类尚未全部人工确认。','items':rows})
    fields=['asset_id','book_title','section_id','section_title','source_role','source_markdown','source_line','printed_page','verified_figure','original_path','package_path','width','height','bytes','short_edge_band','classification','classification_status','proposed_svg_name','sha256']
    with (OUT/'708张图片定位与分类.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    save_json('10张重绘小样清单.json',samples)
    return rows


PRIMARY=[1,2,2,2,2,4,1,2,3,2,1,3,1,2,3,2,1,2,2,3,1,3,None,3,2,2,2,3,2,3]
SECOND=[1,2,2,2,2,4,1,2,3,2,2,3,1,2,3,2,2,2,2,3,1,4,None,3,2,3,2,3,2,4]
SUBS=[[],[],[2,1],[2,2,2,2],[2,2],[2,4,2],[1,1,1,1],[],[],[],[2,1,1],[3,3],[1,1],[],[1,3],[],[2,2],[],[],[],[],[],[],[],[],[3,1,2,2],[2,2],[],[],[]]
EVIDENCE=[
 '两点斜率公式直接给出 $k=4/3$，再由 $0<\\theta<\\pi/2$ 得 $\\theta=\\arctan(4/3)$。入口明确，不因出现反三角记号升星。',
 '距离公式化为 $|3a-28|/5=4$，保留绝对值的两个分支，得 $a=8/3$ 或 $16$。',
 '第(1)问先除以144得标准式，再用 $c^2=a^2+b^2$；第(2)问已是标准式，只需识别焦轴在 $y$ 轴。两问分别2星、1星。',
 '沿棱作有向路径分解，四个结果依次为 $\\vec a+\\vec b+\\vec c$、$\\vec b-\\vec c$、$\\vec a+\\vec c-\\vec b$、$2\\vec a+\\vec b+\\vec c$。重点是反向符号与 $CE=2CC_1$，不是新构造。',
 '将已知项与前项和转为 $a_1,d$ 的二元一次方程，代入求和公式。两问核得 $44$、$-82/5$。',
 '第(1)问 $L_n=3(4/3)^{n-1}$；第(2)问需把每轮新增三角形的个数与面积相乘，再累加等比数列，得到 $A_n=2\\sqrt3/5-(3\\sqrt3/20)(4/9)^{n-1}$；第(3)问可引用前问，极限为 $2\\sqrt3/5$。主要门槛在新增面积的组织。',
 '按有限集与无限集定义判断。数量很大仍可能有限，线段长度有限不意味着点的个数有限。四问均为直接概念识别。',
 '除以参数前分 $a=0$ 与 $a\\ne0$；分别为空集与 $\\{2/a\\}$。分类局部而直接。',
 '把原式转为 $|x-1|\\le |x+2|+3$，识别三角不等式；等号条件 $(x+2)(-3)\\ge0$ 给出 $x\\le-2$。需要完成转化和等号闭合。',
 '对应点由 $(a,1/a)$ 变为 $(a+2,1/a)$，解释向右平移2；作图须同步移动竖直渐近线，不能只移动一条分支。',
 '第一幅的值域为 $[0,1]\\cup\\{2\\}$，必须保留孤立值2；另外两幅分别为 $[0,2]$、$[-1,3]$。图像读取中的离散值筛选使第一问不是机械读区间。',
 '反函数定义域是 $f(\\mathbf R)$。奇性要先证明该值域关于原点对称，再用逆对应证明；保序性需取两个值域元素并比较其原像。',
 '分别加减整周角得到120°与300°，因此为第二、第四象限。两问均为直接应用。',
 '和角公式给出 $\\tan(\\alpha+\\beta)=-1$，结合 $0<\\alpha+\\beta<\\pi$ 得 $3\\pi/4$；范围用于排除周期歧义。',
 '第一问直接用第一象限单调性。第二问先化为 $-\\sin(\\pi/11)$ 与 $-\\sin(\\pi/12)$，再比较；周期、诱导公式与单调性形成依赖链。',
 '夹角在 $[0,\\pi]$，由 $\\sin\\theta=0.6$ 得 $\\cos\\theta=\\pm0.8$。数量投影为 $\\pm4.8$，投影向量为 $\\pm(24/25)\\vec a$，两处符号对应一致。',
 '需把四周期推广到任意整数指数（含0与负整数），再提出 $i^m$，由 $1+i+i^2+i^3=0$ 得和为0。这比只计算四个正整数次幂多一步概括。',
 '共轭给出 $z_1-z_2=-2-3i$，用平方差得 $(3-5i)(-2-3i)=-21+i$；不必分别求两个复数。',
 '取 $AB$ 中点 $M$；由两点在面内得直线 $AB$ 在面内，继而 $M$ 在面内；再得中线 $CM$ 在面内，重心 $G$ 在面内。',
 '将 $AB\\perp PC$、$AB\\perp PD$ 汇聚成 $AB\\perp$ 平面 $PCD$，再得 $AB\\perp CD$。两条线面垂直条件需要通过辅助平面连接。',
 '正六边形底面积为 $6\\sqrt3$，乘高4得到 $24\\sqrt3$；直接应用柱体体积公式。',
 '在标准正放构型下，正方体边长 $s$ 满足 $s/\\sqrt2=r(h-s)/h$，解得 $s=\\sqrt2rh/(h+\\sqrt2r)$。但题块没有配图，必须确认“内接”具体构型后才能定星。',
 '若黑白棋子各至少2粒，有限总体不放回抽取时，同色概率不小于 $1/3$；给定两概率之和却为 $13/42<1/3$。形式相加虽简单，模型条件不可实现，不能确定星级。',
 '样本中位数为 $(1223+1239)/2=1231$，不是1226。“基本奖50%中的至多10%”对应总体至多5%，不是10%；应考察第95百分位数。样本上半月与奖励整月周期也不一致，抽样估计不能保证总体比例。',
 '本节用差商定义：$[5(2+h)^2-20]/h=20+5h$，令 $h\\to0$ 得20 m/s。不能用后学求导法则将概念任务降为一行代入。',
 '第(1)问需构造“某极大值低于另一极小值”的反例；第(2)问直接由定义成立；第(3)(4)问区分局部极值与全局最值。可用 $f(x)=x+2\\sin x$ 跨周期的极值作为第(1)问反例。',
 '按字面允许1至4位：总数 $4+12+24+24=64$；偶数按末位为2或4计数，$2+6+12+12=32$。原答案24、12仅对应四位数，不能静默补入“四位”。',
 '一次项系数得 $m+n=11$；二次项系数为 $(m^2+n^2-11)/2$，定和下平方和最小须在正整数中取相邻的5与6。',
 '均值为100，区间[80,120]关于均值对称，区间外概率为1/4，两尾各1/8。所求人数为 $1600/8=200$，选D。',
 '80组数据复算得到 $r=-0.3609897$、线性回归 $y=-925.265535x+31291.279929$。对数变换给出 $y=31599.619523e^{-0.068655659x}$。难点是模型诊断和变换选择，不是数据行数；指数拟合仍只是探索性候选，不推出因果。'
]
DISPUTES={
 11:'主评1星、复核2星。复议保留2星：第一幅包含孤立值2，要进行取值集合筛选，而非只读上下界。',
 17:'主评1星、复核2星。复议保留2星：题目要求找规律并覆盖任意整数指数，含从计算到概括的转换。',
 22:'主评3星、复核4星候选。暂不解决：先核对原页的内接构型；不以高星掩盖条件缺失。',
 26:'主评2星、复核3星。复议保留3星：第一小问必须给出有效反例或论证，不能只凭概念印象判断。',
 30:'主评3星、复核4星。复议保留4星：题面未指定模型，线性诊断、变量变换和结果解释构成方法选择负担。'
}


def make_ratings():
    raw=json.loads((OUT/'30题原始校准样本.json').read_text(encoding='utf-8'))
    rows=[];blocked={22:'构型待核',23:'模型数据冲突',24:'原解与周期问题',27:'题答范围不一致'}
    for n,item in enumerate(raw['items'],1):
        b=item['block'];row={'number':n,'question_id':b['id'],'book_id':item['book_id'],'book_title':item['book_title'],
                            'section_title':item['section_title'],'primary_star':PRIMARY[n-1], 'independent_star':SECOND[n-1],
                            'suggested_star':None if n in blocked else SECOND[n-1], 'subquestion_stars':SUBS[n-1],
                            'status':blocked.get(n,'双评复议完成'),'evidence_markdown':EVIDENCE[n-1],
                            'discussion':DISPUTES.get(n,'初评同星；保留具体数学依据。' if n!=23 else '双方均认为不能对矛盾模型定星。'),
                            'source_json':item['source_json'],'source_provenance':b.get('provenance_question',b.get('provenance',[])),
                            'source_block_sha256':hashlib.sha256(json.dumps(b,ensure_ascii=False,sort_keys=True).encode()).hexdigest()}
        if n==24:row['discussion']='双方候选3星，但原解需修复且计奖周期需明确，暂不进入量表冻结。样本P95=1752，严格高于此数的1人占基本奖15人的1/15。'
        if n==27:row['discussion']='双方候选2星；独立复核最初将偶数总数误写44，经按位数重新计数更正为32。题答范围冲突仍未解决。'
        rows.append(row)
    comparable=[r for r in rows if r['suggested_star'] is not None]
    same=sum(r['primary_star']==r['independent_star'] for r in comparable)
    data={'rubric':'教学结构五星试行-v0.1','not_hct':True,'scope':'相对所属课程；只用当前节与前置知识；非实测正确率。',
          'selection':raw['selection'],'independent_review':'独立agent未见主评星级；双方均读取来源答案，属于回顾性分析。',
          'agreement':{'sampled':30,'eligible':len(comparable),'initial_same_star':same,'eligible_agreement':same/len(comparable),
                       'one_star_disagreements':[r['question_id'] for r in comparable if r['primary_star']!=r['independent_star']],
                       'unresolved_source_items':[r['question_id'] for r in rows if r['suggested_star'] is None]},
          'freeze_status':'未冻结：尚有4题来源/模型/范围待核；没有已确认的五星边界样例。本轮不启动全量打标。', 'items':rows}
    save_json('30题难度校准与独立复核.json',data)
    with (OUT/'30题难度校准与独立复核.csv').open('w',newline='',encoding='utf-8-sig') as f:
        fields=['number','question_id','book_title','primary_star','independent_star','suggested_star','status','discussion'];w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    return data,raw


CSS='''
:root{--ink:#24332e;--muted:#64746b;--line:#d6ded7;--paper:#f5f4ed;--accent:#246a52;--warn:#955c21}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 "Songti SC","Noto Serif CJK SC",serif}header,main{max-width:1320px;margin:auto;padding:24px 30px}header{border-bottom:1px solid var(--line);background:linear-gradient(120deg,#f5f4ed,#e6eee6)}h1{font-size:32px;line-height:1.25;margin:12px 0}h2{font-size:24px;margin:12px 0}h3{font-size:19px;margin:0 0 10px}.muted,.meta{color:var(--muted);font:13px/1.7 "PingFang SC",sans-serif}.meta{overflow-wrap:anywhere}a{color:var(--accent);text-underline-offset:3px}nav{display:flex;gap:20px;flex-wrap:wrap;font:15px "PingFang SC",sans-serif;margin:20px 0 6px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}.metric{padding:12px 16px;border-left:3px solid var(--accent);background:#fff}.metric b{font:30px Georgia,serif;display:block}.note{padding:14px 18px;border-left:3px solid var(--warn);background:#fff7e9;margin:14px 0}.card{background:#fff;border:1px solid var(--line);padding:20px;margin:18px 0;break-inside:avoid}.compare{display:grid;grid-template-columns:1fr 1fr;gap:18px}.frame{background:#fff;border:1px solid var(--line);padding:12px;text-align:center}.frame img{width:100%;height:300px;object-fit:contain}.frame label{display:block;text-align:left;font:13px "PingFang SC",sans-serif;color:var(--muted)}.pill{display:inline-block;padding:3px 9px;border:1px solid var(--line);border-radius:3px;font:13px "PingFang SC",sans-serif;margin:3px 4px 3px 0}.stars{color:var(--accent);font-family:Georgia,serif;letter-spacing:2px}.question{font-size:17px}.question img{max-width:100%;max-height:380px;object-fit:contain}.question table,.source-table{overflow:auto;max-width:100%}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border-bottom:1px solid var(--line);padding:9px;text-align:left;vertical-align:top}th{font:13px "PingFang SC",sans-serif;background:#eaf0ea}.scroll{overflow:auto}details{margin-top:12px}summary{cursor:pointer;color:var(--accent)}.filters{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0;position:sticky;top:0;background:var(--paper);padding:12px 0;z-index:3}input,select,button{font:14px "PingFang SC",sans-serif;border:1px solid #a4b5a9;background:white;padding:9px 12px;border-radius:3px;color:var(--ink)}input{min-width:260px}.thumb{width:130px;height:95px;object-fit:contain;background:#fff}.math.display{overflow:auto;padding:6px 0}.source-table table{min-width:420px}.inventory td{font-size:13px}.inventory .meta{font-size:12px}.footer{font-size:13px;color:var(--muted);margin-top:30px}.hidden{display:none!important}@media(max-width:700px){header,main{padding:18px 16px}.metrics{grid-template-columns:1fr 1fr}.compare{grid-template-columns:1fr}.frame img{height:240px}h1{font-size:27px}.card{padding:14px}input{min-width:180px;width:100%}}@media print{nav,.filters,button,.footer{display:none!important}body{background:white;font-size:10pt}header,main{max-width:none;padding:0}h1{font-size:20pt}.card{border:0;border-top:1px solid #aaa;margin:10px 0;padding:10px 0;break-inside:auto}.compare,.question{break-inside:avoid}.frame img{height:210px}.metric b{font-size:20pt}.source-table{overflow:visible}.hidden{display:none!important}a{color:inherit;text-decoration:none}}
'''


def page(title, subtitle, body, extra=''):
    vendor='assets/vendor-katex/'
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><link rel="stylesheet" href="{vendor}katex.min.css"><style>{CSS}</style><link rel="stylesheet" href="assets/site-access.css"><script defer src="assets/site-access.js"></script></head><body><noscript><p>请启用 JavaScript，再输入访问口令进入阅读。</p></noscript><header><div class="meta">沪教数学教材 · 审阅样稿 · 2026-10-21</div><h1>{title}</h1><p>{subtitle}</p><nav><a href="index.html">10张高清重绘小样</a><a href="images.html">708张图片清单</a><a href="difficulty.html">30题难度校准</a><a href="README.md">说明与复现</a></nav></header><main>{body}<p class="footer">审阅资产不覆盖原图，不改题干与原答案；图片分类与难度量表仍待审定。</p></main><script src="{vendor}katex.min.js"></script><script>document.querySelectorAll('[data-tex]').forEach(e=>katex.render(e.dataset.tex,e,{{displayMode:e.dataset.display==='true',throwOnError:false,strict:'ignore',trust:false}}));</script>{extra}</body></html>'''


def build_pages(samples, inventory, ratings, raw):
    body='''<div class="metrics"><div class="metric"><b>708</b>原图定位与尺寸清单</div><div class="metric"><b>10</b>代码生成SVG小样</div><div class="metric"><b>5册</b>每册各2张重绘示例</div><div class="metric"><b>0</b>线上图片替换</div></div><div class="note">请重点审定：线条与字体是否清晰、数学条件是否保真、名称是否便于定位。图像是静态高清重建，不代表这些知识点都值得制作交互。708张已完成定位与用途归类；内容语义仅初分，不能视作708张均已人工分类验收。</div><p><a href="708张图片定位与分类.csv">下载图片清单 CSV</a> · <a href="10张重绘小样清单.json">重绘映射 JSON</a> · <a href="redraw_samples.py">绘图源代码</a></p>'''
    for s in samples:
        body+=f'''<section class="card" id="sample-{s['number']}"><span class="meta">{s['book_title']} · {s['section_id']} · {s['figure']}</span><h2>{s['number']:02} / {s['title']}</h2><div class="compare"><div class="frame"><label>教材原图 · 保留原文件</label><a href="{s['package_path']}"><img src="{s['package_path']}" alt="{s['title']}原图"></a></div><div class="frame"><label>SVG重绘 · 点击可放大</label><a href="{s['svg']}"><img src="{s['svg']}" alt="{s['title']}重绘"></a></div></div><p>{s['note']}</p><p class="meta">文件：{Path(s['svg']).name}<br>来源：{s['source_markdown']} L{s['source_line']} · 印刷页码尚未核实</p></section>'''
    (OUT/'index.html').write_text(page('教材图片，恢复成可维护的高清图','10张原图与重绘并排对照；数学结构由代码定义，来源保持可追溯。',body),encoding='utf-8')

    body='<div class="note">所有708张均有来源路径、行号、尺寸、哈希与用途定位。下列“内容类型”除10张小样外是候选分类，尚未逐张人工视觉确认；新文件名只是建议，未对原图改名。纸面页码未知时留空。</div><div class="filters"><input id="search" placeholder="搜索章节、图名、用途或原文件名"><select id="book"><option value="">全部五册</option>'+''.join(f'<option>{b}</option>' for b in sorted({r['book_title'] for r in inventory}))+'</select><span id="count">708张</span><a href="708张图片定位与分类.csv">CSV</a> · <a href="708张图片定位与分类.json">JSON</a></div><div class="scroll"><table class="inventory"><thead><tr><th>原图</th><th>教材位置与用途</th><th>尺寸与处理状态</th><th>建议名称与追溯</th></tr></thead><tbody>'
    for r in inventory:
        key=' '.join([r['book_title'],r['section_id'],r['section_title'],r['original_path'],' '.join(r['usage']),r['proposed_svg_name']])
        body+=f'<tr data-search="{html.escape(key,quote=True)}" data-book="{r["book_title"]}"><td><a href="{r["package_path"]}"><img class="thumb" loading="lazy" src="{r["package_path"]}" alt="{r["asset_id"]}"></a></td><td>{r["book_title"]}<br><b>{r["section_id"]} {r["section_title"]}</b><br>{r["source_role"]} · {" / ".join(r["usage"]) or "来源引用"}</td><td>{r["width"]} × {r["height"]} px<br>{r["classification"]}<br><span class="meta">{r["classification_status"]}</span></td><td>{r["proposed_svg_name"]}<details><summary>来源定位</summary><div class="meta">{r["source_markdown"]}<br>L{r["source_line"]}<br>{r["original_path"]}<br>{r["asset_id"]}</div></details></td></tr>'
    body+='</tbody></table></div>'
    script="""<script>function filter(){let n=0;document.querySelectorAll('tbody tr').forEach(r=>{let show=r.dataset.search.toLowerCase().includes(document.querySelector('#search').value.toLowerCase())&&(!document.querySelector('#book').value||r.dataset.book===document.querySelector('#book').value);r.hidden=!show;if(show)n++;});document.querySelector('#count').textContent=n+'张';}document.querySelector('#search').addEventListener('input',filter);document.querySelector('#book').addEventListener('change',filter);</script>"""
    (OUT/'images.html').write_text(page('708张图片定位与分类清单','原图保留来源并打包副本；记录用途、尺寸和可重绘状态。',body,script),encoding='utf-8')

    a=ratings['agreement'];body=f'''<div class="metrics"><div class="metric"><b>30</b>五册校准题块</div><div class="metric"><b>26</b>可进入当前有效比较</div><div class="metric"><b>{a['initial_same_star']}/26</b>初评同星（84.6%）</div><div class="metric"><b>4</b>来源/条件问题待处理</div></div><div class="note">量表尚未冻结。五星是相对所属课程的教学结构标尺，不是HCT换算，也不是学生实测正确率。样本每册6题，按题序等间距抽取，不代表各册难度分布。主评与独立agent均读取了原答案，属于回顾性分析；独立agent未见主评星级。四个来源问题不计入有效一致率。</div><p>1星：直接应用；2星：基础变式；3星：标准综合；4星：较高要求；5星：关键突破。有效样本中没有确认的五星题，不为凑档位抬高评分。</p><p><a href="30题难度校准与独立复核.csv">校准 CSV</a> · <a href="30题难度校准与独立复核.json">证据与复核 JSON</a> · <a href="30题原始校准样本.json">原题快照 JSON</a></p><div class="filters"><select id="status"><option value="all">全部30题</option><option value="blocked">仅来源待核4题</option><option value="disputed">仅初评分歧5题</option></select><button onclick="window.print()">打印当前内容</button></div>'''
    for r,item in zip(ratings['items'],raw['items']):
        n=r['number'];b=item['block'];stars='★'*r['suggested_star'] if r['suggested_star'] else '暂不定星'
        body+=f'<section class="card rating" id="q{n}" data-blocked="{str(r["suggested_star"] is None).lower()}" data-disputed="{str(r["primary_star"]!=r["independent_star"]).lower()}"><div class="meta">{n:02} / {r["book_title"]} · {r["section_title"]} · {r["question_id"]}</div><h2>{b["title"]}　<span class="stars">{stars}</span></h2><div><span class="pill">主评：{r["primary_star"] or "不定"}</span><span class="pill">独立复核：{r["independent_star"] or "不定"}</span><span class="pill">{r["status"]}</span></div><div class="question">{md(b["markdown"])}</div><div class="note"><b>数学依据与复议</b>{md(r["evidence_markdown"])}<p>{r["discussion"]}</p>'
        if r['subquestion_stars']:body+='<p class="meta">小问候选星级（按原题顺序）：'+ ' / '.join(str(v)+'星' for v in r['subquestion_stars'])+'；整题仅在可定星时显示最高小问星级。</p>'
        body+='</div><details><summary>展开来源答案（原文保留，不代表已通过本轮审校）</summary><div class="question">'+md(b.get('answer','无来源答案'))+'</div></details>'
        body+=f'<details><summary>来源位置</summary><div class="meta">{html.escape(json.dumps(r["source_provenance"],ensure_ascii=False))}<br>{r["source_json"]}</div></details></section>'
    script="""<script>document.querySelector('#status').addEventListener('change',e=>document.querySelectorAll('.rating').forEach(c=>c.classList.toggle('hidden',e.target.value!=='all'&&c.dataset[e.target.value]!=='true')));</script>"""
    (OUT/'difficulty.html').write_text(page('30题难度校准：先看证据，再定星','原题、主评、独立复核与分歧放在同一张题卡里；不把源材料冲突算成低难度。',body,script),encoding='utf-8')


def main():
    samples=make_drawings();inventory=make_inventory(samples)
    for item in inventory:
        target=OUT/item['package_path'];target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/item['original_path'],target)
    shutil.copytree(ROOT/'outputs/五册教材教参整合/bx1/_shared/vendor-katex',OUT/'assets/vendor-katex',dirs_exist_ok=True)
    for name in ('site-access.css','site-access.js'):
        shutil.copy2(ROOT/'outputs/_shared'/name,OUT/'assets'/name)
    ratings,raw=make_ratings();build_pages(samples,inventory,ratings,raw)
    save_json('结构核验.json',{'image_count':len(inventory),'unique_image_paths':len({r['original_path'] for r in inventory}),
      'original_images_untouched':True,'svg_count':len(samples),'rating_count':len(ratings['items']),
      'readable_source_files':all((ROOT/r['original_path']).is_file() for r in inventory),
      'svg_vector_only':all('<image' not in (OUT/s['svg']).read_text(encoding='utf-8') for s in samples),
      'note':'此文件只记录构建结构检查；浏览器、数学及印刷检查另见核验说明。'})
    print(json.dumps({'images':len(inventory),'svgs':len(samples),'calibration':ratings['agreement']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
