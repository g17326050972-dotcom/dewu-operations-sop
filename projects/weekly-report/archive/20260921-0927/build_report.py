"""Build the DARA Sep 21–27 report from reconciled, product-level exports.

Publishes aggregate commerce values and one verified public creator post. The
source order/after-sales workbooks and their customer fields stay in the private
workspace. Missing product photos stop the build, so the shared report never
displays invented or mismatched product art.
"""

import base64
import csv
import html
import json
import mimetypes
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
OUT = WORK / 'site'
PRODUCT = json.loads((WORK / 'product_analysis.json').read_text())
ORDER = json.loads((WORK / 'order_analysis.json').read_text())
TRANSACTION = json.loads((WORK / 'transaction_overview.json').read_text())
CONTENT = json.loads((WORK / 'content_overview.json').read_text())
GRAVITY = json.loads((WORK / 'gravity_overview.json').read_text())
ADS = json.loads((WORK / 'ads_overview.json').read_text())
CSS = (ROOT / 'work/dara-site/app/globals.css').read_text()
GRAVITY_ACTIVITY = GRAVITY['verified_activity']
GRAVITY_PENDING = GRAVITY['pending_acceptance']
if GRAVITY_ACTIVITY['accepted_tasks'] != len(GRAVITY_ACTIVITY['accepted_content']):
    raise ValueError('Gravity accepted-task count does not match the verified content records')
if GRAVITY_ACTIVITY['accepted_tasks'] != 1:
    raise ValueError('Expected one verified Gravity acceptance for this reporting week')
GRAVITY_CONTENT = GRAVITY_ACTIVITY['accepted_content'][0]
GRAVITY_CONTENT_URL = GRAVITY_CONTENT['content_url']
parsed_content_url = urlsplit(GRAVITY_CONTENT_URL)
if (parsed_content_url.scheme != 'https' or parsed_content_url.hostname != 'm.dewu.com'
        or parsed_content_url.path != '/h5-sociality/community/community-share'
        or parse_qs(parsed_content_url.query).get('trendId') != [GRAVITY_CONTENT['content_id']]):
    raise ValueError('Gravity content URL does not match the verified Dewu post ID')

P = PRODUCT['aggregate']
SUMMARY = ORDER['summary']
O = {
    'raw_paid': SUMMARY['rawPaidAmount'],
    'closed_paid': SUMMARY['closedAmount'],
    'active_paid_reference': SUMMARY['actualSalesReference'],
    'pending_return_order_paid': SUMMARY['pendingAfterSalesAmount'],
    'no_known_aftersale_paid_reference': SUMMARY['conservativeRetainedReference'],
}
REQUIRED_TOTALS = [
    'raw_paid', 'closed_paid', 'active_paid_reference',
    'pending_return_order_paid', 'no_known_aftersale_paid_reference',
]
for key in REQUIRED_TOTALS:
    if key not in O:
        raise ValueError(f'order_analysis.json missing totals.{key}')
if round(O['raw_paid'], 2) != round(P['rawPaidAmount'], 2):
    raise ValueError('Order raw payment does not reconcile to the SPU export')
if round(TRANSACTION['paid_amount'], 2) != round(O['raw_paid'], 2) or TRANSACTION['paid_orders'] != SUMMARY['rawPaidOrders']:
    raise ValueError('Transaction overview does not reconcile to the paid-order export')
if round(O['raw_paid'] - O['closed_paid'], 2) != round(O['active_paid_reference'], 2):
    raise ValueError('Closed-order bridge does not reconcile')
if round(O['active_paid_reference'] - O['pending_return_order_paid'], 2) != round(O['no_known_aftersale_paid_reference'], 2):
    raise ValueError('Pending-return bridge does not reconcile')

ORDER_ROWS = [{
    'sku': row['sku'],
    'name': row['name'],
    'raw_paid': row['rawPaidAmount'],
    'paid_orders': row['rawPaidOrders'],
    'closed_paid': row['closedAmount'],
    'closed_orders': row['closedOrders'],
    'active_paid_reference': row['actualSalesReference'],
    'active_orders': row['activeOrders'],
    'pending_return_order_paid': row['pendingAfterSalesAmount'],
    'pending_return_orders': row['pendingAfterSalesOrders'],
    'no_known_aftersale_paid_reference': row['conservativeRetainedReference'],
} for row in ORDER['products'] if row['rawPaidAmount'] > 0]
PAID_PRODUCTS = {item['sku']: item for item in PRODUCT['paidProducts']}
if len({row['sku'] for row in ORDER_ROWS}) != len(ORDER_ROWS):
    raise ValueError('Duplicate SKU in order reconciliation')
missing_skus = sorted({row['sku'] for row in ORDER_ROWS} - PAID_PRODUCTS.keys())
if missing_skus:
    raise ValueError(f'Order SKUs missing from product export: {missing_skus}')
for row in ORDER_ROWS:
    if round(row['raw_paid'], 2) != round(PAID_PRODUCTS[row['sku']]['paidAmount'], 2):
        raise ValueError(f'Raw order/product amount mismatch for {row["sku"]}')
