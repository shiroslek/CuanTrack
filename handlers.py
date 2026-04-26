#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cuan Track Bot - Command Handlers
v2.6 - Fixed multi-user signatures (database.py v2.2)
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest
import calendar

from config import TIMEZONE, BOT_NAME, EMOJI_LIST
from database import Database
from parser import NumberParser
from calculator import Calculator
from report_generator import ReportGenerator
from chart_generator import ChartGenerator

logger = logging.getLogger(__name__)

try:
    from config import INCOME_EXAMPLE_TEXT
except ImportError:
    INCOME_EXAMPLE_TEXT = "Gaji bulanan, Profit Trading, dll"

try:
    from config import EXPENSE_EXAMPLE_TEXT
except ImportError:
    EXPENSE_EXAMPLE_TEXT = "Beli geprek, Bayar listrik, dll"

db = Database()
calc = Calculator(db)
parser = NumberParser()
report_gen = ReportGenerator(db)
chart_gen = ChartGenerator(db)


# ==================== UTILITY ====================

def format_rupiah(amount):
    return parser.format_rupiah(amount)

def get_today():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d")

def get_now_time():
    return datetime.now(TIMEZONE).strftime("%H:%M:%S")

def get_home_button():
    return InlineKeyboardButton("🏠 Dashboard", callback_data="back_to_main")

def get_back_and_dashboard(back_callback: str, back_label: str = "« Kembali"):
    return [
        InlineKeyboardButton(back_label, callback_data=back_callback),
        get_home_button()
    ]

def get_main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Catat Pemasukan", callback_data="menu_income"),
            InlineKeyboardButton("💸 Catat Pengeluaran", callback_data="menu_expense")
        ],
        [
            InlineKeyboardButton("📊 Laporan", callback_data="menu_laporan"),
            InlineKeyboardButton("💳 Saldo", callback_data="menu_saldo")
        ],
        [
            InlineKeyboardButton("📝 Ringkasan", callback_data="menu_ringkasan"),
            InlineKeyboardButton("📓 Notes", callback_data="menu_notes")
        ],
        [
            InlineKeyboardButton("✏️ Edit Transaksi", callback_data="menu_edit"),
            InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")
        ],
        [
            InlineKeyboardButton("⚠️ Reset Data", callback_data="menu_reset_data")
        ]
    ])


async def safe_edit(query, text, reply_markup=None, parse_mode='Markdown'):
    """Edit pesan; fallback kirim baru jika gagal."""
    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        try:
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            logger.error(f"safe_edit total failure: {e}")


async def send_error(query, err: Exception):
    logger.error(f"Handler error: {err}", exc_info=True)
    try:
        await query.message.reply_text(
            f"❌ Error: `{type(err).__name__}: {err}`\n\nKetuk Dashboard untuk kembali.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[get_home_button()]])
        )
    except Exception as e:
        logger.error(f"send_error failed: {e}")


# ==================== START & HELP ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    try:
        # set_setting(user_id, key, value)
        db.set_setting(user_id, 'first_seen', datetime.now(TIMEZONE).strftime("%Y-%m-%d"))
    except Exception as e:
        logger.warning(f"set_setting failed: {e}")

    await update.message.reply_text(
        f"🎉 *Selamat Datang di {BOT_NAME}!*\n\nHalo {user.first_name}! 👋\n\nSilakan pilih menu di bawah:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📚 *PANDUAN {BOT_NAME}*\n\n"
        "*💰 Catat Pemasukan/Pengeluaran:*\n"
        "1. Pilih kategori\n"
        "2. Masukkan keterangan\n"
        "3. Masukkan nominal: 50.000 atau 1.500.000\n\n"
        "*📊 Laporan:* Laporan lengkap + grafik\n"
        "*💳 Saldo:* Cek saldo saat ini\n"
        "*📝 Ringkasan:* Summary harian\n"
        "*📓 Notes:* Catatan penting\n"
        "*✏️ Edit Transaksi:* Koreksi transaksi lama\n"
        "*⚙️ Settings:* Kelola kategori\n\n"
        "Ketuk 🏠 Dashboard untuk kembali ke menu kapan saja.",
        parse_mode='Markdown'
    )


# ==================== INCOME / EXPENSE ====================

