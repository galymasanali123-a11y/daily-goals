"""Learn catalog, lesson progress, and the book reader."""

from __future__ import annotations

import datetime
import json

from flask import abort, jsonify, redirect, render_template, request, session, url_for

from courses import (
    catalog_payload,
    course_payload,
    empty_progress,
    lesson_complete,
    lesson_key,
    progress_map,
    render_sections,
)
from curriculum import card_external_id, get_course, get_lesson, get_level, lesson_topic
from db import query_all, query_one
import srs


def _progress_rows(db, user_id):
    return query_all(
        db,
        "SELECT course_slug, lesson_slug, grammar_done, cards_added, exercises_correct, "
        "exercises_total, answers_json, completed FROM lesson_progress WHERE user_id = ?",
        (user_id,),
    )


def _lesson_progress(db, user_id, course_slug, lesson_slug):
    row = query_one(
        db,
        "SELECT grammar_done, cards_added, exercises_correct, exercises_total, answers_json, completed "
        "FROM lesson_progress WHERE user_id = ? AND course_slug = ? AND lesson_slug = ?",
        (user_id, course_slug, lesson_slug),
    )
    if not row:
        data = empty_progress()
        data["answers"] = {}
        return data
    data = {
        "grammar_done": int(row["grammar_done"] or 0),
        "cards_added": int(row["cards_added"] or 0),
        "exercises_correct": int(row["exercises_correct"] or 0),
        "exercises_total": int(row["exercises_total"] or 0),
        "completed": int(row["completed"] or 0),
        "answers": json.loads(row["answers_json"] or "{}"),
    }
    return data


def _upsert_progress(db, user_id, course_slug, lesson_slug, fields, lesson):
    current = _lesson_progress(db, user_id, course_slug, lesson_slug)
    current.update(fields)
    if lesson_complete(lesson, current):
        current["completed"] = 1
    answers_json = json.dumps(current.get("answers") or {})
    now = datetime.datetime.now().isoformat(timespec="seconds")
    db.execute(
        "INSERT INTO lesson_progress (user_id, course_slug, lesson_slug, grammar_done, cards_added, "
        "exercises_correct, exercises_total, answers_json, completed, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id, course_slug, lesson_slug) DO UPDATE SET "
        "grammar_done = excluded.grammar_done, cards_added = excluded.cards_added, "
        "exercises_correct = excluded.exercises_correct, exercises_total = excluded.exercises_total, "
        "answers_json = excluded.answers_json, completed = excluded.completed, updated_at = excluded.updated_at",
        (
            user_id, course_slug, lesson_slug,
            int(current.get("grammar_done") or 0),
            int(current.get("cards_added") or 0),
            int(current.get("exercises_correct") or 0),
            int(current.get("exercises_total") or 0),
            answers_json,
            int(current.get("completed") or 0),
            now,
        ),
    )
    return _lesson_progress(db, user_id, course_slug, lesson_slug)


def _neighbors(level, lesson_slug):
    slugs = [item["slug"] for item in level["lessons"]]
    index = slugs.index(lesson_slug)
    prev_slug = slugs[index - 1] if index > 0 else None
    next_slug = slugs[index + 1] if index + 1 < len(slugs) else None
    titles = {item["slug"]: item["title"] for item in level["lessons"]}
    return {
        "prev": {"slug": prev_slug, "title": titles[prev_slug]} if prev_slug else None,
        "next": {"slug": next_slug, "title": titles[next_slug]} if next_slug else None,
    }


