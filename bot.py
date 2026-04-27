#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cuan Track Bot - Main File
by Shiroslek
v2.3 - Graceful conflict handling + error handler
"""

import logging
import asyncio
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
    """Hapus webhook & pending updates sebelum polling."""
    try:
        url = (f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
               f"/deleteWebhook?drop_pending_updates=true")
        with urllib.request.urlopen(url, timeout=10) as resp:
            logger.info(f"deleteWebhook: {resp.read().decode()}")
    except Exception as e:
        logger.warning(f"deleteWebhook failed: {e}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler — tangani Conflict dan error lain."""
    err = context.error

    if isinstance(err, Conflict):
        logger.critical(
            "CONFLICT: instance lain masih berjalan. "
            "Bot akan berhenti dan Railway akan restart dengan bersih."
        )
        # Stop aplikasi agar Railway restart dengan satu instance bersih
        asyncio.create_task(context.application.stop())
        return

    if isinstance(err, (NetworkError, TimedOut)):
        logger.warning(f"Network error (akan retry otomatis): {err}")
        return

    # Log error lain tapi jangan crash
    logger.error(f"Unhandled error: {err}", exc_info=err)


def main():
    # 1. Bersihkan webhook & pending updates
    delete_webhook()

    # 2. Init database
    db = Database()
    logger.info("Database initialized")

    # 3. Build application dengan timeout yang lebih longgar
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )

    # 4. Register error handler
    application.add_error_handler(error_handler)

    # 5. Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message_input
    ))

    logger.info(f"🚀 {BOT_NAME} is running...")
    print(f"🚀 {BOT_NAME} is running...")

    # 6. Run polling
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        stop_signals=None,
        # Retry otomatis jika network error
        close_loop=False
    )


if __name__ == '__main__':
    main()
