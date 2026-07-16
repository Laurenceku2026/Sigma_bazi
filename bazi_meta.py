"""
纳音 · 空亡 · 神煞 · 称骨（袁天罡）
神煞表按日干/日支/年支/月支综合，尽量对齐主流排盘软件展示密度。
"""
from __future__ import annotations

from typing import Dict, List, Tuple

TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

NAYIN: Dict[str, str] = {
    "甲子": "海中金", "乙丑": "海中金", "丙寅": "炉中火", "丁卯": "炉中火",
    "戊辰": "大林木", "己巳": "大林木", "庚午": "路旁土", "辛未": "路旁土",
    "壬申": "剑锋金", "癸酉": "剑锋金", "甲戌": "山头火", "乙亥": "山头火",
    "丙子": "涧下水", "丁丑": "涧下水", "戊寅": "城头土", "己卯": "城头土",
    "庚辰": "白蜡金", "辛巳": "白蜡金", "壬午": "杨柳木", "癸未": "杨柳木",
    "甲申": "泉中水", "乙酉": "泉中水", "丙戌": "屋上土", "丁亥": "屋上土",
    "戊子": "霹雳火", "己丑": "霹雳火", "庚寅": "松柏木", "辛卯": "松柏木",
    "壬辰": "长流水", "癸巳": "长流水", "甲午": "砂中金", "乙未": "砂中金",
    "丙申": "山下火", "丁酉": "山下火", "戊戌": "平地木", "己亥": "平地木",
    "庚子": "壁上土", "辛丑": "壁上土", "壬寅": "金箔金", "癸卯": "金箔金",
    "甲辰": "覆灯火", "乙巳": "覆灯火", "丙午": "天河水", "丁未": "天河水",
    "戊申": "大驿土", "己酉": "大驿土", "庚戌": "钗钏金", "辛亥": "钗钏金",
    "壬子": "桑柘木", "癸丑": "桑柘木", "甲寅": "大溪水", "乙卯": "大溪水",
    "丙辰": "砂中土", "丁巳": "砂中土", "戊午": "天上火", "己未": "天上火",
    "庚申": "石榴木", "辛酉": "石榴木", "壬戌": "大海水", "癸亥": "大海水",
}

XUNKONG: Dict[str, Tuple[str, str]] = {
    "甲子": ("戌", "亥"), "甲戌": ("申", "酉"), "甲申": ("午", "未"),
    "甲午": ("辰", "巳"), "甲辰": ("寅", "卯"), "甲寅": ("子", "丑"),
}

