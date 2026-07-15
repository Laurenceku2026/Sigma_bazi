-- =============================================================================
-- 清理测试/误迁入的空资料用户，只保留已排盘（有姓名或生日）的真实用户
-- 执行前请确认：古念松等真实用户已有 display_name / birth_date
-- =============================================================================

-- 先看将要删除的行（可选，在 SQL Editor 单独跑）
-- SELECT email, display_name, birth_date, created_at
-- FROM app_sigma_fate.sf_users
-- WHERE app_id = 'sigma_fate_v1'
--   AND COALESCE(TRIM(display_name), '') = ''
--   AND birth_date IS NULL;

DELETE FROM app_sigma_fate.sf_users
WHERE app_id = 'sigma_fate_v1'
  AND COALESCE(TRIM(display_name), '') = ''
  AND birth_date IS NULL;

-- 同步清理旧 users 表，避免以后再被 005 迁回
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'app_sigma_fate' AND table_name = 'users'
  ) THEN
    DELETE FROM app_sigma_fate.users
    WHERE app_id = 'sigma_fate_v1'
      AND COALESCE(TRIM(email), '') <> ''
      AND user_id NOT IN (
        SELECT user_id FROM app_sigma_fate.sf_users
        WHERE app_id = 'sigma_fate_v1'
      );
  END IF;
END $$;

NOTIFY pgrst, 'reload schema';
