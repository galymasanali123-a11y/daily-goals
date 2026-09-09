"""Anki-style spaced repetition (SM-2 with learning/relearn steps).

Review buttons: 1=Again, 2=Hard, 3=Good, 4=Easy.
New/learning cards use minute steps (default 1m then 10m) instead of jumping a full day.
"""

from __future__ import annotations

import datetime
from copy import deepcopy

QUEUE_NEW = 0
QUEUE_LEARNING = 1
QUEUE_REVIEW = 2
QUEUE_RELEARN = 3

LEARN_STEPS_MIN = (1, 10)
RELEARN_STEPS_MIN = (10,)
GRADUATING_DAYS = 1
EASY_INTERVAL_DAYS = 4
STARTING_EASE = 2.5
MIN_EASE = 1.3
MAX_EASE = 2.8
EASY_BONUS = 1.3
HARD_FACTOR = 1.2
DEFAULT_NEW_PER_DAY = 20
DEFAULT_REVIEWS_PER_DAY = 200
DEFAULT_NOTIFY_HOUR = 9

NEW_SENTINEL = "0000-00-00"


def now_local():
    return datetime.datetime.now().replace(microsecond=0)


def today_str(now=None):
    return (now or now_local()).date().isoformat()


def parse_due_at(value):
    if not value or value == NEW_SENTINEL:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.datetime.strptime(text[:26], fmt if "f" not in fmt else "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
    try:
        return datetime.datetime.strptime(text[:10], "%Y-%m-%d")
    except ValueError:
        return None


def format_due_at(dt):
    if dt is None:
        return ""
    return dt.replace(microsecond=0).isoformat(timespec="seconds")


def infer_queue(card):
    try:
        queue = int(card.get("queue"))
    except (TypeError, ValueError):
        queue = None
    if queue in (QUEUE_LEARNING, QUEUE_REVIEW, QUEUE_RELEARN):
        return queue
    due = card.get("due") or ""
    reps = int(card.get("reps") or 0)
    due_at = card.get("due_at") or ""
    if (not due or due == NEW_SENTINEL) and not due_at:
        return QUEUE_NEW
    if reps <= 0 and queue == QUEUE_NEW:
        return QUEUE_NEW
    return QUEUE_REVIEW


def normalize_card_state(card):
    state = {
        "ease": float(card.get("ease") or STARTING_EASE),
        "reps": int(card.get("reps") or 0),
        "interval": int(card.get("interval") or 0),
        "lapses": int(card.get("lapses") or 0),
        "queue": infer_queue(card),
        "learn_step": int(card.get("learn_step") or 0),
        "due": card.get("due") or NEW_SENTINEL,
        "due_at": card.get("due_at") or "",
    }
    if state["queue"] == QUEUE_NEW and not state["due_at"]:
        state["due_at"] = ""
        state["due"] = NEW_SENTINEL
    return state


def _steps_for(queue):
    return RELEARN_STEPS_MIN if queue == QUEUE_RELEARN else LEARN_STEPS_MIN


def format_interval_label(minutes=None, days=None):
    if days is not None:
        if days < 1:
            minutes = max(1, round(days * 1440))
        else:
            if days >= 30 and days % 30 == 0:
                months = days // 30
                return f"{months}mo"
            return f"{days}d"
    minutes = max(1, int(minutes or 1))
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes / 60
    if hours < 24:
        return f"{int(round(hours))}h" if hours >= 1.5 else f"{minutes}m"
    return f"{max(1, int(round(hours / 24)))}d"


def _set_learning(state, queue, step_index, now):
    steps = _steps_for(queue)
    step_index = max(0, min(step_index, len(steps) - 1))
    minutes = steps[step_index]
    due_at = now + datetime.timedelta(minutes=minutes)
    state["queue"] = queue
    state["learn_step"] = step_index
    state["due_at"] = format_due_at(due_at)
    state["due"] = due_at.date().isoformat()
    state["interval"] = 0
    return {"kind": "learn", "minutes": minutes, "label": format_interval_label(minutes=minutes)}


def _graduate(state, days, now, ease=None):
    days = max(1, int(days))
    due_at = now + datetime.timedelta(days=days)
    state["queue"] = QUEUE_REVIEW
    state["learn_step"] = 0
    state["reps"] = max(1, state.get("reps") or 0)
    state["interval"] = days
    state["ease"] = round(float(ease if ease is not None else state.get("ease") or STARTING_EASE), 2)
    state["due_at"] = format_due_at(due_at.replace(hour=now.hour, minute=now.minute, second=now.second))
    state["due"] = due_at.date().isoformat()
    return {"kind": "review", "days": days, "label": format_interval_label(days=days)}


def _review_interval(state, factor):
    base = max(1, int(state.get("interval") or 1))
    return max(1, round(base * factor))


def preview_review(card, confidence, now=None):
    """Return the interval label a button would apply, without mutating storage."""
    result = apply_review_result(card, confidence, now=now, mutate=False)
    return result["preview"]


def apply_review_result(card, confidence, now=None, mutate=True):
    confidence = max(1, min(4, int(confidence)))
    now = now or now_local()
    state = normalize_card_state(card if mutate else deepcopy(card))
    queue = state["queue"]
    preview = {"kind": "learn", "minutes": 1, "label": "1m"}

    if queue in (QUEUE_NEW, QUEUE_LEARNING):
        steps = LEARN_STEPS_MIN
        step = 0 if queue == QUEUE_NEW else state["learn_step"]
        if confidence == 1:
            preview = _set_learning(state, QUEUE_LEARNING, 0, now)
            state["reps"] = 0
        elif confidence == 2:
            current = steps[min(step, len(steps) - 1)]
            nxt = steps[min(step + 1, len(steps) - 1)]
            minutes = max(1, round((current + nxt) / 2))
            due_at = now + datetime.timedelta(minutes=minutes)
            state["queue"] = QUEUE_LEARNING
            state["learn_step"] = step
            state["due_at"] = format_due_at(due_at)
            state["due"] = due_at.date().isoformat()
            preview = {"kind": "learn", "minutes": minutes, "label": format_interval_label(minutes=minutes)}
        elif confidence == 3:
            if queue == QUEUE_NEW:
                preview = _set_learning(state, QUEUE_LEARNING, 0, now)
            elif step + 1 < len(steps):
                preview = _set_learning(state, QUEUE_LEARNING, step + 1, now)
            else:
                state["reps"] = max(state["reps"], 1)
                preview = _graduate(state, GRADUATING_DAYS, now, ease=state["ease"] or STARTING_EASE)
        else:
            state["reps"] = max(state["reps"], 1)
            preview = _graduate(state, EASY_INTERVAL_DAYS, now, ease=min(MAX_EASE, (state["ease"] or STARTING_EASE) + 0.15))

    elif queue == QUEUE_RELEARN:
        steps = RELEARN_STEPS_MIN
        step = state["learn_step"]
        if confidence == 1:
            preview = _set_learning(state, QUEUE_RELEARN, 0, now)
        elif confidence == 2:
            minutes = steps[min(step, len(steps) - 1)]
            due_at = now + datetime.timedelta(minutes=minutes)
            state["due_at"] = format_due_at(due_at)
            state["due"] = due_at.date().isoformat()
            preview = {"kind": "learn", "minutes": minutes, "label": format_interval_label(minutes=minutes)}
        elif confidence == 3:
            if step + 1 < len(steps):
                preview = _set_learning(state, QUEUE_RELEARN, step + 1, now)
            else:
                days = max(1, int(state.get("interval") or GRADUATING_DAYS))
                preview = _graduate(state, days, now)
        else:
            days = max(GRADUATING_DAYS, int(state.get("interval") or GRADUATING_DAYS))
            preview = _graduate(state, days, now)

    else:  # review
        ease = max(MIN_EASE, float(state.get("ease") or STARTING_EASE))
        interval = max(1, int(state.get("interval") or 1))
        if confidence == 1:
            state["lapses"] = int(state.get("lapses") or 0) + 1
            state["ease"] = round(max(MIN_EASE, ease - 0.2), 2)
            state["interval"] = GRADUATING_DAYS
            state["reps"] = 0
            preview = _set_learning(state, QUEUE_RELEARN, 0, now)
        elif confidence == 2:
            days = max(1, round(interval * HARD_FACTOR))
            state["ease"] = round(max(MIN_EASE, ease - 0.15), 2)
            state["reps"] = int(state.get("reps") or 0) + 1
            preview = _graduate(state, days, now, ease=state["ease"])
        elif confidence == 3:
            days = max(interval + 1, round(interval * ease))
            state["reps"] = int(state.get("reps") or 0) + 1
            preview = _graduate(state, days, now, ease=min(MAX_EASE, ease))
        else:
            days = max(interval + 1, round(interval * ease * EASY_BONUS))
            new_ease = round(min(2.8, ease + 0.15), 2)
            state["reps"] = int(state.get("reps") or 0) + 1
            preview = _graduate(state, days, now, ease=new_ease)

    state["preview"] = preview
    return state


def button_previews(card, now=None):
    now = now or now_local()
    labels = {}
    for confidence in (1, 2, 3, 4):
        labels[str(confidence)] = apply_review_result(card, confidence, now=now, mutate=False)["preview"]["label"]
    return labels


def is_new_card(card):
    return infer_queue(card) == QUEUE_NEW


def is_learning_card(card):
    return infer_queue(card) in (QUEUE_LEARNING, QUEUE_RELEARN)


def is_due(card, now=None):
    now = now or now_local()
    queue = infer_queue(card)
    if queue == QUEUE_NEW:
        return False
    due_at = parse_due_at(card.get("due_at") or card.get("due"))
    if due_at is None:
        return queue != QUEUE_NEW
    return due_at <= now


def default_settings():
    return {
        "new_per_day": DEFAULT_NEW_PER_DAY,
        "reviews_per_day": DEFAULT_REVIEWS_PER_DAY,
        "notify_enabled": 1,
        "notify_hour": DEFAULT_NOTIFY_HOUR,
    }


def clamp_settings(payload):
    current = default_settings()
    if not payload:
        return current
    try:
        current["new_per_day"] = max(0, min(200, int(payload.get("new_per_day", current["new_per_day"]))))
    except (TypeError, ValueError):
        pass
    try:
        current["reviews_per_day"] = max(0, min(9999, int(payload.get("reviews_per_day", current["reviews_per_day"]))))
    except (TypeError, ValueError):
        pass
    current["notify_enabled"] = 1 if str(payload.get("notify_enabled", current["notify_enabled"])) not in {"0", "false", "False"} else 0
    try:
        current["notify_hour"] = max(0, min(23, int(payload.get("notify_hour", current["notify_hour"]))))
    except (TypeError, ValueError):
        pass
    return current


def select_study_queue(cards, settings, intro_ids, new_shown, reviews_shown, now=None):
    """Pick today's Anki queue: due learning first, then reviews, then new cards.

    Learning/relearn cards always enter once they are due (Anki does not cap them).
    New and review counts follow the user's daily limits.
    """
    now = now or now_local()
    today = today_str(now)
    settings = {**default_settings(), **(settings or {})}
    intro_ids = set(intro_ids or [])

    learning_due, learning_waiting, reviews, new_cards = [], [], [], []
    for card in cards:
        queue = infer_queue(card)
        if queue == QUEUE_NEW:
            new_cards.append(card)
            continue
        due_at = parse_due_at(card.get("due_at") or card.get("due"))
        if queue in (QUEUE_LEARNING, QUEUE_RELEARN):
            if due_at is None or due_at <= now:
                learning_due.append(card)
            else:
                learning_waiting.append(card)
            continue
        due_date = (due_at.date().isoformat() if due_at else (card.get("due") or ""))
        if due_date and due_date != NEW_SENTINEL and due_date <= today:
            reviews.append(card)

    still_introduced = [c for c in new_cards if c.get("external_id") in intro_ids]
    fresh = [c for c in new_cards if c.get("external_id") not in intro_ids]
    new_limit = int(settings.get("new_per_day") or 0)
    review_limit = int(settings.get("reviews_per_day") or 0)

    remaining_new = max(0, new_limit - max(new_shown, len(still_introduced)))
    newly = fresh[:remaining_new]
    remaining_reviews = max(0, review_limit - reviews_shown)
    review_due = reviews[:remaining_reviews]

    selected = learning_due + review_due + still_introduced + newly
    selected_ids = {c["external_id"] for c in selected}
    updated_intro = intro_ids | {c["external_id"] for c in still_introduced + newly}
    waiting_at = []
    for card in learning_waiting:
        due_at = parse_due_at(card.get("due_at"))
        if due_at:
            waiting_at.append(format_due_at(due_at))

    counts = {
        "new": len(still_introduced) + len(newly),
        "learning": len(learning_due),
        "review": len(review_due),
        "waiting": len(learning_waiting),
        "new_remaining": remaining_new,
        "review_remaining": remaining_reviews,
    }
    return selected_ids, sorted(updated_intro), waiting_at, counts