async def show_category_grid(query, user_id, trans_type: str):
    # get_categories(trans_type) — kategori global, tidak perlu user_id
    categories = db.get_categories(trans_type)

    if not categories:
        await safe_edit(query, f"❌ Belum ada kategori {trans_type}. Tambahkan di Settings.",
                        reply_markup=InlineKeyboardMarkup([[get_home_button()]]))
        return

    keyboard = []
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(
            f"{cat['icon']} {cat['name']}",
            callback_data=f"cat_{trans_type}_{cat['name']}"
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append(get_back_and_dashboard("back_to_main"))

    icon = "💰" if trans_type == "income" else "💸"
    trans_name = "Pemasukan" if trans_type == "income" else "Pengeluaran"
    await safe_edit(query, f"{icon} *CATAT {trans_name.upper()}*\n\nPilih kategori:",
                    reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_category_selected(query, context, user_id, trans_type: str, category: str):
    context.user_data['pending_transaction'] = {
        'type': trans_type,
        'category': category,
        'step': 'waiting_description',
        'user_id': user_id
    }
    # get_category_by_name(name) — tidak perlu user_id
    cat_info = db.get_category_by_name(category)
    icon = cat_info['icon'] if cat_info else "📌"
    example = INCOME_EXAMPLE_TEXT if trans_type == 'income' else EXPENSE_EXAMPLE_TEXT
    await safe_edit(query, f"{icon} *{category}*\n\nMasukkan keterangan:\n(Contoh: {example})")


async def handle_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    if 'pending_transaction' not in context.user_data:
        await update.message.reply_text(
            "Gunakan /start atau ketuk 🏠 Dashboard untuk membuka menu.",
            reply_markup=InlineKeyboardMarkup([[get_home_button()]])
        )
        return

    pending = context.user_data['pending_transaction']
    step = pending.get('step')
    uid = pending.get('user_id', user_id)

    if step == 'waiting_description':
        pending['description'] = text
        pending['step'] = 'waiting_amount'
        context.user_data['pending_transaction'] = pending
        await update.message.reply_text(
            f"✅ Keterangan: *{text}*\n\nMasukkan nominal (gunakan titik):\nContoh: 50.000",
            parse_mode='Markdown'
        )

    elif step == 'waiting_amount':
        is_valid, error_msg = parser.validate_amount_format(text)
        if not is_valid:
            await update.message.reply_text(f"❌ {error_msg}\n\nCoba lagi:")
            return

        amount = parser.parse_amount(text)
        # add_transaction(user_id, date, time, trans_type, category, amount, description)
        db.add_transaction(uid, get_today(), get_now_time(),
                           pending['type'], pending['category'],
                           amount, pending['description'])
        # get_saldo_info(user_id)
        saldo_info = calc.get_saldo_info(uid)

        trans_name = "Pemasukan" if pending['type'] == 'income' else "Pengeluaran"
        icon = "💰" if pending['type'] == 'income' else "💸"
        menu_back = "menu_income" if pending['type'] == 'income' else "menu_expense"
        del context.user_data['pending_transaction']

        await update.message.reply_text(
            f"✅ *{trans_name} Tercatat!*\n\n"
            f"{icon} {format_rupiah(amount)}\n"
            f"📂 {pending['category']}\n"
            f"📝 {pending['description']}\n\n"
            f"💳 Saldo: *{format_rupiah(saldo_info['saldo'])}*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Catat Lagi", callback_data=menu_back)],
                [get_home_button()]
            ]),
            parse_mode='Markdown'
        )

    elif step == 'waiting_note':
        # add_note(user_id, description)
        db.add_note(uid, text)
        del context.user_data['pending_transaction']
        await update.message.reply_text(
            f"✅ *Note tersimpan!*\n\n📝 {text}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Kembali ke Notes", callback_data="menu_notes")],
                [get_home_button()]
            ]),
            parse_mode='Markdown'
        )

    elif step == 'waiting_category_name':
        pending['new_category_name'] = text
        pending['step'] = 'select_emoji'
        context.user_data['pending_transaction'] = pending
        await show_emoji_selection(update, context)

    elif step == 'waiting_edit_description':
        # update_transaction(trans_id, description=...) — tidak perlu user_id
        db.update_transaction(pending['trans_id'], description=text)
        del context.user_data['pending_transaction']
        await update.message.reply_text(
            f"✅ Keterangan diubah!\n\n📝 {text}",
            reply_markup=InlineKeyboardMarkup([[get_home_button()]])
        )

    elif step == 'waiting_edit_amount':
        is_valid, error_msg = parser.validate_amount_format(text)
        if not is_valid:
            await update.message.reply_text(f"❌ {error_msg}\n\nCoba lagi:")
            return
        amount = parser.parse_amount(text)
        # update_transaction(trans_id, amount=...) — tidak perlu user_id
        db.update_transaction(pending['trans_id'], amount=amount)
        del context.user_data['pending_transaction']
        await update.message.reply_text(
            f"✅ Nominal diubah!\n\n💰 {format_rupiah(amount)}",
            reply_markup=InlineKeyboardMarkup([[get_home_button()]])
        )


