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

    def cell(name_key, field_fn):
        p = pillars.get(name_key, {})
        return (
            f"<td style='text-align:center;padding:8px 6px;border:1px solid #ddd;"
            f"vertical-align:top;'>{field_fn(p, name_key)}</td>"
        )

    rows = []
    ths = "".join(
        f"<th style='background:#f5f5f5;padding:8px;border:1px solid #ddd;'>{lab}</th>"
        for lab in labels
    )
    rows.append(
        f"<tr><th style='background:#eee;padding:8px;border:1px solid #ddd;'></th>{ths}</tr>"
    )

    def gan_god_cell(p, name_key):
        is_day = name_key == "日柱"
        return _god_html("日主" if is_day else p.get("gan_god", ""), is_day)

    cells = "".join(cell(k, gan_god_cell) for k in order)
    rows.append(
        f"<tr><td style='background:#fafafa;padding:8px;border:1px solid #ddd;font-weight:600;'>"
        f"{'十神' if lang == 'zh' else 'Ten Gods'}</td>{cells}</tr>"
    )

    def gan_cell(p, _):
        return _char_html(p.get("gan", "·"), "2.4rem")

    cells = "".join(cell(k, gan_cell) for k in order)
    rows.append(
        f"<tr><td style='background:#fafafa;padding:8px;border:1px solid #ddd;font-weight:600;'>"
        f"{'天干' if lang == 'zh' else 'Stem'}</td>{cells}</tr>"
    )

    def zhi_cell(p, _):
        return _char_html(p.get("zhi", "·"), "2.4rem")

    cells = "".join(cell(k, zhi_cell) for k in order)
    rows.append(
        f"<tr><td style='background:#fafafa;padding:8px;border:1px solid #ddd;font-weight:600;'>"
        f"{'地支' if lang == 'zh' else 'Branch'}</td>{cells}</tr>"
    )

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

    legend = " · ".join(
        f"<span style='color:{c};font-weight:700;'>{w}</span>"
        for w, c in WUXING_COLORS.items()
    )
    caption = f"<div style='margin-top:8px;font-size:0.85rem;'>五行配色：{legend}</div>"
    return (
        "<table style='width:100%;border-collapse:collapse;background:#fff;'>"
        + "".join(rows)
        + "</table>"
        + caption
    )


def render_flow_pillar_table(bazi_data, lang: str = "zh") -> str:
    """出生四柱 + 当前大运/流年/流月/流日（附图一核心）。"""
    pillars = _build_pillars(bazi_data)
    flow = bazi_data.get("flow") or {}
    order_birth = ["年柱", "月柱", "日柱", "时柱"]
    labels = {
        "年柱": ("年柱", "Year"),
        "月柱": ("月柱", "Month"),
        "日柱": ("日柱", "Day"),
        "时柱": ("时柱", "Hour"),
    }
    cols = []
    for name in order_birth:
        lab = labels[name][0] if lang == "zh" else labels[name][1]
        cols.append((lab, pillars.get(name) or {}, False, "*"))
    for zh, en, data in [
        ("大运", "DaYun", flow.get("da_yun")),
        ("流年", "LiuNian", flow.get("liu_nian")),
        ("流月", "LiuYue", flow.get("liu_yue")),
        ("流日", "LiuRi", flow.get("liu_ri")),
    ]:
        data = data or {}
        age = ""
        if data.get("start_age") is not None:
            age = f"{data['start_age']}岁"
        elif data.get("year") is not None:
            age = str(data["year"])
        elif data.get("month") is not None:
            age = f"{data['month']}月"
        elif data.get("day") is not None:
            age = f"{data['day']}日"
        cols.append((zh if lang == "zh" else en, data, True, age))

    th = "".join(
        f"<th style='padding:6px;border:1px solid #ddd;background:#f5f5f5;font-size:0.85rem;'>{c[0]}</th>"
        for c in cols
    )
    age_row = "".join(
        f"<td style='padding:4px;border:1px solid #ddd;text-align:center;font-size:0.8rem;"
        f"background:{'#eee' if c[2] else '#fff'};'>{c[3]}</td>"
        for c in cols
    )
    gan_row = "".join(
        f"<td style='padding:8px;border:1px solid #ddd;text-align:center;"
        f"background:{'#eee' if hl else '#fff'};'>"
        f"<div style='font-size:0.7rem;color:#888;'>{(d or {}).get('gan_god', '')}</div>"
        f"{_char_html((d or {}).get('gan', ''), '1.55rem')}</td>"
        for _, d, hl, _ in cols
    )
    zhi_row = "".join(
        f"<td style='padding:8px;border:1px solid #ddd;text-align:center;"
        f"background:{'#eee' if hl else '#fff'};'>"
        f"{_char_html((d or {}).get('zhi', ''), '1.55rem')}</td>"
        for _, d, hl, _ in cols
    )
    return (
        "<div style='overflow-x:auto;'><table style='width:100%;border-collapse:collapse;"
        "background:#fff;min-width:560px;'>"
        f"<tr>{th}</tr><tr>{age_row}</tr><tr>{gan_row}</tr><tr>{zhi_row}</tr>"
        "</table></div>"
    )


