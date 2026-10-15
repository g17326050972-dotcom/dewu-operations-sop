# -*- coding: utf-8 -*-
from pathlib import Path
import json,re,csv,datetime
B=Path('/Users/nan/Documents/Codex/2026-10-09/zai');O=B/'outputs/2026-10-14';S=B/'outputs/2026-10-13'
END='2026-10-13';START='2026-10-07';PRIOR='2026-09-30';PRIOREND='2026-10-06';TODAY='2026-10-14'
def rd(p):return json.loads(p.read_text())
def wr(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def num(v):
 m=re.search(r'-?[\d,.]+',str(v));return float(m[0].replace(',','')) if m else None
def dates(a,b):
 a=datetime.date.fromisoformat(a);b=datetime.date.fromisoformat(b);return [(a+datetime.timedelta(days=i)).isoformat() for i in range((b-a).days+1)]
def csvout(p,rs):
 fields=list(dict.fromkeys(k for r in rs for k in r))
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rs)
off=rd(O/'2026-10-07_10-13_商品官方导出.json');index={r['商品货号']:r for r in off};ns=set(rd(O/'后台新上架名单_类目交集.json')['codes'])
old=rd(S/'daily-readings.json');oldcmp=rd(S/'weekly-comparisons.json');oldp={r['code']:r for r in old['products']};selection=[];products=[]
for c,r in index.items():
 assert r['类目名称'].split('-')[0]=='流行饰品/眼镜/服配'
 sales=int(num(r['我的销量']));uv=int(num(r['商详访问人数']));fav=int(num(r['收藏用户数']));new=c in ns;yes=sales>0 or fav>0 or new
 why='近7天有销量' if sales else '近7天有收藏' if fav else '本次后台新上架名单' if new else '近7天销量和收藏均0的老款'
 selection.append(dict(code=c,spu=r['SPUID'],title=r['商品标题'],sales=sales,uv=uv,favorites=fav,backendNew=new,included=yes,reason=why))
 if yes:products.append(dict(code=c,name=oldp.get(c,{}).get('name',r['商品标题']),backendNew=new,weekSales=sales,weekUv=uv,weekFavorites=fav,spuId=r['SPUID'],confirmedListingDate=None,newEvidence=TODAY+'后台新上架名单与指定类目交集20款，首次上架日待确认' if new else None,group='有销量款' if sales else '新品观察' if new else '有收藏款'))
products.sort(key=lambda p:(-p['weekSales'],-p['weekUv'],p['code']))
for i,p in enumerate(products):p['rank']=i+1
P={r['code']:r for r in products};assert len(P)==28 and len(off)==55
records={(r['code'],r['date']):r for r in old['records']+oldcmp['businessDays'] if r.get('observed')}
for r in rd(O/'2026-10-13_商品日数据.json'):records[r['code'],END]=dict(r,date=END,source='2026-10-14后台10/13完整日主值读数')
biz=[];missing=[]
for c,p in P.items():
 for d in dates(PRIOR,END):
  if (c,d) in records:r=dict(records[c,d],observed=True)
  else:
   reason='本次新增纳入商品，历史分天主值待继续核验' if c not in oldp else '此前该日历史主列表未返回该商品记录，首次上架日期待确认'
   r=dict(code=c,date=d,observed=False,**{k:None for k in ['uv','orders','favorites','conversionPct','amount']},missing_reason=reason);missing.append([c,d])
  r.update(name=p['name'],backendNew=p['backendNew'],favoriteRate=r['favorites']/r['uv']*100 if r['uv'] else None);biz.append(r)
periods=[dict(r,start=PRIOR,end=PRIOREND,source='2026-10-14后台09/30—10/06区间主值原值') for r in rd(O/'2026-09-30_10-06_商品区间数据.json') if r['code'] in P]
for c,p in P.items():
 r=index[c];periods.append(dict(code=c,start=START,end=END,amount=num(r['支付金额']),orders=num(r['支付订单数']),uv=num(r['商详访问人数']),favorites=num(r['收藏用户数']),conversionPct=num(r['商详转化率']),paidUsers=num(r['支付用户数']),source='10/07—10/13官方商品明细导出'))
for p in periods:
 rs=[r for r in biz if r['code']==p['code'] and p['start']<=r['date']<=p['end']]
 if len(rs)==7 and all(r['observed'] for r in rs):
  for k in ['orders','amount']:assert abs(sum(r[k] for r in rs)-p[k])<.01,(p,k)
wr(O/'daily-readings.json',dict(dates=dates(START,END),products=products,top=list(P)[:10],records=[r for r in biz if r['date']>=START],observedCount=sum(r['observed'] for r in biz if r['date']>=START),expectedCount=len(P)*7))
wr(O/'business-history.json',dict(dates=dates(PRIOR,END),records=biz,periods=periods,selection=selection,missing=missing,status='partial_history_pending',head_tie_note='近7天销量排序；本期3款有销量，其余0销量观察位按周UV降序补足10款'))
csvout(O/'business-two-weeks.csv',biz);csvout(O/'weekly-periods.csv',periods);csvout(O/'selection-audit.csv',selection)
print(json.dumps(dict(focus=len(P),category=len(off),new_watch=len(ns),observed=sum(r['observed'] for r in biz),missing=len(missing),week_periods=len(periods),yesterday_observed=sum(r['observed'] and r['date']==END for r in biz)),ensure_ascii=False))
