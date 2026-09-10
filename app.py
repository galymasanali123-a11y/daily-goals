"""Daily Goals — a small, mobile-friendly daily routine tracker, installable as a PWA.

Multi-user: each person registers their own account and sees only their own goals.
Storage is Supabase Postgres in production (DATABASE_URL) so data survives
redeploys; a local SQLite file is used when that URL is not set.

Run locally with: py app.py
Deploy: see README.md for Render.com + Supabase instructions.
"""

import datetime
import json
import os
import uuid
from functools import wraps
from pathlib import Path

from flask import Flask, Response, abort, g, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import catalog
from db import INTEGRITY_ERRORS, connect_db, init_db, query_all, query_one
from i18n import COOKIE, catalog_for, detect_lang, normalize_lang, parse_accept_language, t
from learn_routes import register_learn_routes
from prefs import load_user_lang, save_user_lang
import srs

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
ASSET_VERSION = "9"
STATIC_DIR = Path(__file__).parent / "static"
SHARED_DECKS_DIR = Path(__file__).parent / "shared_decks"
# A fixed allowlist (code -> filename, label) rather than resolving user input straight to a
# path -- keeps an arbitrary share code from ever reading outside this directory.
SHARED_DECKS = {
    "GOETHE-A1": ("goethe-a1.json", "Goethe-Institut A1 wordlist"),
}

app = Flask(__name__)
app.secret_key = SECRET_KEY


@app.context_processor
def inject_layout():
    path = request.path
    if path.startswith("/settings"):
        nav = "settings"
    elif path.startswith("/learn"):
        nav = "learn"
    elif path.startswith("/flashcards"):
        nav = "cards"
    elif path.startswith("/books"):
        nav = "books"
    elif path in {"/login", "/register"}:
        nav = ""
    else:
        nav = "goals"
    lang = getattr(g, "lang", None) or "en"
    return {
        "active_nav": nav,
        "is_auth_page": path in {"/login", "/register"},
        "wide_layout": path.startswith("/learn") or (path.startswith("/books/") and "/file" not in path),
        "t": t,
        "lang": lang,
        "i18n_catalog": catalog_for(lang),
        "asset_v": ASSET_VERSION,
    }
# Sessions are marked permanent on login/register (session.permanent = True) -- without this,
# Flask's default permanent-session lifetime is only 31 days, which reads as "randomly signed
# out" on an app people check daily. A year is effectively "don't sign me out".
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(days=365)
# A book collection can be large, but a single synced book shouldn't be -- caps one accidental
# giant upload rather than letting it exhaust memory. An 84 MB real-world upload crashed the
# free-tier instance (OOM, most likely -- the body gets buffered in memory at least twice:
# once by Flask, again when the DB client serializes it). 60 MB is the largest size actually
# confirmed stable in production; going higher needs a streaming upload (or more RAM) rather
# than just a bigger number here.
MAX_BOOK_SIZE = 60 * 1024 * 1024
PHONE_BOOK_SIZE = 8 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = MAX_BOOK_SIZE + (1024 * 1024)
INLINE_BOOK_TYPES = {"application/pdf", "text/plain", "text/markdown"}
PHONE_BOOK_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}


def get_db():
    if "db" not in g:
        g.db = connect_db()
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.before_request
def set_language():
    cookie = request.cookies.get(COOKIE)
    stored = None
    if not normalize_lang(cookie) and session.get("user_id") and not request.path.startswith("/static"):
        if "ui_lang" in session:
            stored = session.get("ui_lang") or None
        else:
            try:
                stored = load_user_lang(get_db(), session["user_id"])
            except Exception:
                stored = None
            session["ui_lang"] = stored or ""
    accept = parse_accept_language(request.headers.get("Accept-Language"))
    g.lang = detect_lang(cookie, stored, accept)


@app.after_request
def add_speed_headers(response):
    path = request.path
    if path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=604800, stale-while-revalidate=86400"
    elif path == "/sw.js":
        response.headers["Cache-Control"] = "no-cache"
    elif path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    elif request.method == "GET" and response.mimetype and "html" in response.mimetype:
        response.headers["Cache-Control"] = "private, max-age=0, must-revalidate"
    return response


