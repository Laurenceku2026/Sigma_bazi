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
