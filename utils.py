"""
工具函数 — 五行配色命盘展示
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

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


from bazi_i18n import chart_label, gan_display, ten_god_display, wuxing_display


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


def _char_html(ch: str, size: str = "2.2rem", extra: str = "", lang: str = "zh") -> str:
    wx = WUXING_MAP.get(ch, "")
    color = get_wuxing_color(wx)
    label = gan_display(ch, lang)
    if lang == "en" and label != ch:
        # 汉字 + 罗马音（行业通用展示）
        return (
            f"<span style='display:inline-block;line-height:1.15;text-align:center;' {extra}>"
            f"<span style='color:{color};font-size:{size};font-weight:700;"
            f"font-family:\"Noto Serif SC\",\"Source Han Serif SC\",serif;'>{ch}</span>"
            f"<br><span style='color:{color};font-size:0.72rem;font-weight:600;'>"
            f"{label.split(' ', 1)[-1]}</span></span>"
        )
    return (
        f"<span style='color:{color};font-size:{size};font-weight:700;"
        f"font-family:\"Noto Serif SC\",\"Source Han Serif SC\",serif;' {extra}>{ch}</span>"
    )


def _god_html(god: str, is_day_master: bool = False, lang: str = "zh") -> str:
    if is_day_master:
        label = ten_god_display("日主", lang)
        return f"<span style='color:#1565C0;font-weight:600;'>{label}</span>"
    shown = ten_god_display(god, lang) if god else "—"
    return f"<span style='color:#555;font-size:0.85rem;'>{shown}</span>"


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


def is_bazi_chart_data(bazi_data) -> bool:
    """是否为可用的八字排盘数据（排除紫微存档占位 {_kind: ziwei}）。"""
    if not isinstance(bazi_data, dict) or not bazi_data:
        return False
    if bazi_data.get("_kind") == "ziwei":
        return False
    pillars = bazi_data.get("pillars")
    if isinstance(pillars, dict) and any(
        isinstance(pillars.get(k), dict) and pillars[k].get("gan")
        for k in ("年柱", "月柱", "日柱", "时柱")
    ):
        return True
    raw = bazi_data.get("bazi")
    if isinstance(raw, dict) and raw:
        return True
    return False


def _build_pillars(bazi_data):
    if not isinstance(bazi_data, dict):
        return {}
    pillars = bazi_data.get("pillars")
    if isinstance(pillars, dict) and pillars:
        return pillars
    ten_gods = bazi_data.get("ten_gods") or {}
    raw = bazi_data.get("bazi") or {}
    if not isinstance(raw, dict):
        return {}
    out = {}
    for name, pair in raw.items():
        if isinstance(pair, (list, tuple)) and len(pair) >= 2:
            gan, zhi = pair[0], pair[1]
        elif isinstance(pair, dict):
            gan, zhi = pair.get("gan") or "", pair.get("zhi") or ""
        else:
            continue
        if not gan and not zhi:
            continue
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
    """四柱彩色表格：十神/干支/藏干(本气中气余气)/纳音/神煞/空亡。"""
    if not is_bazi_chart_data(bazi_data):
        return ""
    order = ["年柱", "月柱", "日柱", "时柱"]
    labels = [chart_label(x, lang) for x in order]
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
        return _god_html(
            "日主" if is_day else p.get("gan_god", ""),
            is_day,
            lang=lang,
        )

    cells = "".join(cell(k, gan_god_cell) for k in order)
    rows.append(
        f"<tr><td style='background:#fafafa;padding:8px;border:1px solid #ddd;font-weight:600;'>"
        f"{chart_label('十神', lang)}</td>{cells}</tr>"
    )

    def gan_cell(p, _):
        return _char_html(p.get("gan", "·"), "2.4rem", lang=lang)

    cells = "".join(cell(k, gan_cell) for k in order)
    rows.append(
        f"<tr><td style='background:#fafafa;padding:8px;border:1px solid #ddd;font-weight:600;'>"
        f"{chart_label('天干', lang)}</td>{cells}</tr>"
    )

    def zhi_cell(p, _):
        z = _char_html(p.get("zhi", "·"), "2.4rem", lang=lang)
        if p.get("is_kong"):
            tag = "空" if lang != "en" else "void"
            z += (
                f"<div style='color:#c62828;font-size:0.75rem;font-weight:700;'>({tag})</div>"
            )
        return z

    cells = "".join(cell(k, zhi_cell) for k in order)
    rows.append(
        f"<tr><td style='background:#fafafa;padding:8px;border:1px solid #ddd;font-weight:600;'>"
        f"{chart_label('地支', lang)}</td>{cells}</tr>"
    )

    def cangan_cell(p, _):
        parts = []
        for item in p.get("cangan") or []:
            g = item.get("gan", "")
            god = item.get("god", "")
            role = item.get("role", "")
            god_s = ten_god_display(god, lang) if god else ""
            role_s = role
            if lang == "en":
                role_s = {"本气": "main", "中气": "mid", "余气": "res"}.get(role, role)
            role_html = (
                f"<span style='color:#999;font-size:0.7rem;'>[{role_s}]</span> "
                if role_s
                else ""
            )
            parts.append(
                f"<div style='margin:0 0 6px 0;line-height:1.35;'>{role_html}"
                f"{_char_html(g, '1.05rem', lang=lang)}"
                f"<span style='color:#555;font-size:0.8rem;'> {god_s}</span></div>"
            )
        return "".join(parts) if parts else "—"

    cells = "".join(cell(k, cangan_cell) for k in order)
    rows.append(
        f"<tr><td style='background:#fafafa;padding:8px;border:1px solid #ddd;font-weight:600;'>"
        f"{'藏干' if lang != 'en' else 'Hidden Stems'}</td>{cells}</tr>"
    )

    def nayin_cell(p, _):
        n = p.get("nayin") or ""
        return f"<span style='font-size:0.9rem;'>{n or '—'}</span>"

    cells = "".join(cell(k, nayin_cell) for k in order)
    rows.append(
        f"<tr><td style='background:#fafafa;padding:8px;border:1px solid #ddd;font-weight:600;'>"
        f"{'纳音' if lang != 'en' else 'Nayin'}</td>{cells}</tr>"
    )

    def shensha_cell(p, _):
        ss = p.get("shensha") or []
        if not ss:
            return "<span style='color:#bbb;'>—</span>"
        if lang == "zh_hant":
            from zh_convert import to_traditional

            ss = [to_traditional(s) for s in ss]
        return "<br>".join(
            f"<span style='font-size:0.8rem;color:#6a1b9a;'>{s}</span>" for s in ss
        )

    cells = "".join(cell(k, shensha_cell) for k in order)
    shensha_lab = "神煞" if lang != "en" else "Shen Sha"
    if lang == "zh_hant":
        from zh_convert import to_traditional

        shensha_lab = to_traditional(shensha_lab)
    rows.append(
        f"<tr><td style='background:#fafafa;padding:8px;border:1px solid #ddd;font-weight:600;'>"
        f"{shensha_lab}</td>{cells}</tr>"
    )

    def cs_cell(p, _):
        return f"<span style='font-size:0.85rem;'>{p.get('chang_sheng') or '—'}</span>"

    cells = "".join(cell(k, cs_cell) for k in order)
    rows.append(
        f"<tr><td style='background:#fafafa;padding:8px;border:1px solid #ddd;font-weight:600;'>"
        f"{'长生' if lang != 'en' else '12 Stages'}</td>{cells}</tr>"
    )

    legend = " · ".join(
        f"<span style='color:{c};font-weight:700;'>{wuxing_display(w, lang)}</span>"
        for w, c in WUXING_COLORS.items()
    )
    cap = chart_label("五行配色", lang)
    meta = bazi_data.get("meta") or {}
    kw = meta.get("kongwang") or []
    kw_text = (
        f"{'日空' if lang != 'en' else 'Day void'}：{''.join(kw)}"
        if kw
        else ("" if lang != "en" else "")
    )
    jie = bazi_data.get("month_jie") or ""
    extra = []
    if kw_text:
        extra.append(kw_text)
    if jie and lang != "en":
        extra.append(f"月令节气：{jie}")
    elif jie:
        extra.append(f"Month jieqi: {jie}")
    caption = (
        f"<div style='margin-top:8px;font-size:0.85rem;'>{cap}: {legend}</div>"
        + (
            f"<div style='margin-top:4px;font-size:0.85rem;color:#555;'>{'　'.join(extra)}</div>"
            if extra
            else ""
        )
    )
    html = (
        "<table style='width:100%;border-collapse:collapse;background:#fff;'>"
        + "".join(rows)
        + "</table>"
        + caption
    )
    if lang == "zh_hant":
        from zh_convert import to_traditional

        html = to_traditional(html)
    return html


def render_flow_pillar_table(bazi_data, lang: str = "zh") -> str:
    """出生四柱 + 当前大运/流年/流月/流日。"""
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
        lab = labels[name][0] if lang != "en" else labels[name][1]
        cols.append((lab, pillars.get(name) or {}, False, "*"))
    for zh, en, data in [
        ("大运", "Da Yun", flow.get("da_yun")),
        ("流年", "Liu Nian", flow.get("liu_nian")),
        ("流月", "Liu Yue", flow.get("liu_yue")),
        ("流日", "Liu Ri", flow.get("liu_ri")),
    ]:
        data = data or {}
        age = ""
        if data.get("start_age") is not None:
            age = f"{data['start_age']}岁" if lang != "en" else f"age {data['start_age']}"
        elif data.get("year") is not None:
            age = str(data["year"])
        elif data.get("month") is not None:
            age = f"{data['month']}月" if lang != "en" else f"m{data['month']}"
        elif data.get("day") is not None:
            age = f"{data['day']}日" if lang != "en" else f"d{data['day']}"
        cols.append((chart_label(zh, lang) if lang != "en" else en, data, True, age))

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
        f"<div style='font-size:0.7rem;color:#888;'>"
        f"{ten_god_display((d or {}).get('gan_god', ''), lang)}</div>"
        f"{_char_html((d or {}).get('gan', ''), '1.55rem', lang=lang)}</td>"
        for _, d, hl, _ in cols
    )
    zhi_row = "".join(
        f"<td style='padding:8px;border:1px solid #ddd;text-align:center;"
        f"background:{'#eee' if hl else '#fff'};'>"
        f"{_char_html((d or {}).get('zhi', ''), '1.55rem', lang=lang)}</td>"
        for _, d, hl, _ in cols
    )
    return (
        "<div style='overflow-x:auto;'><table style='width:100%;border-collapse:collapse;"
        "background:#fff;min-width:560px;'>"
        f"<tr>{th}</tr><tr>{age_row}</tr><tr>{gan_row}</tr><tr>{zhi_row}</tr>"
        "</table></div>"
    )


def render_dayun_timeline(bazi_data, lang: str = "zh") -> str:
    cells = []
    for dy in bazi_data.get("da_yun") or []:
        bg = "#dddddd" if dy.get("is_current") else "#fff"
        cells.append(
            f"<td style='padding:6px 4px;border:1px solid #ccc;text-align:center;background:{bg};"
            f"min-width:52px;'>"
            f"<div style='font-size:0.7rem;'>{dy.get('age_label') or dy.get('start_age')}</div>"
            f"{_char_html(dy.get('gan', ''), '1.1rem', lang=lang)}"
            f"{_char_html(dy.get('zhi', ''), '1.1rem', lang=lang)}"
            f"</td>"
        )
    return (
        f"<div style='overflow-x:auto;'><table style='border-collapse:collapse;'>"
        f"<tr>{''.join(cells)}</tr></table></div>"
    )


def render_liunian_timeline(bazi_data, lang: str = "zh") -> str:
    cells = []
    for ln in bazi_data.get("liu_nian") or []:
        bg = "#dddddd" if ln.get("is_current") else "#fff"
        cells.append(
            f"<td style='padding:6px 4px;border:1px solid #ccc;text-align:center;background:{bg};"
            f"min-width:48px;'>"
            f"<div style='font-size:0.7rem;'>{ln.get('year', '')}</div>"
            f"{_char_html(ln.get('gan', ''), '1.05rem', lang=lang)}"
            f"{_char_html(ln.get('zhi', ''), '1.05rem', lang=lang)}"
            f"</td>"
        )
    return (
        f"<div style='overflow-x:auto;'><table style='border-collapse:collapse;'>"
        f"<tr>{''.join(cells)}</tr></table></div>"
    )


def render_dayun_liunian_matrix(bazi_data, lang: str = "zh") -> str:
    """每列一步大运，下列十年流年（五行上色）。"""
    da_yun = bazi_data.get("da_yun") or []
    if not da_yun:
        return "<div>—</div>"

    def col_block(dy: dict) -> str:
        bg = "#f0f0f0" if dy.get("is_current") else "#fff"
        gods = "、".join([g for g in (dy.get("zhi_gods") or []) if g])
        rows = [
            f"<div style='font-size:0.75rem;color:#555;'>{dy.get('age_label', '')}</div>",
            f"<div style='font-size:0.7rem;color:#888;'>"
            f"{'始于' if lang != 'en' else 'from'} {dy.get('start_year', '')}</div>",
            f"<div style='font-size:0.7rem;color:#888;'>{dy.get('gan_god', '')}</div>",
            f"<div style='margin:4px 0;'>{_char_html(dy.get('gan', ''), '1.35rem')}"
            f"{_char_html(dy.get('zhi', ''), '1.35rem')}</div>",
            f"<div style='font-size:0.65rem;color:#777;line-height:1.3;'>{gods}</div>",
            f"<div style='font-size:0.7rem;color:#888;'>{dy.get('chang_sheng', '')}</div>",
            f"<div style='font-size:0.7rem;color:#888;'>"
            f"{'止于' if lang != 'en' else 'to'} {dy.get('end_year', '')}</div>",
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
    """彩色四柱 + 五行 + 大运/流年双表。"""
    from ui_texts import t

    if not is_bazi_chart_data(bazi_data):
        st.warning(
            "当前没有可用的八字排盘数据，请先在「输入信息」重新排盘。"
            if lang != "en"
            else "No usable BaZi chart data. Please generate a chart on the Input tab."
        )
        return

    info = st.session_state.get("birth_info") or {}
    name = info.get("name", "")
    gender = bazi_data.get("gender", "")
    dm = bazi_data.get("day_master", "")
    dm_wx = WUXING_MAP.get(dm, "")
    dm_color = get_wuxing_color(dm_wx)

    dm_show = gan_display(dm, lang) if dm else ""
    dm_wx_show = wuxing_display(dm_wx, lang) if dm_wx else ""
    header = (
        f"<div style='margin-bottom:12px;line-height:1.7;'>"
        f"<div><b>{chart_label('八字排盘结果', lang)}</b>"
        f"{('：' + name) if name else ''}</div>"
        f"<div>{chart_label('性别', lang)}：{gender}　"
        f"{chart_label('日主', lang)}："
        f"<span style='color:{dm_color};font-weight:700;font-size:1.2rem;'>{dm_show or dm}</span>"
        f"<span style='color:{dm_color};'>（{dm_wx_show or dm_wx}）</span></div>"
        f"</div>"
    )
    st.markdown(header, unsafe_allow_html=True)
    st.markdown(render_colored_pillar_table(bazi_data, lang), unsafe_allow_html=True)

    # 称骨评语
    meta = bazi_data.get("meta") or {}
    cg = meta.get("cheng_gu") or {}
    if cg:
        st.markdown("---")
        st.markdown("### " + ("⚖️ 称骨评语（袁天罡）" if lang != "en" else "⚖️ Bone-weight verse"))
        note = cg.get("calendar_note") or ""
        st.caption(
            f"总重量：{cg.get('total_text', '')}（年{cg.get('year')} + 月{cg.get('month')} + 日{cg.get('day')} + 时{cg.get('hour')}；{note}）"
            if lang != "en"
            else f"Total: {cg.get('total_text', '')} ({note})"
        )
        if cg.get("poem"):
            st.info(cg["poem"])

    st.markdown("---")
    st.markdown(f"### {t('wuxing', lang)}")
    bars = render_wuxing_bars(bazi_data.get("wuxing_stats") or {})
    cols = st.columns(5)
    for i, bar in enumerate(bars):
        with cols[i]:
            wx_lab = wuxing_display(bar["wuxing"], lang)
            st.markdown(
                f"<div style='text-align:center;color:{bar['color']};font-weight:700;'>"
                f"{wx_lab}<br>{bar['count']}</div>",
                unsafe_allow_html=True,
            )
            st.progress(min(max(bar["pct"] / 100.0, 0.0), 1.0))

    # 性格分析：紧贴五行分布下方（附图位置）
    try:
        from bazi_analysis import render_personality_html

        st.markdown(render_personality_html(bazi_data, lang), unsafe_allow_html=True)
    except Exception as e:
        st.warning(
            ("性格分析暂不可用：" if lang != "en" else "Personality unavailable: ") + str(e)
        )

    st.markdown("---")
    st.markdown(
        "### " + ("🧭 当前运势柱（大运 · 流年 · 流月 · 流日）" if lang != "en"
                  else "🧭 Current luck pillars (Da Yun · Liu Nian · Liu Yue · Liu Ri)")
    )
    st.markdown(render_flow_pillar_table(bazi_data, lang), unsafe_allow_html=True)

    if bazi_data.get("da_yun"):
        st.markdown("**大运时间轴**" if lang != "en" else "**Decade luck (Da Yun) timeline**")
        qy = bazi_data.get("qi_yun") or {}
        if qy:
            direction = ("顺行" if qy.get("forward") else "逆行") if lang != "en" else ("forward" if qy.get("forward") else "reverse")
            age = qy.get("age_label") or ""
            if lang != "en":
                st.caption(f"起运：{age}（{direction} · 虚岁排大运）")
            else:
                st.caption(f"Qi Yun: {age} ({direction}, nominal age)")
        st.markdown(render_dayun_timeline(bazi_data, lang), unsafe_allow_html=True)
    if bazi_data.get("liu_nian"):
        st.markdown(
            "**流年时间轴（当前大运十年）**" if lang != "en" else "**Annual luck (Liu Nian) timeline**"
        )
        st.markdown(render_liunian_timeline(bazi_data, lang), unsafe_allow_html=True)

    notes_s = bazi_data.get("stem_notes") or []
    notes_b = bazi_data.get("branch_notes") or []
    if notes_s or notes_b:
        st.markdown(
            f"<div style='margin-top:10px;font-size:0.9rem;line-height:1.7;'>"
            f"<div><b>{'天干留意' if lang != 'en' else 'Stem notes'}：</b>"
            f"{'、'.join(notes_s) if notes_s else '—'}</div>"
            f"<div><b>{'地支留意' if lang != 'en' else 'Branch notes'}：</b>"
            f"{'、'.join(notes_b) if notes_b else '—'}</div>"
            f"<div style='color:#888;font-size:0.8rem;'>"
            f"{'合冲提示；神煞已列于上表各柱' if lang != 'en' else 'Harmony/clash notes; Shen Sha listed per pillar above'}"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown(
        "### " + ("📅 大运 · 流年表" if lang != "en" else "📅 Decade × Annual table")
    )
    st.markdown(render_dayun_liunian_matrix(bazi_data, lang), unsafe_allow_html=True)

    xiao = bazi_data.get("xiao_yun") or []
    if xiao:
        st.markdown("**起运前小运**" if lang != "en" else "**Small luck (pre–Da Yun)**")
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


# 已注册 PDF 字体名 → 实际字体文件路径（缺字检测必须与嵌入字体一致）
_pdf_registered_font_paths: dict = {}


def _pdf_font_cache_dir():
    import tempfile
    from pathlib import Path

    d = Path(tempfile.gettempdir()) / "sigma_fate_fonts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _materialize_ttf_for_pdf(path):
    """
    ReportLab 直接嵌 TTC 在部分环境会失败或落回 Helvetica（全文小方块）。
    将 TTC 第 0 面导出为临时 TTF；已是 TTF/OTF 则原样返回。
    """
    from pathlib import Path

    p = Path(path) if path else None
    if not p or not p.is_file() or p.stat().st_size < 100_000:
        return None
    suf = p.suffix.lower()
    if suf in (".ttf", ".otf"):
        return p
    if suf != ".ttc":
        return None
    cache = _pdf_font_cache_dir() / f"{p.stem}-face0.ttf"
    try:
        if cache.is_file() and cache.stat().st_size > 100_000:
            return cache
        from fontTools.ttLib import TTFont

        font = TTFont(str(p), fontNumber=0)
        tmp = Path(str(cache) + ".part")
        font.save(str(tmp))
        if tmp.stat().st_size > 100_000:
            tmp.replace(cache)
            return cache
        tmp.unlink(missing_ok=True)
    except Exception:
        try:
            Path(str(cache) + ".part").unlink(missing_ok=True)
        except Exception:
            pass
    return None


def _pdf_cjk_source_candidates():
    """原始字体候选（TTC 会再物化为 TTF）。优先项目内全量字体。"""
    from pathlib import Path

    here = Path(__file__).resolve().parent
    cache_dir = _pdf_font_cache_dir()
    return [
        here / "fonts" / "NotoSansSC-CJK-Fallback.ttc",
        here / "fonts" / "WenQuanYiMicroHei.ttc",
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        Path("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/arphic/uming.ttc"),
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        # 简体子集放后面：缺「祿」等，需配合缺字替补
        here / "fonts" / "NotoSansSC-Regular.ttf",
        here / "fonts" / "NotoSansSC-Regular.otf",
        here / "fonts" / "SimHei.ttf",
        cache_dir / "NotoSansSC-Regular.ttf",
        cache_dir / "NotoSansSC-Regular.otf",
    ], cache_dir


def _pdf_font_is_sc_subset(font_path) -> bool:
    """简体子集（如 NotoSansSC-Regular）缺「祿」等繁体，ReportLab 会直接丢字。"""
    from pathlib import Path

    if not font_path:
        return True
    name = str(font_path).replace("\\", "/").lower()
    base = name.rsplit("/", 1)[-1]
    if "notosanssc-cjk-fallback" in base or "wqy" in base or "microhei" in base:
        return False
    if "uming" in base or "droid" in base or "notosanscjk" in base or "noto-sans-cjk" in base:
        return False
    if "notosanssc" in base or "noto-sans-sc" in base:
        return True
    try:
        p = Path(font_path)
        if p.is_file() and p.suffix.lower() in (".ttf", ".otf") and p.stat().st_size < 3_500_000:
            # 小于约 3.5MB 的 CJK 单字体几乎都是简体子集
            return True
    except Exception:
        pass
    return False


def _pdf_registered_font_has_cjk(font_name: str) -> bool:
    """确认已注册字体真能出汉字；Helvetica/失败注册会变成全文小方块。"""
    if not font_name or font_name in (
        "Helvetica",
        "Times-Roman",
        "Courier",
        "STSong-Light",
        "STHeiti-Light",
    ):
        return False
    try:
        from reportlab.pdfbase import pdfmetrics

        face = pdfmetrics.getFont(font_name).face
        cmap = getattr(face, "charToGlyph", None) or {}
        # 中 / 禄 / 祿 任一即可
        return any(cmap.get(cp) is not None for cp in (0x4E2D, 0x7984, 0x797F))
    except Exception:
        return False


def register_pdf_cjk_font(font_name: str = "SFCJK") -> tuple:
    """
    注册 PDF 用 CJK 字体，返回 (font_name, font_path)。
    始终优先嵌入 TTF（TTC 先导出），并校验汉字字形；绝不静默落回 Helvetica。
    """
    from pathlib import Path

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    sources, cache_dir = _pdf_cjk_source_candidates()
    bold_name = f"{font_name}-Bold"
    cache_ttf = cache_dir / "NotoSansSC-Regular.ttf"
    cache_otf = cache_dir / "NotoSansSC-Regular.otf"

    try:
        registered = set(pdfmetrics.getRegisteredFontNames())
    except Exception:
        registered = set()

    prev_path = _pdf_registered_font_paths.get(font_name)
    if font_name in registered and prev_path and _pdf_registered_font_has_cjk(font_name):
        return font_name, Path(prev_path)

    # 旧注册无效（如 Helvetica 占位）时换名重试
    use_name = font_name
    if font_name in registered and not _pdf_registered_font_has_cjk(font_name):
        use_name = f"{font_name}X"
        bold_name = f"{use_name}-Bold"

    def _try_register_ttf(ttf_path: Path):
        if not ttf_path or not ttf_path.is_file() or ttf_path.stat().st_size < 100_000:
            return None
        try:
            reg = set(pdfmetrics.getRegisteredFontNames())
        except Exception:
            reg = set()
        if use_name in reg:
            if _pdf_registered_font_has_cjk(use_name):
                _pdf_registered_font_paths[font_name] = str(ttf_path)
                _pdf_registered_font_paths[use_name] = str(ttf_path)
                return use_name
            return None
        try:
            pdfmetrics.registerFont(TTFont(use_name, str(ttf_path)))
            if bold_name not in reg:
                pdfmetrics.registerFont(TTFont(bold_name, str(ttf_path)))
            try:
                pdfmetrics.registerFontFamily(
                    use_name,
                    normal=use_name,
                    bold=bold_name,
                    italic=use_name,
                    boldItalic=bold_name,
                )
            except Exception:
                pass
            if not _pdf_registered_font_has_cjk(use_name):
                return None
            _pdf_registered_font_paths[font_name] = str(ttf_path)
            _pdf_registered_font_paths[use_name] = str(ttf_path)
            return use_name
        except Exception:
            return None

    for src in sources:
        ttf = _materialize_ttf_for_pdf(src)
        got = _try_register_ttf(ttf) if ttf else None
        if got:
            return got, ttf

    urls = (
        (
            "https://cdn.jsdelivr.net/fontsource/fonts/noto-sans-sc@5.2.5/chinese-simplified-400-normal.ttf",
            cache_ttf,
        ),
        (
            "https://cdn.jsdelivr.net/npm/@fontsource/noto-sans-sc@5.2.5/files/noto-sans-sc-chinese-simplified-400-normal.ttf",
            cache_ttf,
        ),
        (
            "https://cdn.jsdelivr.net/gh/googlefonts/noto-cjk@main/Sans/OTF/SimplifiedChinese/NotoSansSC-Regular.otf",
            cache_otf,
        ),
    )
    try:
        import urllib.request

        for url, dest in urls:
            tmp = Path(str(dest) + ".part")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "SigmaFateBaZi/1.0"})
                with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as out:
                    while True:
                        chunk = resp.read(1024 * 256)
                        if not chunk:
                            break
                        out.write(chunk)
                if tmp.stat().st_size > 100_000:
                    tmp.replace(dest)
                    got = _try_register_ttf(dest)
                    if got:
                        return got, dest
            except Exception:
                try:
                    tmp.unlink(missing_ok=True)
                except Exception:
                    pass
                continue
    except Exception:
        pass

    # 不再返回 Helvetica/CID：调用方应改走图片文字，避免全文小方块
    return "", None


def _resolve_pdf_cjk_font() -> tuple:
    """
    返回 (font_body_name, font_head_name)。
    必须嵌入 TrueType 中文字体；CID（STSong）在 Chrome/手机常显示黑方块。
    """
    name, _path = register_pdf_cjk_font("SFCJK")
    if not name:
        return "Helvetica", "Helvetica"
    return name, name



def _cjk_font_file():
    """返回可用于 PIL 的中文字体路径（优先繁简覆盖更全者）。"""
    from pathlib import Path
    here = Path(__file__).resolve().parent
    candidates = [
        here / "fonts" / "NotoSansSC-CJK-Fallback.ttc",
        here / "fonts" / "WenQuanYiMicroHei.ttc",
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        Path("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        here / "fonts" / "NotoSansSC-Regular.ttf",
        here / "fonts" / "NotoSansSC-Regular.otf",
    ]
    for p in candidates:
        try:
            if p.is_file() and p.stat().st_size > 100_000:
                return p
        except Exception:
            continue
    return None


# 简体子集缺繁体字形时的替补（zh_hant / OpenCC 常见字；全量字体下通常不触发）
_PDF_GLYPH_FALLBACKS = str.maketrans(
    {
        "剋": "克",
        "祿": "禄",
        "權": "权",
        "鸞": "鸾",
        "鉞": "钺",
        "銜": "衔",
        "門": "门",
        "馬": "马",
        "龍": "龙",
        "鳳": "凤",
        "華": "华",
        "蓋": "盖",
        "貴": "贵",
        "臺": "台",
        "輔": "辅",
        "誥": "诰",
        "虛": "虚",
        "傷": "伤",
        "應": "应",
        "歲": "岁",
        "與": "与",
        "專": "专",
        "業": "业",
        "總": "总",
        "結": "结",
        "規": "规",
        "則": "则",
        "點": "点",
        "際": "际",
        "牽": "牵",
        "動": "动",
        "當": "当",
        "階": "阶",
        "現": "现",
        "場": "场",
        "為": "为",
        "這": "这",
        "個": "个",
        "還": "还",
        "會": "会",
        "說": "说",
        "對": "对",
        "開": "开",
        "揚": "扬",
        "穩": "稳",
        "經": "经",
        "營": "营",
        "資": "资",
        "讀": "读",
        "盤": "盘",
        "宮": "宫",
        "陽": "阳",
        "陰": "阴",
        "殺": "杀",
        "國": "国",
        "語": "语",
        "術": "术",
        "數": "数",
        "報": "报",
    }
)
_pdf_cmap_cache: dict = {}


def _pdf_load_cmap(font_path):
    """加载字体 cmap；TTC 必须带 fontNumber，失败返回空 dict。"""
    key = str(font_path)
    if key in _pdf_cmap_cache:
        return _pdf_cmap_cache[key]
    cmap = {}
    try:
        from pathlib import Path

        from fontTools.ttLib import TTFont

        p = Path(font_path)
        if p.suffix.lower() == ".ttc":
            font = TTFont(str(p), fontNumber=0)
        else:
            font = TTFont(str(p))
        cmap = font.getBestCmap() or {}
    except Exception:
        cmap = {}
    _pdf_cmap_cache[key] = cmap
    return cmap


def _pdf_font_has_char(font_path, ch: str) -> bool:
    """检查字体 cmap 是否含该字。

    - cmap 读失败时：对非 ASCII 返回 False，促发繁→简替补（避免误留缺字）。
    - 简体子集：已知繁体替补字直接视为缺失。
    """
    if not font_path or not ch:
        return True
    if ord(ch) < 128:
        return True
    if _pdf_font_is_sc_subset(font_path) and ch in _PDF_GLYPH_FALLBACKS:
        return False
    cmap = _pdf_load_cmap(font_path)
    if not cmap:
        # 读不出 cmap 时宁可替换，不可留下豆腐块
        return False
    return ord(ch) in cmap


_PDF_SYMBOL_FALLBACKS = (
    ("→", "->"),
    ("⇒", "->"),
    ("←", "<-"),
    ("｜", "|"),
    ("—", "-"),
)


def _pdf_fix_glyphs(text: str, font_path=None) -> str:
    """
    PDF 出字前替换字体缺失字形，避免「方框里带 X」。
    仅在字体确实缺该字时才用替补表；全量字体则保留繁体原字。
    简体子集或未指定字体时，对已知繁体字一律替补。
    """
    if not text:
        return text
    s = str(text)
    # 短语级：OpenCC 常把「相克」转成「相剋」
    s = s.replace("相剋", "相克")
    force_fallback = (not font_path) or _pdf_font_is_sc_subset(font_path)
    if force_fallback:
        for a, b in _PDF_SYMBOL_FALLBACKS:
            s = s.replace(a, b)
        return s.translate(_PDF_GLYPH_FALLBACKS)
    for a, b in _PDF_SYMBOL_FALLBACKS:
        if a in s and not _pdf_font_has_char(font_path, a):
            s = s.replace(a, b)
    out = []
    for ch in s:
        if ch in ("\u200b", "\ufeff"):
            continue
        if _pdf_font_has_char(font_path, ch):
            out.append(ch)
            continue
        # 字体缺字：查静态繁→简替补
        alt = ch.translate(_PDF_GLYPH_FALLBACKS)
        if alt != ch and _pdf_font_has_char(font_path, alt):
            out.append(alt)
        else:
            out.append(alt if alt != ch else ch)
    return "".join(out)


def _pdf_text_image(
    text: str,
    *,
    font_path,
    font_size: int = 11,
    max_width_pt: float = 460,
    fill: str = "#222222",
    align: str = "left",
):
    """把中文绘成图片 Flowable，避免 ReportLab TTF 子集缺字黑方块。"""
    import io
    from reportlab.platypus import Image as RLImage
    from PIL import Image, ImageDraw, ImageFont

    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    raw = _pdf_fix_glyphs(raw, font_path)
    if not raw:
        return None

    # pt -> px @ 2x for清晰度
    scale = 2
    font = ImageFont.truetype(str(font_path), font_size * scale)
    max_w = int(max_width_pt * scale)

    def char_w(ch: str) -> int:
        box = font.getbbox(ch)
        return max(1, box[2] - box[0])

    lines = []
    for para in raw.split("\n"):
        if not para:
            lines.append("")
            continue
        cur = ""
        cur_w = 0
        for ch in para:
            w = char_w(ch)
            if cur and cur_w + w > max_w:
                lines.append(cur)
                cur = ch
                cur_w = w
            else:
                cur += ch
                cur_w += w
        lines.append(cur)

    line_h = int(font_size * scale * 1.55)
    pad = int(2 * scale)
    img_h = pad * 2 + max(line_h, line_h * len(lines))
    img_w = max_w + pad * 2
    img = Image.new("RGB", (img_w, img_h), "white")
    draw = ImageDraw.Draw(img)
    y = pad
    for line in lines:
        if not line:
            y += line_h
            continue
        bbox = font.getbbox(line)
        tw = bbox[2] - bbox[0]
        if align == "center":
            x = pad + max(0, (max_w - tw) // 2)
        else:
            x = pad
        draw.text((x, y), line, font=font, fill=fill)
        y += line_h

    # 裁掉底部空白
    img = img.crop((0, 0, img_w, min(img_h, y + pad)))
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    draw_w = max_width_pt
    draw_h = img.size[1] / scale
    # ReportLab Image 接受文件路径或 BytesIO，不要包 ImageReader
    return RLImage(bio, width=draw_w, height=draw_h)


def _pdf_lifetime_fortune_pages(bazi_data: dict, lang: str, font_path, page_width_pt: float):
    """将一生流年运势表绘成多页图片 Flowable，供 PDF 附录。"""
    import io
    from reportlab.platypus import Image as RLImage
    from PIL import Image, ImageDraw, ImageFont

    from bazi_analysis import build_lifetime_fortune

    rows = build_lifetime_fortune(bazi_data, max_age=80, lang=lang)
    if not rows or not font_path:
        return []

    def trad(s: str) -> str:
        if lang != "zh_hant":
            return _pdf_fix_glyphs(s, font_path)
        try:
            from zh_convert import to_traditional

            return _pdf_fix_glyphs(to_traditional(s), font_path)
        except Exception:
            return _pdf_fix_glyphs(s, font_path)

    title = trad("一生流年运势分析")
    headers = [trad(x) for x in ("西元", "实岁", "大运", "流年", "合化", "运势", "重要提示")]
    hint = trad("红线越长代表该年运势越佳；重要提示按年龄阶段择要，必要时可并列两条。")

    scale = 2
    # 列宽比例（与网页接近，提示略窄）
    ratios = [0.09, 0.06, 0.08, 0.08, 0.12, 0.16, 0.41]
    max_w = int(page_width_pt * scale)
    col_w = [int(max_w * r) for r in ratios]
    # 修正舍入
    col_w[-1] += max_w - sum(col_w)

    font_title = ImageFont.truetype(str(font_path), 15 * scale)
    font_h = ImageFont.truetype(str(font_path), 9 * scale)
    font_c = ImageFont.truetype(str(font_path), 8 * scale)
    font_tip = ImageFont.truetype(str(font_path), 7 * scale)

    row_h = int(22 * scale)
    title_h = int(28 * scale)
    head_h = int(24 * scale)
    hint_h = int(20 * scale)
    pad = int(6 * scale)

    max_score = max(r["score"] for r in rows) or 100
    min_score = min(r["score"] for r in rows) or 0
    span = max(max_score - min_score, 1)

    def wrap_tip(text: str, max_px: int) -> list:
        t = _pdf_fix_glyphs((text or "—").replace("\n", " "), font_path)
        lines, cur, cw = [], "", 0
        for ch in t:
            box = font_tip.getbbox(ch)
            w = max(1, box[2] - box[0])
            if cur and cw + w > max_px - 4:
                lines.append(cur)
                cur, cw = ch, w
            else:
                cur += ch
                cw += w
        if cur:
            lines.append(cur)
        return lines[:2] or ["—"]

    # 按像素高度分页，避免单页过高
    max_body_px = int(600 * scale)
    chunks: list = []
    cur_chunk: list = []
    cur_h = 0
    for r in rows:
        tips = wrap_tip(r.get("tip") or "—", col_w[6])
        rh = max(row_h, int(9 * scale * 1.35 * len(tips) + 8 * scale))
        if cur_chunk and cur_h + rh > max_body_px:
            chunks.append(cur_chunk)
            cur_chunk, cur_h = [], 0
        cur_chunk.append((r, tips, rh))
        cur_h += rh
    if cur_chunk:
        chunks.append(cur_chunk)

    pages = []
    for pi, chunk in enumerate(chunks):
        heights = [rh for _r, _t, rh in chunk]
        body_h = sum(heights)
        img_h = pad * 2 + (title_h if pi == 0 else int(18 * scale)) + head_h + body_h + (hint_h if pi == len(chunks) - 1 else 0)
        img = Image.new("RGB", (max_w + pad * 2, img_h), "white")
        draw = ImageDraw.Draw(img)
        x0, y = pad, pad

        if pi == 0:
            draw.text((x0, y), title + "：", font=font_title, fill="#8B4513")
            y += title_h
        else:
            draw.text((x0, y), f"{title}（续）", font=font_h, fill="#8B4513")
            y += int(18 * scale)

        draw.rectangle([x0, y, x0 + max_w, y + head_h], fill="#F5F5F5")
        cx = x0
        for hi, htxt in enumerate(headers):
            draw.text((cx + 3, y + 4), htxt, font=font_h, fill="#333333")
            cx += col_w[hi]
        y += head_h

        for i, (r, tip_lines, rh) in enumerate(chunk):
            if i % 2 == 1:
                draw.rectangle([x0, y, x0 + max_w, y + rh], fill="#FAFAFA")
            draw.line([x0, y + rh, x0 + max_w, y + rh], fill="#EEEEEE", width=1)
            cells = [
                str(r["year"]),
                str(r["age"]),
                r.get("dayun") or "—",
                r.get("liunian") or "—",
                (r.get("interaction") or "—")[:18],
            ]
            cx = x0
            for ci, val in enumerate(cells):
                draw.text((cx + 3, y + 4), val, font=font_c, fill="#222222")
                cx += col_w[ci]
            norm = (r["score"] - min_score) / span
            bar_max = col_w[5] - 8
            bar_w = int(8 + norm * (bar_max - 8))
            bar_color = (194, 24, 91) if r["score"] >= 55 else (171, 71, 188)
            if r["score"] <= 35:
                bar_color = (120, 144, 156)
            by = y + rh // 2 - 4
            draw.rectangle([cx + 4, by, cx + 4 + bar_w, by + 8], fill=bar_color)
            cx += col_w[5]
            ty = y + 3
            for line in tip_lines:
                draw.text((cx + 3, ty), line, font=font_tip, fill="#4E342E")
                ty += int(9 * scale * 1.3)
            y += rh

        if pi == len(chunks) - 1:
            draw.text((x0, y + 4), hint, font=font_tip, fill="#888888")

        bio = io.BytesIO()
        img.save(bio, format="PNG")
        bio.seek(0)
        draw_w = page_width_pt
        draw_h = img.size[1] / scale
        max_h = 700
        if draw_h > max_h:
            ratio = max_h / draw_h
            draw_w = draw_w * ratio
            draw_h = max_h
        pages.append(RLImage(bio, width=draw_w, height=draw_h))
    return pages


def generate_pdf_report(report_content, birth_info, bazi_data, *, include_liunian: bool = False, lang: str = "zh"):
    """生成多页中文 PDF（嵌入 CJK 字体，避免黑方块）。金/钻可含流年报告；银卡不含。"""
    import io
    import re
    from xml.sax.saxutils import escape

    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

    from report_generator import ReportGenerator

    def T(s: str) -> str:
        if lang == "zh_hant":
            try:
                from zh_convert import to_traditional

                return to_traditional(s)
            except Exception:
                return s
        return s

    font_body, font_head = _resolve_pdf_cjk_font()
    cjk_path = _cjk_font_file()
    # 有可用 TTF 时用 PIL 出字（ReportLab 子集化 CJK 易出黑方块）
    use_pil = cjk_path is not None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title=T("六西格玛命理 · 八字报告"),
        author=str((birth_info or {}).get("name") or "Sigma Fate"),
    )

    styles = getSampleStyleSheet()
    # 英文字母副标题仍可用内置字体
    style_cover_sub = ParagraphStyle(
        "CoverSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor="#455A64",
    )
    # 下面样式仅作回退；中文主路径走 PIL
    style_h1 = ParagraphStyle(
        "H1CN", parent=styles["Normal"], fontName=font_head, fontSize=18, leading=26,
        spaceBefore=6, spaceAfter=10, alignment=TA_LEFT, textColor="#0B1F33",
    )
    style_h2 = ParagraphStyle(
        "H2CN", parent=styles["Normal"], fontName=font_head, fontSize=13, leading=20,
        spaceBefore=12, spaceAfter=6, textColor="#1565C0",
    )
    style_body = ParagraphStyle(
        "BodyCN", parent=styles["Normal"], fontName=font_body, fontSize=10.5, leading=17,
        alignment=TA_JUSTIFY, spaceAfter=8,
    )
    style_meta = ParagraphStyle(
        "MetaCN", parent=styles["Normal"], fontName=font_body, fontSize=11, leading=18,
        alignment=TA_CENTER, spaceAfter=6,
    )
    style_toc = ParagraphStyle(
        "TocCN", parent=styles["Normal"], fontName=font_body, fontSize=11, leading=18,
        alignment=TA_LEFT, leftIndent=12, spaceAfter=4,
    )
    style_bullet = ParagraphStyle(
        "BulletCN", parent=styles["Normal"], fontName=font_body, fontSize=10.5, leading=17,
        leftIndent=14, spaceAfter=4,
    )

    content_width = A4[0] - 3.6 * cm

    def _pdf_safe(text: str) -> str:
        if not text:
            return ""
        return (
            str(text)
            .replace("⚠️", "")
            .replace("⚠", "")
            .replace("★", "*")
            .replace("☆", "*")
            .replace("●", "-")
            .replace("○", "-")
        )

    def P(text: str, style=style_body, bold: bool = False):
        raw = T(_pdf_safe(str(text or "").strip()))
        if not raw:
            return None
        if use_pil:
            size = 11
            fill = "#222222"
            align = "left"
            width = content_width
            if style is style_h1:
                size, fill = 18, "#0B1F33"
            elif style is style_h2:
                size, fill = 13, "#1565C0"
            elif style is style_meta:
                size, fill, align = 12, "#333333", "center"
            elif style is style_toc:
                size = 11
            elif style is style_bullet:
                size = 10
                raw = "  " + raw
            if bold and size < 16:
                size += 1
            img = _pdf_text_image(
                raw,
                font_path=cjk_path,
                font_size=size,
                max_width_pt=float(width),
                fill=fill,
                align=align,
            )
            if img is not None:
                return img
        # 回退 Paragraph（可能黑方块，仅无字体失败时）
        t = escape(raw).replace("\n", "<br/>")
        return Paragraph(t, style)

    story = []
    name = str((birth_info or {}).get("name") or "")
    gender = str((birth_info or {}).get("gender") or (bazi_data or {}).get("gender") or "")
    birth = str((birth_info or {}).get("birth_date") or "")

    story.append(Spacer(1, 1.8 * cm))
    cover = P("六西格玛命理 · 八字命理报告", style_h1)
    if cover is not None:
        # 封面标题居中：重绘
        if use_pil:
            cover = _pdf_text_image(
                T(_pdf_safe("六西格玛命理 · 八字命理报告")),
                font_path=cjk_path,
                font_size=22,
                max_width_pt=float(content_width),
                fill="#0B1F33",
                align="center",
            )
        story.append(cover)
    story.append(Paragraph(escape("Sigma Fate BaZi Report"), style_cover_sub))
    story.append(Spacer(1, 0.5 * cm))
    if name:
        story.append(P(f"姓名：{name}", style_meta, bold=True))
    if gender:
        story.append(P(f"性别：{gender}", style_meta))
    if birth:
        story.append(P(f"出生：{birth}", style_meta))
    dm = (bazi_data or {}).get("day_master") if isinstance(bazi_data, dict) else ""
    if dm:
        story.append(P(f"日主：{dm}", style_meta, bold=True))
    story.append(Spacer(1, 0.6 * cm))
    story.append(P("本报告仅供参考，请理性看待。", style_meta))

    # 目录
    toc_items = []
    legacy_ln9 = ReportGenerator.is_legacy_liunian_page9(report_content)
    if isinstance(report_content, dict):
        for i in range(1, 11):
            if i == 10 and not include_liunian:
                continue
            if i == 9 and legacy_ln9 and not include_liunian:
                continue
            pk = f"page{i}"
            if pk not in report_content:
                continue
            is_ln = (i == 10) or (i == 9 and legacy_ln9)
            page = ReportGenerator.sanitize_page_for_display(
                report_content[pk],
                T("流年报告") if is_ln else T(f"第{i}页"),
            )
            toc_items.append(str(page.get("title") or (T("流年报告") if is_ln else T(f"第{i}页"))))
    if toc_items:
        story.append(Spacer(1, 0.8 * cm))
        story.append(P("目录", style_h2))
        for idx, tit in enumerate(toc_items, 1):
            story.append(P(f"{idx}. {tit}", style_toc))

    story.append(PageBreak())

    def add_page_block(page: dict, fallback_title: str, *, page_index: int = 0):
        page = ReportGenerator.sanitize_page_for_display(page, fallback_title)
        title = page.get("title") or fallback_title
        story.append(P(str(title), style_h1))
        story.append(Spacer(1, 0.15 * cm))

        if page_index == 1 and isinstance(bazi_data, dict) and bazi_data.get("day_master"):
            try:
                from bazi_analysis import analyze_personality

                pers = analyze_personality(bazi_data, lang)
                story.append(P(str(pers.get("title") or "性格分析"), style_h2))
                p = P(pers.get("body") or "", style_body)
                if p:
                    story.append(p)
                story.append(Spacer(1, 0.12 * cm))
            except Exception:
                pass

        pro = page.get("professional")
        if isinstance(pro, list) and pro:
            story.append(P("专业解读", style_h2))
            for para in pro:
                p = P(para, style_body)
                if p:
                    story.append(p)
        cm_block = page.get("current_month") if isinstance(page.get("current_month"), dict) else None
        if cm_block and any(cm_block.get(k) for k in ("overview", "career", "wealth", "relationship", "health", "action")):
            story.append(P("当月注意（事业 · 财运 · 感情 · 健康）", style_h2))
            if cm_block.get("label"):
                p = P(str(cm_block["label"]), style_body)
                if p:
                    story.append(p)
            for lab, key in (
                ("总览", "overview"),
                ("事业", "career"),
                ("财运", "wealth"),
                ("感情", "relationship"),
                ("健康", "health"),
                ("行动", "action"),
            ):
                if cm_block.get(key):
                    pp = P(f"{lab}：{cm_block[key]}", style_body)
                    if pp:
                        story.append(pp)
        quarters = page.get("quarters") if isinstance(page.get("quarters"), list) else []
        if quarters:
            story.append(P("四季流年预测", style_h2))
            for q in quarters:
                if not isinstance(q, dict):
                    continue
                head = f"{q.get('name', '')}（{q.get('branch', '')} · {q.get('months', '')}）"
                p = P(head, style_h2)
                if p:
                    story.append(p)
                for lab, key in (("局势", "outlook"), ("关键月", "focus_months"), ("建议", "advice")):
                    if q.get(key):
                        pp = P(f"{lab}：{q[key]}", style_body)
                        if pp:
                            story.append(pp)
        plain = page.get("plain") if isinstance(page.get("plain"), dict) else None
        if plain and (plain.get("summary") or plain.get("points") or plain.get("detail") or plain.get("quarters_plain")):
            story.append(P("白话说明", style_h2))
            if plain.get("summary"):
                p = P(f"一句话：{plain['summary']}", style_body)
                if p:
                    story.append(p)
            pts = plain.get("points") or []
            if pts:
                story.append(P("怎么做：", style_body))
                for i, pt in enumerate(pts, 1):
                    p = P(f"{i}. {pt}", style_bullet)
                    if p:
                        story.append(p)
            if plain.get("detail"):
                p = P(plain["detail"], style_body)
                if p:
                    story.append(p)
            for q in plain.get("quarters_plain") or []:
                if not isinstance(q, dict):
                    continue
                p = P(f"{q.get('name', '')}：{q.get('summary', '')}", style_body, bold=True)
                if p:
                    story.append(p)
                for j, tip in enumerate(q.get("tips") or [], 1):
                    pp = P(f"{j}. {tip}", style_bullet)
                    if pp:
                        story.append(pp)
        elif page.get("content"):
            content = re.sub(r"[#*`]+", "", str(page.get("content") or ""))
            if not ReportGenerator._looks_like_json_blob(content):
                for block in re.split(r"\n\s*\n+", content):
                    p = P(block, style_body)
                    if p:
                        story.append(p)
        story.append(PageBreak())

    if isinstance(report_content, dict):
        for i in range(1, 11):
            if i == 10 and not include_liunian:
                continue
            if i == 9 and legacy_ln9 and not include_liunian:
                continue
            pk = f"page{i}"
            if pk not in report_content:
                continue
            page = report_content[pk]
            if not isinstance(page, dict):
                page = {"content": str(page), "title": T(f"第{i}页")}
            is_ln = (i == 10) or (i == 9 and legacy_ln9)
            fallback = T("流年报告") if is_ln else T(f"第{i}页")
            add_page_block(page, fallback, page_index=i)
    else:
        story.append(P("暂无报告内容。", style_body))

    # 附录：一生流年运势分析（有命盘即可；金/钻流年 PDF 尤为需要）
    if isinstance(bazi_data, dict) and bazi_data.get("day_master") and cjk_path:
        try:
            fortune_pages = _pdf_lifetime_fortune_pages(
                bazi_data, lang, cjk_path, float(content_width)
            )
            if fortune_pages:
                if story and not isinstance(story[-1], PageBreak):
                    story.append(PageBreak())
                for i, img in enumerate(fortune_pages):
                    story.append(img)
                    if i < len(fortune_pages) - 1:
                        story.append(PageBreak())
        except Exception:
            pass

    if story and isinstance(story[-1], PageBreak):
        story.pop()

    doc.build(story)
    buffer.seek(0)
    return buffer

def pdf_filename(birth_info) -> str:
    """下载文件名：BaZi_姓名_日期.pdf（汉字音节首字母大写）。"""
    import re
    from datetime import datetime

    raw = str((birth_info or {}).get("name") or "user").strip()
    safe = re.sub(r'[\\/:*?"<>|\s]+', "_", raw).strip("_") or "user"
    return f"BaZi_{safe[:40]}_{datetime.now():%Y%m%d}.pdf"


def hehun_pdf_filename(name_a: str = "", name_b: str = "") -> str:
    """合婚 PDF 文件名：HeHun_甲_乙_日期.pdf。"""
    import re
    from datetime import datetime

    def _safe(n: str) -> str:
        s = re.sub(r'[\\/:*?"<>|\s]+', "_", str(n or "").strip()).strip("_")
        return (s[:20] or "user")

    return f"HeHun_{_safe(name_a)}_{_safe(name_b)}_{datetime.now():%Y%m%d}.pdf"


def _pillar_line_pdf(bazi: dict) -> str:
    parts = []
    for name in ("年柱", "月柱", "日柱", "时柱"):
        p = ((bazi or {}).get("pillars") or {}).get(name) or {}
        g, z = p.get("gan") or "—", p.get("zhi") or "—"
        parts.append(f"{g}{z}")
    return " ".join(parts)


def _pdf_hehun_dim_table(dimensions: list, *, font_path, page_width_pt: float, lang: str = "zh"):
    """
    合婚维度分析表（与网页版一致）：
    合婚维度分析 | 分 | 进度条 | 要点（术语+白话同格，不拆专业/白话）。
    过长时拆成多张图（每页带表头）。
    返回 Flowable 列表。
    """
    import io
    from reportlab.platypus import Image as RLImage
    from PIL import Image, ImageDraw, ImageFont

    if not dimensions or not font_path:
        return []

    en = lang == "en"

    def trad(s: str) -> str:
        if lang != "zh_hant":
            return s
        try:
            from zh_convert import to_traditional

            return to_traditional(s)
        except Exception:
            return s

    scale = 2
    font = ImageFont.truetype(str(font_path), 10 * scale)
    font_sm = ImageFont.truetype(str(font_path), 9 * scale)
    font_b = ImageFont.truetype(str(font_path), 10 * scale)
    font_h = ImageFont.truetype(str(font_path), 10 * scale)
    w = int(page_width_pt * scale)
    # 列宽比例贴近网页：18% / 10% / 22% / 50%
    c_label, c_score, c_bar, c_tip = 0.16, 0.08, 0.18, 0.58
    pad = int(6 * scale)
    header_h = int(26 * scale)
    line_h = int(14 * scale)
    tip_gap = int(3 * scale)
    cell_pad_y = int(6 * scale)
    max_chunk_h = int(620 * scale)  # 约一页可用高度

    def char_w(fnt, ch: str) -> int:
        box = fnt.getbbox(ch)
        return max(1, box[2] - box[0])

    def wrap_text(text: str, fnt, max_w: int) -> list:
        raw = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not raw:
            return []
        lines = []
        for para in raw.split("\n"):
            if not para:
                lines.append("")
                continue
            cur, cur_w = "", 0
            for ch in para:
                cw = char_w(fnt, ch)
                if cur and cur_w + cw > max_w:
                    lines.append(cur)
                    cur, cur_w = ch, cw
                else:
                    cur += ch
                    cur_w += cw
            lines.append(cur)
        return lines

    tip_max_w = int(w * c_tip) - pad * 2
    label_max_w = int(w * c_label) - pad * 2

    # 预计算每行高度与折行
    prepared = []
    for d in dimensions:
        lab = trad(str(d.get("label") or d.get("key") or ""))
        if en:
            lab = str(d.get("label") or d.get("key") or "")
        score = int(d.get("score") or 0)
        jargon = trad(str(d.get("jargon") or "").strip()) if not en else str(d.get("jargon") or "").strip()
        plain = trad(str(d.get("plain") or "").strip()) if not en else str(d.get("plain") or "").strip()
        lab = _pdf_fix_glyphs(lab, font_path)
        jargon = _pdf_fix_glyphs(jargon, font_path)
        plain = _pdf_fix_glyphs(plain, font_path)
        lab_lines = wrap_text(lab, font_b, label_max_w) or [lab]
        j_lines = wrap_text(jargon, font_sm, tip_max_w)
        p_lines = wrap_text(plain, font_sm, tip_max_w)
        tip_lines_h = 0
        if j_lines:
            tip_lines_h += line_h * len(j_lines)
        if j_lines and p_lines:
            tip_lines_h += tip_gap
        if p_lines:
            tip_lines_h += line_h * len(p_lines)
        left_h = line_h * max(1, len(lab_lines))
        row_h = max(int(32 * scale), left_h, tip_lines_h) + cell_pad_y * 2
        prepared.append(
            {
                "lab_lines": lab_lines,
                "score": score,
                "j_lines": j_lines,
                "p_lines": p_lines,
                "row_h": row_h,
            }
        )

    h_dim = "Match dimensions" if en else trad("合婚维度分析")
    h_pts = "Pts" if en else trad("分")
    h_tip = "Notes" if en else trad("要点")

    def render_chunk(rows: list, *, show_header: bool = True):
        body_h = sum(r["row_h"] for r in rows)
        h = pad + (header_h if show_header else 0) + body_h + pad
        img = Image.new("RGB", (w, h), "#FFFFFF")
        draw = ImageDraw.Draw(img)
        y = pad
        if show_header:
            draw.rectangle([0, y, w, y + header_h], fill="#F5F5F5")
            headers = [
                (h_dim, 0.0, "left"),
                (h_pts, c_label, "center"),
                ("", c_label + c_score, "left"),
                (h_tip, c_label + c_score + c_bar, "left"),
            ]
            for text, x0, align in headers:
                if not text:
                    continue
                tx = int(w * x0) + pad
                if align == "center":
                    bb = font_h.getbbox(text)
                    tw = bb[2] - bb[0]
                    col_w = int(w * c_score)
                    tx = int(w * x0) + max(pad, (col_w - tw) // 2)
                draw.text((tx, y + int(7 * scale)), text, font=font_h, fill="#424242")
            y += header_h

        for i, r in enumerate(rows):
            rh = r["row_h"]
            if i % 2 == 1:
                draw.rectangle([0, y, w, y + rh], fill="#FAFAFA")
            # 底部分隔线
            draw.line([(0, y + rh - 1), (w, y + rh - 1)], fill="#EEEEEE", width=1)

            # 维度名
            ly = y + cell_pad_y
            for ln in r["lab_lines"]:
                draw.text((pad, ly), ln, font=font_b, fill="#222222")
                ly += line_h

            # 分数（居中于分列）
            sc = str(r["score"])
            bb = font_b.getbbox(sc)
            tw = bb[2] - bb[0]
            col_x = int(w * c_label)
            col_w = int(w * c_score)
            sx = col_x + max(0, (col_w - tw) // 2)
            draw.text((sx, y + cell_pad_y), sc, font=font_b, fill="#C62828")

            # 进度条
            bar_x0 = int(w * (c_label + c_score)) + pad
            bar_x1 = int(w * (c_label + c_score + c_bar)) - pad
            bar_y0 = y + max(cell_pad_y, (rh - int(8 * scale)) // 2)
            bar_y1 = bar_y0 + int(8 * scale)
            draw.rounded_rectangle([bar_x0, bar_y0, bar_x1, bar_y1], radius=3, fill="#EEEEEE")
            fill_w = bar_x0 + int((bar_x1 - bar_x0) * max(0, min(100, r["score"])) / 100)
            if fill_w > bar_x0 + 2:
                draw.rounded_rectangle([bar_x0, bar_y0, fill_w, bar_y1], radius=3, fill="#C62828")

            # 要点：术语（深褐）+ 白话（灰），同格
            tip_x = int(w * (c_label + c_score + c_bar)) + pad
            ty = y + cell_pad_y
            for ln in r["j_lines"]:
                draw.text((tip_x, ty), ln, font=font_sm, fill="#4E342E")
                ty += line_h
            if r["j_lines"] and r["p_lines"]:
                ty += tip_gap
            for ln in r["p_lines"]:
                draw.text((tip_x, ty), ln, font=font_sm, fill="#555555")
                ty += line_h

            y += rh

        draw.rectangle([0, pad, w - 1, h - pad], outline="#E0E0E0")
        bio = io.BytesIO()
        img.save(bio, format="PNG")
        bio.seek(0)
        return RLImage(bio, width=page_width_pt, height=h / scale)

    # 按高度拆页
    chunks: list = []
    cur: list = []
    cur_h = header_h
    for row in prepared:
        need = row["row_h"]
        if cur and cur_h + need > max_chunk_h:
            chunks.append(cur)
            cur = [row]
            cur_h = header_h + need
        else:
            cur.append(row)
            cur_h += need
    if cur:
        chunks.append(cur)

    return [render_chunk(ch, show_header=True) for ch in chunks if ch]


def generate_hehun_pdf_report(
    result: dict,
    *,
    name_a: str,
    name_b: str,
    bazi_a: dict,
    bazi_b: dict,
    ai_deep: Optional[dict] = None,
    lang: str = "zh",
):
    """
    八字合婚独立 PDF：封面 + 契合总览（含合婚维度分析表，与网页一致）+（可选）AI 深批。
    版式对齐八字命理报告（ReportLab + PIL 中文）。
    """
    import io
    import re
    from xml.sax.saxutils import escape

    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

    from report_generator import ReportGenerator

    en = lang == "en"

    def T(s: str) -> str:
        if lang == "zh_hant":
            try:
                from zh_convert import to_traditional

                return to_traditional(s)
            except Exception:
                return s
        return s

    font_body, font_head = _resolve_pdf_cjk_font()
    cjk_path = _cjk_font_file()
    use_pil = cjk_path is not None

    buffer = io.BytesIO()
    cover_title = "Sigma Fate Marriage Match" if en else T("六西格玛命理 · 八字合婚报告")
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title=cover_title,
        author=f"{name_a or 'A'} & {name_b or 'B'}",
    )

    styles = getSampleStyleSheet()
    style_cover_sub = ParagraphStyle(
        "HehunCoverSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor="#455A64",
    )
    style_h1 = ParagraphStyle(
        "HehunH1", parent=styles["Normal"], fontName=font_head, fontSize=18, leading=26,
        spaceBefore=6, spaceAfter=10, alignment=TA_LEFT, textColor="#0B1F33",
    )
    style_h2 = ParagraphStyle(
        "HehunH2", parent=styles["Normal"], fontName=font_head, fontSize=13, leading=20,
        spaceBefore=12, spaceAfter=6, textColor="#1565C0",
    )
    style_body = ParagraphStyle(
        "HehunBody", parent=styles["Normal"], fontName=font_body, fontSize=10.5, leading=17,
        alignment=TA_JUSTIFY, spaceAfter=8,
    )
    style_meta = ParagraphStyle(
        "HehunMeta", parent=styles["Normal"], fontName=font_body, fontSize=11, leading=18,
        alignment=TA_CENTER, spaceAfter=6,
    )
    style_toc = ParagraphStyle(
        "HehunToc", parent=styles["Normal"], fontName=font_body, fontSize=11, leading=18,
        alignment=TA_LEFT, leftIndent=12, spaceAfter=4,
    )
    style_bullet = ParagraphStyle(
        "HehunBullet", parent=styles["Normal"], fontName=font_body, fontSize=10.5, leading=17,
        leftIndent=14, spaceAfter=4,
    )
    style_score = ParagraphStyle(
        "HehunScore", parent=styles["Normal"], fontName=font_head, fontSize=28, leading=34,
        alignment=TA_CENTER, textColor="#C62828", spaceAfter=8,
    )

    content_width = A4[0] - 3.6 * cm

    def _pdf_safe(text: str) -> str:
        if not text:
            return ""
        return (
            str(text)
            .replace("⚠️", "")
            .replace("⚠", "")
            .replace("★", "*")
            .replace("☆", "*")
            .replace("●", "-")
            .replace("○", "-")
        )

    def P(text: str, style=style_body, bold: bool = False):
        raw = _pdf_safe(str(text or "").strip())
        if not en:
            raw = T(raw)
        if not raw:
            return None
        if use_pil:
            size = 11
            fill = "#222222"
            align = "left"
            if style is style_h1:
                size, fill = 18, "#0B1F33"
            elif style is style_h2:
                size, fill = 13, "#1565C0"
            elif style is style_meta:
                size, fill, align = 12, "#333333", "center"
            elif style is style_toc:
                size = 11
            elif style is style_bullet:
                size = 10
                raw = "  " + raw
            elif style is style_score:
                size, fill, align = 32, "#C62828", "center"
            if bold and size < 16:
                size += 1
            img = _pdf_text_image(
                raw,
                font_path=cjk_path,
                font_size=size,
                max_width_pt=float(content_width),
                fill=fill,
                align=align,
            )
            if img is not None:
                return img
        t = escape(raw).replace("\n", "<br/>")
        return Paragraph(t, style)

    result = result or {}
    total = int(result.get("total") or 0)
    headline = str(result.get("headline") or "")
    summary = str(result.get("summary") or "")
    dims = list(result.get("dimensions") or [])

    L = {
        "brand": "六西格玛命理 · 八字合婚报告" if not en else "Sigma Fate · Marriage Match Report",
        "sub": "Sigma Fate Marriage Match Report",
        "person_a": "甲方" if not en else "Person A",
        "person_b": "乙方" if not en else "Person B",
        "dm": "日主" if not en else "Day Master",
        "pillars": "四柱" if not en else "Pillars",
        "score": "契合度" if not en else "Compatibility",
        "disc": "本报告仅供参考，请理性看待，非婚姻决定依据。" if not en else "For reflection only — not a marital decision.",
        "toc": "目录" if not en else "Contents",
        "overview": "契合总览" if not en else "Match Overview",
        "dim_table": "合婚维度分析" if not en else "Match dimensions",
        "pro": "专业解读" if not en else "Professional",
        "plain": "白话说明" if not en else "In plain words",
        "one_line": "一句话" if not en else "In one line",
        "how": "怎么做" if not en else "What to do",
        "ai_pattern": "缘分格局" if not en else "Bond Pattern",
        "ai_resolve": "相处化解" if not en else "Relating & Repair",
        "ai_sec": "AI 深批" if not en else "AI Deep Read",
        "gender": "性别" if not en else "Gender",
        "name": "姓名" if not en else "Name",
    }

    story = []

    # ---------- 封面 ----------
    story.append(Spacer(1, 1.6 * cm))
    if use_pil:
        brand_txt = L["brand"] if en else T(_pdf_safe(L["brand"]))
        cover = _pdf_text_image(
            brand_txt,
            font_path=cjk_path,
            font_size=22,
            max_width_pt=float(content_width),
            fill="#0B1F33",
            align="center",
        )
        if cover:
            story.append(cover)
    else:
        c = P(L["brand"], style_meta, bold=True)
        if c:
            story.append(c)
    story.append(Paragraph(escape(L["sub"] if not en else "BaZi Compatibility Analysis"), style_cover_sub))
    story.append(Spacer(1, 0.45 * cm))

    na = name_a or L["person_a"]
    nb = name_b or L["person_b"]
    ga = str((bazi_a or {}).get("gender") or "")
    gb = str((bazi_b or {}).get("gender") or "")
    dma = str((bazi_a or {}).get("day_master") or "—")
    dmb = str((bazi_b or {}).get("day_master") or "—")
    pa = _pillar_line_pdf(bazi_a)
    pb = _pillar_line_pdf(bazi_b)
    if lang == "zh_hant":
        pa, pb = T(pa), T(pb)

    story.append(P(f"{L['person_a']} · {na}", style_meta, bold=True))
    if ga:
        story.append(P(f"{L['gender']}：{ga}　{L['dm']}：{dma}", style_meta))
    else:
        story.append(P(f"{L['dm']}：{dma}", style_meta))
    story.append(P(f"{L['pillars']}：{pa}", style_meta))
    story.append(Spacer(1, 0.25 * cm))
    story.append(P(f"{L['person_b']} · {nb}", style_meta, bold=True))
    if gb:
        story.append(P(f"{L['gender']}：{gb}　{L['dm']}：{dmb}", style_meta))
    else:
        story.append(P(f"{L['dm']}：{dmb}", style_meta))
    story.append(P(f"{L['pillars']}：{pb}", style_meta))

    story.append(Spacer(1, 0.7 * cm))
    story.append(P(L["score"], style_meta))
    story.append(P(str(total), style_score))
    if headline:
        story.append(P(headline, style_meta, bold=True))
    story.append(Spacer(1, 0.5 * cm))
    story.append(P(L["disc"], style_meta))

    # 目录
    toc = [L["overview"], L["dim_table"]]
    ai_chapters = []
    if isinstance(ai_deep, dict):
        for key, title in (("pattern", L["ai_pattern"]), ("resolve", L["ai_resolve"])):
            sec = ai_deep.get(key)
            if isinstance(sec, dict) and (
                sec.get("professional") or sec.get("plain") or sec.get("content")
            ):
                ai_chapters.append((title, sec))
            elif isinstance(sec, str) and sec.strip():
                ai_chapters.append((title, {"content": sec.strip(), "title": title}))
        # 旧四段
        if not ai_chapters:
            for key, title in (
                ("pattern", L["ai_pattern"]),
                ("dynamics", "相处模式" if not en else "Dynamics"),
                ("nurture", "宜经营处" if not en else "What to nurture"),
                ("caution", "需留意处" if not en else "What to watch"),
            ):
                body = ai_deep.get(key)
                if isinstance(body, str) and body.strip():
                    ai_chapters.append((title, {"content": body.strip(), "title": title}))
        if ai_chapters:
            toc.append(L["ai_sec"])
            for tit, _ in ai_chapters:
                toc.append(f"  · {tit}")

    story.append(Spacer(1, 0.7 * cm))
    story.append(P(L["toc"], style_h2))
    for idx, tit in enumerate([t for t in toc if not t.startswith("  ")], 1):
        story.append(P(f"{idx}. {tit}", style_toc))
    for tit in toc:
        if tit.startswith("  "):
            story.append(P(tit.strip(), style_toc))

    story.append(PageBreak())

    # ---------- 契合总览 ----------
    story.append(P(L["overview"], style_h1))
    story.append(Spacer(1, 0.1 * cm))
    story.append(P(f"{L['score']}：{total}", style_h2))
    if headline:
        p = P(headline, style_body, bold=True)
        if p:
            story.append(p)
    if summary:
        p = P(summary, style_body)
        if p:
            story.append(p)
    story.append(Spacer(1, 0.25 * cm))
    story.append(P(L["dim_table"], style_h2))
    story.append(Spacer(1, 0.12 * cm))
    if cjk_path and dims:
        tables = _pdf_hehun_dim_table(
            dims, font_path=cjk_path, page_width_pt=float(content_width), lang=lang
        )
        for i, table in enumerate(tables or []):
            if i > 0:
                story.append(PageBreak())
                story.append(P(L["dim_table"], style_h2))
                story.append(Spacer(1, 0.12 * cm))
            story.append(table)
    else:
        for d in dims:
            tip = f"{d.get('jargon') or ''} {d.get('plain') or ''}".strip()
            story.append(
                P(f"{d.get('label', '')}  {d.get('score', 0)}  {tip}", style_body)
            )

    def _para_gap():
        """段落之间空一行。"""
        story.append(Spacer(1, 0.28 * cm))

    def _append_body(text: str, *, bullet: bool = False):
        p = P(text, style_bullet if bullet else style_body)
        if p:
            story.append(p)
            _para_gap()

    # ---------- AI 深批：章内不分页，隔行衔接 ----------
    if ai_chapters:
        story.append(PageBreak())

    def add_ai_chapter(page: dict, fallback_title: str):
        title = str(page.get("title") or fallback_title)
        pro = page.get("professional")
        if isinstance(pro, str) and pro.strip():
            pro = ReportGenerator._split_paragraphs(pro) or [pro.strip()]
        elif isinstance(pro, list):
            pro = [str(x).strip() for x in pro if str(x).strip()]
        else:
            pro = []
        if not pro and page.get("content"):
            content = ReportGenerator._strip_json_artifacts(str(page.get("content") or ""))
            if content and not ReportGenerator._looks_like_json_blob(content):
                pro = ReportGenerator._split_paragraphs(content) or [content]

        plain_raw = page.get("plain")
        if isinstance(plain_raw, str) and plain_raw.strip():
            plain = {"summary": "", "points": [], "detail": plain_raw.strip()}
        elif isinstance(plain_raw, dict):
            plain = plain_raw
        else:
            plain = {}
        # 兼容中文键
        summary = str(
            plain.get("summary") or plain.get("一句话") or plain.get("总结") or ""
        ).strip()
        detail = str(
            plain.get("detail") or plain.get("说明") or plain.get("解释") or ""
        ).strip()
        pts = plain.get("points") or plain.get("建议") or plain.get("怎么做") or []
        if isinstance(pts, str):
            pts = [p.strip() for p in re.split(r"[；;\n]+", pts) if p.strip()]
        else:
            pts = [str(p).strip() for p in pts if str(p).strip()]

        story.append(P(title, style_h1))
        _para_gap()
        if pro:
            story.append(P(L["pro"], style_h2))
            for para in pro:
                if "不完整" in str(para) and (
                    "重新生成" in str(para) or "regenerate" in str(para).lower()
                ):
                    continue
                _append_body(para)
        # 白话说明：只要有任一块就出标题（与屏幕/八字报告一致）
        if summary or pts or detail:
            story.append(P(L["plain"], style_h2))
            if summary:
                _append_body(f"{L['one_line']}：{summary}")
            if pts:
                _append_body(f"{L['how']}：")
                for i, pt in enumerate(pts, 1):
                    _append_body(f"{i}. {pt}", bullet=True)
            if detail:
                _append_body(detail)
        elif not pro and page.get("content"):
            content = re.sub(r"[#*`]+", "", str(page.get("content") or ""))
            if not ReportGenerator._looks_like_json_blob(content):
                story.append(P(L["plain"], style_h2))
                for block in re.split(r"\n\s*\n+", content):
                    if block.strip():
                        _append_body(block.strip())
        # 章与章之间隔行，不分页
        story.append(Spacer(1, 0.45 * cm))

    if ai_chapters:
        story.append(P(L["ai_sec"], style_h1))
        _para_gap()
        _append_body(
            "以下为 AI 深批，理性参考，勿作宿命断言。"
            if not en
            else "AI deep read for reflection — not destiny."
        )
        for tit, sec in ai_chapters:
            page = dict(sec) if isinstance(sec, dict) else {"content": str(sec)}
            page["title"] = tit
            add_ai_chapter(page, tit)

    if story and isinstance(story[-1], PageBreak):
        story.pop()

    doc.build(story)
    buffer.seek(0)
    return buffer

