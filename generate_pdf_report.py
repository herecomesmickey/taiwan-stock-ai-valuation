#!/usr/bin/env python3
"""
台股 AI 投資評價模型 — PDF 報告產生器
用法: python3 generate_pdf_report.py reports/2330_report_20260629.md
"""

import sys
import re
import os
from pathlib import Path
from datetime import datetime

# ── 解析 Markdown 報告 ─────────────────────────────────────────────────────────

def parse_report(md_path):
    with open(md_path, encoding="utf-8") as f:
        content = f.read()

    data = {}

    # 標題
    m = re.search(r"^# (.+?)（(\d+)）(.+?)$", content, re.M)
    if m:
        data["company"] = m.group(1).strip()
        data["code"] = m.group(2).strip()
        data["title_suffix"] = m.group(3).strip()

    # 分析日期
    m = re.search(r"分析日期：(.+?)　", content)
    data["date"] = m.group(1).strip() if m else ""

    # 資料基準
    m = re.search(r"資料基準：(.+?)$", content, re.M)
    data["basis"] = m.group(1).strip() if m else ""

    # 各模組分數
    scores = {}
    for pattern, key in [
        (r"模組2 財務健康.*?\[(\d+)/(\d+)\]", "m2"),
        (r"模組3 成長性.*?\[(\d+)/(\d+)\]", "m3"),
        (r"模組4 估值.*?\[(\d+)/(\d+)\]", "m4"),
        (r"模組5 股利.*?\[(\d+)/(\d+)\]", "m5"),
        (r"模組6 台灣特殊指標.*?\[(\d+)/(\d+)\]", "m6"),
        (r"模組7 綜合評分.*?\[(\d+)/(\d+)\]", "m7"),
    ]:
        m = re.search(pattern, content)
        if m:
            scores[key] = {"score": int(m.group(1)), "max": int(m.group(2))}
    data["scores"] = scores

    # AI 投資評語
    m = re.search(r"### AI 投資評語.*?\n([\s\S]+?)(?=\n---|\n###)", content)
    data["comment"] = m.group(1).strip() if m else ""

    # 建議下次更新
    m = re.search(r"建議下次更新日期：(.+?)$", content, re.M)
    data["next_update"] = m.group(1).strip() if m else ""

    # 各 section 的原始表格文字（保留給後面渲染）
    data["raw_content"] = content

    return data


# ── HTML 表格解析器 ─────────────────────────────────────────────────────────────

