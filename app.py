"""
六西格玛命理 - 八字 App
Sigma Fate - BaZi
基于Streamlit + DeepSeek + Supabase + Stripe
"""
import streamlit as st
from datetime import datetime
import uuid
import json

# 导入自定义模块
from bazi_engine import BaziEngine
from report_generator import ReportGenerator
from supabase_client import SupabaseClient
from stripe_payment import StripeClient
from utils import render_wuxing_bars, format_bazi_display, generate_pdf_report

# --- 配置 ---
st.set_page_config(
    page_title="六西格玛命理 - 八字",
    page_icon="🔮",
    layout="wide"
)

# --- 初始化Session State ---
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if 'subscription_tier' not in st.session_state:
    st.session_state.subscription_tier = 'free'  # free, monthly, quarterly
if 'report_generated' not in st.session_state:
    st.session_state.report_generated = False
if 'report_content' not in st.session_state:
    st.session_state.report_content = None
if 'bazi_data' not in st.session_state:
    st.session_state.bazi_data = None
if 'birth_info' not in st.session_state:
    st.session_state.birth_info = None

# --- 从环境变量读取配置 ---
import os
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_STOCK_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_STOCK_ANON_KEY', '')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-v4-flash')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_PRICE_MONTHLY = os.getenv('STRIPE_PRICE_MONTHLY', '')
STRIPE_PRICE_QUARTERLY = os.getenv('STRIPE_PRICE_QUARTERLY', '')

