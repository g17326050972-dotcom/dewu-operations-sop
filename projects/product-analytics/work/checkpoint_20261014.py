# -*- coding: utf-8 -*-
from pathlib import Path
import json,re,csv,datetime
O=Path('/Users/nan/Documents/Codex/2026-10-09/zai/outputs/2026-10-14')
def rd(n):return json.loads((O/n).read_text())
def wr(n,x):(O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def csvout(n,rs):
 with (O/n).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,list(dict.fromkeys(k for r in rs for k in r)));w.writeheader();w.writerows(rs)
b=rd('business-history.json');tr=rd('daily-readings.json');g=rd('gravity-content-month.json');a=rd('年龄原始读数.json');off={r['商品货号']:r for r in rd('2026-10-07_10-13_商品官方导出.json')}
cm={'全部':'total','商品竞争力':'competition','商品推荐':'recommend','商品搜索':'search','新品保量':'new_guarantee','付费推广':'paid','得物推':'push','引力':'gravity','平台活动':'activity','内容自运营':'content','用户运营':'users','其他':'other'}
channels=[]
for f in O.glob('*_渠道.txt'):
 st=f.read_text();part=st[st.index('文本 渠道明细'):];v={}
 for row in re.split(r'\n\s*\d+ row\n',part)[1:]:
  cs=re.split(r'(?:^|\n)\s*\d+ 单元格[^\n]*\n',row)[1:]
  if len(cs)<2:continue
  label=re.search(r'\d+ 文本 (.+)',cs[0]);val=re.search(r'\d+ 文本 ([\d,]+)',cs[1])
  if label and label[1] in cm and val:v[cm[label[1]]]=int(val[1].replace(',',''))
 assert sum(v[k] for k in ['competition','paid','activity','content','users','other'])==v['total']
 dt=re.search(r'(2026-\d\d-\d\d) 至 (2026-\d\d-\d\d)',st)
 channels.append(dict(code=f.name.split('_')[0],start=dt[1],end=dt[2],unit='PV 次',**v,source_file=f.name))
wr('channel-partial.json',channels);csvout('channel-partial.csv',channels)
ar=[]
for c,cohorts in a['products'].items():
 for cohort,vals in cohorts.items():
  field={'paid':'支付用户数','browse':'商详访问人数','favorite':'收藏用户数'}[cohort];count=int(off[c][field]);assert (count==0 and sum(vals)==0) or abs(sum(vals)-100)<.031
  for group,value in zip(a['groups'],vals):ar.append(dict(code=c,spu=off[c]['SPUID'],start=a['period']['start'],end=a['period']['end'],cohort=cohort,totalUsers=count,ageGroup=group,sharePct=value))
