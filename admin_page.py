"""管理员登录与用户管理页面（参考 Horse racing / TechLife portal）。"""
from __future__ import annotations

import csv
import hmac
import io
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

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
        f"🔒 本页只管理本 App 表 **`sf_users`**（`{supabase_client.schema}` / `{supabase_client.app_id}`）。\n\n"
        f"- 列表里「无姓名无生日」的邮箱，多半是以前无密码注册/试登留下的，**可以删**。\n"
        f"- 删除这里的行 **不会** 删除赛马 App / 门户的账号，也 **不会** 删掉 Supabase Auth 的总账号；"
        f"只是本八字 App 看不到他们。\n"
        f"- 推荐：点「只保留有资料用户」清掉空行，或下方逐个删除。"
        if lang == "zh"
        else f"🔒 Managing `sf_users` only. Deleting rows here does NOT remove Horse racing / portal Auth accounts."
    )
    st.caption(
        f"table=`{getattr(supabase_client, 'USER_TABLE', 'sf_users')}` · "
        f"schema=`{supabase_client.schema}` · app_id=`{supabase_client.app_id}`"
    )

    purge_cols = st.columns(3)
    with purge_cols[0]:
        if st.button(
            "🧹 清理非本 App 脏数据" if lang == "zh" else "🧹 Purge foreign rows",
            key="admin_purge_foreign",
        ):
            n = supabase_client.purge_foreign_users()
            st.success(f"已清理 {n} 条" if lang == "zh" else f"Purged {n} rows")
            st.rerun()
    with purge_cols[1]:
        if st.button(
            "🧹 删除无邮箱匿名用户" if lang == "zh" else "🧹 Delete anonymous (no email)",
            key="admin_purge_anon",
        ):
            n = supabase_client.purge_anonymous_users()
            st.success(f"已删除 {n} 条匿名用户" if lang == "zh" else f"Deleted {n} anon rows")
            st.rerun()
    with purge_cols[2]:
        if st.button(
            "🗑 只保留有资料用户（删空行）" if lang == "zh" else "🗑 Keep profiled users only",
            key="admin_purge_empty_profile",
            type="primary",
        ):
            n = supabase_client.purge_users_without_profile()
            st.success(
                f"已删除 {n} 个无姓名无生日的空用户，已排盘用户保留"
                if lang == "zh"
                else f"Deleted {n} empty-profile users"
            )
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
            st.error(f"读取用户失败：{err}")
            st.info(
                "请确认：1) 已执行 sql/001～006；2) Exposed schemas 含 app_sigma_fate；"
                "3) Secrets 中 URL 与 service_role 属同一项目。"
                if lang == "zh"
                else "Check SQL, exposed schema, and matching Supabase URL/key."
            )

    empty_n = sum(
        1 for u in users
        if not str(u.get("display_name") or "").strip() and not u.get("birth_date")
    )
    if empty_n:
        st.warning(
            f"当前有 **{empty_n}** 个仅邮箱、无排盘资料的用户（例如测试邮箱）。"
            f"点击上方「只保留有资料用户」可一次删掉；或在 Supabase 跑 `sql/006_purge_empty_profile_users.sql`。"
            if lang == "zh"
            else f"{empty_n} email-only empty profiles. Use Keep profiled users only."
        )

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
    c2.metric("有资料" if lang == "zh" else "With profile", len(profiled))
    c3.metric(t("paid_users", lang), len(paid))
    c4.metric(t("free_users", lang), len(free))
    c5.metric(t("configured_users", lang), len(configured))

    show_all = st.checkbox(
        "显示全部（含无资料空行）" if lang == "zh" else "Show all (incl. empty profiles)",
        value=False,
        key="admin_show_all_users",
    )
    view_users = users if show_all else profiled
    if not show_all and len(profiled) < len(users):
        st.caption(
            f"默认只显示有姓名/生日的用户（{len(profiled)}/{len(users)}）。勾选上方可看全部。"
            if lang == "zh"
            else f"Showing profiled users only ({len(profiled)}/{len(users)})."
        )

    st.markdown("---")
    st.markdown(f"### 📋 {t('user_list', lang)}")

    if not view_users:
        st.info(
            t("no_users", lang)
            if not users
            else ("暂无已排盘用户；请勾选「显示全部」或先在 App 排盘。" if lang == "zh" else "No profiled users yet.")
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
                ("姓名" if lang == "zh" else "Name"): u.get("display_name") or "-",
                ("生日" if lang == "zh" else "Birthday"): _safe_date(u.get("birth_date")),
                ("出生时间" if lang == "zh" else "Birth time"): _format_birth_time(u),
                ("出生地点" if lang == "zh" else "Birth place"): _format_birth_location(u, lang),
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

    st.markdown("#### 📍 " + ("出生资料" if lang == "zh" else "Birth profile"))
    bc1, bc2, bc3, bc4 = st.columns(4)
    bc1.metric("姓名" if lang == "zh" else "Name", selected_user.get("display_name") or "-")
    bc2.metric("生日" if lang == "zh" else "Date", _safe_date(selected_user.get("birth_date")))
    bc3.metric("时间" if lang == "zh" else "Time", _format_birth_time(selected_user))
    bc4.metric("性别" if lang == "zh" else "Gender", selected_user.get("gender") or "-")
    st.caption(
        ("出生地点：" if lang == "zh" else "Birth place: ")
        + _format_birth_location(selected_user, lang)
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
    st.markdown("### 📋 " + ("試用問卷（發給測試者）" if lang == "zh" else "Trial questionnaire"))
    with st.expander("查看 10 題問卷摘要" if lang == "zh" else "View 10-question summary", expanded=False):
        st.markdown(
            """
1. 首次註冊與排盤體驗  
2. 命盤準確度與信任感（1–5）  
3. DFSS × 八字概念是否清楚  
4. 專業段 vs 白話段哪個更有用  
5. 事業/財運/感情/健康哪類最有價值  
6. 報告生成速度與穩定性  
7. 介面語言與手機體驗  
8. 免費預覽 vs 付費會員意願  
9. 推薦意願 NPS（0–10）  
10. 最重要的一項改進建議（開放題）
            """.strip()
        )
        qpath = Path(__file__).resolve().parent / "docs" / "trial_questionnaire_zh_hant.md"
        if qpath.is_file():
            st.download_button(
                "📥 下載完整問卷（Markdown）" if lang == "zh" else "📥 Download questionnaire (MD)",
                data=qpath.read_text(encoding="utf-8"),
                file_name="sigma_fate_trial_questionnaire.md",
                mime="text/markdown",
                key="admin_download_questionnaire",
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
