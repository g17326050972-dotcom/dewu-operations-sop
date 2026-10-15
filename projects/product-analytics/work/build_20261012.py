from pathlib import Path
import json,re,csv,datetime,html,shutil
B=Path('/Users/nan/Documents/Codex/2026-10-09/zai');O=B/'outputs/2026-10-12';D=O/'draft-site';S=B/'outputs/2026-10-11/draft-site';D.mkdir(exist_ok=True)
TODAY='2026-10-12';END='2026-10-11';START='2026-10-05';PRIOR='2026-09-28';PRIOREND='2026-10-04';NOW=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
def rd(p):return json.loads(p.read_text())
def wr(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def num(v):
 m=re.search(r'-?[\d,.]+',str(v));return float(m[0].replace(',','')) if m else None
def dates(a,b):
 a=datetime.date.fromisoformat(a);b=datetime.date.fromisoformat(b);return [(a+datetime.timedelta(days=i)).isoformat() for i in range((b-a).days+1)]
def csvout(p,rs,fields=None):
 fields=fields or list(dict.fromkeys(k for r in rs for k in r))
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rs)
tr=rd(S/'daily-readings.json');ch=rd(S/'channel-readings.json');cmp=rd(S/'weekly-comparisons.json');age=rd(S/'age-profiles.json')
off=rd(O/'2026-10-05_10-11_商品官方导出.json');index={r['商品货号']:r for r in off};newset=set(rd(O/'后台新上架名单_全类目.json')['codes']);oldp={p['code']:p for p in tr['products']}
all_dates=dates(PRIOR,END);current=all_dates[7:];prior=all_dates[:7];selection=[];products=[]
for c,r in index.items():
 assert r['类目名称'].split('-')[0]=='流行饰品/眼镜/服配'
 sales=int(num(r['我的销量']));uv=int(num(r['商详访问人数']));fav=int(num(r['收藏用户数']));new=c in newset;yes=sales>0 or fav>0 or new
 why='近7天有销量' if sales else '近7天有收藏' if fav else '本次后台新上架名单' if new else '近7天销量和收藏均0的老款'
 selection.append(dict(code=c,spu=r['SPUID'],title=r['商品标题'],sales=sales,uv=uv,favorites=fav,backendNew=new,included=yes,reason=why))
 if yes:products.append(dict(code=c,name=oldp.get(c,{}).get('name',r['商品标题']),backendNew=new,weekSales=sales,weekUv=uv,weekFavorites=fav,spuId=r['SPUID'],confirmedListingDate=None,newEvidence=TODAY+'后台新上架全量名单与类目官方导出交集；首次上架日待确认' if new else None,group='有销量款' if sales else '新品观察' if new else '有收藏款'))
products.sort(key=lambda p:(-p['weekSales'],-p['weekUv'],p['code']))
for i,p in enumerate(products):p['rank']=i+1
P={p['code']:p for p in products};assert len(P)==25
records={(r['code'],r['date']):r for r in tr['records']+cmp['businessDays'] if r.get('observed')}
for r in rd(O/'2026-10-11_商品日数据.json'):records[r['code'],END]=dict(r,date=END,source=TODAY+'后台昨日主值读数')
biz=[];missing=[]
for c,p in P.items():
 for d in all_dates:
  if(c,d) in records:r=dict(records[c,d],observed=True)
  else:r=dict(code=c,date=d,observed=False,**{k:None for k in ['uv','orders','favorites','conversionPct','amount']},missing_reason='该日期历史查询未返回商品记录，真实上架日期尚未确认');missing.append([c,d])
  r.update(name=p['name'],backendNew=p['backendNew'],favoriteRate=r['favorites']/r['uv']*100 if r['uv'] else None);biz.append(r)
assert len(biz)==350 and len(missing)==55
tr.update(dates=current,products=products,top=list(P)[:10],records=[r for r in biz if r['date'] in current],observedCount=155,expectedCount=175)
cmp.update(report_end=END,businessDays=[r for r in biz if r['date'] in prior],businessPeriods=[],selection=selection,pending_listing_codes=[])
for r in rd(O/'2026-09-28_10-04_商品区间数据.json'):
 if r['code'] in P:cmp['businessPeriods'].append(dict(r,start=PRIOR,end=PRIOREND,source=TODAY+'后台指定7日区间原值，46款'))