if round(sum(row['raw_paid'] for row in ORDER_ROWS), 2) != round(O['raw_paid'], 2):
    raise ValueError('Product-level order amounts do not sum to the order total')
if round(sum(row['active_paid_reference'] for row in ORDER_ROWS), 2) != round(O['active_paid_reference'], 2):
    raise ValueError('Product-level active amounts do not sum to the order total')

ROWS = sorted(ORDER_ROWS, key=lambda row: (-row['active_paid_reference'], -row['raw_paid'], row['sku']))
TOP = [row for row in ROWS if row['active_paid_reference'] > 0][:10]
if len(TOP) < 10:
    raise ValueError('Fewer than ten products have positive active sales')
if '--check-data' in sys.argv:
    print(json.dumps({
        'raw': O['raw_paid'],
        'closed': O['closed_paid'],
        'actual': O['active_paid_reference'],
        'pending': O['pending_return_order_paid'],
        'conservative': O['no_known_aftersale_paid_reference'],
        'paidProducts': len(ROWS),
        'activeProducts': sum(row['active_paid_reference'] > 0 for row in ROWS),
        'top10Skus': [row['sku'] for row in TOP],
        'top10Actual': sum(row['active_paid_reference'] for row in TOP),
    }, ensure_ascii=False, indent=2))
    raise SystemExit(0)


def e(value):
    return html.escape(str(value), quote=True)


def money(value, decimals=None):
    if decimals is None:
        decimals = 0 if round(value, 2) == round(value) else 2
    return f'{value:,.{decimals}f}'


def rate(value):
    return '—' if value is None else f'{value:.2f}%'


def compact_name(item):
    name = item['name'].replace('戴拉 DARA', '').strip()
    return name[:34] + ('…' if len(name) > 34 else '')


def photo_for(sku):
    folders = [WORK / 'images', ROOT / 'work/20260907-0913/images', ROOT / 'work/dara-site/public/top_images']
    for folder in folders:
        for extension in ['.jpeg', '.jpg', '.png', '.webp']:
            path = folder / (sku + extension)
            if path.is_file() and path.stat().st_size > 2000:
                mime = mimetypes.guess_type(path.name)[0]
                return f'data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}'
    raise FileNotFoundError(f'No verified product photo for {sku}')


def table(headers, rows, table_id=None):
    table_attribute = f' id="{e(table_id)}"' if table_id else ''
    head = ''.join(f'<th scope="col">{e(header)}</th>' for header in headers)
    body = ''.join('<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>' for row in rows)
    return f'<div class="table-scroll"><table{table_attribute}><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def metric(label, value, note, tone=''):
    return f'<div class="metric"><span>{e(label)}</span><strong>{e(value)}</strong><small class="{e(tone)}">{e(note)}</small></div>'


def section(number, title, subtitle, content):
    return (title, f'<section id="s{number}" class="section"><div class="section-head"><span class="section-num">{number:02}</span><div><h2>{e(title)}</h2><p>{e(subtitle)}</p></div><a href="#top" class="up" aria-label="返回顶部">↑</a></div>{content}</section>')


def product_cells(row, ranking, with_photo):
    item = PAID_PRODUCTS[row['sku']]
    if with_photo:
        src = photo_for(row['sku'])
        picture = f'<button class="photo-button" aria-label="放大{e(row["sku"])}商品原图"><img src="{src}" alt="{e(compact_name(item))}商品原图" loading="lazy"></button>'
    else:
        picture = ''
    sample_note = '<small class="sample-tag">商详访客不足 30 · 小样本</small>' if item['detailUV'] < 30 else ''
    label = f'<div class="product-cell">{picture}<span><b title="{e(item["name"])}">{e(compact_name(item))}</b><code>{e(row["sku"])}</code>{sample_note}</span></div>'
    return [
        f'<span class="rank">{ranking:02}</span>',
        label,
        f'<b>¥{money(row["active_paid_reference"])}</b>',
        f'¥{money(row["raw_paid"])}',
        f'¥{money(row["closed_paid"])}',
        f'¥{money(row["pending_return_order_paid"])}',
        str(row['active_orders']),
        money(item['detailUV']),
        str(item['favorites']),
        rate(item['favoriteRatePct']),
    ]


headers = ['排名', '商品 / 货号', '当前有效销售', '原始支付', '已关闭', '售后中风险', '有效订单', '商详 UV', '收藏用户', '收藏率']
top_rows = [product_cells(row, i, True) for i, row in enumerate(TOP, 1)]
all_rows = [product_cells(row, i, False) for i, row in enumerate(ROWS, 1)]

category_values = {}
for row in ROWS:
    category = PAID_PRODUCTS[row['sku']]['category']
    current = category_values.setdefault(category, {'raw': 0, 'closed': 0, 'active': 0, 'pending': 0})
    current['raw'] += row['raw_paid']
    current['closed'] += row['closed_paid']
    current['active'] += row['active_paid_reference']
    current['pending'] += row['pending_return_order_paid']
