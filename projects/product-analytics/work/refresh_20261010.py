from pathlib import Path
import json,re,csv,datetime,shutil,html
B=Path(__file__).resolve().parent.parent;D=B/'work/dewu-trend-site/dist';O=B/'outputs/2026-10-10/daily-1130';O.mkdir(exist_ok=True)
backup=O/'更新前网站.html'
if not backup.exists():shutil.copy2(D/'index.html',backup)
s=backup.read_text()
def read(p):return json.loads((B/p).read_text())
def embed(k):return json.loads(re.search('<script id="'+k+'" type="application/json">(.*?)</script>',s,re.S)[1])
def dates(a,b):
 a=datetime.date.fromisoformat(a);b=datetime.date.fromisoformat(b);return [(a+datetime.timedelta(days=i)).isoformat() for i in range((b-a).days+1)]
def num(v):
 m=re.search(r'-?[\d,.]+',str(v));return float(m[0].replace(',','')) if m else None
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def csvout(p,rows,fields):
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def esc(x):return html.escape(str(x))
trend=embed('trend-data');ch=embed('channel-data');cmp=embed('comparison-data')
all_dates=dates('2026-09-26','2026-10-09');now_dates=all_dates[7:];old_dates=all_dates[:7]
new=read('outputs/2026-10-10/daily-1130/经营新增原始读数.json');official=read('outputs/2026-10-10/daily-1130/2026-10-03_10-09_商品官方导出.json');newch=read('outputs/2026-10-10/daily-1130/渠道新增原始读数.json')
assert len(official)==51 and len({r['商品货号'] for r in official})==51
assert all(r['类目名称'].split('-')[0]=='流行饰品/眼镜/服配' for r in official)
index={r['商品货号']:r for r in official};oldprods={p['code']:p for p in trend['products']};watch={p['code'] for p in trend['products'] if p['backendNew']}
base46={r[0] for r in read('work/retry_metrics.json')['rows']};pending=set(index)-base46
assert len(pending)==5
selection=[];products=[]
for r in official:
 c=r['商品货号'];sales=int(num(r['我的销量']));uv=int(num(r['商详访问人数']));fav=int(num(r['收藏用户数']))
 yes=sales>0 or fav>0 or c in watch
 reason='近7天有销量' if sales else '近7天有收藏' if fav else '10/09后台新品标记继续观察' if c in watch else '新增零数据记录，首次上架状态待核' if c in pending else '近7天销量/收藏均0的老款'
 selection.append(dict(code=c,spu=r['SPUID'],name=r['商品标题'],sales=sales,uv=uv,favorites=fav,included=yes,pending_listing=c in pending,reason=reason))
 if yes:
  name=oldprods.get(c,{}).get('name') or ('冰花蓝眼泪' if c=='YX9611001' else r['商品标题'])
  products.append(dict(code=c,name=name,backendNew=c in watch,weekSales=sales,weekUv=uv,weekFavorites=fav,group='有销量款' if sales else '新品观察' if c in watch else '有收藏款',spuId=r['SPUID'],confirmedListingDate=None,newEvidence='沿用2026-10-09后台新品标记；真实首次上架日期待确认' if c in watch else None))
products.sort(key=lambda p:(-p['weekSales'],-p['weekUv'],p['code']))
for i,p in enumerate(products):p['rank']=i+1
P={p['code']:p for p in products};assert len(P)==18
# Actual daily reads: preserve observed zero; no backfilling from period totals.
records={(r['code'],r['date']):r for r in trend['records']+cmp['businessDays']}
for r in read('work/daily_trend.json')['records']:records[r['code'],r['date']]=r
for raw in [new,read('outputs/2026-10-10/daily-1130/YX9611001_补采历史.json')]:
 for date,rows in raw['days'].items():
  for row in rows:records[row[0],date]=dict(zip(raw['fields'],row),date=date,source=raw['source'])
for r in read('outputs/2026-10-10/2026-10-01_商品经营官方导出.json'):
 if r['商品货号']=='YX9611001':records['YX9611001','2026-10-01']=dict(code='YX9611001',date='2026-10-01',uv=num(r['商详访问人数']),orders=num(r['支付订单数']),favorites=num(r['收藏用户数']),conversionPct=num(r['商详转化率']),amount=num(r['支付金额']),source='10/01官方商品导出')