def register_learn_routes(app, get_db, login_required):
    @app.route("/learn")
    @login_required
    def learn_page():
        db = get_db()
        progress = progress_map(_progress_rows(db, session["user_id"]))
        return render_template("learn.html", courses=catalog_payload(progress))

    @app.route("/learn/<course_slug>")
    @login_required
    def course_page(course_slug):
        course = get_course(course_slug)
        if not course:
            abort(404)
        db = get_db()
        progress = progress_map(_progress_rows(db, session["user_id"]))
        return render_template("course.html", course=course_payload(course, progress))

    @app.route("/learn/<course_slug>/<level_slug>/<lesson_slug>")
    @login_required
    def lesson_page(course_slug, level_slug, lesson_slug):
        course = get_course(course_slug)
        level = get_level(course, level_slug)
        lesson = get_lesson(course, level_slug, lesson_slug)
        if not course or not level or not lesson:
            abort(404)
        db = get_db()
        progress = _lesson_progress(db, session["user_id"], course_slug, lesson_slug)
        return render_template(
            "lesson.html",
            course=course,
            level=level,
            lesson=lesson,
            progress=progress,
            body_html=render_sections(lesson.get("sections")),
            neighbors=_neighbors(level, lesson_slug),
            finished=lesson_complete(lesson, progress),
        )

    @app.route("/api/learn/<course_slug>/<level_slug>/<lesson_slug>/grammar", methods=["POST"])
    @login_required
    def api_lesson_grammar(course_slug, level_slug, lesson_slug):
        course = get_course(course_slug)
        lesson = get_lesson(course, level_slug, lesson_slug)
        if not lesson:
            return jsonify({"error": "not found"}), 404
        progress = _upsert_progress(
            get_db(), session["user_id"], course_slug, lesson_slug, {"grammar_done": 1}, lesson
        )
        return jsonify({"progress": progress, "completed": bool(progress.get("completed"))})

    @app.route("/api/learn/<course_slug>/<level_slug>/<lesson_slug>/cards", methods=["POST"])
    @login_required
    def api_lesson_cards(course_slug, level_slug, lesson_slug):
        course = get_course(course_slug)
        level = get_level(course, level_slug)
        lesson = get_lesson(course, level_slug, lesson_slug)
        if not lesson:
            return jsonify({"error": "not found"}), 404
        db = get_db()
        user_id = session["user_id"]
        topic = lesson_topic(course, level, lesson)
        added = 0
        for word in lesson.get("vocab") or []:
            external_id = card_external_id(course_slug, level_slug, lesson_slug, word["id"])
            existing = query_one(
                db, "SELECT id FROM synced_cards WHERE user_id = ? AND external_id = ?", (user_id, external_id)
            )
            if existing:
                continue
            db.execute(
                "INSERT INTO synced_cards (user_id, external_id, topic, question, answer, options_json, "
                "example, notes, due, interval, ease, reps, lapses, queue, due_at, learn_step, source) "
                "VALUES (?, ?, ?, ?, ?, '[]', ?, '', ?, 0, ?, 0, 0, 0, '', 0, 'course')",
                (
                    user_id, external_id, topic, word["front"], word["back"],
                    word.get("example") or "", srs.NEW_SENTINEL, srs.STARTING_EASE,
                ),
            )
            added += 1
        progress = _upsert_progress(db, user_id, course_slug, lesson_slug, {"cards_added": 1}, lesson)
        return jsonify({"added": added, "progress": progress, "topic": topic})

    @app.route("/api/learn/<course_slug>/<level_slug>/<lesson_slug>/exercises", methods=["POST"])
    @login_required
    def api_lesson_exercises(course_slug, level_slug, lesson_slug):
        course = get_course(course_slug)
        lesson = get_lesson(course, level_slug, lesson_slug)
        if not lesson:
            return jsonify({"error": "not found"}), 404
        payload = request.get_json(silent=True) or {}
        submitted = payload.get("answers") or {}
        results = []
        correct_count = 0
        for index, exercise in enumerate(lesson.get("exercises") or []):
            expected = str(exercise.get("answer", "")).strip()
            given = str(submitted.get(str(index), submitted.get(index, ""))).strip()
            ok = given.lower() == expected.lower()
            if ok:
                correct_count += 1
            results.append(
                {
                    "index": index,
                    "correct": ok,
                    "expected": expected,
                    "explanation": exercise.get("explanation") or "",
                }
            )
        progress = _upsert_progress(
            get_db(),
            session["user_id"],
            course_slug,
            lesson_slug,
            {
                "exercises_correct": correct_count,
                "exercises_total": len(results),
                "answers": {str(index): str(submitted.get(str(index), submitted.get(index, ""))) for index in range(len(results))},
            },
            lesson,
        )
        return jsonify({"results": results, "correct": correct_count, "total": len(results), "progress": progress})

    @app.route("/books/<int:book_id>")
    @login_required
    def book_reader(book_id):
        db = get_db()
        row = query_one(
            db,
            "SELECT id, title, filename, content_type, size_bytes, content FROM synced_books "
            "WHERE id = ? AND user_id = ?",
            (book_id, session["user_id"]),
        )
        if not row:
            abort(404)
        content_type = row["content_type"] or "application/octet-stream"
        text_body = None
        if content_type in {"text/plain", "text/markdown"}:
            raw = bytes(row["content"] or b"")
            text_body = raw.decode("utf-8", errors="replace")
        highlights = query_all(
            db,
            "SELECT id, start_offset, end_offset, color, snippet, note, created_at FROM book_highlights "
            "WHERE user_id = ? AND book_id = ? ORDER BY start_offset, id",
            (session["user_id"], book_id),
        )
        return render_template(
            "book_reader.html",
            book={
                "id": row["id"],
                "title": row["title"],
                "filename": row["filename"],
                "content_type": content_type,
                "is_pdf": content_type == "application/pdf",
                "is_text": text_body is not None,
                "file_url": url_for("book_file", book_id=book_id),
            },
            text_body=text_body,
            highlights=[dict(item) for item in highlights],
        )

    @app.route("/api/books/<int:book_id>/highlights", methods=["GET", "POST"])
    @login_required
    def api_book_highlights(book_id):
        db = get_db()
        user_id = session["user_id"]
        book = query_one(db, "SELECT id FROM synced_books WHERE id = ? AND user_id = ?", (book_id, user_id))
        if not book:
            return jsonify({"error": "not found"}), 404
        if request.method == "GET":
            rows = query_all(
                db,
                "SELECT id, start_offset, end_offset, color, snippet, note, created_at FROM book_highlights "
                "WHERE user_id = ? AND book_id = ? ORDER BY id",
                (user_id, book_id),
            )
            return jsonify({"highlights": [dict(row) for row in rows]})

        payload = request.get_json(silent=True) or {}
        color = str(payload.get("color") or "yellow").strip()[:20]
        if color not in {"yellow", "green", "pink", "blue"}:
            color = "yellow"
        snippet = str(payload.get("snippet") or "")[:2000]
        note = str(payload.get("note") or "")[:2000]
        try:
            start = max(0, int(payload.get("start_offset", 0)))
            end = max(start, int(payload.get("end_offset", start)))
        except (TypeError, ValueError):
            return jsonify({"error": "offsets must be numbers"}), 400
        created = datetime.datetime.now().isoformat(timespec="seconds")
        inserted = query_one(
            db,
            "INSERT INTO book_highlights (user_id, book_id, start_offset, end_offset, color, snippet, note, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id, start_offset, end_offset, color, snippet, note, created_at",
            (user_id, book_id, start, end, color, snippet, note, created),
        )
        return jsonify(dict(inserted)), 201

    @app.route("/api/books/<int:book_id>/highlights/<int:highlight_id>", methods=["POST", "DELETE"])
    @login_required
    def api_book_highlight_item(book_id, highlight_id):
        db = get_db()
        user_id = session["user_id"]
        row = query_one(
            db,
            "SELECT id FROM book_highlights WHERE id = ? AND book_id = ? AND user_id = ?",
            (highlight_id, book_id, user_id),
        )
        if not row:
            return jsonify({"error": "not found"}), 404
        if request.method == "DELETE":
            db.execute("DELETE FROM book_highlights WHERE id = ?", (highlight_id,))
            return jsonify({"ok": True})
        payload = request.get_json(silent=True) or {}
        note = str(payload.get("note") or "")[:2000]
        color = str(payload.get("color") or "").strip()
        if color and color in {"yellow", "green", "pink", "blue"}:
            db.execute("UPDATE book_highlights SET note = ?, color = ? WHERE id = ?", (note, color, highlight_id))
        else:
            db.execute("UPDATE book_highlights SET note = ? WHERE id = ?", (note, highlight_id))
        updated = query_one(
            db,
            "SELECT id, start_offset, end_offset, color, snippet, note, created_at FROM book_highlights WHERE id = ?",
            (highlight_id,),
        )
        return jsonify(dict(updated))

    # Keep a named endpoint unused warning away — redirect old file-only habits to the reader.
    @app.route("/books/<int:book_id>/open")
    @login_required
    def book_open_alias(book_id):
        return redirect(url_for("book_reader", book_id=book_id))
