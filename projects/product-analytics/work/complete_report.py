from pathlib import Path
import json,re,csv,datetime,shutil

BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'outputs/2026-10-10'
DIST=BASE/'work/dewu-trend-site/dist'
source=(BASE/'work/site-v3-before-completion.html').read_text()
def read(p):return json.loads((BASE/p).read_text())
def inline(d):return json.dumps(d,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
def embedded(key):return json.loads(re.search(r'<script id="'+key+r'" type="application/json">(.*?)</script>',source,re.S)[1])
def replace_data(s,key,d):return re.sub(r'(<script id="'+key+r'" type="application/json">).*?(</script>)',lambda m:m[1]+inline(d)+m[2],s,flags=re.S)
def write_json(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def date_range(start,end):
    a=datetime.date.fromisoformat(start);b=datetime.date.fromisoformat(end)
    return [(a+datetime.timedelta(days=i)).isoformat() for i in range((b-a).days+1)]
def number(s):
    m=re.search(r'-?[\d,.]+',str(s));return float(m[0].replace(',','')) if m else None
def write_csv(p,rows,fields):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

trend=embedded('trend-data');channels=embedded('channel-data');data=embedded('comparison-data')
products={p['code']:p for p in trend['products']}
history=read('work/historical-focus-capture.json')
business_days=[]
for date,rows in history['days'].items():
    assert len(rows)==18 and len({r[0] for r in rows})==18
    for code,amount,conversion,orders,uv,favorites in rows:
        assert code in products
        business_days.append(dict(code=code,date=date,name=products[code]['name'],amount=amount,conversionPct=conversion,orders=orders,uv=uv,favorites=favorites,favoriteRate=favorites/uv*100 if uv else None,observed=True,source='后台指定单日主值'))
assert len(business_days)==126
data['businessDays']=business_days
all_business=sorted(trend['records']+business_days,key=lambda r:(r['date'],r['code']))
assert len({(r['date'],r['code']) for r in all_business})==252

observed=read('work/channel14-observed.json');dates=date_range(observed['start'],observed['end'])
for code,rows in observed['products'].items():
    assert len(rows)==14
    for date,values in zip(dates,rows):
        assert values[0]==sum(values[1:])
        p=channels['products'][code]
        old=p['days'].get(date,{})
        if old: assert old['total']==values[0],(code,date,old['total'],values[0])
        merged={**old.get('values',{}),**dict(zip(observed['fields'][1:],values[1:]))}
        p['days'][date]={**old,'total':values[0],'values':merged,'observed':True,'primary_complete':True,'primary_sum':sum(values[1:]),'primary_sum_matches_total':True,'source':{'kind':'observed_ui_chart_tooltip','description':observed['source'],'collected_date':'2026-10-10'}}
    p['source_note']='一级渠道连续14天已实采并逐日核对总量；二级渠道以已核实日期及周区间为准。'
extra=read('work/channel-period-extra.json')
data['channelPeriods']=[]
for row in extra['rows']:
    v=dict(zip(extra['fields'],row['values']));total=v.pop('total')
    assert total==sum(v[k] for k in ['competition','paid','activity','content','users','other'])
    if row['start']==row['end']:
        d=channels['products'][row['code']]['days'][row['start']]
        assert d['total']==total
        d['values'].update(v)
    else:data['channelPeriods'].append({**{k:row[k] for k in ['code','start','end']},'total':total,'values':v,'source':extra['source']})
channels['dates']=dates
coverage=channels['coverage'];available=list(observed['products'])
coverage.update(period_date_count=14,expected_product_day_count=18*14,observed_product_day_count=168,observed_product_count=12,observed_counts_by_date={d:12 for d in dates},products_with_complete_period=available,complete_period_product_count=12,missing_dates_by_code={c:[] if c in available else dates for c in products})
channels['collected_date']='2026-10-10'
channels['notes'].append('2026-10-10补齐12款09/25至10/08六个一级来源日值；部分历史二级渠道日值未提供，不用一级量倒推。')

official=read('outputs/2026-10-10/引力任务报告官方导出.json')
merchant=read('outputs/2026-10-10/2026-10-01_商品经营官方导出.json')
spu_map={str(r['SPUID']):r['商品货号'] for r in merchant if r['类目名称'].startswith('流行饰品/眼镜/服配-')}
observed_gravity=read('work/gravity-daily-observed.json')
window={'start':'2026-09-10','end':'2026-10-09','definition':'截至10/09最近30个完整自然日发布的内容；使用任务详情实际发布时间筛选','export_task_count':len(official)}
selected=[r for r in official if window['start']<=r['动态发布时间'][:10]<=window['end']]
assert len(official)==63 and len(selected)==4
snapshots=[];daily=[]
mapping={'exposure':'曝光pv','reads':'阅读pv','interactions':'互动pv','detail_visits':'商详访问pv','favorites':'引导商品收藏数','attributed_orders_14d':'14日归因订单量','attributed_gmv_14d':'14日归因GMV','help_orders':'帮助成交订单','help_gmv':'帮助成交金额','curated_exposure':'穿搭精选曝光量','curated_reads':'穿搭精选阅读量','curated_help_orders':'穿搭精选辅助下单数','cooperation_fee':'子任务金额','backend_visit_cost':'商详访问成本','ctr_pct':'动态点击率','detail_lead_rate_pct':'内容引导商详率'}
for row in selected:
    task=row['子任务ID'];detail=observed_gravity['tasks'][task]
    code=spu_map[row['货号（spu_id）']]
    assert code in products and window['start']<=detail['published_at'][:10]<=window['end']
    s={k:number(row[field]) for k,field in mapping.items()}
    s.update(code=code,product_name=products[code]['name'],task_id=task,content_id=detail['content_id'],title=detail['title'],creator=row['达人昵称'],published_at=detail['published_at'],export_published_at=row['动态发布时间'],data_as_of=detail['data_as_of'],spu_id=row['货号（spu_id）'],association_evidence='引力官方任务报告SPU ID与商家官方SPU导出货号一一匹配，任务详情核验内容ID及发布时间',metric_scope='内容发布后累计快照，截止时间以每条内容为准',actual_ad_spend=None)
    assert [d[0] for d in detail['days']]==date_range(detail['published_at'][:10],window['end'])
    sums={k:sum(d[i+1] for d in detail['days']) for i,k in enumerate(observed_gravity['fields'])}
    s['daily_reconciliation']={k:{'daily_sum':v,'cumulative':s[k],'matches':v==s[k]} for k,v in sums.items()}
    s['notes']=[]
    if any(not x['matches'] for x in s['daily_reconciliation'].values()):s['notes'].append('后台互动日值合计2次，累计概览与官方导出为1次，差异原因待验证；分别保留，不强行改平。')
    if s['published_at']!=s['export_published_at']:s['notes'].append('官方导出发布时间与任务详情不一致，展示及日趋势采用任务详情时间；导出原值留档。')
    snapshots.append(s)
    for date,*values in detail['days']:
        daily.append(dict(task_id=task,content_id=s['content_id'],code=code,creator=s['creator'],date=date,**dict(zip(observed_gravity['fields'],values))))
assert len(daily)==38 and len({(r['task_id'],r['date']) for r in daily})==38
snapshots.sort(key=lambda s:s['published_at'],reverse=True)
gravity={'window':window,'snapshots':snapshots,'daily':daily,'fields':observed_gravity['fields'],'actual_ad_spend_status':'未取得独立广告计划实际消耗；达人任务金额及后台商详访问成本不替代实际广告消耗。','source':'引力官方63条任务报告导出与四条任务详情分天值提示核验','scope_note':'仅最近30天发布的4条内容；未将更早发布内容的最近30天表现混入。'}
data['gravity']=gravity
data['gaps']={'business_day_baseline':None,'channel_day_baseline':'12款六个一级来源两周齐备；6款后台不提供来源入口；历史二级日值部分缺失，3款付费主力周区间已补。','gravity':'内容4条、38个内容日值已齐；独立广告计划实际消耗/点击明细未取得，未记为0。'}
data['coverage']={'business_products':18,'business_dates':dates,'business_records':252,'channel_products':12,'channel_days':168,'channel_unavailable_products':coverage['source_not_exposed_codes'],'gravity_contents':4,'gravity_content_days':38,'business_cutoff':'2026-10-08','content_cutoff':'2026-10-09','collected_date':'2026-10-10'}

source=replace_data(source,'comparison-data',data)
source=replace_data(source,'channel-data',channels)
module=(BASE/'work/comparison-component/comparison.js').read_text()
source=re.sub(r'(<script id="comparison-data" type="application/json">.*?</script>)<script>.*?</script>',lambda m:m[1]+'<script>'+module+'</script>',source,count=1,flags=re.S)
source=source.replace('</style>',(BASE/'work/comparison-component/completion.css').read_text()+'</style>',1)
source=re.sub(r'<p class="notice">.*?</p>','<p class="notice">经营：18款两周252条日值、两周后台区间值已齐；来源：12款六个一级渠道两周168条日值已齐，6款后台未提供入口。近月引力：09/10—10/09发布的4条内容，38条日值已齐。经营/渠道截止10/08，内容截止10/09，采集于10/10。<br>经营和来源均支持日环比、上周同日、周环比；点击「引力与内容」查看每条内容的曝光、阅读、互动和商详访问折线。新品真实首次上架日期待确认。</p>',source,count=1,flags=re.S)
source=re.sub(r'<p class="channel-coverage">.*?</p>','<p class="channel-coverage">一级来源 12/18款 · 12款均14/14天 · 6款后台不提供来源入口 · 09/25—10/08。搜索/推荐/引力等二级来源仅按已取得的日值与区间值展示。</p>',source,count=1,flags=re.S)
source=source.replace('非平台下载导出文件。','日值含逐页读数、单品趋势提示及10/01官方商品导出核验；引力累计值使用官方导出，逐日值来自任务详情。')
source=source.replace('已采集 126/126 条逐日记录','经营两周 252/252 条 · 来源 168 条')
source=source.replace('<footer>','<footer><p>新增底表：<a href="business-two-weeks.csv" download>经营两周CSV</a> · <a href="channel-two-weeks.csv" download>渠道两周CSV</a> · <a href="gravity-content-month.csv" download>引力逐条内容CSV</a> · <a href="gravity-content-daily.csv" download>引力逐日CSV</a> · <a href="gravity-content-month.json" download>引力完整底表JSON</a></p>',1)
write_json(OUT/'周对比与引力整理数据.json',data)
write_json(OUT/'引力近一个月逐条内容整理.json',gravity)
write_json(OUT/'渠道两周整理数据.json',channels)
write_json(OUT/'经营两周整理数据.json',all_business)
shutil.copy2(BASE/'work/channel14-observed.json',OUT/'渠道两周逐日原始读数.json')
shutil.copy2(BASE/'work/channel-period-extra.json',OUT/'主力款二级来源原始读数.json')
shutil.copy2(BASE/'work/gravity-daily-observed.json',OUT/'引力内容逐日原始读数.json')
for name,d in [('weekly-comparisons.json',data),('channel-readings.json',channels),('daily-readings.json',{'dates':dates,'products':trend['products'],'records':all_business}),('gravity-content-month.json',gravity)]:write_json(DIST/name,d)
write_csv(DIST/'business-two-weeks.csv',all_business,['code','name','date','uv','orders','favorites','favoriteRate','conversionPct','amount'])
channel_rows=[]
for code in available:
    for date in dates:
        r=channels['products'][code]['days'][date]
        channel_rows.append(dict(code=code,date=date,total=r['total'],**r['values']))
write_csv(DIST/'channel-two-weeks.csv',channel_rows,['code','date','total']+[r['id'] for r in channels['channels']])
write_csv(DIST/'gravity-content-month.csv',snapshots,['code','product_name','content_id','task_id','title','creator','published_at','data_as_of']+list(mapping))
write_csv(DIST/'gravity-content-daily.csv',daily,['code','content_id','task_id','creator','date']+observed_gravity['fields'])
for name in ['business-two-weeks.csv','channel-two-weeks.csv','gravity-content-month.csv','gravity-content-daily.csv']:shutil.copy2(DIST/name,OUT/name)
(DIST/'index.html').write_text(source)
(OUT/'商品经营来源与引力内容完整核验.html').write_text(source)
print(data['coverage'])