biz=[]
for p in products:
 for d in all_dates:
  r=dict(records[p['code'],d]);r.update(name=p['name'],backendNew=p['backendNew'],observed=True,favoriteRate=r['favorites']/r['uv']*100 if r['uv'] else None);biz.append(r)
trend.update(dates=now_dates,products=products,top=[p['code'] for p in products[:10]],records=[r for r in biz if r['date'] in now_dates],observedCount=126,expectedCount=126)
cmp['report_end']='2026-10-09';cmp['businessDays']=[r for r in biz if r['date'] in old_dates];cmp['businessPeriods']=[]
for row in new['periods'][0]['rows']:
 if row[0] in P:cmp['businessPeriods'].append(dict(zip(new['fields'],row),start=old_dates[0],end=old_dates[-1],source='后台指定7日区间主值，2026-10-10采集'))
for c in P:
 r=index[c];cmp['businessPeriods'].append(dict(code=c,start=now_dates[0],end=now_dates[-1],amount=num(r['支付金额']),orders=num(r['支付订单数']),uv=num(r['商详访问人数']),favorites=num(r['收藏用户数']),conversionPct=num(r['商详转化率']),source='2026-10-03至10-09官方商品明细导出'))
assert len(cmp['businessPeriods'])==36
for row in cmp['businessPeriods']:
 rs=[r for r in biz if r['code']==row['code'] and row['start']<=r['date']<=row['end']]
 for k in ['orders','amount']:assert sum(r[k] for r in rs)==row[k],(row['code'],k,sum(r[k] for r in rs),row[k])
# Channel histories use true primary PV and observed secondary detail only.
primary=['competition','paid','activity','content','users','other']
ch['products']={c:ch['products'].get(c,dict(code=c,days={},source_status='observed')) for c in P}
for c,p in ch['products'].items():
 p.update(P[c]);p.update(eligible=True,topObservation=c in trend['top'],eligibilityReasons=['week_sales_positive'] if P[c]['weekSales'] else ['week_favorites_positive'] if P[c]['weekFavorites'] else ['new_watch'],exclusionReason=None)
 p['days']={d:v for d,v in p['days'].items() if d in all_dates}
for date,values in newch['new_history'].items():
 v=dict(zip(newch['new_history_fields'],values));total=v.pop('total');ch['products']['YX9611001']['days'][date]=dict(total=total,values=v,observed=True,primary_complete=True,primary_sum=total,primary_sum_matches_total=True,source={'kind':'observed_ui_chart_tooltip','collected_date':'2026-10-10'})
for c,values in newch['daily'].items():
 v=dict(zip(newch['fields'],values));total=v.pop('total');assert sum(v[k] for k in primary)==total
 ch['products'][c]['days']['2026-10-09']=dict(total=total,values=v,observed=True,primary_complete=True,primary_sum=total,primary_sum_matches_total=True,source={'kind':'observed_ui_channel_table','collected_date':'2026-10-10'})
 ch['products'][c]['source_status']='observed';ch['products'][c]['source_note']='六个一级渠道09/26—10/09连续14天已实采；搜索/推荐/引力等二级字段以实际取得的日值和周区间为准。'
cmp['channelPeriods']=[]
for key in ['current','prior']:
 for c,values in newch[key].items():
  v=dict(zip(newch['fields'],values));total=v.pop('total')
  if key=='current' and c in newch['current_extra_new_channel']:v['new_guarantee']=newch['current_extra_new_channel'][c]
  start,end=newch[key+'_period'];rs=[ch['products'][c]['days'][d] for d in dates(start,end)]
  assert total==sum(r['total'] for r in rs)
  for k in primary:assert v[k]==sum(r['values'][k] for r in rs),(c,start,k)
  cmp['channelPeriods'].append(dict(code=c,start=start,end=end,total=total,values=v,source='2026-10-10后台指定区间渠道明细主值'))
