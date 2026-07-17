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
from trial_survey import render_trial_survey
from utils import (
    format_bazi_display,
    generate_hehun_pdf_report,
    generate_pdf_report,
    hehun_pdf_filename,
    pdf_filename,
    render_bazi_chart,
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
        st.session_state.report_content = restored_report
        st.session_state.report_generated = True

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
        st.caption(t("forgot_password_hint", lang))
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
                t("forgot_password_submit", lang),
                type="primary",
                use_container_width=True,
            )
        if forgot_go:
            em = (forgot_email or "").strip()
            if not em or "@" not in em:
                st.warning(t("forgot_password_need_email", lang))
            elif not forgot_confirm:
                st.warning(t("forgot_password_need_confirm", lang))
            elif not supabase_client:
                st.error(t("forgot_password_fail", lang))
            else:
                try:
                    ok = supabase_client.clear_password_for_reregister(em)
                except Exception:
                    ok = False
                if ok:
                    st.success(t("forgot_password_ok", lang))
                    # 引导同一邮箱去注册设新密码
                    st.session_state[f"{key_prefix}_reg_email"] = em
                    st.session_state.show_register = True
                    st.session_state.show_login = False
                    st.rerun()
                else:
                    st.error(t("forgot_password_fail", lang))


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


def _form_birth_fingerprint(form: Dict[str, Any]) -> tuple:
    """排盘关键字段指纹（不含姓名，姓名不影响四柱）。"""
    bd = form.get("birth_date")
    if hasattr(bd, "isoformat"):
        bd = bd.isoformat()
    return (
        str(form.get("gender") or ""),
        str(bd or ""),
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
        str(info.get("birth_date") or ""),
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


def generate_full_report(*, consume_quota: bool = True) -> bool:
    """生成报告写入 session；成功返回 True。每次成功生成扣 1 次（钻石无限除外）。"""
    tier = st.session_state.subscription_tier
    if not report_gen:
        st.error("报告引擎未配置" if _is_zh() else "Report engine not configured")
        return False
    if not st.session_state.bazi_data or not st.session_state.birth_info:
        st.error(t("need_input", lang))
        return False
    try:
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
                f"{t('generating', lang)}（{done}/{total}）{label}"
                if _is_zh()
                else f"{t('generating', lang)} ({done}/{total}) {label}"
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
        st.session_state.report_content = report
        st.session_state.report_language = lang
        st.session_state.report_generated = True
        progress.progress(1.0)
        status.caption(t("report_ok", lang))
        if supabase_client and st.session_state.get("auth_ok"):
            try:
                supabase_client.save_report(
                    st.session_state.user_id,
                    st.session_state.birth_info,
                    st.session_state.bazi_data,
                    report,
                    payment_tier=tier or "free",
                )
            except Exception:
                pass
        return True
    except Exception as e:
        st.error(f"{t('report_fail', lang)}{e}")
        return False


def go_report_tab():
    st.session_state.ui_tab = 2
    st.session_state["_scroll_top"] = True


def go_liunian_tab():
    st.session_state.ui_tab = 3
    st.session_state["_scroll_top"] = True


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
                if generate_full_report(consume_quota=True):
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
    """从命盘底部点进报告时滚回顶部，避免用户仍停在页底误以为没生成。"""
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
    """命盘下方大号入口：付费看/生成报告；免费预览（带遮挡）。"""
    tier = st.session_state.subscription_tier
    paid = tier in PAID_TIERS
    has_report = bool(st.session_state.report_content)
    profile = supabase_client.get_user(st.session_state.user_id) if supabase_client else None
    trials = int((profile or {}).get("free_trials_remaining") or 0)
    expires = (profile or {}).get("subscription_expires_at")

    st.markdown(
        """
<style>
div[data-testid="stButton"] > button[kind="primary"] {
  min-height: 3.4rem !important;
  font-size: 1.25rem !important;
  font-weight: 700 !important;
  border-radius: 12px !important;
  letter-spacing: 0.02em;
}
</style>
        """,
        unsafe_allow_html=True,
    )

    if paid:
        st.caption(f"{t('remaining_reports', lang)}：{trials if tier != 'diamond' else '∞'}")
        if has_report:
            if st.button(
                "📄 " + t("tab_report", lang).replace("📄 ", ""),
                key=f"{key_prefix}_view_full_report",
                type="primary",
                use_container_width=True,
            ):
                go_report_tab()
                st.rerun()
            # 小号重新生成
            if can_generate_report(tier, trials, expires) and report_gen:
                if st.button(
                    "🔄 " + ("重新生成报告" if _is_zh() else "Regenerate report"),
                    key=f"{key_prefix}_regen_report",
                    use_container_width=True,
                ):
                    with st.spinner(t("generating", lang)):
                        if generate_full_report(consume_quota=True):
                            st.success(t("report_ok", lang))
                            go_report_tab()
                            st.rerun()
                        elif st.session_state.get("show_join_membership"):
                            st.rerun()
        elif can_generate_report(tier, trials, expires) and report_gen:
            if st.button(
                "📄 " + ("生成完整报告" if _is_zh() else "Generate full report"),
                key=f"{key_prefix}_gen_full_report",
                type="primary",
                use_container_width=True,
            ):
                with st.spinner(t("generating", lang)):
                    if generate_full_report(consume_quota=True):
                        st.success(t("report_ok", lang))
                        go_report_tab()
                        st.rerun()
                    elif st.session_state.get("show_join_membership"):
                        st.rerun()
        else:
            st.warning(
                "会员次数不足或已到期，请升级会员后再生成。"
                if _is_zh()
                else "No quota or expired. Please upgrade."
            )
            if (
                not st.session_state.get("show_join_membership")
                and not st.session_state.get("_quota_upgrade_prompted")
            ):
                open_upgrade_membership(mark_prompted=True)
                st.rerun()
    else:
        # 免费：可预览（默认 5 次含水印；已生成报告可反复查看不扣次）
        free_left = int((profile or {}).get("free_trials_remaining") or 0)
        st.caption(
            t("free_preview_quota", lang).format(left=free_left, total=FREE_PREVIEW_LIMIT)
        )
        st.caption(
            "免费可预览完整报告（遮挡预览 · 不可复制/下载）。升级会员可无遮挡阅读并下载。"
            if _is_zh()
            else "Free preview with watermark — no copy/download. Upgrade to unlock."
        )
        can_gen = can_free_preview(free_left) and bool(report_gen)
        btn_label = (
            ("📄 完整报告（免费预览）" if has_report else "📄 生成并预览完整报告")
            if _is_zh()
            else ("📄 Full report (free preview)" if has_report else "📄 Generate free preview")
        )
        if st.button(
            btn_label,
            key=f"{key_prefix}_free_preview_report",
            type="primary",
            use_container_width=True,
            disabled=not has_report and not can_gen,
        ):
            if not has_report:
                if not report_gen:
                    st.error("报告引擎未配置")
                elif not can_gen:
                    open_upgrade_membership(flash=t("free_preview_exhausted", lang))
                    st.rerun()
                else:
                    with st.spinner(t("generating", lang)):
                        if generate_full_report(consume_quota=False):
                            go_report_tab()
                            st.rerun()
                        elif st.session_state.get("show_join_membership"):
                            st.rerun()
            else:
                go_report_tab()
                st.rerun()
        if not has_report and not can_gen:
            st.warning(t("free_preview_exhausted", lang))
            if (
                not st.session_state.get("show_join_membership")
                and not st.session_state.get("_quota_upgrade_prompted")
            ):
                open_upgrade_membership(
                    flash=t("free_preview_exhausted", lang),
                    mark_prompted=True,
                )
                st.rerun()
            render_membership_plans(f"{key_prefix}_free_upgrade")


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
                st.session_state.pending_form = None

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
_nav = [
    t("tab_input", lang),
    t("tab_chart", lang),
    t("tab_report", lang),
    t("tab_liunian", lang),
    t("tab_hehun", lang),
    t("tab_survey", lang),
]
nav_cols = st.columns(6)
for i, lab in enumerate(_nav):
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
            st.rerun()
        # 试用反馈按钮下显示黄金会员提示
        if i == 5:
            st.caption(t("survey_gold_hint", lang))

_tab = int(st.session_state.get("ui_tab", 0))
apply_scroll_top_if_needed()

# ========== Tab 1：输入 + 命盘 ==========
if _tab == 0:
    st.markdown(f"### {t('input_heading', lang)}")
    st.caption(t("input_caption", lang))

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
            st.rerun()
        else:
            with st.spinner(t("generating", lang)):
                run_bazi(form_snapshot)
            st.rerun()

    # 注册：改由顶部统一注册面板处理（含密码）
    if st.session_state.show_register and not is_registered():
        st.info(t("need_register", lang))

    # 已排盘：同页展示命盘 + 会员
    if st.session_state.bazi_data is not None:
        st.markdown("---")
        st.markdown(f"## {t('chart_section', lang)}")
        render_bazi_chart(st.session_state.bazi_data, lang)
        render_generate_report_button("tab_input")
        render_membership_plans("tab_input")

# ========== Tab 2 ==========
elif _tab == 1:
    if st.session_state.bazi_data is None:
        st.info(t("need_input", lang))
        if not is_registered():
            st.caption(t("login_prompt", lang))
            if st.button(t("login_btn", lang), key="tab2_login"):
                st.session_state.show_login = True
                st.rerun()
    else:
        render_bazi_chart(st.session_state.bazi_data, lang)
        st.markdown("---")
        render_report_cta("tab_chart")

# ========== Tab 3：完整报告（九页） ==========
elif _tab == 2:
    tier = st.session_state.subscription_tier
    paid = tier in PAID_TIERS
    has_report = bool(st.session_state.report_content)

    if not has_report:
        if st.session_state.bazi_data is None:
            st.info(t("need_input", lang))
        else:
            st.info(
                "尚未生成报告。请点击下方按钮。"
                if _is_zh()
                else "No report yet — use the button below."
            )
            render_report_cta("tab_report_empty")
        if not paid:
            st.markdown("---")
            render_membership_plans("tab_report")
    else:
        report = st.session_state.report_content
        st.markdown(
            f"<h2 style='font-weight:800;margin:0 0 0.4rem 0;'>{t('your_report', lang)}</h2>",
            unsafe_allow_html=True,
        )
        report_lang = st.session_state.get("report_language")
        if not report_lang_compatible(report_lang, lang):
            st.warning(t("report_lang_mismatch", lang))
            if st.button(t("report_regen_lang", lang), key="regen_report_for_lang", type="primary"):
                with st.spinner(t("generating", lang)):
                    if generate_full_report(consume_quota=st.session_state.subscription_tier in PAID_TIERS):
                        st.success(t("report_ok", lang))
                        st.rerun()
                    elif st.session_state.get("show_join_membership"):
                        st.rerun()
        if paid:
            st.caption(f"{t('generated_at', lang)}：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
            st.caption(t("report_part_legend", lang))
            if ReportGenerator.health_part2_missing(report):
                st.warning(
                    "当前报告缺少「健康详批 Part 2（方向与化解）」。请点击重新生成完整报告以获得页八+页九。"
                    if _is_zh()
                    else "Health Part 2 is missing. Please regenerate the full report for pages 8–9."
                )
            if ReportGenerator.resolve_liunian_key(report):
                if st.button(
                    t("goto_liunian_report", lang),
                    key="goto_liunian_from_report",
                    use_container_width=True,
                ):
                    go_liunian_tab()
                    st.rerun()
            render_report_pages(report, protected=False, pages=range(1, 10))
            st.markdown("---")
            render_report_download_row(report, "tab_report")
            render_report_tab_bottom_nav(report, key_prefix="tab_report_paid")
        else:
            st.warning(
                "免费预览模式：含水印条码，不可复制、不可下载。升级会员可清晰阅读并下载 PDF。"
                if _is_zh()
                else "Free preview with watermark — no copy/download. Upgrade to unlock."
            )
            render_report_pages(report, protected=True, pages=range(1, 10))
            render_report_tab_bottom_nav(report, key_prefix="tab_report_free")
            st.markdown("---")
            st.markdown(f"### {t('unlock_heading', lang)}")
            st.markdown(t("unlock_body", lang))
            render_membership_plans("tab_report_free")

# ========== Tab 4：流年报告 ==========
elif _tab == 3:
    tier = st.session_state.subscription_tier
    paid = tier in PAID_TIERS
    has_report = bool(st.session_state.report_content)

    if st.session_state.bazi_data is not None:
        from bazi_analysis import render_lifetime_fortune_html

        st.markdown(
            render_lifetime_fortune_html(st.session_state.bazi_data, lang),
            unsafe_allow_html=True,
        )
        st.markdown("---")

    if not has_report:
        if st.session_state.bazi_data is None:
            st.info(t("need_input", lang))
        else:
            st.info(
                "请先生成完整报告（免费预览亦含流年篇章，含水印）。"
                if _is_zh()
                else "Generate the full report first — free preview includes Annual Luck (watermarked)."
            )
            render_report_cta("tab_liunian_empty")
    else:
        report = st.session_state.report_content
        if not ReportGenerator.resolve_liunian_key(report):
            st.warning(
                "当前报告尚无流年篇章。请点击重新生成完整报告（免费用户也会生成流年预览）。"
                if _is_zh()
                else "No Annual Luck chapter yet. Please regenerate the full report."
            )
            render_report_cta("tab_liunian_regen")
        else:
            st.markdown(
                f"<h2 style='font-weight:800;margin:0 0 0.4rem 0;'>{t('liunian_heading', lang)}</h2>",
                unsafe_allow_html=True,
            )
            if st.button(
                t("goto_full_report", lang),
                key="goto_report_from_liunian",
                use_container_width=True,
            ):
                go_report_tab()
                st.rerun()
            if not paid:
                st.warning(
                    "免费预览模式：流年报告含水印条码，不可复制、不可下载。"
                    if _is_zh()
                    else "Free preview: Annual Luck is watermarked — no copy/download."
                )
            render_liunian_report(report, protected=not paid)
            st.markdown("---")
            if paid:
                render_report_download_row(report, "tab_liunian")
                st.markdown("---")
                render_report_cta("tab_liunian_paid")
            else:
                st.markdown(f"### {t('unlock_heading', lang)}")
                st.markdown(t("unlock_body", lang))
                render_membership_plans("tab_liunian_free")
                st.markdown("---")
                if st.button(
                    t("goto_full_report", lang),
                    key="goto_report_from_liunian_free_bottom",
                    type="primary",
                    use_container_width=True,
                ):
                    go_report_tab()
                    st.rerun()

# ========== Tab 5：八字合婚 ==========
elif _tab == 4:
    render_hehun_tab()

# ========== Tab 6：试用问卷 ==========
elif _tab == 5:
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