# ==================== SALDO / RINGKASAN ====================

async def show_saldo(query, user_id):
    # get_saldo_info(user_id)
    saldo_info = calc.get_saldo_info(user_id)
    text = (
        f"💳 *SALDO*\n\n"
        f"💰 Saldo Saat Ini:\n*{format_rupiah(saldo_info['saldo'])}*\n\n"
        f"Total Pemasukan: {format_rupiah(saldo_info['total_income'])}\n"
        f"Total Pengeluaran: {format_rupiah(saldo_info['total_expense'])}"
    )
    await safe_edit(query, text,
                    reply_markup=InlineKeyboardMarkup([get_back_and_dashboard("back_to_main")]))


async def show_ringkasan(query, user_id):
    today = get_today()
    # get_total_by_type(user_id, trans_type, start_date, end_date)
    income_today = db.get_total_by_type(user_id, 'income', today, today)
    expense_today = db.get_total_by_type(user_id, 'expense', today, today)
    saldo_info = calc.get_saldo_info(user_id)
    # get_spending_by_category(user_id, start_date, end_date)
    spending = db.get_spending_by_category(user_id, today, today)

    text = (
        f"📝 *RINGKASAN*\n\n"
        f"*Overall:*\n"
        f"Pemasukan: {format_rupiah(saldo_info['total_income'])}\n"
        f"Pengeluaran: {format_rupiah(saldo_info['total_expense'])}\n"
        f"Saldo: *{format_rupiah(saldo_info['saldo'])}*\n\n"
        f"*Hari Ini ({today}):*\n"
        f"💰 Masuk: {format_rupiah(income_today)}\n"
        f"💸 Keluar: {format_rupiah(expense_today)}"
    )
    if spending:
        text += "\n\n🔝 *Top Spending Hari Ini:*\n"
        for i, cat in enumerate(spending[:3], 1):
            text += f"{i}. {cat['category']} - {format_rupiah(cat['total'])}\n"

    await safe_edit(query, text,
                    reply_markup=InlineKeyboardMarkup([get_back_and_dashboard("back_to_main")]))


# ==================== LAPORAN ====================

async def show_laporan(query, user_id):
    try:
        # generate_text_report(user_id)
        report_text = report_gen.generate_text_report(user_id)
    except TypeError:
        report_text = report_gen.generate_text_report()
    await query.message.reply_text(report_text, parse_mode='Markdown')

    for gen_fn, caption in [
        (chart_gen.generate_pie_chart, "📊 Distribusi Pengeluaran per Kategori"),
        (chart_gen.generate_trend_chart, "📈 Trend Pengeluaran Harian"),
    ]:
        try:
            try:
                f = gen_fn(user_id)
            except TypeError:
                f = gen_fn()
            if f:
                await query.message.reply_photo(photo=open(f, 'rb'), caption=caption)
        except Exception as e:
            logger.warning(f"Chart error: {e}")

    await query.message.reply_text(
        "📥 *Export Laporan:*",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📄 Export PDF", callback_data="export_pdf"),
                InlineKeyboardButton("📊 Export Excel", callback_data="export_excel")
            ],
            [get_home_button()]
        ]),
        parse_mode='Markdown'
    )


# ==================== EDIT TRANSAKSI ====================

async def show_edit_menu(query, user_id):
    # get_unique_dates(user_id, limit)
    dates = db.get_unique_dates(user_id, 30)
    if not dates:
        await safe_edit(query, "❌ Belum ada transaksi.",
                        reply_markup=InlineKeyboardMarkup([[get_home_button()]]))
        return
    keyboard = []
    for date in dates[:10]:
        d = datetime.strptime(date, "%Y-%m-%d").strftime("%d %b %Y")
        keyboard.append([InlineKeyboardButton(f"📅 {d}", callback_data=f"edit_date_{date}")])
    keyboard.append(get_back_and_dashboard("back_to_main"))
    await safe_edit(query, "✏️ *EDIT TRANSAKSI*\n\nPilih tanggal:",
                    reply_markup=InlineKeyboardMarkup(keyboard))


