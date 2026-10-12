import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const base = path.resolve('work/202609-profit');
const outputDir = path.resolve('outputs/01a08e8b-d4b6-7002-a86c-1f8b4ff9f30f');
const outputPath = path.join(outputDir, '戴拉9月货盘利润测算_截至0928.xlsx');
const catalog = JSON.parse(await fs.readFile(path.join(base, 'catalog_costs.json'), 'utf8'));
const analysis = JSON.parse(await fs.readFile(path.join(base, 'analysis.json'), 'utf8'));
const settlements = JSON.parse(await fs.readFile(path.join(base, 'settlement_match.json'), 'utf8'));
const costMap = catalog.cost_by_sku;
const skus = Object.keys(costMap);
const orders = analysis.orders.filter(o => Object.hasOwn(costMap, o.sku));
if (skus.length !== 97 || orders.length !== 171) throw new Error('Source controls changed; review before rebuilding.');

const soldPaid = new Map();
const shortName = new Map();
const orderCount = new Map();
for (const order of orders) {
  soldPaid.set(order.sku, (soldPaid.get(order.sku) || 0) + (order.valid_paid || 0));
  orderCount.set(order.sku, (orderCount.get(order.sku) || 0) + 1);
  if (!shortName.has(order.sku)) {
    const match = order.name.match(/【([^】]+)】/);
    shortName.set(order.sku, match ? match[1] : order.name.replace(/^戴拉\s*DARA\s*/, '').slice(0, 10));
  }
}
const displayedSkus = [...skus].sort((a,b) => {
  const group = s => (soldPaid.get(s)||0)>0 ? 0 : (orderCount.get(s)||0)>0 ? 1 : 2;
  return group(a)-group(b) || (soldPaid.get(b)||0)-(soldPaid.get(a)||0) || (orderCount.get(b)||0)-(orderCount.get(a)||0) || skus.indexOf(a)-skus.indexOf(b);
});

const wb = Workbook.create();
const summary = wb.worksheets.add('逐款利润');
const orderSheet = wb.worksheets.add('订单明细');
const costSheet = wb.worksheets.add('货盘成本');
const basis = wb.worksheets.add('测算口径');
for (const s of [summary,orderSheet,costSheet,basis]) s.showGridLines = false;
summary.tabColor = '#203C57';
basis.tabColor = '#738DA2';

const ink = '#17324A', deep = '#203C57', pale = '#EAF0F4', teal = '#087F8C', amber = '#FFF3D6', red = '#9D2C36';
const font = 'Arial';
const fmtYuan = '#,##0.00;[Red](#,##0.00);–';
const fmtInteger = '#,##0;[Red](#,##0);–';
const fmtPct = '0.0%;[Red](0.0%);–';
const applyBase = (sheet,range) => {
  const r=sheet.getRange(range); r.format.font={name:font,size:10,color:ink};
  r.format.verticalAlignment='center'; r.format.rowHeight=22;
};
const header = (sheet,range) => {
  const r=sheet.getRange(range);
  r.format.fill=deep; r.format.font={name:font,size:10,bold:true,color:'#FFFFFF'};
  r.format.rowHeight=31; r.format.verticalAlignment='center'; r.format.horizontalAlignment='center';
};
const setColumnWidths = (sheet,widths,lastRow) => {
  for (let i=0;i<widths.length;i++) sheet.getRangeByIndexes(0,i,lastRow,1).format.columnWidth=widths[i];
};