for c,p in P.items():
 r=index[c];cmp['businessPeriods'].append(dict(code=c,start=START,end=END,amount=num(r['支付金额']),orders=num(r['支付订单数']),uv=num(r['商详访问人数']),favorites=num(r['收藏用户数']),conversionPct=num(r['商详转化率']),paidUsers=num(r['支付用户数']),source='10/05—10/11官方商品明细导出'))
assert len(cmp['businessPeriods'])==45
for r in cmp['businessPeriods']:
 rs=[x for x in biz if x['code']==r['code'] and r['start']<=x['date']<=r['end']]
 if all(x['observed'] for x in rs):
  for k in ['orders','amount']:assert abs(sum(x[k] for x in rs)-r[k])<.01,(r['code'],k,sum(x[k] for x in rs),r[k])
cm={'全部':'total','商品竞争力':'competition','商品推荐':'recommend','商品搜索':'search','新品保量':'new_guarantee','付费推广':'paid','得物推':'push','引力':'gravity','平台活动':'activity','内容自运营':'content','用户运营':'users','其他':'other'}
def parse(p):
 st=p.read_text();part=st[st.index('文本 渠道明细'):];v={}
 for row in re.split(r'\n\s*\d+ row\n',part)[1:]:
  cs=re.split(r'(?:^|\n)\s*\d+ 单元格[^\n]*\n',row)[1:]
  if len(cs)<2:continue
  label=re.search(r'\d+ 文本 (.+)',cs[0]);val=re.search(r'\d+ 文本 ([\d,]+)',cs[1])
  if label and label[1] in cm and val:v[cm[label[1]]]=int(val[1].replace(',',''))
 return v
primary=['competition','paid','activity','content','users','other'];unavailable=sorted(p.name.split('_')[0] for p in O.glob('*_无渠道入口.txt'));assert len(unavailable)==6
ch['products']={c:ch['products'].get(c,dict(code=c,days={})) for c in P};cr=[]
for c,p in ch['products'].items():
 p.update(P[c],eligible=True,topObservation=c in tr['top'],source_status='not_exposed_in_backend' if c in unavailable else 'observed',verified_date=TODAY)
 p['days']={d:v for d,v in p['days'].items() if d in all_dates}
 if c in unavailable:p.update(source_note=TODAY+'逐款复核仅核心指标入口；保留经营和底部年龄画像。',days={});continue
 f=O/(c+'_daily_渠道.txt');assert '2026-10-11 至 2026-10-11' in f.read_text(),c
 v=parse(f);assert sum(v[k] for k in primary)==v['total'],c
 p['days'][END]=dict(total=v.pop('total'),values=v,observed=True,primary_complete=True,source={'kind':'observed_ui_channel_table','collected_date':TODAY})
 p['source_note']='09/28—10/11连续14日已实采。' if len(p['days'])==14 else '本次新增商品，10/09—10/11来源日值已实采；更早经营查询未返回商品记录。'
 for d,r in p['days'].items():
  assert sum(r['values'][k] for k in primary)==r['total'],(c,d)
  r.update(primary_sum=r['total'],primary_sum_matches_total=True);cr.append(dict(code=c,date=d,total=r['total'],**r['values']))
 if set(current)<=set(p['days']):assert sum(p['days'][d]['total'] for d in current)==num(index[c]['商详访问次数']),(c,'weekly pv')
