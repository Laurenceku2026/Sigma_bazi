"""
工具函数 — 五行配色命盘展示
"""
from __future__ import annotations

from datetime import datetime

import streamlit as st

# 传统排盘配色（参考主流八字站）
WUXING_COLORS = {
    "木": "#2E7D32",  # 绿
    "火": "#C62828",  # 红
    "土": "#8D6E63",  # 褐
    "金": "#F9A825",  # 金黄
    "水": "#1565C0",  # 蓝
}

WUXING_MAP = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火",
    "戊": "土", "己": "土", "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
    "子": "水", "丑": "土", "寅": "木", "卯": "木",
    "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

CANGAN = {
    "子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"],
    "卯": ["乙"], "辰": ["戊", "乙", "癸"], "巳": ["丙", "戊", "庚"],
    "午": ["丁", "己"], "未": ["己", "丁", "乙"], "申": ["庚", "壬", "戊"],
    "酉": ["辛"], "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"],
}


def validate_birth_date(year, month, day, hour):
    try:
        datetime(year, month, day, hour)
        return True
    except ValueError:
        return False


def format_bazi_display(bazi):
    return {
        "年柱": f"{bazi['年柱'][0]}{bazi['年柱'][1]}",
        "月柱": f"{bazi['月柱'][0]}{bazi['月柱'][1]}",
        "日柱": f"{bazi['日柱'][0]}{bazi['日柱'][1]}",
        "时柱": f"{bazi['时柱'][0]}{bazi['时柱'][1]}",
    }


def get_wuxing_color(wuxing):
    return WUXING_COLORS.get(wuxing, "#666666")


def _char_html(ch: str, size: str = "2.2rem", extra: str = "") -> str:
    wx = WUXING_MAP.get(ch, "")
    color = get_wuxing_color(wx)
    return (
        f"<span style='color:{color};font-size:{size};font-weight:700;"
        f"font-family:\"Noto Serif SC\",\"Source Han Serif SC\",serif;' {extra}>{ch}</span>"
    )


def _god_html(god: str, is_day_master: bool = False) -> str:
    if is_day_master:
        return "<span style='color:#1565C0;font-weight:600;'>日主</span>"
    return f"<span style='color:#555;font-size:0.85rem;'>{god or '—'}</span>"


def render_wuxing_bars(stats):
    max_val = max(stats.values()) if stats.values() else 1
    bars = []
    for wuxing, count in stats.items():
        pct = (count / max_val * 100) if max_val > 0 else 0
        bars.append(
            {
                "wuxing": wuxing,
                "count": count,
                "pct": pct,
                "color": get_wuxing_color(wuxing),
            }
        )
    return bars


def _build_pillars(bazi_data):
    pillars = bazi_data.get("pillars")
    if pillars:
        return pillars
    # 兼容旧数据
    ten_gods = bazi_data.get("ten_gods") or {}
    out = {}
    for name, (gan, zhi) in bazi_data["bazi"].items():
        cangan = CANGAN.get(zhi, [])
        out[name] = {
            "gan": gan,
            "zhi": zhi,
            "gan_wx": WUXING_MAP.get(gan, ""),
            "zhi_wx": WUXING_MAP.get(zhi, ""),
            "gan_god": ten_gods.get(gan, ""),
            "zhi_god": ten_gods.get(zhi, ""),
            "cangan": [
                {"gan": g, "wx": WUXING_MAP.get(g, ""), "god": ten_gods.get(g, "")}
                for g in cangan
            ],
        }
    return out


def render_colored_pillar_table(bazi_data, lang: str = "zh") -> str:
    """四柱彩色表格 HTML（年/月/日/时）。"""
    order = ["年柱", "月柱", "日柱", "时柱"]
    labels = (
        ["年柱", "月柱", "日柱", "时柱"]
        if lang == "zh"
        else ["Year", "Month", "Day", "Hour"]
    )
    pillars = _build_pillars(bazi_data)
    day_master = bazi_data.get("day_master", "")

    def cell(name_key, field_fn):
        p = pillars.get(name_key, {})
        return f"<td style='text-align:center;padding:8px 6px;border:1px solid #ddd;vertical-align:top;'>{field_fn(p, name_key)}</td>"

    rows = []
    # header
    ths = "".join(
        f"<th style='background:#f5f5f5;padding:8px;border:1px solid #ddd;'>{lab}</th>"
        for lab in labels
    )
    rows.append(f"<tr><th style='background:#eee;padding:8px;border:1px solid #ddd;'></th>{ths}</tr>")

    # 十神（天干）
    def gan_god_cell(p, name_key):
        is_day = name_key == "日柱"
        return _god_html("日主" if is_day else p.get("gan_god", ""), is_day)

    cells = "".join(cell(k, gan_god_cell) for k in order)
    rows.append(
        f"<tr><td style='background:#fafafa;padding:8px;border:1px solid #ddd;font-weight:600;'>"
        f"{'十神' if lang == 'zh' else 'Ten Gods'}</td>{cells}</tr>"
    )

    # 天干
    def gan_cell(p, _):
        return _char_html(p.get("gan", "·"), "2.4rem")

    cells = "".join(cell(k, gan_cell) for k in order)
    rows.append(
        f"<tr><td style='background:#fafafa;padding:8px;border:1px solid #ddd;font-weight:600;'>"
        f"{'天干' if lang == 'zh' else 'Stem'}</td>{cells}</tr>"
    )

    # 地支
    def zhi_cell(p, _):
        return _char_html(p.get("zhi", "·"), "2.4rem")

    cells = "".join(cell(k, zhi_cell) for k in order)
    rows.append(
        f"<tr><td style='background:#fafafa;padding:8px;border:1px solid #ddd;font-weight:600;'>"
        f"{'地支' if lang == 'zh' else 'Branch'}</td>{cells}</tr>"
    )

    # 藏干
    def cangan_cell(p, _):
        parts = []
        for item in p.get("cangan") or []:
            g = item.get("gan", "")
            god = item.get("god", "")
            parts.append(
                f"{_char_html(g, '1.05rem')}"
                f"<span style='color:#777;font-size:0.75rem;'> ({god})</span>"
            )
        return "<br>".join(parts) if parts else "—"

    cells = "".join(cell(k, cangan_cell) for k in order)
    rows.append(
        f"<tr><td style='background:#fafafa;padding:8px;border:1px solid #ddd;font-weight:600;'>"
        f"{'藏干' if lang == 'zh' else 'Hidden'}</td>{cells}</tr>"
    )

    # legend
    legend = " · ".join(
        f"<span style='color:{c};font-weight:700;'>{w}</span>"
        for w, c in WUXING_COLORS.items()
    )
    caption = f"<div style='margin-top:8px;font-size:0.85rem;'>五行配色：{legend}</div>"
    table = (
        "<table style='width:100%;border-collapse:collapse;background:#fff;'>"
        + "".join(rows)
        + "</table>"
        + caption
    )
    return table