available=[c for c,p in ch['products'].items() if p['source_status']=='observed'];unavail=[c for c in P if c not in available]
assert len(available)==13 and len(unavail)==5
channel_rows=[]
for c in available:
 assert set(ch['products'][c]['days'])==set(all_dates)
 for d in all_dates:
  r=ch['products'][c]['days'][d];assert sum(r['values'][k] for k in primary)==r['total'];channel_rows.append(dict(code=c,date=d,total=r['total'],**r['values']))
 assert sum(ch['products'][c]['days'][d]['total'] for d in now_dates)==num(index[c]['商详访问次数'])
ch.update(data_date='2026-10-09',dates=all_dates,collected_date='2026-10-10',collected_at=datetime.datetime.now().astimezone().isoformat(),built_at=datetime.datetime.now().astimezone().isoformat())
ch['notes']=['一级渠道09/26—10/09逐日核对合计；周PV可加总完整日值。','5款无渠道入口，沿用2026-10-09逐款界面核验证据；经营日值继续保留。','二级历史部分日期未采得；不把付费推广父级直接当引力，不倒推子级。']
ch['coverage']=dict(category_product_count=51,active_product_count=18,excluded_product_count=28,pending_listing_product_count=5,period_date_count=14,expected_product_day_count=252,observed_product_day_count=182,observed_product_count=13,observed_counts_by_date={d:13 for d in all_dates},products_with_complete_period=available,complete_period_product_count=13,source_status_counts={'observed':13,'not_exposed_in_backend':5},source_not_exposed_codes=unavail,source_not_yet_verified_codes=[],target_codes=list(P),target_product_count=18,head_observation_codes=trend['top'],missing_dates_by_code={c:[] if c in available else all_dates for c in P})
cmp['gaps']=dict(business_day_baseline=None,channel_day_baseline='13款一级渠道连续两周完整，5款后台无来源入口；部分二级历史日值未取得，付费主力3款周区间已实采。',gravity='近月4条内容38条日值已齐；独立投放计划状态、实际消耗、广告点击日明细未取得，不记为0。',listing='9款观察沿用10/09后台新品标记，真实首次上架日期未确认；新增5条零数据商品记录单列待核。')
cmp['coverage']=dict(business_products=18,business_dates=all_dates,business_records=252,channel_products=13,channel_days=182,channel_unavailable_products=unavail,gravity_contents=4,gravity_content_days=38,business_cutoff='2026-10-09',content_cutoff='2026-10-09',collected_date='2026-10-10')
cmp['gravity']['reverified_at']=datetime.datetime.now().astimezone().isoformat();cmp['gravity']['reverification']='数据中心刷新后仍63条任务；四条内容曝光9520/3041/1520/96与同日上午导出一致，保留每条详情数据截至时间。'
cmp['selection']=selection;cmp['pending_listing_codes']=sorted(pending)
# Visible daily findings and head list.
headrows=''.join('<tr><td>'+str(p['rank'])+'</td><td>'+esc(p['name'])+'<br><small>'+p['code']+'</small></td><td>'+str(p['weekSales'])+'</td><td>'+str(p['weekUv'])+'</td><td>'+str(p['weekFavorites'])+'</td><td>'+str(num(index[p['code']]['商详转化率']))+'%</td></tr>' for p in products[:10])
pendingrows=''.join('<tr><td>'+c+'</td><td>'+esc(index[c]['商品标题'])+'</td><td>0 / 0 / 0</td><td>0 / 0 / 0</td></tr>' for c in sorted(pending))
report='''<section class="panel daily-brief"><h2>10月9日 · 先看这三件事</h2><div class="brief-grid"><article><h3>月光舞裙：周流量减半，成交仍稳</h3><p>本周UV 1,822 vs 4,056（−55.08%），订单25 vs 24，后台转化1.26% vs 0.57%。渠道PV减少2,461，其中引力减少2,276；搜索增加15、用户运营增加31，部分抵消下降。</p><p>昨日PV 317 vs 288（+29），搜索+22、用户运营+10、其他+4、活动+1，抵消推广−4和内容−6。UV 237 vs 236；订单2 vs 3，转化0.84% vs 0.85%，不能把订单下降当转化大跌。</p><p><b>建议：</b>先查引力曝光与计划变化；当前已知是引力访问减少，尚无实际消耗证据证明预算下降。继续观察流量恢复后的订单和后台转化。</p></article><article><h3>四叶草：增长的流量，转化没跟上</h3><p>本周UV 1,447 vs 619（+133.76%），订单3 vs 2；转化0.21% vs 0.32%（−0.11个百分点）。引力周PV 1,495 vs 578，增加917。</p><p>昨日UV 150 vs 194（−22.68%），0订单、8人收藏。PV 165 vs 227（−62），付费推广/引力减少39，是最大减少来源。昨日该内容曝光44、阅读4、商详访问1，内容日值与商品全部引力访问分别统计。</p><p><b>建议：</b>优先核对券后价、主销规格库存与引力进店人群；目前出价范围未变，但不能据此排除优惠变化。</p></article><article><h3>薄荷蓝绿花朵：首条近月内容已有访问</h3><p>10/09发布内容535391676，96曝光、27阅读、12次内容商详访问。该商品昨日UV从3到19，PV从4到20，其中引力13 PV；尚无订单或新增收藏。</p><p><b>验证结果：</b>“内容发布后是否带来访问”出现正向信号，尚不能证明成交效果；未来连续3个完整日继续看收藏与成交。</p><p><b>新品观察：</b>鸢尾星芒黄水晶YX9640001昨日2/10人收藏（20%）、别针鸢尾花YX9640002为1/3（33.33%），样本很小。真实首日未确认，暂不按100访客/10收藏的例子判为已验证潜力款。</p></article></div><details><summary>头部观察10款 · 10/03—10/09</summary><p>按后台“我的销量”排序，单位定义尚未取得；4款有销量，6款零销量并列按区间UV降序观察，同UV按货号排序。</p><div class="table-scroll"><table><thead><tr><th>序号</th><th>商品</th><th>后台我的销量</th><th>周UV（去重）</th><th>周收藏人数</th><th>后台周转化</th></tr></thead><tbody>'''+headrows+'''</tbody></table></div></details><details><summary>筛选变化、待核记录和原因证据</summary><p>冰花蓝眼泪YX9611001因本周新增1人收藏纳入；老款YX9352001本周销量、收藏均0退出。9款新品观察沿用10/09后台标记，首次上架日期仍待确认；今日首页全店新上架数量为0，不据此删除原观察名单。</p><p>官方导出较旧底表多出以下5条零数据记录，暂保留在待核名单，未将其认定为老款排除，也未虚构上架时间或历史折线。</p><div class="table-scroll"><table><thead><tr><th>货号</th><th>商品</th><th>10/09 UV/单/收藏</th><th>本周UV/销量/收藏</th></tr></thead><tbody>'''+pendingrows+'''</tbody></table></div><p>本次13款来源页出价范围与前次记录一致。出价不等于实际支付价；券后价、主销规格库存、活动及独立广告计划历史未取得，相关原因待验证。未执行改价、投放或活动报名。</p><p>10/09与10/02同为周五，但10/02在国庆假期，10/09为节后工作日，不能直接归因为商品问题。国庆10/01—10/07、调休10/10上班，依据<a href="https://big5.www.gov.cn/gate/big5/www.gov.cn/zhengce/zhengceku/202511/content_7047091.htm" target="_blank" rel="noopener">国务院2026年节假日安排</a>；工作日差异是对照条件，尚未验证为转化变化的原因。</p></details></section>'''
# Correct actual content day annotation directly from verified values.
clover=next(r for r in cmp['gravity']['daily'] if r['code']=='YX9615001' and r['date']=='2026-10-09')
report=report.replace('曝光44、阅读4、商详访问1',f"曝光{clover['exposure']}、阅读{clover['reads']}、商详访问{clover['detail_visits']}")
# Replace only human-readable old dates, then embed untouched true histories.
s=s.replace('近7天商品趋势 2026-10-08','近7天商品趋势 2026-10-09').replace('2026-10-02 至 2026-10-08 · 一级类目','2026-10-03 至 2026-10-09 · 一级类目').replace('关注18款 · 排除28款无销量无收藏老款','关注18款 · 排除28款老款 · 5款新增记录待核').replace('来源 168 条','来源 182 条').replace('后台新品标记</option>','新品观察（上架日待核）</option>').replace('截止10/08','截止10/09').replace('本页已有09/25—10/08','本页已有09/26—10/09')
s=re.sub(r'<p class="notice">.*?</p>','<p class="notice">截至10/09：18款经营两周252条日值、36条后台周区间值；13款一级来源两周182条日值。5款后台无来源入口。引力近月4条内容、38条日值。采集于10/10；引力累计快照截至各条所示早间更新时间。<br>经营和来源均支持日环比、上周同日、周环比；累计快照与每日曲线分别展示。独立广告计划实际消耗、真实首次上架日期及部分二级渠道历史仍有明确缺口。</p>',s,count=1,flags=re.S)
s=re.sub(r'<p class="channel-coverage">.*?</p>','<p class="channel-coverage">一级来源13/18款 · 13款均14/14天 · 5款后台无来源入口（10/09逐款核验）· 09/26—10/09。二级来源只展示实际取得的日值与区间值。</p>',s,count=1,flags=re.S)
s=s.replace('<div class="toolbar">',report+'<div class="toolbar">',1)
s=s.replace('</style>','.daily-brief{margin:22px 0}.daily-brief h2{font-size:21px}.brief-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px;margin:14px 0}.brief-grid h3{font-size:16px}.brief-grid p{margin:10px 0;line-height:1.8}.daily-brief details{border-top:1px solid #e1e8ed;padding:14px 0}.daily-brief summary{cursor:pointer;color:#24536c;font-weight:600}.daily-brief details p{margin:10px 0}.daily-brief td:nth-child(2){max-width:480px;white-space:normal;text-align:left}@media(max-width:900px){.brief-grid{grid-template-columns:1fr}}\n</style>',1)
s=s.replace('总46条，逐页读数去重。','本期官方商品导出51条，一级类目逐条核对。').replace('后台新品标记的实际首次上架日期待确认。','新品观察依据为10/09已读后台标记，实际首次上架日期待确认。')
s=s.replace('<footer>','<footer><p>当日留档：<a href="selection-audit.csv" download>51款筛选依据</a> · <a href="weekly-periods.csv" download>两周后台区间原值</a> · <a href="coverage.json" download>覆盖与缺口说明</a></p>',1)
for key,data in [('trend-data',trend),('channel-data',ch),('comparison-data',cmp)]:
 s=re.sub('(<script id="'+key+'" type="application/json">).*?(</script>)',lambda m:m[1]+json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+m[2],s,flags=re.S)
