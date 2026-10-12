import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const root = '/Users/nan/Documents/Codex/2026-10-09/zai';
const inputPath = path.join(root, 'work/retry_metrics.json');
const outputDir = path.join(root, 'outputs/2026-10-08');
const raw = await fs.readFile(inputPath);
const input = JSON.parse(raw.toString('utf8'));
const records = [...input.rows].sort((a,b) => b[4][1]-a[4][1] || b[4][6]-a[4][6] || a[0].localeCompare(b[0]));
assert.equal(records.length, 46);
assert.equal(new Set(records.map(r => r[0])).size, 46);
assert.equal(input.date, '2026-10-08');
assert.equal(input.week_start, '2026-10-02');
assert.equal(input.week_end, '2026-10-08');
const dayQoq = new Map(input.qoq_raw.filter(r=>r.period==='day').map(r=>[r.code,r]));
const weekQoq = new Map(input.qoq_raw.filter(r=>r.period==='week').map(r=>[r.code,r]));
const missing = input.missing_fields.join('；');
const dataChecks = [];
for (const row of records) {
  for (const index of [4,5]) {
    const m=row[index];
    assert.equal(m.length, 8);
    assert(m.every(v=>typeof v==='number' && Number.isFinite(v) && v>=0));
    for (const j of [1,2,4,5,6,7]) assert(Number.isInteger(m[j]));
    if(m[2]<m[6]) dataChecks.push(`${row[0]} ${index===4?'七天':'昨日'} PV小于UV`);
    if(m[7]>m[6]) dataChecks.push(`${row[0]} ${index===4?'七天':'昨日'} 收藏用户数大于UV`);
    if(m[5]>m[4]) dataChecks.push(`${row[0]} ${index===4?'七天':'昨日'} 支付用户数大于订单数`);
    if(m[6]>0 && Math.abs(m[3]-m[5]/m[6]*100)>0.0051) dataChecks.push(`${row[0]} ${index===4?'七天':'昨日'} 商详转化与支付用户/UV舍入不符`);
  }
  for (const j of [0,1,2,4,5,6,7]) if(row[5][j]>row[4][j]) dataChecks.push(`${row[0]} 昨日指标${j}大于七天`);
}

const wb=Workbook.create();
const day=wb.worksheets.add('昨日46款');
const week=wb.worksheets.add('近7天46款');
const notes=wb.worksheets.add('口径说明');
const firstRow=8,lastRow=53;
const rate=(value)=>value==null?null:value/100;
const rankLabel=(sales)=>{
  const greater=records.filter(r=>r[4][1]>sales).length;
  const same=records.filter(r=>r[4][1]===sales).length;
  return `${same>1?'并列第':'第'}${greater+1}`;
};
const classification=(row,index)=>row[4][1]>0?'有销量款':index<10?'零销量观察':'零销量';
const sourceUrl='https://stark.dewu.com/main/dataCenter/productList';
const widths=[9,15,17,22,15,12,12,15,12,13,13,15,13,13,12,16,17,20,16,17];
const headers=['展示序号','近7天销量名次','货号','商品简称','近7天分组','后台新品标记','我的销量','支付金额(元)','商详访客UV','收藏用户数','收藏率(自算)','商详转化(后台)','支付订单数','支付用户数','商详PV','UV前日环比','商详转化前日环比','当前出价(采集日)','SPU ID','实际首次上架日期'];

