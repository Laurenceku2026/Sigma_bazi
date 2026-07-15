"""
六西格玛命理 - 八字 App
Sigma Fate - BaZi
基于Streamlit + DeepSeek + Supabase + Stripe
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime
from typing import Optional

import streamlit as st
from dotenv import load_dotenv

from admin_page import render_admin_login, render_admin_page
from bazi_engine import BaziEngine
from i18n import t, timezone_options
from report_generator import ReportGenerator
from stripe_payment import StripeClient
from supabase_client import AppAccessDenied, SupabaseClient
from utils import format_bazi_display, generate_pdf_report, render_wuxing_bars

st.set_page_config(
    page_title="六西格玛命理 - 八字",
    page_icon="🔮",
    layout="wide",
)

# --- Session ---
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if "subscription_tier" not in st.session_state:
    st.session_state.subscription_tier = "free"
if "report_generated" not in st.session_state:
    st.session_state.report_generated = False
if "report_content" not in st.session_state:
    st.session_state.report_content = None
if "bazi_data" not in st.session_state:
    st.session_state.bazi_data = None
if "birth_info" not in st.session_state:
    st.session_state.birth_info = None
if "app_user_synced" not in st.session_state:
    st.session_state.app_user_synced = False
if "lang" not in st.session_state:
    st.session_state.lang = "zh"
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "show_admin" not in st.session_state:
    st.session_state.show_admin = False

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
STRIPE_PRICE_MONTHLY = _cfg("STRIPE_PRICE_MONTHLY")
STRIPE_PRICE_QUARTERLY = _cfg("STRIPE_PRICE_QUARTERLY")
ADMIN_USERNAME = _cfg("ADMIN_USERNAME", "Laurence_ku")
ADMIN_PASSWORD = _cfg("ADMIN_PASSWORD", "Ku_product$2026")

lang = st.session_state.lang

supabase_client = None
stripe_client = None
report_gen = None
_init_errors = []

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_client = SupabaseClient(
            SUPABASE_URL,
            SUPABASE_KEY,
            app_id=APP_ID,
            schema=SUPABASE_APP_SCHEMA,
            use_service_role=bool(SUPABASE_SERVICE_KEY),
        )
    except Exception as e:
        _init_errors.append(f"Supabase: {e}")

if STRIPE_SECRET_KEY:
    try:
        stripe_client = StripeClient(
            STRIPE_SECRET_KEY, STRIPE_PRICE_MONTHLY, STRIPE_PRICE_QUARTERLY
        )
    except Exception as e:
        _init_errors.append(f"Stripe: {e}")

if DEEPSEEK_API_KEY:
    try:
        report_gen = ReportGenerator(
            DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
        )
    except Exception as e:
        _init_errors.append(f"DeepSeek: {e}")

if _init_errors:
    st.session_state["_init_errors"] = _init_errors


def sync_app_user(email: Optional[str] = None):
    if not supabase_client:
        return None
    try:
        profile = supabase_client.ensure_app_user(
            user_id=st.session_state.user_id,
            email=email or None,
            subscription_tier=st.session_state.subscription_tier,
            metadata={"source": "streamlit", "app": APP_ID},
        )
        db_tier = profile.get("subscription_tier")
        if db_tier in ("free", "monthly", "quarterly", "annual"):
            st.session_state.subscription_tier = db_tier
        st.session_state.app_user_synced = True
        return profile
    except AppAccessDenied as e:
        st.error(str(e))
        return None
    except Exception as e:
        st.warning(str(e))
        return None


# --- 右上角：中英文 + 齿轮 ---
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

# --- 管理员页面 ---
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
        "monthly": t("tier_monthly", lang),
        "quarterly": t("tier_quarterly", lang),
    }
    st.info(f"{t('current_status', lang)}：**{tier_labels.get(st.session_state.subscription_tier, t('tier_free', lang))}**")
    if st.session_state.subscription_tier == "free":
        st.warning(t("free_warning", lang))
    if st.session_state.get("_init_errors"):
        with st.expander(f"⚠️ {t('init_errors', lang)}", expanded=False):
            for err in st.session_state["_init_errors"]:
                st.caption(err)
            st.caption(t("init_hint", lang))
    st.markdown("---")
    st.caption(f"App：`{APP_ID}` · Schema：`{SUPABASE_APP_SCHEMA}`")
    st.caption("© 2026 Sigma Fate")

# --- 主界面 ---
st.title(t("app_title", lang))
st.markdown(f"*{t('app_subtitle', lang)}*")

tab1, tab2, tab3 = st.tabs([t("tab_input", lang), t("tab_chart", lang), t("tab_report", lang)])

# ========== Tab 1 ==========
with tab1:
    st.markdown(f"### {t('input_heading', lang)}")
    st.caption(t("input_caption", lang))

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input(t("name", lang), placeholder=t("name_ph", lang))
        gender_opts = [t("male", lang), t("female", lang)]
        gender_ui = st.radio(t("gender", lang), options=gender_opts, horizontal=True)
        gender = "男" if gender_ui == t("male", lang) else "女"
        # Streamlit 默认 min≈value-10年；显式放开以便查历史人物
        birth_date = st.date_input(
            t("birth_date", lang),
            value=date(1990, 1, 1),
            min_value=date(1, 1, 1),
            max_value=date.today(),
            format="YYYY-MM-DD",
        )
    with col2:
        birth_hour = st.number_input(
            t("birth_hour", lang),
            min_value=0,
            max_value=23,
            value=12,
            help=t("birth_hour_help", lang),
        )
        birth_minute = st.number_input(t("birth_minute", lang), min_value=0, max_value=59, value=0)
        tz_labels, tz_values = timezone_options(lang)
        tz_idx = st.selectbox(
            t("timezone", lang),
            options=list(range(len(tz_values))),
            format_func=lambda i: tz_labels[i],
            index=0,
        )
        timezone = tz_values[tz_idx]

    use_true_solar = st.checkbox(
        t("true_solar", lang), value=True, help=t("true_solar_help", lang)
    )

    with st.expander(t("more_info", lang)):
        birth_place = st.text_input(t("birth_place", lang), placeholder=t("birth_place_ph", lang))
        email = st.text_input(t("email", lang), placeholder=t("email_ph", lang))
        st.caption(t("more_tip", lang))

    st.markdown("---")
    st.markdown(f"### {t('choose_tier', lang)}")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        tier_free = st.button(t("btn_free", lang), use_container_width=True, key="btn_free")
    with col_t2:
        tier_monthly = st.button(t("btn_monthly", lang), use_container_width=True, key="btn_monthly")
    with col_t3:
        tier_quarterly = st.button(
            t("btn_quarterly", lang), use_container_width=True, key="btn_quarterly"
        )

    selected_tier = st.session_state.subscription_tier
    if tier_free:
        selected_tier = "free"
    elif tier_monthly:
        selected_tier = "monthly"
        if stripe_client:
            try:
                session = stripe_client.create_checkout_session(
                    st.session_state.user_id,
                    email or f"user_{st.session_state.user_id[:8]}@example.com",
                    "monthly",
                )
                st.markdown(f"[{t('pay_link', lang)}]({session.url})")
                st.success(t("pay_jump", lang))
            except Exception as e:
                st.error(f"{t('pay_error', lang)}{e}")
        else:
            st.warning(t("pay_unconfigured", lang))
    elif tier_quarterly:
        selected_tier = "quarterly"
        if stripe_client:
            try:
                session = stripe_client.create_checkout_session(
                    st.session_state.user_id,
                    email or f"user_{st.session_state.user_id[:8]}@example.com",
                    "quarterly",
                )
                st.markdown(f"[{t('pay_link', lang)}]({session.url})")
                st.success(t("pay_jump", lang))
            except Exception as e:
                st.error(f"{t('pay_error', lang)}{e}")
        else:
            st.warning(t("pay_unconfigured", lang))

    st.markdown("---")
    generate_btn = st.button(
        t("generate", lang),
        type="primary",
        use_container_width=True,
        disabled=not name,
    )

    if generate_btn and name:
        if selected_tier == "free":
            st.info(t("free_only_chart", lang))
        with st.spinner(t("generating", lang)):
            bazi_engine = BaziEngine(
                year=birth_date.year,
                month=birth_date.month,
                day=birth_date.day,
                hour=int(birth_hour),
                minute=int(birth_minute),
                gender=gender,
                timezone=timezone,
                true_solar_time=use_true_solar,
            )
            bazi_data = bazi_engine.calculate().get_summary()
            st.session_state.bazi_data = bazi_data
            st.session_state.birth_info = {
                "name": name,
                "gender": gender,
                "birth_date": birth_date.isoformat(),
                "birth_hour": int(birth_hour),
                "birth_minute": int(birth_minute),
                "timezone": timezone,
                "birth_place": birth_place,
                "email": email,
                "payment_tier": selected_tier,
            }

            if supabase_client:
                sync_app_user(email=email or None)
                try:
                    supabase_client.log_action(
                        st.session_state.user_id,
                        "generate_bazi",
                        {"tier": selected_tier, "has_report": selected_tier != "free"},
                    )
                except Exception:
                    pass

            if selected_tier != "free" and report_gen:
                try:
                    report = report_gen.generate(
                        bazi_data, st.session_state.birth_info, selected_tier
                    )
                    st.session_state.report_content = report
                    st.session_state.report_generated = True
                    if supabase_client:
                        try:
                            supabase_client.save_report(
                                st.session_state.user_id,
                                st.session_state.birth_info,
                                bazi_data,
                                report,
                                payment_tier=selected_tier,
                            )
                        except AppAccessDenied as e:
                            st.error(str(e))
                    st.success(t("report_ok", lang))
                except Exception as e:
                    st.error(f"{t('report_fail', lang)}{e}")
                    st.session_state.report_generated = False
            else:
                st.info(t("chart_ready", lang))
                st.session_state.report_generated = False
            st.rerun()

# ========== Tab 2 ==========
with tab2:
    if st.session_state.bazi_data is None:
        st.info(t("need_input", lang))
    else:
        bazi_data = st.session_state.bazi_data
        col_show1, col_show2 = st.columns(2)
        with col_show1:
            st.markdown(f"### {t('four_pillars', lang)}")
            bazi_display = format_bazi_display(bazi_data["bazi"])
            cols = st.columns(4)
            for i, (pillar, value) in enumerate(bazi_display.items()):
                with cols[i]:
                    st.markdown(f"**{pillar}**")
                    st.markdown(
                        f"<h1 style='text-align:center;font-size:3rem;'>{value}</h1>",
                        unsafe_allow_html=True,
                    )
            st.markdown(f"**{t('day_master', lang)}：** {bazi_data['day_master']}")
            st.markdown(f"**{t('gender', lang)}：** {bazi_data['gender']}")
        with col_show2:
            st.markdown(f"### {t('wuxing', lang)}")
            bars = render_wuxing_bars(bazi_data["wuxing_stats"])
            for bar in bars:
                st.markdown(
                    f"{bar['wuxing']}：{'■' * int(bar['pct'] / 10)} ({bar['count']})"
                )
                st.progress(min(max(bar["pct"] / 100.0, 0.0), 1.0))
                st.caption(f"{bar['pct']:.0f}%")

        st.markdown("---")
        st.markdown(f"### {t('dayun', lang)}")
        if bazi_data["da_yun"]:
            for dy in bazi_data["da_yun"][:6]:
                c0, c1, c2 = st.columns([1, 2, 1])
                c0.markdown(f"**{t('step', lang, n=dy['step'])}**")
                c1.markdown(f"{dy['gan']}{dy['zhi']}")
                c2.markdown(f"_{dy['years']}_")

        st.markdown("---")
        st.markdown(f"### {t('liunian', lang)}")
        if bazi_data["liu_nian"]:
            for ln in bazi_data["liu_nian"]:
                year_label = f"**{ln['year']}**" if ln["is_current"] else str(ln["year"])
                st.markdown(f"{year_label}：{ln['gan']}{ln['zhi']}")

# ========== Tab 3 ==========
with tab3:
    if st.session_state.subscription_tier == "free":
        st.warning(t("locked_report", lang))
        st.markdown(f"### {t('unlock_heading', lang)}")
        st.markdown(t("unlock_body", lang))
        st.markdown(f"### {t('preview', lang)}")
        pages_zh = [
            "页一：八字命盘与基本信息",
            "页二：事业流年详批 (Part 1)",
            "页三：事业流年详批 (Part 2)",
            "页四：财运流年详批 (Part 1)",
            "页五：财运流年详批 (Part 2)",
            "页六：感情流年详批 (Part 1)",
            "页七：感情流年详批 (Part 2)",
            "页八：健康流年详批",
        ]
        pages_en = [
            "Page 1: Chart basics",
            "Page 2: Career (1)",
            "Page 3: Career (2)",
            "Page 4: Wealth (1)",
            "Page 5: Wealth (2)",
            "Page 6: Relationship (1)",
            "Page 7: Relationship (2)",
            "Page 8: Health",
        ]
        for page in pages_zh if lang == "zh" else pages_en:
            st.markdown(f"🔒 {page}")
    elif st.session_state.report_content is None:
        st.info(t("need_generate", lang))
    else:
        report = st.session_state.report_content
        st.markdown(f"### {t('your_report', lang)}")
        st.caption(f"{t('generated_at', lang)}：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        page_names = [f"page{i}" for i in range(1, 9)]
        page_labels = (
            [
                "页一：八字命盘与基本信息",
                "页二：事业流年详批 (Part 1)",
                "页三：事业流年详批 (Part 2)",
                "页四：财运流年详批 (Part 1)",
                "页五：财运流年详批 (Part 2)",
                "页六：感情流年详批 (Part 1)",
                "页七：感情流年详批 (Part 2)",
                "页八：健康流年详批",
            ]
            if lang == "zh"
            else [
                "Page 1: Chart basics",
                "Page 2: Career (1)",
                "Page 3: Career (2)",
                "Page 4: Wealth (1)",
                "Page 5: Wealth (2)",
                "Page 6: Relationship (1)",
                "Page 7: Relationship (2)",
                "Page 8: Health",
            ]
        )
        for i, (page_key, label) in enumerate(zip(page_names, page_labels)):
            with st.expander(label, expanded=(i == 0)):
                if page_key in report:
                    st.markdown(report[page_key].get("content", ""))
                else:
                    st.warning("…")

        st.markdown("---")
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            try:
                pdf_buffer = generate_pdf_report(
                    report,
                    st.session_state.birth_info,
                    st.session_state.bazi_data,
                )
                st.download_button(
                    label=t("download_pdf", lang),
                    data=pdf_buffer,
                    file_name=f"bazi_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                )
            except Exception:
                st.warning(t("pdf_warn", lang))
        with col_dl2:
            json_data = json.dumps(report, ensure_ascii=False, indent=2)
            st.download_button(
                label=t("export_json", lang),
                data=json_data,
                file_name=f"bazi_report_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
            )

st.markdown("---")
st.caption(t("footer", lang))
