"""简繁转换：优先 OpenCC，失败则原样返回。"""
from __future__ import annotations

_cc = None


def to_traditional(text: str) -> str:
    if not text:
        return text
    global _cc
    try:
        if _cc is None:
            from opencc import OpenCC

            _cc = OpenCC("s2t")
        return _cc.convert(text)
    except Exception:
        return text