function buildSheet(sheet,index,isDay){
  sheet.showGridLines=false;
  sheet.tabColor=isDay?'#254C64':'#49697D';
  const title=isDay?'2026-10-08 商品底表':'2026-10-02 至 2026-10-08 商品底表';
  sheet.getRange('A2').values=[[title]];
  sheet.getRange('A2:T2').format.rowHeight=27;
  sheet.getRange('A2').format.font={name:'Arial',size:14,bold:true,color:'#183443'};
  sheet.getRange('A3').values=[['商品数']];
  sheet.getRange('B3').values=[[46]];
  sheet.getRange('D3').values=[['我的销量合计']];
  sheet.getRange('E3').formulas=[[`=SUM(G${firstRow}:G${lastRow})`]];
  sheet.getRange('G3').values=[['支付金额合计(元)']];
  sheet.getRange('H3').formulas=[[`=SUM(H${firstRow}:H${lastRow})`]];
  sheet.getRange('J3').values=[['本期有销量款']];
  sheet.getRange('K3').formulas=[[`=COUNTIFS(G${firstRow}:G${lastRow},">0")`]];
  sheet.getRange('M3').values=[['采集日期']];
  sheet.getRange('N3').values=[[new Date(`${input.collected_date}T00:00:00Z`)]];
  sheet.getRange('N3').setNumberFormat('yyyy-mm-dd');
  sheet.getRange('H3').setNumberFormat('#,##0.00');
  sheet.getRange('A4').values=[['一级类目：流行饰品/眼镜/服配；全部品牌、全部商品类型；按货号核对46款。']];
  sheet.getRange('A5').values=[['来源：得物商品分析页面逐页读数，非平台下载导出；当前出价不是历史实付价格。']];
  sheet.getRange('A6').values=[['按近7天销量降序、同销量近7天UV降序；仅4款有销量，42款零销量并列第5。']];
  sheet.getRange('A4:T6').format.font={name:'Arial',size:10,color:'#4B5D66'};
  sheet.getRange('A7:T7').values=[[...headers]];
  if(!isDay){
    sheet.getRange('P7:Q7').values=[['UV较前期环比','商详转化较前期环比']];
  }
  const rows=records.map((row,i)=>{
    const m=row[index],q=(isDay?dayQoq:weekQoq).get(row[0]);
    return [i+1,rankLabel(row[4][1]),row[0],row[1],classification(row,i),row[2]?'是':'否',m[1],m[0],m[6],m[7],null,m[3]/100,m[4],m[5],m[2],rate(q?.uv),isDay?rate(q?.conversion):null,row[3],null,null];
  });
  sheet.getRange(`A${firstRow}:T${lastRow}`).values=rows;
  sheet.getRange(`K${firstRow}`).formulas=[[`=IF(I${firstRow}=0,"",J${firstRow}/I${firstRow})`]];
  sheet.getRange(`K${firstRow}:K${lastRow}`).fillDown();
  sheet.getRange(`A3:T${lastRow}`).format.font={name:'Arial',size:10,color:'#1E2B33'};
  sheet.getRange('A7:T7').format={fill:'#254C64',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:35};
  sheet.getRange(`A${firstRow}:T${lastRow}`).format.rowHeight=24;
  sheet.getRange(`A${firstRow}:T${lastRow}`).format.verticalAlignment='center';
  sheet.getRange(`G${firstRow}:Q${lastRow}`).format.horizontalAlignment='right';
  sheet.getRange(`G${firstRow}:J${lastRow}`).setNumberFormat('#,##0');
  sheet.getRange(`H${firstRow}:H${lastRow}`).setNumberFormat('#,##0.00');
  sheet.getRange(`K${firstRow}:L${lastRow}`).setNumberFormat('0.00%');
  sheet.getRange(`M${firstRow}:O${lastRow}`).setNumberFormat('#,##0');
  sheet.getRange(`P${firstRow}:Q${lastRow}`).setNumberFormat('0.0%;-0.0%;0.0%');
  sheet.getRange(`R${firstRow}:S${lastRow}`).setNumberFormat('@');
  sheet.getRange(`T${firstRow}:T${lastRow}`).setNumberFormat('yyyy-mm-dd');
  sheet.getRange(`A${firstRow}:F${lastRow}`).format.horizontalAlignment='left';
  sheet.getRange(`R${firstRow}:T${lastRow}`).format.horizontalAlignment='left';
  for(let c=0;c<widths.length;c++)sheet.getRangeByIndexes(0,c,lastRow,1).format.columnWidth=widths[c];
  sheet.getRange(`E${firstRow}:E${lastRow}`).conditionalFormats.add('containsText',{text:'零销量观察',format:{fill:'#FFF1CF',font:{color:'#6B4B0B'}}});
  sheet.getRange(`F${firstRow}:F${lastRow}`).conditionalFormats.add('containsText',{text:'是',format:{fill:'#E7EEF3',font:{color:'#254C64'}}});
  sheet.freezePanes.freezeRows(7);
  sheet.freezePanes.freezeColumns(3);
  sheet.tables.add(`A7:T${lastRow}`,true,isDay?'YesterdayMetrics':'SevenDayMetrics');
  sheet.getRange('A55').values=[['缺项：SPU ID、实际首次上架日期及完整对比历史未获取，详见口径说明；未获取不等于0。']];
  sheet.getRange('A56').values=[['UV未求商品跨款去重总数；商详转化保留后台原值，收藏率由同期间收藏用户数/UV计算。']];
  sheet.getRange('A55:T56').format.font={name:'Arial',size:10,color:'#4B5D66'};
  return rows;
}
buildSheet(day,5,true);
buildSheet(week,4,false);

