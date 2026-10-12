import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

// Usage: node work/report/build_report.mjs --authoring-marked [output.xlsx]
// collect_report.py must run immediately before this builder so the ledger is
// read afresh. An activity-ready plan does not establish an enrollment.
const here = path.dirname(new URL(import.meta.url).pathname);
const root = path.resolve(here, '../..');
if (!process.argv.includes('--authoring-marked')) throw Error('Run the skill authoring marker before the first build.');
const outputPath = process.argv.find(a => a.endsWith('.xlsx')) ?? path.join(root, 'outputs/报名汇总.xlsx');
const data = JSON.parse(await fs.readFile(path.join(here, 'report_data.json'), 'utf8'));
const workbook = Workbook.create();
const detail = workbook.worksheets.add('报名明细');
const activities = workbook.worksheets.add('活动概览');
const color = '#48344A';
const light = '#F6F1F6';
const head = 9;
const first = head + 1;
const last = head + data.rows.length;
const aHead = 10;
const aFirst = aHead + 1;
const aLast = aHead + data.activities.length;
const font = 'Helvetica Neue';
const columns = [
  ['货号',16], ['规格',33], ['活动',34], ['活动开始',22], ['活动结束',22], ['报名状态',21],
  ['原出价（元）',14], ['已配折扣',12], ['报名/拟报名价（元）',17], ['实际价格折扣',14],
  ['额外满减规则',34], ['商家满减承担（元）',17], ['预估到手价（元）',17],
  ['活动毛利额（元）',16], ['活动毛利率',14], ['渠道',13], ['活动库存',13], ['记录来源',19],
  ['SKU ID',16], ['SPU ID',14], ['活动 ID',14], ['商品成本（元）',15], ['礼盒增量（元）',15],
  ['平台费用（元）',15], ['履约成本（元）',15], ['货盘10%扣减（元）',18],
  ['其他活动扣减（元）',18], ['到手价依据',48], ['备注',51], ['数据来源',42],
];
function col(n) { let out='';for(n++;n>0;n=Math.floor((n-1)/26))out=String.fromCharCode(65+(n-1)%26)+out;return out; }
function date(value) {
  if (!value) return '待补录';
  if (/^\d{4}-\d{2}-\d{2}/.test(value)) {
    const d = new Date(value.replace(' ', 'T').replace(/[+]08:00$/, '') + (/Z$/.test(value) ? '' : 'Z'));
    if (!Number.isNaN(d.getTime())) return d;
  }
  return value;
}
function origin(value) {
  if (value === 'hold') return '未提交方案';
  if (value === 'failed') return '本次提交失败';
  if (value.startsWith('existing')) return '原有报名，保留';
  return '本次新增报名';
}
function sourceName(value, activityName) {
  if (value.includes('失败日志')) return '得物报名失败日志';
  if (value.startsWith('/')) return `得物已报名商品导出（${activityName}）`;
  return value;
}
for (const sheet of [detail, activities]) {
  sheet.showGridLines = false;
  sheet.tabColor = color;
}
detail.getRange(`A1:AD${last}`).format.font = {name:font,size:10,color:'#242424'};
detail.getRange(`A1:AD${last}`).format.verticalAlignment = 'center';
detail.getRange(`A1:AD${last}`).format.rowHeight = 35;
detail.getRange('A2').values = [['得物商家活动报名汇总']];
detail.getRange('A2').format.font = {name:font,size:15,bold:true,color};
detail.getRange('A2:AD2').format.borders = {bottom:{style:'thin',color}};
detail.getRange('A3').values = [[`统计时点：${data.as_of.replace('T',' ')}  状态：${data.phase}`]];
detail.getRange('A4').values = [[`本次新增提交 ${data.summary.new_submitted_sku} 条 SKU 活动记录；现有已报 ${data.summary.registered_sku_records} 条（含原有 ${data.summary.registered_sku_records-data.summary.new_submitted_sku} 条），涉及 ${data.summary.registered_articles} 款；提交失败 ${data.summary.failed_sku_records??0} 条、未报名待确认 ${data.summary.held_sku_records} 条另列。`]];
detail.getRange('A5').values = [['到手价列为扣商家优惠后的商品预估金额，未扣平台费用和成本，不等于消费者实付款或商家净利润。']];
detail.getRange('A6').values = [['满减在商品折后继续扣除，门槛按原出价判断；商家承担额单列，避免把报名价当作最终到手。']];
detail.getRange('A7').values = [['毛利保留货盘活动公式的 22%（最低45元）费用、14.5元履约及10%扣减，另扣升级礼盒和商家满减承担额。']];
detail.getRange('A8').values = [['到手价依据逐行区分后台核实、条件测算及规则测算；测算不代表后台展示或最终成交，待确认行尚未报名。']];
detail.getRange('A3:A8').format.font = {name:font,size:10,color:'#595959'};
detail.getRange(`A${head}:AD${head}`).values = [columns.map(c=>c[0])];
const values = data.rows.map(r => [
  r.article_no, r.style, r.activity_name + (r.registration_discount_input ? `（${r.origin==='hold'?'拟填':'填报'}${r.registration_discount_input}折）` : ''), date(r.start), date(r.end), r.status,
  r.current_bid ?? r.current_bid_display ?? '待补充', r.configured_discount, r.registration_price ?? '不适用/待补充', null,
  r.full_reduction_rule, r.extra_merchant_reduction ?? '待核实', r.estimated_received ?? '待核实', null, null,
  r.channel, r.inventory, origin(r.origin), r.sku_id, r.spu_id, r.activity_id,
  r.product_cost, r.giftbox_incremental_cost, null, null, null,
  r.extra_activity_rate * (r.registration_price ?? 0) + r.extra_activity_fixed,
  `${r.estimate_mode}：${r.estimate_evidence}`, r.notes + (r.origin==='hold' ? `；拟报名方案，${r.status.includes('已确认')?'用户已确认待提交':'等待用户确认'}` : ''),
  sourceName(r.source,r.activity_name),
]);
if (values.length) detail.getRange(`A${first}:AD${last}`).values = values;
for (let index=0;index<data.rows.length;index++) {
  const r = first+index;
  detail.getRange(`J${r}`).formulas = [[`=IF(ISNUMBER(I${r}),IF(ISNUMBER(G${r}),I${r}/G${r}*10,"待补充"),"不适用")`]];
  detail.getRange(`X${r}`).formulas = [[`=IF(ISNUMBER(I${r}),MAX(I${r}*'活动概览'!$B$6,'活动概览'!$D$6),"不适用")`]];
  detail.getRange(`Y${r}`).formulas = [[`='活动概览'!$F$6`]];
  detail.getRange(`Z${r}`).formulas = [[`=IF(ISNUMBER(I${r}),I${r}*'活动概览'!$H$6,"不适用")`]];
  detail.getRange(`N${r}`).formulas = [[`=IF(ISNUMBER(I${r}),IF(ISNUMBER(L${r}),I${r}-X${r}-Y${r}-Z${r}-V${r}-W${r}-L${r}-AA${r},"待核实"),"不适用")`]];
  detail.getRange(`O${r}`).formulas = [[`=IF(ISNUMBER(N${r}),N${r}/I${r},IF(ISNUMBER(I${r}),"待核实","不适用"))`]];
}
for(let i=0;i<columns.length;i++)detail.getRange(`${col(i)}1:${col(i)}${last}`).format.columnWidth=columns[i][1];
detail.getRange(`A${head}:AD${head}`).format={fill:color,font:{name:font,size:10,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',wrapText:true,rowHeight:39};
detail.getRange(`A${first}:AD${last}`).format.verticalAlignment='center';
detail.getRange(`B${first}:F${last}`).format.wrapText=true;
detail.getRange(`K${first}:K${last}`).format.wrapText=true;
detail.getRange(`AB${first}:AD${last}`).format.wrapText=true;
for(let i=0;i<data.rows.length;i++){
  if(data.rows[i].origin==='failed')
    detail.getRange(`A${first+i}:AD${first+i}`).format.rowHeight=75;
  else if(data.rows[i].estimate_mode==='条件测算' || data.rows[i].activity_id==='3368291')
    detail.getRange(`A${first+i}:AD${first+i}`).format.rowHeight=65;
  else if(data.rows[i].estimate_mode.includes('范围') || data.rows[i].estimate_mode.includes('取整'))
    detail.getRange(`A${first+i}:AD${first+i}`).format.rowHeight=75;
}
detail.getRange(`D${first}:E${last}`).setNumberFormat('yyyy-mm-dd hh:mm');
for(const c of ['G','I','L','M','N','V','W','X','Y','Z','AA'])detail.getRange(`${c}${first}:${c}${last}`).setNumberFormat('#,##0.00;[Red](#,##0.00);0.00');
detail.getRange(`H${first}:H${last}`).setNumberFormat('0.00"折"');
detail.getRange(`J${first}:J${last}`).setNumberFormat('0.00"折"');
detail.getRange(`O${first}:O${last}`).setNumberFormat('0.00%');
detail.getRange(`G${first}:O${last}`).format.horizontalAlignment='right';
detail.getRange(`S${first}:U${last}`).setNumberFormat('@');
detail.getRange(`A${first}:AD${last}`).conditionalFormats.addCustom(`=$R${first}="未提交方案"`,{fill:'#FFF1CD'});
detail.getRange(`A${first}:AD${last}`).conditionalFormats.addCustom(`=$R${first}="本次提交失败"`,{fill:'#FDE9E7'});
detail.getRange(`F${first}:F${last}`).conditionalFormats.add('containsText',{text:'审核中',format:{fill:'#FFF1CD',font:{color:'#805300'}}});
detail.getRange(`O${first}:O${last}`).conditionalFormats.add('cellIs',{operator:'lessThanOrEqual',formula:0.03,format:{fill:'#FDE9E7',font:{color:'#9C1D18',bold:true}}});
detail.getRange(`A${head}:AD${last}`).format.borders={bottom:{style:'thin',color:'#DDD5DD'}};
const dTable=detail.tables.add(`A${head}:AD${last}`,true,'EnrollmentDetails');
dTable.style='TableStyleLight1';
dTable.showFilterButton=true;
detail.freezePanes.freezeRows(head);
detail.freezePanes.freezeColumns(2);

const aColumns = [
  ['活动 ID',14],['活动名称',36],['活动开始',22],['活动结束',22],['处理结果',25],
  ['本次提交SKU数',17],['现有报名SKU数',17],['有效/成功SKU数',18],['审核中SKU数',16],
  ['待提交/确认SKU数',19],['已报名货号',64],['未报名原因/备注',56],['叠加规则',65],
];
activities.getRange(`A1:M${aLast+9}`).format.font={name:font,size:10,color:'#242424'};
activities.getRange(`A1:M${aLast+9}`).format.verticalAlignment='center';
activities.getRange(`A1:M${aLast+9}`).format.rowHeight=36;
activities.getRange('A2').values=[['活动处理概览']];
activities.getRange('A2').format.font={name:font,size:15,bold:true,color};
activities.getRange('A2:M2').format.borders={bottom:{style:'thin',color}};
activities.getRange('A3').values=[[`统计时点：${data.as_of.replace('T',' ')}  状态：${data.phase}`]];
activities.getRange('A4').values=[['本次提交']];
activities.getRange('B4').formulas=[[`=SUM(F${aFirst}:F${aLast})`]];
activities.getRange('C4').values=[['现有报名']];
activities.getRange('D4').formulas=[[`=SUM(G${aFirst}:G${aLast})`]];
activities.getRange('E4').values=[['待提交/确认']];
activities.getRange('F4').formulas=[[`=SUM(J${aFirst}:J${aLast})`]];
activities.getRange('G4').values=[['提交失败']];
activities.getRange('H4').formulas=[[`=COUNTIFS('报名明细'!R${first}:R${last},"本次提交失败")`]];
for(const c of ['B4','D4','F4','H4'])activities.getRange(c).format={fill:light,horizontalAlignment:'center',font:{name:font,size:12,bold:true,color}};
activities.getRange('A6:J6').values=[['平台费率',0.22,'最低平台费（元）',45,'履约成本（元）',14.5,'货盘额外扣减率',0.10,'毛利门槛',0.03]];
activities.getRange('B6').setNumberFormat('0%');activities.getRange('H6').setNumberFormat('0%');activities.getRange('J6').setNumberFormat('0%');
for(const c of ['B6','D6','F6','H6','J6'])activities.getRange(c).format.horizontalAlignment='center';
activities.getRange('A7').values=[['毛利率分母为报名价；礼盒“钟意一生/炽热挚爱/炽烈挚爱”各增加13元成本。活动审批结果可能更新。']];
activities.getRange('A8').values=[['满300减50的原有券参与记录没有独立报名售价，未以后台9999占位数计算折扣或毛利。']];
activities.getRange(`A${aHead}:M${aHead}`).values=[aColumns.map(c=>c[0])];
function stageName(a) {
  if(a.failed_sku)return `提交失败（${a.failed_sku} SKU）`;
  if(a.stage.startsWith('skipped'))return '未报名';
  if(a.stage==='already_enrolled')return '原有报名，保留';
  if(a.stage.includes('await_readback'))return '已提交，逐SKU待读回';
  if(a.pending_sku)return '已提交，部分审核中';
  if(a.registered_sku)return '报名成功';
  if(a.held_sku)return a.moon_user_confirmed?'用户已确认，待提交':'待用户确认';
  return '核查中';
}
activities.getRange(`A${aFirst}:M${aLast}`).values=data.activities.map(a=>[
  a.activity_id,a.name,a.start?date(a.start):'不适用',a.end?date(a.end):'不适用',stageName(a),a.new_submitted_sku,
  a.registered_sku,a.valid_sku,a.pending_sku??'待读回',a.held_sku,a.articles.join('、'),a.reason,a.stacking,
]);
for(let i=0;i<aColumns.length;i++)activities.getRange(`${col(i)}1:${col(i)}${aLast+9}`).format.columnWidth=aColumns[i][1];
activities.getRange(`A${aHead}:M${aHead}`).format={fill:color,font:{name:font,size:10,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',wrapText:true,rowHeight:39};
activities.getRange(`B${aFirst}:E${aLast}`).format.wrapText=true;
activities.getRange(`K${aFirst}:M${aLast}`).format.wrapText=true;
activities.getRange(`K${aFirst}:K${aLast}`).format.rowHeight=75;
activities.getRange(`C${aFirst}:D${aLast}`).setNumberFormat('yyyy-mm-dd hh:mm');
activities.getRange(`F${aFirst}:J${aLast}`).setNumberFormat('#,##0');
activities.getRange(`A${aFirst}:A${aLast}`).setNumberFormat('@');
activities.getRange(`A${aFirst}:M${aLast}`).conditionalFormats.addCustom(`=$J${aFirst}>0`,{fill:'#FFF1CD'});
activities.getRange(`I${aFirst}:I${aLast}`).conditionalFormats.add('cellIs',{operator:'greaterThan',formula:0,format:{fill:'#FFF1CD',font:{color:'#805300'}}});
const aTable=activities.tables.add(`A${aHead}:M${aLast}`,true,'ActivitySummary');
aTable.style='TableStyleLight1';
aTable.showFilterButton=true;
activities.freezePanes.freezeRows(aHead);
activities.freezePanes.freezeColumns(2);
const sourceFirst=aLast+3;
activities.getRange(`A${sourceFirst}`).values=[['数据来源']];
activities.getRange(`A${sourceFirst+1}`).values=[['商品成本/已配折扣：用户提供的戴拉银饰货盘，Sheet1 A1:T98。']];
activities.getRange(`A${sourceFirst+2}`).values=[['报名价格/状态/渠道：得物已报名列表、导出及明确标示的取整测算；活动时间：后台活动详情。']];
activities.getRange(`A${sourceFirst+3}`).values=[['原出价：得物品牌官方出价列表导出；额外优惠：后台预估到手价及活动叠加规则。']];
activities.getRange(`A${sourceFirst+4}`).values=[['到手价是优惠后商品预估金额，未扣平台费用及成本，不等于消费者实付款或商家净利润；真实结算以成交订单为准。']];
activities.getRange(`A${sourceFirst}:A${sourceFirst+4}`).format.font={name:font,size:10,color:'#595959'};

workbook.recalculate();
const recalculationChecks=[];
const lowIndex=data.rows.findIndex(r=>r.registration_price>0 && r.registration_price<200);
if(lowIndex>=0){
  const r=first+lowIndex,original=detail.getRange(`I${r}`).values[0][0];
  const before=detail.getRange(`N${r}`).values[0][0];
  detail.getRange(`I${r}`).values=[[original+1]];
  workbook.recalculate();
  const after=detail.getRange(`N${r}`).values[0][0];
  if(Math.abs(after-before-0.9)>1e-8)throw Error('Low-price profit did not recalculate correctly.');
  detail.getRange(`I${r}`).values=[[original]];
  workbook.recalculate();
  recalculationChecks.push('低于最低平台费分界的报名价提高1元，毛利增加0.9元；已恢复原价');
}
const moonIndex=data.rows.findIndex(r=>r.article_no==='YX9354001' && r.registration_price>0 && r.extra_merchant_reduction>0);
if(moonIndex>=0){
  const r=first+moonIndex,original=detail.getRange(`L${r}`).values[0][0];
  const before=detail.getRange(`N${r}`).values[0][0];
  detail.getRange(`L${r}`).values=[[original+1]];
  workbook.recalculate();
  const after=detail.getRange(`N${r}`).values[0][0];
  if(Math.abs(after-before+1)>1e-8)throw Error('Merchant reduction did not recalculate correctly.');
  detail.getRange(`L${r}`).values=[[original]];
  workbook.recalculate();
  recalculationChecks.push('月光舞裙商家满减承担提高1元，毛利减少1元；已恢复原值');
}
for (let index=0;index<data.rows.length;index++) {
  const record=data.rows[index], row=first+index;
  if(record.profit!==null){
    const got=detail.getRange(`N${row}:O${row}`).values[0];
    if(Math.abs(got[0]-record.profit)>1e-7 || Math.abs(got[1]-record.margin)>1e-9)
      throw Error(`Margin mismatch ${record.activity_id}/${record.sku_id}: ${JSON.stringify(got)}`);
  }
}
const formulaScan=await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},maxChars:3500});
await fs.writeFile(path.join(here,'formula_scan.ndjson'),formulaScan.ndjson);
const inspect=await workbook.inspect({kind:'table',range:`报名明细!G${first}:O${Math.min(last,first+4)}`,include:'values,formulas',tableMaxRows:5,tableMaxCols:9,maxChars:6000});
await fs.writeFile(path.join(here,'final_inspect.ndjson'),inspect.ndjson);
for(const [sheetName,range,file] of [
  ['报名明细','A1:F14','detail_preview.png'],
  ['报名明细',`G${head}:O${head+6}`,'prices_preview.png'],
  ['活动概览','A1:J16','activities_preview.png'],
]) {
  const preview=await workbook.render({sheetName,range,scale:1,format:'png'});
  await fs.writeFile(path.join(here,file),new Uint8Array(await preview.arrayBuffer()));
}
const conditionalIndex=data.rows.findIndex(r=>r.estimate_mode==='条件测算' && r.registration_price!==null);
if(conditionalIndex>=0){
  const r=first+conditionalIndex;
  const preview=await workbook.render({sheetName:'报名明细',range:`AB${r}:AD${Math.min(last,r+2)}`,scale:1,format:'png'});
  await fs.writeFile(path.join(here,'evidence_preview.png'),new Uint8Array(await preview.arrayBuffer()));
}
await fs.mkdir(path.dirname(outputPath),{recursive:true});
const xlsx=await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
await fs.writeFile(path.join(here,'build_audit.json'),JSON.stringify({outputPath,rows:data.rows.length,activities:data.activities.length,summary:data.summary,missingFields:data.gaps.length,phase:data.phase,checkedMarginRows:data.rows.filter(r=>r.profit!==null).length,recalculationChecks,formulaScan:formulaScan.ndjson},null,2));
console.log(JSON.stringify({outputPath,rows:data.rows.length,activities:data.activities.length,summary:data.summary,missingFields:data.gaps.length,phase:data.phase}));
