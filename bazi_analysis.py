"""
命盘衍生分析：性格简述、一生流年运势（1~80 岁，本地计算，不调用 API）。

运势评分依据子平常用思路：
- 先依四柱五行/十神估日主身强身弱 → 定喜用与忌神方向
- 再评大运、流年干支对日主的生克与十神
- 叠加刑冲合害、天克地冲等互动
- 「重要提示」按十神与互动，在事业/财运/感情/健康中择一条最关键
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

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

SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 五行对应脏腑（健康提示用，非医疗诊断）
WX_ORGAN = {
    "木": "肝胆/筋目",
    "火": "心脑/血压",
    "土": "脾胃/消化",
    "金": "肺/呼吸道",
    "水": "肾/泌尿与腰膝",
}

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
    frozenset(["子", "午"]), frozenset(["丑", "未"]), frozenset(["寅", "申"]),
    frozenset(["卯", "酉"]), frozenset(["辰", "戌"]), frozenset(["巳", "亥"]),
}

BRANCH_HAI = {
    frozenset(["子", "未"]), frozenset(["丑", "午"]), frozenset(["寅", "巳"]),
    frozenset(["卯", "辰"]), frozenset(["申", "亥"]), frozenset(["酉", "戌"]),
}

# 三刑：寅巳申、丑戌未、子卯；自刑辰午酉亥
XING_GROUPS = [
    frozenset(["寅", "巳", "申"]),
    frozenset(["丑", "戌", "未"]),
    frozenset(["子", "卯"]),
]
SELF_XING = {"辰", "午", "酉", "亥"}

TRIADS: Dict[frozenset, str] = {
    frozenset(["申", "酉", "戌"]): "金局",
    frozenset(["亥", "子", "丑"]): "水局",
    frozenset(["寅", "卯", "辰"]): "木局",
    frozenset(["巳", "午", "未"]): "火局",
}

# 桃花地支（相对年/日支）
TAOHUA_MAP = {"寅": "卯", "午": "卯", "戌": "卯", "申": "酉", "子": "酉", "辰": "酉",
              "亥": "子", "卯": "子", "未": "子", "巳": "午", "酉": "午", "丑": "午"}

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
        "summary": "聪明，有非常好的才干，在社会上表现优异；具有吸引群众的魅力，对自我的要求很高，能将自己的能力充分发挥。",
        "strength": "个性独立，慷慨大方，擅长社交活动。",
        "weakness": "比较自我中心，喜欢炫耀自己的能力，忽略别人的感受。",
    },
    "辛": {
        "summary": "精致敏锐，重品质与尊严，审美与判断力佳。",
        "strength": "细致、有品味、追求完美。",
        "weakness": "敏感、好面子，有时显得挑剔或冷峻。",
    },
    "壬": {
        "summary": "聪慧灵活，视野开阔，适应变化快，善于谋略与流动。",
        "strength": "机智、包容、学习快。",
        "weakness": "想法多、定力不足时易分散，情绪如水般起伏。",
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
    if wx == day_wx:
        return "比肩" if same else "劫财"
    if SHENG.get(day_wx) == wx:
        return "食神" if same else "伤官"
    if KE.get(day_wx) == wx:
        return "偏财" if same else "正财"
    if KE.get(wx) == day_wx:
        return "七杀" if same else "正官"
    if SHENG.get(wx) == day_wx:
        return "偏印" if same else "正印"
    return ""


def ganzhi_of_year(year: int) -> Tuple[str, str]:
    diff = year - 1900
    return TIANGAN[(6 + diff) % 10], DIZHI[(0 + diff) % 12]


def _maybe_trad(text: str, lang: str) -> str:
    if lang != "zh_hant" or not text:
        return text
    try:
        from zh_convert import to_traditional

        return to_traditional(text)
    except Exception:
        return text


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
            "title": "Personality Analysis",
            "body": (
                f"Day master {dm} ({yy} {wx}): {traits['summary']} "
                f"Strengths: {traits['strength']} Weaknesses: {traits['weakness']}"
            ),
            "summary": traits["summary"],
            "strength": traits["strength"],
            "weakness": traits["weakness"],
        }

    body = f"{traits['summary']}优点是{traits['strength']}缺点是{traits['weakness']}"
    if wx_note:
        body = f"{body}（{wx_note}）"
    if god_bits:
        body = f"{body} {' '.join(god_bits)}"

    title = "性格分析"
    if lang == "zh_hant":
        body = _maybe_trad(body, lang)
        title = _maybe_trad(title, lang)
        traits_s = _maybe_trad(traits["strength"], lang)
        traits_w = _maybe_trad(traits["weakness"], lang)
    else:
        traits_s, traits_w = traits["strength"], traits["weakness"]

    return {
        "title": title,
        "body": body,
        "summary": _maybe_trad(traits["summary"], lang) if lang == "zh_hant" else traits["summary"],
        "strength": traits_s,
        "weakness": traits_w,
        "day_master": dm,
        "day_wx": wx,
    }


def render_personality_html(bazi_data: dict, lang: str = "zh") -> str:
    """附图风格：褐色标题 + 正文。"""
    p = analyze_personality(bazi_data, lang)
    return (
        f"<div style='line-height:1.9;font-size:0.98rem;color:#222;padding:10px 12px;"
        f"background:#FFF8F0;border-left:4px solid #8B4513;border-radius:4px;margin:8px 0;'>"
        f"<div style='font-weight:800;color:#8B4513;margin-bottom:8px;font-size:1.05rem;'>"
        f"{p['title']}：</div>"
        f"<div>{p['body']}</div></div>"
    )


# ---------- 身强弱 · 喜忌 ----------

def estimate_day_strength(bazi_data: dict) -> dict:
    """
    粗估日主强弱：印星+比劫为帮身；食伤+财+官杀为耗泄克。
    返回 strength: strong|weak|balanced，以及喜用五行集合。
    """
    dm = bazi_data.get("day_master") or ""
    dm_wx = WUXING_MAP.get(dm, "")
    if not dm_wx:
        return {"level": "balanced", "score": 0, "favor": set(), "avoid": set(), "dm_wx": ""}

    # 印生我、比劫同我
    yin_wx = {w for w, t in SHENG.items() if t == dm_wx}
    bi_wx = {dm_wx}
    # 食伤我生、财我克、官杀克我
    shi_wx = {SHENG.get(dm_wx)} if SHENG.get(dm_wx) else set()
    cai_wx = {KE.get(dm_wx)} if KE.get(dm_wx) else set()
    guan_wx = {w for w, t in KE.items() if t == dm_wx}

    help_wx = yin_wx | bi_wx
    drain_wx = (shi_wx | cai_wx | guan_wx) - {None}

    stats = bazi_data.get("wuxing_stats") or {}
    help_n = sum(int(stats.get(w, 0) or 0) for w in help_wx)
    drain_n = sum(int(stats.get(w, 0) or 0) for w in drain_wx)
    # 月令地支权重略高
    pillars = bazi_data.get("pillars") or {}
    month = pillars.get("月柱") or {}
    mz = month.get("zhi") or ""
    mw = WUXING_MAP.get(mz, "")
    if mw in help_wx:
        help_n += 2
    elif mw in drain_wx:
        drain_n += 2

    diff = help_n - drain_n
    if diff >= 2:
        level = "strong"
        favor = drain_wx  # 身强喜泄耗克
        avoid = help_wx
    elif diff <= -2:
        level = "weak"
        favor = help_wx
        avoid = drain_wx
    else:
        level = "balanced"
        favor = help_wx | shi_wx | cai_wx
        avoid = guan_wx

    return {
        "level": level,
        "score": diff,
        "favor": {x for x in favor if x},
        "avoid": {x for x in avoid if x},
        "dm_wx": dm_wx,
        "help_n": help_n,
        "drain_n": drain_n,
    }


def _wx_relation_score(dm_wx: str, other_wx: str, favor: set, avoid: set) -> float:
    if not other_wx or not dm_wx:
        return 0.0
    s = 0.0
    if other_wx in favor:
        s += 14
    if other_wx in avoid:
        s -= 12
    if SHENG.get(other_wx) == dm_wx:  # 生我
        s += 6 if other_wx in favor else 2
    if SHENG.get(dm_wx) == other_wx:  # 我生
        s += 4 if other_wx in favor else -1
    if KE.get(other_wx) == dm_wx:  # 克我
        s -= 8 if other_wx in avoid else -3
    if KE.get(dm_wx) == other_wx:  # 我克
        s += 5 if other_wx in favor else 0
    if other_wx == dm_wx:
        s += 3 if other_wx in favor else -4
    return s


def _dayun_for_age(bazi_data: dict, age: int) -> Tuple[str, str]:
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


def _natal_branches(bazi_data: dict) -> List[str]:
    out = []
    pillars = bazi_data.get("pillars") or {}
    for name in ("年柱", "月柱", "日柱", "时柱"):
        z = (pillars.get(name) or {}).get("zhi")
        if z:
            out.append(z)
    if not out:
        bazi = bazi_data.get("bazi") or {}
        for name in ("年柱", "月柱", "日柱", "时柱"):
            p = bazi.get(name)
            if isinstance(p, (list, tuple)) and len(p) >= 2:
                out.append(p[1])
    return out


def _interaction_bundle(
    dy_gan: str, dy_zhi: str, ln_gan: str, ln_zhi: str, natal_zhi: List[str]
) -> dict:
    notes: List[str] = []
    flags = {
        "stem_he": False, "branch_he": False, "chong": False,
        "hai": False, "xing": False, "triad": False, "tianke_dichong": False,
    }

    pair_g = frozenset([dy_gan, ln_gan])
    if len(pair_g) == 2 and pair_g in STEM_HE:
        notes.append(f"天干化{STEM_HE[pair_g]}")
        flags["stem_he"] = True

    pair_z = frozenset([a for a in (dy_zhi, ln_zhi) if a])
    if len(pair_z) == 2:
        if pair_z in BRANCH_HE:
            notes.append(f"地支合{BRANCH_HE[pair_z]}")
            flags["branch_he"] = True
        if pair_z in BRANCH_CHONG:
            notes.append("地支冲")
            flags["chong"] = True
        if pair_z in BRANCH_HAI:
            notes.append("地支害")
            flags["hai"] = True

    # 流年与大运或命局构成三刑
    for grp in XING_GROUPS:
        present = {z for z in (dy_zhi, ln_zhi, *natal_zhi) if z in grp}
        if ln_zhi in grp and len(present) >= 2:
            notes.append("地支刑")
            flags["xing"] = True
            break
    if ln_zhi in SELF_XING and ln_zhi in natal_zhi:
        if "地支刑" not in notes:
            notes.append("自刑")
            flags["xing"] = True

    for triad, label in TRIADS.items():
        if dy_zhi in triad and ln_zhi in triad and dy_zhi != ln_zhi:
            notes.append(f"地支{label}")
            flags["triad"] = True
            break

    # 天克地冲：干相克且支相冲
    if dy_gan and ln_gan and dy_zhi and ln_zhi:
        dw, lw = WUXING_MAP.get(dy_gan), WUXING_MAP.get(ln_gan)
        if (KE.get(dw) == lw or KE.get(lw) == dw) and frozenset([dy_zhi, ln_zhi]) in BRANCH_CHONG:
            notes.append("天克地冲")
            flags["tianke_dichong"] = True

    # 流年冲日支 / 年支
    day_zhi = natal_zhi[2] if len(natal_zhi) > 2 else ""
    year_zhi = natal_zhi[0] if natal_zhi else ""
    if day_zhi and frozenset([ln_zhi, day_zhi]) in BRANCH_CHONG:
        notes.append("冲日支")
        flags["chong"] = True
    if year_zhi and frozenset([ln_zhi, year_zhi]) in BRANCH_CHONG:
        notes.append("冲年支")
        flags["chong"] = True

    # 去重保序
    seen = set()
    uniq = []
    for n in notes:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return {"notes": " ".join(uniq), "flags": flags}


def _god_domain_weights(god: str) -> Dict[str, float]:
    """十神 → 四维权重。"""
    table = {
        "正官": {"career": 1.0, "wealth": 0.3, "love": 0.45, "health": 0.35},
        "七杀": {"career": 0.95, "wealth": 0.25, "love": 0.4, "health": 0.55},
        "正财": {"career": 0.35, "wealth": 1.0, "love": 0.5, "health": 0.2},
        "偏财": {"career": 0.4, "wealth": 0.95, "love": 0.45, "health": 0.2},
        "正印": {"career": 0.45, "wealth": 0.2, "love": 0.25, "health": 0.55},
        "偏印": {"career": 0.4, "wealth": 0.2, "love": 0.2, "health": 0.5},
        "食神": {"career": 0.45, "wealth": 0.4, "love": 0.55, "health": 0.35},
        "伤官": {"career": 0.55, "wealth": 0.35, "love": 0.5, "health": 0.4},
        "比肩": {"career": 0.5, "wealth": 0.35, "love": 0.3, "health": 0.25},
        "劫财": {"career": 0.45, "wealth": 0.55, "love": 0.35, "health": 0.3},
    }
    return table.get(god, {"career": 0.3, "wealth": 0.3, "love": 0.3, "health": 0.3})


def _is_peach_blossom(bazi_data: dict, ln_zhi: str) -> bool:
    natal = _natal_branches(bazi_data)
    year_zhi = natal[0] if natal else ""
    day_zhi = natal[2] if len(natal) > 2 else ""
    for base in (year_zhi, day_zhi):
        if base and TAOHUA_MAP.get(base) == ln_zhi:
            return True
    return False


def _fortune_score_detailed(
    bazi_data: dict,
    strength: dict,
    dy_gan: str,
    dy_zhi: str,
    ln_gan: str,
    ln_zhi: str,
    inter: dict,
) -> int:
    dm = bazi_data.get("day_master") or ""
    dm_wx = strength.get("dm_wx") or WUXING_MAP.get(dm, "")
    favor = strength.get("favor") or set()
    avoid = strength.get("avoid") or set()

    score = 52.0
    # 流年干支（权重高）
    score += _wx_relation_score(dm_wx, WUXING_MAP.get(ln_gan, ""), favor, avoid) * 1.35
    score += _wx_relation_score(dm_wx, WUXING_MAP.get(ln_zhi, ""), favor, avoid) * 1.15
    # 大运干支（权重中）
    score += _wx_relation_score(dm_wx, WUXING_MAP.get(dy_gan, ""), favor, avoid) * 0.75
    score += _wx_relation_score(dm_wx, WUXING_MAP.get(dy_zhi, ""), favor, avoid) * 0.65

    # 十神微调
    ln_god = shishen_of(dm, ln_gan)
    dy_god = shishen_of(dm, dy_gan)
    god_adj = {
        "正官": 8, "正财": 8, "正印": 7, "食神": 7,
        "偏财": 5, "偏印": 3, "比肩": 2,
        "七杀": -2, "伤官": -1, "劫财": -3,
    }
    if strength.get("level") == "weak":
        god_adj.update({"正印": 10, "偏印": 7, "比肩": 6, "劫财": 4, "正官": 1, "七杀": -8, "伤官": -4})
    elif strength.get("level") == "strong":
        god_adj.update({"正财": 10, "偏财": 8, "食神": 8, "伤官": 5, "正官": 7, "七杀": 3, "正印": -4, "比肩": -5})

    score += god_adj.get(ln_god, 0) * 1.2
    score += god_adj.get(dy_god, 0) * 0.55

    flags = inter.get("flags") or {}
    if flags.get("tianke_dichong"):
        score -= 18
    if flags.get("chong"):
        score -= 10
    if flags.get("xing"):
        score -= 7
    if flags.get("hai"):
        score -= 5
    if flags.get("stem_he"):
        score += 8
    if flags.get("branch_he"):
        score += 7
    if flags.get("triad"):
        # 合局五行若为喜用则加，忌则减
        for note in (inter.get("notes") or "").split():
            for wx, lab in (("金", "金局"), ("水", "水局"), ("木", "木局"), ("火", "火局")):
                if lab in note:
                    score += 9 if wx in favor else (-8 if wx in avoid else 2)

    return int(max(18, min(96, round(score))))


def _age_stage_priors(age: int) -> Dict[str, float]:
    """
    人生阶段先验（子平「人生大事」与现实节律）：
    幼年重健康/长养，少年重学业，青年重感情与起步，壮年重事业财运，中年后事业+健康并重。
    """
    if age <= 5:
        return {"career": 0.0, "wealth": 0.0, "love": 0.0, "health": 3.5}
    if age <= 12:
        return {"career": 0.15, "wealth": 0.0, "love": 0.0, "health": 2.2}  # career 映射为学业
    if age <= 18:
        return {"career": 1.6, "wealth": 0.1, "love": 0.35, "health": 1.2}
    if age <= 22:
        return {"career": 1.1, "wealth": 0.35, "love": 1.3, "health": 0.55}
    if age <= 30:
        return {"career": 0.9, "wealth": 0.55, "love": 1.65, "health": 0.45}
    if age <= 40:
        return {"career": 1.7, "wealth": 1.15, "love": 0.7, "health": 0.55}
    if age <= 50:
        return {"career": 1.35, "wealth": 1.0, "love": 0.55, "health": 1.0}
    if age <= 60:
        return {"career": 0.85, "wealth": 0.85, "love": 0.45, "health": 1.45}
    return {"career": 0.4, "wealth": 0.45, "love": 0.35, "health": 2.0}


def _pick_important_tip(
    bazi_data: dict,
    strength: dict,
    year: int,
    age: int,
    dy_gan: str,
    dy_zhi: str,
    ln_gan: str,
    ln_zhi: str,
    inter: dict,
    score: int,
    *,
    detailed: bool,
    lang: str = "zh",
) -> str:
    """按年龄阶段 + 十神/冲合，在四维中择一条最贴合的提示。"""
    dm = bazi_data.get("day_master") or ""
    gender = bazi_data.get("gender") or ""
    ln_god = shishen_of(dm, ln_gan)
    dy_god = shishen_of(dm, dy_gan)
    flags = inter.get("flags") or {}
    ln_wx = WUXING_MAP.get(ln_gan, "") or WUXING_MAP.get(ln_zhi, "")
    organ = WX_ORGAN.get(ln_wx, "身心作息")
    peach = _is_peach_blossom(bazi_data, ln_zhi)

    weights = {"career": 0.0, "wealth": 0.0, "love": 0.0, "health": 0.0}
    for g, mul in ((ln_god, 1.0), (dy_god, 0.4)):
        for k, v in _god_domain_weights(g).items():
            weights[k] += v * mul

    # 年龄阶段强先验（避免幼年出现「事业升迁」）
    for k, v in _age_stage_priors(age).items():
        weights[k] += v

    if peach and age >= 16:
        weights["love"] += 1.35
    if flags.get("chong") or flags.get("tianke_dichong"):
        weights["health"] += 0.85 if age <= 18 or age >= 40 else 0.55
        if 25 <= age <= 55:
            weights["career"] += 0.3
        if 18 <= age <= 35:
            weights["love"] += 0.35
    if flags.get("xing") or flags.get("hai"):
        weights["health"] += 0.5
    if ln_god in ("正财", "偏财", "劫财") and age >= 22:
        weights["wealth"] += 0.55
    if ln_god in ("正官", "七杀", "伤官") and age >= 18:
        weights["career"] += 0.5
    if ln_god in ("正印", "偏印") and age <= 22:
        weights["career"] += 0.8  # 学业
        weights["health"] += 0.3

    # 硬约束：幼年几乎只谈健康/成长
    if age <= 5:
        weights = {"career": 0.0, "wealth": 0.0, "love": 0.0, "health": 5.0}
        if flags.get("chong") or flags.get("xing") or score <= 40:
            weights["health"] += 1.0
    elif age <= 12:
        weights["love"] = 0.0
        weights["wealth"] = 0.0
        weights["health"] = max(weights["health"], weights["career"] * 0.8 + 1.0)

    domain = max(weights, key=weights.get)

    # —— 按年龄生成文案 ——
    text = ""

    if age <= 5:
        if flags.get("chong") or flags.get("tianke_dichong") or flags.get("xing"):
            text = f"健康：幼冲刑之年，留意感冒跌碰与{organ}，作息规律，家长多陪伴。"
        elif ln_god in ("七杀", "伤官"):
            text = f"健康：性情较躁或敏感，宜疏导情绪，防护{organ}，少刺激性环境。"
        elif ln_god in ("正印", "偏印", "食神"):
            text = "健康：长养较顺，重营养睡眠与安全看护，培养安心感。"
        elif score <= 40:
            text = f"健康：体质偏弱之年，慎风寒饮食，重点养护{organ}。"
        else:
            text = f"健康：幼儿长养年，均衡饮食、疫苗与体检按程，留意{organ}。"

    elif age <= 12:
        if domain == "health" or flags.get("chong") or score <= 40:
            text = f"健康：学龄成长年，睡眠充足、户外运动，留意{organ}与近视防护。"
        elif ln_god in ("正印", "偏印", "正官"):
            text = "学业：启蒙/求学期，培养专注与习惯，忌过度报班施压。"
        elif ln_god in ("伤官", "食神"):
            text = "学业：思维活跃，适合兴趣启发；防分心与顶撞师长。"
        else:
            text = "学业：打牢基础之年，劳逸结合，身心同步成长。"

    elif age <= 18:
        if domain == "health" and (flags.get("chong") or score <= 38):
            text = f"健康：青春期注意作息与情绪，养护{organ}，避免熬夜透支。"
        elif domain == "love" and peach:
            text = "感情：情窦初开，宜分寸交往，重心仍在学业与自我成长。"
        elif ln_god in ("正官", "正印", "七杀"):
            text = "学业：考试/升学关键年，宜规划目标、稳住心态，忌临时抱佛脚。"
        elif ln_god in ("伤官", "食神"):
            text = "学业：适合竞赛、表达或技艺发展，防偏科与口舌。"
        else:
            text = "学业：打磨能力与志趣，为升学或就业做准备；兼顾身心。"

    elif age <= 22:
        if domain == "love":
            if peach:
                text = "感情：恋爱契机较多，宜识人与自我边界，勿因感情荒废前程。"
            else:
                text = "感情：关系议题升温，真诚沟通；重大承诺宜与人生规划一并考虑。"
        elif domain == "career":
            text = "事业：求学收官或初入职场，重学习曲线与贵人，忌好高骛远。"
        elif domain == "wealth":
            text = "财运：初有进账宜储蓄理财启蒙，忌超前消费与担保。"
        else:
            text = f"健康：过渡压力大，规律作息，留意{organ}。"

    elif age <= 30:
        if domain == "love":
            if peach:
                text = "感情：桃花较旺，适婚配或关系定性；有伴者防暧昧与口舌。"
            elif flags.get("chong"):
                text = "感情：聚散变动年，婚恋决策宜冷静，沟通优于冷战。"
            elif gender.startswith("女") and ln_god in ("正官", "七杀"):
                text = "感情：婚恋/责任议题突出，适合认真看待承诺与匹配度。"
            elif gender.startswith("男") and ln_god in ("正财", "偏财"):
                text = "感情：家庭与伴侣经营年，重兑现承诺，忌花心分心。"
            else:
                text = "感情：适合深化关系或规划婚姻，也需平衡事业起步。"
        elif domain == "career":
            text = tips_career_young(ln_god)
        elif domain == "wealth":
            text = tips_wealth(ln_god, age)
        else:
            text = f"健康：奋斗期易过劳，运动减压，留意{organ}。"

    elif age <= 40:
        if domain == "career":
            text = tips_career_prime(ln_god)
        elif domain == "wealth":
            text = tips_wealth(ln_god, age)
        elif domain == "love":
            text = "感情：家庭经营与责任年，重陪伴沟通，防因事业冷落伴侣。"
        else:
            text = f"健康：压力型透支初显，体检与{organ}养护要跟上。"

    elif age <= 50:
        if domain == "health" or (flags.get("chong") and score <= 55):
            text = f"健康：中年转折，定期体检，重点{organ}，戒熬夜烟酒。"
        elif domain == "career":
            text = tips_career_mid(ln_god)
        elif domain == "wealth":
            text = tips_wealth(ln_god, age)
        else:
            text = "感情：家庭与亲代关系议题，宜包容沟通，少争执伤和气。"

    elif age <= 60:
        if domain == "health":
            text = f"健康：代谢与慢性风险上升，养护{organ}，保持适度运动。"
        elif domain == "career":
            text = "事业：宜传帮带与守成优化，重大扩张需量力；规划退休节奏。"
        elif domain == "wealth":
            text = "财运：重保值与配置，忌高风险投机；理清传承与保障。"
        else:
            text = "感情：夫妻相处重体贴，亲子关系可多走动、少苛责。"

    else:
        # 60岁以后：以颐养健康为主，财运/事业为辅
        if domain == "wealth" and age <= 75 and not (flags.get("chong") and score <= 40):
            text = "财运：以稳妥保障为先，大额决策与家人商议，防诈骗。"
        elif domain == "career" and age <= 70:
            text = "事业：量力参与顾问/兴趣事业，勿过劳；重生活品质。"
        elif domain == "love":
            text = "感情：亲情友情为贵，多聚会少执拗，家庭和睦即福。"
        elif flags.get("chong") or flags.get("xing") or score <= 40:
            text = f"健康：冲刑或弱运年，起居谨慎，重点{organ}，遵医嘱复查。"
        elif ln_god in ("正印", "食神"):
            text = "健康：宜清心缓步、兴趣养生，饮食清淡，防跌滑。"
        else:
            text = f"健康：颐养为主，规律体检与用药，留意{organ}与情绪。"

    # 详细年附加语气（成年后）
    if detailed and age >= 18:
        if flags.get("tianke_dichong"):
            text = "⚠天克地冲：" + text
        elif score >= 78 and not (flags.get("chong") or flags.get("xing")):
            text = text + "整体气势偏旺，可主动进取但留余地。"
        elif score >= 78 and (flags.get("chong") or flags.get("xing")):
            text = text + "变动中藏机遇，宜调整节奏并稳住身心。"
        elif score <= 35:
            text = text + "整体宜守不宜攻，大事缓决。"

    # 非焦点平常年：缩短（仍保持年龄标签）
    if not detailed and age >= 13 and score >= 45 and score <= 70 and not (
        flags.get("chong") or flags.get("xing") or flags.get("tianke_dichong") or peach
    ):
        short = {
            "career": "学业：平稳进取即可。" if age <= 18 else "事业：按部就班即可。",
            "wealth": "财运：收支平稳即可。",
            "love": "感情：维系日常即可。",
            "health": "健康：常规保养即可。",
        }
        # 幼年/童年不缩短成「事业」
        if age <= 12:
            text = "健康：常规养护即可。" if domain == "health" else "学业：循序渐进即可。"
        else:
            text = short.get(domain, "运势平稳，顺势而为。")

    return _maybe_trad(text, lang)


def tips_career_young(ln_god: str) -> str:
    table = {
        "正官": "事业：职场规矩与考核年，宜稳表现、积口碑，忌顶撞上级。",
        "七杀": "事业：竞争压力大，适合挑战岗，但需策略与抗压，忌意气。",
        "伤官": "事业：适合创意/表达岗或转轨试错，防口舌与制度冲突。",
        "食神": "事业：专长变现起步好，深耕技能比跳槽频率更重要。",
        "正印": "事业：进修考证、导师提携年，先充电再冲刺。",
        "偏印": "事业：适合研究策划类方向，忌分散目标。",
        "比肩": "事业：同辈合作多，分清权责，防争功。",
        "劫财": "事业：变动快，防抢夺与不稳合作。",
    }
    return table.get(ln_god, "事业：打基础、建人脉之年，重大跳槽需看清平台。")


def tips_career_prime(ln_god: str) -> str:
    table = {
        "正官": "事业：升迁/责权扩张窗口，守规建功，忌与制度硬碰。",
        "七杀": "事业：高压攻坚年，宜借势破局，防过劳与树敌。",
        "伤官": "事业：创新改革或转岗窗口，表达有力但需政治智慧。",
        "食神": "事业：专业口碑变现佳，适合做精做深。",
        "正印": "事业：贵人与资质加持，适合品牌与管理升级。",
        "偏印": "事业：适合战略、咨询、冷门专长突破。",
        "比肩": "事业：合伙/团队扩张，契约与股权宜清晰。",
        "劫财": "事业：变动与竞争并存，防拆台与资源被分。",
        "正财": "事业：以业绩与现金流说话，稳扎稳打拓展。",
        "偏财": "事业：项目/机会型收益，评估风险后再上。",
    }
    return table.get(ln_god, "事业：建立壁垒与成果兑现年，重大决策先评估资源。")


def tips_career_mid(ln_god: str) -> str:
    table = {
        "正官": "事业：管理/名望议题，宜传帮带，忌恋战无谓是非。",
        "七杀": "事业：压力型事务多，授权分工，防健康透支。",
        "伤官": "事业：可转型咨询/创作，少硬刚体制。",
        "食神": "事业：经验变现、作品或课程方向佳。",
        "正印": "事业：顾问、教育、幕后支持角色顺。",
    }
    return table.get(ln_god, "事业：优化结构、培养二梯队，扩张需量力。")


def tips_wealth(ln_god: str, age: int) -> str:
    table = {
        "正财": "财运：正财稳健，宜储蓄与固定收益，忌盲目加杠杆。",
        "偏财": "财运：偏财机会现，可适度把握，须止损纪律。",
        "劫财": "财运：破财风险偏高，忌借贷担保、合伙不清。",
        "食神": "财运：才艺/服务变现佳，宜开源轻资产。",
        "伤官": "财运：创意变现可期，忌投机赌博心态。",
        "七杀": "财运：求财辛苦，以技以劳换酬，忌急功近利。",
    }
    text = table.get(ln_god, "财运：量入为出，大额投资宜分批、留备用金。")
    if age >= 45 and ln_god in ("偏财", "劫财"):
        text = text + "中年后更宜稳健配置。"
    return text


def build_lifetime_fortune(bazi_data: dict, max_age: int = 80, lang: str = "zh") -> List[dict]:
    """1~max_age 实岁逐年运势（本地计算）。"""
    birth_year = int(bazi_data.get("birth_year") or 0)
    if not birth_year:
        return []
    strength = estimate_day_strength(bazi_data)
    natal_zhi = _natal_branches(bazi_data)
    now_y = datetime.now().year
    rows = []
    for age in range(1, max_age + 1):
        year = birth_year + age
        ln_gan, ln_zhi = ganzhi_of_year(year)
        dy_gan, dy_zhi = _dayun_for_age(bazi_data, age)
        inter = _interaction_bundle(dy_gan, dy_zhi, ln_gan, ln_zhi, natal_zhi)
        score = _fortune_score_detailed(
            bazi_data, strength, dy_gan, dy_zhi, ln_gan, ln_zhi, inter
        )
        detailed = (now_y - 1) <= year <= (now_y + 10)
        tip = _pick_important_tip(
            bazi_data, strength, year, age, dy_gan, dy_zhi, ln_gan, ln_zhi,
            inter, score, detailed=detailed, lang=lang,
        )
        rows.append(
            {
                "year": year,
                "age": age,
                "dayun": f"{dy_gan}{dy_zhi}" if dy_gan and dy_zhi else "—",
                "liunian": f"{ln_gan}{ln_zhi}",
                "interaction": inter.get("notes") or "",
                "score": score,
                "tip": tip,
                "detailed": detailed,
            }
        )
    return rows


def render_lifetime_fortune_html(
    bazi_data: dict,
    lang: str = "zh",
    *,
    max_age: int = 80,
    highlight_year: Optional[int] = None,
) -> str:
    rows = build_lifetime_fortune(bazi_data, max_age=max_age, lang=lang)
    if not rows:
        return ""
    if highlight_year is None:
        highlight_year = datetime.now().year

    strength = estimate_day_strength(bazi_data)
    level_map = {
        "strong": ("日主偏强，运势条偏喜泄耗（财官食伤）之年", "Day master strong — favor wealth/output years"),
        "weak": ("日主偏弱，运势条偏喜生扶（印比）之年", "Day master weak — favor resource/support years"),
        "balanced": ("日主中和，喜用较均衡，冲合之年波动更明显", "Day master balanced — clashes matter more"),
    }
    level_zh, level_en = level_map.get(strength["level"], level_map["balanced"])

    if lang == "en":
        title = "Lifetime Annual Fortune (ages 1–80)"
        cols = ("Year", "Age", "Da Yun", "Liu Nian", "Interactions", "Fortune", "Key Note")
        hint = (
            f"{level_en}. Longer bar = better year. "
            "Key notes emphasize Career / Wealth / Relationship / Health — "
            "current year and next 10 years are more detailed."
        )
    else:
        title = "一生流年运势分析"
        cols = ("西元", "实岁", "大运", "流年", "大运流年合化", "运势", "重要提示")
        hint = (
            f"{level_zh}。红线越长代表该年运势越佳；"
            "「重要提示」按年龄阶段（幼年健康、青年感情、壮年事业、中年后健康）"
            "并结合十神冲合，在事业·财运·感情·健康中择最相关一条；"
            "今年起未来十年提示更细。仅供参考，非医疗/投资建议。"
        )
        if lang == "zh_hant":
            title = _maybe_trad(title, lang)
            cols = tuple(_maybe_trad(c, lang) for c in cols)
            hint = _maybe_trad(hint, lang)

    # 列宽：合化收窄约 25%，重要提示加宽
    # 西元/实岁/大运/流年/合化/运势/重要提示
    col_widths = ("7%", "5%", "7%", "7%", "9%", "16%", "49%")
    head_cells = []
    for i, c in enumerate(cols):
        w = col_widths[i] if i < len(col_widths) else "auto"
        head_cells.append(
            f"<th style='padding:6px 6px;background:#f5f5f5;border-bottom:1px solid #ddd;"
            f"font-size:0.72rem;font-weight:600;text-align:center;width:{w};'>{c}</th>"
        )
    head = "".join(head_cells)
    body_rows = []
    max_score = max(r["score"] for r in rows) or 100
    min_score = min(r["score"] for r in rows) or 0
    span = max(max_score - min_score, 1)

    for r in rows:
        is_cur = r["year"] == highlight_year
        is_focus = r.get("detailed")
        age_style = "color:#C62828;font-weight:700;" if is_cur else ""
        row_bg = "background:#FFF8E7;" if is_cur else ("background:#FAFAFA;" if is_focus else "")
        # 相对拉伸，让强弱对比更明显
        norm = (r["score"] - min_score) / span
        bar_w = int(28 + norm * 170)
        bar_color = "#C2185B" if r["score"] >= 55 else "#AB47BC"
        if r["score"] <= 35:
            bar_color = "#78909C"
        bar = (
            f"<div style='height:10px;width:{bar_w}px;background:{bar_color};"
            f"border-radius:2px;' title='{r['score']}'></div>"
        )
        inter = r["interaction"] or "—"
        tip = r.get("tip") or "—"
        tip_style = "font-weight:600;color:#4E342E;" if is_focus else "color:#666;"
        body_rows.append(
            f"<tr style='{row_bg}'>"
            f"<td style='padding:4px 4px;border-bottom:1px solid #eee;text-align:center;font-size:0.8rem;width:{col_widths[0]};'>{r['year']}</td>"
            f"<td style='padding:4px 4px;border-bottom:1px solid #eee;text-align:center;font-size:0.8rem;width:{col_widths[1]};{age_style}'>{r['age']}</td>"
            f"<td style='padding:4px 4px;border-bottom:1px solid #eee;text-align:center;font-size:0.8rem;width:{col_widths[2]};'>{r['dayun']}</td>"
            f"<td style='padding:4px 4px;border-bottom:1px solid #eee;text-align:center;font-size:0.8rem;width:{col_widths[3]};'>{r['liunian']}</td>"
            f"<td style='padding:4px 3px;border-bottom:1px solid #eee;text-align:center;font-size:0.68rem;color:#666;"
            f"width:{col_widths[4]};max-width:72px;word-break:break-word;line-height:1.35;'>{inter}</td>"
            f"<td style='padding:4px 4px;border-bottom:1px solid #eee;width:{col_widths[5]};'>{bar}</td>"
            f"<td style='padding:4px 8px;border-bottom:1px solid #eee;text-align:left;font-size:0.75rem;"
            f"{tip_style};width:{col_widths[6]};min-width:200px;line-height:1.45;'>{tip}</td>"
            "</tr>"
        )
    colgroup = "".join(f"<col style='width:{w};'/>" for w in col_widths)
    return (
        f"<div style='margin-top:8px;'>"
        f"<div style='font-weight:700;color:#8B4513;margin-bottom:8px;font-size:1.05rem;'>{title}：</div>"
        f"<div style='overflow-x:auto;'>"
        f"<table style='width:100%;border-collapse:collapse;background:#fff;table-layout:fixed;'>"
        f"<colgroup>{colgroup}</colgroup>"
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        f"</table></div>"
        f"<div style='font-size:0.75rem;color:#888;margin-top:6px;'>{hint}</div>"
        f"</div>"
    )
