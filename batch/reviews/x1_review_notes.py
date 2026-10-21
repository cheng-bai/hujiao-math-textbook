import json
from pathlib import Path
R=Path(__file__).parent
NOTES={
'x1-1-2':{
 'checks':[{'id':'x1-1-2-h12B-9','method':'独立设5x-y+C=0：截距和4C/5=4；三角形面积C²/10=20','result':'C=5或±10√2，教参664行正是题9答案；非缺答案。'}],
 'patches':[{'source':'teacher','start':664,'end':664,'kind':'OCR-number-override','proposed':'恢复为习题1.2B第9题，移出第8题答案','confidence':'high'}]},
'x1-2-1':{'checks':[{'id':'x1-2-1-ex-9','method':'中点圆轨迹C·(C-M)=0得(x-1)²+(y+3)²=10，同时C须在x²+y²<16内','result':'与原解一致；书421“例9还有其他解法吗”不是新题'}],
 'patches':[{'source':'book','start':421,'end':421,'kind':'question-boundary','proposed':'保留追问但不是第二个例9','confidence':'high'}]},
'x1-2-2':{'checks':[{'id':'x1-2-2-p223-1','method':'a=6,c=4，距离范围[a-c,a+c]','result':'最小2最大10，与1086原1.10,2一致'},{'id':'x1-2-2-p223-2','method':'r1+r2=6√5且r1²+r2²=(2c)²=100','result':'r1r2=40，与1088原2.40一致'}],
'patches':[{'source':'teacher','start':1086,'end':1088,'kind':'OCR-number-spacing','proposed':'原1.10,2和2.40分别是第1题、第2题答案','confidence':'high'}]},
'x1-2-3':{'checks':[{'id':'x1-2-3-h23A-3','method':'实轴8给a4，焦距10给c5，b²9；焦轴可x或y','result':'1148为题3答案'},{'id':'x1-2-3-h23A-4','method':'y轴双曲线要求m+2<0且m+1<0','result':'m<-2，1150为题4答案，不是另一个题3'},{'id':'x1-2-3-h23A-5','method':'渐近线±√2x得2x²-y²=k，代(1,1)得k1','result':'1152为题5答案，不能按源错号4配题4'}],
'patches':[{'source':'teacher','start':1150,'end':1150,'kind':'OCR-number-override','proposed':'3.恢复为4.','confidence':'high'},{'source':'teacher','start':1152,'end':1152,'kind':'OCR-number-override','proposed':'4.恢复为5.','confidence':'high'}]},
'x1-2-5':{'checks':[{'id':'x1-2-5-ex-6','method':'视觉逐点核对极坐标原图，角度/半径与2095五点答案一致','result':'真实答案在题干2101之前，非缺解；图2097须保留题内'},{'id':'x1-2-5-ex-3','method':'中点坐标B=(2x-4,2y)代B曲线得4(x-2)²+8y²=1','result':'与原解一致，1905为方法提示，不是新例'}],
'patches':[{'source':'book','start':2093,'end':2101,'kind':'OCR-order-and-private-boundary','proposed':'拆2095前半五点答案给例6；后半接2093概念正文；2097图给例6题干。保留原行provenance。','confidence':'high'},{'source':'book','start':1905,'end':1905,'kind':'hint-private-boundary','proposed':'例3方法提示teacher_only，不重复建题','confidence':'high'}]},
'x1-3-4':{'checks':[{'id':'x1-3-4-ex-2','method':'AC1=(-a,a,a)，A1B=(0,a,-a)，A1D=(-a,0,-a)，点积都0，且两平面互异','result':'垂直和平行结论正确；827为例2证明开头而非前例结尾'}],
'patches':[{'source':'book','start':817,'end':825,'kind':'body-vs-answer','proposed':'保留为一般定理正文，不随例1答案隐藏','confidence':'high'},{'source':'book','start':827,'end':874,'kind':'OCR-order-and-private-boundary','proposed':'827证明开头与839–874合成例2答案；833–837为题干，829图保留在题干','confidence':'high'}]},
'x1-4-4':{'checks':[{'id':'x1-4-4-p441-1','method':'辨错题题干中的两个证明必须保留；(1)n1反例2≠3，(2)证明用几何级数公式未用归纳假设','result':'原答案核心判断吻合，题干“证明”不是学生泄漏。'}],
'issues':[{'origin':'independent','code':'source-answer-sentence-truncated','severity':'warning','status':'open','source':'teacher','line':510,'message':'习题4.4(1)1(2)原源以“这意味”结束；主教参MD3467同样残句，非parser截断。核心错误说明已保留，不自行补写来源缺句。'}]},
'x1-4-5':{'checks':[{'id':'x1-4-5-p45-1','method':'Fraction精确递推5项=-2,-3/2,-17/12,-577/408,-665857/470832','result':'与教参小数表一致；负初值迭代至负根，需保留题中-2条件'},{'id':'x1-4-5-p45-2','method':'Fraction精确递推8项=-2,0,2,4/3,10/7,24/17,58/41,140/99','result':'与教参小数表一致，分母未出现0'},{'id':'x1-4-5-p45-3','method':'Fraction精确递推5项=1,2,7/4,97/56,18817/10864','result':'与教参小数表及sqrt3迭代公式一致'}]}
}
for sid,n in NOTES.items():
 p=R/(sid+'.json');d=json.loads(p.read_text());d['coverage']['key_math_checks']=n.get('checks',[])
 d['patches']=n.get('patches',[])
 d['issues'] += [i for i in n.get('issues',[]) if i not in d['issues']]
 d['status']='blocked' if any(i.get('severity')=='blocking' and i.get('status','open')=='open' for i in d['issues']) else 'reviewed-with-notes'
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2))
