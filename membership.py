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


def tier_outline(tier_id: str, lang: str = "zh") -> List[str]:
    if lang == "en":
        outlines = {
            "silver": [
                "Page 1: BaZi chart & basics",
                "Pages 2–3: Career annual forecast",
                "Pages 4–5: Wealth annual forecast",
                "Pages 6–7: Relationship annual forecast",
                "Page 8: Health annual forecast",
                "10 full reports included",
            ],
            "gold": [
                "All Silver benefits",
                "Dedicated annual luck chapter (predictions & advice)",
                "Month-by-month guidance for the current year",
                "10 full reports + annual luck reports",
            ],
            "diamond": [
                "All Gold benefits",
                "Unlimited reports for 12 months",
                "Priority annual luck updates",
                "Best value for frequent users",
            ],
        }
    else:
        outlines = {
            "silver": [
                "页一：八字命盘与基本信息",
                "页二～三：事业流年详批",
                "页四～五：财运流年详批",
                "页六～七：感情流年详批",
                "页八：健康流年详批",
                "含 10 次完整八页报告",
            ],
            "gold": [
                "银卡全部内容",
                "专属流年预测专章（吉凶趋势 + 行动建议）",
                "当年逐月流年要点与注意事项",
                "含 10 次八页报告 + 流年报告",
            ],
            "diamond": [
                "金卡全部内容",
                "一年内无限次生成报告",
                "流年预测随用随更",
                "适合高频使用者",
            ],
        }
    return outlines.get(tier_id, [])


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
