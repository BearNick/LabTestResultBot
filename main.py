# main.py
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv

from bot.handlers import register_handlers

# ────────────────────────────────────────────────────────────────────────────────
# Безопасные настройки логов: не печатаем контент апдейтов
# ────────────────────────────────────────────────────────────────────────────────
def setup_logging():
    # Подавим болтливость до WARNING (ошибки увидим, данные пользователей — нет)
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    # aiogram/aiogram.event/etc — тоже тише
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


async def main():
    setup_logging()

    # Загружаем .env и достаем токен безопасно
    load_dotenv()
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        # Не печатаем значение токена в лог — просто объясняем причину
        raise SystemExit("BOT_TOKEN is not set. Put it into .env (BOT_TOKEN=XXXXXXXX:YYYYYYYY).")

    # Сессия с мягкими таймаутами (чтобы не зависать)
    session = AiohttpSession(timeout=20)  # seconds

    # Инициализация бота и диспетчера
    bot = Bot(token=bot_token, session=session)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем хендлеры
    register_handlers(dp)

    # Перед запуском опроса: сбрасываем webhook и дропаем «хвост» апдейтов
    await bot.delete_webhook(drop_pending_updates=True)

    # Стартуем polling только по нужным апдейтам (меньше поверхностей для утечек/ошибок)
    allowed_updates = ["message", "callback_query", "edited_message"]

    await dp.start_polling(
        bot,
        allowed_updates=allowed_updates
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        # Тихий выход без трейсбека
        pass
