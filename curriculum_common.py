"""Shared lesson builders. Titles/summaries may be a string (Russian) or {en, ru}."""


def ex(kind, prompt, answer, options=None, explanation=""):
    item = {"type": kind, "prompt": prompt, "answer": answer, "explanation": explanation}
    if options:
        item["options"] = options
    return item


def word(wid, front, back, example=""):
    return {"id": wid, "front": front, "back": back, "example": example}


def _i18n(value):
    if isinstance(value, dict):
        ru = value.get("ru") or value.get("en") or ""
        en = value.get("en") or ru
        return ru, {"en": en, "ru": ru}
    return value, {"en": value, "ru": value}


def lesson(slug, title, minutes, summary, sections, vocab, exercises):
    title_ru, title_i18n = _i18n(title)
    summary_ru, summary_i18n = _i18n(summary)
    return {
        "slug": slug,
        "title": title_ru,
        "title_i18n": title_i18n,
        "minutes": minutes,
        "summary": summary_ru,
        "summary_i18n": summary_i18n,
        "sections": sections,
        "vocab": vocab,
        "exercises": exercises,
    }


def level(slug, short, title, subtitle, lessons):
    title_ru, title_i18n = _i18n(title)
    subtitle_ru, subtitle_i18n = _i18n(subtitle)
    return {
        "slug": slug,
        "short": short,
        "title": title_ru,
        "title_i18n": title_i18n,
        "subtitle": subtitle_ru,
        "subtitle_i18n": subtitle_i18n,
        "lessons": lessons,
    }
