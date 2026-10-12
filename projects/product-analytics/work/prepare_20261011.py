from pathlib import Path
import json,re,csv,datetime,html,shutil
B=Path('/Users/nan/Documents/Codex/2026-10-09/zai'); O=B/'outputs/2026-10-11'; D=O/'draft-site';D.mkdir(exist_ok=True)
S=B/'work/dewu-trend-site/dist';s=(S/'index.html').read_text()
def read(p):return json.loads((B/p).read_text())
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def embed(k):return json.loads(re.search('<script id="'+k+'" type="application/json">(.*?)</script>',s,re.S)[1])
def num(v):
 m=re.search(r'-?[\d,.]+',str(v));return float(m[0].replace(',','')) if m else None
def csvout(p,rs,fields):
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rs)
def dates(a,b):
 a=datetime.date.fromisoformat(a);b=datetime.date.fromisoformat(b);return [(a+datetime.timedelta(days=i)).isoformat() for i in range((b-a).days+1)]
oldtrend=embed('trend-data');tr=embed('trend-data');ch=embed('channel-data');cmp=embed('comparison-data');age=embed('age-data')
off=read('outputs/2026-10-11/2026-10-04_10-10_商品官方导出.json');index={r['商品货号']:r for r in off};newset=set(read('outputs/2026-10-11/后台新上架名单_全类目.json')['codes']);oldp={p['code']:p for p in tr['products']}
all_dates=dates('2026-09-27','2026-10-10');current=all_dates[7:];prior=all_dates[:7];selection=[];products=[]
short={'YS9542001':'八芒星星手链','YX9537001':'星球星芒项链','YX9507001':'圆形荟萃项链','YX9500001':'渐变圆形微笑弧线','YX9498001':'天使羽翼星芒','YX9499001':'云层甜裙','YX9343001':'一个熊抱'}
for c,r in index.items():
 assert r['类目名称'].split('-')[0]=='流行饰品/眼镜/服配'
 sales=int(num(r['我的销量']));uv=int(num(r['商详访问人数']));fav=int(num(r['收藏用户数']));new=c in newset;yes=sales>0 or fav>0 or new
 why='近7天有销量' if sales else '近7天有收藏' if fav else '本次后台新上架名单' if new else '近7天销量和收藏均0的老款'
 selection.append(dict(code=c,spu=r['SPUID'],title=r['商品标题'],sales=sales,uv=uv,favorites=fav,backendNew=new,included=yes,reason=why))
 if yes:products.append(dict(code=c,name=oldp.get(c,{}).get('name',short.get(c,r['商品标题'])),backendNew=new,weekSales=sales,weekUv=uv,weekFavorites=fav,spuId=r['SPUID'],confirmedListingDate=None,newEvidence='2026-10-11后台新上架全量名单与类目官方导出交集；首次上架日待确认' if new else None,group='有销量款' if sales else '新品观察' if new else '有收藏款'))
products.sort(key=lambda p:(-p['weekSales'],-p['weekUv'],p['code']))
for i,p in enumerate(products):p['rank']=i+1
P={p['code']:p for p in products};assert len(P)==25
records={(r['code'],r['date']):r for r in tr['records']+cmp['businessDays']}
for r in read('work/daily_trend.json')['records']:records[r['code'],r['date']]=r
r=read('outputs/2026-10-10/daily-1130/经营新增原始读数.json')
for d,rs in r['days'].items():
 for row in rs:records[row[0],d]=dict(zip(r['fields'],row),date=d,source=r['source'])
for r in read('outputs/2026-10-10/2026-10-01_商品经营官方导出.json'):
 c=r['商品货号'];records[c,'2026-10-01']=dict(code=c,date='2026-10-01',amount=num(r['支付金额']),orders=num(r['支付订单数']),uv=num(r['商详访问人数']),favorites=num(r['收藏用户数']),conversionPct=num(r['商详转化率']),source='同日官方导出')
