# parser/vision_extract.py
from __future__ import annotations

import base64
import io
import json
import os
from typing import Dict, Any, List, Optional

# ── Рендер PDF → PNG: сначала PyMuPDF, затем pdf2image+Pillow как фолбэк ──
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from pdf2image import convert_from_path  # требует poppler в системе
except Exception:
    convert_from_path = None

try:
    from PIL import Image as PILImage
except Exception:
    PILImage = None

from openai import OpenAI

from bot.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,      # базовая модель из .env (используется как запасной вариант)
    MAX_PDF_PAGES,     # лимит страниц для vision-парсинга
)

# Модель для vision: берём из ENV OPENAI_MODEL_VISION, иначе из OPENAI_MODEL, иначе 'gpt-4o-mini'
OPENAI_MODEL_VISION = os.getenv("OPENAI_MODEL_VISION") or OPENAI_MODEL or "gpt-4o-mini"

# Нормализация чисел (DRY): подтягиваем из текстового парсера
try:
    from parser.extract_pdf import convert_value_safely
except Exception:
    # Минимальная заглушка, если по каким-то причинам импорт не удался
    def convert_value_safely(name: str, raw_val: str | float | int | None) -> Optional[float]:
        try:
            if raw_val is None:
                return None
            if isinstance(raw_val, (int, float)):
                return float(raw_val)
            s = str(raw_val).strip().replace(",", ".")
            # Специальный кейс для ANA: если пришло "1:160", вернём 160
            if name == "ANA" and ":" in s:
                parts = s.split(":")
                tail = parts[-1].strip()
                if tail.isdigit():
                    return float(tail)
            tmp = "".join(ch for ch in s if (ch.isdigit() or ch in ".-"))
            return float(tmp) if tmp else None
        except Exception:
            return None

# Канонические КЛЮЧИ (русские) — их понимают translations и интерпретатор
CANON_KEYS: List[str] = [
    # Биохимия — ферменты и белки
    "ALT","AST","ГГТ","АЛП","ЛДГ","Амилаза","Липаза",
    "Общий белок","Альбумин","Глобулин","Соотношение А/Г",
    "Билирубин общий","Билирубин прямой","Билирубин непрямой",

    # Биохимия — липиды/углеводы
    "Глюкоза","Инсулин","HOMA-IR",
    "Холестерин общий","ЛПВП","ЛПНП","ЛПОНП","Не-ЛПВП","Триглицериды",

    # Биохимия — электролиты/минералы/почечные
    "Натрий","Калий","Хлор","Кальций","Магний","Фосфор",
    "Железо","Ферритин","TIBC","Трансферрин","Насыщение трансферрина %",
    "Мочевина","Креатинин","Кислота мочевая","eGFR","С-реактивный белок",

    # ОАК — основные
    "Гемоглобин","Гематокрит","Эритроциты","Лейкоциты","Тромбоциты","СОЭ",

    # Эритроцитарные индексы
    "MCV","MCH","MCHC","RDW",

    # Дифференциал (%)
    "Нейтрофилы %","Лимфоциты %","Моноциты %","Эозинофилы %","Базофилы %",

    # Дифференциал (абс.)
    "Нейтрофилы абс.","Лимфоциты абс.","Моноциты абс.","Эозинофилы абс.","Базофилы абс.",

    # Индексы тромбоцитов
    "MPV","PDW","PCT",

    # Витамины/гормоны щитовидки и др.
    "Витамин D (25-OH)","Витамин B12","Фолиевая кислота","ТСГ","ТТГ","СвТ4","СвТ3",
    "КФК","КФК-МВ",

    # --- Антитела / иммуноглобулины ---
    "IgA","IgG","IgM","IgE","IgD",
    "anti-TPO","anti-TG","ANA",
]

PERCENT_KEYS = {"Нейтрофилы %","Лимфоциты %","Моноциты %","Эозинофилы %","Базофилы %"}

