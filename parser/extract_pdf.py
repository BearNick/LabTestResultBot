import re
from typing import Optional, Tuple, List

import pdfplumber

# Пытаемся подключить анонимайзер, если есть
try:
    from bot.utils.privacy import anonymize_text  # noqa: F401
    HAVE_PRIVACY = True
except Exception:
    HAVE_PRIVACY = False


# -----------------------
# Настройки и словари
# -----------------------

# Какие метрики «логично» чинить, если OCR пропустил точку (111 -> 11.1)
DECIMAL_FIX_WHITELIST = {
    "Гемоглобин", "Hemoglobin", "Hemoglobina",
    "MCH", "MCHC", "MCV",
    "Глюкоза", "Glucose", "Glucosa",
    "Креатинин", "Creatinine", "Creatinina",
    "Мочевина", "Urea",
    "Билирубин общий", "Total bilirubin", "Bilirrubina total",
    "Билирубин прямой", "Direct bilirubin", "Bilirrubina directa",
    "АЛТ", "ALT",
    "АСТ", "AST",
    "ГГТ", "GGT",
    "АЛП", "ALP", "Alkaline phosphatase", "Fosfatasa alcalina",
    "Общий белок", "Total protein", "Proteína total",
    "Холестерин общий", "Total cholesterol", "Colesterol total",
    "ЛПНП", "LDL", "Colesterol LDL",
    "ЛПВП", "HDL", "Colesterol HDL",
}

# Отображение «разных» написаний показателей к **каноническому ключу** в нашем словаре
INDICATORS_MAP = {
    # Биохимия
    "ALT": ["alt", "аланинаминотрансфераза", "алт", "alanine aminotransferase", "transaminasa alt", "алат"],
    "AST": ["ast", "аспартатаминотрансфераза", "аст", "aspartate aminotransferase", "transaminasa ast", "асат"],
    "Глюкоза": ["глюкоза", "glucose", "glucosa"],
    "Креатинин": ["креатинин", "creatinine", "creatinina"],
    "Мочевина": ["мочевина", "urea"],
    "Билирубин общий": ["билирубин общий", "total bilirubin", "bilirrubina total"],
    "Билирубин прямой": ["билирубин прямой", "direct bilirubin", "bilirrubina directa"],
    "Холестерин общий": ["общий холестерин", "total cholesterol", "colesterol total", "cholesterol total"],
    "ЛПВП": ["лпвп", "hdl", "colesterol hdl", "hdl-c"],
    "ЛПНП": ["лпнп", "ldl", "colesterol ldl", "ldl-c"],
    "АЛП": ["щелочная фосфатаза", "алп", "alp", "alkaline phosphatase", "fosfatasa alcalina"],
    "ГГТ": ["ggt", "ггт", "gamma-gt", "gamma glutamyl transferase", "gammaglutamil transferasa"],
    "Общий белок": ["общий белок", "total protein", "proteína total", "protein total"],

    # ОАК
    "Гемоглобин": ["гемоглобин", "hgb", "hemoglobin", "hemoglobina"],
    "Гематокрит": ["гематокрит", "hct", "hematocrit", "hematocrito"],
    "Эритроциты": ["эритроциты", "rbc", "red blood cells", "eritrocitos"],
    "Лейкоциты": ["лейкоциты", "wbc", "white blood cells", "leucocitos"],
    "Тромбоциты": ["тромбоциты", "plt", "platelets", "plaquetas"],
    "СОЭ": ["соэ", "esr", "sedimentation rate", "vsg", "velocidad de sedimentación"],

    "MCV": ["mcv", "mean corpuscular volume", "volumen corpuscular medio"],
    "MCH": ["mch", "mean corpuscular hemoglobin", "hemoglobina corpuscular media"],
    "MCHC": ["mchc", "mean corpuscular hemoglobin concentration",
             "concentración de hemoglobina corpuscular media"],
    "RDW": ["rdw", "red cell distribution width", "amplitud de distribución eritrocitaria"],

    "Нейтрофилы %": ["нейтрофилы", "neutrophils", "neutrófilos"],
    "Лимфоциты %": ["лимфоциты", "lymphocytes", "linfocitos"],
    "Моноциты %": ["моноциты", "monocytes", "monocitos"],
    "Эозинофилы %": ["эозинофилы", "eosinophils", "eosinófilos"],
    "Базофилы %": ["базофилы", "basophils", "basófilos"],

    # Абсолюты (часто встречаются)
    "Нейтрофилы абс.": ["neutrophils abs", "нейтрофилы абс", "neu abs", "neut abs"],
    "Лимфоциты абс.": ["lymphocytes abs", "лимфоциты абс", "lym abs"],
    "Моноциты абс.": ["monocytes abs", "моноциты абс", "mon abs"],
    "Эозинофилы абс.": ["eosinophils abs", "эозинофилы абс", "eos abs"],
    "Базофилы абс.": ["basophils abs", "базофилы абс", "baso abs"],

    # --- Антитела / иммуноглобулины ---
    # Иммуноглобулины (частые варианты записи и локализации)
    "IgA": [
        "iga", "immunoglobulin a", "immunoglobulina a",
        "игa", "иг а", "иммуноглобулин a"
    ],
    "IgG": [
        "igg", "immunoglobulin g", "immunoglobulina g",
        "игg", "иг г", "иммуноглобулин g"
    ],
    "IgM": [
        "igm", "immunoglobulin m", "immunoglobulina m",
        "игm", "иг м", "иммуноглобулин m"
    ],
    "IgE": [
        "ige", "immunoglobulin e", "immunoglobulina e",
        "игe", "иг е", "иммуноглобулин e"
    ],
    "IgD": [
        "igd", "immunoglobulin d", "immunoglobulina d",
        "игd", "иг д", "иммуноглобулин d"
    ],

    # Anti-TPO (антитела к тиреопероксидазе)
    "anti-TPO": [
        "anti-tpo", "anti tpo", "anti-tpo", "anti–tpo",
        "антитела к тпо", "антитела к тиреопероксидазе", "ато", "ат к тпо", "ат-тпо",
        "anti-thyroid peroxidase", "anticuerpos anti tpo", "anticuerpos contra la peroxidasa tiroidea"
    ],

    # Anti-TG (антитела к тиреоглобулину)
    "anti-TG": [
        "anti-tg", "anti tg", "anti-tg", "anti–tg",
        "антитела к тг", "антитела к тиреоглобулину", "ат к тг", "ат-тг",
        "anti-thyroglobulin", "anticuerpos anti tg", "anticuerpos contra la tiroglobulina"
    ],

    # ANA (антинуклеарные антитела)
    "ANA": [
        "ana", "anti-nuclear", "antinuclear", "antinucleares",
        "антинуклеарные антитела", "анти-нуклеарные", "анти нуклеарные"
    ],
}

