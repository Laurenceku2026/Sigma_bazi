"""管理员登录与用户管理页面（参考 Horse racing / TechLife portal）。"""
from __future__ import annotations

import csv
import hmac
import io
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import streamlit as st

from trial_survey import survey_rows_for_admin
from ui_texts import region_label, t


def _safe_date(value: Any) -> str:
    if not value:
        return "-"
    s = str(value)
    return s[:10] if len(s) >= 10 else s


def _to_beijing(dt: datetime) -> datetime:
    """转为北京时间（Asia/Shanghai）。"""
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("Asia/Shanghai")
    except Exception:
        tz = timezone(timedelta(hours=8), name="CST")
    if dt.tzinfo is None:
        # 库内多为 UTC naive / 带 Z 解析后的 aware
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz)


def _parse_expires_date(value: Any) -> Optional[date]:
    """从用户 subscription_expires_at 解析出日期（按北京时间日历日）。"""
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            dt = value
        else:
            s = str(value).strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
        return _to_beijing(dt).date()
    except Exception:
        s = str(value)
        if len(s) >= 10:
            try:
                return date.fromisoformat(s[:10])
            except Exception:
                return None
        return None


def _expires_end_of_day_utc_iso(d: date) -> str:
    """到期日按北京时间当天 23:59:59，存 UTC ISO。"""
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("Asia/Shanghai")
    except Exception:
        tz = timezone(timedelta(hours=8))
    local_end = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=tz)
    return local_end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_datetime(value: Any) -> str:
    """显示北京时间日期+时间，如 2026-07-16 18:53。"""
    if not value:
        return "-"
    dt: datetime | None = None
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip()
        if not s:
            return "-"
        try:
            normalized = s.replace("Z", "+00:00")
            if "T" in normalized or (len(normalized) >= 19 and " " in normalized[:20]):
                dt = datetime.fromisoformat(normalized)
        except Exception:
            dt = None
        if dt is None and len(s) >= 16:
            try:
                dt = datetime.fromisoformat(s[:19].replace(" ", "T"))
            except Exception:
                return s[:16].replace("T", " ")
        if dt is None:
            return s[:10] if len(s) >= 10 else s
    try:
        return _to_beijing(dt).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt.strftime("%Y-%m-%d %H:%M")


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


def _admin_birth_info(user: Dict[str, Any]) -> Dict[str, Any]:
    """拼出可排盘/展示用的 birth_info（优先 last_birth_info，再补用户表字段）。"""
    info = dict(_birth_info_fallback(user))
    if user.get("display_name") and not info.get("name"):
        info["name"] = user["display_name"]
    if user.get("gender") and not info.get("gender"):
        info["gender"] = user["gender"]
    if user.get("birth_date") and not info.get("birth_date"):
        info["birth_date"] = str(user["birth_date"])[:10]
    if user.get("birth_hour") is not None and info.get("birth_hour") is None:
        info["birth_hour"] = user["birth_hour"]
    if user.get("birth_minute") is not None and info.get("birth_minute") is None:
        info["birth_minute"] = user["birth_minute"]
    if user.get("region_id") and not info.get("region_id"):
        info["region_id"] = user["region_id"]
    if user.get("birth_place") is not None and info.get("birth_place") is None:
        info["birth_place"] = user["birth_place"]
    if user.get("email"):
        info["email"] = user["email"]
    return info


