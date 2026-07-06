# Taiwan Stock AI Valuation Model — Product Requirements Document (PRD)

| Field | Value |
|-------|-------|
| Document version | v1.1 |
| Date | 2026-07-01 (initial) / 2026-07-05 (this update) |
| Product owner | Mickey |
| Status | Live system (in active use, now with a semiconductor-specific scoring layer) |

---

## 0. Summary of Changes Since Last PRD (v1.0 → v1.1)

- **New Phase 0 — Industry Detection:** before any analysis, the system now determines whether a stock belongs to Taiwan's semiconductor supply chain, and further classifies it into one of six sub-industries — wafer foundry, IC design, packaging & testing (OSAT), semiconductor equipment/materials, memory, or other semiconductor — to decide whether the "semiconductor-specific thresholds" should be activated.
- **New semiconductor-specific thresholds in Modules 2, 3, and 5:** Financial Health, Growth, and Capex now use sub-industry-specific scoring standards for semiconductor names (e.g., the "strong" gross-margin threshold is 45% for wafer foundries and IC design, but 22% for OSAT — all different from the general-industry 40% threshold). For asset-light sub-industries such as IC design and equipment/materials, Module 5 replaces the traditional Capex-to-depreciation logic with an R&D-expense-ratio logic.
- **New "Historical Valuation Price Reference Range" in Module 4:** converts the P/E river chart's low/fair/high bands into corresponding price bands for disclosure purposes (unscored), with three usage constraints: it must never use action-oriented language like "entry point"; if the P/E historical sample spans less than 3 years it must be flagged as having reduced reference value; and cyclical stocks must be flagged as having lower applicability for the P/E-band method. Under semiconductor mode, peer P/E comparisons are also restricted to the same sub-industry to avoid distortion from cross-sub-industry comparisons.
- **New semiconductor supplementary rules in Module 6:** the yield-rate trend and capacity-utilization direction bonus items now apply only to sub-industries that own actual production capacity (wafer foundry / OSAT / memory) — IC design (fabless) and most equipment/materials companies are excluded. Geopolitical risk assessment under semiconductor mode must now cite specific criteria — whether the company is on the U.S. Entity List, its exposure to U.S. semiconductor export controls on China, its advanced-node or advanced-packaging revenue share, and its China revenue share — rather than a generic judgment.
- **Verification checklist expanded from 7 to 8 items:** a new item 8, "Valuation Price Band Conversion Consistency," confirms the EPS basis used in Module 4's historical valuation price reference range matches the EPS basis used for the P/E determination in the same module, and that no action-oriented language was used.
- **New "📌 Conclusion (Key Points First)" block at the top of the report:** placed before all other content, it immediately shows the composite score (e.g., "71/100 🟢 Worth active attention") and the 200-character investment commentary, so readers can grasp the conclusion without scrolling.
- **Project structure changes:** added `example_reports/2330_report_example.md` (a sample report) and `manual_data/2330_manual.example.md` (a sample filled-in data file) for new users to reference; the project now has Git version control set up (`.gitignore`, an initial commit dated around 2026-07-03).

The rest of this document has been updated to reflect the current `INSTRUCTIONS.md` / `README.md` and the system's actual behavior.

---

## 1. Purpose of This Document

This document describes the product requirements for the "Taiwan Stock AI Valuation Model," covering its goals, usage workflow, functional specification, and scoring logic. The system currently runs as a Claude Cowork Project: the user manually collects a small set of key financial figures, and the AI handles web-search enrichment, industry detection, applies either general or semiconductor-specific scoring rules, and produces a structured investment valuation report. This document serves as a complete record of the system's current state and as a planning baseline for future expansion.

## 2. Background and Problem Statement

Retail investors evaluating individual Taiwan-listed stocks typically run into three problems. First, the financial data they need is scattered across multiple sites — StatementDog, Wantgoo, the Market Observation Post System (MOPS) — making collection time-consuming. Second, valuation logic varies from person to person and is easily swayed by sentiment or news flow, lacking a consistent quantitative standard — and semiconductor sub-industries (wafer foundry, IC design, OSAT, etc.) have fundamentally different "normal" financial profiles, so a single fixed threshold across all of them distorts the picture. Third, the resulting notes usually have no standard format, making it hard to track a stock over time, compare it against others, or later check whether a past judgment was correct.

