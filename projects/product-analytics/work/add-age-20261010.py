import csv, json, pathlib, re
from datetime import datetime
from zoneinfo import ZoneInfo

root = pathlib.Path('/Users/nan/Documents/Codex/2026-10-09/zai')
out = root / 'outputs/2026-10-10/age-profile'
dist = root / 'work/dewu-trend-site/dist'
html = (out / '更新前网站.html').read_text()
raw = json.loads((out / '年龄图原始读数.json').read_text())[:15]
raw += [
    dict(code='YX9648001', paid=[0]*5, browse=[0,50,25,25,0], favorite=[0]*5),
    dict(code='YH9380001', paid=[0]*5, browse=[0,66.67,33.33,0,0], favorite=[0,0,100,0,0]),
    dict(code='YX9648002', paid=[0]*5, browse=[0]*5, favorite=[0]*5),
]
core = {'YX9524001','YX9501001','YX9340001','YH9380001'}
collected = datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')
for r in raw:
    r.update(start='2026-10-03',end='2026-10-09',collected_date='2026-10-10',
             source='核心指标底部年龄分布' if r['code'] in core else '成交分析底部年龄分布')
(out / '年龄图原始读数.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2))

def embedded(name):
    return json.loads(re.search(r'<script[^>]*id="'+name+r'"[^>]*>(.*?)</script>', html, re.S).group(1))
def replace_embedded(name, data):
    global html
    html=re.sub(r'(<script[^>]*id="'+name+r'"[^>]*>).*?(</script>)',lambda m:m[1]+json.dumps(data,ensure_ascii=False)+m[2],html,flags=re.S)
def save_json(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2))

products=embedded('trend-data')['products']
official=json.loads((root/'outputs/2026-10-10/daily-1130/2026-10-03_10-09_商品官方导出.json').read_text())
labels=['0–18岁','18–25岁','26–35岁','36–45岁','其他']
fields={'paid':'支付用户数','browse':'商详访问人数','favorite':'收藏用户数'}
cohort_names={'paid':'支付用户','browse':'浏览用户','favorite':'收藏用户'}
assert len(raw)==18 and {r['code'] for r in raw}=={p['code'] for p in products}
rows=[]
for r in raw:
    p=next(p for p in products if p['code']==r['code'])
    matches=[b for b in official if b['商品货号']==r['code'] and b['SPUID']==p['spuId']]
    assert len(matches)==1
    b=matches[0]
    assert b['类目名称'].startswith('流行饰品/眼镜/服配-')
    cohorts={}
    for key,field in fields.items():
        count=int(b[field]); values=r[key]
        assert len(values)==5 and all(0<=v<=100 for v in values)
        assert (count==0 and sum(values)==0) or (count>0 and abs(sum(values)-100)<.03)
        cohorts[key]={'label':cohort_names[key], 'totalUsers':count,'totalSourceField':field,
                      'status':'no_users' if count==0 else 'observed',
                      'sharesPct':values,'ageCounts':None,'rawShareSumPct':round(sum(values),2)}
    assert cohorts['browse']['totalUsers']==p['weekUv']
    assert cohorts['favorite']['totalUsers']==p['weekFavorites']
    rows.append({'code':r['code'],'spuId':p['spuId'],'name':p['name'],'category':b['类目名称'],
                 'start':r['start'],'end':r['end'],'source':r['source'],'cohorts':cohorts})
data={'schemaVersion':1,'period':{'start':'2026-10-03','end':'2026-10-09'},
      'collectedDate':'2026-10-10','compiledAt':collected,'ageGroups':labels,'products':rows,
      'coverage':{'focusProducts':18,'observedProducts':18,'cohorts':54,'rawPercentValues':270},
      'notes':['年龄占比来自各商品近7天界面图例；同期用户总数来自同区间官方商品导出，支付人数不等于支付订单数。',
               '保留后台年龄分组及四舍五入后的占比，不改平合计、不反推分年龄人数。',
               '其他的年龄定义未取得；0–18岁与18–25岁的边界沿用后台原文，不自行重新分组。',
               '本期无用户时原图图例全为0，日报标注无用户并不绘制分布。缺失另行标记。',
               '这是区间快照，未采集历史年龄结构，不代表每日趋势；年龄占比差异不是年龄转化率。',
               '所有产品已逐款精确核对货号和类目，并用货号加SPU关联官方导出。']}
