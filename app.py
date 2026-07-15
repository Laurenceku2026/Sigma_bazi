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
from ui_texts import region_label, region_longitude, region_options, t
from membership import PAID_TIERS, TIERS, can_generate_report, tier_outline
from report_generator import ReportGenerator
from stripe_payment import StripeClient
from supabase_client import AppAccessDenied, SupabaseClient
from utils import format_bazi_display, generate_pdf_report, render_bazi_chart

st.set_page_config(page_title="六西格玛命理 - 八字", page_icon="🔮", layout="wide")

# --- Session ---
for key, default in [
    ("user_id", str(uuid.uuid4())),
    ("subscription_tier", "free"),
    ("report_generated", False),
    ("report_content", None),
    ("bazi_data", None),
    ("birth_info", None),
    ("app_user_synced", False),
    ("lang", "zh"),
    ("admin_logged_in", False),
    ("show_admin", False),
    ("user_email", ""),
    ("show_register", False),
    ("pending_form", None),
    ("selected_plan", None),
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

lang = st.session_state.lang
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
    if valid_email(st.session_state.get("user_email", "")):
        return True
    if supabase_client:
        u = supabase_client.get_user(st.session_state.user_id)
        if u and valid_email(u.get("email", "")):
            st.session_state.user_email = u["email"]
            return True
    return False


def sync_app_user(email: Optional[str] = None):
    if not supabase_client:
        return None
    try:
        profile = supabase_client.ensure_app_user(
            user_id=st.session_state.user_id,
            email=email or st.session_state.user_email,
            subscription_tier=st.session_state.subscription_tier,
            metadata={"source": "streamlit", "app": APP_ID},
        )
        if email:
            supabase_client.admin_update_user(st.session_state.user_id, email_confirmed=True)
        db_tier = profile.get("subscription_tier")
        if db_tier in ("free", "silver", "gold", "diamond", "monthly", "quarterly", "annual"):
            st.session_state.subscription_tier = db_tier
        st.session_state.app_user_synced = True
        return profile
    except Exception as e:
        st.warning(str(e))
        return None


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
        "email": st.session_state.user_email,
        "payment_tier": st.session_state.subscription_tier,
    }
    if supabase_client:
        sync_app_user()
        try:
            supabase_client.log_action(st.session_state.user_id, "generate_bazi", {})
        except Exception:
            pass


def render_membership_plans():
    st.markdown("---")
    st.markdown(f"### {t('membership_heading', lang)}")
    c1, c2, c3 = st.columns(3)
    plans = [("silver", "btn_silver"), ("gold", "btn_gold"), ("diamond", "btn_diamond")]
    for col, (plan_id, label_key) in zip((c1, c2, c3), plans):
        with col:
            if st.button(t(label_key, lang), key=f"plan_{plan_id}", use_container_width=True):
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
                st.link_button(t("pay_now", lang), session.url, use_container_width=True)
            except Exception as e:
                st.error(f"{t('pay_error', lang)}{e}")
        else:
            st.warning(t("pay_unconfigured", lang))


def render_generate_report_button():
    tier = st.session_state.subscription_tier
    profile = supabase_client.get_user(st.session_state.user_id) if supabase_client else None
    trials = int((profile or {}).get("free_trials_remaining") or 0)
    expires = (profile or {}).get("subscription_expires_at")

    if tier in PAID_TIERS:
        st.caption(f"{t('remaining_reports', lang)}：{trials if tier != 'diamond' else '∞'}")

    if tier in PAID_TIERS and can_generate_report(tier, trials, expires) and report_gen:
        if st.button("📄 " + ("生成完整报告" if lang == "zh" else "Generate full report"), key="gen_full_report"):
            with st.spinner(t("generating", lang)):
                try:
                    if supabase_client and not supabase_client.consume_report_quota(st.session_state.user_id):
                        st.error("次数已用完" if lang == "zh" else "No quota left")
                        return
                    report = report_gen.generate(
                        st.session_state.bazi_data,
                        st.session_state.birth_info,
                        tier,
                    )
                    st.session_state.report_content = report
                    st.session_state.report_generated = True
                    if supabase_client:
                        supabase_client.save_report(
                            st.session_state.user_id,
                            st.session_state.birth_info,
                            st.session_state.bazi_data,
                            report,
                            payment_tier=tier,
                        )
                    st.success(t("report_ok", lang))
                    st.rerun()
                except Exception as e:
                    st.error(f"{t('report_fail', lang)}{e}")


# --- 顶栏 ---
col_spacer, col_zh, col_en, col_gear = st.columns([8.2, 1.1, 1.1, 0.8])
with col_zh:
    if st.button(t("chinese", lang), key="btn_lang_zh", use_container_width=True):
        st.session_state.lang = "zh"
        st.rerun()