def _set_lang_cookie(response, lang):
    response.set_cookie(
        COOKIE,
        lang,
        max_age=365 * 24 * 60 * 60,
        samesite="Lax",
        path="/",
        secure=bool(request.is_secure),
    )
    return response


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": t("not_authenticated")}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if not username or not email or not password:
            error = t("err_all_required")
        elif "@" not in email or "." not in email.split("@")[-1]:
            error = t("err_email")
        elif password != confirm:
            error = t("err_password_match")
        elif len(password) < 4:
            error = t("err_password_short")
        else:
            db = get_db()
            existing = query_one(db, "SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (username,))
            if existing:
                error = t("err_username_taken")
            else:
                try:
                    created = query_one(
                        db,
                        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?) RETURNING id",
                        (username, email, generate_password_hash(password)),
                    )
                except INTEGRITY_ERRORS:
                    error = t("err_username_taken")
                else:
                    session["user_id"] = created["id"]
                    session["username"] = username
                    session.permanent = True
                    return redirect(url_for("index"))
    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        user = query_one(db, "SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,))
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session.permanent = True
            return redirect(url_for("index"))
        error = t("err_bad_login")
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    if request.method == "POST":
        lang = normalize_lang(request.form.get("lang")) or "en"
        if session.get("user_id"):
            try:
                save_user_lang(get_db(), session["user_id"], lang)
            except Exception:
                pass
        g.lang = lang
        session["ui_lang"] = lang
        return _set_lang_cookie(redirect(url_for("settings_page")), lang)
    srs_settings = None
    if session.get("user_id"):
        srs_settings = load_srs_settings(get_db(), session["user_id"])
    return render_template("settings.html", srs_settings=srs_settings)


def today_str():
    return datetime.date.today().isoformat()


def compute_streak(db, user_id, done_dates=None):
    """Consecutive days (ending today) with at least one goal or synced task completed, for this user."""
    if done_dates is None:
        cutoff = (datetime.date.today() - datetime.timedelta(days=800)).isoformat()
        done_dates = {
            row["date"]
            for row in query_all(
                db,
                "SELECT date FROM ("
                "  SELECT DISTINCT c.date AS date FROM completions c JOIN goals g ON g.id = c.goal_id "
                "  WHERE g.user_id = ? AND c.done = 1 AND c.date >= ?"
                "  UNION "
                "  SELECT DISTINCT date FROM synced_tasks WHERE user_id = ? AND done = 1 AND date >= ?"
                ") streak_days",
                (user_id, cutoff, user_id, cutoff),
            )
        }
    streak = 0
    day = datetime.date.today()
    while day.isoformat() in done_dates:
        streak += 1
        day -= datetime.timedelta(days=1)
    return streak


def goals_with_status(db, user_id):
    today = today_str()
    rows = query_all(
        db,
        "SELECT g.id AS id, g.text AS text, COALESCE(c.done, 0) AS done "
        "FROM goals g LEFT JOIN completions c ON c.goal_id = g.id AND c.date = ? "
        "WHERE g.user_id = ? ORDER BY g.sort_order, g.id",
        (today, user_id),
    )
    return [{"id": row["id"], "text": row["text"], "done": bool(row["done"])} for row in rows]


def synced_tasks_for_today(db, user_id):
    today = today_str()
    rows = query_all(
        db,
        "SELECT id, external_id, text, time, task_type, done FROM synced_tasks "
        "WHERE user_id = ? AND date = ? ORDER BY time, id",
        (user_id, today),
    )
    return [
        {
            "id": row["id"],
            "external_id": row["external_id"],
            "text": row["text"],
            "time": row["time"],
            "task_type": row["task_type"],
            "done": bool(row["done"]),
        }
        for row in rows
    ]


CONFIDENCE_LABELS = {1: "Again", 2: "Hard", 3: "Good", 4: "Easy"}
LEECH_THRESHOLD = 8


def row_get(row, key, default=None):
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except (KeyError, IndexError):
        return default


def card_row_to_dict(row):
    return {
        "id": row["id"],
        "external_id": row["external_id"],
        "topic": row["topic"],
        "question": row["question"],
        "answer": row["answer"],
        "options": json.loads(row["options_json"] or "[]"),
        "example": row["example"],
        "notes": row["notes"],
        "due": row["due"],
        "interval": row["interval"],
        "ease": row["ease"],
        "reps": row["reps"],
        "lapses": row["lapses"],
        "queue": int(row_get(row, "queue", 0) or 0),
        "due_at": row_get(row, "due_at", "") or "",
        "learn_step": int(row_get(row, "learn_step", 0) or 0),
        "source": row_get(row, "source", "desktop") or "desktop",
    }


def cards_for_user(db, user_id):
    rows = query_all(db, "SELECT * FROM synced_cards WHERE user_id = ? ORDER BY topic, question", (user_id,))
    return [card_row_to_dict(row) for row in rows]


WEEKDAY_LABELS = {
    "en": ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
    "ru": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
}
WEEKDAY_FULL = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "ru": ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"],
}
MONTHS_FULL = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    "ru": ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"],
}


def friendly_today(iso_date, lang="en"):
    day = datetime.date.fromisoformat(iso_date)
    names = WEEKDAY_FULL.get(lang) or WEEKDAY_FULL["en"]
    months = MONTHS_FULL.get(lang) or MONTHS_FULL["en"]
    if lang == "ru":
        return f"{names[day.weekday()]}, {day.day} {months[day.month - 1]}"
    return f"{names[day.weekday()]}, {day.day} {months[day.month - 1]}"


def _as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def history_payload(db, user_id, lang=None, today=None):
    """One grouped query for the 7-day strip instead of a COUNT per day."""
    today_date = datetime.date.fromisoformat(today) if today else datetime.date.today()
    start = (today_date - datetime.timedelta(days=6)).isoformat()
    end = today_date.isoformat()
    total_goals = _as_int(
        query_one(db, "SELECT COUNT(*) AS n FROM goals WHERE user_id = ?", (user_id,))["n"]
    )
    rows = query_all(
        db,
        "SELECT day, SUM(n) AS n FROM ("
        "  SELECT c.date AS day, COUNT(*) AS n"
        "  FROM completions c JOIN goals g ON g.id = c.goal_id"
        "  WHERE g.user_id = ? AND c.done = 1 AND c.date >= ? AND c.date <= ?"
        "  GROUP BY c.date"
        "  UNION ALL"
        "  SELECT date AS day, COUNT(*) AS n"
        "  FROM synced_tasks"
        "  WHERE user_id = ? AND done = 1 AND date >= ? AND date <= ?"
        "  GROUP BY date"
        ") grouped GROUP BY day",
        (user_id, start, end, user_id, start, end),
    )
    counts = {row["day"]: _as_int(row["n"]) for row in rows}
    return _history_from_counts(counts, total_goals, lang or getattr(g, "lang", None), today_date.isoformat())


