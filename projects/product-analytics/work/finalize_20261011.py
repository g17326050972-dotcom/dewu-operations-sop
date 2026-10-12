from pathlib import Path
import json,csv,re,datetime,shutil
B=Path('/Users/nan/Documents/Codex/2026-10-09/zai');O=B/'outputs/2026-10-11';D=O/'draft-site'
def rd(p):return json.loads(p.read_text())
def wr(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def number(v):
 m=re.search(r'-?[\d,.]+',str(v));return float(m[0].replace(',','')) if m else None
def csvout(p,rs):
 fields=list(dict.fromkeys(k for r in rs for k in r))
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rs)
base=rd(B/'work/dewu-trend-site/dist/gravity-content-month.json');new=rd(O/'引力内容新增读数.json');export=rd(O/'引力任务报告官方导出.json');spus={str(r['SPUID']):r['商品货号'] for r in rd(O/'2026-10-04_10-10_商品官方导出.json')}
assert len(export)==63
recent=[r for r in export if '2026-09-11'<=r['动态发布时间'][:10]<='2026-10-10'];assert len(recent)==4
assert {r['子任务ID'] for r in recent}=={r['task_id'] for r in new['daily']}
index={r['子任务ID']:r for r in recent}
mp={'exposure':'曝光pv','reads':'阅读pv','interactions':'互动pv','detail_visits':'商详访问pv','favorites':'引导商品收藏数','attributed_orders_14d':'14日归因订单量','attributed_gmv_14d':'14日归因GMV','help_orders':'帮助成交订单','help_gmv':'帮助成交金额','curated_exposure':'穿搭精选曝光量','curated_reads':'穿搭精选阅读量','curated_help_orders':'穿搭精选辅助下单数','cooperation_fee':'子任务金额','backend_visit_cost':'商详访问成本','ctr_pct':'动态点击率','detail_lead_rate_pct':'内容引导商详率'}
for p in base['snapshots']:
 r=index[p['task_id']];assert spus[r['货号（spu_id）']]==p['code'] and r['货号（spu_id）']==p['spu_id']
 p.update({k:number(r[f]) for k,f in mp.items()});p.update(new['contents'][p['content_id']]);p['export_published_at']=r['动态发布时间']
 detail=(O/(p['content_id']+'_引力详情.txt')).read_text();p['title']=re.search(r'图片 (.*?) 发布时间',detail)[1]
 d=next(x for x in new['daily'] if x['content_id']==p['content_id']);d.update(code=p['code'],creator=p['creator'],source='2026-10-11引力任务详情发布后30天/7天分天图浮层原值，日期2026-10-10')
 base['daily'].append(d)
 ds=[x for x in base['daily'] if x['task_id']==p['task_id']];assert ds[0]['date']==p['published_at'][:10] and ds[-1]['date']=='2026-10-10'
 assert len(ds)==(datetime.date(2026,10,10)-datetime.date.fromisoformat(p['published_at'][:10])).days+1
 p['daily_reconciliation']={k:{'daily_sum':sum(x[k] for x in ds),'cumulative':p[k],'matches':sum(x[k] for x in ds)==p[k]} for k in base['fields']}
 p['plan_status']=None;p['plan_status_note']='已取得达人任务内容数据；独立广告计划状态、预算与实际广告消耗无对应字段，不以任务金额代替。'
 p['daily_missing_fields']=['14日归因GMV','帮助成交订单','帮助成交金额','独立广告实际消耗','广告点击']
base.update(window={'start':'2026-09-11','end':'2026-10-10'},reverified_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),refresh_status='complete',refresh_note='本次完整导出63条任务，以官方发布时间筛选4条近月内容，再逐条核验详情真实发布时间、数据截止时间与昨日分天值。',reverification={'official_export_rows':63,'published_in_window':4,'matched_focus_products':3,'daily_rows':42,'yesterday_rows':4,'historical_rows':38,'historical_source':'截至10/09原始分天读数；本次新增10/10浮层实采并核对最新累计概览'},scope_note='截至昨日最近30个自然日内发布的4条内容；详情发布时间与导出时间同时保留，展示采用详情时间。六项日曲线有42条日记录。累计与日合计不一致保留差异；周对比只使用完整日期。')
assert len(base['daily'])==42
base['source']='2026-10-11官方任务报告完整导出63条＋四条内容详情与10/10分天浮层；历史38条沿用实采证据。'
wr(O/'引力近一个月逐条内容整理.json',base)
for root in [O,D]:
 wr(root/'gravity-content-month.json',base)
 csvout(root/'gravity-content-month.csv',[{k:v for k,v in r.items() if not isinstance(v,(dict,list))} for r in base['snapshots']])
 csvout(root/'gravity-content-daily.csv',base['daily'])
