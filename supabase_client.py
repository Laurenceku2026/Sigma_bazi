"""
Supabase 客户端 — 同一项目下多 App 隔离

隔离策略：
1. 物理隔离：专属 schema（默认 app_sigma_fate），不读写其他 App 的表
2. 逻辑隔离：所有行写入/查询都带 app_id
3. 登录校验：ensure_app_user / verify_app_access 只认本 App 用户
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from supabase import Client, ClientOptions, create_client


class AppAccessDenied(PermissionError):
    """用户不属于当前 App，或无权访问本 App 数据。"""


class SupabaseClient:
    """同一 Supabase 项目内、按 schema + app_id 隔离的客户端。"""

    DEFAULT_APP_ID = "sigma_fate_v1"
    DEFAULT_SCHEMA = "app_sigma_fate"
    USER_TABLE = "sf_users"  # 专用表名，避免误读 public.users / 其他 App

    def __init__(
        self,
        url: str,
        key: str,
        *,
        app_id: Optional[str] = None,
        schema: Optional[str] = None,
        use_service_role: bool = False,
    ):
        if not url or not key:
            raise ValueError("Supabase URL and key are required")

        self.app_id = app_id or os.getenv("APP_ID", self.DEFAULT_APP_ID)
        self.schema = schema or os.getenv("SUPABASE_APP_SCHEMA", self.DEFAULT_SCHEMA)
        self.use_service_role = use_service_role

        options = ClientOptions(schema=self.schema)
        self.client: Client = create_client(url, key, options=options)
        self.last_error: Optional[str] = None
        # 强制 PostgREST 读写本 App schema（防止落到 public 其他 App 表）
        self._apply_schema_headers()

    def _apply_schema_headers(self) -> None:
        try:
            headers = {
                "Accept-Profile": self.schema,
                "Content-Profile": self.schema,
            }
            # supabase-py / postgrest-py 常见路径
            postgrest = getattr(self.client, "postgrest", None)
            if postgrest is not None:
                session = getattr(postgrest, "session", None)
                if session is not None and hasattr(session, "headers"):
                    session.headers.update(headers)
                if hasattr(postgrest, "schema"):
                    try:
                        postgrest.schema(self.schema)
                    except Exception:
                        pass
        except Exception as e:
            print(f"schema header setup: {e}")

    # ---------- 内部工具 ----------

    def _table(self, table_name: str):
        """始终落在本 App schema，避免误打 public 或其他 App。"""
        self._apply_schema_headers()
        # 禁止在未锁定 schema 时直接 client.table()
        return self.client.schema(self.schema).table(table_name)

    def _is_own_user_row(self, row: Dict[str, Any]) -> bool:
        """只认本 App 用户行，过滤掉 public.profiles 等其他表混入数据。"""
        if not isinstance(row, dict):
            return False
        if row.get("app_id") != self.app_id:
            return False
        # 本表字段：user_id；拒绝门户 profiles（通常只有 id uuid）
        if not row.get("user_id"):
            return False
        return True

    def _filter_own_users(self, rows: Optional[List[Dict]]) -> List[Dict]:
        own = [r for r in (rows or []) if self._is_own_user_row(r)]
        dropped = len(rows or []) - len(own)
        if dropped > 0:
            self.last_error = (
                f"已隔离丢弃 {dropped} 条非本 App 记录"
                f"（仅保留 schema={self.schema}, app_id={self.app_id}）"
            )
        return own

    def _now(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _with_app_id(self, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(data)
        payload["app_id"] = self.app_id
        return payload

    def _set_error(self, where: str, err: Exception) -> None:
        self.last_error = f"{where}: {err}"
        print(self.last_error)

    # ---------- 登录 / 权限校验 ----------

    def verify_app_access(
        self,
        user_id: str,
        *,
        auth_user_id: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        校验用户是否属于本 App。

        规则：
        - 只在本 schema.users 中查
        - 必须匹配 app_id
        - 若找到用户但 app_id 不符（理论上不应发生），拒绝访问
        """
        user = self.get_user(user_id)
        if user is None and auth_user_id:
            user = self.get_user_by_auth_id(auth_user_id)
        if user is None and email:
            user = self.get_user_by_email(email)

        if user is None:
            raise AppAccessDenied(
                f"User not registered for app_id={self.app_id}"
            )

        if user.get("app_id") != self.app_id:
            raise AppAccessDenied(
                f"Cross-app access denied: user app_id={user.get('app_id')} "
                f"!= current app_id={self.app_id}"
            )

        return user

    def register_by_email(
        self,
        email: str,
        session_user_id: str,
        *,
        subscription_tier: str = "free",
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        邮箱注册/登录（无需密码）。
        - 若邮箱已存在：返回该用户并刷新 last_login
        - 若不存在：创建新用户并读回校验
        """
        self.last_error = None
        email = (email or "").strip().lower()
        if not email:
            raise ValueError("email required")

        existing = self.get_user_by_email(email)
        if existing:
            try:
                self._table(self.USER_TABLE).update(
                    {
                        "last_login_at": self._now(),
                        "updated_at": self._now(),
                        "email_confirmed": True,
                    }
                ).eq("user_id", existing["user_id"]).eq("app_id", self.app_id).execute()
            except Exception as e:
                self._set_error("register_by_email.update", e)
            return existing

        data = self._with_app_id(
            {
                "user_id": session_user_id,
                "auth_user_id": session_user_id,
                "email": email,
                "subscription_tier": subscription_tier if subscription_tier in (
                    "free", "silver", "gold", "diamond", "monthly", "quarterly", "annual"
                ) else "free",
                "free_trials_remaining": 30,
                "email_confirmed": True,
                "metadata": metadata or {"source": "email_register"},
                "created_at": self._now(),
                "updated_at": self._now(),
                "last_login_at": self._now(),
            }
        )
        try:
            result = (
                self._table(self.USER_TABLE)
                .upsert(data, on_conflict="user_id,app_id")
                .execute()
            )
            saved = result.data[0] if result.data else None
        except Exception as e:
            self._set_error("register_by_email.insert", e)
            raise

        # 读回校验：管理员列表依赖库中真实记录
        verified = self.get_user_by_email(email) or self.get_user(session_user_id)
        if not verified:
            err = (
                "用户写入后读回失败。请确认已执行 sql/001 且 "
                "Exposed schemas 含 app_sigma_fate，Secrets 中 URL/Key 为同一项目。"
            )
            self.last_error = err
            raise RuntimeError(err + (f" | {self.last_error}" if saved is None else ""))
        return verified

    def ensure_app_user(
        self,
        user_id: str,
        email: Optional[str] = None,
        *,
        auth_user_id: Optional[str] = None,
        subscription_tier: str = "free",
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        登录入口：在本 App 内创建或同步用户。
        """
        self.last_error = None
        if email:
            try:
                return self.register_by_email(
                    email,
                    user_id,
                    subscription_tier=subscription_tier,
                    metadata=metadata,
                )
            except Exception:
                # 已设置 last_error；继续尝试 user_id 路径
                pass

        existing = self.get_user(user_id)
        if existing and existing.get("app_id") == self.app_id:
            updates: Dict[str, Any] = {"updated_at": self._now(), "last_login_at": self._now()}
            if email:
                updates["email"] = email
            if metadata is not None:
                updates["metadata"] = metadata
            try:
                self._table(self.USER_TABLE).update(updates).eq(
                    "user_id", user_id
                ).eq("app_id", self.app_id).execute()
            except Exception as e:
                self._set_error("ensure_app_user sync", e)
            return {**existing, **updates}

        return self.create_or_update_user(
            user_id=user_id,
            email=email or f"{user_id[:8]}@sigma-fate.local",
            auth_user_id=auth_user_id or user_id,
            subscription_tier=subscription_tier,
            metadata=metadata,
        )

    # ---------- 用户操作 ----------

    def create_or_update_user(
        self,
        user_id: str,
        email: str,
        subscription_tier: str = "free",
        metadata: Optional[Dict] = None,
        auth_user_id: Optional[str] = None,
    ) -> Dict:
        """创建或更新本 App 用户（upsert on user_id + app_id）。"""
        self.last_error = None
        tier = subscription_tier if subscription_tier in (
            "free", "silver", "gold", "diamond", "monthly", "quarterly", "annual"
        ) else "free"
        data = self._with_app_id(
            {
                "user_id": user_id,
                "auth_user_id": auth_user_id or user_id,
                "email": email,
                "subscription_tier": tier,
                "free_trials_remaining": 30,
                "metadata": metadata or {},
                "created_at": self._now(),
                "updated_at": self._now(),
                "last_login_at": self._now(),
            }
        )

        try:
            result = (
                self._table(self.USER_TABLE)
                .upsert(data, on_conflict="user_id,app_id")
                .execute()
            )
            if result.data:
                return result.data[0]
            # upsert 无返回时再查一次
            verified = self.get_user(user_id) or self.get_user_by_email(email)
            if verified:
                return verified
            self.last_error = "upsert 无返回数据且读回为空"
            return data
        except Exception as e:
            self._set_error("User upsert", e)
            raise

    def get_user(self, user_id: str) -> Optional[Dict]:
        try:
            result = (
                self._table(self.USER_TABLE)
                .select("*")
                .eq("user_id", user_id)
                .eq("app_id", self.app_id)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            self._set_error("Get user", e)
            return None

    def get_user_by_auth_id(self, auth_user_id: str) -> Optional[Dict]:
        try:
            result = (
                self._table(self.USER_TABLE)
                .select("*")
                .eq("auth_user_id", auth_user_id)
                .eq("app_id", self.app_id)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            self._set_error("Get user by auth_id", e)
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        try:
            result = (
                self._table(self.USER_TABLE)
                .select("*")
                .eq("email", email.strip().lower() if email else email)
                .eq("app_id", self.app_id)
                .limit(1)
                .execute()
            )
            # 兼容大小写存错：再试原样
            if not result.data and email:
                result = (
                    self._table(self.USER_TABLE)
                    .select("*")
                    .ilike("email", email.strip())
                    .eq("app_id", self.app_id)
                    .limit(1)
                    .execute()
                )
            return result.data[0] if result.data else None
        except Exception as e:
            self._set_error("Get user by email", e)
            return None

    def login_by_email(self, email: str) -> Optional[Dict]:
        """邮箱登录：只查找已有用户，不新建。成功则刷新 last_login。"""
        self.last_error = None
        if not email or not str(email).strip():
            self.last_error = "email required"
            return None
        profile = self.get_user_by_email(email.strip())
        if not profile:
            self.last_error = "account_not_found"
            return None
        try:
            self._table(self.USER_TABLE).update(
                {
                    "last_login_at": self._now(),
                    "updated_at": self._now(),
                    "email_confirmed": True,
                }
            ).eq("user_id", profile["user_id"]).eq("app_id", self.app_id).execute()
        except Exception as e:
            self._set_error("login_by_email.update", e)
        refreshed = self.get_user(profile["user_id"]) or profile
        return refreshed

    def update_subscription(
        self,
        user_id: str,
        tier: str,
        stripe_customer_id: Optional[str] = None,
    ) -> bool:
        try:
            data: Dict[str, Any] = {
                "subscription_tier": tier,
                "updated_at": self._now(),
            }
            if stripe_customer_id:
                data["stripe_customer_id"] = stripe_customer_id

            result = (
                self._table(self.USER_TABLE)
                .update(data)
                .eq("user_id", user_id)
                .eq("app_id", self.app_id)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            print(f"Update subscription error: {e}")
            return False

    def has_active_subscription(self, user_id: str) -> bool:
        user = self.get_user(user_id)
        if not user or user.get("app_id") != self.app_id:
            return False
        return user.get("subscription_tier") in (
            "silver", "gold", "diamond", "monthly", "quarterly", "annual"
        )

    def apply_membership_tier(self, user_id: str, tier: str) -> bool:
        """支付成功后应用会员档（银/金/钻）。"""
        from datetime import timedelta

        trials = 10
        expires = None
        if tier == "diamond":
            trials = 9999
            exp = datetime.utcnow() + timedelta(days=365)
            expires = exp.isoformat() + "Z"
        return self.admin_update_user(
            user_id,
            subscription_tier=tier,
            free_trials_remaining=trials,
            subscription_expires_at=expires,
        )

    def consume_report_quota(self, user_id: str) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        tier = user.get("subscription_tier", "free")
        if tier == "diamond":
            return True
        if tier in ("silver", "gold"):
            remaining = int(user.get("free_trials_remaining") or 0)
            if remaining <= 0:
                return False
            return self.admin_update_user(user_id, free_trials_remaining=remaining - 1)
        return False

    # ---------- 管理员：用户列表 / 订阅 / 次数 ----------

    def list_users(self, limit: int = 500) -> List[Dict]:
        """仅返回本 App（schema + app_id）用户，绝不分其他 App。"""
        self.last_error = None
        try:
            result = (
                self._table(self.USER_TABLE)
                .select("*")
                .eq("app_id", self.app_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return self._filter_own_users(result.data)
        except Exception as e:
            self._set_error("List users", e)
            try:
                result = (
                    self._table(self.USER_TABLE)
                    .select("user_id,email,app_id,subscription_tier,free_trials_remaining,"
                            "subscription_expires_at,created_at,last_login_at,email_confirmed")
                    .eq("app_id", self.app_id)
                    .limit(limit)
                    .execute()
                )
                return self._filter_own_users(result.data)
            except Exception as e2:
                self._set_error("List users fallback", e2)
                return []

    def purge_foreign_users(self) -> int:
        """删除误写入本 schema 但 app_id 不是本 App 的行。"""
        try:
            result = (
                self._table(self.USER_TABLE)
                .delete()
                .neq("app_id", self.app_id)
                .execute()
            )
            return len(result.data or [])
        except Exception as e:
            self._set_error("purge_foreign_users", e)
            return 0

    def admin_reset_free_trials(self, default_trials: int = 30) -> int:
        """重置所有 free 用户次数，返回更新条数。"""
        try:
            result = (
                self._table(self.USER_TABLE)
                .update(
                    {
                        "free_trials_remaining": default_trials,
                        "updated_at": self._now(),
                    }
                )
                .eq("app_id", self.app_id)
                .eq("subscription_tier", "free")
                .execute()
            )
            return len(result.data or [])
        except Exception as e:
            print(f"Admin reset free trials error: {e}")
            return 0

    def admin_update_user(
        self,
        user_id: str,
        *,
        subscription_tier: Optional[str] = None,
        free_trials_remaining: Optional[int] = None,
        subscription_expires_at: Optional[str] = None,
        email_confirmed: Optional[bool] = None,
    ) -> bool:
        try:
            data: Dict[str, Any] = {"updated_at": self._now()}
            if subscription_tier is not None:
                data["subscription_tier"] = subscription_tier
            if free_trials_remaining is not None:
                data["free_trials_remaining"] = int(free_trials_remaining)
            if subscription_expires_at is not None:
                data["subscription_expires_at"] = subscription_expires_at
            if email_confirmed is not None:
                data["email_confirmed"] = email_confirmed

            result = (
                self._table(self.USER_TABLE)
                .update(data)
                .eq("user_id", user_id)
                .eq("app_id", self.app_id)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            print(f"Admin update user error: {e}")
            return False

    def admin_delete_user(self, user_id: str) -> bool:
        try:
            # 先删关联报告与支付，再删用户
            self._table("reports").delete().eq("user_id", user_id).eq(
                "app_id", self.app_id
            ).execute()
            self._table("payments").delete().eq("user_id", user_id).eq(
                "app_id", self.app_id
            ).execute()
            result = (
                self._table(self.USER_TABLE)
                .delete()
                .eq("user_id", user_id)
                .eq("app_id", self.app_id)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            print(f"Admin delete user error: {e}")
            return False

    def save_user_profile(self, user_id: str, birth_info: Dict) -> bool:
        """注册/排盘后写入姓名、生日等资料到 sf_users。"""
        if not user_id or not birth_info:
            return False
        data: Dict[str, Any] = {
            "updated_at": self._now(),
            "last_birth_info": birth_info,
        }
        if birth_info.get("name"):
            data["display_name"] = str(birth_info["name"]).strip()
        if birth_info.get("gender"):
            data["gender"] = birth_info["gender"]
        if birth_info.get("birth_date"):
            data["birth_date"] = birth_info["birth_date"]
        if birth_info.get("birth_hour") is not None:
            try:
                data["birth_hour"] = int(birth_info["birth_hour"])
            except (TypeError, ValueError):
                pass
        if birth_info.get("birth_minute") is not None:
            try:
                data["birth_minute"] = int(birth_info["birth_minute"])
            except (TypeError, ValueError):
                pass
        if birth_info.get("region_id"):
            data["region_id"] = birth_info["region_id"]
        if birth_info.get("birth_place") is not None:
            data["birth_place"] = birth_info.get("birth_place") or ""
        if birth_info.get("email"):
            data["email"] = str(birth_info["email"]).strip().lower()

        try:
            result = (
                self._table(self.USER_TABLE)
                .update(data)
                .eq("user_id", user_id)
                .eq("app_id", self.app_id)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            self._set_error("save_user_profile", e)
            return False

    def purge_anonymous_users(self) -> int:
        """删除无邮箱的测试/匿名行（仅本 app_id）。"""
        try:
            result = (
                self._table(self.USER_TABLE)
                .delete()
                .eq("app_id", self.app_id)
                .is_("email", "null")
                .execute()
            )
            n1 = len(result.data or [])
        except Exception as e:
            self._set_error("purge_anonymous_users.null", e)
            n1 = 0
        try:
            result2 = (
                self._table(self.USER_TABLE)
                .delete()
                .eq("app_id", self.app_id)
                .eq("email", "")
                .execute()
            )
            n2 = len(result2.data or [])
        except Exception as e:
            self._set_error("purge_anonymous_users.empty", e)
            n2 = 0
        return n1 + n2

    def purge_users_without_profile(self) -> int:
        """删除从未排盘的用户（无姓名且无生日），只保留真实使用本 App 的记录。"""
        users = self.list_users(limit=1000)
        deleted = 0
        for u in users:
            has_name = bool(str(u.get("display_name") or "").strip())
            has_birth = bool(u.get("birth_date"))
            if has_name or has_birth:
                continue
            uid = u.get("user_id")
            if not uid:
                continue
            if self.admin_delete_user(uid):
                deleted += 1
        return deleted

    # ---------- 报告 ----------

    def save_report(
        self,
        user_id: str,
        birth_info: Dict,
        bazi_data: Dict,
        report_content: Dict,
        report_id: Optional[str] = None,
        payment_tier: str = "monthly",
    ) -> Dict:
        # 写入前校验：防止把报告写到非本 App 用户名下
        self.verify_app_access(user_id)

        data = self._with_app_id(
            {
                "report_id": report_id or self._generate_report_id(),
                "user_id": user_id,
                "birth_info": birth_info,
                "bazi_data": bazi_data,
                "report_content": report_content,
                "payment_tier": payment_tier,
                "created_at": self._now(),
            }
        )

        try:
            result = self._table("reports").insert(data).execute()
            return result.data[0] if result.data else data
        except Exception as e:
            print(f"Save report error: {e}")
            return data

    def get_reports(self, user_id: str, limit: int = 10) -> List[Dict]:
        try:
            self.verify_app_access(user_id)
            result = (
                self._table("reports")
                .select("*")
                .eq("user_id", user_id)
                .eq("app_id", self.app_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []
        except AppAccessDenied:
            raise
        except Exception as e:
            print(f"Get reports error: {e}")
            return []

    def get_report(self, report_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
        try:
            query = (
                self._table("reports")
                .select("*")
                .eq("report_id", report_id)
                .eq("app_id", self.app_id)
            )
            if user_id:
                query = query.eq("user_id", user_id)
            result = query.limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Get report error: {e}")
            return None

    def delete_report(self, report_id: str, user_id: str) -> bool:
        try:
            self.verify_app_access(user_id)
            result = (
                self._table("reports")
                .delete()
                .eq("report_id", report_id)
                .eq("user_id", user_id)
                .eq("app_id", self.app_id)
                .execute()
            )
            return bool(result.data)
        except AppAccessDenied:
            raise
        except Exception as e:
            print(f"Delete report error: {e}")
            return False

    # ---------- 支付 ----------

    def save_payment(
        self,
        user_id: str,
        payment_id: str,
        stripe_session_id: str,
        amount: int,
        tier: str,
        status: str = "pending",
    ) -> Dict:
        self.verify_app_access(user_id)

        data = self._with_app_id(
            {
                "user_id": user_id,
                "payment_id": payment_id,
                "stripe_session_id": stripe_session_id,
                "amount": amount,
                "currency": "CNY",
                "tier": tier,
                "status": status,
                "created_at": self._now(),
            }
        )

        try:
            result = self._table("payments").insert(data).execute()
            return result.data[0] if result.data else data
        except Exception as e:
            print(f"Save payment error: {e}")
            return data

    def update_payment_status(self, payment_id: str, status: str) -> bool:
        try:
            data: Dict[str, Any] = {"status": status}
            if status == "success":
                data["completed_at"] = self._now()

            result = (
                self._table("payments")
                .update(data)
                .eq("payment_id", payment_id)
                .eq("app_id", self.app_id)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            print(f"Update payment error: {e}")
            return False

    # ---------- 访问日志 ----------

    def log_action(
        self,
        user_id: str,
        action: str,
        metadata: Optional[Dict] = None,
    ) -> bool:
        try:
            data = self._with_app_id(
                {
                    "user_id": user_id,
                    "action": action,
                    "metadata": metadata or {},
                    "created_at": self._now(),
                }
            )
            result = self._table("access_logs").insert(data).execute()
            return bool(result.data)
        except Exception as e:
            print(f"Log action error: {e}")
            return False

    # ---------- 工具 ----------

    def _generate_report_id(self) -> str:
        return f"sf_{uuid.uuid4().hex[:12]}"


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    client = SupabaseClient(
        url=os.getenv("SUPABASE_STOCK_URL", ""),
        key=os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_STOCK_ANON_KEY", ""),
        use_service_role=bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
    )
    print(f"schema={client.schema} app_id={client.app_id}")

    result = client.ensure_app_user(
        user_id="test_user_sigma_fate",
        email="test@example.com",
        subscription_tier="free",
        metadata={"source": "cli_smoke_test"},
    )
    print("User:", result.get("user_id"), result.get("app_id"))
