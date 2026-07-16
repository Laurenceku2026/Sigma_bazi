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


def _avg(scores: Dict[str, int]) -> float:
    vals = [int(v) for v in scores.values() if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


def render_trial_survey(lang: str, supabase_client, *, user_id: str, user_email: str) -> None:
    st.markdown(f"### {t('survey_heading', lang)}")
    st.caption(t("survey_intro", lang))

    latest = None
    if supabase_client and user_id:
        try:
            latest = supabase_client.get_latest_survey(user_id)
        except Exception:
            latest = None

    if latest:
        created = str(latest.get("created_at") or "")[:10]
        st.info(t("survey_already", lang).format(date=created or "—"))

    bg_opts = BACKGROUND_EN if lang == "en" else BACKGROUND_ZH
    if lang == "zh_hant":
        try:
            from zh_convert import to_traditional

            bg_opts = [to_traditional(x) for x in BACKGROUND_ZH]
        except Exception:
            bg_opts = BACKGROUND_ZH

    pro_items = [x for x in SURVEY_ITEMS if x[1] == "pro"]
    exp_items = [x for x in SURVEY_ITEMS if x[1] == "exp"]

    with st.form("trial_survey_form", clear_on_submit=True):
        background = st.selectbox(t("survey_background", lang), bg_opts, key="survey_bg")

        st.markdown(f"**{t('survey_section_pro', lang)}**")
        scores: Dict[str, int] = {}
        for item in pro_items:
            qid = item[0]
            scores[qid] = st.slider(
                _label(item, lang),
                min_value=1,
                max_value=10,
                value=7,
                key=f"survey_slider_{qid}",
            )

        st.markdown(f"**{t('survey_section_exp', lang)}**")
        for item in exp_items:
            qid = item[0]
            scores[qid] = st.slider(
                _label(item, lang),
                min_value=1,
                max_value=10,
                value=7,
                key=f"survey_slider_{qid}",
            )

        st.markdown(f"**{t('survey_section_open', lang)}**")
        open_feedback = st.text_area(
            t("survey_open_prompt", lang),
            height=120,
            placeholder=t("survey_open_ph", lang),
            key="survey_open",
        )
        recommend_score = st.slider(
            t("survey_recommend", lang),
            min_value=1,
            max_value=10,
            value=7,
            key="survey_recommend",
        )

        submitted = st.form_submit_button(
            t("survey_submit", lang),
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not open_feedback.strip():
            st.warning(t("survey_open_required", lang))
            return
        payload = {
            "survey_id": str(uuid.uuid4()),
            "user_id": user_id,
            "email": user_email,
            "background": background,
            "scores": scores,
            "open_feedback": open_feedback.strip(),
            "recommend_score": int(recommend_score),
            "ui_lang": lang,
            "avg_pro": _avg({k: scores[k] for k in scores if k in {x[0] for x in pro_items}}),
            "avg_exp": _avg({k: scores[k] for k in scores if k in {x[0] for x in exp_items}}),
            "avg_all": _avg(scores),
        }
        first_survey = latest is None
        if supabase_client and supabase_client.save_survey_response(payload):
            rewarded = False
            if first_survey:
                rewarded = supabase_client.grant_survey_gold_reward(user_id)
                if rewarded:
                    st.session_state.subscription_tier = "gold"
            st.success(t("survey_thanks", lang))
            if rewarded:
                st.success(t("survey_gold_reward", lang))
            st.balloons()
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
            headers["background"]: r.get("background") or "-",
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
