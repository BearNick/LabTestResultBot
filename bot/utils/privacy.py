import re

def anonymize_text(text: str) -> str:
    """
    Убирает или заменяет персональные данные (ФИО, даты рождения, номера полисов).
    Работает упрощённо — через регулярки.
    """
    if not text:
        return text

    # Удаляем ФИО в формате "Фамилия Имя Отчество" или 2 слова с заглавной
    text = re.sub(r"\b[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+( [А-ЯЁ][а-яё]+)?\b", "[REDACTED]", text)
    text = re.sub(r"\b[A-Z][a-z]+ [A-Z][a-z]+( [A-Z][a-z]+)?\b", "[REDACTED]", text)

    # Убираем даты рождения
    text = re.sub(r"\b\d{2}\.\d{2}\.\d{4}\b", "[REDACTED]", text)

    # Убираем номера полисов, паспортов (8–12 цифр подряд)
    text = re.sub(r"\b\d{8,12}\b", "[REDACTED]", text)

    return text
