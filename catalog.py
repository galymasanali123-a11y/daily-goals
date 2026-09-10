"""In-app catalogs: bundled flashcard decks and short readers.

Decks are copied into the caller's synced_cards (skipping ids they already have).
Books are copied into synced_books from files in shared_books/.
"""

from __future__ import annotations

import json
from pathlib import Path

from curriculum import BY_SLUG, card_external_id
from db import query_all, query_one
from i18n import current_lang, t
import srs

ROOT = Path(__file__).parent
SHARED_DECKS_DIR = ROOT / "shared_decks"
SHARED_BOOKS_DIR = ROOT / "shared_books"

CARD_INSERT = (
    "INSERT INTO synced_cards (user_id, external_id, topic, question, answer, options_json, "
    "example, notes, due, interval, ease, reps, lapses, queue, due_at, learn_step, source) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 0, 0, 0, '', 0, ?) "
    "ON CONFLICT(user_id, external_id) DO NOTHING"
)

_COURSE_LANG = {
    "english": "en",
    "german": "de",
    "korean": "ko",
    "medicine": "en",
}


def _auto_decks():
    items = []
    for course in BY_SLUG.values():
        for course_level in course["levels"]:
            subtitle_i18n = course_level.get("subtitle_i18n") or {}
            title_i18n = course_level.get("title_i18n") or {}
            items.append(
                {
                    "id": f"{course['slug']}-{course_level['slug']}",
                    "kind": "course",
                    "course": course["slug"],
                    "levels": [course_level["slug"]],
                    "lang": _COURSE_LANG.get(course["slug"], "en"),
                    "level": course_level["short"],
                    "accent": course["accent"],
                    "title": {
                        "en": title_i18n.get("en") or f"{course['title']} {course_level['short']}",
                        "ru": title_i18n.get("ru") or f"{course['title']} {course_level['short']}",
                    },
                    "blurb": {
                        "en": subtitle_i18n.get("en") or course_level.get("subtitle") or "",
                        "ru": subtitle_i18n.get("ru") or course_level.get("subtitle") or "",
                    },
                }
            )
    return items


DECKS = _auto_decks() + [
    {
        "id": "goethe-a1",
        "kind": "file",
        "filename": "goethe-a1.json",
        "lang": "de",
        "level": "A1",
        "accent": "#c2410c",
        "title": {"en": "Goethe A1 wordlist", "ru": "Goethe A1 — словарь"},
        "blurb": {
            "en": "Official-style A1 vocabulary with examples. Starts a fresh review cycle.",
            "ru": "Словарь уровня A1 с примерами. Свой цикл повторений с нуля.",
        },
    },
]

