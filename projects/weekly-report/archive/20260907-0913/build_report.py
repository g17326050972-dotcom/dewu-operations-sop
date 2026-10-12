# -*- coding: utf-8 -*-
import base64, html, json, mimetypes, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
W = pathlib.Path(__file__).resolve().parent
D = json.loads((W/'verified.json').read_text())
T = json.loads((W/'top.json').read_text())
OLD = json.loads((ROOT/'work/verified.json').read_text())
ADS = json.loads((W/'ads.json').read_text())
CSS = (ROOT/'work/dara-site/app/globals.css').read_text()
N = lambda v, d=0: f'{v:,.{d}f}'
E = html.escape
PAID = D['revenue']['paid']
A = D['ads']
CLOSED_SKUS = {'YX7316001', 'YX7376001D'}
CLOSED_AMOUNT = 11898
REFERENCE_PAID = PAID - CLOSED_AMOUNT
REFERENCE_ORDERS = D['transaction']['orders'] - 2
REFERENCE_AOV = REFERENCE_PAID / REFERENCE_ORDERS
REFERENCE_CHANGE = (REFERENCE_PAID / 51364 - 1) * 100
sections = []

def table(headers, rows, extra=''):
    return '<div class="table-scroll"><table '+extra+'><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'

def cards(items):
    return '<div class="metrics">'+''.join(f'<div class="metric"><span>{a}</span><strong>{b}</strong><small class="{c}">{d}</small></div>' for a,b,c,d in items)+'</div>'

def callout(text, kind=''):
    return f'<div class="callout {kind}">{text}</div>'

def sec(num,title,sub,body):
    sections.append((title, f'<section id="s{num}" class="section"><div class="section-head"><span class="section-num">{num:02}</span><div><h2>{title}</h2><p>{sub}</p></div><a href="#top" class="up" aria-label="返回顶部">↑</a></div>{body}</section>'))

def image_for(t):
    for folder in [W/'images', ROOT/'work/dara-site/public/top_images']:
        for ext in ['.jpeg','.jpg','.png','.webp']:
            p=folder/(t['sku']+ext)
            if p.exists():
                assert p.stat().st_size>2000, p
                return 'data:'+mimetypes.guess_type(p.name)[0]+';base64,'+base64.b64encode(p.read_bytes()).decode()
    raise RuntimeError('Missing verified photo for '+t['sku'])

sec(1,'销售概况','全店经营 · 2026.09.07—09.13 · 订单状态校正',
    callout('<b>本周判断｜两笔高客单已关闭，校正后支付参考额环比下降。</b> 后台商品导出的原始支付金额为 59,830 元；订单页确认 YX7316001、YX7376001D 两笔合计 11,898 元均为“交易关闭成功”。剔除这两笔后的支付参考额为 47,932 元，较上周低 6.68%。')+
    cards([('校正后支付参考额','¥47,932','down','较上周 −6.68%'),('后台原始支付金额','¥59,830','','含两笔后续关闭订单'),('校正后订单参考','149 单','down','151 支付单减 2 关闭单'),('校正后客单参考',f'¥{REFERENCE_AOV:.2f}','down','按 149 单计算'),('商详访客 UV','33,409','down','环比 −4.91%'),('商详浏览 PV','38,807','down','较上期导出 −5.73%'),('下单转化率','0.50%','','提交订单客户数 ÷ 商详 UV'),('已知有效动销参考','62 款','','64 款减两款已知关闭')])+
    '<p class="footnote">59,830 元、151 单是 1,893 条 SPU 明细加总的后台原始支付口径；47,932 元、149 单仅剔除本次已在订单页确认关闭的两笔订单，用作经营判断参考，不等同于财务结算净额。PV 为商品明细汇总，UV 为交易分析去重口径。查询快照：2026 年 9 月 14 日。</p>')

