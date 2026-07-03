#!/usr/bin/env python3
"""
台股 AI 投資評價模型 — 新手友善版 HTML 報告產生器
用法: python3 generate_pdf_report_beginner.py reports/2330_report_20260629.md
產出: reports/2330_report_20260629_beginner.html
"""

import sys, re, os
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# 1. 解析函數
# ═══════════════════════════════════════════════════════════════════════════

def parse_report(md_path):
    with open(md_path, encoding="utf-8") as f:
        raw = f.read()
    d = {"raw": raw}

    # 公司、代號
    m = re.search(r"^# (.+?)（(\d+)）", raw, re.M)
    d["company"] = m.group(1).strip() if m else "—"
    d["code"]    = m.group(2).strip() if m else "—"

    # 日期、基準（去除 markdown bold **）
    m = re.search(r"分析日期[：:]\*?\*?\s*(.+?)[\s　]", raw)
    d["date"] = re.sub(r"\*+", "", m.group(1)).strip() if m else "—"
    m = re.search(r"資料基準[：:]\*?\*?\s*(.+?)$", raw, re.M)
    d["basis"] = re.sub(r"\*+", "", m.group(1)).strip() if m else "—"

    # 股價（多種格式）
    m = re.search(r"(?:基準股價|分析基準股價|最新股價|當前股價)[^\d]*?([\d,]+)\s*元", raw)
    d["price"] = m.group(1).replace(",","").strip() if m else "—"

    # 模組分數
    d["scores"] = parse_module_scores(raw)

    # 個別指標（各 section）
    d["m2_metrics"] = parse_m2_metrics(raw)
    d["m3_metrics"] = parse_m3_metrics(raw)
    d["m4_metrics"] = parse_m4_metrics(raw)
    d["m5_metrics"] = parse_m5_metrics(raw)
    d["m6_metrics"] = parse_m6_metrics(raw)

    # 月營收序列
    d["monthly_rev"] = parse_monthly_revenue(raw)

    # AI 評語（支援 ### AI 投資評語 / ## 🤖 AI 投資評語 等格式）
    m = re.search(r"(?:#{2,3})\s*(?:🤖\s*)?AI 投資評語.*?\n([\s\S]+?)(?=\n---|\n#{2,3}|\Z)", raw)
    d["comment"] = m.group(1).strip() if m else ""

    # 下次更新（支援行內格式或獨立段落）
    m = re.search(r"建議下次更新日期[：:]\s*(.+?)$", raw, re.M)
    if not m:
        # 格式：## 📅 建議下次更新日期\n\n**2026 年 8 月...**
        m = re.search(r"建議下次更新日期[^\n]*\n+\*\*(.+?)\*\*", raw)
    d["next_update"] = m.group(1).strip() if m else "—"

    # 模組 1 表格（取出關鍵欄位）
    d["m1_info"] = parse_m1_info(raw)

    return d


def extract_section(raw, header):
    # 嘗試完全吻合
    pat = rf"## {re.escape(header)}.*?\n([\s\S]+?)(?=\n## |\Z)"
    m = re.search(pat, raw)
    if m: return m.group(1).strip()
    # 依模組編號彈性吻合（支援 模組1/模組 1｜... 等格式）
    num_m = re.match(r"模組\s*(\d+)", header)
    if num_m:
        num = num_m.group(1)
        pat2 = rf"## 模組\s*{num}[^\n]*\n([\s\S]+?)(?=\n## |\Z)"
        m = re.search(pat2, raw)
        if m: return m.group(1).strip()
    return ""


def parse_module_scores(raw):
    scores = {}
    # 支援多種格式：[10/25] / [10 / 25 分] / **[10 / 25 分]**
    patterns = [
        (r"模組\s*2[^\n]*\[(?:總分\s+)?(\d+)\s*/\s*(\d+)", "m2"),
        (r"模組\s*3[^\n]*\[(?:總分\s+)?(\d+)\s*/\s*(\d+)", "m3"),
        (r"模組\s*4[^\n]*\[(?:總分\s+)?(\d+)\s*/\s*(\d+)", "m4"),
        (r"模組\s*5[^\n]*\[(?:總分\s+)?(\d+)\s*/\s*(\d+)", "m5"),
        (r"模組\s*6[^\n]*\[(?:總分\s+)?(\d+)\s*/\s*(\d+)", "m6"),
        (r"模組\s*7[^\n]*\[(?:總分\s+)?(\d+)\s*/\s*(\d+)", "m7"),
    ]
    for pat, key in patterns:
        m = re.search(pat, raw)
        if m:
            scores[key] = {"score": int(m.group(1)), "max": int(m.group(2))}
    if "m7" not in scores:
        total = sum(v["score"] for k,v in scores.items())
        scores["m7"] = {"score": total, "max": 100}
    return scores


def _find_row(section, name):
    """從 Markdown 表格找到一列，回傳 (value_str, period, rating, score)
    支援 3欄（名稱|評估|得分）、4欄（名稱|數值|評級|得分）、5欄（名稱|數值|說明|評級|得分）
    """
    # [^|]* 允許名稱後有補充說明，例如 | 營收 YoY（2026Q1 年增率） |
    pat = rf"\|\s*{re.escape(name)}[^|]*\|(.+)"
    m = re.search(pat, section, re.IGNORECASE)
    if not m:
        return None, None, None, None
    # 分割所有欄位，過濾空字串
    cells = [c.strip() for c in m.group(0).split('|')]
    cells = [c for c in cells if c]
    n = len(cells)
    if n < 2:
        return None, None, None, None
    # cells[0] = 指標名稱
    explicit_period = ""  # 來自獨立欄位的期間（如 2026Q1）
    if n >= 6:
        # 6欄: 名稱 | 數值 | 基準期 | 評級 | 得分 | 來源
        raw_val, rating, score = cells[1], cells[3], cells[4]
        explicit_period = cells[2]
    elif n >= 5:
        # 5欄: 名稱 | 數值 | 說明/白話 | 評級 | 得分
        raw_val, rating, score = cells[1], cells[3], cells[4]
    elif n == 4:
        # 4欄: 名稱 | 數值 | 評級 | 得分
        raw_val, rating, score = cells[1], cells[2], cells[3]
    elif n == 3:
        # 3欄: 名稱 | 評估 | 得分
        raw_val, rating, score = cells[1], cells[1], cells[2]
    else:
        raw_val, rating, score = cells[1], "—", "—"
    # 清除 **bold**
    value = re.sub(r"\*\*(.+?)\*\*", r"\1", raw_val)
    # 拆出括號內的期間（優先使用獨立欄位）
    pm = re.search(r"（(.+?)）", value)
    period = explicit_period or (pm.group(1) if pm else "")
    value  = re.sub(r"（.+?）", "", value).strip()
    # 清除來源標記 emoji（🔍=網搜、🤖=AI估算），保留 ✅ 正向 評級標記
    value  = re.sub(r"[🔍🤖].*$", "", value).strip()
    # 清除評級欄開頭的 emoji（如 🟡 良 → 良）
    rating = re.sub(r"^[🟢🟡🔴✅]\s*", "", rating.strip())
    return value, period, rating, score


def parse_m2_metrics(raw):
    sec = extract_section(raw, "模組2 財務健康")
    keys = ["毛利率","營業利益率","淨利率","ROE","負債比率"]
    out = {}
    for k in keys:
        v, p, r, s = _find_row(sec, k)
        out[k] = {"value": v or "—", "period": p or "—", "rating": r or "—", "score": s or "—"}
    # FCF
    if any(x in sec for x in ["FCF為正","FCF 為正","FCF>0","FCF > 0","為正值","FCF品質加分","FCF 品質加分"]):
        out["FCF"] = {"status": "positive", "score": "+5"}
    elif any(x in sec for x in ["FCF為負","FCF 為負","負值","FCF<0"]):
        out["FCF"] = {"status": "negative", "score": "-3"}
    else:
        out["FCF"] = {"status": "unknown", "score": "—"}
    return out