category_rows = []
for category, values in sorted(category_values.items(), key=lambda pair: -pair[1]['active']):
    share = values['active'] / O['active_paid_reference'] * 100 if O['active_paid_reference'] else 0
    category_rows.append([e(category), f'¥{money(values["raw"])}', f'¥{money(values["closed"])}', f'<b>¥{money(values["active"])}</b>', f'{share:.2f}%'])

top_paid = sum(row['active_paid_reference'] for row in TOP)
top_share = top_paid / O['active_paid_reference'] * 100
closed_top = sorted((row for row in ROWS if row['closed_paid'] > 0), key=lambda row: -row['closed_paid'])[:5]
pending_top = sorted((row for row in ROWS if row['pending_return_order_paid'] > 0), key=lambda row: -row['pending_return_order_paid'])[:5]
closed_rows = [[e(row['sku']), f'¥{money(row["raw_paid"])}', f'¥{money(row["closed_paid"])}', f'¥{money(row["active_paid_reference"])}'] for row in closed_top]
pending_rows = [[e(row['sku']), f'¥{money(row["active_paid_reference"])}', f'¥{money(row["pending_return_order_paid"])}', f'¥{money(row["no_known_aftersale_paid_reference"])}'] for row in pending_top]
order_status_rows = [[e(row['status']), str(row['orderRows']), f'¥{money(row["rawPaidAmount"])}'] for row in SUMMARY['statusBreakdown']]
aftersales_status_rows = [[e(row['status']), str(row['rows']), f'¥{money(row["listedRefundAmount"])}'] for row in SUMMARY['matchedAfterSalesStatusBreakdown']]

sections = []
sections.append(section(1, '经营概况', '9 月 21—27 日支付订单 · 截至 9 月 28 日导出状态',
    '<div class="callout"><b>本周判断</b>：商品分析原始支付包含已关闭订单。订单逐款对账后，当前有效订单销售额为 <b>¥'+money(O['active_paid_reference'])+'</b>。另有 ¥'+money(O['pending_return_order_paid'])+' 的订单处于售后中，结果仍可能变化。</div>'+
    '<div class="metrics">'+''.join([
        metric('当前有效订单销售额', '¥'+money(O['active_paid_reference']), str(SUMMARY['activeOrders'])+' 笔订单 · 已剔除关闭单', 'positive'),
        metric('后台原始支付', '¥'+money(O['raw_paid']), str(P['rawPaidOrders'])+' 笔支付订单'),
        metric('已关闭订单金额', '¥'+money(O['closed_paid']), str(SUMMARY['closedOrders'])+' 笔 · 从原始支付中剔除', 'down'),
        metric('售后中风险金额', '¥'+money(O['pending_return_order_paid']), str(SUMMARY['pendingAfterSalesOrders'])+' 笔 · 暂计入有效销售', 'down'),
        metric('扣除售后中保守参考', '¥'+money(O['no_known_aftersale_paid_reference']), '仅用于风险情景，不作已退款金额'),
        metric('有效成交商品', str(sum(row['active_paid_reference'] > 0 for row in ROWS))+' 款', '按订单状态逐款汇总'),
        metric('商品商详访问', money(P['sumProductDetailPV'])+' 次', '逐 SPU PV 合计'),
        metric('商品收藏用户', money(P['sumProductFavorites']), '逐 SPU 合计，跨商品未去重'),
    ])+'</div>'+
    '<p class="footnote">此处“当前有效”指在订单导出快照中未关闭的支付订单，并非最终结算收入。售后申请尚在处理中，待结果更新后应重算。</p>'))

sections.append(section(2, '销售金额对账', '同一周支付订单，按当前订单状态逐笔归并',
    '<div class="bridge"><div><span>商品分析原始支付</span><strong>¥'+money(O['raw_paid'])+'</strong></div><div><span>减：已关闭及退款成功</span><strong class="down">−¥'+money(O['closed_paid'])+'</strong></div><div class="bridge-result"><span>当前有效订单销售额</span><strong>¥'+money(O['active_paid_reference'])+'</strong></div><div><span>其中：售后处理中</span><strong class="down">¥'+money(O['pending_return_order_paid'])+'</strong></div><div><span>若售后全部完成退款</span><strong>¥'+money(O['no_known_aftersale_paid_reference'])+'</strong></div></div>'+
    '<p class="footnote">已完成退款记录金额 ¥'+money(SUMMARY['completedRefundAmount'])+' 与已关闭订单重叠，只作状态佐证，不再从销售额扣一次。¥'+money(O['pending_return_order_paid'])+' 是售后中订单的已支付金额，不代表实际退款金额；售后申请退款额为 ¥'+money(SUMMARY['pendingAfterSalesRequestedRefund'])+'。保守参考是假设这些订单的全部支付金额最终不保留的情景值。订单导出与商品导出的原始支付合计均为 ¥'+money(O['raw_paid'])+'，已完成总额及逐货号核对。</p>'+
    '<div class="two"><div><h3>类目销售</h3>'+table(['类目', '原始支付', '已关闭', '当前有效', '有效销售占比'], category_rows)+'</div><div><h3>商品集中度</h3><div class="focus-stat"><span>当前有效 TOP10</span><strong>¥'+money(top_paid)+'</strong><small>占全店当前有效销售 '+f'{top_share:.2f}%'+ '</small></div><p class="footnote">TOP10 按订单状态校正后的金额重新排序；不是商品分析的原始支付排名。</p></div></div>'+
    '<details><summary>查看订单与售后状态汇总</summary><div class="two"><div><h3>订单状态</h3>'+table(['状态', '订单行', '原始支付金额'], order_status_rows)+'</div><div><h3>匹配的售后状态</h3>'+table(['状态', '售后单', '售后单列示退款额'], aftersales_status_rows)+'</div></div><p class="footnote">售后单和订单状态会变化；“售后成功”与已关闭订单属于同一批事件，不将售后金额再次扣减。</p></details>'))

