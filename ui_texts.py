"""中英文文案与中国地域真太阳时基准。"""
from __future__ import annotations

from typing import Dict, List, Tuple

# (region_id, 中文名, 英文名, 基准经度用于真太阳时)
REGIONS: List[Tuple[str, str, str, float]] = [
    ("huabei", "华北（北京、天津、河北、山西、内蒙古）", "North China (Beijing region)", 116.4),
    ("dongbei", "东北（辽宁、吉林、黑龙江）", "Northeast China", 125.3),
    ("huadong", "华东（上海、江苏、浙江、安徽、山东、福建）", "East China (Shanghai region)", 121.5),
    ("huazhong", "华中（河南、湖北、湖南、江西）", "Central China", 114.3),
    ("huanan", "华南（广东、广西、海南）", "South China (Guangdong region)", 113.3),
    ("xinan", "西南（四川、重庆、云南、贵州、西藏）", "Southwest China", 104.1),
    ("xibei", "西北（陕西、甘肃、青海、宁夏、新疆）", "Northwest China", 108.9),
    ("gangao", "港澳台", "Hong Kong / Macau / Taiwan", 114.2),
    ("overseas_east", "海外 · 东亚时区", "Overseas · East Asia TZ", 135.0),
    ("overseas_west", "海外 · 欧美时区", "Overseas · US/EU TZ", -75.0),
]

