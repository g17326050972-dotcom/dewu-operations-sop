from pathlib import Path
import json
import re

base = Path(__file__).resolve().parent.parent
site = base / 'work/dewu-trend-site/dist/index.html'
assets = base / 'work/channel-component'
source = site.read_text()
if 'id="channel-data"' not in source:
    (base / 'work/trend-site-before-channels.html').write_text(source)
else:
    source = (base / 'work/trend-site-before-channels.html').read_text()
data = json.loads((base / 'outputs/2026-10-08/渠道逐日整理数据.json').read_text())
metrics = json.loads((base / 'work/retry_metrics.json').read_text())
eligible = {r[0]:r for r in metrics['rows'] if r[2] or r[4][1] > 0 or r[4][7] > 0}
trend_match = re.search(r'<script id="trend-data" type="application/json">(.*?)</script>',source,re.S)
trend = json.loads(trend_match[1])
trend['products'] = [dict(p,weekFavorites=eligible[p['code']][4][7]) for p in trend['products'] if p['code'] in eligible]
trend['records'] = [r for r in trend['records'] if r['code'] in eligible]
trend['top'] = [p['code'] for p in trend['products'][:10]]
trend['observedCount'] = len(trend['records'])
trend['expectedCount'] = len(eligible)*len(trend['dates'])
source = source[:trend_match.start(1)] + json.dumps(trend,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c') + source[trend_match.end(1):]
observed = sum(bool(p['days']) for p in data['products'].values())
unavailable = sum(p.get('source_status') == 'not_exposed_in_backend' for p in data['products'].values())
coverage = f'来源已采 {observed}/{len(eligible)} 款 · {unavailable} 款后台当前仅提供总量 · 核心两款 7 天，其余已采款 2 天 · 截至 2026-10-08'
css = (assets / 'channel-section.css').read_text() + '''
.view-switch{display:flex;gap:8px;margin:14px 0}.view-switch button.active{background:#254c64;color:#fff;border-color:#254c64}
[hidden]{display:none!important}.channel-coverage{font-size:14px;color:#607684;margin:0 0 8px}.channel-section{margin-top:10px}
.channel-section p,.channel-controls,.channel-summary span,.channel-table{font-size:14px}.channel-section .channel-caption{font-size:13px}
@media(max-width:480px){.charts .axis,.charts .point{font-size:24px}.charts .missing{font-size:20px}}
'''
source = source.replace('</style>', css + '</style>', 1)
view_controls = '<div class="view-switch" role="group" aria-label="数据视图"><button id="view-channels" class="active" aria-pressed="true">流量来源</button><button id="view-trends" aria-pressed="false">经营趋势</button></div>'
source = source.replace('<p class="notice">', view_controls + '<p class="notice">', 1)
mount = '<div id="channel-block"><p class="channel-coverage">' + coverage + '</p>' + (assets / 'channel-section.html').read_text() + '</div>'
source = source.replace('<section id="charts"', mount + '<section id="charts"', 1)
inline_data = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
scripts = '<script id="channel-data" type="application/json">' + inline_data + '</script><script>window.CHANNEL_DATA=JSON.parse(document.getElementById("channel-data").textContent);</script><script>' + (assets / 'channel-section.js').read_text() + '</script>'
source = source.replace('<script>(function offlineApp()', scripts + '<script>(function offlineApp()', 1)
source = source.replace("    }).join('');\n  }\n  $('filter')", "    }).join('');\n    window.renderChannelSection($('product').value || codes[0]);\n  }\n  $('filter')", 1)
view_js = '''
  function setDataView(view) {
    const channels = view === 'channels';
    $('channel-block').hidden = !channels;
    $('charts').hidden = channels;
    $('tables').hidden = channels;
    $('cores').hidden = channels;
    $('single').hidden = channels;
    $('view-channels').classList.toggle('active',channels);
    $('view-trends').classList.toggle('active',!channels);
    $('view-channels').setAttribute('aria-pressed',String(channels));
    $('view-trends').setAttribute('aria-pressed',String(!channels));
  }
  $('view-channels').addEventListener('click',()=>setDataView('channels'));
  $('view-trends').addEventListener('click',()=>setDataView('trends'));
  setDataView('channels');
'''
source = source.replace('  window.trendPreview=', view_js + '  window.trendPreview=', 1)
source = source.replace('得物商品近7天按日趋势，查看访客、支付订单、收藏人数、收藏率与转化率。', '得物商品逐日趋势与单品渠道来源，查看搜索、推荐、引力等流量的增加、减少与抵消。', 1)
source = source.replace('默认两核心款对照', '默认查看流量来源', 1)
source = source.replace('const width=620,height=260,left=52,right=22,top=25,bottom=44,plotW=width-left-right,plotH=height-top-bottom;', 'const width=620,height=300,left=96,right=62,top=40,bottom=72,plotW=width-left-right,plotH=height-top-bottom;', 1)
source = source.replace("Math.max(12,y(v)-10)", "Math.max(26,y(v)-12)", 1)
source = source.replace("(height-17)+'\" text-anchor=\"middle\" class=\"axis\"", "(height-37)+'\" text-anchor=\"middle\" class=\"axis\"", 1)
source = source.replace("(height-3)+'\" text-anchor=\"middle\" class=\"missing\"", "(height-7)+'\" text-anchor=\"middle\" class=\"missing\"", 1)
source = source.replace('每项指标独立纵轴；核心两款对照时，同一指标使用相同尺度。缺失显示断点，真实0保留。', '关注近7天有销量、有收藏或后台标记为新品的商品；老款销量和收藏均为0则排除。新品暂无数据也保留。各指标独立纵轴，缺失断线、真实0保留。核心两款的同一经营指标使用相同尺度。', 1)
source = source.replace('与上方商品访客 UV 是不同指标', '与经营趋势中的商品访客 UV 是不同指标')
source = source.replace('<span>46款商品</span>',f'<span>关注{len(eligible)}款 · 排除{len(metrics["rows"])-len(eligible)}款无销量无收藏老款</span>',1)
source = source.replace('已采集 322/322 条逐日记录',f'已采集 {trend["observedCount"]}/{trend["expectedCount"]} 条逐日记录',1)
source = source.replace('全部46款',f'全部{len(eligible)}款重点商品',1)
source = source.replace('42款零销量并列第5；', '近7天销量和收藏均为0的老款不进入本次关注范围；新品即使为0也保留。',1)
assert source.count('id="channel-section"') == 1
assert 'window.renderChannelSection' in source
site.write_text(source)
(base / 'outputs/2026-10-08/近7天商品趋势.html').write_text(source)
print({'bytes':len(source.encode()),'source_products':observed})
