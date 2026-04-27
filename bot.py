#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cuan Track Bot - Main File
by Shiroslek
"""

import logging
import urllib.request
from telegram import Update
from telegram.error import Conflict, NetworkError, TimedOut
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from config import TELEGRAM_BOT_TOKEN, BOT_NAME
from database import Database
from handlers import (
    start_command,
    help_command,
    handle_message_input,
    handle_callback
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def delete_webhook():
    try:
        url = (f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
               f"/deleteWebhook?drop_pending_updates=true")
        with urllib.request.urlopen(url, timeout=10) as resp:
            logger.info(f"deleteWebhook: {resp.read().decode()}")
    except Exception as e:
        logger.warning(f"deleteWebhook failed: {e}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """
    Global error handler.
    Conflict dibiarkan — PTB sudah retry otomatis, jangan stop app.
    """
    err = context.error

    if isinstance(err, Conflict):
        # Log saja, PTB akan retry sendiri setelah beberapa detik
        logger.warning("Conflict: another instance briefly active. Will auto-retry.")
        return

    if isinstance(err, (NetworkError, TimedOut)):
        logger.warning(f"Network issue (auto-retry): {err}")
        return

    logger.error(f"Unhandled error: {err}", exc_info=err)


def main():
    delete_webhook()

    db = Database()
    logger.info("Database initialized")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_error_handler(error_handler)

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message_input
    ))

    logger.info(f"🚀 {BOT_NAME} is running...")
    print(f"🚀 {BOT_NAME} is running...")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        stop_signals=None
    )


if __name__ == '__main__':
    main()
