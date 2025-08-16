import os
from dotenv import load_dotenv

# Загружаем .env один раз при импорте
load_dotenv()


def _get_env(
    key: str,
    default: str | None = None,
    required: bool = False,
    cast=None,
):
    """
    Универсальный геттер переменных окружения с:
    - required=True -> бросаем понятную ошибку, если нет значения
    - cast=float/int/bool/etc -> приводим тип (с безопасной обработкой)
    """
    val = os.getenv(key, default)
    if required and (val is None or val == ""):
        raise RuntimeError(f"Environment variable '{key}' is required but not set.")

    if cast and val is not None:
        try:
            if cast is bool:
                # Поддерживаем '1/0', 'true/false', 'yes/no'
                return str(val).strip().lower() in {"1", "true", "yes", "y"}
            return cast(val)
        except Exception as e:
            raise RuntimeError(f"Failed to cast env '{key}' to {cast}: {e}")

    return val


# ────────────────────────────────────────────────────────────────────────────────
# Базовые секреты
# ────────────────────────────────────────────────────────────────────────────────

BOT_TOKEN        = _get_env("BOT_TOKEN", required=True)
OPENAI_API_KEY   = _get_env("OPENAI_API_KEY", required=True)
OPENAI_MODEL     = _get_env("OPENAI_MODEL", "gpt-4o")  # можно поменять из .env

# ────────────────────────────────────────────────────────────────────────────────
# Приватность/операционные настройки
# ────────────────────────────────────────────────────────────────────────────────

# Хранить ли загруженные PDF на диске (False = в памяти; True = временно на диске и сразу удалять)
STORE_UPLOADS    = _get_env("STORE_UPLOADS", "0", cast=bool)  # по умолчанию НЕ храним

# Каталог для временных загрузок (используется только если STORE_UPLOADS=True)
UPLOAD_FOLDER    = _get_env("UPLOAD_FOLDER", "storage/uploads")

# Ограничение страниц, которые будем пытаться распознать (vision-парсер)
MAX_PDF_PAGES    = _get_env("MAX_PDF_PAGES", "5", cast=int)  # ← увеличено до 5

# Лог-уровень приложения (WARNING/ERROR/INFO)
LOG_LEVEL        = _get_env("LOG_LEVEL", "WARNING")

# Таймаут сетевых операций бота (сек) — для aiohttp-сессии
HTTP_TIMEOUT     = _get_env("HTTP_TIMEOUT", "20", cast=int)

# Какие типы апдейтов принимать (сужаем поверхность)
ALLOWED_UPDATES  = ["message", "callback_query", "edited_message"]

# ────────────────────────────────────────────────────────────────────────────────
# Крипто-оплата (CryptoBot)
# ────────────────────────────────────────────────────────────────────────────────

CRYPTO_PAY_TOKEN = _get_env("CRYPTO_PAY_TOKEN")  # можно оставить пустым — UI не упадёт
CRYPTO_ASSET     = _get_env("CRYPTO_ASSET", "USDT")
CRYPTO_PRICE     = _get_env("CRYPTO_PRICE", "9.99", cast=float)
CRYPTO_API_BASE  = "https://pay.crypt.bot/api"

# ────────────────────────────────────────────────────────────────────────────────
# DonationAlerts (RUB/USD/EUR) — для «доната»/поддержки
# ────────────────────────────────────────────────────────────────────────────────

DA_PAY_URL       = _get_env("DA_PAY_URL")  # может быть None — тогда кнопку не показываем
DA_PRICE_RUB     = _get_env("DA_PRICE_RUB", "999", cast=int)
DA_PRICE_USD     = _get_env("DA_PRICE_USD", "9.99", cast=float)
DA_PRICE_EUR     = _get_env("DA_PRICE_EUR", "9.99", cast=float)
