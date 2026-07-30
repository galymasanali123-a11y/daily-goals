"""Daily Goals — a small, mobile-friendly daily routine tracker, installable as a PWA.

Standalone from the desktop MedStudy Assistant (separate data, separate login).
Starts blank — add your own daily routine items in the app.
Run locally with: py app.py
Deploy: see README.md for Render.com instructions.
"""

import datetime
import os
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, redirect, render_template, request, send_from_directory, session, url_for

APP_PASSWORD = os.environ.get("APP_PASSWORD", "changeme")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
DB_PATH = Path(os.environ.get("DB_PATH", "daily_goals.db"))
STATIC_DIR = Path(__file__).parent / "static"

DEFAULT_GOALS = []

app = Flask(__name__)
app.secret_key = SECRET_KEY


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            sort_order INTEGER NOT NULL
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS completions (
            goal_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            done INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (goal_id, date)
        )"""
    )
    existing = db.execute("SELECT COUNT(*) FROM goals").fetchone()[0]
    if existing == 0:
        for index, text in enumerate(DEFAULT_GOALS):
            db.execute("INSERT INTO goals (text, sort_order) VALUES (?, ?)", (text, index))
    db.commit()
    db.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authed"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "not authenticated"}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password", "") == APP_PASSWORD:
            session["authed"] = True
            session.permanent = True
            return redirect(url_for("index"))
        error = "Wrong password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def today_str():
    return datetime.date.today().isoformat()


def compute_streak(db):
    """Consecutive days (ending today) with at least one goal completed."""
    rows = db.execute("SELECT DISTINCT date FROM completions WHERE done = 1").fetchall()
    done_dates = {row["date"] for row in rows}
    streak = 0
    day = datetime.date.today()
    while day.isoformat() in done_dates:
        streak += 1
        day -= datetime.timedelta(days=1)
    return streak


def goals_with_status(db):
    goals = db.execute("SELECT * FROM goals ORDER BY sort_order").fetchall()
    today = today_str()
    completions = {
        row["goal_id"]: bool(row["done"])
        for row in db.execute("SELECT goal_id, done FROM completions WHERE date = ?", (today,))
    }
    return [{"id": goal["id"], "text": goal["text"], "done": completions.get(goal["id"], False)} for goal in goals]


def current_state(db):
    goal_rows = goals_with_status(db)
    done_count = sum(1 for goal in goal_rows if goal["done"])
    return {
        "goals": goal_rows,
        "done_count": done_count,
        "total_count": len(goal_rows),
        "streak": compute_streak(db),
        "today": today_str(),
    }


@app.route("/")
@login_required
def index():
    db = get_db()
    return render_template("index.html", state=current_state(db))


@app.route("/sw.js")
def service_worker():
    response = send_from_directory(STATIC_DIR, "sw.js")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/api/state")
@login_required
def api_state():
    return jsonify(current_state(get_db()))


@app.route("/api/history")
@login_required
def api_history():
    db = get_db()
    total_goals = db.execute("SELECT COUNT(*) FROM goals").fetchone()[0]
    days = []
    for offset in range(6, -1, -1):
        day = (datetime.date.today() - datetime.timedelta(days=offset)).isoformat()
        count = db.execute(
            "SELECT COUNT(*) FROM completions WHERE date = ? AND done = 1", (day,)
        ).fetchone()[0]
        days.append({"date": day, "count": count})
    return jsonify({"days": days, "total_goals": total_goals})


@app.route("/api/toggle/<int:goal_id>", methods=["POST"])
@login_required
def api_toggle(goal_id):
    db = get_db()
    today = today_str()
    row = db.execute("SELECT done FROM completions WHERE goal_id = ? AND date = ?", (goal_id, today)).fetchone()
    new_done = 0 if row and row["done"] else 1
    db.execute(
        "INSERT INTO completions (goal_id, date, done) VALUES (?, ?, ?) "
        "ON CONFLICT(goal_id, date) DO UPDATE SET done = excluded.done",
        (goal_id, today, new_done),
    )
    db.commit()
    return jsonify(current_state(db))


@app.route("/api/goals", methods=["POST"])
@login_required
def api_add_goal():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    db = get_db()
    max_order = db.execute("SELECT COALESCE(MAX(sort_order), -1) FROM goals").fetchone()[0]
    db.execute("INSERT INTO goals (text, sort_order) VALUES (?, ?)", (text, max_order + 1))
    db.commit()
    return jsonify(current_state(db))


@app.route("/api/goals/<int:goal_id>/edit", methods=["POST"])
@login_required
def api_edit_goal(goal_id):
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    db = get_db()
    db.execute("UPDATE goals SET text = ? WHERE id = ?", (text, goal_id))
    db.commit()
    return jsonify(current_state(db))


@app.route("/api/goals/<int:goal_id>/delete", methods=["POST"])
@login_required
def api_delete_goal(goal_id):
    db = get_db()
    db.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    db.execute("DELETE FROM completions WHERE goal_id = ?", (goal_id,))
    db.commit()
    return jsonify(current_state(db))


@app.route("/api/goals/<int:goal_id>/move", methods=["POST"])
@login_required
def api_move_goal(goal_id):
    payload = request.get_json(silent=True) or {}
    direction = payload.get("direction")
    db = get_db()
    goals = db.execute("SELECT id, sort_order FROM goals ORDER BY sort_order").fetchall()
    ids = [goal["id"] for goal in goals]
    if goal_id not in ids:
        return jsonify({"error": "not found"}), 404

    index = ids.index(goal_id)
    swap_with = index - 1 if direction == "up" else index + 1 if direction == "down" else None
    if swap_with is not None and 0 <= swap_with < len(ids):
        goal_a, goal_b = goals[index], goals[swap_with]
        db.execute("UPDATE goals SET sort_order = ? WHERE id = ?", (goal_b["sort_order"], goal_a["id"]))
        db.execute("UPDATE goals SET sort_order = ? WHERE id = ?", (goal_a["sort_order"], goal_b["id"]))
        db.commit()
    return jsonify(current_state(db))


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
