"""
六西格玛命理 - 八字 App
Sigma Fate - BaZi
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import date, datetime
from typing import Any, Dict, Optional

import streamlit as st
from dotenv import load_dotenv

from admin_page import render_admin_login, render_admin_page
from bazi_engine import BaziEngine
from auth_local import hash_password
from ui_texts import is_chinese, region_label, region_longitude, region_options, t
from membership import FREE_PREVIEW_LIMIT, PAID_TIERS, TIERS, can_free_preview, can_generate_report, tier_outline
from mobile_meta import app_icon_path, inject_mobile_app_meta
from report_generator import ReportGenerator
from stripe_payment import StripeClient
from supabase_client import AppAccessDenied, SupabaseClient
from hehun import analyze_hehun, render_hehun_html
from name_analysis import (
    analyze_name_with_bazi,
    format_name_theory_markdown,
    render_name_report_html,
)
from trial_survey import render_trial_survey
from utils import (
    format_bazi_display,
    generate_hehun_pdf_report,
    generate_pdf_report,
    hehun_pdf_filename,
    pdf_filename,
    render_bazi_chart,
)
from ziwei_engine import (
    build_ziwei_basic_reading,
    compute_ziwei_from_birth_info,
    format_ziwei_theory_markdown,
    generate_ziwei_pdf_report,
    render_ziwei_chart_html,
    render_ziwei_reading_html,
    ziwei_pdf_filename,
)

st.set_page_config(
    page_title="六西格玛命理 - 八字",
    page_icon=app_icon_path() or "🔮",
    layout="wide",
)

# --- Session ---
for key, default in [
    ("user_id", str(uuid.uuid4())),
    ("subscription_tier", "free"),
    ("report_generated", False),
    ("report_content", None),
    ("bazi_data", None),
    ("birth_info", None),
    ("app_user_synced", False),
    ("lang", "zh_hant"),
    ("admin_logged_in", False),
    ("show_admin", False),
    ("user_email", ""),
    ("show_register", False),
    ("show_login", False),
    ("auth_ok", False),
    ("access_token", ""),
    ("pending_form", None),
    ("selected_plan", None),
    ("show_join_membership", False),
    ("ui_tab", 0),
    ("hehun_result", None),
    ("hehun_bazi_a", None),
    ("hehun_bazi_b", None),
    ("hehun_names", None),
    ("hehun_ai", None),
    ("hehun_watermarked", False),
    ("report_source", ""),  # local | ai
    ("ziwei_chart", None),
    ("ziwei_reading", None),
    ("ziwei_ai", None),
    ("ziwei_ai_watermarked", False),
]:
    if key == "user_id":
        if "user_id" not in st.session_state:
            st.session_state.user_id = str(uuid.uuid4())
    elif key not in st.session_state:
        st.session_state[key] = default

load_dotenv()


def _cfg(name: str, default: str = "") -> str:
    val = os.getenv(name)
    if val:
        return val
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return default


SUPABASE_URL = _cfg("SUPABASE_STOCK_URL")
SUPABASE_SERVICE_KEY = _cfg("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_ANON_KEY = _cfg("SUPABASE_STOCK_ANON_KEY")
SUPABASE_KEY = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
APP_ID = _cfg("APP_ID", "sigma_fate_v1")
SUPABASE_APP_SCHEMA = _cfg("SUPABASE_APP_SCHEMA", "app_sigma_fate")
DEEPSEEK_API_KEY = _cfg("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = _cfg("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = _cfg("DEEPSEEK_MODEL", "deepseek-v4-flash")
STRIPE_SECRET_KEY = _cfg("STRIPE_SECRET_KEY")
STRIPE_PRICE_SILVER = _cfg("STRIPE_PRICE_SILVER")
STRIPE_PRICE_GOLD = _cfg("STRIPE_PRICE_GOLD")
STRIPE_PRICE_DIAMOND = _cfg("STRIPE_PRICE_DIAMOND")
APP_BASE_URL = _cfg("APP_BASE_URL") or _cfg("STRIPE_SUCCESS_URL") or "https://sigma-bazi.streamlit.app"
ADMIN_USERNAME = _cfg("ADMIN_USERNAME", "Laurence_ku")
ADMIN_PASSWORD = _cfg("ADMIN_PASSWORD", "Ku_product$2026")
PWA_MANIFEST_URL = _cfg(
    "PWA_MANIFEST_URL",
    "https://raw.githubusercontent.com/Laurenceku2026/Sigma_bazi/main/static/manifest.webmanifest",
)
# Gmail SMTP（忘记密码发信）：需在 Secrets 配置 SMTP_PASSWORD=应用专用密码
SMTP_HOST = _cfg("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(_cfg("SMTP_PORT", "587") or "587")
SMTP_USER = _cfg("SMTP_USER", "Techlife2027@gmail.com")
# Gmail 应用专用密码常显示为带空格的 4 组；SMTP 使用时去掉空格
SMTP_PASSWORD = _cfg("SMTP_PASSWORD").replace(" ", "").replace("\u00a0", "")
SMTP_FROM = _cfg("SMTP_FROM", SMTP_USER or "Techlife2027@gmail.com")
SMTP_USE_TLS = _cfg("SMTP_USE_TLS", "1") not in ("0", "false", "False", "")


def _resolve_app_base_url() -> str:
    """支付回跳用的 App 根地址。优先 Secrets，其次从请求 Host 推断。"""
    configured = (APP_BASE_URL or "").strip().split("?")[0].rstrip("/")
    if configured and "share.streamlit.io" not in configured:
        return configured
    try:
        headers = st.context.headers
        host = (headers.get("Host") or headers.get("host") or "").strip()
        if host and "share.streamlit.io" not in host:
            proto = (
                headers.get("X-Forwarded-Proto")
                or headers.get("x-forwarded-proto")
                or "https"
            )
            return f"{proto}://{host}".rstrip("/")
    except Exception:
        pass
    return configured if configured and "share.streamlit.io" not in configured else ""


lang = st.session_state.lang
inject_mobile_app_meta(manifest_url=PWA_MANIFEST_URL)


def _is_zh() -> bool:
    return is_chinese(lang)


supabase_client = stripe_client = report_gen = None
_init_errors: list[str] = []

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_client = SupabaseClient(
            SUPABASE_URL, SUPABASE_KEY,
            app_id=APP_ID, schema=SUPABASE_APP_SCHEMA,
            use_service_role=bool(SUPABASE_SERVICE_KEY),
        )
    except Exception as e:
        _init_errors.append(f"Supabase: {e}")

if STRIPE_SECRET_KEY:
    try:
        stripe_client = StripeClient(
            STRIPE_SECRET_KEY,
            STRIPE_PRICE_SILVER,
            STRIPE_PRICE_GOLD,
            STRIPE_PRICE_DIAMOND,
            app_base_url=_resolve_app_base_url(),
        )
    except Exception as e:
        _init_errors.append(f"Stripe: {e}")

if DEEPSEEK_API_KEY:
    try:
        report_gen = ReportGenerator(DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL)
    except Exception as e:
        _init_errors.append(f"DeepSeek: {e}")

if _init_errors:
    st.session_state["_init_errors"] = _init_errors


def _clear_checkout_query_params() -> None:
    try:
        for key in ("checkout", "session_id", "success", "cancel"):
            if key in st.query_params:
                del st.query_params[key]
    except Exception:
        try:
            st.query_params.clear()
        except Exception:
            pass


def handle_stripe_checkout_return() -> None:
    """支付完成回跳：核验 Stripe Session → 升级会员 → 清 URL 参数。"""
    try:
        checkout = st.query_params.get("checkout")
    except Exception:
        return
    if not checkout:
        # 兼容旧 success=1
        try:
            if st.query_params.get("success") in ("1", "true", "yes"):
                st.info(
                    "已从支付页返回。若会员未更新，请联系客服并附上支付凭证。"
                    if _is_zh()
                    else "Returned from payment. If membership did not update, contact support."
                )
                _clear_checkout_query_params()
        except Exception:
            pass
        return

    if checkout == "cancel":
        st.warning(
            "已取消支付，可随时重新选择方案。"
            if _is_zh()
            else "Payment cancelled. You can try again anytime."
        )
        st.session_state.show_join_membership = True
        _clear_checkout_query_params()
        return

    if checkout != "success":
        return

    session_id = (st.query_params.get("session_id") or "").strip()
    if not session_id:
        st.error(
            "支付回跳缺少 session_id，无法自动升级。请联系客服。"
            if _is_zh()
            else "Missing session_id on return — cannot auto-upgrade."
        )
        _clear_checkout_query_params()
        return

    if st.session_state.get("_stripe_fulfilled_session") == session_id:
        _clear_checkout_query_params()
        return

    if not stripe_client or not supabase_client:
        st.error(
            "支付系统未就绪，无法完成升级。请稍后刷新或联系客服。"
            if _is_zh()
            else "Payment system not ready — please refresh or contact support."
        )
        return

    try:
        result = stripe_client.fulfill_checkout_session(session_id)
    except Exception as e:
        st.error(
            (f"核验支付失败：{e}" if _is_zh() else f"Payment verification failed: {e}")
        )
        return

    if not result.get("ok"):
        st.error(
            f"支付未完成或无法核验（{result.get('reason', '')}）。"
            if _is_zh()
            else f"Payment not verified ({result.get('reason', '')})."
        )
        _clear_checkout_query_params()
        return

    user_id = result["user_id"]
    tier = result["tier"]
    try:
        ok = supabase_client.apply_membership_tier(user_id, tier)
    except Exception as e:
        st.error(
            (f"升级会员失败：{e}" if _is_zh() else f"Failed to apply membership: {e}")
        )
        return

    if not ok:
        st.error(
            "支付已确认，但写入会员失败。请联系客服并附上支付单号。"
            if _is_zh()
            else "Payment OK but membership update failed. Contact support."
        )
        return

    try:
        supabase_client.save_payment(
            user_id,
            payment_id=f"pay_{session_id[-18:]}",
            stripe_session_id=session_id,
            amount=int(result.get("amount_total") or 0),
            tier=tier,
            status="paid",
        )
    except Exception:
        pass

    st.session_state["_stripe_fulfilled_session"] = session_id
    pay_email = (result.get("customer_email") or "").strip().lower()
    cur_email = (st.session_state.get("user_email") or "").strip().lower()
    same_user = st.session_state.get("user_id") == user_id or (
        bool(pay_email) and bool(cur_email) and pay_email == cur_email
    )
    if same_user:
        st.session_state.subscription_tier = tier
        st.session_state.show_join_membership = False
        st.session_state.selected_plan = None

    try:
        if st.session_state.get("auth_ok") and st.session_state.get("user_id"):
            profile = supabase_client.get_user(st.session_state.user_id)
            if profile and profile.get("subscription_tier") in PAID_TIERS:
                st.session_state.subscription_tier = profile["subscription_tier"]
            elif same_user:
                st.session_state.subscription_tier = tier
    except Exception:
        if same_user:
            st.session_state.subscription_tier = tier

    tier_name = {
        "silver": "银卡" if _is_zh() else "Silver",
        "gold": "金卡" if _is_zh() else "Gold",
        "diamond": "钻石" if _is_zh() else "Diamond",
    }.get(tier, tier)
    st.success(
        f"支付成功！已升级为{tier_name}会员。"
        if _is_zh()
        else f"Payment successful! Upgraded to {tier_name}."
    )
    if not st.session_state.get("auth_ok"):
        st.info(
            "请登录支付时使用的账号，即可看到会员权益。"
            if _is_zh()
            else "Please sign in with the account used for payment."
        )
        st.session_state.show_login = True
    st.balloons()
    _clear_checkout_query_params()


def refresh_membership_tier_from_db() -> None:
    """已登录时从数据库刷新会员档（支付回跳后原标签页也能同步）。"""
    if not supabase_client or not st.session_state.get("auth_ok"):
        return
    uid = st.session_state.get("user_id")
    if not uid:
        return
    try:
        profile = supabase_client.get_user(uid)
        if not profile:
            return
        db_tier = profile.get("subscription_tier")
        if db_tier in ("free", "silver", "gold", "diamond", "monthly", "quarterly", "annual"):
            st.session_state.subscription_tier = db_tier
    except Exception:
        pass


handle_stripe_checkout_return()
refresh_membership_tier_from_db()


def valid_email(email: str) -> bool:
    return bool(email and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def is_registered() -> bool:
    """须完成邮箱+密码登录（auth_ok）。"""
    if st.session_state.get("auth_ok") and valid_email(st.session_state.get("user_email", "")):
        return True
    return False


def _parse_birth_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    s = str(value)[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def birth_info_from_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """从用户表 / last_birth_info 拼出可恢复的 birth_info。"""
    raw = profile.get("last_birth_info") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}
    if not isinstance(raw, dict):
        raw = {}
    info = dict(raw)
    if profile.get("display_name") and not info.get("name"):
        info["name"] = profile["display_name"]
    if profile.get("gender") and not info.get("gender"):
        info["gender"] = profile["gender"]
    if profile.get("birth_date") and not info.get("birth_date"):
        info["birth_date"] = str(profile["birth_date"])[:10]
    if profile.get("birth_hour") is not None and info.get("birth_hour") is None:
        info["birth_hour"] = profile["birth_hour"]
    if profile.get("birth_minute") is not None and info.get("birth_minute") is None:
        info["birth_minute"] = profile["birth_minute"]
    if profile.get("region_id") and not info.get("region_id"):
        info["region_id"] = profile["region_id"]
    if profile.get("birth_place") is not None and info.get("birth_place") is None:
        info["birth_place"] = profile["birth_place"]
    if profile.get("email"):
        info["email"] = profile["email"]
    return info


def prefills_form_from_birth_info(info: Dict[str, Any]) -> None:
    """写入输入框 widget session keys（下次 rerun 生效）。"""
    if not info:
        return
    if info.get("name"):
        st.session_state.input_name = info["name"]
    g = info.get("gender") or ""
    if g in ("男", "male", "Male"):
        st.session_state.input_gender = t("male", lang)
    elif g in ("女", "female", "Female"):
        st.session_state.input_gender = t("female", lang)
    bd = _parse_birth_date(info.get("birth_date"))
    if bd:
        st.session_state.input_birth_date = bd
    if info.get("birth_hour") is not None:
        try:
            st.session_state.input_hour = int(info["birth_hour"])
        except (TypeError, ValueError):
            pass
    if info.get("birth_minute") is not None:
        try:
            st.session_state.input_minute = int(info["birth_minute"])
        except (TypeError, ValueError):
            pass
    rid = info.get("region_id")
    if rid:
        _, reg_ids, _ = region_options(lang)
        if rid in reg_ids:
            st.session_state.input_region = reg_ids.index(rid)
    if info.get("birth_place") is not None:
        st.session_state.input_place = info.get("birth_place") or ""


def restore_session_from_profile(profile: Dict[str, Any]) -> None:
    """登录成功后：对齐 user_id/会员档，恢复资料、命盘、报告。"""
    if profile.get("user_id"):
        st.session_state.user_id = profile["user_id"]
    if profile.get("email"):
        st.session_state.user_email = profile["email"]
    db_tier = profile.get("subscription_tier")
    if db_tier in ("free", "silver", "gold", "diamond", "monthly", "quarterly", "annual"):
        st.session_state.subscription_tier = db_tier

    info = birth_info_from_profile(profile)
    st.session_state.birth_info = info if info else None
    prefills_form_from_birth_info(info)

    reports = []
    if supabase_client and profile.get("user_id"):
        try:
            reports = supabase_client.get_reports(profile["user_id"], limit=5) or []
        except Exception:
            reports = []

    restored_bazi = None
    restored_report = None
    if reports:
        latest = reports[0]
        restored_bazi = latest.get("bazi_data")
        restored_report = latest.get("report_content")
        if not info and latest.get("birth_info"):
            info = latest["birth_info"] if isinstance(latest["birth_info"], dict) else {}
            st.session_state.birth_info = info
            prefills_form_from_birth_info(info)

    if restored_bazi:
        st.session_state.bazi_data = restored_bazi
    elif info and info.get("birth_date") and info.get("name"):
        try:
            bd = _parse_birth_date(info.get("birth_date"))
            if bd:
                form = {
                    "name": info.get("name", ""),
                    "gender": info.get("gender") or "男",
                    "birth_date": bd,
                    "birth_hour": int(info.get("birth_hour") or 12),
                    "birth_minute": int(info.get("birth_minute") or 0),
                    "region_id": info.get("region_id") or "huabei",
                    "use_true_solar": True,
                    "birth_place": info.get("birth_place") or "",
                }
                run_bazi(form)
        except Exception:
            pass

    if restored_report:
        restored_report = _maybe_report_dict(restored_report) or restored_report
        st.session_state.report_content = restored_report
        st.session_state.report_generated = True
        src = _report_source_of(restored_report)
        if src:
            st.session_state.report_source = src
        elif not st.session_state.get("report_source"):
            st.session_state.report_source = "local"

    st.session_state.app_user_synced = True
    st.session_state.show_login = False
    st.session_state.show_register = False
    # 保留密码登录态
    if st.session_state.get("access_token") or st.session_state.get("auth_ok"):
        st.session_state.auth_ok = True


def logout_user() -> None:
    st.session_state.user_id = str(uuid.uuid4())
    st.session_state.user_email = ""
    st.session_state.subscription_tier = "free"
    st.session_state.bazi_data = None
    st.session_state.birth_info = None
    st.session_state.report_content = None
    st.session_state.report_generated = False
    st.session_state.report_source = ""
    st.session_state.app_user_synced = False
    st.session_state.auth_ok = False
    st.session_state.access_token = ""
    st.session_state.show_login = False
    st.session_state.show_register = False
    st.session_state.pending_form = None
    for k in (
        "input_name", "input_gender", "input_birth_date", "input_hour",
        "input_minute", "input_region", "input_place", "input_solar",
    ):
        if k in st.session_state:
            del st.session_state[k]


def do_login(email: str, password: str) -> bool:
    """本 App 独立登录（只查 sf_users，与其他 App 无关）。"""
    if not supabase_client:
        st.error("数据库未连接，无法登录。请检查 Secrets。")
        return False
    if not valid_email(email):
        st.error(t("need_register", lang))
        return False
    if not password or len(password) < 6:
        st.error("请输入至少 6 位密码" if _is_zh() else "Password must be at least 6 characters")
        return False

    profile = supabase_client.login_with_password(email.strip(), password)
    if not profile:
        err = supabase_client.last_error or ""
        if err == "account_not_found":
            st.error(t("login_not_found", lang))
        elif err == "need_register_password":
            st.warning(t("need_set_local_password", lang))
            st.session_state.show_register = True
            st.session_state.show_login = False
        else:
            st.error(t("login_bad_password", lang))
        return False

    st.session_state.access_token = ""
    st.session_state.user_id = profile["user_id"]
    st.session_state.user_email = (profile.get("email") or email).strip().lower()
    st.session_state.auth_ok = True
    restore_session_from_profile(profile)
    st.session_state.auth_ok = True
    st.success(t("login_ok", lang))
    return True


def do_register(email: str, password: str, password2: str) -> bool:
    """本 App 独立注册：全新账号，不与其他 App 共用登录。"""
    if not supabase_client:
        st.error("数据库未连接。")
        return False
    if not valid_email(email):
        st.error(t("need_register", lang))
        return False
    if not password or len(password) < 6:
        st.error("密码至少 6 位" if _is_zh() else "Password min 6 chars")
        return False
    if password != password2:
        st.error("两次密码不一致" if _is_zh() else "Passwords do not match")
        return False

    try:
        profile = supabase_client.register_with_password(
            email.strip().lower(),
            hash_password(password),
            subscription_tier="free",
            metadata={"app": APP_ID},
        )
    except ValueError as e:
        if str(e) == "exists":
            st.warning(t("register_exists_local", lang))
            st.session_state.show_login = True
            st.session_state.show_register = False
            return False
        st.error(str(e))
        return False
    except Exception as e:
        msg = str(e)
        if "password_hash" in msg.lower() or "42703" in msg:
            st.error(
                "数据库缺少 password_hash 列，请在 Supabase 执行 sql/007_sf_users_local_password.sql"
                if _is_zh()
                else "Missing password_hash column — run sql/007_sf_users_local_password.sql"
            )
        else:
            st.error(f"{t('register_fail', lang)}{e}")
        return False

    if not profile:
        st.error(t("register_fail", lang))
        return False

    st.session_state.access_token = ""
    st.session_state.user_id = profile["user_id"]
    st.session_state.user_email = (profile.get("email") or email).strip().lower()
    st.session_state.auth_ok = True
    restore_session_from_profile(profile)
    st.session_state.auth_ok = True
    st.success(t("register_ok", lang))
    return True


def render_login_panel(key_prefix: str = "main") -> None:
    st.markdown(f"### {t('login_heading', lang)}")
    st.caption(t("login_caption", lang))
    # 必须用 form：普通 button 提交时浏览器常清空 password 控件，导致误判「密码至少 6 位」
    with st.form(f"{key_prefix}_login_form", clear_on_submit=False):
        email = st.text_input(
            t("email", lang),
            placeholder=t("email_ph", lang),
            key=f"{key_prefix}_login_email",
        )
        password = st.text_input(
            t("password", lang),
            type="password",
            key=f"{key_prefix}_login_password",
        )
        submitted = st.form_submit_button(
            t("login_submit", lang), type="primary", use_container_width=True
        )
        if submitted:
            if do_login(email or "", password or ""):
                st.rerun()
    c2, c3 = st.columns(2)
    with c2:
        if st.button(t("register_btn_short", lang), use_container_width=True, key=f"{key_prefix}_login_to_reg"):
            st.session_state.show_register = True
            st.session_state.show_login = False
            st.rerun()
    with c3:
        if st.button("取消" if _is_zh() else "Cancel", use_container_width=True, key=f"{key_prefix}_login_cancel"):
            st.session_state.show_login = False
            st.rerun()

    with st.expander(t("forgot_password", lang), expanded=False):
        smtp_ok = bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)
        st.caption(
            t("forgot_password_hint_email", lang)
            if smtp_ok
            else t("forgot_password_hint", lang)
        )
        with st.form(f"{key_prefix}_forgot_form", clear_on_submit=False):
            forgot_email = st.text_input(
                t("forgot_password_email", lang),
                value=st.session_state.get(f"{key_prefix}_login_email") or "",
                key=f"{key_prefix}_forgot_email",
            )
            forgot_confirm = st.checkbox(
                t("forgot_password_confirm", lang),
                key=f"{key_prefix}_forgot_confirm",
            )
            forgot_go = st.form_submit_button(
                t("forgot_password_submit_email", lang)
                if smtp_ok
                else t("forgot_password_submit", lang),
                type="primary",
                use_container_width=True,
            )
        if forgot_go:
            em = (forgot_email or "").strip().lower()
            if not em or "@" not in em:
                st.warning(t("forgot_password_need_email", lang))
            elif not forgot_confirm:
                st.warning(t("forgot_password_need_confirm", lang))
            elif not supabase_client:
                st.error(t("forgot_password_fail", lang))
            elif smtp_ok:
                _handle_forgot_password_email(em)
            else:
                try:
                    ok = supabase_client.clear_password_for_reregister(em)
                except Exception:
                    ok = False
                if ok:
                    st.success(t("forgot_password_ok", lang))
                    st.session_state[f"{key_prefix}_reg_email"] = em
                    st.session_state.show_register = True
                    st.session_state.show_login = False
                    st.rerun()
                else:
                    st.error(t("forgot_password_fail", lang))


def _handle_forgot_password_email(email: str) -> None:
    """发重置邮件（Gmail SMTP）。无论账号是否存在都显示统一成功文案。"""
    from urllib.parse import quote

    from email_smtp import build_password_reset_email, send_email

    token = supabase_client.create_password_reset_token(email)
    if token == "":
        st.warning(t("forgot_password_cooldown", lang))
        return
    # 未知邮箱：不发信，仍提示已发送，避免枚举账号
    if token:
        base = (_resolve_app_base_url() or APP_BASE_URL or "").rstrip("/")
        if not base:
            st.error(t("forgot_password_no_base_url", lang))
            return
        reset_url = (
            f"{base}/?pwd_reset=1&email={quote(email, safe='')}&token={quote(token, safe='')}"
        )
        app_name = "六西格玛命理 · 八字" if _is_zh() else "Sigma Fate BaZi"
        subject, text_body, html_body = build_password_reset_email(
            reset_url=reset_url, lang=lang, app_name=app_name
        )
        if lang == "zh_hant":
            try:
                from zh_convert import to_traditional

                subject = to_traditional(subject)
                text_body = to_traditional(text_body)
                html_body = to_traditional(html_body)
            except Exception:
                pass
        ok, err = send_email(
            host=SMTP_HOST,
            port=SMTP_PORT,
            user=SMTP_USER,
            password=SMTP_PASSWORD,
            mail_from=SMTP_FROM,
            to_addr=email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            use_tls=SMTP_USE_TLS,
        )
        if not ok:
            st.error(f"{t('forgot_password_fail', lang)} ({err})")
            return
    st.success(t("forgot_password_email_sent", lang))


def render_password_reset_panel() -> bool:
    """
    处理邮件重置链接 ?pwd_reset=1&email=&token=
    返回 True 表示已展示重置面板（调用方应 st.stop()）。
    """
    try:
        qp = st.query_params
        flag = qp.get("pwd_reset")
        email = (qp.get("email") or "").strip().lower()
        token = (qp.get("token") or "").strip()
    except Exception:
        return False
    if flag not in ("1", "true", "yes") or not email or not token:
        return False

    st.markdown(f"### {t('reset_password_heading', lang)}")
    st.caption(t("reset_password_caption", lang).format(email=email))
    with st.form("pwd_reset_form", clear_on_submit=False):
        p1 = st.text_input(t("password", lang), type="password", key="pwd_reset_p1")
        p2 = st.text_input(t("password_confirm", lang), type="password", key="pwd_reset_p2")
        go = st.form_submit_button(
            t("reset_password_submit", lang), type="primary", use_container_width=True
        )
    if go:
        if not p1 or len(p1) < 6:
            st.warning(t("password_too_short", lang))
        elif p1 != p2:
            st.warning(t("password_mismatch", lang))
        elif not supabase_client:
            st.error(t("forgot_password_fail", lang))
        else:
            ok = supabase_client.reset_password_with_token(email, token, p1)
            if ok:
                st.success(t("reset_password_ok", lang))
                st.info(t("reset_password_ok_hint", lang))
                try:
                    for k in ("pwd_reset", "email", "token"):
                        if k in st.query_params:
                            del st.query_params[k]
                except Exception:
                    pass
                st.session_state.show_login = True
                st.session_state.show_register = False
            else:
                err = getattr(supabase_client, "last_error", "") or ""
                if err == "token_expired":
                    st.error(t("reset_password_expired", lang))
                else:
                    st.error(t("reset_password_fail", lang))
    if st.button(t("login_btn", lang), key="pwd_reset_to_login"):
        try:
            for k in ("pwd_reset", "email", "token"):
                if k in st.query_params:
                    del st.query_params[k]
        except Exception:
            pass
        st.session_state.show_login = True
        st.rerun()
    return True


def render_register_panel(key_prefix: str = "main", after_ok=None) -> None:
    st.markdown(f"### {t('register_heading', lang)}")
    st.caption(t("register_caption", lang))
    with st.form(f"{key_prefix}_reg_form", clear_on_submit=False):
        email = st.text_input(t("email", lang), key=f"{key_prefix}_reg_email")
        password = st.text_input(t("password", lang), type="password", key=f"{key_prefix}_reg_password")
        password2 = st.text_input(t("password_confirm", lang), type="password", key=f"{key_prefix}_reg_password2")
        submitted = st.form_submit_button(
            t("register_submit", lang), type="primary", use_container_width=True
        )
        if submitted:
            if do_register(email or "", password or "", password2 or ""):
                if callable(after_ok):
                    after_ok()
                st.rerun()
    if st.button(t("login_btn", lang), use_container_width=True, key=f"{key_prefix}_reg_to_login"):
        st.session_state.show_login = True
        st.session_state.show_register = False
        st.rerun()


def sync_app_user(email: Optional[str] = None):
    if not supabase_client:
        st.warning("数据库未连接，用户不会出现在管理员列表。请检查 Secrets。")
        return None
    if not st.session_state.get("auth_ok"):
        return None
    try:
        use_email = (email or st.session_state.user_email or "").strip()
        if use_email:
            profile = supabase_client.register_by_email(
                use_email,
                st.session_state.user_id,
                subscription_tier=st.session_state.subscription_tier or "free",
                metadata={"source": "streamlit", "app": APP_ID},
            )
        else:
            profile = supabase_client.ensure_app_user(
                user_id=st.session_state.user_id,
                email=None,
                subscription_tier=st.session_state.subscription_tier,
                metadata={"source": "streamlit", "app": APP_ID},
            )
        if profile.get("user_id"):
            st.session_state.user_id = profile["user_id"]
        if profile.get("email"):
            st.session_state.user_email = profile["email"]
        db_tier = profile.get("subscription_tier")
        if db_tier in ("free", "silver", "gold", "diamond", "monthly", "quarterly", "annual"):
            st.session_state.subscription_tier = db_tier
        st.session_state.app_user_synced = True
        return profile
    except Exception as e:
        detail = getattr(supabase_client, "last_error", None) or str(e)
        st.error(f"用户同步失败（管理员将看不到此人）：{detail}")
        return None


def _norm_birth_date_str(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        try:
            return str(value.isoformat())[:10]
        except Exception:
            pass
    return str(value)[:10]


def _form_birth_fingerprint(form: Dict[str, Any]) -> tuple:
    """排盘关键字段指纹（不含姓名，姓名不影响四柱）。"""
    return (
        str(form.get("gender") or ""),
        _norm_birth_date_str(form.get("birth_date")),
        int(form.get("birth_hour") or 0),
        int(form.get("birth_minute") or 0),
        str(form.get("region_id") or ""),
        bool(form.get("use_true_solar", True)),
    )


def _saved_birth_fingerprint(info: Dict[str, Any] | None) -> tuple | None:
    if not info or not info.get("birth_date"):
        return None
    return (
        str(info.get("gender") or ""),
        _norm_birth_date_str(info.get("birth_date")),
        int(info.get("birth_hour") or 0),
        int(info.get("birth_minute") or 0),
        str(info.get("region_id") or ""),
        bool(info.get("use_true_solar", True)),
    )


def birth_data_unchanged(form: Dict[str, Any], info: Dict[str, Any] | None) -> bool:
    saved = _saved_birth_fingerprint(info)
    if saved is None:
        return False
    return _form_birth_fingerprint(form) == saved


def _input_form_from_session() -> Optional[Dict[str, Any]]:
    """从输入页控件状态拼出当前出生资料；控件尚未创建时返回 None。"""
    if "input_birth_date" not in st.session_state:
        return None
    gender_ui = st.session_state.get("input_gender")
    gender = "男" if gender_ui in (t("male", lang), "男") else "女"
    _, reg_ids, _ = region_options(lang)
    try:
        reg_idx = int(st.session_state.get("input_region") or 0)
    except (TypeError, ValueError):
        reg_idx = 0
    if not reg_ids:
        region_id = str(st.session_state.birth_info.get("region_id") or "huabei") if st.session_state.get("birth_info") else "huabei"
    else:
        if reg_idx < 0 or reg_idx >= len(reg_ids):
            reg_idx = 0
        region_id = reg_ids[reg_idx]
    return {
        "gender": gender,
        "birth_date": st.session_state.get("input_birth_date"),
        "birth_hour": st.session_state.get("input_hour"),
        "birth_minute": st.session_state.get("input_minute"),
        "region_id": region_id,
        "use_true_solar": bool(st.session_state.get("input_solar", True)),
    }


def _maybe_report_dict(value: Any) -> Optional[Dict[str, Any]]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


def _report_source_of(report: Any) -> str:
    data = _maybe_report_dict(report)
    if not data:
        return ""
    meta = data.get("_meta")
    if isinstance(meta, dict):
        return str(meta.get("source") or "").strip().lower()
    return ""


def _report_is_ai(report: Any) -> bool:
    return _report_source_of(report) == "ai"


def _stamp_report_source(report: Dict[str, Any], source: str) -> Dict[str, Any]:
    out = dict(report or {})
    meta = dict(out.get("_meta") or {}) if isinstance(out.get("_meta"), dict) else {}
    meta["source"] = source
    meta.setdefault("generated_at", datetime.utcnow().isoformat() + "Z")
    out["_meta"] = meta
    return out


def _birth_inputs_match_saved_chart() -> bool:
    """输入页出生资料相对当前已排盘 birth_info 是否未变。"""
    birth = st.session_state.get("birth_info")
    if not _saved_birth_fingerprint(birth):
        return False
    form = _input_form_from_session()
    if form is None:
        return True
    return birth_data_unchanged(form, birth)


def _peek_reusable_ai_report() -> Optional[Dict[str, Any]]:
    """出生信息未变时，返回可复用的 AI 深批（含 report_content，可选 bazi_data）。"""
    if not _birth_inputs_match_saved_chart():
        return None
    birth = st.session_state.get("birth_info")
    fp = _saved_birth_fingerprint(birth)
    if fp is None:
        return None

    session_report = _maybe_report_dict(st.session_state.get("report_content"))
    if session_report and (
        st.session_state.get("report_source") == "ai" or _report_is_ai(session_report)
    ):
        return {"report_content": session_report, "bazi_data": st.session_state.get("bazi_data")}

    uid = st.session_state.get("user_id")
    if not (supabase_client and st.session_state.get("auth_ok") and uid):
        return None
    try:
        reports = supabase_client.get_reports(uid, limit=10) or []
    except Exception:
        return None

    for row in reports:
        content = _maybe_report_dict(row.get("report_content"))
        if not content or not _report_is_ai(content):
            continue
        row_bi = row.get("birth_info") if isinstance(row.get("birth_info"), dict) else None
        if not row_bi or _saved_birth_fingerprint(row_bi) != fp:
            continue
        bazi = _maybe_report_dict(row.get("bazi_data")) or row.get("bazi_data")
        return {"report_content": content, "bazi_data": bazi if isinstance(bazi, dict) else None}
    return None


def try_reuse_ai_deep_report() -> bool:
    """若出生未变且已有 AI 深批，载入 session 并返回 True（不调用 DeepSeek）。"""
    found = _peek_reusable_ai_report()
    if not found:
        return False
    content = found.get("report_content")
    if not isinstance(content, dict) or not content:
        return False
    st.session_state.report_content = content
    st.session_state.report_language = lang
    st.session_state.report_generated = True
    st.session_state.report_source = "ai"
    bazi = found.get("bazi_data")
    if isinstance(bazi, dict) and bazi:
        st.session_state.bazi_data = bazi
    return True


def compute_bazi_from_form(form: Dict[str, Any]) -> dict:
    """按表单排盘，不写入 session（合婚乙方/甲方手动填写用）。"""
    bd = form["birth_date"]
    if isinstance(bd, str):
        bd = date.fromisoformat(bd[:10])
    lon = region_longitude(form["region_id"])
    engine = BaziEngine(
        year=bd.year,
        month=bd.month,
        day=bd.day,
        hour=int(form["birth_hour"]),
        minute=int(form.get("birth_minute") or 0),
        gender=form["gender"],
        true_solar_time=bool(form.get("use_true_solar", True)),
        longitude=lon,
    )
    return engine.calculate().get_summary()


def run_bazi(form: Dict[str, Any]):
    bazi_data = compute_bazi_from_form(form)
    st.session_state.bazi_data = bazi_data
    st.session_state.birth_info = {
        "name": form["name"],
        "gender": form["gender"],
        "birth_date": form["birth_date"].isoformat(),
        "birth_hour": int(form["birth_hour"]),
        "birth_minute": int(form["birth_minute"]),
        "region_id": form["region_id"],
        "region_label": region_label(form["region_id"], lang),
        "birth_place": form.get("birth_place", ""),
        "use_true_solar": bool(form.get("use_true_solar", True)),
        "email": st.session_state.user_email,
        "payment_tier": st.session_state.subscription_tier,
    }
    if supabase_client:
        sync_app_user()
        try:
            supabase_client.save_user_profile(
                st.session_state.user_id,
                st.session_state.birth_info,
            )
        except Exception:
            pass
        try:
            supabase_client.log_action(st.session_state.user_id, "generate_bazi", {})
        except Exception:
            pass


def render_membership_plans(key_prefix: str = "main"):
    st.markdown("---")
    st.markdown(f"### {t('membership_heading', lang)}")
    c1, c2, c3 = st.columns(3)
    plans = [("silver", "btn_silver"), ("gold", "btn_gold"), ("diamond", "btn_diamond")]
    for col, (plan_id, label_key) in zip((c1, c2, c3), plans):
        with col:
            if st.button(
                t(label_key, lang),
                key=f"{key_prefix}_plan_{plan_id}",
                use_container_width=True,
            ):
                st.session_state.selected_plan = plan_id
                st.rerun()

    plan = st.session_state.get("selected_plan")
    if plan and plan in TIERS:
        with st.expander(t("outline_title", lang), expanded=True):
            for line in tier_outline(plan, lang):
                st.markdown(f"- {line}")
        email = st.session_state.user_email or f"user_{st.session_state.user_id[:8]}@example.com"
        if stripe_client:
            try:
                # 每次支付前刷新回跳地址（Secrets 或当前 Host）
                base = _resolve_app_base_url()
                if base:
                    stripe_client.app_base_url = base
                    stripe_client.success_url = (
                        f"{base}/?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
                    )
                    stripe_client.cancel_url = f"{base}/?checkout=cancel"
                session = stripe_client.create_checkout_session(
                    st.session_state.user_id, email, plan
                )
                from html import escape as _html_esc

                pay_url = _html_esc(session.url, quote=True)
                pay_label = _html_esc(t("pay_now", lang))
                st.markdown(
                    f"""
