"""
紫微斗数排盘（本地）

安星规则对齐主流中州/常见软件口径（参考 iztro 同类算法）：
- 寅宫为 0 起算
- 顺数生月、逆数生时安命；顺数生时安身
- 五虎遁起寅首 → 命宫干支 → 五行局
- 局数除日数起紫微，对宫安天府，再布十四主星、六吉六煞、杂曜、四化
- 另安长生十二神、博士十二神、小限年龄
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

# 六吉 / 六煞（盘面着色）
_SOFT_STARS = {
    "左辅",
    "右弼",
    "文昌",
    "文曲",
    "天魁",
    "天钺",
    "禄存",
    "天马",
    "红鸾",
    "天喜",
}
_TOUGH_STARS = {"擎羊", "陀罗", "火星", "铃星", "地空", "地劫"}

_CHANGSHENG12 = [
    "长生",
    "沐浴",
    "冠带",
    "临官",
    "帝旺",
    "衰",
    "病",
    "死",
    "墓",
    "绝",
    "胎",
    "养",
]
_BOSHI12 = [
    "博士",
    "力士",
    "青龙",
    "小耗",
    "将军",
    "奏书",
    "飞廉",
    "喜神",
    "病符",
    "大耗",
    "伏兵",
    "官府",
]

# 长生起点（寅起索引）：水二/土五→申，木三→亥，金四→巳，火六→寅
_CHANGSHENG_START = {2: 6, 3: 9, 4: 3, 5: 6, 6: 0}

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
                "is_laiyin": gan == year_gan,
                "majors": [],
                "minors": [],
                "adjectives": [],
                "sihua": [],
                "changsheng": "",
                "boshi": "",
                "ages": [],
            }
        )

    def add_major(yin_i: int, star: str) -> None:
        palaces[yin_i]["majors"].append(
            {"name": star, "brightness": _brightness(star, yin_i), "type": "major"}
        )

    def add_minor(yin_i: int, star: str) -> None:
        kind = "soft" if star in _SOFT_STARS else ("tough" if star in _TOUGH_STARS else "minor")
        palaces[yin_i]["minors"].append({"name": star, "type": kind})

    def add_adj(yin_i: int, star: str) -> None:
        palaces[_fix(yin_i)]["adjectives"].append({"name": star, "type": "adjective"})

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

    # —— 杂曜 ——
    # 台辅 / 封诰（时系）
    add_adj(_fix(_yin_idx_of_zhi("午") + time_index), "台辅")
    add_adj(_fix(_yin_idx_of_zhi("寅") + time_index), "封诰")

    # 月系：天刑、天姚、解神、阴煞、天月、天巫
    m0 = month_for_palace - 1
    add_adj(_fix(_yin_idx_of_zhi("酉") + m0), "天刑")
    add_adj(_fix(_yin_idx_of_zhi("丑") + m0), "天姚")
    yuejie_map = ["申", "戌", "子", "寅", "辰", "午"]
    add_adj(_yin_idx_of_zhi(yuejie_map[m0 // 2]), "解神")
    yinsha_map = ["寅", "子", "戌", "申", "午", "辰"]
    add_adj(_yin_idx_of_zhi(yinsha_map[m0 % 6]), "阴煞")
    tianyue_map = ["戌", "巳", "辰", "寅", "未", "卯", "亥", "未", "寅", "午", "戌", "寅"]
    add_adj(_yin_idx_of_zhi(tianyue_map[m0]), "天月")
    tianwu_map = ["巳", "申", "寅", "亥"]
    add_adj(_yin_idx_of_zhi(tianwu_map[m0 % 4]), "天巫")

    # 日系：三台八座、恩光天贵（初一=0）
    day_i = max(0, ld - 1)
    add_adj(_fix(zuo + day_i), "三台")
    add_adj(_fix(you - day_i), "八座")
    add_adj(_fix(chang + day_i - 1), "恩光")
    add_adj(_fix(qu + day_i - 1), "天贵")

    # 年系杂曜
    yz = DIZHI.index(year_zhi) if year_zhi in DIZHI else 0
    yg = TIANGAN.index(year_gan) if year_gan in TIANGAN else 0

    # 华盖 / 咸池
    huagai_xianchi = {
        frozenset({"寅", "午", "戌"}): ("戌", "卯"),
        frozenset({"申", "子", "辰"}): ("辰", "酉"),
        frozenset({"巳", "酉", "丑"}): ("丑", "午"),
        frozenset({"亥", "卯", "未"}): ("未", "子"),
    }
    for group, (hg, xc) in huagai_xianchi.items():
        if year_zhi in group:
            add_adj(_yin_idx_of_zhi(hg), "华盖")
            add_adj(_yin_idx_of_zhi(xc), "咸池")
            break

    # 孤辰寡宿
    guchen_guasu = {
        frozenset({"寅", "卯", "辰"}): ("巳", "丑"),
        frozenset({"巳", "午", "未"}): ("申", "辰"),
        frozenset({"申", "酉", "戌"}): ("亥", "未"),
        frozenset({"亥", "子", "丑"}): ("寅", "戌"),
    }
    for group, (gc, gs) in guchen_guasu.items():
        if year_zhi in group:
            add_adj(_yin_idx_of_zhi(gc), "孤辰")
            add_adj(_yin_idx_of_zhi(gs), "寡宿")
            break

    # 天才天寿
    add_adj(_fix(soul_index + yz), "天才")
    add_adj(_fix(body_index + yz), "天寿")

    # 破碎 / 蜚廉 / 龙池凤阁 / 天哭天虚
    posui = ["巳", "丑", "酉"][yz % 3]
    add_adj(_yin_idx_of_zhi(posui), "破碎")
    feilian = ["申", "酉", "戌", "巳", "午", "未", "寅", "卯", "辰", "亥", "子", "丑"][yz]
    add_adj(_yin_idx_of_zhi(feilian), "蜚廉")
    add_adj(_fix(_yin_idx_of_zhi("辰") + yz), "龙池")
    add_adj(_fix(_yin_idx_of_zhi("戌") - yz), "凤阁")
    add_adj(_fix(_yin_idx_of_zhi("午") - yz), "天哭")
    add_adj(_fix(_yin_idx_of_zhi("午") + yz), "天虚")

    # 天官天福 / 天厨
    tianguan = ["未", "辰", "巳", "寅", "卯", "酉", "亥", "酉", "戌", "午"][yg]
    tianfu_adj = ["酉", "申", "子", "亥", "卯", "寅", "午", "巳", "午", "巳"][yg]
    tianchu = ["巳", "午", "子", "巳", "午", "申", "寅", "午", "酉", "亥"][yg]
    add_adj(_yin_idx_of_zhi(tianguan), "天官")
    add_adj(_yin_idx_of_zhi(tianfu_adj), "天福")
    add_adj(_yin_idx_of_zhi(tianchu), "天厨")

    # 天德月德 / 天空 / 截路空亡 / 旬空 / 年解
    add_adj(_fix(_yin_idx_of_zhi("酉") + yz), "天德")
    add_adj(_fix(_yin_idx_of_zhi("巳") + yz), "月德")
    add_adj(_fix(_yin_idx_of_zhi(year_zhi) + 1), "天空")
    jielu = ["申", "午", "辰", "寅", "子"][yg % 5]
    kongwang = ["酉", "未", "巳", "卯", "丑"][yg % 5]
    add_adj(_yin_idx_of_zhi(jielu), "截路")
    add_adj(_yin_idx_of_zhi(kongwang), "空亡")
    xunkong = _fix(_yin_idx_of_zhi(year_zhi) + (9 - yg) + 1)
    if (yz % 2) != (xunkong % 2):
        xunkong = _fix(xunkong + 1)
    add_adj(xunkong, "旬空")
    nianjie = ["戌", "酉", "申", "未", "午", "巳", "辰", "卯", "寅", "丑", "子", "亥"][yz]
    add_adj(_yin_idx_of_zhi(nianjie), "年解")

    # 天伤天使（通行：奴仆/交友、疾厄）
    add_adj(_fix(soul_index + 5), "天伤")
    add_adj(_fix(soul_index + 7), "天使")

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
    # 虚岁 → 公历年近似：出生年 + 虚岁 - 1（与常见排盘软件一致）
    birth_year = int(birth_date.year)
    decadals = []
    for i in range(12):
        idx = _fix(soul_index + i) if forward else _fix(soul_index - i)
        start_age = ju_num + 10 * i
        end_age = start_age + 9
        start_year = birth_year + start_age - 1
        end_year = birth_year + end_age - 1
        decadals.append(
            {
                "palace": palaces[idx]["name"],
                "zhi": palaces[idx]["zhi"],
                "start_age": start_age,
                "end_age": end_age,
                "start_year": start_year,
                "end_year": end_year,
            }
        )
        palaces[idx]["decadal"] = {
            "start_age": start_age,
            "end_age": end_age,
            "start_year": start_year,
            "end_year": end_year,
        }

    # 长生十二神
    cs_start = _CHANGSHENG_START.get(ju_num, 0)
    for i, name_cs in enumerate(_CHANGSHENG12):
        idx = _fix(cs_start + i) if forward else _fix(cs_start - i)
        palaces[idx]["changsheng"] = name_cs

    # 博士十二神（自禄存起）
    for i, name_bs in enumerate(_BOSHI12):
        idx = _fix(lu_i + i) if forward else _fix(lu_i - i)
        palaces[idx]["boshi"] = name_bs

    # 小限年龄：寅午戌辰起，申子辰戌起，巳酉丑未起，亥卯未丑起；男顺女逆
    if year_zhi in ("寅", "午", "戌"):
        age_start = _yin_idx_of_zhi("辰")
    elif year_zhi in ("申", "子", "辰"):
        age_start = _yin_idx_of_zhi("戌")
    elif year_zhi in ("巳", "酉", "丑"):
        age_start = _yin_idx_of_zhi("未")
    else:
        age_start = _yin_idx_of_zhi("丑")
    male = gender_norm == "男"
    for i in range(12):
        idx = _fix(age_start + i) if male else _fix(age_start - i)
        palaces[idx]["ages"] = [12 * j + i + 1 for j in range(8)]

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
    adjs = [s["name"] for s in (p.get("adjectives") or [])]
    bits = majors + minors + adjs
    return "、".join(bits) if bits else "（空宫）"


def _star_palace_map(chart: Dict[str, Any]) -> Dict[str, str]:
    """星名 → 所在宫名。"""
    out: Dict[str, str] = {}
    for p in chart.get("palaces") or []:
        for s in (p.get("majors") or []) + (p.get("minors") or []) + (p.get("adjectives") or []):
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


def _domain_palace_note(chart: Dict[str, Any], pname: str, *, lang: str = "zh") -> str:
    """单宫一句：干支 + 主辅星 + 四化。"""
    en = lang == "en"
    p = _palace_by_name(chart, pname) or {}
    if not p:
        return ""
    line = _star_line(p)
    gz = f"{p.get('gan') or ''}{p.get('zhi') or ''}"
    if en:
        return f"{pname}({gz}): {line}."
    return f"{pname}（{gz}）星曜：{line}。"


def build_ziwei_basic_reading(chart: Dict[str, Any], *, lang: str = "zh") -> Dict[str, Any]:
    """基础解读：读盘顺序 三合→四化→飞星→大限，再事业/财运/感情/健康。"""
    en = lang == "en"
    if not chart.get("ok"):
        return {"ok": False, "sections": []}

    def L(zh: str, en_s: str) -> str:
        return en_s if en else zh

    def add(sec_id: str, title: str, body: str) -> None:
        sections.append({"id": sec_id, "title": title, "body": body})

    sections: List[Dict[str, str]] = []
    ming = _palace_by_name(chart, "命宫") or {}
    add(
        "overview",
        L("命盘总览", "Chart overview"),
        L(
            f"{chart.get('name') or '命主'}，{chart.get('gender')}，"
            f"{(chart.get('lunar') or {}).get('label')}，{chart.get('ju_name')}；"
            f"命宫{ming.get('gan')}{ming.get('zhi')}，身宫{chart.get('shen_palace')}；"
            f"紫微在{chart.get('ziwei_zhi')}，天府在{chart.get('tianfu_zhi')}。"
            "下文按「三合→四化→飞星→大限→事业/财运/感情/健康」展开。",
            f"{chart.get('name') or 'Native'}, {chart.get('ju_name')}, "
            f"Life {ming.get('gan')}{ming.get('zhi')}. Order: San He → Si Hua → Flying → Decades → life areas.",
        ),
    )

    # —— 1 三合 ——
    sf_names = ming_sanfang_sizheng(chart)
    sf_bits = []
    for n in sf_names:
        p = _palace_by_name(chart, n) or {}
        majors = "、".join(s["name"] for s in (p.get("majors") or [])) or L("无主星", "no major")
        sf_bits.append(f"{n}（{p.get('gan')}{p.get('zhi')}）主星{majors}")
    soft_n = tough_n = 0
    for n in sf_names:
        p = _palace_by_name(chart, n) or {}
        for s in p.get("minors") or []:
            if s.get("type") == "soft":
                soft_n += 1
            elif s.get("type") == "tough":
                tough_n += 1
    sanhe_body = L(
        "【三合】先看命宫三方四正（本宫、三合宫、对宫）的主星气势，判断格局骨架。"
        + "；".join(sf_bits)
        + f"。三方吉曜约{soft_n}、煞曜约{tough_n}；吉多则偏开扬，煞多或空宫宜稳健经营。",
        "[San He] Life trine/opposite: " + "; ".join(sf_bits) + ".",
    )
    for pname in ("命宫", "官禄", "财帛", "夫妻"):
        note = _domain_palace_note(chart, pname, lang=lang)
        if note:
            sanhe_body += " " + note
    add("sanhe", L("三合解读", "San He reading"), sanhe_body)

    # —— 2 四化 ——
    sihua = chart.get("sihua") or []
    sihua_body = L(
        "【四化】以生年天干定禄权科忌：禄偏机遇、权偏主导、科偏名声文书、忌偏挂碍功课。",
        "[Si Hua] Year-stem mutagens: Lu=gain, Quan=power, Ke=fame, Ji=stress.",
    )
    if sihua:
        sihua_body += L(
            "生年四化落点："
            + "；".join(f"{x['star']}{x['type']}→{x['palace']}" for x in sihua)
            + "。",
            " Natal: " + "; ".join(f"{x['star']}{x['type']}→{x['palace']}" for x in sihua) + ".",
        )
        for x in sihua:
            tip = {
                "化禄": L("宜把握资源与机会窗口。", " Favor openings there."),
                "化权": L("宜主动担责与推进。", " Favor taking charge."),
                "化科": L("宜文书考试与形象经营。", " Favor reputation/docs."),
                "化忌": L("宜当作长期功课，非宿命判决。", " Treat as long-term focus, not fate."),
            }.get(x.get("type") or "", "")
            sihua_body += L(f"{x['type']}落{x['palace']}，{tip}", f"{x['type']}@{x['palace']}.{tip}")
    add("sihua", L("四化解读", "Si Hua reading"), sihua_body)

    # —— 3 飞星 ——
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
    key_fly_bits = []
    for pname in ("命宫", "官禄", "财帛", "夫妻"):
        fr = next((r for r in flies if r["from_palace"] == pname), None)
        if not fr:
            continue
        parts = []
        for it in fr["flies"]:
            short = (it["type"] or "").replace("化", "")
            parts.append(
                f"{short}→{it['to_palace']}" + ("*" if it["self"] else "")
            )
        key_fly_bits.append(f"{pname}：{' '.join(parts)}")
    feixing_body = L(
        "【飞星】各宫天干飞出禄权科忌，看宫际牵动；飞回本宫为自化。"
        f"命宫天干{ming.get('gan') or '—'}飞出："
        + ("、".join(feixing_bits) if feixing_bits else "—")
        + "。",
        "[Flying Stars] Life-palace stem flies: "
        + (", ".join(feixing_bits) if feixing_bits else "—")
        + ".",
    )
    if key_fly_bits:
        feixing_body += L(
            "重点宫飞出：" + "；".join(key_fly_bits) + "。",
            " Key flies: " + "; ".join(key_fly_bits) + ".",
        )
    if self_bits:
        feixing_body += L(
            "盘中自化：" + "、".join(self_bits[:8]) + "。自化禄权偏自我驱动，自化忌宜防执念内耗。",
            " Self-mutagens: " + ", ".join(self_bits[:8]) + ".",
        )
    add("feixing", L("飞星解读", "Flying-star reading"), feixing_body)

    # —— 4 大限 ——
    dec = chart.get("decadals") or []
    d0 = dec[0] if dec else {}
    d_now = None
    try:
        by = int(str(chart.get("solar_date") or "")[:4])
        from datetime import date as _date

        age_xu = max(1, _date.today().year - by + 1)
        for d in dec:
            if int(d.get("start_age") or 0) <= age_xu <= int(d.get("end_age") or 0):
                d_now = d
                break
    except Exception:
        d_now = None
    dec_bits = []
    for d in dec[:6]:
        dec_bits.append(
            f"{d.get('palace')}{d.get('start_age')}～{d.get('end_age')}岁"
            f"/{d.get('start_year')}～{d.get('end_year')}年"
        )
    decadal_body = L(
        "【大限】十年运应期：阳男阴女顺行、阴男阳女逆行。"
        f"大限由命宫起{'顺行' if chart.get('decadal_forward') else '逆行'}；"
        f"第一大限在{d0.get('palace') or '—'}（{d0.get('start_age') or '—'}～{d0.get('end_age') or '—'}岁"
        f"，约{d0.get('start_year') or '—'}～{d0.get('end_year') or '—'}年）。",
        f"[Decades] First decade at {d0.get('palace')}: "
        f"{d0.get('start_age')}–{d0.get('end_age')} / {d0.get('start_year')}–{d0.get('end_year')}.",
    )
    if d_now:
        decadal_body += L(
            f"当前约在{d_now.get('palace')}大限（{d_now.get('start_age')}～{d_now.get('end_age')}岁，"
            f"{d_now.get('start_year')}～{d_now.get('end_year')}年），宜把该宫议题当作现阶段主舞台。",
            f" Current decade: {d_now.get('palace')} "
            f"({d_now.get('start_age')}–{d_now.get('end_age')}).",
        )
    if dec_bits:
        decadal_body += L(" 前段大限：" + " · ".join(dec_bits) + "。", " Early decades: " + " · ".join(dec_bits) + ".")
    add("decadal", L("大限应期", "Decade timing"), decadal_body)

    # —— 5–8 事业 / 财运 / 感情 / 健康 ——
    def domain_body(title_zh: str, palaces: Tuple[str, ...], focus: str) -> str:
        bits = [_domain_palace_note(chart, n, lang=lang) for n in palaces]
        bits = [b for b in bits if b]
        # 四化牵动
        hits = [x for x in sihua if x.get("palace") in palaces]
        fly_hits = []
        for pname in palaces:
            fr = next((r for r in flies if r["from_palace"] == pname), None)
            if not fr:
                continue
            for it in fr["flies"][:2]:
                fly_hits.append(
                    f"{pname}{(it['type'] or '').replace('化','')}→{it['to_palace']}"
                    + ("*" if it["self"] else "")
                )
        body = L(f"【{title_zh}】{focus}", f"[{title_zh}] {focus}")
        if bits:
            body += " " + " ".join(bits)
        if hits:
            body += L(
                " 生年四化相关："
                + "；".join(f"{x['star']}{x['type']}@{x['palace']}" for x in hits)
                + "。",
                " Mutagens: " + "; ".join(f"{x['star']}{x['type']}@{x['palace']}" for x in hits) + ".",
            )
        if fly_hits:
            body += L(
                " 飞星牵动：" + "；".join(fly_hits[:6]) + "。",
                " Flies: " + "; ".join(fly_hits[:6]) + ".",
            )
        if d_now and d_now.get("palace") in palaces:
            body += L(
                f" 当前大限正落相关宫位（{d_now.get('palace')}），该领域更宜主动布局。",
                f" Current decade on {d_now.get('palace')} — prioritize this area.",
            )
        body += L(" 宜结合大限与流年看应期，理性参考。", " Time with decades/years; reference only.")
        return body

    add(
        "career",
        L("事业分析", "Career"),
        domain_body(
            "事业",
            ("官禄", "迁移", "交友", "命宫"),
            L(
                "以官禄为主、迁移看出外与平台、交友看同事部属、命宫看自我驱动力。",
                "Career from Career/Travel/Friends/Life palaces.",
            ),
        ),
    )
    add(
        "wealth",
        L("财运分析", "Wealth"),
        domain_body(
            "财运",
            ("财帛", "田宅", "福德", "官禄"),
            L(
                "以财帛看求财方式、田宅看资产沉淀、福德看花钱心态、官禄看以业生财。",
                "Wealth from Wealth/Property/Fortune/Career palaces.",
            ),
        ),
    )
    add(
        "love",
        L("感情分析", "Relationships"),
        domain_body(
            "感情",
            ("夫妻", "福德", "子女", "命宫"),
            L(
                "以夫妻看伴侣互动、福德看内心满足、子女看付出与创造、命宫看自身相处模式。",
                "Love from Spouse/Fortune/Children/Life palaces.",
            ),
        ),
    )
    add(
        "health",
        L("健康分析", "Health"),
        domain_body(
            "健康",
            ("疾厄", "父母", "命宫", "福德"),
            L(
                "以疾厄看体质压力出口、父母看作息家风与照护、命宫/福德看身心负荷与放松方式。",
                "Health from Health/Parents/Life/Fortune palaces.",
            ),
        ),
    )
    return {"ok": True, "sections": sections}


def build_ziwei_local_reading(chart: Dict[str, Any], *, lang: str = "zh") -> Dict[str, Any]:
    """兼容旧名 → 基础解读。"""
    return build_ziwei_basic_reading(chart, lang=lang)


def format_ziwei_theory_markdown(lang: str = "zh") -> str:
    if lang == "en":
        return """
