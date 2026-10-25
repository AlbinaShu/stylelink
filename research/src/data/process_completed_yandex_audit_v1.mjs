import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [inputXlsx, outputDir, sourceJsonl] = process.argv.slice(2);
if (!inputXlsx || !outputDir || !sourceJsonl) {
  throw new Error("Usage: node process_completed_yandex_audit.mjs INPUT.xlsx OUTPUT_DIR SOURCE_METADATA.jsonl");
}

const expectedHeaders = [
  "review_id", "заказанный размер", "текст отзыва", "метка посадки", "код метки",
  "явность сигнала", "параметры тела 1", "параметры тела 2", "параметры тела 3",
  "зона посадки 1", "зона посадки 2", "зона посадки 3", "действие пользователя",
  "согласованность внутри отзыва", "информативность", "комментарий",
];

const fitMap = new Map([
  ["маломерит", ["runs_small", -1]],
  ["соответствует", ["true_to_size", 0]],
  ["большемерит", ["runs_large", 1]],
  ["нет сигнала", ["no_signal", null]],
]);
const bodyMap = new Map([["рост", "height"], ["грудь", "bust"], ["талия", "waist"], ["бёдра", "hips"], ["другое", "other"]]);
const zoneMap = new Map([["грудь", "bust"], ["талия", "waist"], ["бёдра", "hips"], ["плечи", "shoulders"], ["рукава", "sleeves"], ["длина", "length"], ["другое", "other"]]);
const actionMap = new Map([
  ["не указано", "not_specified"],
  ["оставил заказанный размер", "kept_ordered_size"],
  ["взял другой размер", "chose_another_size"],
  ["обменял", "exchanged"],
  ["вернул", "returned"],
  ["заказал несколько размеров", "ordered_multiple_sizes"],
  ["другое", "other"],
]);
const consistencyMap = new Map([["согласованный", "consistent"], ["противоречивый", "contradictory"], ["неясно", "unclear"]]);
const informativenessMap = new Map([["низкая", "low"], ["средняя", "medium"], ["высокая", "high"]]);
const explicitness = new Set(["explicit", "implicit", "none"]);

const scalar = (value) => value === null || value === undefined ? "" : String(value).trim();
const csvCell = (value) => {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};
const writeCsv = async (filePath, headers, rows) => {
  const lines = [headers.map(csvCell).join(",")];
  for (const row of rows) lines.push(headers.map((header) => csvCell(row[header])).join(","));
  await fs.writeFile(filePath, "\uFEFF" + lines.join("\n") + "\n", "utf8");
};
const sha256 = async (filePath) => createHash("sha256").update(await fs.readFile(filePath)).digest("hex");

const sourceRows = (await fs.readFile(sourceJsonl, "utf8")).trim().split("\n").filter(Boolean).map((line) => JSON.parse(line));
const sourceByAuditId = new Map(sourceRows.map((row) => [row.audit_id, row]));

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputXlsx));
workbook.recalculate();
const sheet = workbook.worksheets.getItem("Разметка");
const matrix = sheet.getRange("A1:P301").values;
const headers = matrix[0].map(scalar);
if (JSON.stringify(headers) !== JSON.stringify(expectedHeaders)) {
  throw new Error(`Unexpected headers: ${JSON.stringify(headers)}`);
}

const issues = [];
const humanRows = [];
const normalizedRows = [];
const seenIds = new Set();