TEXTS: Dict[str, Dict[str, str]] = {
    "zh": {
        "chinese": "中文简体",
        "chinese_hant": "中文繁體",
        "english": "English",
        "app_title": "🔮 六西格玛命理 · 八字排盘",
        "app_subtitle": "基于DFSS方法论与AI大模型的现代命理分析",
        "sidebar_brand": "🔮 六西格玛命理",
        "sidebar_about": "关于本系统",
        "sidebar_body": (
            "本系统将 **六西格玛设计 (DFSS)** 方法论与千年命理智慧融合，为你提供：\n\n"
            "- ✅ 精准八字排盘（真太阳时校正）\n"
            "- ✅ 九页深度命理报告（事业/财运/感情/健康均含 Part1+Part2）\n"
            "- ✅ 事业 · 财运 · 感情 · 健康 全方位分析\n"
            "- ✅ 基于大数据与AI的工程化命理"
        ),
        "current_status": "当前状态",
        "tier_free": "🆓 免费版",
        "tier_silver": "🥈 银卡会员",
        "tier_gold": "🥇 金卡会员",
        "tier_diamond": "💎 钻石会员",
        "free_warning": "⚠️ 免费版可查看基础命盘；完整报告请选购会员",
        "tab_input": "📝 输入信息",
        "tab_chart": "📊 八字命盘",
        "tab_report": "📄 八字报告",
        "tab_liunian": "📅 流年报告",
        "tab_survey": "📝 试用反馈",
        "survey_heading": "试用问卷（约 3 分钟）",
        "survey_intro": "试用排盘与报告后，请按 1–10 分评价（10 分为最高）。",
        "survey_gold_hint": "首次提交反馈，即可自动升级为黄金会员",
        "survey_background": "您的命理背景",
        "survey_section_pro": "八字专业（5 题）",
        "survey_section_exp": "使用体验（9 题）",
        "survey_section_open": "开放题",
        "survey_open_prompt": "15. 若只改一件事，您最希望改什么？",
        "survey_open_ph": "例如：排盘某柱不准、报告太慢、价格、白话不够清楚…",
        "survey_recommend": "愿意介绍给朋友吗？（1–10）",
        "survey_submit": "提交问卷",
        "survey_thanks": "感谢填写！您的意见已保存。",
        "survey_gold_reward": "谢谢反馈！您已升级为黄金会员",
        "survey_save_fail": "保存失败，请稍后重试或联系客服。",
        "survey_open_required": "请填写开放题（第 15 题）后再提交。",
        "survey_already": "您已于 {date} 提交过问卷，仍可再次填写以反映最新体验。",
        "survey_login_required": "请先登录后再填写试用问卷。",
        "survey_try_first": "建议先完成排盘并预览报告，再来填写问卷，反馈会更准确。",
        "liunian_chapter_badge": "含当月注意与四季预测（免费预览含水印）",
        "liunian_locked": "流年报告为金卡、钻石会员无水印版。免费可预览含水印流年；银卡不含本篇。",
        "liunian_heading": "📅 流年报告",
        "report_part_legend": "Part 1＝局势研判；Part 2＝方向与化解（更进一步、可执行）",
        "input_heading": "请输入您的出生信息",
        "input_caption": "所有信息将严格保密，仅用于生成您的专属命理报告",
        "name": "👤 您的姓名",
        "name_ph": "请输入姓名",
        "gender": "⚧ 性别",
        "male": "男",
        "female": "女",
        "birth_date": "📅 出生日期",
        "birth_hour": "🕐 出生时辰（24小时制）",
        "birth_hour_help": "如果您不确定准确时间，可选择12:00（午时）",
        "birth_minute": "🕐 出生分钟",
        "region": "🗺️ 出生地域（用于真太阳时校正）",
        "region_help": "按中国传统地理分区选择，非具体城市名",
        "true_solar": "☀️ 启用真太阳时校正（推荐）",
        "true_solar_help": "根据所选地域经度校正时辰，使排盘更精准",
        "more_info": "📌 更多信息（可选）",
        "birth_place": "出生地点（可选备注）",
        "birth_place_ph": "例如：广州、洛阳（仅作记录）",
        "email": "📧 电子邮箱",
        "email_ph": "用于注册与接收报告",
        "register_heading": "📧 注册账号",
        "register_caption": "本八字 App 独立账号（邮箱+密码，至少 6 位）。与其他 App 完全隔离，即使用同一邮箱也可在此重新注册。",
        "register_btn": "确认注册并继续",
        "register_btn_short": "去注册",
        "register_submit": "注册",
        "register_ok": "注册成功！本 App 账号已创建。",
        "register_fail": "注册失败：",
        "register_exists_local": "该邮箱已在本八字 App 注册，请直接登录（与其他 App 无关）。",
        "need_set_local_password": "本 App 需独立密码。请通过「注册」为本 App 设置密码（不影响其他 App）。",
        "login_bad_password": "邮箱或密码错误（本 App 独立密码，并非其他 App 的密码）。",
        "need_register": "请先注册或登录后再排盘",
        "registered_as": "当前账号",
        "login_btn": "🔐 登录/注册",
        "logout_btn": "退出登录",
        "login_heading": "🔐 登录本八字 App",
        "login_caption": "使用本 App 注册的邮箱与密码（与其他 App 账号互不影响）",
        "login_submit": "登录",
        "login_ok": "登录成功！已恢复您的资料与历史记录",
        "login_not_found": "本 App 无此账号，请先注册",
        "report_lang_mismatch": "当前报告语言与界面不一致（中文↔英文）。请按当前语言重新生成。",
        "free_preview_quota": "免费预览剩余 {left}/{total} 次（含水印；查看已生成报告不扣次）",
        "free_preview_exhausted": "免费预览次数已用完，请升级会员后继续生成报告。",
        "report_regen_lang": "按当前语言重新生成报告",
        "login_prompt": "已有账号？请先登录，保护个人隐私，无需重复填写",
        "returning_hint": "已从账号恢复上次排盘资料，可直接查看命盘与报告",
        "chart_unchanged_skip": "出生资料未变，已跳过重新排盘。可直接查看命盘与报告。",
        "password": "🔑 密码",
        "password_confirm": "🔑 确认密码",
        "membership_heading": "💎 升级会员 · 解锁完整报告",
        "btn_silver": "🥈 银卡会员\n\nHK$10 · 10次\n完整九页报告",
        "btn_gold": "🥇 金卡会员\n\nHK$100 · 10次\n九页报告 + 独立流年报告",
        "btn_diamond": "💎 钻石会员\n\nHK$999 · 一年无限\n九页报告 + 独立流年报告",
        "outline_title": "📋 报告大纲预览",
        "pay_now": "💳 前往支付",
        "remaining_reports": "剩余报告次数",
        "chart_section": "📊 您的八字命盘",
        "pay_link": "点击这里前往支付",
        "pay_jump": "正在跳转支付页面...",
        "pay_error": "支付系统暂时不可用，请联系客服。错误：",
        "pay_unconfigured": "支付系统未配置，请手动联系客服订阅",
        "generate": "🔮 开始排盘与生成报告",
        "free_only_chart": "免费版将仅展示八字命盘，如需完整报告请订阅会员",
        "generating": "🔮 正在排盘与生成报告...",
        "report_ok": "✅ 报告生成成功！请查看「八字报告」标签页",
        "report_fail": "报告生成失败：",
        "chart_ready": "📊 命盘已生成，请查看「八字命盘」标签页",
        "need_input": "👆 请在「输入信息」标签页填写出生信息并点击生成",
        "four_pillars": "📋 四柱八字",
        "day_master": "日主",
        "wuxing": "🌳 五行分布",
        "dayun": "🚀 大运走势",
        "liunian": "📅 流年运势",
        "step": "第{n}步",
        "locked_report": "🔒 您当前为免费用户，完整九页报告需要订阅会员",
        "unlock_heading": "💎 订阅会员解锁完整报告",
        "unlock_body": (
            "**银卡**：10次完整九页报告（事业/财运/感情/健康均含 Part1+Part2）\n"
            "**金卡**：10次九页报告 + 流年预测专章\n"
            "**钻石**：一年内无限次报告 + 流年预测\n\n"
            "排盘后在下方选择会员方案"
        ),
        "preview": "📄 报告预览（仅限会员）",
        "need_generate": "👆 请先在「输入信息」标签页生成报告",
        "your_report": "📄 您的九页命理报告",
        "generated_at": "生成时间",
        "download_pdf": "📥 下载PDF报告",
        "export_json": "📋 导出数据（JSON）",
        "pdf_warn": "PDF生成功能需要额外配置，请使用复制文本功能",
        "pdf_includes_liunian": "PDF 含完整九页 + 流年报告",
        "pdf_silver_no_liunian": "银卡 PDF 含完整九页（不含流年报告；升级金卡/钻石可含）",
        "goto_liunian_report": "📅 查看流年报告",
        "goto_full_report": "📄 前往八字报告",
        "footer": "⚠️ 本系统仅供娱乐与自我参考，请理性看待命理分析结果。",
        "admin_help": "管理员登录",
        "admin_login_title": "管理员登录",
        "admin_username": "用户名",
        "admin_password": "密码",
        "admin_login_btn": "登录",
        "admin_login_ok": "登录成功！",
        "admin_login_fail": "用户名或密码错误",
        "admin_logout": "退出登录",
        "admin_back": "返回主页",
        "user_mgmt": "用户管理",
        "sys_stats": "系统统计",
        "total_users": "总用户数",
        "paid_users": "专业版用户",
        "free_users": "免费版用户",
        "configured_users": "已配置用户",
        "user_list": "用户列表",
        "email_col": "邮箱",
        "subscription_col": "订阅等级",
        "trials_col": "剩余次数",
        "expires_col": "到期时间",
        "created_col": "注册时间",
        "last_login_col": "最后登录",
        "email_confirmed_col": "邮箱确认",
        "current_user": "当前用户",
        "edit_subscription": "修改订阅",
        "set_subscription": "订阅等级",
        "set_trials": "设置剩余次数",
        "update_subscription": "更新订阅",
        "reset_trials": "重置次数",
        "actions": "操作",
        "send_reset_email": "发送重置邮件",
        "delete_user": "删除用户",
        "refresh_data": "刷新数据",
        "bulk_ops": "批量操作",
        "reset_all_free": "重置所有免费用户次数",
        "export_csv": "导出用户数据(CSV)",
        "select_user": "选择用户",
        "no_users": "暂无用户数据（请确认已执行 SQL 且 Secrets 中密钥正确）",
        "update_ok": "已更新",
        "update_fail": "更新失败",
        "delete_ok": "已删除用户",
        "delete_fail": "删除失败",
        "reset_ok": "次数已重置",
        "reset_all_ok": "所有免费用户次数已重置",
        "reset_email_na": "当前未接入 Supabase Auth 邮件重置，请手动联系用户",
        "init_errors": "外部服务初始化提示",
        "init_hint": "排盘功能仍可本地使用；请检查 Secrets / .env 中的 API Key。",
        "admin_scope_info": (
            "🔒 本页只管理本 App 表 **`sf_users`**（`{schema}` / `{app_id}`）。\n\n"
            "- 列表里「无姓名无生日」的邮箱，多半是以前无密码注册/试登留下的，**可以删**。\n"
            "- 删除这里的行 **不会** 删除赛马 App / 门户的账号，也 **不会** 删掉 Supabase Auth 的总账号；"
            "只是本八字 App 看不到他们。\n"
            "- 推荐：点「只保留有资料用户」清掉空行，或下方逐个删除。"
        ),
        "admin_table_caption": "table=`{table}` · schema=`{schema}` · app_id=`{app_id}`",
        "admin_purge_foreign": "🧹 清理非本 App 脏数据",
        "admin_purge_foreign_ok": "已清理 {n} 条",
        "admin_purge_anon": "🧹 删除无邮箱匿名用户",
        "admin_purge_anon_ok": "已删除 {n} 条匿名用户",
        "admin_purge_empty": "🗑 只保留有资料用户（删空行）",
        "admin_purge_empty_ok": "已删除 {n} 个无姓名无生日的空用户，已排盘用户保留",
        "admin_read_fail": "读取用户失败：{err}",
        "admin_sql_hint": "请确认：1) 已执行 sql/001～009；2) Exposed schemas 含 app_sigma_fate；3) Secrets 中 URL 与 service_role 属同一项目。",
        "admin_empty_warn": "当前有 **{n}** 个仅邮箱、无排盘资料的用户（例如测试邮箱）。点击上方「只保留有资料用户」可一次删掉；或在 Supabase 跑 `sql/006_purge_empty_profile_users.sql`。",
        "admin_with_profile": "有资料",
        "admin_show_all": "显示全部（含无资料空行）",
        "admin_show_all_caption": "默认只显示有姓名/生日的用户（{shown}/{total}）。勾选上方可看全部。",
        "admin_no_profiled": "暂无已排盘用户；请勾选「显示全部」或先在 App 排盘。",
        "admin_col_name": "姓名",
        "admin_col_birthday": "生日",
        "admin_col_birth_time": "出生时间",
        "admin_col_birth_place": "出生地点",
        "admin_birth_profile": "出生资料",
        "admin_col_time": "时间",
        "admin_col_gender": "性别",
        "admin_birth_place_label": "出生地点：",
        "admin_survey_responses": "试用问卷回复（App 内）",
        "admin_survey_empty": "暂无问卷回复。请用户在 App「试用反馈」页填写；需先执行 sql/009_sf_survey_responses.sql。",
        "admin_survey_full": "查看完整开放建议",
        "admin_export_template": "导出问卷模板（可选）",
        "admin_export_template_body": "用户可在 App **「试用反馈」** 页直接填写，无需微信。15 题：5 专业 + 9 体验（1–10 分）+ 1 开放题。",
        "admin_download_md": "📥 下载问卷 Markdown",
        "admin_download_csv": "📥 下载表格 CSV",
        "survey_col_pro_avg": "专业均分",
        "survey_col_exp_avg": "体验均分",
        "survey_col_all_avg": "总均分",
        "survey_col_feedback": "开放建议",
    },
    "en": {
        "chinese": "中文简体",
        "chinese_hant": "中文繁體",
        "english": "English",
        "app_title": "🔮 Sigma Fate · BaZi Chart",
        "app_subtitle": "Modern BaZi analysis powered by DFSS + AI",
        "sidebar_brand": "🔮 Sigma Fate",
        "sidebar_about": "About",
        "sidebar_body": (
            "This app merges **DFSS (Design for Six Sigma)** with classical BaZi wisdom:\n\n"
            "- ✅ Precise charting (true solar time)\n"
            "- ✅ Nine-page deep reports (Career/Wealth/Relationship/Health each have Part1+Part2)\n"
            "- ✅ Career · Wealth · Relationship · Health\n"
            "- ✅ Engineering-style destiny analytics"
        ),
        "current_status": "Status",
        "tier_free": "🆓 Free",
        "tier_silver": "🥈 Silver",
        "tier_gold": "🥇 Gold",
        "tier_diamond": "💎 Diamond",
        "free_warning": "⚠️ Free tier: basic chart only; upgrade for full reports",
        "tab_input": "📝 Input",
        "tab_chart": "📊 Chart",
        "tab_report": "📄 BaZi Report",
        "tab_liunian": "📅 Annual Luck Report",
        "tab_survey": "📝 Feedback",
        "survey_heading": "Trial survey (~3 min)",
        "survey_intro": "After trying the chart and report, please rate each item from 1–10 (10 = best).",
        "survey_gold_hint": "Submit feedback for the first time to unlock Gold membership automatically.",
        "survey_background": "Your BaZi background",
        "survey_section_pro": "BaZi accuracy (5 items)",
        "survey_section_exp": "App experience (9 items)",
        "survey_section_open": "Open question",
        "survey_open_prompt": "15. If you could change one thing, what would it be?",
        "survey_open_ph": "e.g. pillar accuracy, speed, pricing, plain-language clarity…",
        "survey_recommend": "Would you recommend to a friend? (1–10)",
        "survey_submit": "Submit survey",
        "survey_thanks": "Thank you! Your feedback has been saved.",
        "survey_save_fail": "Could not save. Please try again later.",
        "survey_open_required": "Please answer question 15 before submitting.",
        "survey_already": "You submitted on {date}. You may submit again after new changes.",
        "survey_login_required": "Please sign in to complete the survey.",
        "survey_try_first": "We recommend charting and previewing a report first for better feedback.",
        "liunian_chapter_badge": "Current month + four seasons (free preview is watermarked)",
        "liunian_locked": "Clear Annual Luck is for Gold/Diamond. Free users get a watermarked preview; Silver excludes this chapter.",
        "liunian_heading": "📅 Annual Luck Report",
        "report_part_legend": "Part 1 = situation; Part 2 = direction & remedies (actionable next steps)",
        "input_heading": "Enter birth information",
        "input_caption": "Your data is private and used only to generate your report",
        "name": "👤 Name",
        "name_ph": "Your name",
        "gender": "⚧ Gender",
        "male": "Male",
        "female": "Female",
        "birth_date": "📅 Birth date",
        "birth_hour": "🕐 Birth hour (24h)",
        "birth_hour_help": "If unsure, use 12:00 (Wu hour)",
        "birth_minute": "🕐 Birth minute",
        "region": "🗺️ Birth region (true solar time)",
        "region_help": "Chinese geographic regions, not city names",
        "true_solar": "☀️ Enable true solar time (recommended)",
        "true_solar_help": "Adjust hour by regional longitude",
        "more_info": "📌 More info (optional)",
        "birth_place": "Birth place (note only)",
        "birth_place_ph": "e.g. Guangzhou (for records)",
        "email": "📧 Email",
        "email_ph": "For registration and reports",
        "register_heading": "📧 Create account",
        "register_caption": "Independent BaZi account (email + password, min 6). Fully isolated from other apps — you can register here even with the same email.",
        "register_btn": "Register & continue",
        "register_btn_short": "Register",
        "register_submit": "Sign up",
        "register_ok": "Registered! Your BaZi-only account is ready.",
        "register_fail": "Registration failed: ",
        "register_exists_local": "This email is already registered in this BaZi app. Please sign in (unrelated to other apps).",
        "need_set_local_password": "This app needs its own password. Use Register to set one for BaZi only (does not affect other apps).",
        "login_bad_password": "Wrong email or password (BaZi-only password — not your other-app password).",
        "need_register": "Please register or sign in first",
        "registered_as": "Signed in as",
        "login_btn": "🔐 Sign in / Register",
        "logout_btn": "Sign out",
        "login_heading": "🔐 Sign in to BaZi",
        "login_caption": "Use the email and password registered in this BaZi app (independent of other apps)",
        "login_submit": "Sign in",
        "login_ok": "Signed in! Your profile and history were restored",
        "login_not_found": "No BaZi account for this email — please register first",
        "report_lang_mismatch": "This report language does not match the UI (Chinese ↔ English). Please regenerate.",
        "free_preview_quota": "Free watermarked previews left: {left}/{total} (viewing saved report is free)",
        "free_preview_exhausted": "Free preview limit reached. Please upgrade to keep generating reports.",
        "report_regen_lang": "Regenerate report in current language",
        "login_prompt": "Returning user? Sign in first to protect your privacy",
        "returning_hint": "Restored your last chart data. View chart and reports anytime",
        "chart_unchanged_skip": "Birth data unchanged — skipped recalculation. View your chart and report anytime.",
        "password": "🔑 Password",
        "password_confirm": "🔑 Confirm password",
        "membership_heading": "💎 Upgrade · Unlock full reports",
        "btn_silver": "🥈 Silver\n\nHK$10 · 10 uses\nFull 9-page report",
        "btn_gold": "🥇 Gold\n\nHK$100 · 10 uses\n9 pages + Annual Luck Report",
        "btn_diamond": "💎 Diamond\n\nHK$999 · 1 year unlimited\n9 pages + Annual Luck Report",
        "outline_title": "📋 Report outline",
        "pay_now": "💳 Pay now",
        "remaining_reports": "Reports remaining",
        "chart_section": "📊 Your BaZi chart",
        "pay_link": "Click here to pay",
        "pay_jump": "Redirecting to payment...",
        "pay_error": "Payment unavailable. Error: ",
        "pay_unconfigured": "Payment is not configured; contact support to subscribe",
        "generate": "🔮 Generate chart & report",
        "free_only_chart": "Free tier shows the chart only; subscribe for the full report",
        "generating": "🔮 Calculating chart & report...",
        "report_ok": "✅ Report ready — open the BaZi Report tab",
        "report_fail": "Report failed: ",
        "chart_ready": "📊 Chart ready — open the Chart tab",
        "need_input": "👆 Fill birth info on the Input tab and generate",
        "four_pillars": "📋 Four Pillars",
        "day_master": "Day Master",
        "wuxing": "🌳 Five Elements",
        "dayun": "🚀 Decade Luck",
        "liunian": "📅 Annual Luck",
        "step": "Step {n}",
        "locked_report": "🔒 Full 9-page report requires a paid subscription",
        "unlock_heading": "💎 Subscribe to unlock",
        "unlock_body": (
            "**Silver**: 10 full 9-page reports (Career/Wealth/Relationship/Health each have Part1+Part2)\n"
            "**Gold**: 10 reports + annual luck chapter\n"
            "**Diamond**: unlimited reports for 1 year\n\n"
            "Choose a plan below after charting"
        ),
        "preview": "📄 Report preview (members only)",
        "need_generate": "👆 Generate a report on the Input tab first",
        "your_report": "📄 Your 9-page BaZi report",
        "generated_at": "Generated at",
        "download_pdf": "📥 Download PDF",
        "export_json": "📋 Export JSON",
        "pdf_warn": "PDF needs extra setup; use JSON export for now",
        "pdf_includes_liunian": "PDF includes 9 pages + Annual Luck Report",
        "pdf_silver_no_liunian": "Silver PDF: 9 pages only (upgrade Gold/Diamond for Annual Luck)",
        "goto_liunian_report": "📅 Open Annual Luck Report",
        "goto_full_report": "📄 Go to BaZi Report",
        "footer": "⚠️ For entertainment and self-reflection only.",
        "admin_help": "Admin login",
        "admin_login_title": "Admin Login",
        "admin_username": "Username",
        "admin_password": "Password",
        "admin_login_btn": "Sign in",
        "admin_login_ok": "Signed in",
        "admin_login_fail": "Invalid username or password",
        "admin_logout": "Sign out",
        "admin_back": "Back to app",
        "user_mgmt": "User Management",
        "sys_stats": "System Statistics",
        "total_users": "Total Users",
        "paid_users": "Paid Users",
        "free_users": "Free Users",
        "configured_users": "Configured Users",
        "user_list": "User List",
        "email_col": "Email",
        "subscription_col": "Subscription",
        "trials_col": "Remaining Uses",
        "expires_col": "Expiry",
        "created_col": "Registered",
        "last_login_col": "Last Login",
        "email_confirmed_col": "Email Confirmed",
        "current_user": "Selected user",
        "edit_subscription": "Edit Subscription",
        "set_subscription": "Subscription tier",
        "set_trials": "Set remaining uses",
        "update_subscription": "Update subscription",
        "reset_trials": "Reset uses",
        "actions": "Actions",
        "send_reset_email": "Send reset email",
        "delete_user": "Delete user",
        "refresh_data": "Refresh",
        "bulk_ops": "Bulk Actions",
        "reset_all_free": "Reset all free-user quotas",
        "export_csv": "Export users (CSV)",
        "select_user": "Select user",
        "no_users": "No users yet (run SQL and check Secrets keys)",
        "update_ok": "Updated",
        "update_fail": "Update failed",
        "delete_ok": "User deleted",
        "delete_fail": "Delete failed",
        "reset_ok": "Quota reset",
        "reset_all_ok": "All free-user quotas reset",
        "reset_email_na": "Password reset email needs Supabase Auth; contact the user manually",
        "init_errors": "External service init notes",
        "init_hint": "Charting still works offline; check Secrets / .env API keys.",
        "admin_scope_info": (
            "🔒 Managing `sf_users` only (`{schema}` / `{app_id}`).\n\n"
            "- Rows with no name/birthday are usually test sign-ins and **can be deleted**.\n"
            "- Deleting here does **not** remove Horse racing / portal Auth accounts.\n"
            "- Use **Keep profiled users only** to purge empty rows."
        ),
        "admin_table_caption": "table=`{table}` · schema=`{schema}` · app_id=`{app_id}`",
        "admin_purge_foreign": "🧹 Purge foreign rows",
        "admin_purge_foreign_ok": "Purged {n} rows",
        "admin_purge_anon": "🧹 Delete anonymous (no email)",
        "admin_purge_anon_ok": "Deleted {n} anonymous rows",
        "admin_purge_empty": "🗑 Keep profiled users only",
        "admin_purge_empty_ok": "Deleted {n} empty-profile users",
        "admin_read_fail": "Failed to load users: {err}",
        "admin_sql_hint": "Check SQL 001–009, exposed schema app_sigma_fate, and matching Supabase URL/key.",
        "admin_empty_warn": "{n} email-only empty profiles. Use Keep profiled users only.",
        "admin_with_profile": "With profile",
        "admin_show_all": "Show all (incl. empty profiles)",
        "admin_show_all_caption": "Showing profiled users only ({shown}/{total}).",
        "admin_no_profiled": "No profiled users yet.",
        "admin_col_name": "Name",
        "admin_col_birthday": "Birthday",
        "admin_col_birth_time": "Birth time",
        "admin_col_birth_place": "Birth place",
        "admin_birth_profile": "Birth profile",
        "admin_col_time": "Time",
        "admin_col_gender": "Gender",
        "admin_birth_place_label": "Birth place: ",
        "admin_survey_responses": "In-app survey responses",
        "admin_survey_empty": "No responses yet. Users fill in App → Feedback tab.",
        "admin_survey_full": "Full open feedback",
        "admin_export_template": "Export questionnaire template",
        "admin_export_template_body": "Users can fill in App → Feedback tab. 15 items: 5 pro + 9 experience + 1 open.",
        "admin_download_md": "📥 Download questionnaire (MD)",
        "admin_download_csv": "📥 Download table CSV",
        "survey_gold_reward": "Thank you! You have been upgraded to Gold membership.",
        "survey_col_pro_avg": "Pro avg",
        "survey_col_exp_avg": "Exp avg",
        "survey_col_all_avg": "Overall",
        "survey_col_feedback": "Feedback",
    },
}