// Assumptions and source basis. All monetary inputs are per retained unit/order.
applyBase(basis,'A1:F28');
basis.getRange('A2').values=[['2026 年 9 月戴拉货盘订单贡献利润：测算口径']];
basis.getRange('A2').format.font={name:font,size:15,bold:true,color:ink};
basis.getRange('A3').values=[['订单时间 2026-09-01 至 2026-09-28；财务导出为 2026-09-29 查询快照。金额单位：元。']];
basis.getRange('A3').format.font={name:font,size:10,italic:true,color:'#667A8C'};
basis.getRange('A5:C5').values=[['项目','数值','依据']]; header(basis,'A5:C5');
basis.getRange('A6:C11').values=[
  ['指定礼盒每件附加成本',13,'用户规则：规格含“炽热挚爱”或“钟意一生”'],
  ['每件包装费',5,'戴拉银饰货盘.xlsx，Sheet1!I2'],
  ['每件物料费',3,'戴拉银饰货盘.xlsx，Sheet1!J2'],
  ['每件寄件运费',5,'戴拉银饰货盘.xlsx，Sheet1!K2'],
  ['每件操作费',1.5,'戴拉银饰货盘.xlsx，Sheet1!L2'],
  ['税费率（按有效实付）',0.03,'源货盘有订单的 7 款税点均为 3%；21 款无销量货号的空白税点不作推定'],
];
basis.getRange('B6:B11').format.font={name:font,size:10,color:'#1560A8'};
basis.getRange('B6:B10').setNumberFormat(fmtYuan); basis.getRange('B11').setNumberFormat(fmtPct);
basis.getRange('A13:C13').values=[['计算步骤','口径','来源及限制']]; header(basis,'A13:C13');
basis.getRange('A14:C22').values=[
  ['有效销售','仅交易成功、待买家收货、待物流揽收；交易关闭和失败不算销量','得物订单导出 (2).xlsx'],
  ['商家优惠','有效订单的出价减实付；作为收入桥展示，不在预计收入后重复扣除','得物订单导出 (2).xlsx'],
  ['平台费','有效实付－消费者邮费补贴－订单预计收入','订单详情后台说明：预计收入=出价－商家优惠－邮补－基础服务费'],
  ['有效订单预计收入','有效实付－邮补－平台费；仍有未入账订单','销售订单入账详情，2026-09-29 14:49 导出'],
  ['有效履约成本','每有效订单：包装＋物料＋寄件运费＋操作费','货盘成本模型，属于估计值'],
  ['指定礼盒','有效订单和已发货后关闭订单各按每件 13 元计入成本','以订单规格文字匹配'],
  ['已发货后关闭','估算已发生履约成本；另扣消费者邮补，17 单中 15 单有财务退款结算佐证','退款订单入账详情，2026-09-29 14:50 导出'],
  ['税费','有效实付×3%，采用本期有订单货号的货盘税点，非实际税务结算','戴拉银饰货盘.xlsx，Sheet1!M 列'],
  ['贡献利润','有效预计收入－产品成本－有效履约－礼盒－税－已发货关闭损耗','未包含广告费、逆向运费及固定费用，非最终净利润'],
];
basis.getRange('A24:C24').values=[['待核项目','金额／数量','说明']]; header(basis,'A24:C24');
basis.getRange('A25:C27').values=[
  ['发货关闭邮补待核',8.21,'17 单中 2 单未出现在退款结算导出；主测算保守扣除'],
  ['销售财务未列订单',5,'102 笔有效单中，97 笔出现在销售入账详情；其中 66 已入账、31 未入账'],
  ['外部公式缓存成本',74.55,'YX9341001：成本取源货盘 Sheet1!G17 的缓存值；外部引用文件未提供'],
];
basis.getRange('B25').setNumberFormat(fmtYuan); basis.getRange('B26').setNumberFormat(fmtInteger); basis.getRange('B27').setNumberFormat(fmtYuan);
basis.getRange('A25:C27').format.fill=amber;
setColumnWidths(basis,[29,57,95,11,11,11],28);

// Catalog source inputs. Cost values are copied from the supplied workbook, not recalculated from missing external files.
applyBase(costSheet,'A1:E104');
costSheet.getRange('A2').values=[['戴拉货盘：97 个货号的单位产品成本']];
costSheet.getRange('A2').format.font={name:font,size:15,bold:true,color:ink};
costSheet.getRange('A3').values=[['来源：戴拉银饰货盘.xlsx，Sheet1，B 列货号、G 列成本；24 项成本为外部公式缓存值。']];
costSheet.getRange('A3').format.font={name:font,size:10,italic:true,color:'#667A8C'};
costSheet.getRange('A6:E6').values=[['货号','单位产品成本','来源类型','源成本单元格','核对提示']]; header(costSheet,'A6:E6');
costSheet.getRange('A7:E103').values=skus.map(sku => {
  const c=costMap[sku];
  return [sku,c.cost_yuan,c.cost_source_mode==='literal'?'字面成本':'外部公式缓存',c.cost_cell,c.cost_source_mode==='literal'?'':'原引用文件未提供，缓存值待核'];
});
costSheet.getRange('B7:B103').setNumberFormat(fmtYuan);
costSheet.getRange('B7:B103').format.font={name:font,size:10,color:'#1560A8'};
costSheet.getRange('C7:E103').format.font={name:font,size:10,color:'#607587'};
setColumnWidths(costSheet,[19,20,20,20,39],104);
costSheet.freezePanes.freezeRows(6);