The core value of this product is exchanging a small amount of manual input (5 required key data points plus a handful of optional fields) for an investment valuation report with auditable sourcing, fixed scoring logic that can flex by sub-industry, and repeatable verification — while running 8 automated quality checks before every save to reduce the risk of AI hallucination or calculation errors reaching the final report.

## 3. Goals and Non-Goals

**Goals:**
- Compress the manual work required per stock analysis to 5–10 minutes (filling in only the 5 required key data points).
- Use a fixed 7-module scoring framework, with dedicated thresholds for semiconductor sub-industries, so analyses across different stocks and time periods remain comparable.
- Tag every number with its source (manual input / web search / AI estimate) so the report can be manually audited.
- Run 8 automated verification checks before saving, catching common errors (mismatched reporting periods, incorrect dividend-yield math, wrong YoY base month, inconsistent valuation-price-band conversion, etc.).
- Lead every report with a "conclusion first" block showing the composite score and commentary, lowering the barrier to a quick read.
- Provide multiple output formats (Markdown report, standard HTML, beginner-friendly HTML) to serve different reading contexts.

**Non-Goals:**
- No real-time price feeds or intraday automated monitoring.
- No quantitative trading signals or automated order placement; the report explicitly forbids action-oriented language like "entry point."
- Not a substitute for professional investment advice; every report explicitly states it is for learning purposes only.
- Does not cover valuation logic for non-Taiwan markets (e.g., U.S. equities, crypto).

## 4. Target Users

The primary user is an individual investor doing self-directed research on Taiwan-listed stocks, with basic familiarity with financial terminology (gross margin, ROE, P/E, etc.), willing to spend 5–10 minutes looking up key figures, and with a specific interest in Taiwan's semiconductor supply chain (wafer foundry, IC design, OSAT, etc.). The user wants the repetitive work of "look up data → apply formulas → write it up" handed off to AI. A secondary use case is producing a plain-language version of the report for readers unfamiliar with financial metrics (corresponding to the existing "beginner" HTML output), which explains terms like yield rate and capacity utilization in everyday language and why they matter.

## 5. User Workflow

The system splits work between manual data entry and AI automation, in five steps.

