CREATE POLICY app_all ON daily_goals.users FOR ALL TO daily_goals_app USING (true) WITH CHECK (true);
CREATE POLICY app_all ON daily_goals.goals FOR ALL TO daily_goals_app USING (true) WITH CHECK (true);
CREATE POLICY app_all ON daily_goals.completions FOR ALL TO daily_goals_app USING (true) WITH CHECK (true);
CREATE POLICY app_all ON daily_goals.synced_tasks FOR ALL TO daily_goals_app USING (true) WITH CHECK (true);
CREATE POLICY app_all ON daily_goals.synced_cards FOR ALL TO daily_goals_app USING (true) WITH CHECK (true);
CREATE POLICY app_all ON daily_goals.card_review_events FOR ALL TO daily_goals_app USING (true) WITH CHECK (true);
CREATE POLICY app_all ON daily_goals.new_card_intro_state FOR ALL TO daily_goals_app USING (true) WITH CHECK (true);
CREATE POLICY app_all ON daily_goals.synced_books FOR ALL TO daily_goals_app USING (true) WITH CHECK (true);

GRANT USAGE, CREATE ON SCHEMA daily_goals TO daily_goals_app;
GRANT ALL ON ALL TABLES IN SCHEMA daily_goals TO daily_goals_app;
GRANT ALL ON ALL SEQUENCES IN SCHEMA daily_goals TO daily_goals_app;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA daily_goals GRANT ALL ON TABLES TO daily_goals_app;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA daily_goals GRANT ALL ON SEQUENCES TO daily_goals_app;
ALTER ROLE daily_goals_app SET search_path TO daily_goals, public;