weeks=[('08.10–08.16',83127),('08.17–08.23',91325),('08.24–08.30',56821),('08.31–09.06',51364),('09.07–09.13',59830)]
pts=[(90+i*170,230-v/100000*190)for i,(_,v)in enumerate(weeks)]
chart='<svg class="trend" viewBox="0 0 860 290" role="img" aria-label="近五周支付金额，依次为83127、91325、56821、51364和59830元">'
for v in [0,50000,100000]:
    y=230-v/100000*190
    chart+=f'<line x1="60" y1="{y}" x2="825" y2="{y}" stroke="#e5ebef"/><text x="50" y="{y+4}" text-anchor="end" class="axis">{v//10000}万</text>'
chart+='<polyline points="'+' '.join(f'{x},{y:.1f}'for x,y in pts)+'" fill="none" stroke="#138a98" stroke-width="3"/>'
for (x,y),(label,v)in zip(pts,weeks):
    chart+=f'<circle cx="{x}" cy="{y}" r="5" fill="white" stroke="#138a98" stroke-width="3"/><text x="{x}" y="{y-17}" text-anchor="middle" class="plot-value">{N(v)}</text><text x="{x}" y="264" text-anchor="middle" class="axis">{label}</text>'
chart+='</svg>'
sec(2,'销售趋势与收入结构','近五个完整自然周 · 趋势图沿用后台原始支付口径',chart+
    callout('<b>原始支付口径显示增长，订单状态校正后仍在下行。</b> 原始支付金额较上周增加 8,466 元、增长 16.48%；两笔高价订单关闭后，经营参考额为 47,932 元，较上周减少 3,432 元、下降 6.68%。趋势图保留后台原始口径，避免把当前周校正值与历史快照混为同一口径。','warning')+
    '<div class="two"><div><h3>支付与订单状态校正</h3>'+table(['口径','金额（元）'],[['后台原始支付金额','59,830.00'],['两笔已确认关闭','<span class="down">−11,898.00</span>'],['校正后支付参考额','<b>47,932.00</b>'],['后台交易成功金额','52,678.00'],['后台履约中金额','1,693.00'],['后台交易关闭金额','5,459.00'],['预估销售收入','45,343.60']])+'</div><div><h3>交易漏斗</h3><div class="funnel"><div style="width:100%">提交订单 <b>179 单</b></div><div style="width:84.36%">支付订单 <b>151 单</b></div><div style="width:70.39%">交易成功 <b>126 单</b></div></div><p>支付转化率 <b>84.36%</b>；实际履约率 <b>83.44%</b>。后台汇总另列 7 单履约中、18 单交易关闭。</p><p class="footnote">预估收入为后台成功交易金额减平台服务费，未扣货品成本、广告费等，不能视为利润。订单页确认的两笔关闭金额合计 11,898 元，与概览“交易关闭金额 5,459 元”不一致，可能来自统计范围或更新时间差异；本报告将两类口径并列展示，不强行合并。</p></div></div>')

sec(3,'流量与成交结构','类目贡献与商品集中度 · 剔除两笔已知关闭订单',
    '<div class="two"><div><h3>校正后类目支付参考</h3><div class="split-bar"><span style="width:76.19%">珠宝 76.19%</span><span style="width:23.81%">饰品</span></div>'+table(['后台类目','参考金额','参考订单','参考动销款'],[['黄金/珠宝/翡翠/玉石','¥36,517','106','56'],['流行饰品/眼镜/服配','¥11,415','43','6']])+'</div><div><h3>增长与流量并不同步</h3>'+table(['指标','上期','本周'],[['商详 UV','35,135','33,409'],['商详 PV','41,164','38,807'],['商品收藏用户数合计','1,974','1,765'],['原始 TOP10 金额占比',f'{sum(t["paid"]for t in json.loads((ROOT/"work/top.json").read_text()))/51364*100:.2f}%','55.98%'],['剔除关闭后 TOP10 参考占比','—','45.05%']])+'</div></div>'+ 
    callout('<b>主销款仍是更可靠的经营抓手。</b> 月光舞裙的原始支付记录为 7,300 元、28 单，是已知未关闭商品中的金额和单量第一名。原始 TOP10 合计 33,491 元、66 单；剔除两笔已知关闭订单后为 21,593 元、64 单，占校正后支付参考额 45.05%。')+
    '<p class="footnote">类目参考金额、订单和动销款只扣除这两笔已知关闭记录；未对全部订单状态做逐单财务审计。收藏用户数合计为逐 SPU 加总，未跨商品去重，不作为全店收藏人数或全店收藏率。</p>')

