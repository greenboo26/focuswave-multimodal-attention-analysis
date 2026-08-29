import fs from 'node:fs/promises';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const base = 'D:/Project/厚粲杯/08_算法';
const rows = JSON.parse(await fs.readFile(`${base}/data/审计/mmwave_audit_data.json`, 'utf8'));
const outDir = `${base}/output/00_最新审计/mmwave_audit`;
await fs.mkdir(outDir, { recursive: true });

const wb = Workbook.create();
const summary = wb.worksheets.add('汇总');
const audit = wb.worksheets.add('逐被试核查');
const rules = wb.worksheets.add('判定说明');
for (const s of [summary, audit, rules]) s.showGridLines = false;

const invalid = rows.filter(r => r.Status === '无效').length;
const review = rows.filter(r => r.Status === '需复核').length;
const valid = rows.filter(r => r.Status === '有效').length;
const roots = [...new Set(rows.map(r => r.SourceRoot))];

summary.getRange('A1:H1').merge();
summary.getRange('A1').values = [['正式实验毫米波数据完整性核查']];
summary.getRange('A1:H1').format = { fill: '#1F4E78', font: { bold: true, color: '#FFFFFF', size: 16 }, horizontalAlignment: 'center', verticalAlignment: 'center' };
summary.getRange('A2:H2').merge();
summary.getRange('A2').values = [['数据来源：E:/Data 与 F:/正式实验；编号跨号不作为缺失判定。']];
summary.getRange('A2:H2').format = { fill: '#D9EAF7', font: { color: '#1F1F1F', italic: true }, wrapText: true };
summary.getRange('A4:B7').values = [
  ['指标', '数量'],
  ['被试目录总数', rows.length],
  ['有效', valid],
  ['无效', invalid],
];
summary.getRange('A8:B8').values = [['需复核', review]];
summary.getRange('A4:B4').format = { fill: '#5B9BD5', font: { bold: true, color: '#FFFFFF' }, horizontalAlignment: 'center' };
summary.getRange('A5:B8').format.borders = { preset: 'all', style: 'thin', color: '#D9E2F3' };
summary.getRange('A8:B8').format = { fill: '#FFF2CC', font: { bold: true } };
summary.getRange('D4:H4').values = [['无效类型', '数量', '被试编号', '判定依据', '备注']];
summary.getRange('D5:H6').values = [
  ['完全没有 mmwave 文件', rows.filter(r => r.Reason === '未发现 mmwave 文件').length, rows.filter(r => r.Reason === '未发现 mmwave 文件').map(r => r.Subject).join('、'), 'mmwave 子目录为空或不存在', '编号跨号不影响判定'],
  ['文件存在但未实际录制', rows.filter(r => r.Reason.includes('未实际录制')).length, rows.filter(r => r.Reason.includes('未实际录制')).map(r => r.Subject).join('、'), '时间戳为空，bin 文件仅 32 字节', '明确标记为无效'],
];
summary.getRange('D4:H4').format = { fill: '#5B9BD5', font: { bold: true, color: '#FFFFFF' }, horizontalAlignment: 'center', wrapText: true };
summary.getRange('D5:H6').format = { wrapText: true, verticalAlignment: 'top' };
summary.getRange('D4:H6').format.borders = { preset: 'all', style: 'thin', color: '#D9E2F3' };
summary.getRange('A10:H10').merge();
summary.getRange('A10').values = [['判定口径']];
summary.getRange('A10:H10').format = { fill: '#1F4E78', font: { bold: true, color: '#FFFFFF' } };
summary.getRange('A11:H13').merge(true);
summary.getRange('A11:H13').values = [
  ['无效：完全没有 mmwave 文件，或 meta.json 显示 frame_count=0，同时时间戳为空、bin 文件仅 32 字节。'],
  ['需复核：毫米波数据文件存在且体量明显，但缺少元数据或文件不完整，不能仅凭目录结构判无效。'],
  ['有效：毫米波主文件、时间戳文件、元数据均存在，且未触发无效规则。录制时长保留原始 meta.json 数值。'],
];
summary.getRange('A11:H13').format = { wrapText: true, verticalAlignment: 'center' };
summary.getRange('A15:H15').merge();
summary.getRange('A15').values = [['需复核对象：sub-099。该目录有大量 .npz 分片、约 1.8 GB bin 文件及时间戳文件，但缺少 meta.json，未将其计入无效。']];
summary.getRange('A15:H15').format = { fill: '#FFF2CC', wrapText: true };

