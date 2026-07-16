"""管理员登录与用户管理页面（参考 Horse racing / TechLife portal）。"""
from __future__ import annotations

import csv
import hmac
import io
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

from trial_survey import survey_rows_for_admin
from ui_texts import region_label, t


def _safe_date(value: Any) -> str:
    if not value:
        return "-"
    s = str(value)
    return s[:10] if len(s) >= 10 else s


def _birth_info_fallback(user: Dict[str, Any]) -> Dict[str, Any]:
    raw = user.get("last_birth_info") or {}
    if isinstance(raw, str):
        try:
            import json

            raw = json.loads(raw)
        except Exception:
            raw = {}
    return raw if isinstance(raw, dict) else {}


def _format_birth_time(user: Dict[str, Any]) -> str:
    h = user.get("birth_hour")
    m = user.get("birth_minute")
    if h is None:
        h = _birth_info_fallback(user).get("birth_hour")
    if m is None:
        m = _birth_info_fallback(user).get("birth_minute")
    if h is None:
        return "-"
    try:
        return f"{int(h):02d}:{int(m if m is not None else 0):02d}"
    except (TypeError, ValueError):
        return "-"


def _format_birth_location(user: Dict[str, Any], lang: str) -> str:
    raw = _birth_info_fallback(user)
    rid = user.get("region_id") or raw.get("region_id")
    place = user.get("birth_place")
    if place is None:
        place = raw.get("birth_place") or raw.get("region_label") or ""
    parts = []
    if rid:
        parts.append(region_label(str(rid), lang))
    if str(place or "").strip():
        parts.append(str(place).strip())
    return " · ".join(parts) if parts else "-"


def check_admin_password(password: str, expected: str) -> bool:
    return hmac.compare_digest(password or "", expected or "")


def render_admin_login(lang: str, username_expected: str, password_expected: str) -> None:
    st.markdown(f"## ⚙️ {t('admin_login_title', lang)}")
    with st.form("admin_login_form"):
        username = st.text_input(t("admin_username", lang), key="admin_username")
        password = st.text_input(
            t("admin_password", lang), type="password", key="admin_password"
        )
        submitted = st.form_submit_button(
            t("admin_login_btn", lang), type="primary", use_container_width=True
        )
        if submitted:
            if username == username_expected and check_admin_password(
                password, password_expected
            ):
                st.session_state.admin_logged_in = True
                st.session_state.show_admin = True
                st.success(t("admin_login_ok", lang))
                st.rerun()
            else:
                st.error(t("admin_login_fail", lang))

    if st.button(t("admin_back", lang), key="admin_login_back"):
        st.session_state.show_admin = False
        st.rerun()


