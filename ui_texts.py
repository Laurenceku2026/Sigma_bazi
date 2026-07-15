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
        "chinese": "中文",
        "english": "EN",
        "app_title": "🔮 六西格玛命理 · 八字排盘",
        "app_subtitle": "基于DFSS方法论与AI大模型的现代命理分析",
        "sidebar_brand": "🔮 六西格玛命理",
        "sidebar_about": "关于本系统",
        "sidebar_body": (
            "本系统将 **六西格玛设计 (DFSS)** 方法论与千年命理智慧融合，为你提供：\n\n"
            "- ✅ 精准八字排盘（真太阳时校正）\n"
            "- ✅ 八页深度命理报告\n"
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
        "tab_report": "📄 完整报告",
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
        "register_caption": "请使用邮箱 + 密码注册（与赛马 App 同一套 Supabase 登录；密码至少 6 位）",
        "register_btn": "确认注册并继续",
        "register_btn_short": "去注册",
        "register_submit": "注册",
        "register_ok": "注册成功！",
        "need_register": "请先注册或登录后再排盘",
        "registered_as": "当前账号",
        "login_btn": "🔐 登录",
        "logout_btn": "退出登录",
        "login_heading": "🔐 邮箱密码登录",
        "login_caption": "输入注册邮箱与密码；将自动恢复您的命盘资料与报告",
        "login_submit": "登录",
        "login_ok": "登录成功！已恢复您的资料与历史记录",
        "login_not_found": "登录失败，请检查邮箱密码，或先注册",
        "login_prompt": "已有账号？请先登录，保护个人隐私，无需重复填写",
        "returning_hint": "已从账号恢复上次排盘资料，可直接查看命盘与报告",
        "password": "🔑 密码",
        "password_confirm": "🔑 确认密码",
        "membership_heading": "💎 升级会员 · 解锁完整报告",
        "btn_silver": "🥈 银卡会员\n\nHK$10 · 10次\n完整八页报告",
        "btn_gold": "🥇 金卡会员\n\nHK$100 · 10次\n八页报告 + 流年报告",
        "btn_diamond": "💎 钻石会员\n\nHK$999 · 一年无限\n八页报告 + 流年报告",
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
        "report_ok": "✅ 报告生成成功！请查看「完整报告」标签页",
        "report_fail": "报告生成失败：",
        "chart_ready": "📊 命盘已生成，请查看「八字命盘」标签页",
        "need_input": "👆 请在「输入信息」标签页填写出生信息并点击生成",
        "four_pillars": "📋 四柱八字",
        "day_master": "日主",
        "wuxing": "🌳 五行分布",
        "dayun": "🚀 大运走势",
        "liunian": "📅 流年运势",
        "step": "第{n}步",
        "locked_report": "🔒 您当前为免费用户，完整八页报告需要订阅会员",
        "unlock_heading": "💎 订阅会员解锁完整报告",
        "unlock_body": (
            "**银卡**：10次完整八页报告\n"
            "**金卡**：10次八页报告 + 流年预测专章\n"
            "**钻石**：一年内无限次报告 + 流年预测\n\n"
            "排盘后在下方选择会员方案"
        ),
        "preview": "📄 报告预览（仅限会员）",
        "need_generate": "👆 请先在「输入信息」标签页生成报告",
        "your_report": "📄 您的八页命理报告",
        "generated_at": "生成时间",
        "download_pdf": "📥 下载PDF报告",
        "export_json": "📋 导出数据（JSON）",
        "pdf_warn": "PDF生成功能需要额外配置，请使用复制文本功能",
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
    },
    "en": {
        "chinese": "中文",
        "english": "EN",
        "app_title": "🔮 Sigma Fate · BaZi Chart",
        "app_subtitle": "Modern BaZi analysis powered by DFSS + AI",
        "sidebar_brand": "🔮 Sigma Fate",
        "sidebar_about": "About",
        "sidebar_body": (
            "This app merges **DFSS (Design for Six Sigma)** with classical BaZi wisdom:\n\n"
            "- ✅ Precise charting (true solar time)\n"
            "- ✅ Eight-page deep reports\n"
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
        "tab_report": "📄 Full Report",
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
        "register_caption": "Register with email + password (same Supabase Auth as Horse racing; min 6 chars)",
        "register_btn": "Register & continue",
        "register_btn_short": "Register",
        "register_submit": "Sign up",
        "register_ok": "Registered!",
        "need_register": "Please register or sign in first",
        "registered_as": "Signed in as",
        "login_btn": "🔐 Sign in",
        "logout_btn": "Sign out",
        "login_heading": "🔐 Sign in with email & password",
        "login_caption": "Use your email and password. Chart and reports will be restored.",
        "login_submit": "Sign in",
        "login_ok": "Signed in! Your profile and history were restored",
        "login_not_found": "Sign-in failed. Check credentials or register first",
        "login_prompt": "Returning user? Sign in first to protect your privacy",
        "returning_hint": "Restored your last chart data. View chart and reports anytime",
        "password": "🔑 Password",
        "password_confirm": "🔑 Confirm password",
        "membership_heading": "💎 Upgrade · Unlock full reports",
        "btn_silver": "🥈 Silver\n\nHK$10 · 10 uses\nFull 8-page report",
        "btn_gold": "🥇 Gold\n\nHK$100 · 10 uses\n8 pages + annual luck",
        "btn_diamond": "💎 Diamond\n\nHK$999 · 1 year unlimited\n8 pages + annual luck",
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
        "report_ok": "✅ Report ready — open the Full Report tab",
        "report_fail": "Report failed: ",
        "chart_ready": "📊 Chart ready — open the Chart tab",
        "need_input": "👆 Fill birth info on the Input tab and generate",
        "four_pillars": "📋 Four Pillars",
        "day_master": "Day Master",
        "wuxing": "🌳 Five Elements",
        "dayun": "🚀 Decade Luck",
        "liunian": "📅 Annual Luck",
        "step": "Step {n}",
        "locked_report": "🔒 Full 8-page report requires a paid subscription",
        "unlock_heading": "💎 Subscribe to unlock",
        "unlock_body": (
            "**Silver**: 10 full 8-page reports\n"
            "**Gold**: 10 reports + annual luck chapter\n"
            "**Diamond**: unlimited reports for 1 year\n\n"
            "Choose a plan below after charting"
        ),
        "preview": "📄 Report preview (members only)",
        "need_generate": "👆 Generate a report on the Input tab first",
        "your_report": "📄 Your 8-page BaZi report",
        "generated_at": "Generated at",
        "download_pdf": "📥 Download PDF",
        "export_json": "📋 Export JSON",
        "pdf_warn": "PDF needs extra setup; use JSON export for now",
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
    },
}


def t(key: str, lang: str = "zh", **kwargs) -> str:
    text = TEXTS.get(lang, TEXTS["zh"]).get(key) or TEXTS["zh"].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


def region_options(lang: str = "zh"):
    labels, ids, longitudes = [], [], []
    for rid, zh, en, lon in REGIONS:
        ids.append(rid)
        labels.append(zh if lang == "zh" else en)
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
