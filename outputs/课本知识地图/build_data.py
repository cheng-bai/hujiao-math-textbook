import re,json
from pathlib import Path
base=Path('outputs/教材真题框架工作区/framework.md')
text=base.read_text(); books={'必修第一册':'bx1','必修第二册':'bx2','必修第三册':'bx3','选择性必修第一册':'x1','选择性必修第二册':'x2'}
book=None; chapter=None; entries=[]; current=None
for line in text.splitlines():
 if line.startswith('### '):
  book=next((v for k,v in books.items() if line.startswith('### '+k+'：')),None)
  current=None
 elif book and line.startswith('#### '): chapter=line[5:]; current=None
 elif book:
  m=re.match(r'\d+\. \*\*([^*]+)\*\*(.*)',line)
  if m:
   title,rest=m.groups(); link=re.search(r'\]\((\.\./五册教材教参整合/[^)]+)\)',rest)
   if not link: continue
   desc=re.sub(r'\[整合教材定位\]\([^)]+\)','',rest).strip(' ：　')
   current={'book':book,'chapter':chapter,'title':title,'url':link.group(1),'description':desc,'id':link.group(1).split('/')[-2]}; entries.append(current)
  elif current and line.startswith('   - '): current['description']+='；'+line.strip()[2:]
for e in entries:
 e['points']=[p.strip(' 。　') for p in re.split('[；。]',e.pop('description')) if p.strip(' 。　')]
# The independently reviewed entries retain qualification present in the teacher pages.
for e in entries:
 if e['id']=='bx2-9-4': e['points'].append('复数的三角形式：选学内容')
 if e['id']=='x2-7-1': e['points'].append('贝叶斯公式：标星内容')
 if e['id']=='x2-7-3': e['points']=['二项分布：适用条件及概率计算', '超几何分布：适用情境', '正态分布：图像与概率']
 if e['id']=='x2-5-2': e['points'].append('复合函数求导：具体范围须参照教参限定')
assert len(entries)==80,(len(entries),[e['id'] for e in entries])
for e in entries:
 assert (Path('outputs/课本知识地图')/e['url']).exists(),e['url']
out=Path('outputs/课本知识地图/data.js')
out.write_text('window.MAP_DATA = '+json.dumps(entries,ensure_ascii=False,indent=2)+';\n')
print(len(entries),'sections',sum(len(e['points']) for e in entries),'points')
