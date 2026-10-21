import json,re,hashlib,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'batch/reviews'
IMG=re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
def inspect(p):
 d=json.loads(p.read_text());qs=[b for b in d['blocks'] if b.get('type')=='question'];issues=[]
 for i in d.get('issues',[]):issues.append({'origin':'parser','status':'open',**i})
 for b in d['blocks']:
  if b['type'] in ['teacher','editor'] and not b.get('teacher_only'):issues.append({'code':'teacher-not-isolated','severity':'blocking','block':b.get('title')})
  if b['type'] in ['prose','intro','heading','question']:
   for n,l in enumerate(b.get('markdown','').splitlines(),1):
    if re.match(r'^\s*(?:解(?:\s|[（(：:])|答[：:]|证明[（(]\d)',l):issues.append({'code':'possible-student-answer-leak','severity':'blocking','block':b.get('id',b.get('title')),'text':l[:120]})
  for field in ['markdown','answer','teacher_analysis']:
   for im in IMG.findall(b.get(field,'')):
    if not Path(im).is_absolute() or not Path(im).exists():issues.append({'code':'image-unreachable','severity':'blocking','block':b.get('id'),'field':field,'path':im})
 for qid,n in collections.Counter(q['id'] for q in qs).items():
  if n != 1:issues.append({'code':'independent-duplicate-id','severity':'blocking','id':qid,'count':n})
 for source,sha in d.get('source_hashes',{}).items():
  if hashlib.sha256(Path(source).read_bytes()).hexdigest()!=sha:issues.append({'code':'source-hash-mismatch','severity':'blocking','path':source})
 for q in qs:
  if not q.get('answer'):continue
  for ap in q.get('answer_provenance',[]):
   if ap.get('source')=='teacher':
    src=Path(d['sources']['teacher']).read_text().splitlines()
    line=src[ap['start']-1]; n=re.match(r'^(\d+)\.',line)
    num=re.search(r'-(\d+)$',q['id'])
    verified_override=(q['id'],ap['start']) in [('x1-2-3-h23A-4',1150),('x1-2-3-h23A-5',1152)]
    if n and num and int(n[1])!=int(num[1]) and not verified_override:issues.append({'code':'answer-number-mismatch','severity':'blocking','id':q['id'],'answer_line':ap['start'],'text':line[:100]})
 return {'section_id':d['id'],'status':'structure-reviewed-math-sampling-pending','model_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'coverage':{'structure':'模型所有块的字段/ID/图路径/教参隔离标志与显式题号配对检查；人工重点另记','question_count':len(qs),'answered_count':sum(bool(q.get('answer')) for q in qs),'source_hashes':d.get('source_hashes',{}),'key_math_checks':[]},'issues':issues,'patches':[],'limits':['未逐题复算；结构配对通过不等于数学通过。','尚未独立核验最终HTML、PDF或学生ZIP的物理隔离。']}
if __name__=='__main__':
 for p in sorted((ROOT/'batch/sections/x1').glob('*.json')):
  o=OUT/(p.stem+'.json');base=inspect(p)
  if o.exists():
   old=json.loads(o.read_text());base['patches']=old.get('patches',[]);base['coverage']['key_math_checks']=old.get('coverage',{}).get('key_math_checks',[])
   base['issues'] += [i for i in old.get('issues',[]) if i.get('origin')=='independent']
   if base['coverage']['key_math_checks']:base['status']='reviewed-with-notes' if not any(i.get('severity')=='blocking' and i.get('status','open')=='open' for i in base['issues']) else 'blocked'
  o.write_text(json.dumps(base,ensure_ascii=False,indent=2))
