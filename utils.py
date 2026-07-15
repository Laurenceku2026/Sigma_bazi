"""
工具函数
"""
import re
from datetime import datetime
import streamlit as st

def validate_birth_date(year, month, day, hour):
    """验证出生日期合法性"""
    try:
        datetime(year, month, day, hour)
        return True
    except ValueError:
        return False

def format_bazi_display(bazi):
    """格式化八字显示"""
    return {
        '年柱': f"{bazi['年柱'][0]}{bazi['年柱'][1]}",
        '月柱': f"{bazi['月柱'][0]}{bazi['月柱'][1]}",
        '日柱': f"{bazi['日柱'][0]}{bazi['日柱'][1]}",
        '时柱': f"{bazi['时柱'][0]}{bazi['时柱'][1]}"
    }

def get_wuxing_color(wuxing):
    """获取五行对应的颜色"""
    colors = {
        '木': '#4CAF50',
        '火': '#F44336', 
        '土': '#FF9800',
        '金': '#FFD700',
        '水': '#2196F3'
    }
    return colors.get(wuxing, '#666666')

def render_wuxing_bars(stats):
    """渲染五行条形图"""
    max_val = max(stats.values()) if stats.values() else 1
    bars = []
    for wuxing, count in stats.items():
        pct = (count / max_val * 100) if max_val > 0 else 0
        bars.append({
            'wuxing': wuxing,
            'count': count,
            'pct': pct,
            'color': get_wuxing_color(wuxing)
        })
    return bars

def render_bazi_chart(bazi_data, lang: str = "zh"):
    """在页面内渲染八字命盘（供输入页与命盘页复用）。"""
    from i18n import t

    col_show1, col_show2 = st.columns(2)
    with col_show1:
        st.markdown(f"### {t('four_pillars', lang)}")
        bazi_display = format_bazi_display(bazi_data["bazi"])
        cols = st.columns(4)
        for i, (pillar, value) in enumerate(bazi_display.items()):
            with cols[i]:
                st.markdown(f"**{pillar}**")
                st.markdown(
                    f"<h1 style='text-align:center;font-size:3rem;'>{value}</h1>",
                    unsafe_allow_html=True,
                )
        st.markdown(f"**{t('day_master', lang)}：** {bazi_data['day_master']}")
        st.markdown(f"**{t('gender', lang)}：** {bazi_data['gender']}")
    with col_show2:
        st.markdown(f"### {t('wuxing', lang)}")
        bars = render_wuxing_bars(bazi_data["wuxing_stats"])
        for bar in bars:
            st.markdown(f"{bar['wuxing']}：{'■' * int(bar['pct'] / 10)} ({bar['count']})")
            st.progress(min(max(bar["pct"] / 100.0, 0.0), 1.0))
            st.caption(f"{bar['pct']:.0f}%")

    st.markdown("---")
    st.markdown(f"### {t('dayun', lang)}")
    if bazi_data.get("da_yun"):
        for dy in bazi_data["da_yun"][:6]:
            c0, c1, c2 = st.columns([1, 2, 1])
            c0.markdown(f"**{t('step', lang, n=dy['step'])}**")
            c1.markdown(f"{dy['gan']}{dy['zhi']}")
            c2.markdown(f"_{dy['years']}_")

    st.markdown("---")
    st.markdown(f"### {t('liunian', lang)}")
    if bazi_data.get("liu_nian"):
        for ln in bazi_data["liu_nian"]:
            year_label = f"**{ln['year']}**" if ln.get("is_current") else str(ln["year"])
            st.markdown(f"{year_label}：{ln['gan']}{ln['zhi']}")


def generate_pdf_report(report_content, birth_info, bazi_data):
    """生成PDF报告（简化版）"""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    import io
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # 简单排版 - 完整版需要更复杂的布局
    y = 750
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, y, "六西格玛命理 - 八字命盘报告")
    
    y -= 30
    c.setFont("Helvetica", 12)
    c.drawString(100, y, f"姓名：{birth_info.get('name', '未命名')}")
    y -= 20
    c.drawString(100, y, f"性别：{birth_info.get('gender', '')}")
    
    # 添加各页内容（简化）
    for i in range(1, 9):
        y -= 30
        page_key = f'page{i}'
        if page_key in report_content:
            c.setFont("Helvetica-Bold", 14)
            c.drawString(100, y, f"第{i}页：{report_content[page_key].get('title', '')}")
            y -= 15
            c.setFont("Helvetica", 10)
            content = report_content[page_key].get('content', '')[:200] + '...'
            c.drawString(100, y, content)
        
        if y < 100:
            c.showPage()
            y = 750
    
    c.save()
    buffer.seek(0)
    return buffer
