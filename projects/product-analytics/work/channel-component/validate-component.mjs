// Component-only DOM contract test. All numbers below are synthetic fixtures.
// Does not load a browser, access live data, or modify the Site checkout.
import fs from 'node:fs/promises';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const folder=path.dirname(fileURLToPath(import.meta.url));
const script=await fs.readFile(path.join(folder,'channel-section.js'),'utf8');
const css=await fs.readFile(path.join(folder,'channel-section.css'),'utf8');
const elements=new Map();
class Element {
  constructor(id){this.id=id;this.value='';this.handlers={};this._html='';}
  set innerHTML(value){
    this._html=value;
    for(const match of value.matchAll(/<select id="([^"]+)"[^>]*>(.*?)<\/select>/gs)) {
      const child=new Element(match[1]);
      const options=[...match[2].matchAll(/<option value="([^"]*)"([^>]*)>/g)];
      child.value=(options.find(option=>/\bselected\b/.test(option[2]))||options[0])?.[1]??'';
      elements.set(child.id,child);
    }
  }
  get innerHTML(){return this._html;}
  addEventListener(name,handler){this.handlers[name]=handler;}
  change(value){this.value=value;this.handlers.change?.({target:this});}
}
const mount=new Element('channel-section');elements.set(mount.id,mount);
const document={getElementById:id=>elements.get(id)||null};
const channels=[
  {id:'competition',name:'商品竞争力',parent_id:null},
  {id:'recommend',name:'商品推荐',parent_id:'competition'},
  {id:'search',name:'商品搜索',parent_id:'competition'},
  {id:'paid',name:'付费推广',parent_id:null},
  {id:'push',name:'得物推',parent_id:'paid'},
  {id:'gravity',name:'引力',parent_id:'paid'},
  {id:'activity',name:'平台活动',parent_id:null},
  {id:'content',name:'内容自运营',parent_id:null},
  {id:'users',name:'用户运营',parent_id:null},
  {id:'other',name:'其他',parent_id:null}
];
const previous={total:260,values:{competition:100,recommend:10,search:90,paid:100,push:0,gravity:100,activity:0,content:20,users:10,other:30}};
const current={total:240,values:{competition:80,recommend:10,search:70,paid:120,push:0,gravity:120,activity:0,content:10,users:0,other:30},reported_changes:{total:{pct:-7.69,comparison_date:'2026-10-07'},competition:{pct:-20,comparison_date:'2026-10-07'}}};
const data={dates:['2026-10-06','2026-10-07','2026-10-08'],channels,products:{'TEST-ONLY':{name:'测试用合成数据',days:{'2026-10-06':structuredClone(previous),'2026-10-07':structuredClone(previous),'2026-10-08':structuredClone(current)}}}};
const window={CHANNEL_DATA:data};
vm.runInNewContext(script,{window,document,Map,Set,Number,String,Math,Array,Object});
assert.equal(typeof window.renderChannelSection,'function');
window.renderChannelSection('TEST-ONLY');
let html=mount.innerHTML;
assert.equal((html.match(/class="channel-primary"/g)||[]).length,6,'six primary rows');
assert.equal((html.match(/class="channel-child"/g)||[]).length,4,'four child rows');
assert.equal((html.match(/class="channel-trend-heading"/g)||[]).length,6,'six daily charts');
assert.equal((html.match(/class="channel-bar-row"/g)||[]).length,6,'six responsive HTML bars instead of shrinking SVG text');
assert(html.includes('class="channel-bar-fill channel-bar-fill-negative" style="width:50%"'),'largest decline fills its negative half of the shared bar scale');
assert(html.includes('class="channel-bar-fill channel-bar-fill-positive" style="width:50%"'),'equally large increase fills its positive half');
assert(html.includes('全部 PV<strong>240</strong>'),'backend total remains 240, children not added twice');
assert(html.includes('>−20</strong>'),'total delta is negative 20');
assert(html.includes('>−7.69%</small>'),'total relative change uses observed base');
assert(html.includes('减少最多的一级渠道为 商品竞争力 −20 PV、内容自运营 −10 PV、用户运营 −10 PV；增加渠道合计抵消 20 PV'),'decline insight uses three largest primary reductions and gross positive offset');
assert(!html.includes('后台展示涨跌')&&!html.includes('后台全部 PV 展示涨跌'),'backend reported rates are not duplicated in UI');
assert.equal(data.products['TEST-ONLY'].days['2026-10-08'].reported_changes.total.pct,-7.69,'original backend reported data retained');
assert(html.includes('<td>50%</td>'),'competition accounts for half of gross decline');
assert(html.includes('<td>4.17%</td>'),'child share denominator is product total, not parent');
assert(html.includes('<td>0</td>'),'observed zero retained');
assert(!html.includes('NaN')&&!html.includes('Infinity'),'finite SVG and labels');
data.products['TEST-ONLY'].days['2026-10-07'].total=270;
window.renderChannelSection('TEST-ONLY');
assert(mount.innerHTML.includes('对比日一级渠道合计 260 PV，与后台全部 270 PV 不一致'),'comparison aggregate mismatch is visible');
assert(mount.innerHTML.includes('尚未通过核对，下降渠道内份额留空'),'mismatched aggregates suppress decline shares');
assert(!mount.innerHTML.includes('class="channel-change-insight"'),'aggregate mismatch suppresses directional insight');
data.products['TEST-ONLY'].days['2026-10-07'].total=260;
window.renderChannelSection('TEST-ONLY');
elements.get('channel-current-date').change('2026-10-07');
html=mount.innerHTML;
assert(html.includes('全部 PV<strong>260</strong>'),'date selector re-renders current observed total');
assert(html.includes('>0</strong>'),'same selected dates compute zero change');
assert(html.includes('总 PV 持平：6 个一级渠道均无增减'),'flat totals receive a non-causal factual summary');
elements.get('channel-previous-date').change('2026-10-08');
assert(mount.innerHTML.includes('增加最多的一级渠道为 商品竞争力 +20 PV、内容自运营 +10 PV、用户运营 +10 PV；减少渠道合计抵消 20 PV'),'positive total change reverses insight and uses gross negative offset');
elements.get('channel-current-date').change('2026-10-08');
elements.get('channel-previous-date').change('2026-10-06');
assert(mount.innerHTML.includes('2026-10-08 对比 2026-10-06'),'comparison selector re-renders dates');
// A missing middle channel point must break the line and suppress incomplete-share calculations.
data.products['TEST-ONLY'].days['2026-10-07'].values.competition=null;
elements.get('channel-previous-date').change('2026-10-07');
html=mount.innerHTML;
assert(html.includes('下降渠道内份额留空'),'incomplete primary pair prevents misleading decline shares');
assert(!html.includes('class="channel-change-insight"'),'incomplete primary values suppress directional insight');
const competitionChart=html.match(/<svg[^>]+aria-label="商品竞争力 商详访问次数PV按日趋势"[\s\S]*?<\/svg>/)?.[0];
assert(competitionChart&&!competitionChart.includes('<polyline'),'missing middle point prevents bridging known endpoints');
assert(competitionChart.includes('缺失'),'missing point explicitly labeled');
assert(competitionChart.includes('y="263" text-anchor="middle" class="channel-axis"')&&competitionChart.includes('y="293" text-anchor="middle" class="channel-missing"'),'date and missing-label baselines have 30 SVG units of separation');
assert([...competitionChart.matchAll(/<text[^>]+y="([\d.]+)"[^>]+class="channel-point"/g)].every(match=>Number(match[1])>=26),'enlarged maximum-value labels stay inside top SVG boundary');
assert(html.includes('<td class="channel-negative">—</td>')===false,'missing deltas do not receive a false decline style');
// Missing comparison totals and channels do not become zero or get reverse-derived from backend rates.
data.products['TEST-ONLY'].days['2026-10-07']=null;
window.renderChannelSection('TEST-ONLY');
html=mount.innerHTML;
assert(html.includes('增减图需要两个日期的实采渠道 PV'),'no exact delta bars with unobserved comparison');
assert(html.includes('暂不计算总增减'),'no reconstructed comparison total');
assert(!html.includes('class="channel-change-insight"'),'missing comparison suppresses directional insight');
// A newly observed third competition child is rendered dynamically without double counting.
data.products['TEST-ONLY'].days['2026-10-07']=structuredClone(previous);
data.channels.push({id:'new_product_support',name:'新品保量',parent_id:'competition'});
data.products['TEST-ONLY'].days['2026-10-08'].values.new_product_support=3;
data.products['TEST-ONLY'].days['2026-10-08'].values.search=67;
data.products['TEST-ONLY'].days['2026-10-07'].values.new_product_support=0;
window.renderChannelSection('TEST-ONLY');
assert.equal((mount.innerHTML.match(/class="channel-child"/g)||[]).length,5,'new competition child renders dynamically');
assert(mount.innerHTML.includes('<td>新品保量</td><td>3</td><td>1.25%</td>'),'new child uses product total share denominator');
assert(mount.innerHTML.includes('全部 PV<strong>240</strong>'),'new child does not inflate total');
assert(mount.innerHTML.includes('class="channel-change-insight"'),'new child does not alter verified primary aggregate logic');
window.renderChannelSection('NOT-COLLECTED');
assert(mount.innerHTML.includes('该商品尚无已采集的渠道日数据'),'uncollected product gives empty state');
data.products['BACKEND-NOT-EXPOSED']={name:'无来源明细测试',source_status:'not_exposed_in_backend',source_note:'只提供核心指标，无流量分析/渠道明细入口 <已核验>',days:{}};
window.renderChannelSection('BACKEND-NOT-EXPOSED');
assert(mount.innerHTML.includes('后台当前未提供该商品的渠道来源明细'),'backend missing-capability status has a precise empty state');
assert(mount.innerHTML.includes('核验说明：只提供核心指标，无流量分析/渠道明细入口 &lt;已核验&gt;'),'verification note is displayed and escaped');
assert(mount.innerHTML.includes('可切换“经营趋势”'),'existing business trends remain available');
assert(!mount.innerHTML.includes('class="channel-summary"'),'unavailable backend source does not fabricate PV totals');
assert(css.includes('@media(max-width:800px)')&&css.includes('.channel-trends{grid-template-columns:1fr}'),'mobile chart panels stack');
assert(css.includes('.channel-table-scroll{overflow:auto'),'full detail table can scroll');
assert(css.includes('.channel-section .channel-bar-label{font-size:14px')&&css.includes('.channel-section .channel-bar-value{font-size:14px'),'bar labels and values retain actual 14px text on narrow panels');
assert(css.includes('@media(max-width:480px){.channel-section .channel-axis,.channel-section .channel-point{font-size:24px}'),'narrow-screen channel SVG text is enlarged without changing desktop font sizes');
console.log('PASS: totals, dynamic hierarchy/new-product support, child shares, true zero, missing-point gaps, date controls, verified decline/increase summaries, retained source rates, explained backend-unavailable empty state, fixed-size HTML bar text and narrow-screen line-chart labels.');