def weekly_digest(db, user_id, streak=None):
    """Sunday-summary data: streak, goals completed and flashcards reviewed in the last 7
    days, and the weakest topic right now -- reuses data already computed elsewhere rather
    than tracking anything new (except reviews-this-week, backed by card_review_events)."""
    week_ago = (datetime.date.today() - datetime.timedelta(days=6)).isoformat()
    row = query_one(
        db,
        "SELECT "
        "  (SELECT COUNT(*) FROM completions c JOIN goals g ON g.id = c.goal_id "
        "   WHERE g.user_id = ? AND c.date >= ? AND c.done = 1) AS goals_week, "
        "  (SELECT COUNT(*) FROM card_review_events "
        "   WHERE user_id = ? AND reviewed_at >= ?) AS reviews_week, "
        "  (SELECT topic FROM synced_cards WHERE user_id = ? AND (reps > 0 OR lapses > 0) "
        "   GROUP BY topic ORDER BY AVG(ease) ASC LIMIT 1) AS topic, "
        "  (SELECT AVG(ease) FROM synced_cards WHERE user_id = ? AND (reps > 0 OR lapses > 0) AND topic = ("
        "    SELECT topic FROM synced_cards WHERE user_id = ? AND (reps > 0 OR lapses > 0) "
        "    GROUP BY topic ORDER BY AVG(ease) ASC LIMIT 1"
        "  )) AS avg_ease",
        (user_id, week_ago, user_id, week_ago, user_id, user_id, user_id),
    )
    topic = row["topic"] if row else None
    avg_ease = row["avg_ease"] if row else None
    weakest = None
    if topic is not None and avg_ease is not None:
        weakest = {"topic": topic, "avg_ease": round(float(avg_ease), 2)}
    return {
        "streak": streak if streak is not None else compute_streak(db, user_id),
        "goals_completed": _as_int(row["goals_week"] if row else 0),
        "reviews_completed": _as_int(row["reviews_week"] if row else 0),
        "weakest_topic": weakest,
    }


def digest_visible(digest):
    return not (
        digest["streak"] == 0
        and digest["goals_completed"] == 0
        and digest["reviews_completed"] == 0
        and not digest["weakest_topic"]
    )


def load_srs_settings(db, user_id):
    row = query_one(
        db,
        "SELECT new_per_day, reviews_per_day, notify_enabled, notify_hour FROM srs_settings WHERE user_id = ?",
        (user_id,),
    )
    if not row:
        return srs.default_settings()
    return {
        "new_per_day": int(row["new_per_day"]),
        "reviews_per_day": int(row["reviews_per_day"]),
        "notify_enabled": int(row["notify_enabled"]),
        "notify_hour": int(row["notify_hour"]),
    }


def load_day_counts(db, user_id, today):
    row = query_one(
        db, "SELECT new_shown, reviews_shown FROM srs_day_counts WHERE user_id = ? AND date = ?", (user_id, today)
    )
    if not row:
        return 0, 0
    return int(row["new_shown"] or 0), int(row["reviews_shown"] or 0)


def bump_day_count(db, user_id, today, new=0, review=0):
    db.execute(
        "INSERT INTO srs_day_counts (user_id, date, new_shown, reviews_shown) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(user_id, date) DO UPDATE SET "
        "new_shown = srs_day_counts.new_shown + excluded.new_shown, "
        "reviews_shown = srs_day_counts.reviews_shown + excluded.reviews_shown",
        (user_id, today, new, review),
    )


def select_study_cards(cards, db, user_id, new_limit=None):
    """Anki-style daily queue: due learning cards first, then a capped number of reviews,
    then a capped number of new cards. Introduced new-card ids stay stable for the day.
    """
    today = today_str()
    settings = load_srs_settings(db, user_id)
    if new_limit is not None:
        settings = {**settings, "new_per_day": new_limit}
    row = query_one(db, "SELECT date, ids_json FROM new_card_intro_state WHERE user_id = ?", (user_id,))
    already_introduced = set(json.loads(row["ids_json"])) if row and row["date"] == today else set()
    new_shown, reviews_shown = load_day_counts(db, user_id, today)
    selected_ids, updated_intro, waiting_at, counts = srs.select_study_queue(
        cards, settings, already_introduced, new_shown, reviews_shown
    )
    db.execute(
        "INSERT INTO new_card_intro_state (user_id, date, ids_json) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET date = excluded.date, ids_json = excluded.ids_json",
        (user_id, today, json.dumps(list(updated_intro))),
    )
    return selected_ids, waiting_at, counts, settings


def _history_from_counts(counts, total_goals, lang, today):
    today_date = datetime.date.fromisoformat(today)
    labels = WEEKDAY_LABELS.get(lang) or WEEKDAY_LABELS["en"]
    max_count = max(total_goals, 1, *(counts.values() or [0]))
    days = []
    for offset in range(6, -1, -1):
        day = (today_date - datetime.timedelta(days=offset)).isoformat()
        count = counts.get(day, 0)
        weekday = datetime.date.fromisoformat(day).weekday()
        days.append({
            "date": day,
            "count": count,
            "label": labels[weekday],
            "height": max(6, round((count / max_count) * 100)),
        })
    return {"days": days, "total_goals": total_goals}