def render_bazi_chart(bazi_data, lang: str = "zh"):
    """在页面内渲染八字命盘（彩色四柱 + 五行条 + 大运流年）。"""
    from ui_texts import t

    info = st.session_state.get("birth_info") or {}
    name = info.get("name", "")
    gender = bazi_data.get("gender", "")
    dm = bazi_data.get("day_master", "")
    dm_wx = WUXING_MAP.get(dm, "")
    dm_color = get_wuxing_color(dm_wx)

    header = (
        f"<div style='margin-bottom:12px;line-height:1.7;'>"
        f"<div><b>{'八字排盘结果' if lang == 'zh' else 'BaZi Chart'}</b>"
        f"{('：' + name) if name else ''}</div>"
        f"<div>{'性别' if lang == 'zh' else 'Gender'}：{gender}　"
        f"{'日主' if lang == 'zh' else 'Day Master'}："
        f"<span style='color:{dm_color};font-weight:700;font-size:1.2rem;'>{dm}</span>"
        f"<span style='color:{dm_color};'>（{dm_wx}）</span></div>"
        f"</div>"
    )
    st.markdown(header, unsafe_allow_html=True)
    st.markdown(render_colored_pillar_table(bazi_data, lang), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"### {t('wuxing', lang)}")
    bars = render_wuxing_bars(bazi_data["wuxing_stats"])
    cols = st.columns(5)
    for i, bar in enumerate(bars):
        with cols[i]:
            st.markdown(
                f"<div style='text-align:center;color:{bar['color']};font-weight:700;'>"
                f"{bar['wuxing']}<br>{bar['count']}</div>",
                unsafe_allow_html=True,
            )
            st.progress(min(max(bar["pct"] / 100.0, 0.0), 1.0))

    st.markdown("---")
    st.markdown(f"### {t('dayun', lang)}")
    if bazi_data.get("da_yun"):
        for dy in bazi_data["da_yun"][:6]:
            gan, zhi = dy["gan"], dy["zhi"]
            c0, c1, c2 = st.columns([1, 2, 1])
            c0.markdown(f"**{t('step', lang, n=dy['step'])}**")
            c1.markdown(
                f"{_char_html(gan, '1.4rem')}{_char_html(zhi, '1.4rem')}",
                unsafe_allow_html=True,
            )
            c2.markdown(f"_{dy['years']}_")

    st.markdown("---")
    st.markdown(f"### {t('liunian', lang)}")
    if bazi_data.get("liu_nian"):
        for ln in bazi_data["liu_nian"]:
            year_label = f"**{ln['year']}**" if ln.get("is_current") else str(ln["year"])
            st.markdown(
                f"{year_label}：{_char_html(ln['gan'], '1.2rem')}{_char_html(ln['zhi'], '1.2rem')}",
                unsafe_allow_html=True,
            )


def generate_pdf_report(report_content, birth_info, bazi_data):
    """生成PDF报告（简化版）"""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    import io

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    y = 750
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, y, "Sigma Fate - BaZi Report")

    y -= 30
    c.setFont("Helvetica", 12)
    c.drawString(100, y, f"Name: {birth_info.get('name', '')}")
    y -= 20
    c.drawString(100, y, f"Gender: {birth_info.get('gender', '')}")

    for i in range(1, 10):
        y -= 30
        page_key = f"page{i}"
        if page_key in report_content:
            c.setFont("Helvetica-Bold", 14)
            c.drawString(100, y, f"Page {i}: {report_content[page_key].get('title', '')}")
            y -= 15
            c.setFont("Helvetica", 10)
            content = report_content[page_key].get("content", "")[:200] + "..."
            c.drawString(100, y, content[:80])

        if y < 100:
            c.showPage()
            y = 750

    c.save()
    buffer.seek(0)
    return buffer
