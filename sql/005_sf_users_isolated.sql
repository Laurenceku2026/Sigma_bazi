-- =============================================================================
-- 使用独立表名 sf_users，避免与 public.users / 其他 App 的 users 混淆
-- =============================================================================

CREATE TABLE IF NOT EXISTS app_sigma_fate.sf_users (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             TEXT NOT NULL,
    auth_user_id        TEXT,
    email               TEXT,
    app_id              TEXT NOT NULL DEFAULT 'sigma_fate_v1',
    subscription_tier   TEXT NOT NULL DEFAULT 'free',
    free_trials_remaining INTEGER DEFAULT 30,
    subscription_expires_at TIMESTAMPTZ,
    last_login_at       TIMESTAMPTZ,
    email_confirmed     BOOLEAN DEFAULT FALSE,
    -- 排盘资料（会员/注册后保存）
    display_name        TEXT,
    gender              TEXT,
    birth_date          DATE,
    birth_hour          INTEGER,
    birth_minute        INTEGER,
    region_id           TEXT,
    birth_place         TEXT,
    last_birth_info     JSONB NOT NULL DEFAULT '{}'::jsonb,
    stripe_customer_id  TEXT,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT sf_users_user_app_uniq UNIQUE (user_id, app_id),
    CONSTRAINT sf_users_auth_app_uniq UNIQUE (auth_user_id, app_id),
    CONSTRAINT sf_users_tier_check CHECK (subscription_tier IN (
        'free', 'silver', 'gold', 'diamond', 'monthly', 'quarterly', 'annual', 'pro'
    ))
);

CREATE INDEX IF NOT EXISTS idx_sf_users_app_email
    ON app_sigma_fate.sf_users (app_id, email);

-- 从旧 users 表迁移「仅本 App」记录（若存在）
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'app_sigma_fate' AND table_name = 'users'
  ) THEN
    INSERT INTO app_sigma_fate.sf_users (
      user_id, auth_user_id, email, app_id, subscription_tier,
      free_trials_remaining, subscription_expires_at, last_login_at,
      email_confirmed, metadata, created_at, updated_at
    )
    SELECT
      user_id, auth_user_id, email, app_id, subscription_tier,
      COALESCE(free_trials_remaining, 30), subscription_expires_at, last_login_at,
      COALESCE(email_confirmed, FALSE), COALESCE(metadata, '{}'::jsonb),
      COALESCE(created_at, NOW()), COALESCE(updated_at, NOW())
    FROM app_sigma_fate.users
    WHERE app_id = 'sigma_fate_v1'
    ON CONFLICT (user_id, app_id) DO NOTHING;
  END IF;
END $$;

-- 若误把其他 App 数据迁入，清掉
DELETE FROM app_sigma_fate.sf_users WHERE app_id IS DISTINCT FROM 'sigma_fate_v1';

ALTER TABLE app_sigma_fate.sf_users ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS sf_users_app_isolation ON app_sigma_fate.sf_users;
CREATE POLICY sf_users_app_isolation ON app_sigma_fate.sf_users
    FOR ALL
    USING (app_id = 'sigma_fate_v1')
    WITH CHECK (app_id = 'sigma_fate_v1');

GRANT SELECT, INSERT, UPDATE, DELETE ON app_sigma_fate.sf_users TO anon, authenticated, service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app_sigma_fate TO anon, authenticated, service_role;

DROP TRIGGER IF EXISTS trg_sf_users_enforce_app_id ON app_sigma_fate.sf_users;
CREATE TRIGGER trg_sf_users_enforce_app_id
    BEFORE INSERT OR UPDATE ON app_sigma_fate.sf_users
    FOR EACH ROW EXECUTE FUNCTION app_sigma_fate.enforce_app_id();

NOTIFY pgrst, 'reload schema';
