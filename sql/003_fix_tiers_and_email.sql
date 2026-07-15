-- 放开会员档位约束（银卡/金卡/钻石）+ 方便诊断
ALTER TABLE app_sigma_fate.users DROP CONSTRAINT IF EXISTS users_subscription_tier_check;
ALTER TABLE app_sigma_fate.users
    ADD CONSTRAINT users_subscription_tier_check
    CHECK (subscription_tier IN (
        'free', 'silver', 'gold', 'diamond',
        'monthly', 'quarterly', 'annual', 'pro'
    ));

-- 邮箱大小写统一便于查询（已有小写则不变）
UPDATE app_sigma_fate.users
SET email = lower(trim(email))
WHERE email IS NOT NULL AND email <> lower(trim(email));

NOTIFY pgrst, 'reload schema';