rows=[]
for i,t in enumerate(T,1):
    is_closed=t['sku'] in CLOSED_SKUS
    fav=t['favorites']/t['visitors']*100 if t['visitors'] else None
    pv=t['previousUV'];pf=t['previousFavorites']
    delta=f'<small class="rate-note">较上期 {fav-pf/pv*100:+.2f} 个百分点</small>' if pv and fav is not None else ''
    status_note='<small class="closed-badge">交易关闭成功 · 不计入经营参考</small>' if is_closed else ('<small class="sample-tag">仅 1 单 · 小样本</small>' if t['orders']==1 else '')
    product=f'<div class="product-cell"><button class="photo-button" aria-label="放大{E(t["name"])}商品原图"><img src="{image_for(t)}" alt="{E(t["name"])}（{t["sku"]}）" loading="lazy"/></button><span><b>{E(t["name"])}</b><code>{t["sku"]}</code>{status_note}</span></div>'
    change=f'{(t["paid"] /t["previousPaid"]-1)*100:+.2f}%' if t['previousPaid'] else '上期无成交'
    amount_note='<small class="rate-note down">已关闭 · 原始支付记录</small>' if is_closed else f'<small class="rate-note">{change}</small>'
    rows.append([f'<span class="rank">{i:02}</span>',product,f'<b>¥{N(t["paid"])}</b>{amount_note}',N(t['orders']),N(t['pv']),N(t['visitors']),f'{t["cvr"]:.2f}%',N(t['favorites']),f'{fav:.2f}%'+delta])
sec(4,'后台支付金额 TOP10','按原始支付金额降序 · 已关闭订单单独标记',
    '<div class="table-tools"><p>原始合计 <b>¥33,491 / 66 单</b> · 已关闭 <b class="down">¥11,898 / 2 单</b> · 剔除后参考 <b>¥21,593 / 64 单</b></p><label class="search">搜索商品或货号 <input id="productSearch" type="search" placeholder="例如：月光舞裙"/></label></div>'+ 
    '<p class="mobile-hint">左右滑动表格，查看转化率、收藏率等完整指标 →</p>'+table(['排名','商品 / 货号','支付金额 / 环比','订单','PV','UV','转化率','收藏用户','收藏率'],rows,'id="productTable"')+
    '<p id="noResults" class="empty" hidden>没有匹配的商品，请更换关键词。</p><p class="footnote">此表保留后台商品分析的原始支付排序，红色标记的两款订单页已显示“交易关闭成功”，因此不计入经营参考额。收藏率 = 收藏用户数 ÷ 同商品商详访客 UV；变化以两期原始人数计算，为百分点差。转化率采用后台商品分析的支付用户数 ÷ 商详访客人数，与全店提交订单转化率不同。所有图片均为对应货号的商品原图，已嵌入页面。</p>')

