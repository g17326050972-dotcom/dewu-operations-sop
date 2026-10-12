import fs from 'node:fs/promises';
import path from 'node:path';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';

// Intended usage after the real platform template has arrived:
// inspect <input.xlsx> <work-dir>
// build <input.xlsx> <patches.json> <output.xlsx> --authoring-marked
// The calling agent must inspect the baseline render and run the skill's
// mark_artifact_operation_started.mjs --operation-kind edit once before build.
// Never run build until headers, required fields, allowed cells, and native
// validation/protection preservation have been checked against the real file.

const [mode, inputPath, argument3, argument4, ...flags] = process.argv.slice(2);
if (!['inspect', 'build', 'compact'].includes(mode) || !inputPath || !argument3) {
  throw new Error('Usage: inspect <input.xlsx> <work-dir> OR build <input.xlsx> <patches.json> <output.xlsx> --authoring-marked');
}
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));

if (mode === 'inspect') {
  const workDir = argument3;
  await fs.mkdir(workDir, { recursive: true });
  const overview = await workbook.inspect({
    kind: 'workbook,sheet,table,definedName,drawing',
    maxChars: 15000, tableMaxRows: 8, tableMaxCols: 18, tableMaxCellChars: 160,
  });
  await fs.writeFile(path.join(workDir, 'template_inspect.ndjson'), overview.ndjson);
  console.log(overview.ndjson);
  const sheet = workbook.worksheets.getItemAt(0);
  const baseline = await workbook.render({ sheetName: sheet.name, range: 'A1:R12', scale: 1, format: 'png' });
  await fs.writeFile(path.join(workDir, 'template_before.png'), new Uint8Array(await baseline.arrayBuffer()));
  console.log(JSON.stringify({ baseline: path.join(workDir, 'template_before.png') }));
} else if (mode === 'compact') {
  const outputPath = argument4;
  if (!outputPath || !flags.includes('--authoring-marked')) throw new Error('Requires a separate successful authoring marker immediately before this build.');
  if (path.resolve(inputPath) === path.resolve(outputPath)) throw new Error('Never overwrite the downloaded source template.');
  const plan = JSON.parse(await fs.readFile(argument3, 'utf8'));
  if (plan.baselineVisualReviewed !== true || !Array.isArray(plan.ready) || plan.ready.length === 0) throw new Error('Requires a reviewed baseline and ready SKU records.');
  const sheet = workbook.worksheets.getItem(plan.template.sheet);
  const records = [...plan.ready].sort((a,b) => a.source_row-b.source_row);
  const pendingArticles = new Set(plan.rules?.requires_per_activity_user_confirmation_articles ?? ['YX9354001']);
  if (records.some(record => pendingArticles.has(record.article_no))) throw new Error('Upload contains an article requiring separate per-activity user confirmation.');
  const approvals = plan.per_activity_user_price_confirmations ?? [];
  if (records.filter(record => record.article_no === 'YX9354001').some(record => !approvals.some(approval => approval.activity_id === String(plan.activity_id) && approval.sku_id === record.sku_id && approval.registration_price === record.proposed_price && approval.human_approved === true))) throw new Error('Moon SKU requires explicit matching per-activity price approval evidence.');
  const activityId=String(plan.artifact_output_id ?? plan.activity_id).replace(/[^A-Za-z0-9_-]/g,'_');
  const headerRow=plan.template.header_row ?? 2;
  const columns=Object.keys(plan.template.columns);
  const lastColumn=columns.at(-1);
  const colMap=plan.template.column_map ?? {sku_id:7,article_no:2,channels:5,registration_price:8,stock_entry:10};
  const fieldColumn=(field)=>columns[colMap[field]];
  if (![fieldColumn('sku_id'),fieldColumn('article_no'),fieldColumn('channels'),fieldColumn('registration_price'),fieldColumn('stock_entry')].every(Boolean)) throw new Error('Missing template column mapping.');
  const headerBefore = sheet.getRange(`A1:${lastColumn}${headerRow}`).values;
  const retained = [];
  for (const [index, record] of records.entries()) {
    const destRow = index+headerRow+1;
    if (record.source_row < destRow || record.channel !== '品牌官方' || record.stock_entry !== '不限制' || record.status !== 'ready') throw new Error(`Invalid compact record ${record.sku_id}`);
    const original = sheet.getRange(`A${record.source_row}:${lastColumn}${record.source_row}`).values[0];
    if (String(original[colMap.sku_id]) !== record.sku_id || String(original[colMap.article_no]).trim().toUpperCase() !== record.article_no) throw new Error(`Source identity mismatch ${record.sku_id}`);
    // Moving ascending source rows upward cannot overwrite a future source.
    sheet.getRange(`A${destRow}:${lastColumn}${destRow}`).copyFrom(sheet.getRange(`A${record.source_row}:${lastColumn}${record.source_row}`), 'all');
    sheet.getRange(`${fieldColumn('channels')}${destRow}`).values = [['品牌官方']];
    sheet.getRange(`${fieldColumn('registration_price')}${destRow}`).values = [[record.proposed_price]];
    sheet.getRange(`${fieldColumn('stock_entry')}${destRow}`).values = [['不限制']];
    const expected = [...original]; expected[colMap.channels]='品牌官方'; expected[colMap.registration_price]=record.proposed_price; expected[colMap.stock_entry]='不限制';
    retained.push({sourceRow:record.source_row,outputRow:destRow,skuId:record.sku_id,expected});
  }
  // The importer receives only retained product records; discarded rows lose
  // their contents and formatting, while the template's first two rows remain.
  sheet.getRange(`A${records.length+headerRow+1}:${lastColumn}${plan.template.last_source_row ?? plan.summary.all_export_sku_count+headerRow}`).clear({applyTo:'all'});
  workbook.recalculate();
  if (JSON.stringify(headerBefore)!==JSON.stringify(sheet.getRange(`A1:${lastColumn}${headerRow}`).values)) throw new Error('Template instruction/header changed.');
  for (const row of retained) {
    const got=sheet.getRange(`A${row.outputRow}:${lastColumn}${row.outputRow}`).values[0];
    if (JSON.stringify(got)!==JSON.stringify(row.expected)) throw new Error(`Compacted row verification failed ${row.skuId}`);
  }
  const inspect=await workbook.inspect({kind:'sheet,table',maxChars:2500,tableMaxRows:3,tableMaxCols:17});
  console.log(inspect.ndjson);
  const image=await workbook.render({sheetName:sheet.name,range:`A1:${lastColumn}10`,scale:1,format:'png'});
  await fs.writeFile(path.join(path.dirname(argument3),`activity_${activityId}_after.png`),new Uint8Array(await image.arrayBuffer()));
  const xlsx=await SpreadsheetFile.exportXlsx(workbook);
  await xlsx.save(outputPath);
  await fs.writeFile(path.join(path.dirname(argument3),`activity_${activityId}_upload_manifest.json`),JSON.stringify({inputPath,outputPath,rows:retained},null,2));
  console.log(JSON.stringify({outputPath,skuCount:records.length,lastDataRow:records.length+headerRow,nativePreservationAuditRequired:true}));
} else {
  const outputPath = argument4;
  if (!outputPath || !flags.includes('--authoring-marked')) throw new Error('Requires a separate successful authoring marker immediately before this build.');
  if (path.resolve(inputPath) === path.resolve(outputPath)) throw new Error('Never overwrite the downloaded source template.');
  const plan = JSON.parse(await fs.readFile(argument3, 'utf8'));
  if (!Array.isArray(plan.patches) || !Array.isArray(plan.allowedCells) || plan.patches.length === 0) throw new Error('Plan must contain nonempty patches and explicit allowedCells.');
  if (plan.baselineVisualReviewed !== true) throw new Error('The source template must be rendered and visually inspected first.');
  const allowed = new Set(plan.allowedCells);
  const seen = new Set();
  for (const patch of plan.patches) {
    const key = `${patch.sheet}!${patch.cell}`;
    if (!allowed.has(key) || seen.has(key) || !/^[A-Z]+[1-9][0-9]*$/.test(patch.cell)) throw new Error(`Invalid, duplicate, or unauthorized patch: ${key}`);
    if (!['string', 'number', 'boolean'].includes(typeof patch.value) && patch.value !== null) throw new Error(`Invalid cell value: ${key}`);
    if (typeof patch.value === 'number' && !Number.isFinite(patch.value)) throw new Error(`Nonfinite number: ${key}`);
    seen.add(key);
  }
  // Patch only the declared input cells. Retain tabs, columns, styles,
  // names, validations, filters, protection, and existing identifiers.
  for (const patch of plan.patches) {
    workbook.worksheets.getItem(patch.sheet).getRange(patch.cell).values = [[patch.value]];
  }
  workbook.recalculate();
  for (const patch of plan.patches) {
    const got = workbook.worksheets.getItem(patch.sheet).getRange(patch.cell).values[0][0];
    if (got !== patch.value) throw new Error(`Patch verification failed: ${patch.sheet}!${patch.cell}`);
  }
  const errorScan = await workbook.inspect({
    kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',
    options: { useRegex: true, maxResults: 100 }, maxChars: 6000,
  });
  console.log(errorScan.ndjson);
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const first = plan.patches[0];
  const after = await workbook.render({ sheetName: first.sheet, range: plan.reviewRange ?? 'A1:R12', scale: 1, format: 'png' });
  await fs.writeFile(path.join(path.dirname(argument3), 'template_after.png'), new Uint8Array(await after.arrayBuffer()));
  const xlsx = await SpreadsheetFile.exportXlsx(workbook);
  await xlsx.save(outputPath);
  console.log(JSON.stringify({ outputPath, patchedCells: plan.patches.length, nativePreservationAuditRequired: true }));
}

