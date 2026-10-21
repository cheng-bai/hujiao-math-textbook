#!/usr/bin/env python3
"""Replay independently traceable x2 editorial repairs; never edit source files."""

from project_paths import use_project_root, launch_browser
use_project_root()
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / 'batch/patches/repair-x2-v1.json'
REVIEW = ROOT / 'batch/reviews/repair-x2-author.json'
IDS = ['x2-5-1', 'x2-5-3', 'x2-6-2', 'x2-chapter-end-5', 'x2-chapter-end-6', 'x2-chapter-end-7', 'x2-8-1', 'x2-8-2', 'x2-8-3', 'x2-chapter-end-8']

def encoded(d):
    return json.dumps(d, ensure_ascii=False, indent=2) + '\n'

def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()

def ref(source, start, end):
    return [{'source': source, 'start': start, 'end': end}]

def regression(x, y):
    mx, my = sum(x)/len(x), sum(y)/len(y)
    sxx = sum((a-mx)**2 for a in x)
    syy = sum((a-my)**2 for a in y)
    sxy = sum((a-mx)*(b-my) for a,b in zip(x,y))
    return sxy/sxx, my-sxy/sxx*mx, sxy/math.sqrt(sxx*syy)

def author():
    docs = {sid: json.loads((ROOT/f'batch/sections/x2/{sid}.json').read_text(encoding='utf-8')) for sid in IDS}
    before = copy.deepcopy(docs)
    evidence = []
    for sid,d in docs.items():
        for i,b in enumerate(d['blocks']):
            b.setdefault('id', f'{sid}-b{i}')
    def q(sid, suffix):
        return next(b for b in docs[sid]['blocks'] if b['id'] == sid+'-'+suffix)
    def lines(sid, source, start, end):
        p = Path(docs[sid]['sources'][source])
        text = '\n'.join(p.read_text(encoding='utf-8').splitlines()[start-1:end]).strip()
        return re.sub(r'(!\[[^\]]*\]\()([^)]*)(\))', lambda m: m[1]+str((p.parent/m[2]).resolve())+m[3], text)
    def answer(b, text, analysis='', source_refs=None):
        if b.get('answer'):
            b.setdefault('editor_original_answer', b['answer'])
            b.setdefault('editor_original_answer_provenance', b.get('answer_provenance', []))
        b.update(answer=text, teacher_analysis=analysis, answer_provenance=source_refs or [], analysis_provenance=[])
        b['editor_revision'] = {'author':'编辑补写/复核', 'kind':'source_repair_with_independent_derivation', 'not_original_teacher_text':True}
    def convert(b, category, number, question_refs):
        b.update(type='question', category=category, title=f'{category} · {number}', provenance_question=question_refs, provenance=question_refs)
        b.pop('teacher_only', None)
        b.setdefault('answer',''); b.setdefault('answer_provenance',[]); b.setdefault('teacher_analysis',''); b.setdefault('analysis_provenance',[])
    def evidence_row(sid, issue, details):
        evidence.append({'section':sid,'issue':issue,'action':details})
    def finish(sid, resolved_codes):
        d=docs[sid]
        resolved=[i for i in d['issues'] if i['code'] in resolved_codes]
        d['issues']=[i for i in d['issues'] if i['code'] not in resolved_codes]
        d.setdefault('editorial_repairs',[]).append({'id':'repair-x2-v1','resolved_issues':resolved,'evidence':'batch/reviews/repair-x2-author.json','source_files_read_only':True})

    sid='x2-5-1';d=docs[sid];b=q(sid,'ex-1')
    split=b['answer'].index('用瞬时速度的说法,')
    definition=b['answer'][split:];b['answer']=b['answer'][:split].rstrip();b['answer_provenance']=ref('book',35,64)
    d['blocks'].insert(d['blocks'].index(b)+1,{'type':'prose','id':sid+'-repair-derivative-definition','title':'导数与瞬时变化率','markdown':definition,'provenance':ref('book',65,78)})
    finish(sid,set());evidence_row(sid,'example-answer-boundary-detected-by-print','例1解答结束后的一般导数定义、平均/瞬时变化率及高铁解释从answer移回公共正文，保留完整原文，学生正文也可读；例1中h<0的计算旁注仍保留在该题答案。')

    sid='x2-5-3'; d=docs[sid]
    b12=q(sid,'ex-12'); b13=q(sid,'ex-13')
    split=b12['answer'].index('解 根据题意,可知')
    moved=b12['answer'][split:]
    b12['answer']=b12['answer'][:split].rstrip();b12['answer_provenance']=ref('book',1049,1058)
    old13=b13['markdown']; caption=re.search(r'!\[[^\]]*\]\([^\n]*\)\n\n图 5-3-5',moved).group()
    b13['markdown']=old13.split('\n\n求导')[0]+'\n\n'+caption
    b13['provenance']=b13['provenance_question']=ref('book',1061,1066)
    answer(b13, r'【编辑复核】当 $b=\frac{\sqrt{3}}{3}d$、$h=\frac{\sqrt{6}}{3}d$ 时，抗弯强度最大，最大值为 $\frac{d^3}{9\sqrt{3}}$。', r'由矩形内接于圆，$b^2+h^2=d^2$，且 $0<b<d$。因此 $W(b)=\frac16 b(d^2-b^2)$，$W\prime(b)=\frac16(d^2-3b^2)$。当 $0<b<d/\sqrt3$ 时导数为正；当 $d/\sqrt3<b<d$ 时导数为负，故在 $b=d/\sqrt3$ 处取得唯一最大值。代入得 $h=d\sqrt{2/3}$ 及所求最大值。原例12尾部误收的本例建模、图5-3-5已移回；本例题干中混入的求导过程移至答案。',ref('book',1059,1070))
    d['blocks'].insert(d['blocks'].index(b13)+1,{'type':'prose','id':sid+'-repair-optimization-note','title':'最优值与驻点','markdown':lines(sid,'book',1071,1072),'provenance':ref('book',1071,1072)})
    b1=q(sid,'p534-1'); b2=q(sid,'p534-2')
    b1['markdown']=b1['markdown'].split('\n\n![')[0];b1['provenance']=b1['provenance_question']=ref('book',1089,1090)
    answer(b1,r'【编辑补写】产量取 $q=200$ 时利润最大，最大利润为 $3150000$（与题设成本、售价使用同一货币单位）。',r'利润等于销售收入减成本，故 $L(q)=q(24200-q^2/5)-(50000+200q)=24000q-q^3/5-50000$。按 $q\ge0$ 且单价非负，有 $0\le q\le\sqrt{121000}$。$L\prime(q)=24000-3q^2/5$，在 $q=200$ 两侧由正变负，故利润在此取得最大值。代入得 $L(200)=3150000$；若产量要求取整数，$200$ 本身即为可行整数。正式教参该题只有编号，本解为独立补写。')
    b1['answer_editorial']={'kind':'independently-derived','reason':'正式教参437行只有编号，无有效答案；由完整题设建立利润函数并独立求导，明确售价非负与整数产量的可行性。'}
    evidence_row(sid,'example-answer-boundary;empty-answer-content','例12尾部误收例13的建模和图，已移回；恢复例13题答边界和完整最大值证明。练习5.3(4)1独立利润模型补答，附定义域与整数可行性。')
    finish(sid,{'example-answer-boundary','empty-answer-content'})

    sid='x2-6-2';d=docs[sid]
    b=q(sid,'b16');convert(b,'练习6.2(2)',1,ref('book',557,564));b['markdown']=b['markdown'].replace('1.5 名','1. 5 名',1)
    answer(b,r'【回源配对并编辑补解】(1) $120$；(2) $24$；(3) $72$。',r'(1)五名队员全排列，共 $5!=120$ 种。(2)固定甲在排头，余下四人有 $4!=24$ 种。(3)甲有三个内部位置可选，每种位置其余四人有 $4!$ 种，共 $3\times4!=72$ 种。原OCR“1.5名”是第1题加“5名”，不是小数。',ref('teacher',263,264))
    answer(q(sid,'p622-2'),r'【回源配对并编辑补解】(1) $1440$ 次；(2) $5760$ 种。',r'(1)先排四种非有机材料，有 $4!$ 种。在形成的五个空位中选三个放入三种不同有机染料，有 $\mathrm C_5^3 3!$ 种，共 $4!\mathrm C_5^3 3!=1440$ 次。(2)三类画作为三个块，水彩画块必须在中间，另两块可交换；块内分别有 $4!$、$5!$ 种排法，故共 $2\times4!\times5!=5760$ 种。',ref('teacher',265,266))
    pool=next(b for b in d['blocks'] if '未配对参考' in b.get('title',''));pool['title']='练习6.2(2) · 原教参答案存档（已逐题复核回接）'
    finish(sid,{'answer-group-numbering'});evidence_row(sid,'answer-group-numbering','从正文恢复被1.5 OCR吞掉的第1题，保留既有b16锚点；两题答案与原教参逐项对应并补解。')

    sid='x2-chapter-end-5'
    b=q(sid,'hA-4')
    answer(b,r'【编辑订正】(1) $3\mathrm e-5$；(2) $\mathrm e$；(3) 在 $x=1$ 无定义，因而不存在题目所问的导数值；(4) $2\mathrm e^3+\frac32$。',r'(1) $h\prime(x)=3\mathrm e^x-5/x$，代入 $x=1$ 得 $3\mathrm e-5$。(2)由乘积求导，$h\prime(1)=\mathrm e\ln1+\mathrm e=\mathrm e$。(3)分母 $g(1)=\ln1=0$，所以 $h(1)$ 不存在，不能套商法则求该点导数；且 $\mathrm e^x/\ln x$ 在 $x=1$ 处发散，不能以可去间断延拓修补。(4) $h(x)=\mathrm e^{2x+1}+\ln(3x-1)$，故 $h\prime(x)=2\mathrm e^{2x+1}+3/(3x-1)$，代入得 $2\mathrm e^3+3/2$。原教参OCR依次列为“3-5e、e、1/e、2/3+3e²”，与当前教材题面不符，保留题面，不据答案猜改题。',ref('teacher',479,482))
    b=q(sid,'hA-7')
    answer(b,r'【编辑订正】(1) 最大值 $1$，最小值 $-1$；(2) 最大值 $\frac94$，最小值 $0$；(3) 最大值 $19$，最小值 $\frac{13}{27}$。',r'(1)函数严格增，端点值为 $f(0)=-1$、$f(3)=1$。(2)配方得 $f(x)=9/4-(x-1/2)^2$，在 $x=1/2$ 处取最大值 $9/4$；两端值为 $f(-1)=0$、$f(1)=2$，故最小值为 $0$。(3) $f\prime(x)=3x^2+2x-8=(3x-4)(x+2)$，驻点为 $-2,4/3$。比较 $f(-3)=13$、$f(-2)=19$、$f(4/3)=13/27$、$f(3)=19$ 即得。原教参OCR第(1)小问最小值写0，第(2)小问最大值写19，均已据题面订正；第(3)小问与原教参相符。',ref('teacher',490,495))
    finish(sid,{'source-math-conflict'});evidence_row(sid,'source-math-conflict','完整保留A4题面，明确A4(3)无定义而非猜改f/g；将错配原答案存入editor_original_answer。A7独立求导和端点核算，修复最大最小值。')

    sid='x2-chapter-end-6'; d=docs[sid]
    a1=q(sid,'hA-1');original=a1['markdown'];q2text=re.search(r'2\.5 个工程队.*?(?=\n\n|$)',original,re.S).group()
    a1['markdown']=original.replace(q2text+'\n\n','').replace(q2text,'').strip();a1['provenance']=a1['provenance_question']=ref('book',1679,1684)
    a2={'type':'question','id':sid+'-hA-2','title':'复习题A · 2','category':'复习题A','markdown':q2text.replace('2.5 个','2. 5 个',1),'provenance':ref('book',1685,1686),'provenance_question':ref('book',1685,1686)}
    d['blocks'].insert(d['blocks'].index(a1)+1,a2)
    b1=q(sid,'b14');convert(b1,'复习题B',1,ref('book',1699,1700));b1['markdown']=b1['markdown'].replace('1.7 名','1. 7 名',1)
    A={1:(r'$150$',r'图中只有A与B、B与C共享边。先给B选色有6种，A、C各有5种，二者可同色，故为 $6\times5\times5=150$。'),2:(r'$96$',r'甲可选除1号外的4个项目，其余四队有 $4!$ 种安排，故为 $4\times4!=96$。'),3:(r'$144$',r'个位从1、3、5中选，有3种；千位从剩余非零数中选，有4种；百位、十位再分别有4种、3种。共 $3\times4\times4\times3=144$。'),4:(r'$x=10$',r'组合数有意义要求 $x\ge3$。由 $11x(x-1)(x-2)/6=12x(x+1)$，约去正数 $x$ 后得 $11x^2-105x-50=0$，即 $(x-10)(11x+5)=0$。取正整数解 $x=10$。'),5:(r'$10$',r'令 $x=1$，得系数和 $2^n=32$，所以 $n=5$。通项为 $\mathrm C_5^k x^{10-3k}$，指数等于1时 $k=3$，故所求系数为 $\mathrm C_5^3=10$。'),6:(r'$41$',r'$a_0=1$、$a_1=-8$、$a_3=\mathrm C_4^3(-2)^3=-32$，故三项绝对值之和为 $1+8+32=41$。'),7:(r'$5$',r'通项中x的指数为 $6(n-k)-3k/2=6n-15k/2$。常数项要求 $4n=5k$，所以正整数n至少为5；取 $n=5,k=4$ 可达到。')}
    B={1:(r'$192$',r'甲固定在中间。乙丙相邻只能占左侧或右侧的相邻位置，每侧各2对，共4对；乙丙内部有2种次序，其余四人有 $4!$ 种，故为 $4\times2\times4!=192$。'),2:(r'$150$',r'用容斥原理，任意放法有 $3^5$ 种，减去至少一个空盒，再补回两个空盒：$3^5-\mathrm C_3^1 2^5+\mathrm C_3^2=150$。'),3:(r'$420$',r'先选两男两女，再将两名女队员配给两名男队员，共 $\mathrm C_7^2\mathrm C_5^2\times2=420$ 种；两支队伍不再另编号。'),4:(r'(1) $3720$；(2) $720$；(3) $144$；(4) $720$',r'(1) $7!-2\times6!+5!=3720$。(2)把三名男生捆成一块，有 $5!\times3!=720$。(3)只能按女男女男女男女排列，有 $4!\times3!=144$。(4)甲乙的位置差为4，有3对位置，每对有2种次序，其余五人任排，共 $3\times2\times5!=720$。'),5:(r'(1) $115$；(2) $186$',r'(1)红球数为2、3、4，计 $\mathrm C_4^2\mathrm C_6^2+\mathrm C_4^3\mathrm C_6^1+\mathrm C_4^4=90+24+1=115$。(2)选五球，若红球为r个，总分为 $5+r$，故 $r\ge2$。计 $\mathrm C_4^2\mathrm C_6^3+\mathrm C_4^3\mathrm C_6^2+\mathrm C_4^4\mathrm C_6^1=120+60+6=186$。'),6:(r'(1) $2^{100}$；(2) $\frac{(2-\sqrt3)^{100}-(2+\sqrt3)^{100}}2$；(3) $1$',r'设 $F(x)=(2-\sqrt3 x)^{100}$。常数项为 $F(0)=2^{100}$。奇数次项系数之和为 $[F(1)-F(-1)]/2$。设偶、奇数次项系数和为S、T，则 $S+T=F(1)$、$S-T=F(-1)$，故 $S^2-T^2=F(1)F(-1)=(4-3)^{100}=1$。'),7:(r'$7$',r'$55^{55}=(56-1)^{55}$。二项展开中除末项外均含因子56，因而均为8的倍数；末项为 $(-1)^{55}=-1$，所以余数为7。')}
    for group,data,base in [('A',A,433),('B',B,449)]:
        for n,(a,t) in data.items():
            b=a2 if group=='A' and n==2 else b1 if group=='B' and n==1 else q(sid,f'h{group}-{n}')
            answer(b,'【回源配对并编辑补解】'+a+'。',t,ref('teacher',base+2*(n-1),base+2*(n-1)+1))
    for b in d['blocks']:
        if '未配对参考' in b.get('title',''): b['title']=b['title'].replace('未配对参考答案原文（题号异常）','原教参答案存档（已逐题复核回接）')
    finish(sid,{'answer-group-numbering'});evidence_row(sid,'answer-group-numbering','从A1内拆出A2（2.5个）并恢复B1（1.7名）；A1三区域原图已目视确认相邻链。14题答案逐题回接并独立推导。')

    sid='x2-chapter-end-7';d=docs[sid];b=q(sid,'hB-1');s=b['markdown'].split('\n\n2.100 件')
    b['markdown']=s[0];b['provenance']=b['provenance_question']=ref('book',1319,1320)
    b2={'type':'question','id':sid+'-hB-2','title':'复习题B · 2','category':'复习题B','markdown':'2. 100 件'+s[1],'provenance':ref('book',1321,1322),'provenance_question':ref('book',1321,1322)}
    d['blocks'].insert(d['blocks'].index(b)+1,b2)
    answer(b,'【回源配对并编辑补解】$0.3$。',r'乙须在甲答错后才有答题机会，故所求概率为 $(1-0.4)\times0.5=0.3$。题中0.5应理解为轮到乙答题时答对的概率。',ref('teacher',501,502))
    answer(b2,r'【回源配对并编辑补解】$\frac{95}{99}$。',r'已知第一件是次品，剩下99件，其中正品仍有95件，故第二件为正品的条件概率是 $95/99$。',ref('teacher',503,504))
    answer(q(sid,'hB-3'),r'【回源配对并编辑补解】$\frac13$。',r'已知不是黑球，条件样本空间只含10个白球与5个黄球，故概率为 $5/(10+5)=1/3$。',ref('teacher',505,506))
    answer(q(sid,'hB-4'),r'【编辑补写并核对教参未编号答案】(1) $\frac{10}{21}$；(2) $P(X=0)=\frac5{12}$，$P(X=1)=\frac12$，$P(X=2)=\frac1{12}$，$E[X]=\frac23$。',r'(1)共有 $\mathrm C_9^3=84$ 种等可能选法；4个偶数中选1个、5个奇数中选2个，有 $4\mathrm C_5^2=40$ 种，故概率为 $40/84=10/21$。(2)按大小写作 $a<b<c$。X只能取0、1、2。没有相邻数的选法数为 $\mathrm C_7^3=35$（将b减1、c减2，转化为从1到7中选三个不同数）；有两组相邻时只能选连续三个数，共7种；恰有一组相邻时为 $84-35-7=42$ 种。因此分布如上，期望为 $42/84+2\times7/84=2/3$。',ref('teacher',507,508))
    answer(q(sid,'hB-5'),r'【回源配对并编辑补解】$P(X=0,1,2,3)=\left(\frac{14}{27},\frac{10}{27},\frac2{27},\frac1{27}\right)$，$E[X]=\frac{17}{27}$。',r'每次红球概率为1/3，白球概率为2/3。以红、白分别记作R、W：X=0来自WRR、WRW、WW W，其概率合计为 $2/27+4/27+8/27=14/27$（WWW中第三次由甲摸白球）；X=1来自RWR、RWW、WWR，共 $2/27+4/27+4/27=10/27$；X=2只来自RRW，为2/27；X=3只来自RRR，为1/27。各概率和为1，故 $E[X]=(10+4+3)/27=17/27$。',ref('teacher',509,518))
    pool=next(b for b in d['blocks'] if '未配对参考' in b.get('title',''));pool['title']='复习题B · 原教参答案存档（已逐题复核回接）'
    finish(sid,{'missing-answer','answer-group-numbering'});evidence_row(sid,'missing-answer;answer-group-numbering','从B1恢复2.100件产品独立题；B4教参漏题号及(1)答案，补组合计数证明；五题逐题回接。')

    sid='x2-8-1';d=docs[sid];p=q(sid,'b12');t=q(sid,'b13');mark=p['markdown'].index('例 2 ');md=p['markdown'][mark:];p['markdown']=p['markdown'][:mark].rstrip();p['provenance']=ref('book',68,104)
    old_answer=t['markdown'];convert(t,'例题',2,ref('book',105,110));t['markdown']=md
    answer(t,old_answer,r'【编辑校注】将原先被隔离的“解”回接例2，恢复完整题答边界。Pearson相关系数的定义与计算并不要求两个变量各自服从正态分布；正态性属于某些统计推断方法的适用条件，不是计算样本相关系数的必要条件。原教材相关旁注保留供辨识，不把它作为定义限制。',ref('book',111,134))
    finish(sid,{'unattached-book-solution'});evidence_row(sid,'unattached-book-solution','例2题干与表8-3从长正文分出，原b13改为独立题块并接回111—134行解答。题干表格保留；正常性旁注加准确限定。')

    sid='x2-8-3';d=docs[sid];p=q(sid,'b6');t=q(sid,'b7');mark=p['markdown'].index('例 1 ');md=p['markdown'][mark:];p['markdown']=p['markdown'][:mark].rstrip();p['provenance']=ref('book',693,694)
    old_answer=t['markdown'];convert(t,'例题',1,ref('book',695,702));t['markdown']=md
    answer(t,old_answer,r'【编辑复核】这是表8-10对应的例1解答，不是游离正文。检验得到显著的样本关联，不据此推断性别对色盲的因果机制。',ref('book',703,712))
    finish(sid,{'unattached-book-solution'});evidence_row(sid,'unattached-book-solution','例1题干、表8-10与色盲独立性检验解答回接为题块；保持b7既有锚点ID。')

    sid='x2-8-2';d=docs[sid]
    answer(q(sid,'h82B-1'),r'【回源配对并编辑补解】(1) $\widehat y=60+5x$；(2) 预测月营业收入为 $110$ 千元。',r'以x、y的题设单位计算，$\bar x=14$、$\bar y=130$，$S_{xx}=568$、$S_{xy}=2840$，所以斜率为5，截距为60。10000人对应 $x=10$，代入得 $\widehat y=110$。',ref('teacher',474,476))
    answer(q(sid,'h82B-2'),r'【回源配对并编辑复核】(1)男性：$\widehat y\approx0.186x+11.571$；女性：$\widehat y\approx0.403x+5.240$。(2)合并斜率约0.021，显著小于两组内的斜率，不能忽略性别构成。(3)相关系数分别约为 $0.935$、$0.813$、$0.078$。',r'分别对男性10组、女性9组成对数据代入最小二乘公式 $\widehat a=S_{xy}/S_{xx}$、$\widehat b=\bar y-\widehat a\bar x$，并用 $r=S_{xy}/\sqrt{S_{xx}S_{yy}}$ 计算。各性别内部体重与脂肪比例呈正相关；两组的中心位置不同，合并后组间差异抵消了部分组内趋势，整体几乎不呈线性相关。这与合并斜率接近零一致。相关弱不代表不存在其他关系，也不应从该样本归纳性别因果结论。',ref('teacher',478,486))
    N=[71900,74400,78400,87800,87000,110200,121200,139400,161000,171200,190200,210300,264100,295700,326200,361100,400000,444000,500000,553900]
    slope,intercept,r=regression(list(range(20)),[math.log(n) for n in N]);pred2026=math.exp(intercept+slope*27);pred2027=math.exp(intercept+slope*28)
    answer(q(sid,'h82B-3'),rf'【回源修订并编辑补解】令 $t=Y-1999$，$Y$ 为公历年份，则 $\widehat{{\ln N}}={intercept:.6f}+{slope:.6f}t$，即 $\widehat N=\exp({intercept:.6f}+{slope:.6f}t)$（万人次）。若把“今年、明年”明确取为本次编写年份2026、2027，纯模型外推分别约为 ${pred2026:.0f}$、${pred2027:.0f}$ 万人次；这不是实际游客数量，也不是经现实数据校准的可靠预报。',r'【编辑补解】表8-5呈指数增长趋势，先对原始N取自然对数，再对t与lnN作一元线性回归。取1999年为t=0可避免大年份造成截距精度损失；代回时必须是 $\exp(\widehat b+\widehat a t)=\mathrm e^{\widehat b}\mathrm e^{\widehat a t}$，不能把第二个指数因子写进第一个指数。通用年份T的外推为 $\widehat N_T=\exp(\widehat b+\widehat a(T-1999))$，“今年”须先明确年份。这里使用原始N计算，而非表8-6已四舍五入的lnN。原教参488行的指数排版有误，490行的中心化形式说明了正确乘积结构。训练区间止于2018年，原教参也指出疫情后依赖关系发生改变；因此2026、2027的数值只演示模型代入，不作现实预测。',ref('teacher',488,492))
    pool=next(b for b in d['blocks'] if '未配对参考' in b.get('title',''));pool['title']='习题8.2B · 原教参答案存档（已逐题复核回接；指数式另见编辑订正）'
    finish(sid,{'missing-answer','answer-group-numbering'});evidence_row(sid,'missing-answer;answer-group-numbering','B3教参488—492有未编号模型说明，已回接并修复指数排版；按原始N重算回归，不把长程外推当实际数量。B1/B2重新配对并独立数值复核。')

    sid='x2-chapter-end-8';d=docs[sid]
    answer(q(sid,'hA-1'),r'【回源配对并编辑补解】斜率约为 $0.992$。',r'由 $\bar x=47.5$、$\bar y=114$、$S_{xx}=3250$、$S_{xy}=3225$，得 $\widehat a=3225/3250\approx0.992$。',ref('teacher',542,543))
    answer(q(sid,'hA-2'),r'【回源配对并编辑补解】$-44.866$。',r'把 $x=50$ 代入所给回归方程，得 $\widehat y=-0.960\times50+3.134=-44.866$。',ref('teacher',544,545))
    answer(q(sid,'hA-3'),r'【回源配对并编辑补解】在该线性回归模型下，广告费每增加1万元，销售额的预测值平均增加约9.4万元。',r'斜率表示解释变量每增加1个单位时，反应变量预测值的变化量。这里两个量的单位均为万元；这是模型中的平均趋势，不是每次投放必然增收的因果保证。',ref('teacher',546,549))
    x=[84,85,71,74,60,58,51,82,87,69,79,80,83,84,63,54];y=[84,88,72,73,68,62,60,85,88,73,84,82,83,83,66,67]
    slope,intercept,corr=regression(x,y)
    plot=ROOT/'batch/patches/repair-x2-assets/scores-scatter.svg';plot.parent.mkdir(parents=True,exist_ok=True)
    dots=''.join(f'<circle cx="{50+(a-45)*8:.2f}" cy="{400-(b-50)*8:.2f}" r="4" fill="#136b69"/>' for a,b in zip(x,y))
    ticks=''.join(f'<text x="{50+(v-45)*8}" y="424" text-anchor="middle">{v}</text><text x="40" y="{400-(v-50)*8+5}" text-anchor="end">{v}</text>' for v in range(50,91,10))
    plot.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="460" viewBox="0 0 480 460" role="img" aria-label="Paired scores of 16 students"><rect width="480" height="460" fill="white"/><g font-family="serif" font-size="15" fill="#263c43"><path d="M50 40V400H440" fill="none" stroke="#263c43"/>{ticks}<text x="440" y="447">x</text><text x="22" y="30">y</text>{dots}</g></svg>', encoding='utf-8')
    source_scatter=lines(sid,'teacher',548,549)
    answer(q(sid,'hA-4'),rf'【回源配对并编辑复核】(1)以高一成绩为x、高二成绩为y，散点图如下。\n\n![16名学生成对成绩散点图]({plot})\n\n(2) $r\approx{corr:.6f}$，约为 $0.965$，两次数学成绩呈很强的正线性相关。'.replace('\\n','\n'),r'横轴为高一成绩，纵轴为高二成绩，每名学生贡献一个点。16对数据有 $\bar x=72.75$、$\bar y=76.125$；将中心化数据代入 $r=\frac{\sum(x_i-\bar x)(y_i-\bar y)}{\sqrt{\sum(x_i-\bar x)^2\sum(y_i-\bar y)^2}}$ 得约0.965。由此可说该样本中高一成绩较高者在高二也往往较高，不能仅凭r断言成绩整体提高或存在因果关系。原教参550行是本题未编号的(2)答案，现已回接。',ref('teacher',548,550))
    answer(q(sid,'hA-5'),r'【回源配对并编辑补解】$\chi^2\approx8.416>3.841$，在显著性水平 $0.05$ 下拒绝“性别与是否读营养说明无关”的原假设，认为二者存在统计关联。',r'按表中排列取 $a=28,b=16,c=8,d=20,n=72$，有 $\chi^2=\frac{72(28\times20-16\times8)^2}{44\times28\times36\times36}\approx8.416$。与自由度1的5%临界值3.841比较即得。题目“95%把握”是教材对显著性检验的通俗表达，不应解释为原假设成立概率为5%。',ref('teacher',552,553))
    pool=next(b for b in d['blocks'] if '未配对参考' in b.get('title',''));pool['title']='复习题A · 原教参答案存档（已逐题复核回接）'
    finish(sid,{'missing-answer','answer-group-numbering'});evidence_row(sid,'missing-answer;answer-group-numbering','A4实际有未编号教参散点图与r答案，已按原始16对数据重算并绘制清晰图；五题逐题回接并补推理及统计解释边界。')

    patch={'schema':'textbook-editorial-patch/v1','id':'repair-x2-v1','files':[],'evidence':evidence}
    for sid,after in docs.items():
        orig=before[sid]
        assert after['source_hashes']==orig['source_hashes']
        assert not [i for i in after['issues'] if i.get('severity')=='blocking'],sid
        for source,expected in after['source_hashes'].items(): assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==expected,source
        oldids={b['id'] for b in orig['blocks'] if 'id' in b};newids=[b['id'] for b in after['blocks']]
        assert oldids <= set(newids) and len(newids)==len(set(newids))
        assert all(b.get('answer','').strip() for b in after['blocks'] if b['type']=='question')
        patch['files'].append({'path':f'batch/sections/x2/{sid}.json','before_sha256':sha(encoded(orig)),'after_sha256':sha(encoded(after)),'before':orig,'after':after})
    PATCH.parent.mkdir(parents=True,exist_ok=True);PATCH.write_text(encoded(patch), encoding='utf-8')
    REVIEW.parent.mkdir(parents=True,exist_ok=True);REVIEW.write_text(encoded({'status':'author_math_and_structure_checked_pending_independent_review','repair_id':'repair-x2-v1','sections':IDS,'evidence':evidence,'scope':'content-only; browser/print delegated to root','source_hashes_unchanged':True,'stable_existing_ids':True,'note':'Unnumbered source answers recovered; genuinely empty answer independently authored. Full before/after evidence is in patch.'}), encoding='utf-8')
    return patch