cmp=rd(D/'weekly-comparisons.json');cmp['gravity']=base;cmp['gaps']['gravity']='近月4条内容及截至10/10六项分天值已取得；独立广告计划、实际广告消耗及广告点击未取得，分天图无GMV和帮助成交指标，累计值单列。'
cmp['coverage'].update(gravity_content_days=42,content_cutoff='2026-10-10',publication_status='ready_pending_sites_connection')
cov=rd(D/'coverage.json');cov.update(cmp['coverage']);cov['gaps']=cmp['gaps'];cov['publication_blocker']='Sites get_site 三次返回 HTTP transport send failure；待发布服务恢复。'
for root in [O,D]:wr(root/'weekly-comparisons.json',cmp);wr(root/'coverage.json',cov)
s=(D/'index.html').read_text()
s=s.replace('10月10日商品数据 · 待补引力内容','10月10日商品日报').replace('10月10日数据 · 本地待发布稿','10月10日 · 流量、成交与内容表现').replace(' · 待发布稿','')
s=s.replace('<p><b>引力登录已失效，近月内容当前清单及10/10日值尚未补齐，暂未更新公开站点。</b></p>','')
s=s.replace('建议：优先恢复引力明细核验，核对曝光和计划状态；当前没有实际消耗证据，不能直接认定预算下降。成交效率回升，继续观察稳定性。','建议：两条近月内容昨日曝光331与101，合计432，对前日437略降；不能据此解释全部历史内容带来的引力周降量。继续核对独立投放计划及实际消耗，并观察成交效率稳定性。')
s=s.replace('建议：对照后续三个完整日订单、收藏与后台转化，逐条内容数据补齐后再判断素材贡献。','建议：该条近月内容昨日75曝光、2阅读、0次商详访问；商品全部引力渠道PV增加53，不能归因给这一条内容。继续观察后续三个完整日，并核验其他内容和投放来源。')
s=s.replace('薄荷蓝绿花朵昨日36 UV、0收藏、0订单；引力PV32 vs13。已有访问增长，尚未验证新增收藏或成交。','薄荷蓝绿花朵内容535391676昨日443曝光、59阅读、27次内容商详访问、1次互动，收藏和14日归因订单为0；商品引力PV32 vs13。内容与商品访问均增长，尚未验证新增收藏或成交。')
s=re.sub(r'<p class="notice">.*?</p>','<p class="notice">数据截至10/10：20款经营两周日值完整、5款新增记录自10/09有读数；周人数与后台转化采用同区间原值。来源14款两周完整、5款两日、6款无入口。25款年龄画像375个原始占比，近月4条引力内容42条分天值已核验。实际首次上架日期及独立广告消耗仍缺。</p>',s,count=1,flags=re.S)
s=s.replace('4条内容 / 38条日值','4条内容 / 42条日值')
s=s.replace("'；真实上架日期待确认。'", "'；真实上架日期待确认。'")
# Put verified cooperation fields next to each content's cumulative metrics.
s=s.replace("官方报告子任务金额 ¥'+fmt(s.cooperation_fee)", "合作状态：'+escape(s.cooperation_status||'未取得')+'；详情页合作金额 ¥'+fmt(s.cooperation_amount)+'，官方报告子任务金额 ¥'+fmt(s.cooperation_fee)")
s=s.replace('这两个字段不作为广告实际消耗。','以上金额分别沿用后台字段，费用构成未核实；不作为广告实际消耗。')

s=s.replace(' · <a href="coverage.json" download>覆盖与缺口</a>', ' · <a href="gravity-content-month.csv" download>引力逐条累计底表</a> · <a href="gravity-content-daily.csv" download>引力逐日底表</a> · <a href="coverage.json" download>覆盖与缺口</a>')

s=s.replace('本页已有09/26—10/09完整经营日值及对应两周后台区间值。','本页采用09/27—10/10实际日值；5款新增商品更早查询未返回记录，缺失保留为空。')
s=s.replace('<h2>近一个月 · 逐条内容数据</h2>','<h2>近一个月 · 逐条内容数据</h2>')
s=s.replace('<p>公开网址仍为上次版本；引力登录恢复并完成核验后再发布本稿。</p>','<p>内容为累计快照与独立日值分别展示，累计截止时间见每条内容。原始导出与采集证据按日期本地留档。</p>')
for key,data in [('comparison-data',cmp)]:s=re.sub(r'(<script id="'+key+r'" type="application/json">).*?(</script>)',lambda m:m[1]+json.dumps(data,ensure_ascii=False)+m[2],s,flags=re.S)
(D/'index.html').write_text(s)
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
channel=rd(D/'channel-readings.json');channel.update(built_at=now,collected_at=now)
for root in [O,D]:wr(root/'channel-readings.json',channel)
s=(D/'index.html').read_text();s=re.sub(r'(<script id="channel-data" type="application/json">).*?(</script>)',lambda m:m[1]+json.dumps(channel,ensure_ascii=False)+m[2],s,flags=re.S);(D/'index.html').write_text(s)
q=rd(O/'校验结果.json');q.update(gravity_official_task_rows=63,gravity_contents=4,gravity_daily_rows=42,status='ready_pending_sites_connection');wr(O/'校验结果.json',q)
print(json.dumps({'near_month_contents':4,'daily_rows':42,'snapshot_totals':{k:sum(p[k] for p in base['snapshots']) for k in base['fields']},'daily_differences':{p['content_id']:{k:v for k,v in p['daily_reconciliation'].items() if not v['matches']} for p in base['snapshots']}},ensure_ascii=False))