reviews=[('月光舞裙','YX9354001','主销款转化改善','支付记录 7,300 元、28 单，金额环比 +20.78%；UV 从 5,974 降至 5,141，支付转化率从 0.37% 升至 0.54%。收藏率从 8.05% 降至 7.43%。','复盘促成支付的到手价与页面信息，稳定库存；补充佩戴尺寸和材质说明，观察收藏后的支付承接。'),('甄选满天星','X2117005','修复主销款','支付记录 4,422 元、19 单，金额环比 −35.80%；UV 减少约 15%，转化率从 0.53% 降至 0.44%。收藏率 6.18%。','按素材、价格和访问来源拆解下降环节；先观察点击到商详、商详到支付，再调整投放预算。'),('全珠链四件套','X9315001T','恢复有效访问','支付记录 2,584 元、6 单，金额环比 −32.50%；UV 从 3,008 降至 1,589，转化率从 0.27% 升至 0.38%。收藏率 5.92%。','优先恢复有成交质量的访问，强化套装内容、佩戴与送礼展示；避免仅为拉高访问而放宽人群。'),('南洋金珠吊坠','YX2494001','小样本观察','支付记录 1,679 元、1 单，仅 3 个商详访客，收藏率 0%。','订单量与访问量都很小，先核对履约状态并补充稳定流量样本，再评价商品转化。'),('金珠万能扣吊坠','YX7306001','低量成交观察','支付记录 1,609 元、1 单，91 个商详访客，支付转化率 1.10%；收藏率 0%。','补充珠径、扣头细节和佩戴场景；继续按订单状态核实有效成交，避免按单周一笔支付扩量。')]
sec(5,'商品复盘 TOP5','剔除两笔已知关闭订单后的支付金额前五 · 数据观察与建议动作分开记录',''.join(f'<details class="analysis" open><summary><span class="rank">{i:02}</span><b>{name}</b><code>{sku}</code><span class="tag">{tag}</span></summary><div class="analysis-body"><p><span>数据观察</span>{ev}</p><p><span>建议动作</span>{act}</p></div></details>'for i,(name,sku,tag,ev,act)in enumerate(reviews,1)))

sec(6,'内容运营','蓝 V 及商家矩阵 · 内容展现总次数口径',
    cards([('本周发布','40 条','down','上期 118 条 · −66.10%'),('获推荐内容','36 条','','推荐率 90.00%'),('内容曝光','3,293','down','较上期 −81.39%'),('阅读 / 点击率','48 / 1.46%','','触达人群 1,919')])+
    table(['分发位置','曝光次数','占总曝光'],[['穿搭精选','3,267','99.21%'],['社区推荐','26','0.79%'],['购买推荐位','0','0.00%']])+
    callout('<b>内容供给和曝光同时收缩。</b> 发布数下降 66.10%，曝光下降 81.39%，阅读从 303 次降至 48 次；推荐率虽从 86.44% 提高到 90.00%，尚未弥补总量减少。优先恢复主销款的内容供给，再用阅读与进店承接判断素材质量。')+
    '<div class="mini-stats"><span>点赞 <b>0</b></span><span>评论 <b>0</b></span><span>优质动态 <b>0</b></span><span>品牌内容影响力指数 <b>8,234.39</b></span></div><p class="footnote">曝光、阅读为周期内内容获得的数据，不等于仅统计本周新发布内容；本节与引力投放存在不同统计口径，不合并加总。内容明细页本次未返回可核对的样本列表，因此不沿用上周内容链接。</p>')

adrows=[]
for r in ADS[1:]:
    x=dict(zip(ADS[0],r));adrows.append([x['时间'],x['消耗(元)'],x['点击(次)'],x['直接支付单量(单)'],x['直接支付金额(元)'],x['引导支付单量(单)'],x['引导支付金额(元)']])
