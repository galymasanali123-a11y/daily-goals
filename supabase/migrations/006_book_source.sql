-- Library source + optional object-storage key so phone uploads are not
-- wiped by a desktop finalize-sync, and large PDFs can live outside BYTEA.

ALTER TABLE daily_goals.synced_books
    ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'desktop';
ALTER TABLE daily_goals.synced_books
    ADD COLUMN IF NOT EXISTS storage_key TEXT NOT NULL DEFAULT '';
