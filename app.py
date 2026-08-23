"""Daily Goals — a small, mobile-friendly daily routine tracker, installable as a PWA.

Multi-user: each person registers their own account and sees only their own goals.
Storage is libSQL (SQLite-compatible): a local file when run locally, or a Turso
database in production so data survives redeploys (Render's local disk doesn't).

Run locally with: py app.py
Deploy: see README.md for Render.com + Turso instructions.
"""

import datetime
import json
import os
from functools import wraps
from pathlib import Path

import libsql_client
from flask import Flask, g, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")

# Render's local disk is wiped on every redeploy. Falling back to it silently here has, in
# practice, silently deleted every account on the next deploy with no error anywhere -- refuse
# to start on Render at all without Turso configured, rather than repeat that quietly.
if os.environ.get("RENDER") and not TURSO_DATABASE_URL:
    raise RuntimeError(
        "TURSO_DATABASE_URL is not set. Running on Render without it means every account and "
        "goal is stored on disk that gets wiped on the next deploy. Set TURSO_DATABASE_URL and "
        "TURSO_AUTH_TOKEN in the Render dashboard's Environment tab, then redeploy."
    )

DB_URL = TURSO_DATABASE_URL or f"file:{os.environ.get('DB_PATH', 'daily_goals.db')}"
STATIC_DIR = Path(__file__).parent / "static"

app = Flask(__name__)
app.secret_key = SECRET_KEY
# Sessions are marked permanent on login/register (session.permanent = True) -- without this,
# Flask's default permanent-session lifetime is only 31 days, which reads as "randomly signed
# out" on an app people check daily. A year is effectively "don't sign me out".
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(days=365)


def connect_db():
    return libsql_client.create_client_sync(DB_URL, auth_token=TURSO_AUTH_TOKEN)


def query_one(db, sql, params=()):
    rows = db.execute(sql, params).rows
    return rows[0] if rows else None


def query_all(db, sql, params=()):
    return db.execute(sql, params).rows