CHENG_GU_YEAR = {
    "甲子": 1.2, "乙丑": 0.9, "丙寅": 0.6, "丁卯": 0.7, "戊辰": 1.2, "己巳": 0.5,
    "庚午": 0.9, "辛未": 0.8, "壬申": 0.7, "癸酉": 0.8, "甲戌": 1.5, "乙亥": 0.9,
    "丙子": 1.6, "丁丑": 0.8, "戊寅": 0.8, "己卯": 1.9, "庚辰": 1.2, "辛巳": 0.6,
    "壬午": 0.8, "癸未": 0.7, "甲申": 0.5, "乙酉": 1.5, "丙戌": 0.6, "丁亥": 1.6,
    "戊子": 1.5, "己丑": 0.7, "庚寅": 0.9, "辛卯": 1.2, "壬辰": 1.0, "癸巳": 0.7,
    "甲午": 1.5, "乙未": 0.6, "丙申": 0.5, "丁酉": 1.4, "戊戌": 1.4, "己亥": 0.9,
    "庚子": 0.7, "辛丑": 0.7, "壬寅": 0.9, "癸卯": 1.2, "甲辰": 0.8, "乙巳": 0.7,
    "丙午": 1.3, "丁未": 0.5, "戊申": 1.4, "己酉": 0.5, "庚戌": 0.9, "辛亥": 1.7,
    "壬子": 0.5, "癸丑": 0.7, "甲寅": 1.2, "乙卯": 0.8, "丙辰": 0.7, "丁巳": 0.6,
    "戊午": 1.9, "己未": 0.6, "庚申": 0.8, "辛酉": 1.6, "壬戌": 1.0, "癸亥": 0.6,
}
CHENG_GU_MONTH = {
    1: 0.6, 2: 0.7, 3: 1.8, 4: 0.9, 5: 0.5, 6: 1.6,
    7: 0.9, 8: 1.5, 9: 1.8, 10: 0.8, 11: 0.9, 12: 0.5,
}
CHENG_GU_DAY = {
    1: 0.5, 2: 1.0, 3: 0.8, 4: 1.5, 5: 1.6, 6: 1.5, 7: 0.8, 8: 1.6, 9: 0.8, 10: 1.6,
    11: 0.9, 12: 1.7, 13: 0.8, 14: 1.7, 15: 1.0, 16: 0.8, 17: 0.9, 18: 1.8, 19: 0.5, 20: 1.5,
    21: 1.0, 22: 0.9, 23: 0.8, 24: 0.9, 25: 1.5, 26: 1.8, 27: 0.7, 28: 0.8, 29: 1.6, 30: 0.6, 31: 0.6,
}
CHENG_GU_HOUR = {
    "子": 1.6, "丑": 0.6, "寅": 0.7, "卯": 1.0, "辰": 0.9, "巳": 1.6,
    "午": 1.0, "未": 0.8, "申": 0.8, "酉": 0.9, "戌": 0.6, "亥": 0.6,
}

CHENG_GU_POEM: Dict[float, str] = {
    2.1: "短命非业谓大空，平生灾难事重重；凶祸频临陷逆境，终步困苦事不成。",
    2.2: "身寒骨冷苦伶仃，此命推来行乞人；劳劳碌碌无度日，血食斋墙过一生。",
    2.3: "此命推来骨肉轻，求谋做事事难成；妻儿兄弟应难靠，外出他乡作散人。",
    2.4: "此命推来福禄无，门庭困苦总难荣；六亲骨肉皆无靠，流到他乡作老翁。",
    2.5: "此命推来祖业微，门庭营度似稀栖；六亲骨肉如冰炭，一世勤劳自把持。",
    2.6: "平生衣禄苦中求，独自营谋事不休；离祖出门宜早计，晚来衣禄自无忧。",
    2.7: "一生作事少商量，难靠祖宗作主张；独马单枪空做去，早年晚岁守空房。",
    2.8: "一生作事似飘蓬，祖宗产业在梦中；若不过房并改姓，也当移徒二三通。",
    2.9: "初年运道未曾亨，纵有功名在后成；须过十方求上进，出入头地始为荣。",
    3.0: "此命推来祖业通，衣食丰足早年荣；若得生来时较晚，中年衣食自如松。",
    3.1: "此命平生有祖荫，事业经营得意成；早年财禄有多利，晚景兴隆家道成。",
    3.2: "此命平生更聪明，衣食丰足事称心；一生安闲多自在，一世清闲好安身。",
    3.3: "平生衣禄自天来，祖业营谋事事开；不须劳心多费力，自然衣禄自无灾。",
    3.4: "此命推来事不同，为人能巧又聪明；衣禄自有方来助，不须劳力苦劳心。",
    3.5: "此命推来旺祖宗，根基深厚有财丰；少年衣食多安稳，晚景悠闲福更隆。",
    3.6: "此命平生福不轻，自有衣禄足丰盈；祖业根基常兴旺，平生衣食免劳心。",
    3.7: "此命推来禄力强，门庭兴旺好风光；身荣体贵多安乐，一世荣华大吉昌。",
    3.8: "此命推来福不轻，自有衣禄享丰盈；财源广进家道旺，一世荣华福寿增。",
    3.9: "此命推来福自厚，财禄丰盈不用愁；祖业根基多兴旺，平生衣食自然优。",
    4.0: "此命推来大不同，福禄双全事事通；一生衣食多丰足，晚景荣华福更隆。",
    4.1: "此命推来事事通，一生福禄自丰隆；祖业根基多稳固，晚景逍遥福寿宏。",
    4.2: "此命推来福不轻，财官双美事亨通；一生衣禄多丰足，晚景荣华福寿增。",
    4.3: "此命推来主大贵，功名事业两相宜；财禄丰盈多福庆，一世荣华福寿齐。",
    4.4: "此命推来福禄全，财官双美事安然；一生衣食多丰足，晚景荣华福寿绵。",
    4.5: "此命推来福更深，财官双美贵人钦；一生衣禄多丰足，晚景荣华福寿临。",
    5.0: "此命推来福禄全，财官双美事安然；一生衣食多丰足，晚景荣华福寿绵。",
    5.5: "此命推来福禄全，财官双美事安然；一生衣食多丰足，晚景荣华福寿绵。",
    6.0: "此命推来福禄全，财官双美事安然；一生衣食多丰足，晚景荣华福寿绵。",
    7.2: "此命推来福更奇，财官双美贵人宜；一生衣禄多丰足，晚景荣华福寿齐。",
}


