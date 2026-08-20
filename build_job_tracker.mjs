import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "outputs/job_application_tracker";
const outputPath = `${outputDir}/Pushp_Raj_Job_Application_Tracker.xlsx`;

const workbook = Workbook.create();
const dashboard = workbook.worksheets.add("Dashboard");
const applications = workbook.worksheets.add("Applications");
const rules = workbook.worksheets.add("Rules & Answers");
const reference = workbook.worksheets.add("Reference Data");

const navy = "#12355B";
const blue = "#1F6FEB";
const lightBlue = "#EAF3FF";
const teal = "#0F766E";
const lightTeal = "#E6FFFB";
const gray = "#64748B";
const lightGray = "#F1F5F9";
const border = "#CBD5E1";

function title(sheet, range, text) {
  const r = sheet.getRange(range);
  r.merge();
  r.values = [[text]];
  r.format = {
    fill: navy,
    font: { bold: true, color: "#FFFFFF", size: 16 },
    horizontalAlignment: "left",
    verticalAlignment: "center",
  };
  r.format.rowHeight = 30;
}

function section(sheet, range, text) {
  const r = sheet.getRange(range);
  r.merge();
  r.values = [[text]];
  r.format = {
    fill: lightBlue,
    font: { bold: true, color: navy, size: 11 },
    horizontalAlignment: "left",
    verticalAlignment: "center",
  };
  r.format.rowHeight = 22;
}

// Reference data
title(reference, "A1:D1", "Reference Data - Job Application Tracker");
reference.getRange("A3:D3").values = [["Role families", "Portals", "Application statuses", "Priority-review companies"]];
reference.getRange("A3:D3").format = { fill: lightBlue, font: { bold: true, color: navy }, borders: { preset: "outside", style: "thin", color: border } };
const roleFamilies = [
  "Product Manager", "Associate Product Manager / APM", "Product Analyst", "Senior Product Analyst",
  "Strategy Analyst", "Product Owner", "Product Generalist", "Product Operations / Product Ops",
  "Product Strategy", "Growth Product / Growth Analyst",
];
const portals = ["LinkedIn", "Naukri", "Indeed", "Company careers page", "Referral", "Other"];
const statuses = ["New", "Held for review", "Ready to apply", "Applied", "Referral requested", "Interview", "Rejected", "Offer", "Closed"];
const priorityCompanies = [
  "Nanonets", "Meesho", "Navi", "Groww", "CRED", "Zomato", "Blinkit", "Swiggy", "Zepto", "Cure.fit", "Slice", "Uber", "Dezerv", "Flipkart", "super.money", "PhonePe", "Razorpay", "Cashfree Payments", "Juspay", "Zeta", "Paytm", "Paytm Money", "Fi Money", "Jupiter", "Fam", "Upstox", "Urban Company", "Porter", "OYO", "Dream11", "Postman", "BrowserStack", "Freshworks", "Chargebee", "CleverTap", "Google", "Amazon", "Microsoft", "Atlassian", "Adobe", "Walmart Global Tech", "Pine Labs",
];
const referenceRows = Math.max(roleFamilies.length, portals.length, statuses.length, priorityCompanies.length);
const refValues = [];
for (let i = 0; i < referenceRows; i++) {
  refValues.push([roleFamilies[i] ?? null, portals[i] ?? null, statuses[i] ?? null, priorityCompanies[i] ?? null]);
}
reference.getRange(`A4:D${3 + referenceRows}`).values = refValues;
reference.getRange(`A3:D${3 + referenceRows}`).format.borders = { preset: "inside", style: "thin", color: "#E2E8F0" };
reference.getRange("A:D").format.wrapText = true;
reference.getRange("A:A").format.columnWidth = 32;
reference.getRange("B:B").format.columnWidth = 24;
reference.getRange("C:C").format.columnWidth = 22;
reference.getRange("D:D").format.columnWidth = 28;
reference.showGridLines = false;

