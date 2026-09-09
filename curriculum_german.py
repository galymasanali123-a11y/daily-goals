def _ex(kind, prompt, answer, options=None, explanation=""):
    item = {"type": kind, "prompt": prompt, "answer": answer, "explanation": explanation}
    if options:
        item["options"] = options
    return item


def _word(wid, front, back, example=""):
    return {"id": wid, "front": front, "back": back, "example": example}


def _lesson(slug, title, minutes, summary, sections, vocab, exercises):
    return {
        "slug": slug,
        "title": title,
        "minutes": minutes,
        "summary": summary,
        "sections": sections,
        "vocab": vocab,
        "exercises": exercises,
    }


COURSE = {
    "slug": "german",
    "title": "Deutsch",
    "short": "DE",
    "subtitle": "A1: приветствие, sein/haben, артикли и настоящее время",
    "category": "language",
    "accent": "#c2410c",
    "icon": "De",
    "blurb": "Немецкий с нуля: род существительных сразу, честные таблицы и слова, которые пригодятся в быту.",
    "levels": [
        {
            "slug": "a1",
            "short": "A1",
            "title": "A1 · Start",
            "subtitle": "Первые фразы, род, глаголы sein и haben",
            "lessons": [
                _lesson(
                    "hallo",
                    "Hallo и алфавит",
                    10,
                    "Приветствие, вежливость и как звучат умляуты.",
                    [
                        {"type": "p", "text": "В немецком вежливость слышно сразу: Sie — вежливое «вы», du — «ты». С незнакомыми взрослыми начинайте с Sie."},
                        {"type": "table", "headers": ["Deutsch", "Русский"], "rows": [
                            ["Hallo / Guten Tag", "Привет / Добрый день"],
                            ["Guten Morgen / Guten Abend", "Доброе утро / Добрый вечер"],
                            ["Auf Wiedersehen / Tschüss", "До свидания / Пока"],
                            ["Bitte / Danke", "Пожалуйста / Спасибо"],
                            ["Wie heißen Sie?", "Как вас зовут? (вежливо)"],
                            ["Ich heiße… / Ich bin…", "Меня зовут… / Я…"],
                        ]},
                        {"type": "h2", "text": "Буквы, которых нет в английском"},
                        {"type": "ul", "items": [
                            "ä, ö, ü — умляуты: Mädchen, schön, Tür",
                            "ß (эсцет) = ss: heiß, Straße (в Швейцарии часто ss)",
                        ]},
                        {"type": "example", "en": "Guten Tag! Ich heiße Lena. Freut mich.", "ru": "Добрый день! Меня зовут Лена. Очень приятно."},
                    ],
                    [
                        _word("hallo", "Hallo", "привет", "Hallo, Anna!"),
                        _word("tag", "Guten Tag", "добрый день", "Guten Tag, Herr Klein."),
                        _word("danke", "Danke", "спасибо", "Danke schön!"),
                        _word("bitte", "Bitte", "пожалуйста", "Bitte sehr."),
                        _word("heisse", "Ich heiße…", "меня зовут", "Ich heiße Max."),
                        _word("tschuss", "Tschüss", "пока", "Tschüss!"),
                    ],
                    [
                        _ex("mcq", "Как вежливо спросить имя?", "Wie heißen Sie?", ["Wie heißt du?", "Wie heißen Sie?", "Was ist Name?", "Wer bist du?"], "Sie — вежливая форма."),
                        _ex("mcq", "ß читается как…", "ss", ["ш", "ss", "з", "тс"], "Straße ≈ Strasse."),
                        _ex("fill", "____ Tag! (добрый день)", "Guten", None, "Guten Tag."),
                    ],
                ),
                _lesson(
                    "sein-haben",
                    "sein и haben",
                    14,
                    "Два глагола, без которых нет ни одного простого текста.",
                    [
                        {"type": "h2", "text": "sein — быть"},
                        {"type": "table", "headers": ["Person", "sein", "Пример"], "rows": [
                            ["ich", "bin", "Ich bin Student."],
                            ["du", "bist", "Du bist müde."],
                            ["er/sie/es", "ist", "Sie ist Ärztin."],
                            ["wir", "sind", "Wir sind hier."],
                            ["ihr", "seid", "Ihr seid nett."],
                            ["sie/Sie", "sind", "Sie sind Lehrer."],
                        ]},
                        {"type": "h2", "text": "haben — иметь"},
                        {"type": "table", "headers": ["Person", "haben", "Пример"], "rows": [
                            ["ich", "habe", "Ich habe Zeit."],
                            ["du", "hast", "Hast du Hunger?"],
                            ["er/sie/es", "hat", "Er hat ein Auto."],
                            ["wir", "haben", "Wir haben Glück."],
                            ["ihr", "habt", "Habt ihr Fragen?"],
                            ["sie/Sie", "haben", "Sie haben Recht."],
                        ]},
                        {"type": "note", "text": "sie (они) и Sie (вы вежливо) пишутся по-разному только с заглавной. По смыслу смотрите контекст."},
                        {"type": "example", "en": "Ich bin 20. Ich habe eine Schwester.", "ru": "Мне 20. У меня есть сестра."},
                    ],
                    [
                        _word("bin", "ich bin", "я есть", "Ich bin müde."),
                        _word("ist", "er/sie/es ist", "он/она/оно есть", "Es ist kalt."),
                        _word("sind", "wir/sie sind", "мы/они есть", "Wir sind bereit."),
                        _word("habe", "ich habe", "у меня есть", "Ich habe einen Hund."),
                        _word("hat", "er/sie hat", "у него/неё есть", "Sie hat Zeit."),
                        _word("hast", "du hast", "у тебя есть", "Hast du Brot?"),
                    ],
                    [
                        _ex("mcq", "Du ____ Lehrer.", "bist", ["bin", "bist", "ist", "seid"], "du bist"),
                        _ex("mcq", "Er ____ keine Zeit.", "hat", ["habe", "hast", "hat", "habt"], "er hat"),
                        _ex("fill", "Wir ____ Studenten. (sein)", "sind", None, "wir sind"),
                        _ex("tf", "Ich bist hungrig — правильно.", "false", ["true", "false"], "Ich bin hungrig."),
                    ],
                ),
                _lesson(
                    "articles",
                    "der / die / das",
                    14,
                    "Род нужно учить вместе со словом. Иначе падежи потом развалятся.",
                    [
                        {"type": "p", "text": "У каждого немецкого существительного есть род: мужской (der), женский (die), средний (das). Во множественном числе артикль почти всегда die."},
                        {"type": "table", "headers": ["Артикль", "Род", "Примеры"], "rows": [
                            ["der", "мужской", "der Mann, der Tisch, der Tag"],
                            ["die", "женский", "die Frau, die Lampe, die Tür"],
                            ["das", "средний", "das Kind, das Buch, das Haus"],
                            ["die (Pl.)", "множественное", "die Bücher, die Frauen"],
                        ]},
                        {"type": "h2", "text": "Неопределённый артикль — «какой-то»"},
                        {"type": "ul", "items": ["der → ein", "die → eine", "das → ein", "отрицание: kein / keine"]},
                        {"type": "example", "en": "Das ist ein Buch. Das Buch ist neu.", "ru": "Сначала ein (новое), потом das (уже известное)."},
                        {"type": "h2", "text": "Подсказки, не правила на 100%"},
                        {"type": "ul", "items": [
                            "-ung, -heit, -keit, -tion → обычно die",
                            "-chen, -lein → das (Mädchen — девочка, но средний род!)",
                            "дни, месяцы, времена года, большинство марок машин → der",
                        ]},
                        {"type": "note", "text": "Учите карточку как «das Buch», не «Buch». Без артикля слово почти бесполезно."},
                    ],
                    [
                        _word("der", "der", "определённый, м.р.", "der Stuhl"),
                        _word("die", "die", "определённый, ж.р. / мн.ч.", "die Lampe"),
                        _word("das", "das", "определённый, ср.р.", "das Fenster"),
                        _word("ein", "ein", "неопределённый, м.р. и ср.р.", "ein Tisch / ein Kind"),
                        _word("eine", "eine", "неопределённый, ж.р.", "eine Frau"),
                        _word("buch", "das Buch", "книга", "Ich lese das Buch."),
                        _word("frau", "die Frau", "женщина", "Die Frau ist nett."),
                    ],
                    [
                        _ex("mcq", "____ Mädchen (девочка)", "das", ["der", "die", "das", "ein"], "-chen → das Mädchen."),
                        _ex("mcq", "Ich habe ____ Auto. (неопределённый, das Auto)", "ein", ["ein", "eine", "einen", "das"], "das → ein."),
                        _ex("fill", "____ Tür ist offen. (дверь — die)", "Die", None, "Die Tür."),
                    ],
                ),
                _lesson(
                    "present-verbs",
                    "Настоящее время: слабые глаголы",
                    12,
                    "Основы спряжения: ich lerne, du lernst, er lernt.",
                    [
                        {"type": "pattern", "text": "основа + окончание    lernen → lern-"},
                        {"type": "table", "headers": ["Person", "Окончание", "lernen"], "rows": [
                            ["ich", "-e", "lerne"],
                            ["du", "-st", "lernst"],
                            ["er/sie/es", "-t", "lernt"],
                            ["wir", "-en", "lernen"],
                            ["ihr", "-t", "lernt"],
                            ["sie/Sie", "-en", "lernen"],
                        ]},
                        {"type": "example", "en": "Ich lerne Deutsch. Wo wohnst du?", "ru": "Я учу немецкий. Где ты живёшь?"},
                        {"type": "h2", "text": "Глагол в предложении — на втором месте"},
                        {"type": "ul", "items": [
                            "Heute lerne ich. — если начали с обстоятельства, глагол всё равно второй.",
                            "Вопрос без вопросительного слова: Lernst du Deutsch?",
                        ]},
                        {"type": "note", "text": "kommen, heißen, sprechen — сильные, у них меняется гласная: du kommst, du sprichst. Их список — отдельно, не ломайте слабую таблицу."},
                    ],
                    [
                        _word("lernen", "lernen", "учить", "Wir lernen zusammen."),
                        _word("wohnen", "wohnen", "жить", "Ich wohne in Berlin."),
                        _word("arbeiten", "arbeiten", "работать", "Sie arbeitet viel."),
                        _word("kommen", "kommen", "приходить", "Woher kommst du?"),
                        _word("sprechen", "sprechen", "говорить", "Sprechen Sie Deutsch?"),
                    ],
                    [
                        _ex("mcq", "Du ____ Deutsch. (lernen)", "lernst", ["lerne", "lernst", "lernt", "lernen"], "du → -st."),
                        _ex("mcq", "Глагол стоит…", "на втором месте", ["в конце", "на втором месте", "всегда первым", "где угодно"], "Во 2-й позиции в утверждении."),
                        _ex("fill", "____ du in Köln? (wohnen, форма du)", "Wohnst", None, "Wohnst du…"),
                    ],
                ),
            ],
        }
    ],
}