def nayin_of(gan: str, zhi: str) -> str:
    return NAYIN.get(f"{gan}{zhi}", "")


def xunkong_of_pillar(gan: str, zhi: str) -> Tuple[str, str]:
    if gan not in TIANGAN or zhi not in DIZHI:
        return ("", "")
    gi, zi = TIANGAN.index(gan), DIZHI.index(zhi)
    xun_zhi = DIZHI[(zi - gi) % 12]
    return XUNKONG.get(f"甲{xun_zhi}", ("", ""))


def day_kongwang(day_gan: str, day_zhi: str) -> List[str]:
    a, b = xunkong_of_pillar(day_gan, day_zhi)
    return [x for x in (a, b) if x]


def format_liang(v: float) -> str:
    liang = int(v)
    qian = int(round((v - liang) * 10))
    if qian >= 10:
        liang += 1
        qian = 0
    parts = []
    if liang:
        parts.append(f"{liang}两")
    if qian:
        parts.append(f"{qian}钱")
    return "".join(parts) or "零"


def cheng_gu(year_gz: str, lunar_month: int, lunar_day: int, hour_zhi: str) -> Dict:
    y = CHENG_GU_YEAR.get(year_gz, 0.8)
    m = CHENG_GU_MONTH.get(max(1, min(12, lunar_month)), 0.8)
    d = CHENG_GU_DAY.get(max(1, min(31, lunar_day)), 0.8)
    h = CHENG_GU_HOUR.get(hour_zhi, 0.8)
    total = round(y + m + d + h, 1)
    poem = CHENG_GU_POEM.get(total)
    if not poem:
        keys = sorted(CHENG_GU_POEM.keys())
        nearest = min(keys, key=lambda k: abs(k - total)) if keys else None
        poem = CHENG_GU_POEM.get(nearest, "称骨评语待查。") if nearest else ""
    return {
        "year": y, "month": m, "day": d, "hour": h,
        "total": total, "total_text": format_liang(total), "poem": poem,
    }


# 展示顺序：吉神在前、凶煞在后（对齐主流排盘软件）
SHENSHA_ORDER = [
    "天乙贵人", "太极贵人", "天德", "月德", "天德合", "月德合",
    "文昌", "学堂", "词馆", "天厨", "福星贵人", "国印", "金舆", "天医",
    "禄神", "将星", "华盖", "驿马", "红鸾", "天喜", "红艳", "桃花",
    "羊刃", "飞刃", "流霞", "血刃",
    "亡神", "劫煞", "灾煞", "孤辰", "寡宿", "勾绞",
    "天罗", "地网", "元辰", "丧门", "吊客", "披麻", "白虎", "病符", "官符",
    "魁罡", "金神", "阴差阳错", "孤鸾煞", "十恶大败", "四废", "天赦", "截路空亡",
]