// Applications sheet
title(applications, "A1:V1", "Job Application Tracker");
applications.getRange("A2:W2").merge();
applications.getRange("A2").values = [["Add one opportunity per row. Routing is calculated from the posting age and protected-company list."]];
applications.getRange("A2:W2").format = { font: { italic: true, color: gray }, fill: "#F8FAFC", verticalAlignment: "center" };
const headers = [[
  "Job ID", "Company", "Role Title", "Role Family", "Location", "Work Arrangement", "Portal", "Job URL", "Date Posted", "Age (Days)", "Priority Company?", "Routing", "Match Score", "Status", "Application Date", "Current CTC (LPA)", "Expected CTC (LPA)", "Resume Version", "Referral Contact", "Referral Status", "Follow-up Date", "Notes",
]];
applications.getRange("A4:V4").values = headers;
applications.getRange("A4:V4").format = {
  fill: navy,
  font: { bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
};
applications.getRange("A4:V4").format.rowHeight = 34;
applications.getRange("A5:V5").values = [Array(22).fill(null)];
applications.getRange("A5:A204").formulasR1C1 = [["=IF(RC[1]=\"\",\"\",\"JOB-\"&TEXT(ROW()-4,\"000\"))"]];
applications.getRange("J5:J204").formulasR1C1 = [["=IF(RC[-1]=\"\",\"\",TODAY()-RC[-1])"]];
applications.getRange("K5:K204").formulasR1C1 = [["=IF(RC[-9]=\"\",\"\",IF(COUNTIF('Reference Data'!R4C4:R45C4,RC[-9])>0,\"Yes\",\"No\"))"]];
applications.getRange("L5:L204").formulasR1C1 = [["=IF(RC[-11]=\"\",\"\",IF(OR(RC[-2]<7,RC[-1]=\"Yes\"),\"Hold for review\",\"Auto-apply\"))"]];
applications.getRange("P5:P204").formulasR1C1 = [["=IF(RC[-12]=\"\",\"\",IF(OR(RC[-12]=\"Product Analyst\",RC[-12]=\"Associate Product Manager / APM\"),22,25))"]];
applications.getRange("Q5:Q204").formulasR1C1 = [["=IF(RC[-13]=\"\",\"\",IF(OR(RC[-13]=\"Product Analyst\",RC[-13]=\"Associate Product Manager / APM\"),25,27))"]];
applications.getRange("A4:V204").format.borders = { preset: "inside", style: "thin", color: "#E2E8F0" };
applications.getRange("A4:V4").format.borders = { preset: "outside", style: "thin", color: navy };
applications.getRange("I5:I204").setNumberFormat("yyyy-mm-dd");
applications.getRange("O5:O204").setNumberFormat("yyyy-mm-dd");
applications.getRange("U5:U204").setNumberFormat("yyyy-mm-dd");
applications.getRange("M5:M204").setNumberFormat("0%");
applications.getRange("P5:Q204").setNumberFormat("0.0");
applications.getRange("A:V").format.wrapText = true;
applications.getRange("A:A").format.columnWidth = 12;
applications.getRange("B:B").format.columnWidth = 20;
applications.getRange("C:C").format.columnWidth = 28;
applications.getRange("D:D").format.columnWidth = 26;
applications.getRange("E:E").format.columnWidth = 16;
applications.getRange("F:F").format.columnWidth = 17;
applications.getRange("G:G").format.columnWidth = 18;
applications.getRange("H:H").format.columnWidth = 36;
applications.getRange("I:L").format.columnWidth = 15;
applications.getRange("M:Q").format.columnWidth = 16;
applications.getRange("R:R").format.columnWidth = 26;
applications.getRange("S:T").format.columnWidth = 18;
applications.getRange("U:U").format.columnWidth = 16;
applications.getRange("V:V").format.columnWidth = 38;
applications.freezePanes.freezeRows(4);
applications.getRange("D5:D204").dataValidation = { rule: { type: "list", formula1: "'Reference Data'!$A$4:$A$13" } };
applications.getRange("F5:F204").dataValidation = { rule: { type: "list", values: ["Remote", "Hybrid", "On-site"] } };
applications.getRange("G5:G204").dataValidation = { rule: { type: "list", formula1: "'Reference Data'!$B$4:$B$9" } };
applications.getRange("N5:N204").dataValidation = { rule: { type: "list", formula1: "'Reference Data'!$C$4:$C$12" } };
applications.getRange("T5:T204").dataValidation = { rule: { type: "list", values: ["Not needed", "Researching", "Draft ready", "Sent", "Replied", "Declined"] } };
applications.getRange("L5:L204").conditionalFormats.add("containsText", { text: "Hold for review", format: { fill: "#FEF3C7", font: { color: "#92400E", bold: true } } });
applications.getRange("L5:L204").conditionalFormats.add("containsText", { text: "Auto-apply", format: { fill: "#DCFCE7", font: { color: "#166534", bold: true } } });
applications.getRange("N5:N204").conditionalFormats.add("containsText", { text: "Applied", format: { fill: "#DBEAFE", font: { color: "#1D4ED8", bold: true } } });
applications.getRange("N5:N204").conditionalFormats.add("containsText", { text: "Interview", format: { fill: "#EDE9FE", font: { color: "#6D28D9", bold: true } } });
applications.getRange("N5:N204").conditionalFormats.add("containsText", { text: "Offer", format: { fill: "#DCFCE7", font: { color: "#166534", bold: true } } });
applications.showGridLines = false;

// Rules & answers
title(rules, "A1:F1", "Application Rules & Answer Guidance");
section(rules, "A3:F3", "Routing rules");
rules.getRange("A4:B7").values = [
  ["Matching startup or big-tech role posted more than 7 days ago", "Auto-apply"],
  ["Any role posted within the past 7 days", "Hold for review"],
  ["Any priority-review company", "Hold for review regardless of posting age"],
  ["CAPTCHA, assessment, unusual or unverified factual/legal question", "Stop and request review"],
];
section(rules, "A9:F9", "Compensation answers");
rules.getRange("A10:E12").values = [
  ["Role type", "Current CTC", "Expected CTC", "Variable", "ESOP"],
  ["APM / Product Analyst", "22 LPA fixed", "25 LPA fixed", "0", "0"],
  ["PM, Senior Analyst, Strategy, Product Owner, Product Generalist, or 2-4 year roles", "25 LPA fixed", "27 LPA fixed", "0", "0"],
];
section(rules, "A14:F14", "Tailored-answer guidance");
rules.getRange("A15:B17").values = [
  ["Why join us?", "Connect the company's product, users, growth stage, and role to fintech/edtech experience, experimentation, AI-enabled products, and 0-to-1 work."],
  ["Impactful project - fintech", "Use Navi Account Aggregator, pre-purchase conversion, or payment-funnel optimization. Structure: context, challenge, action, measurable impact, learning."],
  ["Impactful project - edtech / AI / consumer", "Use Voyage Math, AI quiz generation, or Interactive Video adoption. Structure: context, challenge, action, measurable impact, learning."],
];
rules.getRange("A3:F17").format.borders = { preset: "inside", style: "thin", color: "#E2E8F0" };
rules.getRange("A:A").format.columnWidth = 42;
rules.getRange("B:B").format.columnWidth = 88;
rules.getRange("C:F").format.columnWidth = 17;
rules.getRange("A1:F17").format.wrapText = true;
rules.getRange("A10:E10").format = { fill: lightBlue, font: { bold: true, color: navy } };
rules.showGridLines = false;

// Dashboard
title(dashboard, "A1:H1", "Job Search Dashboard");
dashboard.getRange("A2:H2").merge();
dashboard.getRange("A2").values = [["Track opportunities, routing decisions, applications, referrals, and follow-ups in one place."]];
dashboard.getRange("A2:H2").format = { font: { italic: true, color: gray }, fill: "#F8FAFC" };
const kpis = [
  ["Tracked roles", "=COUNTA('Applications'!$B$5:$B$204)"],
  ["Applications sent", "=COUNTIF('Applications'!$N$5:$N$204,\"Applied\")"],
  ["Held for review", "=COUNTIF('Applications'!$L$5:$L$204,\"Hold for review\")"],
  ["Interviews", "=COUNTIF('Applications'!$N$5:$N$204,\"Interview\")"],
  ["Offers", "=COUNTIF('Applications'!$N$5:$N$204,\"Offer\")"],
  ["Referrals sent", "=COUNTIF('Applications'!$T$5:$T$204,\"Sent\")"],
];
for (let i = 0; i < kpis.length; i++) {
  const col = i % 3 === 0 ? "A" : i % 3 === 1 ? "D" : "G";
  const row = i < 3 ? 4 : 8;
  dashboard.getRange(`${col}${row}:${String.fromCharCode(col.charCodeAt(0) + 1)}${row}`).merge();
  dashboard.getRange(`${col}${row}`).values = [[kpis[i][0]]];
  dashboard.getRange(`${col}${row}:${String.fromCharCode(col.charCodeAt(0) + 1)}${row}`).format = { fill: lightBlue, font: { bold: true, color: navy }, horizontalAlignment: "center" };
  dashboard.getRange(`${col}${row + 1}:${String.fromCharCode(col.charCodeAt(0) + 1)}${row + 2}`).merge();
  dashboard.getRange(`${col}${row + 1}`).formulas = [[kpis[i][1]]];
  dashboard.getRange(`${col}${row + 1}:${String.fromCharCode(col.charCodeAt(0) + 1)}${row + 2}`).format = { fill: "#FFFFFF", font: { bold: true, color: blue, size: 20 }, horizontalAlignment: "center", verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: border } };
}
section(dashboard, "A13:H13", "How to use this tracker");
dashboard.getRange("A14:H17").merge();
dashboard.getRange("A14").values = [["1. Add every job to Applications.  2. Enter Company, Role Title, Role Family, posting date, and portal.  3. Routing, priority-company check, and salary figures populate automatically.  4. Update Status and Referral Status after each action.  5. Filter Applications by Routing or Status for your daily review."]];
dashboard.getRange("A14:H17").format = { fill: "#F8FAFC", wrapText: true, verticalAlignment: "top", borders: { preset: "outside", style: "thin", color: border } };
dashboard.getRange("A:H").format.columnWidth = 16;
dashboard.showGridLines = false;

await fs.mkdir(outputDir, { recursive: true });
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);

const check = await workbook.inspect({ kind: "table", range: "Applications!A1:V8", include: "values,formulas", tableMaxRows: 8, tableMaxCols: 22 });
console.log(check.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 50 }, summary: "formula error scan" });
console.log(errors.ndjson);
for (const [sheetName, range] of [
  ["Dashboard", "A1:H17"],
  ["Applications", "A1:V18"],
  ["Rules & Answers", "A1:F17"],
  ["Reference Data", "A1:D45"],
]) {
  const png = await workbook.render({ sheetName, range, scale: 1.3 });
  const name = sheetName.replaceAll(" ", "_").replaceAll("&", "and");
  await fs.writeFile(`${outputDir}/${name}_preview.png`, new Uint8Array(await png.arrayBuffer()));
}