<style>
a.sf-pay-btn, a.sf-pay-btn:link, a.sf-pay-btn:visited, a.sf-pay-btn:hover,
a.sf-pay-btn:active, a.sf-pay-btn span {{
  color: #ffffff !important;
  text-decoration: none !important;
  -webkit-text-fill-color: #ffffff !important;
}}
a.sf-pay-btn {{
  display: block !important;
  width: 100% !important;
  box-sizing: border-box !important;
  text-align: center !important;
  background: #C62828 !important;
  font-weight: 800 !important;
  font-size: 1.15rem !important;
  padding: 0.85rem 1rem !important;
  border-radius: 10px !important;
  letter-spacing: 0.03em !important;
  box-shadow: 0 2px 8px rgba(198,40,40,0.35) !important;
  border: none !important;
}}
</style>
<a class="sf-pay-btn" href="{pay_url}" rel="noopener noreferrer">
  <span style="color:#ffffff!important;-webkit-text-fill-color:#ffffff!important;">{pay_label}</span>
</a>
                    """,
                    unsafe_allow_html=True,
                )
            except Exception as e:
                st.error(f"{t('pay_error', lang)}{e}")
        else:
            st.warning(t("pay_unconfigured", lang))


def format_welcome(email: str, name: str = "", lang: str = "zh") -> str:
    """欢迎 Laurence.ku 古念松 回来 —— 邮箱前缀首字母大写 + 姓名。"""
    local = (email or "").split("@")[0].strip()
    if local:
        local = local[0].upper() + local[1:]
    name = (name or "").strip()
    who = " ".join(p for p in (local, name) if p).strip() or "用户"
    if lang == "en":
        return f"Welcome back, {who}"
    return f"欢迎 {who} 回来"


def report_lang_compatible(report_lang: str | None, ui_lang: str) -> bool:
    """简繁同属中文，不强制因 zh↔zh_hant 重新生成。"""
    if not report_lang:
        return True
    if report_lang == ui_lang:
        return True
    if report_lang in ("zh", "zh_hant") and ui_lang in ("zh", "zh_hant"):
        return True
    return False


def open_upgrade_membership(*, flash: str | None = None, mark_prompted: bool = False) -> None:
    """打开主区「升级会员」面板（需随后 st.rerun 才能显示）。"""
    st.session_state.show_join_membership = True
    if flash:
        st.session_state["_upgrade_flash"] = flash
    if mark_prompted:
        st.session_state["_quota_upgrade_prompted"] = True


def _include_liunian_for_tier(tier: str) -> bool:
    """银卡不含流年；免费/金/钻含流年（免费为本地预览）。"""
    return (tier or "free") != "silver"


def _save_report_if_logged_in(report: dict) -> None:
    if not (supabase_client and st.session_state.get("auth_ok")):
        return
    try:
        supabase_client.save_report(
            st.session_state.user_id,
            st.session_state.birth_info,
            st.session_state.bazi_data,
            report,
            payment_tier=st.session_state.subscription_tier or "free",
        )
    except Exception:
        pass


def generate_local_full_report() -> bool:
    """
    本地规则版：命盘后自动生成八字报告 +（非银卡）流年，不调用 DeepSeek、不扣次数。
    """
    if not st.session_state.bazi_data or not st.session_state.birth_info:
        st.error(t("need_input", lang))
        return False
    try:
        from report_local import build_local_report

        tier = st.session_state.subscription_tier or "free"
        report = build_local_report(
            st.session_state.bazi_data,
            st.session_state.birth_info,
            include_liunian=_include_liunian_for_tier(tier),
            lang=lang,
        )
        st.session_state.report_content = report
        st.session_state.report_language = lang
        st.session_state.report_generated = True
        st.session_state.report_source = "local"
        _save_report_if_logged_in(report)
        return True
    except Exception as e:
        st.error(f"{t('report_fail', lang)}{e}")
        return False


def generate_full_report(*, consume_quota: bool = True, force: bool = False) -> bool:
    """AI 深批（DeepSeek）写入 session；成功返回 True。默认扣次数（钻石无限除外）。

    出生信息未变且已有 AI 深批存档时，默认直接复用（不调用 DeepSeek）。
    force=True 时强制重新生成。
    """
    if not force and try_reuse_ai_deep_report():
        st.session_state["_ai_deep_reused"] = True
        return True

    tier = st.session_state.subscription_tier
    if not report_gen:
        st.error(t("ai_engine_missing", lang))
        return False
    if not st.session_state.bazi_data or not st.session_state.birth_info:
        st.error(t("need_input", lang))
        return False
    try:
        st.session_state.pop("_ai_deep_reused", None)
        if consume_quota and tier in PAID_TIERS and supabase_client:
            if not supabase_client.consume_report_quota(st.session_state.user_id):
                open_upgrade_membership(
                    flash="次数已用完，请升级会员后继续生成报告。"
                    if _is_zh()
                    else "No quota left. Please upgrade to continue."
                )
                return False
        elif tier == "free" and supabase_client and st.session_state.get("auth_ok"):
            if not supabase_client.consume_free_preview_quota(st.session_state.user_id):
                open_upgrade_membership(flash=t("free_preview_exhausted", lang))
                return False

        progress = st.progress(0.0)
        status = st.empty()

        def on_progress(done: int, total: int, label: str):
            pct = min(max(done / max(total, 1), 0.0), 1.0)
            progress.progress(pct)
            status.caption(
                f"{t('ai_generating', lang)}（{done}/{total}）{label}"
                if _is_zh()
                else f"{t('ai_generating', lang)} ({done}/{total}) {label}"
            )

        gen_tier = (
            tier
            if tier in ("gold", "diamond")
            else ("gold" if tier == "free" else "silver")
        )
        report = report_gen.generate(
            st.session_state.bazi_data,
            st.session_state.birth_info,
            gen_tier,
            lang=lang,
            progress_callback=on_progress,
        )
        # 银卡：不含流年篇章（page10）
        if tier == "silver":
            report = {
                k: v
                for k, v in report.items()
                if k != "page10" and not (
                    k == "page9" and isinstance(v, dict) and v.get("quarters")
                )
            }
        report = _stamp_report_source(report, "ai")
        st.session_state.report_content = report
        st.session_state.report_language = lang
        st.session_state.report_generated = True
        st.session_state.report_source = "ai"
        progress.progress(1.0)
        status.caption(t("report_ok", lang))
        _save_report_if_logged_in(report)
        return True
    except Exception as e:
        st.error(f"{t('report_fail', lang)}{e}")
        return False


def go_results_section(section: str = "chart") -> None:
    """切换到命盘/报告/流年 Tab（独立页，滚到顶部）。"""
    tab_map = {"chart": 1, "report": 2, "liunian": 3}
    st.session_state.ui_tab = tab_map.get(section, 1)
    st.session_state["_scroll_top"] = True
    st.session_state.pop("_scroll_section", None)


def go_report_tab():
    go_results_section("report")


def go_liunian_tab():
    go_results_section("liunian")


def _ensure_local_report() -> None:
    """有命盘但无报告时，自动补本地报告（不耗 AI）。"""
    if st.session_state.bazi_data is not None and not st.session_state.report_content:
        generate_local_full_report()


def render_report_tab_bottom_nav(report: dict, *, key_prefix: str = "report_bottom") -> None:
    """八字报告页底部：可重新生成；有流年篇章则跳转流年报告。"""
    st.markdown("---")
    tier = st.session_state.subscription_tier
    profile = supabase_client.get_user(st.session_state.user_id) if supabase_client else None
    trials = int((profile or {}).get("free_trials_remaining") or 0)
    expires = (profile or {}).get("subscription_expires_at")

    if tier in PAID_TIERS and can_generate_report(tier, trials, expires) and report_gen:
        if st.button(
            "🔄 " + ("重新生成报告" if _is_zh() else "Regenerate report"),
            key=f"{key_prefix}_regen",
            use_container_width=True,
        ):
            with st.spinner(t("generating", lang)):
                # 底部「重新生成」为显式强制重跑 DeepSeek
                if generate_full_report(consume_quota=True, force=True):
                    st.success(t("report_ok", lang))
                    st.rerun()
                elif st.session_state.get("show_join_membership"):
                    st.rerun()

    if ReportGenerator.resolve_liunian_key(report):
        if st.button(
            t("goto_liunian_report", lang),
            key=f"{key_prefix}_to_liunian",
            type="primary",
            use_container_width=True,
        ):
            go_liunian_tab()
            st.rerun()


def _hehun_normalize_gender(g: Any) -> str:
    """归一为「男」/「女」。"""
    s = str(g or "").strip()
    if s.startswith("女") or s.lower() in ("female", "f", "woman"):
        return "女"
    return "男"


def _hehun_opposite_gender(g: Any) -> str:
    return "女" if _hehun_normalize_gender(g) == "男" else "男"


def _hehun_person_form(prefix: str, *, defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """合婚单人出生信息表单。"""
    defaults = defaults or {}
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input(
            t("name", lang),
            value=str(defaults.get("name") or ""),
            key=f"hehun_{prefix}_name",
        )
        gender_opts = [t("male", lang), t("female", lang)]
        g_default = _hehun_normalize_gender(defaults.get("gender") or "男")
        g_idx = 0 if g_default == "男" else 1
        gender_key = f"hehun_{prefix}_gender"
        # 若外部已写入 session（如乙方随甲方取反），沿用；否则用 defaults
        if gender_key not in st.session_state:
            st.session_state[gender_key] = gender_opts[g_idx]
        gender_ui = st.radio(
            t("gender", lang),
            options=gender_opts,
            horizontal=True,
            key=gender_key,
        )
        gender = "男" if gender_ui == t("male", lang) else "女"
        try:
            bd_default = defaults.get("birth_date")
            if isinstance(bd_default, str):
                bd_default = date.fromisoformat(bd_default[:10])
            if not isinstance(bd_default, date):
                bd_default = date(1990, 1, 1)
        except Exception:
            bd_default = date(1990, 1, 1)
        birth_date = st.date_input(
            t("birth_date", lang),
            value=bd_default,
            min_value=date(1, 1, 1),
            max_value=date.today(),
            format="YYYY-MM-DD",
            key=f"hehun_{prefix}_date",
        )
    with c2:
        birth_hour = st.number_input(
            t("birth_hour", lang),
            0,
            23,
            int(defaults.get("birth_hour") or 12),
            key=f"hehun_{prefix}_hour",
        )
        birth_minute = st.number_input(
            t("birth_minute", lang),
            0,
            59,
            int(defaults.get("birth_minute") or 0),
            key=f"hehun_{prefix}_minute",
        )
        reg_labels, reg_ids, _ = region_options(lang)
        try:
            reg_default = reg_ids.index(defaults.get("region_id")) if defaults.get("region_id") in reg_ids else 2
        except Exception:
            reg_default = 2
        reg_idx = st.selectbox(
            t("region", lang),
            options=list(range(len(reg_ids))),
            format_func=lambda i: reg_labels[i],
            index=reg_default,
            key=f"hehun_{prefix}_region",
        )
        region_id = reg_ids[reg_idx]
    use_true_solar = st.checkbox(
        t("true_solar", lang),
        value=bool(defaults.get("use_true_solar", True)),
        key=f"hehun_{prefix}_solar",
    )
    return {
        "name": (name or "").strip(),
        "gender": gender,
        "birth_date": birth_date,
        "birth_hour": int(birth_hour),
        "birth_minute": int(birth_minute),
        "region_id": region_id,
        "use_true_solar": use_true_solar,
    }


def render_hehun_tab() -> None:
    """八字合婚：默认本地打分；金/钻无水印；免费/银卡 3 次水印；AI 仅钻石。"""
    st.markdown(f"### {t('hehun_heading', lang)}")
    st.caption(t("hehun_disclaimer", lang))
    st.caption(t("hehun_intro", lang))

    if not is_registered():
        st.info(t("hehun_login_required", lang))
        if st.button(t("login_btn", lang), key="hehun_login", type="primary"):
            st.session_state.show_login = True
            st.rerun()
        return

    tier = st.session_state.subscription_tier
    is_diamond = tier == "diamond"
    can_local_clean = tier in ("gold", "diamond")  # 金卡/钻石：本地无水印
    needs_watermark_quota = tier in ("free", "silver")
    match_left = 0
    if needs_watermark_quota and supabase_client:
        try:
            match_left = supabase_client.get_match_preview_remaining(st.session_state.user_id)
        except Exception:
            match_left = 3
        st.caption(
            t("hehun_preview_quota", lang).format(
                left=match_left,
                total=getattr(supabase_client, "MATCH_PREVIEW_DEFAULT", 3),
            )
        )

    if needs_watermark_quota and match_left <= 0:
        st.warning(t("hehun_free_exhausted", lang))
        st.info(t("hehun_upgrade_gold", lang))
        st.caption(t("hehun_ai_diamond_only", lang))
        st.session_state.selected_plan = "gold"
        render_membership_plans("hehun_lock_preview")
        return

    reuse = False
    if st.session_state.get("bazi_data") and st.session_state.get("birth_info"):
        reuse = st.checkbox(
            t("hehun_reuse_chart", lang),
            value=True,
            key="hehun_reuse_a",
        )

    st.markdown(f"#### {t('hehun_person_a', lang)}")
    form_a = None
    gender_a = "男"
    if reuse:
        info = st.session_state.birth_info or {}
        st.caption(
            f"{info.get('name') or '—'} · {info.get('birth_date') or '—'} "
            f"{info.get('birth_hour', '—')}:{int(info.get('birth_minute') or 0):02d}"
        )
        gender_a = _hehun_normalize_gender(
            info.get("gender")
            or (st.session_state.get("bazi_data") or {}).get("gender")
            or "男"
        )
        if not st.session_state.get("bazi_data"):
            st.warning(t("hehun_reuse_need_chart", lang))
    else:
        form_a = _hehun_person_form("a", defaults=st.session_state.get("birth_info") or {})
        gender_a = _hehun_normalize_gender((form_a or {}).get("gender") or "男")

    # 乙方性别默认取甲方相反；甲方变更时同步，用户仍可手动改乙方
    gender_b_default = _hehun_opposite_gender(gender_a)
    if st.session_state.get("_hehun_sync_a_gender") != gender_a:
        st.session_state["hehun_b_gender"] = (
            t("male", lang) if gender_b_default == "男" else t("female", lang)
        )
        st.session_state["_hehun_sync_a_gender"] = gender_a

    st.markdown(f"#### {t('hehun_person_b', lang)}")
    form_b = _hehun_person_form("b", defaults={"gender": gender_b_default})

    if st.button(t("hehun_run", lang), type="primary", use_container_width=True, key="hehun_run_btn"):
        try:
            if reuse:
                bazi_a = st.session_state.bazi_data
                name_a = (st.session_state.birth_info or {}).get("name") or t("hehun_person_a", lang)
                if not bazi_a:
                    st.warning(t("hehun_reuse_need_chart", lang))
                    return
            else:
                if not form_a or not form_a.get("name"):
                    st.warning(t("hehun_need_names", lang))
                    return
                bazi_a = compute_bazi_from_form(form_a)
                name_a = form_a["name"]

            if not form_b.get("name"):
                st.warning(t("hehun_need_names", lang))
                return
            bazi_b = compute_bazi_from_form(form_b)
            name_b = form_b["name"]

            # 权限：金/钻无水印；免费/银卡扣次并打水印
            watermarked = False
            if can_local_clean:
                watermarked = False
            elif needs_watermark_quota:
                if not supabase_client or not supabase_client.consume_match_preview_quota(
                    st.session_state.user_id
                ):
                    st.warning(t("hehun_free_exhausted", lang))
                    st.session_state.selected_plan = "gold"
                    st.rerun()
                    return
                watermarked = True
            else:
                st.warning(t("hehun_gold_local_only", lang))
                return

            result = analyze_hehun(bazi_a, bazi_b, lang)
            st.session_state.hehun_result = result
            st.session_state.hehun_bazi_a = bazi_a
            st.session_state.hehun_bazi_b = bazi_b
            st.session_state.hehun_names = {"a": name_a, "b": name_b}
            st.session_state.hehun_ai = None
            st.session_state.hehun_watermarked = watermarked
            try:
                if supabase_client:
                    supabase_client.log_action(
                        st.session_state.user_id,
                        "hehun_local",
                        {"total": result.get("total"), "watermarked": watermarked},
                    )
            except Exception:
                pass
            st.rerun()
        except Exception as e:
            st.error(f"{t('report_fail', lang)}{e}")

    result = st.session_state.get("hehun_result")
    if not result:
        return

    names = st.session_state.get("hehun_names") or {}
    bazi_a = st.session_state.get("hehun_bazi_a") or {}
    bazi_b = st.session_state.get("hehun_bazi_b") or {}
    html = render_hehun_html(
        result,
        name_a=names.get("a") or "",
        name_b=names.get("b") or "",
        bazi_a=bazi_a,
        bazi_b=bazi_b,
        lang=lang,
    )
    watermarked = bool(st.session_state.get("hehun_watermarked"))
    if watermarked:
        mark = f"SigmaFate/{st.session_state.get('user_email') or 'preview'}"
        html = _wrap_protected_html(html, mark)
    st.markdown(html, unsafe_allow_html=True)

    st.markdown("---")
    if is_diamond and report_gen:
        if st.button(t("hehun_ai_btn", lang), type="primary", use_container_width=True, key="hehun_ai_btn"):
            with st.spinner(t("generating", lang)):
                try:
                    ai = report_gen.generate_hehun_deep(
                        name_a=names.get("a") or "",
                        name_b=names.get("b") or "",
                        bazi_a=bazi_a,
                        bazi_b=bazi_b,
                        local_result=result,
                        lang=lang,
                    )
                    st.session_state.hehun_ai = ai
                    st.rerun()
                except Exception as e:
                    st.error(f"{t('hehun_ai_fail', lang)}{e}")

        ai = st.session_state.get("hehun_ai")
        if isinstance(ai, dict) and any(ai.values()):
            st.markdown(f"### {t('hehun_ai_heading', lang)}")
            # 两章：缘分格局 / 相处化解；每章专业解读 + 白话说明（与九页报告同款分段）
            chapters = []
            for key, label_key in (
                ("pattern", "hehun_ai_pattern"),
                ("resolve", "hehun_ai_resolve"),
            ):
                sec = ai.get(key)
                if isinstance(sec, dict) and (
                    sec.get("professional") or sec.get("plain") or sec.get("content")
                ):
                    chapters.append((key, label_key, sec))
                elif isinstance(sec, str) and sec.strip():
                    chapters.append((key, label_key, {"content": sec.strip()}))
            # 兼容旧版四段扁平字符串
            if not chapters:
                for key, label_key in (
                    ("pattern", "hehun_ai_pattern"),
                    ("dynamics", "hehun_ai_dynamics"),
                    ("nurture", "hehun_ai_nurture"),
                    ("caution", "hehun_ai_caution"),
                ):
                    body = (ai.get(key) or "").strip() if isinstance(ai.get(key), str) else ""
                    if body:
                        chapters.append((key, label_key, {"content": body}))
            for _key, label_key, sec in chapters:
                title = t(label_key, lang)
                if report_gen:
                    page = report_gen._normalize_hehun_chapter(sec, title, "")
                else:
                    page = dict(sec) if isinstance(sec, dict) else {"content": str(sec)}
                    page["title"] = title
                html = ReportGenerator.render_page_html(page, lang)
                st.markdown(html, unsafe_allow_html=True)
                st.markdown("")
    elif tier == "gold":
        st.info(t("hehun_ai_diamond_only", lang))
        st.session_state.selected_plan = st.session_state.get("selected_plan") or "diamond"
        if st.button(t("hehun_upgrade_diamond", lang), key="hehun_gold_to_diamond", use_container_width=True):
            st.session_state.show_join_membership = True
            st.session_state.selected_plan = "diamond"
            st.rerun()

    # 金卡/钻石：独立合婚 PDF（封面+总览+维度；钻石若已生成 AI 深批一并收录）
    if not watermarked and tier in ("gold", "diamond"):
        st.markdown("---")
        try:
            ai_for_pdf = st.session_state.get("hehun_ai") if is_diamond else None
            # 写入 PDF 前再规范化，保证 professional / 白话说明 齐全
            if isinstance(ai_for_pdf, dict) and report_gen:
                norm_ai = {}
                for key, label_key in (
                    ("pattern", "hehun_ai_pattern"),
                    ("resolve", "hehun_ai_resolve"),
                ):
                    sec = ai_for_pdf.get(key)
                    if sec:
                        norm_ai[key] = report_gen._normalize_hehun_chapter(
                            sec, t(label_key, lang), ""
                        )
                if norm_ai:
                    ai_for_pdf = norm_ai
            pdf_buf = generate_hehun_pdf_report(
                result,
                name_a=names.get("a") or "",
                name_b=names.get("b") or "",
                bazi_a=bazi_a,
                bazi_b=bazi_b,
                ai_deep=ai_for_pdf if isinstance(ai_for_pdf, dict) else None,
                lang=lang,
            )
            st.caption(t("hehun_pdf_caption", lang))
            st.download_button(
                t("hehun_download_pdf", lang),
                pdf_buf,
                hehun_pdf_filename(names.get("a") or "", names.get("b") or ""),
                "application/pdf",
                key="hehun_dl_pdf",
                use_container_width=True,
            )
        except Exception:
            st.warning(t("pdf_warn", lang))

    if needs_watermark_quota and not (tier in ("gold", "diamond")):
        # 免费/银卡：水印本地结果后，提示升金（无水印）与升钻（AI）
        st.info(t("hehun_upgrade_gold", lang))
        st.caption(t("hehun_ai_diamond_only", lang))
        if st.button(t("hehun_upgrade_diamond", lang), key="hehun_preview_to_diamond", use_container_width=True):
            st.session_state.show_join_membership = True
            st.session_state.selected_plan = "diamond"
            st.rerun()
        st.session_state.selected_plan = st.session_state.get("selected_plan") or "gold"
        render_membership_plans("hehun_after_preview")


def apply_scroll_top_if_needed():
    """滚回页面顶部。"""
    if not st.session_state.pop("_scroll_top", False):
        return
    import streamlit.components.v1 as components

    components.html(
        """
