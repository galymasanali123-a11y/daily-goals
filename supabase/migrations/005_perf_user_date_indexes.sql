-- Speed up home history, streaks, flashcards, and catalogs that always
-- filter by the signed-in user (and often a date range).

CREATE INDEX IF NOT EXISTS idx_goals_user_id
    ON daily_goals.goals (user_id);

CREATE INDEX IF NOT EXISTS idx_synced_tasks_user_date
    ON daily_goals.synced_tasks (user_id, date);

CREATE INDEX IF NOT EXISTS idx_synced_cards_user_id
    ON daily_goals.synced_cards (user_id);

CREATE INDEX IF NOT EXISTS idx_synced_cards_user_reviewed
    ON daily_goals.synced_cards (user_id, topic)
    WHERE reps > 0 OR lapses > 0;

CREATE INDEX IF NOT EXISTS idx_lesson_progress_user_id
    ON daily_goals.lesson_progress (user_id);

CREATE INDEX IF NOT EXISTS idx_synced_books_user_id
    ON daily_goals.synced_books (user_id);

CREATE INDEX IF NOT EXISTS idx_completions_date
    ON daily_goals.completions (date);