BOOKS = [
    {
        "id": "english-a1-reader",
        "filename": "english-a1-reader.md",
        "content_type": "text/markdown",
        "lang": "en",
        "accent": "#0d9488",
        "title": {"en": "English A1 reader", "ru": "Читалка English A1"},
        "blurb": {
            "en": "Short dialogues for beginners. Highlight as you read.",
            "ru": "Короткие диалоги для начинающих. Можно красить маркером.",
        },
    },
    {
        "id": "english-b1-reader",
        "filename": "english-b1-reader.md",
        "content_type": "text/markdown",
        "lang": "en",
        "accent": "#0f766e",
        "title": {"en": "English B1 graded reader", "ru": "Читалка English B1"},
        "blurb": {
            "en": "Work, health, the city, disagreement — plus Aesop. Built for B1 speaking.",
            "ru": "Работа, здоровье, город, спор — плюс Эзоп. Для устной речи B1.",
        },
    },
    {
        "id": "english-b2-holmes",
        "filename": "english-b2-holmes.md",
        "content_type": "text/markdown",
        "lang": "en",
        "accent": "#115e59",
        "title": {"en": "A Scandal in Bohemia (study)", "ru": "Скандал в Богемии — разбор"},
        "blurb": {
            "en": "Public-domain Sherlock Holmes with B2 grammar, vocab, and speaking tasks.",
            "ru": "Шерлок Холмс из общественного достояния: грамматика B2, слова и задания на речь.",
        },
    },
    {
        "id": "german-a1-reader",
        "filename": "german-a1-reader.md",
        "content_type": "text/markdown",
        "lang": "de",
        "accent": "#ea580c",
        "title": {"en": "Deutsch A1 Lesebuch", "ru": "Читалка Deutsch A1"},
        "blurb": {
            "en": "Very simple German texts: café, city, family, doctor.",
            "ru": "Очень простые немецкие тексты: кафе, город, семья, врач.",
        },
    },
    {
        "id": "german-grimm-rotkaeppchen",
        "filename": "german-grimm-rotkaeppchen.md",
        "content_type": "text/markdown",
        "lang": "de",
        "accent": "#c2410c",
        "title": {"en": "Rotkäppchen (Grimm 1857)", "ru": "Красная Шапочка (Гримм, 1857)"},
        "blurb": {
            "en": "Public-domain Märchen with glossary, Präteritum notes, and a modern rewrite.",
            "ru": "Сказка из общественного достояния: словарь, Präteritum и современный пересказ.",
        },
    },
    {
        "id": "german-reading-companion",
        "filename": "german-reading-companion.md",
        "content_type": "text/markdown",
        "lang": "de",
        "accent": "#9a3412",
        "title": {"en": "Reading German companion", "ru": "Спутник чтения по-немецки"},
        "blurb": {
            "en": "Original companion to the UW-Madison open textbook (Martin & Ng, CC BY-NC-SA).",
            "ru": "Оригинальный спутник открытого учебника UW-Madison (Martin & Ng, CC BY-NC-SA).",
        },
    },
    {
        "id": "korean-hangul-reader",
        "filename": "korean-hangul-reader.md",
        "content_type": "text/markdown",
        "lang": "ko",
        "accent": "#2563eb",
        "title": {"en": "Hangul primer and dialogues", "ru": "Хангыль и диалоги"},
        "blurb": {
            "en": "Syllable blocks plus store, subway, clinic, and work dialogues A1–B2.",
            "ru": "Слоговые блоки и диалоги: магазин, метро, клиника, работа — A1–B2.",
        },
    },
    {
        "id": "korean-b2-reader",
        "filename": "korean-b2-reader.md",
        "content_type": "text/markdown",
        "lang": "ko",
        "accent": "#1d4ed8",
        "title": {"en": "Korean B2 reader", "ru": "Читалка Korean B2"},
        "blurb": {
            "en": "News-style text, workplace email, clinic talk, and an opinion essay.",
            "ru": "Новостной абзац, рабочее письмо, клиника и эссе-мнение.",
        },
    },
    {
        "id": "medicine-basics",
        "filename": "medicine-basics.md",
        "content_type": "text/markdown",
        "lang": "en",
        "accent": "#7c3aed",
        "title": {"en": "Medicine: first terms", "ru": "Медицина: первые термины"},
        "blurb": {
            "en": "A short plain-language intro to body systems and clinic words.",
            "ru": "Короткое введение простыми словами: системы тела и клиника.",
        },
    },
    {
        "id": "openstax-anatomy-companion",
        "filename": "openstax-anatomy-companion.md",
        "content_type": "text/markdown",
        "lang": "en",
        "accent": "#6d28d9",
        "title": {"en": "OpenStax A&P companion", "ru": "Спутник OpenStax A&P"},
        "blurb": {
            "en": "Original study map of OpenStax Anatomy and Physiology 2e (CC BY-NC-SA).",
            "ru": "Оригинальная карта OpenStax Anatomy and Physiology 2e (CC BY-NC-SA).",
        },
    },
    {
        "id": "grays-anatomy-heart",
        "filename": "grays-anatomy-heart.md",
        "content_type": "text/markdown",
        "lang": "en",
        "accent": "#5b21b6",
        "title": {"en": "Gray’s Anatomy: the heart (1918)", "ru": "Gray’s Anatomy: сердце (1918)"},
        "blurb": {
            "en": "Public-domain heart chapter with modern clinical English beside it.",
            "ru": "Глава о сердце из общественного достояния и рядом — современный клинический английский.",
        },
    },
    {
        "id": "openstax-microbiology-companion",
        "filename": "openstax-microbiology-companion.md",
        "content_type": "text/markdown",
        "lang": "en",
        "accent": "#7e22ce",
        "title": {"en": "OpenStax Microbiology companion", "ru": "Спутник OpenStax Microbiology"},
        "blurb": {
            "en": "Original companion to OpenStax Microbiology 2e — infection language, not treatment.",
            "ru": "Оригинальный спутник OpenStax Microbiology 2e — язык инфекции, не лечение.",
        },
    },
    {
        "id": "study-routine",
        "filename": "study-routine.md",
        "content_type": "text/markdown",
        "lang": "en",
        "accent": "#0f2438",
        "title": {"en": "How to study a little every day", "ru": "Как заниматься понемногу каждый день"},
        "blurb": {
            "en": "A one-page routine: cards, a lesson, a page of reading.",
            "ru": "Одна страница: карточки, урок, страница чтения.",
        },
    },
]

