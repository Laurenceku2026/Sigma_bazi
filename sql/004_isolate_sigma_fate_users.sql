-- =============================================================================
-- 强化本 App 用户隔离：只保留 app_id = sigma_fate_v1
-- 不会删除 public.profiles / 其他 App schema 的数据
-- =============================================================================

-- 删掉误入本 schema、但 app_id 不是本 App 的行
DELETE FROM app_sigma_fate.users
WHERE app_id IS DISTINCT FROM 'sigma_fate_v1';

DELETE FROM app_sigma_fate.reports
WHERE app_id IS DISTINCT FROM 'sigma_fate_v1';

DELETE FROM app_sigma_fate.payments
WHERE app_id IS DISTINCT FROM 'sigma_fate_v1';

DELETE FROM app_sigma_fate.access_logs
WHERE app_id IS DISTINCT FROM 'sigma_fate_v1';

-- 确保触发器仍锁定 app_id
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

NOTIFY pgrst, 'reload schema';
