"""Build the Oct 5–11 DARA weekly report from verified aggregate evidence."""
import argparse,csv,html,json,shutil
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
BASE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data',type=Path,default=BASE/'examples/20261005-1011')
parser.add_argument('--output',type=Path,default=BASE/'output/site')
args=parser.parse_args()
W=args.data.resolve();OUT=args.output.resolve()
def load(n): return json.loads((W/n).read_text())
A=load('analysis.json'); S=A['summary']; T=load('transaction_overview.json'); C=load('content_overview.json'); D=load('ads_overview.json'); G=load('gravity_evidence.json'); GW=load('gravity_weekly.json')
ROWS=A['products']; TOP=ROWS[:10]
assert all(A['checks'].values())
assert T['paid_amount']==S['raw'] and T['paid_orders']==S['paid_orders']
assert S['raw']-S['closed']-S['other_refund']==S['active']
assert S['active']-S['pending']==S['conservative']
assert sum(r['active'] for r in ROWS)==S['active']
assert G['accepted_count']==len(G['accepted_content'])==2
for x in G['accepted_content']:
    u=urlsplit(x['content_url']); assert u.hostname=='m.dewu.com' and parse_qs(u.query)['trendId']==[x['content_id']]
OUT.mkdir(parents=True,exist_ok=True); (OUT/'images').mkdir(exist_ok=True)
CSS=(BASE/'assets/report.css').read_text()
JS=(BASE/'assets/report.js').read_text()
CSS+='\n.metric strong{white-space:normal;overflow-wrap:anywhere}.two>*{min-width:0}.gravity-story{break-inside:avoid}.up{flex:none}.source-grid{line-height:1.9}@media(max-width:600px){.section-head{align-items:flex-start}.hero-number>span{float:none;padding:0}.gravity-story-head h3{overflow-wrap:anywhere}.metric strong{font-size:20px}}'