_DECK_BY_ID = {item["id"]: item for item in DECKS}
_BOOK_BY_ID = {item["id"]: item for item in BOOKS}
_goethe_cache = None


def _pick(item, lang=None):
    lang = lang or current_lang()
    title = item["title"]
    blurb = item["blurb"]
    return title.get(lang) or title["en"], blurb.get(lang) or blurb["en"]


def _course_cards(spec):
    course = BY_SLUG.get(spec["course"])
    if not course:
        return []
    wanted = spec.get("levels")
    cards = []
    for level in course["levels"]:
        if wanted and level["slug"] not in wanted:
            continue
        topic = f"{course['title']} · {level['short']}"
        for lesson in level["lessons"]:
            for word in lesson.get("vocab") or []:
                cards.append(
                    {
                        "external_id": card_external_id(
                            course["slug"], level["slug"], lesson["slug"], word["id"]
                        ),
                        "topic": topic,
                        "question": word["front"],
                        "answer": word["back"],
                        "example": word.get("example") or "",
                        "notes": "",
                        "options": [],
                    }
                )
    return cards


def _goethe_cards():
    global _goethe_cache
    if _goethe_cache is None:
        path = SHARED_DECKS_DIR / "goethe-a1.json"
        _goethe_cache = json.loads(path.read_text(encoding="utf-8"))
        for card in _goethe_cache:
            card["topic"] = "Goethe A1"
    return _goethe_cache


def deck_cards(deck_id):
    spec = _DECK_BY_ID.get(deck_id)
    if not spec:
        return None
    if spec["kind"] == "file":
        return _goethe_cards()
    return _course_cards(spec)


def deck_prefix(spec):
    if spec["kind"] == "file":
        return None
    course = spec["course"]
    levels = spec.get("levels")
    if not levels:
        return f"course:{course}:"
    if len(levels) == 1:
        return f"course:{course}:{levels[0]}:"
    return f"course:{course}:"


def _count_owned(db, user_id, spec):
    source = f"catalog:{spec['id']}"
    if spec["kind"] == "file":
        row = query_one(
            db,
            "SELECT COUNT(*) AS n FROM synced_cards WHERE user_id = ? AND (source = ? OR source = 'shared')",
            (user_id, source),
        )
        return int(row["n"] if row else 0)
    prefix = deck_prefix(spec)
    row = query_one(
        db,
        "SELECT COUNT(*) AS n FROM synced_cards WHERE user_id = ? AND external_id LIKE ?",
        (user_id, prefix + "%"),
    )
    return int(row["n"] if row else 0)


def decks_payload(db, user_id, lang=None):
    lang = lang or current_lang()
    items = []
    for spec in DECKS:
        cards = deck_cards(spec["id"]) or []
        total = len(cards)
        owned = min(_count_owned(db, user_id, spec), total)
        title, blurb = _pick(spec, lang)
        items.append(
            {
                "id": spec["id"],
                "title": title,
                "blurb": blurb,
                "lang": spec["lang"],
                "level": spec["level"],
                "accent": spec["accent"],
                "card_count": total,
                "owned": owned,
                "downloaded": owned >= total and total > 0,
            }
        )
    return items