def current_state(db, user_id):
    today = today_str()
    start = (datetime.date.fromisoformat(today) - datetime.timedelta(days=6)).isoformat()
    cutoff = (datetime.date.fromisoformat(today) - datetime.timedelta(days=800)).isoformat()
    lang = getattr(g, "lang", None) or "en"
    rows = query_all(
        db,
        "SELECT 'goal' AS k, g.id AS id, g.text AS text, COALESCE(c.done, 0) AS n, "
        "       g.sort_order AS sort_order, CAST(NULL AS TEXT) AS day, "
        "       CAST(NULL AS TEXT) AS time, CAST(NULL AS TEXT) AS task_type, "
        "       CAST(NULL AS TEXT) AS external_id "
        "FROM goals g LEFT JOIN completions c ON c.goal_id = g.id AND c.date = ? "
        "WHERE g.user_id = ? "
        "UNION ALL "
        "SELECT 'task', t.id, t.text, t.done, CAST(NULL AS INTEGER), t.date, t.time, t.task_type, t.external_id "
        "FROM synced_tasks t WHERE t.user_id = ? AND t.date = ? "
        "UNION ALL "
        "SELECT 'hist', CAST(NULL AS INTEGER), CAST(NULL AS TEXT), SUM(n), CAST(NULL AS INTEGER), day, "
        "       CAST(NULL AS TEXT), CAST(NULL AS TEXT), CAST(NULL AS TEXT) "
        "FROM ("
        "  SELECT c.date AS day, COUNT(*) AS n FROM completions c JOIN goals g ON g.id = c.goal_id "
        "  WHERE g.user_id = ? AND c.done = 1 AND c.date >= ? AND c.date <= ? GROUP BY c.date "
        "  UNION ALL "
        "  SELECT date, COUNT(*) FROM synced_tasks "
        "  WHERE user_id = ? AND done = 1 AND date >= ? AND date <= ? GROUP BY date"
        ") hist_days GROUP BY day "
        "UNION ALL "
        "SELECT 'streak', CAST(NULL AS INTEGER), CAST(NULL AS TEXT), CAST(NULL AS INTEGER), CAST(NULL AS INTEGER), date, "
        "       CAST(NULL AS TEXT), CAST(NULL AS TEXT), CAST(NULL AS TEXT) "
        "FROM ("
        "  SELECT DISTINCT c.date AS date FROM completions c JOIN goals g ON g.id = c.goal_id "
        "  WHERE g.user_id = ? AND c.done = 1 AND c.date >= ? "
        "  UNION "
        "  SELECT DISTINCT date FROM synced_tasks WHERE user_id = ? AND done = 1 AND date >= ?"
        ") streak_days",
        (
            today, user_id,
            user_id, today,
            user_id, start, today, user_id, start, today,
            user_id, cutoff, user_id, cutoff,
        ),
    )
    goal_rows = []
    synced_rows = []
    hist_counts = {}
    streak_dates = set()
    for row in rows:
        kind = row["k"]
        if kind == "goal":
            goal_rows.append({"id": row["id"], "text": row["text"], "done": bool(row["n"]), "sort_order": row["sort_order"]})
        elif kind == "task":
            synced_rows.append({
                "id": row["id"],
                "external_id": row["external_id"],
                "text": row["text"],
                "time": row["time"] or "",
                "task_type": row["task_type"] or "Task",
                "done": bool(row["n"]),
            })
        elif kind == "hist" and row["day"]:
            hist_counts[row["day"]] = _as_int(row["n"])
        elif kind == "streak" and row["day"]:
            streak_dates.add(row["day"])
    goal_rows.sort(key=lambda item: (item["sort_order"] if item["sort_order"] is not None else 0, item["id"]))
    synced_rows.sort(key=lambda item: (item["time"] or "", item["id"]))
    for item in goal_rows:
        item.pop("sort_order", None)
    streak = compute_streak(db, user_id, done_dates=streak_dates)
    done_count = sum(1 for goal in goal_rows if goal["done"]) + sum(1 for task in synced_rows if task["done"])
    digest = weekly_digest(db, user_id, streak=streak)
    return {
        "goals": goal_rows,
        "synced_tasks": synced_rows,
        "done_count": done_count,
        "total_count": len(goal_rows) + len(synced_rows),
        "streak": streak,
        "today": today,
        "today_label": friendly_today(today, lang),
        "username": session.get("username"),
        "history": _history_from_counts(hist_counts, len(goal_rows), lang, today),
        "digest": digest,
    }


def owned_goal(db, user_id, goal_id):
    """Fetch a goal only if it belongs to this user — prevents editing someone else's goals by guessing an id."""
    return query_one(db, "SELECT * FROM goals WHERE id = ? AND user_id = ?", (goal_id, user_id))


@app.route("/")
@login_required
def index():
    db = get_db()
    state = current_state(db, session["user_id"])
    return render_template(
        "index.html",
        state=state,
        history=state["history"],
        digest=state["digest"],
        show_digest=digest_visible(state["digest"]),
    )


@app.route("/sw.js")
def service_worker():
    response = send_from_directory(STATIC_DIR, "sw.js")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/api/state")
@login_required
def api_state():
    return jsonify(current_state(get_db(), session["user_id"]))


@app.route("/api/history")
@login_required
def api_history():
    return jsonify(history_payload(get_db(), session["user_id"], lang=getattr(g, "lang", None)))


@app.route("/api/weekly-digest")
@login_required
def api_weekly_digest():
    return jsonify(weekly_digest(get_db(), session["user_id"]))


@app.route("/api/toggle/<int:goal_id>", methods=["POST"])
@login_required
def api_toggle(goal_id):
    db = get_db()
    user_id = session["user_id"]
    if not owned_goal(db, user_id, goal_id):
        return jsonify({"error": t("err_not_found")}), 404
    today = today_str()
    row = query_one(db, "SELECT done FROM completions WHERE goal_id = ? AND date = ?", (goal_id, today))
    new_done = 0 if row and row["done"] else 1
    db.execute(
        "INSERT INTO completions (goal_id, date, done) VALUES (?, ?, ?) "
        "ON CONFLICT(goal_id, date) DO UPDATE SET done = excluded.done",
        (goal_id, today, new_done),
    )
    return jsonify(current_state(db, user_id))


@app.route("/api/goals", methods=["POST"])
@login_required
def api_add_goal():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    if not text:
        return jsonify({"error": t("err_text_required")}), 400
    db = get_db()
    user_id = session["user_id"]
    max_order = query_one(db, "SELECT COALESCE(MAX(sort_order), -1) AS n FROM goals WHERE user_id = ?", (user_id,))["n"]
    db.execute("INSERT INTO goals (user_id, text, sort_order) VALUES (?, ?, ?)", (user_id, text, max_order + 1))
    return jsonify(current_state(db, user_id))


@app.route("/api/goals/<int:goal_id>/edit", methods=["POST"])
@login_required
def api_edit_goal(goal_id):
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    if not text:
        return jsonify({"error": t("err_text_required")}), 400
    db = get_db()
    user_id = session["user_id"]
    if not owned_goal(db, user_id, goal_id):
        return jsonify({"error": t("err_not_found")}), 404
    db.execute("UPDATE goals SET text = ? WHERE id = ?", (text, goal_id))
    return jsonify(current_state(db, user_id))