sec(7,'得物推投放','推广首页 · 含一键起量 · 7 天导出明细汇总',
    cards([('投放消耗',f'¥{N(A["spend"],2)}','down','较上期 −3.11%'),('曝光次数','148,337','','点击 10,153 · 点击率 6.84%'),('直接支付金额','¥6,001','down','23 单 · 直接 ROI 1.48'),('引导支付金额','¥17,158','','44 单 · 引导 ROI 4.24')])+
    table(['推导指标','本周','说明'],[['平均点击成本',f'¥{A["spend"]/A["clicks"]:.2f}','消耗 ÷ 点击'],['直接订单成本',f'¥{A["spend"]/A["directOrders"]:.2f}','消耗 ÷ 直接支付单量'],['引导订单成本',f'¥{A["spend"]/A["guidedOrders"]:.2f}','消耗 ÷ 引导支付单量'],['商详访问 / 收藏数','5,530 / 273','广告明细口径'],['消耗占全店支付金额',f'{A["spend"]/PAID*100:.2f}%','投入强度参考']])+
    callout('<b>点击效率改善，支付承接走弱。</b> 相比上期，点击增长 8.43%，直接支付金额下降 46.30%，直接 ROI 从 2.68 降至 1.48。9 月 8 日贡献引导金额 9,086 元，占全周 52.95%；引导回报集中度较高，应继续下钻到商品和素材，确认可重复的成交来源。','warning')+
    '<details><summary>查看每日投放与归因成交</summary>'+table(['日期','消耗（元）','点击','直接订单','直接金额','引导订单','引导金额'],adrows)+'</details><p class="footnote">采用 9 月 14 日 09:45 导出版本，消耗加总 4,045.07 元；此前概览快照为 4,045.01 元，相差 0.06 元，统一以导出明细为准。ROI 由汇总金额 ÷ 汇总消耗计算，不平均每日 ROI。直接和引导归因可能重叠，不相加；广告 ROI 不等于利润，归因回传可能继续变化。</p>')

sec(8,'引力投放与任务','图文 / 短视频 · 2026.09.07—09.13',
    cards([('发布任务','0 个','','环比 0%'),('达人新发动态','0 条','','环比 0%'),('引力曝光','75,988','down','环比 −26.40%'),('商详访问','2,626','down','环比 −29.65%')])+
    table(['内容阅读','曝光→阅读点击率','阅读→商详访问率'],[['10,485 次','13.80%','25.05%']])+
    callout('<b>存量素材仍有流量，商详承接继续下降。</b> 阅读环比下降 15.16%，商详访问下降 29.65%；曝光到阅读点击率提高，但阅读到商详访问率从 30.21% 降至 25.05%。优先检查内容与挂接商品的一致性、商品吸引力及购买入口，再安排新内容接续。')+
    '<div class="empty-state"><b>本周已完成任务明细：暂无数据</b><p>发布时间筛选为 9 月 7 日—13 日，图文/短视频已完成任务列表为空。该结果不代表全部在途合作，也不能据此认定引力费用为零。</p></div>')

sec(9,'下一轮内容与商品机会','基于本周数据制定的待执行测试',
    table(['对象','本周证据','建议测试','复盘指标'],[['月光舞裙','28 单；收藏率 7.43%','佩戴比例、银饰材质、扇形细节三组表达','相同周期 UV、收藏率、支付转化'],['甄选满天星','19 单；金额 −35.80%','对比原有有效素材与新封面，核查到手价','访问来源、直接订单成本、退款'],['薄荷蓝绿花朵 YX9638001','88 UV / 4 单；金额 1,526 元','围绕近景质感和上身尺寸做小批量测试','UV 样本扩大后转化是否稳定'],['18K金属怪色 KX1824001','760 UV / 4 单；金额 1,284 元','珠光、金属色与礼赠场景对比','收藏到支付、商品级归因成本']])+
    callout('<b>先用有限预算验证，避免由小样本直接推预算。</b> 新品和高价款应同时关注有效访问、支付、交付与退款。银饰货盘可用于相应 SKU 的成本核算，但不能替代海水珍珠等全店商品的真实成本，也不能用全账户 ROI 推算单款利润。'))

