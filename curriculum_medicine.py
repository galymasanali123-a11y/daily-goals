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
    "slug": "medicine",
    "title": "Medicine",
    "short": "MD",
    "subtitle": "Термины, системы органов, витальные признаки и симптомы",
    "category": "medicine",
    "accent": "#be185d",
    "icon": "Rx",
    "blurb": "Не учебник терапии, а ясный каркас: из чего состоит слово, как устроено тело, что измерять и как назвать жалобу по-английски.",
    "levels": [
        {
            "slug": "foundation",
            "short": "Base",
            "title": "Foundation",
            "subtitle": "Язык медицины и первичная картина пациента",
            "lessons": [
                _lesson(
                    "word-roots",
                    "Как устроены медицинские слова",
                    14,
                    "Приставка + корень + суффикс. Выучите 15 корней — и начнёте читать вывески отделений.",
                    [
                        {"type": "p", "text": "Большинство терминов — конструктор из греческого и латыни. Не зубрите стостраничный словарь: соберите слово из трёх частей."},
                        {"type": "h2", "text": "Три детали"},
                        {"type": "table", "headers": ["Часть", "Роль", "Пример"], "rows": [
                            ["Приставка", "где / сколько / против", "hyper- слишком, hypo- мало, anti- против"],
                            ["Корень", "орган или вещество", "cardi/o сердце, hepat/o печень"],
                            ["Суффикс", "состояние или процедура", "-itis воспаление, -ectomy удаление"],
                        ]},
                        {"type": "example", "en": "cardi + itis → carditis", "ru": "воспаление сердца"},
                        {"type": "example", "en": "hepat + itis → hepatitis", "ru": "воспаление печени"},
                        {"type": "example", "en": "append + ectomy → appendectomy", "ru": "удаление аппендикса"},
                        {"type": "h2", "text": "Корни, которые встречаются каждый день"},
                        {"type": "table", "headers": ["Корень", "Значение"], "rows": [
                            ["cardi/o", "сердце"],
                            ["neur/o", "нерв, нервная система"],
                            ["gastr/o", "желудок"],
                            ["hepat/o", "печень"],
                            ["nephr/o, ren/o", "почка"],
                            ["oste/o", "кость"],
                            ["my/o", "мышца"],
                            ["derm/o", "кожа"],
                            ["hem/o, hemat/o", "кровь"],
                            ["pneum/o, pulmon/o", "лёгкое"],
                        ]},
                        {"type": "note", "text": "Соединительная -o- появляется, если дальше согласная: gastr-o-scopy. Перед гласной часто без неё: gastritis."},
                    ],
                    [
                        _word("cardio", "cardi/o", "сердце", "cardiology"),
                        _word("neuro", "neur/o", "нерв", "neurology"),
                        _word("gastro", "gastr/o", "желудок", "gastritis"),
                        _word("hepato", "hepat/o", "печень", "hepatitis"),
                        _word("itis", "-itis", "воспаление", "arthritis"),
                        _word("ectomy", "-ectomy", "удаление", "tonsillectomy"),
                        _word("hyper", "hyper-", "избыток, высоко", "hypertension"),
                        _word("hypo", "hypo-", "недостаток, низко", "hypoglycemia"),
                    ],
                    [
                        _ex("mcq", "hepat/o означает…", "печень", ["сердце", "печень", "почка", "кость"], "hepat/o — печень."),
                        _ex("mcq", "Суффикс воспаления —", "-itis", ["-ectomy", "-itis", "-ology", "-emia"], "gastritis, arthritis."),
                        _ex("fill", "____tension — высокое давление (приставка)", "hyper", None, "hypertension."),
                        _ex("mcq", "appendectomy — это…", "удаление аппендикса", ["воспаление аппендикса", "удаление аппендикса", "снимок аппендикса", "боль в аппендиксе"], "-ectomy = cut out."),
                    ],
                ),
                _lesson(
                    "body-systems",
                    "Системы органов: карта тела",
                    14,
                    "Один экран — все системы, чтобы потом не путать «где болит» и «какая служба».",
                    [
                        {"type": "p", "text": "Клиническое мышление начинается с системы, а не со случайного термина. Ниже — рабочие определения, достаточные для учёбы и карточек."},
                        {"type": "table", "headers": ["Система", "Главная работа", "Ориентиры"], "rows": [
                            ["Cardiovascular", "гнать кровь", "heart, arteries, veins"],
                            ["Respiratory", "газобмен", "lungs, trachea, bronchi"],
                            ["Nervous", "сигналы и управление", "brain, spinal cord, nerves"],
                            ["Digestive", "разбор пищи", "esophagus, stomach, intestines, liver"],
                            ["Urinary", "фильтр и баланс жидкости", "kidneys, bladder"],
                            ["Musculoskeletal", "движение и опора", "bones, muscles, joints"],
                            ["Endocrine", "гормоны", "thyroid, pancreas, adrenal"],
                            ["Integumentary", "барьер", "skin, nails"],
                            ["Immune / lymphatic", "защита", "lymph nodes, spleen"],
                            ["Reproductive", "продолжение рода", "uterus, ovaries / testes"],
                        ]},
                        {"type": "h2", "text": "Как описывать положение"},
                        {"type": "ul", "items": [
                            "anterior — спереди, posterior — сзади",
                            "superior — выше, inferior — ниже",
                            "medial — к средней линии, lateral — в сторону",
                            "proximal — ближе к туловищу, distal — дальше (для конечностей)",
                        ]},
                        {"type": "example", "en": "The heart is medial to the lungs and superior to the diaphragm.", "ru": "Сердце медиальнее лёгких и выше диафрагмы."},
                    ],
                    [
                        _word("heart", "heart", "сердце", "The heart pumps blood."),
                        _word("lungs", "lungs", "лёгкие", "The lungs fill with air."),
                        _word("kidney", "kidney", "почка", "Each person has two kidneys."),
                        _word("liver", "liver", "печень", "The liver sits in the right upper abdomen."),
                        _word("anterior", "anterior", "передний", "the anterior chest"),
                        _word("posterior", "posterior", "задний", "posterior view"),
                        _word("lateral", "lateral", "боковой", "lateral ankle"),
                        _word("distal", "distal", "дистальный", "distal radius"),
                    ],
                    [
                        _ex("mcq", "Почки относятся к системе…", "urinary", ["digestive", "urinary", "respiratory", "integumentary"], "kidneys → urinary."),
                        _ex("mcq", "Distal значит…", "дальше от туловища", ["ближе к туловищу", "дальше от туловища", "сзади", "внутри"], "кисть дистальнее плеча."),
                        _ex("fill", "The ____ pumps blood. (орган)", "heart", None, "heart"),
                        _ex("tf", "Liver — это почка.", "false", ["true", "false"], "liver = печень, kidney = почка."),
                    ],
                ),
                _lesson(
                    "vitals",
                    "Витальные признаки",
                    12,
                    "Четыре числа, которые смотрят первыми: пульс, давление, дыхание, температура (+ SpO2).",
                    [
                        {"type": "p", "text": "Vital signs — быстрый снимок, жив ли контур «насос — кислород — терморегуляция». Нормы взрослых ниже — ориентир, не догма: смотрите на человека, возраст и тренд."},
                        {"type": "table", "headers": ["Признак", "Сокращение", "Ориентир взрослого"], "rows": [
                            ["Heart rate", "HR / pulse", "60–100 / min"],
                            ["Blood pressure", "BP", "около 90/60 – 120/80 mmHg"],
                            ["Respiratory rate", "RR", "12–20 / min"],
                            ["Temperature", "T", "около 36.1–37.2 °C"],
                            ["Oxygen saturation", "SpO₂", "обычно ≥ 95% на воздухе"],
                        ]},
                        {"type": "h2", "text": "Как читать давление"},
                        {"type": "ul", "items": [
                            "Первое число — систола (сердце сжалось)",
                            "Второе — диастола (сердце расслабилось)",
                            "120/80 читают «сто двадцать на восемьдесят»",
                        ]},
                        {"type": "h2", "text": "Слова, которые путают"},
                        {"type": "table", "headers": ["Термин", "Смысл"], "rows": [
                            ["tachycardia", "слишком частый пульс"],
                            ["bradycardia", "слишком редкий пульс"],
                            ["hypertension", "высокое давление"],
                            ["hypotension", "низкое давление"],
                            ["fever / pyrexia", "повышенная температура"],
                            ["hypoxia", "мало кислорода в тканях"],
                        ]},
                        {"type": "note", "text": "Одно «плохое» число ещё не диагноз. Два витальных вне нормы + жалобы — уже повод действовать по протоколу, а не по памяти из приложения."},
                    ],
                    [
                        _word("hr", "heart rate", "частота сердечных сокращений", "HR 72 bpm"),
                        _word("bp", "blood pressure", "артериальное давление", "BP 118/76"),
                        _word("rr", "respiratory rate", "частота дыхания", "RR 16"),
                        _word("spo2", "SpO₂", "сатурация кислорода", "SpO2 98%"),
                        _word("tachy", "tachycardia", "тахикардия", "HR 130 → tachycardia"),
                        _word("brady", "bradycardia", "брадикардия", "HR 42 → bradycardia"),
                        _word("htn", "hypertension", "гипертония", "high blood pressure"),
                    ],
                    [
                        _ex("mcq", "Нормальный пульс взрослого ближе к…", "72 / min", ["32 / min", "72 / min", "160 / min", "8 / min"], "60–100."),
                        _ex("mcq", "В записи 130/85 первое число — это…", "систола", ["диастола", "систола", "пульс", "температура"], "systolic / diastolic."),
                        _ex("fill", "Слишком редкий пульс называют ____cardia.", "brady", None, "bradycardia."),
                        _ex("tf", "SpO₂ 88% на воздухе для здорового взрослого — норма.", "false", ["true", "false"], "Обычно ждут ≥ 95%, 88% — гипоксия, пока нет другой цели (например COPD)."),
                    ],
                ),
                _lesson(
                    "symptoms",
                    "Жалобы на английском",
                    12,
                    "Слова, которыми пациент и врач называют боль, одышку, тошноту и слабость.",
                    [
                        {"type": "p", "text": "На приёме полезен каркас SOCRATES для боли: Site, Onset, Character, Radiation, Associations, Time course, Exacerbating/relieving, Severity."},
                        {"type": "table", "headers": ["English", "Русский", "Уточнение"], "rows": [
                            ["pain / ache", "боль", "ache — тупая, тянущая"],
                            ["chest pain", "боль в груди", "всегда уточняйте характер"],
                            ["shortness of breath (SOB)", "одышка", "at rest or on exertion?"],
                            ["cough", "кашель", "dry or productive?"],
                            ["fever", "лихорадка", "measured or subjective?"],
                            ["nausea / vomiting", "тошнота / рвота", "не одно и то же"],
                            ["dizziness", "головокружение", "vertigo vs lightheaded"],
                            ["fatigue / weakness", "усталость / слабость", "weakness — сила мышц"],
                            ["swelling (edema)", "отёк", "legs, face, one-sided?"],
                            ["rash", "сыпь", "itchy? spreading?"],
                        ]},
                        {"type": "example", "en": "I have a sharp pain in my right lower abdomen. It started this morning.", "ru": "Острая боль в правом нижнем квадранте с утра — формулировка, которую ждут на практике."},
                        {"type": "h2", "text": "Характер боли"},
                        {"type": "ul", "items": ["sharp — острая", "dull — тупая", "burning — жжение", "cramping — схваткообразная", "pressure / tightness — давящая, стеснение"]},
                    ],
                    [
                        _word("pain", "pain", "боль", "Where is the pain?"),
                        _word("sob", "shortness of breath", "одышка", "SOB on exertion"),
                        _word("cough", "cough", "кашель", "a dry cough"),
                        _word("fever", "fever", "лихорадка", "fever and chills"),
                        _word("nausea", "nausea", "тошнота", "nausea without vomiting"),
                        _word("edema", "edema / swelling", "отёк", "ankle edema"),
                        _word("rash", "rash", "сыпь", "an itchy rash"),
                        _word("fatigue", "fatigue", "усталость", "extreme fatigue"),
                    ],
                    [
                        _ex("mcq", "Shortness of breath — это…", "одышка", ["кровотечение", "одышка", "сыпь", "отёк"], "SOB."),
                        _ex("mcq", "Nausea без vomiting значит…", "тошнит, но не рвёт", ["только рвота", "тошнит, но не рвёт", "головная боль", "кашель"], "это разные жалобы."),
                        _ex("fill", "Dull ____ in the lower back. (слово «боль»)", "pain", None, "dull pain / ache."),
                        _ex("mcq", "Onset в SOCRATES — это…", "когда началось", ["где болит", "когда началось", "насколько сильно", "куда отдаёт"], "Onset = начало."),
                    ],
                ),
            ],
        }
    ],
}