for (let index = 1; index < matrix.length; index += 1) {
  const sourceRow = index + 1;
  const values = matrix[index].map(scalar);
  const row = Object.fromEntries(expectedHeaders.map((header, col) => [header, values[col] ?? ""]));
  const id = row.review_id;
  const source = sourceByAuditId.get(id);
  if (!id) issues.push({ source_row: sourceRow, field: "review_id", issue: "missing" });
  if (seenIds.has(id)) issues.push({ source_row: sourceRow, field: "review_id", issue: "duplicate", value: id });
  seenIds.add(id);
  if (!source) issues.push({ source_row: sourceRow, field: "review_id", issue: "missing_source_metadata", value: id });
  if (!row["текст отзыва"]) issues.push({ source_row: sourceRow, field: "текст отзыва", issue: "missing" });

  const fit = fitMap.get(row["метка посадки"]);
  if (!fit) issues.push({ source_row: sourceRow, field: "метка посадки", issue: "missing_or_invalid", value: row["метка посадки"] });
  const expectedCode = fit?.[1] ?? null;
  const actualCode = row["код метки"] === "" ? null : Number(row["код метки"]);
  if ((expectedCode === null && actualCode !== null) || (expectedCode !== null && actualCode !== expectedCode)) {
    issues.push({ source_row: sourceRow, field: "код метки", issue: "does_not_match_fit_label", value: row["код метки"] });
  }

  const normalizationFlags = [];
  let normalizedExplicitness = row["явность сигнала"];
  if (!explicitness.has(row["явность сигнала"])) issues.push({ source_row: sourceRow, field: "явность сигнала", issue: "missing_or_invalid", value: row["явность сигнала"] });
  if (fit?.[0] === "no_signal" && row["явность сигнала"] !== "none") {
    issues.push({ source_row: sourceRow, field: "явность сигнала", issue: "no_signal_requires_none", value: row["явность сигнала"], normalized_to: "none" });
    normalizedExplicitness = "none";
    normalizationFlags.push("signal_explicitness_corrected_to_none_for_no_signal");
  }
  if (fit && fit[0] !== "no_signal" && row["явность сигнала"] === "none") issues.push({ source_row: sourceRow, field: "явность сигнала", issue: "directed_fit_cannot_be_none", value: row["явность сигнала"] });

  const rawBody = [row["параметры тела 1"], row["параметры тела 2"], row["параметры тела 3"]].filter(Boolean);
  let bodyParameters = [];
  if (rawBody[0] === "нет") {
    if (rawBody.length > 1) issues.push({ source_row: sourceRow, field: "параметры тела", issue: "none_with_extra_values", value: rawBody.join("|") });
  } else if (rawBody.length === 0) {
    issues.push({ source_row: sourceRow, field: "параметры тела 1", issue: "missing" });
  } else {
    bodyParameters = rawBody.map((value) => bodyMap.get(value));
    rawBody.forEach((value) => { if (!bodyMap.has(value)) issues.push({ source_row: sourceRow, field: "параметры тела", issue: "invalid", value }); });
  }

  const rawZones = [row["зона посадки 1"], row["зона посадки 2"], row["зона посадки 3"]].filter(Boolean);
  let fitZones = [];
  if (rawZones[0] === "не указана") {
    if (rawZones.length > 1) issues.push({ source_row: sourceRow, field: "зона посадки", issue: "none_with_extra_values", value: rawZones.join("|") });
  } else if (rawZones.length === 0) {
    issues.push({ source_row: sourceRow, field: "зона посадки 1", issue: "missing" });
  } else {
    fitZones = rawZones.map((value) => zoneMap.get(value));
    rawZones.forEach((value) => { if (!zoneMap.has(value)) issues.push({ source_row: sourceRow, field: "зона посадки", issue: "invalid", value }); });
  }

  const action = actionMap.get(row["действие пользователя"]);
  if (!action) issues.push({ source_row: sourceRow, field: "действие пользователя", issue: "missing_or_invalid", value: row["действие пользователя"] });
  const consistency = consistencyMap.get(row["согласованность внутри отзыва"]);
  if (!consistency) issues.push({ source_row: sourceRow, field: "согласованность внутри отзыва", issue: "missing_or_invalid", value: row["согласованность внутри отзыва"] });
  const informativeness = informativenessMap.get(row["информативность"]);
  if (!informativeness) issues.push({ source_row: sourceRow, field: "информативность", issue: "missing_or_invalid", value: row["информативность"] });

  humanRows.push(row);
  normalizedRows.push({
    schema_version: "review_annotation_v4",
    dataset_version: "yandex_market_external_audit_labeled_v1",
    annotator_id: "researcher_1",
    source_file: "Аудит отзывов Яндекс Маркета — разметка v4",
    source_row: sourceRow,
    review_id: id,
    marketplace_review_id: source?.review_id ?? "",
    product_id: source?.product_id ?? "",
    category: source?.category ?? "",
    selection_stratum: source?.selection_stratum ?? "",
    source_page_url: source?.source_page_url ?? "",
    ordered_size: row["заказанный размер"],
    review_text: row["текст отзыва"],
    fit_label: fit?.[0] ?? "",
    fit_code: expectedCode ?? "",
    signal_explicitness: normalizedExplicitness,
    body_parameters_json: JSON.stringify(bodyParameters.filter(Boolean)),
    fit_zones_json: JSON.stringify(fitZones.filter(Boolean)),
    user_action: action ?? "",
    internal_consistency: consistency ?? "",
    informativeness: informativeness ?? "",
    comment: row["комментарий"],
    normalization_flags_json: JSON.stringify(normalizationFlags),
  });
}

