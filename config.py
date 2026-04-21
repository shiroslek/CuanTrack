#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration file for Cuan Track Bot
v2.1 - Updated categories
"""

import os
import pytz

# ============================================================================
# BOT CONFIGURATION
# ============================================================================

# Telegram Bot Token (get from @BotFather)
TELEGRAM_BOT_TOKEN = "8482730888:AAHb0Mm4ZJM-YqGeJYDn9nHM3aaI5vNN9_I"

# Bot Name
BOT_NAME = "Cuan Track by Shiroslek"

# Timezone
TIMEZONE = pytz.timezone('Asia/Jakarta')

# Database
DB_NAME = "/app/data/finbot.db"

# Currency symbol
CURRENCY_SYMBOL = "Rp"

# ============================================================================
# DEFAULT CATEGORIES - UPDATED V2.1
# ============================================================================

DEFAULT_INCOME_CATEGORIES = [
    {"name": "Starting Balance", "icon": "💰"},
    {"name": "Gaji", "icon": "💵"},
    {"name": "Freelance", "icon": "💻"},
    {"name": "Withdraw", "icon": "🏦"},
    {"name": "Piutang", "icon": "💸"},
    {"name": "Lainnya", "icon": "📌"}
]

DEFAULT_EXPENSE_CATEGORIES = [
    {"name": "Belanja", "icon": "🛒"},
    {"name": "Nongkrong", "icon": "☕"},
    {"name": "Kesehatan", "icon": "💊"},
    {"name": "Tempat Tinggal", "icon": "🏠"},
    {"name": "Makan & Minum", "icon": "🍔"},
    {"name": "Transportasi", "icon": "🚗"},
    {"name": "Tagihan Rutin", "icon": "📱"},
    {"name": "Investasi", "icon": "📈"},
    {"name": "Utang", "icon": "💳"},
    {"name": "Lainnya", "icon": "📌"}
]

# ============================================================================
# PLACEHOLDER TEXT - UPDATED V2.1
# ============================================================================

INCOME_EXAMPLE_TEXT = "Gaji bulanan, Jual Biawak, Profit Trading, dll"
EXPENSE_EXAMPLE_TEXT = "Beli geprek, Beli Ginjal, Hilang Di curi"

# ============================================================================
# EMOJI LIST FOR CATEGORY SELECTION
# ============================================================================

EMOJI_LIST = [
    "💰", "💵", "💴", "💶", "💷", "💳", "💸", "🏦",
    "🍔", "🍕", "🍜", "🍱", "☕", "🍺", "🥤", "🧃",
    "🚗", "🚕", "🚙", "🚌", "🏍️", "🚲", "✈️", "🚢",
    "🏠", "🏢", "🏪", "🏥", "🎓", "📚", "✏️", "📝",
    "🎮", "🎬", "🎵", "🎨", "⚽", "🏀", "🎾", "🎯",
    "💻", "📱", "⌚", "📷", "🎧", "🖥️", "⌨️", "🖱️",
    "👕", "👔", "👗", "👠", "👟", "🎒", "👜", "💄",
    "💊", "🩺", "💉", "🏥", "🧴", "🧼", "🧽", "🧹",
    "📊", "📈", "📉", "💹", "📌", "📍", "🎯", "✅",
    "❤️", "🎁", "🎉", "🎊", "⭐", "✨", "🔥", "💡",
    "🛒", "🛍️", "🏪", "🏬", "🍽️", "🥘", "🍲", "🥗"
]

# ============================================================================
# EXPORT SETTINGS
# ============================================================================

# Export directories
EXPORT_DIR = "exports"
CHART_DIR = "charts"

# Create directories if not exist
os.makedirs(EXPORT_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)

# ============================================================================
# LOGGING
# ============================================================================

LOG_LEVEL = "INFO"
LOG_FILE = "bot.log"