// Order source inputs and formula build. Order IDs are the only retained audit identifier; no recipient data is copied.
applyBase(orderSheet,'A1:AJ178');
orderSheet.getRange('A2').values=[['戴拉货盘：9 月订单明细与利润计算']];
orderSheet.getRange('A2').format.font={name:font,size:15,bold:true,color:ink};
orderSheet.getRange('A3').values=[['来源：得物订单导出 (2).xlsx；销售订单入账详情、退货退款订单入账详情（均于 2026-09-29 导出）。']];
orderSheet.getRange('A3').format.font={name:font,size:10,italic:true,color:'#667A8C'};
orderSheet.getRange('A4').values=[['仅保留货盘 97 个货号对应的 171 笔订单；销售应结未全部入账，利润为当前订单贡献测算。']];
const orderHeaders=[
  '订单号','货号','订单品名','规格','下单时间','订单状态','发货时间','出价','商家优惠','实付','消费者邮补','订单预计收入',
  '销售财务状态','销售应结金额','退款财务状态','退款应结金额','有效标记','发货关闭标记','指定礼盒标记','有效销量','有效出价','有效优惠','有效实付','有效邮补','平台基础服务费','有效预计收入','单位产品成本','有效产品成本','有效履约成本','有效礼盒成本','税费估算','发货关闭履约成本','发货关闭邮补损耗','订单贡献利润','销售应结差异','退款邮补核对差异'
];
orderSheet.getRange('A7:AJ7').values=[orderHeaders]; header(orderSheet,'A7:AJ7');
// Excel date-times are timezone-free wall times. Preserve the backend's China-local text components.
const toDate = s => s ? new Date(s.replace(' ','T')+'Z') : null;
const sourceRows=orders.map(o=>{
  const sale=settlements.sales_by_order[o.order_id];
  const refund=settlements.refund_by_order[o.order_id];
  return [o.order_id,o.sku,o.name,o.spec,toDate(o.order_time),o.status,toDate(o.ship_time),o.offer,o.seller_discount,o.paid,o.postage_subsidy,o.expected_income,
    sale?.status||'',sale?.amount_yuan??null,refund?.map(x=>x.status).join('、')||'',refund?refund.reduce((s,x)=>s+x.amount_yuan,0):null];
});
orderSheet.getRange('A8:P178').values=sourceRows;
orderSheet.getRange('A8:P178').format.font={name:font,size:10,color:'#1560A8'};
orderSheet.getRange('A8:A178').setNumberFormat('@');
orderSheet.getRange('E8:E178').setNumberFormat('yyyy-mm-dd hh:mm');
orderSheet.getRange('G8:G178').setNumberFormat('yyyy-mm-dd hh:mm');
orderSheet.getRange('H8:P178').setNumberFormat(fmtYuan);
for(const col of ['M','O']) orderSheet.getRange(`${col}8:${col}178`).setNumberFormat('@');
const orderFormulaRows=orders.map((_,idx)=>{
  const r=idx+8;
  return [
    `=IF(OR(F${r}="交易成功",F${r}="待买家收货",F${r}="待物流揽收"),1,0)`,
    `=IF(AND(F${r}="交易关闭成功",G${r}<>""),1,0)`,
    `=IF(OR(ISNUMBER(SEARCH("炽热挚爱",D${r})),ISNUMBER(SEARCH("钟意一生",D${r}))),1,0)`,
    `=Q${r}`,
    `=H${r}*Q${r}`,
    `=I${r}*Q${r}`,
    `=J${r}*Q${r}`,
    `=K${r}*Q${r}`,
    `=IF(Q${r}=1,J${r}-K${r}-L${r},0)`,
    `=L${r}*Q${r}`,
    `=VLOOKUP(B${r},'货盘成本'!$A$7:$B$103,2,FALSE)`,
    `=AA${r}*T${r}`,
    `=T${r}*SUM('测算口径'!$B$7:$B$10)`,
    `=S${r}*T${r}*'测算口径'!$B$6`,
    `=W${r}*'测算口径'!$B$11`,
    `=R${r}*(SUM('测算口径'!$B$7:$B$10)+S${r}*'测算口径'!$B$6)`,
    `=R${r}*K${r}`,
    `=Z${r}-SUM(AB${r}:AG${r})`,
    `=IF(N${r}="","",N${r}-L${r})`,
    `=IF(P${r}="","",L${r}+P${r}+K${r})`,
  ];
});
orderSheet.getRange('Q8:AJ178').formulas=orderFormulaRows;
orderSheet.getRange('Q8:T178').setNumberFormat(fmtInteger);
orderSheet.getRange('U8:AJ178').setNumberFormat(fmtYuan);
orderSheet.getRange('AA8:AA178').format.font={name:font,size:10,color:'#1F8A68'};
setColumnWidths(orderSheet,[22,17,51,42,21,17,21,15,15,15,16,18,16,18,16,18,13,16,16,13,16,16,16,16,19,17,18,17,17,17,16,19,19,17,18,22],178);
orderSheet.freezePanes.freezeRows(7);
orderSheet.freezePanes.freezeColumns(2);