async def show_transactions_by_date(query, user_id, date: str):
    # get_transactions_by_date(user_id, date)
    transactions = db.get_transactions_by_date(user_id, date)
    if not transactions:
        await safe_edit(query, f"❌ Tidak ada transaksi pada {date}",
                        reply_markup=InlineKeyboardMarkup([[get_home_button()]]))
        return
    keyboard = []
    for trans in transactions:
        icon = "💰" if trans['type'] == 'income' else "💸"
        keyboard.append([InlineKeyboardButton(
            f"{icon} {trans['category']} - {format_rupiah(trans['amount'])}",
            callback_data=f"edit_trans_{trans['id']}"
        )])
    keyboard.append(get_back_and_dashboard("menu_edit"))
    d = datetime.strptime(date, "%Y-%m-%d").strftime("%d %b %Y")
    await safe_edit(query, f"📅 *{d}*\n\nPilih transaksi:",
                    reply_markup=InlineKeyboardMarkup(keyboard))


async def show_transaction_options(query, trans_id: int):
    # get_transaction_by_id(trans_id) — tidak perlu user_id
    trans = db.get_transaction_by_id(trans_id)
    if not trans:
        await safe_edit(query, "❌ Transaksi tidak ditemukan",
                        reply_markup=InlineKeyboardMarkup([[get_home_button()]]))
        return
    icon = "💰" if trans['type'] == 'income' else "💸"
    trans_name = "Pemasukan" if trans['type'] == 'income' else "Pengeluaran"
    text = (
        f"{icon} *{trans_name}*\n\n"
        f"📅 {trans['date']} {trans['time']}\n"
        f"📂 {trans['category']}\n"
        f"💰 {format_rupiah(trans['amount'])}\n"
        f"📝 {trans['description'] or '-'}\n\nPilih aksi:"
    )
    keyboard = [
        [
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit_options_{trans_id}"),
            InlineKeyboardButton("🗑️ Hapus", callback_data=f"delete_confirm_{trans_id}")
        ],
        get_back_and_dashboard(f"edit_date_{trans['date']}")
    ]
    await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_edit_options(query, trans_id: int):
    keyboard = [
        [InlineKeyboardButton("📅 Tanggal", callback_data=f"edit_field_date_{trans_id}")],
        [InlineKeyboardButton("📝 Keterangan", callback_data=f"edit_field_desc_{trans_id}")],
        [InlineKeyboardButton("💰 Nominal", callback_data=f"edit_field_amount_{trans_id}")],
        get_back_and_dashboard(f"edit_trans_{trans_id}")
    ]
    await safe_edit(query, "Apa yang ingin diubah?", reply_markup=InlineKeyboardMarkup(keyboard))


# ==================== CALENDAR ====================

async def show_calendar_month(query, year: int, month: int, callback_prefix: str):
    month_name = calendar.month_name[month]
    cal = calendar.monthcalendar(year, month)
    keyboard = [
        [
            InlineKeyboardButton("«", callback_data=f"cal_prev_{year}_{month}_{callback_prefix}"),
            InlineKeyboardButton(f"{month_name} {year}", callback_data="cal_ignore"),
            InlineKeyboardButton("»", callback_data=f"cal_next_{year}_{month}_{callback_prefix}")
        ],
        [InlineKeyboardButton(d, callback_data="cal_ignore")
         for d in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]]
    ]
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="cal_ignore"))
            else:
                row.append(InlineKeyboardButton(
                    str(day),
                    callback_data=f"{callback_prefix}_{year:04d}-{month:02d}-{day:02d}"
                ))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("« Batal", callback_data="menu_edit"), get_home_button()])
    await safe_edit(query, "📅 *Pilih Tanggal*", reply_markup=InlineKeyboardMarkup(keyboard))


# ==================== NOTES ====================

async def show_notes_menu(query):
    await safe_edit(query, "📓 *NOTES*\n\nCatatan penting kamu:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📝 Tambah Note", callback_data="notes_add")],
                        [InlineKeyboardButton("📋 Lihat Semua Notes", callback_data="notes_list")],
                        get_back_and_dashboard("back_to_main")
                    ]))