cmp['channelPeriods']=[]
for c in P:
 if c in unavailable:continue
 f=O/(c+'_period_渠道.txt');assert START+' 至 '+END in f.read_text(),c
 v=parse(f);assert sum(v[k] for k in primary)==v['total'];assert v['total']==num(index[c]['商详访问次数']),(c,v['total'],index[c]['商详访问次数'])
 cmp['channelPeriods'].append(dict(code=c,start=START,end=END,total=v.pop('total'),values=v,source='后台当前7日渠道表原值'))
 if set(prior)<=set(ch['products'][c]['days']):
  rs=[ch['products'][c]['days'][d] for d in prior];ks=set.intersection(*[set(r['values']) for r in rs]);v={k:sum(r['values'][k] for r in rs) for k in ks};total=sum(r['total'] for r in rs)
  previous_file=O/(c+'_prior_渠道.txt');source='完整7日可加总PV日值，人数未相加'
  if previous_file.exists():
   assert PRIOR+' 至 '+PRIOREND in previous_file.read_text();actual=parse(previous_file);assert actual['total']==total
   for k in primary:assert actual[k]==v[k],(c,k,actual[k],v[k])
   total=actual.pop('total');v=actual;source='2026-10-12后台前7日渠道表原值，一级合计与7日日值核对'
  cmp['channelPeriods'].append(dict(code=c,start=PRIOR,end=PRIOREND,total=total,values=v,source=source))
assert len(cr)==211 and len(cmp['channelPeriods'])==33
ch.update(data_date=END,dates=all_dates,collected_date=TODAY,built_at=NOW,collected_at=NOW)
ch['coverage']=dict(category_product_count=51,active_product_count=25,excluded_product_count=26,pending_listing_product_count=0,period_date_count=14,expected_product_day_count=350,observed_product_day_count=211,observed_product_count=19,observed_counts_by_date={d:sum(d in p['days'] for p in ch['products'].values()) for d in all_dates},products_with_complete_period=[c for c,p in ch['products'].items() if len(p['days'])==14],complete_period_product_count=14,source_status_counts={'observed':19,'not_exposed_in_backend':6},source_not_exposed_codes=unavailable,source_not_yet_verified_codes=[],target_codes=list(P),target_product_count=25,head_observation_codes=tr['top'],missing_dates_by_code={c:[d for d in all_dates if d not in p['days']] for c,p in ch['products'].items()})
ch['notes']=['PV与UV分开；一级渠道合计逐日核对，不重复相加父子渠道。','14款具有完整两周来源，5款新记录具有10/09—10/11三日来源，6款经核验仅核心指标入口。','二级渠道只有实际取得的日期和区间显示数值；不从四舍五入环比倒推。']
ar=rd(O/'年龄原始读数.json');assert set(ar['products'])==set(P) and ar['period']=={'start':START,'end':END}
age.update(period={'start':START,'end':END},collectedDate=TODAY,compiledAt=NOW,products=[],coverage={'focusProducts':25,'observedProducts':25,'cohorts':75,'rawPercentValues':375})
ac=[]
for c,p in P.items():
 cohorts={}
 for k,field,label in [('paid','支付用户数','支付用户'),('browse','商详访问人数','浏览用户'),('favorite','收藏用户数','收藏用户')]:
  count=int(num(index[c][field]));vals=ar['products'][c][k];assert(count==0 and sum(vals)==0)or(count>0 and abs(sum(vals)-100)<.031),(c,k,count,vals)
  cohorts[k]=dict(label=label,totalUsers=count,totalSourceField=field,status='no_users' if count==0 else 'observed',sharesPct=vals,ageCounts=None,rawShareSumPct=round(sum(vals),2))
  for ag,v in zip(ar['groups'],vals):ac.append(dict(code=c,spu=p['spuId'],name=p['name'],start=START,end=END,cohort=label,totalUsers=count,ageGroup=ag,sharePct=v,status=cohorts[k]['status']))
 age['products'].append(dict(code=c,spuId=p['spuId'],name=p['name'],category=index[c]['类目名称'],start=START,end=END,source='核心指标底部年龄分布' if c in unavailable else '成交分析底部年龄分布',cohorts=cohorts))
