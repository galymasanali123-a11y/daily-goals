CREATE TABLE IF NOT EXISTS daily_goals.user_prefs (
    user_id BIGINT PRIMARY KEY REFERENCES daily_goals.users(id) ON DELETE CASCADE,
    lang TEXT NOT NULL DEFAULT 'en'
);

ALTER TABLE daily_goals.user_prefs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS app_all ON daily_goals.user_prefs;
CREATE POLICY app_all ON daily_goals.user_prefs FOR ALL TO daily_goals_app USING (true) WITH CHECK (true);

GRANT ALL ON TABLE daily_goals.user_prefs TO daily_goals_app;
