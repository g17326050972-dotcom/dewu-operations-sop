from pathlib import Path
import json,re,csv,datetime,shutil
B=Path('/Users/nan/Documents/Codex/2026-10-09/zai');O=B/'outputs/2026-10-13';D=O/'draft-site';S=B/'outputs/2026-10-12/draft-site';D.mkdir(exist_ok=True)
TODAY='2026-10-13';END='2026-10-12';START='2026-10-06';PRIOR='2026-09-29';PRIOREND='2026-10-05';NOW=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
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
off=rd(O/'2026-10-06_10-12_商品官方导出.json');index={r['商品货号']:r for r in off};newset=set(rd(O/'后台新上架名单_类目交集.json')['codes']);oldp={p['code']:p for p in tr['products']}
all_dates=dates(PRIOR,END);current=all_dates[7:];prior=all_dates[:7];selection=[];products=[]
for c,r in index.items():
 assert r['类目名称'].split('-')[0]=='流行饰品/眼镜/服配'
 sales=int(num(r['我的销量']));uv=int(num(r['商详访问人数']));fav=int(num(r['收藏用户数']));new=c in newset;yes=sales>0 or fav>0 or new
 why='近7天有销量' if sales else '近7天有收藏' if fav else '本次后台新上架名单' if new else '近7天销量和收藏均0的老款'
 selection.append(dict(code=c,spu=r['SPUID'],title=r['商品标题'],sales=sales,uv=uv,favorites=fav,backendNew=new,included=yes,reason=why))
 if yes:products.append(dict(code=c,name=oldp.get(c,{}).get('name',r['商品标题']),backendNew=new,weekSales=sales,weekUv=uv,weekFavorites=fav,spuId=r['SPUID'],confirmedListingDate=None,newEvidence=TODAY+'后台新上架类目16款名单；首次上架日待确认' if new else None,group='有销量款' if sales else '新品观察' if new else '有收藏款'))
products.sort(key=lambda p:(-p['weekSales'],-p['weekUv'],p['code']))
for i,p in enumerate(products):p['rank']=i+1
P={p['code']:p for p in products};assert len(P)==25
records={(r['code'],r['date']):r for r in tr['records']+cmp['businessDays'] if r.get('observed')}
for r in rd(O/'2026-10-12_商品日数据.json'):records[r['code'],END]=dict(r,date=END,source=TODAY+'后台昨日主值读数')
biz=[];missing=[]
for c,p in P.items():
 for d in all_dates:
  if(c,d) in records:r=dict(records[c,d],observed=True)
  else:r=dict(code=c,date=d,observed=False,**{k:None for k in ['uv','orders','favorites','conversionPct','amount']},missing_reason='该日期历史主列表查询未返回商品记录，真实上架日期尚未确认');missing.append([c,d])
  r.update(name=p['name'],backendNew=p['backendNew'],favoriteRate=r['favorites']/r['uv']*100 if r['uv'] else None);biz.append(r)
tr.update(dates=current,products=products,top=list(P)[:10],records=[r for r in biz if r['date'] in current],observedCount=sum(r['observed'] for r in biz if r['date'] in current),expectedCount=len(P)*7)
cmp.update(report_end=END,businessDays=[r for r in biz if r['date'] in prior],businessPeriods=[],selection=selection,pending_listing_codes=[])
for r in rd(O/'2026-09-29_10-05_商品区间数据.json'):
 if r['code'] in P:cmp['businessPeriods'].append(dict(r,start=PRIOR,end=PRIOREND,source=TODAY+'后台指定7日区间原值，46款'))
for c,p in P.items():
 r=index[c];cmp['businessPeriods'].append(dict(code=c,start=START,end=END,amount=num(r['支付金额']),orders=num(r['支付订单数']),uv=num(r['商详访问人数']),favorites=num(r['收藏用户数']),conversionPct=num(r['商详转化率']),paidUsers=num(r['支付用户数']),source='10/06—10/12官方商品明细导出'))
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
ch['products']={c:ch['products'].get(c,dict(code=c,days={})) for c in P};cr=[];cmp['channelPeriods']=[]
for c,p in ch['products'].items():
 p.update(P[c],eligible=True,topObservation=c in tr['top'],source_status='not_exposed_in_backend' if c in unavailable else 'observed',verified_date=TODAY)
 p['days']={d:v for d,v in p['days'].items() if d in all_dates}
 if c in unavailable:p.update(source_note=TODAY+'逐款复核仅核心指标入口；保留经营和底部年龄画像。',days={});continue
 f=O/(c+'_daily_渠道.txt');assert END+' 至 '+END in f.read_text(),c
 v=parse(f);assert sum(v[k] for k in primary)==v['total'],c
 p['days'][END]=dict(total=v.pop('total'),values=v,observed=True,primary_complete=True,source={'kind':'observed_ui_channel_table','collected_date':TODAY})
 p['source_note']='09/29—10/12连续14日已实采。' if len(p['days'])==14 else '10/09—10/12来源日值已实采；更早日值尚未取得，周区间直接读取后台。'
 for d,r in p['days'].items():
  assert sum(r['values'][k] for k in primary)==r['total'],(c,d)
  r.update(primary_sum=r['total'],primary_sum_matches_total=True);cr.append(dict(code=c,date=d,total=r['total'],**r['values']))
 for a,b,suffix in [(START,END,'period'),(PRIOR,PRIOREND,'prior')]:
  f=O/(c+'_'+suffix+'_渠道.txt');assert a+' 至 '+b in f.read_text(),(c,suffix)
  v=parse(f);assert sum(v[k] for k in primary)==v['total'],(c,suffix)
  if suffix=='period':assert v['total']==num(index[c]['商详访问次数']),(c,'weekly pv',v['total'],index[c]['商详访问次数'])
  if set(dates(a,b))<=set(p['days']):
   for k in primary:assert sum(p['days'][d]['values'][k] for d in dates(a,b))==v[k],(c,suffix,k)
  cmp['channelPeriods'].append(dict(code=c,start=a,end=b,total=v.pop('total'),values=v,source=TODAY+'后台7日渠道表原值，一级合计核对'))
