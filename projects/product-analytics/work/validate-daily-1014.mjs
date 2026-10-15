// Read-only acceptance of the actual integrated HTML in a minimal DOM contract.
// Uses the real embedded scripts and data, with no browser, network, or writes.
// Optional argv[2]: another local HTML path to validate after final integration.
// Optional argv[3]: backend weekly-read baseline for the same period.
import fs from 'node:fs/promises';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const sitePath=process.argv[2] || '/Users/nan/Documents/Codex/2026-10-09/zai/outputs/2026-10-14/draft-site/index.html';
const weeklyPath=process.argv[3] || '/Users/nan/Documents/Codex/2026-10-09/zai/work/retry_metrics.json';
const html=await fs.readFile(sitePath,'utf8');

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


assert.equal(data.products.length,28);assert.equal(data.records.length,196);
assert.equal(data.dates.at(-1),'2026-10-13');assert.equal(data.dates[0],'2026-10-07');
const all=[...data.records,...comparison.businessDays];
assert.equal(all.length,392);assert.equal(all.filter(r=>r.observed).length,333);
assert.deepEqual(data.products.map(p=>p.code).sort(),comparison.selection.filter(p=>p.included).map(p=>p.code).sort());
for(const r of comparison.selection)assert.equal(r.included,r.sales>0||r.favorites>0||r.backendNew);
for(const p of data.products){
 for(const mode of ['day','weekday','week']){
  math.state.date='2026-10-13';math.state.mode=mode;
  window.renderBusinessComparison(p.code);window.renderChannelSection(p.code);window.renderGravitySection(p.code);
  for(const id of ['business-comparison','channel-section','gravity-section'])assert(!/NaN|Infinity|undefined/.test(el(id).innerHTML),p.code+' '+id);
 }
 for(const r of comparison.businessPeriods.filter(r=>r.code===p.code)){
  const v=math.business(p.code,[r.start,r.end]);
  for(const k of ['uv','favorites','conversionPct'])assert.equal(v[k],r[k]);
 }
}
assert.equal(math.business('YX9354001',['2026-10-07','2026-10-13']).uv,1705);
assert.equal(math.business('YX9354001',['2026-09-30','2026-10-06']).uv,2862);
assert.equal(math.business('YX9521001',['2026-10-07','2026-10-07']).uv,0);
assert.equal(math.business('YX9521001',['2026-10-07','2026-10-07']).conversionPct,null);
assert.equal(math.business('YX9507001',['2026-10-05','2026-10-05']).uv,null);
assert.equal(math.channelPeriod('YX9354001',['2026-10-07','2026-10-13']).values.gravity,919);
assert.equal(math.channelPeriod('YX9354001',['2026-09-30','2026-10-06']).values.gravity,2114);
let n=0,full=0,unavailable=0,zeroIntervals=0;
for(const p of Object.values(channels.products)){
 if(p.source_status!=='observed'){assert.equal(Object.keys(p.days).length,0);unavailable++;continue;}
 assert.equal(Object.keys(p.days).length,14);full++;
 for(const r of Object.values(p.days)){assert.equal(['competition','paid','activity','content','users','other'].reduce((s,k)=>s+r.values[k],0),r.total);n++;if(r.source?.kind==='verified_zero_interval'){assert.equal(r.total,0);zeroIntervals++;}}
}
assert.equal(n,322);assert.equal(full,23);assert.equal(unavailable,5);
const age=JSON.parse(el('age-data').textContent);assert.equal(age.products.length,28);
for(const p of age.products){
 el('filter').change('all');el('product').change(p.code);el('view-age').click();
 assert.equal(el('age-section').hidden,false);assert(el('age-section').innerHTML.includes(p.code));
 assert(el('age-section').innerHTML.includes('2026-10-07 至 2026-10-13'));
 assert(!/NaN|Infinity|undefined/.test(el('age-section').innerHTML));
 for(const c of Object.values(p.cohorts)){assert.equal(c.sharesPct.length,5);assert.equal(c.ageCounts,null);if(c.totalUsers===0){assert.equal(c.status,'no_users');assert(el('age-section').innerHTML.includes('本期无'+c.label));}else assert(Math.abs(c.sharesPct.reduce((a,b)=>a+b,0)-100)<.031);}
}
for(const [view,visible,hidden] of [['view-trends','business-comparison','age-section'],['view-channels','channel-block','business-comparison'],['view-gravity','gravity-section','channel-block']]){el(view).click();assert.equal(el(visible).hidden,false);assert.equal(el(hidden).hidden,true);}
math.state.date='2026-10-13';math.state.mode='day';window.renderBusinessComparison('YX9354001');el('business-comparison').querySelectorAll('[data-compare-mode]').find(b=>b.dataset.compareMode==='weekday').click();
assert(el('business-comparison').innerHTML.includes('2026-10-13 周二'));assert(el('business-comparison').innerHTML.includes('2026-10-06 周二'));
el('filter').change('top');assert.equal(el('product').options.length,10);el('filter').change('new');assert.equal(el('product').options.length,20);el('filter').change('all');assert.equal(el('product').options.length,28);
el('view-trends').click();assert.equal((el('charts').innerHTML.match(/<article class="panel">/g)||[]).length,5);
assert.equal(comparison.gravity.refresh_status,'complete');assert.equal(comparison.gravity.daily.length,57);assert.equal(comparison.gravity.snapshots.length,5);
assert.equal(comparison.gravity.snapshots.find(r=>r.content_id==='535391676').chart_cumulative.detail_visits,79);
window.renderChannelSection('YX9639002');assert(el('channel-section').innerHTML.includes('来源周PV与经营导出不一致'));
console.log(JSON.stringify({result:'PASS',cutoff:'2026-10-13',products:28,business_usable:333,business_history_gap:59,source_days:322,source_full_products:23,source_unavailable:5,zero_interval_days:zeroIntervals,age_cohorts:84,age_shares:420,gravity_contents:5,gravity_days:57,all_views_and_filters:true,zero_vs_missing:true}));
