-- =============================================================================
-- 修复 reports / payments 外键：从旧 users 表改挂到 sf_users
--
-- 症状（管理员「保存命盘」）：
--   23503 reports_user_id_fkey
--   Key is not present in table "users".
--
-- 原因：用户已迁到 app_sigma_fate.sf_users，但 reports.user_id 仍 REFERENCES users。
-- 本脚本可重复执行。
-- =============================================================================

-- 1) 去掉指向旧 users（或错误目标）的 user_id 外键
DO $$
DECLARE
  r record;
BEGIN
  FOR r IN
    SELECT
      c.conname,
      n.nspname AS schema_name,
      t.relname AS table_name
    FROM pg_constraint c
    JOIN pg_class t ON t.oid = c.conrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = 'app_sigma_fate'
      AND c.contype = 'f'
      AND t.relname IN ('reports', 'payments', 'access_logs')
      AND (
        c.conname ILIKE '%user_id%fkey%'
        OR pg_get_constraintdef(c.oid) ILIKE '%REFERENCES%users%'
      )
  LOOP
    EXECUTE format(
      'ALTER TABLE %I.%I DROP CONSTRAINT IF EXISTS %I',
      r.schema_name,
      r.table_name,
      r.conname
    );
    RAISE NOTICE 'Dropped FK %.%.%', r.schema_name, r.table_name, r.conname;
  END LOOP;
END $$;

-- 2) 确保 sf_users 有 (user_id, app_id) 唯一约束（复合外键依赖）
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'sf_users_user_app_uniq'
      AND conrelid = 'app_sigma_fate.sf_users'::regclass
  ) THEN
    ALTER TABLE app_sigma_fate.sf_users
      ADD CONSTRAINT sf_users_user_app_uniq UNIQUE (user_id, app_id);
  END IF;
END $$;

-- 3) 清理无法挂到 sf_users 的孤儿报告（可选但利于加新外键）
DELETE FROM app_sigma_fate.reports r
WHERE r.app_id = 'sigma_fate_v1'
  AND NOT EXISTS (
    SELECT 1
    FROM app_sigma_fate.sf_users u
    WHERE u.user_id = r.user_id
      AND u.app_id = r.app_id
  );

DELETE FROM app_sigma_fate.payments p
WHERE p.app_id = 'sigma_fate_v1'
  AND NOT EXISTS (
    SELECT 1
    FROM app_sigma_fate.sf_users u
    WHERE u.user_id = p.user_id
      AND u.app_id = p.app_id
  );

-- 4) 新外键：reports / payments → sf_users(user_id, app_id)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'reports_sf_user_app_fkey'
      AND conrelid = 'app_sigma_fate.reports'::regclass
  ) THEN
    ALTER TABLE app_sigma_fate.reports
      ADD CONSTRAINT reports_sf_user_app_fkey
      FOREIGN KEY (user_id, app_id)
      REFERENCES app_sigma_fate.sf_users (user_id, app_id)
      ON DELETE CASCADE;
  END IF;

  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'app_sigma_fate' AND table_name = 'payments'
  ) AND NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'payments_sf_user_app_fkey'
      AND conrelid = 'app_sigma_fate.payments'::regclass
  ) THEN
    ALTER TABLE app_sigma_fate.payments
      ADD CONSTRAINT payments_sf_user_app_fkey
      FOREIGN KEY (user_id, app_id)
      REFERENCES app_sigma_fate.sf_users (user_id, app_id)
      ON DELETE CASCADE;
  END IF;
END $$;

NOTIFY pgrst, 'reload schema';
