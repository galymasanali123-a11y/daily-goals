"""English/Russian copy for course catalog metadata (titles, blurbs, summaries)."""

from i18n import current_lang

COURSE_META = {
    "english": {
        "title": {"en": "English", "ru": "Английский"},
        "subtitle": {
            "en": "Grammar, words, and exercises — from A1 to B1",
            "ru": "Грамматика, слова и задания — от A1 до B1",
        },
        "blurb": {
            "en": "Tap the block, pick a level, and go through the lessons in order. Each lesson has a plain-language rule, a table, examples, cards, and a check.",
            "ru": "Нажмите на блок, выберите уровень и проходите уроки по порядку. В каждом уроке — правило простыми словами, таблица, примеры, карточки и проверка.",
        },
        "levels": {
            "a1": {
                "title": {"en": "A1 · Start", "ru": "A1 · Начало"},
                "subtitle": {
                    "en": "Simple sentences, to be, articles, Present Simple",
                    "ru": "Простые предложения, to be, артикли, Present Simple",
                },
            },
            "a2": {
                "title": {"en": "A2 · Foundation", "ru": "A2 · База"},
                "subtitle": {
                    "en": "The past, right now, comparison, plans, and modal verbs",
                    "ru": "Прошедшее, «прямо сейчас», сравнение, планы и модальные глаголы",
                },
            },
            "b1": {
                "title": {"en": "B1 · Confidence", "ru": "B1 · Уверенность"},
                "subtitle": {
                    "en": "Present Perfect, conditionals, the passive, and relative clauses",
                    "ru": "Present Perfect, условия, пассив и относительные предложения",
                },
            },
        },
        "lessons": {
            "greetings": {
                "title": {"en": "Greetings and the alphabet", "ru": "Приветствие и алфавит"},
                "summary": {
                    "en": "How to say hello, introduce yourself, and read English letters.",
                    "ru": "Как поздороваться, представиться и прочитать английские буквы.",
                },
            },
            "to-be": {
                "title": {"en": "The verb to be (am / is / are)", "ru": "Глагол to be (am / is / are)"},
                "summary": {
                    "en": "The most useful verb: who you are, where you are, what you are like.",
                    "ru": "Самый нужный глагол: кто вы, где вы, какой вы.",
                },
            },
            "articles": {
                "title": {"en": "Articles a / an / the", "ru": "Артикли a / an / the"},
                "summary": {
                    "en": "When to say “some kind of” and when to say “that one”.",
                    "ru": "Когда говорить «какой-то» и когда «тот самый».",
                },
            },
            "pronouns": {
                "title": {"en": "Pronouns and possessives", "ru": "Местоимения и притяжательные"},
                "summary": {
                    "en": "I, you, my, your — who is speaking and whose thing it is.",
                    "ru": "I, you, my, your — кто говорит и чья это вещь.",
                },
            },
            "present-simple": {
                "title": {"en": "Present Simple", "ru": "Present Simple"},
                "summary": {
                    "en": "Facts, habits, timetables. The -s ending with he/she/it.",
                    "ru": "Факты, привычки, расписание. Окончание -s у he/she/it.",
                },
            },
            "there-is": {
                "title": {"en": "There is / there are", "ru": "There is / there are"},
                "summary": {
                    "en": "How to say that something is in a place.",
                    "ru": "Как сказать «есть / находится» про вещи в месте.",
                },
            },
            "questions": {
                "title": {"en": "Questions: yes/no and Wh-", "ru": "Вопросы: yes/no и Wh-"},
                "summary": {
                    "en": "Do, does, is, and what, where, who, when, why, how.",
                    "ru": "Do, does, is и слова what, where, who, when, why, how.",
                },
            },
            "everyday-words": {
                "title": {"en": "Everyday words", "ru": "Слова на каждый день"},
                "summary": {
                    "en": "Family, home, food, and simple prepositions of place.",
                    "ru": "Семья, дом, еда и простые предлоги места.",
                },
            },
            "past-simple": {
                "title": {"en": "Past Simple", "ru": "Past Simple"},
                "summary": {
                    "en": "What happened yesterday: regular -ed and a short irregular list.",
                    "ru": "Что случилось вчера: правильные -ed и список неправильных.",
                },
            },
            "present-continuous": {
                "title": {"en": "Present Continuous", "ru": "Present Continuous"},
                "summary": {
                    "en": "An action right now, or a temporary situation.",
                    "ru": "Действие прямо сейчас или временная ситуация.",
                },
            },
            "comparatives": {
                "title": {"en": "Comparison: -er, more, the most", "ru": "Сравнение: -er, more, the most"},
                "summary": {
                    "en": "How to say taller, more interesting, and the most.",
                    "ru": "Как сказать «выше», «более интересный», «самый».",
                },
            },
            "modals": {
                "title": {"en": "Can, must, should", "ru": "Can, must, should"},
                "summary": {
                    "en": "Ability, duty, and advice — with no to after them.",
                    "ru": "Умение, обязанность и совет — без to после них.",
                },
            },
            "future": {
                "title": {"en": "The future: going to and will", "ru": "Будущее: going to и will"},
                "summary": {
                    "en": "A plan already exists — going to. A decision now or a promise — will.",
                    "ru": "План уже есть — going to. Решение сейчас или обещание — will.",
                },
            },
            "present-perfect": {
                "title": {"en": "Present Perfect", "ru": "Present Perfect"},
                "summary": {
                    "en": "Experience and a link to now: have/has + third form.",
                    "ru": "Опыт и связь с настоящим: have/has + 3-я форма.",
                },
            },
            "conditionals": {
                "title": {"en": "First conditional", "ru": "First conditional"},
                "summary": {
                    "en": "A real future: If + Present, will…",
                    "ru": "Реальное будущее: If + Present, will…",
                },
            },
            "passive": {
                "title": {"en": "Passive Voice", "ru": "Passive Voice"},
                "summary": {
                    "en": "When the object matters more than who did it: be + V3.",
                    "ru": "Когда важен объект, а не тот, кто сделал: be + V3.",
                },
            },
            "relative-clauses": {
                "title": {"en": "Who, which, that", "ru": "Who, which, that"},
                "summary": {
                    "en": "Clauses that say who or what you mean.",
                    "ru": "Придаточные, которые уточняют, о ком и о чём речь.",
                },
            },
        },
    },
    "german": {
        "title": {"en": "German", "ru": "Немецкий"},
        "subtitle": {
            "en": "A1: greetings, sein/haben, articles, and the present tense",
            "ru": "A1: приветствие, sein/haben, артикли и настоящее время",
        },
        "blurb": {
            "en": "German from zero: noun gender from the start, honest tables, and words you will actually use.",
            "ru": "Немецкий с нуля: род существительных сразу, честные таблицы и слова, которые пригодятся в быту.",
        },
        "levels": {
            "a1": {
                "title": {"en": "A1 · Start", "ru": "A1 · Начало"},
                "subtitle": {
                    "en": "First phrases, gender, and the verbs sein and haben",
                    "ru": "Первые фразы, род, глаголы sein и haben",
                },
            },
        },
        "lessons": {
            "hallo": {
                "title": {"en": "Hallo and the alphabet", "ru": "Hallo и алфавит"},
                "summary": {
                    "en": "Greetings, politeness, and how umlauts sound.",
                    "ru": "Приветствие, вежливость и как звучат умляуты.",
                },
            },
            "sein-haben": {
                "title": {"en": "sein and haben", "ru": "sein и haben"},
                "summary": {
                    "en": "Two verbs you cannot get through a simple text without.",
                    "ru": "Два глагола, без которых нет ни одного простого текста.",
                },
            },
            "articles": {
                "title": {"en": "der / die / das", "ru": "der / die / das"},
                "summary": {
                    "en": "Learn gender together with the word. Otherwise the cases fall apart later.",
                    "ru": "Род нужно учить вместе со словом. Иначе падежи потом развалятся.",
                },
            },
            "present-verbs": {
                "title": {"en": "Present tense: weak verbs", "ru": "Настоящее время: слабые глаголы"},
                "summary": {
                    "en": "The basic pattern: ich lerne, du lernst, er lernt.",
                    "ru": "Основы спряжения: ich lerne, du lernst, er lernt.",
                },
            },
        },
    },
    "medicine": {
        "title": {"en": "Medicine", "ru": "Медицина"},
        "subtitle": {
            "en": "Terms, organ systems, vital signs, and symptoms",
            "ru": "Термины, системы органов, витальные признаки и симптомы",
        },
        "blurb": {
            "en": "Not a therapy textbook — a clear frame: how a word is built, how the body is organized, what to measure, and how to name a complaint in English.",
            "ru": "Не учебник терапии, а ясный каркас: из чего состоит слово, как устроено тело, что измерять и как назвать жалобу по-английски.",
        },
        "levels": {
            "foundation": {
                "title": {"en": "Foundation", "ru": "Основы"},
                "subtitle": {
                    "en": "The language of medicine and a first picture of the patient",
                    "ru": "Язык медицины и первичная картина пациента",
                },
            },
        },
        "lessons": {
            "word-roots": {
                "title": {"en": "How medical words are built", "ru": "Как устроены медицинские слова"},
                "summary": {
                    "en": "Prefix + root + suffix. Learn 15 roots and you start reading department signs.",
                    "ru": "Приставка + корень + суффикс. Выучите 15 корней — и начнёте читать вывески отделений.",
                },
            },
            "body-systems": {
                "title": {"en": "Organ systems: a map of the body", "ru": "Системы органов: карта тела"},
                "summary": {
                    "en": "One screen for every system, so you do not mix up “where it hurts” and “which service”.",
                    "ru": "Один экран — все системы, чтобы потом не путать «где болит» и «какая служба».",
                },
            },
            "vitals": {
                "title": {"en": "Vital signs", "ru": "Витальные признаки"},
                "summary": {
                    "en": "Four numbers you look at first: pulse, blood pressure, breathing, temperature (+ SpO2).",
                    "ru": "Четыре числа, которые смотрят первыми: пульс, давление, дыхание, температура (+ SpO2).",
                },
            },
            "symptoms": {
                "title": {"en": "Complaints in English", "ru": "Жалобы на английском"},
                "summary": {
                    "en": "Words patients and doctors use for pain, shortness of breath, nausea, and fatigue.",
                    "ru": "Слова, которыми пациент и врач называют боль, одышку, тошноту и слабость.",
                },
            },
        },
    },
}


def pick(entry, lang=None):
    lang = lang or current_lang()
    if not isinstance(entry, dict):
        return entry or ""
    return entry.get(lang) or entry.get("en") or entry.get("ru") or ""


def course_field(course_slug, field, fallback="", lang=None):
    block = COURSE_META.get(course_slug) or {}
    return pick(block.get(field), lang) or fallback


def level_field(course_slug, level_slug, field, fallback="", lang=None):
    block = ((COURSE_META.get(course_slug) or {}).get("levels") or {}).get(level_slug) or {}
    return pick(block.get(field), lang) or fallback


def lesson_field(course_slug, lesson_slug, field, fallback="", lang=None):
    block = ((COURSE_META.get(course_slug) or {}).get("lessons") or {}).get(lesson_slug) or {}
    return pick(block.get(field), lang) or fallback