payment_funnel_width = TRANSACTION['paid_orders'] / TRANSACTION['submitted_orders'] * 100
success_funnel_width = TRANSACTION['transaction_success_orders'] / TRANSACTION['submitted_orders'] * 100
sections.append(section(3, '流量与交易漏斗', '后台交易概览的周维度数据',
    '<div class="metrics">'+''.join([
        metric('全店商详访客 UV', money(TRANSACTION['product_detail_visitors_uv']), '环比 '+f'{TRANSACTION["week_over_week_percent"]["product_detail_visitors_uv"]:+.2f}%'),
        metric('提交订单', str(TRANSACTION['submitted_orders'])+' 单', '提交客户 '+str(TRANSACTION['submitted_customers'])+' 人 · 转化率 '+f'{TRANSACTION["product_detail_cvr_percent"]:.2f}%'),
        metric('支付订单', str(TRANSACTION['paid_orders'])+' 单', '支付转化率 '+f'{TRANSACTION["payment_conversion_percent"]:.2f}%'),
        metric('后台交易成功', str(TRANSACTION['transaction_success_orders'])+' 单', '周维度金额 ¥'+money(TRANSACTION['transaction_success_amount'])+' · 履约率 '+f'{TRANSACTION["fulfillment_rate_percent"]:.2f}%'),
    ])+'</div>'+
    '<div class="funnel"><div style="width:100%">提交订单 <b>'+str(TRANSACTION['submitted_orders'])+' 单</b></div><div style="width:'+f'{payment_funnel_width:.2f}%'+'">支付订单 <b>'+str(TRANSACTION['paid_orders'])+' 单</b></div><div style="width:'+f'{success_funnel_width:.2f}%'+'">后台交易成功 <b>'+str(TRANSACTION['transaction_success_orders'])+' 单</b></div></div>'+
    '<p class="footnote">后台原始支付金额环比 '+f'{TRANSACTION["week_over_week_percent"]["paid_amount"]:+.2f}%'+ '。此环比使用后台周维度原始支付口径。后台本周交易成功 123 单，与 9 月 28 日订单导出快照中的 124 笔当前有效订单统计时间和状态含义不同，报告分别列示。</p>'))

sections.append(section(4, '当前有效销售 TOP10', '真实商品原图 · 原始支付和售后风险并列展示',
    '<div class="table-tools"><p>TOP10 当前有效销售 <b>¥'+money(top_paid)+'</b>，占全店 <b>'+f'{top_share:.2f}%'+ '</b></p><label class="search">搜索商品或货号 <input id="topSearch" type="search" placeholder="输入货号或名称"></label></div>'+
    '<p class="mobile-hint">左右滑动查看金额、访客与收藏率 →</p>'+table(headers, top_rows, 'topTable')+
    '<p id="topEmpty" class="empty" hidden>没有匹配商品。</p><p class="footnote">收藏率 = 单款收藏用户数 ÷ 单款商详访问人数；访客不足 30 的商品标注小样本，收藏率波动较大。“售后中风险”仅提示可能变化的金额，当前仍包含在有效销售中。图片按商品货号匹配真实商品原图。所有金额均为订单支付口径，不等于最终利润。</p>'))

sections.append(section(5, '逐款销售对账', '全部有支付记录的商品 · 可查询并下载不含订单号的汇总',
    '<div class="table-tools"><p>共 <b>'+str(len(ROWS))+' 款</b>；按当前有效销售额降序</p><label class="search">搜索商品或货号 <input id="allSearch" type="search" placeholder="输入货号或名称"></label><a class="download" href="./sku-reconciliation.csv" download>下载逐款对账 CSV</a></div>'+
    '<p class="mobile-hint">左右滑动查看完整字段 →</p>'+table(headers, all_rows, 'allTable')+
    '<p id="allEmpty" class="empty" hidden>没有匹配商品。</p><p class="footnote">CSV 仅含 SKU 汇总，不含订单编号、买家信息或地址。单款原始金额与订单导出按货号合计一致；售后状态按导出快照更新。</p>'))