def e(v): return html.escape(str(v),quote=True)
def num(v): return '—' if v is None else f'{v:,.0f}'
def money(v): return f'¥{v:,.0f}' if v==round(v) else f'¥{v:,.2f}'
def pct(v): return '—' if v is None else f'{v:.2f}%'
def metric(label,value,note='',tone=''): return f'<div class="metric"><span>{e(label)}</span><strong>{e(value)}</strong><small class="{e(tone)}">{e(note)}</small></div>'
def metrics(items,cls=''): return f'<div class="metrics {cls}">'+''.join(metric(*i) for i in items)+'</div>'
def table(head,rows,id=''): return '<div class="table-scroll"><table'+(f' id="{id}"' if id else '')+'><thead><tr>'+''.join(f'<th scope="col">{e(h)}</th>' for h in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{v}</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def note(s): return '<p class="footnote">'+s+'</p>'
def call(s,w=False): return '<div class="callout'+(' warning' if w else '')+'">'+s+'</div>'
sections=[]
def sec(title,sub,body):
    n=len(sections)+1; sections.append((title,f'<section id="s{n}" class="section"><div class="section-head"><span class="section-num">{n:02}</span><div><h2>{e(title)}</h2><p>{e(sub)}</p></div><a class="up" href="#top" aria-label="返回顶部">↑</a></div>{body}</section>'))
NAMES={'YX9354001':'月光舞裙银饰项链','X2117005':'甄选满天星珍珠项链','X9315001T':'全珠链吊坠四件套','H8177001':'正圆强光白珠耳钉','S2245001':'AK白珠双排手串','YX6829001':'戴妃款珍珠项链','YH9389002':'强光白珠简约耳钉','YX6952001':'金色海水珍珠项链','X1818002':'长款珍珠毛衣链','YX9615001':'好运相随四叶草项链'}
photos={}
for r in TOP:
    sku=r['sku']; found=None
    for folder in [W/'images']:
        for ext in ['.jpg','.jpeg','.png','.webp']:
            f=folder/(sku+ext)
            if f.is_file() and f.stat().st_size>2000: found=f; break
        if found: break
    if not found: raise FileNotFoundError(sku)
    shutil.copy2(found,OUT/'images'/found.name); photos[sku]='images/'+found.name

def product_cells(r,i,photo=False):
    name=NAMES.get(r['sku'],r['name'].replace('戴拉 DARA','').strip()[:35])
    image=f'<button class="photo-button" aria-label="放大{e(r["sku"])}商品原图"><img src="{photos[r["sku"]]}" alt="{e(name)} {e(r["sku"])}" loading="eager" width="72" height="72"></button>' if photo else ''
    sample='<small class="sample-tag">商详访客不足30 · 小样本</small>' if r['detail_uv'] is not None and r['detail_uv']<30 else ''
    label=f'<div class="product-cell">{image}<span><b title="{e(r["name"])}">{e(name)}</b><code>{e(r["sku"])}</code>{sample}</span></div>'
    return [f'<span class="rank">{i:02}</span>',label,'<b>'+money(r['active'])+'</b>',money(r['raw']),money(r['closed']),money(r['pending']),num(r['active_orders']),num(r['detail_uv']),num(r['favorites']),pct(r['favorite_rate'])]
HEAD=['排名','商品 / 货号','当前有效销售','原始支付','已关闭','售后中风险','有效订单','商详 UV','收藏用户','收藏率']
top_total=sum(r['active'] for r in TOP); top_share=top_total/S['active']*100
sec('经营概况','2026年10月5日—11日 · 全店 · 10月12日订单与售后快照',
    call('<b>本周判断：</b>商详访客环比 +27.87%，原始支付金额环比 −12.54%。流量增加未同步转化为成交；已关闭金额占原始支付 '+pct(S['closed']/S['raw']*100)+'。按订单状态核对后的当前有效销售为 <b>'+money(S['active'])+'</b>。')+
    metrics([('当前有效订单销售额',money(S['active']),'88单 · 已剔除关闭及完成退款','positive'),('后台原始支付',money(S['raw']),'125单 · 环比 −12.54%'),('已关闭订单金额',money(S['closed']),'37单 · 从原始支付中剔除','down'),('售后中风险金额',money(S['pending']),'5单 · 暂计入当前有效销售','down'),('扣除售后中保守参考',money(S['conservative']),'假设售后中订单全部不保留'),('有效成交商品','43款','有原始支付记录的商品56款'),('商品商详访问',num(S['product_pv'])+'次','逐SPU PV合计'),('商品收藏用户',num(S['product_favorites']),'逐SPU合计，跨商品未去重')])+
    note('当前有效销售不是最终结算收入，也不是利润。订单状态截至10月12日导出时点；未完成售后仍可能改变结果。'))
cat={}
for r in ROWS:
    z=cat.setdefault(r['category'],dict(raw=0,closed=0,active=0))
    for k in z: z[k]+=r[k]
bridge='<div class="bridge">'+''.join(f'<div><span>{label}</span><strong>{value}</strong></div>' for label,value in [('原始支付',money(S['raw'])),('减：已关闭',money(S['closed'])),('当前有效销售',money(S['active'])),('其中：售后处理中',money(S['pending'])),('扣除售后中保守参考',money(S['conservative']))])+'</div>'
sec('销售金额对账','订单与商品导出总额、逐货号金额及支付单量全部核对一致',bridge+
    note('已完成退款记录 '+money(S['completed_refund_evidence'])+' 与已关闭订单重叠，仅作状态佐证，不再重复扣除。售后中5单的支付金额为 '+money(S['pending'])+'，申请退款金额为 '+money(S['pending_requested'])+'；保守参考按这些订单全部支付金额不保留计算。144条订单中，19条交易失败未形成支付。')+
    '<div class="two"><div><h3>类目销售</h3>'+table(['类目','原始支付','已关闭','当前有效','有效销售占比'],[[e(k),money(v['raw']),money(v['closed']),money(v['active']),pct(v['active']/S['active']*100)] for k,v in sorted(cat.items(),key=lambda x:-x[1]['active'])])+'</div><div><h3>商品集中度</h3><div class="focus-stat"><span>当前有效销售 TOP10</span><strong>'+money(top_total)+'</strong><small>占全店 '+pct(top_share)+'</small></div></div></div>'+
    '<details><summary>查看订单与售后状态计数</summary><div class="two">'+table(['订单状态','订单数'],[[e(k),num(v)] for k,v in A['status_counts'].items()])+table(['匹配售后状态','售后记录数'],[[e(k),num(v)] for k,v in A['aftersales_status_counts'].items()])+'</div>'+note('售后按订单号关联并去重。一个订单可有多个售后申请，不能按售后记录条数重复扣款。')+'</details>')
sec('流量与交易漏斗','全店优惠后口径 · 周度交易概览',metrics([('全店商详访客 UV',num(T['detail_uv']),'环比 +27.87%'),('提交订单','144单','130位客户 · 商详转化率0.35%'),('支付订单','125单','支付转化率86.81%'),('支付笔单价',money(T['average_paid_order']),'环比 −7.64%')])+
    '<div class="funnel"><div style="width:100%">提交订单 <b>144单</b></div><div style="width:86.81%">支付订单 <b>125单</b></div></div>'+
    call('后台本周交易成功 <b>95单 / ¥32,840</b>，实际履约率76.00%。此指标按后台周度事件口径统计，不能替代本周订单截至10月12日的有效销售 ¥25,122。')+
    note('环比为后台与前7天比较，使用原始支付口径；本报告未将此环比标在剔除关闭后的销售额上。全店UV为去重访客，与逐SPU访客加总不同。'))
sec('当前有效销售 TOP10','真实商品原图 · 按剔除关闭后的金额排序',
    '<div class="table-tools"><p>TOP10合计 <b>'+money(top_total)+'</b> · 全店占比 '+pct(top_share)+'</p><label class="search">搜索商品或货号 <input id="topSearch" type="search" placeholder="输入货号或名称"></label></div><p class="mobile-hint">左右滑动查看金额、访客与收藏率 →</p>'+table(HEAD,[product_cells(r,i,True) for i,r in enumerate(TOP,1)],'topTable')+'<p id="topEmpty" class="empty" hidden>没有匹配商品。</p>'+note('收藏率 = 单款收藏用户数 ÷ 单款商详访问人数。售后中风险已包含在当前有效金额内；图片可点开查看大图。'))
sec('逐款销售对账','全部56款有支付记录商品 · 汇总CSV可下载',
    '<div class="table-tools"><label class="search">搜索商品或货号 <input id="allSearch" type="search" placeholder="输入货号或名称"></label><a class="download" href="sku-reconciliation.csv" download>下载逐款对账 CSV</a></div><p class="mobile-hint">左右滑动查看完整字段 →</p>'+table(HEAD,[product_cells(r,i) for i,r in enumerate(ROWS,1)],'allTable')+'<p id="allEmpty" class="empty" hidden>没有匹配商品。</p>'+note('CSV包含完整商品名称和逐款汇总，不包含订单编号、买家联系方式或收货地址。'))
closed=sorted(ROWS,key=lambda r:-r['closed'])[:5]; pending=sorted([r for r in ROWS if r['pending']],key=lambda r:-r['pending'])
sec('退货与关闭观察','按金额识别需要复核的款',
    '<div class="two"><div><h3>关闭金额前5款</h3>'+table(['货号','原始支付','已关闭','当前有效'],[[e(r['sku']),money(r['raw']),money(r['closed']),money(r['active'])] for r in closed])+'</div><div><h3>全部售后中商品</h3>'+table(['货号','风险订单','售后中支付额','扣除后参考'],[[e(r['sku']),num(r['pending_orders']),money(r['pending']),money(r['conservative'])] for r in pending])+'</div></div>'+call('优先跟进 YH6166001（¥629）与 YX6829001（¥299）的售后结果；两款占售后中支付金额 '+pct(928/1463*100)+'。售后最终状态更新后，再重算销售与排名。',True))
sec('内容运营','蓝V及商家矩阵 · 10月5日—11日',metrics([('本周发布','121条','转发3次'),('获推荐内容','109条','推荐率90.08% · 优质动态0条'),('内容展现','4,230次','触达2,297人'),('阅读 / 点击率','71 / 1.68%','点赞1次 · 评论0次')])+
    table(['分发位置','展现次数','展现占比'],[['穿搭精选','4,100',pct(4100/4230*100)],['社区推荐','130',pct(130/4230*100)],['购买推荐位','0','0.00%']])+note('内容展现主要来自穿搭精选。121条发布对应71次阅读，后续可优先测试封面、上身效果和标题；发布量本身不代表有效获客。本节不与引力或广告流量加总。'))
sec('得物推投放','推广首页 · 含一键起量 · 10月12日11:11查询',metrics([('投放消耗',money(D['spend']),'本周广告消耗'),('点击次数',num(D['clicks']),'点击率9.19%'),('商详访问成本',money(D['product_detail_visit_cost']),'后台展示口径'),('引导支付金额',money(D['guided_payment_amount']),'31单 · 引导ROI 1.89'),('优惠后引导支付 ROI','1.89','优惠后引导支付 ¥8,774')],'ads-metrics')+
    table(['口径','支付订单','支付金额','ROI'],[['直接支付','19',money(D['direct_payment_amount']),'1.08'],['引导支付','31','¥8,774','1.89'],['优惠后引导支付','—','¥8,774','1.89']])+
    call('广告归因可能重叠并随后续回传更新，不与全店有效销售相加。ROI 1.89 是归因收入与消耗之比，不代表扣除退款、货品成本及平台费用后的利润。',True))
gbody=metrics([('本周新建任务','4个','10月11日创建的4个主任务'),('本周商家验收','2条','10月9日1条、10月11日1条'),('当前待验收任务','0个','10月12日10:42查询快照')],'gravity-metrics')
gbody+='<h3>本周引力整体流量</h3>'+metrics([('内容曝光',num(GW['impressions']),'环比 +17.16%'),('内容阅读',num(GW['reads']),'点击率12.96% · 环比 +9.98%'),('商详访问',num(GW['detail_visits']),'阅读→商详27.88% · 环比 +16.15%')],'gravity-metrics')
for x in G['accepted_content']:
    gbody+=f'<article class="gravity-story"><div class="gravity-story-head"><span>本周验收内容 · {e(x["accepted_at"][:16])} 商家验收</span><h3>{e(x["title"])}</h3><p>{e(x["creator"])} · 花朵项链 YX9638001 · 实际发布 {e(x["actual_published_at"][:16])}</p><a class="gravity-story-link" href="{e(x["content_url"])}" target="_blank" rel="noopener noreferrer">查看得物原帖 ↗</a></div>'
    gbody+=metrics([('单篇曝光',num(x['impressions']),'累计快照'),('单篇阅读',num(x['reads']),'点击率 '+pct(x['ctr_percent'])),('单篇商详访问',num(x['detail_visits']),'阅读→商详 '+pct(x['detail_rate_percent'])),('14日归因成交','0单','GMV ¥0 · 归因期尚未结束')],'gravity-story-metrics')+note('单篇数据截至 '+e(x['metrics_as_of'])+'，为发布后累计快照，不是本周区间数据。任务数据页将“发布时间”记为验收时点；实际发布时间采用最新任务报告导出的动态发布时间。14日归因仍可能更新。')+'</article>'
gbody+=note('商家旧引力周概览的发布任务/动态均显示0，与新版引力明细不一致；本报告任务数量采用新版任务列表及商家验收时间逐条核实的4个新建、2条验收。周度流量采用商家引力概览的10月5—11日范围。当前待验收0个是10月12日快照，不能视为10月11日末的历史存量。')
sec('引力投放','任务数量、周度流量与单篇累计表现分开展示',gbody)
sec('下周重点动作','数据支持的建议 · 尚未自动调整投放或价格',
    '<div class="action-list">'+''.join(f'<div class="action"><span></span><span class="priority {"p0" if i<2 else ""}">P{i}</span><span><b>{title}</b><p>{text}</p></span></div>' for i,title,text in [
    (0,'先更新5单售后结果','售后中支付金额¥1,463；退款完成后同步重算有效销售和TOP10，避免把关闭订单当成交。'),
    (1,'围绕月光舞裙做内容与转化复盘','YX9354001当前有效¥4,359、17单，收藏率8.37%。对比访问、收藏和关闭原因，继续观察高意向访客是否转为有效订单。'),
    (2,'复核广告的退款后回收','得物推消耗¥4,639.75、优惠后引导支付ROI 1.89。按同一批归因订单核对售后后，再判断是否增加预算。'),
    (2,'对比花朵项链两条验收内容','枳川大点击率19.00%、商详访问57；麦麦子z点击率7.76%、商详访问15。发布时长不同且样本小，先追踪7/14日结果，再决定复用哪种内容。')])+'</div>')
sec('数据口径与来源','便于分享、复核与下一期延续',
    '<div class="source-grid"><div><h3>销售与售后</h3><p>全店订单144行：10月12日10:36导出；售后909行：10:39导出，并仅关联本周订单。原始支付按出价减卖家承担优惠还原，与SPU及交易概览完全一致。</p></div><div><h3>商品与投放</h3><p>SPU明细1909款，明确选择10月5—11日，11:06导出。商品图片按货号匹配后台及已有商品原图。得物推选择同一周，含一键起量。</p></div><div><h3>内容与引力</h3><p>蓝V及商家矩阵为自然周第41周。引力任务与验收逐条核对，单篇指标取10月12日任务报告与数据页；原帖链接已核对内容标题。</p></div></div>'+
    note('本报告销售为优惠后支付口径，已排除关闭订单及与之重叠的完成退款；尚未扣除货品成本、平台服务费、运费和投放费用，不作为利润报表。不同模块的访问和归因不能相加。金额单位为人民币。'))
nav='<nav class="section-nav" aria-label="报告目录">'+''.join(f'<a href="#s{i}"><span>{i:02}</span>{e(t)}</a>' for i,(t,b) in enumerate(sections,1))+'</nav>'
body='<div id="top"></div><header class="topbar"><a class="brand" href="#top">DARA<span>戴拉</span></a><span class="top-period">得物经营周报 / 2026年第41周</span><button id="printBtn">打印 / 保存PDF</button></header>'
body+='<div class="hero"><div><div class="eyebrow">WEEKLY BUSINESS REPORT</div><h1>戴拉得物经营周报</h1><p class="period">2026.10.05 — 10.11</p><p class="hero-note">全店销售与售后对账 · 商品表现 · 内容与投放</p><div class="hero-meta"><span>自然周 · 周一至周日</span><span>10月12日核验</span><span>真实商品图与原帖链接</span></div></div><div class="hero-number"><span>当前有效订单销售额</span><strong>¥25,122</strong><div>88单 <span>·</span> 另有售后中 ¥1,463</div></div></div>'+nav+'<main>'+''.join(b for t,b in sections)+'</main><footer><b>DARA 戴拉</b><span>2026年10月12日整理 · 状态后续可能更新</span><a href="#top">返回顶部 ↑</a></footer><dialog id="photoDialog"><button id="closePhoto" aria-label="关闭商品大图">×</button><img id="largePhoto" alt=""><p id="photoCaption"></p></dialog>'
page='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><meta name="description" content="戴拉得物10月5日—11日周报，含订单售后对账、真实商品图、收藏率、得物推及引力内容。"><title>戴拉得物经营周报｜2026.10.05—10.11</title><style>'+CSS+'</style></head><body>'+body+'<script>'+JS+'</script></body></html>'
(OUT/'index.html').write_text(page)
with (OUT/'sku-reconciliation.csv').open('w',encoding='utf-8-sig',newline='') as f:
    wr=csv.writer(f); wr.writerow(['排名','货号','商品名称','类目','原始支付金额','已关闭金额','当前有效销售','售后中支付金额','扣除售后中保守参考','支付订单数','有效订单数','商详访客','收藏用户','收藏率%'])
    for i,r in enumerate(ROWS,1): wr.writerow([i,r['sku'],r['name'],r['category'],r['raw'],r['closed'],r['active'],r['pending'],r['conservative'],r['paid_orders'],r['active_orders'],r['detail_uv'],r['favorites'],r['favorite_rate']])
print(json.dumps({'built':str(OUT),'sku_rows':len(ROWS),'photos':len(photos),'top10_total':top_total,'top10_share':round(top_share,2),'sales':S,'checks':A['checks']},ensure_ascii=False,indent=2))
