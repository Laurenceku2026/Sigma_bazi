"""管理员登录与用户管理页面（参考 Horse racing / TechLife portal）。"""
from __future__ import annotations

import csv
import hmac
import io
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import streamlit as st

from ui_texts import t


def _safe_date(value: Any) -> str:
    if not value:
        return "-"
    s = str(value)
    return s[:10] if len(s) >= 10 else s


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

    st.caption(f"schema=`{supabase_client.schema}` · app_id=`{supabase_client.app_id}`")
    users: List[Dict] = supabase_client.list_users()
    if getattr(supabase_client, "last_error", None):
        st.error(f"读取用户失败：{supabase_client.last_error}")
        st.info(
            "请确认：1) 已执行 sql/001 与 002；2) API Exposed schemas 含 app_sigma_fate；"
            "3) Secrets 中 SUPABASE_STOCK_URL 与 SERVICE_ROLE 属于同一项目。"
            if lang == "zh"
            else "Check SQL migration, exposed schema app_sigma_fate, and matching Supabase URL/key."
        )

    paid = [
        u
        for u in users
        if u.get("subscription_tier") in ("silver", "gold", "diamond", "monthly", "quarterly", "annual", "pro")
    ]
    free = [u for u in users if u.get("subscription_tier", "free") == "free"]
    configured = [u for u in users if u.get("email")]

    st.markdown(f"### 📊 {t('sys_stats', lang)}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("total_users", lang), len(users))
    c2.metric(t("paid_users", lang), len(paid))
    c3.metric(t("free_users", lang), len(free))
    c4.metric(t("configured_users", lang), len(configured))

    st.markdown("---")
    st.markdown(f"### 📋 {t('user_list', lang)}")

    if not users:
        st.info(t("no_users", lang))
        return

    table_rows = []
    for u in users:
        table_rows.append(
            {
                t("email_col", lang): u.get("email") or "-",
                t("subscription_col", lang): u.get("subscription_tier", "free"),
                t("trials_col", lang): u.get("free_trials_remaining", 30),
                t("expires_col", lang): _safe_date(u.get("subscription_expires_at")),
                t("created_col", lang): _safe_date(u.get("created_at")),
                t("last_login_col", lang): _safe_date(u.get("last_login_at")),
                t("email_confirmed_col", lang): "✅" if u.get("email_confirmed") else "—",
            }
        )
    st.dataframe(table_rows, use_container_width=True, hide_index=True, height=360)

    # 选择用户
    options = [
        f"{u.get('email') or u.get('user_id')}|{u.get('user_id')}" for u in users
    ]
    labels = [o.split("|")[0] for o in options]
    selected_label = st.selectbox(t("select_user", lang), labels, key="admin_select_user")
    selected_user = next(
        (
            u
            for u, lab in zip(users, labels)
            if lab == selected_label
        ),
        None,
    )
    if not selected_user:
        return

    st.caption(f"{t('current_user', lang)}: {selected_user.get('email') or selected_user.get('user_id')}")

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
        trials_val = int(selected_user.get("free_trials_remaining") or 30)
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
    st.markdown(f"### 🔁 {t('bulk_ops', lang)}")
    bb1, bb2 = st.columns(2)
    with bb1:
        if st.button(t("reset_all_free", lang), key="admin_reset_all", use_container_width=True):
            n = supabase_client.admin_reset_free_trials(30)
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
