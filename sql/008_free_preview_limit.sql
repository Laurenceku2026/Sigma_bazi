-- 免费预览次数默认改为 5（含水印；用尽后须升级会员）
-- 已有用户若仍为 30，可按需执行下方 UPDATE

ALTER TABLE app_sigma_fate.sf_users
    ALTER COLUMN free_trials_remaining SET DEFAULT 5;

-- 可选：仅将仍为默认 30 的免费用户改为 5
-- UPDATE app_sigma_fate.sf_users
-- SET free_trials_remaining = 5
-- WHERE subscription_tier = 'free' AND free_trials_remaining = 30;
