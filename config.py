#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration file for Cuan Track Bot
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
DB_NAME = "finbot.db"

# Currency symbol
CURRENCY_SYMBOL = "Rp"

# ============================================================================
# DEFAULT CATEGORIES
# ============================================================================

DEFAULT_INCOME_CATEGORIES = [
    {"name": "Saldo Awal", "icon": "💰"},
    {"name": "Freelance", "icon": "💻"},
    {"name": "Joki", "icon": "🎮"},
    {"name": "Withdraw", "icon": "🏦"},
    {"name": "Dana Tambahan", "icon": "💵"},
    {"name": "Lainnya", "icon": "📌"}
]

DEFAULT_EXPENSE_CATEGORIES = [
    {"name": "Makanan", "icon": "🍔"},
    {"name": "Rokok/Vape", "icon": "🚬"},
    {"name": "Transportasi", "icon": "🚗"},
    {"name": "Nongkrong", "icon": "☕"},
    {"name": "Skincare/Suplemen", "icon": "💊"},
    {"name": "Tagihan", "icon": "📱"},
    {"name": "Tempat Tinggal", "icon": "🏠"},
    {"name": "Investasi", "icon": "📈"},
    {"name": "Kendaraan", "icon": "🏍️"},
    {"name": "Piutang", "icon": "💸"},
    {"name": "Hiburan", "icon": "🎬"},
    {"name": "Alokasi Khusus", "icon": "🎯"},
    {"name": "Lainnya", "icon": "📌"}
]

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
    "❤️", "🎁", "🎉", "🎊", "⭐", "✨", "🔥", "💡"
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