def render_dayun_timeline(bazi_data) -> str:
    cells = []
    for dy in bazi_data.get("da_yun") or []:
        bg = "#dddddd" if dy.get("is_current") else "#fff"
        cells.append(
            f"<td style='padding:6px 4px;border:1px solid #ccc;text-align:center;background:{bg};"
            f"min-width:52px;'>"
            f"<div style='font-size:0.7rem;'>{dy.get('age_label') or dy.get('start_age')}</div>"
            f"{_char_html(dy.get('gan', ''), '1.1rem')}{_char_html(dy.get('zhi', ''), '1.1rem')}"
            f"</td>"
        )
    return (
        f"<div style='overflow-x:auto;'><table style='border-collapse:collapse;'>"
        f"<tr>{''.join(cells)}</tr></table></div>"
    )


def render_liunian_timeline(bazi_data) -> str:
    cells = []
    for ln in bazi_data.get("liu_nian") or []:
        bg = "#dddddd" if ln.get("is_current") else "#fff"
        cells.append(
            f"<td style='padding:6px 4px;border:1px solid #ccc;text-align:center;background:{bg};"
            f"min-width:48px;'>"
            f"<div style='font-size:0.7rem;'>{ln.get('year', '')}</div>"
            f"{_char_html(ln.get('gan', ''), '1.05rem')}{_char_html(ln.get('zhi', ''), '1.05rem')}"
            f"</td>"
        )
    return (
        f"<div style='overflow-x:auto;'><table style='border-collapse:collapse;'>"
        f"<tr>{''.join(cells)}</tr></table></div>"
    )


def render_dayun_liunian_matrix(bazi_data, lang: str = "zh") -> str:
    """附图二：每列一步大运，下列十年流年（五行上色）。"""
    da_yun = bazi_data.get("da_yun") or []
    if not da_yun:
        return "<div>—</div>"

    def col_block(dy: dict) -> str:
        bg = "#f0f0f0" if dy.get("is_current") else "#fff"
        gods = "、".join([g for g in (dy.get("zhi_gods") or []) if g])
        rows = [
            f"<div style='font-size:0.75rem;color:#555;'>{dy.get('age_label', '')}</div>",
            f"<div style='font-size:0.7rem;color:#888;'>"
            f"{'始于' if lang == 'zh' else 'from'} {dy.get('start_year', '')}</div>",
            f"<div style='font-size:0.7rem;color:#888;'>{dy.get('gan_god', '')}</div>",
            f"<div style='margin:4px 0;'>{_char_html(dy.get('gan', ''), '1.35rem')}"
            f"{_char_html(dy.get('zhi', ''), '1.35rem')}</div>",
            f"<div style='font-size:0.65rem;color:#777;line-height:1.3;'>{gods}</div>",
            f"<div style='font-size:0.7rem;color:#888;'>{dy.get('chang_sheng', '')}</div>",
            f"<div style='font-size:0.7rem;color:#888;'>"
            f"{'止于' if lang == 'zh' else 'to'} {dy.get('end_year', '')}</div>",
            "<hr style='border:none;border-top:1px solid #ddd;margin:6px 0;'>",
        ]
        for ln in dy.get("liu_nian") or []:
            hl = "font-weight:700;" if ln.get("is_current") else ""
            rows.append(
                f"<div style='padding:2px 0;{hl}'>"
                f"<span style='font-size:0.7rem;color:#666;margin-right:4px;'>{ln.get('year', '')}</span>"
                f"{_char_html(ln.get('gan', ''), '1.05rem')}{_char_html(ln.get('zhi', ''), '1.05rem')}"
                f"</div>"
            )
        return (
            f"<td style='vertical-align:top;padding:8px 6px;border:1px solid #ddd;"
            f"background:{bg};text-align:center;min-width:72px;'>{''.join(rows)}</td>"
        )

    body = "".join(col_block(dy) for dy in da_yun)
    return (
        "<div style='overflow-x:auto;'>"
        f"<table style='border-collapse:collapse;background:#fff;'><tr>{body}</tr></table>"
        "</div>"
    )


