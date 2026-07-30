"""Daily Goals — a small, mobile-friendly daily routine tracker, installable as a PWA.

Multi-user: each person registers their own account and sees only their own goals.
Run locally with: py app.py
Deploy: see README.md for Render.com instructions.
"""

import datetime
import os
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
DB_PATH = Path(os.environ.get("DB_PATH", "daily_goals.db"))
STATIC_DIR = Path(__file__).parent / "static"

app = Flask(__name__)
app.secret_key = SECRET_KEY


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
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
    db.commit()
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
            existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if existing:
                error = "That username is already taken."
            else:
                cursor = db.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
                session["user_id"] = cursor.lastrowid
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
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
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
    """Consecutive days (ending today) with at least one goal completed, for this user."""
    rows = db.execute(
        "SELECT DISTINCT c.date FROM completions c JOIN goals g ON g.id = c.goal_id "
        "WHERE g.user_id = ? AND c.done = 1",
        (user_id,),
    ).fetchall()
    done_dates = {row["date"] for row in rows}
    streak = 0
    day = datetime.date.today()
    while day.isoformat() in done_dates:
        streak += 1
        day -= datetime.timedelta(days=1)
    return streak


def goals_with_status(db, user_id):
    goals = db.execute("SELECT * FROM goals WHERE user_id = ? ORDER BY sort_order", (user_id,)).fetchall()
    today = today_str()
    completions = {
        row["goal_id"]: bool(row["done"])
        for row in db.execute(
            "SELECT c.goal_id, c.done FROM completions c JOIN goals g ON g.id = c.goal_id "
            "WHERE g.user_id = ? AND c.date = ?",
            (user_id, today),
        )
    }
    return [{"id": goal["id"], "text": goal["text"], "done": completions.get(goal["id"], False)} for goal in goals]


def current_state(db, user_id):
    goal_rows = goals_with_status(db, user_id)
    done_count = sum(1 for goal in goal_rows if goal["done"])
    return {
        "goals": goal_rows,
        "done_count": done_count,
        "total_count": len(goal_rows),
        "streak": compute_streak(db, user_id),
        "today": today_str(),
        "username": session.get("username"),
    }


def owned_goal(db, user_id, goal_id):
    """Fetch a goal only if it belongs to this user — prevents editing someone else's goals by guessing an id."""
    return db.execute("SELECT * FROM goals WHERE id = ? AND user_id = ?", (goal_id, user_id)).fetchone()


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
    total_goals = db.execute("SELECT COUNT(*) FROM goals WHERE user_id = ?", (user_id,)).fetchone()[0]
    days = []
    for offset in range(6, -1, -1):
        day = (datetime.date.today() - datetime.timedelta(days=offset)).isoformat()
        count = db.execute(
            "SELECT COUNT(*) FROM completions c JOIN goals g ON g.id = c.goal_id "
            "WHERE g.user_id = ? AND c.date = ? AND c.done = 1",
            (user_id, day),
        ).fetchone()[0]
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
    row = db.execute("SELECT done FROM completions WHERE goal_id = ? AND date = ?", (goal_id, today)).fetchone()
    new_done = 0 if row and row["done"] else 1
    db.execute(
        "INSERT INTO completions (goal_id, date, done) VALUES (?, ?, ?) "
        "ON CONFLICT(goal_id, date) DO UPDATE SET done = excluded.done",
        (goal_id, today, new_done),
    )
    db.commit()
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
    max_order = db.execute("SELECT COALESCE(MAX(sort_order), -1) FROM goals WHERE user_id = ?", (user_id,)).fetchone()[0]
    db.execute("INSERT INTO goals (user_id, text, sort_order) VALUES (?, ?, ?)", (user_id, text, max_order + 1))
    db.commit()
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
    db.commit()
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
    db.commit()
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

    goals = db.execute("SELECT id, sort_order FROM goals WHERE user_id = ? ORDER BY sort_order", (user_id,)).fetchall()
    ids = [goal["id"] for goal in goals]
    index = ids.index(goal_id)
    swap_with = index - 1 if direction == "up" else index + 1 if direction == "down" else None
    if swap_with is not None and 0 <= swap_with < len(ids):
        goal_a, goal_b = goals[index], goals[swap_with]
        db.execute("UPDATE goals SET sort_order = ? WHERE id = ?", (goal_b["sort_order"], goal_a["id"]))
        db.execute("UPDATE goals SET sort_order = ? WHERE id = ?", (goal_a["sort_order"], goal_b["id"]))
        db.commit()
    return jsonify(current_state(db, user_id))


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