def _admin_recompute_bazi(birth_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """按出生资料现算命盘。"""
    if not birth_info or not birth_info.get("birth_date"):
        return None
    try:
        from bazi_engine import BaziEngine
        from ui_texts import region_longitude

        bd = birth_info.get("birth_date")
        if isinstance(bd, str):
            bd = date.fromisoformat(bd[:10])
        elif not isinstance(bd, date):
            return None
        region_id = birth_info.get("region_id") or "huabei"
        engine = BaziEngine(
            year=bd.year,
            month=bd.month,
            day=bd.day,
            hour=int(birth_info.get("birth_hour") or 12),
            minute=int(birth_info.get("birth_minute") or 0),
            gender=birth_info.get("gender") or "男",
            true_solar_time=bool(birth_info.get("use_true_solar", True)),
            longitude=region_longitude(region_id),
        )
        return engine.calculate().get_summary()
    except Exception:
        return None


def _admin_serialize_birth_info(birth_info: Dict[str, Any]) -> Dict[str, Any]:
    """写入数据库前规范化 birth_info。"""
    bi = dict(birth_info or {})
    bd = bi.get("birth_date")
    if isinstance(bd, date):
        bi["birth_date"] = bd.isoformat()
    elif bd is not None:
        bi["birth_date"] = str(bd)[:10]
    for key in ("birth_hour", "birth_minute"):
        if bi.get(key) is not None:
            try:
                bi[key] = int(bi[key])
            except (TypeError, ValueError):
                pass
    return bi


def _admin_build_local_report(
    bazi_data: Dict[str, Any],
    birth_info: Dict[str, Any],
    *,
    tier: str,
    lang: str,
) -> Dict[str, Any]:
    from report_local import build_local_report

    return build_local_report(
        bazi_data,
        _admin_serialize_birth_info(birth_info),
        include_liunian=(tier or "free") != "silver",
        lang=lang,
    )


def _admin_save_chart_and_report(
    supabase_client: Any,
    *,
    user_id: str,
    birth_info: Dict[str, Any],
    bazi_data: Dict[str, Any],
    report_content: Dict[str, Any],
    tier: str,
) -> bool:
    """管理员保存现算命盘 + 本地报告到 reports，并同步出生资料。"""
    bi = _admin_serialize_birth_info(birth_info)
    try:
        supabase_client.save_user_profile(user_id, bi)
    except Exception:
        pass
    try:
        saved = supabase_client.save_report(
            user_id,
            bi,
            bazi_data,
            report_content,
            payment_tier=tier or "free",
        )
        return bool(saved)
    except Exception:
        return False


def _admin_maybe_json_dict(value: Any) -> Optional[Dict[str, Any]]:
    if isinstance(value, dict):
        return value if value else None
    if isinstance(value, str) and value.strip():
        try:
            import json

            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) and parsed else None
        except Exception:
            return None
    return None


@contextmanager
def _admin_preview_session(
    *,
    birth_info: Optional[Dict[str, Any]],
    bazi_data: Optional[Dict[str, Any]],
) -> Iterator[None]:
    """临时写入 birth_info（命盘标题名）后还原，避免污染管理员自己的会话。"""
    keys = ("birth_info", "bazi_data")
    backup = {k: st.session_state.get(k) for k in keys}
    try:
        st.session_state.birth_info = birth_info
        st.session_state.bazi_data = bazi_data
        yield
    finally:
        for k, v in backup.items():
            st.session_state[k] = v


