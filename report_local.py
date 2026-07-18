"""
本地规则版命理报告（不调用 DeepSeek）。
结构与 AI 报告一致：page1–page9 + 可选 page10 流年，便于同一套 UI/存档复用。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from bazi_analysis import (
    WUXING_MAP,
    analyze_personality,
    build_lifetime_fortune,
    estimate_day_strength,
)
from report_generator import ReportGenerator


def _trad(text: str, lang: str) -> str:
    if lang != "zh_hant" or not text:
        return text
    try:
        from zh_convert import to_traditional

        return to_traditional(text)
    except Exception:
        return text


def _page(
    title: str,
    professional: List[str],
    *,
    summary: str,
    points: List[str],
    detail: str,
    lang: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    page = {
        "title": _trad(title, lang),
        "professional": [_trad(p, lang) for p in professional if p],
        "plain": {
            "summary": _trad(summary, lang),
            "points": [_trad(p, lang) for p in points if p],
            "detail": _trad(detail, lang),
        },
        "content": _trad("\n\n".join(professional), lang),
        "source": "local",
    }
    if extra:
        page.update(extra)
    return ReportGenerator.sanitize_page_for_display(page, page["title"])


def _strength_label(level: str, lang: str) -> str:
    if lang == "en":
        return {"strong": "strong", "weak": "weak", "balanced": "balanced"}.get(level, level)
    m = {"strong": "身强", "weak": "身弱", "balanced": "中和"}
    return _trad(m.get(level, level), lang)


def _favor_text(strength: dict, lang: str) -> str:
    favor = "、".join(sorted(strength.get("favor") or [])) or ("均衡" if lang != "en" else "balanced")
    avoid = "、".join(sorted(strength.get("avoid") or [])) or ("—" if lang != "en" else "—")
    if lang == "en":
        return f"Favor: {favor}; Caution: {avoid}"
    return _trad(f"喜用偏：{favor}；慎用偏：{avoid}", lang)


def _pillar_line(bazi_data: dict) -> str:
    bazi = bazi_data.get("bazi") or {}
    parts = []
    for k in ("年柱", "月柱", "日柱", "时柱"):
        p = bazi.get(k) or ["?", "?"]
        parts.append(f"{p[0]}{p[1]}")
    return " ".join(parts)


def _current_flow(bazi_data: dict) -> Dict[str, Any]:
    flow = bazi_data.get("flow") or {}
    da_yun = bazi_data.get("da_yun") or []
    liu_nian = bazi_data.get("liu_nian") or []
    cur_dy = next((d for d in da_yun if d.get("is_current")), da_yun[0] if da_yun else {})
    cur_ln = next((n for n in liu_nian if n.get("is_current")), liu_nian[-1] if liu_nian else {})
    return {
        "flow": flow,
        "da_yun": cur_dy or {},
        "liu_nian": cur_ln or {},
        "year": int((cur_ln or {}).get("year") or datetime.now().year),
    }


def _age(birth_info: dict) -> Optional[int]:
    s = str((birth_info or {}).get("birth_date") or "")[:10]
    try:
        b = date.fromisoformat(s)
    except Exception:
        return None
    today = date.today()
    return today.year - b.year - ((today.month, today.day) < (b.month, b.day))


def build_local_report(
    bazi_data: dict,
    birth_info: dict,
    *,
    include_liunian: bool = True,
    lang: str = "zh",
) -> Dict[str, Any]:
    """生成本地报告 dict（page1…page9，可选 page10）。"""
    lang = lang if lang in ("zh", "zh_hant", "en") else "zh"
    en = lang == "en"
    name = (birth_info or {}).get("name") or ("User" if en else "用户")
    dm = bazi_data.get("day_master") or ""
    dm_wx = WUXING_MAP.get(dm, "")
    strength = estimate_day_strength(bazi_data)
    pers = analyze_personality(bazi_data, lang)
    flow_info = _current_flow(bazi_data)
    age = _age(birth_info)
    pillars = _pillar_line(bazi_data)
    level = _strength_label(strength.get("level") or "balanced", lang)
    favor = _favor_text(strength, lang)
    wx_stats = bazi_data.get("wuxing_stats") or {}
    wx_line = "、".join(f"{k}{int(v or 0)}" for k, v in wx_stats.items()) if isinstance(wx_stats, dict) else ""

    dy = flow_info["da_yun"]
    ln = flow_info["liu_nian"]
    dy_s = f"{dy.get('gan', '')}{dy.get('zhi', '')}".strip() or "—"
    ln_s = f"{ln.get('gan', '')}{ln.get('zhi', '')}".strip() or "—"
    year = flow_info["year"]

    report: Dict[str, Any] = {}

    # page1
    if en:
        report["page1"] = _page(
            "BaZi Chart & Basics",
            [
                f"{name}'s chart: {pillars}. Day Master {dm} ({dm_wx}), overall {level}.",
                f"Five-element counts: {wx_line or 'n/a'}. {favor}.",
                f"Current decade luck {dy_s}; year pillar {ln_s} ({year}). Use this as the baseline for later chapters.",
                f"Personality snapshot: {pers.get('summary') or pers.get('body') or '—'}. Strengths: {pers.get('strength')}; watch: {pers.get('weakness')}.",
            ],
            summary=f"{name}: Day Master {dm}, {level}.",
            points=[
                "Read the chart first, then career/wealth/relationship/health.",
                "Favor elements are guides, not absolute commands.",
                "Annual Luck chapter focuses on this year and this month.",
            ],
            detail="This is a local rule-based report (no AI tokens). Use AI deep read later if you want richer prose.",
            lang=lang,
        )
    else:
        report["page1"] = _page(
            "八字命盘与基本信息",
            [
                f"{name} 四柱：{pillars}。日主{dm}（{dm_wx}），整体判断为{level}。",
                f"五行统计：{wx_line or '暂缺'}。{favor}。",
                f"当前大运 {dy_s}；流年 {ln_s}（{year}年）。后文事业/财运/感情/健康均以此为底盘。",
                f"性格要点：{pers.get('summary') or pers.get('body') or '—'}；优势偏「{pers.get('strength')}」，留意「{pers.get('weakness')}」。",
            ],
            summary=f"{name}：日主{dm}，{level}。",
            points=["先看命盘格局，再看分章详批。", "喜用是方向参考，不必极端补泻。", "流年篇重点看当年与当月。"],
            detail="本报告为本地规则版（不消耗 AI）。若需更细文笔，可再点「AI 深批」。",
            lang=lang,
        )

    # Domain chapters: career / wealth / relationship / health × part1+2
    domains = [
        (
            "page2",
            "page3",
            "事业详批 (Part 1)",
            "事业详批 (Part 2)",
            "Career (Part 1)",
            "Career (Part 2)",
            "career",
        ),
        (
            "page4",
            "page5",
            "财运详批 (Part 1)",
            "财运详批 (Part 2)",
            "Wealth (Part 1)",
            "Wealth (Part 2)",
            "wealth",
        ),
        (
            "page6",
            "page7",
            "感情详批 (Part 1)",
            "感情详批 (Part 2)",
            "Relationship (Part 1)",
            "Relationship (Part 2)",
            "relationship",
        ),
        (
            "page8",
            "page9",
            "健康详批 (Part 1)",
            "健康详批 (Part 2)",
            "Health (Part 1)",
            "Health (Part 2)",
            "health",
        ),
    ]

    tips_rows = build_lifetime_fortune(bazi_data, max_age=80, lang=lang)
    tip_now = next((r for r in tips_rows if r.get("year") == year), None)
    tip_text = (tip_now or {}).get("tip") or ""

    for p1, p2, zh1, zh2, en1, en2, domain in domains:
        report[p1] = _local_domain_part1(
            domain, zh1 if not en else en1, name, level, favor, dy_s, ln_s, year, tip_text, age, lang
        )
        report[p2] = _local_domain_part2(
            domain, zh2 if not en else en2, name, strength, favor, year, age, lang
        )

    if include_liunian:
        report["page10"] = _local_liunian_page(bazi_data, birth_info, tips_rows, year, lang)

    # mark meta
    report["_meta"] = {"source": "local", "generated_at": datetime.utcnow().isoformat() + "Z"}
    return report


def _local_domain_part1(
    domain: str,
    title: str,
    name: str,
    level: str,
    favor: str,
    dy_s: str,
    ln_s: str,
    year: int,
    tip_text: str,
    age: Optional[int],
    lang: str,
) -> Dict[str, Any]:
    en = lang == "en"
    age_s = f"{age}" if age is not None else ("n/a" if en else "未知")
    tip = tip_text or ("See the annual chapter for details." if en else "详见流年篇章。")

    if domain == "career":
        if en:
            pro = [
                f"{year}: career weather sits on decade {dy_s} and year {ln_s}; day-master tone is {level}.",
                "Near-term focus: delivery quality, role clarity, and avoiding overcommitment in clash months.",
                f"Age band ~{age_s}: prioritize skill compounding over title chasing when pressure rises.",
                f"Year note: {tip}",
            ]
            summary = f"{year} career: steady progress if boundaries stay clear."
            points = ["Clarify one main KPI this quarter.", "Avoid multi-thread fights in tense months.", "Document wins monthly."]
            detail = f"{favor}. Keep workload rhythmic; review role fit mid-year."
        else:
            pro = [
                f"{year}年事业盘：大运{dy_s}、流年{ln_s}叠合，日主整体{level}。",
                "近阶段宜看「节奏与边界」：项目落地、岗位职责是否清晰，冲克月少硬刚。",
                f"年龄约{age_s}岁：压力大时优先练可迁移能力，再谈头衔跳槽。",
                f"本年提示：{tip}",
            ]
            summary = f"{year}年事业：守节奏、清边界，稳步推进。"
            points = ["本季只盯一个主目标。", "紧张月份少开多线战场。", "每月记录一次成果。"]
            detail = f"{favor}。工作负荷宜有呼吸感，年中复盘岗位匹配度。"
    elif domain == "wealth":
        if en:
            pro = [
                f"{year} wealth tone follows {level} day-master dynamics under {dy_s}/{ln_s}.",
                "Cashflow first: separate living costs, buffers, and speculative money.",
                "High-volatility months: shrink position size; do not chase late signals.",
                f"Year note: {tip}",
            ]
            summary = f"{year} wealth: protect cashflow, then seek selective upside."
            points = ["Auto-save a fixed ratio.", "Cap speculative risk.", "Review big buys twice."]
            detail = f"{favor}. Prefer steady accumulation over all-in bets."
        else:
            pro = [
                f"{year}年财运：在大运{dy_s}与流年{ln_s}下，日主{level}，先看现金流稳定。",
                "建议分账：生活/备用/试错三笔，避免混用导致误判。",
                "波动月缩小仓位，不追尾盘消息。",
                f"本年提示：{tip}",
            ]
            summary = f"{year}年财运：先稳现金流，再谈增值。"
            points = ["固定比例自动储蓄。", "投机仓设上限。", "大额支出两次确认。"]
            detail = f"{favor}。偏稳健积累，少做孤注一掷。"
    elif domain == "relationship":
        if en:
            pro = [
                f"{year} relationship weather: {dy_s}/{ln_s} with a {level} day-master baseline.",
                "Watch communication load in busy months; small frictions amplify when tired.",
                "If single: quality of circles > quantity of events. If partnered: schedule repair talks.",
                f"Year note: {tip}",
            ]
            summary = f"{year} bonds: clearer words beat harder pushes."
            points = ["One weekly check-in.", "Pause arguments when exhausted.", "Keep social pace sustainable."]
            detail = f"{favor}. Warmth plus boundaries usually works better than extremes."
        else:
            pro = [
                f"{year}年感情：大运{dy_s}、流年{ln_s}，底盘{level}。",
                "忙碌月沟通成本上升，小摩擦容易放大，宜先休息再讨论。",
                "单身重圈子质量；有伴则固定「修复对话」时间。",
                f"本年提示：{tip}",
            ]
            summary = f"{year}年感情：把话说清，比用力推进更重要。"
            points = ["每周一次关系对表。", "疲惫时先暂停争执。", "社交节奏别过载。"]
            detail = f"{favor}。温度与边界并存，比极端付出更稳。"
    else:  # health
        if en:
            pro = [
                f"Health snapshot at age ~{age_s}: chart tone {level}; year pillars {dy_s}/{ln_s}.",
                "Treat BaZi organ metaphors as lifestyle alerts, not medical diagnosis.",
                "Midlife+: sleep, BP/metabolic checks, and recovery days matter more than intensity spikes.",
                f"Year note: {tip}",
            ]
            summary = f"Health focus: recovery rhythm over heroic overwork."
            points = ["Sleep window first.", "Walk after meals.", "Book routine screening if midlife+."]
            detail = f"{favor}. This chapter is for reflection only — see a clinician for symptoms."
        else:
            pro = [
                f"健康局势（约{age_s}岁）：命局{level}，大运{dy_s}/流年{ln_s}。",
                "五行脏腑对应只作生活提醒，不是医学诊断。",
                "中年后更重睡眠、血压/代谢筛查与恢复日，少靠硬撑高强度。",
                f"本年提示：{tip}",
            ]
            summary = "健康重点：恢复节奏优先于硬撑。"
            points = ["先稳住睡眠。", "饭后散步。", "中年后按龄体检。"]
            detail = f"{favor}。本章仅供参考；有症状请就医。"

    return _page(title, pro, summary=summary, points=points, detail=detail, lang=lang)


def _local_domain_part2(
    domain: str,
    title: str,
    name: str,
    strength: dict,
    favor: str,
    year: int,
    age: Optional[int],
    lang: str,
) -> Dict[str, Any]:
    en = lang == "en"
    fav = " / ".join(sorted(strength.get("favor") or [])) or ("balance" if en else "中和")

    if domain == "career":
        if en:
            pro = [
                f"Direction: pick roles that let {fav} strengths show (craft, coordination, or analysis).",
                "Remedy for bottlenecks: reduce parallel projects; negotiate scope before deadlines slip.",
                "Switch/promotion path: build a 90-day proof pack (metrics + samples + references).",
                "Weekly action: one deep-work block + one visibility update to stakeholders.",
            ]
            summary = "Career path: fewer threads, clearer proof, steady visibility."
            points = ["Cut one low-value task.", "Ship a visible deliverable.", "Ask for feedback monthly."]
            detail = f"{favor}. Direction beats hustle when energy is uneven."
        else:
            pro = [
                f"方向：选择更能发挥「{fav}」特质的岗位/赛道（专精、协调或分析）。",
                "瓶颈化解：减少并行项目，deadline 前先谈清范围。",
                "升迁/转职：准备 90 天成果包（数据+作品+评价）。",
                "每周行动：一次深度工作块 + 一次向关键人同步进展。",
            ]
            summary = "事业方向：少线、明证、稳曝光。"
            points = ["砍掉一件低价值事。", "交付一件看得见的成果。", "每月主动要一次反馈。"]
            detail = f"{favor}。能量不稳时，方向比蛮干更重要。"
    elif domain == "wealth":
        if en:
            pro = [
                f"Allocation tilt toward habits that match {fav} (steady cash + small experimental sleeve).",
                "Remedy loss risk: pre-commit max drawdown and cooling-off rules.",
                "Build: automate savings; review subscriptions quarterly.",
                "Action: one money meeting per month (even 20 minutes).",
            ]
            summary = "Wealth path: automate safety, then selective growth."
            points = ["Emergency fund first.", "Write a loss limit.", "Quarterly cost audit."]
            detail = f"{favor}. Process > prediction."
        else:
            pro = [
                f"配置方向：匹配「{fav}」——稳健现金底仓 + 小比例试错仓。",
                "破财化解：预设最大回撤与冷静期规则。",
                "积累：自动储蓄；每季清理订阅与闲置支出。",
                "行动：每月一次财务对表（20 分钟也够）。",
            ]
            summary = "财运方向：先自动安全垫，再谈选择性增值。"
            points = ["先备应急金。", "写下亏损上限。", "每季审计开支。"]
            detail = f"{favor}。流程比预测更重要。"
    elif domain == "relationship":
        if en:
            pro = [
                "Direction: invest in reciprocal bonds; prune draining one-way ties.",
                "Remedy conflict: state need + boundary in one short message, then pause.",
                "Environment: shared calm routines beat grand gestures under stress.",
                "Timing: hard talks after rest, not after overtime.",
            ]
            summary = "Relationship path: reciprocity, short clarity, timed talks."
            points = ["Name one need calmly.", "Keep one shared ritual.", "Protect rest before talks."]
            detail = f"{favor}. Warm consistency usually outperforms intensity spikes."
        else:
            pro = [
                "方向：投资对等关系，减少单向消耗。",
                "矛盾化解：短讯说清需要与边界，然后暂停降温。",
                "环境：压力期用共同的平静仪式，比大型浪漫更稳。",
                "时机：重要谈话放在休息后，不放在加班后。",
            ]
            summary = "感情方向：对等、短而清、选对时机。"
            points = ["平静说出一个需要。", "维持一个共同小仪式。", "谈话前先休息。"]
            detail = f"{favor}。稳定的温度，通常胜过短暂爆发。"
    else:
        if en:
            pro = [
                "Care direction: sleep regularity, hydration, and joint-friendly movement.",
                "If midlife+: prioritize BP/metabolic screening discussions with a clinician.",
                "Stress remedy: 10-minute breath/walk breaks after intense blocks.",
                "Checklist: sleep, steps, veggies, screening — pick one to improve this month.",
            ]
            summary = "Health path: boring basics done daily."
            points = ["Fixed sleep window.", "Daily walk.", "Schedule checkup if due."]
            detail = f"{favor}. Not a diagnosis — personal medical advice needs a professional."
        else:
            pro = [
                "调养方向：睡眠规律、补水、对关节友好的活动。",
                "中年后：与医生讨论血压/代谢筛查安排。",
                "压力化解：高强度后安排 10 分钟呼吸或散步。",
                "清单：睡眠、步数、蔬果、体检——本月只改进一项。",
            ]
            summary = "健康方向：把基础事项做成日常。"
            points = ["固定睡眠窗口。", "每天走路。", "到期就去体检。"]
            detail = f"{favor}。非诊断；具体医疗问题请咨询专业人士。"

    return _page(title, pro, summary=summary, points=points, detail=detail, lang=lang)


def _local_liunian_page(
    bazi_data: dict,
    birth_info: dict,
    tips_rows: List[dict],
    year: int,
    lang: str,
) -> Dict[str, Any]:
    en = lang == "en"
    title = "Annual Luck Report" if en else "流年报告"
    tip_now = next((r for r in tips_rows if r.get("year") == year), None)
    tip_text = (tip_now or {}).get("tip") or ("—" if en else "—")
    ln = f"{(tip_now or {}).get('liunian') or ''}".strip() or "—"
    score = (tip_now or {}).get("score")
    score_s = f"{int(score)}" if isinstance(score, (int, float)) else "—"

    # seasons from SEASON_SPECS
    seasons = ReportGenerator.SEASON_SPECS_EN if en else ReportGenerator.SEASON_SPECS
    quarters = []
    quarters_plain = []
    for i, (season, branches, months, mood) in enumerate(seasons):
        # pick tip rows roughly in season months via year tips nearby — use simple templates
        if en:
            how = f"In {season.lower()}, keep one priority and protect recovery."
            focus = months
            advice = f"Align actions with {mood}; avoid stacking conflicts."
            summary = f"{season}: steady pace, watch key months."
        else:
            how = f"{season}季宜守一个主线，并留恢复空间。"
            focus = months
            advice = f"行动配合「{mood}」，少叠冲突。"
            summary = f"{season}：稳节奏，盯关键月。"
        quarters.append(
            {
                "season": season,
                "branches": branches,
                "months": months,
                "theme": mood,
                "how": how,
                "focus_months": focus,
                "advice": advice,
            }
        )
        quarters_plain.append(
            {
                "season": season,
                "summary": summary,
                "how": how,
                "focus": focus,
                "advice": advice,
            }
        )

    month = datetime.now().month
    if en:
        cm = {
            "label": f"Current month focus ({year}-{month:02d})",
            "overview": f"Year pillar {ln}, local score ~{score_s}. Keep one main track.",
            "career": "Ship something visible; reduce meeting sprawl.",
            "wealth": "Track cashflow weekly; delay impulse buys.",
            "relationship": "Short honest updates beat long silent gaps.",
            "health": "Sleep and walks first; intensity second.",
            "action": "Pick one career + one health action this week.",
        }
        pro = [
            f"{year} annual overview: pillar {ln}. Local fortune score ~{score_s}.",
            f"Key note: {tip_text}",
            "Read seasons below for pacing; use current-month box for immediate actions.",
            "This chapter is rule-based (no AI). Upgrade AI deep read for richer narrative.",
        ]
        summary = f"{year}: pace the year; act monthly."
        points = ["One yearly theme.", "Monthly review.", "Protect sleep in peak months."]
        detail = "Scroll the four seasons, then follow this month's checklist."
    else:
        cm = {
            "label": f"当月注意（{year}-{month:02d}）",
            "overview": f"流年{ln}，本地运势分约{score_s}。本月只抓一条主线。",
            "career": "做出一件看得见的交付，减少无效会议。",
            "wealth": "每周看现金流，冲动消费先搁置。",
            "relationship": "短而诚实的同步，好过长时间沉默。",
            "health": "睡眠与走路优先，强度其次。",
            "action": "本周各定一件事业与健康小行动。",
        }
        pro = [
            f"{year}年总论：流年{ln}。本地运势分约{score_s}。",
            f"要点：{tip_text}",
            "下方四季看节奏；上方/当月框看立刻能做的事。",
            "本章为本地规则版（不耗 AI）。需要更细文笔可再点 AI 深批。",
        ]
        summary = f"{year}年：先定节奏，再按月行动。"
        points = ["全年一个主题。", "每月复盘一次。", "高峰月优先睡眠。"]
        detail = "先浏览四季，再按当月清单执行。"

    page = _page(
        title,
        pro,
        summary=summary,
        points=points,
        detail=detail,
        lang=lang,
        extra={"current_month": {k: _trad(str(v), lang) for k, v in cm.items()}},
    )
    page["quarters"] = [
        {k: _trad(str(v), lang) if isinstance(v, str) else v for k, v in q.items()}
        for q in quarters
    ]
    plain = page.get("plain") if isinstance(page.get("plain"), dict) else {}
    plain["quarters_plain"] = [
        {k: _trad(str(v), lang) if isinstance(v, str) else v for k, v in qp.items()}
        for qp in quarters_plain
    ]
    page["plain"] = plain
    return page
