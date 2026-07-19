"""
紫微斗数排盘（本地）

安星规则对齐主流中州/常见软件口径（参考 iztro 同类算法）：
- 寅宫为 0 起算
- 顺数生月、逆数生时安命；顺数生时安身
- 五虎遁起寅首 → 命宫干支 → 五行局
- 局数除日数起紫微，对宫安天府，再布十四主星与常用辅星、四化
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from bazi_meta import DIZHI, TIANGAN

# 寅起索引：寅=0 … 丑=11
YIN_BRANCHES = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]

PALACE_NAMES = [
    "命宫",
    "兄弟",
    "夫妻",
    "子女",
    "财帛",
    "疾厄",
    "迁移",
    "交友",
    "官禄",
    "田宅",
    "福德",
    "父母",
]

# 五虎遁：年干 → 寅宫天干
TIGER_RULE = {
    "甲": "丙",
    "己": "丙",
    "乙": "戊",
    "庚": "戊",
    "丙": "庚",
    "辛": "庚",
    "丁": "壬",
    "壬": "壬",
    "戊": "甲",
    "癸": "甲",
}

# 干支数取五行局（iztro 口诀）→ (局名, 局数)
_JU_BY_DIFF = {
    1: ("木三局", 3),
    2: ("金四局", 4),
    3: ("水二局", 2),
    4: ("火六局", 6),
    5: ("土五局", 5),
}

# 年干四化：禄权科忌
SIHUA_BY_YEAR_GAN: Dict[str, Tuple[str, str, str, str]] = {
    "甲": ("廉贞", "破军", "武曲", "太阳"),
    "乙": ("天机", "天梁", "紫微", "太阴"),
    "丙": ("天同", "天机", "文昌", "廉贞"),
    "丁": ("太阴", "天同", "天机", "巨门"),
    "戊": ("贪狼", "太阴", "右弼", "天机"),
    "己": ("武曲", "贪狼", "天梁", "文曲"),
    "庚": ("太阳", "武曲", "太阴", "天同"),
    "辛": ("巨门", "太阳", "文曲", "文昌"),
    "壬": ("天梁", "紫微", "左辅", "武曲"),
    "癸": ("破军", "巨门", "太阴", "贪狼"),
}

SIHUA_LABELS = ("化禄", "化权", "化科", "化忌")

# 亮度：按寅起 12 宫
_BRIGHT = {
    "庙": "庙",
    "旺": "旺",
    "得": "得",
    "利": "利",
    "平": "平",
    "不": "不",
    "陷": "陷",
}
_BRIGHTNESS: Dict[str, List[str]] = {
    "紫微": ["旺", "旺", "得", "旺", "庙", "庙", "旺", "旺", "得", "旺", "平", "庙"],
    "天机": ["得", "旺", "利", "平", "庙", "陷", "得", "旺", "利", "平", "庙", "陷"],
    "太阳": ["旺", "庙", "旺", "旺", "旺", "得", "得", "陷", "不", "陷", "陷", "不"],
    "武曲": ["得", "利", "庙", "平", "旺", "庙", "得", "利", "庙", "平", "旺", "庙"],
    "天同": ["利", "平", "平", "庙", "陷", "不", "旺", "平", "平", "庙", "旺", "不"],
    "廉贞": ["庙", "平", "利", "陷", "平", "利", "庙", "平", "利", "陷", "平", "利"],
    "天府": ["庙", "得", "庙", "得", "旺", "庙", "得", "旺", "庙", "得", "庙", "庙"],
    "太阴": ["旺", "陷", "陷", "陷", "不", "不", "利", "不", "旺", "庙", "庙", "庙"],
    "贪狼": ["平", "利", "庙", "陷", "旺", "庙", "平", "利", "庙", "陷", "旺", "庙"],
    "巨门": ["庙", "庙", "陷", "旺", "旺", "不", "庙", "庙", "陷", "旺", "旺", "不"],
    "天相": ["庙", "陷", "得", "得", "庙", "得", "庙", "陷", "得", "得", "庙", "庙"],
    "天梁": ["庙", "庙", "庙", "陷", "庙", "旺", "陷", "得", "庙", "陷", "庙", "旺"],
    "七杀": ["庙", "旺", "庙", "平", "旺", "庙", "庙", "庙", "庙", "平", "旺", "庙"],
    "破军": ["得", "陷", "旺", "平", "庙", "旺", "得", "陷", "旺", "平", "庙", "旺"],
}

# 紫微系（逆）/ 天府系（顺）偏移表
_ZIWEI_GROUP = ["紫微", "天机", "", "太阳", "武曲", "天同", "", "", "廉贞"]
_TIANFU_GROUP = ["天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "", "", "", "破军"]

# 宫位主题（本地解读）
_PALACE_HINTS = {
    "命宫": "性格格局、人生主轴与自我形象",
    "兄弟": "手足同辈、人际协作与横向支持",
    "夫妻": "婚姻感情、合伙与亲密关系",
    "子女": "子女缘、创作成果与下级部属",
    "财帛": "理财方式、求财路径与金钱观",
    "疾厄": "健康体质、压力出口与内在损耗",
    "迁移": "外出变动、环境机遇与流动性",
    "交友": "朋友部属、社交圈与合作对象",
    "官禄": "事业官运、职责角色与社会成就",
    "田宅": "家庭不动产、安全感与居住场域",
    "福德": "精神享受、兴趣福气与内心富足",
    "父母": "长辈贵人、家风教养与上级关系",
}


def _fix(i: int, n: int = 12) -> int:
    return i % n


def _yin_idx_of_zhi(zhi: str) -> int:
    if zhi in YIN_BRANCHES:
        return YIN_BRANCHES.index(zhi)
    if zhi in DIZHI:
        return _fix(DIZHI.index(zhi) - 2)
    return 0


def _zhi_of_yin_idx(idx: int) -> str:
    return YIN_BRANCHES[_fix(idx)]


def hour_to_time_index(hour: int, minute: int = 0) -> int:
    """时辰索引：子=0 … 亥=11（23:00–00:59 为子）。"""
    h = int(hour) % 24
    if h == 23 or h == 0:
        return 0
    return ((h + 1) // 2) % 12


def _solar_to_lunar(y: int, m: int, d: int) -> Tuple[int, int, int, bool]:
    """返回 (农历年, 月, 日, 是否闰月)。"""
    try:
        from lunardate import LunarDate

        if hasattr(LunarDate, "from_solar_date"):
            ld = LunarDate.from_solar_date(y, m, d)
        else:
            ld = LunarDate.fromSolarDate(y, m, d)
        leap = bool(getattr(ld, "isLeapMonth", False) or getattr(ld, "is_leap_month", False))
        return int(ld.year), int(ld.month), int(ld.day), leap
    except Exception:
        return y, m, d, False


def _five_elements_ju(gan: str, zhi: str) -> Tuple[str, int]:
    """命宫干支 → 五行局名与局数。"""
    gi = TIANGAN.index(gan) if gan in TIANGAN else 0
    yi = _yin_idx_of_zhi(zhi)
    # 还原到子起地支序再套口诀
    abs_zhi = DIZHI.index(_zhi_of_yin_idx(yi)) if _zhi_of_yin_idx(yi) in DIZHI else 0
    stem_n = gi // 2 + 1
    branch_n = (abs_zhi % 6) // 2 + 1
    idx = stem_n + branch_n
    while idx > 5:
        idx -= 5
    return _JU_BY_DIFF[idx]


def _ziwei_tianfu_index(lunar_day: int, ju: int) -> Tuple[int, int]:
    """局数除日数起紫微（寅=0），天府相对。"""
    day = max(1, int(lunar_day))
    offset = 0
    quotient = 0
    while True:
        divisor = day + offset
        if ju > 0 and divisor % ju == 0:
            quotient = divisor // ju
            break
        offset += 1
        if offset > 60:
            break
    quotient %= 12
    ziwei = quotient - 1
    if offset % 2 == 0:
        ziwei += offset
    else:
        ziwei -= offset
    ziwei = _fix(ziwei)
    tianfu = _fix(12 - ziwei)
    return ziwei, tianfu


def _brightness(star: str, yin_idx: int) -> str:
    arr = _BRIGHTNESS.get(star)
    if not arr:
        return ""
    return arr[_fix(yin_idx)]


def compute_ziwei_chart(
    *,
    birth_date: date,
    birth_hour: int,
    birth_minute: int = 0,
    gender: str = "男",
    name: str = "",
    year_gan: str = "",
    year_zhi: str = "",
    hour_zhi: str = "",
) -> Dict[str, Any]:
    """由公历生辰排紫微命盘。年干支/时支可传入八字结果以保持一致。"""
    ly, lm, ld, leap = _solar_to_lunar(birth_date.year, birth_date.month, birth_date.day)
    # 闰月：按下一月起（全书常见处理）
    month_for_palace = lm + 1 if leap else lm
    month_for_palace = min(max(month_for_palace, 1), 12)

    if hour_zhi and hour_zhi in DIZHI:
        time_index = DIZHI.index(hour_zhi)
    else:
        time_index = hour_to_time_index(birth_hour, birth_minute)
        hour_zhi = DIZHI[time_index]

    # 年干支：优先用八字年柱；否则用农历年粗推（与日柱无关的简化）
    if not year_gan or not year_zhi:
        # 与公元年的近似：以立春前后可能偏差，故强烈建议传入八字年柱
        base = ly - 4
        year_gan = TIANGAN[base % 10]
        year_zhi = DIZHI[base % 12]

    month_index = month_for_palace - 1  # 寅起：正月=0
    soul_index = _fix(month_index - time_index)
    body_index = _fix(month_index + time_index)

    start_gan = TIGER_RULE.get(year_gan, "丙")
    soul_gan = TIANGAN[_fix(TIANGAN.index(start_gan) + soul_index, 10)]
    soul_zhi = _zhi_of_yin_idx(soul_index)
    ju_name, ju_num = _five_elements_ju(soul_gan, soul_zhi)

    ziwei_i, tianfu_i = _ziwei_tianfu_index(ld, ju_num)

    # 十二宫：yin_idx → 宫名（命宫起逆行）
    palaces: List[Dict[str, Any]] = []
    for yin_i in range(12):
        pname = PALACE_NAMES[_fix(soul_index - yin_i)]
        gan = TIANGAN[_fix(TIANGAN.index(start_gan) + yin_i, 10)]
        zhi = _zhi_of_yin_idx(yin_i)
        palaces.append(
            {
                "yin_index": yin_i,
                "name": pname,
                "gan": gan,
                "zhi": zhi,
                "is_ming": yin_i == soul_index,
                "is_shen": yin_i == body_index,
                "majors": [],
                "minors": [],
                "sihua": [],
            }
        )

    def add_major(yin_i: int, star: str) -> None:
        palaces[yin_i]["majors"].append(
            {"name": star, "brightness": _brightness(star, yin_i), "type": "major"}
        )

    def add_minor(yin_i: int, star: str) -> None:
        palaces[yin_i]["minors"].append({"name": star, "type": "minor"})

    for i, s in enumerate(_ZIWEI_GROUP):
        if s:
            add_major(_fix(ziwei_i - i), s)
    for i, s in enumerate(_TIANFU_GROUP):
        if s:
            add_major(_fix(tianfu_i + i), s)

    # 辅星
    zuo = _fix(_yin_idx_of_zhi("辰") + (month_for_palace - 1))
    you = _fix(_yin_idx_of_zhi("戌") - (month_for_palace - 1))
    add_minor(zuo, "左辅")
    add_minor(you, "右弼")

    chang = _fix(_yin_idx_of_zhi("戌") - time_index)
    qu = _fix(_yin_idx_of_zhi("辰") + time_index)
    add_minor(chang, "文昌")
    add_minor(qu, "文曲")

    kui_yue = {
        "甲": ("丑", "未"),
        "戊": ("丑", "未"),
        "庚": ("丑", "未"),
        "乙": ("子", "申"),
        "己": ("子", "申"),
        "辛": ("午", "寅"),
        "壬": ("卯", "巳"),
        "癸": ("卯", "巳"),
        "丙": ("亥", "酉"),
        "丁": ("亥", "酉"),
    }
    kui_z, yue_z = kui_yue.get(year_gan, ("丑", "未"))
    add_minor(_yin_idx_of_zhi(kui_z), "天魁")
    add_minor(_yin_idx_of_zhi(yue_z), "天钺")

    lu_map = {
        "甲": "寅",
        "乙": "卯",
        "丙": "巳",
        "戊": "巳",
        "丁": "午",
        "己": "午",
        "庚": "申",
        "辛": "酉",
        "壬": "亥",
        "癸": "子",
    }
    lu_z = lu_map.get(year_gan, "寅")
    lu_i = _yin_idx_of_zhi(lu_z)
    add_minor(lu_i, "禄存")
    add_minor(_fix(lu_i + 1), "擎羊")
    add_minor(_fix(lu_i - 1), "陀罗")

    # 天马
    ma_map = {
        "寅": "申",
        "午": "申",
        "戌": "申",
        "申": "寅",
        "子": "寅",
        "辰": "寅",
        "巳": "亥",
        "酉": "亥",
        "丑": "亥",
        "亥": "巳",
        "卯": "巳",
        "未": "巳",
    }
    add_minor(_yin_idx_of_zhi(ma_map.get(year_zhi, "申")), "天马")

    # 地空地劫
    hai = _yin_idx_of_zhi("亥")
    add_minor(_fix(hai - time_index), "地空")
    add_minor(_fix(hai + time_index), "地劫")

    # 火星铃星
    huo_ling_start = {
        "寅": ("丑", "卯"),
        "午": ("丑", "卯"),
        "戌": ("丑", "卯"),
        "申": ("寅", "戌"),
        "子": ("寅", "戌"),
        "辰": ("寅", "戌"),
        "巳": ("卯", "戌"),
        "酉": ("卯", "戌"),
        "丑": ("卯", "戌"),
        "亥": ("酉", "戌"),
        "卯": ("酉", "戌"),
        "未": ("酉", "戌"),
    }
    hs, ls = huo_ling_start.get(year_zhi, ("寅", "戌"))
    add_minor(_fix(_yin_idx_of_zhi(hs) + time_index), "火星")
    add_minor(_fix(_yin_idx_of_zhi(ls) + time_index), "铃星")

    # 红鸾天喜
    hong = _fix(_yin_idx_of_zhi("卯") - DIZHI.index(year_zhi))
    add_minor(hong, "红鸾")
    add_minor(_fix(hong + 6), "天喜")

    # 四化挂到星上
    sihua_tuple = SIHUA_BY_YEAR_GAN.get(year_gan, ("", "", "", ""))
    sihua_list = []
    star_to_sihua = {s: SIHUA_LABELS[i] for i, s in enumerate(sihua_tuple) if s}
    for p in palaces:
        for star in p["majors"] + p["minors"]:
            tag = star_to_sihua.get(star["name"])
            if tag:
                star["sihua"] = tag
                p["sihua"].append(f"{star['name']}{tag}")
                sihua_list.append(
                    {
                        "star": star["name"],
                        "type": tag,
                        "palace": p["name"],
                        "zhi": p["zhi"],
                    }
                )

    # 大限：阳男阴女顺，阴男阳女逆；起运年龄=局数
    year_zhi_yy = "阳" if DIZHI.index(year_zhi) % 2 == 0 else "阴"
    gender_norm = "女" if str(gender) in ("女", "female", "F", "f") else "男"
    forward = (gender_norm == "男" and year_zhi_yy == "阳") or (
        gender_norm == "女" and year_zhi_yy == "阴"
    )
    decadals = []
    for i in range(12):
        idx = _fix(soul_index + i) if forward else _fix(soul_index - i)
        start_age = ju_num + 10 * i
        decadals.append(
            {
                "palace": palaces[idx]["name"],
                "zhi": palaces[idx]["zhi"],
                "start_age": start_age,
                "end_age": start_age + 9,
            }
        )

    return {
        "ok": True,
        "name": name or "",
        "gender": gender_norm,
        "solar_date": birth_date.isoformat(),
        "birth_hour": int(birth_hour),
        "birth_minute": int(birth_minute),
        "lunar": {
            "year": ly,
            "month": lm,
            "day": ld,
            "leap": leap,
            "month_used": month_for_palace,
            "label": f"农历{ly}年{'闰' if leap else ''}{lm}月{ld}日",
        },
        "year_gan": year_gan,
        "year_zhi": year_zhi,
        "hour_zhi": hour_zhi,
        "time_index": time_index,
        "ming_palace": palaces[soul_index]["name"],
        "shen_palace": palaces[body_index]["name"],
        "ming_ganzhi": f"{soul_gan}{soul_zhi}",
        "soul_index": soul_index,
        "body_index": body_index,
        "ju_name": ju_name,
        "ju_num": ju_num,
        "ziwei_zhi": _zhi_of_yin_idx(ziwei_i),
        "tianfu_zhi": _zhi_of_yin_idx(tianfu_i),
        "palaces": palaces,
        "sihua": sihua_list,
        "decadals": decadals,
        "decadal_forward": forward,
    }


def compute_ziwei_from_birth_info(
    birth_info: Dict[str, Any],
    bazi_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """沿用八字页的 birth_info / bazi_data 排盘。"""
    bi = birth_info or {}
    bd = bazi_data or {}
    raw = bi.get("birth_date") or ""
    if isinstance(raw, date):
        bdate = raw
    else:
        bdate = date.fromisoformat(str(raw)[:10])

    pillars = bd.get("pillars") or {}
    year_p = pillars.get("年柱") or {}
    hour_p = pillars.get("时柱") or {}
    # pillars 可能是 {gan,zhi} 或旧结构
    year_gan = year_p.get("gan") or ""
    year_zhi = year_p.get("zhi") or ""
    hour_zhi = hour_p.get("zhi") or ""
    if not year_gan and isinstance(bd.get("bazi"), dict):
        y = bd["bazi"].get("年柱") or ("", "")
        if isinstance(y, (list, tuple)) and len(y) >= 2:
            year_gan, year_zhi = y[0], y[1]
        h = bd["bazi"].get("时柱") or ("", "")
        if isinstance(h, (list, tuple)) and len(h) >= 2:
            hour_zhi = h[1]

    return compute_ziwei_chart(
        birth_date=bdate,
        birth_hour=int(bi.get("birth_hour") or 0),
        birth_minute=int(bi.get("birth_minute") or 0),
        gender=str(bi.get("gender") or bd.get("gender") or "男"),
        name=str(bi.get("name") or ""),
        year_gan=year_gan,
        year_zhi=year_zhi,
        hour_zhi=hour_zhi,
    )


def _palace_by_name(chart: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    for p in chart.get("palaces") or []:
        if p.get("name") == name:
            return p
    return None


def _star_line(p: Dict[str, Any]) -> str:
    majors = []
    for s in p.get("majors") or []:
        bit = s["name"]
        if s.get("brightness"):
            bit += f"（{s['brightness']}）"
        if s.get("sihua"):
            bit += s["sihua"]
        majors.append(bit)
    minors = [s["name"] + (s.get("sihua") or "") for s in (p.get("minors") or [])]
    return "、".join(majors + minors) if (majors or minors) else "（空宫）"


def _star_palace_map(chart: Dict[str, Any]) -> Dict[str, str]:
    """星名 → 所在宫名。"""
    out: Dict[str, str] = {}
    for p in chart.get("palaces") or []:
        for s in (p.get("majors") or []) + (p.get("minors") or []):
            out[s["name"]] = p["name"]
    return out


def _trigram_group(zhi: str) -> set:
    trigrams = [
        {"申", "子", "辰"},
        {"寅", "午", "戌"},
        {"巳", "酉", "丑"},
        {"亥", "卯", "未"},
    ]
    return next((set(g) for g in trigrams if zhi in g), {zhi})


def ming_sanfang_sizheng(chart: Dict[str, Any]) -> List[str]:
    """命宫三方四正宫名列表（本宫 + 三合 + 对宫）。"""
    ming = _palace_by_name(chart, "命宫") or {}
    ming_zhi = ming.get("zhi") or "寅"
    soul = int(chart.get("soul_index") or 0)
    group = _trigram_group(ming_zhi)
    names: List[str] = []
    seen = set()
    for p in chart.get("palaces") or []:
        zhi = p.get("zhi") or ""
        is_opp = _fix(_yin_idx_of_zhi(zhi) - soul) == 6
        if zhi in group or is_opp or p.get("is_ming"):
            if p["name"] not in seen:
                seen.add(p["name"])
                names.append(p["name"])
    # 命宫置顶
    if "命宫" in names:
        names = ["命宫"] + [n for n in names if n != "命宫"]
    return names


def compute_palace_fly(chart: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    飞星：以各宫天干起四化，飞到盘中星曜所在宫。
    若飞入本宫则为自化。
    """
    star_at = _star_palace_map(chart)
    rows: List[Dict[str, Any]] = []
    for p in chart.get("palaces") or []:
        gan = p.get("gan") or ""
        flies = SIHUA_BY_YEAR_GAN.get(gan)
        if not flies:
            continue
        items = []
        for star, label in zip(flies, SIHUA_LABELS):
            target = star_at.get(star, "")
            self_hua = bool(target and target == p["name"])
            items.append(
                {
                    "star": star,
                    "type": label,
                    "to_palace": target or "—",
                    "self": self_hua,
                }
            )
        rows.append({"from_palace": p["name"], "gan": gan, "zhi": p.get("zhi"), "flies": items})
    return rows


