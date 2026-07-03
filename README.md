# 台股 AI 投資評價模型

> 用 Claude AI 自動分析台灣上市股票，7 模組評分，5 分鐘產出完整評價報告。

---

## ⚠️ 使用前提

本專案**不是獨立程式**，需要搭配 **Claude Desktop（Cowork 模式）** 才能運作。

Claude Desktop 是 Anthropic 提供的免費桌面應用程式，Cowork 模式是其中的 AI 協作功能。  
→ 下載 Claude Desktop：[claude.ai/download](https://claude.ai/download)

---

## 這個專案能做什麼

1. 你填入約 5 項財務數字（本益比、EPS、月營收等）
2. Claude AI 自動搜尋網路補充其他資訊
3. 套用 7 模組評分邏輯，產出一份完整的投資評價報告（Markdown 格式）

**支援功能：**
- 7 模組量化評分（財務健康／成長性／估值／資本支出／台灣特殊指標等）
- 每個數字標記來源（手動輸入／網路搜尋／AI 估算）
- 製造業 / 半導體特殊指標（良率、產能利用率）
- 驗證清單（自動檢查資料一致性）
- 一鍵產出 PDF / HTML 美化報告（需 Python）

---

## 資料夾結構

```
台股評價模型/
│
├── README.md                        ← 你現在看的這份（快速上手）
├── INSTRUCTIONS.md                  ← Claude AI 的分析大腦（貼進 Cowork Project 指示欄）
│
├── manual_data/
│   ├── _TEMPLATE.md                 ← 每次分析前複製這個，填入數字
│   └── 2330_manual.example.md      ← 填寫完成的示範（台積電，數字為示意值）
│
├── example_reports/
│   └── 2330_report_example.md      ← AI 產出的報告示範（台積電）
│
├── generate_pdf_report.py           ← 將 .md 報告轉成美化 HTML（一般版）
└── generate_pdf_report_beginner.py  ← 同上，但加入新手友善說明
```

---

## 快速上手（初次設定）

### Step 1｜安裝 Claude Desktop

下載並安裝：[claude.ai/download](https://claude.ai/download)  
登入你的 Claude 帳號（免費方案即可使用 Cowork）。

### Step 2｜下載本專案

點右上角 **Code → Download ZIP**，解壓縮到你喜歡的位置。  
或使用 Git：
```bash
git clone https://github.com/你的帳號/台股評價模型.git
```

### Step 3｜建立 Cowork Project

1. 打開 Claude Desktop，點左上角「**Cowork**」分頁
2. 點「**+ 新增 Project**」，命名為「台股評價模型」
3. 點「**選擇資料夾**」，選取你剛下載的 `台股評價模型/` 資料夾
4. 點「**Project 指示**」，將 `INSTRUCTIONS.md` 的**全部內容貼入**
5. 儲存 → 設定完成 ✅

> 這個設定只需要做一次，之後每次打開 Project 就能直接分析。

---

## 每次使用流程（約 5～10 分鐘）

### Step 1｜複製資料表

把 `manual_data/_TEMPLATE.md` 複製一份，重新命名：

```
2330_manual.md   ← 台積電
2454_manual.md   ← 聯發科
6488_manual.md   ← 環球晶
```

### Step 2｜填入 5 項關鍵數據

同時開啟以下網頁查詢：

| 網頁 | 網址 | 取得資料 |
|------|------|---------|
| 財報狗 | `statementdog.com/analysis/{代號}` | EPS、毛利率、本益比河流圖 |
| 玩股網 | `wantgoo.com/stock/{代號}` | ROE、負債比率、月營收 |
| 公開資訊觀測站 | `mops.twse.com.tw` | 現金流量表（Capex、OCF） |

填完 5 個區塊（EPS / 獲利能力 / 估值 / Capex / 月營收），儲存檔案。

### Step 3｜讓 AI 分析

在 Cowork 對話框輸入：

```
分析 2330
```

AI 會自動：
1. 讀取你填好的 `2330_manual.md`
2. 搜尋網路補充資料（法說會、外資籌碼等）
3. 套用 7 模組評分
4. 產出報告並存進 `reports/` 資料夾

### Step 4｜（選用）產出美化報告

```bash
python3 generate_pdf_report.py reports/2330_report_20260629.md
```

會在 `reports/` 產出對應的 `.html` 美化報告，用瀏覽器開啟即可列印或存成 PDF。

---

## 7 模組評分說明

| 模組 | 滿分 | 評估內容 |
|------|------|---------|
| 模組 1 | 不計分 | 基本資料（公司、產業、業務描述） |
| 模組 2 | 25 分 | 財務健康（毛利率、ROE、負債比率、FCF） |
| 模組 3 | 20 分 | 成長性（營收 YoY、EPS CAGR、月營收趨勢） |
| 模組 4 | 20 分 | 估值（P/E 河流圖位置、合理股價空間） |
| 模組 5 | 15 分 | 資本支出 Capex（擴張力道、FCF margin） |
| 模組 6 | 20 分 | 台灣特殊指標（外資籌碼、法說態度、地緣風險） |
| 模組 7 | — | 綜合評分與投資評語 |

**評分結果：**
- 🟢 70 分以上：值得積極關注
- 🟡 50～69 分：持續觀察追蹤
- 🔴 50 分以下：暫時迴避

> 製造業 / 半導體類股加計良率與產能利用率，滿分為 104 分，門檻等比例調整。

---

## 範例報告

`example_reports/2330_report_example.md` 是台積電的完整分析報告範例，可以在開始前先參考報告格式與內容深度。

---

## 常見問題

**Q：要付費才能用 Claude？**  
A：Claude 有免費方案，Cowork 功能包含在內。付費方案可使用更多訊息次數與更強的模型。

**Q：每次都要重新設定嗎？**  
A：不用。Cowork Project 設定一次後，資料夾連結和 AI 指示都會保留。

**Q：可以同時分析多支股票嗎？**  
A：可以，分別填好 `2330_manual.md`、`2454_manual.md`，然後分別輸入「分析 2330」、「分析 2454」即可。

**Q：AI 的分析結果可以信任嗎？**  
A：本模型提供量化框架協助整理資訊，但 AI 可能取得過期或不準確的網路資料。每個數字旁標有來源，建議自行核實重要數字後再做決策。

---

## 資料更新建議

| 資料 | 更新時機 |
|------|---------|
| 月營收 | 每月 10 日後（公布當天）|
| EPS / 三表 | 每季財報後（約 3、5、8、11 月）|
| 本益比河流圖 | 每季一次 |
| 外資 / 投信籌碼 | 分析當天查詢 |

---

## ⚠️ 免責聲明

本專案僅供學習與研究用途，不構成任何投資建議。  
投資有風險，請自行判斷並承擔決策責任。
