from pathlib import Path
import json,re,datetime

base=Path(__file__).resolve().parent.parent
source=(base/'work/trend-site-before-weekly.html').read_text()
trend=json.loads(re.search(r'<script id="trend-data" type="application/json">(.*?)</script>',source,re.S)[1])
channel_match=re.search(r'<script id="channel-data" type="application/json">(.*?)</script>',source,re.S)
channels=json.loads(channel_match[1])
eligible={p['code'] for p in trend['products']}
raw_prior=json.loads((base/'work/prior-week-business-read.json').read_text())
current=json.loads((base/'work/retry_metrics.json').read_text())
periods=[]
for code,amount,conversion,orders,uv,favorites in raw_prior['rows']:
    if code in eligible:
        periods.append(dict(code=code,start=raw_prior['start'],end=raw_prior['end'],amount=amount,conversionPct=conversion,orders=orders,uv=uv,favorites=favorites,source='商家后台 商品分析 指定区间原值',collected_at=raw_prior['collected_at']))
for r in current['rows']:
    if r[0] in eligible:
        m=r[4]
        periods.append(dict(code=r[0],start=current['week_start'],end=current['week_end'],amount=m[0],conversionPct=m[3],orders=m[4],uv=m[6],favorites=m[7],source='2026-10-09已采后台近7天区间原值'))
