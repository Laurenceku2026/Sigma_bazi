"""
二十四节气（定气近似）。
用于：年柱立春分界、月柱十二节分界。
算法：寿星天文历常用 C 值表 + 世纪修正，民用排盘足够。
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Tuple

JIEQI_NAMES = [
    "小寒", "大寒", "立春", "雨水", "惊蛰", "春分",
    "清明", "谷雨", "立夏", "小满", "芒种", "夏至",
    "小暑", "大暑", "立秋", "处暑", "白露", "秋分",
    "寒露", "霜降", "立冬", "小雪", "大雪", "冬至",
]

# 节（分月）→ 地支
JIE_TO_BRANCH = {
    0: "丑", 2: "寅", 4: "卯", 6: "辰", 8: "巳", 10: "午",
    12: "未", 14: "申", 16: "酉", 18: "戌", 20: "亥", 22: "子",
}

# 20 世纪 / 21 世纪 C 值（寿星表节选，按小寒起）
_C_20 = [
    6.11, 20.84, 4.6295, 19.4599, 6.3826, 21.4155,
    5.59, 20.888, 6.318, 21.86, 6.5, 22.2,
    7.928, 23.65, 8.35, 23.95, 8.44, 23.822,
    9.098, 24.218, 8.218, 23.08, 7.9, 22.6,
]
_C_21 = [
    5.4055, 20.12, 3.87, 18.73, 5.63, 20.646,
    4.81, 20.1, 5.52, 21.04, 5.678, 21.37,
    7.108, 22.83, 7.5, 23.13, 7.646, 23.042,
    8.318, 23.438, 7.438, 22.36, 7.18, 21.94,
]

# 各节气大致所在公历月（1-12）
_MONTH_OF = [
    1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6,
    7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12,
]


def jieqi_datetime(year: int, n: int) -> datetime:
    """公历 year 年第 n 个节气（0=小寒 … 23=冬至）的近似时刻。"""
    n = n % 24
    c = (_C_21 if year >= 2000 else _C_20)[n]
    y = year % 100
    if year >= 2000:
        day_f = y * 0.2422 + c - int((y - 1) / 4)
    else:
        day_f = y * 0.2422 + c - int(y / 4)
    day = int(day_f)
    hour = int((day_f - day) * 24)
    month = _MONTH_OF[n]
    # 防止 day 超出月份
    for _ in range(3):
        try:
            return datetime(year, month, day, hour, 0)
        except ValueError:
            day -= 1
            if day < 1:
                day = 1
                break
    return datetime(year, month, 1, hour, 0)


def lichun(year: int) -> datetime:
    return jieqi_datetime(year, 2)


def month_branch_by_jieqi(dt: datetime) -> Tuple[str, str]:
    """按「节」取月支，返回 (地支, 节名)。"""
    y = dt.year
    points: List[Tuple[datetime, int]] = []
    for yy in (y - 1, y, y + 1):
        for n in (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22):
            points.append((jieqi_datetime(yy, n), n))
    points.sort(key=lambda x: x[0])
    branch, name = "丑", "小寒"
    for jq_dt, n in points:
        if dt >= jq_dt:
            branch = JIE_TO_BRANCH[n]
            name = JIEQI_NAMES[n]
        else:
            break
    return branch, name

# 十二「节」（分月界，不含中气）
JIE_INDICES = (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22)


def _jie_points_around(dt: datetime) -> List[Tuple[datetime, int, str]]:
    y = dt.year
    pts = []
    for yy in (y - 1, y, y + 1):
        for n in JIE_INDICES:
            pts.append((jieqi_datetime(yy, n), n, JIEQI_NAMES[n]))
    pts.sort(key=lambda x: x[0])
    return pts


def prev_next_jie(dt: datetime) -> Tuple[Tuple[datetime, str], Tuple[datetime, str]]:
    """返回 (上一节, 下一节)，各为 (时刻, 节名)。"""
    pts = _jie_points_around(dt)
    prev = (pts[0][0], pts[0][2])
    nxt = (pts[-1][0], pts[-1][2])
    for i, (jq_dt, _n, name) in enumerate(pts):
        if jq_dt <= dt:
            prev = (jq_dt, name)
            if i + 1 < len(pts):
                nxt = (pts[i + 1][0], pts[i + 1][2])
        else:
            nxt = (jq_dt, name)
            break
    return prev, nxt


def qi_yun_from_jieqi(birth: datetime, forward: bool) -> dict:
    """
    起运：顺行数至下一节，逆行数至上一节；三天折一年，一天折四月。
    """
    prev, nxt = prev_next_jie(birth)
    target_dt, target_name = (nxt if forward else prev)
    delta = (target_dt - birth) if forward else (birth - target_dt)
    total_seconds = abs(delta.total_seconds())
    total_days = total_seconds / 86400.0
    years = int(total_days // 3)
    rem_days = total_days - years * 3
    months = int(rem_days * 4)
    if months >= 12:
        years += months // 12
        months = months % 12
    age_float = years + months / 12.0
    age_label = f"{years}岁{months}个月" if months else f"{years}岁"
    return {
        "years": years,
        "months": months,
        "days_span": round(total_days, 2),
        "target_jie": target_name,
        "target_dt": target_dt.isoformat(sep=" ", timespec="minutes"),
        "forward": forward,
        "age_years_float": age_float,
        "age_label": age_label,
        "start_age": max(1, years) if total_days >= 1 else 1,
    }
