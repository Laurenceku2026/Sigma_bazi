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
from trial_survey import render_trial_survey
from utils import format_bazi_display, generate_pdf_report, pdf_filename, render_bazi_chart

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
ADMIN_USERNAME = _cfg("ADMIN_USERNAME", "Laurence_ku")
ADMIN_PASSWORD = _cfg("ADMIN_PASSWORD", "Ku_product$2026")
PWA_MANIFEST_URL = _cfg(
    "PWA_MANIFEST_URL",
    "https://raw.githubusercontent.com/Laurenceku2026/Sigma_bazi/main/static/manifest.webmanifest",
)

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
            STRIPE_SECRET_KEY, STRIPE_PRICE_SILVER, STRIPE_PRICE_GOLD, STRIPE_PRICE_DIAMOND
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


def run_bazi(form: Dict[str, Any]):
    lon = region_longitude(form["region_id"])
    engine = BaziEngine(
        year=form["birth_date"].year,
        month=form["birth_date"].month,
        day=form["birth_date"].day,
        hour=int(form["birth_hour"]),
        minute=int(form["birth_minute"]),
        gender=form["gender"],
        true_solar_time=form["use_true_solar"],
        longitude=lon,
    )
    bazi_data = engine.calculate().get_summary()
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
                session = stripe_client.create_checkout_session(
                    st.session_state.user_id, email, plan
                )
                st.link_button(
                    t("pay_now", lang),
                    session.url,
                    use_container_width=True,
                    key=f"{key_prefix}_pay_{plan}",
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


def generate_full_report(*, consume_quota: bool = True) -> bool:
    """生成报告写入 session；成功返回 True。"""
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
                st.error("次数已用完" if _is_zh() else "No quota left")
                return False
        elif tier == "free" and supabase_client and st.session_state.get("auth_ok"):
            if not supabase_client.consume_free_preview_quota(st.session_state.user_id):
                st.error(t("free_preview_exhausted", lang))
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
        else:
            st.warning("会员次数不足或已到期，请续费后再生成。" if _is_zh() else "No quota or expired.")
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
                    st.warning(t("free_preview_exhausted", lang))
                else:
                    with st.spinner(t("generating", lang)):
                        if generate_full_report(consume_quota=False):
                            go_report_tab()
                            st.rerun()
            else:
                go_report_tab()
                st.rerun()
        if not has_report and not can_gen:
            st.warning(t("free_preview_exhausted", lang))
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

    # 加入会员
    join_label = "💎 加入会员" if _is_zh() else "💎 Join Membership"
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

# --- 侧边栏「加入会员」：主区弹注册 + 三档支付 ---
if st.session_state.get("show_join_membership"):
    with st.container(border=True):
        st.markdown(f"### {join_label}")
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

# --- 主导航（可用按钮跳到「完整报告」）---
_nav = [
    t("tab_input", lang),
    t("tab_chart", lang),
    t("tab_report", lang),
    t("tab_liunian", lang),
    t("tab_survey", lang),
]
nav_cols = st.columns(5)
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
            st.markdown("---")
            render_report_cta("tab_report_paid")
        else:
            st.warning(
                "免费预览模式：含水印条码，不可复制、不可下载。升级会员可清晰阅读并下载 PDF。"
                if _is_zh()
                else "Free preview with watermark — no copy/download. Upgrade to unlock."
            )
            render_report_pages(report, protected=True, pages=range(1, 10))
            if ReportGenerator.resolve_liunian_key(report):
                st.caption(
                    "已含流年报告预览，请点顶部「流年报告」查看（含水印）。"
                    if _is_zh()
                    else "Annual Luck preview included — open the Annual Luck tab (watermarked)."
                )
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

# ========== Tab 5：试用问卷 ==========
elif _tab == 4:
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