const noteRows=[
 ['报告范围','昨日及近7天各46款核心指标底表；尚不构成具备全部对比、渠道及历史证据的完整经营日报。'],
 ['一级类目','流行饰品/眼镜/服配；后台 Value1，黄金/珠宝/翡翠/玉石 Value0。'],
 ['数据期间','昨日2026-10-08；近7天2026-10-02至2026-10-08；采集日期2026-10-09，精确时刻未记录。'],
 ['数据来源',input.source],
 ['来源页面',sourceUrl],
 ['覆盖与商品标识','昨日46条、七天46条，按货号匹配且唯一；SPU ID未获取，不能替填货号。'],
 ['名称',input.name_note],
 ['销量',input.sales_definition],
 ['排序与并列','按近7天销量降序、同销量近7天UV降序；仍相同时按货号。仅4款有销量，42款零销量并列第5；其中6款只作零销量观察。两款销量为1的商品并列第3。'],
 ['收藏率','同商品同期间收藏用户数÷商详访问人数UV；XLSX使用公式，UV为0时留空，不显示0%或除零错误。'],
 ['商详转化',input.conversion_definition+' 原始输入百分数÷100后存为数值百分比。'],
 ['环比','两款昨日UV及商详转化环比来自页面原值，方向经截图核验。没有用环比倒推前日原值；完整原始环比见下表及JSON。'],
 ['七天转化环比','YX9354001变动幅度125.5%、YX9615001幅度55.3%，方向未核验；七天页环比列留空，不能写成升降结论。'],
 ['当前出价','仅为2026-10-09采集时页面出价/区间，按文本保留；不是10月8日实际成交价或历史优惠记录。'],
 ['新品','后台新品标记共有9款；该标记不能证明实际首次上架日期、首日流量或商品年龄。'],
 ['缺项',missing],
 ['0与缺失','源页面明确读到0的指标保留0；未获取字段留空，并列出缺项。收藏率UV=0时为空；后台转化源值为0仍保留0%。'],
 ['加总限制','我的销量和支付金额可按商品相加。跨商品UV不是店铺去重访客数，跨商品支付用户、收藏用户也未作去重加总；不将日UV求和代替七天去重UV。'],
 ['日历背景','10月8日为国庆假期后首个工作日，10月7日及10月1日均是假期；七天窗口含6天假期。对比存在日历差异，不能据此确认因果。'],
 ['日历来源','https://www.gov.cn/zhengce/zhengceku/202511/content_7047091.htm'],
 ['本次审查',dataChecks.length?dataChecks.join('；'):'46款货号唯一；数值非负；UV≤PV、收藏用户≤UV、支付用户≤订单数；昨日对应核心指标≤七天指标。未发现这些检查下的矛盾。'],
 ['转化复核','有访客记录的后台商详转化与支付用户数/UV按两位小数舍入相符；此算术核对不能代替平台指标定义的正式核验。'],
 ['潜力判断','后台新品样本仍小且实际首次上架日缺失；本底表不把小样本高收藏率或后台新品标记直接当成已确认潜力爆款。'],
];
notes.showGridLines=false;
notes.tabColor='#8B969D';
notes.getRange('A2').values=[['指标口径与数据缺项']];
notes.getRange('A2').format.font={name:'Arial',size:14,bold:true,color:'#183443'};
notes.getRange('A4:B4').values=[['项目','说明']];
notes.getRange(`A5:B${4+noteRows.length}`).values=noteRows;
notes.getRange(`A4:B${4+noteRows.length}`).format.font={name:'Arial',size:10,color:'#1E2B33'};
notes.getRange('A4:B4').format={fill:'#254C64',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:26};
notes.getRange('A1:A44').format.columnWidth=21;
notes.getRange('B1:B44').format.columnWidth=115;
notes.getRange(`A5:B${4+noteRows.length}`).format.wrapText=true;
notes.getRange(`A5:B${4+noteRows.length}`).format.verticalAlignment='center';
notes.getRange(`A5:B${4+noteRows.length}`).format.autofitRows();
notes.getRange('A30').values=[['后台环比原始读数（方向未核验者保留文字幅度）']];
const signed=q=>`${q>0?'+':''}${q.toFixed(1)}%`;
notes.getRange('A32:B32').values=[['货号/期间','后台环比原值']];
const qRows=input.qoq_raw.map(q=>[`${q.code} ${q.period==='day'?'昨日':'七天'}`,q.period==='day'?`UV ${signed(q.uv)}；收藏用户数 ${signed(q.favorites)}；商详转化 ${signed(q.conversion)}；我的销量 ${signed(q.sales)}；支付金额 ${signed(q.payment_amount)}；PV ${signed(q.pv)}`:`UV ${signed(q.uv)}；收藏用户数 ${signed(q.favorites)}；商详转化变动幅度 ${q.conversion_magnitude}%，方向未核验`]);
notes.getRange('A33:B36').values=qRows;
notes.getRange('A32:B36').format.font={name:'Arial',size:10,color:'#1E2B33'};
notes.getRange('A32:B32').format={fill:'#254C64',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:27,wrapText:true};
notes.getRange('A33:B36').format.wrapText=true;
notes.getRange('A33:B36').format.verticalAlignment='center';
notes.getRange('A33:B36').format.autofitRows();
notes.freezePanes.freezeRows(4);