# Gravity: refreshed official full task export plus verified content details; historical daily originals retained.
g=rd(S/'gravity-content-month.json');new=rd(O/'引力内容新增读数.json');export=rd(O/'引力任务报告官方导出.json');spus={str(r['SPUID']):r['商品货号'] for r in off}
recent=[r for r in export if '2026-09-12'<=r['动态发布时间'][:10]<=END];assert len(export)==64 and len(recent)==5
assert {r['子任务ID'] for r in recent}=={r['task_id'] for r in new['daily']}
gindex={r['子任务ID']:r for r in recent};snapold={p['content_id']:p for p in g['snapshots']};snapshots=[]
mp={'exposure':'曝光pv','reads':'阅读pv','interactions':'互动pv','detail_visits':'商详访问pv','favorites':'引导商品收藏数','attributed_orders_14d':'14日归因订单量','attributed_gmv_14d':'14日归因GMV','help_orders':'帮助成交订单','help_gmv':'帮助成交金额','curated_exposure':'穿搭精选曝光量','curated_reads':'穿搭精选阅读量','curated_help_orders':'穿搭精选辅助下单数','cooperation_fee':'子任务金额','backend_visit_cost':'商详访问成本','ctr_pct':'动态点击率','detail_lead_rate_pct':'内容引导商详率'}
for cid,meta in new['contents'].items():
 r=gindex[meta['task_id']];assert spus[str(r['货号（spu_id）'])]==meta['code']
 p=dict(snapold.get(cid,{}));p.update({k:num(r[f]) for k,f in mp.items()});p.update(meta)
 p.update(data_as_of=meta['as_of'],export_published_at=r['动态发布时间'],spu_id=str(r['货号（spu_id）']),creator=r['达人昵称'],product_name=P[meta['code']]['name'],association_evidence='引力官方任务报告SPU ID与商家官方SPU导出货号一一匹配；10/12逐条详情核验内容ID、发布时间、合作状态与金额',metric_scope='内容发布后累计快照，截止时间以每条内容为准',actual_ad_spend=None,notes=['官方导出发布时间与任务详情不一致，展示及日趋势采用任务详情时间；导出原值留档。'])
 d=next(x for x in new['daily'] if x['content_id']==cid);d.update(creator=p['creator'],source=TODAY+'引力任务详情发布后30天/7天分天图浮层原值，日期'+END);g['daily'].append(d)
 ds=sorted([x for x in g['daily'] if x['content_id']==cid],key=lambda x:x['date']);assert [x['date'] for x in ds]==dates(p['published_at'][:10],END)
 p['daily_reconciliation']={k:{'daily_sum':sum(x[k] for x in ds),'cumulative':p[k],'matches':sum(x[k] for x in ds)==p[k]} for k in g['fields']}
 p['plan_status']=None;p['plan_status_note']='已取得达人任务内容数据；独立广告计划状态、预算与实际广告消耗无对应字段，不以任务金额代替。'
 p['daily_missing_fields']=['14日归因GMV','帮助成交订单','帮助成交金额','独立广告实际消耗','广告点击']
 if cid=='535391676':p['notes'].append('10/12核验：分天图显示累计商详访问61，详情概览及官方导出为57；保留两处原值，不改平。')
 snapshots.append(p)