for d,rs in read('outputs/2026-10-11/经营补采历史.json').items():
 for r in rs:records[r['code'],d]=dict(r,date=d,source='2026-10-11后台单日主值读数')
for r in read('outputs/2026-10-11/2026-10-10_商品日数据.json'):records[r['code'],'2026-10-10']=dict(r,date='2026-10-10',source='2026-10-11后台昨日主值读数')
biz=[];missing=[]
for c,p in P.items():
 for d in all_dates:
  if (c,d) in records:r=dict(records[c,d],observed=True)
  else:r=dict(code=c,date=d,observed=False,**{k:None for k in ['uv','orders','favorites','conversionPct','amount']},missing_reason='该日期历史查询未返回商品记录，真实上架日期尚未确认');missing.append([c,d])
  r.update(name=p['name'],backendNew=p['backendNew'],favoriteRate=r['favorites']/r['uv']*100 if r['uv'] else None);biz.append(r)
assert len(biz)==350 and len(missing)==60
tr.update(dates=current,products=products,top=list(P)[:10],records=[r for r in biz if r['date'] in current],observedCount=150,expectedCount=175)
cmp.update(report_end='2026-10-10',businessDays=[r for r in biz if r['date'] in prior],businessPeriods=[],selection=selection,pending_listing_codes=[])
for r in read('outputs/2026-10-11/2026-09-27_10-03_商品区间数据.json'):
 if r['code'] in P:cmp['businessPeriods'].append(dict(r,start=prior[0],end=prior[-1],source='2026-10-11后台指定7日区间原值，46款'))
for c,p in P.items():
 r=index[c];cmp['businessPeriods'].append(dict(code=c,start=current[0],end=current[-1],amount=num(r['支付金额']),orders=num(r['支付订单数']),uv=num(r['商详访问人数']),favorites=num(r['收藏用户数']),conversionPct=num(r['商详转化率']),paidUsers=num(r['支付用户数']),source='10/04—10/10官方商品明细导出'))
assert len(cmp['businessPeriods'])==45
for r in cmp['businessPeriods']:
 rs=[x for x in biz if x['code']==r['code'] and r['start']<=x['date']<=r['end']]
 if all(x['observed'] for x in rs):
  for k in ['orders','amount']:assert abs(sum(x[k] for x in rs)-r[k])<.01,(r['code'],k,sum(x[k] for x in rs),r[k])
# Reparse original channel AX tables so all recorded children are retained.
cm={'全部':'total','商品竞争力':'competition','商品推荐':'recommend','商品搜索':'search','新品保量':'new_guarantee','付费推广':'paid','得物推':'push','引力':'gravity','平台活动':'activity','内容自运营':'content','用户运营':'users','其他':'other'}
def parse(p):
 st=p.read_text();part=st[st.index('文本 渠道明细'):];v={}
 for row in re.split(r'\n\s*\d+ row\n',part)[1:]:
  cs=re.split(r'(?:^|\n)\s*\d+ 单元格[^\n]*\n',row)[1:]
  if len(cs)<2:continue
  label=re.search(r'\d+ 文本 (.+)',cs[0]);val=re.search(r'\d+ 文本 ([\d,]+)',cs[1])
  if label and label[1] in cm and val:v[cm[label[1]]]=int(val[1].replace(',',''))
 return v