def get_db():
    if "db" not in g:
        g.db = connect_db()
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = connect_db()
    db.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL DEFAULT '',
            password_hash TEXT NOT NULL
        )"""
    )
    # Migrate a database created before the email column existed.
    user_columns = {row["name"] for row in db.execute("PRAGMA table_info(users)").rows}
    if "email" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''")
    # A real (case-insensitive) uniqueness guarantee — "Alice" and "alice" can't both register.
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_nocase ON users(username COLLATE NOCASE)")
    db.execute(
        """CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            text TEXT NOT NULL,
            sort_order INTEGER NOT NULL
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS completions (
            goal_id INTEGER NOT NULL REFERENCES goals(id),
            date TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (goal_id, date)
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS synced_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            external_id TEXT NOT NULL,
            date TEXT NOT NULL,
            text TEXT NOT NULL,
            time TEXT NOT NULL DEFAULT '',
            task_type TEXT NOT NULL DEFAULT 'Task',
            done INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, external_id)
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS synced_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            external_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            options_json TEXT NOT NULL DEFAULT '[]',
            example TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            due TEXT NOT NULL DEFAULT '0000-00-00',
            interval INTEGER NOT NULL DEFAULT 1,
            ease REAL NOT NULL DEFAULT 2.5,
            reps INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, external_id)
        )"""
    )
    # Migrate a database created before leech tracking existed.
    card_columns = {row["name"] for row in db.execute("PRAGMA table_info(synced_cards)").rows}
    if "lapses" not in card_columns:
        db.execute("ALTER TABLE synced_cards ADD COLUMN lapses INTEGER NOT NULL DEFAULT 0")
    db.execute(
        """CREATE TABLE IF NOT EXISTS card_review_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            external_id TEXT NOT NULL,
            confidence INTEGER NOT NULL DEFAULT 3,
            reviewed_at TEXT NOT NULL
        )"""
    )
    # Migrate a database created before confidence ratings existed (was a plain correct/wrong flag).
    review_columns = {row["name"] for row in db.execute("PRAGMA table_info(card_review_events)").rows}
    if "confidence" not in review_columns:
        db.execute("ALTER TABLE card_review_events ADD COLUMN confidence INTEGER NOT NULL DEFAULT 3")
        if "correct" in review_columns:
            db.execute("UPDATE card_review_events SET confidence = CASE WHEN correct = 1 THEN 3 ELSE 1 END")
    db.execute(
        """CREATE TABLE IF NOT EXISTS new_card_intro_state (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            date TEXT NOT NULL,
            ids_json TEXT NOT NULL DEFAULT '[]'
        )"""
    )
    db.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "not authenticated"}), 401
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
            error = "Username, email, and password are all required."
        elif "@" not in email or "." not in email.split("@")[-1]:
            error = "Enter a valid email address."
        elif password != confirm:
            error = "Passwords don't match."
        elif len(password) < 4:
            error = "Password must be at least 4 characters."
        else:
            db = get_db()
            existing = query_one(db, "SELECT id FROM users WHERE username = ? COLLATE NOCASE", (username,))
            if existing:
                error = "That username is already taken."
            else:
                try:
                    result = db.execute(
                        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                        (username, email, generate_password_hash(password)),
                    )
                except Exception:
                    error = "That username is already taken."
                else:
                    session["user_id"] = result.last_insert_rowid
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
        user = query_one(db, "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,))
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session.permanent = True
            return redirect(url_for("index"))
        error = "Wrong username or password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def today_str():
    return datetime.date.today().isoformat()


def compute_streak(db, user_id):
    """Consecutive days (ending today) with at least one goal or synced task completed, for this user."""
    goal_dates = {
        row["date"]
        for row in query_all(
            db,
            "SELECT DISTINCT c.date AS date FROM completions c JOIN goals g ON g.id = c.goal_id "
            "WHERE g.user_id = ? AND c.done = 1",
            (user_id,),
        )
    }
    synced_dates = {
        row["date"]
        for row in query_all(db, "SELECT DISTINCT date FROM synced_tasks WHERE user_id = ? AND done = 1", (user_id,))
    }
    done_dates = goal_dates | synced_dates
    streak = 0
    day = datetime.date.today()
    while day.isoformat() in done_dates:
        streak += 1
        day -= datetime.timedelta(days=1)
    return streak


def goals_with_status(db, user_id):
    goals = query_all(db, "SELECT * FROM goals WHERE user_id = ? ORDER BY sort_order", (user_id,))
    today = today_str()
    completions = {
        row["goal_id"]: bool(row["done"])
        for row in query_all(
            db,
            "SELECT c.goal_id AS goal_id, c.done AS done FROM completions c JOIN goals g ON g.id = c.goal_id "
            "WHERE g.user_id = ? AND c.date = ?",
            (user_id, today),
        )
    }
    return [{"id": goal["id"], "text": goal["text"], "done": completions.get(goal["id"], False)} for goal in goals]


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


def apply_review_result(card_state, confidence):
    """Same SM-2-lite schedule as the desktop app (main.py / medstudy_gui.py) — kept in sync by hand
    since this Flask service has no shared package with the desktop code. 1=Again, 2=Hard,
    3=Good, 4=Easy; "Again" always resets the card, higher confidence grows the interval faster."""
    confidence = max(1, min(4, int(confidence)))
    ease = card_state.get("ease", 2.5)
    reps = card_state.get("reps", 0)

    if confidence == 1:
        reps = 0
        interval = 1
        ease = max(1.3, ease - 0.2)
    else:
        reps += 1
        if reps == 1:
            interval = 1
        elif reps == 2:
            interval = 6
        else:
            interval = round(card_state.get("interval", 1) * ease)

        if confidence == 2:
            interval = max(1, round(interval * 0.6))
            ease = max(1.3, ease - 0.15)
        elif confidence == 3:
            ease = min(2.6, ease + 0.1)
        else:  # confidence == 4, Easy
            interval = round(interval * 1.3)
            ease = min(2.8, ease + 0.15)

    due = (datetime.date.today() + datetime.timedelta(days=interval)).isoformat()
    lapses = card_state.get("lapses", 0) + (1 if confidence == 1 else 0)
    return {"reps": reps, "interval": interval, "ease": round(ease, 2), "due": due, "lapses": lapses}


LEECH_THRESHOLD = 4


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
    }


def cards_for_user(db, user_id):
    rows = query_all(db, "SELECT * FROM synced_cards WHERE user_id = ? ORDER BY topic, question", (user_id,))
    return [card_row_to_dict(row) for row in rows]


NEW_CARDS_PER_DAY = 20


def select_study_cards(cards, db, user_id, new_limit=NEW_CARDS_PER_DAY):
    """External ids of cards actually worth studying today: every card already in the review
    cycle that's due, plus up to `new_limit` never-reviewed cards -- same "new cards/day" cap
    as the desktop app, mirrored here so the phone doesn't dump an entire freshly-synced deck
    on you at once. State persists per user across a day so the set stays stable on reload.
    """
    today = today_str()
    row = query_one(db, "SELECT date, ids_json FROM new_card_intro_state WHERE user_id = ?", (user_id,))
    already_introduced = set(json.loads(row["ids_json"])) if row and row["date"] == today else set()

    review_due = [c for c in cards if c["due"] and c["due"] != "0000-00-00" and c["due"] <= today]
    new_cards = [c for c in cards if not c["due"] or c["due"] == "0000-00-00"]

    still_introduced = [c for c in new_cards if c["external_id"] in already_introduced]
    fresh_candidates = [c for c in new_cards if c["external_id"] not in already_introduced]
    remaining_slots = max(0, new_limit - len(still_introduced))
    newly_introduced = fresh_candidates[:remaining_slots]

    updated_ids = already_introduced | {c["external_id"] for c in still_introduced + newly_introduced}
    db.execute(
        "INSERT INTO new_card_intro_state (user_id, date, ids_json) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET date = excluded.date, ids_json = excluded.ids_json",
        (user_id, today, json.dumps(list(updated_ids))),
    )
    return {c["external_id"] for c in review_due + still_introduced + newly_introduced}


def current_state(db, user_id):
    goal_rows = goals_with_status(db, user_id)
    synced_rows = synced_tasks_for_today(db, user_id)
    done_count = sum(1 for goal in goal_rows if goal["done"]) + sum(1 for task in synced_rows if task["done"])
    total_count = len(goal_rows) + len(synced_rows)
    return {
        "goals": goal_rows,
        "synced_tasks": synced_rows,
        "done_count": done_count,
        "total_count": total_count,
        "streak": compute_streak(db, user_id),
        "today": today_str(),
        "username": session.get("username"),
    }


def owned_goal(db, user_id, goal_id):
    """Fetch a goal only if it belongs to this user — prevents editing someone else's goals by guessing an id."""
    return query_one(db, "SELECT * FROM goals WHERE id = ? AND user_id = ?", (goal_id, user_id))