def t(key: str, lang: str = "zh", **kwargs) -> str:
    # zh_hant 复用简体词条再转繁体
    base = "zh" if lang in ("zh", "zh_hant") else lang
    text = TEXTS.get(base, TEXTS["zh"]).get(key) or TEXTS["zh"].get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    if lang == "zh_hant":
        from zh_convert import to_traditional

        text = to_traditional(text)
    return text


def is_chinese(lang: str) -> bool:
    return lang in ("zh", "zh_hant")


def report_output_language(lang: str) -> str:
    """给 DeepSeek 的输出语言指令。"""
    if lang == "en":
        return "English (write the entire report in English; do not use Chinese)"
    if lang == "zh_hant":
        return "繁體中文（全篇必須使用繁體，不要用簡體）"
    return "简体中文（全篇必须使用简体）"


def region_options(lang: str = "zh"):
    labels, ids, longitudes = [], [], []
    for rid, zh, en, lon in REGIONS:
        ids.append(rid)
        if lang == "en":
            labels.append(en)
        elif lang == "zh_hant":
            from zh_convert import to_traditional

            labels.append(to_traditional(zh))
        else:
            labels.append(zh)
        longitudes.append(lon)
    return labels, ids, longitudes


def region_longitude(region_id: str) -> float:
    for rid, _, _, lon in REGIONS:
        if rid == region_id:
            return lon
    return 120.0


def region_label(region_id: str, lang: str = "zh") -> str:
    for rid, zh, en, _ in REGIONS:
        if rid == region_id:
            return zh if lang == "zh" else en
    return region_id


# 兼容旧 import
def timezone_options(lang: str = "zh"):
    return region_options(lang)[:2]