save_json(out/'单品年龄画像底表.json',data)
save_json(dist/'age-profiles.json',data)
with (out/'单品年龄画像底表.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f);writer.writerow(['货号','SPU','商品','开始日期','结束日期','人群','同期后台用户数','年龄分组','后台原始占比百分数','状态','来源'])
    for p in rows:
        for c in p['cohorts'].values():
            for label,v in zip(labels,c['sharesPct']):
                writer.writerow([p['code'],p['spuId'],p['name'],p['start'],p['end'],c['label'],c['totalUsers'],label,v,c['status'],p['source']])
(dist/'age-profiles.csv').write_bytes((out/'单品年龄画像底表.csv').read_bytes())

# Correct a disproved entry-availability claim without inventing missing history.
channels=embedded('channel-data')
p=channels['products']['YX9341001']
p.update(source_status='history_pending',source_note='2026-10-10按精确货号YX9341001复核，存在流量分析和成交分析入口；不能选为同前缀YX9341001D。渠道历史日值尚未补采，原“无入口”判断撤回。',verified_date='2026-10-10',verified_period={'start':'2026-10-03','end':'2026-10-09','preset':'近7天'},source='observed_backend_ui')
channels['coverage']['source_status_counts']={'observed':13,'not_exposed_in_backend':4,'history_pending':1}
channels['coverage']['source_not_exposed_codes']=[c for c in channels['coverage']['source_not_exposed_codes'] if c!='YX9341001']
channels['coverage']['source_history_pending_codes']=['YX9341001']
channels['notes'][1]='4款核心指标页未见渠道入口；YX9341001于10/10复核有流量入口，历史待补采。经营日值继续保留。'
replace_embedded('channel-data',channels);save_json(dist/'channel-readings.json',channels)
comparison=embedded('comparison-data')
comparison['gaps']['channel_day_baseline']='13款一级渠道连续两周完整；4款未见渠道入口；YX9341001于10/10复核有入口，历史待补采。部分二级历史日值未取得，付费主力3款周区间已实采。'
comparison['coverage']['channel_unavailable_products']=[c for c in comparison['coverage']['channel_unavailable_products'] if c!='YX9341001']
comparison['coverage']['channel_history_pending_products']=['YX9341001']
comparison['coverage']['age_profile']=data['coverage']|data['period']
replace_embedded('comparison-data',comparison);save_json(dist/'weekly-comparisons.json',comparison)
coverage=json.loads((dist/'coverage.json').read_text())
coverage.update(comparison['coverage']);coverage['gaps']=comparison['gaps'];save_json(dist/'coverage.json',coverage)
save_json(out/'覆盖与核验.json',coverage)

css='''
.view-switch{flex-wrap:wrap}.age-section{margin-top:20px}.age-heading{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:18px;flex-wrap:wrap}.age-heading h2{margin:0;font-size:24px}.age-heading p{margin:5px 0;color:#607684}.age-period{background:#e8eef2;padding:9px 12px;border-radius:6px;font-size:14px}.age-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.age-card{padding:20px;background:#fff;border:1px solid #dfe6eb;border-radius:9px}.age-card h3{font-size:17px;margin:0}.age-total{margin:9px 0 3px;font-size:30px;font-weight:650;font-variant-numeric:tabular-nums}.age-total small{font-size:14px;font-weight:400;margin-left:6px}.age-caption{font-size:12px;color:#607684;margin:0 0 16px}.age-bar{display:grid;grid-template-columns:66px minmax(40px,1fr) 66px;gap:9px;align-items:center;margin:17px 0;font-size:14px}.age-track{height:13px;background:#edf1f4;border-radius:3px;overflow:hidden}.age-fill{display:block;height:100%;border-radius:3px;background:#2476a8}.age-percent{text-align:right;font-weight:600;font-variant-numeric:tabular-nums}.age-main{font-size:14px;border-top:1px solid #edf1f4;padding-top:14px;margin:18px 0 0}.age-sample{font-size:12px;background:#fff3da;color:#745318;border-radius:5px;padding:8px 10px;margin-top:10px}.age-empty{min-height:205px;display:flex;align-items:center;justify-content:center;text-align:center;background:#f4f7f9;border-radius:5px;color:#71838d;flex-direction:column;padding:15px;gap:5px}.age-notes{font-size:13px;color:#607684;line-height:1.8;margin-top:16px}.age-detail{margin-top:17px;padding:18px}.age-detail summary{cursor:pointer;font-weight:600}.age-detail table{margin-top:12px}.age-overview{padding:13px 16px;background:#e8eef2;border-radius:6px;margin:0 0 16px;font-size:14px}.age-source{font-size:12px;color:#6b7e89;margin-top:7px}@media(max-width:900px){.age-grid{grid-template-columns:1fr}.age-card{padding:18px}.age-empty{min-height:100px}}'''
html=html.replace('</style>',css+'</style>')
html=html.replace('经营 / 来源 / 引力三视图','经营 / 来源 / 引力 / 年龄画像')
html=html.replace('<button id="view-gravity" aria-pressed="false">引力与内容</button>','<button id="view-gravity" aria-pressed="false">引力与内容</button><button id="view-age" aria-pressed="false">年龄画像</button>')
html=html.replace('5款后台无来源入口。','4款未见来源入口，福禄葫芦已复核有入口、历史待补采。年龄画像18款已齐。')
html=html.replace('5款后台无来源入口（10/09逐款核验）','4款未见来源入口；福禄葫芦10/10复核有入口、历史待补采')
html=html.replace('<section id="charts"','<section id="age-section" class="age-section" aria-label="单品年龄画像" hidden></section><section id="charts"',1)
html=html.replace('<footer>','<footer><p>年龄画像：<a href="age-profiles.csv" download>18款年龄分布CSV</a> · <a href="age-profiles.json" download>年龄画像完整底表JSON</a> · 区间10/03—10/09，采集于10/10</p>',1)
age_script=(root/'work/age-view.js').read_text()
html=html.replace('<script>(function offlineApp()', '<script id="age-data" type="application/json">'+json.dumps(data,ensure_ascii=False)+'</script><script>'+age_script+'</script><script>(function offlineApp()',1)
html=html.replace("window.renderGravitySection($('product').value || codes[0]);", "window.renderGravitySection($('product').value || codes[0]);\n    window.renderAgeSection($('product').value || codes[0]);")
html=html.replace("gravity=view==='gravity',business=view==='trends';", "gravity=view==='gravity',business=view==='trends',age=view==='age';")
html=html.replace("$('gravity-section').hidden=!gravity;", "$('gravity-section').hidden=!gravity;\n    $('age-section').hidden=!age;")
html=html.replace("['channels','trends','gravity'].forEach", "['channels','trends','gravity','age'].forEach")
html=html.replace('if(gravity)window.renderGravitySection(code);','if(gravity)window.renderGravitySection(code);\n    if(age)window.renderAgeSection(code);')
html=html.replace("  setDataView('trends');", "  $('view-age').addEventListener('click',()=>setDataView('age'));\n  setDataView('trends');")
(dist/'index.html').write_text(html)
(out/'已发布页面候选.html').write_text(html)
print(json.dumps({'products':len(rows),'cohorts':len(rows)*3,'percent_values':len(rows)*15,'period':data['period'],'totals':[(p['code'],{k:c['totalUsers'] for k,c in p['cohorts'].items()}) for p in rows]},ensure_ascii=False))