sections.append(section(6, '退货与关闭观察', '按影响金额找需要继续跟进的商品',
    '<div class="two"><div><h3>关闭金额较高的商品</h3>'+table(['货号', '原始支付', '已关闭', '当前有效'], closed_rows)+'</div><div><h3>售后中金额较高的商品</h3>'+table(['货号', '当前有效', '售后中支付额', '保守参考'], pending_rows)+'</div></div>'+
    '<div class="callout warning"><b>后续复核</b>：对售后中商品跟踪最终退款状态，再更新实销额与 TOP10。按退款时间发生的退款可能来自更早支付的订单，不能直接从本周支付额再次扣除。</div>'))

content = CONTENT['blue_v_and_merchant_matrix']
sections.append(section(7, '内容运营', '蓝 V 及商家矩阵 · 本周内容概览',
    '<div class="metrics">'+''.join([
        metric('本周发布', str(content['published'])+' 条', '转载 '+str(content['reposts'])+' 条'),
        metric('获推荐内容', str(content['recommended'])+' 条', '推荐率 '+f'{content["recommendation_rate_percent"]:.2f}%'),
        metric('内容展现', money(content['content_impressions'])+' 次', '触达人群 '+money(content['unique_impression_viewers'])),
        metric('阅读 / 点击率', str(content['reads'])+' / '+f'{content["click_through_rate_percent"]:.2f}%','本周互动点赞 '+str(content['likes'])+' 次'),
    ])+'</div>'+
    table(['分发位置', '展现次数', '占本周展现'], [
        ['穿搭精选', money(content['outfit_selection_impressions']), f'{content["outfit_selection_impressions"] / content["content_impressions"] * 100:.2f}%'],
        ['社区推荐', money(content['community_recommendation_impressions']), f'{content["community_recommendation_impressions"] / content["content_impressions"] * 100:.2f}%'],
        ['购买推荐位', money(content['purchase_recommendation_impressions']), f'{content["purchase_recommendation_impressions"] / content["content_impressions"] * 100:.2f}%'],
    ])+'<p class="footnote">本节为本周后台内容概览，未叠加得物推或引力数据；内容展现和商品商详访问属于不同统计范围。</p>'))

sections.append(section(8, '得物推投放', '推广首页 · 含一键起量 · '+ADS['snapshot_at']+' 更新',
    '<div class="metrics ads-metrics">'+''.join([
        metric('投放消耗', '¥'+money(ADS['spend'], 2), '后台推广首页口径'),
        metric('点击次数', money(ADS['clicks']), '本周广告点击'),
        metric('商详访问成本', '¥'+money(ADS['product_detail_visit_cost'], 2), '后台概览指标'),
        metric('引导支付金额', '¥'+money(ADS['guided_payment_amount']), '引导 ROI '+f'{ADS["guided_payment_roi"]:.2f}'),
        metric('优惠后引导支付 ROI', f'{ADS["guided_payment_roi_after_discount"]:.2f}', '优惠后引导支付 ¥'+money(ADS['guided_payment_amount_after_discount'])),
    ])+'</div><div class="callout warning"><b>广告归因与全店实销不同。</b> 本周直接支付 '+str(ADS['direct_paid_orders'])+' 单；引导支付金额和优惠后引导支付金额按后台分别列示，本次快照均为 ¥'+money(ADS['guided_payment_amount'])+'。归因可能与直接支付重叠，也可能随回传更新。不得与 ¥'+money(O['active_paid_reference'])+' 全店当前有效销售额相加；ROI 也不等于利润。</div>'))

