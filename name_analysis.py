"""
姓名学参考（五格剖象 + 汉字五行 + 与八字喜用对照）

规则要点：
- 笔画以康熙/繁体为准；简体输入会先转繁再查表
- 数理五行：尾数 1/2木 3/4火 5/6土 7/8金 9/0水
- 与八字结合：按喜用神对照，而非简单「缺啥补啥」
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from zh_convert import to_traditional

_DATA = Path(__file__).resolve().parent / "data" / "hanzi_strokes.json"


def _is_en(lang: str) -> bool:
    return (lang or "zh") == "en"


def _loc(text: str, lang: str) -> str:
    """中文简体文案；繁体界面再转繁。"""
    if not text or _is_en(lang):
        return text
    if lang == "zh_hant":
        return to_traditional(text)
    return text


def _luck_label(luck: str, lang: str) -> str:
    if _is_en(lang):
        return {"吉": "Auspicious", "半吉": "Mixed", "凶": "Inauspicious"}.get(luck, luck)
    return _loc(luck, lang)


def _wx_label(wx: str, lang: str) -> str:
    if not wx:
        return "—"
    if _is_en(lang):
        return {"木": "Wood", "火": "Fire", "土": "Earth", "金": "Metal", "水": "Water"}.get(wx, wx)
    return _loc(wx, lang)

# 姓名学常见康熙笔画校正（与通用笔顺库不一致时）
_NAMEOLOGY_STROKE_OVERRIDES: Dict[str, int] = {
    "華": 12,
    "興": 16,
    "艷": 24,
    "靈": 24,
    "鬱": 29,
    "龜": 16,
    "龍": 16,
    "廣": 15,
    "廳": 25,
    "麗": 19,
    "彎": 22,
    "歡": 22,
    "觀": 25,
    "權": 22,
    "勸": 20,
    "獲": 17,
    "護": 21,
    "黨": 20,
    "齊": 14,
    "齋": 17,
    "齒": 15,
    "齡": 20,
    "麵": 20,
    "麥": 11,
    "鳳": 14,
    "鳥": 11,
    "鴨": 16,
    "鵝": 18,
    "雞": 18,
    "雙": 18,
    "雜": 18,
    "難": 19,
    "離": 19,
    "霧": 18,
    "霸": 21,
    "露": 21,
    "霹": 21,
    "靂": 24,
}

# 81 数理简表：吉 / 半吉 / 凶（参考五格剖象常用归类，供参考）
_NUM_LUCK: Dict[int, str] = {
    1: "吉", 2: "凶", 3: "吉", 4: "凶", 5: "吉", 6: "吉", 7: "吉", 8: "吉", 9: "凶",
    10: "凶", 11: "吉", 12: "凶", 13: "吉", 14: "凶", 15: "吉", 16: "吉", 17: "吉",
    18: "吉", 19: "凶", 20: "凶", 21: "吉", 22: "凶", 23: "吉", 24: "吉", 25: "吉",
    26: "凶", 27: "凶", 28: "凶", 29: "吉", 30: "半吉", 31: "吉", 32: "吉", 33: "吉",
    34: "凶", 35: "吉", 36: "凶", 37: "吉", 38: "半吉", 39: "吉", 40: "半吉",
    41: "吉", 42: "凶", 43: "凶", 44: "凶", 45: "吉", 46: "凶", 47: "吉", 48: "吉",
    49: "凶", 50: "半吉", 51: "半吉", 52: "吉", 53: "吉", 54: "凶", 55: "半吉",
    56: "凶", 57: "吉", 58: "半吉", 59: "半吉", 60: "凶", 61: "吉", 62: "凶",
    63: "吉", 64: "凶", 65: "吉", 66: "凶", 67: "吉", 68: "吉", 69: "凶",
    70: "凶", 71: "半吉", 72: "半吉", 73: "半吉", 74: "凶", 75: "半吉", 76: "凶",
    77: "半吉", 78: "半吉", 79: "凶", 80: "凶", 81: "吉",
}

# 部首 → 五行（字形五行，辅助）
_RADICAL_WUXING: Dict[str, str] = {
    "木": "木", "艹": "木", "竹": "木", "禾": "木", "米": "木", "瓜": "木", "豆": "木",
    "水": "水", "氵": "水", "冫": "水", "雨": "水", "川": "水",
    "火": "火", "灬": "火", "日": "火", "赤": "火",
    "土": "土", "山": "土", "石": "土", "田": "土", "厂": "土", "阝": "土",
    "金": "金", "钅": "金", "釒": "金", "刀": "金", "刂": "金", "戈": "金",
    "矛": "金", "斤": "金", "车": "金", "車": "金",
}

# 字义关键词 → 五行
_MEANING_KEYWORDS: List[Tuple[str, str]] = [
    ("木|林|森|树|柳|梅|松|柏|桐|楠|梓|荣|華|花|叶|竹|禾", "木"),
    ("水|雨|江|河|湖|海|泉|波|涛|涵|泽|潤|清|溪|澜|潮", "水"),
    ("火|炎|焰|煜|晖|晖|阳|日|昊|晓|晴|朗|辉|煊|烨|炤", "火"),
    ("土|山|岩|峰|城|坤|培|垚|垒|坚|安|宇|宏|坦", "土"),
    ("金|钜|钧|铭|锐|锋|钢|锦|钰|银|铁|鑫|铠|镇", "金"),
]

_COMPOUND_SURNAMES = {
    "歐陽", "司马", "司馬", "上官", "皇甫", "诸葛", "諸葛", "东方", "東方",
    "尉迟", "尉遲", "公孙", "公孫", "慕容", "长孙", "長孫", "司徒", "司空",
    "端木", "夏侯", "赫连", "赫連", "宇文", "轩辕", "軒轅", "令狐", "呼延",
    "南宫", "南宮", "独孤", "獨孤", "闻人", "聞人",
}


@lru_cache(maxsize=1)
def _stroke_table() -> Dict[str, int]:
    if not _DATA.is_file():
        return {}
    try:
        with _DATA.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        return {str(k): int(v) for k, v in raw.items() if v}
    except Exception:
        return {}


def stroke_of(ch: str) -> Optional[int]:
    """康熙/姓名学笔画；未知返回 None。"""
    if not ch:
        return None
    if ch in _NAMEOLOGY_STROKE_OVERRIDES:
        return _NAMEOLOGY_STROKE_OVERRIDES[ch]
    table = _stroke_table()
    if ch in table:
        return table[ch]
    # 数字字
    digit_map = {
        "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    }
    return digit_map.get(ch)


def number_wuxing(n: int) -> str:
    """数理五行（尾数）。"""
    d = int(n) % 10
    if d in (1, 2):
        return "木"
    if d in (3, 4):
        return "火"
    if d in (5, 6):
        return "土"
    if d in (7, 8):
        return "金"
    return "水"  # 9, 0


def number_luck(n: int) -> str:
    k = ((int(n) - 1) % 81) + 1
    return _NUM_LUCK.get(k, "半吉")


def _is_cjk(ch: str) -> bool:
    o = ord(ch)
    return (
        0x4E00 <= o <= 0x9FFF
        or 0x3400 <= o <= 0x4DBF
        or 0xF900 <= o <= 0xFAFF
    )


def normalize_name_chars(name: str) -> Tuple[str, str]:
    """返回 (显示用原名清洗, 繁体用于计算)。"""
    raw = re.sub(r"\s+", "", (name or "").strip())
    # 去掉非汉字（保留·）
    cleaned = "".join(ch for ch in raw if _is_cjk(ch) or ch in "·・")
    trad = to_traditional(cleaned.replace("・", "·"))
    return cleaned, trad


def split_surname_given(
    trad_name: str,
    *,
    compound: Optional[bool] = None,
) -> Tuple[str, str, bool]:
    """拆姓/名。compound=None 时自动识别常见复姓。"""
    name = trad_name.replace("·", "").replace("・", "")
    if not name:
        return "", "", False
    is_compound = False
    if compound is True and len(name) >= 3:
        is_compound = True
        surname, given = name[:2], name[2:]
    elif compound is False:
        surname, given = name[0], name[1:]
    else:
        if len(name) >= 3 and name[:2] in _COMPOUND_SURNAMES:
            is_compound = True
            surname, given = name[:2], name[2:]
        else:
            surname, given = name[0], name[1:]
    return surname, given, is_compound


def char_wuxing_hints(ch: str) -> Dict[str, Any]:
    """字形（部首启发）+ 字义关键词 → 五行提示。"""
    radical_wx = ""
    for rad, wx in _RADICAL_WUXING.items():
        if ch == rad or rad in ch:
            radical_wx = wx
            break
    meaning_wx = ""
    for pattern, wx in _MEANING_KEYWORDS:
        parts = [p for p in pattern.split("|") if p]
        if ch in parts or any(p in ch for p in parts if len(p) > 1):
            meaning_wx = wx
            break
    primary = meaning_wx or radical_wx or ""
    return {
        "char": ch,
        "radical_wuxing": radical_wx,
        "meaning_wuxing": meaning_wx,
        "char_wuxing": primary,
    }


def compute_wuge(surname: str, given: str, *, compound: bool) -> Dict[str, Any]:
    s_strokes = [stroke_of(c) for c in surname]
    g_strokes = [stroke_of(c) for c in given]
    if any(x is None for x in s_strokes + g_strokes) or not surname or not given:
        missing = [
            c for c, n in zip(surname + given, s_strokes + g_strokes) if n is None
        ]
        return {"ok": False, "missing": missing}

    s_nums = [int(x) for x in s_strokes]  # type: ignore
    g_nums = [int(x) for x in g_strokes]  # type: ignore
    total = sum(s_nums) + sum(g_nums)

    if compound:
        # 复姓
        tian = sum(s_nums)
        if len(given) == 1:
            ren = s_nums[-1] + g_nums[0]
            di = g_nums[0] + 1
            wai = s_nums[0] + 1
        else:
            ren = s_nums[-1] + g_nums[0]
            di = g_nums[0] + g_nums[1]
            wai = s_nums[0] + g_nums[-1]
    else:
        # 单姓
        tian = s_nums[0] + 1
        if len(given) == 1:
            ren = s_nums[0] + g_nums[0]
            di = g_nums[0] + 1
            wai = 2
        else:
            ren = s_nums[0] + g_nums[0]
            di = g_nums[0] + g_nums[1]
            wai = g_nums[-1] + 1

    def pack(n: int) -> Dict[str, Any]:
        return {
            "number": n,
            "wuxing": number_wuxing(n),
            "luck": number_luck(n),
        }

    return {
        "ok": True,
        "chars": [
            {"char": c, "strokes": n, "stroke_wuxing": number_wuxing(n)}
            for c, n in zip(surname + given, s_nums + g_nums)
        ],
        "tian": pack(tian),
        "ren": pack(ren),
        "di": pack(di),
        "wai": pack(wai),
        "zong": pack(total),
        "sancai": {
            "combo": f"{number_wuxing(tian)}{number_wuxing(ren)}{number_wuxing(di)}",
            "tian": number_wuxing(tian),
            "ren": number_wuxing(ren),
            "di": number_wuxing(di),
        },
    }


def _sheng_ke_relation(a: str, b: str) -> str:
    """a 相对 b：同 / 生 / 被生 / 克 / 被克 / 其他。"""
    sheng = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    ke = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
    if not a or not b:
        return "其他"
    if a == b:
        return "比和"
    if sheng.get(a) == b:
        return "我生"
    if sheng.get(b) == a:
        return "生我"
    if ke.get(a) == b:
        return "我克"
    if ke.get(b) == a:
        return "克我"
    return "其他"


def analyze_name_with_bazi(
    name: str,
    bazi_data: Optional[Dict[str, Any]],
    *,
    compound: Optional[bool] = None,
    lang: str = "zh",
) -> Dict[str, Any]:
    """完整姓名分析（本地）。"""
    from bazi_analysis import estimate_day_strength

    display, trad = normalize_name_chars(name)
    surname, given, is_compound = split_surname_given(trad, compound=compound)
    en = _is_en(lang)

    if not surname or not given:
        return {
            "ok": False,
            "lang": lang,
            "error": "need_fullname",
            "message": (
                "Please enter a Chinese name with surname + given name."
                if en
                else _loc("请输入含姓与名的中文姓名（至少两字）。", lang)
            ),
        }

    wuge = compute_wuge(surname, given, compound=is_compound)
    if not wuge.get("ok"):
        missing = "、".join(wuge.get("missing") or [])
        return {
            "ok": False,
            "lang": lang,
            "error": "unknown_strokes",
            "message": (
                f"No Kangxi stroke data for: {missing}. Try traditional form or another character."
                if en
                else _loc(f"暂无康熙笔画数据：{missing}。可改用常见繁体字，或调整用字。", lang)
            ),
            "display_name": display,
            "traditional_name": trad,
            "missing": wuge.get("missing"),
        }

    char_details = []
    for item in wuge["chars"]:
        hints = char_wuxing_hints(item["char"])
        char_details.append({**item, **hints})

    strength = estimate_day_strength(bazi_data) if bazi_data else {
        "level": "balanced",
        "favor": set(),
        "avoid": set(),
        "dm_wx": "",
    }
    favor = set(strength.get("favor") or [])
    avoid = set(strength.get("avoid") or [])
    wx_stats = (bazi_data or {}).get("wuxing_stats") or {}
    missing_wx = [w for w in ("木", "火", "土", "金", "水") if int(wx_stats.get(w, 0) or 0) <= 0]

    # 姓名侧五行信号：人格/总格数理 + 用字五行
    name_wx_signals: List[str] = []
    for key in ("ren", "zong", "di"):
        name_wx_signals.append(wuge[key]["wuxing"])
    for c in char_details:
        if c.get("char_wuxing"):
            name_wx_signals.append(c["char_wuxing"])

    help_favor = sorted({w for w in name_wx_signals if w in favor})
    hit_avoid = sorted({w for w in name_wx_signals if w in avoid})

    # 三才简评
    sc = wuge["sancai"]
    relations = [
        _sheng_ke_relation(sc["tian"], sc["ren"]),
        _sheng_ke_relation(sc["ren"], sc["di"]),
    ]
    if all(r in ("比和", "我生", "生我") for r in relations):
        sancai_tone = "harmonious" if en else _loc("较顺", lang)
    elif any(r in ("我克", "克我") for r in relations):
        sancai_tone = "mixed" if en else _loc("有克战", lang)
    else:
        sancai_tone = "neutral" if en else _loc("中平", lang)

    summary_lines = _build_summary(
        display=display,
        trad=trad,
        wuge=wuge,
        favor=favor,
        avoid=avoid,
        help_favor=help_favor,
        hit_avoid=hit_avoid,
        missing_wx=missing_wx,
        sancai_tone=sancai_tone,
        lang=lang,
    )
    detail_lines = _build_details(
        char_details=char_details,
        wuge=wuge,
        favor=favor,
        avoid=avoid,
        help_favor=help_favor,
        hit_avoid=hit_avoid,
        missing_wx=missing_wx,
        strength=strength,
        sancai_tone=sancai_tone,
        lang=lang,
    )

    return {
        "ok": True,
        "lang": lang,
        "display_name": display,
        "traditional_name": trad,
        "surname": surname,
        "given": given,
        "compound": is_compound,
        "wuge": wuge,
        "chars": char_details,
        "bazi": {
            "dm_wx": strength.get("dm_wx") or "",
            "level": strength.get("level") or "balanced",
            "favor": sorted(favor),
            "avoid": sorted(avoid),
            "missing_in_chart": missing_wx,
            "name_helps_favor": help_favor,
            "name_hits_avoid": hit_avoid,
        },
        "sancai_tone": sancai_tone,
        "summary_lines": summary_lines,
        "detail_lines": detail_lines,
        "disclaimer": (
            "Reference only: Kangxi strokes + Five-Grid theory. "
            "Supplement the favorable elements (喜用), not merely missing ones. Not a rename guarantee."
            if en
            else _loc(
                "仅供参考：笔画按康熙/繁体；补的是八字喜用，不是简单缺啥补啥；不构成改名承诺。",
                lang,
            )
        ),
    }


def _join_wx(items: Sequence[str], lang: str) -> str:
    if not items:
        return "—"
    sep = ", " if _is_en(lang) else "、"
    return sep.join(_wx_label(x, lang) for x in items)


def _build_summary(**kw) -> List[str]:
    lang = kw["lang"]
    wuge = kw["wuge"]
    en = _is_en(lang)
    if en:
        return [
            f"Name: {kw['display']} → Kangxi/traditional for strokes: {kw['trad']}",
            f"Five grids — Heaven {wuge['tian']['number']}({_wx_label(wuge['tian']['wuxing'], lang)}), "
            f"Person {wuge['ren']['number']}({_wx_label(wuge['ren']['wuxing'], lang)}), "
            f"Earth {wuge['di']['number']}({_wx_label(wuge['di']['wuxing'], lang)}), "
            f"Total {wuge['zong']['number']}({_wx_label(wuge['zong']['wuxing'], lang)}).",
            f"San Cai: {_loc(wuge['sancai']['combo'], lang)} ({kw['sancai_tone']}).",
            f"Vs BaZi favor {_join_wx(kw['favor'], lang)}: name signals help {_join_wx(kw['help_favor'], lang)}; "
            f"caution {_join_wx(kw['hit_avoid'], lang)}.",
            "Rule: reinforce favorable elements, not simply fill missing ones.",
        ]
    # 输入名保持原样，避免繁体界面把简体输入也转掉，便于看清「输入→康熙/繁体」
    convert = (
        f"{_loc('姓名：', lang)}{kw['display']}"
        f"{_loc(' → 计画用康熙/繁体：', lang)}{kw['trad']}"
    )
    rest = [
        f"五格：天{wuge['tian']['number']}({wuge['tian']['wuxing']}) · "
        f"人{wuge['ren']['number']}({wuge['ren']['wuxing']}) · "
        f"地{wuge['di']['number']}({wuge['di']['wuxing']}) · "
        f"总{wuge['zong']['number']}({wuge['zong']['wuxing']})",
        f"三才：{wuge['sancai']['combo']}（{kw['sancai_tone']}）",
        f"对照八字喜用（{_join_wx(kw['favor'], lang)}）：姓名侧扶助 {_join_wx(kw['help_favor'], lang)}；"
        f"需留意 {_join_wx(kw['hit_avoid'], lang)}",
        "要点：按喜用神补益，不是命盘缺什么就补什么。",
    ]
    return [convert] + [_loc(x, lang) for x in rest]


def _build_details(**kw) -> List[str]:
    lang = kw["lang"]
    en = _is_en(lang)
    lines: List[str] = []
    wuge = kw["wuge"]
    if en:
        lines.append("Character strokes & element hints")
        for c in kw["char_details"]:
            lines.append(
                f"- {c['char']}: {c['strokes']} strokes "
                f"(number-element {_wx_label(c['stroke_wuxing'], lang)}); "
                f"char hint {_wx_label(c.get('char_wuxing') or '', lang)}"
            )
        lines.append(
            f"Grids luck: Tian {_luck_label(wuge['tian']['luck'], lang)}, "
            f"Ren {_luck_label(wuge['ren']['luck'], lang)}, "
            f"Di {_luck_label(wuge['di']['luck'], lang)}, "
            f"Wai {_luck_label(wuge['wai']['luck'], lang)}, "
            f"Zong {_luck_label(wuge['zong']['luck'], lang)}"
        )
        lvl = kw["strength"].get("level")
        lines.append(
            f"BaZi day-master tendency: {lvl}; favor {_join_wx(kw['favor'], lang)}; "
            f"caution {_join_wx(kw['avoid'], lang)}"
        )
        lines.append(f"Elements absent in chart counts: {_join_wx(kw['missing_wx'], lang)}")
        lines.append(
            "Interpretation: if a missing element is also favorable, name support is constructive; "
            "if missing but unfavorable, do not add it just to complete the set."
        )
        if kw["help_favor"]:
            lines.append(f"This name leans toward helping: {_join_wx(kw['help_favor'], lang)}.")
        if kw["hit_avoid"]:
            lines.append(f"Watch elements that may stress the chart: {_join_wx(kw['hit_avoid'], lang)}.")
        lines.append("San Cai tone: " + kw["sancai_tone"])
        return lines

    raw = [
        "【用字笔画与五行提示】",
    ]
    for c in kw["char_details"]:
        raw.append(
            f"- {c['char']}：康熙/姓名学 {c['strokes']} 画（数理{c['stroke_wuxing']}）；"
            f"字义/部首提示 {c.get('char_wuxing') or '—'}"
        )
    raw.append(
        f"【五格吉凶参考】天{_luck_label(wuge['tian']['luck'], lang)} · "
        f"人{_luck_label(wuge['ren']['luck'], lang)} · "
        f"地{_luck_label(wuge['di']['luck'], lang)} · "
        f"外{_luck_label(wuge['wai']['luck'], lang)} · "
        f"总{_luck_label(wuge['zong']['luck'], lang)}"
    )
    lvl_map = {"strong": "偏强", "weak": "偏弱", "balanced": "中和"}
    lvl = lvl_map.get(kw["strength"].get("level"), "中和")
    raw.append(
        f"【八字对照】日主{lvl}；喜用 {_join_wx(kw['favor'], lang)}；慎用 {_join_wx(kw['avoid'], lang)}"
    )
    raw.append(f"命盘计数为 0 的五行：{_join_wx(kw['missing_wx'], lang)}")
    raw.append(
        "解读：若「缺」的恰是喜用，名字扶助有建设性；"
        "若只是缺但属忌神，不必为凑齐五行而补。"
    )
    if kw["help_favor"]:
        raw.append(f"本姓名偏向扶助：{_join_wx(kw['help_favor'], lang)}。")
    if kw["hit_avoid"]:
        raw.append(f"需留意可能加重慎用的信号：{_join_wx(kw['hit_avoid'], lang)}。")
    raw.append(f"三才观感：{kw['sancai_tone']}")
    return [_loc(x, lang) for x in raw]


def render_name_report_html(result: Dict[str, Any], *, full: bool, lang: str) -> str:
    """生成可展示 HTML（随当前界面语言）。"""
    if not result.get("ok"):
        msg = result.get("message") or (
            "Analysis failed" if _is_en(lang) else _loc("分析失败", lang)
        )
        return f"<p>{msg}</p>"

    def esc(s: Any) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    title = "Name Reference Report" if _is_en(lang) else _loc("姓名参考报告", lang)
    src = result.get("display_name") or ""
    trad = result.get("traditional_name") or ""
    convert_line = (
        f"Stroke conversion: 「{src}」 → Kangxi/traditional 「{trad}」"
        if _is_en(lang)
        else f"{_loc('计画转换：输入「', lang)}{src}{_loc('」→ 康熙/繁体「', lang)}{trad}{_loc('」', lang)}"
    )
    blocks = [
        f"<h3>{esc(title)}</h3>",
        f"<p><strong>{esc(convert_line)}</strong></p>",
        "<ul>",
    ]
    for line in result.get("summary_lines") or []:
        blocks.append(f"<li>{esc(line)}</li>")
    blocks.append("</ul>")

    if full:
        blocks.append("<hr/>")
        sub = "Full reading" if _is_en(lang) else _loc("完整解读", lang)
        blocks.append(f"<h4>{esc(sub)}</h4><ul>")
        for line in result.get("detail_lines") or []:
            blocks.append(f"<li>{esc(line)}</li>")
        blocks.append("</ul>")
        w = result.get("wuge") or {}
        labels = (
            [("Heaven", "tian"), ("Person", "ren"), ("Earth", "di"), ("Outer", "wai"), ("Total", "zong")]
            if _is_en(lang)
            else [
                (_loc("天格", lang), "tian"),
                (_loc("人格", lang), "ren"),
                (_loc("地格", lang), "di"),
                (_loc("外格", lang), "wai"),
                (_loc("总格", lang), "zong"),
            ]
        )
        blocks.append("<table style='width:100%;border-collapse:collapse;font-size:0.95rem;'>")
        for lab, key in labels:
            cell = w.get(key) or {}
            blocks.append(
                "<tr>"
                f"<td style='border:1px solid #ccc;padding:6px;'>{esc(lab)}</td>"
                f"<td style='border:1px solid #ccc;padding:6px;'>{esc(cell.get('number'))}</td>"
                f"<td style='border:1px solid #ccc;padding:6px;'>{esc(_wx_label(str(cell.get('wuxing') or ''), lang))}</td>"
                f"<td style='border:1px solid #ccc;padding:6px;'>{esc(_luck_label(str(cell.get('luck') or ''), lang))}</td>"
                "</tr>"
            )
        blocks.append("</table>")

    blocks.append(
        f"<p style='opacity:0.75;font-size:0.85rem;'>{esc(result.get('disclaimer'))}</p>"
    )
    return "\n".join(blocks)