def render_admin_page(lang: str, supabase_client) -> None:
    st.markdown(f"## 👥 {t('user_mgmt', lang)}")

    col_back, col_logout = st.columns([1, 1])
    with col_back:
        if st.button(t("admin_back", lang), key="admin_back_btn", use_container_width=True):
            st.session_state.show_admin = False
            st.rerun()
    with col_logout:
        if st.button(t("admin_logout", lang), key="admin_logout_btn", use_container_width=True):
            st.session_state.admin_logged_in = False
            st.session_state.show_admin = False
            st.rerun()

    if not supabase_client:
        st.warning(t("no_users", lang))
        return

    st.info(
        t(
            "admin_scope_info",
            lang,
            schema=supabase_client.schema,
            app_id=supabase_client.app_id,
        )
    )
    st.caption(
        t(
            "admin_table_caption",
            lang,
            table=getattr(supabase_client, "USER_TABLE", "sf_users"),
            schema=supabase_client.schema,
            app_id=supabase_client.app_id,
        )
    )

    purge_cols = st.columns(3)
    with purge_cols[0]:
        if st.button(t("admin_purge_foreign", lang), key="admin_purge_foreign"):
            n = supabase_client.purge_foreign_users()
            st.success(t("admin_purge_foreign_ok", lang, n=n))
            st.rerun()
    with purge_cols[1]:
        if st.button(t("admin_purge_anon", lang), key="admin_purge_anon"):
            n = supabase_client.purge_anonymous_users()
            st.success(t("admin_purge_anon_ok", lang, n=n))
            st.rerun()
    with purge_cols[2]:
        if st.button(
            t("admin_purge_empty", lang),
            key="admin_purge_empty_profile",
            type="primary",
        ):
            n = supabase_client.purge_users_without_profile()
            st.success(t("admin_purge_empty_ok", lang, n=n))
            st.rerun()

    users: List[Dict] = supabase_client.list_users()
    # 二次保险：前端再滤一次
    users = [
        u for u in users
        if u.get("app_id") == getattr(supabase_client, "app_id", "sigma_fate_v1")
        and u.get("user_id")
    ]
    if getattr(supabase_client, "last_error", None):
        err = supabase_client.last_error
        if "已隔离丢弃" in str(err):
            st.warning(err)
        else:
            st.error(t("admin_read_fail", lang, err=err))
            st.info(t("admin_sql_hint", lang))

    empty_n = sum(
        1 for u in users
        if not str(u.get("display_name") or "").strip() and not u.get("birth_date")
    )
    if empty_n:
        st.warning(t("admin_empty_warn", lang, n=empty_n))

    paid = [
        u
        for u in users
        if u.get("subscription_tier") in ("silver", "gold", "diamond", "monthly", "quarterly", "annual", "pro")
    ]
    free = [u for u in users if u.get("subscription_tier", "free") == "free"]
    configured = [u for u in users if u.get("email")]
    profiled = [
        u for u in users
        if str(u.get("display_name") or "").strip() or u.get("birth_date")
    ]

    st.markdown(f"### 📊 {t('sys_stats', lang)}")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(t("total_users", lang), len(users))
    c2.metric(t("admin_with_profile", lang), len(profiled))
    c3.metric(t("paid_users", lang), len(paid))
    c4.metric(t("free_users", lang), len(free))
    c5.metric(t("configured_users", lang), len(configured))

    show_all = st.checkbox(
        t("admin_show_all", lang),
        value=False,
        key="admin_show_all_users",
    )
    view_users = users if show_all else profiled
    if not show_all and len(profiled) < len(users):
        st.caption(
            t("admin_show_all_caption", lang, shown=len(profiled), total=len(users))
        )

    st.markdown("---")
    st.markdown(f"### 📋 {t('user_list', lang)}")

    if not view_users:
        st.info(
            t("no_users", lang)
            if not users
            else t("admin_no_profiled", lang)
        )
        if not users:
            return
        # 仍允许在全部模式下管理；若默认空但 users 非空，用全部继续选用户
        view_users = users

    table_rows = []
    for u in view_users:
        table_rows.append(
            {
                t("email_col", lang): u.get("email") or "-",
                t("admin_col_name", lang): u.get("display_name") or "-",
                t("admin_col_birthday", lang): _safe_date(u.get("birth_date")),
                t("admin_col_birth_time", lang): _format_birth_time(u),
                t("admin_col_birth_place", lang): _format_birth_location(u, lang),
                t("subscription_col", lang): u.get("subscription_tier", "free"),
                t("trials_col", lang): u.get("free_trials_remaining", 5),
                t("expires_col", lang): _safe_date(u.get("subscription_expires_at")),
                t("created_col", lang): _safe_date(u.get("created_at")),
                t("last_login_col", lang): _safe_date(u.get("last_login_at")),
                t("email_confirmed_col", lang): "✅" if u.get("email_confirmed") else "—",
            }
        )
    st.dataframe(table_rows, use_container_width=True, hide_index=True, height=360)

    # 选择用户（编辑时用完整列表）
    manage_users = users
    options = [
        f"{u.get('email') or u.get('user_id')}|{u.get('user_id')}" for u in manage_users
    ]
    labels = [o.split("|")[0] for o in options]
    selected_label = st.selectbox(t("select_user", lang), labels, key="admin_select_user")
    selected_user = next(
        (
            u
            for u, lab in zip(manage_users, labels)
            if lab == selected_label
        ),
        None,
    )
    if not selected_user:
        return

    st.caption(f"{t('current_user', lang)}: {selected_user.get('email') or selected_user.get('user_id')}")

    st.markdown(f"#### 📍 {t('admin_birth_profile', lang)}")
    bc1, bc2, bc3, bc4 = st.columns(4)
    bc1.metric(t("admin_col_name", lang), selected_user.get("display_name") or "-")
    bc2.metric(t("admin_col_birthday", lang), _safe_date(selected_user.get("birth_date")))
    bc3.metric(t("admin_col_time", lang), _format_birth_time(selected_user))
    bc4.metric(t("admin_col_gender", lang), selected_user.get("gender") or "-")
    st.caption(
        t("admin_birth_place_label", lang) + _format_birth_location(selected_user, lang)
    )

    st.markdown("---")
    st.markdown(f"### 📝 {t('edit_subscription', lang)}")
    col_a, col_b = st.columns(2)
    tiers = ["free", "silver", "gold", "diamond", "monthly", "quarterly", "annual"]
    cur_tier = selected_user.get("subscription_tier", "free")
    with col_a:
        new_tier = st.selectbox(
            t("set_subscription", lang),
            tiers,
            index=tiers.index(cur_tier) if cur_tier in tiers else 0,
            key="admin_tier_select",
        )
        if st.button(t("update_subscription", lang), key="admin_update_tier", use_container_width=True):
            expires = None
            if new_tier in ("monthly", "quarterly", "annual"):
                days = {"monthly": 30, "quarterly": 90, "annual": 365}[new_tier]
                expires = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"
            ok = supabase_client.admin_update_user(
                selected_user["user_id"],
                subscription_tier=new_tier,
                subscription_expires_at=expires,
            )
            st.success(t("update_ok", lang)) if ok else st.error(t("update_fail", lang))
            if ok:
                st.rerun()
    with col_b:
        trials_val = int(selected_user.get("free_trials_remaining") or 5)
        new_trials = st.number_input(
            t("set_trials", lang),
            min_value=0,
            max_value=9999,
            value=trials_val,
            key="admin_trials_input",
        )
        if st.button(t("reset_trials", lang), key="admin_reset_trials", use_container_width=True):
            ok = supabase_client.admin_update_user(
                selected_user["user_id"],
                free_trials_remaining=int(new_trials),
            )
            st.success(t("reset_ok", lang)) if ok else st.error(t("update_fail", lang))
            if ok:
                st.rerun()

    st.markdown("---")
    st.markdown(f"### ⚙️ {t('actions', lang)}")
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button(f"📧 {t('send_reset_email', lang)}", key="admin_send_reset", use_container_width=True):
            st.info(t("reset_email_na", lang))
    with b2:
        if st.button(f"🗑 {t('delete_user', lang)}", key="admin_delete_user", use_container_width=True):
            ok = supabase_client.admin_delete_user(selected_user["user_id"])
            st.success(t("delete_ok", lang)) if ok else st.error(t("delete_fail", lang))
            if ok:
                st.rerun()
    with b3:
        if st.button(f"🔄 {t('refresh_data', lang)}", key="admin_refresh", use_container_width=True):
            st.rerun()

    st.markdown("---")
    st.markdown(f"### 📋 {t('admin_survey_responses', lang)}")
    surveys = supabase_client.list_survey_responses(limit=200) if supabase_client else []
    if not surveys:
        st.caption(t("admin_survey_empty", lang))
    else:
        srows = survey_rows_for_admin(surveys, lang)
        st.dataframe(srows, use_container_width=True, hide_index=True, height=280)
        with st.expander(t("admin_survey_full", lang), expanded=False):
            for r in surveys[:30]:
                st.markdown(
                    f"**{str(r.get('created_at') or '')[:10]}** · "
                    f"{r.get('email') or '-'} · {r.get('background') or '-'}"
                )
                st.write(r.get("open_feedback") or "—")
                st.markdown("---")

    with st.expander(t("admin_export_template", lang), expanded=False):
        st.markdown(t("admin_export_template_body", lang))
        doc_dir = Path(__file__).resolve().parent / "docs"
        qpath = doc_dir / "trial_questionnaire_zh_hant.md"
        csvpath = doc_dir / "trial_questionnaire_table.csv"
        if qpath.is_file():
            st.download_button(
                t("admin_download_md", lang),
                data=qpath.read_text(encoding="utf-8"),
                file_name="sigma_fate_trial_questionnaire.md",
                mime="text/markdown",
                key="admin_download_questionnaire",
            )
        if csvpath.is_file():
            st.download_button(
                t("admin_download_csv", lang),
                data=csvpath.read_text(encoding="utf-8-sig"),
                file_name="sigma_fate_trial_questionnaire.csv",
                mime="text/csv",
                key="admin_download_questionnaire_csv",
            )

    st.markdown("---")
    st.markdown(f"### 🔁 {t('bulk_ops', lang)}")
    bb1, bb2 = st.columns(2)
    with bb1:
        if st.button(t("reset_all_free", lang), key="admin_reset_all", use_container_width=True):
            n = supabase_client.admin_reset_free_trials(5)
            st.success(f"{t('reset_all_ok', lang)} ({n})")
            st.rerun()
    with bb2:
        csv_buf = io.StringIO()
        writer = csv.DictWriter(
            csv_buf,
            fieldnames=list(table_rows[0].keys()) if table_rows else [],
        )
        if table_rows:
            writer.writeheader()
            writer.writerows(table_rows)
        st.download_button(
            t("export_csv", lang),
            data=csv_buf.getvalue().encode("utf-8-sig"),
            file_name=f"sigma_fate_users_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
            key="admin_export_csv",
        )
