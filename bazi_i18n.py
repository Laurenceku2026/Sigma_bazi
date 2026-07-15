"""
八字术语英译（行业通行译名，供英文界面命盘展示）。
参考：Heavenly Stems / Earthly Branches / Ten Gods / Hidden Stems。
"""
from __future__ import annotations

# 天干 Heavenly Stems — 汉字 + 威妥玛/拼音罗马字（BaZi 英文文献通用）
STEM_EN = {
    "甲": "Jia",
    "乙": "Yi",
    "丙": "Bing",
    "丁": "Ding",
    "戊": "Wu",
    "己": "Ji",
    "庚": "Geng",
    "辛": "Xin",
    "壬": "Ren",
    "癸": "Gui",
}

# 地支 Earthly Branches
BRANCH_EN = {
    "子": "Zi",
    "丑": "Chou",
    "寅": "Yin",
    "卯": "Mao",
    "辰": "Chen",
    "巳": "Si",
    "午": "Wu",
    "未": "Wei",
    "申": "Shen",
    "酉": "You",
    "戌": "Xu",
    "亥": "Hai",
}

# 十神 Ten Gods（标准英文）
TEN_GOD_EN = {
    "比肩": "Friend",
    "劫财": "Rob Wealth",
    "食神": "Eating God",
    "伤官": "Hurting Officer",
    "正财": "Direct Wealth",
    "偏财": "Indirect Wealth",
    "正官": "Direct Officer",
    "七杀": "Seven Killings",
    "偏官": "Seven Killings",
    "正印": "Direct Resource",
    "偏印": "Indirect Resource",
    "日主": "Day Master",
}

# 五行
WUXING_EN = {
    "木": "Wood",
    "火": "Fire",
    "土": "Earth",
    "金": "Metal",
    "水": "Water",
}

LABEL_EN = {
    "十神": "Ten Gods",
    "天干": "Heavenly Stem",
    "地支": "Earthly Branch",
    "藏干": "Hidden Stems",
    "年柱": "Year",
    "月柱": "Month",
    "日柱": "Day",
    "时柱": "Hour",
    "大运": "Da Yun",
    "流年": "Liu Nian",
    "流月": "Liu Yue",
    "流日": "Liu Ri",
    "日主": "Day Master",
    "性别": "Gender",
    "八字排盘结果": "BaZi Chart",
    "五行配色": "Five Elements colors",
}


def gan_display(ch: str, lang: str = "zh") -> str:
    if lang != "en":
        return ch
    roman = STEM_EN.get(ch) or BRANCH_EN.get(ch)
    return f"{ch} {roman}" if roman else ch


def ten_god_display(god: str, lang: str = "zh") -> str:
    if not god:
        return "—" if lang == "en" else "—"
    if lang != "en":
        return god
    return TEN_GOD_EN.get(god, god)


def wuxing_display(wx: str, lang: str = "zh") -> str:
    if lang != "en":
        return wx
    return WUXING_EN.get(wx, wx)


def chart_label(zh: str, lang: str = "zh") -> str:
    if lang != "en":
        return zh
    return LABEL_EN.get(zh, zh)