@app.route("/")
@login_required
def index():
    db = get_db()
    return render_template("index.html", state=current_state(db, session["user_id"]))


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
    db = get_db()
    user_id = session["user_id"]
    total_goals = query_one(db, "SELECT COUNT(*) AS n FROM goals WHERE user_id = ?", (user_id,))["n"]
    days = []
    for offset in range(6, -1, -1):
        day = (datetime.date.today() - datetime.timedelta(days=offset)).isoformat()
        count = query_one(
            db,
            "SELECT COUNT(*) AS n FROM completions c JOIN goals g ON g.id = c.goal_id "
            "WHERE g.user_id = ? AND c.date = ? AND c.done = 1",
            (user_id, day),
        )["n"]
        days.append({"date": day, "count": count})
    return jsonify({"days": days, "total_goals": total_goals})


@app.route("/api/toggle/<int:goal_id>", methods=["POST"])
@login_required
def api_toggle(goal_id):
    db = get_db()
    user_id = session["user_id"]
    if not owned_goal(db, user_id, goal_id):
        return jsonify({"error": "not found"}), 404
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
        return jsonify({"error": "text is required"}), 400
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
        return jsonify({"error": "text is required"}), 400
    db = get_db()
    user_id = session["user_id"]
    if not owned_goal(db, user_id, goal_id):
        return jsonify({"error": "not found"}), 404
    db.execute("UPDATE goals SET text = ? WHERE id = ?", (text, goal_id))
    return jsonify(current_state(db, user_id))


