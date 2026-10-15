# -*- coding: utf-8 -*-
from pathlib import Path
import json,re,html
B=Path('/Users/nan/Documents/Codex/2026-10-09/zai');O=B/'outputs/2026-10-14';D=O/'draft-site';S=B/'outputs/2026-10-13/draft-site'
def rd(n):return json.loads((D/n).read_text())
tr=rd('daily-readings.json');ch=rd('channel-readings.json');cmp=rd('weekly-comparisons.json');age=rd('age-profiles.json');g=rd('gravity-content-month.json');cov=rd('coverage.json');esc=html.escape
s=(S/'index.html').read_text()
report='''<section class="panel daily-brief"><h2>10月13日 · 月光舞裙降量，四叶草增流量但转化回落</h2><div class="brief-grid">
<article><h3>月光舞裙：日流量下降，周减少主要在引力</h3><p>昨日229 UV，前日257（−10.89%）；订单3→2，后台转化1.17%→0.87%（−0.30个百分点）。收藏23→21人，收藏率8.95%→9.17%。对上周二10/06，UV251→229，订单仍为2，转化0.80%→0.87%。</p><p>日PV321→299，净减少22。搜索−13、引力−9、用户运营−5、其他−3、活动−2，共减少32；内容自运营+8、推荐+2抵消10。</p><p>近7天去重UV1,705，前7天2,862（−40.43%）；订单26→20，周转化0.87%→1.11%。周PV3,655→2,241，净减1,414；引力2,114→919，减少1,195，是主要减少来源。PV贡献不能直接分摊UV降幅。</p><p><b>验证与建议：</b>昨天恢复3单后，本日仍有2单，连续两天有成交；周流量尚未恢复。优先查引力完整投放曝光和内容供给。近月两条内容昨日商详访问1次，不能解释全部117次引力渠道访问；价格优惠与投放消耗的历史证据尚不足，原因待核。</p></article>
<article><h3>四叶草：引力流量增加，订单与收藏率回落</h3><p>昨日284 UV，前日223（+27.35%）；订单2→1，后台转化0.90%→0.35%（−0.55个百分点）。收藏15→16人，但收藏率6.73%→5.63%。对上周二10/06，UV265→284，订单均1单，后台转化0.38%→0.35%。</p><p>日PV288→324，净增36。引力+49、推荐+2、内容自运营+2，共增53；搜索−6、其他−5、用户运营−4、活动−2抵消17。昨日引力302 PV，占93.21%。</p><p>周UV1,110→1,535（+38.29%），订单1→9，周转化0.09%→0.59%；引力周PV1,110→1,618（+45.77%）。</p><p><b>验证与建议：</b>日流量增加没有带来订单同步增长，继续核对新增流量质量、到手价、优惠和库存。单日只有1单，先观察连续3个完整日，不因一天转化下降直接加预算或改价。</p></article>
<article><h3>新品与收藏观察：鸢尾出单，路路通内容流量增长</h3><p>鸢尾星芒YX9640001：昨日48 UV、1单，后台转化2.08%；收藏9→1人，收藏率24.32%→2.08%。前日报的“观察收藏能否带来成交”已有1单结果，仍需继续验证。别针鸢尾YX9640002周57 UV、28人收藏、0单；昨日8 UV、0收藏，高收藏率尚未变成成交。</p><p>薄荷蓝绿花朵YX9638001：昨日60 UV，比前日54增加，但收藏6→0、仍0单；前日收藏改善未持续。先检查内容承接和到手价，再判断培养投入。</p><p>路路通YX9639002：昨日516 UV、28人收藏、0单，收藏率5.43%；同系列YX9639001为56 UV、4收藏、0单，收藏率7.14%。两款主要来源是内容自运营，真实首次上架日期尚未确认，不能当作首日潜力阈值案例。</p><p><b>口径核对：</b>YX9639002近7天渠道706 PV、经营导出589 PV；YX9639001为223与67 PV。来源图保留经营列表首次返回前的访问读数，经营图保留其自身口径；差异成因未证实，不改平。</p></article>
<article><h3>年龄画像：28款、84个人群已更新</h3><p>区间10/07—10/13，420个后台原始占比。月光舞裙支付19人，18—25岁73.68%；浏览1,705人，该年龄组65.16%；收藏154人，该年龄组68.18%。四叶草支付9人，18—25岁66.67%。支付人数与订单数不同。</p><p>鸢尾星芒仅1位支付用户，后台显示36—45岁100%，不据此推断稳定目标人群。其收藏36人，26—35岁52.78%；别针鸢尾收藏28人，该年龄组57.14%。</p><p>没有用户的人群显示“本期无用户”；“其他”保持后台名称。年龄是整周快照，不做每日曲线，也不将不同人群年龄占比之差视为年龄转化率。</p></article>
<article><h3>引力：近30天5条内容、57条分天记录</h3><p>官方任务报告64条已核对，统计09/14—10/13发布的5条内容。昨日合计曝光831、阅读66、商详访问9；引导收藏与14日归因订单均0。每条内容的曝光、阅读、互动、商详、收藏、归因订单曲线和日明细见引力入口。</p><p>四叶草内容533156499昨日88曝光、5阅读、2商详，未新增归因订单；累计14日归因GMV255元。月光舞裙两条内容合计419曝光、11阅读、1商详。花朵两条合计324曝光、50阅读、6商详。</p><p>花朵图表累计商详28/79，概览为27/68；内容532609487历史日互动合计2、最新累计1，原值和差异均保留。合作状态沿用10/12证据并注明时间；任务费用不当成广告实际消耗。独立广告计划、消耗、预算、点击历史仍未取得。</p></article>
</div><details><summary>头部观察10款 · 10/07—10/13</summary><p>按近7天后台销量排序；本期3款有销量，其余7个零销量观察位按周UV降序、货号升序选取。</p><div class="table-scroll"><table><thead><tr><th>序号</th><th>商品</th><th>周销量</th><th>周UV</th><th>周收藏人数</th><th>后台周转化</th></tr></thead><tbody>'''
for p in tr['products'][:10]:
 r=next(x for x in cmp['businessPeriods'] if x['code']==p['code'] and x['end']=='2026-10-13');v='—' if r['conversionPct'] is None else f"{r['conversionPct']:.2f}%"
 report+=f"<tr><td>{p['rank']}</td><td>{esc(p['name'])}<br>{p['code']}</td><td>{p['weekSales']}</td><td>{p['weekUv']}</td><td>{p['weekFavorites']}</td><td>{v}</td></tr>"
