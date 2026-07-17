"""
八字合婚：本地结构化合婚分析（分数 + 五维 + 术语/白话）。
不调用 API；AI 深批由 report_generator 另做。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from bazi_analysis import (
    BRANCH_CHONG,
    BRANCH_HAI,
    BRANCH_HE,
    KE,
    SELF_XING,
    SHENG,
    WUXING_MAP,
    XING_GROUPS,
    estimate_day_strength,
    shishen_of,
)
from zh_convert import to_traditional

DIM_KEYS = ("day_master", "spouse_palace", "wuxing", "shishen", "stability")

DIM_LABELS_ZH = {
    "day_master": "日主关系",
    "spouse_palace": "夫妻宫",
    "wuxing": "五行补益",
    "shishen": "十神意象",
    "stability": "整体稳定",
}
DIM_LABELS_EN = {
    "day_master": "Day Master Bond",
    "spouse_palace": "Spouse Palace",
    "wuxing": "Five-Element Support",
    "shishen": "Ten-God Imagery",
    "stability": "Overall Stability",
}


def _maybe_trad(text: str, lang: str) -> str:
    if lang == "zh_hant" and text:
        try:
            return to_traditional(text)
        except Exception:
            return text
    return text


def _clamp(n: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, n))


def _pillar(bazi: dict, name: str) -> dict:
    return (bazi.get("pillars") or {}).get(name) or {}


def _dm_relation(dm_a: str, dm_b: str) -> Tuple[str, float]:
    """返回关系标签与基础分贡献。"""
    wa, wb = WUXING_MAP.get(dm_a, ""), WUXING_MAP.get(dm_b, "")
    if not wa or not wb:
        return ("unknown", 50.0)
    if wa == wb:
        return ("same", 72.0)
    if SHENG.get(wa) == wb:
        return ("a_sheng_b", 78.0)  # A 生 B：A 付出偏多
    if SHENG.get(wb) == wa:
        return ("b_sheng_a", 78.0)
    if KE.get(wa) == wb:
        return ("a_ke_b", 48.0)
    if KE.get(wb) == wa:
        return ("b_ke_a", 48.0)
    return ("other", 55.0)


def _branch_pair_flags(za: str, zb: str) -> Dict[str, bool]:
    pair = frozenset([za, zb])
    he = pair in BRANCH_HE
    chong = pair in BRANCH_CHONG
    hai = pair in BRANCH_HAI
    xing = False
    if za and zb:
        if za == zb and za in SELF_XING:
            xing = True
        else:
            for g in XING_GROUPS:
                if za in g and zb in g and za != zb:
                    xing = True
                    break
    return {"he": he, "chong": chong, "hai": hai, "xing": xing}


def _score_day_master(a: dict, b: dict, lang: str) -> dict:
    dm_a, dm_b = a.get("day_master") or "", b.get("day_master") or ""
    rel, base = _dm_relation(dm_a, dm_b)
    # 阴阳异性略加分（正财正官象更稳）
    yang = {"甲", "丙", "戊", "庚", "壬"}
    if (dm_a in yang) != (dm_b in yang):
        base += 6
    else:
        base -= 2
    score = int(round(_clamp(base)))

    if lang == "en":
        jargon_map = {
            "same": f"Same element Day Masters ({dm_a}/{dm_b}): peer energy.",
            "a_sheng_b": f"{dm_a} generates {dm_b}: A tends to give more.",
            "b_sheng_a": f"{dm_b} generates {dm_a}: B tends to give more.",
            "a_ke_b": f"{dm_a} controls {dm_b}: A may lead/pressure.",
            "b_ke_a": f"{dm_b} controls {dm_a}: B may lead/pressure.",
            "other": f"Day Masters {dm_a}/{dm_b}: mixed dynamic.",
            "unknown": "Day Master relation unclear.",
        }
        plain_map = {
            "same": "Similar tempo — easy rapport, watch stubborn sameness.",
            "a_sheng_b": "A often supports B; keep giving reciprocal.",
            "b_sheng_a": "B often supports A; keep giving reciprocal.",
            "a_ke_b": "A may steer; soften tone to avoid friction.",
            "b_ke_a": "B may steer; soften tone to avoid friction.",
            "other": "Complement needs conscious balance.",
            "unknown": "Need clearer birth data.",
        }
        return {
            "key": "day_master",
            "score": score,
            "jargon": jargon_map.get(rel, jargon_map["other"]),
            "plain": plain_map.get(rel, plain_map["other"]),
            "meta": {"relation": rel, "dm_a": dm_a, "dm_b": dm_b},
        }

    jargon_map = {
        "same": f"日主同气（{dm_a}/{dm_b}），比和之象。",
        "a_sheng_b": f"甲生乙之象：{dm_a}生{dm_b}，偏付出。",
        "b_sheng_a": f"乙生甲之象：{dm_b}生{dm_a}，偏付出。",
        "a_ke_b": f"甲克乙之象：{dm_a}克{dm_b}，主导/压力偏甲。",
        "b_ke_a": f"乙克甲之象：{dm_b}克{dm_a}，主导/压力偏乙。",
        "other": f"日主{dm_a}与{dm_b}交互偏杂。",
        "unknown": "日主关系不明。",
    }
    plain_map = {
        "same": "节奏相近好说话，也要防「谁都不肯让」。",
        "a_sheng_b": "甲方容易多付出，记得互相补给，勿单边耗尽。",
        "b_sheng_a": "乙方容易多付出，记得互相补给，勿单边耗尽。",
        "a_ke_b": "甲方较像掌舵方，语气软一点，冲突会少很多。",
        "b_ke_a": "乙方较像掌舵方，语气软一点，冲突会少很多。",
        "other": "互补要靠自觉经营，别指望「天生就顺」。",
        "unknown": "请先确认双方出生资料。",
    }
    return {
        "key": "day_master",
        "score": score,
        "jargon": _maybe_trad(jargon_map.get(rel, jargon_map["other"]), lang),
        "plain": _maybe_trad(plain_map.get(rel, plain_map["other"]), lang),
        "meta": {"relation": rel, "dm_a": dm_a, "dm_b": dm_b},
    }


def _score_spouse_palace(a: dict, b: dict, lang: str) -> dict:
    za = a.get("day_branch") or _pillar(a, "日柱").get("zhi") or ""
    zb = b.get("day_branch") or _pillar(b, "日柱").get("zhi") or ""
    flags = _branch_pair_flags(za, zb)
    score = 62.0
    bits_zh, bits_en = [], []
    if flags["he"]:
        score += 22
        bits_zh.append("日支六合")
        bits_en.append("day-branch harmony")
    if flags["chong"]:
        score -= 28
        bits_zh.append("日支相冲")
        bits_en.append("day-branch clash")
    if flags["xing"]:
        score -= 16
        bits_zh.append("日支相刑")
        bits_en.append("day-branch punishment")
    if flags["hai"]:
        score -= 12
        bits_zh.append("日支相害")
        bits_en.append("day-branch harm")
    if za == zb and za:
        score += 4
        bits_zh.append("夫妻宫同位")
        bits_en.append("same spouse-palace branch")
    score = int(round(_clamp(score)))

    if lang == "en":
        jargon = f"Spouse palaces {za}/{zb}: " + (", ".join(bits_en) if bits_en else "no major clash/combine")
        if flags["he"] and not flags["chong"]:
            plain = "Intimacy bond looks supportive — nurture routines together."
        elif flags["chong"] or flags["xing"]:
            plain = "Relationship weather can swing; prioritize repair talks early."
        else:
            plain = "Neither especially sticky nor stormy — consistency matters more than sparks."
        return {
            "key": "spouse_palace",
            "score": score,
            "jargon": jargon + ".",
            "plain": plain,
            "meta": {"zhi_a": za, "zhi_b": zb, **flags},
        }

    jargon = f"夫妻宫（日支）{za}/{zb}" + ("：" + "、".join(bits_zh) if bits_zh else "：无明显冲合刑害")
    if flags["he"] and not flags["chong"]:
        plain = "亲密感较易建立，把日常仪式感做起来会更稳。"
    elif flags["chong"] or flags["xing"]:
        plain = "相处起伏可能偏大，有事早说、少冷战。"
    else:
        plain = "不算特别黏，也不算硬碰硬——稳定比激情更重要。"
    return {
        "key": "spouse_palace",
        "score": score,
        "jargon": _maybe_trad(jargon + "。", lang),
        "plain": _maybe_trad(plain, lang),
        "meta": {"zhi_a": za, "zhi_b": zb, **flags},
    }


def _score_wuxing(a: dict, b: dict, lang: str) -> dict:
    sa, sb = estimate_day_strength(a), estimate_day_strength(b)
    stats_a = a.get("wuxing_stats") or {}
    stats_b = b.get("wuxing_stats") or {}

    def favor_hit(favor: set, other_stats: dict) -> float:
        if not favor:
            return 0.0
        total = sum(int(other_stats.get(w, 0) or 0) for w in ("木", "火", "土", "金", "水")) or 1
        hit = sum(int(other_stats.get(w, 0) or 0) for w in favor)
        return hit / total

    # A 被 B 补益、B 被 A 补益
    a_gain = favor_hit(sa.get("favor") or set(), stats_b)
    b_gain = favor_hit(sb.get("favor") or set(), stats_a)
    a_hurt = favor_hit(sa.get("avoid") or set(), stats_b)
    b_hurt = favor_hit(sb.get("avoid") or set(), stats_a)

    score = 50 + (a_gain + b_gain) * 40 - (a_hurt + b_hurt) * 35
    score = int(round(_clamp(score)))

    la, lb = sa.get("level", "balanced"), sb.get("level", "balanced")
    if lang == "en":
        jargon = (
            f"Day strength A={la}, B={lb}; "
            f"mutual favor hit {a_gain:.0%}/{b_gain:.0%}, avoid hit {a_hurt:.0%}/{b_hurt:.0%}."
        )
        if score >= 70:
            plain = "Elements look more nourishing than draining — good teamwork fuel."
        elif score <= 40:
            plain = "May amplify each other's stress points — schedule recovery time."
        else:
            plain = "Support is mixed: lean into what replenishes both of you."
        return {
            "key": "wuxing",
            "score": score,
            "jargon": jargon,
            "plain": plain,
            "meta": {
                "level_a": la,
                "level_b": lb,
                "a_gain": a_gain,
                "b_gain": b_gain,
                "a_hurt": a_hurt,
                "b_hurt": b_hurt,
            },
        }

    jargon = (
        f"身强弱：甲{la}/乙{lb}；"
        f"互为喜用占比约{a_gain:.0%}/{b_gain:.0%}，忌神占比约{a_hurt:.0%}/{b_hurt:.0%}。"
    )
    if score >= 70:
        plain = "五行上更像互相补益，一起做事会有助力感。"
    elif score <= 40:
        plain = "可能加重彼此压力点，记得留白与休息，别硬扛。"
    else:
        plain = "有补有耗——把「能补对方的事」做明确，消耗就会下降。"
    return {
        "key": "wuxing",
        "score": score,
        "jargon": _maybe_trad(jargon, lang),
        "plain": _maybe_trad(plain, lang),
        "meta": {
            "level_a": la,
            "level_b": lb,
            "a_gain": a_gain,
            "b_gain": b_gain,
            "a_hurt": a_hurt,
            "b_hurt": b_hurt,
        },
    }


def _marriage_gods_for(gender: str) -> Tuple[set, set]:
    """返回 (正向婚姻相关十神, 压力相关十神)。"""
    g = (gender or "").strip()
    if g.startswith("女"):
        return {"正官", "七杀", "食神", "伤官"}, {"七杀", "伤官", "劫财"}
    # 男命以财为妻星口径（通行简化）
    return {"正财", "偏财", "正官"}, {"劫财", "比肩", "七杀"}


def _score_shishen(a: dict, b: dict, lang: str) -> dict:
    dm_a, dm_b = a.get("day_master") or "", b.get("day_master") or ""
    ga, gb = a.get("gender") or "", b.get("gender") or ""
    # 看对方日主对自己的十神
    god_ab = shishen_of(dm_a, dm_b) if dm_a and dm_b else ""
    god_ba = shishen_of(dm_b, dm_a) if dm_a and dm_b else ""
    pos_a, neg_a = _marriage_gods_for(ga)
    pos_b, neg_b = _marriage_gods_for(gb)

    score = 58.0
    if god_ab in pos_a:
        score += 14
    if god_ba in pos_b:
        score += 14
    if god_ab in neg_a:
        score -= 10
    if god_ba in neg_b:
        score -= 10
    # 正财/正官加稳
    if god_ab in {"正财", "正官"} or god_ba in {"正财", "正官"}:
        score += 6
    score = int(round(_clamp(score)))

    if lang == "en":
        jargon = f"B as seen from A: {god_ab or '—'}; A as seen from B: {god_ba or '—'}."
        plain = (
            "Commitment/roles look relatively clear — name responsibilities early."
            if score >= 70
            else (
                "Role expectations may clash — spell out money, chores, and boundaries."
                if score <= 45
                else "Attraction is there; define commitment style to avoid mixed signals."
            )
        )
        return {
            "key": "shishen",
            "score": score,
            "jargon": jargon,
            "plain": plain,
            "meta": {"god_ab": god_ab, "god_ba": god_ba},
        }

    jargon = f"乙对甲为「{god_ab or '—'}」，甲对乙为「{god_ba or '—'}」（以日主论）。"
    if score >= 70:
        plain = "承诺与角色感相对清楚，早点把责任边界说开会更顺。"
    elif score <= 45:
        plain = "期望容易错位——钱、家务、边界最好明文约定。"
    else:
        plain = "有吸引力，但要讲清「怎么认真」，避免信号混乱。"
    return {
        "key": "shishen",
        "score": score,
        "jargon": _maybe_trad(jargon, lang),
        "plain": _maybe_trad(plain, lang),
        "meta": {"god_ab": god_ab, "god_ba": god_ba},
    }


def _collect_cross_branch_stress(a: dict, b: dict) -> int:
    """双方四支两两刑冲害计数（越高越不稳）。"""
    zhis_a = []
    zhis_b = []
    for name in ("年柱", "月柱", "日柱", "时柱"):
        za = _pillar(a, name).get("zhi")
        zb = _pillar(b, name).get("zhi")
        if za:
            zhis_a.append(za)
        if zb:
            zhis_b.append(zb)
    stress = 0
    for za in zhis_a:
        for zb in zhis_b:
            f = _branch_pair_flags(za, zb)
            if f["chong"]:
                stress += 2
            if f["xing"]:
                stress += 2
            if f["hai"]:
                stress += 1
    return stress


def _score_stability(a: dict, b: dict, dims: List[dict], lang: str) -> dict:
    stress = _collect_cross_branch_stress(a, b)
    # 日支冲已在夫妻宫计过，这里看全局
    base = 78 - stress * 4
    # 若日主克战强且夫妻宫也冲，再降
    dm = next((d for d in dims if d["key"] == "day_master"), None)
    sp = next((d for d in dims if d["key"] == "spouse_palace"), None)
    if dm and sp and dm["score"] < 55 and sp["score"] < 50:
        base -= 8
    score = int(round(_clamp(base)))

    if lang == "en":
        jargon = f"Cross-chart clash/punish/harm weight ≈ {stress}."
        plain = (
            "Overall climate is steady — keep small repairs frequent."
            if score >= 70
            else (
                "Volatility risk is higher — agree on cool-down rules before fights escalate."
                if score <= 45
                else "Manageable ups and downs if you avoid extreme reactions."
            )
        )
        return {
            "key": "stability",
            "score": score,
            "jargon": jargon,
            "plain": plain,
            "meta": {"stress": stress},
        }

    jargon = f"双方地支刑冲害压力指数约 {stress}（越高起伏越大）。"
    if score >= 70:
        plain = "整体气场偏稳，小摩擦勤修补即可。"
    elif score <= 45:
        plain = "波动风险偏高，先约好「冷静规则」，别让情绪滚雪球。"
    else:
        plain = "有起伏但可控——避免走极端反应，关系会耐用很多。"
    return {
        "key": "stability",
        "score": score,
        "jargon": _maybe_trad(jargon, lang),
        "plain": _maybe_trad(plain, lang),
        "meta": {"stress": stress},
    }


def analyze_hehun(a: dict, b: dict, lang: str = "zh") -> Dict[str, Any]:
    """
    输入两份 get_summary() 命盘，输出总分与五维。
    """
    d1 = _score_day_master(a, b, lang)
    d2 = _score_spouse_palace(a, b, lang)
    d3 = _score_wuxing(a, b, lang)
    d4 = _score_shishen(a, b, lang)
    partial = [d1, d2, d3, d4]
    d5 = _score_stability(a, b, partial, lang)
    dims = [d1, d2, d3, d4, d5]

    weights = {
        "day_master": 0.28,
        "spouse_palace": 0.24,
        "wuxing": 0.22,
        "shishen": 0.14,
        "stability": 0.12,
    }
    total = sum(d["score"] * weights[d["key"]] for d in dims)
    total = int(round(_clamp(total)))

    if lang == "en":
        if total >= 75:
            headline = "Generally complementary — nurture the mid-path, avoid extremes."
        elif total >= 55:
            headline = "Workable match: strengths and friction both matter; manage the edges."
        else:
            headline = "Friction signals are louder — go slow and invest in communication."
        summary = (
            "Scores reflect balance (中庸), not destiny. "
            "High is not automatic success; low is not a verdict — look at each dimension."
        )
    else:
        if total >= 75:
            headline = "整体偏互补：守中道、避极端，关系可经营。"
        elif total >= 55:
            headline = "可合可磨：优势与摩擦并存，关键在边界管理。"
        else:
            headline = "摩擦信号偏多：宜缓、宜沟通，勿用分数否定缘分。"
        summary = (
            "分数看的是「互补是否过中、冲突是否过极」，不是命运宣判。"
            "高分不等于必成，低分也不等于无缘——请逐维阅读。"
        )
        headline = _maybe_trad(headline, lang)
        summary = _maybe_trad(summary, lang)

    labels = DIM_LABELS_EN if lang == "en" else DIM_LABELS_ZH
    for d in dims:
        lab = labels.get(d["key"], d["key"])
        if lang != "en":
            lab = _maybe_trad(lab, lang)
        d["label"] = lab

    return {
        "total": total,
        "headline": headline,
        "summary": summary,
        "dimensions": dims,
        "weights": weights,
    }


def _bar_html(score: int) -> str:
    pct = max(4, min(100, int(score)))
    return (
        f"<div style='background:#eee;border-radius:4px;height:10px;width:100%;overflow:hidden;'>"
        f"<div style='width:{pct}%;height:100%;background:#C62828;border-radius:4px;'></div>"
        f"</div>"
    )


def _pillar_line(bazi: dict) -> str:
    parts = []
    for name in ("年柱", "月柱", "日柱", "时柱"):
        p = _pillar(bazi, name)
        g, z = p.get("gan") or "—", p.get("zhi") or "—"
        parts.append(f"{g}{z}")
    return " ".join(parts)


def render_hehun_html(
    result: dict,
    *,
    name_a: str,
    name_b: str,
    bazi_a: dict,
    bazi_b: dict,
    lang: str = "zh",
) -> str:
    """合婚结果 HTML（可再包水印）。"""
    total = int(result.get("total") or 0)
    headline = result.get("headline") or ""
    summary = result.get("summary") or ""
    dims = result.get("dimensions") or []

    if lang == "en":
        title = "BaZi Marriage Match"
        score_lab = "Compatibility"
        dim_h = "Dimensions"
        tip_h = "Notes"
        pa, pb = "Person A", "Person B"
        disc = "For reflection only — not a marital decision."
    else:
        title = _maybe_trad("八字合婚", lang)
        score_lab = _maybe_trad("契合度", lang)
        dim_h = _maybe_trad("五维分析", lang)
        tip_h = _maybe_trad("要点", lang)
        pa = _maybe_trad("甲方", lang)
        pb = _maybe_trad("乙方", lang)
        disc = _maybe_trad("仅供娱乐与自我参考，非婚姻决定依据。", lang)

    na = name_a or pa
    nb = name_b or pb
    line_a = _pillar_line(bazi_a)
    line_b = _pillar_line(bazi_b)
    if lang == "zh_hant":
        line_a = _maybe_trad(line_a, lang)
        line_b = _maybe_trad(line_b, lang)

    rows = []
    for d in dims:
        rows.append(
            "<tr>"
            f"<td style='padding:8px 6px;border-bottom:1px solid #eee;width:18%;font-weight:600;'>{d.get('label','')}</td>"
            f"<td style='padding:8px 6px;border-bottom:1px solid #eee;width:10%;text-align:center;font-weight:700;color:#C62828;'>{d.get('score',0)}</td>"
            f"<td style='padding:8px 6px;border-bottom:1px solid #eee;width:22%;'>{_bar_html(int(d.get('score') or 0))}</td>"
            f"<td style='padding:8px 6px;border-bottom:1px solid #eee;font-size:0.88rem;'>"
            f"<div style='color:#4E342E;font-weight:600;margin-bottom:2px;'>{d.get('jargon','')}</div>"
            f"<div style='color:#555;'>{d.get('plain','')}</div></td>"
            "</tr>"
        )

    return f"""