nr=read('outputs/2026-10-11/渠道原始读数.json');primary=['competition','paid','activity','content','users','other'];unavailable=sorted(nr['unavailable'])
assert len(unavailable)==6
ch['products']={c:ch['products'].get(c,dict(code=c,days={})) for c in P};cr=[]
for c,p in ch['products'].items():
 p.update(P[c],eligible=True,topObservation=c in tr['top'],source_status='not_exposed_in_backend' if c in unavailable else 'observed',verified_date='2026-10-11')
 p['days']={d:v for d,v in p['days'].items() if d in all_dates}
 if c in unavailable:p.update(source_note='2026-10-11逐款复核仅核心指标入口；保留经营和底部年龄画像。',days={});continue
 for d,v in nr.get('history',{}).get(c,{}).items():
  p['days'][d]=dict(total=v['total'],values={('push' if k=='dewu_push' else k):x for k,x in v.items() if k!='total'},observed=True,primary_complete=True,primary_sum=v['total'],primary_sum_matches_total=True,source={'kind':'observed_ui_daily_filter','collected_date':'2026-10-11'})
 f=O/(c+'_daily_渠道.txt')
 if not f.exists():f=O/(c+'_10-10_流量原始.txt')
 v=parse(f);assert sum(v[k] for k in primary)==v['total']
 p['days']['2026-10-10']=dict(total=v.pop('total'),values=v,observed=True,primary_complete=True,source={'kind':'observed_ui_channel_table','collected_date':'2026-10-11'})
 p['source_note']='09/27—10/10连续14日已实采。' if len(p['days'])==14 else '本次新增商品，10/09、10/10来源日值已实采；更早经营查询未返回商品记录。'
 for d,r in p['days'].items():
  assert sum(r['values'][k] for k in primary)==r['total'],(c,d)
  r.update(primary_sum=r['total'],primary_sum_matches_total=True);cr.append(dict(code=c,date=d,total=r['total'],**r['values']))
 # Compare full present current week primary PV to official whole-week value.
 if set(current)<=set(p['days']):assert sum(p['days'][d]['total'] for d in current)==num(index[c]['商详访问次数']),(c,'weekly pv')
cmp['channelPeriods']=[]
for c in P:
 if c in unavailable:continue
 f=O/(c+'_period_渠道.txt')
 if not f.exists():f=O/(c+'_10-04_10-10_流量原始.txt')
 v=parse(f);assert v['total']==num(index[c]['商详访问次数']),(c,v['total'],index[c]['商详访问次数'])
 cmp['channelPeriods'].append(dict(code=c,start=current[0],end=current[-1],total=v.pop('total'),values=v,source='后台当前7日渠道表原值'))
 f=O/(c+'_prior_渠道.txt')
 if f.exists():
  assert '2026-09-27 至 2026-10-03' in f.read_text();v=parse(f);total=v.pop('total');source='后台前7日渠道表原值'
 elif set(prior)<=set(ch['products'][c]['days']):
  rs=[ch['products'][c]['days'][d] for d in prior];ks=set.intersection(*[set(r['values']) for r in rs]);v={k:sum(r['values'][k] for r in rs) for k in ks};total=sum(r['total'] for r in rs);source='完整7日可加总PV日值，人数未相加'
 else:continue
 assert total==sum(ch['products'][c]['days'][d]['total'] for d in prior)
 cmp['channelPeriods'].append(dict(code=c,start=prior[0],end=prior[-1],total=total,values=v,source=source))
