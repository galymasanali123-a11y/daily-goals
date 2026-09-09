"""Per-user interface language."""

from db import query_one
from i18n import normalize_lang


def ensure_prefs_table(db):
    try:
        db.execute("SELECT lang FROM user_prefs LIMIT 0")
        return
    except Exception:
        pass
    try:
        db.execute(
            """CREATE TABLE IF NOT EXISTS user_prefs (
                user_id BIGINT PRIMARY KEY,
                lang TEXT NOT NULL DEFAULT 'en'
            )"""
        )
    except Exception:
        pass


def load_user_lang(db, user_id):
    if not user_id:
        return None
    ensure_prefs_table(db)
    try:
        row = query_one(db, "SELECT lang FROM user_prefs WHERE user_id = ?", (user_id,))
    except Exception:
        return None
    if not row:
        return None
    return normalize_lang(row["lang"])


def save_user_lang(db, user_id, lang):
    lang = normalize_lang(lang) or "en"
    ensure_prefs_table(db)
    db.execute(
        "INSERT INTO user_prefs (user_id, lang) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET lang = excluded.lang",
        (user_id, lang),
    )
    return lang