def main():
    patch=json.loads(PATCH.read_text(encoding='utf-8')) if PATCH.exists() else author()
    for f in patch['files']:
        p=ROOT/f['path'];current=json.loads(p.read_text(encoding='utf-8'));fingerprint=sha(encoded(current))
        if fingerprint==f['after_sha256']:
            print('already applied',p.name);continue
        if fingerprint!=f['before_sha256']:
            raise SystemExit(f'Concurrent or unexpected change in {p}; refusing overwrite')
        for source,expected in f['after']['source_hashes'].items():
            if hashlib.sha256(Path(source).read_bytes()).hexdigest()!=expected: raise SystemExit('source drift: '+source)
        p.write_text(encoded(f['after']), encoding='utf-8'); print('repaired',p.name)


def check():
    import itertools
    from fractions import Fraction
    checks=[]
    def test(label, actual, expected, tolerance=0):
        ok=abs(actual-expected)<=tolerance
        checks.append({'label':label,'actual':str(actual),'expected':str(expected),'pass':ok})
        assert ok,(label,actual,expected)
    # Direct finite enumeration is independent of the formulas used in the prose.
    test('A3-four-digit-odd',sum(p[0]!=0 and p[-1]%2==1 for p in itertools.permutations(range(6),4)),144)
    for index,expected in enumerate([3720,720,144,720]):
        count=0
        for p in itertools.permutations(range(7)):
            if index==0:match=p[0]!=0 and p[-1]!=1
            elif index==1:match=max(p.index(i) for i in range(3))-min(p.index(i) for i in range(3))==2
            elif index==2:match=all((p[i]<3)!=(p[i+1]<3) for i in range(6))
            else:match=abs(p.index(0)-p.index(1))==4
            count+=match
        test(f'B4({index+1})',count,expected)
    test('B1-middle-and-adjacent',sum(p[3]==0 and abs(p.index(1)-p.index(2))==1 for p in itertools.permutations(range(7))),192)
    test('B2-nonempty-boxes',sum(len(set(p))==3 for p in itertools.product(range(3),repeat=5)),150)
    test('B5-at-least-half-red',sum(sum(x<4 for x in p)>=2 for p in itertools.combinations(range(10),4)),115)
    test('B5-score-at-least-seven',sum(sum(x<4 for x in p)>=2 for p in itertools.combinations(range(10),5)),186)
    triples=list(itertools.combinations(range(1,10),3))
    test('probability-B4-exactly-one-even',Fraction(sum(sum(x%2==0 for x in p)==1 for p in triples),len(triples)),Fraction(10,21))
    for k,expected in enumerate([35,42,7]):test(f'probability-B4-X={k}',sum(sum(p[j+1]-p[j]==1 for j in range(2))==k for p in triples),expected)
    dist={k:Fraction(0) for k in range(4)}
    for seq in itertools.product([False,True],repeat=3):
        player=0; count=0;prob=Fraction(1)
        for red in seq:
            prob*=Fraction(1,3) if red else Fraction(2,3)
            if red and player==0:count+=1
            if not red:player=1-player
        dist[count]+=prob
    for k,v in enumerate([14,10,2,1]):test(f'probability-B5-X={k}',dist[k],Fraction(v,27))
    test('probability-B5-expectation',sum(k*v for k,v in dist.items()),Fraction(17,27))
    test('binomial-55^55-mod8',pow(55,55,8),7)
    x=[2,6,8,8,12,16,20,20,22,26];y=[58,105,88,118,117,137,157,169,149,202]
    a,b,r=regression(x,y);test('restaurant-slope',a,5,1e-12);test('restaurant-intercept',b,60,1e-12)
    x=[10,25,40,50,55,60,65,75];y=[81,92,104,114,117,124,130,150]
    a,b,r=regression(x,y);test('nitrate-slope',a,3225/3250,1e-12)
    x=[84,85,71,74,60,58,51,82,87,69,79,80,83,84,63,54];y=[84,88,72,73,68,62,60,85,88,73,84,82,83,83,66,67]
    a,b,r=regression(x,y);test('scores-correlation',r,0.9647532891340839,1e-12);test('scores-mean-x',sum(x)/16,72.75);test('scores-mean-y',sum(y)/16,76.125)
    test('nutrition-chi-square',72*(28*20-16*8)**2/(44*28*36*36),8.415584415584416,1e-12)
    test('beam-maximum-d1',((1/math.sqrt(3))*(1-1/3)/6),1/(9*math.sqrt(3)),1e-12)
    test('profit-at-q200',24000*200-200**3/5-50000,3150000)
    patch=json.loads(PATCH.read_text(encoding='utf-8'))
    for f in patch['files']:
        current=json.loads((ROOT/f['path']).read_text(encoding='utf-8'))
        assert sha(encoded(current))==f['after_sha256'],f['path']
        assert all(b.get('answer','').strip() for b in current['blocks'] if b['type']=='question')
        assert all(i.get('severity')!='blocking' for i in current['issues'])
        oldids={b.get('id',f['before']['id']+f'-b{i}') for i,b in enumerate(f['before']['blocks'])}
        newids={b['id'] for b in current['blocks']}
        assert oldids<=newids,f['path']
        for source,expected in current['source_hashes'].items():assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==expected
    out=ROOT/'batch/reviews/repair-x2-selfcheck.json'
    out.write_text(encoded({'status':'pass','numeric_checks':checks,'finite_enumerations':'all 7! permutations, 3^5 assignments, all choose(9,3) triples, all 2^3 draw paths','structural_sections':len(patch['files']),'resolved_original_blocking_issues':sum(len(f['before']['issues']) for f in patch['files']),'existing_and_default_ids_preserved':True,'all_source_hashes_unchanged':True,'independent_review_pending':True}), encoding='utf-8')
    print(f'{len(checks)} numeric checks and {len(patch["files"])} section structural checks passed')

if __name__=='__main__':
    check() if '--check' in sys.argv else main()

