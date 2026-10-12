(function installChannelSection(global) {
  'use strict';
  const stateByCode = new Map();
  const escape = value => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const validPV = value => typeof value === 'number' && Number.isFinite(value) && value >= 0 && Number.isInteger(value) ? value : null;
  const pv = (day,id) => validPV(day?.values?.[id]);
  const total = day => validPV(day?.total);
  const fmt = value => value == null ? '—' : Number(value).toLocaleString('zh-CN',{maximumFractionDigits:2});
  const signed = value => value == null ? '—' : (value > 0 ? '+' : value < 0 ? '−' : '') + fmt(Math.abs(value));
  const pct = value => value == null ? '—' : signed(value) + '%';
  const change = (current,previous) => current != null && previous != null ? current - previous : null;
  const changePct = (current,previous) => current != null && previous > 0 ? (current - previous) / previous * 100 : null;
  const direction = value => value == null || value === 0 ? '' : value > 0 ? 'channel-positive' : 'channel-negative';
  const datePattern = /^\d{4}-\d{2}-\d{2}$/;

  function orderedChannels(channels) {
    const result = [], seen = new Set();
    const append = channel => {
      if (seen.has(channel.id)) return;
      seen.add(channel.id); result.push(channel);
      channels.filter(item => item.parent_id === channel.id).forEach(append);
    };
    channels.filter(item => item.parent_id == null || item.parent_id === '').forEach(append);
    channels.forEach(append);
    return result;
  }

  function summarizeChanges(rows,totalDelta) {
    const reductions=rows.filter(row=>row.delta<0).sort((a,b)=>Math.abs(b.delta)-Math.abs(a.delta));
    const increases=rows.filter(row=>row.delta>0).sort((a,b)=>b.delta-a.delta);
    const lost=reductions.reduce((sum,row)=>sum-row.delta,0),gained=increases.reduce((sum,row)=>sum+row.delta,0);
    const list=items=>items.slice(0,3).map(row=>escape(row.name)+' '+signed(row.delta)+' PV').join('、');
    if(totalDelta<0) return '总 PV 减少 '+fmt(-totalDelta)+'：减少最多的一级渠道为 '+list(reductions)+'；增加渠道合计抵消 '+fmt(gained)+' PV。';
    if(totalDelta>0) return '总 PV 增加 '+fmt(totalDelta)+'：增加最多的一级渠道为 '+list(increases)+'；减少渠道合计抵消 '+fmt(lost)+' PV。';
    return lost>0?'总 PV 持平：减少渠道合计 '+fmt(lost)+' PV，增加渠道合计 '+fmt(gained)+' PV，两者抵消。':'总 PV 持平：6 个一级渠道均无增减。';
  }

  function barChart(rows) {
    const observed = rows.map(row=>row.delta).filter(value=>value!=null);
    if (!observed.length) return '<div class="channel-empty">增减图需要两个日期的实采渠道 PV。<p>当前仍可查看已采集日的渠道构成；不会反推缺失的对比日 PV。</p></div>';
    const max = Math.max(1,...observed.map(Math.abs));
    const parts=['<div class="channel-bar-columns" aria-hidden="true"><span>渠道</span><span class="channel-bar-axis"><span>−'+fmt(max)+'</span><span>0</span><span>+'+fmt(max)+'</span></span><span>增减 PV</span></div><div class="channel-bars" role="list" aria-label="一级渠道访问次数PV增减条形图">'];
    rows.forEach(row=>{
      let track='<span class="channel-bar-zero"></span>',label;
      if(row.delta==null) {
        label=row.current==null&&row.previous==null?'双日缺失':row.current==null?'查看日缺失':'对比日缺失';
      } else {
        const width=Math.abs(row.delta)/max*50;
        if(width>0) track+='<span class="channel-bar-fill '+(row.delta<0?'channel-bar-fill-negative':'channel-bar-fill-positive')+'" style="width:'+width+'%"></span>';
        else track+='<span class="channel-bar-zero-point"></span>';
        label=signed(row.delta)+' PV';
      }
      parts.push('<div class="channel-bar-row" role="listitem" aria-label="'+escape(row.name+'：'+label)+'"><span class="channel-bar-label">'+escape(row.name)+'</span><span class="channel-bar-track" aria-hidden="true">'+track+'</span><span class="channel-bar-value '+direction(row.delta)+'">'+label+'</span></div>');
    });
    parts.push('</div>'); return parts.join('');
  }

  function lineChart(channel,dates,days) {
    const values=dates.map(date=>pv(days[date],channel.id)), known=values.filter(value=>value!=null);
    const width=620,height=300,left=72,right=42,top=44,bottom=72,plotW=width-left-right,plotH=height-top-bottom;
    const maxY=known.length?Math.max(4,Math.ceil(Math.max(...known)/4)*4):4;
    const x=index=>dates.length===1?left+plotW/2:left+index*plotW/(dates.length-1);
    const y=value=>top+plotH-value/maxY*plotH;
    const parts=['<svg viewBox="0 0 '+width+' '+height+'" role="img" aria-label="'+escape(channel.name)+' 商详访问次数PV按日趋势">'];
    for(let i=0;i<=4;i++) {
      const value=maxY*i/4,yy=y(value);
      parts.push('<line x1="'+left+'" y1="'+yy+'" x2="'+(width-right)+'" y2="'+yy+'" stroke="#e2e7eb"/><text x="'+(left-10)+'" y="'+(yy+4)+'" text-anchor="end" class="channel-axis">'+fmt(value)+'</text>');
    }
    let segment=[];
    const flush=()=>{if(segment.length>1)parts.push('<polyline points="'+segment.join(' ')+'" fill="none" stroke="#2476A8" stroke-width="2.5"/>');segment=[];};
    values.forEach((value,index)=>{if(value==null)flush();else segment.push(x(index)+','+y(value));});flush();
    values.forEach((value,index)=>{
      parts.push('<text x="'+x(index)+'" y="'+(height-37)+'" text-anchor="middle" class="channel-axis">'+escape(dates[index].slice(5).replace('-','/'))+'</text>');
      if(value==null) parts.push('<text x="'+x(index)+'" y="'+(height-7)+'" text-anchor="middle" class="channel-missing">缺失</text>');
      else parts.push('<circle cx="'+x(index)+'" cy="'+y(value)+'" r="4" fill="#2476A8"><title>'+escape(dates[index]+' '+channel.name+'：'+fmt(value)+' PV')+'</title></circle><text x="'+x(index)+'" y="'+Math.max(26,y(value)-12)+'" text-anchor="middle" class="channel-point">'+fmt(value)+'</text>');
    });
    if(!known.length) parts.push('<text x="'+width/2+'" y="'+height/2+'" text-anchor="middle" class="channel-missing">此渠道暂无已采集日值</text>');
    parts.push('</svg>');return parts.join('');
  }

  function renderChannelSection(code) {
    const mount=document.getElementById('channel-section');
    if(!mount) return;
    const data=global.CHANNEL_DATA || {}, product=data.products?.[code], days=product?.days || {};
    const dates=[...new Set((Array.isArray(data.dates)?data.dates:[]).filter(date=>typeof date==='string'&&datePattern.test(date)))].sort();
    const channels=Array.isArray(data.channels)?data.channels.filter(channel=>channel&&typeof channel.id==='string'&&typeof channel.name==='string'):[];
    const primary=channels.filter(channel=>channel.parent_id==null||channel.parent_id==='');
    const anyObserved=dates.some(date=>total(days[date])!=null||channels.some(channel=>pv(days[date],channel.id)!=null));
    const heading='<h2>单品流量来源</h2><p>'+escape(product?.name?product.name+' · '+code:code||'请选择商品')+' · 商详访问次数 PV</p>';
    if(!code || !dates.length || !channels.length || !anyObserved) {
      const unavailable=product?.source_status==='not_exposed_in_backend';
      const message=!code?'选择商品后查看流量来源。':unavailable?'后台当前未提供该商品的渠道来源明细。':'该商品尚无已采集的渠道日数据。';
      const note=typeof product?.source_note==='string'&&product.source_note.trim()?'<p>核验说明：'+escape(product.source_note)+'</p>':'';
      mount.innerHTML='<div class="channel-header"><div>'+heading+'</div></div><div class="channel-empty">'+message+note+'<p>可切换“经营趋势”查看该商品已采集的访客、订单和收藏；渠道缺失不会填成 0。</p></div>';
      return;
    }
    const lastObserved=[...dates].reverse().find(date=>total(days[date])!=null||channels.some(channel=>pv(days[date],channel.id)!=null));
    let state=stateByCode.get(code);
    if(!state||!dates.includes(state.current)) {
      const index=dates.indexOf(lastObserved);
      state={current:lastObserved,previous:index>0?dates[index-1]:null};
      stateByCode.set(code,state);
    }
    const current=days[state.current],previous=days[state.previous];
    const currentTotal=total(current),previousTotal=total(previous),totalDelta=change(currentTotal,previousTotal),totalPct=changePct(currentTotal,previousTotal);
    const rows=primary.map(channel=>({id:channel.id,name:channel.name,current:pv(current,channel.id),previous:pv(previous,channel.id),delta:change(pv(current,channel.id),pv(previous,channel.id))}));
    const pairValuesComplete=rows.length===6&&rows.every(row=>row.delta!=null);
    const currentPrimaryComplete=rows.length===6&&rows.every(row=>row.current!=null);
    const previousPrimaryComplete=rows.length===6&&rows.every(row=>row.previous!=null);
    const currentSum=currentPrimaryComplete?rows.reduce((sum,row)=>sum+row.current,0):null;
    const previousSum=previousPrimaryComplete?rows.reduce((sum,row)=>sum+row.previous,0):null;
    const completePair=pairValuesComplete&&currentTotal!=null&&previousTotal!=null&&currentSum===currentTotal&&previousSum===previousTotal;
    const grossDecline=completePair?rows.reduce((sum,row)=>sum+Math.max(0,-row.delta),0):null;
    const options=(selected,includeBlank)=> (includeBlank?'<option value="">未选择</option>':'')+dates.map(date=>'<option value="'+date+'"'+(date===selected?' selected':'')+'>'+date+'</option>').join('');
    const controls='<div class="channel-controls"><label for="channel-current-date">查看日</label><select id="channel-current-date">'+options(state.current,false)+'</select><label for="channel-previous-date">对比日</label><select id="channel-previous-date">'+options(state.previous,true)+'</select></div>';
    let summary='<div class="channel-summary"><span>'+escape(state.current)+' 全部 PV<strong>'+fmt(currentTotal)+'</strong></span><span>'+escape(state.previous||'对比日未选择')+' PV<strong>'+fmt(previousTotal)+'</strong></span><span>增减 PV<strong class="'+direction(totalDelta)+'">'+signed(totalDelta)+'</strong>'+(totalPct!=null?'<small class="'+direction(totalPct)+'">'+pct(totalPct)+'</small>':'')+'</span></div>';
    if(completePair) summary+='<p class="channel-change-insight">'+summarizeChanges(rows,totalDelta)+'</p>';
    if(currentTotal!=null&&previousTotal===0) summary+='<p class="channel-caption">对比日总 PV 为 0，增减次数可计算，涨跌百分比不计算。</p>';
    if(totalDelta==null) summary+='<p class="channel-caption">所选两日总 PV 尚未全部采集，暂不计算总增减。</p>';
    const alerts=[];
    if(primary.length!==6) alerts.push('当前渠道结构含 '+primary.length+' 个一级渠道；完整一级渠道应为 6 个，增减份额暂不计算。');
    if(currentSum!=null&&currentTotal!=null&&currentSum!==currentTotal) alerts.push('查看日一级渠道合计 '+fmt(currentSum)+' PV，与后台全部 '+fmt(currentTotal)+' PV 不一致，需核对采集口径。');
    if(previousSum!=null&&previousTotal!=null&&previousSum!==previousTotal) alerts.push('对比日一级渠道合计 '+fmt(previousSum)+' PV，与后台全部 '+fmt(previousTotal)+' PV 不一致，需核对采集口径。');
    const tableRows=orderedChannels(channels).map(channel=>{
      const a=pv(current,channel.id),b=pv(previous,channel.id),delta=change(a,b),ratio=changePct(a,b),child=channel.parent_id!=null&&channel.parent_id!=='';
      const share=a!=null&&currentTotal>0?a/currentTotal*100:null;
      const declineShare=!child&&grossDecline>0&&delta<0?-delta/grossDecline*100:null;
      const shareLabel=share==null?'—':fmt(share)+'%';
      return '<tr class="'+(child?'channel-child':'channel-primary')+'"><td>'+escape(channel.name)+'</td><td>'+fmt(a)+'</td><td>'+shareLabel+'</td><td>'+fmt(b)+'</td><td class="'+direction(delta)+'">'+signed(delta)+'</td><td class="'+direction(ratio)+'">'+pct(ratio)+'</td><td>'+ (declineShare==null?'—':fmt(declineShare)+'%')+'</td></tr>';
    }).join('');
    const table='<div class="channel-table-scroll"><table class="channel-table"><thead><tr><th>渠道</th><th>查看日 PV</th><th>占全部 PV</th><th>对比日 PV</th><th>增减 PV</th><th>计算涨跌</th><th>下降渠道内份额</th></tr></thead><tbody>'+tableRows+'</tbody></table></div>';
    const tableNote='子渠道缩进列示，占比均以该商品查看日全部 PV 为分母；父级已包含子渠道，不重复求和。计算涨跌仅使用所选双日实采值，不反推历史值。';
    const declineNote=completePair?'下降渠道内份额=该一级渠道减少 PV÷所有减少一级渠道减少 PV 之和；它不是总净变化贡献。':!pairValuesComplete?'所选双日的 6 个一级渠道尚未完整采集，下降渠道内份额留空。':'所选双日的一级渠道合计与后台全部 PV 尚未通过核对，下降渠道内份额留空。';
    const trends=primary.map(channel=>{
      const read=dates.filter(date=>pv(days[date],channel.id)!=null).length;
      return '<article class="channel-panel"><div class="channel-trend-heading"><h3>'+escape(channel.name)+'</h3><small>'+read+'/'+dates.length+' 天 · PV</small></div>'+lineChart(channel,dates,days)+'</article>';
    }).join('');
    mount.innerHTML='<div class="channel-header"><div>'+heading+'</div>'+controls+'</div>'+summary+alerts.map(alert=>'<div class="channel-alert">'+escape(alert)+'</div>').join('')+'<div class="channel-layout"><article class="channel-panel"><h3>一级渠道增减</h3><p>'+escape(state.current)+' 对比 '+escape(state.previous||'未选择')+' · 正值增加，负值减少</p>'+barChart(rows)+'<p class="channel-caption">仅对两个日期均已采集的渠道绘制增减；缺失留空。</p></article><article class="channel-panel"><h3>渠道完整明细</h3>'+table+'<p class="channel-caption">'+tableNote+'</p><p class="channel-caption">'+declineNote+'</p></article></div><div class="channel-trends">'+trends+'</div><p class="channel-notes">渠道趋势使用商详访问次数 PV，与上方商品访客 UV 是不同指标。各渠道独立纵轴，缺失日期断线，明确读取的真实 0 正常显示。</p>';
    document.getElementById('channel-current-date')?.addEventListener('change',event=>{state.current=event.target.value;renderChannelSection(code);});
    document.getElementById('channel-previous-date')?.addEventListener('change',event=>{state.previous=event.target.value||null;renderChannelSection(code);});
  }

  global.renderChannelSection=renderChannelSection;
})(window);