sections.append(section(9, '引力投放', '图文 / 短视频 · 本周数据概览',
    '<div class="metrics gravity-metrics">'+''.join([
        metric('本周新建任务', str(GRAVITY_ACTIVITY['created_tasks'])+' 个', '9 月 21—27 日'),
        metric('本周商家验收', str(GRAVITY_ACTIVITY['accepted_tasks'])+' 条', '已发布并验收'),
        metric('当前待验收任务', str(GRAVITY_PENDING['count'])+' 个', GRAVITY_PENDING['snapshot_date']+' 查询快照'),
    ])+'</div><h3>引力内容 · 本周整体表现</h3><div class="metrics gravity-metrics">'+''.join([
        metric('内容曝光', money(GRAVITY['impressions']), '环比 '+f'{GRAVITY["week_over_week_percent"]["impressions"]:+.2f}%'),
        metric('内容阅读', money(GRAVITY['reads']), '曝光→阅读 '+f'{GRAVITY["impression_to_read_ctr_percent"]:.2f}%'),
        metric('商详访问', money(GRAVITY['product_detail_visits']), '阅读→商详 '+f'{GRAVITY["read_to_product_detail_rate_percent"]:.2f}%'),
    ])+'</div><div class="gravity-story"><div class="gravity-story-head"><span>本周验收内容 · '+e(GRAVITY_CONTENT['merchant_accepted_at'][:10])+' 商家验收</span><h3>'+e(GRAVITY_CONTENT['title'])+'</h3><p>'+e(GRAVITY_CONTENT['creator'])+' · '+e(GRAVITY_CONTENT['product'])+' · '+e(GRAVITY_CONTENT['sku'])+' · 动态详情显示 '+e(GRAVITY_CONTENT['dynamic_detail_published_at'][:16])+' 发布</p><a class="gravity-story-link" href="'+e(GRAVITY_CONTENT_URL)+'" target="_blank" rel="noopener noreferrer">查看得物原帖 ↗</a></div><div class="metrics gravity-story-metrics">'+''.join([
        metric('单篇曝光', money(GRAVITY_CONTENT['impressions']), '累计快照'),
        metric('单篇阅读', money(GRAVITY_CONTENT['reads']), '点击率 '+f'{GRAVITY_CONTENT["click_through_rate_percent"]:.1f}%'),
        metric('单篇商详访问', money(GRAVITY_CONTENT['product_detail_visits']), '阅读→商详 '+f'{GRAVITY_CONTENT["read_to_product_detail_rate_percent"]:.2f}%'),
        metric('14 日归因成交', str(GRAVITY_CONTENT['attributed_14_day_orders'])+' 单', 'GMV ¥'+money(GRAVITY_CONTENT['attributed_14_day_gmv'])),
    ])+'</div><p class="footnote">任务数据页将该条发布时间记为 '+e(GRAVITY_CONTENT['task_data_published_at'][:16])+'，与动态详情显示的 '+e(GRAVITY_CONTENT['dynamic_detail_published_at'][:16])+' 不一致；本页以动态详情作为实际发布时间。单篇数据截至 '+e(GRAVITY_CONTENT['metrics_as_of'])+'，为发布后的累计快照，不是 9 月 21—27 日单篇区间值；14 日归因尚会更新，也不与全店销售相加。</p></div><p class="footnote">新建任务与本周流量总量取营销引力周概览；新发及验收按引力任务明细核对：本周发布内容 '+str(GRAVITY_ACTIVITY['creator_posts'])+' 条。周概览的新发动态显示 0 条，与任务明细不符，因此本页使用逐任务核验值。待验收 0 个是 '+e(GRAVITY_PENDING['snapshot_date'])+' 的查询存量，不代表 9 月 27 日末的历史状态。引力、蓝 V 内容与得物推的流量归因可能重叠，不能加总为全店访问。</p>'))

head_product = next(row for row in ROWS if row['sku'] == 'X9315001T')
sections.append(section(10, '下周重点动作', '基于本周数据提出的待执行复核与测试',
    '<div class="action-list">'+''.join([
        '<div class="action"><span></span><span class="priority p0">P0</span><span><b>更新售后结果</b><p>跟踪 '+str(SUMMARY['pendingAfterSalesOrders'])+' 笔售后处理中订单，优先核对 YH5525004 涉及的 ¥'+money(next(row['pending_return_order_paid'] for row in ROWS if row['sku'] == 'YH5525004'))+'；售后完结后重算各款当前有效销售与 TOP10。</p><em>验收：订单状态、退款结果和更新日期在逐款对账中一致。</em></span></div>',
        '<div class="action"><span></span><span class="priority p0">P0</span><span><b>复核头部款关闭原因</b><p>全珠链四件套 X9315001T 原始支付 ¥'+money(head_product['raw_paid'])+'，其中 ¥'+money(head_product['closed_paid'])+' 已关闭；按订单关闭原因分类，定位可改善的履约或商品说明问题。</p><em>验收：按原因统计关闭单数和金额，并跟踪下一周变化。</em></span></div>',
        '<div class="action"><span></span><span class="priority p1">P1</span><span><b>提高内容点击效率</b><p>本周发布 '+str(content['published'])+' 条，内容展现 '+money(content['content_impressions'])+' 次、阅读 '+str(content['reads'])+' 次；围绕当前有效销售 TOP3 的佩戴图与尺寸信息做封面对照。</p><em>验收：同口径比较展现→阅读点击率和对应商品商详访问。</em></span></div>',
        '<div class="action"><span></span><span class="priority p1">P1</span><span><b>核对广告商品级回报</b><p>得物推本周消耗 ¥'+money(ADS['spend'], 2)+'、引导支付 ¥'+money(ADS['guided_payment_amount'])+'；按商品追踪广告归因订单后续关闭和售后，复核真实保留成交。</p><em>验收：分清直接与引导归因，逐款核对消耗、成交状态及售后结果。</em></span></div>',
        '<div class="action"><span></span><span class="priority p1">P1</span><span><b>检查引力商详承接</b><p>引力内容阅读 '+money(GRAVITY['reads'])+' 次、商详访问 '+money(GRAVITY['product_detail_visits'])+' 次；复核挂接商品和当前页面信息，确认阅读后访问的阻力。</p><em>验收：按素材记录阅读→商详访问率，避免和蓝 V 数据相加。</em></span></div>',
    ])+'</div><p class="footnote">以上为建议动作，报告生成时尚未在后台执行。</p>'))