def _admin_page_labels(lang: str) -> List[str]:
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
    if lang == "en":
        return [
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
    if lang == "zh_hant":
        try:
            from zh_convert import to_traditional

            return [to_traditional(x) for x in labels_zh]
        except Exception:
            return labels_zh
    return labels_zh


def _admin_render_report_pages(
    report: Dict[str, Any],
    *,
    lang: str,
    bazi_data: Optional[Dict[str, Any]],
    pages: range,
) -> None:
    """管理员只读渲染报告页（不依赖 app.py，避免 Streamlit 主脚本循环导入）。"""
    from report_generator import ReportGenerator

    labels = _admin_page_labels(lang)
    legacy_ln9 = ReportGenerator.is_legacy_liunian_page9(report)
    core_mode = 1 in pages and len(list(pages)) > 1

    for i in pages:
        if i == 9 and legacy_ln9 and core_mode:
            continue
        pk = f"page{i}"
        lab = labels[i - 1] if i <= len(labels) else pk
        page_obj = report.get(pk) if isinstance(report, dict) else None
        if isinstance(page_obj, dict) and page_obj.get("quarters"):
            lab = labels[9] if len(labels) > 9 else lab
        with st.expander(lab, expanded=(i == pages.start)):
            if pk not in report:
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
            html = ReportGenerator.render_page_html(page, lang)
            if i == 1 and bazi_data:
                try:
                    from bazi_analysis import render_personality_html

                    html = render_personality_html(bazi_data, lang) + html
                except Exception:
                    pass
            st.markdown(html, unsafe_allow_html=True)


def _admin_resolve_user_bazi(
    user: Dict[str, Any],
    supabase_client: Any,
) -> tuple[Optional[Dict[str, Any]], Dict[str, Any], str]:
    """返回 (bazi_data, birth_info, display_name)。优先存档命盘，否则现算。"""
    birth_info = _admin_birth_info(user)
    name = (
        str(birth_info.get("name") or "").strip()
        or str(user.get("display_name") or "").strip()
        or str(user.get("email") or "").split("@")[0]
        or "User"
    )
    uid = user.get("user_id")
    bazi_data = None
    if uid and supabase_client:
        try:
            reports = supabase_client.get_reports(uid, limit=1) or []
        except Exception:
            reports = []
        if reports:
            bazi_data = _admin_maybe_json_dict(reports[0].get("bazi_data"))
            bi = reports[0].get("birth_info")
            if isinstance(bi, dict) and bi:
                merged = dict(bi)
                for k, v in birth_info.items():
                    if k not in merged or merged.get(k) in (None, ""):
                        merged[k] = v
                birth_info = merged
                if birth_info.get("name"):
                    name = str(birth_info["name"])
    if bazi_data is None:
        bazi_data = _admin_recompute_bazi(birth_info)
    return bazi_data, birth_info, name


def _admin_person_form(prefix: str, lang: str, *, defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """管理员手动输入一方出生资料（独立 key，不与用户合婚页冲突）。"""
    from ui_texts import region_options

    defaults = defaults or {}
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input(
            t("name", lang),
            value=str(defaults.get("name") or ""),
            key=f"admin_match_{prefix}_name",
        )
        gender_opts = [t("male", lang), t("female", lang)]
        g_raw = str(defaults.get("gender") or "男")
        g_idx = 1 if g_raw.startswith("女") or g_raw.lower() in ("female", "f") else 0
        gender_ui = st.radio(
            t("gender", lang),
            options=gender_opts,
            index=g_idx,
            horizontal=True,
            key=f"admin_match_{prefix}_gender",
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
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            format="YYYY-MM-DD",
            key=f"admin_match_{prefix}_date",
        )
    with c2:
        birth_hour = st.number_input(
            t("birth_hour", lang),
            0,
            23,
            int(defaults.get("birth_hour") or 12),
            key=f"admin_match_{prefix}_hour",
        )
        birth_minute = st.number_input(
            t("birth_minute", lang),
            0,
            59,
            int(defaults.get("birth_minute") or 0),
            key=f"admin_match_{prefix}_minute",
        )
        reg_labels, reg_ids, _ = region_options(lang)
        try:
            reg_default = (
                reg_ids.index(defaults.get("region_id"))
                if defaults.get("region_id") in reg_ids
                else 2
            )
        except Exception:
            reg_default = 2
        reg_idx = st.selectbox(
            t("region", lang),
            options=list(range(len(reg_ids))),
            format_func=lambda i: reg_labels[i],
            index=reg_default,
            key=f"admin_match_{prefix}_region",
        )
        region_id = reg_ids[reg_idx]
    use_true_solar = st.checkbox(
        t("true_solar", lang),
        value=bool(defaults.get("use_true_solar", True)),
        key=f"admin_match_{prefix}_solar",
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


def render_admin_user_results(
    lang: str,
    supabase_client: Any,
    selected_user: Dict[str, Any],
) -> None:
    """管理员查看所选用户的命盘、八字报告、流年报告。"""
    from report_generator import ReportGenerator
    from utils import render_bazi_chart

    st.caption(t("admin_user_results_hint", lang))
    st.caption(t("admin_how_reports_saved", lang))

    uid = selected_user.get("user_id")
    if not uid or not supabase_client:
        st.warning(t("admin_user_results_unavailable", lang))
        return

    reports: List[Dict[str, Any]] = []
    try:
        reports = supabase_client.get_reports(uid, limit=10) or []
    except Exception as e:
        st.error(t("admin_read_fail", lang, err=str(e)))
        return

    birth_info = _admin_birth_info(selected_user)
    selected_report: Optional[Dict[str, Any]] = None
    if reports:
        labels = []
        for r in reports:
            created = _safe_datetime(r.get("created_at"))
            rid = str(r.get("report_id") or "")[:8]
            tier = r.get("payment_tier") or "-"
            labels.append(f"{created} · {tier} · {rid}")
        pick = st.selectbox(
            t("admin_select_report", lang),
            options=list(range(len(reports))),
            format_func=lambda i: labels[i],
            key=f"admin_report_pick_{uid}",
        )
        selected_report = reports[int(pick)]
        if isinstance(selected_report.get("birth_info"), dict) and selected_report["birth_info"]:
            merged = dict(selected_report["birth_info"])
            for k, v in birth_info.items():
                if k not in merged or merged.get(k) in (None, ""):
                    merged[k] = v
            birth_info = merged
        st.success(
            t(
                "admin_report_loaded",
                lang,
                n=len(reports),
                when=_safe_datetime(selected_report.get("created_at")),
            )
        )
    else:
        st.info(t("admin_no_saved_report", lang))

    bazi_data = None
    report_content = None
    if selected_report:
        bazi_data = _admin_maybe_json_dict(selected_report.get("bazi_data"))
        report_content = _admin_maybe_json_dict(selected_report.get("report_content"))

    override_key = f"admin_bazi_override_{uid}"
    report_override_key = f"admin_report_override_{uid}"
    view_key = f"admin_view_mode_{uid}"
    tier = str(selected_user.get("subscription_tier") or "free")
    can_recompute = bool(birth_info.get("birth_date"))

    c_recompute, c_save, c_tip = st.columns([1, 1, 2])
    with c_recompute:
        if st.button(
            t("admin_recompute_chart", lang),
            key=f"admin_recompute_btn_{uid}",
            use_container_width=True,
            disabled=not can_recompute,
            type="primary",
        ):
            computed = _admin_recompute_bazi(birth_info)
            if computed:
                try:
                    local_report = _admin_build_local_report(
                        computed, birth_info, tier=tier, lang=lang
                    )
                except Exception:
                    local_report = None
                st.session_state[override_key] = computed
                if local_report:
                    st.session_state[report_override_key] = local_report
                st.session_state[view_key] = "chart"
                st.session_state["_admin_recompute_flash"] = uid
                st.rerun()
            else:
                st.error(t("admin_recompute_fail", lang))

    # 优先用现算覆盖
    if override_key in st.session_state:
        bazi_data = st.session_state[override_key]
    elif bazi_data is None and can_recompute:
        bazi_data = _admin_recompute_bazi(birth_info)

    if report_override_key in st.session_state:
        report_content = st.session_state[report_override_key]

    with c_save:
        can_save = bool(bazi_data and can_recompute)
        if st.button(
            t("admin_save_chart", lang),
            key=f"admin_save_chart_btn_{uid}",
            use_container_width=True,
            disabled=not can_save,
            type="secondary",
        ):
            try:
                to_save_report = report_content or _admin_build_local_report(
                    bazi_data, birth_info, tier=tier, lang=lang
                )
            except Exception as e:
                st.error(t("admin_render_fail", lang, err=str(e)))
                to_save_report = None
            if to_save_report and _admin_save_chart_and_report(
                supabase_client,
                user_id=uid,
                birth_info=birth_info,
                bazi_data=bazi_data,
                report_content=to_save_report,
                tier=tier,
            ):
                st.session_state.pop(override_key, None)
                st.session_state.pop(report_override_key, None)
                st.session_state[view_key] = "chart"
                st.session_state["_admin_save_flash"] = uid
                st.rerun()
            else:
                st.error(t("admin_save_chart_fail", lang))

    with c_tip:
        if st.session_state.get("_admin_save_flash") == uid:
            st.session_state.pop("_admin_save_flash", None)
            st.success(t("admin_save_chart_ok", lang))
        elif st.session_state.get("_admin_recompute_flash") == uid:
            st.session_state.pop("_admin_recompute_flash", None)
            st.success(t("admin_recompute_ok", lang))
        elif not can_recompute:
            st.caption(t("admin_recompute_need_birth", lang))
        elif override_key in st.session_state:
            st.caption(t("admin_bazi_using_recomputed", lang))

    # 现算后强制落在命盘视图
    if view_key not in st.session_state:
        st.session_state[view_key] = "chart"

    view = st.radio(
        t("admin_view_mode", lang),
        options=["chart", "report", "liunian"],
        format_func=lambda k: {
            "chart": t("admin_tab_chart", lang),
            "report": t("admin_tab_report", lang),
            "liunian": t("admin_tab_liunian", lang),
        }.get(k, k),
        horizontal=True,
        key=view_key,
    )

    try:
        if view == "chart":
            if not bazi_data:
                st.info(t("admin_no_chart", lang))
            else:
                st.markdown(f"#### 📊 {t('admin_tab_chart', lang)}")
                with _admin_preview_session(
                    birth_info=birth_info or None,
                    bazi_data=bazi_data,
                ):
                    render_bazi_chart(bazi_data, lang)
        elif view == "report":
            if not report_content:
                st.info(t("admin_no_report", lang))
            else:
                _admin_render_report_pages(
                    report_content,
                    lang=lang,
                    bazi_data=bazi_data,
                    pages=range(1, 10),
                )
        else:
            if not report_content:
                st.info(t("admin_no_report", lang))
            else:
                lk = ReportGenerator.resolve_liunian_key(report_content)
                if not lk:
                    st.info(t("admin_no_liunian", lang))
                else:
                    if bazi_data:
                        try:
                            from bazi_analysis import render_lifetime_fortune_html

                            st.markdown(
                                render_lifetime_fortune_html(bazi_data, lang),
                                unsafe_allow_html=True,
                            )
                        except Exception:
                            pass
                    idx = 10 if lk == "page10" else 9
                    _admin_render_report_pages(
                        report_content,
                        lang=lang,
                        bazi_data=bazi_data,
                        pages=range(idx, idx + 1),
                    )
    except Exception as e:
        st.error(t("admin_render_fail", lang, err=str(e)))


def render_admin_match(lang: str, supabase_client: Any, users: List[Dict[str, Any]]) -> None:
    """管理员：两人八字契合（同合婚八维，适用于婚姻/亲密/合作等关系参考）。"""
    from hehun import analyze_hehun, render_hehun_html

    st.caption(t("admin_match_intro", lang))

    if not users:
        st.info(t("no_users", lang))
        return

    def _label(u: Dict[str, Any]) -> str:
        name = str(u.get("display_name") or "").strip() or "-"
        email = str(u.get("email") or "").strip() or str(u.get("user_id") or "")[:8]
        return f"{name} · {email}"

    mode = st.radio(
        t("admin_match_mode", lang),
        options=["users", "manual"],
        format_func=lambda k: {
            "users": t("admin_match_mode_users", lang),
            "manual": t("admin_match_mode_manual", lang),
        }.get(k, k),
        horizontal=True,
        key="admin_match_mode",
    )

    name_a = name_b = ""
    bazi_a = bazi_b = None

    if mode == "users":
        c1, c2 = st.columns(2)
        with c1:
            idx_a = st.selectbox(
                t("admin_match_person_a", lang),
                options=list(range(len(users))),
                format_func=lambda i: _label(users[i]),
                key="admin_match_user_a",
            )
        with c2:
            idx_b = st.selectbox(
                t("admin_match_person_b", lang),
                options=list(range(len(users))),
                format_func=lambda i: _label(users[i]),
                index=min(1, len(users) - 1),
                key="admin_match_user_b",
            )
        user_a = users[int(idx_a)]
        user_b = users[int(idx_b)]
        if st.button(
            t("admin_match_run", lang),
            type="primary",
            use_container_width=True,
            key="admin_match_run_users",
        ):
            if user_a.get("user_id") == user_b.get("user_id"):
                st.warning(t("admin_match_same_user", lang))
            else:
                try:
                    bazi_a, _, name_a = _admin_resolve_user_bazi(user_a, supabase_client)
                    bazi_b, _, name_b = _admin_resolve_user_bazi(user_b, supabase_client)
                    if not bazi_a or not bazi_b:
                        st.error(t("admin_match_need_bazi", lang))
                    else:
                        result = analyze_hehun(bazi_a, bazi_b, lang)
                        st.session_state["admin_match_result"] = result
                        st.session_state["admin_match_bazi_a"] = bazi_a
                        st.session_state["admin_match_bazi_b"] = bazi_b
                        st.session_state["admin_match_names"] = {"a": name_a, "b": name_b}
                        st.rerun()
                except Exception as e:
                    st.error(t("admin_render_fail", lang, err=str(e)))
    else:
        st.markdown(f"#### {t('admin_match_person_a', lang)}")
        form_a = _admin_person_form("a", lang)
        st.markdown(f"#### {t('admin_match_person_b', lang)}")
        form_b = _admin_person_form("b", lang)
        if st.button(
            t("admin_match_run", lang),
            type="primary",
            use_container_width=True,
            key="admin_match_run_manual",
        ):
            if not form_a.get("name") or not form_b.get("name"):
                st.warning(t("admin_match_need_names", lang))
            else:
                try:
                    bazi_a = _admin_recompute_bazi(form_a)
                    bazi_b = _admin_recompute_bazi(form_b)
                    if not bazi_a or not bazi_b:
                        st.error(t("admin_match_need_bazi", lang))
                    else:
                        result = analyze_hehun(bazi_a, bazi_b, lang)
                        st.session_state["admin_match_result"] = result
                        st.session_state["admin_match_bazi_a"] = bazi_a
                        st.session_state["admin_match_bazi_b"] = bazi_b
                        st.session_state["admin_match_names"] = {
                            "a": form_a["name"],
                            "b": form_b["name"],
                        }
                        st.rerun()
                except Exception as e:
                    st.error(t("admin_render_fail", lang, err=str(e)))

    result = st.session_state.get("admin_match_result")
    if not result:
        return
    names = st.session_state.get("admin_match_names") or {}
    bazi_a = st.session_state.get("admin_match_bazi_a") or {}
    bazi_b = st.session_state.get("admin_match_bazi_b") or {}
    html = render_hehun_html(
        result,
        name_a=names.get("a") or "",
        name_b=names.get("b") or "",
        bazi_a=bazi_a,
        bazi_b=bazi_b,
        lang=lang,
    )
    st.markdown(html, unsafe_allow_html=True)


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

    if not view_users:
        st.info(
            t("no_users", lang)
            if not users
            else t("admin_no_profiled", lang)
        )
        if not users:
            return
        view_users = users

    manage_users = users

    def _user_option_label(u: Dict[str, Any]) -> str:
        name = str(u.get("display_name") or "").strip() or "-"
        email = str(u.get("email") or "").strip() or str(u.get("user_id") or "")[:8]
        return f"{name} · {email}"

    tab_mgmt, tab_results, tab_match, tab_feedback = st.tabs(
        [
            f"👥 {t('admin_tab_user_mgmt', lang)}",
            f"🔮 {t('admin_tab_user_results', lang)}",
            f"💞 {t('admin_tab_match', lang)}",
            f"📋 {t('admin_tab_feedback', lang)}",
        ]
    )

    # ========== Tab 1：用户管理 ==========
    with tab_mgmt:
        st.markdown(f"### 📋 {t('user_list', lang)}")
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
                    t("created_col", lang): _safe_datetime(u.get("created_at")),
                    t("last_login_col", lang): _safe_datetime(u.get("last_login_at")),
                    t("email_confirmed_col", lang): "✅" if u.get("email_confirmed") else "—",
                }
            )
        st.dataframe(table_rows, use_container_width=True, hide_index=True, height=360)

        selected_idx = st.selectbox(
            t("select_user", lang),
            options=list(range(len(manage_users))),
            format_func=lambda i: _user_option_label(manage_users[i]),
            key="admin_select_user_idx",
        )
        selected_user = manage_users[int(selected_idx)] if manage_users else None
        if not selected_user:
            st.warning(t("admin_user_results_unavailable", lang))
        else:
            st.caption(
                f"{t('current_user', lang)}: "
                f"{selected_user.get('email') or selected_user.get('user_id')} · "
                f"{t('last_login_col', lang)} {_safe_datetime(selected_user.get('last_login_at'))}"
            )

            st.markdown("---")
            st.markdown(f"### 📝 {t('edit_subscription', lang)}")
            col_a, col_b = st.columns(2)
            tiers = ["free", "silver", "gold", "diamond", "monthly", "quarterly", "annual"]
            cur_tier = selected_user.get("subscription_tier", "free")
            uid = selected_user["user_id"]
            cur_exp_raw = selected_user.get("subscription_expires_at")
            parsed_exp = _parse_expires_date(cur_exp_raw)
            default_exp = parsed_exp or (date.today() + timedelta(days=365))
            prev_uid = st.session_state.get("_admin_expires_uid")
            if prev_uid != uid:
                st.session_state["admin_no_expires"] = not bool(cur_exp_raw)
                st.session_state["admin_expires_date"] = default_exp
                st.session_state["_admin_expires_uid"] = uid

            with col_a:
                new_tier = st.selectbox(
                    t("set_subscription", lang),
                    tiers,
                    index=tiers.index(cur_tier) if cur_tier in tiers else 0,
                    key="admin_tier_select",
                )
                if st.button(
                    t("update_subscription", lang),
                    key="admin_update_tier",
                    use_container_width=True,
                ):
                    clear_exp = bool(st.session_state.get("admin_no_expires"))
                    exp_d = st.session_state.get("admin_expires_date")
                    kwargs: Dict[str, Any] = {"subscription_tier": new_tier}
                    if clear_exp:
                        kwargs["clear_subscription_expires"] = True
                    elif isinstance(exp_d, date):
                        kwargs["subscription_expires_at"] = _expires_end_of_day_utc_iso(exp_d)
                    elif new_tier in ("monthly", "quarterly", "annual"):
                        days = {"monthly": 30, "quarterly": 90, "annual": 365}[new_tier]
                        kwargs["subscription_expires_at"] = (
                            datetime.now(timezone.utc) + timedelta(days=days)
                        ).isoformat().replace("+00:00", "Z")
                    ok = supabase_client.admin_update_user(uid, **kwargs)
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
                if st.button(
                    t("reset_trials", lang),
                    key="admin_reset_trials",
                    use_container_width=True,
                ):
                    ok = supabase_client.admin_update_user(
                        uid,
                        free_trials_remaining=int(new_trials),
                    )
                    st.success(t("reset_ok", lang)) if ok else st.error(t("update_fail", lang))
                    if ok:
                        st.rerun()

            st.markdown(f"#### ⏳ {t('set_expires', lang)}")
            st.caption(t("set_expires_hint", lang))
            st.caption(f"{t('current_expires', lang)}：{_safe_datetime(cur_exp_raw)}")

            no_expires = st.checkbox(
                t("no_expires", lang),
                key="admin_no_expires",
            )
            exp_date = st.date_input(
                t("expires_date", lang),
                value=st.session_state.get("admin_expires_date") or default_exp,
                min_value=date(2020, 1, 1),
                max_value=date(2100, 12, 31),
                format="YYYY-MM-DD",
                disabled=bool(no_expires),
                key="admin_expires_date",
            )

            q1, q2, q3, q4 = st.columns(4)
            with q1:
                if st.button(
                    t("expires_quick_30", lang),
                    key="admin_exp_30",
                    use_container_width=True,
                    disabled=bool(no_expires),
                ):
                    st.session_state["admin_expires_date"] = date.today() + timedelta(days=30)
                    st.rerun()
            with q2:
                if st.button(
                    t("expires_quick_90", lang),
                    key="admin_exp_90",
                    use_container_width=True,
                    disabled=bool(no_expires),
                ):
                    st.session_state["admin_expires_date"] = date.today() + timedelta(days=90)
                    st.rerun()
            with q3:
                if st.button(
                    t("expires_quick_365", lang),
                    key="admin_exp_365",
                    use_container_width=True,
                    disabled=bool(no_expires),
                ):
                    st.session_state["admin_expires_date"] = date.today() + timedelta(days=365)
                    st.rerun()
            with q4:
                if st.button(
                    t("update_expires", lang),
                    key="admin_update_expires",
                    type="primary",
                    use_container_width=True,
                ):
                    if no_expires:
                        ok = supabase_client.admin_update_user(
                            uid, clear_subscription_expires=True
                        )
                    else:
                        d = exp_date if isinstance(exp_date, date) else default_exp
                        ok = supabase_client.admin_update_user(
                            uid,
                            subscription_expires_at=_expires_end_of_day_utc_iso(d),
                        )
                    st.success(t("update_ok", lang)) if ok else st.error(t("update_fail", lang))
                    if ok:
                        st.rerun()

            st.markdown("---")
            st.markdown(f"### ⚙️ {t('actions', lang)}")
            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button(
                    f"📧 {t('send_reset_email', lang)}",
                    key="admin_send_reset",
                    use_container_width=True,
                ):
                    st.info(t("reset_email_na", lang))
            with b2:
                if st.button(
                    f"🗑 {t('delete_user', lang)}",
                    key="admin_delete_user",
                    use_container_width=True,
                ):
                    ok = supabase_client.admin_delete_user(selected_user["user_id"])
                    st.success(t("delete_ok", lang)) if ok else st.error(t("delete_fail", lang))
                    if ok:
                        st.rerun()
            with b3:
                if st.button(
                    f"🔄 {t('refresh_data', lang)}",
                    key="admin_refresh",
                    use_container_width=True,
                ):
                    st.rerun()

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

    # ========== Tab 2：用户命盘与报告 ==========
    with tab_results:
        st.markdown(f"### 🔮 {t('admin_user_results', lang)}")
        st.caption(t("admin_user_results_howto", lang))
        if not manage_users:
            st.info(t("no_users", lang))
        else:
            selected_idx_r = st.selectbox(
                t("select_user", lang),
                options=list(range(len(manage_users))),
                format_func=lambda i: _user_option_label(manage_users[i]),
                key="admin_results_user_idx",
            )
            selected_user_r = manage_users[int(selected_idx_r)]
            st.caption(
                f"{t('current_user', lang)}: "
                f"{selected_user_r.get('email') or selected_user_r.get('user_id')} · "
                f"{t('last_login_col', lang)} {_safe_datetime(selected_user_r.get('last_login_at'))}"
            )
            st.markdown(f"#### 📍 {t('admin_birth_profile', lang)}")
            bc1, bc2, bc3, bc4 = st.columns(4)
            bc1.metric(t("admin_col_name", lang), selected_user_r.get("display_name") or "-")
            bc2.metric(t("admin_col_birthday", lang), _safe_date(selected_user_r.get("birth_date")))
            bc3.metric(t("admin_col_time", lang), _format_birth_time(selected_user_r))
            bc4.metric(t("admin_col_gender", lang), selected_user_r.get("gender") or "-")
            st.caption(
                t("admin_birth_place_label", lang)
                + _format_birth_location(selected_user_r, lang)
            )
            render_admin_user_results(lang, supabase_client, selected_user_r)

    # ========== Tab 3：八字契合 ==========
    with tab_match:
        st.markdown(f"### 💞 {t('admin_match_heading', lang)}")
        render_admin_match(lang, supabase_client, manage_users)

    # ========== Tab 4：用户反馈 ==========
    with tab_feedback:
        st.markdown(f"### 📋 {t('admin_survey_responses', lang)}")
        surveys = supabase_client.list_survey_responses(limit=200) if supabase_client else []
        if not surveys:
            st.caption(t("admin_survey_empty", lang))
        else:
            srows = survey_rows_for_admin(surveys, lang)
            st.dataframe(srows, use_container_width=True, hide_index=True, height=280)
            with st.expander(t("admin_survey_full", lang), expanded=False):
                from trial_survey import _bg_display

                for r in surveys[:30]:
                    st.markdown(
                        f"**{str(r.get('created_at') or '')[:10]}** · "
                        f"{r.get('email') or '-'} · {_bg_display(r.get('background'), lang)}"
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
