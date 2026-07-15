"""
本 App 独立认证（不使用共享 Supabase Auth）。
密码只存 sf_users.password_hash，与其他 App 完全隔离。
旧版 auth_supabase.py 已弃用，请勿再接入 shared Auth。
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Optional


_ITERATIONS = 120_000
_PREFIX = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        (password or "").encode("utf-8"),
        salt.encode("utf-8"),
        _ITERATIONS,
    )
    return f"{_PREFIX}${_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    if not stored or not password:
        return False
    try:
        parts = stored.split("$")
        if len(parts) != 4 or parts[0] != _PREFIX:
            return False
        iterations = int(parts[1])
        salt = parts[2]
        expected = parts[3]
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return hmac.compare_digest(dk.hex(), expected)
    except Exception:
        return False