#### What Zi Wei Dou Shu is
A natal chart maps birth data onto **12 palaces** (Life, Siblings, Spouse, Children, Wealth, Health, Travel, Friends, Career, Property, Fortune, Parents). Stars and **mutagens (四化)** describe themes and timing.

#### Palace decade (大限)
Each palace’s bottom-left ages/years are its **decade**: e.g. ages 6～15 (nominal), about years 1995～2004. One palace ≈ one ten-year chapter; direction depends on gender + year yin/yang.

#### Three chart views
1. **Si Hua (四化)** — year-stem mutagens 禄/权/科/忌 = gain / power / fame / stress. See which palace they land in.  
2. **San He (三合)** — Life palace + its trine + opposite (三方四正). Structure / pattern first.  
3. **Flying Stars (飞星)** — each palace has a stem that also flies 禄/权/科/忌 to where those stars sit (**fly path**). In the Flying Stars view, `禄→Wealth` means this palace’s stem flies Lu to Wealth; `*` = self-mutagen.

#### Read order
San He (structure) → Si Hua (natal mutagens) → Flying Stars (links) → decade ages for timing.
""".strip()

    body = """
#### 紫微斗数在讲什么
以出生年月日时排出一张命盘：把人生分成 **12 宫**（命、兄弟、夫妻、子女、财帛、疾厄、迁移、交友、官禄、田宅、福德、父母），看各宫星曜与组合，论性格、事业、感情、财运等。