actions=[('P0','统一关闭订单口径','运营与财务 / 本周一','YX7316001、YX7376001D 已确认交易关闭；记录关闭原因，并核对订单页合计 11,898 元与经营概览关闭金额 5,459 元的统计差异。','验收：后续周报同时保留后台原始值、已知关闭订单和校正后经营参考值。'),('P0','下钻投放支付承接','投放 / 本周一至二','按商品、素材检查点击增长而直接订单下降的原因；核对 9 月 8 日引导成交明细，再调整预算。','验收：商品级消耗、直接/引导归因、退款口径一致。'),('P1','恢复主销款内容供给','内容 / 本周二至五','围绕月光舞裙、满天星、四件套补充佩戴和礼赠素材，标记素材版本与挂接商品。','验收：以曝光、阅读、商详访问及支付评估，不只看发布数。'),('P1','验证两款商品增量','运营与内容 / 本周内','对薄荷花朵和18K金属怪色款做小规模素材测试，先确认更大访问样本下的支付表现。','验收：两款分别记录 UV、收藏率、支付转化和归因成本。'),('P1','复核订单与退款进度','客服与运营 / 每日','跟进 7 单履约中订单；商品导出显示按支付时间退款 18 单、11,970 元，需与交易关闭等口径分开核对。','验收：本周订单处理状态、退款原因及退款时间口径可追溯。')]
sec(10,'本周行动清单','2026.09.14—09.20 · 建议责任人与验收标准，尚未执行','<p id="actionProgress" class="footnote">已勾选 0 / 5 项（仅当前页面）</p><div class="action-list">'+''.join(f'<label class="action"><input type="checkbox" data-action/><span class="priority {"p0" if p=="P0" else ""}">{p}</span><span><b>{name}</b><small>{owner}</small><p>{act}</p><em>{accept}</em></span></label>'for p,name,owner,act,accept in actions)+'</div>')

