import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

// 仅在逐日输入就绪并完成本次 marker 后运行；编写脚本不创建工作簿。
const ROOT = '/Users/nan/Documents/Codex/2026-10-09/zai';
const INPUT = path.join(ROOT, 'work/daily_trend.json');
const META = path.join(ROOT, 'work/retry_metrics.json');
const BLUE = '#2476A8', ORANGE = '#BA631E', INK = '#183443';
const numberFields = ['uv', 'orders', 'favorites', 'conversionPct', 'amount'];
const metricDefs = [
  { key: 'uv', label: '商详访客 UV', unit: '人', helperColumn: 2 },
  { key: 'orders', label: '支付订单数', unit: '单', helperColumn: 3 },
  { key: 'favorites', label: '收藏用户数', unit: '人', helperColumn: 4 }
];
const percentageDefs = [
  { key:'conversionPct',label:'商详转化率（后台）',unit:'%',helperColumn:5 },
  { key:'favoriteRate',label:'收藏率（计算）',unit:'%',helperColumn:6 }
];
const sha = data => crypto.createHash('sha256').update(data).digest('hex');
const execFileAsync=promisify(execFile);
const originalBytes = await fs.readFile(INPUT);
const input = JSON.parse(originalBytes.toString('utf8'));
const meta = JSON.parse(await fs.readFile(META, 'utf8'));
assert(Array.isArray(input.records), '输入必须含 records 数组');
const ranked = [...meta.rows].sort((a,b) => b[4][1]-a[4][1] || b[4][6]-a[4][6] || a[0].localeCompare(b[0]));
assert.equal(ranked.length, 46);
const products = ranked.map((r,index) => ({
  code:r[0], name:r[1], backendNew:r[2], weekSales:r[4][1], weekUv:r[4][6],
  group:r[4][1]>0?'有销量款':index<10?'零销量观察':'零销量',
  rank:ranked.filter(x=>x[4][1]>r[4][1]).length+1
}));
const productMap = new Map(products.map(p => [p.code,p]));
const dates = [];
for(let t=Date.parse(meta.week_start+'T00:00:00Z'); t<=Date.parse(meta.week_end+'T00:00:00Z'); t+=86400000)
  dates.push(new Date(t).toISOString().slice(0,10));
assert.equal(dates.length, 7, '当前交付必须是近7个完整自然日');
const actual = new Map(), warnings = [];
for(const record of input.records) {
  assert(productMap.has(record.code), '输入出现未核准类目货号：'+record.code);
  assert(dates.includes(record.date), '输入日期不属于所需7日：'+record.date);
  const key=record.code+'|'+record.date;
  assert(!actual.has(key), '同款同日重复：'+key);
  for(const field of numberFields) {
    const v=record[field];
    assert(v==null || typeof v==='number' && Number.isFinite(v) && v>=0, key+' '+field+'必须是非负数或null');
    if(['uv','orders','favorites'].includes(field) && v!=null) assert(Number.isInteger(v), key+' '+field+'必须为整数');
  }
  if(record.uv!=null && record.favorites!=null && record.favorites>record.uv)
    warnings.push(key+' 收藏用户数大于UV，收藏率口径须复核');
  actual.set(key, record);
}
assert(actual.size>0, '没有实际逐日记录，停止生成空图');
const grid = [];
for(const product of products) for(const date of dates) {
  const r=actual.get(product.code+'|'+date);
  grid.push({
    date,code:product.code,name:product.name,backendNew:product.backendNew,observed:Boolean(r),
    uv:r?.uv??null,orders:r?.orders??null,favorites:r?.favorites??null,
    conversionPct:r?.conversionPct??null,amount:r?.amount??null
  });
}
for(const r of grid) r.favoriteRate=r.uv>0 && r.favorites!=null?r.favorites/r.uv*100:null;
const cores=['YX9354001','YX9615001'].filter(c=>productMap.has(c));
assert.equal(cores.length, 2);
assert(cores.some(code=>grid.some(r=>r.code===code && [r.uv,r.orders,r.favorites].some(v=>v!=null))),
  '两核心款均无真实逐日点，停止生成空图');