def parse_m3_metrics(raw):
    sec = extract_section(raw, "模組3 成長性")
    out = {}
    # 營收 YoY
    for name in ["營收 YoY","營收YoY","營收年增率"]:
        v, p, r, s = _find_row(sec, name)
        if v: out["yoy"] = {"value": v, "period": p, "rating": r, "score": s}; break
    if "yoy" not in out: out["yoy"] = {"value":"—","period":"—","rating":"—","score":"—"}
    # EPS CAGR
    for name in ["EPS 3年CAGR","EPS 3年 CAGR","EPS 3 年 CAGR","EPS 3年複合成長率"]:
        v, p, r, s = _find_row(sec, name)
        if v: out["cagr"] = {"value": v, "period": p, "rating": r, "score": s}; break
    if "cagr" not in out: out["cagr"] = {"value":"—","period":"—","rating":"—","score":"—"}
    # 月營收趨勢
    for name in ["月營收趨勢","月營收趨勢（2026年）"]:
        v, p, r, s = _find_row(sec, name)
        if v: out["monthly"] = {"value": v, "period": p, "rating": r, "score": s}; break
    if "monthly" not in out: out["monthly"] = {"value":"—","period":"—","rating":"—","score":"—"}
    # 法說展望
    for name in ["法說展望","法說會展望"]:
        v, p, r, s = _find_row(sec, name)
        if v: out["guidance"] = {"value": v, "period": p, "rating": r, "score": s}; break
    if "guidance" not in out: out["guidance"] = {"value":"—","period":"—","rating":"—","score":"—"}
    return out


def parse_m4_metrics(raw):
    sec = extract_section(raw, "模組4 估值")
    out = {}
    # PE 值：支援 **57.7 倍** / 57.7× / 79.95× 格式
    m = re.search(r"(?:TTM\s*PE|TTM\s*P/E|當前\s*PE|當前\s*P/E|PE|本益比)[^|\n]*\*\*([\d.]+)\s*[倍×x]?\*\*", sec)
    if not m:
        m = re.search(r"(?:當前\s*PE|當前\s*P/E)[^|\n]*\|\s*\*?\*?\s*TTM\s*([\d.]+)\s*[×x倍]", sec)
    if not m:
        m = re.search(r"TTM\s*([\d.]+)\s*[×x倍]", sec)
    if not m:
        m = re.search(r"([\d.]+)\s*[×x倍]", sec)
    out["pe"] = float(m.group(1)) if m else None
    # 合理股價
    m = re.search(r"合理股價上漲空間[^\n]*([NT$＄\s]*[\d,]+)\s*元", sec)
    out["fair_price"] = m.group(1).replace(",","").strip() if m else None
    # 目標價
    m = re.search(r"目標價\s*([NT$＄\s]*[\d,]+)\s*元", sec)
    out["target_price"] = m.group(1).replace(",","").strip() if m else None
    return out


def parse_m5_metrics(raw):
    sec = extract_section(raw, "模組5 股利")
    out = {}
    for name in ["殖利率","現金殖利率"]:
        v, p, r, s = _find_row(sec, name)
        if v: out["yield"] = {"value": v, "period": p or "—", "rating": r or "—", "score": s or "—"}; break
    if "yield" not in out: out["yield"] = {"value":"—","period":"—","rating":"—","score":"—"}
    for name in ["配息率可持續性","配息率"]:
        v, p, r, s = _find_row(sec, name)
        if v: out["payout"] = {"value": v, "rating": r, "score": s}; break
    if "payout" not in out: out["payout"] = {"value":"—","rating":"—","score":"—"}
    for name in ["配息穩定性","股利穩定性","近 5 年股利穩定性","近5年股利穩定性"]:
        v, p, r, s = _find_row(sec, name)
        if v: out["stability"] = {"value": v, "rating": r, "score": s}; break
    if "stability" not in out: out["stability"] = {"value":"—","rating":"—","score":"—"}
    for name in ["填息狀況","填息"]:
        v, p, r, s = _find_row(sec, name)
        if v: out["fill"] = {"value": v, "rating": r, "score": s}; break
    if "fill" not in out: out["fill"] = {"value":"—","rating":"—","score":"—"}
    # 現金股利金額：嘗試多種格式
    m = re.search(r"(?:現金股利|年配息|全年配息)[^\d]*?([\d.]+)\s*元", sec)
    if not m:
        m = re.search(r"\|\s*\d{4}\s*年\s*現金股利\s*\|\s*([\d.]+)\s*元", sec)
    out["dividend_amt"] = m.group(1) if m else None
    return out


def _find_m6_row(sec, name):
    """M6 表格可能有兩種格式：
    3欄: | 名稱 | 評估 | 得分 |
    5欄: | 名稱 | 配分(max) | 評估內容 | 得分 | 來源 |
    偵測：若 cells[1] 是純數字，代表是「配分」欄位，評估在 cells[2]。
    """
    pat = rf"\|\s*{re.escape(name)}[^|]*\|(.+)"
    m = re.search(pat, sec, re.IGNORECASE)
    if not m:
        return None, None
    cells = [c.strip() for c in m.group(0).split('|')]
    cells = [c for c in cells if c]
    n = len(cells)
    if n >= 5 and re.match(r'^\d+$', cells[1]):
        # 格式：名稱 | 配分 | 評估 | 得分 | 來源
        value, score = cells[2], cells[3]
    elif n >= 4:
        value, score = cells[1], cells[3]
    elif n == 3:
        value, score = cells[1], cells[2]
    else:
        value, score = cells[1] if n > 1 else "—", "—"
    value = re.sub(r"\*\*(.+?)\*\*", r"\1", value)
    value = re.sub(r"（[^）]*）", "", value).strip()
    value = re.sub(r"[🔍🤖].*$", "", value).strip()
    return value, score


def parse_m6_metrics(raw):
    sec = extract_section(raw, "模組6 台灣特殊指標")
    out = {}

    v, s = _find_m6_row(sec, "月營收動能")
    out["momentum"] = {"value": v or "—", "score": s or "—"}

    for name in ["外資籌碼"]:
        v, s = _find_m6_row(sec, name)
        if v:
            direction = "sell" if any(x in v for x in ["賣","賣超","偏賣","偏空"]) else "buy"
            out["foreign"] = {"value": v, "score": s, "direction": direction}
    if "foreign" not in out: out["foreign"] = {"value":"—","score":"—","direction":"unknown"}

    for name in ["投信籌碼"]:
        v, s = _find_m6_row(sec, name)
        if v:
            direction = "sell" if any(x in v for x in ["賣","賣超","偏賣","偏空"]) else "buy"
            out["trust"] = {"value": v, "score": s, "direction": direction}
    if "trust" not in out: out["trust"] = {"value":"—","score":"—","direction":"unknown"}

    v, s = _find_m6_row(sec, "法說會態度")
    out["guidance"] = {"value": v or "—", "score": s or "—"}

    v, s = _find_m6_row(sec, "庫藏股")
    out["buyback"] = {"value": v or "無", "score": s or "0"}

    for name in ["地緣政治風險","地緣政治"]:
        v, s = _find_m6_row(sec, name)
        if v:
            out["geopolitical"] = {"value": v, "rating": v, "score": s}
            break
    if "geopolitical" not in out: out["geopolitical"] = {"value":"—","rating":"—","score":"—"}
    return out


def parse_monthly_revenue(raw):
    """解析月份+年增率，回傳 list of (month_label, yoy_float)"""
    # 嘗試格式1: "1月+36.8%、2月+22.2%..."
    pat1 = re.findall(r"(\d+)月\s*([+\-]\s*[\d.]+)%", raw)
    if pat1:
        return [(f"{m}月", float(v.replace(" ",""))) for m, v in pat1[:6]]
    # 嘗試格式2: bar chart descriptions "03月 ... +0.1%"
    pat2 = re.findall(r"(\d{2})月\D+?([+\-][\d.]+)%", raw)
    if pat2:
        return [(f"{m}月", float(v)) for m, v in pat2[:6]]
    return []