def md_table_to_html(table_text, row_colors=True):
    lines = [l.strip() for l in table_text.strip().splitlines() if l.strip()]
    rows = []
    for line in lines:
        if re.match(r"^\|[-| :]+\|$", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(cells)

    if not rows:
        return ""

    html = ['<table class="data-table">']
    for i, row in enumerate(rows):
        html.append("<tr>")
        tag = "th" if i == 0 else "td"
        for j, cell in enumerate(row):
            cell_html = format_cell(cell)
            html.append(f"  <{tag}>{cell_html}</{tag}>")
        html.append("</tr>")
    html.append("</table>")
    return "\n".join(html)


def format_cell(text):
    # 粗體
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # 符號標色
    text = text.replace("✅", '<span class="tag tag-manual">✅ 手動</span>')
    text = text.replace("🔍", '<span class="tag tag-search">🔍 網搜</span>')
    text = text.replace("🤖", '<span class="tag tag-ai">🤖 AI估</span>')
    return text


def extract_section(content, header):
    pattern = rf"## {re.escape(header)}.*?\n([\s\S]+?)(?=\n## |\Z)"
    m = re.search(pattern, content)
    return m.group(1).strip() if m else ""


def section_to_html(raw):
    """把 Markdown section 轉成 HTML（表格 + 段落）"""
    blocks = []
    table_buf = []
    in_table = False
    in_code = False
    code_buf = []

    for line in raw.splitlines():
        if line.startswith("```"):
            if in_code:
                blocks.append('<pre class="ascii-chart">' + "\n".join(code_buf) + "</pre>")
                code_buf = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue

        if line.startswith("|"):
            in_table = True
            table_buf.append(line)
        else:
            if in_table:
                blocks.append(md_table_to_html("\n".join(table_buf)))
                table_buf = []
                in_table = False
            if line.strip():
                para = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
                para = para.replace("> ", "").strip()
                para = para.lstrip("#").strip()
                if para:
                    blocks.append(f'<p class="section-note">{para}</p>')

    if in_table:
        blocks.append(md_table_to_html("\n".join(table_buf)))

    return "\n".join(blocks)


# ── 分數顏色 ────────────────────────────────────────────────────────────────────

def score_color(score, max_score):
    pct = score / max_score if max_score else 0
    if pct >= 0.75:
        return "#10b981"  # green
    elif pct >= 0.5:
        return "#f59e0b"  # amber
    else:
        return "#ef4444"  # red


def overall_badge(score):
    if score >= 70:
        return ("🟢 值得積極關注", "#10b981")
    elif score >= 50:
        return ("🟡 持續觀察追蹤", "#f59e0b")
    else:
        return ("🔴 暫時迴避", "#ef4444")


# ── 主 HTML 產生器 ──────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&display=swap');

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Noto Sans TC', 'PingFang TC', 'Microsoft JhengHei', sans-serif;
    background: #f0f4f8;
    color: #1e293b;
    font-size: 13px;
    line-height: 1.6;
  }}

  /* ── 封面 Header ── */
  .header {{
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 60%, #0e4d7a 100%);
    color: #fff;
    padding: 44px 48px 36px;
    position: relative;
    overflow: hidden;
  }}
  .header::before {{
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 280px; height: 280px;
    border-radius: 50%;
    background: rgba(255,255,255,0.04);
  }}
  .header::after {{
    content: '';
    position: absolute;
    bottom: -80px; left: 30%;
    width: 360px; height: 360px;
    border-radius: 50%;
    background: rgba(255,255,255,0.03);
  }}
  .header-top {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }}
  .company-name {{
    font-size: 26px;
    font-weight: 700;
    letter-spacing: 1px;
    line-height: 1.2;
  }}
  .company-code {{
    font-size: 14px;
    color: #94a3b8;
    margin-top: 4px;
    letter-spacing: 2px;
  }}
  .overall-badge {{
    background: {badge_bg};
    color: #fff;
    border-radius: 12px;
    padding: 10px 22px;
    text-align: center;
    min-width: 140px;
  }}
  .badge-score {{
    font-size: 36px;
    font-weight: 700;
    line-height: 1;
  }}
  .badge-label {{
    font-size: 11px;
    opacity: 0.9;
    margin-top: 4px;
  }}
  .badge-verdict {{
    font-size: 13px;
    font-weight: 600;
    margin-top: 6px;
  }}
  .header-meta {{
    margin-top: 28px;
    display: flex;
    gap: 32px;
    font-size: 12px;
    color: #94a3b8;
  }}
  .header-meta span strong {{
    color: #e2e8f0;
    font-weight: 500;
  }}

  /* ── 分數橫條 ── */
  .score-bar-section {{
    background: #fff;
    padding: 24px 48px;
    display: flex;
    gap: 20px;
    border-bottom: 1px solid #e2e8f0;
    flex-wrap: wrap;
  }}
  .score-pill {{
    flex: 1;
    min-width: 120px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 12px 16px;
    text-align: center;
  }}
  .score-pill .module-name {{
    font-size: 11px;
    color: #64748b;
    margin-bottom: 6px;
  }}
  .score-pill .score-val {{
    font-size: 22px;
    font-weight: 700;
  }}
  .score-pill .score-max {{
    font-size: 11px;
    color: #94a3b8;
  }}
  .score-bar-wrap {{
    height: 4px;
    background: #e2e8f0;
    border-radius: 2px;
    margin-top: 8px;
  }}
  .score-bar-fill {{
    height: 100%;
    border-radius: 2px;
  }}

  /* ── 內容區 ── */
  .content {{
    max-width: 860px;
    margin: 32px auto;
    padding: 0 24px;
  }}

  /* ── 模組卡片 ── */
  .module-card {{
    background: #fff;
    border-radius: 14px;
    margin-bottom: 24px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    overflow: hidden;
  }}
  .module-header {{
    display: flex;
    align-items: center;
    padding: 16px 24px;
    border-bottom: 1px solid #f1f5f9;
  }}
  .module-icon {{
    width: 36px; height: 36px;
    border-radius: 9px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 17px;
    margin-right: 14px;
    flex-shrink: 0;
  }}
  .module-title {{
    font-size: 15px;
    font-weight: 600;
    color: #0f172a;
    flex: 1;
  }}
  .module-score-badge {{
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 700;
    color: #fff;
  }}
  .module-body {{
    padding: 20px 24px;
  }}

  /* ── 表格 ── */
  .data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12.5px;
  }}
  .data-table th {{
    background: #f8fafc;
    padding: 9px 12px;
    text-align: left;
    font-weight: 600;
    color: #475569;
    border-bottom: 2px solid #e2e8f0;
    white-space: nowrap;
  }}
  .data-table td {{
    padding: 9px 12px;
    border-bottom: 1px solid #f1f5f9;
    vertical-align: top;
  }}
  .data-table tr:last-child td {{
    border-bottom: none;
  }}
  .data-table tr:hover td {{
    background: #f8fafc;
  }}

  /* ── 標籤 ── */
  .tag {{
    display: inline-block;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 500;
    vertical-align: middle;
  }}
  .tag-manual {{ background: #dcfce7; color: #15803d; }}
  .tag-search {{ background: #dbeafe; color: #1d4ed8; }}
  .tag-ai      {{ background: #fef3c7; color: #92400e; }}

  /* ── ASCII 圖表 ── */
  .ascii-chart {{
    background: #0f172a;
    color: #a3e635;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    padding: 16px 20px;
    border-radius: 8px;
    overflow-x: auto;
    white-space: pre;
    margin-top: 12px;
  }}

  /* ── 段落備注 ── */
  .section-note {{
    font-size: 12px;
    color: #475569;
    margin: 8px 0;
    padding-left: 12px;
    border-left: 3px solid #e2e8f0;
  }}

  /* ── AI 評語 ── */
  .comment-box {{
    background: linear-gradient(135deg, #eff6ff, #f0fdf4);
    border: 1px solid #bfdbfe;
    border-radius: 12px;
    padding: 20px 24px;
    font-size: 13px;
    line-height: 1.9;
    color: #1e293b;
  }}

  /* ── 資料來源說明 ── */
  .source-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 12px;
  }}
  .source-item {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 14px 16px;
    font-size: 12px;
  }}
  .source-item .source-label {{
    font-weight: 600;
    margin-bottom: 4px;
    font-size: 13px;
  }}

  /* ── Footer ── */
  .footer {{
    background: #0f172a;
    color: #64748b;
    text-align: center;
    padding: 24px 48px;
    font-size: 11px;
    line-height: 1.8;
    margin-top: 40px;
  }}
  .footer strong {{
    color: #94a3b8;
  }}
  .disclaimer {{
    background: #fef9c3;
    border: 1px solid #fde68a;
    border-radius: 10px;
    padding: 14px 20px;
    font-size: 12px;
    color: #92400e;
    margin-top: 16px;
  }}

  /* ── 列印設定 ── */
  @media print {{
    body {{ background: #fff; }}
    .module-card {{ box-shadow: none; border: 1px solid #e2e8f0; }}
    .header {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .score-pill {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .module-icon {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  }}
</style>
</head>
<body>

<!-- ══ HEADER ══ -->
<div class="header">
  <div class="header-top">
    <div>
      <div class="company-name">{company}</div>
      <div class="company-code">TSE：{code} ｜ 台灣股市投資評價報告</div>
    </div>
    <div class="overall-badge" style="background:{badge_bg}">
      <div class="badge-score">{total_score}</div>
      <div class="badge-label">綜合評分 / {total_max}</div>
      <div class="badge-verdict">{verdict}</div>
    </div>
  </div>
  <div class="header-meta">
    <span><strong>分析日期</strong> {date}</span>
    <span><strong>資料基準</strong> {basis}</span>
    <span><strong>模型版本</strong> v1.0</span>
  </div>
</div>

<!-- ══ 分數橫條 ══ -->
<div class="score-bar-section">
  {score_pills}
</div>

<div class="content">

<!-- ══ 資料來源 ══ -->
<div class="module-card">
  <div class="module-header">
    <div class="module-icon" style="background:#f0f9ff; color:#0284c7">📋</div>
    <div class="module-title">資料來源說明</div>
  </div>
  <div class="module-body">
    <div class="source-grid">
      <div class="source-item">
        <div class="source-label">✅ 手動輸入</div>
        <div style="color:#475569">{src_manual}</div>
      </div>
      <div class="source-item">
        <div class="source-label">🔍 網路搜尋</div>
        <div style="color:#475569">{src_search}</div>
      </div>
      <div class="source-item">
        <div class="source-label">🤖 AI 估算</div>
        <div style="color:#475569">{src_ai}</div>
      </div>
    </div>
  </div>
</div>

<!-- ══ 模組 1 基本資料 ══ -->
<div class="module-card">
  <div class="module-header">
    <div class="module-icon" style="background:#f0fdf4; color:#16a34a">🏢</div>
    <div class="module-title">模組 1｜基本資料</div>
    <span style="font-size:11px;color:#94a3b8">不計分・純資訊</span>
  </div>
  <div class="module-body">
    {m1_content}
  </div>
</div>

<!-- ══ 模組 2 財務健康 ══ -->
<div class="module-card">
  <div class="module-header">
    <div class="module-icon" style="background:#fef3c7; color:#d97706">💰</div>
    <div class="module-title">模組 2｜財務健康</div>
    <span class="module-score-badge" style="background:{m2_color}">{m2_score}/{m2_max}</span>
  </div>
  <div class="module-body">
    {m2_content}
  </div>
</div>

<!-- ══ 模組 3 成長性 ══ -->
<div class="module-card">
  <div class="module-header">
    <div class="module-icon" style="background:#f0fdf4; color:#16a34a">📈</div>
    <div class="module-title">模組 3｜成長性</div>
    <span class="module-score-badge" style="background:{m3_color}">{m3_score}/{m3_max}</span>
  </div>
  <div class="module-body">
    {m3_content}
  </div>
</div>

<!-- ══ 模組 4 估值 ══ -->
<div class="module-card">
  <div class="module-header">
    <div class="module-icon" style="background:#fff1f2; color:#e11d48">🎯</div>
    <div class="module-title">模組 4｜估值</div>
    <span class="module-score-badge" style="background:{m4_color}">{m4_score}/{m4_max}</span>
  </div>
  <div class="module-body">
    {m4_content}
  </div>
</div>

<!-- ══ 模組 5 股利 ══ -->
<div class="module-card">
  <div class="module-header">
    <div class="module-icon" style="background:#fdf4ff; color:#9333ea">💎</div>
    <div class="module-title">模組 5｜股利</div>
    <span class="module-score-badge" style="background:{m5_color}">{m5_score}/{m5_max}</span>
  </div>
  <div class="module-body">
    {m5_content}
  </div>
</div>

<!-- ══ 模組 6 台灣特殊指標 ══ -->
<div class="module-card">
  <div class="module-header">
    <div class="module-icon" style="background:#fff7ed; color:#ea580c">🇹🇼</div>
    <div class="module-title">模組 6｜台灣特殊指標</div>
    <span class="module-score-badge" style="background:{m6_color}">{m6_score}/{m6_max}</span>
  </div>
  <div class="module-body">
    {m6_content}
  </div>
</div>

<!-- ══ 模組 7 AI 評語 ══ -->
<div class="module-card">
  <div class="module-header">
    <div class="module-icon" style="background:#eff6ff; color:#2563eb">🤖</div>
    <div class="module-title">模組 7｜AI 投資評語</div>
  </div>
  <div class="module-body">
    <div class="comment-box">
      {comment}
    </div>
    {m7_table}
    <div class="disclaimer">
      ⚠️ 本報告僅供學習參考，不構成投資建議。所有數據已標示來源，🤖 AI估算部分請自行至公開財報驗證後再行參考。<br>
      <strong>建議下次更新：{next_update}</strong>
    </div>
  </div>
</div>

</div><!-- /content -->

<div class="footer">
  <strong>台股 AI 投資評價模型 v1.0</strong><br>
  分析日期：{date} ｜ {company}（{code}）｜ 資料基準：{basis}<br>
  本報告由 Claude AI 輔助產生，數據來源已於各模組標示
</div>

</body>
</html>
"""


def build_score_pills(scores):
    modules = [
        ("m2", "財務健康"),
        ("m3", "成長性"),
        ("m4", "估值"),
        ("m5", "股利"),
        ("m6", "台灣指標"),
    ]
    pills = []
    for key, name in modules:
        if key not in scores:
            continue
        s = scores[key]["score"]
        mx = scores[key]["max"]
        color = score_color(s, mx)
        pct = s / mx * 100 if mx else 0
        pills.append(f"""
<div class="score-pill">
  <div class="module-name">{name}</div>
  <div class="score-val" style="color:{color}">{s}</div>
  <div class="score-max">/ {mx}</div>
  <div class="score-bar-wrap">
    <div class="score-bar-fill" style="width:{pct:.0f}%;background:{color}"></div>
  </div>
</div>""")
    return "\n".join(pills)


def extract_source_section(content):
    m = re.search(r"## 資料來源說明([\s\S]+?)(?=\n## )", content)
    if not m:
        return "", "", ""
    block = m.group(1)
    manual = re.search(r"✅ 手動輸入[：:]\s*(.+)", block)
    search = re.search(r"🔍 網路搜尋[：:]\s*(.+)", block)
    ai = re.search(r"🤖 AI估算[：:]\s*(.+)", block)
    return (
        manual.group(1).strip() if manual else "—",
        search.group(1).strip() if search else "—",
        ai.group(1).strip() if ai else "—",
    )


def generate_html(data):
    scores = data.get("scores", {})
    total_score = scores.get("m7", {}).get("score", 0)
    total_max = scores.get("m7", {}).get("max", 100)
    if total_score == 0:
        # sum m2~m6
        total_score = sum(v["score"] for k, v in scores.items() if k != "m7")
        total_max = 100

    verdict_text, badge_bg = overall_badge(total_score)

    def sc(key):
        return scores.get(key, {}).get("score", "—")
    def mx(key):
        return scores.get(key, {}).get("max", "—")
    def cl(key):
        s = scores.get(key, {})
        return score_color(s.get("score", 0), s.get("max", 1))

    raw = data["raw_content"]

    # section 提取
    m1 = section_to_html(extract_section(raw, "模組1 基本資料"))
    m2 = section_to_html(extract_section(raw, "模組2 財務健康"))
    m3 = section_to_html(extract_section(raw, "模組3 成長性"))
    m4 = section_to_html(extract_section(raw, "模組4 估值"))
    m5 = section_to_html(extract_section(raw, "模組5 股利"))
    m6 = section_to_html(extract_section(raw, "模組6 台灣特殊指標"))

    # m7 總表
    m7_raw = extract_section(raw, "模組7 綜合評分")
    m7_table = section_to_html(m7_raw)

    src_manual, src_search, src_ai = extract_source_section(raw)

    comment_paragraphs = data.get("comment", "").replace("\n\n", "</p><p>")
    comment_html = f"<p>{comment_paragraphs}</p>"

    return HTML_TEMPLATE.format(
        company=data.get("company", ""),
        code=data.get("code", ""),
        date=data.get("date", ""),
        basis=data.get("basis", ""),
        badge_bg=badge_bg,
        total_score=total_score,
        total_max=total_max,
        verdict=verdict_text,
        score_pills=build_score_pills(scores),
        src_manual=src_manual,
        src_search=src_search,
        src_ai=src_ai,
        m1_content=m1,
        m2_content=m2, m2_score=sc("m2"), m2_max=mx("m2"), m2_color=cl("m2"),
        m3_content=m3, m3_score=sc("m3"), m3_max=mx("m3"), m3_color=cl("m3"),
        m4_content=m4, m4_score=sc("m4"), m4_max=mx("m4"), m4_color=cl("m4"),
        m5_content=m5, m5_score=sc("m5"), m5_max=mx("m5"), m5_color=cl("m5"),
        m6_content=m6, m6_score=sc("m6"), m6_max=mx("m6"), m6_color=cl("m6"),
        m7_table=m7_table,
        comment=comment_html,
        next_update=data.get("next_update", ""),
    )


# ── 主程式 ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        # 預設找最新報告
        reports_dir = Path(__file__).parent / "reports"
        md_files = sorted(reports_dir.glob("*_report_*.md"), reverse=True)
        if not md_files:
            print("找不到報告檔案，請指定路徑：python3 generate_pdf_report.py reports/2330_report_20260629.md")
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
    html = generate_html(data)

    # 輸出 HTML
    stem = md_path.stem
    out_dir = md_path.parent
    html_path = out_dir / f"{stem}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ HTML 已儲存：{html_path}")

    # 嘗試轉 PDF（需要 weasyprint）
    pdf_path = out_dir / f"{stem}.pdf"
    try:
        from weasyprint import HTML as WP_HTML
        WP_HTML(filename=str(html_path)).write_pdf(str(pdf_path))
        print(f"✅ PDF 已儲存：{pdf_path}")
    except ImportError:
        print("\n⚠️  未安裝 weasyprint，只產出 HTML 版本。")
        print("   安裝方法：pip3 install weasyprint --break-system-packages")
        print(f"   HTML 檔案可用瀏覽器開啟後「列印 → 儲存為 PDF」：{html_path}")
    except Exception as e:
        print(f"\n⚠️  PDF 轉換失敗：{e}")
        print(f"   請用瀏覽器開啟 HTML 後列印為 PDF：{html_path}")


if __name__ == "__main__":
    main()