const observedCount=actual.size;
// 对照已有昨日底表；只核验已读到的字段，不用既有值填补每日缺项。
for(const original of meta.rows) {
  const code=original[0],last=actual.get(code+'|'+meta.week_end);
  const reference={uv:original[5][6],orders:original[5][4],favorites:original[5][7],conversionPct:original[5][3],amount:original[5][0]};
  if(last) for(const field of numberFields) {
    if(last[field]!=null && Math.abs(last[field]-reference[field])>0.0051)
      warnings.push(code+' '+meta.week_end+' '+field+'与此前昨日底表不同，须核对取数时点及读数');
  }
  for(const [field,index] of [['orders',4],['amount',0]]) {
    const daily=dates.map(date=>actual.get(code+'|'+date)?.[field]);
    if(daily.every(v=>v!=null) && Math.abs(daily.reduce((a,b)=>a+b,0)-original[4][index])>0.0051)
      warnings.push(code+' 7日'+field+'合计与此前七天页面读数不同，须复核；未对UV或收藏人数作这种加总');
  }
}
const outputDir=path.join(ROOT,'outputs',meta.week_end);
const xlsxPath=path.join(outputDir,'近7天商品趋势.xlsx');
const htmlPath=path.join(outputDir,'近7天商品趋势.html');
const pngPath=path.join(outputDir,'核心两款近7天趋势.png');
const oldBottom=path.join(outputDir,'商品底表_重试.xlsx');
const oldBottomHash=sha(await fs.readFile(oldBottom));
const period=meta.week_start+' 至 '+meta.week_end;
const sourceLabel=input.source || '得物商家后台商品分析，逐日页面读数；非平台下载导出。';

const wb=Workbook.create();
const coreSheet=wb.worksheets.add('核心两款趋势');
const selectedSheet=wb.worksheets.add('单款趋势');
const rawSheet=wb.worksheets.add('每日底表');
const rawFirst=7,rawLast=rawFirst+grid.length-1;
const rawHeaders=['数据日期','货号','商品简称','后台新品标记','商详访客UV','支付订单数','收藏用户数','商详转化(后台)','支付金额(元)','收藏率(自算)','采集状态','匹配键'];
const unavailable=v=>v==null?'未获取':v;
rawSheet.getRange('A6:L6').values=[rawHeaders];
rawSheet.getRange('A'+rawFirst+':L'+rawLast).values=grid.map(r=>[
  new Date(r.date+'T00:00:00Z'),r.code,r.name,r.backendNew?'是；上架日待确认':'否',
  unavailable(r.uv),unavailable(r.orders),unavailable(r.favorites),
  r.conversionPct==null?'未获取':r.conversionPct/100,unavailable(r.amount),null,
  r.observed?'已采集':'未采集',r.code+'|'+r.date
]);
rawSheet.getRange('J'+rawFirst).formulas=[[
  '=IF(AND(ISNUMBER(E'+rawFirst+'),ISNUMBER(G'+rawFirst+'),E'+rawFirst+'>0),G'+rawFirst+'/E'+rawFirst+',"")'
]];
rawSheet.getRange('J'+rawFirst+':J'+rawLast).fillDown();
rawSheet.getRange('A2').values=[['近7天每日商品数据']];
rawSheet.getRange('A3').values=[['期间：'+period+'；一级类目：流行饰品/眼镜/服配；46款，实际采集'+observedCount+'/'+grid.length+'条。']];
rawSheet.getRange('A4').values=[[sourceLabel]];
rawSheet.getRange('A5').values=[['每款按日期连续7行，图表按此固定排列读取；需排序时请使用副本。缺失为“未获取”，真实0保留。']];
rawSheet.getRange('A'+rawFirst+':A'+rawLast).setNumberFormat('yyyy-mm-dd');
rawSheet.getRange('E'+rawFirst+':G'+rawLast).setNumberFormat('#,##0');
rawSheet.getRange('H'+rawFirst+':H'+rawLast).setNumberFormat('0.00%');
rawSheet.getRange('I'+rawFirst+':I'+rawLast).setNumberFormat('#,##0.00');
rawSheet.getRange('J'+rawFirst+':J'+rawLast).setNumberFormat('0.00%');