# 初始化客户端
supabase_client = SupabaseClient(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None
stripe_client = StripeClient(STRIPE_SECRET_KEY, STRIPE_PRICE_MONTHLY, STRIPE_PRICE_QUARTERLY) if STRIPE_SECRET_KEY else None
report_gen = ReportGenerator(DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL) if DEEPSEEK_API_KEY else None

# --- 侧边栏 - 品牌与导航 ---
with st.sidebar:
    st.markdown("""
    # 🔮 六西格玛命理
    ## Sigma Fate · BaZi
    """)
    
    st.markdown("---")
    
    st.markdown("""
    ### 关于本系统
    本系统将 **六西格玛设计 (DFSS)** 方法论与千年命理智慧融合，为你提供：
    
    - ✅ 精准八字排盘（真太阳时校正）
    - ✅ 八页深度命理报告
    - ✅ 事业 · 财运 · 感情 · 健康 全方位分析
    - ✅ 基于大数据与AI的工程化命理
    """)
    
    st.markdown("---")
    
    # 订阅状态
    tier_labels = {
        'free': '🆓 免费版',
        'monthly': '🌟 月度会员',
        'quarterly': '👑 季度会员'
    }
    st.info(f"当前状态：**{tier_labels.get(st.session_state.subscription_tier, '免费版')}**")
    
    if st.session_state.subscription_tier == 'free':
        st.warning("⚠️ 免费版仅可查看基本命盘，完整报告需订阅")
    
    st.markdown("---")
    
    st.caption("© 2026 Sigma Fate · 六西格玛命理")

# --- 主界面 ---
st.title("🔮 六西格玛命理 · 八字排盘")
st.markdown("*基于DFSS方法论与AI大模型的现代命理分析*")

# --- Tab切换 ---
tab1, tab2, tab3 = st.tabs(["📝 输入信息", "📊 八字命盘", "📄 完整报告"])

# ========== Tab 1: 输入信息 ==========
with tab1:
    st.markdown("### 请输入您的出生信息")
    st.caption("所有信息将严格保密，仅用于生成您的专属命理报告")
    
    col1, col2 = st.columns(2)
    
    with col1:
        name = st.text_input("👤 您的姓名", placeholder="请输入姓名")
        
        gender = st.radio(
            "⚧ 性别",
            options=['男', '女'],
            horizontal=True
        )
        
        birth_date = st.date_input(
            "📅 出生日期",
            value=datetime(1990, 1, 1),
            max_value=datetime.now()
        )
    
    with col2:
        birth_hour = st.number_input(
            "🕐 出生时辰（24小时制）",
            min_value=0,
            max_value=23,
            value=12,
            help="如果您不确定准确时间，可选择12:00（午时）"
        )
        
        birth_minute = st.number_input(
            "🕐 出生分钟",
            min_value=0,
            max_value=59,
            value=0
        )
        
        timezone = st.selectbox(
            "🌍 出生时区",
            options=['Asia/Shanghai', 'Asia/Hong_Kong', 'Asia/Taipei', 'America/New_York', 'Europe/London'],
            index=0
        )
    
    # 真太阳时选项
    use_true_solar = st.checkbox(
        "☀️ 启用真太阳时校正（推荐）",
        value=True,
        help="根据出生地的经度校正时间，使排盘更精准"
    )
    
    # 可选信息
    with st.expander("📌 更多信息（可选）"):
        birth_place = st.text_input("出生地点", placeholder="例如：中国 上海")
        email = st.text_input("📧 电子邮箱", placeholder="用于接收报告和订阅通知")
        
        st.caption("💡 提供更多信息有助于生成更精准的报告")
    
    # 会员选择
    st.markdown("---")
    st.markdown("### 💎 选择报告版本")
    
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        tier_free = st.button(
            "🆓 免费版\n\n基础命盘展示",
            use_container_width=True,
            key="btn_free"
        )
    with col_t2:
        tier_monthly = st.button(
            "🌟 月度会员\n¥XX/月\n\n完整八页报告",
            use_container_width=True,
            key="btn_monthly"
        )
    with col_t3:
        tier_quarterly = st.button(
            "👑 季度会员\n¥XX/季\n\n完整报告 + 优先咨询",
            use_container_width=True,
            key="btn_quarterly"
        )
    
    # 处理会员选择
    selected_tier = st.session_state.subscription_tier
    if tier_free:
        selected_tier = 'free'
    elif tier_monthly:
        selected_tier = 'monthly'
        # 跳转到Stripe支付
        if stripe_client:
            try:
                session = stripe_client.create_checkout_session(
                    st.session_state.user_id,
                    email or f"user_{st.session_state.user_id[:8]}@example.com",
                    'monthly'
                )
                st.markdown(f"[点击这里前往支付]({session.url})")
                st.success("正在跳转支付页面...")
            except Exception as e:
                st.error(f"支付系统暂时不可用，请联系客服。错误：{e}")
        else:
            st.warning("支付系统未配置，请手动联系客服订阅")
    elif tier_quarterly:
        selected_tier = 'quarterly'
        if stripe_client:
            try:
                session = stripe_client.create_checkout_session(
                    st.session_state.user_id,
                    email or f"user_{st.session_state.user_id[:8]}@example.com",
                    'quarterly'
                )
                st.markdown(f"[点击这里前往支付]({session.url})")
                st.success("正在跳转支付页面...")
            except Exception as e:
                st.error(f"支付系统暂时不可用，请联系客服。错误：{e}")
        else:
            st.warning("支付系统未配置，请手动联系客服订阅")
    
    # 生成按钮
    st.markdown("---")
    generate_btn = st.button(
        "🔮 开始排盘与生成报告",
        type="primary",
        use_container_width=True,
        disabled=not name
    )
    
    if generate_btn and name:
        if selected_tier == 'free':
            st.info("免费版将仅展示八字命盘，如需完整报告请订阅会员")
        
        with st.spinner("🔮 正在排盘与生成报告..."):
            # 1. 八字排盘
            bazi_engine = BaziEngine(
                year=birth_date.year,
                month=birth_date.month,
                day=birth_date.day,
                hour=birth_hour,
                minute=birth_minute,
                gender=gender,
                timezone=timezone,
                true_solar_time=use_true_solar
            )
            bazi_data = bazi_engine.calculate().get_summary()
            
            # 2. 保存到session
            st.session_state.bazi_data = bazi_data
            st.session_state.birth_info = {
                'name': name,
                'gender': gender,
                'birth_date': birth_date.isoformat(),
                'birth_hour': birth_hour,
                'birth_minute': birth_minute,
                'timezone': timezone,
                'birth_place': birth_place,
                'email': email,
                'payment_tier': selected_tier
            }
            
            # 3. 生成报告（如果已订阅）
            if selected_tier != 'free' and report_gen:
                try:
                    report = report_gen.generate(bazi_data, st.session_state.birth_info, selected_tier)
                    st.session_state.report_content = report
                    st.session_state.report_generated = True
                    
                    # 保存到Supabase
                    if supabase_client:
                        supabase_client.save_report(
                            st.session_state.user_id,
                            st.session_state.birth_info,
                            bazi_data,
                            report
                        )
                    st.success("✅ 报告生成成功！请查看「完整报告」标签页")
                    
                except Exception as e:
                    st.error(f"报告生成失败：{e}")
                    st.session_state.report_generated = False
            else:
                st.info("📊 命盘已生成，请查看「八字命盘」标签页")
                st.session_state.report_generated = False
            
            # 刷新页面
            st.rerun()

# ========== Tab 2: 八字命盘 ==========
with tab2:
    if st.session_state.bazi_data is None:
        st.info("👆 请在「输入信息」标签页填写出生信息并点击生成")
    else:
        bazi_data = st.session_state.bazi_data
        
        # 命盘展示
        col_show1, col_show2 = st.columns([1, 1])
        
        with col_show1:
            st.markdown("### 📋 四柱八字")
            bazi_display = format_bazi_display(bazi_data['bazi'])
            
            # 用表格展示
            cols = st.columns(4)
            for i, (pillar, value) in enumerate(bazi_display.items()):
                with cols[i]:
                    st.markdown(f"**{pillar}**")
                    st.markdown(f"<h1 style='text-align:center;font-size:3rem;'>{value}</h1>", unsafe_allow_html=True)
            
            st.markdown(f"**日主：** {bazi_data['day_master']}")
            st.markdown(f"**性别：** {bazi_data['gender']}")
        
        with col_show2:
            st.markdown("### 🌳 五行分布")
            stats = bazi_data['wuxing_stats']
            bars = render_wuxing_bars(stats)
            
            for bar in bars:
                st.markdown(f"{bar['wuxing']}：{'■' * int(bar['pct']/10)} ({bar['count']})")
                st.progress(bar['pct']/100, text=f"{bar['pct']:.0f}%")
        
        # 大运
        st.markdown("---")
        st.markdown("### 🚀 大运走势")
        if bazi_data['da_yun']:
            for dy in bazi_data['da_yun'][:6]:  # 显示前6步
                cols = st.columns([1, 2, 1])
                with cols[0]:
                    st.markdown(f"**第{dy['step']}步**")
                with cols[1]:
                    st.markdown(f"{dy['gan']}{dy['zhi']}")
                with cols[2]:
                    st.markdown(f"_{dy['years']}_")
        
        # 流年
        st.markdown("---")
        st.markdown("### 📅 流年运势")
        if bazi_data['liu_nian']:
            for ln in bazi_data['liu_nian']:
                year_label = f"**{ln['year']}**" if ln['is_current'] else str(ln['year'])
                st.markdown(f"{year_label}：{ln['gan']}{ln['zhi']}")

# ========== Tab 3: 完整报告 ==========
with tab3:
    if st.session_state.subscription_tier == 'free':
        st.warning("🔒 您当前为免费用户，完整八页报告需要订阅会员")
        st.markdown("""
        ### 💎 订阅会员解锁完整报告
        
        **月度会员**：解锁完整八页报告 + 实时流年更新
        **季度会员**：全部权益 + 专属咨询 + 五行风水建议
        
        请在「输入信息」标签页选择订阅
        """)
        
        # 模拟预览（仅展示标题）
        st.markdown("### 📄 报告预览（仅限会员）")
        preview_pages = [
            "页一：八字命盘与基本信息",
            "页二：事业流年详批 (Part 1)",
            "页三：事业流年详批 (Part 2)",
            "页四：财运流年详批 (Part 1)",
            "页五：财运流年详批 (Part 2)",
            "页六：感情流年详批 (Part 1)",
            "页七：感情流年详批 (Part 2)",
            "页八：健康流年详批"
        ]
        for page in preview_pages:
            st.markdown(f"🔒 {page}")
        
    elif st.session_state.report_content is None:
        st.info("👆 请先在「输入信息」标签页生成报告")
        
    else:
        report = st.session_state.report_content
        
        st.markdown("### 📄 您的八页命理报告")
        st.caption(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # 页导航
        page_names = ['page1', 'page2', 'page3', 'page4', 'page5', 'page6', 'page7', 'page8']
        page_labels = [
            '页一：八字命盘与基本信息',
            '页二：事业流年详批 (Part 1)',
            '页三：事业流年详批 (Part 2)',
            '页四：财运流年详批 (Part 1)',
            '页五：财运流年详批 (Part 2)',
            '页六：感情流年详批 (Part 1)',
            '页七：感情流年详批 (Part 2)',
            '页八：健康流年详批'
        ]
        
        # 分页展示
        for i, (page_key, label) in enumerate(zip(page_names, page_labels)):
            with st.expander(f"{label}", expanded=(i == 0)):
                if page_key in report:
                    content = report[page_key].get('content', '')
                    st.markdown(content)
                else:
                    st.warning("此页内容生成中")
        
        # 下载PDF
        st.markdown("---")
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            try:
                pdf_buffer = generate_pdf_report(
                    report,
                    st.session_state.birth_info,
                    st.session_state.bazi_data
                )
                st.download_button(
                    label="📥 下载PDF报告",
                    data=pdf_buffer,
                    file_name=f"命理报告_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.warning("PDF生成功能需要额外配置，请使用复制文本功能")
        
        with col_dl2:
            # 复制JSON数据
            json_data = json.dumps(report, ensure_ascii=False, indent=2)
            st.download_button(
                label="📋 导出数据（JSON）",
                data=json_data,
                file_name=f"命理报告_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )

# --- 页脚 ---
st.markdown("---")
st.caption("⚠️ 本系统仅供娱乐与自我参考，请理性看待命理分析结果。")