ch.update(data_date=END,dates=all_dates,collected_date=TODAY,built_at=NOW,collected_at=NOW)
ch['coverage']=dict(category_product_count=51,active_product_count=25,excluded_product_count=26,pending_listing_product_count=0,period_date_count=14,expected_product_day_count=350,observed_product_day_count=len(cr),observed_product_count=19,observed_counts_by_date={d:sum(d in p['days'] for p in ch['products'].values()) for d in all_dates},products_with_complete_period=[c for c,p in ch['products'].items() if len(p['days'])==14],complete_period_product_count=14,source_status_counts={'observed':19,'not_exposed_in_backend':6},source_not_exposed_codes=unavailable,source_not_yet_verified_codes=[],target_codes=list(P),target_product_count=25,head_observation_codes=tr['top'],missing_dates_by_code={c:[d for d in all_dates if d not in p['days']] for c,p in ch['products'].items()})
ch['notes']=['PV与UV分开；一级渠道合计逐日核对，不重复相加父子渠道。','14款具有完整两周来源，5款新记录具有10/09—10/12四日来源，6款经核验仅核心指标入口。','19款的当前周及前周一级、二级渠道区间原值本次均已实采；部分历史日二级渠道仍有缺口。']
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
g=rd(S/'gravity-content-month.json');g.update(refresh_status='blocked_login',refresh_note='10/13引力登录失效，10/12日值及新的近月内容名单尚未刷新；历史数据仍截至10/11。')
cmp['gravity']=g
cmp['gaps']=dict(business_day_baseline='5款新增记录09/29—10/08历史主列表未返回商品，不填0；其余20款两周日值齐。',channel_day_baseline='14款一级来源两周齐；5款新增商品有10/09—10/12原值；6款核心指标页无渠道入口；部分二级历史有缺口。',channel_previous_week_children='19款当前周与前周一级及可用二级渠道均已实采；之前4款待补的前周渠道已完成本次新范围核验。',gravity=g['refresh_note'],listing='16款来自本次后台新上架类目名单，真实首次上架日期未确认。',causes='实际优惠、库存、活动及独立投放消耗历史未取得，不能把渠道变化直接当作已证明原因。')
cmp['coverage']=dict(business_products=25,business_dates=all_dates,business_records=sum(r['observed'] for r in biz),business_missing_records=len(missing),channel_products=19,channel_days=len(cr),channel_unavailable_products=unavailable,channel_history_pending_products=[],gravity_contents=len(g['snapshots']),gravity_content_days=len(g['daily']),business_cutoff=END,content_cutoff='2026-10-11',collected_date=TODAY,age_profile=age['coverage']|age['period'],publication_status='held_gravity_login',channel_previous_week_child_pending_products=[],channel_previous_week_actual_products=19)
coverage=cmp['coverage']|{'gaps':cmp['gaps'],'business_missing':missing,'new_watch_count':sum(p['backendNew'] for p in products),'channel_coverage':ch['coverage'],'publication_blocker':'引力登录失效，待用户登录后补10/12内容；原网站权限已恢复。'}
for fn,data in [('daily-readings.json',tr),('channel-readings.json',ch),('weekly-comparisons.json',cmp),('age-profiles.json',age),('coverage.json',coverage),('gravity-content-month.json',g)]:
 for root in [D,O]:wr(root/fn,data)
for fn,rs,fields in [('business-two-weeks.csv',biz,['code','name','date','uv','orders','favorites','favoriteRate','conversionPct','amount','observed','missing_reason','source']),('channel-two-weeks.csv',cr,['code','date','total','competition','recommend','search','new_guarantee','paid','push','gravity','activity','content','users','other']),('weekly-periods.csv',cmp['businessPeriods'],['code','start','end','amount','orders','uv','favorites','conversionPct','paidUsers','source']),('selection-audit.csv',selection,['code','spu','title','sales','uv','favorites','backendNew','included','reason']),('age-profiles.csv',ac,['code','spu','name','start','end','cohort','totalUsers','ageGroup','sharePct','status'])]:
 csvout(O/fn,rs,fields);shutil.copy2(O/fn,D/fn)
validation={'focus':25,'category_rows':51,'new_watch':16,'business_observed':sum(r['observed'] for r in biz),'business_missing':len(missing),'backend_week_periods':len(cmp['businessPeriods']),'source_observed_days':len(cr),'source_week_periods':len(cmp['channelPeriods']),'source_full14_products':14,'source_unavailable_products':6,'age_products':25,'age_cohorts':75,'age_percent_values':375,'business_amount_order_sums_checked':True,'primary_pv_sums_checked':True,'weekly_pv_totals_checked':True,'status':'merchant_ready_gravity_login_required'};wr(O/'商家数据校验结果.json',validation);print(json.dumps(validation,ensure_ascii=False))
