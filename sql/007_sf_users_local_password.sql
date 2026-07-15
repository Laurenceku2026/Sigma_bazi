-- 本 App 独立密码：与共享 Supabase Auth / 其他 App 完全隔离
ALTER TABLE app_sigma_fate.sf_users
    ADD COLUMN IF NOT EXISTS password_hash TEXT;

-- 同一 App 内邮箱唯一（小写）
CREATE UNIQUE INDEX IF NOT EXISTS idx_sf_users_app_email_unique
    ON app_sigma_fate.sf_users (app_id, lower(email))
    WHERE email IS NOT NULL AND btrim(email) <> '';

COMMENT ON COLUMN app_sigma_fate.sf_users.password_hash IS
    '本八字 App 独立口令哈希；不读写 auth.users，与其他 App 账号无关';

NOTIFY pgrst, 'reload schema';