#### 宫里大限解读
宫左下角的年龄与年份，就是该宫的 **大限**（十年运）。例如虚岁 6～15 岁，约对应公历 1995～2004 年（按「出生年 + 虚岁 − 1」粗算）。  
十二宫各管一段十年；阳男阴女顺行、阴男阳女逆行。读盘时常叠看：**本命 + 当前大限 + 流年**。

#### 三种排盘视角
1. **四化**  
   用**出生年天干**定四颗「变化星」：  
   - **化禄**：机遇、收获、顺遂  
   - **化权**：主导、掌控、进取  
   - **化科**：名声、文书、贵人眼缘  
   - **化忌**：分心、挂碍、功课所在（不是「注定倒霉」）  
   看它们落在哪一宫，就知道先天哪一块人生更「有戏」或更要经营。

2. **三合**  
   先看 **命宫的三方四正**（本宫 + 三合宫 + 对宫）里主星多不多、吉凶搭配如何，用来判断格局骨架高低。像看房子的承重墙，而不是先盯一扇窗。

3. **飞星**（怎么看）  
   每个宫有自己的**天干**，按该干再飞出禄权科忌，落到盘中对应星所在的宫——「从本宫干 → 落点宫」就是 **飞星路径**。  
   切换上方 **「飞星」视角** 后，看宫内小字即可：  
   - `禄→财帛`：本宫天干飞化禄，落在财帛 → 本宫议题牵动财运  
   - `权→官禄`：飞化权落官禄 → 主导力牵动事业  
   - 带 `*`：**自化**（飞回本宫），力量更向内  
   可先只看命宫、财帛、官禄、夫妻四宫的飞出。