def build_ziwei_basic_reading(chart: Dict[str, Any], *, lang: str = "zh") -> Dict[str, Any]:
    """基础解读：按四化 / 三合 / 飞星三套排盘视角给出专业摘要。"""
    en = lang == "en"
    if not chart.get("ok"):
        return {"ok": False, "sections": []}

    def L(zh: str, en_s: str) -> str:
        return en_s if en else zh

    sections: List[Dict[str, str]] = []
    ming = _palace_by_name(chart, "命宫") or {}
    sections.append(
        {
            "title": L("命盘总览", "Chart overview"),
            "body": L(
                f"{chart.get('name') or '命主'}，{chart.get('gender')}，"
                f"{(chart.get('lunar') or {}).get('label')}，{chart.get('ju_name')}；"
                f"命宫{ming.get('gan')}{ming.get('zhi')}，身宫{chart.get('shen_palace')}；"
                f"紫微在{chart.get('ziwei_zhi')}，天府在{chart.get('tianfu_zhi')}。"
                f"下方按「四化 / 三合 / 飞星」三套视角解读。",
                f"{chart.get('name') or 'Native'}, {chart.get('ju_name')}, "
                f"Life {ming.get('gan')}{ming.get('zhi')}. Readings below use Si Hua / San He / Flying Stars.",
            ),
        }
    )

    # —— 四化 ——
    sihua = chart.get("sihua") or []
    sihua_body = L(
        "【四化盘】以生年天干定禄权科忌，看先天加强与挂碍。"
        "化禄偏机遇收获，化权偏主导掌控，化科偏名声文书，化忌偏挂碍分心。",
        "[Si Hua] Year-stem mutagens: Lu=gain, Quan=power, Ke=fame, Ji=stress.",
    )
    if sihua:
        sihua_body += L(
            "生年四化落点："
            + "；".join(f"{x['star']}{x['type']}→{x['palace']}" for x in sihua)
            + "。",
            " Natal: " + "; ".join(f"{x['star']}{x['type']}→{x['palace']}" for x in sihua) + ".",
        )
        ji = [x for x in sihua if x.get("type") == "化忌"]
        lu = [x for x in sihua if x.get("type") == "化禄"]
        if lu:
            sihua_body += L(
                f"禄星落{lu[0]['palace']}，该宫议题易见机遇与资源流动；",
                f" Lu in {lu[0]['palace']} favors opportunity there; ",
            )
        if ji:
            sihua_body += L(
                f"忌星落{ji[0]['palace']}，宜当作长期功课与风险管理，而非宿命判决。",
                f" Ji in {ji[0]['palace']} is a long-term focus, not fate.",
            )
    sections.append({"title": L("四化解读", "Si Hua reading"), "body": sihua_body})

    # —— 三合 ——
    sf_names = ming_sanfang_sizheng(chart)
    sf_bits = []
    for n in sf_names:
        p = _palace_by_name(chart, n) or {}
        majors = "、".join(s["name"] for s in (p.get("majors") or [])) or L("无主星", "no major")
        sf_bits.append(f"{n}（{p.get('gan')}{p.get('zhi')}）主星{majors}")
    sanhe_body = L(
        "【三合盘】先看命宫三方四正（本宫、三合宫、对宫）的主星气势，再论格局高低。"
        + "；".join(sf_bits)
        + "。三方有吉曜叠临则格局偏开扬；忌曜或空宫较多则宜稳健经营。",
        "[San He] Life-palace trine/opposite: " + "; ".join(sf_bits) + ".",
    )
    # 重点宫位一句
    for pname in ("命宫", "官禄", "财帛", "夫妻"):
        p = _palace_by_name(chart, pname) or {}
        if not p:
            continue
        hint = _PALACE_HINTS.get(pname, "")
        majors = "、".join(s["name"] for s in (p.get("majors") or [])) or L("无主星", "no major")
        sanhe_body += L(
            f" {pname}主「{hint}」，星曜：{_star_line(p)}。",
            f" {pname} ({hint}): {_star_line(p)}.",
        )
    sections.append({"title": L("三合解读", "San He reading"), "body": sanhe_body})

    # —— 飞星 ——
    flies = compute_palace_fly(chart)
    ming_fly = next((r for r in flies if r["from_palace"] == "命宫"), None)
    feixing_bits = []
    self_bits = []
    if ming_fly:
        for it in ming_fly["flies"]:
            tag = L("自化", "self") if it["self"] else L(f"飞入{it['to_palace']}", f"→{it['to_palace']}")
            feixing_bits.append(f"{it['star']}{it['type']}（{tag}）")
    for r in flies:
        for it in r["flies"]:
            if it["self"]:
                self_bits.append(f"{r['from_palace']}{it['star']}{it['type']}")
    feixing_body = L(
        "【飞星盘】以各宫天干飞出禄权科忌，看宫际牵动；飞回本宫为自化，能量更内聚。"
        f"命宫天干{ming.get('gan') or '—'}飞出："
        + ("、".join(feixing_bits) if feixing_bits else "—")
        + "。",
        "[Flying Stars] Life-palace stem flies: "
        + (", ".join(feixing_bits) if feixing_bits else "—")
        + ".",
    )
    if self_bits:
        feixing_body += L(
            "盘中自化：" + "、".join(self_bits[:8]) + "。自化禄权偏自我驱动，自化忌宜防执念内耗。",
            " Self-mutagens: " + ", ".join(self_bits[:8]) + ".",
        )
    else:
        feixing_body += L(
            "本盘显著自化不多，宫际飞化牵动更明显，宜结合流年再看应期。",
            " Few self-mutagens; inter-palace flies matter more with annual timing.",
        )
    sections.append({"title": L("飞星解读", "Flying-star reading"), "body": feixing_body})

    # —— 综合 ——
    dec = chart.get("decadals") or []
    d0 = dec[0] if dec else {}
    sections.append(
        {
            "title": L("综合要点", "Synthesis"),
            "body": L(
                "读盘顺序建议：先三合看格局骨架 → 再四化看先天喜忌 → 再飞星看宫际连动。"
                f"大限由命宫起{'顺行' if chart.get('decadal_forward') else '逆行'}，"
                f"第一大限约在{d0.get('palace') or '—'}（{d0.get('start_age') or '—'}–{d0.get('end_age') or '—'}岁）。"
                "以上为基础规则解读；更细的组合与文笔可用 AI 深批展开。仅供参考。",
                "Order: San He structure → Si Hua mutagens → Flying links. Reference only.",
            ),
        }
    )
    return {"ok": True, "sections": sections}