async def show_notes_list(query, user_id):
    # get_all_notes(user_id)
    notes = db.get_all_notes(user_id)
    if not notes:
        await safe_edit(query, "📋 Belum ada notes.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("📝 Tambah Note", callback_data="notes_add")],
                            get_back_and_dashboard("menu_notes")
                        ]))
        return
    text = "📋 *SEMUA NOTES*\n\n"
    keyboard = []
    for i, note in enumerate(notes, 1):
        text += f"{i}. {note['description']}\n"
        keyboard.append([InlineKeyboardButton(
            f"🗑️ Hapus Note {i}", callback_data=f"notes_delete_{note['id']}"
        )])
    keyboard.append(get_back_and_dashboard("menu_notes"))
    await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(keyboard))


# ==================== SETTINGS ====================

async def show_category_management(query):
    await safe_edit(query, "📂 *KELOLA KATEGORI*\n\nPilih aksi:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("➕ Tambah Kategori", callback_data="cat_add")],
                        [InlineKeyboardButton("✏️ Edit Kategori", callback_data="cat_edit_select_type")],
                        [InlineKeyboardButton("🗑️ Hapus Kategori", callback_data="cat_delete_select_type")],
                        get_back_and_dashboard("menu_settings")
                    ]))


async def show_emoji_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    row = []
    for emoji in EMOJI_LIST:
        row.append(InlineKeyboardButton(emoji, callback_data=f"emoji_{emoji}"))
        if len(row) == 5:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("« Batal", callback_data="settings_categories"),
                     get_home_button()])
    await update.message.reply_text("Pilih emoji untuk kategori:",
                                    reply_markup=InlineKeyboardMarkup(keyboard))


# ==================== MAIN CALLBACK HANDLER ====================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    # Jawab Telegram DULU agar tidak loading
    try:
        await query.answer()
    except Exception:
        pass

    if data == "cal_ignore":
        return

    try:
        await _route(update, context, query, data, user_id)
    except Exception as e:
        await send_error(query, e)