# -----------------------
# Публичная функция
# -----------------------

def extract_lab_data_from_pdf(filepath: str, max_pages: int = 5) -> dict:
    """
    Извлекает метрики из PDF. Возвращает словарь {канонический_показатель: float|None}.
    Читает до max_pages страниц. Пытается фиксить частые OCR-ошибки.
    """
    lab_data: dict = {}

    try:
        with pdfplumber.open(filepath) as pdf:
            text_chunks: List[str] = []
            pages_to_read = min(len(pdf.pages), max_pages)
            for i in range(pages_to_read):
                page = pdf.pages[i]
                page_text = page.extract_text() or ""
                text_chunks.append(page_text)

        raw_text = "\n".join(text_chunks)

        # Анонимизация (если есть модуль)
        if HAVE_PRIVACY:
            try:
                raw_text = anonymize_text(raw_text)  # type: ignore
            except Exception:
                pass

        # По строкам
        lines = [l for l in raw_text.split("\n") if l.strip()]

        for line in lines:
            key, val = match_indicator(line)
            if key:
                lab_data[key] = val

        return lab_data

    except Exception as e:
        # Без лишней болтологии: просто вернём пусто.
        # Если нужно логировать — логи уже настраиваются в main/logging.
        return {}


# -----------------------
# Внутренняя логика
# -----------------------

def match_indicator(line: str) -> Tuple[Optional[str], Optional[float]]:
    """
    Пытаемся сопоставить строку конкретному показателю и извлечь значение.
    """
    line_low = line.lower()

    for canonical, aliases in INDICATORS_MAP.items():
        for alias in aliases:
            if alias in line_low:
                # Нашли целевой показатель
                value = extract_value(line, canonical)
                return canonical, value

    return None, None


