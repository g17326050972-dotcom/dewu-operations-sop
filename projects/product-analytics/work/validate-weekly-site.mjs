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
  querySelectorAll(selector) {
    if(selector!=='[data-compare-mode]') throw new Error('unsupported selector '+selector);
    if(!this._queryButtons) this._queryButtons=[...this._html.matchAll(/<button\b([^>]*)data-compare-mode="([^"]+)"([^>]*)>/g)].map((m,i)=>{const b=new Element('button',this.id+'-mode-'+i,attrs(m[1]+m[3]));b.dataset={compareMode:m[2]};return b;});
    return this._queryButtons;
  }
  get className(){return this._className;}
  set className(value){this._className=String(value);}
  get innerHTML(){return this._html;}
  set innerHTML(value) {
    for(const id of this.ownedIds) elements.delete(id);
    this.ownedIds.clear();this._queryButtons=null;this._html=String(value);this._text=strip(value);
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
const comparison=JSON.parse(el('comparison-data').textContent),math=window.ComparisonMath;
assert.equal(data.products.length,18);assert.equal(data.records.length,126);
assert.equal(comparison.businessPeriods.length,36);
const focused=weekly.rows.filter(r=>r[2]||r[4][1]>0||r[4][7]>0).map(r=>r[0]).sort();
assert.deepEqual(data.products.map(p=>p.code).sort(),focused);
assert.deepEqual(Object.keys(channels.products).sort(),focused);
assert.equal(new Set(data.records.map(r=>r.code+'|'+r.date)).size,126);
assert.equal(math.shift('2026-10-05',-7),'2026-09-28');
assert.equal(math.weekday('2026-10-05'),'周一');assert.equal(math.weekday('2026-09-28'),'周一');
assert.deepEqual(JSON.parse(JSON.stringify(math.pair('2026-10-08','week'))),{a:['2026-10-02','2026-10-08'],b:['2026-09-25','2026-10-01']});
assert.equal(math.compare(1,0).pct,null);assert.equal(math.compare(1,null).delta,null);assert.equal(math.compare(null,1).delta,null);
const rawPrior=JSON.parse(await fs.readFile('/Users/nan/Documents/Codex/2026-10-09/zai/work/prior-week-business-read.json','utf8'));
assert.equal(rawPrior.rows.length,46);assert.equal(new Set(rawPrior.rows.map(r=>r[0])).size,46);
for(const p of data.products) {
  const period=math.business(p.code,['2026-09-25','2026-10-01']), raw=rawPrior.rows.find(r=>r[0]===p.code);
  assert.deepEqual([period.amount,period.conversionPct,period.orders,period.uv,period.favorites],raw.slice(1),'prior week is actual backend period '+p.code);
  const now=math.business(p.code,['2026-10-02','2026-10-08']),original=weekly.rows.find(r=>r[0]===p.code)[4];
  assert.deepEqual([now.amount,now.conversionPct,now.orders,now.uv,now.favorites],[original[0],original[3],original[4],original[6],original[7]]);
  assert.equal(now.favoriteRate,now.uv>0?now.favorites/now.uv*100:null);
  for(const mode of ['day','weekday','week']) {
    math.state.date='2026-10-08';math.state.mode=mode;window.renderBusinessComparison(p.code);window.renderChannelSection(p.code);window.renderGravitySection(p.code);
    assert(el('business-comparison').innerHTML.includes(p.code));
    assert(el('business-comparison').innerHTML.includes('周四'));
    assert(!/NaN|Infinity/.test(el('business-comparison').innerHTML));
    assert(!/NaN|Infinity/.test(el('channel-section').innerHTML));
    assert(!/NaN|Infinity/.test(el('gravity-section').innerHTML));
  }
}
const rateDelta=math.business('YX9354001',['2026-10-02','2026-10-08']).favoriteRate-160/2182*100;
assert.equal(rateDelta,0);
const coreWeek=math.business('YX9354001',['2026-10-02','2026-10-08']);
assert.equal(coreWeek.uv,2182);
assert.equal(coreWeek.uv,comparison.businessPeriods.find(r=>r.code==='YX9354001'&&r.start==='2026-10-02').uv,'weekly UV matches observed backend period');
assert.equal(math.business('YX9354001',['2026-09-25','2026-10-01']).uv,4094);
assert.equal(math.channelPeriod('YX9354001',['2026-10-01','2026-10-01']).total,723);
assert.equal(math.channelPeriod('YX9354001',['2026-10-02','2026-10-08']).total,data.dates.reduce((s,d)=>s+channels.products.YX9354001.days[d].total,0));
assert.equal(math.channelPeriod('YX9354001',['2026-09-25','2026-10-01']).total,4974);
assert.equal(math.business('YX9354001',['2026-10-01','2026-10-01']).uv,597);
math.state.mode='weekday';math.state.date='2026-10-08';window.renderChannelSection('YX9354001');
assert(el('channel-section').innerHTML.includes('−435'));assert(el('channel-section').innerHTML.includes('−60.17%'));
assert(el('channel-section').innerHTML.includes('2026-10-01 周四'));
math.state.mode='week';window.renderBusinessComparison('YX9354001');
assert(el('business-comparison').innerHTML.includes('2,182人'));assert(el('business-comparison').innerHTML.includes('4,094人'));
assert(el('business-comparison').innerHTML.includes('个百分点'));
el('business-comparison').querySelectorAll('[data-compare-mode]').find(b=>b.dataset.compareMode==='weekday').click();
el('business-date').change('2026-10-05');
assert(el('business-comparison').innerHTML.includes('2026-10-05 周一'));assert(el('business-comparison').innerHTML.includes('2026-09-28 周一'));
assert(!el('business-comparison').innerHTML.includes('待补采'));
el('view-trends').click();assert.equal(el('business-comparison').hidden,false);assert.equal(el('gravity-section').hidden,true);assert.equal(el('channel-block').hidden,true);
el('view-channels').click();assert.equal(el('channel-block').hidden,false);assert.equal(el('business-comparison').hidden,true);assert.equal(el('charts').hidden,true);
el('view-gravity').click();assert.equal(el('gravity-section').hidden,false);assert.equal(el('channel-block').hidden,true);assert.equal(el('charts').hidden,true);
el('product').change('YX9638001');
assert(el('gravity-section').innerHTML.includes('535391676'));assert(el('gravity-section').innerHTML.includes('96次'));
assert.equal(comparison.businessDays.length,126);
assert.equal(comparison.gravity.daily.length,38);
assert.equal(comparison.gravity.snapshots.length,4);
for(const p of comparison.gravity.snapshots) {
 const daily=comparison.gravity.daily.filter(r=>r.task_id===p.task_id);
 assert(daily.length>0);assert.equal(daily[0].date,p.published_at.slice(0,10));assert.equal(daily.at(-1).date,'2026-10-09');
 for(const key of comparison.gravity.fields) {
  const total=daily.reduce((s,r)=>s+r[key],0);
  if(p.task_id==='S17891134954148398'&&key==='interactions') {assert.equal(total,2);assert.equal(p[key],1);assert(p.notes.some(n=>n.includes('互动')));}
  else assert.equal(total,p[key],p.task_id+' '+key);
 }
 assert.equal(p.actual_ad_spend,null);
}
assert.equal(comparison.gravity.snapshots.reduce((s,r)=>s+r.exposure,0),14177);
assert.equal(comparison.gravity.snapshots.reduce((s,r)=>s+r.reads,0),561);
assert.equal(comparison.gravity.snapshots.reduce((s,r)=>s+r.detail_visits,0),118);
assert.equal(comparison.gravity.window.export_task_count,63);
for(const code of comparison.coverage.channel_unavailable_products) assert.equal(Object.keys(channels.products[code].days).length,0);
for(const p of Object.values(channels.products).filter(p=>p.source_status==='observed')) {
 assert.equal(Object.keys(p.days).length,14);
 for(const day of Object.values(p.days)) assert.equal(['competition','paid','activity','content','users','other'].reduce((s,k)=>s+day.values[k],0),day.total);
 for(const d of data.dates) {
  const last=math.shift(d,-7);assert.notEqual(math.channelPeriod(p.code,[last,last]).total,null);
 }
}
for(const p of data.products) for(const d of data.dates) {
 const last=math.shift(d,-7);assert.notEqual(math.business(p.code,[last,last]).uv,null);
}
math.state.date='2026-10-08';math.state.mode='week';
assert.equal(math.channelPeriod('YX9354001',['2026-09-25','2026-10-01']).values.gravity,3447);
assert.equal(math.channelPeriod('YX9615001',['2026-09-25','2026-10-01']).values.gravity,584);
assert.equal(math.channelPeriod('YX9339001',['2026-10-02','2026-10-08']).values.gravity,57);
el('product').change('YX9648002');assert(el('gravity-section').innerHTML.includes('对应 0条近月内容'));
el('product').change('YX9341001');el('view-channels').click();assert(el('channel-section').innerHTML.includes('后台当前未提供'));
el('filter').change('top');assert.equal(el('product').options.length,10);
el('filter').change('new');assert.equal(el('product').options.length,9);
el('filter').change('all');assert.equal(el('product').options.length,18);
el('view-trends').click();assert.equal((el('charts').innerHTML.match(/<article class="panel">/g)||[]).length,5);
console.log(JSON.stringify({result:'PASS',products:18,business_day_records:252,channel_day_records:168,actual_backend_week_periods:36,all_three_comparison_modes_verified:true,same_weekday_dates_verified:true,weekly_people_not_summed:true,verified_gravity_contents:4,verified_gravity_content_days:38,reconciliation_difference_preserved:true,missing_source_and_ad_spend_not_zeroed:true,all_three_views_verified:true},null,2));