sections.append(section(11, '口径与数据来源', '商品经营汇总与公开内容信息；不展示订单或买家明细',
    '<div class="source-grid"><p><b>商品数据</b><br>得物商家后台商品（SPU）明细导出，'+money(P['spuRows'])+' 个 SPU。支付金额、商详访客、收藏人数和收藏率按商品口径。</p><p><b>订单与售后</b><br>得物订单导出及售后单导出，按订单号在本地匹配状态，再按货号汇总。公开页面仅展示逐款金额。</p><p><b>概览与引力</b><br>交易分析、蓝 V 内容、得物推与引力周概览均筛选 2026.09.21—09.27；得物推取 '+e(ADS['snapshot_at'])+' 快照。引力单篇链接由公开分享页核对，发布时间对照任务数据页与动态详情，验收及累计表现按任务明细核对。订单、售后与待验收状态取 2026.09.28 查询快照。</p></div>'+
    '<details><summary>查看详细口径</summary><p>商品分析的原始支付金额、订单导出的原始支付金额均为 ¥'+money(O['raw_paid'])+'。先剔除订单状态确认已关闭或退款成功的支付金额，再得到当前有效销售额。售后处理中订单仍属于当前有效销售，但在页面单独列示风险；保守参考是假设售后中订单均不保留的情景测算。</p><p>商品导出中的“退货金额（支付时间）”为 ¥'+money(P['returnAmountByPaymentTime'])+'，“退货金额（退款时间）”为 ¥'+money(P['returnAmountByRefundTime'])+'，统计窗口不同，不叠加扣减。逐商品 UV 与收藏用户数会跨商品重复，不能相加作为全店去重人数；'+str(P['indexLabeledVisitCellsExcludedFromSums']['商详访问人数'])+' 个带“指数”的商详访问单元格不代表绝对人数，已从商品访问加总中排除。</p></details>'))

body = '<div id="top" class="topbar"><a href="#top" class="brand">DARA <span>戴拉</span></a><span class="top-period">得物经营周报 · 2026 W39</span><button id="printBtn">打印 / 保存 PDF</button></div>'
body += '<header class="hero"><div><div class="eyebrow">WEEKLY BUSINESS REVIEW</div><h1>戴拉 · 得物经营周报</h1><p class="period">2026.09.21 — 09.27</p><p class="hero-note">逐单核对关闭与售后状态后的当前有效销售</p><div class="hero-meta"><span>杭州戴拉珠宝有限公司</span><span>全店商品</span><span>状态快照 2026.09.28</span></div></div><div class="hero-number"><span>当前有效订单销售额</span><strong>¥'+money(O['active_paid_reference'])+'</strong><div>原始支付 ¥'+money(O['raw_paid'])+' <span>·</span> 售后中风险 ¥'+money(O['pending_return_order_paid'])+'</div></div></header>'
body += '<nav class="section-nav" aria-label="周报目录">'+''.join(f'<a href="#s{i}"><span>{i:02}</span>{e(title)}</a>' for i, (title, _) in enumerate(sections, 1))+'</nav>'
body += '<main>'+''.join(content for _, content in sections)+'</main><footer><b>DARA 戴拉</b><span>数据截止 2026.09.27 · 状态查询 2026.09.28</span><a href="#top">返回顶部 ↑</a></footer>'
body += '<dialog id="photoDialog"><button id="closePhoto" aria-label="关闭商品大图">×</button><img id="largePhoto" alt=""><p id="photoCaption"></p></dialog>'