# Системный промпт с единицами и конверсиями
SYSTEM_PROMPT = (
    "You are a medical lab report extractor. You will see 1–5 images of a lab report "
    "(CBC and/or biochemistry). Extract ONLY the patient's RESULT values (numeric) into "
    "a strict JSON object with EXACT Russian keys from the provided list. "
    "Do not include units or comments. If a value is missing, set it to null. "
    "Use the following STANDARD UNITS and convert if needed:\n"
    "- Гемоглобин: g/L (if g/dL, multiply by 10)\n"
    "- Гематокрит: % (0–100)\n"
    "- Эритроциты (RBC): x10^12/L\n"
    "- Лейкоциты (WBC): x10^9/L\n"
    "- Тромбоциты: x10^9/L\n"
    "- СОЭ: mm/h\n"
    "- MCV: fL; MCH: pg; MCHC: g/L (if g/dL, multiply by 10)\n"
    "- Differential % remain 0..100%; absolute counts in x10^9/L\n"
    "- ALT/AST/GGT/ALP/LDH/Amylase/Lipase/CK/CK-MB: U/L\n"
    "- Общий белок/Альбумин/Глобулин: g/L (if g/dL, ×10)\n"
    "- Билирубин общий/прямой/непрямой: µmol/L (if mg/dL, ×17.104)\n"
    "- Глюкоза: mmol/L (if mg/dL, ÷18)\n"
    "- Инсулин: µIU/mL\n"
    "- Холестерин/ЛПВП/ЛПНП/ЛПОНП/Не-ЛПВП: mmol/L (if mg/dL, ×0.0259)\n"
    "- Триглицериды: mmol/L (if mg/dL, ×0.01129)\n"
    "- Натрий/Калий/Хлор: mmol/L\n"
    "- Кальций: mmol/L (if mg/dL, ×0.2495)\n"
    "- Магний: mmol/L (if mg/dL, ×0.4114)\n"
    "- Фосфор: mmol/L (if mg/dL, ×0.3229)\n"
    "- Железо: µmol/L (if µg/dL, ×0.179)\n"
    "- Мочевина: mmol/L (if mg/dL, ×0.1665)\n"
    "- Креатинин: µmol/L (if mg/dL, ×88.4)\n"
    "- Мочевая кислота: µmol/L (if mg/dL, ×59.48)\n"
    "- Ферритин: ng/mL; CRP: mg/L; eGFR: mL/min/1.73m2\n"
    "- ТТГ/СвТ4/СвТ3: mIU/L, pmol/L, pmol/L (convert if required)\n"
    "- Витамин D (25-OH): ng/mL (if nmol/L, ×0.4)\n"
    "- IgG/IgA/IgM: g/L (if mg/dL, ×0.01)\n"
    "- IgE: IU/mL (if kU/L, the numeric value is the same; if IU/L, ÷1000)\n"
    "- IgD: g/L (if mg/L, ÷1000)\n"
    "- anti-TPO / anti-TG: IU/mL (if U/mL treat as IU/mL; if IU/L, ÷1000)\n"
    "- ANA (titer): if reported like '1:160', return 160; if 'negative', return 0; "
    "if only 'positive' without numeric titer, return null.\n"
    "Sanity-check: percentages must be 0..100; discard impossible values by using null. "
    "Return ONLY a JSON object with keys EXACTLY from the list. No prose."
)


def _img_to_data_url(pil_img) -> str:
    """PIL.Image -> data URL (base64 PNG)"""
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def _user_content() -> List[Dict[str, Any]]:
    """Текстовый кусок user-сообщения с перечислением допустимых ключей"""
    keys_text = "Ключи: " + ", ".join(CANON_KEYS)
    return [{"type": "text", "text": f"Верни JSON строго по этим ключам. {keys_text}"}]


def _render_pdf_to_images(pdf_path: str, max_pages: int) -> List:
    """
    Пытаемся рендерить PDF:
      1) PyMuPDF (быстрее, без системных зависимостей)
      2) pdf2image+Pillow (нужно poppler в системе)
    Возвращаем список PIL.Image.
    """
    images = []

    # 1) PyMuPDF
    if fitz is not None:
        doc = None
        try:
            doc = fitz.open(pdf_path)
            pages_to_read = min(len(doc), max_pages)
            # Немного увеличим масштаб, чтобы повысить читаемость OCR/LLM
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            for i in range(pages_to_read):
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                # Pillow обязателен здесь; предполагается, что он установлен (см. requirements.txt)
                from PIL import Image as _PILImage
                pil_img = _PILImage.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                images.append(pil_img)
            if images:
                return images
        except Exception:
            images = []
        finally:
            try:
                if doc is not None:
                    doc.close()
            except Exception:
                pass

    # 2) pdf2image
    if convert_from_path is not None:
        try:
            imgs = convert_from_path(pdf_path, dpi=200)
            if imgs:
                return imgs[:max_pages]
        except Exception:
            return []

    return []


def extract_lab_data_via_vision(
    pdf_path: str,
    max_pages: Optional[int] = None,
    lang: str = "ru",
) -> Dict[str, Optional[float]]:
    """
    PDF → изображения → Vision LLM → строгий JSON → нормализация чисел.
    Возвращает словарь {канонический_ключ: float|None}
    """
    if not OPENAI_API_KEY:
        return {}

    if max_pages is None:
        max_pages = MAX_PDF_PAGES

    pil_images = _render_pdf_to_images(pdf_path, max_pages=max_pages)
    if not pil_images:
        return {}

    # Формируем контент: текст + картинки
    user_content = _user_content()
    for img in pil_images:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": _img_to_data_url(img)}
        })

    client = OpenAI(api_key=OPENAI_API_KEY)

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL_VISION,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ]
        )
        raw = resp.choices[0].message.content or "{}"
    except Exception:
        return {}

    # Парсим JSON и аккуратно приводим значения
    try:
        data = json.loads(raw)
    except Exception:
        # На всякий случай попробуем вырезать JSON из текста
        first = raw.find("{")
        last = raw.rfind("}")
        if first != -1 and last > first:
            try:
                data = json.loads(raw[first:last + 1])
            except Exception:
                data = {}
        else:
            data = {}

    out: Dict[str, Optional[float]] = {}
    for key in CANON_KEYS:
        val = data.get(key)
        num = convert_value_safely(key, val)
        # Доп. sanity-check для процентов
        if key in PERCENT_KEYS and (num is not None) and not (0 <= num <= 100):
            num = None
        out[key] = num

    return out