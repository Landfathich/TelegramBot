import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Бот Kodama работает!")


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "Не задана переменная окружения TELEGRAM_BOT_TOKEN"
        )

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))

    print("Telegram-бот запущен.")
    application.run_polling()


if __name__ == "__main__":
    main()