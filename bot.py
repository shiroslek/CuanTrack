#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cuan Track Bot - Main File
by Shiroslek
"""

import logging
import urllib.request
from telegram import Update
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

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def delete_webhook():
    """Hapus webhook aktif sebelum mulai polling — mencegah Conflict error."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook?drop_pending_updates=true"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = resp.read().decode()
            logger.info(f"✅ deleteWebhook: {data}")
    except Exception as e:
        logger.warning(f"⚠️ Could not delete webhook: {e}")


def main():
    """Main function to run the bot"""

    # Hapus webhook dulu sebelum polling
    delete_webhook()

    # Initialize database
    db = Database()
    logger.info("Database initialized")

    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Register callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Register message handler
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message_input
    ))

    # Start bot
    logger.info(f"🚀 {BOT_NAME} is running...")
    print(f"🚀 {BOT_NAME} is running...")
    print("Press Ctrl+C to stop")

    # Run polling
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        stop_signals=None
    )


if __name__ == '__main__':
    main()
