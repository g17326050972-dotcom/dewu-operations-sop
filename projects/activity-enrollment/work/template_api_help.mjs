import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(process.argv[2]));
console.log(wb.help('range.delete',{include:'index,examples,notes',maxChars:6000}).ndjson);
