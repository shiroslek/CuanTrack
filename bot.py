#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cuan Track Bot - Main File
by Shiroslek
"""

import logging
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

def main():
    """Main function to run the bot"""
    
    # Initialize database
    db = Database()
    logger.info("Database initialized")
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Register callback query handler (for all inline keyboard buttons)
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Register message handler (for text input during flows)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message_input
    ))
    
    # Start bot
    logger.info(f"🚀 {BOT_NAME} is running...")
    print(f"🚀 {BOT_NAME} is running...")
    print("Press Ctrl+C to stop")
    
    # Run bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