def parse_m1_info(raw):
    sec = extract_section(raw, "模組1 基本資料")
    out = {}
    # 欄位別名：每個 key 對應多個可能的欄位標題
    fields = [
        (["公司名稱","公司"],                    "company_full"),
        (["市場","市場/產業","市場／產業"],        "market"),
        (["產業","產業別","產業類別"],             "industry"),
        (["供應鏈位置","供應鏈角色"],             "chain"),
        (["業務描述","特殊亮點"],                 "desc"),
        (["主要客戶"],                            "customers"),
        (["董事長","CEO"],                       "ceo"),
    ]
    for labels, key in fields:
        for label in labels:
            pat = rf"\|\s*{re.escape(label)}\s*\|\s*(.+?)\s*\|"
            m = re.search(pat, sec, re.IGNORECASE)
            if m:
                val = re.sub(r"\*\*(.+?)\*\*", r"\1", m.group(1)).strip()
                val = re.sub(r"[🔍🤖✅]\s*.*$", "", val).strip()
                out[key] = val
                break
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 2. 顏色 / 評級工具
# ═══════════════════════════════════════════════════════════════════════════

def score_color(score, max_score):
    if max_score == 0: return "#94a3b8"
    pct = score / max_score
    if pct >= 0.75: return "#10b981"
    if pct >= 0.50: return "#f59e0b"
    return "#ef4444"

def overall_verdict(score):
    if score >= 70: return ("🟢 值得積極關注", "#10b981")
    if score >= 50: return ("🟡 持續觀察追蹤", "#f59e0b")
    return ("🔴 暫時迴避", "#ef4444")

def rating_color(rating_str):
    s = rating_str.lower()
    if any(x in s for x in ["優","正向","強","加分","秒填","全數","上修"]):
        return "#10b981"
    if any(x in s for x in ["良","偏買","持平","中"]):
        return "#f59e0b"
    return "#ef4444"

def pe_marker_left_pct(pe_val, lo=10, hi=70):
    """PE 指針位置 (%)，lo~hi 對應 0~100%"""
    if pe_val is None: return None
    pct = (pe_val - lo) / (hi - lo) * 100
    return max(2, min(96, pct))


# ═══════════════════════════════════════════════════════════════════════════
# 3. HTML 組件
# ═══════════════════════════════════════════════════════════════════════════

def h_score_pill(label, score, mx):
    color = score_color(score, mx)
    pct = round(score / mx * 100) if mx else 0
    return f"""
<div class="score-pill">
  <div class="sp-label">{label}</div>
  <div class="sp-num" style="color:{color}">{score}</div>
  <div class="sp-max">/ {mx}</div>
  <div class="bar-wrap"><div class="bar-fill" style="width:{pct}%;background:{color}"></div></div>
</div>"""


def h_metric_row(name, value, period, benchmark, rating, score_txt, explanation, score_color_val="#10b981"):
    rat_color = rating_color(rating)
    return f"""
<div class="metric-row">
  <div class="metric-top">
    <div class="mc">
      <div class="mc-label">{name}</div>
      <div class="mc-value" style="color:{score_color_val}">{value}</div>
      <div class="mc-sub">{period}</div>
    </div>
    <div class="mc">
      <div class="mc-label">及格線</div>
      <div class="mc-bench">{benchmark}</div>
    </div>
    <div class="mc mc-sm">
      <div class="mc-rating" style="color:{rat_color}">{rating}</div>
    </div>
    <div class="mc mc-xs">
      <div class="mc-score" style="color:{score_color_val}">{score_txt}</div>
    </div>
  </div>
  <div class="metric-explain">💡 {explanation}</div>
</div>"""


def h_rev_chart(monthly):
    if not monthly:
        return '<p style="color:#64748b;font-size:12px;">（月營收資料未提供）</p>'
    max_abs = max(abs(v) for _, v in monthly) or 1
    bars = ""
    for label, yoy in monthly:
        height_pct = abs(yoy) / max_abs * 80 + 10
        color = "#10b981" if yoy >= 0 else "#ef4444"
        yoy_txt = f"+{yoy:.1f}%" if yoy >= 0 else f"{yoy:.1f}%"
        bars += f"""
  <div class="rb-wrap">
    <div class="rb-yoy" style="color:{color}">{yoy_txt}</div>
    <div class="rb-bar" style="height:{height_pct:.0f}%;background:{color}"></div>
    <div class="rb-label">{label}</div>
  </div>"""
    return f'<div class="rev-chart">{bars}</div>'


def h_pe_river(pe_val, lo_thresh=20, hi_thresh=30):
    marker_html = ""
    if pe_val is not None:
        pct = pe_marker_left_pct(pe_val)
        marker_html = f"""
      <div class="pe-marker" style="left:{pct}%">
        <div class="pe-dot"></div>
        <div class="pe-marker-label">現在 {pe_val:.1f}x</div>
      </div>"""
    return f"""
<div class="pe-river-wrap">
  <div style="font-size:11px;color:#64748b;margin-bottom:8px;">低 ← 便宜　　　　　　貴 → 高</div>
  <div style="position:relative;">
    <div class="pe-track"></div>
    {marker_html}
  </div>
  <div class="pe-labels">
    <span>{lo_thresh}x 合理偏低</span>
    <span>{(lo_thresh+hi_thresh)//2}x 中間</span>
    <span>{hi_thresh}x 偏高</span>
  </div>
</div>"""


def h_chip_bar(label, direction, description):
    is_sell = direction == "sell"
    color = "#ef4444" if is_sell else "#10b981"
    width = 75 if is_sell else 55
    icon  = "📉 賣超為主" if is_sell else "📈 買超為主"
    return f"""
<div class="chip-row">
  <span class="chip-name">{label}</span>
  <div class="chip-track">
    <div class="chip-fill" style="width:{width}%;background:{color}"></div>
  </div>
  <span class="chip-label" style="color:{color}">{icon}</span>
</div>
<div class="chip-detail">{description}</div>"""


def h_circular_score(score, mx, color):
    pct = score / mx * 100 if mx else 0
    return f"""
<div class="circ-wrap">
  <div class="circ" style="background:conic-gradient({color} 0% {pct:.0f}%, #e2e8f0 {pct:.0f}% 100%)">
    <div class="circ-inner">
      <div class="circ-num" style="color:{color}">{score}</div>
      <div class="circ-denom">/ {mx}</div>
    </div>
  </div>
</div>"""


# ═══════════════════════════════════════════════════════════════════════════
# 4. CSS
# ═══════════════════════════════════════════════════════════════════════════

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'PingFang TC','Microsoft JhengHei','Noto Sans TC',sans-serif;
  background: #f0f4f8; color: #1e293b; font-size: 13.5px; line-height: 1.7;
}

