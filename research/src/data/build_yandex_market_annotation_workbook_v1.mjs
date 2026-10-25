import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const inputCsv = process.argv[2];
const outputXlsx = process.argv[3];
if (!inputCsv || !outputXlsx) throw new Error("Usage: node build_annotation_workbook.mjs INPUT.csv OUTPUT.xlsx");

const csvText = (await fs.readFile(inputCsv, "utf8")).replace(/^\uFEFF/, "");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "Разметка" });
const sheet = workbook.worksheets.getItem("Разметка");
sheet.showGridLines = false;
sheet.freezePanes.freezeRows(1);
sheet.freezePanes.freezeColumns(3);

const used = sheet.getUsedRange();
used.format.font = { name: "Arial", size: 10, color: "#1F2937" };
used.format.verticalAlignment = "top";
sheet.getRange("A1:P1").format = {
  fill: "#1F4E78",
  font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "inside", style: "thin", color: "#FFFFFF" },
};
sheet.getRange("A2:B301").format.horizontalAlignment = "center";
sheet.getRange("C2:C301").format.wrapText = true;
sheet.getRange("D2:P301").format.wrapText = true;
sheet.getRange("D2:D301").format.fill = "#FFF2CC";
sheet.getRange("F2:P301").format.fill = "#FFF2CC";
sheet.getRange("E2:E301").format.fill = "#D9EAF7";
sheet.getRange("A1:A301").format.columnWidth = 14;
sheet.getRange("B1:B301").format.columnWidth = 20;
sheet.getRange("C1:C301").format.columnWidth = 90;
sheet.getRange("D1:D301").format.columnWidth = 18;
sheet.getRange("E1:E301").format.columnWidth = 12;
sheet.getRange("F1:F301").format.columnWidth = 18;
sheet.getRange("G1:L301").format.columnWidth = 18;
sheet.getRange("M1:M301").format.columnWidth = 26;
sheet.getRange("N1:N301").format.columnWidth = 28;
sheet.getRange("O1:O301").format.columnWidth = 18;
sheet.getRange("P1:P301").format.columnWidth = 32;
sheet.getRange("1:1").format.rowHeight = 34;
sheet.getRange("A2:P301").format.autofitRows();

sheet.getRange("D2:D301").dataValidation = { rule: { type: "list", values: ["маломерит", "соответствует", "большемерит", "нет сигнала"] } };
sheet.getRange("E2").formulas = [["=IF(D2=\"маломерит\",-1,IF(D2=\"соответствует\",0,IF(D2=\"большемерит\",1,\"\")))"]];
sheet.getRange("E2:E301").fillDown();
sheet.getRange("F2:F301").dataValidation = { rule: { type: "list", values: ["explicit", "implicit", "none"] } };
sheet.getRange("G2:G301").dataValidation = { rule: { type: "list", values: ["нет", "рост", "грудь", "талия", "бёдра", "другое"] } };
sheet.getRange("H2:I301").dataValidation = { rule: { type: "list", values: ["рост", "грудь", "талия", "бёдра", "другое"] } };
sheet.getRange("J2:J301").dataValidation = { rule: { type: "list", values: ["не указана", "грудь", "талия", "бёдра", "плечи", "рукава", "длина", "другое"] } };
sheet.getRange("K2:L301").dataValidation = { rule: { type: "list", values: ["грудь", "талия", "бёдра", "плечи", "рукава", "длина", "другое"] } };
sheet.getRange("M2:M301").dataValidation = { rule: { type: "list", values: ["не указано", "оставил заказанный размер", "взял другой размер", "обменял", "вернул", "заказал несколько размеров", "другое"] } };
sheet.getRange("N2:N301").dataValidation = { rule: { type: "list", values: ["согласованный", "противоречивый", "неясно"] } };
sheet.getRange("O2:O301").dataValidation = { rule: { type: "list", values: ["низкая", "средняя", "высокая"] } };

