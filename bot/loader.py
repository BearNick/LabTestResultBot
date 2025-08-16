# loader.py
from __future__ import annotations

import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Загружаем переменные окружения из файла .env (если он есть рядом с проектом)
# Значения из ОС не перезаписываем.
load_dotenv(override=False)

# Читаем токен бота из окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    # Остановим приложение с понятной ошибкой, если токен не задан.
    # Создай файл .env и добавь строку: BOT_TOKEN=123:ABC
    raise RuntimeError(
        "BOT_TOKEN is not set. Create a .env file with 'BOT_TOKEN=<your_telegram_bot_token>'"
    )

# Инициализируем Bot/Dispatcher
bot = Bot(token=BOT_TOKEN)

# Хранилище FSM в памяти (для продакшена можно заменить на Redis)
storage = MemoryStorage()

# aiogram 3.x:
# Dispatcher не принимает bot в конструктор — bot передаётся в start_polling(...)
dp = Dispatcher(storage=storage)

# --- Если у тебя aiogram 2.x, раскомментируй строку ниже и удали dp = Dispatcher(storage=storage) выше ---
# from aiogram import Dispatcher as DispatcherV2  # noqa
# dp = DispatcherV2(bot, storage=storage)