assert len(periods)==len(eligible)*2
core_oct1=dict(total=723,values=dict(competition=102,recommend=12,search=90,paid=494,push=1,gravity=493,activity=1,content=53,users=64,other=9),observed=True,primary_complete=True,primary_sum=723,primary_sum_matches_total=True,source={'kind':'observed_ui_raw_json','description':'2026-10-10商家后台YX9354001单品分析，所选日期2026-10-01至2026-10-01','collected_at':raw_prior['collected_at']})
assert sum(core_oct1['values'][k] for k in ['competition','paid','activity','content','users','other'])==core_oct1['total']
channels['products']['YX9354001']['days']['2026-10-01']=core_oct1
snapshots=[dict(code='YX9638001',task_id='S17905606054010918',content_id='535391676',title='布契拉提暂时买不起🥹买布契拉提拉丝🌼总可以叭！',published_at='2026-10-09 20:42:38',association_evidence='引力任务详情标题含货号YX9638001，任务详情关联内容ID535391676',exposure=0,reads=0,interactions=0,detail_visits=0,cooperation_fee=107,metric_scope='任务详情累计快照，后台未显示此模块单独更新时间',collected_at='2026-10-10 09时（界面采集）',limit='只有一次累计快照，不能判断当日增量或画内容日趋势；数据中心更新时间为10/09 07:38，早于此内容发布时间。实际广告消耗、归因窗口及日明细尚未取得。')]
data={'report_end':trend['dates'][-1],'category':'流行饰品/眼镜/服配','businessPeriods':periods,'businessDays':[],'channelPeriods':[],'gravity':{'snapshots':snapshots,'daily':[]},'gaps':{'business_day_baseline':'09/25—10/01经营日值尚未完成补采；指定10/01后页面持续加载，未把未刷新的周表当日值。','channel_day_baseline':'已实采YX9354001的10/01；其他历史渠道日值尚未取得。','gravity':'当月/当年累计报表可见，实际广告消耗与内容逐日增量未取得。'}}
out=base/'outputs/2026-10-10'
(out/'周对比与引力整理数据.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
(out/'前周经营原始读数.json').write_text(json.dumps(raw_prior,ensure_ascii=False,indent=2))
(out/'YX9354001_2026-10-01_渠道原始读数.json').write_text(json.dumps(core_oct1,ensure_ascii=False,indent=2))
(out/'引力内容原始核验.json').write_text(json.dumps({'source':'https://gravity.dewu.com/task/detail/taskDetail/S17905606054010918','snapshots':snapshots,'notes':['数据中心同一任务行金额100元，任务详情合作费用107元；各自口径不同，不当作广告实际消耗。','引力我的流量页所见0为流量券曝光额度余额，不是广告消耗或投放曝光。']},ensure_ascii=False,indent=2))
(base/'work/dewu-trend-site/dist/weekly-comparisons.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
(base/'work/dewu-trend-site/dist/daily-readings.json').write_text(json.dumps(trend,ensure_ascii=False,indent=2))
(base/'work/dewu-trend-site/dist/channel-readings.json').write_text(json.dumps(channels,ensure_ascii=False,indent=2))
def inline(obj):return json.dumps(obj,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
source=source[:channel_match.start(1)]+inline(channels)+source[channel_match.end(1):]
source=source.replace('</style>',(base/'work/comparison-component/comparison.css').read_text()+'</style>',1)
source=source.replace('<button id="view-trends" aria-pressed="false">经营趋势</button>','<button id="view-trends" aria-pressed="false">经营趋势</button><button id="view-gravity" aria-pressed="false">引力与内容</button>',1)
source=source.replace('<section id="charts"','<section id="business-comparison" class="panel business-comparison"></section><section id="gravity-section" class="gravity-section" hidden></section><section id="charts"',1)
module='<script id="comparison-data" type="application/json">'+inline(data)+'</script><script>'+(base/'work/comparison-component/comparison.js').read_text()+'</script>'
source=source.replace('<script>(function installChannelSection',module+'<script>(function installChannelSection',1)
# The shared comparison engine uses actual backend periods for people/rates and only complete daily values for additive PV.
start=source.index('    const lastObserved=',source.index('function renderChannelSection'))
end=source.index('    const currentTotal=',start)
source=source[:start]+'''    const math=global.ComparisonMath, range=math.pair(math.state.date,math.state.mode);
    const state={current:math.rangeLabel(range.a),previous:math.rangeLabel(range.b)};
    const current=math.channelPeriod(code,range.a),previous=math.channelPeriod(code,range.b);
'''+source[end:]
start=source.index('    const options=',source.index('function renderChannelSection'))
end=source.index('    let summary=',start)
source=source[:start]+"    const controls='<div class=\"channel-controls\">'+math.controls('channel')+'</div>';\n"+source[end:]
start=source.index("    document.getElementById('channel-current-date')",source.index('function renderChannelSection'))
end=source.index('\n  }',start)
source=source[:start]+"    math.bind(mount,'channel',()=>renderChannelSection(code));"+source[end:]
source=source.replace('查看日 PV','本期 PV').replace('对比日 PV','对比期 PV').replace('查看日全部 PV','本期全部 PV')
source=source.replace('计算涨跌仅使用所选双日实采值，不反推历史值。','日对比使用所选日期实采值；周对比只加总完整7天PV或使用后台同区间原值，不反推历史值。')
source=source.replace('所选两日总 PV 尚未全部采集，暂不计算总增减。','所选期间总PV未全部采集，暂不计算总增减；历史缺失不会填0。')
source=source.replace('双日','双期').replace('两个日期均已采集','两个期间均已采集').replace('两个日期的实采渠道 PV','两个期间的实采渠道 PV')
source=source.replace("  let mode='cores';","  let mode='single';",1)
source=source.replace("    window.renderChannelSection($('product').value || codes[0]);","    window.renderChannelSection($('product').value || codes[0]);\n    window.renderBusinessComparison($('product').value || codes[0]);\n    window.renderGravitySection($('product').value || codes[0]);",1)
start=source.index('  function setDataView(view)')
end=source.index('  window.trendPreview=',start)
source=source[:start]+'''  function setDataView(view) {
    const channels=view==='channels', gravity=view==='gravity',business=view==='trends';
    $('channel-block').hidden=!channels;
    $('business-comparison').hidden=!business;
    $('gravity-section').hidden=!gravity;
    ['charts','tables','cores','single'].forEach(id=>$(id).hidden=!business);
    ['channels','trends','gravity'].forEach(key=>{
      $('view-'+key).classList.toggle('active',view===key);
      $('view-'+key).setAttribute('aria-pressed',String(view===key));
    });
    const code=$('product').value;
    if(channels)window.renderChannelSection(code);
    if(business)window.renderBusinessComparison(code);
    if(gravity)window.renderGravitySection(code);
  }
  $('view-channels').addEventListener('click',()=>setDataView('channels'));
  $('view-trends').addEventListener('click',()=>setDataView('trends'));
  $('view-gravity').addEventListener('click',()=>setDataView('gravity'));
  setDataView('trends');
'''+source[end:]
source=source.replace('默认查看流量来源','经营 / 来源 / 引力三视图',1)
source=source.replace('来源已采 12/18 款','来源已采 12/18 款',1)
source=source.replace('<p class="notice">','<p class="notice">经营与渠道均支持日环比、上周同日、周环比。经营两周区间18款已齐；上周经营日值仍待补采。引力内容累计快照补充至10/09，逐日消耗、阅读、互动未取得。<br>',1)
source=source.replace('查看搜索、推荐、引力等流量的增加、减少与抵消。','查看经营和渠道的日环比、上周同日、周环比及引力内容核验。',1)
source=source.replace('<footer>','<footer><p>底表下载：<a href="weekly-comparisons.json" download>经营周对比与引力核验</a> · <a href="daily-readings.json" download>18款经营逐日底表</a> · <a href="channel-readings.json" download>单品渠道逐日底表</a>（JSON）</p>',1)
(base/'work/dewu-trend-site/dist/index.html').write_text(source)
(out/'商品经营与来源周对比.html').write_text(source)
(base/'outputs/2026-10-08/近7天商品趋势.html').write_text(source)
print({'site_bytes':len(source.encode()),'periods':len(periods),'focus_products':len(eligible),'channel_extra_day':1,'gravity_verified_contents':len(snapshots)})