def _sort_shensha(names: List[str]) -> List[str]:
    rank = {n: i for i, n in enumerate(SHENSHA_ORDER)}
    uniq = list(dict.fromkeys(names))
    return sorted(uniq, key=lambda x: (rank.get(x, 900), x))


def shensha_for_chart(
    day_master: str,
    day_zhi: str,
    year_gan: str,
    year_zhi: str,
    month_zhi: str,
    pillars: Dict[str, Tuple[str, str]],
    gender: str = "男",
) -> Dict[str, List[str]]:
    """
    返回 {柱名: [神煞...]}。
    查法对齐《三命通会》/主流排盘：天乙、文昌、太极、金舆、国印等以「日干+年干」双查；
    驿马桃花华盖将星亡神劫煞以「年支+日支」双查；天医以月支；另含太岁系列与日柱专煞。
    """
    branches = {name: zhi for name, (_g, zhi) in pillars.items()}
    out: Dict[str, List[str]] = {k: [] for k in pillars}

    def mark_zhi(targets, label: str, skip_bases: Tuple[str, ...] = ()):
        if isinstance(targets, str):
            targets = [targets] if targets else []
        for zhi_target in targets:
            if not zhi_target:
                continue
            for name, zhi in branches.items():
                if skip_bases and name in skip_bases:
                    continue
                if zhi == zhi_target:
                    out[name].append(label)

    def mark_gan(targets, label: str):
        if isinstance(targets, str):
            targets = [targets] if targets else []
        for gan_target in targets:
            if not gan_target:
                continue
            for name, (gan, _z) in pillars.items():
                if gan == gan_target:
                    out[name].append(label)

    # —— 日干 / 年干双查 ——
    tianyi = {
        "甲": ["丑", "未"], "戊": ["丑", "未"], "庚": ["丑", "未"],
        "乙": ["子", "申"], "己": ["子", "申"],
        "丙": ["亥", "酉"], "丁": ["亥", "酉"],
        "壬": ["巳", "卯"], "癸": ["巳", "卯"],
        "辛": ["寅", "午"],
    }
    wenchang = {
        "甲": "巳", "乙": "午", "丙": "申", "丁": "酉", "戊": "申",
        "己": "酉", "庚": "亥", "辛": "子", "壬": "寅", "癸": "卯",
    }
    taiji = {
        "甲": ["子", "午"], "乙": ["子", "午"],
        "丙": ["卯", "酉"], "丁": ["卯", "酉"],
        "戊": ["辰", "戌", "丑", "未"], "己": ["辰", "戌", "丑", "未"],
        "庚": ["寅", "亥"], "辛": ["寅", "亥"],
        "壬": ["巳", "申"], "癸": ["巳", "申"],
    }
    lu = {
        "甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳",
        "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子",
    }
    yangren = {
        "甲": "卯", "乙": "寅", "丙": "午", "丁": "巳", "戊": "午",
        "己": "巳", "庚": "酉", "辛": "申", "壬": "子", "癸": "亥",
    }
    # 飞刃 = 羊刃所冲
    feiren = {g: DIZHI[(DIZHI.index(z) + 6) % 12] for g, z in yangren.items()}
    jinyu = {
        "甲": "辰", "乙": "巳", "丙": "未", "丁": "申", "戊": "未",
        "己": "申", "庚": "戌", "辛": "亥", "壬": "丑", "癸": "寅",
    }
    guoyin = {
        "甲": "戌", "乙": "亥", "丙": "丑", "丁": "寅", "戊": "丑",
        "己": "寅", "庚": "辰", "辛": "巳", "壬": "未", "癸": "申",
    }
    hongyan = {
        "甲": "午", "乙": "申", "丙": "寅", "丁": "未", "戊": "辰",
        "己": "辰", "庚": "戌", "辛": "酉", "壬": "子", "癸": "申",
    }
    liuxia = {
        "甲": "酉", "乙": "戌", "丙": "未", "丁": "申", "戊": "巳",
        "己": "午", "庚": "辰", "辛": "卯", "壬": "亥", "癸": "寅",
    }
    tianchu = {  # 天厨
        "甲": "巳", "乙": "午", "丙": "巳", "丁": "午", "戊": "申",
        "己": "酉", "庚": "亥", "辛": "子", "壬": "寅", "癸": "卯",
    }
    fuxing = {  # 福星贵人（常见口诀）
        "甲": ["寅", "子"], "乙": ["丑", "卯", "未"], "丙": ["寅", "子"],
        "丁": ["亥"], "戊": ["申"], "己": ["未"],
        "庚": ["午"], "辛": ["巳"], "壬": ["辰"], "癸": ["丑", "卯"],
    }
    jielu = {  # 截路空亡
        "甲": ["申", "酉"], "乙": ["午", "未"], "丙": ["辰", "巳"], "丁": ["寅", "卯"],
        "戊": ["子", "丑"], "己": ["申", "酉"], "庚": ["午", "未"], "辛": ["辰", "巳"],
        "壬": ["寅", "卯"], "癸": ["子", "丑"],
    }

    for gan in (day_master, year_gan):
        if not gan:
            continue
        mark_zhi(tianyi.get(gan, []), "天乙贵人")
        mark_zhi(wenchang.get(gan, ""), "文昌")
        mark_zhi(taiji.get(gan, []), "太极贵人")
        mark_zhi(jinyu.get(gan, ""), "金舆")
        mark_zhi(guoyin.get(gan, ""), "国印")
        mark_zhi(tianchu.get(gan, ""), "天厨")
        mark_zhi(fuxing.get(gan, []), "福星贵人")

    # 禄刃红艳流霞等以日干为主（年干禄刃易与日主混淆，仅日干）
    mark_zhi(lu.get(day_master, ""), "禄神")
    mark_zhi(yangren.get(day_master, ""), "羊刃")
    mark_zhi(feiren.get(day_master, ""), "飞刃")
    mark_zhi(hongyan.get(day_master, ""), "红艳")
    mark_zhi(liuxia.get(day_master, ""), "流霞")
    mark_zhi(jielu.get(day_master, []), "截路空亡")

    # —— 年支 / 日支双查（三合类）；驿马华盖等一般不标在「起例之支」本柱 ——
    taohua = {
        "申": "酉", "子": "酉", "辰": "酉",
        "寅": "卯", "午": "卯", "戌": "卯",
        "巳": "午", "酉": "午", "丑": "午",
        "亥": "子", "卯": "子", "未": "子",
    }
    yima = {
        "申": "寅", "子": "寅", "辰": "寅",
        "寅": "申", "午": "申", "戌": "申",
        "巳": "亥", "酉": "亥", "丑": "亥",
        "亥": "巳", "卯": "巳", "未": "巳",
    }
    huagai = {
        "寅": "戌", "午": "戌", "戌": "戌",
        "亥": "未", "卯": "未", "未": "未",
        "巳": "丑", "酉": "丑", "丑": "丑",
        "申": "辰", "子": "辰", "辰": "辰",
    }
    jiangxing = {
        "寅": "午", "午": "午", "戌": "午",
        "巳": "酉", "酉": "酉", "丑": "酉",
        "申": "子", "子": "子", "辰": "子",
        "亥": "卯", "卯": "卯", "未": "卯",
    }
    wangshen = {
        "寅": "巳", "午": "巳", "戌": "巳",
        "亥": "寅", "卯": "寅", "未": "寅",
        "巳": "申", "酉": "申", "丑": "申",
        "申": "亥", "子": "亥", "辰": "亥",
    }
    jiesha = {
        "申": "巳", "子": "巳", "辰": "巳",
        "寅": "亥", "午": "亥", "戌": "亥",
        "巳": "寅", "酉": "寅", "丑": "寅",
        "亥": "申", "卯": "申", "未": "申",
    }
    zaisha = {
        "申": "午", "子": "午", "辰": "午",
        "寅": "子", "午": "子", "戌": "子",
        "巳": "卯", "酉": "卯", "丑": "卯",
        "亥": "酉", "卯": "酉", "未": "酉",
    }

    base_pillar = {"年": "年柱", "日": "日柱"}
    for label_base, base in (("年", year_zhi), ("日", day_zhi)):
        skip = (base_pillar[label_base],)
        # 将星可落本支（酉人见酉），不 skip；桃花驿马华盖等 skip 起例柱更干净
        mark_zhi(taohua.get(base, ""), "桃花")
        mark_zhi(yima.get(base, ""), "驿马", skip_bases=skip)
        mark_zhi(huagai.get(base, ""), "华盖")
        mark_zhi(jiangxing.get(base, ""), "将星")
        mark_zhi(wangshen.get(base, ""), "亡神", skip_bases=skip)
        mark_zhi(jiesha.get(base, ""), "劫煞", skip_bases=skip)
        mark_zhi(zaisha.get(base, ""), "灾煞", skip_bases=skip)

    # 孤辰寡宿（年支）
    guchen = {
        "亥": "寅", "子": "寅", "丑": "寅",
        "寅": "巳", "卯": "巳", "辰": "巳",
        "巳": "申", "午": "申", "未": "申",
        "申": "亥", "酉": "亥", "戌": "亥",
    }
    guasu = {
        "亥": "戌", "子": "戌", "丑": "戌",
        "寅": "丑", "卯": "丑", "辰": "丑",
        "巳": "辰", "午": "辰", "未": "辰",
        "申": "未", "酉": "未", "戌": "未",
    }
    mark_zhi(guchen.get(year_zhi, ""), "孤辰", skip_bases=("年柱",))
    mark_zhi(guasu.get(year_zhi, ""), "寡宿", skip_bases=("年柱",))

    hongluan = {
        "子": "卯", "丑": "寅", "寅": "丑", "卯": "子", "辰": "亥", "巳": "戌",
        "午": "酉", "未": "申", "申": "未", "酉": "午", "戌": "巳", "亥": "辰",
    }
    tianxi = {
        "子": "酉", "丑": "申", "寅": "未", "卯": "午", "辰": "巳", "巳": "辰",
        "午": "卯", "未": "寅", "申": "丑", "酉": "子", "戌": "亥", "亥": "戌",
    }
    mark_zhi(hongluan.get(year_zhi, ""), "红鸾", skip_bases=("年柱",))
    mark_zhi(tianxi.get(year_zhi, ""), "天喜", skip_bases=("年柱",))

    goujiao = {
        "子": ("卯", "酉"), "丑": ("辰", "戌"), "寅": ("巳", "亥"), "卯": ("午", "子"),
        "辰": ("未", "丑"), "巳": ("申", "寅"), "午": ("酉", "卯"), "未": ("戌", "辰"),
        "申": ("亥", "巳"), "酉": ("子", "午"), "戌": ("丑", "未"), "亥": ("寅", "申"),
    }
    gj = goujiao.get(year_zhi)
    if gj:
        mark_zhi(gj[0], "勾绞", skip_bases=("年柱",))
        mark_zhi(gj[1], "勾绞", skip_bases=("年柱",))

    # 天德 / 月德 / 合（月支）
    tiande = {
        "寅": "丁", "卯": "申", "辰": "壬", "巳": "辛", "午": "亥", "未": "甲",
        "申": "癸", "酉": "寅", "戌": "丙", "亥": "乙", "子": "巳", "丑": "庚",
    }
    yuede = {
        "寅": "丙", "卯": "甲", "辰": "壬", "巳": "庚", "午": "丙", "未": "甲",
        "申": "壬", "酉": "庚", "戌": "丙", "亥": "甲", "子": "壬", "丑": "庚",
    }
    gan_he = {"甲": "己", "己": "甲", "乙": "庚", "庚": "乙", "丙": "辛", "辛": "丙",
              "丁": "壬", "壬": "丁", "戊": "癸", "癸": "戊"}
    td = tiande.get(month_zhi, "")
    yd = yuede.get(month_zhi, "")
    for name, (gan, zhi) in pillars.items():
        if td:
            if td in DIZHI and zhi == td:
                out[name].append("天德")
            elif td in TIANGAN and gan == td:
                out[name].append("天德")
        if yd and gan == yd:
            out[name].append("月德")
        if td in TIANGAN and gan == gan_he.get(td, ""):
            out[name].append("天德合")
        if yd and gan == gan_he.get(yd, ""):
            out[name].append("月德合")

    # 血刃（月支）
    xueyin = {
        "寅": "丑", "卯": "未", "辰": "寅", "巳": "申", "午": "卯", "未": "酉",
        "申": "辰", "酉": "戌", "戌": "巳", "亥": "亥", "子": "午", "丑": "子",
    }
    mark_zhi(xueyin.get(month_zhi, ""), "血刃")

    # 天医：正月起丑，顺行（寅月丑…戌月酉）
    if month_zhi in DIZHI:
        tianyi_zhi = DIZHI[(DIZHI.index(month_zhi) - 1) % 12]
        mark_zhi(tianyi_zhi, "天医", skip_bases=("月柱",))

    # 学堂 / 词馆：子平（日干）+ 纳音（年柱纳音五行）
    xuetang_ziping = {
        "甲": "亥", "乙": "午", "丙": "寅", "丁": "酉", "戊": "寅",
        "己": "酉", "庚": "巳", "辛": "子", "壬": "申", "癸": "卯",
    }
    ciguan_ziping = {
        "甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳",
        "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子",
    }
    mark_zhi(xuetang_ziping.get(day_master, ""), "学堂")
    mark_zhi(ciguan_ziping.get(day_master, ""), "词馆")

    year_nayin = nayin_of(year_gan, year_zhi)
    nayin_wx = ""
    for wx in ("金", "木", "水", "火", "土"):
        if wx in year_nayin:
            nayin_wx = wx
            break
    # 纳音学堂=长生，词馆=临官
    nayin_xuetang = {"金": "巳", "木": "亥", "水": "申", "土": "申", "火": "寅"}
    nayin_ciguan = {"金": "申", "木": "寅", "水": "亥", "土": "亥", "火": "巳"}
    mark_zhi(nayin_xuetang.get(nayin_wx, ""), "学堂", skip_bases=("年柱",))
    mark_zhi(nayin_ciguan.get(nayin_wx, ""), "词馆", skip_bases=("年柱",))

    # 天罗地网：戌亥天罗，辰巳地网（落柱即标，主流软件常见）
    for name, zhi in branches.items():
        if zhi in ("戌", "亥"):
            out[name].append("天罗")
        if zhi in ("辰", "巳"):
            out[name].append("地网")

    # 太岁十二神相关（自年支起）：丧门+2、官符+4、白虎+8、吊客+10、病符+11、披麻+3
    if year_zhi in DIZHI:
        yi = DIZHI.index(year_zhi)
        mark_zhi(DIZHI[(yi + 2) % 12], "丧门", skip_bases=("年柱",))
        mark_zhi(DIZHI[(yi + 3) % 12], "披麻", skip_bases=("年柱",))
        mark_zhi(DIZHI[(yi + 4) % 12], "官符", skip_bases=("年柱",))
        mark_zhi(DIZHI[(yi + 8) % 12], "白虎", skip_bases=("年柱",))
        mark_zhi(DIZHI[(yi + 10) % 12], "吊客", skip_bases=("年柱",))
        mark_zhi(DIZHI[(yi + 11) % 12], "病符", skip_bases=("年柱",))

    # 元辰：阳男阴女见大耗（年支后六位之对冲再推：子未…）；阴男阳女相反
    yuanchen_yang = {
        "子": "未", "丑": "申", "寅": "酉", "卯": "戌", "辰": "亥", "巳": "子",
        "午": "丑", "未": "寅", "申": "卯", "酉": "辰", "戌": "巳", "亥": "午",
    }
    yuanchen_yin = {
        "子": "巳", "丑": "午", "寅": "未", "卯": "申", "辰": "酉", "巳": "戌",
        "午": "亥", "未": "子", "申": "丑", "酉": "寅", "戌": "卯", "亥": "辰",
    }
    year_yang = year_gan in ("甲", "丙", "戊", "庚", "壬")
    is_male = "女" not in (gender or "男")
    # 阳男阴女用 yang 表；阴男阳女用 yin 表
    use_yang_table = (is_male and year_yang) or ((not is_male) and (not year_yang))
    yc = (yuanchen_yang if use_yang_table else yuanchen_yin).get(year_zhi, "")
    mark_zhi(yc, "元辰", skip_bases=("年柱",))

    # —— 日柱专煞 ——
    day_gz = f"{day_master}{day_zhi}"
    if day_gz in ("庚辰", "庚戌", "壬辰", "戊戌"):
        out["日柱"].append("魁罡")
    if day_gz in ("乙丑", "己巳", "癸酉"):
        out["日柱"].append("金神")
    # 金神亦查年柱
    year_gz = f"{year_gan}{year_zhi}"
    if year_gz in ("乙丑", "己巳", "癸酉"):
        out["年柱"].append("金神")

    yinyang_cuocuo = {
        "丙子", "丁丑", "戊寅", "辛卯", "壬辰", "癸巳",
        "丙午", "丁未", "戊申", "辛酉", "壬戌", "癸亥",
    }
    if day_gz in yinyang_cuocuo:
        out["日柱"].append("阴差阳错")

    guluan = {"甲寅", "乙巳", "丙午", "丁巳", "戊午", "戊申", "辛亥", "壬子"}
    if day_gz in guluan:
        out["日柱"].append("孤鸾煞")

    shie = {
        "甲辰", "乙巳", "壬申", "丙申", "丁亥", "庚辰", "戊戌", "癸亥",
        "己丑", "甲戌",
    }
    if day_gz in shie:
        out["日柱"].append("十恶大败")

    # 四废：春庚申辛酉，夏壬子癸亥，秋甲寅乙卯，冬丙午丁巳
    season = {
        "寅": "春", "卯": "春", "辰": "春",
        "巳": "夏", "午": "夏", "未": "夏",
        "申": "秋", "酉": "秋", "戌": "秋",
        "亥": "冬", "子": "冬", "丑": "冬",
    }
    sifei = {
        "春": {"庚申", "辛酉"},
        "夏": {"壬子", "癸亥"},
        "秋": {"甲寅", "乙卯"},
        "冬": {"丙午", "丁巳"},
    }
    if day_gz in sifei.get(season.get(month_zhi, ""), set()):
        out["日柱"].append("四废")

    # 天赦：春戊寅，夏甲午，秋戊申，冬甲子
    tianshe = {"春": "戊寅", "夏": "甲午", "秋": "戊申", "冬": "甲子"}
    if day_gz == tianshe.get(season.get(month_zhi, ""), ""):
        out["日柱"].append("天赦")

    for k in out:
        out[k] = _sort_shensha(out[k])
    return out
