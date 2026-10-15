# -*- coding: utf-8 -*-
from pathlib import Path
import json,re,csv,datetime,shutil
B=Path('/Users/nan/Documents/Codex/2026-10-09/zai');O=B/'outputs/2026-10-14';D=O/'draft-site';S=B/'outputs/2026-10-13/draft-site';D.mkdir(exist_ok=True)
TODAY='2026-10-14';END='2026-10-13';START='2026-10-07';PRIOR='2026-09-30';PE='2026-10-06'
def rd(p):return json.loads(p.read_text())
def num(v):return float(re.search(r'[\d,.]+',str(v))[0].replace(',',''))
def wr(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def dates(a,b):
 a=datetime.date.fromisoformat(a);b=datetime.date.fromisoformat(b);return [(a+datetime.timedelta(days=i)).isoformat() for i in range((b-a).days+1)]
def csvout(name,rs):
 fields=list(dict.fromkeys(k for r in rs for k in r))
 with (O/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rs)
 shutil.copy2(O/name,D/name)
tr=rd(S/'daily-readings.json')|rd(O/'daily-readings.json');history=rd(O/'business-history.json');ch=rd(S/'channel-readings.json');cmp=rd(S/'weekly-comparisons.json');age=rd(S/'age-profiles.json');g=rd(O/'gravity-content-month.json')
P={p['code']:p for p in tr['products']};off={r['商品货号']:r for r in rd(O/'2026-10-07_10-13_商品官方导出.json')};all_dates=dates(PRIOR,END)
# Keep the full historical query evidence; chart tooltips fill metrics independently.
records={(r['code'],r['date']):dict(r) for r in history['records']}
metric_names={'商详访客人数':'uv','支付订单数':'orders','收藏用户数':'favorites','商详转化':'conversionPct','支付金额':'amount'}
chart_reads=[]
for f in sorted(O.glob('*_经营图表_*.txt')):
 c=f.name.split('_')[0];st=f.read_text();m=re.search(r'(?:text|文本) (\d\d\.\d\d)(.*)',st)
 if not m:continue
 d='2026-'+m[1].replace('.','-');vals={key:float(v[1]) for label,key in metric_names.items() if (v:=re.search(re.escape(label)+r' ([\d.]+)',m[2]))}
 if not vals:continue
 r=records[c,d]
 for k,v in vals.items():
  if r.get('observed') and r.get(k) is not None:assert abs(r[k]-v)<.001,(c,d,k,r[k],v)
  r[k]=v
 r.setdefault('metricSources',{}).update({k:f.name for k in vals});chart_reads.append(dict(code=c,date=d,**vals,source=f.name))
# User correction: a verified zero total covers its entire interval; never iterate zero days.
# Counts are nonnegative. Preserve this provenance separately from actual day readings.
zero_evidence=[]
fields={'orders':'支付订单数','favorites':'收藏用户数','uv':'商详访问人数','amount':'支付金额'}
for c,p in P.items():
 for k,field in fields.items():
  if num(off[c][field])!=0:continue
  evidence=dict(code=c,metric=k,start=START,end=END,total=0,source='10/07—10/13官方商品明细导出',method='verified_zero_interval')
  zero_evidence.append(evidence)
  for d in dates(START,END):
   r=records[c,d]
   if r.get(k) is None:r[k]=0;r.setdefault('metricSources',{})[k]='verified_zero_interval:10/07—10/13官方商品明细导出'
biz=[]
for (c,d),r in records.items():
 r['observed']=all(r.get(k) is not None for k in ['uv','orders','favorites'])
 if r.get('uv')==0:
  r['backendConversionPct']=r.get('conversionPct');r['conversionPct']=None
 r['favoriteRate']=r['favorites']/r['uv']*100 if r.get('uv') and r.get('favorites') is not None else None
 if r['observed']:r.pop('missing_reason',None)
 else:r['missing_reason']='该日完整类目列表未返回商品；未提供的指标留空，不将—视为0。'
 biz.append(r)
biz.sort(key=lambda r:(P[r['code']]['rank'],r['date']))
tr.update(dates=dates(START,END),records=[r for r in biz if r['date']>=START],observedCount=sum(r['observed'] for r in biz if r['date']>=START),expectedCount=len(P)*7)
cmp.update(report_end=END,businessDays=[r for r in biz if r['date']<START],businessPeriods=history['periods'],selection=history['selection'],pending_listing_codes=[])
for r in cmp['businessPeriods']:
 if r.get('uv')==0:r['backendConversionPct']=r.get('conversionPct');r['conversionPct']=None
 rs=[x for x in biz if x['code']==r['code'] and r['start']<=x['date']<=r['end']]
 for k in ['orders','amount']:
  if len(rs)==7 and all(x.get(k) is not None for x in rs):assert abs(sum(x[k] for x in rs)-r[k])<.01,(r['code'],k)
cm={'全部':'total','商品竞争力':'competition','商品推荐':'recommend','商品搜索':'search','新品保量':'new_guarantee','付费推广':'paid','得物推':'push','引力':'gravity','平台活动':'activity','内容自运营':'content','用户运营':'users','其他':'other'}
primary=['competition','paid','activity','content','users','other']
def parse_channel(f):
 st=f.read_text();part=st[st.index('文本 渠道明细'):];v={}
 for row in re.split(r'\n\s*\d+ row\n',part)[1:]:
  cs=re.split(r'(?:^|\n)\s*\d+ 单元格[^\n]*\n',row)[1:]
  if len(cs)<2:continue
  label=re.search(r'\d+ 文本 (.+)',cs[0]);val=re.search(r'\d+ 文本 ([\d,]+)',cs[1])
  if label and label[1] in cm and val:v[cm[label[1]]]=int(val[1].replace(',',''))
 assert sum(v[k] for k in primary)==v['total'],f.name
 dt=re.search(r'(2026-\d\d-\d\d) 至 (2026-\d\d-\d\d)',st)
 return dt[1],dt[2],v
unavailable=sorted(f.name.split('_')[0] for f in O.glob('*_无渠道入口.txt'));assert len(unavailable)==5
oldch=ch['products'];ch['products']={c:dict(oldch.get(c,dict(code=c,days={}))) for c in P};cmp['channelPeriods']=[];discrepancies=[]
for c,p in ch['products'].items():
 p.update(P[c],eligible=True,topObservation=c in tr['top'],source_status='not_exposed_in_backend' if c in unavailable else 'observed',verified_date=TODAY)
 p['days']={d:r for d,r in p['days'].items() if d in all_dates}
 if c in unavailable:p.update(days={},source_note='10/14逐款复核仅核心指标入口；经营趋势与底部年龄画像保留。');continue
 for suffix in ['daily','period','prior']:
  f=O/(c+'_'+suffix+'_渠道.txt');a,b,v=parse_channel(f)
  assert (a,b)==({'daily':(END,END),'period':(START,END),'prior':(PRIOR,PE)}[suffix]),f.name
  total=v.pop('total')
  if suffix=='daily':p['days'][END]=dict(total=total,values=v,observed=True,primary_complete=True,source={'kind':'observed_ui_channel_table','file':f.name})
  else:
   cmp['channelPeriods'].append(dict(code=c,start=a,end=b,total=total,values=v,source=f.name))
   if suffix=='period' and total!=float(off[c]['商详访问次数']):discrepancies.append(dict(code=c,start=a,end=b,channelPV=total,businessPV=float(off[c]['商详访问次数']),difference=total-float(off[c]['商详访问次数']),status='保留后台两处原值，统计口径或上架前归属差异待验证'))
  if total==0:
   for d in dates(a,b):
    if d not in p['days']:p['days'][d]=dict(total=0,values={k:0 for k in v},observed=True,primary_complete=True,source={'kind':'verified_zero_interval','file':f.name,'start':a,'end':b})
 for f in O.glob(c+'_*_渠道图表.txt'):
  st=f.read_text();m=re.search(r'文本 (2026\d{4})',st)
  if not m:continue
  dt=m[1];d=dt[:4]+'-'+dt[4:6]+'-'+dt[6:];part=st[m.start():];labels=re.findall(r'\d+ 文本 ([^\n]+)',part);v={}
  for i,k in enumerate(labels[:-1]):
   if k in cm and re.fullmatch(r'\d+',labels[i+1]):v[cm[k]]=int(labels[i+1])
  assert set(primary+['total'])<=set(v),(f.name,v)
  total=v.pop('total');assert sum(v[k] for k in primary)==total
  if d in p['days']:
   for k in primary:assert p['days'][d]['values'][k]==v[k],(c,d,k)
   p['days'][d]['values'].update(v)
  else:p['days'][d]=dict(total=total,values=v,observed=True,primary_complete=True,source={'kind':'observed_ui_chart','file':f.name})
 for f in O.glob(c+'_gap_渠道.txt'):
  a,b,v=parse_channel(f);assert v['total']==0
  for d in dates(a,b):p['days'].setdefault(d,dict(total=0,values={k:0 for k in v if k!='total'},observed=True,primary_complete=True,source={'kind':'verified_zero_interval','file':f.name,'start':a,'end':b}))
 for per in [r for r in cmp['channelPeriods'] if r['code']==c]:
  if set(dates(per['start'],per['end']))<=set(p['days']):
   for k in primary:assert sum(p['days'][d]['values'][k] for d in dates(per['start'],per['end']))==per['values'][k],(c,k,per)
 n=len(p['days']);p['source_note']=f'两周14日中已覆盖{n}日；明确为0的区间按区间依据覆盖，未逐日重复读取。'
 if c in [x['code'] for x in discrepancies]:p['source_note']+=' 来源周PV与经营导出不一致，见口径核对说明；两处原值保留。'
cr=[dict(code=c,date=d,total=r['total'],**r['values'],provenance=r.get('source',{}).get('kind','observed_ui'),source=json.dumps(r.get('source',{}),ensure_ascii=False)) for c,p in ch['products'].items() for d,r in sorted(p['days'].items())]
for p in ch['products'].values():
 for r in p['days'].values():assert sum(r['values'][k] for k in primary)==r['total'];r.update(primary_sum=r['total'],primary_sum_matches_total=True)
ch.update(data_date=END,dates=all_dates,collected_date=TODAY,built_at=datetime.datetime.now().isoformat(),scope_filter=dict(rule='backendNew || weekSales > 0 || weekFavorites > 0',period_start=START,period_end=END,category_product_count=55,active_product_count=28,active_codes=list(P),excluded_products=[r for r in history['selection'] if not r['included']]))
ch['coverage']=dict(category_product_count=55,active_product_count=28,excluded_product_count=27,period_date_count=14,expected_product_day_count=28*14,observed_product_day_count=len(cr),observed_product_count=23,target_codes=list(P),target_product_count=28,head_observation_codes=tr['top'],source_status_counts={'observed':23,'not_exposed_in_backend':5},source_not_exposed_codes=unavailable,source_not_yet_verified_codes=[],products_with_complete_period=[c for c,p in ch['products'].items() if len(p['days'])==14],complete_period_product_count=sum(len(p['days'])==14 for p in ch['products'].values()),observed_counts_by_date={d:sum(d in p['days'] for p in ch['products'].values()) for d in all_dates},missing_dates_by_code={c:[d for d in all_dates if d not in p['days']] for c,p in ch['products'].items()})
ch['notes']=['PV与UV分开；父子不重复相加，一级合计逐日核对。','明确零值区间直接覆盖零值日期，来源字段注明区间证据；—和未返回记录仍留空。','两款路路通来源周PV与经营页不同，保留原值，不改平。']
ar=rd(O/'年龄原始读数.json');assert set(ar['products'])==set(P)
age.update(period={'start':START,'end':END},collectedDate=TODAY,compiledAt=datetime.datetime.now().isoformat(),products=[],coverage={'focusProducts':28,'observedProducts':28,'cohorts':84,'rawPercentValues':420})
ac=[]
for c,p in P.items():
 cohorts={}
 for k,field,label in [('paid','支付用户数','支付用户'),('browse','商详访问人数','浏览用户'),('favorite','收藏用户数','收藏用户')]:
  count=int(off[c][field]);vals=ar['products'][c][k];assert (count==0 and sum(vals)==0) or (count>0 and abs(sum(vals)-100)<.031)
  cohorts[k]=dict(label=label,totalUsers=count,totalSourceField=field,status='no_users' if count==0 else 'observed',sharesPct=vals,ageCounts=None,rawShareSumPct=round(sum(vals),2))
  for ag,v in zip(ar['groups'],vals):ac.append(dict(code=c,spu=p['spuId'],name=p['name'],start=START,end=END,cohort=label,totalUsers=count,ageGroup=ag,sharePct=v,status=cohorts[k]['status']))
 age['products'].append(dict(code=c,spuId=p['spuId'],name=p['name'],category=off[c]['类目名称'],start=START,end=END,source='核心指标底部年龄分布' if c in unavailable else '成交分析底部年龄分布',cohorts=cohorts))
cmp['gravity']=g
cmp['gaps']=dict(business_day_baseline='完整历史列表复核及可得图表已回补；未返回商品且经营区间显示—的历史指标留空。区间零总量直接覆盖零值，来源另注。',channel_day_baseline='23款有来源入口、5款核心页未提供来源；所有23款两周区间已采，明确零值区间不再逐日检查。',channel_previous_week_children='本次23款两周区间一级与可得二级已采；部分历史日二级渠道仍缺。',gravity=g.get('refresh_note',''),listing='20款来自后台新品名单，真实首次上架日期未确认。',causes='历史实际优惠、库存、活动与独立广告实际消耗未取得，不把渠道贡献变化当作已证明成因。')
missing=[[r['code'],r['date']] for r in biz if not r['observed']]
cmp['coverage']=dict(business_products=28,business_dates=all_dates,business_records=sum(r['observed'] for r in biz),business_missing_records=len(missing),channel_products=23,channel_days=len(cr),channel_unavailable_products=unavailable,channel_history_pending_products=[c for c,p in ch['products'].items() if 0<len(p['days'])<14],gravity_contents=5,gravity_content_days=57,business_cutoff=END,content_cutoff=END,collected_date=TODAY,age_profile=age['coverage']|age['period'],publication_status='ready_with_verified_gaps',channel_previous_week_actual_products=23)
coverage=cmp['coverage']|dict(gaps=cmp['gaps'],business_missing=missing,new_watch_count=20,channel_coverage=ch['coverage'],pv_scope_discrepancies=discrepancies,zero_interval_policy='用户10/14修正：区间总量为0直接标零，不逐天重复采集；—不填0。无访客转化率显示—，后台0另存。',zero_interval_evidence=zero_evidence)
for fn,data in [('daily-readings.json',tr),('channel-readings.json',ch),('weekly-comparisons.json',cmp),('age-profiles.json',age),('coverage.json',coverage),('gravity-content-month.json',g)]:
 for root in [O,D]:wr(root/fn,data)
for fn,rs in [('business-two-weeks.csv',biz),('channel-two-weeks.csv',cr),('weekly-periods.csv',cmp['businessPeriods']),('channel-weekly-periods.csv',[dict(code=r['code'],start=r['start'],end=r['end'],total=r['total'],**r['values'],source=r['source']) for r in cmp['channelPeriods']]),('selection-audit.csv',history['selection']),('age-profiles.csv',ac),('zero-interval-evidence.csv',zero_evidence),('pv-scope-discrepancies.csv',discrepancies)]:csvout(fn,rs)
for fn in ['gravity-content-daily.csv','gravity-content-month.csv']:shutil.copy2(O/fn,D/fn)
wr(O/'图表补采读数.json',chart_reads);wr(O/'商家数据校验结果.json',cmp['coverage']|{'primary_sums_pass':True,'complete_period_channel_sums_pass':True,'age_shares_pass':True,'pv_scope_discrepancies':discrepancies})
print(json.dumps(cmp['coverage']|{'pv_scope_discrepancies':discrepancies},ensure_ascii=False))
