"""App 内试用问卷（15 题：5 专业 + 9 体验 + 1 开放）。"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from ui_texts import t

# (id, category, zh, en)
SURVEY_ITEMS: List[Tuple[str, str, str, str]] = [
    ("q1", "pro", "四柱排盘（年月日时）与您所知是否一致？", "Do the four pillars match what you know?"),
    ("q2", "pro", "出生时辰、真太阳时校正是否合理？", "Is the birth hour / true solar time reasonable?"),
    ("q3", "pro", "性格强弱、五行描述像不像您自己？", "Do strength/weakness and five elements feel like you?"),
    ("q4", "pro", "大运与人生阶段（学业/事业/家庭）是否对得上？", "Do decade luck stages match your life phases?"),
    ("q5", "pro", "流年或近几个月运势与您的感受是否接近？", "Does annual/monthly luck match recent experience?"),
    ("q6", "exp", "注册、登录、第一次排盘是否顺畅？", "Was sign-up and first charting smooth?"),
    ("q7", "exp", "「六西格玛×八字」说法是否好懂、可信？", "Is the DFSS × BaZi message clear and trustworthy?"),
    ("q8", "exp", "报告「专业解读」有没有帮助？", "Was the professional section helpful?"),
    ("q9", "exp", "报告「白话说明」是否看得懂？", "Was the plain-language section easy to understand?"),
    ("q10", "exp", "整份报告对您有没有参考价值？", "Was the full report valuable overall?"),
    ("q11", "exp", "生成报告的速度、是否曾卡住？", "Report speed and reliability (1=slow/failed, 10=fine)?"),
    ("q12", "exp", "页面好不好读（字体、颜色、翻页）？", "Is the UI easy to read and navigate?"),
    ("q13", "exp", "手机上看是否方便？", "Is mobile use convenient?"),
    ("q14", "exp", "免费预览够不够帮您决定是否付费？", "Did free preview help you decide on membership?"),
]

# 入库一律用简体 canonical，避免繁体/英文选项与 clear_on_submit 导致错存成第一项
BACKGROUND_ZH = ["完全新手", "略懂", "曾找过师傅", "自己研究过"]
BACKGROUND_EN = ["Complete beginner", "Some knowledge", "Consulted a master before", "Self-studied"]


def _label(item: Tuple[str, str, str, str], lang: str) -> str:
    _, _, zh, en = item
    if lang == "en":
        return en
    if lang == "zh_hant":
        try:
            from zh_convert import to_traditional

            return to_traditional(zh)
        except Exception:
            pass
    return zh


def _bg_labels(lang: str) -> List[str]:
    if lang == "en":
        return list(BACKGROUND_EN)
    if lang == "zh_hant":
        try:
            from zh_convert import to_traditional

            return [to_traditional(x) for x in BACKGROUND_ZH]
        except Exception:
            pass
    return list(BACKGROUND_ZH)


def _bg_index_from_stored(stored: Any) -> int:
    """把库里的背景（简/繁/英文）解析回选项下标。"""
    s = str(stored or "").strip()
    if not s:
        return 0
    for i, zh in enumerate(BACKGROUND_ZH):
        if s == zh:
            return i
    for i, en in enumerate(BACKGROUND_EN):
        if s == en:
            return i
    try:
        from zh_convert import to_traditional

        for i, zh in enumerate(BACKGROUND_ZH):
            if s == to_traditional(zh):
                return i
    except Exception:
        pass
    return 0


def _bg_display(stored: Any, lang: str) -> str:
    idx = _bg_index_from_stored(stored)
    labels = _bg_labels(lang)
    if 0 <= idx < len(labels):
        return labels[idx]
    return str(stored or "-")


def _avg(scores: Dict[str, int]) -> float:
    vals = [int(v) for v in scores.values() if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def _clear_survey_widget_keys() -> None:
    for k in list(st.session_state.keys()):
        if str(k).startswith("survey_"):
            del st.session_state[k]


def render_trial_survey(lang: str, supabase_client, *, user_id: str, user_email: str) -> None:
    flash = st.session_state.pop("_survey_flash", None)
    if isinstance(flash, dict):
        if flash.get("thanks"):
            st.success(flash["thanks"])
        if flash.get("gold"):
            st.success(flash["gold"])
        if flash.get("balloons"):
            st.balloons()

    st.markdown(f"### {t('survey_heading', lang)}")
    st.caption(t("survey_intro", lang))
    st.caption(t("survey_gold_hint", lang))

    latest = None
    if supabase_client and user_id:
        try:
            latest = supabase_client.get_latest_survey(user_id)
        except Exception:
            latest = None

    if latest:
        created = str(latest.get("created_at") or "")[:10]
        st.info(t("survey_already", lang).format(date=created or "—"))
        st.caption(
            f"{t('survey_background', lang)}：{_bg_display(latest.get('background'), lang)}"
        )

    bg_labels = _bg_labels(lang)
    default_bg_idx = _bg_index_from_stored((latest or {}).get("background")) if latest else 0
    pro_items = [x for x in SURVEY_ITEMS if x[1] == "pro"]
    exp_items = [x for x in SURVEY_ITEMS if x[1] == "exp"]

    # 注意：clear_on_submit=True + 带 key 的控件，在部分 Streamlit 版本会把提交值重置为默认第一项
    # （背景变成「完全新手」）。改为 False，提交成功后再手动清空。
    with st.form("trial_survey_form", clear_on_submit=False):
        bg_idx = st.selectbox(
            t("survey_background", lang),
            options=list(range(len(BACKGROUND_ZH))),
            format_func=lambda i: bg_labels[i],
            index=min(max(default_bg_idx, 0), len(BACKGROUND_ZH) - 1),
        )

        st.markdown(f"**{t('survey_section_pro', lang)}**")
        scores: Dict[str, int] = {}
        for item in pro_items:
            qid = item[0]
            scores[qid] = st.slider(
                _label(item, lang),
                min_value=1,
                max_value=10,
                value=7,
            )

        st.markdown(f"**{t('survey_section_exp', lang)}**")
        for item in exp_items:
            qid = item[0]
            scores[qid] = st.slider(
                _label(item, lang),
                min_value=1,
                max_value=10,
                value=7,
            )

        st.markdown(f"**{t('survey_section_open', lang)}**")
        open_feedback = st.text_area(
            t("survey_open_prompt", lang),
            height=120,
            placeholder=t("survey_open_ph", lang),
        )
        recommend_score = st.slider(
            t("survey_recommend", lang),
            min_value=1,
            max_value=10,
            value=7,
        )

        submitted = st.form_submit_button(
            t("survey_submit", lang),
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not str(open_feedback or "").strip():
            st.warning(t("survey_open_required", lang))
            return
        # 入库固定用简体 canonical，避免 UI 语言导致后台显示不一致
        try:
            bg_idx_i = int(bg_idx)
        except Exception:
            bg_idx_i = 0
        if bg_idx_i < 0 or bg_idx_i >= len(BACKGROUND_ZH):
            bg_idx_i = 0
        background = BACKGROUND_ZH[bg_idx_i]

        payload = {
            "survey_id": str(uuid.uuid4()),
            "user_id": user_id,
            "email": user_email,
            "background": background,
            "scores": scores,
            "open_feedback": str(open_feedback).strip(),
            "recommend_score": int(recommend_score),
            "ui_lang": lang,
            "avg_pro": _avg({k: scores[k] for k in scores if k in {x[0] for x in pro_items}}),
            "avg_exp": _avg({k: scores[k] for k in scores if k in {x[0] for x in exp_items}}),
            "avg_all": _avg(scores),
        }
        first_survey = latest is None
        if supabase_client and supabase_client.save_survey_response(payload):
            upgraded = False
            if first_survey:
                supabase_client.grant_survey_gold_reward(user_id)
                profile = supabase_client.get_user(user_id) or {}
                tier_now = profile.get("subscription_tier", "free")
                meta = profile.get("metadata") if isinstance(profile.get("metadata"), dict) else {}
                if tier_now in ("gold", "diamond"):
                    st.session_state.subscription_tier = tier_now
                if meta.get("survey_gold_rewarded") and tier_now == "gold":
                    upgraded = True
            _clear_survey_widget_keys()
            st.session_state._survey_flash = {
                "thanks": t("survey_thanks", lang),
                "gold": t("survey_gold_reward", lang) if upgraded else "",
                "balloons": bool(upgraded),
            }
            st.rerun()
        else:
            st.error(t("survey_save_fail", lang))


def survey_rows_for_admin(responses: List[Dict[str, Any]], lang: str) -> List[Dict[str, Any]]:
    """管理员表格行。"""
    if lang == "en":
        headers = {
            "date": "Date",
            "email": "Email",
            "background": "Background",
            "avg_pro": "Pro avg",
            "avg_exp": "Exp avg",
            "avg_all": "Overall",
            "recommend": "Recommend",
            "feedback": "Feedback",
        }
    else:
        headers = {
            "date": t("created_col", lang),
            "email": t("email_col", lang),
            "background": t("survey_background", lang),
            "avg_pro": t("survey_col_pro_avg", lang),
            "avg_exp": t("survey_col_exp_avg", lang),
            "avg_all": t("survey_col_all_avg", lang),
            "recommend": t("survey_recommend", lang).split("（")[0].split("(")[0].strip(),
            "feedback": t("survey_col_feedback", lang),
        }
    rows = []
    for r in responses:
        scores = r.get("scores") if isinstance(r.get("scores"), dict) else {}
        row = {
            headers["date"]: str(r.get("created_at") or "")[:10],
            headers["email"]: r.get("email") or "-",
            headers["background"]: _bg_display(r.get("background"), lang),
            headers["avg_pro"]: r.get("avg_pro", "-"),
            headers["avg_exp"]: r.get("avg_exp", "-"),
            headers["avg_all"]: r.get("avg_all", "-"),
            headers["recommend"]: r.get("recommend_score", "-"),
            headers["feedback"]: (str(r.get("open_feedback") or ""))[:80],
        }
        for i in range(1, 15):
            qk = f"q{i}"
            if qk in scores:
                row[f"Q{i}"] = scores[qk]
        rows.append(row)
    return rows