/* ── Header ── */
.header {
  background: linear-gradient(135deg,#0f172a 0%,#1e3a5f 60%,#0e4d7a 100%);
  color:#fff; padding:40px 48px 32px; position:relative; overflow:hidden;
}
.header::before {
  content:''; position:absolute; top:-60px; right:-60px;
  width:260px; height:260px; border-radius:50%; background:rgba(255,255,255,0.04);
}
.hdr-top { display:flex; justify-content:space-between; align-items:flex-start; position:relative; z-index:1; }
.hdr-company { font-size:26px; font-weight:700; letter-spacing:1px; }
.hdr-sub     { font-size:13px; color:#94a3b8; margin-top:5px; }
.beginner-badge {
  background:#7c3aed; color:#fff; font-size:11px; font-weight:700;
  padding:3px 12px; border-radius:20px; margin-top:10px; display:inline-block;
}
.score-badge {
  text-align:center; border-radius:14px; padding:12px 24px; min-width:148px;
  box-shadow:0 4px 18px rgba(0,0,0,0.3);
}
.sb-num    { font-size:42px; font-weight:800; line-height:1; }
.sb-max    { font-size:13px; opacity:.8; margin-top:2px; }
.sb-verdict{ font-size:13px; font-weight:600; margin-top:7px; padding-top:7px; border-top:1px solid rgba(255,255,255,.3); }
.hdr-meta  { display:flex; gap:32px; margin-top:26px; font-size:12px; color:#94a3b8; position:relative; z-index:1; }
.hdr-meta strong { color:#e2e8f0; display:block; font-size:10px; text-transform:uppercase; letter-spacing:1px; margin-bottom:2px; }

/* ── Intro banner ── */
.intro-banner {
  background:linear-gradient(135deg,#7c3aed,#4f46e5);
  color:#fff; padding:18px 48px; font-size:13px; line-height:1.8;
}
.intro-banner strong { font-size:14px; display:block; margin-bottom:5px; }

/* ── Score pills ── */
.score-pills { background:#fff; padding:18px 48px; display:flex; gap:14px; border-bottom:1px solid #e2e8f0; }
.score-pill  { flex:1; background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:13px 14px; text-align:center; }
.sp-label    { font-size:10px; color:#64748b; font-weight:600; text-transform:uppercase; letter-spacing:.5px; margin-bottom:5px; }
.sp-num      { font-size:23px; font-weight:800; line-height:1; }
.sp-max      { font-size:11px; color:#94a3b8; }
.bar-wrap    { height:5px; background:#e2e8f0; border-radius:3px; margin-top:7px; overflow:hidden; }
.bar-fill    { height:100%; border-radius:3px; }

/* ── Content ── */
.content { max-width:900px; margin:28px auto; padding:0 22px; }

/* ── Card ── */
.card {
  background:#fff; border-radius:14px; margin-bottom:20px;
  box-shadow:0 1px 6px rgba(0,0,0,.06),0 0 0 1px rgba(0,0,0,.04); overflow:hidden;
}
.card-header { display:flex; align-items:center; padding:15px 22px; border-bottom:1px solid #f1f5f9; gap:13px; }
.card-icon   { width:36px; height:36px; border-radius:9px; display:flex; align-items:center; justify-content:center; font-size:17px; flex-shrink:0; }
.card-title  { font-size:14.5px; font-weight:700; color:#0f172a; flex:1; }
.card-score  { padding:4px 15px; border-radius:20px; font-size:13.5px; font-weight:700; color:#fff; }
.card-body   { padding:18px 22px; }

/* ── Metric Row ── */
.metric-row      { border:1px solid #e2e8f0; border-radius:11px; margin-bottom:12px; overflow:hidden; }
.metric-top      { display:grid; grid-template-columns:2fr 1.6fr 0.75fr 0.5fr; align-items:stretch; border-bottom:1px solid #f1f5f9; }
.mc              { padding:11px 14px; border-right:1px solid #f1f5f9; }
.mc:last-child   { border-right:none; }
.mc-sm           { display:flex; align-items:center; }
.mc-xs           { display:flex; align-items:center; justify-content:center; }
.mc-label        { font-size:10px; color:#64748b; font-weight:600; text-transform:uppercase; letter-spacing:.5px; margin-bottom:3px; }
.mc-value        { font-size:15px; font-weight:700; }
.mc-sub          { font-size:11px; color:#94a3b8; margin-top:2px; }
.mc-bench        { font-size:12px; color:#475569; line-height:1.5; }
.mc-rating       { font-size:12.5px; font-weight:700; }
.mc-score        { font-size:21px; font-weight:800; }
.metric-explain  { background:#fafbff; padding:9px 14px; font-size:12.5px; color:#475569; line-height:1.7; }

/* ── Tip / Warn / Highlight boxes ── */
.tip-box {
  background:#f0fdf4; border:1px solid #bbf7d0; border-left:4px solid #10b981;
  border-radius:0 10px 10px 0; padding:11px 15px; font-size:12.5px;
  color:#065f46; margin-bottom:14px; line-height:1.8;
}
.warn-box {
  background:#fef2f2; border:1px solid #fecaca; border-left:4px solid #ef4444;
  border-radius:0 10px 10px 0; padding:11px 15px; font-size:12.5px;
  color:#991b1b; margin-bottom:14px; line-height:1.8;
}
.info-box {
  background:#eff6ff; border:1px solid #bfdbfe; border-left:4px solid #3b82f6;
  border-radius:0 10px 10px 0; padding:11px 15px; font-size:12.5px;
  color:#1e40af; margin-bottom:14px; line-height:1.8;
}

/* ── Revenue chart ── */
.rev-chart     { display:flex; align-items:flex-end; gap:10px; height:110px; margin:14px 0; padding:0 4px; }
.rb-wrap       { flex:1; display:flex; flex-direction:column; align-items:center; gap:3px; height:100%; justify-content:flex-end; }
.rb-yoy        { font-size:11px; font-weight:700; text-align:center; }
.rb-bar        { width:100%; border-radius:4px 4px 0 0; min-height:4px; transition:height .3s; }
.rb-label      { font-size:11px; color:#64748b; }

/* ── PE River ── */
.pe-river-wrap { background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:18px 20px; margin:14px 0; }
.pe-track {
  height:36px; border-radius:8px; margin:10px 0 4px;
  background:linear-gradient(to right,#166534,#16a34a,#ca8a04,#b45309,#991b1b);
}
.pe-marker       { position:absolute; top:-8px; transform:translateX(-50%); display:flex; flex-direction:column; align-items:center; }
.pe-dot          { width:14px; height:52px; background:#fff; border-radius:3px; box-shadow:0 0 10px rgba(255,255,255,.7); }
.pe-marker-label { background:#fff; color:#0f172a; font-size:10px; font-weight:700; padding:2px 6px; border-radius:4px; margin-top:3px; white-space:nowrap; }
.pe-labels       { display:flex; justify-content:space-between; font-size:11px; color:#64748b; margin-top:4px; }

/* ── Chip bars ── */
.chip-row    { display:flex; align-items:center; gap:12px; margin-bottom:4px; }
.chip-name   { font-size:13px; color:#64748b; width:50px; flex-shrink:0; }
.chip-track  { flex:1; background:#f1f5f9; border-radius:4px; height:12px; overflow:hidden; }
.chip-fill   { height:12px; border-radius:4px; }
.chip-label  { font-size:12px; width:90px; text-align:right; flex-shrink:0; font-weight:600; }
.chip-detail { font-size:11.5px; color:#94a3b8; margin-bottom:12px; padding-left:62px; }

/* ── Circular score ── */
.circ-wrap { display:inline-flex; align-items:center; justify-content:center; }
.circ      { width:96px; height:96px; border-radius:50%; display:flex; align-items:center; justify-content:center; }
.circ-inner{ width:68px; height:68px; background:#fff; border-radius:50%; display:flex; flex-direction:column; align-items:center; justify-content:center; }
.circ-num  { font-size:22px; font-weight:800; line-height:1; }
.circ-denom{ font-size:11px; color:#94a3b8; }

/* ── Module 7 总分 ── */
.m7-top    { display:flex; gap:20px; align-items:center; margin-bottom:20px; flex-wrap:wrap; }
.score-grid{ display:grid; grid-template-columns:repeat(5,1fr); gap:8px; flex:1; min-width:260px; }
.sg-item   { background:#f8fafc; border:1px solid #e2e8f0; border-radius:9px; padding:10px; text-align:center; }
.sg-label  { font-size:10px; color:#64748b; font-weight:600; margin-bottom:3px; }
.sg-score  { font-size:18px; font-weight:800; }
.sg-max    { font-size:11px; color:#94a3b8; }

/* ── AI comment ── */
.comment-wrap {
  background:linear-gradient(135deg,#eff6ff,#f0fdf4);
  border:1px solid #bfdbfe; border-radius:12px;
  padding:20px 24px; font-size:13.5px; line-height:2; color:#1e293b;
}
.comment-wrap p + p { margin-top:12px; }

/* ── Glossary ── */
.divider { font-size:10.5px; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:1px; margin:20px 0 10px; padding-bottom:5px; border-bottom:1px solid #f1f5f9; }
.glossary { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.gl-item  { background:#f8fafc; border:1px solid #e2e8f0; border-radius:9px; padding:12px 14px; }
.gl-term  { font-weight:700; color:#0f172a; font-size:13px; margin-bottom:3px; }
.gl-def   { font-size:12px; color:#475569; line-height:1.7; }
.gl-eg    { font-size:11.5px; color:#94a3b8; margin-top:3px; font-style:italic; }

/* ── Next update ── */
.next-update { background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:16px 20px; margin-top:16px; }
.nu-title    { font-size:11px; color:#64748b; font-weight:600; text-transform:uppercase; letter-spacing:.5px; margin-bottom:6px; }
.nu-date     { font-size:17px; font-weight:700; color:#0f172a; margin-bottom:8px; }
.nu-list     { list-style:none; font-size:12px; color:#64748b; }
.nu-list li::before { content:'→ '; color:#6366f1; font-weight:600; }
.nu-list li  { margin-bottom:3px; }

/* ── Disclaimer ── */
.disclaimer { background:#fefce8; border:1px solid #fde68a; border-radius:10px; padding:12px 16px; font-size:12px; color:#92400e; margin-top:16px; line-height:1.8; }

/* ── Source pills ── */
.src-pills  { display:flex; flex-wrap:wrap; gap:6px; margin-top:14px; }
.src-pill   { background:#f1f5f9; border:1px solid #e2e8f0; border-radius:20px; padding:2px 10px; font-size:11px; color:#64748b; }

/* ── Footer ── */
.footer { background:#0f172a; color:#475569; text-align:center; padding:24px 48px; font-size:11.5px; line-height:1.9; margin-top:28px; }
.footer strong { color:#94a3b8; }

/* ── Table ── */
table.dt { width:100%; border-collapse:collapse; font-size:13px; }
table.dt th { background:#f8fafc; padding:8px 12px; text-align:left; font-weight:600; color:#475569; border-bottom:2px solid #e2e8f0; }
table.dt td { padding:9px 12px; border-bottom:1px solid #f1f5f9; vertical-align:top; }
table.dt tr:last-child td { border-bottom:none; }

@media print {
  body { background:#fff; -webkit-print-color-adjust:exact; print-color-adjust:exact; }
  .card { box-shadow:none; border:1px solid #e2e8f0; break-inside:avoid; }
  .content { max-width:100%; }
}
"""


# ═══════════════════════════════════════════════════════════════════════════
# 5. HTML Section 組裝
# ═══════════════════════════════════════════════════════════════════════════

def render_header(d):
    scores  = d["scores"]
    total   = scores.get("m7", {}).get("score", 0)
    total_m = scores.get("m7", {}).get("max", 100)
    verdict, badge_bg = overall_verdict(total)
    src_m = re.search(r"✅ 手動輸入[：:]\s*(.+)", d["raw"])
    src_s = re.search(r"🔍 網路搜尋[：:]\s*(.+)", d["raw"])
    src_a = re.search(r"🤖 AI估算[：:]\s*(.+)", d["raw"])
    sources = []
    if src_m: sources.append(f"✅ {src_m.group(1)[:40]}")
    if src_s:
        for s in src_s.group(1).split("、")[:5]: sources.append(f"🔍 {s.strip()}")
    if src_a: sources.append(f"🤖 {src_a.group(1)[:40]}")
    src_html = "".join(f'<span class="src-pill">{s}</span>' for s in sources)
    return f"""
<div class="header">
  <div class="hdr-top">
    <div>
      <div class="hdr-company">{d['company']}</div>
      <div class="hdr-sub">TSE/OTC：{d['code']} ｜ 台股 AI 投資評價報告</div>
      <span class="beginner-badge">📖 新手友善版</span>
    </div>
    <div class="score-badge" style="background:{badge_bg}">
      <div class="sb-num">{total}</div>
      <div class="sb-max">綜合評分 / {total_m}</div>
      <div class="sb-verdict">{verdict}</div>
    </div>
  </div>
  <div class="hdr-meta">
    <div><strong>分析日期</strong>{d['date']}</div>
    <div><strong>資料基準</strong>{d['basis']}</div>
    <div><strong>基準股價</strong>NT${d['price']} 元</div>
    <div><strong>模型版本</strong>v1.0</div>
  </div>
  <div class="src-pills">{src_html}</div>
</div>"""


def render_intro_banner():
    return """
<div class="intro-banner">
  <strong>📖 新手怎麼看這份報告？</strong>
  這份報告用 <strong>7 個模組、100 分</strong> 評估一支股票值不值得投資。每個指標下方都有 💡 說明，告訴你「這個數字是什麼意思」和「為什麼重要」。<br>
  分數顏色：<span style="background:#10b981;color:#fff;padding:1px 8px;border-radius:4px">🟢 優秀（≥75%）</span>
  <span style="background:#f59e0b;color:#fff;padding:1px 8px;border-radius:4px">🟡 普通（50~75%）</span>
  <span style="background:#ef4444;color:#fff;padding:1px 8px;border-radius:4px">🔴 需注意（&lt;50%）</span>　總分 70+ 值得積極研究。
</div>"""


def render_score_pills(d):
    sc = d["scores"]
    pills = [
        h_score_pill("財務健康", sc.get("m2",{}).get("score",0), sc.get("m2",{}).get("max",30)),
        h_score_pill("成長性",   sc.get("m3",{}).get("score",0), sc.get("m3",{}).get("max",20)),
        h_score_pill("估值",     sc.get("m4",{}).get("score",0), sc.get("m4",{}).get("max",20)),
        h_score_pill("股利",     sc.get("m5",{}).get("score",0), sc.get("m5",{}).get("max",15)),
        h_score_pill("台灣指標", sc.get("m6",{}).get("score",0), sc.get("m6",{}).get("max",20)),
    ]
    return f'<div class="score-pills">{"".join(pills)}</div>'


def render_module1(d):
    info = d.get("m1_info", {})
    rows = ""
    fields = [
        ("公司全名",   info.get("company_full", d["company"])),
        ("市場／產業", info.get("market","—") + "　/" + info.get("industry","—")),
        ("供應鏈角色", info.get("chain","—")),
        ("主要客戶",   info.get("customers","—")),
        ("業務描述",   info.get("desc","—")),
    ]
    if info.get("ceo"): fields.append(("董事長", info["ceo"]))
    for label, val in fields:
        rows += f"<tr><td style='color:#64748b;width:110px'>{label}</td><td><strong>{val}</strong></td></tr>"
    return f"""
<div class="card">
  <div class="card-header">
    <div class="card-icon" style="background:#f0fdf4;color:#16a34a">🏢</div>
    <div class="card-title">模組 1｜認識這家公司</div>
    <span style="font-size:11px;color:#94a3b8">不計分・純資訊</span>
  </div>
  <div class="card-body">
    <div class="tip-box">💡 <strong>投資第一步：先搞懂這家公司是做什麼的。</strong><br>
    你願意把錢交給一家完全不了解的公司嗎？在看數字之前，先確認自己能用一句話說清楚這間公司的核心業務，這是最重要的功課。</div>
    <table class="dt"><tbody>{rows}</tbody></table>
  </div>
</div>"""


def render_module2(d):
    m  = d["m2_metrics"]
    sc = d["scores"].get("m2", {})
    score, mx = sc.get("score",0), sc.get("max",30)
    c = score_color(score, mx)

    def row(name, bench, explain):
        info = m.get(name, {})
        v, p, r, s = info.get("value","—"), info.get("period","—"), info.get("rating","—"), info.get("score","—")
        vc = rating_color(r)
        return h_metric_row(name, v, p, bench, r, s, explain, vc)

    fcf = m.get("FCF", {})
    fcf_status = fcf.get("status","unknown")
    fcf_color  = "#10b981" if fcf_status=="positive" else ("#ef4444" if fcf_status=="negative" else "#94a3b8")
    fcf_txt    = "FCF 為正 ✅" if fcf_status=="positive" else ("FCF 為負 ⚠️" if fcf_status=="negative" else "—")
    fcf_score  = fcf.get("score","—")
    fcf_explain = ("公司「實際收到的現金」扣掉「維持並擴張業務所需的投資（蓋廠、買機器）」後剩下的現金。"
                   "這比帳面利潤更真實，因為現金造不出來。FCF 持續為正代表獲利品質高。" if fcf_status=="positive"
                   else "FCF 為負通常代表公司正在大量投資擴張（蓋廠、買設備）。短期手頭緊，需觀察未來能否轉正。")

    summary_color = "#10b981" if score/mx >= 0.75 else ("#f59e0b" if score/mx >= 0.5 else "#ef4444")
    return f"""
<div class="card">
  <div class="card-header">
    <div class="card-icon" style="background:#fef3c7;color:#d97706">💰</div>
    <div class="card-title">模組 2｜財務健康 ── 公司賺不賺錢、穩不穩？</div>
    <span class="card-score" style="background:{c}">{score} / {mx}</span>
  </div>
  <div class="card-body">
    <div class="tip-box">💡 <strong>新手重點：</strong>財務健康就像幫公司量血壓。毛利率／淨利率是「賺錢能力」，ROE 是「幫股東錢滾錢的效率」，負債比是「有沒有借太多錢」。</div>
    {row("毛利率",   "優 >40%　良 20~40%　差 <20%",
         "<strong>賣東西賺到的錢，扣掉直接生產成本後，剩下的比例。</strong>越高代表產品議價能力越強，技術門檻越高。一般製造業約 10~30%，超過 40% 就是優秀。")}
    {row("營業利益率","優 >20%　良 10~20%　差 <10%",
         "<strong>在毛利基礎上，再扣掉管理費、研發費、銷售費後，本業的獲利率。</strong>最能反映「公司本業經營好不好」，是比毛利率更嚴格的考驗。")}
    {row("淨利率",   "優 >15%　良 5~15%　差 <5%",
         "<strong>所有收入扣掉全部費用、利息、稅後，最終真正落袋的比例。</strong>是最底線的指標。超市淨利率約 1~3%，科技龍頭通常可達 15% 以上。")}
    {row("ROE",      "優 >20%　良 10~20%　差 <10%",
         "<strong>「用股東的錢，幫股東賺了多少錢」的比率。</strong>ROE 20% 代表你給公司 100 萬，一年能賺回 20 萬。巴菲特把「ROE 持續 >15%」列為選股重要條件之一。")}
    {row("負債比率", "優 <30%　良 30~50%　差 >50%",
         "<strong>公司總資產裡面，有多少比例是借來的錢。</strong>越低越安全，但製造業本來就需要大量資本支出（蓋廠、買機器），業界標準通常在 40% 以內。")}
    <div class="metric-row">
      <div class="metric-top">
        <div class="mc" style="grid-column:span 2">
          <div class="mc-label">現金流品質（自由現金流 FCF）</div>
          <div class="mc-value" style="color:{fcf_color}">{fcf_txt}</div>
        </div>
        <div class="mc mc-sm"><div class="mc-rating" style="color:{fcf_color}">{'🟢 加分' if fcf_status=='positive' else '🔴 扣分'}</div></div>
        <div class="mc mc-xs"><div class="mc-score" style="color:{fcf_color}">{fcf_score}</div></div>
      </div>
      <div class="metric-explain">💡 {fcf_explain}</div>
    </div>
    <div class="tip-box" style="margin-top:14px">
      {'✅' if score/mx >= 0.75 else ('🟡' if score/mx >= 0.5 else '⚠️')}
      <strong>模組 2 小結（{score}/{mx}）：</strong>
      {'財務健康指標整體表現優秀，公司獲利能力與資產品質良好。' if score/mx >= 0.75
       else ('財務健康表現中等，部分指標需持續觀察。' if score/mx >= 0.5
             else '財務健康需要關注，建議深入了解各項指標的背後原因。')}
    </div>
  </div>
</div>"""


def render_module3(d):
    m  = d["m3_metrics"]
    sc = d["scores"].get("m3", {})
    score, mx = sc.get("score",0), sc.get("max",20)
    c = score_color(score, mx)

    def row(key, name, bench, explain):
        info = m.get(key, {})
        v, p, r, s = info.get("value","—"), info.get("period","—"), info.get("rating","—"), info.get("score","—")
        return h_metric_row(name, v, p, bench, r, s, explain, rating_color(r))

    rev_chart = h_rev_chart(d.get("monthly_rev", []))
    return f"""
<div class="card">
  <div class="card-header">
    <div class="card-icon" style="background:#f0fdf4;color:#16a34a">📈</div>
    <div class="card-title">模組 3｜成長性 ── 公司有沒有在持續變大、變強？</div>
    <span class="card-score" style="background:{c}">{score} / {mx}</span>
  </div>
  <div class="card-body">
    <div class="tip-box">💡 <strong>新手重點：</strong>一家公司現在賺錢不夠，還要「持續成長」才值得投資。成長性看的是：營收有沒有越來越多？獲利有沒有越來越高？未來方向是否樂觀？</div>
    {row("yoy","營收 YoY（年增率）","優 >15%　良 0~15%　差 <0%",
         "<strong>「今年這一季的營收，比去年同一季成長了多少 %」。</strong>比較同一季是為了排除季節性影響。年增率持續正成長代表業績持續擴張。")}
    {row("cagr","EPS 三年複合成長率（CAGR）","優 >15%　良 5~15%　差 <5%",
         "<strong>EPS（每股盈餘）= 公司獲利 ÷ 總股數；CAGR = 平均每年成長多少 %，排除單年波動。</strong>三年 CAGR >15% 代表獲利每年平均成長超過一成五，是高成長公司的標準。")}
    <p style="font-size:11.5px;color:#64748b;margin:12px 0 4px;font-weight:600">📊 月營收年增率趨勢（台股每月10日公布，是最即時的景氣溫度計）</p>
    {rev_chart}
    {row("monthly","月營收趨勢","連續3月YoY正 → 優；持平 → 良；連續3月YoY負 → 差",
         "<strong>台灣上市公司每月10日前公布上個月營收，比財報早1~2個月。</strong>連續多月正成長 = 景氣持續向上；由正轉負連3個月 = 景氣反轉的預警訊號。")}
    {row("guidance","法說會展望","正向上修 → 優；持平 → 良；下修 → 差",
         "<strong>法說會（法人說明會）是公司 CEO 每季親自對投資人說明業績與未來展望的場合。</strong>「上修展望」= 公司對未來更樂觀，有信心接更多訂單。管理層是最了解自家公司的人，這個訊號很重要。")}
    <div class="tip-box" style="margin-top:14px">
      {'✅' if score/mx >= 0.75 else ('🟡' if score/mx >= 0.5 else '⚠️')}
      <strong>模組 3 小結（{score}/{mx}）：</strong>
      {'成長動能強勁，各項指標均表現優異。' if score/mx >= 0.75
       else ('成長力尚可，但部分指標顯示景氣仍在觀望階段。' if score/mx >= 0.5
             else '成長性偏弱，目前可能處於景氣低谷，需觀察後續是否回溫。')}
    </div>
  </div>
</div>"""


def render_module4(d):
    m  = d["m4_metrics"]
    sc = d["scores"].get("m4", {})
    score, mx = sc.get("score",0), sc.get("max",20)
    c = score_color(score, mx)
    pe_val = m.get("pe")
    pe_display = f"{pe_val:.1f} 倍" if pe_val else "—"

    # PE 位置判斷（支援行內 "歷史合理區 20~30倍" 與表格 "| 歷史 PE 合理區 | 約 30~35 倍 |" 格式）
    raw = d["raw"]
    lo_m = re.search(r"(?:歷史\s*PE\s*合理區|歷史合理區)[^|]*\|?\s*約?\s*(\d+)[~～\-](\d+)\s*倍", raw)
    lo_thresh = int(lo_m.group(1)) if lo_m else 20
    hi_thresh = int(lo_m.group(2)) if lo_m else 30

    pe_river = h_pe_river(pe_val, lo_thresh, hi_thresh)

    # 合理股價說明
    fair_section = extract_section(raw, "模組4 估值")
    # 嘗試找估值表
    est_rows = ""
    for line in fair_section.splitlines():
        if "|" in line and "EPS" in line and "PE" in line.upper() or ("算法" in line or "合理股價" in line):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 3 and not re.match(r"^[-| :]+$", line):
                est_rows += "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"

    return f"""
<div class="card">
  <div class="card-header">
    <div class="card-icon" style="background:#fff1f2;color:#e11d48">🎯</div>
    <div class="card-title">模組 4｜估值 ── 現在的股價，貴不貴？</div>
    <span class="card-score" style="background:{c}">{score} / {mx}</span>
  </div>
  <div class="card-body">
    {'<div class="warn-box">⚠️ <strong>本次報告估值偏低分。</strong>好公司 ≠ 好時機，「用好價格買到好公司」才是真正聰明的投資。</div>' if score/mx < 0.5 else '<div class="info-box">📌 估值處於合理或低估區間，投資時機相對較佳。</div>'}
    <div class="metric-row">
      <div class="metric-top">
        <div class="mc">
          <div class="mc-label">本益比（PE）TTM</div>
          <div class="mc-value" style="color:{c}">{pe_display}</div>
          <div class="mc-sub">股價 ÷ 近四季 EPS</div>
        </div>
        <div class="mc">
          <div class="mc-label">歷史合理區間</div>
          <div class="mc-bench">{lo_thresh}x（低）～ {hi_thresh}x（高）</div>
        </div>
        <div class="mc mc-sm">
          <div class="mc-rating" style="color:{c}">
            {'🟢 低檔區' if (pe_val or 99) < lo_thresh else ('🟡 合理區' if (pe_val or 99) <= hi_thresh else '🔴 高檔區')}
          </div>
        </div>
        <div class="mc mc-xs">
          <div class="mc-score" style="color:{c}">{score}<span style="font-size:11px;color:#94a3b8">/{mx}</span></div>
        </div>
      </div>
      <div class="metric-explain">💡 <strong>本益比（PE）是什麼？</strong><br>
        「你付出的股價，相當於公司多少年的獲利」。PE = 股價 ÷ EPS。<br>
        <strong>PE 越低 = 越便宜；PE 越高 = 越貴。</strong>
        成長股通常 PE 較高（市場預期未來獲利會增加），但超過歷史高檔區就需要小心，因為一旦成長不如預期，股價可能大幅修正。
      </div>
    </div>
    <p style="font-size:11px;color:#64748b;margin:14px 0 4px;font-weight:700;text-transform:uppercase;letter-spacing:.5px">本益比河流圖──現在落在哪個區間？</p>
    {pe_river}
  </div>
</div>"""


def render_module5(d):
    m  = d["m5_metrics"]
    sc = d["scores"].get("m5", {})
    score, mx = sc.get("score",0), sc.get("max",15)
    c = score_color(score, mx)

    def row(key, name, bench, explain):
        info = m.get(key, {})
        v, r, s = info.get("value","—"), info.get("rating","—"), info.get("score","—")
        return h_metric_row(name, v, "—", bench, r, s, explain, rating_color(r))

    div_amt = m.get("dividend_amt")
    div_html = f'<div class="info-box">📅 本期現金股利：<strong>{div_amt} 元</strong></div>' if div_amt else ""

    return f"""
<div class="card">
  <div class="card-header">
    <div class="card-icon" style="background:#fdf4ff;color:#9333ea">💎</div>
    <div class="card-title">模組 5｜股利 ── 公司有沒有把獲利分給你？</div>
    <span class="card-score" style="background:{c}">{score} / {mx}</span>
  </div>
  <div class="card-body">
    <div class="tip-box">💡 <strong>新手重點：</strong>股利是公司把賺到的錢直接發給股東的現金，類似「租金收入」。殖利率越高、填息越快，對領息投資人越有利。但殖利率低不代表公司差，可能只是股價太高。</div>
    {div_html}
    {row("yield","殖利率","優 >5%　良 3~5%　差 <3%",
         "<strong>「你投入的錢，每年可以領回多少 % 的現金股利」。</strong>殖利率 = 股利 ÷ 股價。低殖利率通常代表股價已很高（因為分子小分母大），多半是市場看好未來成長的「成長股」。")}
    {row("payout","配息率（可持續性）","優 <60%　良 60~80%　差 >80%",
         "<strong>「公司把賺到的錢，有多少比例發出去當股利」。</strong>配息率太高（>80%）代表公司幾乎把所有獲利都發出去，未來若景氣不好，股利可能縮水。低配息率則代表公司保留更多錢投資成長，股利也更有保障。")}
    {row("stability","配息穩定性","逐年成長 → 優；持平 → 良；曾中斷 → 差",
         "<strong>過去股利有沒有穩定甚至逐年成長。</strong>曾經中斷配息的公司，代表某年獲利大幅下滑或財務壓力大，需要特別留意。")}
    {row("fill","填息狀況","1個月內 → 優；1~3個月 → 良；未填息 → 差",
         "<strong>什麼是填息？</strong>除息日當天股價會自動「向下調整」股利金額（因為公司的錢發出去了）。填息 = 股價重新漲回除息前水準。填息越快代表市場越看好這家公司，股東不只領到股利，股價也沒跌。")}
    <div class="tip-box" style="margin-top:14px">
      {'✅' if score/mx >= 0.75 else ('🟡' if score/mx >= 0.5 else '⚠️')}
      <strong>模組 5 小結（{score}/{mx}）：</strong>
      {'股利政策穩健，殖利率吸引力高或配息品質優良。' if score/mx >= 0.75
       else ('股利表現中等，適合同時期待資本利得與股息的投資人。' if score/mx >= 0.5
             else '股利吸引力較低，此股較適合以成長為主要訴求的投資策略。')}
    </div>
  </div>
</div>"""


def render_module6(d):
    m  = d["m6_metrics"]
    sc = d["scores"].get("m6", {})
    score, mx = sc.get("score",0), sc.get("max",20)
    c = score_color(score, mx)

    foreign = m.get("foreign", {})
    trust   = m.get("trust",   {})
    chip_html = h_chip_bar("外資", foreign.get("direction","unknown"), foreign.get("value","—")) + \
                h_chip_bar("投信", trust.get("direction","unknown"),   trust.get("value","—"))

    geo = m.get("geopolitical", {})
    geo_color = rating_color(geo.get("rating","") + geo.get("value",""))

    return f"""
<div class="card">
  <div class="card-header">
    <div class="card-icon" style="background:#fff7ed;color:#ea580c">🇹🇼</div>
    <div class="card-title">模組 6｜台灣特殊指標 ── 台股獨有的資訊</div>
    <span class="card-score" style="background:{c}">{score} / {mx}</span>
  </div>
  <div class="card-body">
    <div class="tip-box">💡 <strong>台股獨特指標說明：</strong>台灣股市有幾項其他市場少見的資訊：每月公布月營收、外資與投信每日買賣超、法說會態度，以及台灣特有的地緣政治風險。這些資訊能幫助更即時掌握市場動態。</div>

    <p style="font-size:11.5px;color:#475569;font-weight:600;margin-bottom:10px">🏦 法人籌碼方向（外資是台股最大資金力量；投信是本土基金公司）</p>
    {chip_html}
    <div class="info-box" style="margin-top:4px">
      💡 <strong>外資買超</strong> = 外國機構今天買多於賣（正面）；<strong>賣超</strong> = 出清持股，股價可能承壓。<br>
      外資規模遠大於投信，兩者同步買超 = 最強訊號；同步賣超 = 需要警惕。
    </div>

    <div class="metric-row">
      <div class="metric-top">
        <div class="mc" style="grid-column:span 2">
          <div class="mc-label">月營收動能</div>
          <div class="mc-value">{m.get("momentum",{}).get("value","—")}</div>
        </div>
        <div class="mc mc-sm"><div class="mc-rating">—</div></div>
        <div class="mc mc-xs"><div class="mc-score">{m.get("momentum",{}).get("score","—")}<span style="font-size:11px;color:#94a3b8">/4</span></div></div>
      </div>
      <div class="metric-explain">💡 台灣上市公司每月10日前公布上個月營收。連續月數與加速度越高，代表景氣越強勁。</div>
    </div>

    <div class="metric-row">
      <div class="metric-top">
        <div class="mc" style="grid-column:span 2">
          <div class="mc-label">法說會態度</div>
          <div class="mc-value">{m.get("guidance",{}).get("value","—")}</div>
        </div>
        <div class="mc mc-sm"><div class="mc-rating">—</div></div>
        <div class="mc mc-xs"><div class="mc-score">{m.get("guidance",{}).get("score","—")}<span style="font-size:11px;color:#94a3b8">/4</span></div></div>
      </div>
      <div class="metric-explain">💡 管理層親自說明的未來展望。「上修」= 比上次更樂觀；「下修」= 需謹慎，通常是賣股預警。</div>
    </div>

    <div class="metric-row">
      <div class="metric-top">
        <div class="mc" style="grid-column:span 2">
          <div class="mc-label">地緣政治風險</div>
          <div class="mc-value" style="color:{geo_color}">{geo.get("value","—")}</div>
        </div>
        <div class="mc mc-sm"><div class="mc-rating" style="color:{geo_color}">{geo.get("rating","—")}</div></div>
        <div class="mc mc-xs"><div class="mc-score" style="color:{geo_color}">{geo.get("score","—")}<span style="font-size:11px;color:#94a3b8">/3</span></div></div>
      </div>
      <div class="metric-explain">💡 台灣公司普遍面臨的獨特風險。台海局勢、供應鏈地緣政治、出口管制等因素，都可能在極端情況下影響股價。這是台股投資必須納入考量的「尾部風險」（低機率但影響大的事件）。</div>
    </div>

    <div class="tip-box" style="margin-top:14px">
      {'✅' if score/mx >= 0.75 else ('🟡' if score/mx >= 0.5 else '⚠️')}
      <strong>模組 6 小結（{score}/{mx}）：</strong>
      {'台灣市場各項指標表現強勁，籌碼面與基本面共振向上。' if score/mx >= 0.75
       else ('台灣特殊指標表現中等，部分籌碼面或地緣政治因素需持續觀察。' if score/mx >= 0.5
             else '台灣特殊指標偏弱，外資賣超或地緣政治風險需特別注意。')}
    </div>
  </div>
</div>"""


def render_module7(d):
    sc = d["scores"]
    total   = sc.get("m7", {}).get("score", 0)
    total_m = sc.get("m7", {}).get("max", 100)
    tc = score_color(total, total_m)
    verdict, _ = overall_verdict(total)

    circ = h_circular_score(total, total_m, tc)

    def sg(label, key, mx_val):
        s = sc.get(key, {}).get("score", 0)
        m = sc.get(key, {}).get("max", mx_val)
        cl = score_color(s, m)
        return f'<div class="sg-item"><div class="sg-label">{label}</div><div class="sg-score" style="color:{cl}">{s}</div><div class="sg-max">/ {m}</div></div>'

    grid = (sg("財務健康","m2",30) + sg("成長性","m3",20) +
            sg("估值","m4",20) + sg("股利","m5",15) + sg("台灣指標","m6",20))

    # AI 評語段落
    comment_paras = d.get("comment","").strip().split("\n\n")
    comment_html  = "".join(f"<p>{p.strip()}</p>" for p in comment_paras if p.strip())

    # 建議觀察 watchpoints（從 next_update 區段解析）
    raw = d["raw"]
    watch_sec = re.search(r"(?:建議下次更新|next_update)([\s\S]{0,600})", raw, re.IGNORECASE)
    watch_items = []
    if watch_sec:
        for line in watch_sec.group(1).splitlines():
            li = line.strip().lstrip("→-・•").strip()
            if li and len(li) > 5: watch_items.append(li)
    watch_html = "".join(f"<li>{w}</li>" for w in watch_items[:5])

    # 名詞速查
    m2 = d["m2_metrics"]
    m5 = d["m5_metrics"]
    m4 = d["m4_metrics"]
    glossary_items = [
        ("毛利率",        "賣東西扣掉直接生產成本的利潤比率。越高代表技術門檻越高、議價能力越強。", m2.get("毛利率",{}).get("value","—")),
        ("ROE（股東報酬率）","用股東的錢，幫股東賺回多少 %。巴菲特最重視的指標之一，>15% 是優秀標準。", m2.get("ROE",{}).get("value","—")),
        ("EPS（每股盈餘）",  "公司總獲利 ÷ 總股數，每一股能分到多少利潤。EPS 成長 = 公司越來越賺錢。", "詳見模組 3"),
        ("本益比（PE）",    "股價 ÷ EPS。衡量股價貴不貴，越低越便宜。成長股 PE 通常偏高。", f"現在 {m4.get('pe') or '—'} 倍"),
        ("殖利率",         "每年現金股利 ÷ 股價。「存股族」最重視的數字，越高越像定存。", m5.get("yield",{}).get("value","—")),
        ("填息",           "除息後股價回補缺口。填息越快代表市場越看好，股東兩頭賺（股利＋股價）。", m5.get("fill",{}).get("value","—")),
        ("外資買賣超",      "外國機構每天買進或賣出的張數差額。外資是台股最大資金力量，動向至關重要。", d["m6_metrics"].get("foreign",{}).get("value","—")),
        ("自由現金流（FCF）","營業現金 – 投資支出。比帳面利潤更真實，現金是造不出來的。", "FCF 為正最佳"),
    ]
    gl_html = "".join(f"""
<div class="gl-item">
  <div class="gl-term">{term}</div>
  <div class="gl-def">{defn}</div>
  <div class="gl-eg">本次：{eg}</div>
</div>""" for term, defn, eg in glossary_items)

    return f"""
<div class="card">
  <div class="card-header">
    <div class="card-icon" style="background:#eff6ff;color:#2563eb">🤖</div>
    <div class="card-title">模組 7｜AI 綜合評語與投資建議</div>
    <span class="card-score" style="background:{tc}">{total} / {total_m}</span>
  </div>
  <div class="card-body">
    <div class="m7-top">
      {circ}
      <div class="score-grid">{grid}</div>
    </div>
    <div class="comment-wrap">{comment_html}</div>
    <div class="next-update">
      <div class="nu-title">📅 建議下次更新日期</div>
      <div class="nu-date">{d['next_update']}</div>
      {'<ul class="nu-list">' + watch_html + '</ul>' if watch_html else ''}
    </div>
    <div class="divider">📚 新手名詞速查表</div>
    <div class="glossary">{gl_html}</div>
    <div class="disclaimer">
      ⚠️ <strong>免責聲明：</strong>本報告僅供學習參考，不構成投資建議。投資一定有風險，入市前請自行查證最新數據，必要時諮詢專業財務顧問。
    </div>
  </div>
</div>"""


def render_footer(d):
    return f"""
<div class="footer">
  <strong>台股 AI 投資評價模型 v1.0 ｜ 新手友善版</strong><br>
  {d['company']}（{d['code']}）｜ 分析日期：{d['date']} ｜ 資料基準：{d['basis']}<br>
  本報告由 Claude AI 輔助產生，數據來源已於各模組標示 ｜ 僅供學習參考，非投資建議
</div>"""


# ═══════════════════════════════════════════════════════════════════════════
# 6. 主組裝函數
# ═══════════════════════════════════════════════════════════════════════════

def build_html(d):
    title = f"{d['company']}（{d['code']}）投資評價報告｜新手版"
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>
{render_header(d)}
{render_intro_banner()}
{render_score_pills(d)}
<div class="content">
{render_module1(d)}
{render_module2(d)}
{render_module3(d)}
{render_module4(d)}
{render_module5(d)}
{render_module6(d)}
{render_module7(d)}
</div>
{render_footer(d)}
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════
# 7. 入口
# ═══════════════════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        reports_dir = Path(__file__).parent / "reports"
        md_files = sorted(reports_dir.glob("*_report_*.md"), reverse=True)
        # 排除 beginner 版
        md_files = [f for f in md_files if "beginner" not in f.name]
        if not md_files:
            print("找不到報告檔案，請指定：python3 generate_pdf_report_beginner.py reports/2330_report_20260629.md")
            sys.exit(1)
        md_path = md_files[0]
        print(f"自動選取最新報告：{md_path.name}")
    else:
        md_path = Path(sys.argv[1])
        if not md_path.is_absolute():
            md_path = Path(__file__).parent / md_path

    if not md_path.exists():
        print(f"找不到檔案：{md_path}")
        sys.exit(1)

    print(f"📄 解析報告：{md_path.name}")
    data = parse_report(md_path)
    html = build_html(data)

    stem     = md_path.stem
    out_path = md_path.parent / f"{stem}_beginner.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ HTML 已儲存：{out_path}")

    # 嘗試轉 PDF
    pdf_path = md_path.parent / f"{stem}_beginner.pdf"
    try:
        from weasyprint import HTML as WP
        WP(filename=str(out_path)).write_pdf(str(pdf_path))
        print(f"✅ PDF 已儲存：{pdf_path}")
    except ImportError:
        print(f"\n💡 若需直接產出 PDF：pip3 install weasyprint --break-system-packages")
        print(f"   或在瀏覽器開啟 HTML 後 Cmd+P → 儲存為 PDF：{out_path}")
    except Exception as e:
        print(f"\n⚠️  PDF 轉換失敗：{e}\n   請用瀏覽器開啟 HTML：{out_path}")


if __name__ == "__main__":
    main()