assert len(cr)==206 and len(cmp['channelPeriods'])==33
ch.update(data_date='2026-10-10',dates=all_dates,collected_date='2026-10-11')
ch['coverage']=dict(category_product_count=51,active_product_count=25,excluded_product_count=26,pending_listing_product_count=0,period_date_count=14,expected_product_day_count=350,observed_product_day_count=206,observed_product_count=19,observed_counts_by_date={d:sum(d in p['days'] for p in ch['products'].values()) for d in all_dates},products_with_complete_period=[c for c,p in ch['products'].items() if len(p['days'])==14],complete_period_product_count=14,source_status_counts={'observed':19,'not_exposed_in_backend':6},source_not_exposed_codes=unavailable,source_not_yet_verified_codes=[],target_codes=list(P),target_product_count=25,head_observation_codes=tr['top'],missing_dates_by_code={c:[d for d in all_dates if d not in p['days']] for c,p in ch['products'].items()})
ch['notes']=['PV与UV分开；一级渠道合计逐日核对，不重复相加父子渠道。','14款具有完整两周来源，5款新记录具有10/09—10/10两日来源，6款经核验仅核心指标入口。','二级渠道只有实际取得的日期和区间显示数值；不从四舍五入环比倒推。']
# Age cohort originals and same-period official counts.
ar=read('outputs/2026-10-11/年龄原始读数.json'); assert set(ar['products'])==set(P)
age.update(period={'start':current[0],'end':current[-1]},collectedDate='2026-10-11',compiledAt=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),products=[],coverage={'focusProducts':25,'observedProducts':25,'cohorts':75,'rawPercentValues':375})
ac=[]
for c,p in P.items():
 cohorts={}
 for k,field,label in [('paid','支付用户数','支付用户'),('browse','商详访问人数','浏览用户'),('favorite','收藏用户数','收藏用户')]:
  count=int(num(index[c][field]));vals=ar['products'][c][k];assert (count==0 and sum(vals)==0) or(count>0 and abs(sum(vals)-100)<.031),(c,k,count,vals)
  cohorts[k]=dict(label=label,totalUsers=count,totalSourceField=field,status='no_users' if count==0 else 'observed',sharesPct=vals,ageCounts=None,rawShareSumPct=round(sum(vals),2))
  for ag,v in zip(ar['groups'],vals):ac.append(dict(code=c,spu=p['spuId'],name=p['name'],start=current[0],end=current[-1],cohort=label,totalUsers=count,ageGroup=ag,sharePct=v,status=cohorts[k]['status']))
 age['products'].append(dict(code=c,spuId=p['spuId'],name=p['name'],category=index[c]['类目名称'],start=current[0],end=current[-1],source='核心指标底部年龄分布' if c in unavailable else '成交分析底部年龄分布',cohorts=cohorts))
cmp['gaps']=dict(business_day_baseline='5款新增记录09/27—10/08查询未返回商品，不填0；其余20款两周日值齐。',channel_day_baseline='14款一级来源两周齐；5款新增商品有10/09、10/10原值；6款核心指标页无渠道入口；部分二级历史有缺口。',gravity='本次引力登录失效，当前任务总数及10/10内容日值尚未取得。保留截至10/09历史数据，未完成当日报更新。',listing='16款来自本次后台新上架名单，真实首次上架日期未确认。',causes='实际优惠、库存、活动及独立投放消耗历史未取得，不能把渠道变化直接当作已证明原因。')
cmp['gravity']['target_window']={'start':'2026-09-11','end':'2026-10-10'};cmp['gravity']['refresh_status']='blocked_login';cmp['gravity']['refresh_note']=cmp['gaps']['gravity']
cmp['coverage']=dict(business_products=25,business_dates=all_dates,business_records=290,business_missing_records=60,channel_products=19,channel_days=206,channel_unavailable_products=unavailable,channel_history_pending_products=[],gravity_contents=4,gravity_content_days=38,business_cutoff='2026-10-10',content_cutoff='2026-10-09',collected_date='2026-10-11',age_profile=age['coverage']|age['period'],publication_status='held_for_gravity_login')
coverage=cmp['coverage']|{'gaps':cmp['gaps'],'business_missing':missing,'new_watch_count':sum(p['backendNew'] for p in products),'channel_coverage':ch['coverage']}
for fn,data in [('daily-readings.json',tr),('channel-readings.json',ch),('weekly-comparisons.json',cmp),('age-profiles.json',age),('coverage.json',coverage),('gravity-content-month.json',cmp['gravity'])]:write(D/fn,data);write(O/fn,data)
for fn,rs,fields in [('business-two-weeks.csv',biz,['code','name','date','uv','orders','favorites','favoriteRate','conversionPct','amount','observed','missing_reason','source']),('channel-two-weeks.csv',cr,['code','date','total','competition','recommend','search','new_guarantee','paid','push','gravity','activity','content','users','other']),('weekly-periods.csv',cmp['businessPeriods'],['code','start','end','amount','orders','uv','favorites','conversionPct','paidUsers','source']),('selection-audit.csv',selection,['code','spu','title','sales','uv','favorites','backendNew','included','reason']),('age-profiles.csv',ac,['code','spu','name','start','end','cohort','totalUsers','ageGroup','sharePct','status'])]:csvout(O/fn,rs,fields);shutil.copy2(O/fn,D/fn)
for f in ['gravity-content-month.csv','gravity-content-daily.csv']:
 if (S/f).exists():shutil.copy2(S/f,D/f)