with col_en:
    if st.button(t("english", lang), key="btn_lang_en", use_container_width=True):
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
    if is_registered():
        st.caption(f"{t('registered_as', lang)}: {st.session_state.user_email}")
    if st.session_state.subscription_tier == "free":
        st.warning(t("free_warning", lang))
    if st.session_state.get("_init_errors"):
        with st.expander(f"⚠️ {t('init_errors', lang)}", expanded=False):
            for err in st.session_state["_init_errors"]:
                st.caption(err)
    st.markdown("---")
    st.markdown("📧 **聯絡我們**" if lang == "zh" else "📧 **Contact us**")
    st.caption("✉️ 電郵: Techlife2027@gmail.com" if lang == "zh" else "✉️ Email: Techlife2027@gmail.com")
    st.markdown("---")
    st.caption(f"App：`{APP_ID}`")

st.title(t("app_title", lang))
st.markdown(f"*{t('app_subtitle', lang)}*")

tab1, tab2, tab3 = st.tabs([t("tab_input", lang), t("tab_chart", lang), t("tab_report", lang)])

# ========== Tab 1：输入 + 注册 + 命盘 ==========
with tab1:
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
        else:
            with st.spinner(t("generating", lang)):
                run_bazi(form_snapshot)
            st.rerun()

    # 注册页
    if st.session_state.show_register and not is_registered():
        st.markdown("---")
        st.markdown(f"### {t('register_heading', lang)}")
        st.caption(t("register_caption", lang))
        reg_email = st.text_input(t("email", lang), placeholder=t("email_ph", lang), key="register_email")
        if st.button(t("register_btn", lang), type="primary", use_container_width=True, key="do_register"):
            if not valid_email(reg_email):
                st.error(t("need_register", lang))
            else:
                st.session_state.user_email = reg_email.strip()
                st.session_state.show_register = False
                sync_app_user(reg_email.strip())
                pending = st.session_state.pending_form or form_snapshot
                with st.spinner(t("generating", lang)):
                    run_bazi(pending)
                st.session_state.pending_form = None
                st.success(t("register_ok", lang))
                st.rerun()

    # 已排盘：同页展示命盘 + 会员
    if st.session_state.bazi_data is not None:
        st.markdown("---")
        st.markdown(f"## {t('chart_section', lang)}")
        render_bazi_chart(st.session_state.bazi_data, lang)
        render_generate_report_button()
        render_membership_plans()

# ========== Tab 2 ==========
with tab2:
    if st.session_state.bazi_data is None:
        st.info(t("need_input", lang))
    else:
        render_bazi_chart(st.session_state.bazi_data, lang)

# ========== Tab 3 ==========
with tab3:
    tier = st.session_state.subscription_tier
    if tier == "free" or not st.session_state.report_content:
        st.warning(t("locked_report", lang))
        st.markdown(f"### {t('unlock_heading', lang)}")
        st.markdown(t("unlock_body", lang))
        render_membership_plans()
    else:
        report = st.session_state.report_content
        st.markdown(f"### {t('your_report', lang)}")
        st.caption(f"{t('generated_at', lang)}：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        max_page = 9 if tier in ("gold", "diamond") else 8
        labels_zh = [
            "页一：八字命盘与基本信息", "页二：事业流年详批 (Part 1)", "页三：事业流年详批 (Part 2)",
            "页四：财运流年详批 (Part 1)", "页五：财运流年详批 (Part 2)", "页六：感情流年详批 (Part 1)",
            "页七：感情流年详批 (Part 2)", "页八：健康流年详批", "页九：流年预测专章",
        ]
        labels_en = [
            "Page 1: Chart", "Page 2: Career (1)", "Page 3: Career (2)",
            "Page 4: Wealth (1)", "Page 5: Wealth (2)", "Page 6: Relationship (1)",
            "Page 7: Relationship (2)", "Page 8: Health", "Page 9: Annual luck",
        ]
        labels = labels_zh if lang == "zh" else labels_en
        for i in range(1, max_page + 1):
            pk = f"page{i}"
            with st.expander(labels[i - 1], expanded=(i == 1)):
                if pk in report:
                    st.markdown(report[pk].get("content", ""))
        st.markdown("---")
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            try:
                pdf_buffer = generate_pdf_report(report, st.session_state.birth_info, st.session_state.bazi_data)
                st.download_button(t("download_pdf", lang), pdf_buffer, f"bazi_{datetime.now():%Y%m%d}.pdf", "application/pdf")
            except Exception:
                st.warning(t("pdf_warn", lang))
        with col_dl2:
            st.download_button(
                t("export_json", lang),
                json.dumps(report, ensure_ascii=False, indent=2),
                f"bazi_{datetime.now():%Y%m%d}.json",
                "application/json",
            )

st.markdown("---")
st.caption(t("footer", lang))
