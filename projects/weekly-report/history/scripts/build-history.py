#!/usr/bin/env python3
"""Build the public weekly archive without external dependencies or private inputs."""
import argparse
import json
import re
import shutil
from datetime import date, timedelta
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, default=ROOT / 'weekly-archive')
parser.add_argument('--output', type=Path, default=ROOT / 'dist')
args = parser.parse_args()
source, output = args.source.resolve(), args.output.resolve()
data = json.loads((source / 'weeks.json').read_text())
weeks = sorted(data['weeks'], key=lambda w: w['start'])
assert len({w['id'] for w in weeks}) == len(weeks)

def label(w):
    return f"{w['start'].replace('-', '.')} — {w['end'][5:].replace('-', '.')}"

def num(value, money=False, decimals=0):
    return '—' if value is None else ('¥' if money else '') + f'{value:,.{decimals}f}'

def panel(current, prefix):
    route = lambda w: f"{prefix}reports/{w['id']}/"
    current_index = weeks.index(current)
    available = {w['start']: w for w in weeks}
    options = []
    day = date.fromisoformat(weeks[-1]['start'])
    while day >= date.fromisoformat(weeks[0]['start']):
        w = available.get(day.isoformat())
        if w:
            selected = ' selected' if w == current else ''
            options.append(f'<option value="{route(w)}"{selected}>{label(w)} · W{w["week"]}</option>')
        else:
            end = day + timedelta(days=6)
            options.append(f'<option disabled>{day:%Y.%m.%d} — {end:%m.%d} · 暂无归档</option>')
        day -= timedelta(days=7)
    def nav(index, text):
        return f'<a href="{route(weeks[index])}">{text}</a>' if 0 <= index < len(weeks) else f'<span class="history-disabled" aria-disabled="true">{text}</span>'
    rows, content_rows = [], []
    for w in reversed(weeks):
        active = ' aria-current="true"' if w == current else ''
        first = f'<td><a href="{route(w)}">{label(w)}</a><small>查询快照 {w["snapshot"]}</small></td>'
        rows.append(f'<tr{active}>{first}<td>{num(w["raw"], True)}</td><td>{num(w["orders"])}</td><td><strong>{num(w["effective"], True)}</strong><small>{escape(w["basis"])}</small></td><td>{num(w["pending"], True)}</td><td>{num(w["adSpend"], True, 2)}</td><td>{num(w["discountRoi"], decimals=2)}</td></tr>')
        content_rows.append(f'<tr{active}>{first}<td>{num(w["visitors"])}</td><td>{num(w["exposure"])}</td><td>{num(w["reads"])}</td><td>{num(w["productVisits"])}</td><td>{num(w["created"])}</td><td>{num(w["accepted"])}</td></tr>')
    return f'''<section id="weekly-history" class="weekly-history" aria-labelledby="history-title">
<div class="history-heading"><div><h2 id="history-title">按周查看</h2><p>切换周次，查看当周完整经营报告</p></div><span class="history-count">已归档 {len(weeks)} 期</span></div>
<div class="history-controls"><div class="history-field"><label for="history-week-select">报告周次 · 周一至周日</label><select id="history-week-select">{''.join(options)}</select></div>{nav(current_index-1, '← 较早一期')}{nav(current_index+1, '较新一期 →')}<a class="history-share" href="{route(current)}">本期固定链接 ↗</a></div>
<p class="history-context"><strong>当前：{label(current)}</strong> · 查询快照 {current['snapshot']}。历史数据保留当期口径；后续退款与归因结果可能变化。</p>
<details class="history-compare"><summary>查看历史周数据对照 · {len(weeks)} 期</summary>
<h3>销售与得物推</h3><div class="history-scroll" tabindex="0" role="region" aria-label="历史销售与得物推，窄屏可左右滚动"><table class="history-table"><thead><tr><th scope="col">报告周次 / 查询日期</th><th scope="col">原始优惠后支付</th><th scope="col">支付订单</th><th scope="col">剔除关闭后销售参考</th><th scope="col">售后中金额</th><th scope="col">得物推消耗</th><th scope="col">优惠后引导支付 ROI</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="history-note">销售参考不是净利润。9月7—13日仅剔除2笔已知关闭订单；9月21—27日与10月5—11日按订单及售后核对，销售参考仍含售后中金额。早期未采集优惠后 ROI，显示“—”，不以原始引导支付 ROI 替代。</p>
<h3>流量与引力投放</h3><div class="history-scroll" tabindex="0" role="region" aria-label="历史流量与引力，窄屏可左右滚动"><table class="history-table"><thead><tr><th scope="col">报告周次 / 查询日期</th><th scope="col">商详访客 UV</th><th scope="col">引力周曝光</th><th scope="col">引力周阅读</th><th scope="col">引力商详访问</th><th scope="col">本周新建任务</th><th scope="col">本周验收内容</th></tr></thead><tbody>{''.join(content_rows)}</tbody></table></div>
<p class="history-note">“—”表示未采集或未完整核验，不等于0。9月14—20日、9月28日—10月4日暂无周报归档。引力待验收为查询时点存量，详见各期正文；不作为周末历史存量横向比较。</p>
</details><noscript><p class="history-note">浏览器未启用 JavaScript，可展开历史对照，点击报告周次切换。</p></noscript></section>'''

def render(w, dest, prefix):
    src = source / 'pages' / w['id']
    html = (src / 'index.html').read_text()
    assert 'id="weekly-history"' not in html
    hero = re.search(r'<(?:header|div)\b[^>]*class="hero"[^>]*>', html)
    if not hero:
        raise ValueError(f'Missing report hero: {w["id"]}')
    html = html[:hero.start()] + panel(w, prefix) + html[hero.start():]
    html = html.replace('</head>', f'<link rel="stylesheet" href="{prefix}history-assets/history.css">\n</head>', 1)
    html = html.replace('</body>', f'<script src="{prefix}history-assets/history.js" defer></script>\n</body>', 1)
    html = re.sub(r'<title>.*?</title>', f'<title>戴拉得物周报 · {label(w)} · 历史周次</title>', html, count=1)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / 'index.html').write_text(html)
    for asset in src.iterdir():
        if asset.name == 'index.html':
            continue
        if asset.is_dir():
            shutil.copytree(asset, dest / asset.name, dirs_exist_ok=True)
        else:
            shutil.copy2(asset, dest / asset.name)

output.mkdir(parents=True, exist_ok=True)
shutil.copytree(source / 'ui', output / 'history-assets', dirs_exist_ok=True)
for w in weeks:
    render(w, output / 'reports' / w['id'], '../../')
render(weeks[-1], output, '')
print(f'Built {len(weeks)} historical reports; latest {weeks[-1]["id"]}; output {output}')