@app.route("/api/goals/<int:goal_id>/delete", methods=["POST"])
@login_required
def api_delete_goal(goal_id):
    db = get_db()
    user_id = session["user_id"]
    if not owned_goal(db, user_id, goal_id):
        return jsonify({"error": t("err_not_found")}), 404
    db.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    db.execute("DELETE FROM completions WHERE goal_id = ?", (goal_id,))
    return jsonify(current_state(db, user_id))


@app.route("/api/goals/<int:goal_id>/move", methods=["POST"])
@login_required
def api_move_goal(goal_id):
    payload = request.get_json(silent=True) or {}
    direction = payload.get("direction")
    db = get_db()
    user_id = session["user_id"]
    if not owned_goal(db, user_id, goal_id):
        return jsonify({"error": t("err_not_found")}), 404

    goals = query_all(db, "SELECT id, sort_order FROM goals WHERE user_id = ? ORDER BY sort_order", (user_id,))
    ids = [goal["id"] for goal in goals]
    index = ids.index(goal_id)
    swap_with = index - 1 if direction == "up" else index + 1 if direction == "down" else None
    if swap_with is not None and 0 <= swap_with < len(ids):
        goal_a, goal_b = goals[index], goals[swap_with]
        db.execute("UPDATE goals SET sort_order = ? WHERE id = ?", (goal_b["sort_order"], goal_a["id"]))
        db.execute("UPDATE goals SET sort_order = ? WHERE id = ?", (goal_a["sort_order"], goal_b["id"]))
    return jsonify(current_state(db, user_id))


@app.route("/api/sync", methods=["POST"])
@login_required
def api_sync():
    """Push today's desktop Planner tasks; completions merge (OR) so a phone check-off is never lost."""
    payload = request.get_json(silent=True) or {}
    incoming_tasks = payload.get("tasks", [])
    if not isinstance(incoming_tasks, list):
        return jsonify({"error": "tasks must be a list"}), 400

    db = get_db()
    user_id = session["user_id"]
    today = today_str()

    incoming_ids = set()
    for task in incoming_tasks:
        external_id = str(task.get("external_id", "")).strip()
        text = str(task.get("text", "")).strip()
        if not external_id or not text:
            continue
        incoming_ids.add(external_id)
        time_value = str(task.get("time", ""))
        task_type = str(task.get("task_type", "Task"))
        incoming_done = 1 if task.get("done") else 0

        existing = query_one(
            db, "SELECT done FROM synced_tasks WHERE user_id = ? AND external_id = ?", (user_id, external_id)
        )
        merged_done = 1 if incoming_done or (existing and existing["done"]) else 0

        db.execute(
            "INSERT INTO synced_tasks (user_id, external_id, date, text, time, task_type, done) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, external_id) DO UPDATE SET "
            "date = excluded.date, text = excluded.text, time = excluded.time, "
            "task_type = excluded.task_type, done = ?",
            (user_id, external_id, today, text, time_value, task_type, merged_done, merged_done),
        )

    # A task no longer reported by the desktop for today (deleted/renamed there) drops out here too.
    existing_today = query_all(db, "SELECT id, external_id FROM synced_tasks WHERE user_id = ? AND date = ?", (user_id, today))
    for row in existing_today:
        if row["external_id"] not in incoming_ids:
            db.execute("DELETE FROM synced_tasks WHERE id = ?", (row["id"],))

    return jsonify(current_state(db, user_id))


