"""Built-in courses: languages and medicine. Explanations are in Russian so the structure stays clear."""

from curriculum_english import COURSE as ENGLISH
from curriculum_german import COURSE as GERMAN
from curriculum_medicine import COURSE as MEDICINE

COURSES = [ENGLISH, GERMAN, MEDICINE]
BY_SLUG = {course["slug"]: course for course in COURSES}


def get_course(slug):
    return BY_SLUG.get(slug)


def get_level(course, level_slug):
    if not course:
        return None
    for level in course["levels"]:
        if level["slug"] == level_slug:
            return level
    return None


def get_lesson(course, level_slug, lesson_slug):
    level = get_level(course, level_slug)
    if not level:
        return None
    for lesson in level["lessons"]:
        if lesson["slug"] == lesson_slug:
            return lesson
    return None


def course_counts(course):
    lessons = [lesson for level in course["levels"] for lesson in level["lessons"]]
    return {
        "levels": len(course["levels"]),
        "lessons": len(lessons),
        "words": sum(len(lesson.get("vocab") or []) for lesson in lessons),
        "exercises": sum(len(lesson.get("exercises") or []) for lesson in lessons),
    }


def card_external_id(course_slug, level_slug, lesson_slug, word_id):
    return f"course:{course_slug}:{level_slug}:{lesson_slug}:{word_id}"


def lesson_topic(course, level, lesson):
    return f"{course['title']} / {level['short']} / {lesson['title']}"