def extract_value(line: str, metric_name: str) -> Optional[float]:
    """
    Извлекаем число из строки, исправляем типичные OCR-ошибки (по whitelists),
    мягко нормализуем.
    """
    candidates = _parse_candidates(line)

    if not candidates:
        return None

    # если несколько кандидатов — берём первый разумный
    raw = candidates[0]

    # Фиксы под конкретные метрики (где часто пропадает точка)
    fixed = _smart_decimal_fix(raw, metric_name)

    # Нормализация единиц при явном контексте (очень мягкая)
    fixed = _unit_adjust_if_needed(fixed, line, metric_name)

    return fixed


def _parse_candidates(line: str) -> List[float]:
    """
    Находим все числа в строке и приводим к float:
    - '7,5' -> 7.5
    - '7 500' -> 7500
    - '7•5', '7·5' -> 7.5
    """
    # Уберём тонкие точки/межточки
    clean = line.replace("•", ".").replace("·", ".")
    # числа (включая десятичные)
    raw_nums = re.findall(r"(?<![\w])[-+]?\d[\d\s.,]*", clean)

    nums: List[float] = []
    for token in raw_nums:
        t = token.strip()

        # Если внутри есть пробелы — это либо разделители тысяч, либо мусор
        # Пробуем сначала вариант без пробелов
        t_no_space = t.replace(" ", "")

        # Приводим запятую к точке
        t_no_space = t_no_space.replace(",", ".")

        # Если несколько точек (как у 327.0.0) — оставим только первую
        parts = t_no_space.split(".")
        if len(parts) > 2:
            t_no_space = parts[0] + "." + "".join(parts[1:])

        try:
            val = float(t_no_space)
            nums.append(val)
        except Exception:
            # может быть «7 500» (без десятичной, но с пробелом как тысяча)
            t_only_digits = re.sub(r"[^\d-+]", "", t)
            if t_only_digits and t_only_digits.lstrip("+-").isdigit():
                try:
                    nums.append(float(t_only_digits))
                except Exception:
                    pass
            else:
                pass

    return nums


def _smart_decimal_fix(value: float, metric_name: str) -> float:
    """
    Если метрика в whitelist — пробуем аккуратно восстановить «пропавшую» точку,
    но только если число выглядит подозрительно большим (>= 100) для типичных диапазонов.
    """
    name = metric_name.strip()

    if name not in DECIMAL_FIX_WHITELIST:
        return value

    # Частые кейсы: 111 -> 11.1, 327 -> 32.7, 134 -> 13.4
    if 100 <= value < 1000:
        # 3 знака — ставим точку перед последней цифрой
        # 327 -> 32.7
        main = int(value)
        last = main % 10
        head = main // 10
        return float(f"{head}.{last}")

    # Иногда 1000+ (менее вероятно, но вдруг OCR)
    if 1000 <= value < 10000:
        # 1234 -> 123.4
        main = int(value)
        last = main % 10
        head = main // 10
        return float(f"{head}.{last}")

    return value


def _unit_adjust_if_needed(value: float, line: str, metric_name: str) -> float:
    """
    Базовая нормализация единиц (минималистично, чтобы не «перемудрить»).
    Примеры:
      - Гемоглобин в g/dL -> *10, если ожидаем г/л
    """
    low = line.lower()
    name = metric_name.lower()

    # Гемоглобин часто бывает в g/dL (норма 13–17 g/dL) ИЛИ г/л (130–170 г/л).
    # Если видим явное "g/dl" и значение похоже на 12–20 — переводим в г/л.
    if "g/dl" in low and ("гемоглобин" in name or "hemoglobin" in name or "hemoglobina" in name):
        if 8.0 <= value <= 25.0:
            return round(value * 10.0, 1)

    # Глюкоза иногда в mg/dL (70–99), а в ммоль/л — 3.9–5.5
    # Если видим mg/dL и значение 60–200 — переведём приблизительно в ммоль/л (делим на 18)
    if "mg/dl" in low and ("глюкоза" in name or "glucose" in name or "glucosa" in name):
        if 50 <= value <= 400:
            return round(value / 18.0, 2)

    # Остальное не трогаем (чтобы не ломать редкие кейсы)
    return value