@app.route("/api/synced-tasks/<int:task_id>/toggle", methods=["POST"])
@login_required
def api_toggle_synced_task(task_id):
    db = get_db()
    user_id = session["user_id"]
    row = query_one(db, "SELECT done FROM synced_tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    if not row:
        return jsonify({"error": t("err_not_found")}), 404
    new_done = 0 if row["done"] else 1
    db.execute("UPDATE synced_tasks SET done = ? WHERE id = ?", (new_done, task_id))
    return jsonify(current_state(db, user_id))


def study_payload(db, user_id):
    cards = cards_for_user(db, user_id)
    due_today_ids, waiting_at, counts, settings = select_study_cards(cards, db, user_id)
    for card in cards:
        card["due_today"] = card["external_id"] in due_today_ids
        card["queue"] = srs.infer_queue(card)
        card["previews"] = srs.button_previews(card)
    topics = sorted({card["topic"] for card in cards})
    due_count = sum(1 for card in cards if card["due_today"])
    studied_today = 0
    try:
        row = query_one(
            db,
            "SELECT COUNT(*) AS n FROM card_review_events WHERE user_id = ? AND reviewed_at LIKE ?",
            (user_id, today_str() + "%"),
        )
        studied_today = int(row["n"] if row else 0)
    except Exception:
        studied_today = 0
    try:
        decks = catalog.decks_payload(db, user_id)
    except Exception:
        decks = []
    return {
        "cards": cards,
        "topics": topics,
        "today": today_str(),
        "counts": counts,
        "settings": settings,
        "waiting_at": waiting_at,
        "due_count": due_count,
        "studied_today": studied_today,
        "decks": decks,
    }


@app.route("/flashcards")
@login_required
def flashcards_page():
    return render_template("flashcards.html", cards_bootstrap=study_payload(get_db(), session["user_id"]))


@app.route("/api/cards", methods=["GET"])
@login_required
def api_cards():
    return jsonify(study_payload(get_db(), session["user_id"]))


@app.route("/api/cards/pull-reviews", methods=["POST"])
@login_required
def api_cards_pull_reviews():
    """The desktop app calls this before pushing: fetch review events made on the phone since the
    last sync (oldest first, so SM-2 intervals apply in the order they actually happened), then
    mark them consumed -- each event is applied exactly once, but (unlike a hard delete) it stays
    around long enough for the weekly digest to still count it toward "reviews this week"."""
    db = get_db()
    user_id = session["user_id"]
    rows = query_all(
        db,
        "SELECT id, external_id, confidence, reviewed_at FROM card_review_events "
        "WHERE user_id = ? AND consumed = 0 ORDER BY reviewed_at, id",
        (user_id,),
    )
    events = [{"external_id": row["external_id"], "confidence": row["confidence"], "reviewed_at": row["reviewed_at"]} for row in rows]
    if rows:
        db.execute("UPDATE card_review_events SET consumed = 1 WHERE user_id = ? AND consumed = 0", (user_id,))
    # Opportunistic cleanup so this table doesn't grow forever -- old consumed rows have already
    # done their job (SM-2 applied, digest counted them if recent enough).
    cutoff = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    db.execute("DELETE FROM card_review_events WHERE user_id = ? AND consumed = 1 AND reviewed_at < ?", (user_id, cutoff))
    return jsonify({"events": events})


@app.route("/api/cards/sync", methods=["POST"])
@login_required
def api_cards_sync():
    """Push the full desktop flashcard deck (content + spaced-repetition state). The desktop is
    authoritative for due/interval/ease/reps — it's expected to have already pulled and applied
    any pending phone review events (via /api/cards/pull-reviews) before calling this, so this
    push's state reflects those reviews too."""
    payload = request.get_json(silent=True) or {}
    incoming_cards = payload.get("cards", [])
    if not isinstance(incoming_cards, list):
        return jsonify({"error": "cards must be a list"}), 400

    db = get_db()
    user_id = session["user_id"]

    incoming_ids = set()
    for card in incoming_cards:
        external_id = str(card.get("external_id", "")).strip()
        topic = str(card.get("topic", "")).strip()
        question = str(card.get("question", "")).strip()
        if not external_id or not topic or not question:
            continue
        incoming_ids.add(external_id)
        answer = str(card.get("answer", ""))
        options_json = json.dumps(card.get("options") or [])
        example = str(card.get("example", ""))
        notes = str(card.get("notes", ""))
        due = str(card.get("due", "0000-00-00"))
        interval = int(card.get("interval", 1) or 1)
        ease = float(card.get("ease", 2.5) or 2.5)
        reps = int(card.get("reps", 0) or 0)
        lapses = int(card.get("lapses", 0) or 0)
        queue = int(card["queue"]) if card.get("queue") is not None else (srs.QUEUE_REVIEW if reps else srs.QUEUE_NEW)
        due_at = str(card.get("due_at") or ("" if due == srs.NEW_SENTINEL else due))
        learn_step = int(card.get("learn_step") or 0)
        source = str(card.get("source") or "desktop")

        db.execute(
            "INSERT INTO synced_cards (user_id, external_id, topic, question, answer, options_json, "
            "example, notes, due, interval, ease, reps, lapses, queue, due_at, learn_step, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, external_id) DO UPDATE SET "
            "topic = excluded.topic, question = excluded.question, answer = excluded.answer, "
            "options_json = excluded.options_json, example = excluded.example, notes = excluded.notes, "
            "due = excluded.due, interval = excluded.interval, ease = excluded.ease, reps = excluded.reps, "
            "lapses = excluded.lapses, queue = excluded.queue, due_at = excluded.due_at, "
            "learn_step = excluded.learn_step, source = excluded.source",
            (user_id, external_id, topic, question, answer, options_json, example, notes, due, interval, ease, reps, lapses, queue, due_at, learn_step, source),
        )

    # Desktop is authoritative only for cards it owns. Course/shared decks stay on the phone.
    existing = query_all(db, "SELECT id, external_id, source FROM synced_cards WHERE user_id = ?", (user_id,))
    for row in existing:
        source = row_get(row, "source", "desktop") or "desktop"
        if source != "desktop":
            continue
        if row["external_id"] not in incoming_ids:
            db.execute("DELETE FROM synced_cards WHERE id = ?", (row["id"],))

    return jsonify({"card_count": len(incoming_ids)})


@app.route("/api/import-shared-deck", methods=["POST"])
@login_required
def api_import_shared_deck():
    """Add a bundled deck (see SHARED_DECKS) to the caller's own account -- e.g. sharing a
    coursemate a copy of a deck without either side ever handling the other's password. Cards
    land fresh (due today, no review history) so the importer starts their own review cycle,
    regardless of what progress the original owner had made on their copy."""
    payload = request.get_json(silent=True) or {}
    code = str(payload.get("code", "")).strip().upper()
    entry = SHARED_DECKS.get(code)
    if not entry:
        return jsonify({"error": t("err_share_code")}), 404
    filename, label = entry
    cards = json.loads((SHARED_DECKS_DIR / filename).read_text(encoding="utf-8"))

    db = get_db()
    user_id = session["user_id"]
    for card in cards:
        db.execute(
            "INSERT INTO synced_cards (user_id, external_id, topic, question, answer, options_json, "
            "example, notes, due, interval, ease, reps, lapses, queue, due_at, learn_step, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, external_id) DO UPDATE SET "
            "topic = excluded.topic, question = excluded.question, answer = excluded.answer, "
            "options_json = excluded.options_json, example = excluded.example, notes = excluded.notes, "
            "due = excluded.due, interval = excluded.interval, ease = excluded.ease, reps = excluded.reps, "
            "lapses = excluded.lapses, queue = excluded.queue, due_at = excluded.due_at, "
            "learn_step = excluded.learn_step, source = excluded.source",
            (
                user_id, card["external_id"], card["topic"], card["question"], card["answer"],
                json.dumps(card.get("options") or []), card.get("example", ""), card.get("notes", ""),
                card.get("due") or srs.NEW_SENTINEL, card.get("interval") or 0, card.get("ease") or srs.STARTING_EASE,
                0, 0, srs.QUEUE_NEW, "", 0, "shared",
            ),
        )
    return jsonify({"card_count": len(cards), "label": label})


@app.route("/api/catalog/decks/<deck_id>/download", methods=["POST"])
@login_required
def api_catalog_download_deck(deck_id):
    result = catalog.download_deck(get_db(), session["user_id"], deck_id)
    if not result:
        return jsonify({"error": t("err_not_found")}), 404
    return jsonify(result)


@app.route("/api/catalog/decks/<deck_id>", methods=["DELETE"])
@login_required
def api_catalog_delete_deck(deck_id):
    result = catalog.delete_deck(get_db(), session["user_id"], deck_id)
    if not result:
        return jsonify({"error": t("err_not_found")}), 404
    return jsonify(result)


@app.route("/api/cards/<int:card_id>/restore", methods=["POST"])
@login_required
def api_card_restore(card_id):
    payload = request.get_json(silent=True) or {}
    db = get_db()
    user_id = session["user_id"]
    row = query_one(db, "SELECT * FROM synced_cards WHERE id = ? AND user_id = ?", (card_id, user_id))
    if not row:
        return jsonify({"error": t("err_not_found")}), 404
    due = str(payload.get("due") or row["due"])
    interval = int(payload.get("interval") or 0)
    ease = float(payload.get("ease") or srs.STARTING_EASE)
    reps = int(payload.get("reps") or 0)
    lapses = int(payload.get("lapses") or 0)
    queue = int(payload.get("queue") if payload.get("queue") is not None else srs.infer_queue(card_row_to_dict(row)))
    due_at = str(payload.get("due_at") or "")
    learn_step = int(payload.get("learn_step") or 0)
    db.execute(
        "UPDATE synced_cards SET due = ?, interval = ?, ease = ?, reps = ?, lapses = ?, "
        "queue = ?, due_at = ?, learn_step = ? WHERE id = ?",
        (due, interval, ease, reps, lapses, queue, due_at, learn_step, card_id),
    )
    last = query_one(
        db,
        "SELECT id FROM card_review_events WHERE user_id = ? AND external_id = ? ORDER BY id DESC LIMIT 1",
        (user_id, row["external_id"]),
    )
    if last:
        db.execute("DELETE FROM card_review_events WHERE id = ?", (last["id"],))
    return jsonify({"ok": True})


@app.route("/api/cards/<int:card_id>/review", methods=["POST"])
@login_required
def api_card_review(card_id):
    payload = request.get_json(silent=True) or {}
    try:
        confidence = max(1, min(4, int(payload.get("confidence", 3))))
    except (TypeError, ValueError):
        confidence = 3

    db = get_db()
    user_id = session["user_id"]
    row = query_one(db, "SELECT * FROM synced_cards WHERE id = ? AND user_id = ?", (card_id, user_id))
    if not row:
        return jsonify({"error": t("err_not_found")}), 404

    before = card_row_to_dict(row)
    before_queue = srs.infer_queue(before)
    updated = srs.apply_review_result(before, confidence)
    db.execute(
        "UPDATE synced_cards SET due = ?, interval = ?, ease = ?, reps = ?, lapses = ?, "
        "queue = ?, due_at = ?, learn_step = ? WHERE id = ?",
        (
            updated["due"], updated["interval"], updated["ease"], updated["reps"], updated["lapses"],
            updated["queue"], updated["due_at"], updated["learn_step"], card_id,
        ),
    )
    if before_queue == srs.QUEUE_NEW:
        bump_day_count(db, user_id, today_str(), new=1)
    elif before_queue == srs.QUEUE_REVIEW:
        bump_day_count(db, user_id, today_str(), review=1)
    db.execute(
        "INSERT INTO card_review_events (user_id, external_id, confidence, reviewed_at) VALUES (?, ?, ?, ?)",
        (user_id, row["external_id"], confidence, datetime.datetime.now().isoformat()),
    )
    result = card_row_to_dict(row)
    result.update(
        due=updated["due"], interval=updated["interval"], ease=updated["ease"],
        reps=updated["reps"], lapses=updated["lapses"], queue=updated["queue"],
        due_at=updated["due_at"], learn_step=updated["learn_step"],
        previews=srs.button_previews(updated),
    )
    return jsonify(result)


@app.route("/api/srs-settings", methods=["GET", "POST"])
@login_required
def api_srs_settings():
    db = get_db()
    user_id = session["user_id"]
    if request.method == "GET":
        settings = load_srs_settings(db, user_id)
        new_shown, reviews_shown = load_day_counts(db, user_id, today_str())
        return jsonify({**settings, "new_shown": new_shown, "reviews_shown": reviews_shown})
    settings = srs.clamp_settings(request.get_json(silent=True) or {})
    db.execute(
        "INSERT INTO srs_settings (user_id, new_per_day, reviews_per_day, notify_enabled, notify_hour) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET "
        "new_per_day = excluded.new_per_day, reviews_per_day = excluded.reviews_per_day, "
        "notify_enabled = excluded.notify_enabled, notify_hour = excluded.notify_hour",
        (user_id, settings["new_per_day"], settings["reviews_per_day"], settings["notify_enabled"], settings["notify_hour"]),
    )
    return jsonify(settings)


def format_book_size(size_bytes):
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


@app.route("/books")
@login_required
def books_page():
    db = get_db()
    rows = query_all(
        db,
        "SELECT id, title, filename, content_type, size_bytes FROM synced_books "
        "WHERE user_id = ? ORDER BY LOWER(title)",
        (session["user_id"],),
    )
    books = [
        {
            "id": row["id"],
            "title": row["title"],
            "filename": row["filename"],
            "inline": row["content_type"] in INLINE_BOOK_TYPES,
            "size": format_book_size(row["size_bytes"]),
        }
        for row in rows
    ]
    try:
        catalog_books = catalog.books_payload(db, session["user_id"])
    except Exception:
        catalog_books = []
    return render_template("books.html", books=books, catalog_books=catalog_books)


@app.route("/api/books", methods=["GET"])
@login_required
def api_books():
    db = get_db()
    rows = query_all(
        db,
        "SELECT id, external_id, title, filename, content_type, size_bytes FROM synced_books "
        "WHERE user_id = ? ORDER BY LOWER(title)",
        (session["user_id"],),
    )
    books = [
        {
            "id": row["id"], "external_id": row["external_id"], "title": row["title"],
            "filename": row["filename"], "content_type": row["content_type"], "size_bytes": row["size_bytes"],
        }
        for row in rows
    ]
    return jsonify({"books": books})


@app.route("/api/books/upload", methods=["POST"])
@login_required
def api_books_upload():
    """The desktop app pushes one book's raw bytes here per call (query string carries the
    metadata, the body is the file itself) -- only for books the student has explicitly
    flagged to sync, since a full book collection is too large to mirror wholesale."""
    external_id = request.args.get("external_id", "").strip()
    title = request.args.get("title", "").strip()
    filename = request.args.get("filename", "").strip()
    if not external_id or not title or not filename:
        return jsonify({"error": "external_id, title, and filename are required"}), 400

    content = request.get_data()
    if not content:
        return jsonify({"error": "no file content received"}), 400
    if len(content) > MAX_BOOK_SIZE:
        return jsonify({"error": f"file is larger than the {MAX_BOOK_SIZE // (1024 * 1024)} MB per-book sync limit"}), 413

    content_type = request.content_type or "application/octet-stream"
    if ";" in content_type:  # strip a charset parameter etc., e.g. "text/plain; charset=utf-8"
        content_type = content_type.split(";", 1)[0].strip()

    db = get_db()
    db.execute(
        "INSERT INTO synced_books (user_id, external_id, title, filename, content_type, size_bytes, content) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id, external_id) DO UPDATE SET "
        "title = excluded.title, filename = excluded.filename, content_type = excluded.content_type, "
        "size_bytes = excluded.size_bytes, content = excluded.content",
        (session["user_id"], external_id, title, filename, content_type, len(content), content),
    )
    return jsonify({"external_id": external_id, "size_bytes": len(content)})


@app.route("/api/books/finalize-sync", methods=["POST"])
@login_required
def api_books_finalize_sync():
    """Desktop is authoritative for which books are flagged to sync -- after pushing every
    currently-flagged book's content, it calls this with the full list of external_ids that
    should exist, so un-flagging a book on desktop removes it from the phone too."""
    payload = request.get_json(silent=True) or {}
    keep_ids = payload.get("external_ids", [])
    if not isinstance(keep_ids, list):
        return jsonify({"error": "external_ids must be a list"}), 400

    db = get_db()
    user_id = session["user_id"]
    existing = query_all(db, "SELECT id, external_id FROM synced_books WHERE user_id = ?", (user_id,))
    keep_ids = set(keep_ids)
    dropped = 0
    for row in existing:
        if row["external_id"] not in keep_ids:
            db.execute("DELETE FROM synced_books WHERE id = ?", (row["id"],))
            dropped += 1
    return jsonify({"dropped": dropped})


@app.route("/api/catalog/books/<book_id>/download", methods=["POST"])
@login_required
def api_catalog_download_book(book_id):
    result = catalog.download_book(get_db(), session["user_id"], book_id)
    if not result:
        return jsonify({"error": t("err_not_found")}), 404
    return jsonify(result)


@app.route("/api/books/<int:book_id>", methods=["DELETE"])
@login_required
def api_delete_book(book_id):
    db = get_db()
    row = query_one(
        db, "SELECT id FROM synced_books WHERE id = ? AND user_id = ?", (book_id, session["user_id"])
    )
    if not row:
        return jsonify({"error": t("err_not_found")}), 404
    db.execute("DELETE FROM book_highlights WHERE book_id = ? AND user_id = ?", (book_id, session["user_id"]))
    db.execute("DELETE FROM synced_books WHERE id = ?", (book_id,))
    return jsonify({"ok": True})


@app.route("/api/books/from-phone", methods=["POST"])
@login_required
def api_books_from_phone():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": t("unsupported_file")}), 400
    filename = secure_filename(uploaded.filename)
    ext = Path(filename).suffix.lower()
    content_type = PHONE_BOOK_TYPES.get(ext)
    if not content_type:
        return jsonify({"error": t("unsupported_file")}), 400
    content = uploaded.read()
    if not content:
        return jsonify({"error": t("unsupported_file")}), 400
    if len(content) > PHONE_BOOK_SIZE:
        return jsonify({"error": t("book_too_big")}), 413
    title = (request.form.get("title") or Path(filename).stem or "Book").strip()[:200]
    external_id = f"phone:{uuid.uuid4().hex}"
    inserted = query_one(
        get_db(),
        "INSERT INTO synced_books (user_id, external_id, title, filename, content_type, size_bytes, content, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'phone') RETURNING id",
        (session["user_id"], external_id, title, filename, content_type, len(content), content),
    )
    return jsonify({"id": inserted["id"], "title": title})


@app.route("/books/<int:book_id>/file")
@login_required
def book_file(book_id):
    db = get_db()
    row = query_one(
        db, "SELECT title, filename, content_type, content FROM synced_books WHERE id = ? AND user_id = ?",
        (book_id, session["user_id"]),
    )
    if not row:
        abort(404)
    disposition = "inline" if row["content_type"] in INLINE_BOOK_TYPES else "attachment"
    response = Response(bytes(row["content"]), mimetype=row["content_type"])
    response.headers["Content-Disposition"] = f'{disposition}; filename="{row["filename"]}"'
    return response


register_learn_routes(app, get_db, login_required)
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    local = not os.environ.get("RENDER")
    if local:
        # Without this, Flask keeps the previous HTML in memory, so login/register
        # edits never show until the process is killed and started again.
        app.config["TEMPLATES_AUTO_RELOAD"] = True
        app.jinja_env.auto_reload = True
        if "PORT" not in os.environ:
            import socket
            probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            in_use = probe.connect_ex(("127.0.0.1", port)) == 0
            probe.close()
            if in_use:
                # macOS AirPlay Receiver commonly occupies 5000.
                port = 5001
                print(f"Port 5000 is already in use. Open http://127.0.0.1:{port} instead.")
    app.run(host="0.0.0.0", port=port, debug=False)