def add_cards_skip_existing(db, user_id, cards, source):
    existing = {
        row["external_id"]
        for row in query_all(db, "SELECT external_id FROM synced_cards WHERE user_id = ?", (user_id,))
    }
    added = 0
    for card in cards:
        external_id = str(card.get("external_id") or "").strip()
        question = str(card.get("question") or "").strip()
        topic = str(card.get("topic") or "").strip() or "Cards"
        if not external_id or not question or external_id in existing:
            continue
        db.execute(
            CARD_INSERT,
            (
                user_id,
                external_id,
                topic,
                question,
                str(card.get("answer") or ""),
                json.dumps(card.get("options") or []),
                str(card.get("example") or ""),
                str(card.get("notes") or ""),
                srs.NEW_SENTINEL,
                srs.STARTING_EASE,
                source,
            ),
        )
        existing.add(external_id)
        added += 1
    return added


def download_deck(db, user_id, deck_id):
    spec = _DECK_BY_ID.get(deck_id)
    cards = deck_cards(deck_id)
    if not spec or cards is None:
        return None
    before = _count_owned(db, user_id, spec)
    add_cards_skip_existing(db, user_id, cards, f"catalog:{deck_id}")
    after = _count_owned(db, user_id, spec)
    return {"added": max(0, after - before), "card_count": len(cards), "label": _pick(spec)[0]}


def delete_deck(db, user_id, deck_id):
    spec = _DECK_BY_ID.get(deck_id)
    if not spec:
        return None
    source = f"catalog:{deck_id}"
    if spec["kind"] == "file":
        db.execute(
            "DELETE FROM synced_cards WHERE user_id = ? AND (source = ? OR source = 'shared')",
            (user_id, source),
        )
    else:
        prefix = deck_prefix(spec)
        db.execute(
            "DELETE FROM synced_cards WHERE user_id = ? AND (source = ? OR external_id LIKE ?)",
            (user_id, source, prefix + "%"),
        )
    return {"ok": True}


def book_bytes(spec):
    path = SHARED_BOOKS_DIR / spec["filename"]
    return path.read_bytes()


def books_payload(db, user_id, lang=None):
    lang = lang or current_lang()
    rows = query_all(
        db,
        "SELECT external_id FROM synced_books WHERE user_id = ?",
        (user_id,),
    )
    owned = {row["external_id"] for row in rows}
    items = []
    for spec in BOOKS:
        external_id = f"catalog:book:{spec['id']}"
        raw = book_bytes(spec)
        title, blurb = _pick(spec, lang)
        items.append(
            {
                "id": spec["id"],
                "title": title,
                "blurb": blurb,
                "lang": spec["lang"],
                "accent": spec["accent"],
                "size_bytes": len(raw),
                "size": _format_size(len(raw)),
                "downloaded": external_id in owned,
            }
        )
    return items


def download_book(db, user_id, book_id):
    spec = _BOOK_BY_ID.get(book_id)
    if not spec:
        return None
    external_id = f"catalog:book:{book_id}"
    existing = query_one(
        db,
        "SELECT id FROM synced_books WHERE user_id = ? AND external_id = ?",
        (user_id, external_id),
    )
    if existing:
        return {"id": existing["id"], "added": 0, "title": _pick(spec)[0]}
    raw = book_bytes(spec)
    inserted = query_one(
        db,
        "INSERT INTO synced_books (user_id, external_id, title, filename, content_type, size_bytes, content, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'catalog') RETURNING id",
        (
            user_id,
            external_id,
            _pick(spec)[0],
            spec["filename"],
            spec["content_type"],
            len(raw),
            raw,
        ),
    )
    return {"id": inserted["id"], "added": 1, "title": _pick(spec)[0]}


def _format_size(size_bytes):
    if size_bytes < 1024:
        return t("size_bytes", n=size_bytes)
    if size_bytes < 1024 * 1024:
        return t("size_kb", n=round(size_bytes / 1024))
    return t("size_mb", n=round(size_bytes / (1024 * 1024), 1))