body='<div id="top" class="topbar"><a class="brand" href="#top">DARA <small>戴拉</small></a><span class="top-period">得物经营周报 · W37</span><button id="printBtn">打印 / 保存 PDF</button></div>'
body+='<header class="hero"><div><div class="eyebrow">DARA · WEEKLY BUSINESS REVIEW</div><h1>戴拉得物经营周报</h1><p class="period">2026.09.07 — 09.13</p><p class="hero-note">两笔高客单已关闭，校正后支付参考额环比下降 6.68%</p><div class="hero-meta"><span>杭州戴拉珠宝有限公司</span><span>数据核对：2026.09.14</span><span>第 37 周</span></div></div><div class="hero-number"><span>校正后支付参考额</span><strong>¥47,932</strong><small>剔除两笔已知关闭 · 149 单参考</small><small>后台原始支付 ¥59,830</small></div></header>'
body+='<nav class="section-nav" aria-label="报告目录">'+''.join(f'<a href="#s{i}">{i:02} {title}</a>'for i,(title,_)in enumerate(sections,1))+'</nav><main>'+''.join(content for _,content in sections)
body+='<aside class="sources"><h2>数据来源与口径</h2><div class="source-grid"><p><b>经营与商品</b><br>得物商家后台经营概览、交易分析；9 月 14 日生成的商品 SPU 导出，共 1,893 条。统一筛选 9 月 7 日—13 日，全部品牌、类目与渠道，优惠后支付口径。</p><p><b>订单状态校正</b><br>订单页截图确认 YX7316001（6,299 元）和 YX7376001D（5,599 元）均显示“交易关闭成功”。公开报告不展示订单编号；两笔只用于校正经营参考额。</p><p><b>内容、投放与比较</b><br>蓝 V / 商家矩阵内容概览、引力数据概览及得物推导出。环比基期为 8 月 31 日—9 月 6 日；TOP10 原图按货号匹配商品页并嵌入页面。</p></div><details><summary>退款与状态说明</summary><p>商品明细按退款时间汇总为 44 单、27,617.23 元，可能包含更早支付订单；按支付时间汇总为 18 单、11,970 元。订单页确认的两笔关闭订单合计 11,898 元，而经营概览显示交易关闭金额 5,459 元，可能来自统计范围或更新时间差异。报告保留后台原始支付数据，并单独给出剔除这两笔后的经营参考值，不把不同口径强行相减。后续履约、退款和广告归因回传仍可能更新。</p></details></aside></main>'
body+='<footer><b>DARA 戴拉</b><span>经营复盘 · 数据截止 2026.09.13 · 制作 2026.09.14</span><a href="../20260831-0906/">查看上期周报 ↗</a></footer><dialog id="photoDialog"><button id="closePhoto" aria-label="关闭商品大图">×</button><img id="largePhoto" alt=""/><p id="photoCaption"></p></dialog>'
CSS+='''
.mobile-hint{display:none}@media(max-width:600px){.mobile-hint{display:block;font-size:11px;color:#6c8997;margin:0 0 12px}}.hero-number small{color:#cbe3e9;display:block}.eyebrow{letter-spacing:2px;font-size:11px;color:#bfdee2;margin-bottom:12px}.rate-note{display:block;color:#8196a4;font-size:10px;margin-top:5px}.sample-tag{display:block;font-size:10px;color:#b27845;margin-top:4px}.closed-badge{display:block;width:max-content;max-width:100%;font-size:10px;font-weight:700;color:#a33f31;background:#ffe3dc;border-radius:999px;padding:3px 7px;margin-top:5px}.product-cell>span{min-width:180px}.photo-button{padding:0;background:none;border:0;cursor:zoom-in;flex:none}.product-cell .photo-button img{width:72px;height:72px;display:block}.photo-button:focus-visible{outline:2px solid #258c96;border-radius:7px}dialog{border:0;border-radius:12px;padding:25px;max-width:min(90vw,760px);box-shadow:0 15px 70px #0004}dialog::backdrop{background:#1238}dialog img{display:block;max-width:100%;max-height:75vh;object-fit:contain;margin:auto}dialog p{text-align:center;font-size:13px;color:#456}#closePhoto{position:absolute;right:8px;top:4px;background:white;border:0;font-size:30px;cursor:pointer}#productTable th{position:sticky;top:0}#productTable td{padding:15px 13px}#productTable tbody tr:has(.closed-badge){background:#fff4f0}#productTable tbody tr:has(.closed-badge) img{filter:saturate(.7)}@media(max-width:600px){.product-cell>span{min-width:145px}.product-cell .photo-button img{width:66px;height:66px}.metric strong{font-size:20px}.section-nav{gap:14px}}@media print{.product-cell .photo-button img{width:42px;height:42px}.product-cell>span{min-width:85px}#productTable td{padding:7px 5px}.sample-tag,.closed-badge,.rate-note{font-size:8px}dialog{display:none}}
'''
JS='''const search=document.getElementById('productSearch');function filter(){const q=search.value.trim().toLowerCase();let shown=0;document.querySelectorAll('#productTable tbody tr').forEach(r=>{r.hidden=!r.textContent.toLowerCase().includes(q);shown+=!r.hidden});document.getElementById('noResults').hidden=shown>0}search.addEventListener('input',filter);document.getElementById('printBtn').onclick=()=>{search.value='';filter();document.querySelectorAll('details').forEach(d=>d.open=true);window.print()};const actions=[...document.querySelectorAll('[data-action]')];actions.forEach(a=>a.onchange=()=>document.getElementById('actionProgress').textContent='已勾选 '+actions.filter(x=>x.checked).length+' / 5 项（仅当前页面）');const dialog=document.getElementById('photoDialog');document.querySelectorAll('.photo-button').forEach(b=>b.onclick=()=>{const im=b.querySelector('img');document.getElementById('largePhoto').src=im.src;document.getElementById('largePhoto').alt=im.alt;document.getElementById('photoCaption').textContent=im.alt;dialog.showModal()});document.getElementById('closePhoto').onclick=()=>dialog.close();dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close()});'''
out='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/><meta name="robots" content="noindex,nofollow"/><title>戴拉 DARA｜得物经营周报 2026.09.07—09.13</title><style>'+CSS+'</style></head><body>'+body+'<script>'+JS+'</script></body></html>'
dest=W/'site';dest.mkdir(exist_ok=True);(dest/'index.html').write_text(out)
(ROOT/'outputs/戴拉得物经营周报_20260907-0913.html').write_text(out)
print(f'Generated {len(sections)} sections, {len(T)} original product photos, {len(out.encode()):,} bytes')
