-- 管理员用户管理所需字段（可重复执行）
ALTER TABLE app_sigma_fate.users
    ADD COLUMN IF NOT EXISTS free_trials_remaining INTEGER DEFAULT 30,
    ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS email_confirmed BOOLEAN DEFAULT FALSE;

UPDATE app_sigma_fate.users
SET free_trials_remaining = COALESCE(free_trials_remaining, 30)
WHERE free_trials_remaining IS NULL;

NOTIFY pgrst, 'reload schema';