<script>
(function () {
  const w = window.parent || window;
  const tryScroll = () => {
    try {
      w.scrollTo(0, 0);
      const doc = w.document;
      const nodes = [
        doc.scrollingElement,
        doc.documentElement,
        doc.body,
        doc.querySelector('[data-testid="stAppViewContainer"]'),
        doc.querySelector('section.main'),
        doc.querySelector('[data-testid="stMain"]'),
      ];
      nodes.forEach((el) => {
        if (el && typeof el.scrollTo === 'function') el.scrollTo(0, 0);
        if (el) el.scrollTop = 0;
      });
    } catch (e) {}
  };
  tryScroll();
  setTimeout(tryScroll, 50);
  setTimeout(tryScroll, 200);
})();
</script>
        """,
        height=0,
        width=0,
    )


def apply_scroll_section_if_needed():
    """命盘/报告/流年 Tab：滚到对应标题（同一连续页内跳转）。"""
    section = st.session_state.pop("_scroll_section", None)
    if not section:
        return
    markers = {
        "chart": ["八字命盘", "BaZi Chart", "Chart result", "排盘结果"],
        "report": ["八字报告", "BaZi Report", "Your report", "完整报告"],
        "liunian": ["流年报告", "Annual Luck", "一生流年"],
    }.get(section, [])
    if not markers:
        return
    import json
    import streamlit.components.v1 as components

    markers_js = json.dumps(markers, ensure_ascii=False)
    components.html(
        f"""
