"""简繁转换：优先 OpenCC，失败则原样返回。"""
from __future__ import annotations

_cc_s2t = None
_cc_t2s = None


def to_traditional(text: str) -> str:
    if not text:
        return text
    global _cc_s2t
    try:
        if _cc_s2t is None:
            from opencc import OpenCC

            _cc_s2t = OpenCC("s2t")
        return _cc_s2t.convert(text)
    except Exception:
        return text


def to_simplified(text: str) -> str:
    if not text:
        return text
    global _cc_t2s
    try:
        if _cc_t2s is None:
            from opencc import OpenCC

            _cc_t2s = OpenCC("t2s")
        return _cc_t2s.convert(text)
    except Exception:
        return text