const guide = workbook.worksheets.add("Инструкция");
guide.showGridLines = false;
guide.getRange("A1:B18").values = [
  ["Аудит отзывов Яндекс Маркета", "Разметка v4"],
  ["Что видно", "Используйте только текст отзыва и заказанный размер. Не открывайте карточку товара."],
  ["Метка посадки", "маломерит / соответствует / большемерит / нет сигнала"],
  ["Граница «нет сигнала»", "«Сел хорошо», «подошло», «мало», «велико» без сравнения с обычным размером не задают направление размерной сетки."],
  ["Код метки", "Заполняется автоматически: маломерит = -1; соответствует = 0; большемерит = 1; для «нет сигнала» остаётся пустым."],
  ["Явность сигнала", "explicit / implicit / none; при метке «нет сигнала» обязательно none"],
  ["Параметры тела", "До 3 значений в отдельных колонках: рост, грудь, талия, бёдра, другое. Если нет — выбрать «нет» в первой колонке."],
  ["Зоны посадки", "До 3 значений в отдельных колонках: грудь, талия, бёдра, плечи, рукава, длина, другое. Если нет — выбрать «не указана» в первой колонке."],
  ["Действие пользователя", "не указано / оставил заказанный размер / взял другой размер / обменял / вернул / заказал несколько размеров / другое"],
  ["Согласованность", "согласованный / противоречивый / неясно; при метке «нет сигнала» обычно «неясно»"],
  ["Низкая информативность", "Нет пригодного направления или есть только общее утверждение без подтверждающего контекста."],
  ["Средняя информативность", "Есть один независимый подтверждающий элемент: зона, параметр тела, действие или сравнение размеров."],
  ["Высокая информативность", "Есть явное сравнение обычного и выбранного размера либо несколько независимых подтверждающих элементов."],
  ["Порядок работы", "Сначала метка посадки и явность, затем параметры и зоны, действие, согласованность; информативность заполнить последней."],
  ["Не додумывать", "Используйте только явно указанные сведения. Для отсутствующего или неясного признака выбирайте нейтральную метку."],
  ["Комментарий", "Кратко поясните спорное решение. Для очевидных строк комментарий не обязателен."],
  ["Язык полей", "Таблица для ручной разметки использует русские названия и значения, как два исходных файла разметчиков. Английские ключи остаются только во внутренних ML-файлах."],
  ["Статус набора", "External audit одного разметчика. Cohen's Kappa для него не рассчитывается."],
];
guide.getRange("A1:B18").format.font = { name: "Arial", size: 11, color: "#1F2937" };
guide.getRange("A1:B1").format = { fill: "#1F4E78", font: { name: "Arial", size: 12, bold: true, color: "#FFFFFF" } };
guide.getRange("A2:A18").format = { fill: "#D9EAF7", font: { name: "Arial", size: 11, bold: true, color: "#1F2937" } };
guide.getRange("A1:A18").format.columnWidth = 30;
guide.getRange("B1:B18").format.columnWidth = 95;
guide.getRange("A1:B18").format.wrapText = true;
guide.getRange("A1:B18").format.verticalAlignment = "top";
guide.getRange("1:18").format.autofitRows();

workbook.recalculate();
const check = await workbook.inspect({ kind: "table", range: "Разметка!A1:P8", include: "values,formulas", tableMaxRows: 8, tableMaxCols: 16 });
console.log(check.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: { useRegex: true, maxResults: 100 }, summary: "final formula error scan" });
console.log(errors.ndjson);
const preview = await workbook.render({ sheetName: "Разметка", range: "A1:P8", scale: 1, format: "png" });
await fs.writeFile(outputXlsx.replace(/\.xlsx$/i, "_preview.png"), new Uint8Array(await preview.arrayBuffer()));
const guidePreview = await workbook.render({ sheetName: "Инструкция", range: "A1:B18", scale: 1, format: "png" });
await fs.writeFile(outputXlsx.replace(/\.xlsx$/i, "_guide_preview.png"), new Uint8Array(await guidePreview.arrayBuffer()));
const out = await SpreadsheetFile.exportXlsx(workbook);
await out.save(outputXlsx);

const xlsxBytes = await fs.readFile(outputXlsx);
const manifestPath = path.join(path.dirname(outputXlsx), "manifest.json");
const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
manifest.files[path.basename(outputXlsx)] = {
  bytes: xlsxBytes.byteLength,
  sha256: createHash("sha256").update(xlsxBytes).digest("hex"),
};
await fs.writeFile(manifestPath, JSON.stringify(manifest, null, 2) + "\n", "utf8");
