"""
Supabase Auth（与 Horse racing 同款）：邮箱 + 密码 → auth.users，再同步本 App sf_users。
密码只存 Supabase Auth，不写入 sf_users。
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import requests


class AuthError(Exception):
    pass


class SupabaseAuth:
    def __init__(self, url: str, anon_key: str, service_key: Optional[str] = None):
        self.url = (url or "").rstrip("/")
        self.anon_key = anon_key or ""
        self.service_key = service_key or ""
        self.last_error: Optional[str] = None

    @property
    def configured(self) -> bool:
        return bool(self.url and self.anon_key)

    def _anon_headers(self) -> Dict[str, str]:
        return {
            "apikey": self.anon_key,
            "Content-Type": "application/json",
        }

    def _service_headers(self) -> Dict[str, str]:
        key = self.service_key or self.anon_key
        return {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def sign_up(self, email: str, password: str) -> Tuple[bool, str, Optional[str]]:
        """
        注册。成功返回 (True, msg, auth_user_id)。
        若邮箱已在 Auth 存在，返回 (False, 'exists', None) 便于前端引导登录。
        """
        self.last_error = None
        email = (email or "").strip().lower()
        if not email or not password:
            return False, "请填写邮箱和密码", None
        if len(password) < 6:
            return False, "密码至少 6 位", None
        try:
            resp = requests.post(
                f"{self.url}/auth/v1/signup",
                headers=self._anon_headers(),
                json={"email": email, "password": password},
                timeout=30,
            )
            data = resp.json() if resp.content else {}
            if resp.status_code in (200, 201):
                user = data.get("user") or {}
                uid = user.get("id")
                # 部分项目需邮箱确认，uid 仍可用
                if uid:
                    return True, "注册成功", uid
                # 极少数返回只有 session
                uid = (data.get("session") or {}).get("user", {}).get("id")
                if uid:
                    return True, "注册成功", uid
                return True, "注册成功，请查收确认邮件后登录", None

            msg = str(data.get("msg") or data.get("error_description") or data.get("error") or data)
            low = msg.lower()
            if "already" in low or "registered" in low or "exists" in low:
                return False, "exists", None
            self.last_error = msg
            return False, f"注册失败：{msg}", None
        except Exception as e:
            self.last_error = str(e)
            return False, f"注册失败：{e}", None

    def sign_in(self, email: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        密码登录。成功返回 (True, msg, {user_id, email, access_token, refresh_token})。
        """
        self.last_error = None
        email = (email or "").strip().lower()
        if not email or not password:
            return False, "请填写邮箱和密码", None
        try:
            resp = requests.post(
                f"{self.url}/auth/v1/token?grant_type=password",
                headers=self._anon_headers(),
                json={"email": email, "password": password},
                timeout=30,
            )
            data = resp.json() if resp.content else {}
            if resp.status_code != 200:
                self.last_error = str(data)
                return False, "邮箱或密码错误", None
            user = data.get("user") or {}
            uid = user.get("id")
            uemail = (user.get("email") or email).strip().lower()
            access = data.get("access_token")
            refresh = data.get("refresh_token")
            if not uid or not access:
                return False, "登录响应不完整，请重试", None
            return True, "登录成功", {
                "user_id": uid,
                "email": uemail,
                "access_token": access,
                "refresh_token": refresh,
            }
        except Exception as e:
            self.last_error = str(e)
            return False, f"登录失败：{e}", None

    def admin_find_user_id_by_email(self, email: str) -> Optional[str]:
        """service_role 下按邮箱查 Auth 用户 id（用于已注册用户补建 sf_users）。"""
        if not self.service_key:
            return None
        email = (email or "").strip().lower()
        try:
            # 新 Admin API
            resp = requests.get(
                f"{self.url}/auth/v1/admin/users",
                headers=self._service_headers(),
                params={"page": 1, "per_page": 200},
                timeout=30,
            )
            if resp.status_code != 200:
                return None
            payload = resp.json()
            users = payload.get("users") if isinstance(payload, dict) else payload
            for u in users or []:
                if (u.get("email") or "").strip().lower() == email:
                    return u.get("id")
        except Exception as e:
            self.last_error = str(e)
        return None