def build_ziwei_local_reading(chart: Dict[str, Any], *, lang: str = "zh") -> Dict[str, Any]:
    """兼容旧名 → 基础解读。"""
    return build_ziwei_basic_reading(chart, lang=lang)


def format_ziwei_theory_markdown(lang: str = "zh") -> str:
    if lang == "en":
        return """
#### What Zi Wei Dou Shu is
A natal chart system that maps birth data onto **12 palaces** (Life, Siblings, Spouse, Children, Wealth, Health, Travel, Friends, Career, Property, Fortune, Parents). Stars and **mutagens (四化)** describe themes and timing.

#### Four layers
1. **Chart setup** — lunar month/day & hour → Life/Body palaces → Five-Element board → place Zi Wei & other stars  
2. **Stars** — 14 majors (紫微、天机、太阳…) plus auxiliaries; brightness (庙旺利陷) matters  
3. **Palaces & mutagens** — palaces = life areas; 禄权科忌 = gain / power / fame / stress  
4. **Timing** — decades (大限), years (流年), months — read natal + decadal + annual together  

#### Vs BaZi
BaZi emphasizes stems/branches, Ten Gods and favorable elements. Zi Wei emphasizes palace storytelling + star combinations + mutagen timing.
""".strip()

    body = """
#### 紫微斗数在讲什么
以出生年月日时排出一张命盘：把人生分成 **12 宫**（命、兄弟、夫妻、子女、财帛、疾厄、迁移、交友、官禄、田宅、福德、父母），看各宫星曜与组合，论性格、事业、感情、财运等。

#### 四层结构
1. **定盘**：农历月日与时辰 → 命宫/身宫 → 五行局 → 安紫微等星  
2. **星曜**：十四主星（紫微、天机、太阳、武曲、天同、廉贞、天府、太阴、贪狼、巨门、天相、天梁、七杀、破军）为主干，辅星补细节；星有庙旺利陷  
3. **宫位与四化**：宫位回答「看哪一块人生」；**禄权科忌**回答加强与挂碍  
4. **大限 / 流年**：静态看先天格局，动态看十年与流年应期；实务常叠看「本命 + 大限 + 流年」

#### 和八字的差别
- **八字**：干支五行、十神、喜用、大运流年  
- **紫微**：宫位叙事 + 星曜组合 + 四化应期，更像十二个生活领域的剧本
""".strip()
    if lang == "zh_hant":
        from zh_convert import to_traditional

        return to_traditional(body)
    return body


