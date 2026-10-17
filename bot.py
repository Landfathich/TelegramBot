
import asyncio
import logging
import os

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    if not context.args:
        await update.message.reply_text(
            "Чтобы привязать Telegram к Kodama, откройте "
            "персональную ссылку из CRM."
        )
        return

    token = context.args[0]
    chat = update.effective_chat
    user = update.effective_user

    if not chat or not user:
        return

    api_url = os.getenv("CRM_TELEGRAM_LINK_API")
    api_secret = os.getenv("TELEGRAM_INTERNAL_API_SECRET")

    if not api_url or not api_secret:
        await update.message.reply_text(
            "Не удалось подключиться к CRM. Попробуйте позже."
        )
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                api_url,
                json={
                    "token": token,
                    "chat_id": chat.id,
                    "username": user.username or "",
                },
                headers={"X-Internal-Secret": api_secret},
            )
    except httpx.HTTPError:
        logger.exception("Ошибка подключения к CRM API")
        await update.message.reply_text(
            "Не удалось подключиться к CRM. Попробуйте позже."
        )
        return

    if response.status_code == 200:
        await update.message.reply_text(
            "Telegram успешно привязан к вашему аккаунту Kodama."
        )
    elif response.status_code == 404:
        await update.message.reply_text(
            "Ссылка недействительна. Получите новую ссылку в CRM."
        )
    else:
        logger.error("CRM API вернул статус %s", response.status_code)
        await update.message.reply_text(
            "Не удалось привязать Telegram. Попробуйте позже."
        )


async def process_outbox(application: Application) -> None:
    api_url = os.getenv("CRM_TELEGRAM_LINK_API", "")
    api_secret = os.getenv("TELEGRAM_INTERNAL_API_SECRET", "")

    if not api_url or not api_secret:
        logger.error("Не настроено подключение к CRM API")
        return

    outbox_url = api_url.rsplit("/", 2)[0] + "/outbox/"
    headers = {"X-Internal-Secret": api_secret}

    async with httpx.AsyncClient(timeout=15) as client:
        while True:
            try:
                response = await client.get(outbox_url, headers=headers)
                response.raise_for_status()
                messages = response.json().get("messages", [])

                for message in messages:
                    message_id = message["id"]
                    success = False
                    error = ""

                    try:
                        await application.bot.send_message(
                            chat_id=message["chat_id"],
                            text=message["text"],
                        )
                        success = True
                    except Exception as exc:
                        error = str(exc)[:1000]
                        logger.warning(
                            "Не удалось отправить сообщение %s: %s",
                            message_id,
                            error,
                        )

                    result_url = f"{outbox_url}{message_id}/result/"
                    try:
                        result = await client.post(
                            result_url,
                            headers=headers,
                            json={"success": success, "error": error},
                        )
                        result.raise_for_status()
                    except httpx.HTTPError:
                        logger.exception(
                            "Не удалось сохранить результат сообщения %s",
                            message_id,
                        )

            except (httpx.HTTPError, ValueError, KeyError) as exc:
                logger.warning("Ошибка обработки очереди CRM: %s", exc)

            await asyncio.sleep(5)


async def post_init(application: Application) -> None:
    application.create_task(process_outbox(application))


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        raise RuntimeError("Не задана переменная TELEGRAM_BOT_TOKEN")

    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )
    application.add_handler(CommandHandler("start", start))

    logger.info("Telegram-бот запущен")
    application.run_polling()


if __name__ == "__main__":
    main()
