(function (global) {
  'use strict';
  const data = JSON.parse(document.getElementById('comparison-data').textContent);
  const trends = JSON.parse(document.getElementById('trend-data').textContent);
  const dayMap = new Map([...trends.records,...(data.businessDays || [])].map(r=>[r.code+'|'+r.date,r]));
  const state = {date:trends.dates.at(-1),mode:'day'};
  const valid = x=>typeof x==='number' && Number.isFinite(x) && x>=0 ? x : null;
  const escape = x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = x=>x==null?'待补采':Number(x).toLocaleString('zh-CN',{maximumFractionDigits:2});
  const signed = x=>x==null?'—':(x>0?'+':x<0?'−':'')+fmt(Math.abs(x));
  function shift(date,n) {const d=new Date(date+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+n);return d.toISOString().slice(0,10);}
  const weekday = date=>'周'+'日一二三四五六'[new Date(date+'T00:00:00Z').getUTCDay()];
  const dateLabel = date=>date+' '+weekday(date);
  const days = (start,end)=>{const out=[];for(let d=start;d<=end;d=shift(d,1))out.push(d);return out;};
  function pair(date,mode) {
    return mode==='week'?{a:[shift(date,-6),date],b:[shift(date,-13),shift(date,-7)]}:
      {a:[date,date],b:[shift(date,mode==='weekday'?-7:-1),shift(date,mode==='weekday'?-7:-1)]};
  }
  const rangeLabel = range=>range[0]===range[1]?dateLabel(range[0]):range[0]+' 至 '+range[1];
  function compare(a,b) {a=valid(a);b=valid(b);return {a,b,delta:a!=null&&b!=null?a-b:null,pct:a!=null&&b>0?(a-b)/b*100:null};}
  function business(code,range) {
    let r;
    if(range[0]===range[1]) r=dayMap.get(code+'|'+range[0]);
    else r=data.businessPeriods?.find(r=>r.code===code&&r.start===range[0]&&r.end===range[1]);
    const result={};
    for(const key of ['uv','orders','favorites','conversionPct','amount']) result[key]=valid(r?.[key]);
    if(range[0]!==range[1] && result.orders==null) {
      const readings=days(...range).map(date=>valid(dayMap.get(code+'|'+date)?.orders));
      if(readings.every(v=>v!=null))result.orders=readings.reduce((a,b)=>a+b,0);
    }
    result.favoriteRate=result.uv>0&&result.favorites!=null?result.favorites/result.uv*100:null;
    return result;
  }
  function channelPeriod(code,range) {
    const explicit=data.channelPeriods?.find(r=>r.code===code&&r.start===range[0]&&r.end===range[1]);
    if(explicit)return explicit;
    const p=global.CHANNEL_DATA.products[code], records=days(...range).map(date=>p?.days?.[date]);
    const result={total:null,values:{},days:records.filter(r=>valid(r?.total)!=null).length,expected:records.length};
    for(const key of ['total',...global.CHANNEL_DATA.channels.map(c=>c.id)]) {
      const vals=records.map(r=>valid(key==='total'?r?.total:r?.values?.[key]));
      const value=vals.every(v=>v!=null)?vals.reduce((a,b)=>a+b,0):null;
      if(key==='total')result.total=value;else result.values[key]=value;
    }
    return result;
  }
  const metrics=[['uv','商详访客 UV','人'],['orders','支付订单数','单'],['favorites','收藏用户数','人'],['favoriteRate','收藏率','%'],['conversionPct','商详转化率（后台）','%']];
  function controls(prefix) {
    return '<div class="compare-controls"><label>查看日 <select id="'+prefix+'-date">'+(state.mode==='week'?[trends.dates.at(-1)]:trends.dates).map(d=>'<option value="'+d+'"'+(d===state.date?' selected':'')+'>'+dateLabel(d)+'</option>').join('')+'</select></label><div class="compare-modes" role="group" aria-label="对比口径">'+[['day','日环比'],['weekday','上周同日'],['week','周环比']].map(([key,label])=>'<button data-compare-mode="'+key+'" aria-pressed="'+(state.mode===key)+'" class="'+(state.mode===key?'active':'')+'">'+label+'</button>').join('')+'</div></div>';
  }
  function bind(mount,prefix,render) {
    document.getElementById(prefix+'-date').addEventListener('change',e=>{state.date=e.target.value;render();});
    mount.querySelectorAll('[data-compare-mode]').forEach(b=>b.addEventListener('click',()=>{state.mode=b.dataset.compareMode;if(state.mode==='week')state.date=trends.dates.at(-1);render();}));
  }
  function comparisonTable(rows,range) {
    return '<div class="table-scroll"><table class="comparison-table"><thead><tr><th>指标</th><th>本期<br><small>'+rangeLabel(range.a)+'</small></th><th>对比期<br><small>'+rangeLabel(range.b)+'</small></th><th>增减</th><th>涨跌幅</th></tr></thead><tbody>'+rows.map(([label,unit,a,b])=>{
      const c=compare(a,b);const rate=unit==='%';
      return '<tr><td>'+escape(label)+'</td><td>'+fmt(c.a)+(c.a==null?'':unit)+'</td><td>'+fmt(c.b)+(c.b==null?'':unit)+'</td><td class="'+(c.delta<0?'down':c.delta>0?'up':'')+'">'+signed(c.delta)+(c.delta==null?'':rate?' 个百分点':unit)+'</td><td>'+(c.pct==null?(c.b===0?'基数为0':'—'):signed(c.pct)+'%')+'</td></tr>';
    }).join('')+'</tbody></table></div>';
  }
  function renderBusiness(code) {
    const mount=document.getElementById('business-comparison');if(!mount)return;
    const p=trends.products.find(p=>p.code===code),range=pair(state.date,state.mode),a=business(code,range.a),b=business(code,range.b);
    const missing=metrics.filter(([key])=>a[key]==null||b[key]==null).map(([,label])=>label);
    mount.innerHTML='<div class="compare-heading"><div><h2>经营数据对比</h2><p>'+escape(p.name+' · '+code)+'</p></div>'+controls('business')+'</div>'+comparisonTable(metrics.map(([key,label,unit])=>[label,unit,a[key],b[key]]),range)+
      '<p class="compare-note">'+(state.mode==='week'?'周访客、收藏人数与转化率使用后台对应7天区间值；收藏率=区间收藏人数÷区间访客。':'上周同日按日期减7天匹配相同星期几，例如周一对周一。')+' 比率同时展示百分点与相对涨跌；0基数不计算百分比。</p>'+
      (missing.length?'<p class="compare-gap">所选期间待补采：'+missing.join('、')+'。本页已有09/25—10/08完整经营日值及对应两周后台区间值。</p>':'')+
      '<p class="compare-note">同星期几不代表同样的工作日或节假日条件，价格、库存、优惠及活动历史仍需单独核实。</p>';
    bind(mount,'business',()=>renderBusiness(code));
  }
  function lineChart(title,dates,values,unit) {
    const W=620,H=300,L=75,R=35,T=35,B=60,known=values.filter(v=>v!=null),max=Math.max(4,...known)*1.15;
    const x=i=>L+i*(W-L-R)/Math.max(1,dates.length-1),y=v=>H-B-v/max*(H-T-B);
    const out=['<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+escape(title)+'逐日趋势">'];
    for(let i=0;i<=4;i++){const v=max*i/4,yy=y(v);out.push('<line x1="'+L+'" y1="'+yy+'" x2="'+(W-R)+'" y2="'+yy+'" stroke="#e2e7eb"/><text x="'+(L-10)+'" y="'+(yy+5)+'" text-anchor="end" class="axis">'+fmt(v)+'</text>');}
    let segment=[];const flush=()=>{if(segment.length>1)out.push('<polyline points="'+segment.join(' ')+'" fill="none" stroke="#2476A8" stroke-width="3"/>');segment=[];};
    values.forEach((v,i)=>{if(v==null)flush();else segment.push(x(i)+','+y(v));});flush();
    const tick=Math.ceil(dates.length/7);
    values.forEach((v,i)=>{if(i%tick===0||i===dates.length-1)out.push('<text x="'+x(i)+'" y="'+(H-25)+'" text-anchor="middle" class="axis">'+dates[i].slice(5).replace('-','/')+'</text>');if(v!=null){out.push('<circle cx="'+x(i)+'" cy="'+y(v)+'" r="4" fill="#2476A8"><title>'+dates[i]+' '+escape(title)+' '+fmt(v)+unit+'</title></circle>');if(dates.length<=9)out.push('<text x="'+x(i)+'" y="'+Math.max(20,y(v)-12)+'" text-anchor="middle" class="point">'+fmt(v)+'</text>');}});
    if(!known.length)out.push('<text x="310" y="150" text-anchor="middle" class="missing">该期间没有可用的逐日值</text>');
    return out.join('')+'</svg>';
  }
  const contentMetrics=[['exposure','曝光','次'],['reads','阅读','次'],['interactions','互动','次'],['detail_visits','商详访问','次'],['favorites','引导商品收藏','次'],['attributed_orders_14d','14日归因订单','单']];
  function contentPeriod(task,range) {
    const rows=days(...range).map(date=>data.gravity.daily.find(r=>r.task_id===task&&r.date===date)),result={};
    for(const [key] of contentMetrics)result[key]=rows.every(r=>valid(r?.[key])!=null)?rows.reduce((sum,r)=>sum+r[key],0):null;
    return result;
  }
  function contentComparisons(s) {
    return '<details class="content-comparisons"><summary>查看日环比、上周同日和周环比</summary>'+[['day','日环比'],['weekday','上周同日'],['week','周环比']].map(([mode,label])=>{
      const range=pair(data.gravity.window.end,mode),a=contentPeriod(s.task_id,range.a),b=contentPeriod(s.task_id,range.b);
      return '<h4>'+label+'</h4>'+comparisonTable(contentMetrics.map(([key,name,unit])=>[name,unit,a[key],b[key]]),range).replaceAll('待补采','未满区间');
    }).join('')+'<p class="compare-note">内容发布前的日期不补0；发布不足完整7天或对比期未发布时，不计算整周涨跌。14日归因订单保持平台口径。</p></details>';
  }
  function contentCard(s,selectedCode) {
    const rows=data.gravity.daily.filter(r=>r.task_id===s.task_id).sort((a,b)=>a.date.localeCompare(b.date)),ds=rows.map(r=>r.date);
    return '<details class="panel content-detail" id="content-'+escape(s.content_id)+'"'+(s.code===selectedCode?' open':'')+'><summary><span class="content-title">'+escape(s.title)+'</span><span>'+escape(s.creator+' · '+s.product_name+' · '+s.published_at.slice(0,10))+'</span></summary><p>货号 '+escape(s.code)+' · 内容ID '+escape(s.content_id)+' · 发布 '+escape(s.published_at)+' · 数据截至 '+escape(s.data_as_of)+'</p><div class="gravity-snapshot">'+contentMetrics.map(([key,label,unit])=>'<span>累计'+label+'<strong>'+fmt(s[key])+unit+'</strong></span>').join('')+'</div><p>14日归因GMV ¥'+fmt(s.attributed_gmv_14d)+' · 帮助成交 '+fmt(s.help_orders)+'单 / ¥'+fmt(s.help_gmv)+' · 点击率 '+fmt(s.ctr_pct)+'% · 内容引导商详率 '+fmt(s.detail_lead_rate_pct)+'%</p><p class="compare-note">官方报告子任务金额 ¥'+fmt(s.cooperation_fee)+'；后台商详访问成本 ¥'+fmt(s.backend_visit_cost)+'。这两个字段不作为广告实际消耗。帮助成交与14日归因成交分别保留，不相加。</p>'+(s.notes.some(n=>n.includes('互动'))?'<p class="compare-gap">'+escape(s.notes.find(n=>n.includes('互动')))+'</p>':'')+'<div class="charts content-charts">'+contentMetrics.map(([key,label,unit])=>'<article class="content-chart"><h4>'+label+' <small>'+unit+'</small></h4><p>'+ds.length+'/'+ds.length+'个已发布自然日 · 分天值</p>'+lineChart(label,ds,rows.map(r=>valid(r[key])),unit)+'</article>').join('')+'</div>'+contentComparisons(s)+'<details class="content-daily"><summary>逐日精确读数（'+rows.length+'天）</summary><div class="table-scroll"><table><thead><tr><th>日期</th>'+contentMetrics.map(([,n])=>'<th>'+n+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr><td>'+r.date+'</td>'+contentMetrics.map(([k])=>'<td>'+fmt(r[k])+'</td>').join('')+'</tr>').join('')+'</tbody></table></div></details><details class="content-evidence"><summary>数据来源与时间核验</summary><p>'+escape(s.association_evidence)+'</p><p>任务详情发布时间 '+escape(s.published_at)+'；官方导出发布时间 '+escape(s.export_published_at)+'。两处时间不一致，发布日期及图表以详情为准，导出原值保留在底表。</p></details></details>';
  }
  function renderGravity(code) {
    const mount=document.getElementById('gravity-section');if(!mount)return;
    const p=trends.products.find(p=>p.code===code),g=data.gravity,range=pair(state.date,state.mode),a=channelPeriod(code,range.a),b=channelPeriod(code,range.b),all=g.snapshots;
    const related=all.filter(s=>s.code===code),pv=trends.dates.map(d=>valid(global.CHANNEL_DATA.products[code]?.days?.[d]?.values?.gravity));
    const monthTable='<div class="table-scroll"><table class="month-content-table"><thead><tr><th>内容 / 达人</th><th>商品 / 发布日期</th>'+contentMetrics.map(([,n])=>'<th>累计'+n+'</th>').join('')+'<th>14日归因GMV</th></tr></thead><tbody>'+all.map(s=>'<tr><td><a href="#content-'+escape(s.content_id)+'">'+escape(s.title)+'</a><small>'+escape(s.creator)+' · ID '+escape(s.content_id)+'</small></td><td>'+escape(s.product_name)+'<small>'+escape(s.code)+' · '+s.published_at.slice(0,10)+'</small></td>'+contentMetrics.map(([k])=>'<td>'+fmt(s[k])+'</td>').join('')+'<td>¥'+fmt(s.attributed_gmv_14d)+'</td></tr>').join('')+'</tbody></table></div>';
    mount.innerHTML='<section class="panel gravity-month"><div class="compare-heading"><div><h2>近一个月 · 逐条内容数据</h2><p>'+g.window.start+' 至 '+g.window.end+'发布 · 核验63条任务报告，筛出4条内容，关联3款重点商品</p></div><span class="month-badge">4条内容 / 38条日值</span></div><div class="gravity-snapshot">'+[['内容',all.length,'条'],['累计曝光',all.reduce((n,s)=>n+s.exposure,0),'次'],['累计阅读',all.reduce((n,s)=>n+s.reads,0),'次'],['累计商详访问',all.reduce((n,s)=>n+s.detail_visits,0),'次']].map(([n,v,u])=>'<span>'+n+'<strong>'+fmt(v)+u+'</strong></span>').join('')+'</div>'+monthTable+'<p class="compare-note">以上为每条内容发布后累计表现，各自截止时间见下方；每日曲线只使用已读取的分天值。点击下方内容标题展开六项日趋势和明细。当前商品 '+escape(code)+' 对应 '+related.length+'条近月内容。</p></section>'+all.map(s=>contentCard(s,code)).join('')+'<section class="panel gravity-merchant"><div class="compare-heading"><div><h2>所选商品 · 引力渠道访问</h2><p>'+escape(p.name+' · '+code)+'</p></div>'+controls('gravity')+'</div>'+comparisonTable([['商家后台引力渠道商详访问','PV',a.values?.gravity,b.values?.gravity]],range)+'<div class="content-chart"><h4>引力渠道商详访问趋势</h4><p>'+pv.filter(v=>v!=null).length+'/7天 · 截止10/08</p>'+lineChart('引力渠道PV',trends.dates,pv,'PV')+'</div><p class="compare-note">商家渠道PV与内容曝光、阅读分别统计；不能把内容日数据直接当作该商品全部引力访问。</p></section><div class="gravity-status"><strong>广告消耗单独核验</strong><p>'+escape(g.actual_ad_spend_status)+' 目前已有达人任务内容数据与商家引力渠道访问，独立广告计划状态、实际消耗和广告点击日明细仍未取得。</p></div>';
    bind(mount,'gravity',()=>renderGravity(code));
  }

  global.ComparisonMath={shift,weekday,dateLabel,days,pair,rangeLabel,compare,business,channelPeriod,comparisonTable,controls,bind,state};
  global.renderBusinessComparison=renderBusiness;
  global.renderGravitySection=renderGravity;
})(window);
