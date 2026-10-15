# -*- coding: utf-8 -*-
from pathlib import Path
import json,re,csv,datetime,shutil
B=Path('/Users/nan/Documents/Codex/2026-10-09/zai');O=B/'outputs/2026-10-14';D=O/'draft-site';END='2026-10-13'
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
g=rd(B/'outputs/2026-10-13/gravity-content-month.json');n=rd(O/'引力内容新增读数.json');export=rd(O/'引力任务报告官方导出.json');off=rd(O/'2026-10-07_10-13_商品官方导出.json');spus={str(r['SPUID']):r['商品货号'] for r in off}
recent=[r for r in export if '2026-09-14'<=r['动态发布时间'][:10]<=END];assert len(export)==64 and len(recent)==5
assert {r['子任务ID'] for r in recent}=={r['task_id'] for r in n['daily']}
gi={r['子任务ID']:r for r in recent};snap=[]
mp={'exposure':'曝光pv','reads':'阅读pv','interactions':'互动pv','detail_visits':'商详访问pv','favorites':'引导商品收藏数','attributed_orders_14d':'14日归因订单量','attributed_gmv_14d':'14日归因GMV','help_orders':'帮助成交订单','help_gmv':'帮助成交金额','curated_exposure':'穿搭精选曝光量','curated_reads':'穿搭精选阅读量','curated_help_orders':'穿搭精选辅助下单数','cooperation_fee':'子任务金额','backend_visit_cost':'商详访问成本','ctr_pct':'动态点击率','detail_lead_rate_pct':'内容引导商详率'}
for p in g['snapshots']:
 cid=p['content_id'];meta=n['contents'][cid];r=gi[meta['task_id']];assert spus[str(r['货号（spu_id）'])]==meta['code'];assert '2026-09-14'<=meta['published_at'][:10]<=END
 p.update({k:num(r[f]) for k,f in mp.items()});p.update(meta);p.update(data_as_of=meta['as_of'],export_published_at=r['动态发布时间'],association_evidence='10/14完整官方任务报告SPU与商家官方导出货号匹配；列表内容ID与详情实际发布时间、截止时间及10/13分天图逐条核验。')
 p['notes']=['官方导出与详情发布时间不同，两者原值保留，展示采用详情时间。','合作状态与详情合作金额沿用10/12核验，非10/14实时状态；任务金额不是实际广告消耗。']
 p.pop('chart_cumulative_detail_visits',None)
 d=next(x for x in n['daily'] if x['content_id']==cid);d.update(creator=p['creator'],source='2026-10-14引力任务详情发布后30天/7天分天图浮层原值，日期2026-10-13');g['daily'].append(d)
 ds=sorted([x for x in g['daily'] if x['content_id']==cid],key=lambda x:x['date']);assert [x['date'] for x in ds]==dates(p['published_at'][:10],END)
 p['daily_reconciliation']={k:{'daily_sum':sum(x[k] for x in ds),'cumulative':p[k],'matches':sum(x[k] for x in ds)==p[k]} for k in g['fields']}
 for k,v in p['daily_reconciliation'].items():
  if not v['matches']:p['notes'].append(f'{k}历史实采日值合计{v["daily_sum"]}与最新概览累计{v["cumulative"]:g}不同，保留原值。')
 for k,v in meta['chart_cumulative'].items():
  if v!=p[k]:p['notes'].append(f'{k}最新分天图累计{v}与概览/官方导出累计{p[k]:g}不同，保留两处原值。')
 snap.append(p)
g['snapshots']=sorted(snap,key=lambda p:p['published_at'],reverse=True);g['daily'].sort(key=lambda p:(p['content_id'],p['date']))
assert len(g['daily'])==57 and len({(r['content_id'],r['date']) for r in g['daily']})==57
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
g.update(window={'start':'2026-09-14','end':END},reverified_at=now,refresh_status='complete',refresh_note='10/14完整导出64条任务，按09/14—10/13发布时间筛选并逐条核验5条内容，补齐截至10/13共57条六项真实日值。',reverification={'official_export_rows':64,'published_in_window':5,'matched_focus_products':3,'daily_rows':57,'yesterday_rows':5,'historical_rows':52,'historical_source':'截至10/12原始分天读数；本次新增10/13浮层实采并核对最新累计概览'},scope_note='截至昨日最近30个自然日内发布的5条内容；详情发布时间与官方导出时间分别保留。六项日曲线共57条日记录，累计快照截止见各内容。合作状态截至10/12；独立广告计划与实际消耗未取得。',source='2026-10-14官方任务报告完整导出64条＋5条内容详情与10/13分天浮层；历史52条沿用原始实采证据。')

wr(O/'gravity-content-month.json',g)
for fn,rs in [('gravity-content-month.csv',[{k:v for k,v in p.items() if not isinstance(v,(list,dict))} for p in g['snapshots']]),('gravity-content-daily.csv',g['daily'])]:csvout(O/fn,rs)
wr(O/'引力数据校验结果.json',{'status':'PASS','official_tasks':64,'content_count':5,'observed_daily_rows':57,'cutoff':END,'spu_code_associations_verified':True,'daily_dates_unique_complete_since_publication':True,'reconciliation':{p['content_id']:p['daily_reconciliation'] for p in g['snapshots']},'chart_cumulative':{p['content_id']:p['chart_cumulative'] for p in g['snapshots']}})
print(json.dumps({'result':'PASS','daily_count':len(g['daily']),'window':g['window'],'differences':{p['content_id']:{k:v for k,v in p['daily_reconciliation'].items() if not v['matches']} for p in g['snapshots']}},ensure_ascii=False))
