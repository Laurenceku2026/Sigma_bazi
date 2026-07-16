"""
命盘衍生分析：性格简述、一生流年运势（1~80 岁，本地计算，不调用 API）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

WUXING_MAP = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火",
    "戊": "土", "己": "土", "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
    "子": "水", "丑": "土", "寅": "木", "卯": "木",
    "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

YANG_GAN = {"甲", "丙", "戊", "庚", "壬"}

STEM_HE: Dict[frozenset, str] = {
    frozenset(["甲", "己"]): "土",
    frozenset(["乙", "庚"]): "金",
    frozenset(["丙", "辛"]): "水",
    frozenset(["丁", "壬"]): "木",
    frozenset(["戊", "癸"]): "火",
}

BRANCH_HE: Dict[frozenset, str] = {
    frozenset(["子", "丑"]): "土",
    frozenset(["寅", "亥"]): "木",
    frozenset(["卯", "戌"]): "火",
    frozenset(["辰", "酉"]): "金",
    frozenset(["巳", "申"]): "水",
    frozenset(["午", "未"]): "土",
}

BRANCH_CHONG = {
    frozenset(["子", "午"]),
    frozenset(["丑", "未"]),
    frozenset(["寅", "申"]),
    frozenset(["卯", "酉"]),
    frozenset(["辰", "戌"]),
    frozenset(["巳", "亥"]),
}

TRIADS: Dict[frozenset, str] = {
    frozenset(["申", "酉", "戌"]): "金局",
    frozenset(["亥", "子", "丑"]): "水局",
    frozenset(["寅", "卯", "辰"]): "木局",
    frozenset(["巳", "午", "未"]): "火局",
}

GOD_SCORE = {
    "正官": 9, "七杀": 6, "正财": 9, "偏财": 7,
    "正印": 8, "偏印": 6, "食神": 8, "伤官": 5,
    "比肩": 6, "劫财": 5,
}

DAY_STEM_TRAITS: Dict[str, Dict[str, str]] = {
    "甲": {
        "summary": "正直进取，有开拓精神，重视原则与成长空间。",
        "strength": "有担当、肯学习、适应力强。",
        "weakness": "有时过于理想化，易因坚持己见而显得固执。",
    },
    "乙": {
        "summary": "温和细腻，善于协调，外柔内韧，重人情与美感。",
        "strength": "体贴、灵活、善于沟通与合作。",
        "weakness": "顾虑较多，决断时易犹豫，易受环境影响。",
    },
    "丙": {
        "summary": "热情开朗，光明磊落，行动力强，喜欢表现与引领。",
        "strength": "自信、慷慨、感染力强。",
        "weakness": "性子急，情绪起伏时易冲动，有时不够细致。",
    },
    "丁": {
        "summary": "心思细密，重情重义，观察力佳，内秀而有韧性。",
        "strength": "专注、敏感、能洞察人心。",
        "weakness": "多思多虑，易内耗，有时过于在意他人看法。",
    },
    "戊": {
        "summary": "稳重厚实，讲信用，能扛事，重视安全与积累。",
        "strength": "可靠、务实、有耐心。",
        "weakness": "反应偏慢，不喜变动，有时显得保守。",
    },
    "己": {
        "summary": "包容务实，善于整合资源，重实际与归属感。",
        "strength": "细心、能守成、擅长照顾他人。",
        "weakness": "顾虑多、易自我怀疑，有时过于迁就。",
    },
    "庚": {
        "summary": "刚毅果断，重义气，有原则与执行力，敢作敢当。",
        "strength": "正直、有魄力、讲信用。",
        "weakness": "语气较硬，易与人起冲突，不够圆滑。",
    },
    "辛": {
        "summary": "精致敏锐，重品质与尊严，审美与判断力佳。",
        "strength": "细致、有品味、追求完美。",
        "weakness": "敏感、好面子，有时显得挑剔或冷峻。",
    },
    "壬": {
        "summary": "聪慧灵活，视野开阔，适应变化快，善于谋略与流动。",
        "strength": "机智、包容、学习快。",
        "weakness": "想法多、定力强时易分散，情绪如水般起伏。",
    },
    "癸": {
        "summary": "内敛聪慧，感知力强，重直觉与内在世界。",
        "strength": "细腻、有同理心、能深入思考。",
        "weakness": "易多虑、不够主动，有时显得被动或退缩。",
    },
}

GOD_TRAITS: Dict[str, str] = {
    "正官": "行事有分寸，重视规则与名誉。",
    "七杀": "竞争意识强，压力下反而能激发潜能。",
    "正财": "务实理财，重视稳定与循序渐进。",
    "偏财": "机会嗅觉灵敏，善于把握流动资源。",
    "正印": "好学重道，易得长辈或贵人扶持。",
    "偏印": "思维独特，适合钻研或创意型工作。",
    "食神": "表达与才艺佳，生活品味较好。",
    "伤官": "才思敏捷，不喜束缚，创新欲强。",
    "比肩": "独立自尊，重视同伴与自我主张。",
    "劫财": "行动快、敢拼，但需注意合作与边界。",
}


def _yy(char: str) -> str:
    if char in YANG_GAN:
        return "阳"
    if char in TIANGAN:
        return "阴"
    return "阳" if char in ["子", "寅", "辰", "午", "申", "戌"] else "阴"


def shishen_of(day_master: str, char: str) -> str:
    if not char or not day_master:
        return ""
    day_wx = WUXING_MAP.get(day_master, "")
    wx = WUXING_MAP.get(char, "")
    if not day_wx or not wx:
        return ""
    same = _yy(day_master) == _yy(char)
    sheng = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    ke = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
    if wx == day_wx:
        return "比肩" if same else "劫财"
    if sheng.get(day_wx) == wx:
        return "食神" if same else "伤官"
    if ke.get(day_wx) == wx:
        return "偏财" if same else "正财"
    if ke.get(wx) == day_wx:
        return "七杀" if same else "正官"
    if sheng.get(wx) == day_wx:
        return "偏印" if same else "正印"
    return ""


def ganzhi_of_year(year: int) -> Tuple[str, str]:
    diff = year - 1900
    return TIANGAN[(6 + diff) % 10], DIZHI[(0 + diff) % 12]


def _dominant_gods(bazi_data: dict, top_n: int = 2) -> List[str]:
    counts: Dict[str, int] = {}
    pillars = bazi_data.get("pillars") or {}
    for p in pillars.values():
        g = p.get("gan_god")
        if g and g != "日主":
            counts[g] = counts.get(g, 0) + 2
        zg = p.get("zhi_god")
        if zg:
            counts[zg] = counts.get(zg, 0) + 1
        for c in p.get("cangan") or []:
            cg = c.get("god")
            if cg:
                counts[cg] = counts.get(cg, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    return [g for g, _ in ranked[:top_n]]


def _wuxing_note(stats: dict) -> str:
    if not stats:
        return ""
    mx = max(stats.values()) if stats else 0
    mn = min(stats.values()) if stats else 0
    strong = [k for k, v in stats.items() if v == mx and v > 0]
    weak = [k for k, v in stats.items() if v == mn]
    parts = []
    if strong:
        parts.append(f"五行{'、'.join(strong)}偏旺")
    if weak and mn < mx:
        parts.append(f"{'、'.join(weak)}相对偏弱")
    return "；".join(parts) if parts else ""


def analyze_personality(bazi_data: dict, lang: str = "zh") -> dict:
    """基于日主、十神与五行分布生成性格简述。"""
    dm = bazi_data.get("day_master") or ""
    traits = DAY_STEM_TRAITS.get(dm, {
        "summary": "命盘信息不足，暂无法细述性格。",
        "strength": "—",
        "weakness": "—",
    })
    yy = "阳" if dm in YANG_GAN else "阴"
    wx = WUXING_MAP.get(dm, "")
    gods = _dominant_gods(bazi_data)
    god_bits = [GOD_TRAITS.get(g, "") for g in gods if GOD_TRAITS.get(g)]
    wx_note = _wuxing_note(bazi_data.get("wuxing_stats") or {})

    if lang == "en":
        return {
            "title": "Personality",
            "body": (
                f"Day master {dm} ({yy} {wx}): {traits['summary']} "
                f"Strengths: {traits['strength']} Weaknesses: {traits['weakness']}"
            ),
        }

    body = (
        f"日主{dm}（{yy}{wx}）{traits['summary']}"
        f"{' ' + ' '.join(god_bits) if god_bits else ''}"
        f"{' ' + wx_note + '。' if wx_note else ''}"
        f"优点：{traits['strength']}缺点：{traits['weakness']}"
    )
    title = "性格分析"
    if lang == "zh_hant":
        try:
            from zh_convert import to_traditional

            body = to_traditional(body)
            title = to_traditional(title)
        except Exception:
            pass
    return {"title": title, "body": body}


def _dayun_for_age(bazi_data: dict, age: int) -> Tuple[str, str]:
    """返回指定实岁的大运干支。"""
    for row in bazi_data.get("xiao_yun") or []:
        if int(row.get("age") or 0) == age:
            return row.get("gan", ""), row.get("zhi", "")
    for dy in bazi_data.get("da_yun") or []:
        sa = int(dy.get("start_age") or 0)
        ea = int(dy.get("end_age") or 0)
        if sa <= age <= ea:
            return dy.get("gan", ""), dy.get("zhi", "")
    da_yun = bazi_data.get("da_yun") or []
    if da_yun:
        last = da_yun[-1]
        return last.get("gan", ""), last.get("zhi", "")
    return "", ""


def _interaction_notes(dy_gan: str, dy_zhi: str, ln_gan: str, ln_zhi: str) -> str:
    notes: List[str] = []
    pair_g = frozenset([dy_gan, ln_gan])
    if pair_g in STEM_HE:
        notes.append(f"天干化{STEM_HE[pair_g]}")
    pair_z = frozenset([dy_zhi, ln_zhi])
    if pair_z in BRANCH_HE:
        notes.append("地支合")
    if pair_z in BRANCH_CHONG:
        notes.append("地支冲")
    for triad, label in TRIADS.items():
        if dy_zhi in triad and ln_zhi in triad and dy_zhi != ln_zhi:
            notes.append(f"地支{label}")
            break
    return " ".join(notes)


def _fortune_score(day_master: str, dy_gan: str, dy_zhi: str, ln_gan: str, ln_zhi: str) -> int:
    score = 45.0
    ln_god = shishen_of(day_master, ln_gan)
    dy_god = shishen_of(day_master, dy_gan)
    score += GOD_SCORE.get(ln_god, 5) * 2.2
    score += GOD_SCORE.get(dy_god, 5) * 1.2
    pair_z = frozenset([dy_zhi, ln_zhi])
    if pair_z in BRANCH_CHONG:
        score -= 18
    pair_g = frozenset([dy_gan, ln_gan])
    if pair_g in STEM_HE:
        score += 12
    if pair_z in BRANCH_HE:
        score += 10
    for triad in TRIADS:
        if dy_zhi in triad and ln_zhi in triad and dy_zhi != ln_zhi:
            score += 8
            break
    return int(max(18, min(100, round(score))))


def build_lifetime_fortune(bazi_data: dict, max_age: int = 80) -> List[dict]:
    """1~max_age 实岁逐年运势（本地计算）。"""
    birth_year = int(bazi_data.get("birth_year") or 0)
    if not birth_year:
        return []
    dm = bazi_data.get("day_master") or ""
    rows = []
    for age in range(1, max_age + 1):
        year = birth_year + age
        ln_gan, ln_zhi = ganzhi_of_year(year)
        dy_gan, dy_zhi = _dayun_for_age(bazi_data, age)
        score = _fortune_score(dm, dy_gan, dy_zhi, ln_gan, ln_zhi)
        rows.append(
            {
                "year": year,
                "age": age,
                "dayun": f"{dy_gan}{dy_zhi}" if dy_gan and dy_zhi else "—",
                "liunian": f"{ln_gan}{ln_zhi}",
                "interaction": _interaction_notes(dy_gan, dy_zhi, ln_gan, ln_zhi),
                "score": score,
            }
        )
    return rows


def render_personality_html(bazi_data: dict, lang: str = "zh") -> str:
    p = analyze_personality(bazi_data, lang)
    return (
        f"<div style='line-height:1.85;font-size:0.95rem;color:#333;'>"
        f"<div style='font-weight:700;color:#8B4513;margin-bottom:6px;'>{p['title']}：</div>"
        f"<div>{p['body']}</div></div>"
    )


def render_lifetime_fortune_html(
    bazi_data: dict,
    lang: str = "zh",
    *,
    max_age: int = 80,
    highlight_year: Optional[int] = None,
) -> str:
    rows = build_lifetime_fortune(bazi_data, max_age=max_age)
    if not rows:
        return ""
    if highlight_year is None:
        highlight_year = datetime_now_year()

    if lang == "en":
        title = "Lifetime annual fortune (ages 1–80)"
        cols = ("Year", "Age", "Da Yun", "Liu Nian", "Interactions", "Fortune")
        hint = "Longer bar = better fortune for that year."
    else:
        title = "一生流年运势分析"
        cols = ("西元", "实岁", "大运", "流年", "大运流年合化", "运势（红线越长代表该年运势越佳）")
        hint = "红线越长代表该年运势越佳。"
        if lang == "zh_hant":
            try:
                from zh_convert import to_traditional

                title = to_traditional(title)
                cols = tuple(to_traditional(c) for c in cols)
                hint = to_traditional(hint)
            except Exception:
                pass

    head = "".join(
        f"<th style='padding:6px 8px;background:#f5f5f5;border-bottom:1px solid #ddd;"
        f"font-size:0.78rem;font-weight:600;text-align:center;white-space:nowrap;'>{c}</th>"
        for c in cols
    )
    body_rows = []
    max_score = max(r["score"] for r in rows) or 100
    for r in rows:
        is_cur = r["year"] == highlight_year
        age_style = "color:#C62828;font-weight:700;" if is_cur else ""
        bar_w = int(40 + (r["score"] / max_score) * 160)
        bar = (
            f"<div style='height:10px;width:{bar_w}px;background:#C2185B;border-radius:2px;'></div>"
        )
        inter = r["interaction"] or "—"
        body_rows.append(
            "<tr>"
            f"<td style='padding:4px 8px;border-bottom:1px solid #eee;text-align:center;font-size:0.82rem;'>{r['year']}</td>"
            f"<td style='padding:4px 8px;border-bottom:1px solid #eee;text-align:center;font-size:0.82rem;{age_style}'>{r['age']}</td>"
            f"<td style='padding:4px 8px;border-bottom:1px solid #eee;text-align:center;font-size:0.82rem;'>{r['dayun']}</td>"
            f"<td style='padding:4px 8px;border-bottom:1px solid #eee;text-align:center;font-size:0.82rem;'>{r['liunian']}</td>"
            f"<td style='padding:4px 8px;border-bottom:1px solid #eee;text-align:center;font-size:0.75rem;color:#666;'>{inter}</td>"
            f"<td style='padding:4px 8px;border-bottom:1px solid #eee;'>{bar}</td>"
            "</tr>"
        )
    return (
        f"<div style='margin-top:8px;'>"
        f"<div style='font-weight:700;color:#8B4513;margin-bottom:8px;font-size:1rem;'>{title}：</div>"
        f"<div style='overflow-x:auto;'>"
        f"<table style='width:100%;border-collapse:collapse;background:#fff;'>"
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        f"</table></div>"
        f"<div style='font-size:0.75rem;color:#888;margin-top:6px;'>{hint}</div>"
        f"</div>"
    )


def datetime_now_year() -> int:
    from datetime import datetime

    return datetime.now().year