@app.route("/api/goals/<int:goal_id>/delete", methods=["POST"])
@login_required
def api_delete_goal(goal_id):
    db = get_db()
    user_id = session["user_id"]
    if not owned_goal(db, user_id, goal_id):
        return jsonify({"error": "not found"}), 404
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
        return jsonify({"error": "not found"}), 404

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
        return jsonify({"error": "not found"}), 404
    new_done = 0 if row["done"] else 1
    db.execute("UPDATE synced_tasks SET done = ? WHERE id = ?", (new_done, task_id))
    return jsonify(current_state(db, user_id))


@app.route("/flashcards")
@login_required
def flashcards_page():
    return render_template("flashcards.html")


@app.route("/api/cards", methods=["GET"])
@login_required
def api_cards():
    db = get_db()
    user_id = session["user_id"]
    cards = cards_for_user(db, user_id)
    due_today_ids = select_study_cards(cards, db, user_id)
    for card in cards:
        card["due_today"] = card["external_id"] in due_today_ids
    topics = sorted({card["topic"] for card in cards})
    return jsonify({"cards": cards, "topics": topics, "today": today_str()})


@app.route("/api/cards/pull-reviews", methods=["POST"])
@login_required
def api_cards_pull_reviews():
    """The desktop app calls this before pushing: fetch review events made on the phone since the
    last sync (oldest first, so SM-2 intervals apply in the order they actually happened), then
    clear them out — they're consumed exactly once."""
    db = get_db()
    user_id = session["user_id"]
    rows = query_all(
        db,
        "SELECT id, external_id, confidence, reviewed_at FROM card_review_events "
        "WHERE user_id = ? ORDER BY reviewed_at, id",
        (user_id,),
    )
    events = [{"external_id": row["external_id"], "confidence": row["confidence"], "reviewed_at": row["reviewed_at"]} for row in rows]
    if rows:
        db.execute("DELETE FROM card_review_events WHERE user_id = ?", (user_id,))
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

        db.execute(
            "INSERT INTO synced_cards (user_id, external_id, topic, question, answer, options_json, "
            "example, notes, due, interval, ease, reps, lapses) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, external_id) DO UPDATE SET "
            "topic = excluded.topic, question = excluded.question, answer = excluded.answer, "
            "options_json = excluded.options_json, example = excluded.example, notes = excluded.notes, "
            "due = excluded.due, interval = excluded.interval, ease = excluded.ease, reps = excluded.reps, "
            "lapses = excluded.lapses",
            (user_id, external_id, topic, question, answer, options_json, example, notes, due, interval, ease, reps, lapses),
        )

    # A card no longer in the desktop's deck (deleted there) drops out here too.
    existing = query_all(db, "SELECT id, external_id FROM synced_cards WHERE user_id = ?", (user_id,))
    for row in existing:
        if row["external_id"] not in incoming_ids:
            db.execute("DELETE FROM synced_cards WHERE id = ?", (row["id"],))

    return jsonify({"card_count": len(incoming_ids)})


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
        return jsonify({"error": "not found"}), 404

    updated = apply_review_result(
        {"ease": row["ease"], "reps": row["reps"], "interval": row["interval"], "lapses": row["lapses"]}, confidence
    )
    db.execute(
        "UPDATE synced_cards SET due = ?, interval = ?, ease = ?, reps = ?, lapses = ? WHERE id = ?",
        (updated["due"], updated["interval"], updated["ease"], updated["reps"], updated["lapses"], card_id),
    )
    db.execute(
        "INSERT INTO card_review_events (user_id, external_id, confidence, reviewed_at) VALUES (?, ?, ?, ?)",
        (user_id, row["external_id"], confidence, datetime.datetime.now().isoformat()),
    )
    result = card_row_to_dict(row)
    result.update(due=updated["due"], interval=updated["interval"], ease=updated["ease"], reps=updated["reps"], lapses=updated["lapses"])
    return jsonify(result)


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