const headers = ['来源目录','被试编号','文件夹名','状态','判定依据','录制时长(s)','帧数','帧率(fps)','bin大小(GB)','时间戳大小(MB)','NPZ文件数','mmwave文件数','mmwave目录'];
audit.getRange(`A1:M${rows.length+1}`).values = [headers, ...rows.map(r => [r.SourceRoot, r.Subject, r.SubjectFolder, r.Status, r.Reason, r.Duration_s, r.FrameCount, r.FPS, r.Bin_GB, r.Timestamp_MB, r.NPZ_Count, r.MMwaveFileCount, r.MMwavePath])];
audit.getRange(`A1:M1`).format = { fill: '#1F4E78', font: { bold: true, color: '#FFFFFF' }, horizontalAlignment: 'center', wrapText: true };
audit.getRange(`A1:M${rows.length+1}`).format.borders = { preset: 'insideHorizontal', style: 'thin', color: '#E6E6E6' };
audit.getRange(`F2:J${rows.length+1}`).format.numberFormat = '0.00';
audit.getRange(`G2:G${rows.length+1}`).format.numberFormat = '#,##0';
audit.getRange(`K2:L${rows.length+1}`).format.numberFormat = '0';
audit.getRange(`D2:D${rows.length+1}`).conditionalFormats.add('containsText', { text: '无效', format: { fill: '#F4CCCC', font: { bold: true, color: '#9C0006' } } });
audit.getRange(`D2:D${rows.length+1}`).conditionalFormats.add('containsText', { text: '需复核', format: { fill: '#FFF2CC', font: { bold: true, color: '#7F6000' } } });
audit.getRange(`D2:D${rows.length+1}`).conditionalFormats.add('containsText', { text: '有效', format: { fill: '#D9EAD3', font: { color: '#274E13' } } });
audit.tables.add(`A1:M${rows.length+1}`, true, 'MmwaveAuditTable');
audit.freezePanes.freezeRows(1);

rules.getRange('A1:D1').values = [['字段','内容','','']];
rules.getRange('A1:D1').format = { fill: '#1F4E78', font: { bold: true, color: '#FFFFFF' } };
rules.getRange('A2:B5').values = [
  ['检查范围','E:/Data 与 F:/正式实验下所有一级被试目录'],
  ['编号说明','编号跨号属于正常情况，不按编号连续性判定缺失'],
  ['无效判定','无 mmwave 文件；或时间戳为空且 bin 文件仅 32 字节；或 frame_count=0'],
  ['需复核判定','存在数据文件但缺少 meta.json 或文件组合不完整'],
];
rules.getRange('A2:B5').format = { wrapText: true, verticalAlignment: 'top' };
rules.getRange('A1:B5').format.borders = { preset: 'all', style: 'thin', color: '#D9E2F3' };

for (const s of [summary, audit, rules]) s.getUsedRange().format.font = { name: 'Microsoft YaHei', size: 10 };
summary.getRange('A1:H1').format.font = { name: 'Microsoft YaHei', size: 16, bold: true, color: '#FFFFFF' };
summary.getRange('A1:H15').format.wrapText = true;
summary.getRange('A:A').format.columnWidth = 20; summary.getRange('B:B').format.columnWidth = 12;
summary.getRange('D:D').format.columnWidth = 22; summary.getRange('E:E').format.columnWidth = 10; summary.getRange('F:F').format.columnWidth = 18; summary.getRange('G:G').format.columnWidth = 34; summary.getRange('H:H').format.columnWidth = 18;
audit.getRange('A:A').format.columnWidth = 16; audit.getRange('B:C').format.columnWidth = 12; audit.getRange('D:D').format.columnWidth = 10; audit.getRange('E:E').format.columnWidth = 36; audit.getRange('F:J').format.columnWidth = 14; audit.getRange('K:L').format.columnWidth = 12; audit.getRange('M:M').format.columnWidth = 38;
rules.getRange('A:A').format.columnWidth = 18; rules.getRange('B:B').format.columnWidth = 80;

const check = await wb.inspect({ kind: 'table', sheetId: '汇总', range: 'A1:H15', include: 'values,formulas', tableMaxRows: 20, tableMaxCols: 10 });
console.log(check.ndjson);
const errors = await wb.inspect({ kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A', options: { useRegex: true, maxResults: 100 }, summary: 'formula error scan' });
console.log(errors.ndjson);
const preview = await wb.render({ sheetName: '汇总', range: 'A1:H15', scale: 1.5, format: 'png' });
await fs.writeFile(`${outDir}/mmwave_audit_preview.png`, new Uint8Array(await preview.arrayBuffer()));
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(`${outDir}/毫米波数据逐被试核查表.xlsx`);
console.log(JSON.stringify({rows: rows.length, valid, invalid, review, output: `${outDir}/毫米波数据逐被试核查表.xlsx`}));


