"""
Stripe 支付 — 银卡 / 金卡 / 钻石（一次性付款）
"""
from __future__ import annotations

import os
from typing import Optional

import stripe


class StripeClient:
    """Stripe 结账客户端"""

    def __init__(self, secret_key: str, price_silver: str, price_gold: str, price_diamond: str,
                 success_url: Optional[str] = None, cancel_url: Optional[str] = None):
        stripe.api_key = secret_key
        self.prices = {
            "silver": price_silver,
            "gold": price_gold,
            "diamond": price_diamond,
        }
        self.success_url = success_url or os.getenv(
            "STRIPE_SUCCESS_URL", "https://share.streamlit.io/?success=1"
        )
        self.cancel_url = cancel_url or os.getenv(
            "STRIPE_CANCEL_URL", "https://share.streamlit.io/?cancel=1"
        )

    def create_checkout_session(self, user_id: str, email: str, tier: str = "silver"):
        price_id = self.prices.get(tier)
        if not price_id:
            raise ValueError(f"Unknown tier or missing Stripe price: {tier}")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="payment",
            success_url=self.success_url,
            cancel_url=self.cancel_url,
            customer_email=email,
            metadata={"user_id": user_id, "tier": tier, "app_id": "sigma_fate_v1"},
        )
        return session

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
