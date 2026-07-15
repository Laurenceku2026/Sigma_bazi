-- =============================================================================
-- Sigma Fate (BaZi) — 多 App 隔离 Schema
-- 在共享 Supabase 项目中执行本脚本一次即可。
--
-- 隔离原则：
-- 1. 独立 schema：app_sigma_fate（与其他 App 的 public / app_xxx 物理隔离）
-- 2. 行级 app_id：默认 sigma_fate_v1，所有表强制写入/查询带 app_id
-- 3. RLS：按 app_id +（可选）auth.uid() 限制跨 App / 跨用户读写
--
-- 执行后请到 Supabase Dashboard → Settings → API → Exposed schemas
-- 把 app_sigma_fate 加入暴露列表（否则 PostgREST 访问不到自定义 schema）。
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS app_sigma_fate;

-- ---------- users ----------
CREATE TABLE IF NOT EXISTS app_sigma_fate.users (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             TEXT NOT NULL,
    auth_user_id        TEXT,
    email               TEXT,
    app_id              TEXT NOT NULL DEFAULT 'sigma_fate_v1',
    subscription_tier   TEXT NOT NULL DEFAULT 'free'
                        CHECK (subscription_tier IN ('free', 'monthly', 'quarterly', 'annual')),
    stripe_customer_id  TEXT,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT users_user_app_uniq UNIQUE (user_id, app_id),
    CONSTRAINT users_auth_app_uniq UNIQUE (auth_user_id, app_id)
);

CREATE INDEX IF NOT EXISTS idx_users_app_email
    ON app_sigma_fate.users (app_id, email);

CREATE INDEX IF NOT EXISTS idx_users_app_auth
    ON app_sigma_fate.users (app_id, auth_user_id);

-- ---------- reports ----------
CREATE TABLE IF NOT EXISTS app_sigma_fate.reports (
    id                  BIGSERIAL PRIMARY KEY,
    report_id           TEXT NOT NULL,
    user_id             TEXT NOT NULL,
    app_id              TEXT NOT NULL DEFAULT 'sigma_fate_v1',
    birth_info          JSONB NOT NULL DEFAULT '{}'::jsonb,
    bazi_data           JSONB NOT NULL DEFAULT '{}'::jsonb,
    report_content      JSONB NOT NULL DEFAULT '{}'::jsonb,
    payment_tier        TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT reports_id_app_uniq UNIQUE (report_id, app_id)
);

CREATE INDEX IF NOT EXISTS idx_reports_app_user_created
    ON app_sigma_fate.reports (app_id, user_id, created_at DESC);

-- ---------- payments ----------
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
    completed_at        TIMESTAMPTZ,
    CONSTRAINT payments_id_app_uniq UNIQUE (payment_id, app_id)
);

CREATE INDEX IF NOT EXISTS idx_payments_app_user
    ON app_sigma_fate.payments (app_id, user_id);

-- ---------- access_logs ----------
CREATE TABLE IF NOT EXISTS app_sigma_fate.access_logs (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             TEXT,
    app_id              TEXT NOT NULL DEFAULT 'sigma_fate_v1',
    action              TEXT NOT NULL,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_access_logs_app_created
    ON app_sigma_fate.access_logs (app_id, created_at DESC);

-- ---------- 防止跨 App 篡改 app_id（触发器） ----------
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

-- ---------- 权限：仅开放本 schema，不碰其他 App ----------
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

-- service_role 默认绕过 RLS；以下策略约束 anon / authenticated

-- users: 本 App +（已登录时）只能碰自己的行；Streamlit 匿名 UUID 场景允许按 app_id 读写
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

-- 可选：当接入 Supabase Auth 后，收紧为「本 App + 本人」
-- DROP POLICY IF EXISTS users_own_row ON app_sigma_fate.users;
-- CREATE POLICY users_own_row ON app_sigma_fate.users
--     FOR ALL
--     USING (app_id = 'sigma_fate_v1' AND auth_user_id = auth.uid()::text)
--     WITH CHECK (app_id = 'sigma_fate_v1' AND auth_user_id = auth.uid()::text);

COMMENT ON SCHEMA app_sigma_fate IS 'Sigma Fate BaZi app — isolated from other apps in the same Supabase project';
COMMENT ON TABLE app_sigma_fate.users IS 'App-local users; UNIQUE(user_id, app_id) prevents collision with other apps';

-- =============================================================================
-- 等价于 Dashboard → Settings → API → Exposed schemas 勾选 app_sigma_fate
-- PostgREST 只暴露 authenticator 角色上的 pgrst.db_schemas；此处自动追加并 reload。
-- =============================================================================
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
    -- Supabase 常见默认暴露（若项目另有自定义 schema，会被下面的追加逻辑保留）
    schemas := 'public, storage, graphql_public';
  END IF;

  IF position('app_sigma_fate' in schemas) = 0 THEN
    schemas := schemas || ', app_sigma_fate';
  END IF;

  EXECUTE format('ALTER ROLE authenticator SET pgrst.db_schemas TO %L', schemas);
END $$;

-- 让 PostgREST 立刻重新加载配置（无需再去 Dashboard 手点 Exposed schemas）
NOTIFY pgrst, 'reload config';
NOTIFY pgrst, 'reload schema';