# Candidate report: plainly held, never misrepresents prior Gravity as fresh.
esc=html.escape
report='''<section class="panel daily-brief"><h2>10月10日数据 · 本地待发布稿</h2><p><b>引力登录已失效，近月内容当前清单及10/10日值尚未补齐，暂未更新公开站点。</b></p><div class="brief-grid"><article><h3>月光舞裙：访客略降，成交回升</h3><p>昨日UV216，前日237（−8.86%）；订单6 vs 2；后台转化2.78% vs 0.84%。昨日PV289 vs317，搜索−23、用户运营−13、推荐−5、活动−1，引力+8及内容自运营+6抵消一部分下降。</p><p>本周去重UV1,722 vs3,717（−53.67%），订单26 vs25，后台转化1.45% vs0.65%。引力PV993 vs2,985（−1,992），是周PV下降的主要来源。</p><p>建议：优先恢复引力明细核验，核对曝光和计划状态；当前没有实际消耗证据，不能直接认定预算下降。成交效率回升，继续观察稳定性。</p></article><article><h3>四叶草：引力访问与成交同日回升</h3><p>昨日UV195 vs150（+30%），4单 vs0单，后台转化2.05% vs0%。PV228 vs165，其中引力+53、搜索+4、推荐+1、用户运营+3、其他+2；引力是访问增长主要来源。</p><p>本周UV1,480 vs671（+120.57%），订单7 vs2，后台转化0.47% vs0.30%；引力PV1,522 vs644。前日报“观察新增流量能否成交”的验证出现正向结果，尚不能把全部订单归因给引力。</p><p>建议：对照后续三个完整日订单、收藏与后台转化，逐条内容数据补齐后再判断素材贡献。</p></article><article><h3>两款鸢尾花：收藏增加，访问以内容自运营为主</h3><p>别针鸢尾花YX9640002昨日24 UV、19人收藏（79.17%）；鸢尾星芒YX9640001为34 UV、19人收藏（55.88%），均0订单。前者内容自运营32/33 PV，后者31/41 PV，引力均0。</p><p>两款本周收藏用户26—35岁占46.43%和57.69%。收藏样本28人、26人，仍需谨慎判断。进入收藏增长观察名单；真实上架首日未核验，不套用首日100访客10收藏的例子。</p><p>薄荷蓝绿花朵昨日36 UV、0收藏、0订单；引力PV32 vs13。已有访问增长，尚未验证新增收藏或成交。</p></article></div><details><summary>头部观察10款 · 10/04—10/10</summary><p>按后台我的销量排序；4款有销量，其余6款零销量并列，按区间UV降序、货号升序观察。销量与订单分别保留。</p><div class="table-scroll"><table><thead><tr><th>序号</th><th>商品</th><th>周销量</th><th>周UV</th><th>周收藏人数</th><th>后台周转化</th></tr></thead><tbody>'''
for p in products[:10]:report+=f"<tr><td>{p['rank']}</td><td>{esc(p['name'])}<br>{p['code']}</td><td>{p['weekSales']}</td><td>{p['weekUv']}</td><td>{p['weekFavorites']}</td><td>{num(index[p['code']]['商详转化率'])}%</td></tr>"
report+='''</tbody></table></div></details><p>本期51款中纳入25款、排除26款。后台新上架交集16款，首次上架日期仍待确认。10/10与10/03同为周六，但10/10为国庆调休工作日，10/03为假期；日期属性属于对照条件，不视作已证明原因。价格出价范围与实际支付价分开，优惠、库存及活动历史待验证。</p></section>'''
s=re.sub(r'<section class="panel daily-brief">.*?</section>',lambda m:report,s,count=1,flags=re.S)
s=re.sub(r'<title>.*?</title>','<title>10月10日商品数据 · 待补引力内容</title>',s,count=1)
s=re.sub(r'<p class="intro">.*?</p>','<p class="intro">2026-10-04 至 2026-10-10 · 一级类目：流行饰品/眼镜/服配 · 待发布稿</p>',s,count=1)
s=re.sub(r'<div class="scope">.*?</div>','<div class="scope"><span>关注25款 · 排除26款老款</span><span>经营290条真实日值 · 来源206条真实日值</span><span>年龄25款75个人群</span></div>',s,count=1)
s=re.sub(r'<p class="notice">.*?</p>','<p class="notice">当前为本地待发布稿。经营截至10/10：20款两周日值完整、5款新增记录自10/09有读数；周UV、收藏人数与后台转化读取同区间原值。来源14款两周完整，5款两日，6款无入口。年龄25款375个原值已齐。引力仍为截至10/09历史基线，今日登录阻断，未作为当前完整日报发布。</p>',s,count=1,flags=re.S)
s=re.sub(r'<p class="channel-coverage">.*?</p>','<p class="channel-coverage">19/25款有来源入口：14款14/14日，5款10/09—10/10实采，6款核心指标页无来源入口。PV与UV分开。</p>',s,count=1,flags=re.S)
s=re.sub(r'<footer>.*?</footer>','<footer><p>采集于2026-10-11。<a href="age-profiles.csv" download>25款年龄画像CSV</a> · <a href="business-two-weeks.csv" download>经营逐日底表</a> · <a href="channel-two-weeks.csv" download>来源逐日底表</a> · <a href="weekly-periods.csv" download>后台周区间原值</a> · <a href="selection-audit.csv" download>筛选依据</a> · <a href="coverage.json" download>覆盖与缺口</a></p><p>公开网址仍为上次版本；引力登录恢复并完成核验后再发布本稿。</p></footer>',s,count=1,flags=re.S)
s=s.replace('全部18款重点商品','全部25款重点商品')
s=s.replace('完整7天 · 2026-10-10采集','完整7天 · 2026-10-11采集')
for key,data in [('trend-data',tr),('channel-data',ch),('comparison-data',cmp),('age-data',age)]:s=re.sub(r'(<script id="'+key+r'" type="application/json">).*?(</script>)',lambda m:m[1]+json.dumps(data,ensure_ascii=False)+m[2],s,flags=re.S)
# A visible alert is present in the Gravity section on every product switch.
s=s.replace("    bind(mount,'gravity',()=>renderGravity(code));", "    if(g.refresh_status==='blocked_login')mount.innerHTML='<div class=\"compare-gap\">引力登录失效：以下内容为截至10/09的历史基线，近月清单及10/10日值尚未核验。当前页面为待发布稿。</div>'+mount.innerHTML;\n    bind(mount,'gravity',()=>renderGravity(code));")
s=s.replace('/7天 · 截止10/09</p>', '/7天 · 截止10/10</p>')

(D/'index.html').write_text(s)
write(O/'校验结果.json',{'focus':25,'category_rows':51,'new_watch':sum(p['backendNew'] for p in products),'business_observed':290,'business_missing':60,'backend_week_periods':45,'source_observed_days':206,'source_full14_products':14,'source_new2_products':5,'source_unavailable_products':6,'age_products':25,'age_cohorts':75,'age_percent_values':375,'business_amount_order_sums_checked':True,'primary_pv_sums_checked':True,'weekly_pv_totals_checked':True,'status':'held_for_gravity_login'})
print(json.dumps({'status':'prepared_not_published','focus':25,'new_watch':sum(p['backendNew'] for p in products),'age':len(ac),'business_observed':290,'channels':len(cr)},ensure_ascii=False))