function baseStyle(sheet,lastRow,lastColumn,widths) {
  sheet.showGridLines=false;
  sheet.getRangeByIndexes(0,0,lastRow,lastColumn).format.font={name:'Arial',size:10,color:INK};
  sheet.getRangeByIndexes(0,0,lastRow,lastColumn).format.verticalAlignment='center';
  sheet.getRangeByIndexes(0,0,lastRow,lastColumn).format.rowHeight=21;
  sheet.getRange('A2').format.font={name:'Arial',size:14,bold:true,color:INK};
  sheet.getRange('A2').format.rowHeight=27;
  widths.forEach((w,i)=>sheet.getRangeByIndexes(0,i,lastRow,1).format.columnWidth=w);
}
function styleHeader(sheet,range) {
  sheet.getRange(range).format={fill:'#254C64',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},
    wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:32};
}
baseStyle(rawSheet,rawLast,12,[13,17,24,22,14,14,14,17,15,15,13,31]);
styleHeader(rawSheet,'A6:L6');
rawSheet.getRange('E'+rawFirst+':J'+rawLast).format.horizontalAlignment='right';
rawSheet.getRange('E'+rawFirst+':I'+rawLast).conditionalFormats.add('containsText',{
  text:'未获取',format:{fill:'#FFF1CF',font:{color:'#6B4B0B'}}
});
rawSheet.tables.add('A6:L'+rawLast,true,'DailyTrendSource');
rawSheet.freezePanes.freezeRows(6);
rawSheet.freezePanes.freezeColumns(2);
rawSheet.tabColor='#8B969D';

const helperHeaders=['日期','日期标签','商详访客UV','支付订单数','收藏用户数','商详转化(后台)','收藏率','支付金额(元)','源数据位置'];
const letters=n=>{let r='';while(n>=0){r=String.fromCharCode(n%26+65)+r;n=Math.floor(n/26)-1;}return r;};
function helperBlock(sheet,startColumn,headerRow,codeReference) {
  const endColumn=startColumn+8,first=headerRow+1,last=headerRow+7;
  sheet.getRangeByIndexes(headerRow-1,startColumn,1,9).values=[helperHeaders];
  styleHeader(sheet,letters(startColumn)+headerRow+':'+letters(endColumn)+headerRow);
  dates.forEach((date,i)=>{
    const r=first+i,a=letters(startColumn)+r,b=letters(startColumn+1)+r,k=letters(startColumn+8)+r;
    sheet.getRange(a).values=[[new Date(date+'T00:00:00Z')]];
    sheet.getRange(b).formulas=[['=TEXT('+a+',"mm/dd")']];
    sheet.getRange(k).formulas=[[
      '=(MATCH('+codeReference+',\'单款趋势\'!$N$7:$N$52,0)-1)*7+'+(i+1)
    ]];
    ['E','F','G','H','J','I'].forEach((sourceColumn,j)=>{
      const source='INDEX(\'每日底表\'!$'+sourceColumn+'$'+rawFirst+':$'+sourceColumn+'$'+rawLast+','+k+')';
      sheet.getRange(letters(startColumn+2+j)+r).formulas=[['=IF(ISNUMBER('+source+'),'+source+',"")']];
    });
  });
  sheet.getRange(letters(startColumn)+first+':'+letters(startColumn)+last).setNumberFormat('mm/dd');
  sheet.getRange(letters(startColumn+2)+first+':'+letters(startColumn+4)+last).setNumberFormat('#,##0');
  sheet.getRange(letters(startColumn+5)+first+':'+letters(startColumn+6)+last).setNumberFormat('0.00%');
  sheet.getRange(letters(startColumn+7)+first+':'+letters(startColumn+7)+last).setNumberFormat('#,##0.00');
  return {startColumn,headerRow,first,last};
}
function makeChart(sheet,block,metric,color,from,to,title) {
  const categoryColumn=letters(block.startColumn+1);
  const valueColumn=letters(block.startColumn+metric.helperColumn);
  const chart=sheet.charts.add('line',[
    sheet.getRange(categoryColumn+block.headerRow+':'+categoryColumn+block.last),
    sheet.getRange(valueColumn+block.headerRow+':'+valueColumn+block.last)
  ]);
  chart.title=title;
  chart.titleTextStyle.typeface='Arial';
  chart.titleTextStyle.fontSize=14;
  chart.hasLegend=false;
  chart.xAxis={axisType:'textAxis',textStyle:{typeface:'Arial',fontSize:11}};
  chart.yAxis={numberFormatCode:metric.unit==='%'?'0.0%':'#,##0',numberFormatSourceLinked:false,textStyle:{typeface:'Arial',fontSize:11}};
  chart.setPosition(from,to);
  assert.equal(chart.series.items.length,1);
  chart.series.items[0].line={fill:color,style:'solid',width:2};
  chart.series.items[0].fill=color;
  return chart;
}

