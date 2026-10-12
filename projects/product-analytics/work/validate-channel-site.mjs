// Read-only acceptance of the actual integrated HTML in a minimal DOM contract.
// Uses the real embedded scripts and data, with no browser, network, or writes.
// Optional argv[2]: another local HTML path to validate after final integration.
// Optional argv[3]: backend weekly-read baseline for the same period.
import fs from 'node:fs/promises';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const sitePath=process.argv[2] || '/Users/nan/Documents/Codex/2026-10-09/zai/work/dewu-trend-site/dist/index.html';
const weeklyPath=process.argv[3] || '/Users/nan/Documents/Codex/2026-10-09/zai/work/retry_metrics.json';
const html=await fs.readFile(sitePath,'utf8');
const weekly=JSON.parse(await fs.readFile(weeklyPath,'utf8'));
const decode=value=>String(value).replace(/&(?:amp|lt|gt|quot|#39);/g,m=>({'&amp;':'&','&lt;':'<','&gt;':'>','&quot;':'"','&#39;':"'"}[m]));
const escape=value=>String(value).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const attrs=text=>Object.fromEntries([...text.matchAll(/([^\s=\/]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g)].map(m=>[m[1],decode(m[2]??m[3]??m[4]??'')]));
const strip=value=>decode(String(value).replace(/<[^>]*>/g,''));
const elements=new Map();
class Element {
  constructor(tag,id,attributes={}) {
    this.tagName=tag.toUpperCase();this.id=id;this.attributes={...attributes};this.hidden=Object.hasOwn(attributes,'hidden');
    this._html='';this._text='';this._value='';this._className=attributes.class||'';this.listeners=new Map();this.ownedIds=new Set();this.options=[];
    this.classList={
      toggle:(name,force)=>{const set=new Set(this._className.split(/\s+/).filter(Boolean));const on=force??!set.has(name);if(on)set.add(name);else set.delete(name);this._className=[...set].join(' ');return on;},
      contains:name=>this._className.split(/\s+/).includes(name),
      add:name=>this.classList.toggle(name,true),remove:name=>this.classList.toggle(name,false)
    };
  }
  get className(){return this._className;}
  set className(value){this._className=String(value);}
  get innerHTML(){return this._html;}
  set innerHTML(value) {
    for(const id of this.ownedIds) elements.delete(id);
    this.ownedIds.clear();this._html=String(value);this._text=strip(value);
    if(this.tagName==='SELECT') {
      this.options=[...this._html.matchAll(/<option\b([^>]*)>([\s\S]*?)<\/option>/g)].map(match=>{
        const a=attrs(match[1]);return {value:a.value??strip(match[2]),textContent:strip(match[2]),selected:Object.hasOwn(a,'selected')};
      });
      this._value=(this.options.find(option=>option.selected)||this.options[0])?.value??'';
    }
    for(const match of this._html.matchAll(/<([a-z][a-z0-9-]*)\b([^>]*\bid="[^"]+"[^>]*)>/gi)) {
      const a=attrs(match[2]);if(!a.id)continue;
      const child=new Element(match[1],a.id,a);elements.set(a.id,child);this.ownedIds.add(a.id);
      if(child.tagName==='SELECT') {
        const after=this._html.slice(match.index+match[0].length),end=after.indexOf('</select>');
        child.innerHTML=end>=0?after.slice(0,end):'';
      }
    }
  }
  get textContent(){return this._text;}
  set textContent(value){this._text=String(value);}
  get value(){return this._value;}
  set value(value){value=String(value);this._value=this.tagName==='SELECT'&&!this.options.some(option=>option.value===value)?'':value;}
  setAttribute(name,value){this.attributes[name]=String(value);if(name==='class')this._className=String(value);}
  getAttribute(name){return this.attributes[name]??null;}
  addEventListener(name,listener){const list=this.listeners.get(name)||[];list.push(listener);this.listeners.set(name,list);}
  dispatchEvent(event){for(const listener of this.listeners.get(event.type)||[])listener({...event,target:this,currentTarget:this});return true;}
  click(){this.dispatchEvent({type:'click'});}
  change(value){this.value=value;this.dispatchEvent({type:'change'});}
}
const scripts=[...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)].map(match=>({attrs:attrs(match[1]),code:match[2]}));
const markup=html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'');
for(const match of markup.matchAll(/<([a-z][a-z0-9-]*)\b([^>]*\bid="[^"]+"[^>]*)>/gi)) {
  const a=attrs(match[2]),element=new Element(match[1],a.id,a);elements.set(a.id,element);
  if(element.tagName==='SELECT') {
    const after=markup.slice(match.index+match[0].length),end=after.indexOf('</select>');
    element.innerHTML=end>=0?after.slice(0,end):'';
  }
}
for(const script of scripts) if(script.attrs.id) {
  const element=new Element('script',script.attrs.id,script.attrs);element.textContent=script.code;elements.set(script.attrs.id,element);
}
const document={getElementById:id=>elements.get(id)||null};
const window={document};const context=vm.createContext({window,document,console});
let scriptsExecuted=0;
for(const [index,script] of scripts.entries()) {
  assert(!script.attrs.src,'acceptance expects no external script dependency');
  if(script.attrs.type==='application/json')continue;
  vm.runInContext(script.code,context,{filename:'integrated-script-'+index+'.js',timeout:5000});scriptsExecuted++;
}
const el=id=>{const node=elements.get(id);assert(node,'expected DOM element '+id);return node;};
const data=JSON.parse(el('trend-data').textContent),channels=JSON.parse(JSON.stringify(window.CHANNEL_DATA));
const known=value=>typeof value==='number'&&Number.isFinite(value)&&value>=0&&Number.isInteger(value);
const fmt=value=>value==null?'—':Number(value).toLocaleString('zh-CN',{maximumFractionDigits:2});
const allCodes=data.products.map(p=>p.code),primary=channels.channels.filter(channel=>channel.parent_id==null||channel.parent_id==='');
assert(allCodes.length>0,'nonempty focus products');
assert.equal(new Set(allCodes).size,allCodes.length,'unique focus products');
assert.equal(data.dates.length,7);assert.equal(data.cores.length,2);
assert.equal(data.records.length,allCodes.length*data.dates.length,'one daily record per focused product/date');
assert.equal(new Set(data.records.map(record=>record.code+'|'+record.date)).size,data.records.length,'unique daily records');
for(const date of data.dates) assert.deepEqual(data.records.filter(record=>record.date===date).map(record=>record.code).sort(),[...allCodes].sort(),'trend daily product scope '+date);
if(data.expectedCount!=null) assert.equal(data.expectedCount,data.records.length,'focused expected-count metadata');
if(data.observedCount!=null) assert.equal(data.observedCount,data.records.length,'focused observed-count metadata');
assert.equal(typeof window.renderChannelSection,'function');
assert.equal(weekly.week_start,data.dates[0],'weekly baseline starts with displayed period');
assert.equal(weekly.week_end,data.dates.at(-1),'weekly baseline ends with displayed period');
const backendProducts=new Map(weekly.rows.map(row=>[row[0],{code:row[0],backendNew:row[2],weekSales:row[4][1],weekFavorites:row[4][7]}]));
const keep=product=>product.backendNew===true||product.weekSales>0||product.weekFavorites>0;
for(const product of backendProducts.values()) assert(known(product.weekSales)&&known(product.weekFavorites),'backend weekly sales/favorite counts must be actual nonnegative integers');
const expectedFocus=[...backendProducts.values()].filter(keep).map(product=>product.code);
const excluded=[...backendProducts.values()].filter(product=>!keep(product)).map(product=>product.code);
assert.deepEqual([...allCodes].sort(),[...expectedFocus].sort(),'trend scope equals backend rule: exclude old AND zero weekly sales AND zero weekly favorites');
assert.deepEqual(Object.keys(channels.products).sort(),[...allCodes].sort(),'source and trend payloads have identical product sets');
assert.deepEqual([...channels.dates].sort(),[...data.dates].sort(),'source and trend periods match');
for(const product of data.products) {
  const backend=backendProducts.get(product.code);assert(backend,'focused code exists in backend baseline');
  assert.equal(product.backendNew,backend.backendNew,'focused new label matches backend '+product.code);
  assert.equal(product.weekSales,backend.weekSales,'focused weekly sales matches backend '+product.code);
  if(product.weekFavorites!=null) assert.equal(product.weekFavorites,backend.weekFavorites,'focused weekly favorites matches backend '+product.code);
}
assert(!allCodes.includes('YX9611001')&&!Object.hasOwn(channels.products,'YX9611001'),'old zero-sales zero-favorite example excluded from both views');
assert(allCodes.includes('YX9648002')&&Object.hasOwn(channels.products,'YX9648002'),'zero-data new product remains in both views');
assert(backendProducts.get('YX9648002').backendNew&&backendProducts.get('YX9648002').weekSales===0&&backendProducts.get('YX9648002').weekFavorites===0,'retained example is truly a zero-data new product');
assert.equal(primary.length,6,'six primary channel definitions');
const observedCodes=allCodes.filter(code=>channels.dates.some(date=>{const day=channels.products[code]?.days?.[date];return known(day?.total)||channels.channels.some(channel=>known(day?.values?.[channel.id]));}));
const missingSourceCodes=allCodes.filter(code=>!observedCodes.includes(code));
for(const code of missingSourceCodes) {
  const product=channels.products[code];
  assert(typeof product?.source_status==='string'&&product.source_status.trim()&&!['collected','available'].includes(product.source_status),'unavailable source requires an explicit status '+code);
  assert(typeof product?.source_note==='string'&&product.source_note.trim(),'unavailable source requires a concrete verification note '+code);
}
for(const code of observedCodes) for(const date of channels.dates.slice(-2)) {
  const day=channels.products[code]?.days?.[date];assert(known(day?.total),'all focused products have actual final-two-day total PV '+code+' '+date);
  const values=primary.map(channel=>day?.values?.[channel.id]);assert(values.every(known),'all focused products have actual final-two-day primary channels '+code+' '+date);
  assert.equal(values.reduce((sum,value)=>sum+value,0),day.total,'final-two-day source reconciliation '+code+' '+date);
}
for(const code of data.cores) assert.equal(channels.dates.filter(date=>known(channels.products[code]?.days?.[date]?.total)).length,data.dates.length,'both cores retain full seven-day source coverage '+code);
const channelStateVisible=()=>{
  assert.equal(el('channel-block').hidden,false);assert.equal(el('charts').hidden,true);assert.equal(el('tables').hidden,true);
  assert.equal(el('cores').hidden,true);assert.equal(el('single').hidden,true);
  assert(el('view-channels').classList.contains('active'));assert(!el('view-trends').classList.contains('active'));
  assert.equal(el('view-channels').getAttribute('aria-pressed'),'true');assert.equal(el('view-trends').getAttribute('aria-pressed'),'false');
};
const trendStateVisible=()=>{
  assert.equal(el('channel-block').hidden,true);assert.equal(el('charts').hidden,false);assert.equal(el('tables').hidden,false);
  assert.equal(el('cores').hidden,false);assert.equal(el('single').hidden,false);
  assert(!el('view-channels').classList.contains('active'));assert(el('view-trends').classList.contains('active'));
  assert.equal(el('view-channels').getAttribute('aria-pressed'),'false');assert.equal(el('view-trends').getAttribute('aria-pressed'),'true');
};
channelStateVisible();assert.equal(el('product').value,data.cores[0],'default source product is first core');
assert.equal(el('product').options.length,allCodes.length,'default focused-products dropdown');
assert(html.includes('[hidden]{display:none!important}'),'hidden state has a CSS rule');

const trendMetrics=[
  {key:'uv',label:'商详访客 UV',unit:'人'}, {key:'orders',label:'支付订单数',unit:'单'},
  {key:'favorites',label:'收藏用户数',unit:'人'}, {key:'conversionPct',label:'商详转化率（后台）',unit:'%'},
  {key:'favoriteRate',label:'收藏率（计算）',unit:'%'}
];
const trendLookup=new Map(data.records.map(record=>[record.code+'|'+record.date,record]));
function checkTrend(codes) {
  const panels=[...el('charts').innerHTML.matchAll(/<article class="panel">([\s\S]*?)<\/article>/g)].map(match=>match[1]);
  assert.equal(panels.length,codes.length*5,'original five metrics per product');
  trendMetrics.forEach((metric,mi)=>codes.forEach((code,ci)=>{
    const panel=panels[mi*codes.length+ci],product=data.products.find(p=>p.code===code);
    assert(panel.includes(escape(product.name+' · '+code)),'trend panel product label');
    assert(panel.includes(escape(metric.label)),'trend panel metric label');
    const titles=[...panel.matchAll(/<title>([\s\S]*?)<\/title>/g)].map(match=>decode(match[1]));
    const expected=data.dates.filter(date=>trendLookup.get(code+'|'+date)?.[metric.key]!=null).map(date=>date+' '+metric.label+'：'+fmt(trendLookup.get(code+'|'+date)[metric.key])+(metric.unit==='%'?'%':''));
    assert.deepEqual(titles,expected,'every rendered trend daily point matches embedded record '+code+' '+metric.key);
    assert(!/NaN|Infinity/.test(panel),'finite trend SVG coordinates');
  }));
  const tables=[...el('tables').innerHTML.matchAll(/<tbody>([\s\S]*?)<\/tbody>/g)].map(match=>match[1]);assert.equal(tables.length,codes.length);
  tables.forEach((table,index)=>{
    const rows=[...table.matchAll(/<tr>([\s\S]*?)<\/tr>/g)].map(match=>[...match[1].matchAll(/<td>([\s\S]*?)<\/td>/g)].map(cell=>strip(cell[1])));
    assert.equal(rows.length,7,'seven actual daily table rows');
    rows.forEach((row,i)=>{const r=trendLookup.get(codes[index]+'|'+data.dates[i]);assert.deepEqual(row,[data.dates[i],fmt(r?.uv),fmt(r?.orders),fmt(r?.favorites),r?.uv>0&&r?.favorites!=null?(r.favorites/r.uv*100).toFixed(2)+'%':'—',r?.conversionPct==null?'—':r.conversionPct.toFixed(2)+'%'],'trend table daily values');});
  });
}
checkTrend(data.cores); // default keeps original 10 core panels, hidden in source view.
el('view-trends').click();trendStateVisible();checkTrend(data.cores);
el('view-channels').click();channelStateVisible();

const rowValues=markup=>[...markup.matchAll(/<tr class="channel-(primary|child)">([\s\S]*?)<\/tr>/g)].map(match=>({kind:match[1],cells:[...match[2].matchAll(/<td\b[^>]*>([\s\S]*?)<\/td>/g)].map(cell=>strip(cell[1]))}));
function verifySource(code) {
  const output=el('channel-section').innerHTML,product=channels.products[code],hasData=observedCodes.includes(code);
  assert(output.includes(escape(code)),'source title uses selected code '+code);
  if(!hasData) {
    assert(output.includes(product?.source_status==='not_exposed_in_backend'?'后台当前未提供该商品的渠道来源明细':'该商品尚无已采集的渠道日数据'),'unavailable product has an accurate status-specific empty state '+code);
    assert(output.includes(escape(product.source_note)),'unavailable product displays its verification note '+code);
    assert(output.includes('可切换“经营趋势”'),'unavailable source preserves business-trend access '+code);
    assert(!output.includes('class="channel-summary"'),'empty product has no fabricated totals');return;
  }
  assert(!output.includes('该商品尚无已采集的渠道日数据'),'observed product is not empty '+code);
  const currentDate=el('channel-current-date').value,previousDate=el('channel-previous-date').value,current=product.days?.[currentDate],previous=product.days?.[previousDate];
  assert(output.includes('全部 PV<strong>'+fmt(current?.total)+'</strong>'),'source total matches selected date '+code);
  const values=rowValues(output);assert.equal(values.filter(r=>r.kind==='primary').length,6,'six primary detail rows');
  channels.channels.forEach(channel=>{
    const row=values.find(r=>r.cells[0]===channel.name);assert(row,'all channel definitions rendered '+channel.name);
    const a=known(current?.values?.[channel.id])?current.values[channel.id]:null,b=known(previous?.values?.[channel.id])?previous.values[channel.id]:null;
    assert.equal(row.cells[1],fmt(a),'current channel value '+code+' '+channel.name);
    assert.equal(row.cells[3],fmt(b),'comparison channel value '+code+' '+channel.name);
    const delta=a!=null&&b!=null?a-b:null,signed=delta==null?'—':(delta>0?'+':delta<0?'−':'')+fmt(Math.abs(delta));
    assert.equal(row.cells[4],signed,'observed channel delta '+code+' '+channel.name);
    assert.equal(row.cells[2],a!=null&&current?.total>0?fmt(a/current.total*100)+'%':'—','product-total share '+code+' '+channel.name);
  });
  assert.equal((output.match(/class="channel-trend-heading"/g)||[]).length,6,'six channel daily charts');
  if(primary.some(channel=>known(current?.values?.[channel.id])&&known(previous?.values?.[channel.id]))) assert.equal((output.match(/class="channel-bar-row"/g)||[]).length,6,'responsive HTML bar rows preserve readable text');
  primary.forEach(channel=>{
    const svg=[...output.matchAll(/<svg\b[^>]*aria-label="([^"]*)"[^>]*>([\s\S]*?)<\/svg>/g)].find(match=>decode(match[1])===channel.name+' 商详访问次数PV按日趋势');assert(svg,'channel line chart '+channel.name);
    const titles=[...svg[2].matchAll(/<title>([\s\S]*?)<\/title>/g)].map(match=>decode(match[1]));
    const expected=channels.dates.filter(date=>known(product.days?.[date]?.values?.[channel.id])).map(date=>date+' '+channel.name+'：'+fmt(product.days[date].values[channel.id])+' PV');
    assert.deepEqual(titles,expected,'channel daily points match actual embedded dates '+code+' '+channel.name);
  });
  assert(!output.includes('后台展示涨跌'),'removed duplicate backend-rate column');
  assert(!/NaN|Infinity/.test(output),'finite channel SVG coordinates');
}
for(const code of allCodes) {el('product').change(code);assert.equal(el('product').value,code);verifySource(code);channelStateVisible();checkTrend([code]);}
el('filter').change('top');
assert.deepEqual(el('product').options.map(option=>option.value),allCodes.slice(0,10),'top10 subset unchanged');assert(el('choice-count').textContent.startsWith('10款'));verifySource(el('product').value);
el('filter').change('new');
const newCodes=data.products.filter(product=>product.backendNew).map(product=>product.code);
assert.deepEqual([...newCodes].sort(),[...backendProducts.values()].filter(product=>product.backendNew).map(product=>product.code).sort(),'all backend-new products retained despite zero data');
assert.deepEqual(el('product').options.map(option=>option.value),newCodes,'new-product subset unchanged');assert(el('choice-count').textContent.startsWith(newCodes.length+'款'));verifySource(el('product').value);
el('filter').change('all');assert.equal(el('product').options.length,allCodes.length);el('product').change(data.cores[0]);
const coreProduct=channels.products[data.cores[0]],coreDates=channels.dates.filter(date=>known(coreProduct.days?.[date]?.total));assert.equal(coreDates.length,7,'first core has seven channel days');
el('channel-current-date').change(coreDates.at(-2));el('channel-previous-date').change(coreDates.at(-3));verifySource(data.cores[0]);
assert(el('channel-section').innerHTML.includes(coreDates.at(-2)+' 对比 '+coreDates.at(-3)),'source date selectors update heading');
el('channel-previous-date').change('');verifySource(data.cores[0]);assert(el('channel-section').innerHTML.includes('暂不计算总增减'),'cleared comparison does not become zero');
el('channel-current-date').change(coreDates.at(-1));el('channel-previous-date').change(coreDates.at(-2));verifySource(data.cores[0]);
el('view-trends').click();trendStateVisible();el('cores').click();checkTrend(data.cores);assert(el('cores').classList.contains('active'),'core mode preserved');
el('single').click();checkTrend([el('product').value]);assert(el('single').classList.contains('active'),'single mode preserved');
el('product').change(data.cores[1]);checkTrend([data.cores[1]]);verifySource(data.cores[1]);
el('view-channels').click();channelStateVisible();verifySource(data.cores[1]);
assert(html.includes('@media(max-width:800px)')&&html.includes('.channel-trends{grid-template-columns:1fr}'),'mobile source charts stack');
assert(html.includes('.channel-section .channel-bar-label{font-size:14px')&&html.includes('.channel-section .channel-bar-value{font-size:14px'),'bar labels and values stay 14px rather than scale with SVG');
assert(html.includes('@media(max-width:480px){.channel-section .channel-axis,.channel-section .channel-point{font-size:24px}'),'narrow channel line-chart labels are enlarged');
console.log(JSON.stringify({result:'PASS',site:sitePath,weeklyBackendBaseline:weeklyPath,scriptsExecuted,defaultView:'channels',products:allCodes.length,channelProducts:observedCodes.length,sourceEmptyStates:missingSourceCodes.length,sourceEmptyCodes:missingSourceCodes,unavailableSourceStatusAndNotesVerified:true,backendScopeRuleVerified:true,sourceAndTrendProductSetsMatch:true,excludedProducts:excluded.length,excludedOldExample:'YX9611001',retainedZeroDataNewExample:'YX9648002',allFocusSelectionVerified:true,observedProductsFinalTwoChannelDaysVerified:true,bothCoreSevenChannelDaysVerified:true,sourceDateSwitchVerified:true,sourceTrendButtonsVerified:true,filters:{top:Math.min(10,allCodes.length),new:newCodes.length},coreTrendPanels:10,singleTrendPanels:5,allRenderedDailyPointsMatchEmbeddedData:true,notes:'Minimal DOM acceptance; actual browser layout still requires root preview.'},null,2));