# 方格盘地支位置（文墨天机式固定地盘）：4x4，中宫 2x2
#   巳 午 未 申
#   辰 [中] 酉
#   卯 [中] 戌
#   寅 丑 子 亥
_GRID_ZHI_ORDER = [
    "巳", "午", "未", "申",
    "辰", None, None, "酉",
    "卯", None, None, "戌",
    "寅", "丑", "子", "亥",
]

_SIHUA_MARK = {
    "化禄": ("禄", "#2E7D32"),
    "化权": ("权", "#6A1B9A"),
    "化科": ("科", "#1565C0"),
    "化忌": ("忌", "#C62828"),
}


def render_ziwei_chart_html(
    chart: Dict[str, Any],
    *,
    mode: str = "sihua",
    lang: str = "zh",
    include_title: bool = False,
) -> str:
    """文墨天机式十二宫方格盘。mode: sihua | sanhe | feixing。"""
    en = lang == "en"
    mode = (mode or "sihua").lower()
    if mode in ("四化",):
        mode = "sihua"
    elif mode in ("三合",):
        mode = "sanhe"
    elif mode in ("飞星", "飛星"):
        mode = "feixing"

    def esc(s: Any) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def loc(zh: str, en_s: str) -> str:
        text = en_s if en else zh
        if lang == "zh_hant":
            from zh_convert import to_traditional

            return to_traditional(text)
        return text

    if not chart.get("ok"):
        return f"<p>{esc(loc('排盘失败', 'Chart failed'))}</p>"

    mode_label = {
        "sihua": loc("四化", "Si Hua"),
        "sanhe": loc("三合", "San He"),
        "feixing": loc("飞星", "Flying Stars"),
    }.get(mode, loc("四化", "Si Hua"))

    sihua = chart.get("sihua") or []
    sf_names = set(ming_sanfang_sizheng(chart))
    fly_rows = compute_palace_fly(chart)
    fly_by_palace = {r["from_palace"]: r for r in fly_rows}
    natal_sihua_at = {}
    for x in sihua:
        natal_sihua_at.setdefault(x["palace"], []).append(x)

    # 大限年龄挂到宫
    dec_by_palace = {}
    for d in chart.get("decadals") or []:
        dec_by_palace[d.get("palace")] = d

    by_zhi = {p.get("zhi"): p for p in (chart.get("palaces") or [])}

    def star_html(s: dict, *, major: bool) -> str:
        name = esc(s.get("name") or "")
        sihua_tag = s.get("sihua") or ""
        mark = ""
        if sihua_tag in _SIHUA_MARK:
            short, color = _SIHUA_MARK[sihua_tag]
            mark = (
                f"<sup style='color:{color};font-weight:700;margin-left:1px;'>"
                f"{esc(loc(short, short))}</sup>"
            )
        bright = s.get("brightness") or ""
        bright_s = f"<span style='opacity:0.55;font-size:0.7em;'>/{esc(bright)}</span>" if bright and major else ""
        weight = "700" if major else "500"
        size = "0.95rem" if major else "0.78rem"
        color = "#111" if major else "#455A64"
        return (
            f"<span style='display:inline-block;margin:0 4px 2px 0;font-weight:{weight};"
            f"font-size:{size};color:{color};'>{name}{bright_s}{mark}</span>"
        )

    def palace_cell(zhi: str) -> str:
        p = by_zhi.get(zhi) or {}
        pname = p.get("name") or zhi
        gan = p.get("gan") or ""
        majors = "".join(star_html(s, major=True) for s in (p.get("majors") or []))
        minors = "".join(star_html(s, major=False) for s in (p.get("minors") or []))
        if not majors and not minors:
            majors = f"<span style='opacity:0.45;'>{esc(loc('空宫', 'empty'))}</span>"

        # 高亮
        hl = False
        accent = ""
        if mode == "sihua":
            hl = pname in natal_sihua_at
            if hl:
                accent = "、".join(f"{x['star']}{x['type']}" for x in natal_sihua_at[pname])
        elif mode == "sanhe":
            hl = pname in sf_names
            if hl:
                if p.get("is_ming"):
                    accent = loc("命·本宫", "Life")
                elif _fix(_yin_idx_of_zhi(zhi) - int(chart.get("soul_index") or 0)) == 6:
                    accent = loc("对宫", "Opp")
                else:
                    accent = loc("三合", "Trine")
        else:
            fr = fly_by_palace.get(pname)
            if fr:
                accent = " ".join(
                    f"{it['type'][1:] if str(it['type']).startswith('化') else it['type']}→{it['to_palace']}"
                    + ("*" if it["self"] else "")
                    for it in fr["flies"]
                )
            hl = pname == "命宫" or bool(fr and any(it["self"] for it in fr["flies"]))

        dec = dec_by_palace.get(pname) or {}
        age = ""
        if dec:
            age = f"{dec.get('start_age')}~{dec.get('end_age')}"

        tags = []
        if p.get("is_ming"):
            tags.append(loc("命", "命"))
        if p.get("is_shen"):
            tags.append(loc("身", "身"))
        tag_s = ("·".join(tags)) if tags else ""

        bg = "#FFF8E1" if hl else "#FAFAFA"
        border = "#F9A825" if hl else "#B0BEC5"
        name_color = "#C62828" if p.get("is_ming") else "#1565C0"

        return (
            f"<div style='border:1.5px solid {border};background:{bg};padding:6px 7px;"
            f"min-height:118px;display:flex;flex-direction:column;justify-content:space-between;"
            f"box-sizing:border-box;'>"
            f"<div style='line-height:1.35;'>{majors}<div style='margin-top:2px;'>{minors}</div>"
            f"{('<div style=\"margin-top:4px;font-size:0.72rem;color:#6D4C41;\">' + esc(accent) + '</div>') if accent else ''}"
            f"</div>"
            f"<div style='display:flex;justify-content:space-between;align-items:flex-end;"
            f"gap:4px;margin-top:6px;font-size:0.78rem;'>"
            f"<span style='opacity:0.75;'>{esc(age)}</span>"
            f"<span style='text-align:right;'>"
            f"<span style='color:{name_color};font-weight:700;'>{esc(pname)}"
            f"{('·' + esc(tag_s)) if tag_s else ''}</span><br/>"
            f"<span style='opacity:0.8;'>{esc(gan)}{esc(zhi)}</span>"
            f"</span></div></div>"
        )

    # 中宫
    sihua_line = "、".join(f"{x['star']}{x['type']}" for x in sihua) if sihua else "—"
    center = (
        "<div style='border:1.5px solid #90A4AE;background:linear-gradient(180deg,#ECEFF1,#FAFAFA);"
        "padding:10px 12px;height:100%;min-height:248px;box-sizing:border-box;"
        "display:flex;flex-direction:column;justify-content:center;gap:6px;'>"
        f"<div style='font-weight:700;font-size:1.05rem;color:#0B1F33;'>"
        f"{esc(chart.get('name') or loc('命主', 'Native'))}</div>"
        f"<div style='font-size:0.9rem;'>{esc(chart.get('gender') or '')} · "
        f"{esc(chart.get('ju_name') or '')}</div>"
        f"<div style='font-size:0.85rem;opacity:0.9;'>"
        f"{esc((chart.get('lunar') or {}).get('label') or '')} "
        f"{esc(chart.get('hour_zhi') or '')}{esc(loc('时', ' hour'))}</div>"
        f"<div style='font-size:0.85rem;'>"
        f"{esc(loc('命宫', 'Life'))} {esc(chart.get('ming_ganzhi') or '')} · "
        f"{esc(loc('身宫', 'Body'))} {esc(chart.get('shen_palace') or '')}</div>"
        f"<div style='font-size:0.8rem;margin-top:4px;'>"
        f"{esc(loc('视角', 'View'))}：<b>{esc(mode_label)}</b></div>"
        f"<div style='font-size:0.78rem;color:#4E342E;line-height:1.4;'>"
        f"{esc(loc('生年四化', 'Natal Si Hua'))}：{esc(sihua_line)}</div>"
        f"<div style='font-size:0.72rem;opacity:0.75;margin-top:2px;'>"
        f"{esc(loc('禄绿·权紫·科蓝·忌红', 'Lu green · Quan purple · Ke blue · Ji red'))}"
        f"</div></div>"
    )

    # 组装 4x4：中宫占 (1,1)-(2,2) 在 0-index 的格子 5,6,9,10
    cells_html: List[str] = []
    center_placed = False
    for i, zhi in enumerate(_GRID_ZHI_ORDER):
        row, col = divmod(i, 4)
        if zhi is None:
            if not center_placed and row == 1 and col == 1:
                cells_html.append(
                    f"<div style='grid-column:2 / span 2;grid-row:2 / span 2;'>{center}</div>"
                )
                center_placed = True
            continue
        cells_html.append(palace_cell(zhi))

    blocks: List[str] = []
    if include_title:
        blocks.append(f"<h3>{esc(loc('紫微命盘', 'Zi Wei Chart'))}</h3>")

    # 模式短注
    if mode == "sihua":
        hint = loc("四化盘：高亮生年禄权科忌所在宫；星旁色标为四化。", "Si Hua: highlighted palaces hold natal mutagens.")
    elif mode == "sanhe":
        hint = loc(
            "三合盘：高亮命宫三方四正（" + "、".join(ming_sanfang_sizheng(chart)) + "）。",
            "San He: Life trine/opposite highlighted.",
        )
    else:
        hint = loc("飞星盘：宫内小字为该宫天干飞出；* 为自化。", "Flying Stars: small text = flies out; * = self.")

    blocks.append(f"<p style='font-size:0.85rem;margin:0.2rem 0 0.55rem;'>{esc(hint)}</p>")
    blocks.append(
        "<div style='width:100%;max-width:920px;margin:0 auto;"
        "display:grid;grid-template-columns:repeat(4,minmax(0,1fr));"
        "grid-template-rows:repeat(4,minmax(118px,auto));gap:3px;"
        "background:#90A4AE;padding:3px;border-radius:4px;'>"
        + "".join(cells_html)
        + "</div>"
    )

    # 大限条
    dec = chart.get("decadals") or []
    if dec:
        bits = [
            f"{d.get('start_age')}~{d.get('end_age')} {d.get('palace')}({d.get('zhi')})"
            for d in dec[:6]
        ]
        blocks.append(
            "<p style='font-size:0.8rem;margin:0.55rem 0 0.2rem;opacity:0.85;'>"
            + esc(loc("大限：", "Decades: ") + " · ".join(bits) + " …")
            + "</p>"
        )
    return "\n".join(blocks)