wb.recalculate();
const checkedDay=day.getRange(`A${firstRow}:T${lastRow}`).values;
const checkedWeek=week.getRange(`A${firstRow}:T${lastRow}`).values;
for(let i=0;i<records.length;i++){
  const source=records[i];
  for(const [sheetRows,index]of [[checkedDay,5],[checkedWeek,4]]){
    const got=sheetRows[i],m=source[index];
    assert.equal(got[2],source[0]);
    assert.equal(got[6],m[1]);assert.equal(got[7],m[0]);assert.equal(got[8],m[6]);assert.equal(got[9],m[7]);
    assert.equal(got[11],m[3]/100);assert.equal(got[12],m[4]);assert.equal(got[13],m[5]);assert.equal(got[14],m[2]);
    if(m[6]===0)assert(got[10]===''||got[10]===null);else assert(Math.abs(got[10]-m[7]/m[6])<1e-12);
    assert(got[18]===null||got[18]==='');assert(got[19]===null||got[19]==='');
  }
}
assert.equal(day.getRange('E3').values[0][0],4);
assert.equal(day.getRange('H3').values[0][0],969);
assert.equal(week.getRange('E3').values[0][0],32);
assert.equal(week.getRange('H3').values[0][0],7988);
const inspect=await wb.inspect({kind:'table',range:'昨日46款!C7:Q12',include:'values,formulas',tableMaxRows:6,tableMaxCols:15,maxChars:6000});
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},summary:'最终公式错误扫描',maxChars:3000});
console.log(JSON.stringify({inspect:inspect.ndjson,errors:errors.ndjson}));

await fs.mkdir(outputDir,{recursive:true});
const xlsxPath=path.join(outputDir,'商品底表_重试.xlsx');
const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(xlsxPath);
try { await fs.rename(`${xlsxPath}.inspect.ndjson`,path.join(root,'work/retry_export_inspect.ndjson')); } catch(e) { if(e.code!=='ENOENT') throw e; }
await fs.copyFile(inputPath,path.join(outputDir,'页面原始读数_重试.json'));
assert.equal(crypto.createHash('sha256').update(await fs.readFile(inputPath)).digest('hex'),crypto.createHash('sha256').update(await fs.readFile(path.join(outputDir,'页面原始读数_重试.json'))).digest('hex'));

