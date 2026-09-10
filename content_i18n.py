"""English/Russian copy for course catalog metadata (titles, blurbs, summaries)."""

from i18n import current_lang

COURSE_META = {
    "english": {
        "title": {"en": "English", "ru": "Английский"},
        "subtitle": {
            "en": "Grammar, words, and exercises — from A1 to B2",
            "ru": "Грамматика, слова и задания — от A1 до B2",
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
            "b2": {
                "title": {"en": "B2 · Independent user", "ru": "B2 · Свободный пользователь"},
                "subtitle": {
                    "en": "Narrative tenses, mixed conditionals, register, debate, and fluency labs",
                    "ru": "Повествование, смешанные условия, регистр, спор и лаборатории речи",
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
            "en": "Grammar, words, and exercises — from A1 to B2",
            "ru": "Грамматика, слова и задания — от A1 до B2",
        },
        "blurb": {
            "en": "German from zero to B2: gender from the start, cases, Perfekt, Konjunktiv, and dialogues. Reading follows the UW-Madison open course and Grimm tales.",
            "ru": "Немецкий с нуля до B2: род сразу, падежи, Perfekt, Konjunktiv и живые диалоги. Чтение опирается на открытый курс UW-Madison и сказки Гримм.",
        },
        "levels": {
            "a1": {
                "title": {"en": "A1 · Start", "ru": "A1 · Начало"},
                "subtitle": {
                    "en": "First phrases, gender, cases, café, city, and speech",
                    "ru": "Первые фразы, род, падеж, кафе, город и речь",
                },
            },
            "a2": {
                "title": {"en": "A2 · Everyday German", "ru": "A2 · Бытовой немецкий"},
                "subtitle": {
                    "en": "Modals, Perfekt, separable verbs, dative, and travel talk",
                    "ru": "Модальные, Perfekt, отделяемые приставки, датив и дорога",
                },
            },
            "b1": {
                "title": {"en": "B1 · Independent German", "ru": "B1 · Самостоятельный немецкий"},
                "subtitle": {
                    "en": "Präteritum, relative clauses, Konjunktiv II, passive — with speaking labs",
                    "ru": "Präteritum, относительные предложения, Konjunktiv II, пассив и речь",
                },
            },
            "b2": {
                "title": {"en": "B2 · Formal and fluent", "ru": "B2 · Формально и бегло"},
                "subtitle": {
                    "en": "Reported speech, nominal style, argumentation, and fluency",
                    "ru": "Косвенная речь, номинальный стиль, аргументация и беглость",
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
            "en": "Terms, OpenStax anatomy, and clinic English",
            "ru": "Термины, анатомия по OpenStax и клинический английский",
        },
        "blurb": {
            "en": "Not a therapy textbook — a strong frame: word-building, body systems via open OpenStax A&P 2e, Gray’s Anatomy 1918, and clinic English for complaints and case talk.",
            "ru": "Не учебник терапии, а сильная база: словообразование, системы тела по открытому OpenStax A&P 2e, Gray’s Anatomy 1918 и клинический английский для жалоб и разбора случая.",
        },
        "levels": {
            "foundation": {
                "title": {"en": "Foundation", "ru": "Основы"},
                "subtitle": {
                    "en": "Medical language, vitals, history, and safety",
                    "ru": "Язык медицины, витальные признаки, анамнез и безопасность",
                },
            },
            "anatomy": {
                "title": {"en": "Anatomy · OpenStax path", "ru": "Анатомия · путь OpenStax"},
                "subtitle": {
                    "en": "Cells to endocrine: original lessons mapped to OpenStax A&P 2e",
                    "ru": "От клетки до эндокринной системы: уроки по карте OpenStax A&P 2e",
                },
            },
            "clinic": {
                "title": {"en": "Clinic · language", "ru": "Клиника · язык"},
                "subtitle": {
                    "en": "Infection vocabulary, case talk, and plain-language fluency — not treatment",
                    "ru": "Инфекция, разбор случая и ясные формулировки — не лечение",
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
    "korean": {
        "title": {"en": "Korean", "ru": "Корейский"},
        "subtitle": {
            "en": "Hangul, particles, and conversation through B2",
            "ru": "Хангыль, частицы и разговор до B2",
        },
        "blurb": {
            "en": "Korean from zero to B2: Hangul, 은/는 and 이/가, 해요체 as the working register, food, directions, work, and debate. Modern Seoul Korean — not 1960s textbook spellings.",
            "ru": "Корейский с нуля до B2: хангыль, 은/는 и 이/가, 해요체 как рабочий регистр, еда, дорога, работа и спор. Современный сеульский язык — не орфография учебников 1960-х.",
        },
        "levels": {
            "a1": {
                "title": {"en": "A1 · Hangul and first conversations", "ru": "A1 · Хангыль и первые разговоры"},
                "subtitle": {
                    "en": "Letters, greetings, particles, numbers, time, place, food",
                    "ru": "Буквы, приветствия, частицы, числа, время, место, еда",
                },
            },
            "a2": {
                "title": {"en": "A2 · Objects, past, honorifics, travel", "ru": "A2 · Объект, прошлое, гоноратив, дорога"},
                "subtitle": {
                    "en": "을/를, past tense, 고 싶다, 시, counters, clause links, subway Korean",
                    "ru": "을/를, прошедшее, 고 싶다, 시, счётные слова, связки, метро",
                },
            },
            "b1": {
                "title": {"en": "B1 · Independent Korean", "ru": "B1 · Самостоятельный корейский"},
                "subtitle": {
                    "en": "Future, conditionals, quoted speech, modifiers, workplace talk",
                    "ru": "Будущее, условия, косвенная речь, определения, работа и школа",
                },
            },
            "b2": {
                "title": {"en": "B2 · Register and fluency", "ru": "B2 · Регистр и беглость"},
                "subtitle": {
                    "en": "Speech levels, passive/causative, debate, and repair strategies",
                    "ru": "Уровни речи, пассив/каузатив, спор и стратегии починки фразы",
                },
            },
        },
        "lessons": {},
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


def from_packed(obj, field, lang=None, fallback=""):
    """Prefer {field}_i18n on the curriculum object, then COURSE_META, then the raw string."""
    packed = (obj or {}).get(f"{field}_i18n")
    if packed:
        return pick(packed, lang) or fallback
    return fallback