def render_ziwei_reading_html(
    reading: Dict[str, Any],
    *,
    lang: str = "zh",
    include_title: bool = False,
) -> str:
    """基础解读 HTML。默认不含外层标题。"""
    def esc(s: Any) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    blocks: List[str] = []
    if include_title:
        title = "Basic reading" if lang == "en" else "基础解读"
        if lang == "zh_hant":
            from zh_convert import to_traditional

            title = to_traditional(title)
        blocks.append(f"<h3>{esc(title)}</h3>")
    for sec in reading.get("sections") or []:
        t = sec.get("title") or ""
        b = sec.get("body") or ""
        if lang == "zh_hant":
            from zh_convert import to_traditional

            t, b = to_traditional(t), to_traditional(b)
        blocks.append(f"<h4 style='margin:0.8rem 0 0.35rem;'>{esc(t)}</h4>")
        blocks.append(f"<p style='margin:0.2rem 0 0.6rem;'>{esc(b)}</p>")
    return "\n".join(blocks)


def chart_summary_for_ai(chart: Dict[str, Any]) -> str:
    """压缩命盘文本供 DeepSeek（含四化/三合/飞星要点）。"""
    lines = [
        f"姓名:{chart.get('name')} 性别:{chart.get('gender')}",
        f"公历:{chart.get('solar_date')} 时:{chart.get('birth_hour')}:{chart.get('birth_minute')} "
        f"农历:{(chart.get('lunar') or {}).get('label')} 时支:{chart.get('hour_zhi')}",
        f"命宫:{chart.get('ming_ganzhi')} 身宫:{chart.get('shen_palace')} 局:{chart.get('ju_name')}",
        f"紫微:{chart.get('ziwei_zhi')} 天府:{chart.get('tianfu_zhi')}",
        "【四化】生年:"
        + "、".join(f"{x['star']}{x['type']}@{x['palace']}" for x in (chart.get("sihua") or [])),
        "【三合】命宫三方四正:" + "、".join(ming_sanfang_sizheng(chart)),
    ]
    ming_fly = next((r for r in compute_palace_fly(chart) if r["from_palace"] == "命宫"), None)
    if ming_fly:
        lines.append(
            "【飞星】命宫飞出:"
            + "、".join(
                f"{it['star']}{it['type']}→{it['to_palace']}"
                + ("(自化)" if it["self"] else "")
                for it in ming_fly["flies"]
            )
        )
    lines.append("十二宫:")
    by_name = {p["name"]: p for p in chart.get("palaces") or []}
    for pname in PALACE_NAMES:
        p = by_name.get(pname) or {}
        lines.append(f"- {pname}({p.get('gan')}{p.get('zhi')}): {_star_line(p)}")
    return "\n".join(lines)