#### 建议读盘顺序
三合看格局 → 四化看先天喜忌 → 飞星看宫际牵动 → 再对照大限年龄/年份看应期。

#### 和八字的差别
- **八字**：干支五行、十神、喜用、大运流年  
- **紫微**：宫位叙事 + 星曜组合 + 四化应期，更像十二个生活领域的剧本
""".strip()
    if lang == "zh_hant":
        from zh_convert import to_traditional

        return to_traditional(body)
    return body


# 方格盘地支位置（固定地盘）：4x4，中宫 2x2
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
    """十二宫方格盘。mode: sihua | sanhe | feixing。"""
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

    def star_html(s: dict, *, kind: str) -> str:
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
        bright_s = (
            f"<span style='opacity:0.55;font-size:0.68em;'>/{esc(bright)}</span>"
            if bright and kind == "major"
            else ""
        )
        if kind == "major":
            weight, size, color = "700", "13px", "#111"
        elif kind == "soft":
            weight, size, color = "600", "11px", "#1B5E20"
        elif kind == "tough":
            weight, size, color = "600", "11px", "#B71C1C"
        elif kind == "adjective":
            weight, size, color = "400", "10px", "#546E7A"
        else:
            weight, size, color = "500", "11px", "#37474F"
        return (
            f"<span style='display:inline-block;margin:0 3px 1px 0;font-weight:{weight};"
            f"font-size:{size};color:{color};line-height:1.25;'>{name}{bright_s}{mark}</span>"
        )

    def palace_cell(zhi: str) -> str:
        p = by_zhi.get(zhi) or {}
        pname = p.get("name") or zhi
        gan = p.get("gan") or ""
        majors = "".join(star_html(s, kind="major") for s in (p.get("majors") or []))
        minors = "".join(
            star_html(s, kind=s.get("type") or "minor") for s in (p.get("minors") or [])
        )
        adjs = "".join(star_html(s, kind="adjective") for s in (p.get("adjectives") or []))
        if not majors and not minors and not adjs:
            majors = f"<span style='opacity:0.45;font-size:12px;'>{esc(loc('空宫', 'empty'))}</span>"

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

        # 大限：年龄 + 公历年（缺年份时按出生年回填，避免旧缓存只显示岁数）
        dec = dict(p.get("decadal") or dec_by_palace.get(pname) or {})
        birth_year = 0
        try:
            birth_year = int(str(chart.get("solar_date") or "")[:4])
        except Exception:
            birth_year = 0
        if dec and birth_year and (not dec.get("start_year") or not dec.get("end_year")):
            try:
                sa, ea = int(dec["start_age"]), int(dec["end_age"])
                dec["start_year"] = birth_year + sa - 1
                dec["end_year"] = birth_year + ea - 1
            except Exception:
                pass

        timing_html = ""
        if dec.get("start_age") is not None and dec.get("end_age") is not None:
            age_bit = loc(
                f"{dec.get('start_age')}～{dec.get('end_age')}岁",
                f"{dec.get('start_age')}–{dec.get('end_age')}",
            )
            if dec.get("start_year") and dec.get("end_year"):
                year_bit = loc(
                    f"{dec.get('start_year')}～{dec.get('end_year')}年",
                    f"{dec.get('start_year')}–{dec.get('end_year')}",
                )
                timing_txt = loc(f"大限 {age_bit}｜{year_bit}", f"Dec {age_bit} | {year_bit}")
            else:
                timing_txt = loc(f"大限 {age_bit}", f"Dec {age_bit}")
            timing_html = (
                f"<div style='margin-top:4px;padding-top:3px;border-top:1px solid #CFD8DC;"
                f"font-size:11px;line-height:1.3;color:#263238;font-weight:600;'>"
                f"{esc(timing_txt)}</div>"
            )

        tags = []
        if p.get("is_ming"):
            tags.append(loc("命", "命"))
        if p.get("is_shen"):
            tags.append(loc("身", "身"))
        if p.get("is_laiyin"):
            tags.append(loc("来因", "来因"))
        tag_s = ("·".join(tags)) if tags else ""

        meta_bits = []
        if p.get("changsheng"):
            meta_bits.append(esc(p["changsheng"]))
        if p.get("boshi"):
            meta_bits.append(esc(p["boshi"]))
        meta_s = " · ".join(meta_bits)
        ages = p.get("ages") or []
        ages_s = ""
        if ages:
            ages_s = loc("小限 ", "Ages ") + " ".join(str(a) for a in ages[:5])
            if len(ages) > 5:
                ages_s += "…"

        bg = "#FFF8E1" if hl else "#FAFAFA"
        border = "#F9A825" if hl else "#90A4AE"
        name_color = "#C62828" if (p.get("is_ming") or p.get("is_shen")) else "#0D47A1"

        return (
            f"<td style='width:25%;border:1.5px solid {border};background:{bg};"
            f"padding:4px 5px 3px;vertical-align:top;min-height:158px;'>"
            f"<div style='line-height:1.2;min-height:56px;'>"
            f"{majors}"
            f"{('<div style=\"margin-top:1px;\">' + minors + '</div>') if minors else ''}"
            f"{('<div style=\"margin-top:1px;\">' + adjs + '</div>') if adjs else ''}"
            f"{('<div style=\"margin-top:3px;font-size:10px;color:#6D4C41;line-height:1.25;\">' + esc(accent) + '</div>') if accent else ''}"
            f"</div>"
            f"<div style='margin-top:3px;font-size:10px;color:#78909C;line-height:1.2;'>"
            f"{meta_s}"
            f"{('<br/>' + esc(ages_s)) if ages_s else ''}"
            f"</div>"
            f"{timing_html}"
            f"<div style='margin-top:3px;font-size:12px;line-height:1.25;text-align:right;'>"
            f"<b style='color:{name_color};font-size:13px;'>{esc(pname)}"
            f"{('·' + esc(tag_s)) if tag_s else ''}</b><br/>"
            f"<span style='opacity:0.85;font-size:11px;'>{esc(gan)}{esc(zhi)}</span>"
            f"</div>"
            f"</td>"
        )

    # 中宫（合并 2x2）
    sihua_line = "、".join(f"{x['star']}{x['type']}" for x in sihua) if sihua else "—"
    center_td = (
        "<td colspan='2' rowspan='2' style='border:1.5px solid #90A4AE;"
        "background:#ECEFF1;padding:12px;vertical-align:middle;text-align:center;'>"
        f"<div style='font-weight:700;font-size:18px;color:#0B1F33;margin-bottom:6px;'>"
        f"{esc(chart.get('name') or loc('命主', 'Native'))}</div>"
        f"<div style='font-size:14px;margin:3px 0;'>{esc(chart.get('gender') or '')} · "
        f"{esc(chart.get('ju_name') or '')}</div>"
        f"<div style='font-size:13px;margin:3px 0;opacity:0.9;'>"
        f"{esc((chart.get('lunar') or {}).get('label') or '')} "
        f"{esc(chart.get('hour_zhi') or '')}{esc(loc('时', ' hour'))}</div>"
        f"<div style='font-size:13px;margin:3px 0;'>"
        f"{esc(loc('命宫', 'Life'))} {esc(chart.get('ming_ganzhi') or '')} · "
        f"{esc(loc('身宫', 'Body'))} {esc(chart.get('shen_palace') or '')}</div>"
        f"<div style='font-size:13px;margin:6px 0;'>"
        f"{esc(loc('视角', 'View'))}：<b>{esc(mode_label)}</b></div>"
        f"<div style='font-size:12px;color:#4E342E;line-height:1.45;'>"
        f"{esc(loc('生年四化', 'Natal Si Hua'))}：{esc(sihua_line)}</div>"
        f"<div style='font-size:11px;opacity:0.75;margin-top:6px;'>"
        f"{esc(loc('禄绿·权紫·科蓝·忌红', 'Lu green · Quan purple · Ke blue · Ji red'))}"
        f"</div></td>"
    )

    # 4x4 表格行（地支固定）
    # 巳 午 未 申
    # 辰 [中宫] 酉
    # 卯 [中宫] 戌
    # 寅 丑 子 亥
    row1 = "".join(palace_cell(z) for z in ("巳", "午", "未", "申"))
    row2 = palace_cell("辰") + center_td + palace_cell("酉")
    row3 = palace_cell("卯") + palace_cell("戌")
    row4 = "".join(palace_cell(z) for z in ("寅", "丑", "子", "亥"))

    blocks: List[str] = []
    if include_title:
        blocks.append(f"<h3>{esc(loc('紫微命盘', 'Zi Wei Chart'))}</h3>")

    if mode == "sihua":
        hint = loc("四化盘：高亮生年禄权科忌所在宫；星旁色标为四化。", "Si Hua: highlighted palaces hold natal mutagens.")
    elif mode == "sanhe":
        hint = loc(
            "三合盘：高亮命宫三方四正（" + "、".join(ming_sanfang_sizheng(chart)) + "）。",
            "San He: Life trine/opposite highlighted.",
        )
    else:
        hint = loc(
            "飞星盘：宫内「禄→某某宫」= 本宫天干飞化禄落到该宫；* 为自化（飞回本宫）。",
            "Flying Stars: e.g. Lu→Wealth = this palace stem flies Lu to Wealth; * = self-mutagen.",
        )

    blocks.append(f"<p style='font-size:13px;margin:4px 0 8px;'>{esc(hint)}</p>")
    blocks.append(
        "<table style='width:100%;max-width:960px;border-collapse:collapse;"
        "table-layout:fixed;background:#90A4AE;border:3px solid #90A4AE;'>"
        f"<tr>{row1}</tr>"
        f"<tr>{row2}</tr>"
        f"<tr>{row3}</tr>"
        f"<tr>{row4}</tr>"
        "</table>"
    )

    dec = chart.get("decadals") or []
    if dec:
        bits = [
            f"{d.get('palace')} {d.get('start_age')}～{d.get('end_age')}岁/"
            f"{d.get('start_year')}～{d.get('end_year')}年"
            for d in dec
        ]
        blocks.append(
            "<p style='font-size:11px;margin:8px 0 2px;opacity:0.85;line-height:1.45;'>"
            + esc(loc("大限（年龄/年）：", "Decades (age/year): ") + " · ".join(bits))
            + "</p>"
        )
    blocks.append(
        "<p style='font-size:10px;margin:2px 0 0;opacity:0.7;'>"
        + esc(
            loc(
                "盘面：左下为大限虚岁与对应公历年 · 右下宫名干支 · 主星加粗 · 吉曜绿/煞曜红/杂曜灰 · 飞星视角看宫内「禄→某某宫」",
                "Bottom-left: decade age + calendar years · majors bold · Flying view: Lu→palace labels",
            )
        )
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
        extra = []
        if p.get("changsheng"):
            extra.append(p["changsheng"])
        if p.get("boshi"):
            extra.append(p["boshi"])
        if p.get("is_laiyin"):
            extra.append("来因")
        if p.get("is_shen"):
            extra.append("身")
        suf = (" |" + " ".join(extra)) if extra else ""
        lines.append(f"- {pname}({p.get('gan')}{p.get('zhi')}): {_star_line(p)}{suf}")
    return "\n".join(lines)


# --- PDF export ---

def ziwei_pdf_filename(name: str = "") -> str:
    """紫微 PDF 文件名。"""
    import re
    from datetime import datetime

    raw = str(name or "user").strip()
    safe = re.sub(r'[\\/:*?"<>|\s]+', "_", raw).strip("_") or "user"
    return f"ZiWei_{safe[:40]}_{datetime.now():%Y%m%d}.pdf"


def render_ziwei_chart_image(
    chart: Dict[str, Any],
    *,
    mode: str = "sanhe",
    lang: str = "zh",
    max_width_pt: float = 460,
):
    """将十二宫方格盘绘成 PDF 可用图片（PIL）。"""
    import io
    from reportlab.platypus import Image as RLImage
    from PIL import Image, ImageDraw, ImageFont

    from utils import _cjk_font_candidates_for_pil, _cjk_font_file, _pdf_fix_glyphs

    if not chart.get("ok"):
        return None
    cands = _cjk_font_candidates_for_pil()
    font_path = cands[0] if cands else _cjk_font_file()
    if not font_path:
        return None

    en = lang == "en"
    mode = (mode or "sanhe").lower()
    if mode in ("四化",):
        mode = "sihua"
    elif mode in ("三合",):
        mode = "sanhe"
    elif mode in ("飞星", "飛星"):
        mode = "feixing"

    scale = 2
    cell_w, cell_h = 118 * scale, 108 * scale
    pad = 6 * scale
    img_w = cell_w * 4 + pad * 2
    img_h = cell_h * 4 + pad * 2
    img = Image.new("RGB", (img_w, img_h), "#90A4AE")
    draw = ImageDraw.Draw(img)
    try:
        font_sm = ImageFont.truetype(str(font_path), 9 * scale)
        font_md = ImageFont.truetype(str(font_path), 11 * scale)
        font_lg = ImageFont.truetype(str(font_path), 13 * scale)
    except Exception:
        return None

    sf_names = set(ming_sanfang_sizheng(chart))
    natal_sihua_at = {}
    for x in chart.get("sihua") or []:
        natal_sihua_at.setdefault(x.get("palace"), []).append(x)
    fly_by = {r["from_palace"]: r for r in compute_palace_fly(chart)}
    by_zhi = {p.get("zhi"): p for p in (chart.get("palaces") or [])}

    grid = [
        ["巳", "午", "未", "申"],
        ["辰", None, None, "酉"],
        ["卯", None, None, "戌"],
        ["寅", "丑", "子", "亥"],
    ]

    def text(xy, s, font, fill="#111"):
        s = _pdf_fix_glyphs(str(s or ""), font_path)
        if s:
            draw.text(xy, s, font=font, fill=fill)

    # center
    cx0, cy0 = pad + cell_w, pad + cell_h
    draw.rectangle([cx0, cy0, cx0 + cell_w * 2 - 1, cy0 + cell_h * 2 - 1], fill="#ECEFF1", outline="#78909C")
    mode_label = {"sihua": "四化", "sanhe": "三合", "feixing": "飞星"}.get(mode, "三合")
    if en:
        mode_label = {"sihua": "Si Hua", "sanhe": "San He", "feixing": "Flying"}.get(mode, "San He")
    center_lines = [
        str(chart.get("name") or ("Native" if en else "命主")),
        f"{chart.get('gender') or ''} · {chart.get('ju_name') or ''}",
        f"{(chart.get('lunar') or {}).get('label') or ''}",
        f"{'命' if not en else 'Life'} {chart.get('ming_ganzhi') or ''}",
        f"{'视角' if not en else 'View'}：{mode_label}",
    ]
    ty = cy0 + 14 * scale
    for line in center_lines:
        text((cx0 + 10 * scale, ty), line, font_md if ty == cy0 + 14 * scale else font_sm, "#0B1F33")
        ty += 16 * scale

    for r, row in enumerate(grid):
        for c, zhi in enumerate(row):
            if zhi is None:
                continue
            x0 = pad + c * cell_w
            y0 = pad + r * cell_h
            p = by_zhi.get(zhi) or {}
            pname = p.get("name") or zhi
            hl = False
            if mode == "sihua":
                hl = pname in natal_sihua_at
            elif mode == "sanhe":
                hl = pname in sf_names
            else:
                hl = pname == "命宫" or bool(
                    fly_by.get(pname) and any(it.get("self") for it in fly_by[pname].get("flies") or [])
                )
            bg = "#FFF8E1" if hl else "#FAFAFA"
            draw.rectangle([x0, y0, x0 + cell_w - 1, y0 + cell_h - 1], fill=bg, outline="#78909C")
            majors = " ".join(s.get("name", "")[:2] for s in (p.get("majors") or [])[:3])
            minors = " ".join(s.get("name", "")[:2] for s in (p.get("minors") or [])[:4])
            text((x0 + 4 * scale, y0 + 4 * scale), majors or ("空" if not en else "—"), font_md, "#111")
            text((x0 + 4 * scale, y0 + 20 * scale), minors, font_sm, "#455A64")
            dec = p.get("decadal") or {}
            if dec:
                timing = f"{dec.get('start_age')}～{dec.get('end_age')}｜{dec.get('start_year')}～{dec.get('end_year')}"
                text((x0 + 4 * scale, y0 + cell_h - 34 * scale), timing, font_sm, "#37474F")
            name_c = "#C62828" if p.get("is_ming") or p.get("is_shen") else "#0D47A1"
            text((x0 + 4 * scale, y0 + cell_h - 18 * scale), f"{pname} {p.get('gan') or ''}{zhi}", font_lg, name_c)

    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    draw_w = float(max_width_pt)
    draw_h = img_h / scale * (draw_w / (img_w / scale))
    return RLImage(bio, width=draw_w, height=draw_h)


def generate_ziwei_pdf_report(
    chart: dict,
    reading: dict,
    *,
    ai_deep: Optional[dict] = None,
    lang: str = "zh",
):
    """紫微专业 PDF：封面→8 章目录→三合/四化/飞星（盘+解读）→大限→四域（规则+AI）。

    中文与八字报告一致：PIL 绘字嵌图（Streamlit Cloud 上 ReportLab 子集易出全文小方块）。
    盘图亦为图片。英文副标题仍用 Helvetica。
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
    from utils import (
        _cjk_font_candidates_for_pil,
        _cjk_font_file,
        _pdf_font_is_sc_subset,
        _pdf_fix_glyphs,
        _pdf_text_image,
    )

    en = lang == "en"
    # 强制用仓库内单文件 TTF（Cloud 无 fontTools 时 TTC 无法物化会出方块）
    cands = _cjk_font_candidates_for_pil()
    cjk_path = cands[0] if cands else _cjk_font_file()
    use_pil = cjk_path is not None
    if not use_pil:
        raise RuntimeError(
            "No CJK font found under fonts/; cannot generate Zi Wei PDF without tofu."
        )

    def T(s: str) -> str:
        if en or not s:
            return s
        # 简体子集：必须转简体。全量字体：界面繁体可保留。
        if _pdf_font_is_sc_subset(cjk_path):
            try:
                from zh_convert import to_simplified

                return to_simplified(s)
            except Exception:
                return _pdf_fix_glyphs(s, None)
        if lang == "zh_hant":
            try:
                from zh_convert import to_traditional

                return to_traditional(s)
            except Exception:
                return s
        return s

    buffer = io.BytesIO()
    cover_title = T("六西格玛命理 · 紫微斗数报告") if not en else "Sigma Fate Zi Wei Report"
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
    # ParagraphStyle 仅作英文/极端回退；中文主路径走 PIL
    style_cover_sub = ParagraphStyle(
        "ZWCoverSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor="#455A64",
    )
    style_h1 = ParagraphStyle(
        "ZW1",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=18,
        leading=26,
        spaceBefore=6,
        spaceAfter=10,
        textColor="#0B1F33",
        alignment=TA_LEFT,
    )
    style_h1c = ParagraphStyle("ZW1C", parent=style_h1, alignment=TA_CENTER, fontSize=22, leading=30)
    style_h2 = ParagraphStyle(
        "ZW2",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=13,
        leading=20,
        spaceBefore=12,
        spaceAfter=6,
        textColor="#1565C0",
    )
    style_body = ParagraphStyle(
        "ZWB",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=17,
        alignment=TA_JUSTIFY,
        spaceAfter=8,
    )
    style_meta = ParagraphStyle(
        "ZWM",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    style_toc = ParagraphStyle(
        "ZWToc",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=18,
        alignment=TA_LEFT,
        leftIndent=12,
        spaceAfter=4,
    )
    content_width = A4[0] - 3.6 * cm
    story = []

    def _pdf_safe(text: str) -> str:
        raw = (
            str(text or "")
            .replace("⚠️", "")
            .replace("★", "*")
            .replace("●", "-")
        )
        return _pdf_fix_glyphs(raw, cjk_path)

    def add(text, style=style_body):
        raw = str(text or "").strip()
        if not en:
            raw = T(raw)
        raw = _pdf_safe(raw)
        if not raw:
            return
        if use_pil:
            size, fill, align = 11, "#222222", "left"
            if style is style_h1 or style is style_h1c:
                size, fill = 18, "#0B1F33"
                if style is style_h1c:
                    size, align = 22, "center"
            elif style is style_h2:
                size, fill = 13, "#1565C0"
            elif style is style_meta:
                size, fill, align = 12, "#333333", "center"
            elif style is style_toc:
                size = 11
            img = _pdf_text_image(
                raw,
                font_path=cjk_path,
                font_size=size,
                max_width_pt=float(content_width),
                fill=fill,
                align=align,
            )
            if img is not None:
                story.append(img)
                return
        # 无 PIL 字体时：英文可用 Paragraph；中文宁可不输出，避免 Helvetica 方块
        if en:
            story.append(Paragraph(escape(raw).replace("\n", "<br/>"), style))

    def section_by_id(sec_id: str) -> Dict[str, str]:
        for sec in (reading or {}).get("sections") or []:
            if sec.get("id") == sec_id:
                return sec
        for sec in (reading or {}).get("sections") or []:
            t = str(sec.get("title") or "")
            mapping = {
                "overview": ("命盘总览", "Chart overview"),
                "sanhe": ("三合", "San He"),
                "sihua": ("四化", "Si Hua"),
                "feixing": ("飞星", "Flying"),
                "decadal": ("大限", "Decade"),
                "career": ("事业", "Career"),
                "wealth": ("财运", "Wealth"),
                "love": ("感情", "Love", "Relationship"),
                "health": ("健康", "Health"),
            }
            keys = mapping.get(sec_id) or ()
            if any(k in t for k in keys):
                return sec
        return {}

    def add_ai_chapter(page: dict):
        if not isinstance(page, dict):
            return
        pro = page.get("professional") or []
        if isinstance(pro, str):
            pro = [pro]
        if pro:
            add("专业解读" if not en else "Professional reading", style_h2)
            for para in pro:
                if str(para).strip():
                    add(str(para).strip())
        plain = page.get("plain") or {}
        if isinstance(plain, dict) and (plain.get("summary") or plain.get("points") or plain.get("detail")):
            add("白话说明" if not en else "Plain language", style_h2)
            if plain.get("summary"):
                add(("一句话：" if not en else "Summary: ") + str(plain.get("summary")))
            for i, pt in enumerate(plain.get("points") or [], 1):
                add(f"{i}. {pt}")
            if plain.get("detail"):
                add(str(plain.get("detail")))
        elif page.get("content"):
            content = re.sub(r"[#*`]+", "", str(page.get("content") or ""))
            if content and not ReportGenerator._looks_like_json_blob(content):
                add(content)

    # —— 封面 ——
    name = (chart or {}).get("name") or ("Native" if en else "命主")
    story.append(Spacer(1, 1.8 * cm))
    add(cover_title, style_h1c)
    story.append(Paragraph(escape("Sigma Fate Zi Wei Report"), style_cover_sub))
    story.append(Spacer(1, 0.5 * cm))
    add(f"{'姓名' if not en else 'Name'}：{name}", style_meta)
    add(f"{'性别' if not en else 'Gender'}：{chart.get('gender') or '—'}", style_meta)
    add(
        f"{'出生' if not en else 'Birth'}：{chart.get('solar_date')} "
        f"{int(chart.get('birth_hour') or 0):02d}:{int(chart.get('birth_minute') or 0):02d}",
        style_meta,
    )
    add(
        f"{(chart.get('lunar') or {}).get('label') or ''} · {chart.get('ju_name') or ''} · "
        f"{'命宫' if not en else 'Life'} {chart.get('ming_ganzhi') or ''} · "
        f"{'身宫' if not en else 'Body'} {chart.get('shen_palace') or ''}",
        style_meta,
    )
    story.append(Spacer(1, 0.6 * cm))
    add("本报告仅供参考，请理性看待。" if not en else "For reference only — please read rationally.", style_meta)

    toc = [
        ("1", "三合盘与格局" if not en else "San He chart & structure"),
        ("2", "四化盘与先天喜忌" if not en else "Si Hua chart & mutagens"),
        ("3", "飞星盘与宫际牵动" if not en else "Flying-star chart & links"),
        ("4", "大限应期" if not en else "Decade timing"),
        ("5", "事业总结" if not en else "Career summary"),
        ("6", "财运总结" if not en else "Wealth summary"),
        ("7", "感情总结" if not en else "Relationship summary"),
        ("8", "健康总结" if not en else "Health summary"),
    ]
    story.append(Spacer(1, 0.4 * cm))
    add("目录" if not en else "Contents", style_h1)
    for num, title in toc:
        add(f"{num}. {title}", style_toc)
    story.append(PageBreak())

    # —— 1 三合 ——
    add(toc[0][1], style_h1)
    add("高亮命宫三方四正，先看格局骨架。" if not en else "Highlight Life trine/opposite — structure first.")
    img = render_ziwei_chart_image(chart, mode="sanhe", lang=lang, max_width_pt=content_width)
    if img is not None:
        story.append(Spacer(1, 0.2 * cm))
        story.append(img)
        story.append(Spacer(1, 0.3 * cm))
    sec = section_by_id("sanhe")
    if sec.get("body"):
        add(sec["body"])
    story.append(PageBreak())

    # —— 2 四化 ——
    add(toc[1][1], style_h1)
    add("高亮生年禄权科忌所在宫。" if not en else "Highlight natal mutagen palaces.")
    img = render_ziwei_chart_image(chart, mode="sihua", lang=lang, max_width_pt=content_width)
    if img is not None:
        story.append(Spacer(1, 0.2 * cm))
        story.append(img)
        story.append(Spacer(1, 0.3 * cm))
    sec = section_by_id("sihua")
    if sec.get("body"):
        add(sec["body"])
    story.append(PageBreak())

    # —— 3 飞星 ——
    add(toc[2][1], style_h1)
    add("宫内路径见飞星视角；下文摘录重点宫飞出。" if not en else "Fly paths summarized below.")
    img = render_ziwei_chart_image(chart, mode="feixing", lang=lang, max_width_pt=content_width)
    if img is not None:
        story.append(Spacer(1, 0.2 * cm))
        story.append(img)
        story.append(Spacer(1, 0.3 * cm))
    sec = section_by_id("feixing")
    if sec.get("body"):
        add(sec["body"])
    story.append(PageBreak())

    # —— 4 大限 ——
    add(toc[3][1], style_h1)
    sec = section_by_id("decadal")
    if sec.get("body"):
        add(sec["body"])
    story.append(PageBreak())

    # —— 5–8 四域：规则 + AI ——
    domain_map = [
        ("career", toc[4][1], ("career", "事业", "事业财运")),
        ("wealth", toc[5][1], ("wealth", "财运")),
        ("love", toc[6][1], ("love", "感情", "life", "感情身心")),
        ("health", toc[7][1], ("health", "健康", "life", "感情身心")),
    ]
    ai = ai_deep if isinstance(ai_deep, dict) else {}
    for i, (sec_id, title, ai_aliases) in enumerate(domain_map):
        add(title, style_h1)
        add("规则要点" if not en else "Rule-based notes", style_h2)
        sec = section_by_id(sec_id)
        if sec.get("body"):
            add(sec["body"])
        ai_page = None
        for a in ai_aliases:
            if a in ai and ai.get(a) not in (None, "", {}, []):
                if sec_id == "wealth" and a in ("career", "事业财运"):
                    continue
                ai_page = ai.get(a)
                break
        if ai_page:
            add(
                "AI 深批（与上列规则互补，勿作宿命断言）"
                if not en
                else "AI deep read (complements rules — not destiny)",
                style_h2,
            )
            page = dict(ai_page) if isinstance(ai_page, dict) else {"content": str(ai_page)}
            add_ai_chapter(page)
        elif sec_id == "career" and not any(ai.get(k) for k in ("career", "wealth", "love", "health")):
            # 兼容旧三章：仅事业章尝试 pattern
            if ai.get("pattern"):
                add("AI 深批" if not en else "AI deep read", style_h2)
                add_ai_chapter(dict(ai["pattern"]) if isinstance(ai["pattern"], dict) else {"content": str(ai["pattern"])})
        if i < len(domain_map) - 1:
            story.append(PageBreak())

    story.append(Spacer(1, 0.5 * cm))
    add(
        "仅供参考：紫微斗数本地规则 +（可选）AI 文笔，不构成人生决定依据。"
        if not en
        else "Reference only — not a life decision.",
        style_meta,
    )
    doc.build(story)
    buffer.seek(0)
    return buffer

