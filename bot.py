"""
Бот, который отвечает на сообщения в Telegram.
Сначала определяются несколько функций-обработчиков.
Затем эти функции передаются в приложение и регистрируются в соответствующих местах.
После этого бот запускается и работает до тех пор, пока вы не нажмете Ctrl-C в командной строке.

ИЗМЕНЕНИЯ:
1. Добавлен base_url / base_file_url для работы через Cloudflare Worker.
2. Адрес Worker берётся из переменной окружения WORKER_URL в .env.
3. Включена поддержка SOCKS/HTTP прокси (если понадобится) через TELEGRAM_PROXY_URL.
"""

import logging
from logging.handlers import RotatingFileHandler
import os

# Настройка логирования: файл + вывод в консоль
log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "bot.log")

file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)
stream_handler.setLevel(logging.INFO)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
# Удаляем возможные хендлеры, чтобы не дублировать вывод при повторном импорте
if root_logger.handlers:
    root_logger.handlers.clear()
root_logger.addHandler(file_handler)
root_logger.addHandler(stream_handler)

logger = logging.getLogger(__name__)

# Запрещаем propagate, чтобы сообщения не шли в root и не писались другими глобальными хендлерами
logger.propagate = False

# Отключаем детальные логи библиотеки httpcore
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

from telegram import ForceReply, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from chat_pipeline import run_pipeline

import dotenv

# Загружаем переменные окружения из файла .env
try:
    env = dotenv.dotenv_values(".env")
    TELEGRAM_BOT_TOKEN = env["TELEGRAM_BOT_TOKEN"]
except FileNotFoundError:
    raise FileNotFoundError(
        "Файл .env не найден. Убедитесь, что он существует в корневой директории проекта."
    )
except KeyError as e:
    raise KeyError(
        f"Переменная окружения {str(e)} не найдена в файле .env. Проверьте его содержимое."
    )

# --- Настройки работы через Cloudflare Worker и/или прокси -------------------
# WORKER_URL — адрес вашего Worker (например: https://tg.ваш-домен.com)
# Если он не задан, бот будет ходить напрямую в api.telegram.org (может не работать в РФ).
WORKER_URL = (env.get("WORKER_URL") or "").strip().rstrip("/")

# TELEGRAM_PROXY_URL — необязательный SOCKS5/HTTP прокси для запросов к Bot API.
# Пример: socks5://user:pass@host:port
TELEGRAM_PROXY_URL = (env.get("TELEGRAM_PROXY_URL") or "").strip() or None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start. При старте бота пользователь получает приветственное сообщение."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Основная функция для обработки текстовых сообщений от пользователя с целью ответа на них с помощью AI."""
    user_message = update.message.text
    user = update.effective_user.first_name
    user_message = f"{user_message}. Имя пользователя: {user}"

    # Получаем историю сообщений из context.chat_data
    history = context.chat_data.get("history", [])
    logger.debug(f"History: {history}")

    # Передаем текущий запрос и историю сообщений в llm_service
    llm_response = run_pipeline(user_message)
    context.chat_data["history"] = history  # сохраняем обновленную историю
    await update.message.reply_text(llm_response)


def build_application() -> Application:
    """Создаёт Application с учётом Worker URL и прокси."""
    builder = Application.builder().token(TELEGRAM_BOT_TOKEN)

    if WORKER_URL:
        # Все запросы к Bot API пойдут через наш Worker
        builder = builder.base_url(f"{WORKER_URL}/bot")
        builder = builder.base_file_url(f"{WORKER_URL}/file/bot")
        logger.info("Using Cloudflare Worker base URL: %s", WORKER_URL)
    else:
        logger.warning(
            "WORKER_URL не задан — бот будет обращаться напрямую к api.telegram.org. "
            "В РФ это, скорее всего, не сработает."
        )

    if TELEGRAM_PROXY_URL:
        # Если у вас есть SOCKS5/HTTP-прокси, можно дополнительно его указать.
        # Для SOCKS5 нужен пакет python-telegram-bot[socks].
        try:
            builder = builder.proxy(TELEGRAM_PROXY_URL).get_updates_proxy(
                TELEGRAM_PROXY_URL
            )
            logger.info("Using Telegram proxy: %s", TELEGRAM_PROXY_URL)
        except Exception as exc:
            logger.error("Не удалось настроить прокси %s: %s", TELEGRAM_PROXY_URL, exc)

    return builder.build()


def main() -> None:
    """Функция инициализации бот-приложения."""
    # Создание основного объекта приложения Telegram API
    application = build_application()

    # Обработчик всех текстовых сообщений без команды
    chat_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, chat)

    # Регистрируем обработчики:
    # Команда /start
    application.add_handler(CommandHandler("start", start))
    # Все остальные текстовые сообщения обрабатываются chat_handler
    application.add_handler(chat_handler)

    # Запуск бота в режиме постоянного ожидания команд.
    # Бот работает до прекращения программы (нажатие Ctrl-C или завершение по другому сигналу)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()