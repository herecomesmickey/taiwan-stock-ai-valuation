# Taiwan Stock AI Valuation Model — Product Requirements Document (PRD)

| Field | Value |
|-------|-------|
| Document version | v1.0 |
| Date | 2026-07-01 |
| Product owner | Mickey |
| Status | Live system (in active use) |

---

## 1. Purpose of This Document

This document describes the product requirements for the "Taiwan Stock AI Valuation Model," covering its goals, usage workflow, functional specification, and scoring logic. The system currently runs as a Claude Cowork Project: the user manually collects a small set of key financial figures, and the AI handles web-search enrichment, applies a fixed scoring framework, and produces a structured investment valuation report. This document serves as a complete record of the system's current state and as a planning baseline for future expansion (e.g., automated data ingestion, multi-stock comparison, scheduled refreshes).

## 2. Background and Problem Statement

Retail investors evaluating individual Taiwan-listed stocks typically run into three problems. First, the financial data they need is scattered across multiple sites — the Market Observation Post System (MOPS), StatementDog, Goodinfo — making collection time-consuming. Second, valuation logic varies from person to person and is easily swayed by sentiment or news flow, lacking a consistent quantitative standard. Third, the resulting notes usually have no standard format, making it hard to track a stock over time, compare it against others, or later check whether a past judgment was correct.

The core value of this product is exchanging a small amount of manual input (5 required key data points plus a handful of optional fields) for an investment valuation report with auditable sourcing, fixed scoring logic, and repeatable verification — while running 7 automated quality checks before every save to reduce the risk of AI hallucination or calculation errors reaching the final report.

## 3. Goals and Non-Goals

**Goals:**
- Compress the manual work required per stock analysis to under 5 minutes (filling in only the 5 required key data points).
- Use a fixed 7-module scoring framework so that analyses across different stocks and different points in time remain comparable.
- Tag every number with its source (manual input / web search / AI estimate) so the report can be manually audited.
- Run 7 automated verification checks before saving, catching common errors (mismatched reporting periods, incorrect dividend-yield math, wrong YoY base month, etc.).
- Provide multiple output formats (Markdown report, standard HTML, beginner-friendly HTML) to serve different reading contexts.

**Non-Goals:**
- No real-time price feeds or intraday automated monitoring.
- No quantitative trading signals or automated order placement.
- Not a substitute for professional investment advice; every report explicitly states it is for learning purposes only.
- Does not cover valuation logic for non-Taiwan markets (e.g., U.S. equities, crypto).

## 4. Target Users