<div class="sf-hehun" style="font-family:system-ui,sans-serif;color:#222;">
  <div style="font-size:0.85rem;color:#c62828;margin-bottom:0.6rem;">{disc}</div>
  <h3 style="margin:0 0 0.6rem 0;font-weight:800;">{title}</h3>
  <div style="display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:0.8rem;">
    <div style="flex:1;min-width:200px;background:#fafafa;border-radius:8px;padding:10px 12px;">
      <div style="font-size:0.8rem;color:#666;">{pa} · {na}</div>
      <div style="font-weight:700;letter-spacing:0.06em;">{line_a}</div>
      <div style="font-size:0.8rem;color:#888;">{_maybe_trad('日主', lang) if lang != 'en' else 'Day Master'}：{bazi_a.get('day_master') or '—'}</div>
    </div>
    <div style="flex:1;min-width:200px;background:#fafafa;border-radius:8px;padding:10px 12px;">
      <div style="font-size:0.8rem;color:#666;">{pb} · {nb}</div>
      <div style="font-weight:700;letter-spacing:0.06em;">{line_b}</div>
      <div style="font-size:0.8rem;color:#888;">{_maybe_trad('日主', lang) if lang != 'en' else 'Day Master'}：{bazi_b.get('day_master') or '—'}</div>
    </div>
  </div>
  <div style="text-align:center;margin:0.8rem 0 1rem 0;">
    <div style="font-size:0.85rem;color:#666;">{score_lab}</div>
    <div style="font-size:2.6rem;font-weight:800;color:#C62828;line-height:1.1;">{total}</div>
    <div style="font-weight:600;margin-top:0.35rem;">{headline}</div>
    <div style="font-size:0.88rem;color:#666;margin-top:0.35rem;">{summary}</div>
  </div>
  <h4 style="margin:1rem 0 0.4rem 0;">{dim_h}</h4>
  <table style="width:100%;border-collapse:collapse;">
    <thead>
      <tr style="background:#f5f5f5;font-size:0.75rem;">
        <th style="padding:6px;text-align:left;">{dim_h}</th>
        <th style="padding:6px;">{'分' if lang != 'en' else 'Pts'}</th>
        <th style="padding:6px;"></th>
        <th style="padding:6px;text-align:left;">{tip_h}</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</div>
"""
