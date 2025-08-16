import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY не найден. Проверь .env")

client = OpenAI(api_key=OPENAI_API_KEY)


def generate_interpretation(lab_data):
    prompt = build_prompt(lab_data)

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
    )

    return response.choices[0].message.content.strip()


def build_prompt(lab_data: dict) -> str:
    lang = lab_data.get("language", "ru")
    age = lab_data.get("age", "неизвестен")
    gender = lab_data.get("gender", "неизвестен").capitalize()

    lab_values = {k: v for k, v in lab_data.items() if k not in ["language", "age", "gender"]}

    if lang == "en":
        prompt = (
            "You are a professional physician, nutritionist, and sports advisor. "
            "A patient has submitted their lab test results. "
            f"The patient is {age} years old and identifies as {gender}.\n\n"
            "Your task is to interpret the results professionally and briefly, providing personal recommendations.\n\n"
            "Response requirements:\n"
            "1. Before interpreting, **check each value against standard medical reference ranges**, considering the patient's age and gender.\n"
            "2. Highlight abnormalities and **analyze them in context**, not in isolation.\n"
            "3. Compare values with trusted sources (Mayo Clinic, UpToDate, LabTestsOnline).\n"
            "4. Avoid saying 'everything is normal' for borderline results. Instead, say 'upper limit of normal' or 'slightly reduced within range'.\n"
            "5. Draw conclusions about possible systemic issues (e.g. liver function, metabolism, inflammation).\n"
            "6. Support conclusions with **evidence-based medical reasoning**.\n"
            "7. Provide **specific recommendations** for diet, supplements, or vitamins, with brief justification.\n"
            "8. Suggest which tests should be repeated or added.\n"
            "9. Be concise: no more than 6–7 paragraphs. Avoid generic advice or vague language.\n"
            "10. Don't repeat normal values — focus only on deviations and important relationships.\n\n"
            "📊 Lab results provided by the patient:\n"
        )

    elif lang == "es":
        prompt = (
            "Eres un médico profesional, nutricionista y asesor deportivo. "
            "Un paciente ha enviado sus resultados de análisis de laboratorio. "
            f"El paciente tiene {age} años y su género es {gender}.\n\n"
            "Tu tarea es interpretar los resultados de manera profesional y concisa, brindando recomendaciones personalizadas.\n\n"
            "Requisitos para la respuesta:\n"
            "1. Antes de interpretar, **verifica cada valor con los rangos de referencia médicos**, considerando la edad y el género del paciente.\n"
            "2. Destaca las anomalías y **analízalas en conjunto**, no por separado.\n"
            "3. Compara los valores con fuentes confiables (Mayo Clinic, UpToDate, LabTestsOnline).\n"
            "4. Evita decir 'todo está normal' si los valores están en el límite. Di mejor: 'en el límite superior de lo normal' o 'ligeramente bajo dentro del rango'.\n"
            "5. Haz conclusiones sobre posibles disfunciones sistémicas (hígado, metabolismo, inflamación, etc.).\n"
            "6. Sustenta tus conclusiones con **argumentos médicos actuales y confiables**.\n"
            "7. Proporciona **recomendaciones específicas** sobre dieta, vitaminas o suplementos, con una breve justificación.\n"
            "8. Indica qué análisis se deben repetir o agregar.\n"
            "9. Sé conciso: no más de 6–7 párrafos. Evita frases genéricas o consejos vagos.\n"
            "10. No repitas valores normales: céntrate en las desviaciones y relaciones clave.\n\n"
            "📊 Resultados proporcionados por el paciente:\n"
        )

    else:  # Russian by default
        prompt = (
            "Ты — профессиональный врач-терапевт, нутрициолог и спортивный консультант. "
            f"Пациенту {age} лет, пол — {gender}.\n\n"
            "Пациент прислал тебе результаты лабораторных анализов. "
            "Твоя задача — кратко, но профессионально интерпретировать их и дать персональные рекомендации.\n\n"
            "Требования к ответу:\n"
            "1. Перед интерпретацией **выполни проверку каждого показателя на соответствие медицинским нормам**, учитывая возраст и пол пациента.\n"
            "2. Выдели отклонения от нормы и **проанализируй их в комплексе**, а не по отдельности.\n"
            "3. Сравни значения с актуальными справочниками (Mayo Clinic, UpToDate, LabTestsOnline).\n"
            "4. Не пиши «всё в норме», если показатель пограничный. Лучше обозначь как «на верхней границе нормы» или «сниженный в пределах допустимого».\n"
            "5. Сделай выводы о возможных системных нарушениях (печень, обмен веществ, воспаления и т.д.).\n"
            "6. Подкрепи выводы **аргументами**, основанными на актуальных медицинских данных.\n"
            "7. Дай **конкретные рекомендации** по питанию, витаминам и БАДам с кратким обоснованием.\n"
            "8. Укажи, **какие анализы стоит пересдать или дополнительно сдать**.\n"
            "9. Будь краток: не больше 6–7 абзацев. Не пиши шаблонные советы. Не используй фразы типа 'дай знать' или 'обратись ко мне'.\n"
            "10. Не повторяй нормальные показатели, только отклонения и значимые взаимосвязи.\n\n"
            "📊 Вот значения, которые прислал пациент:\n"
        )

    for name, value in lab_values.items():
        prompt += f"- {name}: {value}\n"

    prompt += "\nОтвет:\n" if lang == "ru" else "\nResponse:\n"

    return prompt