async def _route(update, context, query, data, user_id):

    # ── DASHBOARD ──
    if data == "back_to_main":
        await safe_edit(query, f"🏠 *Dashboard — {BOT_NAME}*\n\nPilih menu:",
                        reply_markup=get_main_menu_keyboard())
        return

    # ── INCOME / EXPENSE ──
    if data == "menu_income":
        await show_category_grid(query, user_id, "income"); return
    if data == "menu_expense":
        await show_category_grid(query, user_id, "expense"); return
    if data.startswith("cat_income_"):
        await handle_category_selected(query, context, user_id, "income",
                                       data.replace("cat_income_", "")); return
    if data.startswith("cat_expense_"):
        await handle_category_selected(query, context, user_id, "expense",
                                       data.replace("cat_expense_", "")); return

    # ── SALDO / RINGKASAN / LAPORAN ──
    if data == "menu_saldo":
        await show_saldo(query, user_id); return
    if data == "menu_ringkasan":
        await show_ringkasan(query, user_id); return
    if data == "menu_laporan":
        await show_laporan(query, user_id); return

    # ── EDIT TRANSAKSI ──
    if data == "menu_edit":
        await show_edit_menu(query, user_id); return
    if data.startswith("edit_date_") and not data.startswith("edit_date_pick"):
        await show_transactions_by_date(query, user_id, data.replace("edit_date_", "")); return
    if data.startswith("edit_trans_"):
        await show_transaction_options(query, int(data.replace("edit_trans_", ""))); return
    if data.startswith("edit_options_"):
        await show_edit_options(query, int(data.replace("edit_options_", ""))); return

    if data.startswith("delete_confirm_"):
        trans_id = int(data.replace("delete_confirm_", ""))
        # get_transaction_by_id(trans_id) — tidak perlu user_id
        trans = db.get_transaction_by_id(trans_id)
        if trans:
            await safe_edit(query,
                f"⚠️ Yakin hapus transaksi ini?\n\n"
                f"{format_rupiah(trans['amount'])} - {trans['category']}",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Ya, Hapus", callback_data=f"delete_yes_{trans_id}"),
                        InlineKeyboardButton("❌ Batal", callback_data=f"edit_trans_{trans_id}")
                    ],
                    [get_home_button()]
                ]))
        return

    if data.startswith("delete_yes_"):
        trans_id = int(data.replace("delete_yes_", ""))
        # delete_transaction(trans_id) — tidak perlu user_id
        db.delete_transaction(trans_id)
        await safe_edit(query, "✅ Transaksi berhasil dihapus!",
                        reply_markup=InlineKeyboardMarkup([[get_home_button()]]))
        return

    if data.startswith("edit_field_date_"):
        trans_id = int(data.replace("edit_field_date_", ""))
        now = datetime.now(TIMEZONE)
        await show_calendar_month(query, now.year, now.month, f"edit_date_pick_{trans_id}")
        return

    if data.startswith("edit_field_desc_"):
        trans_id = int(data.replace("edit_field_desc_", ""))
        await safe_edit(query, "Masukkan keterangan baru:")
        context.user_data['pending_transaction'] = {
            'step': 'waiting_edit_description',
            'trans_id': trans_id,
            'user_id': user_id
        }
        return

    if data.startswith("edit_field_amount_"):
        trans_id = int(data.replace("edit_field_amount_", ""))
        await safe_edit(query, "Masukkan nominal baru (gunakan titik):\nContoh: 50.000")
        context.user_data['pending_transaction'] = {
            'step': 'waiting_edit_amount',
            'trans_id': trans_id,
            'user_id': user_id
        }
        return

    if data.startswith("edit_date_pick_") and "_20" in data:
        parts = data.split("_")
        trans_id = int(parts[3])
        new_date = parts[4]
        # update_transaction(trans_id, date=...) — tidak perlu user_id
        db.update_transaction(trans_id, date=new_date)
        await safe_edit(query, f"✅ Tanggal diubah ke {new_date}",
                        reply_markup=InlineKeyboardMarkup([[get_home_button()]]))
        return

    if data.startswith("cal_prev_") or data.startswith("cal_next_"):
        parts = data.split("_")
        action, year, month = parts[1], int(parts[2]), int(parts[3])
        prefix = "_".join(parts[4:])
        if action == "prev":
            month -= 1
            if month < 1:
                month = 12; year -= 1
        else:
            month += 1
            if month > 12:
                month = 1; year += 1
        await show_calendar_month(query, year, month, prefix)
        return

    # ── NOTES ──
    if data == "menu_notes":
        await show_notes_menu(query); return

    if data == "notes_add":
        context.user_data['pending_transaction'] = {'step': 'waiting_note', 'user_id': user_id}
        await safe_edit(query,
            "📝 *TAMBAH NOTE*\n\nKetik catatan kamu:\n(Contoh: Reminder bayar listrik tanggal 25)")
        return

    if data == "notes_list":
        await show_notes_list(query, user_id); return

    if data.startswith("notes_delete_"):
        note_id = int(data.replace("notes_delete_", ""))
        # delete_note(note_id) — tidak perlu user_id
        db.delete_note(note_id)
        await show_notes_list(query, user_id)
        return

    # ── SETTINGS ──
    if data == "menu_settings":
        await safe_edit(query, "⚙️ *SETTINGS*\n\nPilih menu:",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("📂 Kelola Kategori",
                                                  callback_data="settings_categories")],
                            get_back_and_dashboard("back_to_main")
                        ]))
        return

    if data == "settings_categories":
        await show_category_management(query); return

    if data == "cat_add":
        await safe_edit(query, "Pilih tipe kategori:",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("💰 Pemasukan", callback_data="cat_add_income")],
                            [InlineKeyboardButton("💸 Pengeluaran", callback_data="cat_add_expense")],
                            get_back_and_dashboard("settings_categories", "« Batal")
                        ]))
        return

    if data in ("cat_add_income", "cat_add_expense"):
        cat_type = data.replace("cat_add_", "")
        await safe_edit(query, f"Masukkan nama kategori {cat_type}:")
        context.user_data['pending_transaction'] = {
            'step': 'waiting_category_name',
            'category_type': cat_type,
            'user_id': user_id
        }
        return

    if data.startswith("emoji_"):
        emoji = data.replace("emoji_", "")
        pending = context.user_data.get('pending_transaction', {})
        if pending.get('step') == 'select_emoji':
            # add_category(name, trans_type, icon) — kategori global, tidak perlu user_id
            success = db.add_category(pending['new_category_name'],
                                      pending['category_type'], emoji)
            del context.user_data['pending_transaction']
            msg = (f"✅ Kategori ditambahkan!\n\n{emoji} {pending['new_category_name']}"
                   if success else "❌ Kategori dengan nama tersebut sudah ada!")
            await safe_edit(query, msg, reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Kembali", callback_data="settings_categories"),
                get_home_button()
            ]]))
        return

    if data == "cat_edit_select_type":
        await safe_edit(query, "Pilih tipe kategori yang ingin diedit:",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("💰 Pemasukan",
                                                  callback_data="cat_edit_list_income")],
                            [InlineKeyboardButton("💸 Pengeluaran",
                                                  callback_data="cat_edit_list_expense")],
                            get_back_and_dashboard("settings_categories", "« Batal")
                        ]))
        return

    if data.startswith("cat_edit_list_"):
        cat_type = data.replace("cat_edit_list_", "")
        # get_categories(trans_type) — global, tidak perlu user_id
        categories = db.get_categories(cat_type)
        keyboard = [[InlineKeyboardButton(f"{c['icon']} {c['name']}",
                     callback_data=f"cat_edit_select_{c['name']}")] for c in categories]
        keyboard.append(get_back_and_dashboard("settings_categories", "« Batal"))
        await safe_edit(query, "Pilih kategori yang ingin diedit:",
                        reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "cat_delete_select_type":
        await safe_edit(query, "Pilih tipe kategori yang ingin dihapus:",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("💰 Pemasukan",
                                                  callback_data="cat_delete_list_income")],
                            [InlineKeyboardButton("💸 Pengeluaran",
                                                  callback_data="cat_delete_list_expense")],
                            get_back_and_dashboard("settings_categories", "« Batal")
                        ]))
        return

    if data.startswith("cat_delete_list_"):
        cat_type = data.replace("cat_delete_list_", "")
        categories = db.get_categories(cat_type)
        keyboard = [[InlineKeyboardButton(f"{c['icon']} {c['name']}",
                     callback_data=f"cat_delete_confirm_{c['name']}")] for c in categories]
        keyboard.append(get_back_and_dashboard("settings_categories", "« Batal"))
        await safe_edit(query, "Pilih kategori yang ingin dihapus:",
                        reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("cat_delete_confirm_"):
        cat_name = data.replace("cat_delete_confirm_", "")
        # delete_category(name) — global, tidak perlu user_id
        success = db.delete_category(cat_name)
        msg = (f"✅ Kategori '{cat_name}' berhasil dihapus!" if success
               else f"❌ Kategori '{cat_name}' tidak bisa dihapus (masih ada transaksi)")
        await safe_edit(query, msg, reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("« Kembali", callback_data="settings_categories"),
            get_home_button()
        ]]))
        return

    # ── EXPORT ──
    if data == "export_pdf":
        try:
            try:
                f = report_gen.generate_pdf(user_id)
            except TypeError:
                f = report_gen.generate_pdf()
            await query.message.reply_document(document=open(f, 'rb'),
                                               caption="📄 Laporan Keuangan (PDF)")
        except Exception as e:
            await query.message.reply_text(f"❌ Error PDF: {e}")
        return

    if data == "export_excel":
        try:
            try:
                f = report_gen.generate_excel(user_id)
            except TypeError:
                f = report_gen.generate_excel()
            await query.message.reply_document(document=open(f, 'rb'),
                                               caption="📊 Laporan Keuangan (Excel)")
        except Exception as e:
            await query.message.reply_text(f"❌ Error Excel: {e}")
        return

    # ── RESET DATA ──
    if data == "menu_reset_data":
        await safe_edit(query,
            "⚠️ *RESET DATA*\n\nYakin hapus semua data?\n\n"
            "Ini akan menghapus:\n"
            "• Semua transaksi kamu\n"
            "• Semua notes kamu\n"
            "• Settings kamu\n\n"
            "❗ *Tindakan ini TIDAK BISA dibatalkan!*",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Ya, Hapus Semua", callback_data="reset_data_confirm"),
                InlineKeyboardButton("❌ Batal", callback_data="back_to_main")
            ]]))
        return

    if data == "reset_data_confirm":
        # reset_user_data(user_id) — hanya hapus data user ini
        db.reset_user_data(user_id)
        await safe_edit(query,
            "✅ *Semua data berhasil dihapus!*\n\nDatabase sudah bersih.\n"
            "Silakan mulai tracking dari awal.",
            reply_markup=InlineKeyboardMarkup([[get_home_button()]]))
        return

    logger.warning(f"Unhandled callback: {data}")