// Pure pricing helper. discount is represented as 7 for seven-tenths.
// configured discounts remain preferred; platform maximum is used only when
// the configured price is too high. Every output uses the actual rounded price.
export function activityDecision({ bidPrice, configuredDiscount, platformMaxPrice, productCost, upgradedGiftbox = false, moneyDecimals = 0 }) {
  if (![bidPrice, configuredDiscount, platformMaxPrice, productCost].every(Number.isFinite) || bidPrice <= 0 || platformMaxPrice <= 0) throw new Error('Missing or invalid pricing input.');
  const configuredPrice = bidPrice * configuredDiscount / 10;
  const lowerDiscountRequired = configuredPrice > platformMaxPrice + 1e-9;
  const price = Math.floor((Math.min(configuredPrice, platformMaxPrice) + 1e-9) * (10 ** moneyDecimals)) / (10 ** moneyDecimals);
  const giftboxCost = upgradedGiftbox ? 13 : 0;
  const platformFee = Math.max(price * 0.22, 45);
  const profit = price - platformFee - 14.5 - price * 0.10 - productCost - giftboxCost;
  const margin = profit / price;
  return { price, configuredPrice, lowerDiscountRequired, discount: price / bidPrice * 10, productCost, giftboxCost, platformFee, profit, margin, eligible: margin > 0.03 };
}