await fs.mkdir(outputDir, { recursive: true });
const xlsxPath = path.join(outputDir, "yandex_market_audit_300_labeled.xlsx");
const humanPath = path.join(outputDir, "yandex_market_audit_300_labeled_ru.csv");
const normalizedPath = path.join(outputDir, "yandex_market_audit_300_labeled_v4.csv");
const jsonlPath = path.join(outputDir, "yandex_market_audit_300_labeled_v4.jsonl");
const reportPath = path.join(outputDir, "validation_report.json");
await fs.copyFile(inputXlsx, xlsxPath);
await writeCsv(humanPath, expectedHeaders, humanRows);
const normalizedHeaders = Object.keys(normalizedRows[0]);
await writeCsv(normalizedPath, normalizedHeaders, normalizedRows);
await fs.writeFile(jsonlPath, normalizedRows.map((row) => JSON.stringify(row)).join("\n") + "\n", "utf8");

const countBy = (field) => Object.fromEntries([...normalizedRows.reduce((map, row) => map.set(row[field], (map.get(row[field]) ?? 0) + 1), new Map())].sort());
const report = {
  checked_at: "2026-10-23",
  source_google_sheet: "https://docs.google.com/spreadsheets/d/180uZg85rI86OHn5q4jdA8PzRBe8J8cvf-VnyT_Rl5zs/edit",
  rows: normalizedRows.length,
  unique_review_ids: seenIds.size,
  validation_status: issues.length === 0 ? "passed" : issues.every((issue) => Object.hasOwn(issue, "normalized_to")) ? "normalized_with_correction" : "issues_found",
  source_validation_status: issues.length === 0 ? "passed" : "issues_found",
  normalized_validation_status: issues.every((issue) => Object.hasOwn(issue, "normalized_to")) ? "passed" : "issues_found",
  issue_count: issues.length,
  automatic_corrections_applied: normalizedRows.filter((row) => row.normalization_flags_json !== "[]").length,
  issues,
  distributions: {
    fit_label: countBy("fit_label"),
    signal_explicitness: countBy("signal_explicitness"),
    informativeness: countBy("informativeness"),
    user_action: countBy("user_action"),
    internal_consistency: countBy("internal_consistency"),
  },
};
await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + "\n", "utf8");

const deliverables = [xlsxPath, humanPath, normalizedPath, jsonlPath, reportPath];
const manifest = {
  dataset: "yandex_market_external_audit_labeled_v1",
  completed_at: "2026-10-23",
  source_google_sheet: report.source_google_sheet,
  annotation_protocol: "single-annotator external audit using ANNOTATION_GUIDE_V4",
  rows: report.rows,
  unique_review_ids: report.unique_review_ids,
  validation_status: report.validation_status,
  source_validation_status: report.source_validation_status,
  normalized_validation_status: report.normalized_validation_status,
  issue_count: report.issue_count,
  automatic_corrections_applied: report.automatic_corrections_applied,
  distributions: report.distributions,
  files: {},
};
for (const filePath of deliverables) {
  const stat = await fs.stat(filePath);
  manifest.files[path.basename(filePath)] = { bytes: stat.size, sha256: await sha256(filePath) };
}
const manifestPath = path.join(outputDir, "manifest.json");
await fs.writeFile(manifestPath, JSON.stringify(manifest, null, 2) + "\n", "utf8");
const checksumPaths = [...deliverables, manifestPath];
const checksumLines = [];
for (const filePath of checksumPaths) checksumLines.push(`${await sha256(filePath)}  ${path.basename(filePath)}`);
await fs.writeFile(path.join(outputDir, "checksums.sha256"), checksumLines.join("\n") + "\n", "utf8");

const formulaCheck = await workbook.inspect({
  kind: "table",
  range: "Разметка!D2:E6",
  include: "values,formulas",
  tableMaxRows: 5,
  tableMaxCols: 2,
});
console.log(formulaCheck.ndjson);
console.log(JSON.stringify(report));