baseStyle(coreSheet,73,23,Array(23).fill(8.5));
coreSheet.tabColor='#254C64';
coreSheet.getRange('A2').values=[['近7天核心商品按日趋势']];
coreSheet.getRange('A3').values=[['期间：'+period+'；UV、支付订单、收藏分别使用独立纵轴；逐日读数，缺失不补0。']];
coreSheet.getRange('A4').values=[['10月2—7日处于国庆假期，10月8日恢复工作日；图中变化不能直接证明价格或流量原因。']];
coreSheet.getRange('A5').values=[['可在“单款趋势”选择全部46款；后台新品真实首次上架日期待确认。']];
const coreBlocks=[];
cores.forEach((code,i)=>{
  const col=i===0?0:12,color=i===0?BLUE:ORANGE,p=productMap.get(code);
  coreSheet.getRange(letters(col)+'6').values=[[p.name+' '+p.code]];
  coreSheet.getRange(letters(col)+'6').format.font={name:'Arial',size:11,bold:true,color};
  coreSheet.getRange(letters(col)+'62').values=[[code]];
  coreSheet.getRange(letters(col+2)+'62').values=[['图表对应每日值（可核对）']];
  const block=helperBlock(coreSheet,col,64,'$'+letters(col)+'$62');
  coreBlocks.push(block);
  metricDefs.forEach((metric,j)=>{
    const top=8+j*16,bottom=top+14;
    makeChart(coreSheet,block,metric,color,letters(col)+top,letters(col+10)+bottom,metric.label+'（'+metric.unit+'）');
  });
});

baseStyle(selectedSheet,100,18,[13,16,16,15,15,18,15,18,15,9,9,9,3,17,27,16,18,13]);
selectedSheet.tabColor='#49697D';
selectedSheet.getRange('A2').values=[['选择商品查看近7天趋势']];
selectedSheet.getRange('A3').values=[['选择货号']];
selectedSheet.getRange('B3').values=[[cores[0]]];
selectedSheet.getRange('B3').format={fill:'#FFF1CF',font:{name:'Arial',size:10,bold:true,color:INK}};
selectedSheet.getRange('D3').formulas=[['=INDEX($O$7:$O$52,MATCH($B$3,$N$7:$N$52,0))']];
selectedSheet.getRange('A4').values=[['期间：'+period+'；缺失日期保持断点；订单数不替代“我的销量”。']];
selectedSheet.getRange('N5').values=[['全部46款，可在B3下拉选择']];
selectedSheet.getRange('N6:Q6').values=[['货号','商品简称','近7天分组','后台新品标记']];
selectedSheet.getRange('N7:Q52').values=products.map(p=>[p.code,p.name,p.group,p.backendNew?'是；日期待确认':'否']);
styleHeader(selectedSheet,'N6:Q6');
selectedSheet.getRange('B3').dataValidation={rule:{type:'list',formula1:'$N$7:$N$52'}};
const selectedBlock=helperBlock(selectedSheet,0,6,'$B$3');
[...metricDefs,...percentageDefs].forEach((metric,i)=>{
  const top=17+i*16;
  makeChart(selectedSheet,selectedBlock,metric,BLUE,'A'+top,'L'+(top+14),metric.label+'（'+metric.unit+'）');
});
selectedSheet.getRange('A98').values=[['收藏率=同商品同日收藏用户数/UV，UV=0或缺失留空；商详转化为后台原值。']];
selectedSheet.getRange('A99').values=[['单款每日UV不相加冒充七天去重访客；新品真实上架日期仍待确认。']];
selectedSheet.freezePanes.freezeRows(4);