g['snapshots']=sorted(snapshots,key=lambda p:p['published_at'],reverse=True)
g['daily']=sorted(g['daily'],key=lambda p:(p['content_id'],p['date']));assert len(g['daily'])==47
assert len({(r['content_id'],r['date']) for r in g['daily']})==47
g.update(window={'start':'2026-09-12','end':END},reverified_at=NOW,refresh_status='complete',refresh_note='本次完整导出64条任务，以官方发布时间筛选5条近月内容，逐条核验详情真实发布时间、数据截止时间与昨日分天值。',reverification={'official_export_rows':64,'published_in_window':5,'matched_focus_products':3,'daily_rows':47,'yesterday_rows':5,'historical_rows':42,'historical_source':'截至10/10原始分天读数；本次新增10/11浮层实采并核对最新累计概览'},scope_note='截至昨日最近30个自然日内发布的5条内容；详情发布时间与导出时间同时保留，展示采用详情时间。六项日曲线有47条日记录。累计与日合计不一致保留差异；周对比只使用完整日期。',source='2026-10-12官方任务报告完整导出64条＋5条内容详情与10/11分天浮层；历史42条沿用实采证据。')
cmp['gravity']=g
cmp['gaps']=dict(business_day_baseline='5款新增记录09/28—10/08查询未返回商品，不填0；其余20款两周日值齐。',channel_day_baseline='14款一级来源两周齐；5款新增商品有10/09—10/11原值；6款核心指标页无渠道入口；部分二级历史有缺口。',gravity='近月5条内容及截至10/11六项分天值已取得；独立广告计划、实际广告消耗及广告点击未取得，分天图无GMV和帮助成交指标，累计值单列。',listing='16款来自本次后台新上架名单，真实首次上架日期未确认。',causes='实际优惠、库存、活动及独立投放消耗历史未取得，不能把渠道变化直接当作已证明原因。')
blocker='原日报 Sites 项目 [原站点标识已移除] 返回404 Project not found；当前连接完整站点列表不含该项目，需恢复原账号/工作区编辑权限。'
cmp['coverage']=dict(business_products=25,business_dates=all_dates,business_records=295,business_missing_records=55,channel_products=19,channel_days=211,channel_unavailable_products=unavailable,channel_history_pending_products=[],gravity_contents=5,gravity_content_days=47,business_cutoff=END,content_cutoff=END,collected_date=TODAY,age_profile=age['coverage']|age['period'],publication_status='ready_pending_original_site_access')
pending_children=[c for c,p in ch['products'].items() if len(p['days'])==14 and not (O/(c+'_prior_渠道.txt')).exists()]
cmp['coverage']['channel_previous_week_child_pending_products']=pending_children
cmp['coverage']['channel_previous_week_actual_products']=14-len(pending_children)
cmp['gaps']['channel_previous_week_children']='前周一级来源均已核对。前周二级渠道已实采10款，剩余'+','.join(pending_children)+'因Mac锁屏暂停补核，缺失留空；二级每日历史缺口仍保留。'
cmp['coverage']['publication_status']='held_original_site_access_and_channel_backfill'
coverage=cmp['coverage']|{'gaps':cmp['gaps'],'business_missing':missing,'new_watch_count':sum(p['backendNew'] for p in products),'channel_coverage':ch['coverage'],'publication_blocker':blocker}
for fn,data in [('daily-readings.json',tr),('channel-readings.json',ch),('weekly-comparisons.json',cmp),('age-profiles.json',age),('coverage.json',coverage),('gravity-content-month.json',g)]:
 for root in [D,O]:wr(root/fn,data)
for fn,rs,fields in [('business-two-weeks.csv',biz,['code','name','date','uv','orders','favorites','favoriteRate','conversionPct','amount','observed','missing_reason','source']),('channel-two-weeks.csv',cr,['code','date','total','competition','recommend','search','new_guarantee','paid','push','gravity','activity','content','users','other']),('weekly-periods.csv',cmp['businessPeriods'],['code','start','end','amount','orders','uv','favorites','conversionPct','paidUsers','source']),('selection-audit.csv',selection,['code','spu','title','sales','uv','favorites','backendNew','included','reason']),('age-profiles.csv',ac,['code','spu','name','start','end','cohort','totalUsers','ageGroup','sharePct','status']),('gravity-content-month.csv',[{k:v for k,v in p.items() if not isinstance(v,(dict,list))} for p in g['snapshots']],None),('gravity-content-daily.csv',g['daily'],None)]:
 csvout(O/fn,rs,fields);shutil.copy2(O/fn,D/fn)
wr(O/'校验结果.json',{'focus':25,'category_rows':51,'new_watch':16,'business_observed':295,'business_missing':55,'backend_week_periods':45,'source_observed_days':211,'source_full14_products':14,'source_new3_products':5,'source_unavailable_products':6,'age_products':25,'age_cohorts':75,'age_percent_values':375,'business_amount_order_sums_checked':True,'primary_pv_sums_checked':True,'weekly_pv_totals_checked':True,'gravity_official_task_rows':64,'gravity_contents':5,'gravity_daily_rows':47,'status':'ready_pending_original_site_access'})
print(json.dumps({'coverage':cmp['coverage'],'gravity_differences':{p['content_id']:{k:v for k,v in p['daily_reconciliation'].items() if not v['matches']} for p in g['snapshots']}},ensure_ascii=False))
