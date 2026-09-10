"""Course progress helpers. Curriculum lives in Python modules; only progress is stored."""

from markupsafe import Markup, escape

from content_i18n import course_field, from_packed, lesson_field, level_field
from curriculum import BY_SLUG, course_counts
from i18n import current_lang, t


def lesson_key(course_slug, lesson_slug):
    return f"{course_slug}:{lesson_slug}"


def empty_progress():
    return {
        "grammar_done": 0,
        "cards_added": 0,
        "exercises_correct": 0,
        "exercises_total": 0,
        "completed": 0,
    }


def progress_map(rows):
    mapping = {}
    for row in rows:
        mapping[lesson_key(row["course_slug"], row["lesson_slug"])] = {
            "grammar_done": int(row["grammar_done"] or 0),
            "cards_added": int(row["cards_added"] or 0),
            "exercises_correct": int(row["exercises_correct"] or 0),
            "exercises_total": int(row["exercises_total"] or 0),
            "completed": int(row["completed"] or 0),
        }
    return mapping


def lesson_complete(lesson, progress):
    if progress.get("completed"):
        return True
    grammar = bool(progress.get("grammar_done"))
    exercises = lesson.get("exercises") or []
    if not exercises:
        return grammar
    total = progress.get("exercises_total") or 0
    correct = progress.get("exercises_correct") or 0
    return grammar and total >= len(exercises) and correct == len(exercises)


def course_payload(course, progress, lang=None):
    lang = lang or current_lang()
    slug = course["slug"]
    counts = course_counts(course)
    levels = []
    done_lessons = 0
    total_lessons = 0
    for level in course["levels"]:
        lessons = []
        level_done = 0
        for lesson in level["lessons"]:
            total_lessons += 1
            item = progress.get(lesson_key(course["slug"], lesson["slug"]), empty_progress())
            finished = lesson_complete(lesson, item)
            if finished:
                done_lessons += 1
                level_done += 1
            lessons.append(
                {
                    "slug": lesson["slug"],
                    "title": from_packed(lesson, "title", lang, lesson_field(slug, lesson["slug"], "title", lesson["title"], lang)),
                    "minutes": lesson["minutes"],
                    "summary": from_packed(lesson, "summary", lang, lesson_field(slug, lesson["slug"], "summary", lesson["summary"], lang)),
                    "words": len(lesson.get("vocab") or []),
                    "exercises": len(lesson.get("exercises") or []),
                    "progress": item,
                    "completed": finished,
                }
            )
        level_total = len(level["lessons"]) or 1
        levels.append(
            {
                "slug": level["slug"],
                "short": level["short"],
                "title": from_packed(level, "title", lang, level_field(slug, level["slug"], "title", level["title"], lang)),
                "subtitle": from_packed(level, "subtitle", lang, level_field(slug, level["slug"], "subtitle", level["subtitle"], lang)),
                "lessons": lessons,
                "done": level_done,
                "total": len(level["lessons"]),
                "percent": round(100 * level_done / level_total),
            }
        )
    percent = round(100 * done_lessons / total_lessons) if total_lessons else 0
    category = course["category"]
    return {
        "slug": course["slug"],
        "title": course_field(slug, "title", course["title"], lang),
        "short": course["short"],
        "subtitle": course_field(slug, "subtitle", course["subtitle"], lang),
        "category": t("category_medicine") if category == "medicine" else t("category_language"),
        "accent": course["accent"],
        "icon": course["icon"],
        "blurb": course_field(slug, "blurb", course["blurb"], lang),
        "counts": counts,
        "levels": levels,
        "done": done_lessons,
        "total": total_lessons,
        "percent": percent,
    }


def catalog_payload(progress, lang=None):
    return [course_payload(course, progress, lang) for course in BY_SLUG.values()]


def continue_lesson(progress, lang=None):
    for course in BY_SLUG.values():
        payload = course_payload(course, progress, lang)
        for level in payload["levels"]:
            for lesson in level["lessons"]:
                if not lesson["completed"]:
                    return {
                        "course_slug": payload["slug"],
                        "course_title": payload["title"],
                        "level_slug": level["slug"],
                        "level_short": level["short"],
                        "lesson_slug": lesson["slug"],
                        "lesson_title": lesson["title"],
                        "accent": payload["accent"],
                    }
    return None


def _p(text):
    return f"<p>{escape(text)}</p>"


def render_sections(sections):
    blocks = []
    for section in sections or []:
        kind = section.get("type")
        if kind == "h2":
            blocks.append(f"<h2>{escape(section.get('text', ''))}</h2>")
        elif kind == "h3":
            blocks.append(f"<h3>{escape(section.get('text', ''))}</h3>")
        elif kind == "p":
            blocks.append(_p(section.get("text", "")))
        elif kind == "note":
            blocks.append(f'<aside class="lesson-note">{escape(section.get("text", ""))}</aside>')
        elif kind == "pattern":
            blocks.append(f'<p class="lesson-pattern">{escape(section.get("text", ""))}</p>')
        elif kind == "ul":
            items = "".join(f"<li>{escape(item)}</li>" for item in section.get("items") or [])
            blocks.append(f"<ul>{items}</ul>")
        elif kind == "ol":
            items = "".join(f"<li>{escape(item)}</li>" for item in section.get("items") or [])
            blocks.append(f"<ol>{items}</ol>")
        elif kind == "example":
            text = escape(
                section.get("text")
                or section.get("en")
                or section.get("de")
                or section.get("ko")
                or ""
            )
            ru = escape(section.get("ru", ""))
            lang_attr = escape(section.get("lang") or ("ko" if section.get("ko") else "en"))
            blocks.append(
                f'<figure class="lesson-example"><blockquote lang="{lang_attr}">{text}</blockquote>'
                f'<figcaption>{ru}</figcaption></figure>'
            )
        elif kind == "dialogue":
            rows = []
            lang_attr = escape(section.get("lang") or "en")
            for line in section.get("lines") or []:
                speaker = escape(line.get("speaker") or "")
                text = escape(line.get("text") or "")
                rows.append(f"<p><strong>{speaker}:</strong> {text}</p>")
            caption = escape(section.get("ru") or "")
            cap = f"<figcaption>{caption}</figcaption>" if caption else ""
            blocks.append(
                f'<figure class="lesson-example" lang="{lang_attr}">{"".join(rows)}{cap}</figure>'
            )
        elif kind == "table":
            headers = section.get("headers") or []
            head = "".join(f"<th>{escape(cell)}</th>" for cell in headers)
            body = []
            for row in section.get("rows") or []:
                cells = "".join(f"<td>{escape(cell)}</td>" for cell in row)
                body.append(f"<tr>{cells}</tr>")
            blocks.append(f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>')
        else:
            blocks.append(_p(section.get("text", "")))
    return Markup("\n".join(blocks))
