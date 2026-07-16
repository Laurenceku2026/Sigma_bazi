-- 试用问卷回复（App 内填写）
CREATE TABLE IF NOT EXISTS app_sigma_fate.sf_survey_responses (
    id                  BIGSERIAL PRIMARY KEY,
    survey_id           TEXT NOT NULL,
    user_id             TEXT NOT NULL,
    email               TEXT,
    app_id              TEXT NOT NULL DEFAULT 'sigma_fate_v1',
    background          TEXT,
    scores              JSONB NOT NULL DEFAULT '{}'::jsonb,
    open_feedback       TEXT,
    recommend_score     INTEGER,
    avg_pro             NUMERIC(4, 2),
    avg_exp             NUMERIC(4, 2),
    avg_all             NUMERIC(4, 2),
    ui_lang             TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT sf_survey_responses_survey_id_uniq UNIQUE (survey_id)
);

CREATE INDEX IF NOT EXISTS idx_sf_survey_app_created
    ON app_sigma_fate.sf_survey_responses (app_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_sf_survey_user
    ON app_sigma_fate.sf_survey_responses (user_id, created_at DESC);

ALTER TABLE app_sigma_fate.sf_survey_responses ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS sf_survey_app_isolation ON app_sigma_fate.sf_survey_responses;
CREATE POLICY sf_survey_app_isolation ON app_sigma_fate.sf_survey_responses
    FOR ALL
    USING (app_id = 'sigma_fate_v1')
    WITH CHECK (app_id = 'sigma_fate_v1');

GRANT SELECT, INSERT, UPDATE, DELETE ON app_sigma_fate.sf_survey_responses TO anon, authenticated, service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app_sigma_fate TO anon, authenticated, service_role;

NOTIFY pgrst, 'reload schema';