<script>
(function () {{
  const markers = {markers_js};
  const w = window.parent || window;
  const doc = w.document;
  const findEl = () => {{
    const nodes = [...doc.querySelectorAll('h1,h2,h3,h4,div,p,span')];
    for (const m of markers) {{
      const hit = nodes.find((n) => (n.textContent || '').includes(m));
      if (hit) return hit;
    }}
    return null;
  }};
  const go = () => {{
    try {{
      const el = findEl();
      if (el && el.scrollIntoView) {{
        el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        return;
      }}
      w.scrollTo(0, 0);
    }} catch (e) {{}}
  }};
  go();
  setTimeout(go, 80);
  setTimeout(go, 250);
  setTimeout(go, 500);
}})();
</script>
        """,
        height=0,
        width=0,
    )


def render_ziwei_tab() -> None:
    """紫微斗数：排盘（四化/三合/飞星）+ 基础解读全员开放；AI 深批金卡+无水印与 PDF。"""
    st.markdown(f"### {t('ziwei_heading', lang)}")
    st.caption(t("ziwei_intro", lang))
    with st.expander(t("ziwei_theory_title", lang), expanded=False):
        st.markdown(format_ziwei_theory_markdown(lang))

    bi = st.session_state.get("birth_info")
    bd = st.session_state.get("bazi_data")
    if not bi or not bd:
        st.info(t("ziwei_need_chart", lang))
        return

    st.caption(t("ziwei_reuse_caption", lang))
    st.caption(
        f"{bi.get('name') or '—'} · {bi.get('birth_date') or '—'} "
        f"{bi.get('birth_hour', '—')}:{int(bi.get('birth_minute') or 0):02d} · "
        f"{bi.get('gender') or bd.get('gender') or '—'}"
    )

    if st.button(t("ziwei_run", lang), type="primary", use_container_width=True, key="ziwei_run_btn"):
        try:
            chart = compute_ziwei_from_birth_info(bi, bd)
            reading = build_ziwei_basic_reading(chart, lang=lang)
            st.session_state.ziwei_chart = chart
            st.session_state.ziwei_reading = reading
            st.session_state.ziwei_ai = None
            st.session_state.ziwei_ai_watermarked = False
            st.rerun()
        except Exception as e:
            st.error(f"{t('report_fail', lang)}{e}")
            return

    chart = st.session_state.get("ziwei_chart")
    if not isinstance(chart, dict) or not chart.get("ok"):
        return

    # 刷新盘面字段（如大限公历年），避免旧 session 缓存缺年份
    try:
        chart = compute_ziwei_from_birth_info(bi, bd)
        st.session_state.ziwei_chart = chart
    except Exception:
        pass

    reading = build_ziwei_basic_reading(chart, lang=lang)
    st.session_state.ziwei_reading = reading

    # 1) 方格十二宫盘（四化 / 三合 / 飞星）
    st.markdown(f"#### {t('ziwei_chart_heading', lang)}")
    mode_labels = [
        t("ziwei_mode_sihua", lang),
        t("ziwei_mode_sanhe", lang),
        t("ziwei_mode_feixing", lang),
    ]
    mode_keys = ["sihua", "sanhe", "feixing"]
    picked = st.radio(
        t("ziwei_mode_label", lang),
        options=mode_labels,
        horizontal=True,
        key="ziwei_chart_mode",
        label_visibility="collapsed",
    )
    mode = mode_keys[mode_labels.index(picked)] if picked in mode_labels else "sihua"
    st.caption(t("ziwei_mode_hint", lang))
    # 用 components.html 渲染方格盘，避免 st.markdown 吃掉复杂 HTML/CSS
    import streamlit.components.v1 as components

    chart_html = render_ziwei_chart_html(chart, mode=mode, lang=lang, include_title=False)
    components.html(
        f"""<!doctype html><html><head><meta charset="utf-8"/>
