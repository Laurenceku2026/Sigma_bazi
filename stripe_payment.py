"""
Stripe 支付 — 银卡 / 金卡 / 钻石（一次性付款）

支付成功后依赖 success_url 回跳 App，由 App 用 session_id 核验并升级会员。
（Streamlit 无法稳定接收 Stripe Webhook，故以回跳履约为准。）
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import stripe

PAID_TIERS = ("silver", "gold", "diamond")


def _strip_base(url: str) -> str:
    return (url or "").strip().split("?")[0].rstrip("/")


class StripeClient:
    """Stripe 结账客户端"""

    def __init__(
        self,
        secret_key: str,
        price_silver: str,
        price_gold: str,
        price_diamond: str,
        *,
        app_base_url: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ):
        stripe.api_key = secret_key
        self.prices = {
            "silver": price_silver,
            "gold": price_gold,
            "diamond": price_diamond,
        }
        base = _strip_base(
            app_base_url
            or success_url
            or os.getenv("APP_BASE_URL", "")
            or os.getenv("STRIPE_SUCCESS_URL", "")
        )
        # 旧默认 share.streamlit.io 无效，视为未配置
        if "share.streamlit.io" in base:
            base = ""
        self.app_base_url = base
        if base:
            self.success_url = (
                f"{base}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
            )
            self.cancel_url = f"{base}/?checkout=cancel"
        else:
            self.success_url = success_url or os.getenv("STRIPE_SUCCESS_URL", "")
            self.cancel_url = cancel_url or os.getenv(
                "STRIPE_CANCEL_URL", ""
            ) or self.success_url

    def create_checkout_session(self, user_id: str, email: str, tier: str = "silver"):
        price_id = self.prices.get(tier)
        if not price_id:
            raise ValueError(f"Unknown tier or missing Stripe price: {tier}")
        if not self.success_url or "{CHECKOUT_SESSION_ID}" not in self.success_url:
            raise ValueError(
                "未配置 APP_BASE_URL（支付成功后需跳回本 App）。"
                "请在 Streamlit Secrets 设置 APP_BASE_URL=https://你的应用.streamlit.app"
            )

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="payment",
            success_url=self.success_url,
            cancel_url=self.cancel_url or self.success_url,
            customer_email=email,
            client_reference_id=user_id,
            metadata={
                "user_id": user_id,
                "tier": tier,
                "app_id": "sigma_fate_v1",
            },
        )
        return session

    def retrieve_checkout_session(self, session_id: str):
        return stripe.checkout.Session.retrieve(session_id)

    def fulfill_checkout_session(self, session_id: str) -> Dict[str, Any]:
        """
        核验 Checkout Session 并返回应履约的 user_id / tier。
        不写库；由调用方 apply_membership_tier。
        """
        session = self.retrieve_checkout_session(session_id)
        payment_status = getattr(session, "payment_status", None) or session.get(
            "payment_status"
        )
        status = getattr(session, "status", None) or session.get("status")
        if payment_status not in ("paid", "no_payment_required") and status != "complete":
            return {
                "ok": False,
                "reason": f"payment_status={payment_status}, status={status}",
            }

        meta = getattr(session, "metadata", None) or session.get("metadata") or {}
        if hasattr(meta, "to_dict"):
            meta = meta.to_dict()
        user_id = (meta.get("user_id") or "").strip() or (
            getattr(session, "client_reference_id", None)
            or session.get("client_reference_id")
            or ""
        )
        tier = (meta.get("tier") or "").strip()
        if not user_id or tier not in PAID_TIERS:
            return {
                "ok": False,
                "reason": f"missing metadata user_id/tier ({user_id!r}, {tier!r})",
            }

        amount_total = getattr(session, "amount_total", None)
        if amount_total is None and isinstance(session, dict):
            amount_total = session.get("amount_total")

        return {
            "ok": True,
            "user_id": user_id,
            "tier": tier,
            "session_id": session_id,
            "amount_total": int(amount_total or 0),
            "customer_email": (
                getattr(session, "customer_email", None)
                or (session.get("customer_email") if isinstance(session, dict) else None)
            ),
        }

    def handle_webhook(self, payload, sig_header, webhook_secret):
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except ValueError:
            raise ValueError("Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise ValueError("Invalid signature")

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            return {
                "type": "payment_completed",
                "user_id": session["metadata"].get("user_id"),
                "tier": session["metadata"].get("tier"),
                "session_id": session["id"],
            }
        return {"type": "unknown"}