csvout('age-profiles-partial.csv',ar)
cutoff='2026-10-13';focus=[p['code'] for p in tr['products']]
cov={'report_end':cutoff,'collected_date':'2026-10-14','publication_status':'held_browser_window_unavailable','publication_blocker':'Edge窗口读取中断，重新绑定返回cgWindowNotFound；渠道、年龄和新增款历史尚未采齐，原公开网址未更新。','category_products':len(off),'focus_products':len(focus),'new_watch':sum(p['backendNew'] for p in tr['products']),'head':tr['top'],'business_yesterday_observed':28,'business_two_week_observed':sum(r['observed'] for r in b['records']),'business_two_week_missing':len(b['missing']),'business_current_week_observed':tr['observedCount'],'business_weekly_periods':len(b['periods']),'gravity_official_tasks':64,'gravity_recent_contents':5,'gravity_daily_rows':57,'channel_current_collection_rows':len(channels),'age_current_products':len(a['products']),'age_current_cohorts':len(a['products'])*3,'age_current_pct_values':len(ar),'pending_channel_codes':[c for c in focus if c!='YX9354001'],'moon_prior_channel_pending':True,'pending_age_codes':[c for c in focus if c not in a['products']],'newly_included_history_pending':['YX9639002','YX9639001','YX9531001','YX9521001'],'business_missing_records':b['missing'],'other_gaps':['真实首次上架日期未确认，后台新品名单不是首日证据。','独立广告实际消耗、预算及计划状态未取得；任务金额不充当实际消耗。','历史价格、优惠、库存、活动变化尚待核验；渠道贡献变化不直接证明原因。'],'site_url':'https://dewu-product-daily-trends.lucky-fawn-8231.chatgpt.site/','site_live_cutoff_at_last_successful_verification':'2026-10-12'}
wr('coverage.json',cov)
state={'status':'blocked_browser_window','timestamp':datetime.datetime.now().astimezone().isoformat(),'coverage_file':'coverage.json','completed':['55款官方近7天导出及筛选依据','28款昨日经营，295条两周真实日值，47条后台周区间','64条引力官方报告，近30天5条内容57条日值已合并校验','月光舞裙当前周与昨日渠道，当前周三类年龄画像'],'remaining':['恢复Edge窗口','其余27款渠道入口复核/昨日与两周原值、月光舞裙前周原值','其余27款当前周年龄截图原值','4款新纳入商品历史分天核验','经营/渠道原因及上一日报建议验证','完整站点构建、验证、通过Sites原站公开发布与回读'],'scripts':['work/consolidate_20261014.py','work/finish_gravity_20261014.py','work/checkpoint_20261014.py'],'browser_state':'历史运行环境记录已省略','ui_helpers':'历史运行环境记录已省略','calendar':'历史运行环境记录已省略','current_period':'2026-10-07—2026-10-13','prior_period':'2026-09-30—2026-10-06','gravity_window':'2026-09-14—2026-10-13','site_project_id':'[原站点标识已移除]','site_checkout':'work/dewu-trend-site','site_not_changed_this_run':True}
wr('交接状态.json',state)
text='''# 10月13日数据整理进度（未发布）

本次类目精确限定“流行饰品/眼镜/服配”。55款中纳入28款，排除27款近7天无销量无收藏的老款；20款有后台新上架标记，真实首次上架日尚未确认。

已完成：28款10月13日完整日经营数据；当前周10/07—10/13及前周09/30—10/06共47条后台区间读数；两周295条真实日记录，97条缺口留空。近月引力完整任务报告64条，符合发布时间范围09/14—10/13的5条内容已逐条核验并合并57条真实日记录。

初步发现：
- 月光舞裙 YX9354001：昨日UV229，前日257，下降10.9%；2单，后台转化率0.87%，前日1.17%。近7天20单，前7天26单。昨日渠道总PV299，付费推广117（全部来自引力）、商品竞争力86；完整渠道变化解释待补齐。
- 四叶草 YX9615001：昨日UV284，前日223，增长27.4%；1单，后台转化率0.35%，前日0.90%。需要继续核对渠道结构、优惠和库存。
- 鸢尾 YX9640001：昨日48名访客、1单、1名收藏用户，后台转化率2.08%；单日样本小，继续观察。
- 新纳入 YX9639002：近7天516名访客、28名收藏用户、无成交；收藏率5.43%。尚未确认真实首日，不能套用首日10%例子判定。
- 5条引力内容昨日曝光合计831次、阅读66次、商详访问9次；无新增引导收藏和14日归因订单。该指标不等于商家后台支付订单。

年龄画像目前仅月光舞裙本期已完成：支付用户19人，其中18—25岁73.68%；浏览用户1705人，18—25岁65.16%；收藏用户154人，18—25岁68.18%。占比来自区间图，不反推各年龄人数，不视为年龄转化率。

## 中断与待补

Edge窗口连接丢失；重新绑定连续返回cgWindowNotFound。其余27款渠道与年龄画像、月光舞裙前周来源和4款新纳入商品历史仍待补齐。因此本次没有发布，原网址仍保留此前版本。

引力两条花朵内容的图表累计商详访问分别28/79，概览分别27/68；小裙子内容532609487历史日互动合计2与最新累计1不一致，均保留原值。独立广告消耗等缺口仍需验证，合作状态沿用10/12证据并注明时间。

## 本地底表

- business-two-weeks.csv：两周经营日值，observed=false为缺失
- weekly-periods.csv：实际后台周区间，周UV和收藏人数未由日值相加
- selection-audit.csv：55款筛选依据
- gravity-content-daily.csv / gravity-content-month.csv：逐条内容分天值与累计快照
- channel-partial.csv / age-profiles-partial.csv：仅本次已采部分
- coverage.json / 交接状态.json：精确覆盖与续采位置
'''
(O/'整理进度.md').write_text(text)
print(json.dumps({k:v for k,v in cov.items() if k not in ['business_missing_records','pending_channel_codes','pending_age_codes']},ensure_ascii=False))