def render_bazi_chart(bazi_data, lang: str = "zh"):
    """彩色四柱 + 五行 + 附图风格的大运/流年双表。"""
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
    st.markdown(
        "### " + ("🧭 当前运势柱（大运 · 流年 · 流月 · 流日）" if lang == "zh"
                  else "🧭 Current luck pillars")
    )
    st.caption(
        "此区块对应附图一；干支与留意在免费盘展示，会员报告详述吉凶建议。"
        if lang == "zh"
        else "Matches reference chart 1; membership report expands commentary."
    )
    st.markdown(render_flow_pillar_table(bazi_data, lang), unsafe_allow_html=True)

    if bazi_data.get("da_yun"):
        st.markdown("**大运时间轴**" if lang == "zh" else "**Decade timeline**")
        st.markdown(render_dayun_timeline(bazi_data), unsafe_allow_html=True)
    if bazi_data.get("liu_nian"):
        st.markdown(
            "**流年时间轴（当前大运十年）**" if lang == "zh" else "**Annual timeline**"
        )
        st.markdown(render_liunian_timeline(bazi_data), unsafe_allow_html=True)

    notes_s = bazi_data.get("stem_notes") or []
    notes_b = bazi_data.get("branch_notes") or []
    if notes_s or notes_b:
        st.markdown(
            f"<div style='margin-top:10px;font-size:0.9rem;line-height:1.7;'>"
            f"<div><b>{'天干留意' if lang == 'zh' else 'Stem notes'}：</b>"
            f"{'、'.join(notes_s) if notes_s else '—'}</div>"
            f"<div><b>{'地支留意' if lang == 'zh' else 'Branch notes'}：</b>"
            f"{'、'.join(notes_b) if notes_b else '—'}</div>"
            f"<div style='color:#888;font-size:0.8rem;'>"
            f"{'神煞与深度解读见会员报告' if lang == 'zh' else 'Detailed reading in membership report'}"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown(
        "### " + ("📅 大运 · 流年表" if lang == "zh" else "📅 Decade × Annual table")
    )
    st.caption(
        "对应附图二：每步大运下嵌套十年流年（亦属流年体系）；详批在报告中展开。"
        if lang == "zh"
        else "Matches reference chart 2: Liu Nian nested under each Da Yun."
    )
    st.markdown(render_dayun_liunian_matrix(bazi_data, lang), unsafe_allow_html=True)

    xiao = bazi_data.get("xiao_yun") or []
    if xiao:
        st.markdown("**起运前小运**" if lang == "zh" else "**Small luck (pre–Da Yun)**")
        cells = "".join(
            f"<td style='padding:4px 8px;border:1px solid #eee;text-align:center;'>"
            f"{x['age']}岁<br>{_char_html(x['gan'], '1rem')}{_char_html(x['zhi'], '1rem')}"
            f"<br><span style='font-size:0.75rem;color:#666;'>{x.get('year', '')}</span></td>"
            for x in xiao
        )
        st.markdown(
            f"<table style='border-collapse:collapse;'><tr>{cells}</tr></table>",
            unsafe_allow_html=True,
        )


def generate_pdf_report(report_content, birth_info, bazi_data):
    """生成多页中文 PDF（ReportLab CID 宋体，避免黑体小方块）。"""
    import io
    import re
    from xml.sax.saxutils import escape

    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

    font_name = "STSong-Light"
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(font_name))
    except Exception:
        font_name = "Helvetica"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title="六西格玛命理 · 八字报告",
        author=str((birth_info or {}).get("name") or "Sigma Fate"),
    )

    styles = getSampleStyleSheet()
    style_cover = ParagraphStyle(
        "Cover",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=20,
        leading=28,
        alignment=TA_CENTER,
        spaceAfter=18,
    )
    style_h1 = ParagraphStyle(
        "H1CN",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=14,
        leading=22,
        spaceBefore=8,
        spaceAfter=10,
    )
    style_h2 = ParagraphStyle(
        "H2CN",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=12,
        leading=18,
        spaceBefore=10,
        spaceAfter=6,
    )
    style_body = ParagraphStyle(
        "BodyCN",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10.5,
        leading=17,
        alignment=TA_JUSTIFY,
        spaceAfter=8,
    )
    style_meta = ParagraphStyle(
        "MetaCN",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=11,
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    style_bullet = ParagraphStyle(
        "BulletCN",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10.5,
        leading=17,
        leftIndent=14,
        spaceAfter=4,
    )

    def P(text: str, style=style_body):
        t = escape(str(text or "").strip()).replace("\n", "<br/>")
        if not t:
            return None
        return Paragraph(t, style)

    story = []
    name = str((birth_info or {}).get("name") or "")
    gender = str((birth_info or {}).get("gender") or (bazi_data or {}).get("gender") or "")
    birth = str((birth_info or {}).get("birth_date") or "")

    story.append(Spacer(1, 2.2 * cm))
    story.append(Paragraph(escape("六西格玛命理 · 八字报告"), style_cover))
    story.append(Paragraph(escape("Sigma Fate BaZi Report"), style_meta))
    story.append(Spacer(1, 0.6 * cm))
    if name:
        story.append(Paragraph(escape(f"姓名：{name}"), style_meta))
    if gender:
        story.append(Paragraph(escape(f"性别：{gender}"), style_meta))
    if birth:
        story.append(Paragraph(escape(f"出生：{birth}"), style_meta))
    dm = (bazi_data or {}).get("day_master") if isinstance(bazi_data, dict) else ""
    if dm:
        story.append(Paragraph(escape(f"日主：{dm}"), style_meta))
    story.append(Spacer(1, 1.0 * cm))
    story.append(Paragraph(escape("本报告仅供参考，请理性看待。"), style_meta))
    story.append(PageBreak())

    def add_page_block(page: dict, fallback_title: str):
        title = page.get("title") or fallback_title
        story.append(Paragraph(escape(str(title)), style_h1))

        pro = page.get("professional")
        if isinstance(pro, list) and pro:
            story.append(Paragraph(escape("专业解读"), style_h2))
            for para in pro:
                p = P(para, style_body)
                if p:
                    story.append(p)
        plain = page.get("plain") if isinstance(page.get("plain"), dict) else None
        if plain and (plain.get("summary") or plain.get("points") or plain.get("detail")):
            story.append(Paragraph(escape("白话说明"), style_h2))
            if plain.get("summary"):
                p = P(f"一句话：{plain['summary']}", style_body)
                if p:
                    story.append(p)
            pts = plain.get("points") or []
            if pts:
                story.append(Paragraph(escape("怎么做："), style_body))
                for i, pt in enumerate(pts, 1):
                    p = P(f"{i}. {pt}", style_bullet)
                    if p:
                        story.append(p)
            if plain.get("detail"):
                p = P(plain["detail"], style_body)
                if p:
                    story.append(p)
        elif page.get("content"):
            content = re.sub(r"[#*`]+", "", str(page.get("content") or ""))
            for block in re.split(r"\n\s*\n+", content):
                p = P(block, style_body)
                if p:
                    story.append(p)
        story.append(PageBreak())

    if isinstance(report_content, dict):
        for i in range(1, 10):
            pk = f"page{i}"
            if pk not in report_content:
                continue
            page = report_content[pk]
            if not isinstance(page, dict):
                page = {"content": str(page), "title": f"第{i}页"}
            add_page_block(page, f"第{i}页")
    else:
        story.append(Paragraph(escape("暂无报告内容。"), style_body))

    if story and isinstance(story[-1], PageBreak):
        story.pop()

    doc.build(story)
    buffer.seek(0)
    return buffer


def pdf_filename(birth_info) -> str:
    """下载文件名：含姓名。"""
    import re
    from datetime import datetime

    raw = str((birth_info or {}).get("name") or "user").strip()
    safe = re.sub(r'[\\/:*?"<>|\s]+', "_", raw).strip("_") or "user"
    return f"bazi_{safe[:40]}_{datetime.now():%Y%m%d}.pdf"
