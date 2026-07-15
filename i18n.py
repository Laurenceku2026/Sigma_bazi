"""中英文文案与时区标签。"""
from __future__ import annotations

from typing import Dict

TIMEZONES = [
    ("Asia/Shanghai", "中国（上海 / 北京）", "China (Shanghai / Beijing)"),
    ("Asia/Hong_Kong", "中国香港", "Hong Kong"),
    ("Asia/Taipei", "中国台湾（台北）", "Taiwan (Taipei)"),
    ("Asia/Tokyo", "日本（东京）", "Japan (Tokyo)"),
    ("Asia/Singapore", "新加坡", "Singapore"),
    ("America/New_York", "美国东部（纽约）", "US Eastern (New York)"),
    ("America/Los_Angeles", "美国西部（洛杉矶）", "US Pacific (Los Angeles)"),
    ("Europe/London", "英国（伦敦）", "UK (London)"),
    ("Europe/Paris", "欧洲中部（巴黎）", "Central Europe (Paris)"),
    ("UTC", "协调世界时 UTC", "Coordinated Universal Time (UTC)"),
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
        "tier_monthly": "🌟 月度会员",
        "tier_quarterly": "👑 季度会员",
        "free_warning": "⚠️ 免费版仅可查看基本命盘，完整报告需订阅",
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
        "timezone": "🌍 出生时区",
        "true_solar": "☀️ 启用真太阳时校正（推荐）",
        "true_solar_help": "根据出生地的经度校正时间，使排盘更精准",
        "more_info": "📌 更多信息（可选）",
        "birth_place": "出生地点",
        "birth_place_ph": "例如：中国 上海",
        "email": "📧 电子邮箱",
        "email_ph": "用于接收报告和订阅通知",
        "more_tip": "💡 提供更多信息有助于生成更精准的报告",
        "choose_tier": "💎 选择报告版本",
        "btn_free": "🆓 免费版\n\n基础命盘展示",
        "btn_monthly": "🌟 月度会员\n¥XX/月\n\n完整八页报告",
        "btn_quarterly": "👑 季度会员\n¥XX/季\n\n完整报告 + 优先咨询",
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
            "**月度会员**：解锁完整八页报告 + 实时流年更新\n"
            "**季度会员**：全部权益 + 专属咨询 + 五行风水建议\n\n"
            "请在「输入信息」标签页选择订阅"
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
        "tier_monthly": "🌟 Monthly",
        "tier_quarterly": "👑 Quarterly",
        "free_warning": "⚠️ Free tier shows the chart only; subscribe for full reports",
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
        "timezone": "🌍 Birth timezone",
        "true_solar": "☀️ Enable true solar time (recommended)",
        "true_solar_help": "Adjust by longitude for higher chart accuracy",
        "more_info": "📌 More info (optional)",
        "birth_place": "Birth place",
        "birth_place_ph": "e.g. Shanghai, China",
        "email": "📧 Email",
        "email_ph": "For report delivery and subscription notices",
        "more_tip": "💡 Extra details help improve report relevance",
        "choose_tier": "💎 Choose report tier",
        "btn_free": "🆓 Free\n\nBasic chart",
        "btn_monthly": "🌟 Monthly\n¥XX/mo\n\nFull 8-page report",
        "btn_quarterly": "👑 Quarterly\n¥XX/qtr\n\nReport + priority consult",
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
            "**Monthly**: full 8-page report + annual updates\n"
            "**Quarterly**: all benefits + consult + feng shui tips\n\n"
            "Choose a plan on the Input tab"
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


def timezone_options(lang: str = "zh"):
    """返回 (显示名列表, 值列表)。"""
    labels = []
    values = []
    for tz_id, zh_name, en_name in TIMEZONES:
        values.append(tz_id)
        labels.append(zh_name if lang == "zh" else en_name)
    return labels, values


def timezone_label(tz_id: str, lang: str = "zh") -> str:
    for tid, zh_name, en_name in TIMEZONES:
        if tid == tz_id:
            return zh_name if lang == "zh" else en_name
    return tz_id
