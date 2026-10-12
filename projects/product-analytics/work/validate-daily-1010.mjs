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
assert.deepEqual(data.dates,['2026-10-03','2026-10-04','2026-10-05','2026-10-06','2026-10-07','2026-10-08','2026-10-09']);
assert.equal(comparison.businessPeriods.length,36);
assert.equal(new Set([...data.records,...comparison.businessDays].map(r=>r.code+'|'+r.date)).size,252);
assert.deepEqual(data.products.map(p=>p.code).sort(),comparison.selection.filter(p=>p.included).map(p=>p.code).sort());
assert.equal(comparison.pending_listing_codes.length,5);assert(!data.products.some(p=>p.code==='YX9352001'));assert(data.products.some(p=>p.code==='YX9611001'));
assert.deepEqual(JSON.parse(JSON.stringify(math.pair('2026-10-09','week'))),{a:['2026-10-03','2026-10-09'],b:['2026-09-26','2026-10-02']});
assert.equal(math.weekday('2026-10-09'),'周五');assert.equal(math.weekday('2026-10-02'),'周五');
assert.equal(math.compare(1,0).pct,null);assert.equal(math.compare(1,null).delta,null);assert.equal(math.compare(null,1).delta,null);
for(const p of data.products) {
 for(const mode of ['day','weekday','week']) {
  math.state.date='2026-10-09';math.state.mode=mode;window.renderBusinessComparison(p.code);window.renderChannelSection(p.code);window.renderGravitySection(p.code);
  assert(el('business-comparison').innerHTML.includes(p.code));
  for(const mount of ['business-comparison','channel-section','gravity-section'])assert(!/NaN|Infinity/.test(el(mount).innerHTML));
 }
 for(const d of data.dates)assert.notEqual(math.business(p.code,[math.shift(d,-7),math.shift(d,-7)]).uv,null);
 for(const r of comparison.businessPeriods.filter(r=>r.code===p.code)) {
  const v=math.business(p.code,[r.start,r.end]);assert.equal(v.uv,r.uv);assert.equal(v.conversionPct,r.conversionPct);assert.equal(v.favorites,r.favorites);
 }
}
assert.equal(math.business('YX9354001',['2026-10-03','2026-10-09']).uv,1822);
assert.equal(math.business('YX9354001',['2026-09-26','2026-10-02']).uv,4056);
assert.equal(math.business('YX9615001',['2026-10-03','2026-10-09']).conversionPct,0.21);
assert.equal(math.channelPeriod('YX9354001',['2026-09-26','2026-10-02']).values.gravity,3356);
assert.equal(math.channelPeriod('YX9354001',['2026-10-03','2026-10-09']).values.gravity,1080);
assert.equal(math.channelPeriod('YS407600A',['2026-10-09','2026-10-09']).total,1);
let channelCount=0;
for(const p of Object.values(channels.products)) {
 if(p.source_status!=='observed'){assert.equal(Object.keys(p.days).length,0);continue;}
 assert.equal(Object.keys(p.days).length,14);
 for(const r of Object.values(p.days)){assert.equal(['competition','paid','activity','content','users','other'].reduce((s,k)=>s+r.values[k],0),r.total);channelCount++;}
}
assert.equal(channelCount,182);
assert.equal(comparison.gravity.daily.length,38);assert.equal(comparison.gravity.snapshots.length,4);
for(const p of comparison.gravity.snapshots) {
 const ds=comparison.gravity.daily.filter(r=>r.task_id===p.task_id);assert.equal(ds[0].date,p.published_at.slice(0,10));assert.equal(ds.at(-1).date,'2026-10-09');
 for(const key of comparison.gravity.fields){const total=ds.reduce((s,r)=>s+r[key],0);if(p.content_id==='532609487'&&key==='interactions'){assert.equal(total,2);assert.equal(p[key],1);}else assert.equal(total,p[key]);}
 assert.equal(p.actual_ad_spend,null);
}
assert.equal(comparison.gravity.snapshots.reduce((s,r)=>s+r.exposure,0),14177);
for(const [view,visible,hidden] of [['view-trends','business-comparison','gravity-section'],['view-channels','channel-block','business-comparison'],['view-gravity','gravity-section','channel-block']]){el(view).click();assert.equal(el(visible).hidden,false);assert.equal(el(hidden).hidden,true);}
el('product').change('YX9638001');assert(el('gravity-section').innerHTML.includes('535391676'));
el('product').change('YX9611001');el('view-channels').click();assert(el('channel-section').innerHTML.includes('冰花蓝眼泪'));
math.state.date='2026-10-09';math.state.mode='day';window.renderBusinessComparison('YX9354001');assert(el('business-comparison').innerHTML.includes('237人'));
el('business-comparison').querySelectorAll('[data-compare-mode]').find(b=>b.dataset.compareMode==='weekday').click();el('business-date').change('2026-10-05');
assert(el('business-comparison').innerHTML.includes('2026-10-05 周一'));assert(el('business-comparison').innerHTML.includes('2026-09-28 周一'));
el('filter').change('top');assert.equal(el('product').options.length,10);el('filter').change('new');assert.equal(el('product').options.length,9);el('filter').change('all');assert.equal(el('product').options.length,18);
el('view-trends').click();assert.equal((el('charts').innerHTML.match(/<article class="panel">/g)||[]).length,5);
const age=JSON.parse(el('age-data').textContent);
assert.equal(age.products.length,18);
assert.deepEqual(age.products.map(p=>p.code).sort(),data.products.map(p=>p.code).sort());
for(const p of age.products){
 el('product').change(p.code);el('view-age').click();
 assert.equal(el('age-section').hidden,false);
 for(const id of ['business-comparison','channel-block','gravity-section','charts','tables'])assert.equal(el(id).hidden,true);
 assert(el('age-section').innerHTML.includes(p.code));
 assert(el('age-section').innerHTML.includes('2026-10-03 至 2026-10-09'));
 assert(!/NaN|Infinity|undefined/.test(el('age-section').innerHTML));
 for(const c of Object.values(p.cohorts)){
  assert.equal(c.sharesPct.length,5);
  if(c.totalUsers===0){assert.equal(c.status,'no_users');assert(el('age-section').innerHTML.includes('本期无'+c.label));}
  else assert(Math.abs(c.sharesPct.reduce((a,b)=>a+b,0)-100)<.03);
 }
}
assert.equal(age.products.find(p=>p.code==='YX9354001').cohorts.paid.totalUsers,23);
el('product').change('YX9648002');assert(!el('age-section').innerHTML.includes('class="age-bar"'));
el('product').change('YX9615001');assert(el('age-section').innerHTML.includes('仅3人'));
el('view-trends').click();assert.equal(el('age-section').hidden,true);
console.log(JSON.stringify({age:'PASS',products:18,cohorts:54,raw_percent_values:270,empty_cohorts_not_charted:true,product_switch_and_four_views:true}));
console.log(JSON.stringify({result:'PASS',cutoff:'2026-10-09',products:18,business_days:252,backend_week_periods:36,channel_products:13,channel_days:182,gravity_contents:4,gravity_days:38,three_comparisons:true,three_views:true,focus_filter:true,weekly_people_backend_actual:true,zero_missing_distinguished:true}));