// Primary 97-SKU view: all catalog products, including zero-sale rows.
applyBase(summary,'A1:U108');
summary.getRange('A2').values=[['戴拉 9 月货盘逐款订单贡献利润']];
summary.getRange('A2').format.font={name:font,size:15,bold:true,color:ink};
summary.getRange('A3').values=[['2026-09-01 至 09-28 订单；按 09-29 财务快照核对。货盘 97 个货号，未销售款仍列示。']];
summary.getRange('A3').format.font={name:font,size:10,italic:true,color:'#667A8C'};
summary.getRange('A5:Q5').values=[['有效销量',null,null,'有效实付',null,null,'有效预计收入',null,null,'贡献利润测算',null,null,'利润率',null,null,'已关闭实付',null]];
summary.getRange('B5').formulas=[['=E11']]; summary.getRange('E5').formulas=[['=H11']]; summary.getRange('H5').formulas=[['=K11']]; summary.getRange('K5').formulas=[['=R11']]; summary.getRange('N5').formulas=[['=S11']]; summary.getRange('Q5').formulas=[['=T11']];
for(const c of ['B','E','H','K','N','Q']) {summary.getRange(`${c}5`).format.fill=pale;summary.getRange(`${c}5`).format.font={name:font,size:12,bold:true,color:ink};}
summary.getRange('B5').setNumberFormat(fmtInteger); for(const c of ['E','H','K','Q'])summary.getRange(`${c}5`).setNumberFormat(fmtYuan);summary.getRange('N5').setNumberFormat(fmtPct);
summary.getRange('A7').values=[['有效 102 单中，销售财务 66 单已入账、31 单未入账、5 单未列；发货后关闭 17 单的邮补按保守口径计入损耗。']];
summary.getRange('A8').values=[['其中 2 单邮补合计 8.21 元仍待核；成本含货盘估算费用，未包含广告、逆向运费与固定费用。']];
summary.getRange('A7:A8').format.font={name:font,size:10,color:'#607587'};
const sumHeaders=['货号','订单品名简称','单位成本','订单数','有效销量','有效出价','商家优惠','有效实付','消费者邮补','平台基础服务费','有效预计收入','产品成本','履约成本','指定礼盒成本','税费估算','发货关闭履约','发货关闭邮补','贡献利润','利润率','已关闭实付','成本备注'];
summary.getRange('A10:U10').values=[sumHeaders]; header(summary,'A10:U10');
summary.getRange('A11:B11').values=[['货盘合计','97 个货号']];
summary.getRange('D11:T11').formulas=[[...Array.from({length:16},(_,i)=>{
  const col=String.fromCharCode('D'.charCodeAt(0)+i);
  return `=SUM(${col}12:${col}108)`;
}), '=SUM(T12:T108)']];
summary.getRange('S11').formulas=[['=IF(H11=0,"n.a.",R11/H11)']];
summary.getRange('A11:U11').format.fill='#D8E9E8';
summary.getRange('A11:U11').format.font={name:font,size:10,bold:true,color:ink};
const summaryIds=displayedSkus.map(sku => [sku,shortName.get(sku)||'',costMap[sku].cost_yuan]);
summary.getRange('A12:C108').values=summaryIds;
const orderLast=orders.length+7;
const sr=`'订单明细'!$B$8:$B$${orderLast}`;
const sums=displayedSkus.map((sku,idx)=>{
  const r=idx+12;
  const sumCol=col=>`=SUMIFS('订单明细'!$${col}$8:$${col}$${orderLast},${sr},$A${r})`;
  const count=`=COUNTIFS(${sr},$A${r})`;
  return [count,...['T','U','V','W','X','Y','Z','AB','AC','AD','AE','AF','AG','AH'].map(sumCol),`=IF(H${r}=0,"n.a.",R${r}/H${r})`,`=SUMIFS('订单明细'!$J$8:$J$${orderLast},${sr},$A${r},'订单明细'!$F$8:$F$${orderLast},"交易关闭成功")`];
});
summary.getRange('D12:T108').formulas=sums;
summary.getRange('U12:U108').values=displayedSkus.map(sku=>[costMap[sku].cost_source_mode==='literal'?'':'外部公式缓存，待核']);
summary.getRange('C11:R108').setNumberFormat(fmtYuan);
summary.getRange('D11:E108').setNumberFormat(fmtInteger);
summary.getRange('S11:S108').setNumberFormat(fmtPct);
summary.getRange('T11:T108').setNumberFormat(fmtYuan);
summary.getRange('C12:C108').format.font={name:font,size:10,color:'#1F8A68'};
summary.getRange('R12:R108').format.font={name:font,size:10,bold:true,color:ink};
summary.getRange('U12:U108').format.font={name:font,size:10,color:'#8C6410'};
summary.getRange('R12:R108').conditionalFormats.add('cellIs',{operator:'lessThan',formula:0,format:{fill:'#FBE8E8',font:{color:red,bold:true}}});
setColumnWidths(summary,[18,20,15,12,12,15,16,15,17,18,18,16,16,17,15,18,18,16,13,16,23],108);
summary.freezePanes.freezeRows(10);
summary.freezePanes.freezeColumns(2);

