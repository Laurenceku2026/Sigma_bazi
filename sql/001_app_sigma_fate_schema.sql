-- =============================================================================
-- Sigma Fate (BaZi) — 多 App 隔离 Schema（可重复执行）
--
-- 42703 column "app_id" does not exist 的常见原因：
-- 表已存在但没有 app_id，CREATE TABLE IF NOT EXISTS 不会补列，
-- 后面的 INDEX / POLICY 引用 app_id 就会报错。
-- 本脚本会：建表 → 补齐缺失列 → 再建索引/约束/RLS/暴露 schema。
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS app_sigma_fate;

-- ---------- 建表（仅在不存在时创建；已存在的旧表靠下面 ALTER 补列） ----------
CREATE TABLE IF NOT EXISTS app_sigma_fate.users (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             TEXT NOT NULL,
    auth_user_id        TEXT,
    email               TEXT,
    app_id              TEXT NOT NULL DEFAULT 'sigma_fate_v1',
    subscription_tier   TEXT NOT NULL DEFAULT 'free',
    stripe_customer_id  TEXT,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app_sigma_fate.reports (
    id                  BIGSERIAL PRIMARY KEY,
    report_id           TEXT NOT NULL,
    user_id             TEXT NOT NULL,
    app_id              TEXT NOT NULL DEFAULT 'sigma_fate_v1',
    birth_info          JSONB NOT NULL DEFAULT '{}'::jsonb,
    bazi_data           JSONB NOT NULL DEFAULT '{}'::jsonb,
    report_content      JSONB NOT NULL DEFAULT '{}'::jsonb,
    payment_tier        TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app_sigma_fate.payments (
    id                  BIGSERIAL PRIMARY KEY,
    payment_id          TEXT NOT NULL,
    user_id             TEXT NOT NULL,
    app_id              TEXT NOT NULL DEFAULT 'sigma_fate_v1',
    stripe_session_id   TEXT,
    amount              INTEGER,
    currency            TEXT DEFAULT 'CNY',
    tier                TEXT,
    status              TEXT NOT NULL DEFAULT 'pending',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS app_sigma_fate.access_logs (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             TEXT,
    app_id              TEXT NOT NULL DEFAULT 'sigma_fate_v1',
    action              TEXT NOT NULL,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------- 补齐旧表缺失列（解决 42703） ----------
ALTER TABLE app_sigma_fate.users
    ADD COLUMN IF NOT EXISTS user_id TEXT,
    ADD COLUMN IF NOT EXISTS auth_user_id TEXT,
    ADD COLUMN IF NOT EXISTS email TEXT,
    ADD COLUMN IF NOT EXISTS app_id TEXT,
    ADD COLUMN IF NOT EXISTS subscription_tier TEXT,
    ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT,
    ADD COLUMN IF NOT EXISTS metadata JSONB,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

ALTER TABLE app_sigma_fate.reports
    ADD COLUMN IF NOT EXISTS report_id TEXT,
    ADD COLUMN IF NOT EXISTS user_id TEXT,
    ADD COLUMN IF NOT EXISTS app_id TEXT,
    ADD COLUMN IF NOT EXISTS birth_info JSONB,
    ADD COLUMN IF NOT EXISTS bazi_data JSONB,
    ADD COLUMN IF NOT EXISTS report_content JSONB,
    ADD COLUMN IF NOT EXISTS payment_tier TEXT,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;

ALTER TABLE app_sigma_fate.payments
    ADD COLUMN IF NOT EXISTS payment_id TEXT,
    ADD COLUMN IF NOT EXISTS user_id TEXT,
    ADD COLUMN IF NOT EXISTS app_id TEXT,
    ADD COLUMN IF NOT EXISTS stripe_session_id TEXT,
    ADD COLUMN IF NOT EXISTS amount INTEGER,
    ADD COLUMN IF NOT EXISTS currency TEXT,
    ADD COLUMN IF NOT EXISTS tier TEXT,
    ADD COLUMN IF NOT EXISTS status TEXT,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

ALTER TABLE app_sigma_fate.access_logs
    ADD COLUMN IF NOT EXISTS user_id TEXT,
    ADD COLUMN IF NOT EXISTS app_id TEXT,
    ADD COLUMN IF NOT EXISTS action TEXT,
    ADD COLUMN IF NOT EXISTS metadata JSONB,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ;

-- 填充默认值，再收紧 NOT NULL
UPDATE app_sigma_fate.users
SET app_id = COALESCE(NULLIF(app_id, ''), 'sigma_fate_v1'),
    subscription_tier = COALESCE(NULLIF(subscription_tier, ''), 'free'),
    metadata = COALESCE(metadata, '{}'::jsonb),
    created_at = COALESCE(created_at, NOW()),
    updated_at = COALESCE(updated_at, NOW());

UPDATE app_sigma_fate.reports
SET app_id = COALESCE(NULLIF(app_id, ''), 'sigma_fate_v1'),
    birth_info = COALESCE(birth_info, '{}'::jsonb),
    bazi_data = COALESCE(bazi_data, '{}'::jsonb),
    report_content = COALESCE(report_content, '{}'::jsonb),
    created_at = COALESCE(created_at, NOW());

UPDATE app_sigma_fate.payments
SET app_id = COALESCE(NULLIF(app_id, ''), 'sigma_fate_v1'),
    currency = COALESCE(NULLIF(currency, ''), 'CNY'),
    status = COALESCE(NULLIF(status, ''), 'pending'),
    created_at = COALESCE(created_at, NOW());

UPDATE app_sigma_fate.access_logs
SET app_id = COALESCE(NULLIF(app_id, ''), 'sigma_fate_v1'),
    metadata = COALESCE(metadata, '{}'::jsonb),
    created_at = COALESCE(created_at, NOW()),
    action = COALESCE(NULLIF(action, ''), 'unknown');

ALTER TABLE app_sigma_fate.users
    ALTER COLUMN app_id SET DEFAULT 'sigma_fate_v1',
    ALTER COLUMN app_id SET NOT NULL,
    ALTER COLUMN subscription_tier SET DEFAULT 'free',
    ALTER COLUMN subscription_tier SET NOT NULL,
    ALTER COLUMN metadata SET DEFAULT '{}'::jsonb,
    ALTER COLUMN metadata SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT NOW(),
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN updated_at SET DEFAULT NOW(),
    ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE app_sigma_fate.reports
    ALTER COLUMN app_id SET DEFAULT 'sigma_fate_v1',
    ALTER COLUMN app_id SET NOT NULL,
    ALTER COLUMN birth_info SET DEFAULT '{}'::jsonb,
    ALTER COLUMN birth_info SET NOT NULL,
    ALTER COLUMN bazi_data SET DEFAULT '{}'::jsonb,
    ALTER COLUMN bazi_data SET NOT NULL,
    ALTER COLUMN report_content SET DEFAULT '{}'::jsonb,
    ALTER COLUMN report_content SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT NOW(),
    ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE app_sigma_fate.payments
    ALTER COLUMN app_id SET DEFAULT 'sigma_fate_v1',
    ALTER COLUMN app_id SET NOT NULL,
    ALTER COLUMN currency SET DEFAULT 'CNY',
    ALTER COLUMN status SET DEFAULT 'pending',
    ALTER COLUMN status SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT NOW(),
    ALTER COLUMN created_at SET NOT NULL;

ALTER TABLE app_sigma_fate.access_logs
    ALTER COLUMN app_id SET DEFAULT 'sigma_fate_v1',
    ALTER COLUMN app_id SET NOT NULL,
    ALTER COLUMN metadata SET DEFAULT '{}'::jsonb,
    ALTER COLUMN metadata SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT NOW(),
    ALTER COLUMN created_at SET NOT NULL;

-- subscription_tier 检查约束（存在则跳过）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'users_subscription_tier_check'
          AND conrelid = 'app_sigma_fate.users'::regclass
    ) THEN
        ALTER TABLE app_sigma_fate.users
            ADD CONSTRAINT users_subscription_tier_check
            CHECK (subscription_tier IN ('free', 'monthly', 'quarterly', 'annual'));
    END IF;
END $$;

-- 唯一约束（存在则跳过）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'users_user_app_uniq'
          AND conrelid = 'app_sigma_fate.users'::regclass
    ) THEN
        ALTER TABLE app_sigma_fate.users
            ADD CONSTRAINT users_user_app_uniq UNIQUE (user_id, app_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'users_auth_app_uniq'
          AND conrelid = 'app_sigma_fate.users'::regclass
    ) THEN
        ALTER TABLE app_sigma_fate.users
            ADD CONSTRAINT users_auth_app_uniq UNIQUE (auth_user_id, app_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'reports_id_app_uniq'
          AND conrelid = 'app_sigma_fate.reports'::regclass
    ) THEN
        ALTER TABLE app_sigma_fate.reports
            ADD CONSTRAINT reports_id_app_uniq UNIQUE (report_id, app_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'payments_id_app_uniq'
          AND conrelid = 'app_sigma_fate.payments'::regclass
    ) THEN
        ALTER TABLE app_sigma_fate.payments
            ADD CONSTRAINT payments_id_app_uniq UNIQUE (payment_id, app_id);
    END IF;
END $$;

-- ---------- 索引（app_id 已存在后才能建） ----------
CREATE INDEX IF NOT EXISTS idx_users_app_email
    ON app_sigma_fate.users (app_id, email);

CREATE INDEX IF NOT EXISTS idx_users_app_auth
    ON app_sigma_fate.users (app_id, auth_user_id);

CREATE INDEX IF NOT EXISTS idx_reports_app_user_created
    ON app_sigma_fate.reports (app_id, user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_payments_app_user
    ON app_sigma_fate.payments (app_id, user_id);

CREATE INDEX IF NOT EXISTS idx_access_logs_app_created
    ON app_sigma_fate.access_logs (app_id, created_at DESC);

-- ---------- 防止跨 App 篡改 app_id ----------
CREATE OR REPLACE FUNCTION app_sigma_fate.enforce_app_id()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.app_id IS DISTINCT FROM 'sigma_fate_v1' THEN
        RAISE EXCEPTION 'app_id must be sigma_fate_v1 for schema app_sigma_fate';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_users_enforce_app_id ON app_sigma_fate.users;
CREATE TRIGGER trg_users_enforce_app_id
    BEFORE INSERT OR UPDATE ON app_sigma_fate.users
    FOR EACH ROW EXECUTE FUNCTION app_sigma_fate.enforce_app_id();

DROP TRIGGER IF EXISTS trg_reports_enforce_app_id ON app_sigma_fate.reports;
CREATE TRIGGER trg_reports_enforce_app_id
    BEFORE INSERT OR UPDATE ON app_sigma_fate.reports
    FOR EACH ROW EXECUTE FUNCTION app_sigma_fate.enforce_app_id();

DROP TRIGGER IF EXISTS trg_payments_enforce_app_id ON app_sigma_fate.payments;
CREATE TRIGGER trg_payments_enforce_app_id
    BEFORE INSERT OR UPDATE ON app_sigma_fate.payments
    FOR EACH ROW EXECUTE FUNCTION app_sigma_fate.enforce_app_id();

DROP TRIGGER IF EXISTS trg_logs_enforce_app_id ON app_sigma_fate.access_logs;
CREATE TRIGGER trg_logs_enforce_app_id
    BEFORE INSERT OR UPDATE ON app_sigma_fate.access_logs
    FOR EACH ROW EXECUTE FUNCTION app_sigma_fate.enforce_app_id();

-- ---------- 权限 ----------
GRANT USAGE ON SCHEMA app_sigma_fate TO anon, authenticated, service_role;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app_sigma_fate
    TO anon, authenticated, service_role;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app_sigma_fate
    TO anon, authenticated, service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA app_sigma_fate
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO anon, authenticated, service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA app_sigma_fate
    GRANT USAGE, SELECT ON SEQUENCES TO anon, authenticated, service_role;

-- ---------- RLS ----------
ALTER TABLE app_sigma_fate.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_sigma_fate.reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_sigma_fate.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_sigma_fate.access_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS users_app_isolation ON app_sigma_fate.users;
CREATE POLICY users_app_isolation ON app_sigma_fate.users
    FOR ALL
    USING (app_id = 'sigma_fate_v1')
    WITH CHECK (app_id = 'sigma_fate_v1');

DROP POLICY IF EXISTS reports_app_isolation ON app_sigma_fate.reports;
CREATE POLICY reports_app_isolation ON app_sigma_fate.reports
    FOR ALL
    USING (app_id = 'sigma_fate_v1')
    WITH CHECK (app_id = 'sigma_fate_v1');

DROP POLICY IF EXISTS payments_app_isolation ON app_sigma_fate.payments;
CREATE POLICY payments_app_isolation ON app_sigma_fate.payments
    FOR ALL
    USING (app_id = 'sigma_fate_v1')
    WITH CHECK (app_id = 'sigma_fate_v1');

DROP POLICY IF EXISTS access_logs_app_isolation ON app_sigma_fate.access_logs;
CREATE POLICY access_logs_app_isolation ON app_sigma_fate.access_logs
    FOR ALL
    USING (app_id = 'sigma_fate_v1')
    WITH CHECK (app_id = 'sigma_fate_v1');

COMMENT ON SCHEMA app_sigma_fate IS 'Sigma Fate BaZi app — isolated from other apps in the same Supabase project';
COMMENT ON TABLE app_sigma_fate.users IS 'App-local users; UNIQUE(user_id, app_id) prevents collision with other apps';

-- ---------- Exposed schemas（Dashboard 等价操作） ----------
DO $$
DECLARE
  cfg text[];
  item text;
  schemas text := NULL;
BEGIN
  SELECT rolconfig INTO cfg FROM pg_roles WHERE rolname = 'authenticator';

  IF cfg IS NOT NULL THEN
    FOREACH item IN ARRAY cfg LOOP
      IF item LIKE 'pgrst.db_schemas=%' THEN
        schemas := substr(item, length('pgrst.db_schemas=') + 1);
        schemas := trim(both '''' from trim(both '"' from schemas));
        EXIT;
      END IF;
    END LOOP;
  END IF;

  IF schemas IS NULL OR length(trim(schemas)) = 0 THEN
    schemas := 'public, storage, graphql_public';
  END IF;

  IF position('app_sigma_fate' in schemas) = 0 THEN
    schemas := schemas || ', app_sigma_fate';
  END IF;

  EXECUTE format('ALTER ROLE authenticator SET pgrst.db_schemas TO %L', schemas);
END $$;

NOTIFY pgrst, 'reload config';
NOTIFY pgrst, 'reload schema';