report+='</tbody></table></div></details><p>类目55款，纳入28款、排除27款近7天销量收藏均0的老款；20款来自后台新上架名单，真实首次上架日待确认。只读分析，未改价、改投放或报名活动。</p></section>'
s=re.sub(r'<section class="panel daily-brief">.*?</section>',lambda m:report,s,count=1,flags=re.S)
s=re.sub(r'<title>.*?</title>','<title>10月13日得物商品日报</title>',s,count=1)
s=re.sub(r'<p class="intro">.*?</p>','<p class="intro">2026-10-07 至 2026-10-13 · 一级类目：流行饰品/眼镜/服配 · 10月14日采集</p>',s,count=1)
s=re.sub(r'<div class="scope">.*?</div>',f'<div class="scope"><span>关注28款 · 排除27款老款</span><span>经营{cov["business_records"]}条可用日记录 · 来源322条日记录</span><span>年龄28款84个人群</span></div>',s,count=1)
notice='数据截至10/13。昨日28款经营已齐；两周333条经营日记录可用，59个商品日存在历史指标缺口。来源23款完整覆盖两周，5款经逐款核验无入口。明确区间总量为0直接覆盖零值日期，并注明区间依据；—与未返回记录保留为空，无访客转化率显示—。28款年龄画像420个占比、近月5条引力内容57条分天记录已核验。'
s=re.sub(r'<p class="notice">.*?</p>','<p class="notice">'+notice+'</p>',s,count=1,flags=re.S)
s=re.sub(r'<p class="channel-coverage">.*?</p>','<p class="channel-coverage">23/28款有来源入口，一级渠道完整覆盖09/30—10/13两周；5款仅核心指标页，无渠道明细。区间总量0直接标零，来源底表保留依据，不重复逐日检查；部分历史二级渠道留空。两款路路通来源PV与经营PV存在口径差异，详见单品说明。</p>',s,count=1,flags=re.S)
footer='''<footer><p>采集于2026-10-14。<a href="age-profiles.csv" download>年龄画像底表</a> · <a href="business-two-weeks.csv" download>经营逐日底表</a> · <a href="channel-two-weeks.csv" download>来源逐日底表</a> · <a href="weekly-periods.csv" download>经营周区间原值</a> · <a href="channel-weekly-periods.csv" download>来源周区间原值</a> · <a href="gravity-content-daily.csv" download>引力逐条日值</a> · <a href="gravity-content-month.csv" download>引力累计快照</a> · <a href="selection-audit.csv" download>筛选依据</a> · <a href="zero-interval-evidence.csv" download>零值区间依据</a> · <a href="pv-scope-discrepancies.csv" download>PV口径差异</a> · <a href="coverage.json" download>覆盖与缺口</a></p><p>数据截至10/13，原始导出与截图本地留档。区间零值有依据，缺失不补造；内容累计快照截止时间逐条标明。</p></footer>'''
s=re.sub(r'<footer>.*?</footer>',footer,s,count=1,flags=re.S)
s=s.replace('全部25款重点商品','全部28款重点商品').replace('完整7天 · 2026-10-13采集','完整7天 · 2026-10-14采集')
s=s.replace("const fmt = x=>x==null?'待补采'", "const fmt = x=>x==null?'—'")
s=s.replace("所选期间待补采：", "所选期间不可计算或后台未提供：").replace('本页采用09/29—10/12实际日值；5款新增商品更早查询未返回记录，缺失保留为空。','本页覆盖09/30—10/13；无访客时比率显示—，历史未返回指标留空。零值区间有明确证据，未逐日重复检查。')
# Always show verified per-product source notes, including the observed discrepancy.
s=s.replace("+' · 商详访问次数 PV</p>';", "+' · 商详访问次数 PV</p>'+(product?.source_note?'<p class=\"compare-note\">'+escape(product.source_note)+'</p>':'');")
s=s.replace("    const missing=metrics.filter", "    const missing=metrics.filter")
# Original graphs are driven by records, so null stays a gap and genuine zero remains zero.
for key,data in [('trend-data',tr),('channel-data',ch),('comparison-data',cmp),('age-data',age)]:
 s=re.sub(r'(<script id="'+key+r'" type="application/json">).*?(</script>)',lambda m:m[1]+json.dumps(data,ensure_ascii=False)+m[2],s,flags=re.S)
(D/'index.html').write_text(s)
(O/'10月13日得物商品日报.html').write_text(s)
print(D/'index.html')