The primary user is an individual investor doing self-directed research on Taiwan-listed stocks (the system's current actual user), with basic familiarity with financial terminology (gross margin, ROE, P/E, etc.) and willingness to spend 5 minutes looking up key figures — but who wants the repetitive work of "look up data → apply formulas → write it up" handed off to AI. A secondary use case is producing a plain-language version of the report for readers unfamiliar with financial metrics (corresponding to the existing "beginner" HTML output), which explains terms like yield rate and capacity utilization in everyday language and why they matter.

## 5. Definitions

TTM means Trailing Twelve Months; YoY means year-over-year growth; FCF means Free Cash Flow; Capex means Capital Expenditure; a "P/E river chart" (本益比河流圖) plots a stock's price against its historical P/E band to indicate whether the current valuation sits in a low, fair, or high range.

## 6. User Workflow

The system splits work between manual data entry and AI automation, in five steps.

Step 1: the user copies `manual_data/_TEMPLATE.md` and renames it to `{ticker}_manual.md`. Step 2: the user cross-references two data sources — the Market Observation Post System (balance sheet, cash flow statement, monthly revenue, insider/board shareholding) and StatementDog (P/E river chart) — to fill in 5 required key data points: EPS and its 3-year CAGR; five profitability metrics (gross margin / operating margin / net margin / ROE / debt ratio) plus FCF; valuation data (current P/E and the three historical P/E bands); Capex and depreciation; and the last 6 months of monthly revenue. Optional fields include foreign/investment-trust flows, earnings-call guidance, share buybacks, geopolitical risk, and — for manufacturing names — yield-rate and capacity-utilization trends. Step 3: save the file. Step 4: type "分析 {ticker}" (Analyze {ticker}) in the Cowork chat box. Step 5: within about one minute, the AI completes reading, searching, scoring, report generation, and verification, displaying the full report in the chat window for the user's review before it is saved.

## 7. Functional Requirements

### 7.1 Phase 1 — Read Manual Data

The system reads the corresponding `manual_data/{ticker}_manual.md` and checks whether the 5 required key data points are complete. If any field is blank, it must list the missing items and ask the user whether to proceed anyway (partial data is allowed, but must be flagged explicitly).

### 7.2 Phase 2 — Web Search Enrichment

Using Traditional Chinese search terms plus the stock ticker, the system runs 5 categories of search: latest quarterly gross margin / EPS / revenue; 2026 monthly revenue YoY growth; foreign institutional and investment-trust buy/sell flows; earnings-call outlook; and Capex / capacity-expansion plans. Search results fill in information the manual form doesn't cover — Module 1 (company basics, revenue structure) and Module 6 (institutional flows, earnings-call tone, geopolitical risk).

### 7.3 Phase 3 — Seven-Module Scoring Logic

**Module 1 / Company Basics (unscored):** company name, market, industry, position in the supply chain, business description, and an optional revenue breakdown by business line, noting the primary growth driver. If the company doesn't disclose segment data, it is flagged "🤖 Insufficient disclosure."

**Module 2 / Financial Health (25 pts):** gross margin, operating margin, net margin, ROE, and debt ratio are each scored on a three-tier scale (Strong / Fair / Weak = 5 / 3 / 1 pts), with a cash-flow-quality adjustment: +5 if FCF is positive and close to net income, −3 if FCF is negative. Thresholds below.

| Metric | Strong (5 pts) | Fair (3 pts) | Weak (1 pt) |
|--------|-----------------|--------------|-------------|
| Gross margin | >40% | 20–40% | <20% |
| Operating margin | >20% | 10–20% | <10% |
| Net margin | >15% | 5–15% | <5% |
| ROE | >20% | 10–20% | <10% |
| Debt ratio | <30% | 30–50% | >50% |

**Module 3 / Growth (20 pts):** Revenue YoY (6 pts), 3-year EPS CAGR (6 pts), monthly revenue trend (4 pts), and earnings-call outlook (4 pts), each scored against Strong/Fair/Weak thresholds.

**Module 4 / Valuation (20 pts):** scored by where the current P/E sits on the historical river chart (low band = 18 pts, fair band = 12 pts, high band = 6 pts), +2 pts for trading at a discount to peers (0 for a premium), and +2 pts if fair-value upside exceeds 15%.

**Module 5 / Capex (15 pts):** Capex-to-depreciation ratio (4 pts), Capex YoY change (4 pts), post-Capex FCF margin (4 pts), and consistency between Capex direction and earnings-call guidance (3 pts). Formulas: Capex/depreciation ratio = TTM Capex ÷ TTM depreciation; FCF margin = (operating cash flow − Capex) ÷ revenue.

**Module 6 / Taiwan-Specific Indicators (20 pts general, up to 24 pts for manufacturing):** monthly revenue momentum (4 pts), foreign institutional flows (4 pts), investment-trust flows (3 pts), earnings-call tone (4 pts), share buybacks (2 pts), geopolitical risk (3 pts); manufacturing / semiconductor / packaging-and-testing names additionally score yield-rate trend (+2 pts) and capacity-utilization direction (+2 pts). These two items are manufacturing-specific bonus criteria — if not applicable, the denominator stays at 20 pts; if applicable, it becomes 24 pts, and the overall pass thresholds scale up proportionally.

**Module 7 / Composite Score:** for general industries, the maximum is 100 pts — 🟢 Worth active attention at 70+, 🟡 Keep monitoring at 50–69, 🔴 Avoid for now below 50. For manufacturing/semiconductor names, the maximum is 104 pts, with thresholds of 73+ / 52–72 / below 52 respectively.

### 7.4 Phase 4 — Report Generation

The report draft follows a fixed template: a data-source summary (three lists — manual input / web search / AI estimate), the full content of Modules 1 through 7, a 200-character (Chinese) investment commentary, the verification checklist, and a disclaimer. Every number must carry a source tag — none may be omitted. For manufacturing/semiconductor names, Module 6 must include fixed explanatory text on why yield rate and capacity utilization matter. The draft must be displayed in full in the chat window — unsaved — for user confirmation before it is written to disk.

### 7.5 Phase 4.5 — Pre-Save Verification Checklist

Before saving, the system must check 7 verification rules one by one and append the results to the end of the report: financial-period consistency (Module 2 and 3 figures must come from the same reporting period); price timeliness (the price used in Module 4 must be the closing price as of the analysis date or the prior trading day); EPS basis disclosed (TTM, FY, or estimated EPS must be explicitly labeled); dividend yield calculated correctly (cash dividend ÷ current price, not the pre-ex-dividend price); monthly revenue YoY base period correct (compared to the same month last year, not the prior month); AI-estimated fields justified (every field flagged "🤖 AI estimate" must include the basis for the estimate); and score totals consistent (each module's score must sum to the Module 7 total). Each item is marked ✅ Pass or ⚠️ Needs review with a stated reason; if any item is ⚠️, the report can still be saved but the user must be reminded to manually review it. Once all items pass, the report is saved to `reports/{ticker}_report_{date}.md`.

## 8. Report Output Specification

The system currently supports several output formats: the raw Markdown report (stored in `reports/`, the source of truth for all downstream formats); a standard HTML report (produced by `generate_pdf_report.py`, parsed from the Markdown and rendered with module scores, metric detail, and monthly revenue trends); and a beginner-friendly HTML report (produced by `generate_pdf_report_beginner.py`, adding plain-language explanations to lower the barrier for readers unfamiliar with financial terms). The monthly revenue trend is rendered as a text-based ASCII chart, and the P/E river-chart position is indicated in text (low / fair / high band). Every report ends with a "recommended next update date," aligned to the next quarterly earnings release.

## 9. Folder and File Structure

```
台股評價模型/
├── README.md              Quick-start guide for the user
├── INSTRUCTIONS.md         Cowork Project instructions (the AI's analysis logic)
├── manual_data/
│   ├── _TEMPLATE.md        Manual data-entry template
│   └── {ticker}_manual.md  Filled-in data per stock
├── reports/
│   ├── {ticker}_report_{date}.md              Raw report
│   ├── {ticker}_report_{date}.html            Standard HTML version
│   └── {ticker}_report_{date}_beginner.html   Beginner-friendly HTML version
├── generate_pdf_report.py           Standard report generator
└── generate_pdf_report_beginner.py  Beginner-friendly report generator
```

## 10. Non-Functional Requirements

Every number must carry a source tag — this cannot be omitted. Where web search cannot find a figure, it must be marked "🤖 AI estimate" with the basis for the estimate stated — it cannot be left blank or silently assumed. The system must keep the reporting period, price timeliness, and EPS basis internally consistent within a single report, avoiding the mixing of figures from different quarters or different bases. Every report must carry the disclaimer: "This report is for learning purposes only and does not constitute investment advice."

## 11. Acceptance Criteria / Success Metrics

A valid report must simultaneously satisfy: all 5 required data points present, or any gaps explicitly flagged and confirmed with the user; all 7 module scores are justified and sum correctly; all 7 verification checklist items are executed and their results disclosed; and the draft is produced within about one minute for user confirmation. Over the longer term, the user should be able to use the accumulated history of reports to compare a given stock's score over time, or compare the relative attractiveness of different stocks side by side.

## 12. Risks and Limitations

The timeliness and accuracy of web-search results depend on what public information is available at the moment of the query, and may lag actual financial filings. Fields marked "🤖 AI estimate" are, by nature, model inference rather than official data, and the user must judge how much weight to give them. The scoring rules use fixed thresholds and cannot fully capture industry-specific nuance (for example, cyclical stocks and growth stocks warrant fundamentally different valuation logic). The report does not constitute investment advice; the risk of any final decision rests with the user.

## 13. Potential Future Extensions

Possible directions include: integrating brokerage or financial-data APIs to auto-populate the required data points and reduce manual lookup; building a dashboard for side-by-side comparison across multiple stocks; charting a given stock's historical reports to visualize how its score has changed over time; and adding industry-specific scoring modules (e.g., biotech, financials). These are potential directions, not committed roadmap items for the current system.

---

*This document was compiled from the current `README.md`, `INSTRUCTIONS.md`, `manual_data/_TEMPLATE.md`, and the report-generator scripts, and reflects the system's actual operation as of 2026-07-01.*
