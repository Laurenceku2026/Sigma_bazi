"""手机主屏幕 / PWA 图标与 meta 注入（iOS Safari、Android Chrome、华为/小米/vivo 等）。"""
from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

_STATIC = Path(__file__).resolve().parent / "static"


def _b64_png(name: str) -> str:
    path = _STATIC / name
    if not path.is_file():
        return ""
    return base64.b64encode(path.read_bytes()).decode("ascii")


def app_icon_path() -> str:
    p = _STATIC / "app_icon.png"
    return str(p) if p.is_file() else ""


def inject_mobile_app_meta(*, manifest_url: str = "") -> None:
    """在页面注入 apple-touch-icon、theme-color、manifest（供「添加到主屏幕」）。"""
    apple = _b64_png("apple-touch-icon.png")
    fav32 = _b64_png("favicon-32.png")
    if not apple and not fav32:
        return

    links = []
    if apple:
        links.append(f'<link rel="apple-touch-icon" sizes="180x180" href="data:image/png;base64,{apple}">')
    if fav32:
        links.append(f'<link rel="icon" type="image/png" sizes="32x32" href="data:image/png;base64,{fav32}">')
    if manifest_url:
        links.append(f'<link rel="manifest" href="{manifest_url}">')

    st.markdown(
        "\n".join(links)
        + """
<meta name="theme-color" content="#0B1F33">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Sigma Fate">
<meta name="mobile-web-app-capable" content="yes">
<meta name="application-name" content="Sigma Fate">
""",
        unsafe_allow_html=True,
    )