// Force a single final recalc, then inspect key output/control ranges.
wb.recalculate();
const overview=await wb.inspect({kind:'table',range:'逐款利润!A10:U18',include:'values,formulas',tableMaxRows:9,tableMaxCols:21,maxChars:4500});
const basisCheck=await wb.inspect({kind:'table',range:'测算口径!A5:C11',include:'values',tableMaxRows:7,tableMaxCols:3,maxChars:1500});
const errorCheck=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:50},summary:'formula errors',maxChars:2500});
console.log('OVERVIEW',overview.ndjson);
console.log('BASIS',basisCheck.ndjson);
console.log('ERRORS',errorCheck.ndjson);

await fs.mkdir(outputDir,{recursive:true});
for(const [sheetName,range,file] of [
  ['逐款利润','A1:U17','preview-summary.png'],
  ['订单明细','A1:P12','preview-orders.png'],
  ['货盘成本','A1:E13','preview-costs.png'],
  ['测算口径','A1:C27','preview-basis.png'],
]) {
  const blob=await wb.render({sheetName,range,scale:1.3,format:'png'});
  await fs.writeFile(path.join(base,file),new Uint8Array(await blob.arrayBuffer()));
}
const out=await SpreadsheetFile.exportXlsx(wb);
await out.save(outputPath);
console.log('OUTPUT',outputPath);
