"""Daily Goals — a small, mobile-friendly daily routine tracker, installable as a PWA.

Multi-user: each person registers their own account and sees only their own goals.
Storage is libSQL (SQLite-compatible): a local file when run locally, or a Turso
database in production so data survives redeploys (Render's local disk doesn't).

Run locally with: py app.py
Deploy: see README.md for Render.com + Turso instructions.
"""

import datetime
import os
from functools import wraps
from pathlib import Path

import libsql_client
from flask import Flask, g, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")
DB_URL = TURSO_DATABASE_URL or f"file:{os.environ.get('DB_PATH', 'daily_goals.db')}"
STATIC_DIR = Path(__file__).parent / "static"

app = Flask(__name__)
app.secret_key = SECRET_KEY


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
            password_hash TEXT NOT NULL
        )"""
    )
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
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if not username or not password:
            error = "Username and password are required."
        elif password != confirm:
            error = "Passwords don't match."
        elif len(password) < 4:
            error = "Password must be at least 4 characters."
        else:
            db = get_db()
            existing = query_one(db, "SELECT id FROM users WHERE username = ?", (username,))
            if existing:
                error = "That username is already taken."
            else:
                result = db.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
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
        user = query_one(db, "SELECT * FROM users WHERE username = ?", (username,))
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


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