wb.recalculate();
const selectedValues=selectedSheet.getRange('C7:H13').values;
const expectedDateLabels=dates.map(date=>date.slice(5).replace('-','/'));
assert.deepEqual(selectedSheet.getRange('B7:B13').values.flat(),expectedDateLabels);
for(const block of coreBlocks) assert.deepEqual(
  coreSheet.getRange(letters(block.startColumn+1)+block.first+':'+letters(block.startColumn+1)+block.last).values.flat(),
  expectedDateLabels
);
if(process.env.TREND_DEBUG==='1') {
  console.log(JSON.stringify({selected:selectedSheet.getRange('A7:I13').values,raw:rawSheet.getRange('A7:L13').values,formulas:selectedSheet.getRange('A7:I8').formulas}));
}
function compareBlock(blockValues,code) {
  dates.forEach((date,i)=>{
    const source=actual.get(code+'|'+date);
    const expected=[source?.uv??null,source?.orders??null,source?.favorites??null,
      source?.conversionPct==null?null:source.conversionPct/100,
      source?.uv>0 && source?.favorites!=null?source.favorites/source.uv:null,source?.amount??null];
    expected.forEach((v,j)=>{
      const got=blockValues[i][j];
      if(v==null) assert(got===''||got===null, '缺失被变成0：'+code+' '+date+' '+j);
      else assert(typeof got==='number' && Math.abs(got-v)<1e-10, '图表明细与源数据不符：'+code+' '+date+' '+j+' got='+JSON.stringify(got)+' expected='+v);
    });
  });
}
compareBlock(selectedValues,cores[0]);
for(let i=0;i<2;i++){
  const b=coreBlocks[i];
  compareBlock(coreSheet.getRange(letters(b.startColumn+2)+b.first+':'+letters(b.startColumn+7)+b.last).values,cores[i]);
}
// 实际切换一次第二核心款并验证联动，再恢复默认值。
selectedSheet.getRange('B3').values=[[cores[1]]];
wb.recalculate();
compareBlock(selectedSheet.getRange('C7:H13').values,cores[1]);
selectedSheet.getRange('B3').values=[[cores[0]]];
wb.recalculate();
assert.equal(coreSheet.charts.items.length,6);
assert.equal(selectedSheet.charts.items.length,5);
const formulaCheck=await wb.inspect({
  kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',
  options:{useRegex:true,maxResults:100},maxChars:3000
});
assert(/matched 0 entries/.test(formulaCheck.ndjson), '存在公式错误：'+formulaCheck.ndjson);