<style>
  body {{ margin:0; padding:0; font-family: "Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif;
         background: transparent; color:#222; }}
  table {{ font-variant-east-asian: proportional-width; }}
</style></head><body>{chart_html}</body></html>""",
        height=920,
        scrolling=True,
    )

    # 2) 盘面下方：基础解读
    st.markdown("---")
    st.markdown(f"#### {t('ziwei_local_heading', lang)}")
    st.caption(t("ziwei_basic_hint", lang))
    st.markdown(
        render_ziwei_reading_html(reading, lang=lang, include_title=False),
        unsafe_allow_html=True,
    )

    st.markdown("---")
    tier = st.session_state.subscription_tier or "free"
    can_ai_clean = tier in ("gold", "diamond")

    if can_ai_clean:
        st.caption(t("ziwei_ai_clean_note", lang))
    else:
        st.caption(t("ziwei_ai_watermark_note", lang))

    if st.button(t("ziwei_ai_btn", lang), type="primary", use_container_width=True, key="ziwei_ai_btn"):
        if not is_registered():
            st.warning(t("ziwei_ai_need_login", lang))
            st.session_state.show_login = True
        elif not report_gen:
            st.warning(t("ai_engine_missing", lang))
        else:
            with st.spinner(t("generating", lang)):
                try:
                    # 免费预览额度 / 付费报告额度（银卡）；金钻不扣次
                    if tier == "free" and supabase_client and st.session_state.get("auth_ok"):
                        if not supabase_client.consume_free_preview_quota(st.session_state.user_id):
                            st.warning(t("free_preview_exhausted", lang))
                            st.session_state.selected_plan = "gold"
                            render_membership_plans("ziwei_ai_quota")
                            return
                    elif tier == "silver" and supabase_client:
                        if not supabase_client.consume_report_quota(st.session_state.user_id):
                            st.warning(t("free_preview_exhausted", lang))
                            return
                    ai = report_gen.generate_ziwei_deep(
                        chart=chart,
                        local_reading=reading,
                        lang=lang,
                    )
                    st.session_state.ziwei_ai = ai
                    st.session_state.ziwei_ai_watermarked = not can_ai_clean
                    st.rerun()
                except Exception as e:
                    st.error(f"{t('ziwei_ai_fail', lang)}{e}")

    ai = st.session_state.get("ziwei_ai")
    if isinstance(ai, dict) and any(ai.values()):
        st.markdown(f"### {t('ziwei_ai_heading', lang)}")
        ai_keys = (
            ("career", "ziwei_ai_career"),
            ("wealth", "ziwei_ai_wealth"),
            ("love", "ziwei_ai_love"),
            ("health", "ziwei_ai_health"),
        )
        # 兼容旧三章缓存
        if not any(ai.get(k) for k, _ in ai_keys) and (ai.get("pattern") or ai.get("life")):
            ai_keys = (
                ("pattern", "ziwei_ai_career"),
                ("career", "ziwei_ai_wealth"),
                ("life", "ziwei_ai_love"),
            )
        for key, label_key in ai_keys:
            sec = ai.get(key)
            if not sec:
                continue
            title = t(label_key, lang)
            if report_gen:
                page = report_gen._normalize_hehun_chapter(sec, title, "")
            else:
                page = dict(sec) if isinstance(sec, dict) else {"content": str(sec)}
                page["title"] = title
            html = ReportGenerator.render_page_html(page, lang)
            if st.session_state.get("ziwei_ai_watermarked"):
                mark = f"SigmaFate/{st.session_state.get('user_email') or 'preview'}"
                html = _wrap_protected_html(html, mark)
            st.markdown(html, unsafe_allow_html=True)
            st.markdown("")

        if not can_ai_clean:
            st.info(t("ziwei_ai_watermark_note", lang))
            st.session_state.selected_plan = st.session_state.get("selected_plan") or "gold"
            render_membership_plans("ziwei_ai_upgrade")

    # 金卡/钻石：PDF（含本地；若有 AI 一并收录），无水印
    if can_ai_clean:
        st.markdown("---")
        try:
            ai_for_pdf = st.session_state.get("ziwei_ai")
            if isinstance(ai_for_pdf, dict) and report_gen:
                norm = {}
                for key, label_key in (
                    ("career", "ziwei_ai_career"),
                    ("wealth", "ziwei_ai_wealth"),
                    ("love", "ziwei_ai_love"),
                    ("health", "ziwei_ai_health"),
                    ("pattern", "ziwei_ai_career"),
                    ("life", "ziwei_ai_love"),
                ):
                    sec = ai_for_pdf.get(key)
                    if sec:
                        norm[key] = report_gen._normalize_hehun_chapter(
                            sec, t(label_key, lang), ""
                        )
                if norm:
                    ai_for_pdf = norm
            pdf_buf = generate_ziwei_pdf_report(
                chart,
                reading,
                ai_deep=ai_for_pdf if isinstance(ai_for_pdf, dict) else None,
                lang=lang,
            )
            st.caption(t("ziwei_pdf_caption", lang))
            st.download_button(
                t("ziwei_download_pdf", lang),
                pdf_buf,
                ziwei_pdf_filename(str(bi.get("name") or chart.get("name") or "")),
                "application/pdf",
                key="ziwei_dl_pdf",
                use_container_width=True,
            )
        except Exception:
            st.warning(t("pdf_warn", lang))


def render_name_tab() -> None:
    """独立 Tab：姓名详批（本地；全员完整无水印；输入即算，无需按钮）。"""
    st.markdown(f"### {t('name_heading', lang)}")
    st.caption(t("name_intro", lang))
    st.caption(t("name_stroke_note", lang))
    with st.expander(t("name_theory_title", lang), expanded=False):
        st.markdown(format_name_theory_markdown(lang))

    if st.session_state.bazi_data is None:
        st.info(t("name_need_chart", lang))

    # 默认沿用八字输入姓名；若用户未改过预填值，源姓名更新时同步
    bi = st.session_state.get("birth_info") or {}
    source_name = ""
    if isinstance(bi, dict) and bi.get("name"):
        source_name = str(bi.get("name") or "").strip()
    if not source_name:
        source_name = str(st.session_state.get("input_name") or "").strip()
    prev_source = str(st.session_state.get("_name_tab_source") or "")
    current_val = str(st.session_state.get("name_tab_input") or "")
    if "name_tab_input" not in st.session_state:
        st.session_state.name_tab_input = source_name
    elif source_name and (not current_val or current_val == prev_source):
        st.session_state.name_tab_input = source_name
    st.session_state._name_tab_source = source_name

    name_val = st.text_input(
        t("name_input", lang),
        placeholder=t("name_input_ph", lang),
        key="name_tab_input",
    )
    st.caption(t("name_input_hint", lang))
    compound = st.checkbox(t("name_compound", lang), value=False, key="name_tab_compound")

    raw_name = (name_val or "").strip()
    if not raw_name:
        st.info(t("name_enter_hint", lang))
        return

    result = analyze_name_with_bazi(
        raw_name,
        st.session_state.get("bazi_data"),
        compound=True if compound else None,
        lang=lang,
    )
    st.session_state["name_analysis_result"] = result

    if not result.get("ok"):
        st.error(result.get("message") or t("report_fail", lang))
        return

    st.success(
        t("name_kangxi_convert", lang).format(
            src=result.get("display_name") or raw_name,
            trad=result.get("traditional_name") or "",
        )
    )
    # 简繁字形差异 + 异体笔画回退提示
    src = str(result.get("display_name") or raw_name or "")
    trad = str(result.get("traditional_name") or "")
    bits = []
    if len(src) == len(trad):
        for a, b in zip(src, trad):
            if a != b:
                bits.append(
                    f"「{a}」→ traditional 「{b}」"
                    if lang == "en"
                    else f"「{a}」转繁体为「{b}」"
                )
    for n in result.get("variant_notes") or []:
        bits.append(
            f"「{n.get('char')}」→ count as 「{n.get('alias')}」 ({n.get('strokes')} strokes)"
            if lang == "en"
            else f"「{n.get('char')}」为异体，按常用字「{n.get('alias')}」{n.get('strokes')}画计"
        )
    if bits:
        detail = "; ".join(bits) if lang == "en" else "；".join(bits)
        if lang == "zh_hant":
            from zh_convert import to_traditional

            detail = to_traditional(detail)
        st.info(t("name_variant_note", lang).format(detail=detail))

    html = render_name_report_html(result, full=True, lang=lang)
    st.markdown(html, unsafe_allow_html=True)


def render_ai_deep_cta(key_prefix: str = "ai") -> None:
    """AI 深批入口（才消耗 DeepSeek / 次数）；出生未变且已有存档时直接复用。"""
    if st.session_state.bazi_data is None:
        return
    reusable = _peek_reusable_ai_report()
    if not report_gen and not reusable:
        return
    tier = st.session_state.subscription_tier
    paid = tier in PAID_TIERS
    has_report = bool(st.session_state.report_content)
    can_reuse = bool(reusable)
    profile = supabase_client.get_user(st.session_state.user_id) if supabase_client else None
    trials = int((profile or {}).get("free_trials_remaining") or 0)
    expires = (profile or {}).get("subscription_expires_at")

    def _after_ai_deep(ok: bool) -> None:
        if ok:
            if st.session_state.pop("_ai_deep_reused", False):
                st.success(t("ai_deep_reuse_unchanged", lang))
            else:
                st.success(t("report_ok", lang))
            go_results_section("report")
            st.rerun()
        elif st.session_state.get("show_join_membership"):
            st.rerun()

    if paid:
        # 可复用已存 AI 时不要求剩余次数
        can = can_reuse or can_generate_report(tier, trials, expires)
        if can_reuse:
            label = t("ai_deep_btn_reuse", lang)
        elif has_report:
            label = t("ai_deep_btn_regen", lang)
        else:
            label = t("ai_deep_btn", lang)
        if st.button(
            label,
            key=f"{key_prefix}_ai_deep",
            type="secondary",
            use_container_width=True,
            disabled=not can,
        ):
            with st.spinner(t("ai_generating", lang)):
                _after_ai_deep(generate_full_report(consume_quota=True, force=False))
    else:
        free_left = int((profile or {}).get("free_trials_remaining") or 0)
        can = can_reuse or can_free_preview(free_left)
        label = t("ai_deep_btn_reuse", lang) if can_reuse else t("ai_deep_btn", lang)
        if st.button(
            label,
            key=f"{key_prefix}_ai_deep_free",
            type="secondary",
            use_container_width=True,
            disabled=not can,
        ):
            with st.spinner(t("ai_generating", lang)):
                _after_ai_deep(generate_full_report(consume_quota=True, force=False))


def render_results_bundle(*, key_prefix: str = "results") -> None:
    """
    入口 A（命盘页）：命盘 → 八字报告 → 流年，同一页连续下滚。
    顶部「八字报告 / 流年报告」仍是独立页（入口 B）。
    """
    if st.session_state.bazi_data is None:
        st.info(t("need_input", lang))
        return

    _ensure_local_report()
    tier = st.session_state.subscription_tier
    paid = tier in PAID_TIERS
    report = st.session_state.report_content
    has_report = bool(report)
    src = st.session_state.get("report_source") or ""

    st.info(t("results_scroll_hint", lang))
    if src == "local":
        st.caption(t("report_source_local", lang))
    elif src == "ai":
        st.caption(t("report_source_ai", lang))

    jump_l, jump_r = st.columns(2)
    with jump_l:
        if st.button(
            t("jump_to_report", lang),
            key=f"{key_prefix}_open_report_tab",
            use_container_width=True,
        ):
            go_report_tab()
            st.rerun()
    with jump_r:
        if st.button(
            t("jump_to_liunian", lang),
            key=f"{key_prefix}_open_liunian_tab",
            use_container_width=True,
        ):
            go_liunian_tab()
            st.rerun()

    st.markdown(f"## 📊 {t('tab_chart', lang)}")
    render_bazi_chart(st.session_state.bazi_data, lang)
    render_ai_deep_cta(f"{key_prefix}_after_chart")

    st.markdown("---")
    st.markdown(f"## 📄 {t('tab_report', lang)}")
    if not has_report:
        st.warning(t("results_report_missing", lang))
        if st.button(
            t("generate_local_now", lang),
            key=f"{key_prefix}_gen_local",
            type="primary",
        ):
            with st.spinner(t("generating", lang)):
                if generate_local_full_report():
                    st.rerun()
    else:
        report_lang = st.session_state.get("report_language")
        if not report_lang_compatible(report_lang, lang):
            st.warning(t("report_lang_mismatch", lang))
            if st.button(t("report_regen_lang", lang), key=f"{key_prefix}_regen_lang"):
                with st.spinner(t("generating", lang)):
                    if generate_local_full_report():
                        st.rerun()
        if not paid:
            st.warning(t("free_preview_banner", lang))
        render_report_pages(report, protected=not paid, pages=range(1, 10))
        if paid:
            st.markdown("---")
            render_report_download_row(report, f"{key_prefix}_report")

    st.markdown("---")
    st.markdown(f"## 📅 {t('tab_liunian', lang)}")
    try:
        from bazi_analysis import render_lifetime_fortune_html

        st.markdown(
            render_lifetime_fortune_html(st.session_state.bazi_data, lang),
            unsafe_allow_html=True,
        )
    except Exception:
        pass

    if not has_report:
        st.info(t("results_liunian_need_report", lang))
    elif not ReportGenerator.resolve_liunian_key(report):
        st.info(t("results_no_liunian", lang))
    else:
        if not paid:
            st.warning(t("free_preview_banner", lang))
        render_liunian_report(report, protected=not paid)
        if paid:
            st.markdown("---")
            render_report_download_row(report, f"{key_prefix}_liunian")

    if not paid:
        st.markdown("---")
        st.markdown(f"### {t('unlock_heading', lang)}")
        st.markdown(t("unlock_body", lang))
        render_membership_plans(f"{key_prefix}_unlock")


def render_report_tab_page(*, key_prefix: str = "tab_report") -> None:
    """入口 B：顶部「八字报告」独立页。"""
    if st.session_state.bazi_data is None:
        st.info(t("need_input", lang))
        return
    _ensure_local_report()
    tier = st.session_state.subscription_tier
    paid = tier in PAID_TIERS
    report = st.session_state.report_content
    if not report:
        st.warning(t("results_report_missing", lang))
        if st.button(t("generate_local_now", lang), key=f"{key_prefix}_gen", type="primary"):
            with st.spinner(t("generating", lang)):
                if generate_local_full_report():
                    st.rerun()
        return

    st.markdown(f"## 📄 {t('your_report', lang)}")
    src = st.session_state.get("report_source") or ""
    if src == "local":
        st.caption(t("report_source_local", lang))
    elif src == "ai":
        st.caption(t("report_source_ai", lang))

    report_lang = st.session_state.get("report_language")
    if not report_lang_compatible(report_lang, lang):
        st.warning(t("report_lang_mismatch", lang))
        if st.button(t("report_regen_lang", lang), key=f"{key_prefix}_regen_lang"):
            with st.spinner(t("generating", lang)):
                if generate_local_full_report():
                    st.rerun()

    if ReportGenerator.resolve_liunian_key(report):
        if st.button(
            t("goto_liunian_report", lang),
            key=f"{key_prefix}_to_liunian",
            use_container_width=True,
        ):
            go_liunian_tab()
            st.rerun()

    if not paid:
        st.warning(t("free_preview_banner", lang))
    render_report_pages(report, protected=not paid, pages=range(1, 10))
    render_ai_deep_cta(f"{key_prefix}_ai")
    if paid:
        st.markdown("---")
        render_report_download_row(report, f"{key_prefix}_dl")
        render_report_tab_bottom_nav(report, key_prefix=f"{key_prefix}_nav")
    else:
        render_report_tab_bottom_nav(report, key_prefix=f"{key_prefix}_nav_free")
        st.markdown("---")
        st.markdown(f"### {t('unlock_heading', lang)}")
        st.markdown(t("unlock_body", lang))
        render_membership_plans(f"{key_prefix}_unlock")


def render_liunian_tab_page(*, key_prefix: str = "tab_liunian") -> None:
    """入口 B：顶部「流年报告」独立页。"""
    if st.session_state.bazi_data is None:
        st.info(t("need_input", lang))
        return
    _ensure_local_report()
    tier = st.session_state.subscription_tier
    paid = tier in PAID_TIERS
    report = st.session_state.report_content

    st.markdown(f"## 📅 {t('liunian_heading', lang)}")
    try:
        from bazi_analysis import render_lifetime_fortune_html

        st.markdown(
            render_lifetime_fortune_html(st.session_state.bazi_data, lang),
            unsafe_allow_html=True,
        )
        st.markdown("---")
    except Exception:
        pass

    if not report:
        st.info(t("results_liunian_need_report", lang))
        if st.button(t("generate_local_now", lang), key=f"{key_prefix}_gen", type="primary"):
            with st.spinner(t("generating", lang)):
                if generate_local_full_report():
                    st.rerun()
        return

    if not ReportGenerator.resolve_liunian_key(report):
        st.info(t("results_no_liunian", lang))
        if st.button(t("goto_full_report", lang), key=f"{key_prefix}_to_report"):
            go_report_tab()
            st.rerun()
        return

    if st.button(
        t("goto_full_report", lang),
        key=f"{key_prefix}_back_report",
        use_container_width=True,
    ):
        go_report_tab()
        st.rerun()

    if not paid:
        st.warning(t("free_preview_banner", lang))
    render_liunian_report(report, protected=not paid)
    if paid:
        st.markdown("---")
        render_report_download_row(report, f"{key_prefix}_dl")
    else:
        st.markdown("---")
        st.markdown(f"### {t('unlock_heading', lang)}")
        st.markdown(t("unlock_body", lang))
        render_membership_plans(f"{key_prefix}_unlock")


def render_report_download_row(report: dict, key_prefix: str = "dl"):
    """付费用户：下载 PDF（金/钻含流年；银卡仅九页主报告）。"""
    tier = st.session_state.subscription_tier
    include_liunian = tier in ("gold", "diamond")
    try:
        pdf_buffer = generate_pdf_report(
            report,
            st.session_state.birth_info or {},
            st.session_state.bazi_data or {},
            include_liunian=include_liunian,
            lang=lang,
        )
        label = t("download_pdf", lang)
        if include_liunian:
            st.caption(t("pdf_includes_liunian", lang))
        else:
            st.caption(t("pdf_silver_no_liunian", lang))
        st.download_button(
            label,
            pdf_buffer,
            pdf_filename(st.session_state.birth_info or {}),
            "application/pdf",
            key=f"{key_prefix}_pdf",
            use_container_width=True,
        )
    except Exception:
        st.warning(t("pdf_warn", lang))


def render_report_cta(key_prefix: str = "main"):
    """兼容旧入口：引导继续下滚阅读；AI 深批单独按钮。"""
    if st.session_state.bazi_data is None:
        return
    if not st.session_state.report_content:
        if st.button(
            t("generate_local_now", lang),
            key=f"{key_prefix}_ensure_local",
            type="primary",
            use_container_width=True,
        ):
            with st.spinner(t("generating", lang)):
                if generate_local_full_report():
                    go_results_section("report")
                    st.rerun()
        return
    st.caption(t("results_scroll_hint", lang))
    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            t("jump_to_report", lang),
            key=f"{key_prefix}_jump_report",
            type="primary",
            use_container_width=True,
        ):
            go_results_section("report")
            st.rerun()
    with c2:
        if st.button(
            t("jump_to_liunian", lang),
            key=f"{key_prefix}_jump_liunian",
            use_container_width=True,
        ):
            go_results_section("liunian")
            st.rerun()
    render_ai_deep_cta(key_prefix)



def _wrap_protected_html(inner_html: str, mark: str) -> str:
    """免费预览：条码水印 + 禁选禁复制（浏览器层，无法绝对禁止截屏）。"""
    mark_esc = (
        (mark or "preview")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    # 条码感条纹 + 斜向水印字
    return f"""
<div class="sf-protected" style="position:relative;user-select:none;-webkit-user-select:none;
  -webkit-touch-callout:none;overflow:hidden;border-radius:10px;"
  oncopy="return false;" oncut="return false;" oncontextmenu="return false;"
  ondragstart="return false;">
  <div style="position:relative;z-index:1;filter:contrast(0.95);">{inner_html}</div>
  <div aria-hidden="true" style="pointer-events:none;position:absolute;inset:0;z-index:2;
    background:
      repeating-linear-gradient(90deg,
        rgba(0,0,0,0.07) 0px, rgba(0,0,0,0.07) 2px,
        transparent 2px, transparent 5px,
        rgba(0,0,0,0.04) 5px, rgba(0,0,0,0.04) 6px,
        transparent 6px, transparent 11px),
      repeating-linear-gradient(-28deg,
        transparent 0 46px,
        rgba(45,90,45,0.10) 46px 58px);
    mix-blend-mode:multiply;"></div>
  <div aria-hidden="true" style="pointer-events:none;position:absolute;inset:-20%;z-index:3;
    display:flex;flex-wrap:wrap;align-content:space-around;justify-content:space-around;
    transform:rotate(-24deg);opacity:0.22;font-weight:800;font-size:15px;color:#1b5e20;
    letter-spacing:0.08em;line-height:2.4;word-break:break-all;">
    {" ".join([mark_esc] * 36)}
  </div>
  <div style="position:absolute;left:0;right:0;bottom:0;z-index:4;padding:8px 12px;
    background:linear-gradient(transparent, rgba(255,255,255,0.92));
    color:#c62828;font-size:0.85rem;font-weight:700;text-align:center;">
    免费预览 · 含水印条码 · 禁止复制/下载 · 截图亦含水印标识
  </div>
</div>
<script>
(function(){{
  document.querySelectorAll('.sf-protected').forEach(function(el){{
    el.addEventListener('copy', function(e){{ e.preventDefault(); }});
    el.addEventListener('cut', function(e){{ e.preventDefault(); }});
  }});
}})();
</script>
""".strip()


def render_report_pages(report: dict, *, protected: bool = False, pages=None):
    """渲染主报告页；默认 1–9（含健康 Part2）。流年（page10）另用独立入口。"""
    tier = st.session_state.subscription_tier
    page_range = pages or range(1, ReportGenerator.CORE_PAGE_COUNT + 1)
    labels_zh = [
        "页一：八字命盘与基本信息",
        "页二：事业详批 (Part 1｜局势)",
        "页三：事业详批 (Part 2｜方向与化解)",
        "页四：财运详批 (Part 1｜局势)",
        "页五：财运详批 (Part 2｜方向与化解)",
        "页六：感情详批 (Part 1｜局势)",
        "页七：感情详批 (Part 2｜方向与化解)",
        "页八：健康详批 (Part 1｜局势)",
        "页九：健康详批 (Part 2｜方向与化解)",
        "流年报告",
    ]
    labels_en = [
        "Page 1: Chart",
        "Page 2: Career (Part 1 · Situation)",
        "Page 3: Career (Part 2 · Direction & Remedy)",
        "Page 4: Wealth (Part 1 · Situation)",
        "Page 5: Wealth (Part 2 · Direction & Remedy)",
        "Page 6: Relationship (Part 1 · Situation)",
        "Page 7: Relationship (Part 2 · Direction & Remedy)",
        "Page 8: Health (Part 1 · Situation)",
        "Page 9: Health (Part 2 · Direction & Remedy)",
        "Annual Luck Report",
    ]
    labels = labels_en if lang == "en" else labels_zh
    if lang == "zh_hant":
        try:
            from zh_convert import to_traditional

            labels = [to_traditional(x) for x in labels_zh]
        except Exception:
            pass
    mark = st.session_state.get("user_email") or (st.session_state.birth_info or {}).get("name") or "SIGMA-FATE"
    legacy_ln9 = ReportGenerator.is_legacy_liunian_page9(report)
    # 主报告视图：多页且含第1页；流年单页视图不跳过旧 page9
    core_mode = pages is None or (1 in page_range and len(list(page_range)) > 1)

    for i in page_range:
        if i == 10 and tier == "silver":
            continue
        if i == 9 and legacy_ln9 and core_mode:
            continue
        pk = f"page{i}"
        lab = labels[i - 1] if i <= len(labels) else pk
        # 流年页（page10 或旧 page9 带四季）统一用「流年报告」标签
        page_obj = report.get(pk) if isinstance(report, dict) else None
        if isinstance(page_obj, dict) and page_obj.get("quarters"):
            lab = labels[9] if len(labels) > 9 else ("流年报告" if lang != "en" else "Annual Luck Report")
        with st.expander(lab, expanded=(i == page_range.start)):
            if pk not in report:
                if i == 9 and not legacy_ln9:
                    st.info(
                        "本篇为健康 Part 2（方向与化解）。当前报告尚未生成此页，请重新生成完整报告。"
                        if _is_zh()
                        else "Health Part 2 is missing — please regenerate the full report."
                    )
                continue
            page = report[pk]
            if not isinstance(page, dict):
                page = {"content": str(page), "title": lab}
            page = ReportGenerator.sanitize_page_for_display(page, lab)
            if not page.get("professional") and page.get("content"):
                page = ReportGenerator._split_legacy_content(
                    str(page.get("content")),
                    page.get("title") or lab,
                )
                page = ReportGenerator.sanitize_page_for_display(page, lab)
            if report_gen and report_gen._plain_missing(page.get("plain")):
                try:
                    report_gen.lang = lang
                    page = report_gen._ensure_plain_section(
                        page, page.get("title") or lab
                    )
                    st.session_state.report_content[pk] = page
                except Exception:
                    pass
            html = ReportGenerator.render_page_html(page, lang)
            # 页一：在报告正文前插入性格分析（与命盘五行下同款）
            if i == 1 and st.session_state.get("bazi_data"):
                try:
                    from bazi_analysis import render_personality_html

                    pers = render_personality_html(st.session_state.bazi_data, lang)
                    html = pers + html
                except Exception:
                    pass
            if protected:
                html = _wrap_protected_html(html, str(mark))
            st.markdown(html, unsafe_allow_html=True)


def render_liunian_report(report: dict, *, protected: bool = False):
    """独立篇章：流年报告（金卡/钻石）。"""
    st.caption(t("liunian_chapter_badge", lang))
    lk = ReportGenerator.resolve_liunian_key(report)
    if not lk:
        st.info(
            "尚未生成流年报告。请重新生成完整报告（金卡/钻石会包含本篇）。"
            if _is_zh()
            else "No Annual Luck Report yet. Regenerate (Gold/Diamond includes this chapter)."
        )
        return
    # page10 → range 10；旧 page9 流年 → range 9
    idx = 10 if lk == "page10" else 9
    render_report_pages(report, protected=protected, pages=range(idx, idx + 1))


def render_generate_report_button(key_prefix: str = "main"):
    """兼容旧调用名 → 大号报告入口。"""
    render_report_cta(key_prefix)


# --- 顶栏：中文简体 | 中文繁體 | English ---
col_spacer, col_zh, col_hant, col_en, col_gear = st.columns([5.2, 1.6, 1.6, 1.5, 0.7])
with col_zh:
    if st.button("中文简体", key="btn_lang_zh", use_container_width=True,
                 type="primary" if lang == "zh" else "secondary"):
        st.session_state.lang = "zh"
        st.rerun()
with col_hant:
    if st.button("中文繁體", key="btn_lang_zh_hant", use_container_width=True,
                 type="primary" if lang == "zh_hant" else "secondary"):
        st.session_state.lang = "zh_hant"
        st.rerun()
with col_en:
    if st.button("English", key="btn_lang_en", use_container_width=True,
                 type="primary" if lang == "en" else "secondary"):
        st.session_state.lang = "en"
        st.rerun()
with col_gear:
    if st.button("⚙️", key="btn_admin_gear", help=t("admin_help", lang), use_container_width=True):
        st.session_state.show_admin = True
        st.rerun()

if st.session_state.show_admin:
    if not st.session_state.admin_logged_in:
        render_admin_login(lang, ADMIN_USERNAME, ADMIN_PASSWORD)
    else:
        render_admin_page(lang, supabase_client)
    st.stop()

# --- 邮件重置密码链接（优先于主界面）---
if render_password_reset_panel():
    st.stop()

# --- 侧边栏 ---
with st.sidebar:
    # 顶部：登录状态 / 登录按钮
    if is_registered():
        display_name = (
            (st.session_state.birth_info or {}).get("name")
            or st.session_state.user_email.split("@")[0]
        )
        st.markdown(
            f"<div style='padding:8px 10px;background:#f0f7ff;border-radius:8px;margin-bottom:8px;'>"
            f"<div style='font-size:0.8rem;color:#666;'>{'已登录' if _is_zh() else 'Signed in'}</div>"
            f"<div style='font-weight:700;color:#1565C0;'>👤 {display_name}</div>"
            f"<div style='font-size:0.75rem;color:#888;'>{st.session_state.user_email}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button(t("logout_btn", lang), key="sidebar_logout", use_container_width=True):
            logout_user()
            st.rerun()
    else:
        st.caption("尚未登录" if _is_zh() else "Not signed in")
        if st.button(t("login_btn", lang), key="sidebar_login_btn", use_container_width=True, type="primary"):
            st.session_state.show_login = True
            st.session_state.show_register = False
            st.rerun()

    st.markdown(f"# {t('sidebar_brand', lang)}\n## Sigma Fate · BaZi")
    st.markdown("---")
    st.markdown(f"### {t('sidebar_about', lang)}")
    st.markdown(t("sidebar_body", lang))
    st.markdown("---")
    tier_labels = {
        "free": t("tier_free", lang),
        "silver": t("tier_silver", lang),
        "gold": t("tier_gold", lang),
        "diamond": t("tier_diamond", lang),
    }
    st.info(f"{t('current_status', lang)}：**{tier_labels.get(st.session_state.subscription_tier, t('tier_free', lang))}**")
    if st.session_state.subscription_tier == "free":
        st.warning(t("free_warning", lang))

    # 升级会员
    join_label = "💎 升级会员" if _is_zh() else "💎 Upgrade Membership"
    if st.button(join_label, key="sidebar_join_membership", use_container_width=True):
        st.session_state.show_join_membership = True
        if not is_registered():
            st.session_state.show_register = True
        st.rerun()

    if st.session_state.get("_init_errors"):
        with st.expander(f"⚠️ {t('init_errors', lang)}", expanded=False):
            for err in st.session_state["_init_errors"]:
                st.caption(err)
    st.markdown("---")
    st.markdown("📧 **聯絡我們**" if _is_zh() else "📧 **Contact us**")
    st.caption("✉️ 電郵: Techlife2027@gmail.com" if _is_zh() else "✉️ Email: Techlife2027@gmail.com")
    st.markdown("---")
    st.caption(f"App：`{APP_ID}`")

st.title(t("app_title", lang))
st.markdown(f"*{t('app_subtitle', lang)}*")

# --- 主区顶部：登录入口 ---
if not is_registered():
    top_l, top_r = st.columns([3, 1])
    with top_l:
        st.info(t("login_prompt", lang))
    with top_r:
        if st.button(t("login_btn", lang), key="main_login_btn", use_container_width=True, type="primary"):
            st.session_state.show_login = True
            st.session_state.show_register = False
            st.rerun()
else:
    name_hint = (st.session_state.birth_info or {}).get("name") or ""
    st.success(format_welcome(st.session_state.user_email, name_hint, lang))
    if st.session_state.bazi_data is not None:
        st.caption(t("returning_hint", lang))

# --- 登录面板（侧栏或主区触发）---
if st.session_state.get("show_login") and not is_registered():
    with st.container(border=True):
        render_login_panel("main")

# --- 注册面板（排盘前 / 主动打开）---
if st.session_state.get("show_register") and not is_registered() and not st.session_state.get("show_login"):
    with st.container(border=True):
        def _after_reg():
            pending = st.session_state.pending_form
            if pending:
                with st.spinner(t("generating", lang)):
                    run_bazi(pending)
                    generate_local_full_report()
                st.session_state.pending_form = None
                go_results_section("chart")

        render_register_panel("main_reg", after_ok=_after_reg)

# --- 侧边栏「升级会员」：主区弹注册 + 三档支付 ---
if st.session_state.get("show_join_membership"):
    with st.container(border=True):
        st.markdown(f"### {join_label}")
        _upgrade_flash = st.session_state.pop("_upgrade_flash", None)
        if _upgrade_flash:
            st.warning(_upgrade_flash)
        if not is_registered():
            st.caption(t("register_caption", lang))
            jc1, jc2 = st.columns(2)
            with jc1:
                if st.button(t("register_btn_short", lang), key="join_open_register", type="primary", use_container_width=True):
                    st.session_state.show_register = True
                    st.session_state.show_join_membership = False
                    st.rerun()
            with jc2:
                if st.button(t("login_btn", lang), key="join_switch_login", use_container_width=True):
                    st.session_state.show_login = True
                    st.session_state.show_join_membership = False
                    st.rerun()
        else:
            st.caption(f"{t('registered_as', lang)}: {st.session_state.user_email}")
            render_membership_plans("sidebar_join")
            if st.button("关闭" if _is_zh() else "Close", key="close_join_panel"):
                st.session_state.show_join_membership = False
                st.rerun()

# --- 主导航 ---
_nav_keys = [
    "tab_input",
    "tab_chart",
    "tab_report",
    "tab_liunian",
    "tab_hehun",
    "tab_name",
    "tab_ziwei",
    "tab_survey",
]
_nav_fallback = {
    "tab_name": "✍️ 姓名详批" if _is_zh() else "✍️ Name Analysis",
    "tab_ziwei": "🌌 紫微斗数" if _is_zh() else "🌌 Zi Wei",
}
nav_cols = st.columns(8)
for i, key in enumerate(_nav_keys):
    lab = t(key, lang)
    if lab == key:
        lab = _nav_fallback.get(key, key)
    with nav_cols[i]:
        is_on = int(st.session_state.get("ui_tab", 0)) == i
        if st.button(
            lab,
            key=f"ui_tab_btn_{i}",
            type="primary" if is_on else "secondary",
            use_container_width=True,
        ):
            st.session_state.ui_tab = i
            st.session_state["_scroll_top"] = True
            st.session_state.pop("_scroll_section", None)
            st.rerun()
        if i == 7:
            st.caption(t("survey_gold_hint", lang))

_tab = int(st.session_state.get("ui_tab", 0))
apply_scroll_top_if_needed()

# ========== Tab 0：输入资料 ==========
if _tab == 0:
    st.markdown(f"### {t('input_heading', lang)}")
    st.caption(t("input_caption", lang))
    st.caption(t("input_auto_report_hint", lang))

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input(t("name", lang), placeholder=t("name_ph", lang), key="input_name")
        gender_opts = [t("male", lang), t("female", lang)]
        gender_ui = st.radio(t("gender", lang), options=gender_opts, horizontal=True, key="input_gender")
        gender = "男" if gender_ui == t("male", lang) else "女"
        birth_date = st.date_input(
            t("birth_date", lang),
            value=date(1990, 1, 1),
            min_value=date(1, 1, 1),
            max_value=date.today(),
            format="YYYY-MM-DD",
            key="input_birth_date",
        )
    with col2:
        birth_hour = st.number_input(t("birth_hour", lang), 0, 23, 12, help=t("birth_hour_help", lang), key="input_hour")
        birth_minute = st.number_input(t("birth_minute", lang), 0, 59, 0, key="input_minute")
        reg_labels, reg_ids, _ = region_options(lang)
        reg_idx = st.selectbox(
            t("region", lang),
            options=list(range(len(reg_ids))),
            format_func=lambda i: reg_labels[i],
            index=2,
            help=t("region_help", lang),
            key="input_region",
        )
        region_id = reg_ids[reg_idx]

    use_true_solar = st.checkbox(t("true_solar", lang), True, help=t("true_solar_help", lang), key="input_solar")
    with st.expander(t("more_info", lang)):
        birth_place = st.text_input(t("birth_place", lang), placeholder=t("birth_place_ph", lang), key="input_place")

    form_snapshot = {
        "name": name,
        "gender": gender,
        "birth_date": birth_date,
        "birth_hour": birth_hour,
        "birth_minute": birth_minute,
        "region_id": region_id,
        "use_true_solar": use_true_solar,
        "birth_place": birth_place,
    }

    generate_btn = st.button(t("generate", lang), type="primary", use_container_width=True, disabled=not name)

    if generate_btn and name:
        if not is_registered():
            st.session_state.pending_form = form_snapshot
            st.session_state.show_register = True
            st.rerun()
        elif (
            birth_data_unchanged(form_snapshot, st.session_state.birth_info)
            and st.session_state.bazi_data is not None
            and st.session_state.report_content
        ):
            st.info(t("chart_unchanged_skip", lang))
            go_results_section("chart")
            st.rerun()
        else:
            with st.spinner(t("generating", lang)):
                run_bazi(form_snapshot)
                generate_local_full_report()
            go_results_section("chart")
            st.rerun()

    if st.session_state.show_register and not is_registered():
        st.info(t("need_register", lang))

    if st.session_state.bazi_data is not None:
        st.success(t("input_ready_hint", lang))
        if st.button(
            t("open_chart_scroll", lang),
            key="input_open_chart",
            type="primary",
            use_container_width=True,
        ):
            go_results_section("chart")
            st.rerun()

# ========== Tab 1：命盘（可下滚连看报告+流年） ==========
elif _tab == 1:
    if st.session_state.bazi_data is None:
        st.info(t("need_input", lang))
        if not is_registered():
            st.caption(t("login_prompt", lang))
            if st.button(t("login_btn", lang), key="tab_chart_login"):
                st.session_state.show_login = True
                st.rerun()
    else:
        render_results_bundle(key_prefix="tab_chart")

# ========== Tab 2：八字报告（独立页） ==========
elif _tab == 2:
    render_report_tab_page(key_prefix="tab_report_page")

# ========== Tab 3：流年报告（独立页） ==========
elif _tab == 3:
    render_liunian_tab_page(key_prefix="tab_liunian_page")

# ========== Tab 4：八字合婚 ==========
elif _tab == 4:
    render_hehun_tab()

# ========== Tab 5：姓名详批 ==========
elif _tab == 5:
    render_name_tab()

# ========== Tab 6：紫微斗数 ==========
elif _tab == 6:
    render_ziwei_tab()

# ========== Tab 7：试用问卷 ==========
elif _tab == 7:
    if not is_registered():
        st.info(t("survey_login_required", lang))
        if st.button(t("login_btn", lang), key="survey_tab_login", type="primary"):
            st.session_state.show_login = True
            st.rerun()
    else:
        if st.session_state.bazi_data is None:
            st.caption(t("survey_try_first", lang))
        render_trial_survey(
            lang,
            supabase_client,
            user_id=st.session_state.user_id,
            user_email=st.session_state.user_email,
        )

st.markdown("---")
st.caption(t("footer", lang))