// CSV从经Artifact公式核验的单元格读取数据；格式为46款一行一款、昨日与七天并列。
const percent=(n,digits=2)=>n==null||n===''?'':`${(n*100).toFixed(digits)}%`;
const csvHeader=['数据日期','近7天开始','近7天结束','采集日期','一级类目','展示序号','近7天销量名次','近7天分组','货号','商品简称','后台新品标记','当前出价_采集日_非历史实付价','SPU ID','实际首次上架日期','昨日我的销量','昨日支付金额_元','昨日商详访客UV','昨日收藏用户数','昨日收藏率_自算','昨日商详转化_后台原值','昨日支付订单数','昨日支付用户数','昨日商详PV','昨日UV前日环比_后台','昨日商详转化前日环比_后台','昨日收藏用户数前日环比_后台','昨日销量前日环比_后台','昨日支付金额前日环比_后台','昨日PV前日环比_后台','近7天我的销量','近7天支付金额_元','近7天商详访客UV','近7天收藏用户数','近7天收藏率_自算','近7天商详转化_后台原值','近7天支付订单数','近7天支付用户数','近7天商详PV','近7天UV较前期环比_后台','近7天转化变动幅度_方向未核验','缺项'];
const csvRows=checkedDay.map((d,i)=>{
 const w=checkedWeek[i],q=dayQoq.get(d[2]),qw=weekQoq.get(d[2]);
 return [input.date,input.week_start,input.week_end,input.collected_date,'流行饰品/眼镜/服配',d[0],d[1],d[4],d[2],d[3],d[5],d[17],d[18],d[19],d[6],d[7],d[8],d[9],percent(d[10]),percent(d[11]),d[12],d[13],d[14],percent(d[15],1),percent(d[16],1),percent(rate(q?.favorites),1),percent(rate(q?.sales),1),percent(rate(q?.payment_amount),1),percent(rate(q?.pv),1),w[6],w[7],w[8],w[9],percent(w[10]),percent(w[11]),w[12],w[13],w[14],percent(w[15],1),qw?.conversion_magnitude==null?'':`幅度${qw.conversion_magnitude}%，方向未核验`,missing];
});
const escapeCsv=v=>{const s=v==null?'':String(v);return /[",\r\n]/.test(s)?`"${s.replaceAll('"','""')}"`:s;};
const csvPath=path.join(outputDir,'商品底表_重试.csv');
await fs.writeFile(csvPath,'\ufeff'+[csvHeader,...csvRows].map(r=>r.map(escapeCsv).join(',')).join('\r\n')+'\r\n','utf8');

const previews=[['昨日46款','A1:N16','retry_day_preview.png'],['昨日46款','O7:T16','retry_day_tail_preview.png'],['近7天46款','A1:N16','retry_week_preview.png'],['口径说明','A1:B28','retry_notes_preview.png'],['口径说明','A30:B36','retry_qoq_preview.png']];
for(const [sheetName,range,file]of previews){const blob=await wb.render({sheetName,range,scale:1.25,format:'png'});await fs.writeFile(path.join(root,'work',file),new Uint8Array(await blob.arrayBuffer()));}
const summary={outputs:[xlsxPath,csvPath,path.join(outputDir,'页面原始读数_重试.json')],rows:46,sheets:['昨日46款','近7天46款','口径说明'],day_sales:4,day_payment:969,week_sales:32,week_payment:7988,week_selling_products:4,zero_sales_tied_products:42,backend_new_flags:records.filter(r=>r[2]).length,source_consistency_issues:dataChecks,formula_errors:errors.ndjson,previews:previews.map(p=>path.join(root,'work',p[2]))};
await fs.writeFile(path.join(root,'work/retry_table_validation.json'),JSON.stringify(summary,null,2),'utf8');
console.log(JSON.stringify(summary));