# --- PDF export ---

def ziwei_pdf_filename(name: str = "") -> str:
    """紫微 PDF 文件名。"""
    import re
    from datetime import datetime

    raw = str(name or "user").strip()
    safe = re.sub(r'[\\/:*?"<>|\s]+', "_", raw).strip("_") or "user"
    return f"ZiWei_{safe[:40]}_{datetime.now():%Y%m%d}.pdf"


def generate_ziwei_pdf_report(
    chart: dict,
    reading: dict,
    *,
    ai_deep: Optional[dict] = None,
    lang: str = "zh",
):
    """紫微斗数 PDF：封面 + 命盘摘要 + 本地解读 +（可选）AI 深批。"""
    import io
    import re
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    from report_generator import ReportGenerator
    from utils import _cjk_font_file, _pdf_text_image, _resolve_pdf_cjk_font

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
    cover_title = "Sigma Fate Zi Wei Report" if en else T("六西格玛命理 · 紫微斗数报告")
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title=cover_title,
        author=str((chart or {}).get("name") or "user"),
    )
    styles = getSampleStyleSheet()
    style_h1 = ParagraphStyle(
        "ZW1", parent=styles["Normal"], fontName=font_head, fontSize=18, leading=26,
        spaceBefore=6, spaceAfter=10, textColor="#0B1F33",
    )
    style_h2 = ParagraphStyle(
        "ZW2", parent=styles["Normal"], fontName=font_head, fontSize=13, leading=20,
        spaceBefore=12, spaceAfter=6, textColor="#1565C0",
    )
    style_body = ParagraphStyle(
        "ZWB", parent=styles["Normal"], fontName=font_body, fontSize=10.5, leading=17,
        alignment=TA_JUSTIFY, spaceAfter=8,
    )
    style_meta = ParagraphStyle(
        "ZWM", parent=styles["Normal"], fontName=font_body, fontSize=11, leading=18,
        alignment=TA_CENTER, spaceAfter=6,
    )
    content_width = A4[0] - 3.6 * cm
    story = []

    def _pdf_safe(text: str) -> str:
        return str(text or "").replace("⚠️", "").replace("★", "*")

    def P(text: str, style=style_body):
        raw = _pdf_safe(str(text or "").strip())
        if not en:
            raw = T(raw)
        if not raw:
            return None
        if use_pil:
            img = _pdf_text_image(
                raw,
                font_path=cjk_path,
                max_width_pt=content_width,
                font_size=11 if style == style_body else (16 if style == style_h1 else 13),
                fill="#0B1F33" if style != style_body else "#222222",
                align="center" if style == style_meta else "left",
            )
            if img is not None:
                return img
        return Paragraph(raw.replace("\n", "<br/>"), style)

    def add(text, style=style_body):
        node = P(text, style=style)
        if node is not None:
            story.append(node)

    name = (chart or {}).get("name") or ("Native" if en else "命主")
    add(cover_title, style_h1)
    add(
        f"{name} · {chart.get('gender')} · {chart.get('solar_date')} "
        f"{int(chart.get('birth_hour') or 0):02d}:{int(chart.get('birth_minute') or 0):02d}",
        style_meta,
    )
    add(
        f"{(chart.get('lunar') or {}).get('label')} · {chart.get('ju_name')} · "
        f"{'命宫' if not en else 'Life'} {chart.get('ming_ganzhi')} · "
        f"{'身宫' if not en else 'Body'} {chart.get('shen_palace')}",
        style_meta,
    )
    story.append(Spacer(1, 0.3 * cm))

    add("命盘十二宫" if not en else "Twelve palaces", style_h1)
    by_name = {p["name"]: p for p in (chart.get("palaces") or [])}
    for pname in PALACE_NAMES:
        p = by_name.get(pname) or {}
        majors = "、".join(
            s["name"] + (f"({s.get('brightness')})" if s.get("brightness") else "") + (s.get("sihua") or "")
            for s in (p.get("majors") or [])
        ) or "—"
        minors = "、".join(
            s["name"] + (s.get("sihua") or "") for s in (p.get("minors") or [])
        ) or "—"
        add(f"{pname}（{p.get('gan')}{p.get('zhi')}）主星：{majors}；辅星：{minors}")

    sihua = chart.get("sihua") or []
    if sihua:
        add("生年四化" if not en else "Natal mutagens", style_h2)
        add("、".join(f"{x['star']}{x['type']}（{x['palace']}）" for x in sihua))

    add("基础解读" if not en else "Basic reading", style_h1)
    for sec in (reading or {}).get("sections") or []:
        add(sec.get("title") or "", style_h2)
        add(sec.get("body") or "")

    if isinstance(ai_deep, dict) and any(ai_deep.values()):
        add("AI 深批" if not en else "AI deep read", style_h1)
        add(
            "以下为 AI 深批，理性参考，勿作宿命断言。"
            if not en
            else "AI deep read for reflection — not destiny."
        )
        for key, fallback in (
            ("pattern", "命格总论" if not en else "Natal Pattern"),
            ("career", "事业财运" if not en else "Career & Wealth"),
            ("life", "感情身心" if not en else "Love, Health & Mind"),
        ):
            sec = ai_deep.get(key)
            if not sec:
                continue
            page = dict(sec) if isinstance(sec, dict) else {"content": str(sec)}
            title = page.get("title") or fallback
            add(title, style_h2)
            pro = page.get("professional") or []
            if isinstance(pro, str):
                pro = [pro]
            for para in pro:
                if str(para).strip():
                    add(str(para).strip())
            plain = page.get("plain") or {}
            if isinstance(plain, dict):
                if plain.get("summary"):
                    add(("一句话：" if not en else "Summary: ") + str(plain.get("summary")))
                for i, pt in enumerate(plain.get("points") or [], 1):
                    add(f"{i}. {pt}")
                if plain.get("detail"):
                    add(str(plain.get("detail")))
            elif page.get("content"):
                content = re.sub(r"[#*`]+", "", str(page.get("content") or ""))
                if not ReportGenerator._looks_like_json_blob(content):
                    add(content)

    add(
        "仅供参考：紫微斗数本地规则 +（可选）AI 文笔，不构成人生决定依据。"
        if not en
        else "Reference only — not a life decision.",
        style_body,
    )
    doc.build(story)
    buffer.seek(0)
    return buffer
