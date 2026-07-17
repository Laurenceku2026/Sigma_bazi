"""会员方案与报告大纲。"""
from __future__ import annotations

from typing import Any, Dict, List

TIERS: Dict[str, Dict[str, Any]] = {
    "silver": {
        "id": "silver",
        "price_hkd": 10,
        "quota": 10,
        "unlimited": False,
        "includes_liunian": False,
        "stripe_env": "STRIPE_PRICE_SILVER",
    },
    "gold": {
        "id": "gold",
        "price_hkd": 100,
        "quota": 10,
        "unlimited": False,
        "includes_liunian": True,
        "stripe_env": "STRIPE_PRICE_GOLD",
    },
    "diamond": {
        "id": "diamond",
        "price_hkd": 999,
        "quota": -1,
        "unlimited": True,
        "includes_liunian": True,
        "stripe_env": "STRIPE_PRICE_DIAMOND",
        "valid_days": 365,
    },
}

PAID_TIERS = ("silver", "gold", "diamond")

# 免费用户：含水印预览次数上限（用尽后须升级会员）
FREE_PREVIEW_LIMIT = 5


def can_free_preview(trials_remaining: int) -> bool:
    return int(trials_remaining or 0) > 0


def tier_outline(tier_id: str, lang: str = "zh") -> List[str]:
    if lang == "en":
        outlines = {
            "silver": [
                "Page 1: BaZi chart & basics",
                "Pages 2–3: Career (Part1 situation / Part2 direction & remedy)",
                "Pages 4–5: Wealth (Part1 / Part2)",
                "Pages 6–7: Relationship (Part1 / Part2)",
                "Pages 8–9: Health (Part1 / Part2)",
                "10 full 9-page reports (no Annual Luck Report)",
            ],
            "gold": [
                "All Silver benefits (9-page report)",
                "Independent chapter: Annual Luck Report",
                "Four seasons + key months + action tips",
                "10 uses of 9-page report + Annual Luck Report",
            ],
            "diamond": [
                "All Gold benefits",
                "Unlimited reports for 12 months",
                "Annual Luck Report updated anytime",
                "BaZi Marriage Match (local score + optional AI deep read)",
                "Best value for frequent users",
            ],
        }
        return outlines.get(tier_id, [])

    outlines = {
        "silver": [
            "页一：八字命盘与基本信息",
            "页二～三：事业详批（Part1 局势 / Part2 方向与化解）",
            "页四～五：财运详批（Part1 / Part2）",
            "页六～七：感情详批（Part1 / Part2）",
            "页八～九：健康详批（Part1 / Part2）",
            "含 10 次完整九页报告（不含流年报告）",
        ],
        "gold": [
            "银卡全部内容（完整九页报告）",
            "独立篇章：《流年报告》",
            "四季预测 + 每季关键月 + 行动建议",
            "含 10 次九页报告 + 流年报告",
        ],
        "diamond": [
            "金卡全部内容",
            "一年内无限次生成报告",
            "流年报告随用随更",
            "专属《八字合婚》（本地契合度 + 可选 AI 深批）",
            "适合高频使用者",
        ],
    }
    lines = outlines.get(tier_id, [])
    if lang == "zh_hant":
        try:
            from zh_convert import to_traditional

            return [to_traditional(x) for x in lines]
        except Exception:
            pass
    return lines


def can_generate_report(tier: str, trials_remaining: int, expires_at: str | None = None) -> bool:
    if tier == "diamond":
        if expires_at:
            from datetime import datetime

            try:
                exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                return exp > datetime.now(exp.tzinfo) if exp.tzinfo else exp > datetime.utcnow()
            except Exception:
                return True
        return True
    if tier in PAID_TIERS:
        return trials_remaining > 0
    return False