function offlineApp() {
  const payload=JSON.parse(document.getElementById('trend-data').textContent);
  const $=id=>document.getElementById(id);
  const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const lookup=new Map(payload.records.map(r=>[r.code+'|'+r.date,r]));
  const productMap=new Map(payload.products.map(p=>[p.code,p]));
  const metrics=[{key:'uv',label:'商详访客 UV',unit:'人'},{key:'orders',label:'支付订单数',unit:'单'},{key:'favorites',label:'收藏用户数',unit:'人'},{key:'conversionPct',label:'商详转化率（后台）',unit:'%'},{key:'favoriteRate',label:'收藏率（计算）',unit:'%'}];
  const fmt=v=>v==null?'—':Number(v).toLocaleString('zh-CN',{maximumFractionDigits:2});
  let mode='cores';
  function choices() {
    const filter=$('filter').value;
    const list=filter==='top'?payload.products.slice(0,10):filter==='new'?payload.products.filter(p=>p.backendNew):payload.products;
    const old=$('product').value;
    $('product').innerHTML=list.map(p=>'<option value="'+escape(p.code)+'">'+escape(p.code+' '+p.name+(p.weekSales===0?'（零销量）':''))+'</option>').join('');
    if(list.some(p=>p.code===old))$('product').value=old;
    $('choice-count').textContent=list.length+'款'+(filter==='new'?'，真实上架日期待确认':'');
  }
  function svgChart(code,metric,maxY) {
    const values=payload.dates.map(date=>lookup.get(code+'|'+date)?.[metric.key]??null);
    const width=620,height=260,left=52,right=22,top=25,bottom=44,plotW=width-left-right,plotH=height-top-bottom;
    const x=i=>left+i*plotW/(payload.dates.length-1);
    const y=v=>top+plotH-v/maxY*plotH;
    const color=code===payload.cores[1]?'#BA631E':'#2476A8';
    const parts=['<svg viewBox="0 0 '+width+' '+height+'" role="img" aria-label="'+escape(productMap.get(code).name+' '+metric.label+' 按日趋势')+'">'];
    for(let i=0;i<=4;i++){
      const value=maxY*i/4,yy=y(value);
      parts.push('<line x1="'+left+'" y1="'+yy+'" x2="'+(width-right)+'" y2="'+yy+'" stroke="#e2e7eb"/><text x="'+(left-10)+'" y="'+(yy+4)+'" text-anchor="end" class="axis">'+fmt(value)+(metric.unit==='%'?'%':'')+'</text>');
    }
    let segment=[];
    const flush=()=>{if(segment.length>1)parts.push('<polyline points="'+segment.join(' ')+'" fill="none" stroke="'+color+'" stroke-width="2.5"/>');segment=[];};
    values.forEach((v,i)=>{if(v==null)flush();else segment.push(x(i)+','+y(v));});flush();
    values.forEach((v,i)=>{
      parts.push('<text x="'+x(i)+'" y="'+(height-17)+'" text-anchor="middle" class="axis">'+payload.dates[i].slice(5).replace('-','/')+'</text>');
      if(v==null)parts.push('<text x="'+x(i)+'" y="'+(height-3)+'" text-anchor="middle" class="missing">缺失</text>');
      else parts.push('<circle cx="'+x(i)+'" cy="'+y(v)+'" r="4" fill="'+color+'"><title>'+escape(payload.dates[i]+' '+metric.label+'：'+fmt(v)+(metric.unit==='%'?'%':''))+'</title></circle><text x="'+x(i)+'" y="'+Math.max(12,y(v)-10)+'" text-anchor="middle" class="point">'+fmt(v)+(metric.unit==='%'?'%':'')+'</text>');
    });
    if(values.every(v=>v==null))parts.push('<text x="'+(width/2)+'" y="'+(height/2)+'" text-anchor="middle" class="missing">此指标暂无已核验日值</text>');
    parts.push('</svg>');
    return parts.join('');
  }
  function render() {
    const codes=mode==='cores'?payload.cores:[$('product').value];
    $('cores').classList.toggle('active',mode==='cores');
    $('single').classList.toggle('active',mode==='single');
    $('charts').className='charts'+(mode==='single'?' single':'');
    const cards=[];
    metrics.forEach(metric=>{
      const values=codes.flatMap(code=>payload.dates.map(date=>lookup.get(code+'|'+date)?.[metric.key]).filter(v=>v!=null));
      const maxY=metric.unit==='%'?(values.length?Math.max(1,Math.ceil(Math.max(...values)*1.12*4)/4):1):(values.length?Math.max(4,Math.ceil(Math.max(...values)/4)*4):4);
      codes.forEach(code=>{
        const p=productMap.get(code);
        const read=payload.dates.filter(date=>lookup.get(code+'|'+date)?.[metric.key]!=null).length;
        cards.push('<article class="panel"><div class="panel-heading"><div><h2>'+escape(metric.label)+' <small>'+metric.unit+'</small></h2><p>'+escape(p.name+' · '+p.code)+'</p></div><span class="coverage">'+read+'/7 天</span></div>'+svgChart(code,metric,maxY)+'</article>');
      });
    });
    $('charts').innerHTML=cards.join('');
    $('tables').innerHTML=codes.map(code=>{
      const p=productMap.get(code);
      return '<article class="panel detail"><h2>'+escape(p.name)+' 每日读数</h2><div class="table-scroll"><table><thead><tr><th>日期</th><th>访客 UV</th><th>支付订单</th><th>收藏人数</th><th>收藏率</th><th>商详转化</th></tr></thead><tbody>'+payload.dates.map(date=>{
        const r=lookup.get(code+'|'+date),favoriteRate=r?.uv>0 && r?.favorites!=null?(r.favorites/r.uv*100).toFixed(2)+'%':'—';
        return '<tr><td>'+date+'</td><td>'+fmt(r?.uv)+'</td><td>'+fmt(r?.orders)+'</td><td>'+fmt(r?.favorites)+'</td><td>'+favoriteRate+'</td><td>'+(r?.conversionPct==null?'—':r.conversionPct.toFixed(2)+'%')+'</td></tr>';
      }).join('')+'</tbody></table></div></article>';
    }).join('');
  }
  $('filter').addEventListener('change',()=>{choices();mode='single';render();});
  $('product').addEventListener('change',()=>{mode='single';render();});
  $('cores').addEventListener('click',()=>{mode='cores';render();});
  $('single').addEventListener('click',()=>{mode='single';render();});
  choices();$('product').value=payload.cores[0];render();
  window.trendPreview={setProduct:code=>{ $('filter').value='all';choices();$('product').value=code;mode='single';render();},coreView:()=>{mode='cores';render();}};
}
const payload={dates,products,cores,records:grid,observedCount,expectedCount:grid.length};
const safeJson=JSON.stringify(payload).replaceAll('<','\\u003c');
const html=[
  '<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
  '<title>近7天商品趋势 '+meta.week_end+'</title><style>',
  '*{box-sizing:border-box}body{margin:0;background:#f4f6f8;color:#183443;font:15px/1.55 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}.wrap{max-width:1380px;margin:auto;padding:32px 28px 48px}h1{font-size:28px;margin:0 0 5px;font-weight:650;letter-spacing:-.5px}.intro{margin:0;color:#526875}.scope{margin-top:14px;display:flex;flex-wrap:wrap;gap:9px;font-size:13px}.scope span{background:#e8eef2;padding:4px 10px;border-radius:5px}.toolbar{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:23px 0 17px}.toolbar label{color:#526875;font-size:13px}select,button{font:inherit;border:1px solid #ccd7df;background:white;color:#183443;border-radius:6px;padding:8px 11px}select#product{max-width:360px}button{cursor:pointer}button.active{background:#254c64;color:white;border-color:#254c64}#choice-count{font-size:12px;color:#6c7f89}.notice{color:#647985;font-size:13px;margin:0 0 17px}.charts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:17px}.charts.single{max-width:980px;grid-template-columns:1fr}.panel{background:white;border:1px solid #dfe6eb;border-radius:9px;padding:18px 18px 10px;min-width:0}.panel-heading{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.panel h2{margin:0;font-size:17px;font-weight:650}.panel h2 small{font-size:12px;color:#6b7d87;font-weight:400}.panel p{margin:4px 0;color:#607684;font-size:13px}.coverage{color:#71858f;font-size:12px;white-space:nowrap}.panel svg{display:block;width:100%;height:auto;margin-top:8px}.axis{font:12px sans-serif;fill:#6b7e89}.point{font:12px sans-serif;fill:#183443;paint-order:stroke;stroke:white;stroke-width:3px;stroke-linejoin:round}.missing{font:11px sans-serif;fill:#9a671b}#tables{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:17px;margin-top:20px}.detail{padding-bottom:18px}.detail h2{margin-bottom:12px}.table-scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px;white-space:nowrap}th{text-align:right;color:#607684;font-weight:500;background:#f4f7f9}td{text-align:right;border-bottom:1px solid #edf1f4}th,td{padding:9px 8px}th:first-child,td:first-child{text-align:left}footer{margin-top:22px;font-size:12px;color:#6c7f89}footer p{margin:6px 0}@media(max-width:800px){.wrap{padding:22px 14px}h1{font-size:24px}.charts,#tables{grid-template-columns:1fr}.toolbar{gap:8px}select#product{max-width:100%}.panel{padding:14px 10px 6px}}@media print{body{background:white}.toolbar{display:none}.wrap{max-width:none;padding:0}.panel{break-inside:avoid}.charts{gap:10px}}',
  '</style></head><body><main class="wrap"><h1>近7天商品趋势</h1><p class="intro">'+period+' · 一级类目：流行饰品/眼镜/服配</p>',
  '<div class="scope"><span>46款商品</span><span>已采集 '+observedCount+'/'+grid.length+' 条逐日记录</span><span>默认两核心款对照</span></div>',
  '<div class="toolbar"><button id="cores" class="active">核心两款对照</button><button id="single">所选单款</button><label for="filter">范围</label><select id="filter"><option value="all">全部46款</option><option value="top">头部观察10款</option><option value="new">后台新品标记</option></select><label for="product">商品</label><select id="product"></select><span id="choice-count"></span></div>',
  '<p class="notice">每项指标独立纵轴；核心两款对照时，同一指标使用相同尺度。缺失显示断点，真实0保留。10月2—7日为国庆假期，10月8日恢复工作日。</p>',
  '<section id="charts" class="charts" aria-label="逐日趋势折线图"></section><section id="tables" aria-label="每日精确读数"></section>',
  '<footer><p>单量采用支付订单数；收藏率=同商品同日收藏用户数÷UV，UV=0或缺失时不计算；商详转化保留后台原值。</p><p>“头部观察10款”含4款近7天有销量商品及6款零销量观察商品；这6款按七天UV降序选取，同UV时按货号排序。42款零销量并列第5；后台新品标记的实际首次上架日期待确认。</p><p>来源：'+sourceLabel.replaceAll('&','&amp;').replaceAll('<','&lt;')+' 图中没有将七天汇总或环比反推数填入每日值；每日UV不相加作为七天去重访客。</p></footer></main>',
  '<script id="trend-data" type="application/json">'+safeJson+'</script><script>('+offlineApp.toString()+')();</script></body></html>'
].join('');

