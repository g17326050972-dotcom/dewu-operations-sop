import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
const dir = new URL('.', import.meta.url).pathname;
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load('/Users/nan/Downloads/按照SPU维度设置折扣.xlsx'));
console.log((await wb.inspect({kind:'table',range:'Sheet1!A1:E5',maxChars:2000})).ndjson);
if (process.argv.includes('--inspect')) {
 const p=await wb.render({sheetName:'Sheet1',range:'A1:E2',scale:1.5});
 await fs.writeFile(dir+'template-preview.png',new Uint8Array(await p.arrayBuffer()));
} else {
 const s=wb.worksheets.getItem('Sheet1');
 s.getRange('A2:E5').values=[
 ['96953327','戴拉 DARA 星星流苏吊坠轻奢小众设计感精致闪耀锁骨链约会百搭 925银 项链 女款','YX9502001',8,-1],
 ['96974434','戴拉 DARA 圆环双星流苏吊坠轻奢小众设计感精致锁骨链通勤百搭 925银 项链 女款','YX9533001',8,-1],
 ['96948546','戴拉 DARA 蝴蝶结圆环水滴吊坠轻奢小众设计感精致锁骨链通勤百搭 925银 项链 女款','YX9539001',8,-1],
 ['96942224','戴拉 DARA 圆形包镶锆石间隔圆柱轻奢小众设计感精致百搭通勤 925银合成立方氧化锆 手链 女款','YS9541001',8,-1]
 ];
 s.getRange('B2:C5').clear({applyTo:'contents'});
 s.getRange('E1:E5').format.columnWidth=28;
 wb.recalculate();
 console.log((await wb.inspect({kind:'table',range:'Sheet1!A1:E5',tableMaxRows:5,tableMaxCols:5,maxChars:4000})).ndjson);
 const p=await wb.render({sheetName:'Sheet1',range:'A1:E5',scale:1.5});
 await fs.writeFile(dir+'filled-preview.png',new Uint8Array(await p.arrayBuffer()));
 await (await SpreadsheetFile.exportXlsx(wb)).save(dir+'四款自建折扣报名.xlsx');
}