Step 1: the user copies `manual_data/_TEMPLATE.md` and renames it to `{ticker}_manual.md` (they may reference the sample `manual_data/2330_manual.example.md`). Step 2: the user cross-references three data sources — StatementDog (`statementdog.com/analysis/{ticker}`, for EPS, gross margin, P/E river chart), Wantgoo (`wantgoo.com/stock/{ticker}`, for ROE, debt ratio, monthly revenue), and the Market Observation Post System (`mops.twse.com.tw`, for the cash flow statement's Capex and OCF) — to fill in 5 required key data points: EPS and its 3-year CAGR; five profitability metrics (gross margin / operating margin / net margin / ROE / debt ratio) plus FCF; valuation data (current P/E and the three historical P/E bands); Capex and depreciation; and the last 6 months of monthly revenue. Optional fields include foreign/investment-trust flows, earnings-call guidance, share buybacks, geopolitical risk, and — for manufacturing/semiconductor names — yield-rate and capacity-utilization trends. Step 3: save the file. Step 4: type "分析 {ticker}" (Analyze {ticker}) in the Cowork chat box. Step 5: within about one minute, the AI completes industry detection, reading, searching, scoring, report generation (including the new conclusion block), and verification, displaying the full report in the chat window for the user's review before it is saved; the user can also ask Cowork, via chat, to produce a polished HTML report.

## 6. Functional Requirements

### 7.0 Phase 0 — Industry Detection (New)

Before reading the manual data, the system first determines whether the stock belongs to Taiwan's semiconductor technology sector. The determination order is: if `manual_data/{ticker}_manual.md` has already manually tagged an industry, that takes priority; if not tagged, the Phase 2 web search adds the keywords "{ticker} {company name} 產業別 半導體 IC設計 晶圓代工 封測" (industry classification, semiconductor, IC design, wafer foundry, packaging & testing); the system then classifies the company, based on its primary revenue source, into one of six sub-industries: wafer foundry, IC design, OSAT (packaging & testing), semiconductor equipment/materials, memory, or other semiconductor.

If the stock is determined to fall into one of these sub-industries, the system activates the "semiconductor-specific thresholds" — Modules 2, 3, and 5 switch to sub-industry-specific scoring standards, while Modules 4 and 6 keep their original table structure but apply supplementary rules. If the stock does not belong to any of these (including other general Taiwan industries or non-Taiwan companies), the original "general thresholds" apply. The determination and its basis must be written into the report's "Data Source Notes" section (e.g., "Industry detection: Wafer Foundry (semiconductor-specific standards activated)"). If classified as "other semiconductor," the conservative OSAT-level thresholds are applied with an added note.

### 7.1 Phase 1 — Read Manual Data

The system reads the corresponding `manual_data/{ticker}_manual.md` and checks whether the 5 required key data points are complete. If any field is blank, it must list the missing items and ask the user whether to proceed anyway.

### 7.2 Phase 2 — Web Search Enrichment

Using Traditional Chinese search terms plus the stock ticker, the system runs 5 categories of search: latest quarterly gross margin / EPS / revenue; 2026 monthly revenue YoY growth; foreign institutional and investment-trust buy/sell flows; earnings-call outlook; and Capex / capacity-expansion plans (semiconductor names add the industry-classification keywords from Phase 0). Search results fill in information the manual form doesn't cover — Module 1 (company basics, revenue structure, sub-industry classification) and Module 6 (institutional flows, earnings-call tone, geopolitical risk).

### 7.3 Phase 3 — Seven-Module Scoring Logic

**Module 1 / Company Basics (unscored):** company name, market, industry, position in the supply chain, business description; semiconductor names must additionally fill in a sub-industry classification (wafer foundry / IC design / OSAT / equipment-materials / memory / other semiconductor / not applicable). An optional revenue breakdown by business line notes the primary growth driver; if the company doesn't disclose segment data, it is flagged "🤖 Insufficient disclosure."

**Module 2 / Financial Health (25 pts, general thresholds):** gross margin, operating margin, net margin, ROE, and debt ratio are each scored on a three-tier scale (Strong / Fair / Weak = 5 / 3 / 1 pts), with a cash-flow-quality adjustment: +5 if FCF is positive and close to net income, −3 if FCF is negative.

| Metric | Strong (5 pts) | Fair (3 pts) | Weak (1 pt) |
|--------|-----------------|--------------|-------------|
| Gross margin | >40% | 20–40% | <20% |
| Operating margin | >20% | 10–20% | <10% |
| Net margin | >15% | 5–15% | <5% |
| ROE | >20% | 10–20% | <10% |
| Debt ratio | <30% | 30–50% | >50% |

**Semiconductor-specific thresholds (if activated by Phase 0):** gross margin, operating margin, ROE, and debt ratio switch to sub-industry-specific thresholds. For example, wafer foundries use a 45% "strong" gross-margin threshold (vs. 40% general) and a relaxed 45% "strong" debt-ratio threshold (capital-intensive businesses can carry more leverage); IC design also uses 45% for gross margin but a tighter 25% debt-ratio threshold (asset-light businesses should be held to a stricter standard); OSAT uses a lower 22% "strong" gross-margin threshold (structurally lower margins in that sub-industry). Net margin keeps the general threshold. For equipment/materials and memory, which lack sufficient statistical basis for absolute thresholds, the system recommends judging Strong/Fair/Weak based on the company's own 5-year historical range rather than fixed percentages.

**Module 3 / Growth (20 pts):** Revenue YoY (6 pts), 3-year EPS CAGR (6 pts), monthly revenue trend (4 pts), and earnings-call outlook (4 pts). The general thresholds mark >15% revenue YoY and >15% EPS CAGR as "Strong"; the semiconductor-specific thresholds raise these to >25% revenue YoY and >20% EPS CAGR, since recent growth in the sector (especially AI-related) is running off an already-high base and the general thresholds lack discriminating power. Monthly revenue trend and earnings-call outlook thresholds do not vary by industry.

**Module 4 / Valuation (20 pts):** scored by where the current P/E sits on the historical river chart (low band = 18 pts, fair band = 12 pts, high band = 6 pts), +2 pts for trading at a discount to peers (0 for a premium), and +2 pts if fair-value upside exceeds 15%. Under semiconductor mode, peer P/E comparisons must be restricted to the same sub-industry (e.g., a wafer foundry can only be compared to other wafer foundries, not to OSAT names).

Module 4 also adds a new, unscored "Historical Valuation Price Reference Range" for disclosure purposes: the historical P/E low value, the fair-band edges, and the high value are each multiplied by EPS to derive corresponding price bands, presented as e.g. "Historical valuation price reference: below $XX (low) / $XX–$XX (fair) / above $XX (high) (based on the past N years' P/E range)." This field carries three constraints: the EPS basis must match the EPS used for the P/E determination in the same module and be explicitly labeled (TTM and estimated EPS cannot be mixed); the wording must be limited to "historical valuation price reference range" — action-oriented terms like "entry point" or "recommended buy point" are prohibited; and if the historical P/E sample spans less than 3 years, it must be flagged as having "a short sample period, reducing reference value," with cyclical stocks (e.g., memory) additionally flagged as having lower applicability for the P/E-band method.

**Module 5 / Capex (15 pts):** Capex-to-depreciation ratio (4 pts), Capex YoY change (4 pts), post-Capex FCF margin (4 pts), and consistency between Capex direction and earnings-call guidance (3 pts). Formulas: Capex/depreciation ratio = TTM Capex ÷ TTM depreciation; FCF margin = (operating cash flow − Capex) ÷ revenue. This is the default logic for asset-heavy sub-industries such as wafer foundry, OSAT, and memory.

**Semiconductor-specific logic switch:** for asset-light (typically fabless) sub-industries such as IC design and equipment/materials, the first two items in Module 5 are replaced with an R&D-expense-ratio logic: R&D expense ratio (R&D ÷ revenue) >15% and growing YoY is "Strong" (4 pts); R&D expense YoY change >15% is "Strong" (4 pts). The FCF margin and Capex/guidance-consistency items keep their original logic.

**Module 6 / Taiwan-Specific Indicators (20 pts general, up to 24 pts for manufacturing):** monthly revenue momentum (4 pts), foreign institutional flows (4 pts), investment-trust flows (3 pts), earnings-call tone (4 pts), share buybacks (2 pts), geopolitical risk (3 pts); manufacturing / semiconductor / OSAT names additionally score yield-rate trend (+2 pts) and capacity-utilization direction (+2 pts). These two bonus items now apply only to sub-industries that own actual production capacity (wafer foundry / OSAT / memory); IC design (fabless) and most equipment/materials companies do not qualify, and the denominator stays at 20 pts for them. Under semiconductor mode, geopolitical risk must be assessed against specific criteria — whether the company is on the U.S. Entity List, whether it is directly affected by U.S. semiconductor export controls on China, its advanced-node or advanced-packaging revenue share, and its China revenue share — scored Low (3 pts) / Medium (2 pts) / High (1 pt) exposure with the basis stated in the report, rather than a generic judgment call.

**Module 7 / Composite Score:** for general industries, the maximum is 100 pts — 🟢 Worth active attention at 70+, 🟡 Keep monitoring at 50–69, 🔴 Avoid for now below 50. For manufacturing/semiconductor names where the yield-rate and capacity-utilization bonus items apply, the maximum is 104 pts, with thresholds of 73+ / 52–72 / below 52. If a semiconductor name doesn't qualify for those bonus items (e.g., a fabless IC design company), it still uses the 100-pt scale and general thresholds.

### 7.4 Phase 4 — Report Generation

The report draft follows a fixed template, now with a new **"📌 Conclusion (Key Points First)" block at the very top**, showing the composite score (e.g., "71/100 🟢 Worth active attention") and the 200-character investment commentary up front, so the reader gets the bottom line without scrolling. It's followed by the full template: a data-source summary (now including a "🔬 Industry Detection" line stating the sub-industry classification and whether semiconductor-specific standards were activated), the full content of Modules 1 through 7, the (repeated) investment commentary, the verification checklist, and a disclaimer. Every number must carry a source tag — none may be omitted. For manufacturing/semiconductor names, Module 6 must include fixed explanatory text on why yield rate and capacity utilization matter. The draft must be displayed in full in the chat window — unsaved — for user confirmation before it is written to disk.

### 7.5 Phase 4.5 — Pre-Save Verification Checklist (Expanded from 7 to 8 Items)

Before saving, the system must check 8 verification rules one by one and append the results to the end of the report: financial-period consistency, price timeliness, EPS basis disclosed, dividend yield calculated correctly, monthly revenue YoY base period correct, AI-estimated fields justified, score totals consistent, and the new **item 8, "Valuation Price Band Conversion Consistency"** — confirming that the EPS basis used in Module 4's historical valuation price reference range matches the EPS basis used for that module's P/E determination, and that no action-oriented language (like "entry point") was used. Each item is marked ✅ Pass or ⚠️ Needs review with a stated reason; if any item is ⚠️, the report can still be saved but the user must be reminded to manually review it. Once all items pass, the report is saved to `reports/{ticker}_report_{date}.md`.

## 7. Report Output Specification

The system currently supports several output formats: the raw Markdown report (stored in `reports/`, the source of truth for all downstream formats, now including the conclusion block and the 8-item checklist); a standard HTML report; and a beginner-friendly HTML report (with additional plain-language explanations). The monthly revenue trend is rendered as a text-based ASCII chart, and both the P/E river-chart position and the historical valuation price reference range are indicated in text. Every report ends with a "recommended next update date," aligned to the next quarterly earnings release.

## 8. Folder and File Structure

```
台股評價模型/
├── README.md              Quick-start guide for the user
├── INSTRUCTIONS.md         Cowork Project instructions (the AI's analysis logic, incl. semiconductor layer)
├── .gitignore              Git configuration (new)
├── manual_data/
│   ├── _TEMPLATE.md              Manual data-entry template
│   ├── 2330_manual.md    Sample filled-in data (new, for reference)
│   └── {ticker}_manual.md        Filled-in data per stock
├── example_reports/
│   └── 2330_report_20260702.md    Sample report (new, but in the old format — Module 5 is still
│                                  "Dividend," inconsistent with the current logic)
├── reports/
    ├── {ticker}_report_{date}.md              Raw report
    ├── {ticker}_report_{date}.html            Standard HTML version
    └── {ticker}_report_{date}_beginner.html   Beginner-friendly HTML version

```

The project now has Git version control set up, with an initial commit message of "Initial commit - 台股AI評價模型 v1.0" dated around 2026-07-03.

## 9. Non-Functional Requirements

Every number must carry a source tag — this cannot be omitted. Where web search cannot find a figure, it must be marked "🤖 AI estimate" with the basis stated — it cannot be left blank or silently assumed. The system must keep the reporting period, price timeliness, EPS basis, and valuation-price-band conversion internally consistent within a single report, avoiding the mixing of figures from different quarters, different bases, or different EPS conventions. Module 4's historical valuation price reference range must never use action-oriented language such as "entry point" or "recommended buy point." Every report must carry the disclaimer: "This report is for learning purposes only and does not constitute investment advice."

## 10. Acceptance Criteria / Success Metrics

A valid report must simultaneously satisfy: Phase 0 industry detection is completed and its basis disclosed in the report; all 5 required data points are present, or any gaps explicitly flagged and confirmed with the user; all 7 module scores are justified and sum correctly (semiconductor names must apply the correct sub-industry thresholds); all 8 verification checklist items are executed and their results disclosed; the conclusion block at the top matches the Module 7 total; and the draft is produced within about one minute for user confirmation. Over the longer term, the user should be able to use the accumulated history of reports to compare a given stock's score over time, or compare the relative attractiveness of different stocks — including semiconductor names within the same sub-industry — side by side.

## 11. Risks and Limitations

The timeliness and accuracy of web-search results depend on what public information is available at the moment of the query, and may lag actual financial filings. Fields marked "🤖 AI estimate" are, by nature, model inference rather than official data, and the user must judge how much weight to give them. Although the semiconductor-specific thresholds are now broken out by sub-industry, equipment/materials and memory still lack sufficient statistical basis for absolute thresholds and rely on relative historical positioning, which is more subjective. Module 4's historical valuation price reference range has markedly lower reference value when the P/E sample spans less than 3 years or the stock is cyclical. The report does not constitute investment advice; the risk of any final decision rests with the user.

## 12. Potential Future Extensions

Possible directions include: integrating brokerage or financial-data APIs to auto-populate the required data points; building a dashboard for side-by-side comparison across multiple stocks (grouped by sub-industry for semiconductor names); charting a given stock's historical reports to visualize how its score has changed over time; and extending the sub-industry-threshold approach used for semiconductors to other sectors (e.g., biotech, financials). These are potential directions, not committed roadmap items for the current system.

---

*This document was compiled from the current `README.md`, `INSTRUCTIONS.md`, `manual_data/_TEMPLATE.md`, recently generated reports (2330 / 3037 / 3661), and the report-generator scripts, and reflects the system's actual operation as of 2026-07-05.*