(D/'index.html').write_text(s);(O/'10月9日商品日报.html').write_text(s)
for name,data in [('daily-readings.json',dict(dates=all_dates,products=products,records=biz)),('channel-readings.json',ch),('weekly-comparisons.json',cmp),('gravity-content-month.json',cmp['gravity']),('coverage.json',dict(**cmp['coverage'],gaps=cmp['gaps'],pending_listing_codes=sorted(pending)))]:write(D/name,data);shutil.copy2(D/name,O/name)
csvout(D/'business-two-weeks.csv',biz,['code','name','date','uv','orders','favorites','favoriteRate','conversionPct','amount'])
csvout(D/'channel-two-weeks.csv',channel_rows,['code','date','total']+[x['id'] for x in ch['channels']])
csvout(D/'weekly-periods.csv',cmp['businessPeriods'],['code','start','end','uv','orders','favorites','conversionPct','amount','source'])
csvout(D/'selection-audit.csv',selection,['code','spu','name','sales','uv','favorites','included','pending_listing','reason'])
for name in ['business-two-weeks.csv','channel-two-weeks.csv','weekly-periods.csv','selection-audit.csv','gravity-content-month.csv','gravity-content-daily.csv']:shutil.copy2(D/name,O/name)
for name in ['引力任务报告官方导出.xlsx','引力任务报告官方导出.json','引力内容逐日原始读数.json']:shutil.copy2(B/'outputs/2026-10-10'/name,O/name)
write(O/'筛选与覆盖核验.json',dict(coverage=cmp['coverage'],selection=selection,gaps=cmp['gaps'],verified='经营订单/金额两周均逐款与后台区间核对；渠道每个日值六个一级和核对，13款本周PV与官方导出核对，3款前周渠道明细与七天实值核对。'))
print(json.dumps(dict(coverage=cmp['coverage'],top=trend['top'],new_focus='YX9611001',removed='YX9352001',pending=sorted(pending)),ensure_ascii=False,indent=2))