CSS += '''
.two>*{min-width:0}
.ads-metrics{grid-template-columns:repeat(5,minmax(0,1fr))}
.gravity-story-link{display:inline-flex;align-items:center;margin:0 0 16px;padding:7px 11px;border:1px solid #a8d2d8;border-radius:6px;background:#eaf6f7;color:#176f7d;font-size:12px;font-weight:700}.gravity-story-link:hover{background:#dff1f3;text-decoration:none}
.gravity-metrics{grid-template-columns:repeat(3,minmax(0,1fr));margin-bottom:20px}.gravity-story{margin-top:20px;padding:22px;border:1px solid #cde2e8;border-radius:10px;background:#f7fbfc}.gravity-story-head span{font-size:11px;font-weight:700;letter-spacing:.5px;color:#187d8c}.gravity-story-head h3{margin:7px 0 2px}.gravity-story-head p{margin:0 0 17px;color:#647b8e;font-size:12px}.gravity-story-metrics{grid-template-columns:repeat(4,minmax(0,1fr));margin:0}.gravity-story>.footnote{margin:15px 0 0}
.gravity-story-head p{margin-bottom:7px}
.hero-number strong{font-size:42px}.mobile-hint{display:none}.bridge{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:20px 0}.bridge>div{padding:15px;border:1px solid #e4ecf0;background:#f7fafb;border-radius:8px}.bridge>div span{display:block;font-size:11px;color:#78909e;min-height:35px}.bridge>div strong{display:block;font-size:18px;color:#345c71;white-space:nowrap}.bridge .bridge-result{background:#e6f3f2;border-color:#bcdedc}.bridge-result strong{color:#147d7d!important}.focus-stat{padding:24px;border:1px solid #dfedf0;border-radius:10px;background:#f2faf9}.focus-stat span,.focus-stat small{display:block;color:#738e9a;font-size:12px}.focus-stat strong{display:block;font-size:31px;color:#177f88;margin:4px 0}.download{border:1px solid #bfdadd;border-radius:6px;padding:6px 12px;white-space:nowrap;font-size:11px}.product-cell>span{display:block;min-width:195px;white-space:normal;line-height:1.4}.product-cell b{display:block;max-width:245px}.sample-tag{display:block;color:#a77c48;font-size:10px;margin-top:4px}.photo-button{padding:0;background:none;border:0;cursor:zoom-in;flex:none}.product-cell .photo-button img{width:72px;height:72px;display:block}.photo-button:focus-visible{outline:2px solid #258c96;border-radius:7px}#topTable td,#allTable td{padding:12px 10px}#topTable th,#allTable th{padding:12px 10px}#topTable td:nth-child(3),#allTable td:nth-child(3){background:#f0f9f8}#topTable td:nth-child(6),#allTable td:nth-child(6){color:#b47a55}dialog{border:0;border-radius:12px;padding:25px;max-width:min(90vw,760px);box-shadow:0 15px 70px #0004}dialog::backdrop{background:#1238}dialog img{display:block;max-width:100%;max-height:75vh;object-fit:contain;margin:auto}dialog p{text-align:center;font-size:13px;color:#456}#closePhoto{position:absolute;right:8px;top:4px;background:white;border:0;font-size:30px;cursor:pointer}@media(max-width:900px){.bridge{grid-template-columns:repeat(2,1fr)}}@media(max-width:600px){.bridge{grid-template-columns:1fr 1fr}.bridge>div{padding:11px}.bridge>div span{min-height:40px}.bridge>div strong{font-size:15px}.mobile-hint{display:block;color:#7d96a3;font-size:11px}.hero-number strong{font-size:34px}.hero-number>span{float:none;padding:0}.product-cell>span{min-width:160px}.product-cell .photo-button img{width:62px;height:62px}.download{display:block}}@media print{.bridge{grid-template-columns:repeat(5,1fr);break-inside:avoid}.bridge>div strong{font-size:13px}.bridge>div span{font-size:9px}.photo-button img{width:40px!important;height:40px!important}.product-cell>span{min-width:90px}#topTable td,#allTable td{padding:6px 4px;font-size:8px}.download,dialog{display:none}#allTable{font-size:7px}}
@media(max-width:600px){.gravity-metrics,.gravity-story-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.gravity-story{padding:16px}}
@media(max-width:900px){.ads-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media print{.ads-metrics{grid-template-columns:repeat(3,1fr)}.gravity-metrics{grid-template-columns:repeat(3,1fr)}.gravity-story-metrics{grid-template-columns:repeat(4,1fr)}}
'''
JS = '''function wireSearch(inputId,tableId,emptyId){const input=document.getElementById(inputId),rows=[...document.querySelectorAll('#'+tableId+' tbody tr')],empty=document.getElementById(emptyId);input.addEventListener('input',()=>{const q=input.value.trim().toLowerCase();let shown=0;rows.forEach(row=>{row.hidden=!row.textContent.toLowerCase().includes(q);shown+=!row.hidden});empty.hidden=shown>0})}wireSearch('topSearch','topTable','topEmpty');wireSearch('allSearch','allTable','allEmpty');document.getElementById('printBtn').onclick=()=>{document.querySelectorAll('input[type=search]').forEach(i=>{i.value='';i.dispatchEvent(new Event('input'))});document.querySelectorAll('details').forEach(d=>d.open=true);window.print()};const dialog=document.getElementById('photoDialog');document.querySelectorAll('.photo-button').forEach(button=>button.onclick=()=>{const original=button.querySelector('img');document.getElementById('largePhoto').src=original.src;document.getElementById('largePhoto').alt=original.alt;document.getElementById('photoCaption').textContent=original.alt;dialog.showModal()});document.getElementById('closePhoto').onclick=()=>dialog.close();dialog.addEventListener('click',event=>{if(event.target===dialog)dialog.close()});'''
page = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>戴拉得物经营周报｜2026.09.21—09.27</title><style>'+CSS+'</style></head><body>'+body+'<script>'+JS+'</script></body></html>'

OUT.mkdir(exist_ok=True)
(OUT / 'index.html').write_text(page)
with (OUT / 'sku-reconciliation.csv').open('w', encoding='utf-8-sig', newline='') as handle:
    writer = csv.writer(handle)
    writer.writerow(['排名', '货号', '商品名称', '类目', '原始支付金额', '已关闭金额', '当前有效销售额', '售后中支付金额', '扣除售后中保守参考', '原始支付订单数', '当前有效订单数', '商品商详访客', '收藏用户', '收藏率%'])
    for index, row in enumerate(ROWS, 1):
        item = PAID_PRODUCTS[row['sku']]
        writer.writerow([index, row['sku'], item['name'], item['category'], row['raw_paid'], row['closed_paid'], row['active_paid_reference'], row['pending_return_order_paid'], row['no_known_aftersale_paid_reference'], row['paid_orders'], row['active_orders'], item['detailUV'], item['favorites'], item['favoriteRatePct']])
print(f'Built {OUT / "index.html"} ({len(page.encode()):,} bytes), {len(ROWS)} SKU rows, 10 verified photos')