await fs.mkdir(outputDir,{recursive:true});
const exported=await SpreadsheetFile.exportXlsx(wb);
await exported.save(xlsxPath);
const finalization=await execFileAsync(
  '/Users/nan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',
  [path.join(ROOT,'work/finalize_daily_trend_xlsx.py'),xlsxPath]
);
console.log(finalization.stdout.trim());
try{await fs.rename(xlsxPath+'.inspect.ndjson',path.join(ROOT,'work/daily_trend_export_inspect.ndjson'));}catch(e){if(e.code!=='ENOENT')throw e;}
await fs.writeFile(htmlPath,html,'utf8');
const overview=await wb.render({sheetName:'核心两款趋势',range:'A1:W56',scale:1.3,format:'png'});
// 用户PNG由独立标准绘图步骤维护；此处只保留Artifact原生渲染作为QA。
await fs.writeFile(path.join(ROOT,'work/daily_trend_native_core_preview.png'),new Uint8Array(await overview.arrayBuffer()));
const singlePreview=await wb.render({sheetName:'单款趋势',range:'A1:L99',scale:1,format:'png'});
await fs.writeFile(path.join(ROOT,'work/daily_trend_single_preview.png'),new Uint8Array(await singlePreview.arrayBuffer()));
const rawPreview=await wb.render({sheetName:'每日底表',range:'A1:K16',scale:1,format:'png'});
await fs.writeFile(path.join(ROOT,'work/daily_trend_raw_preview.png'),new Uint8Array(await rawPreview.arrayBuffer()));
assert.equal(sha(await fs.readFile(INPUT)),sha(originalBytes),'输入在构建期间被修改');
assert.equal(sha(await fs.readFile(oldBottom)),oldBottomHash,'原底表被修改');
const summary={
  period,products:products.length,actualRecords:observedCount,expectedRecords:grid.length,
  missingRecords:grid.length-observedCount,warnings,charts:11,selectorSwitchVerified:true,
  formulaCheck:formulaCheck.ndjson,sourceInputUnchanged:true,originalBottomUnchanged:true,
  outputs:[xlsxPath,htmlPath],corePreviewMaintainedSeparately:pngPath,
  chartBindings:coreSheet.charts.items.concat(selectedSheet.charts.items).flatMap(c=>c.series.items.map(s=>({values:s.formula,categories:s.categoryFormula})))
};
await fs.writeFile(path.join(ROOT,'work/daily_trend_validation.json'),JSON.stringify(summary,null,2),'utf8');
console.log(JSON.stringify(summary));
