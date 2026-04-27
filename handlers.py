#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cuan Track Bot - Command Handlers
v2.7 - Monthly filter untuk saldo/ringkasan/laporan
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
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

def get_month_start():
    """Tanggal 1 bulan ini."""
    now = datetime.now(TIMEZONE)
    return now.replace(day=1).strftime("%Y-%m-%d")

def get_month_label():
    """Nama bulan + tahun, misal: April 2026."""
    return datetime.now(TIMEZONE).strftime("%B %Y")

def get_last_month_end():
    """Tanggal terakhir bulan lalu (hari sebelum tanggal 1 bulan ini)."""
    first_this_month = datetime.now(TIMEZONE).replace(day=1)
    from datetime import timedelta
    last_month_last = first_this_month - timedelta(days=1)
    return last_month_last.strftime("%Y-%m-%d")

def get_saldo_awal_bulan(user_id):
    """
    Saldo akhir bulan lalu = semua pemasukan - semua pengeluaran s.d. akhir bulan lalu.
    Ini otomatis jadi saldo awal bulan ini tanpa perlu input transaksi.
    """
    last_end = get_last_month_end()
    total_inc = db.get_total_by_type(user_id, 'income', end_date=last_end)
    total_exp = db.get_total_by_type(user_id, 'expense', end_date=last_end)
    return total_inc - total_exp

def get_home_button():
    return InlineKeyboardButton("🏠 Dashboard", callback_data="back_to_main")

def get_back_and_dashboard(back_callback: str, back_label: str = "« Kembali"):
    """Hanya tombol Kembali — Dashboard sudah ada di persistent keyboard."""
    return [InlineKeyboardButton(back_label, callback_data=back_callback)]

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
            InlineKeyboardButton("💡 Insight", callback_data="menu_insight")
        ],
        [
            InlineKeyboardButton("📓 Notes", callback_data="menu_notes"),
            InlineKeyboardButton("✏️ Edit Transaksi", callback_data="menu_edit")
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
            InlineKeyboardButton("⚠️ Reset Data", callback_data="menu_reset_data")
        ]
    ])


def get_persistent_keyboard():
    """Keyboard permanen yang selalu muncul di area input — tap kapan saja untuk buka Dashboard."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🏠 Dashboard")]],
        resize_keyboard=True,
        is_persistent=True
    )


async def safe_edit(query, text, reply_markup=None, parse_mode='Markdown'):
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
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")]])
        )
    except Exception as e:
        logger.error(f"send_error failed: {e}")


# ==================== START & HELP ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    try:
        db.set_setting(user_id, 'first_seen', datetime.now(TIMEZONE).strftime("%Y-%m-%d"))
    except Exception as e:
        logger.warning(f"set_setting failed: {e}")

    await update.message.reply_text(
        f"🎉 *Selamat Datang di {BOT_NAME}!*\n\nHalo {user.first_name}! 👋\n\nSilakan pilih menu:",
        reply_markup=get_persistent_keyboard(),
        parse_mode='Markdown'
    )
    await update.message.reply_text(
        "📋 *Menu Utama:*",
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
        "*📊 Laporan:* Ringkasan bulan ini + export PDF/Excel\n"
        "*💳 Saldo:* Saldo bulan ini\n"
        "*📝 Ringkasan:* Summary bulan ini\n"
        "*📓 Notes:* Catatan penting\n"
        "*✏️ Edit Transaksi:* Koreksi transaksi lama\n"
        "*⚙️ Settings:* Kelola kategori\n\n"
        "💡 Saldo & Ringkasan menampilkan data bulan berjalan.\n"
        "📄 PDF & Excel menampilkan semua data dipisah per bulan.\n\n"
        "Ketuk 🏠 Dashboard kapan saja untuk kembali ke menu.",
        parse_mode='Markdown'
    )


# ==================== INCOME / EXPENSE ====================

async def show_category_grid(query, user_id, trans_type: str):
    categories = db.get_categories(trans_type)
    if not categories:
        await safe_edit(query, f"❌ Belum ada kategori {trans_type}. Tambahkan di Settings.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")]]))
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
    cat_info = db.get_category_by_name(category)
    icon = cat_info['icon'] if cat_info else "📌"
    example = INCOME_EXAMPLE_TEXT if trans_type == 'income' else EXPENSE_EXAMPLE_TEXT
    await safe_edit(query, f"{icon} *{category}*\n\nMasukkan keterangan:\n(Contoh: {example})")


async def handle_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    # Tap tombol keyboard permanen → tampilkan menu utama
    if text in ("🏠 Dashboard", "/start"):
        user = update.effective_user
        await update.message.reply_text(
            f"🏠 *Dashboard — {BOT_NAME}*\n\nPilih menu:",
            reply_markup=get_main_menu_keyboard(),
            parse_mode='Markdown'
        )
        return

    if 'pending_transaction' not in context.user_data:
        await update.message.reply_text(
            "Ketuk tombol *🏠 Dashboard* di keyboard untuk membuka menu.",
            reply_markup=get_persistent_keyboard(),
            parse_mode='Markdown'
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
        db.add_transaction(uid, get_today(), get_now_time(),
                           pending['type'], pending['category'],
                           amount, pending['description'])

        # Saldo bulan ini (carry-over dari bulan lalu + transaksi bulan ini)
        month_start = get_month_start()
        today = get_today()
        saldo_awal = get_saldo_awal_bulan(uid)
        income_month = db.get_total_by_type(uid, 'income', month_start, today)
        expense_month = db.get_total_by_type(uid, 'expense', month_start, today)
        saldo_month = saldo_awal + income_month - expense_month

        trans_name = "Pemasukan" if pending['type'] == 'income' else "Pengeluaran"
        icon = "💰" if pending['type'] == 'income' else "💸"
        menu_back = "menu_income" if pending['type'] == 'income' else "menu_expense"
        del context.user_data['pending_transaction']

        await update.message.reply_text(
            f"✅ *{trans_name} Tercatat!*\n\n"
            f"{icon} {format_rupiah(amount)}\n"
            f"📂 {pending['category']}\n"
            f"📝 {pending['description']}\n\n"
            f"💳 Saldo {get_month_label()}: *{format_rupiah(saldo_month)}*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Catat Lagi", callback_data=menu_back)]
            ]),
            parse_mode='Markdown'
        )

    elif step == 'waiting_note':
        db.add_note(uid, text)
        del context.user_data['pending_transaction']
        await update.message.reply_text(
            f"✅ *Note tersimpan!*\n\n📝 {text}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Kembali ke Notes", callback_data="menu_notes")]
            ]),
            parse_mode='Markdown'
        )

    elif step == 'waiting_category_name':
        pending['new_category_name'] = text
        pending['step'] = 'select_emoji'
        context.user_data['pending_transaction'] = pending
        await show_emoji_selection(update, context)

    elif step == 'waiting_edit_description':
        db.update_transaction(pending['trans_id'], description=text)
        del context.user_data['pending_transaction']
        await update.message.reply_text(
            f"✅ Keterangan diubah!\n\n📝 {text}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")]])
        )

    elif step == 'waiting_edit_amount':
        is_valid, error_msg = parser.validate_amount_format(text)
        if not is_valid:
            await update.message.reply_text(f"❌ {error_msg}\n\nCoba lagi:")
            return
        amount = parser.parse_amount(text)
        db.update_transaction(pending['trans_id'], amount=amount)
        del context.user_data['pending_transaction']
        await update.message.reply_text(
            f"✅ Nominal diubah!\n\n💰 {format_rupiah(amount)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")]])
        )


# ==================== SALDO (bulan ini) ====================

async def show_saldo(query, user_id):
    month_start = get_month_start()
    today = get_today()
    month_label = get_month_label()

    saldo_awal = get_saldo_awal_bulan(user_id)
    income_month = db.get_total_by_type(user_id, 'income', month_start, today)
    expense_month = db.get_total_by_type(user_id, 'expense', month_start, today)
    saldo_month = saldo_awal + income_month - expense_month

    text = (
        f"💳 *SALDO — {month_label}*\n\n"
        f"🔄 Saldo Awal Bulan: {format_rupiah(saldo_awal)}\n"
        f"💰 Pemasukan: {format_rupiah(income_month)}\n"
        f"💸 Pengeluaran: {format_rupiah(expense_month)}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💵 Saldo Saat Ini: *{format_rupiah(saldo_month)}*"
    )
    await safe_edit(query, text,
                    reply_markup=InlineKeyboardMarkup([get_back_and_dashboard("back_to_main")]))


# ==================== RINGKASAN (bulan ini) ====================

async def show_ringkasan(query, user_id):
    today = get_today()
    month_start = get_month_start()
    month_label = get_month_label()

    # Data bulan ini
    income_month = db.get_total_by_type(user_id, 'income', month_start, today)
    expense_month = db.get_total_by_type(user_id, 'expense', month_start, today)

    # Data hari ini
    income_today = db.get_total_by_type(user_id, 'income', today, today)
    expense_today = db.get_total_by_type(user_id, 'expense', today, today)

    # Top spending bulan ini
    spending_month = db.get_spending_by_category(user_id, month_start, today)

    saldo_awal = get_saldo_awal_bulan(user_id)
    saldo_month = saldo_awal + income_month - expense_month

    # ── Ringkasan keuangan ──
    text = (
        f"📝 *RINGKASAN — {month_label}*\n\n"
        f"🔄 Saldo Awal Bulan: {format_rupiah(saldo_awal)}\n"
        f"💰 Pemasukan: {format_rupiah(income_month)}\n"
        f"💸 Pengeluaran: {format_rupiah(expense_month)}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💵 Saldo Saat Ini: *{format_rupiah(saldo_month)}*\n\n"
        f"*Hari Ini ({today}):*\n"
        f"💰 Masuk: {format_rupiah(income_today)}\n"
        f"💸 Keluar: {format_rupiah(expense_today)}"
    )
    if spending_month:
        text += f"\n\n🔝 *Top Spending {month_label}:*\n"
        for i, cat in enumerate(spending_month[:5], 1):
            text += f"{i}. {cat['category']} - {format_rupiah(cat['total'])}\n"

    await safe_edit(query, text,
                    reply_markup=InlineKeyboardMarkup([get_back_and_dashboard("back_to_main")]))


# ==================== INSIGHT ====================

async def show_insight(query, user_id):
    month_label = get_month_label()

    try:
        insights = calc.generate_insights(user_id)
    except Exception as e:
        logger.warning(f"Insights error: {e}")
        insights = []

    if not insights:
        await safe_edit(
            query,
            "📝 *Belum ada insight.*\n\nTerus catat transaksi untuk mendapatkan analisis.",
            reply_markup=InlineKeyboardMarkup([get_back_and_dashboard("back_to_main")])
        )
        return

    header = (
        f"💡 *INSIGHT & SARAN — {month_label}*\n"
        f"_{len(insights)} analisis tersedia_"
    )
    await safe_edit(query, header)

    for i, ins in enumerate(insights, 1):
        text = f"*[{i}/{len(insights)}]*\n\n{ins}"
        kb = None
        if i == len(insights):
            kb = InlineKeyboardMarkup([get_back_and_dashboard("back_to_main")])
        await query.message.reply_text(text, parse_mode='Markdown', reply_markup=kb)


# ==================== LAPORAN (teks bulan ini + export all) ====================

async def show_laporan(query, user_id):
    month_start = get_month_start()
    today = get_today()
    month_label = get_month_label()

    # Teks laporan bulan ini
    try:
        report_text = report_gen.generate_text_report(user_id, month_start, today)
    except TypeError:
        try:
            report_text = report_gen.generate_text_report(user_id)
        except TypeError:
            report_text = report_gen.generate_text_report()

    await query.message.reply_text(report_text, parse_mode='Markdown')

    # Grafik bulan ini
    for gen_fn, caption in [
        (chart_gen.generate_expense_pie_chart, "📊 Distribusi Pengeluaran per Kategori"),
        (chart_gen.generate_trend_chart, "📈 Trend Pengeluaran Harian (30 Hari Terakhir)"),
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
        f"📥 *Export Laporan Lengkap* (semua bulan, dipisah per bulan):",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📄 Export PDF", callback_data="export_pdf"),
                InlineKeyboardButton("📊 Export Excel", callback_data="export_excel")
            ],
            [InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")]
        ]),
        parse_mode='Markdown'
    )


# ==================== EDIT TRANSAKSI ====================

async def show_edit_menu(query, user_id):
    dates = db.get_unique_dates(user_id, 30)
    if not dates:
        await safe_edit(query, "❌ Belum ada transaksi.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")]]))
        return
    keyboard = []
    for date in dates[:10]:
        d = datetime.strptime(date, "%Y-%m-%d").strftime("%d %b %Y")
        keyboard.append([InlineKeyboardButton(f"📅 {d}", callback_data=f"edit_date_{date}")])
    keyboard.append(get_back_and_dashboard("back_to_main"))
    await safe_edit(query, "✏️ *EDIT TRANSAKSI*\n\nPilih tanggal:",
                    reply_markup=InlineKeyboardMarkup(keyboard))


async def show_transactions_by_date(query, user_id, date: str):
    transactions = db.get_transactions_by_date(user_id, date)
    if not transactions:
        await safe_edit(query, f"❌ Tidak ada transaksi pada {date}",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")]]))
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
    trans = db.get_transaction_by_id(trans_id)
    if not trans:
        await safe_edit(query, "❌ Transaksi tidak ditemukan",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")]]))
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
    keyboard.append([InlineKeyboardButton("« Batal", callback_data="menu_edit")])
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
    keyboard.append([InlineKeyboardButton("« Batal", callback_data="settings_categories")])
    await update.message.reply_text("Pilih emoji untuk kategori:",
                                    reply_markup=InlineKeyboardMarkup(keyboard))


# ==================== MAIN CALLBACK HANDLER ====================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

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
    if data == "menu_insight":
        await show_insight(query, user_id); return
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
                    [InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")]
                ]))
        return

    if data.startswith("delete_yes_"):
        db.delete_transaction(int(data.replace("delete_yes_", "")))
        await safe_edit(query, "✅ Transaksi berhasil dihapus!",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")]]))
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
            'step': 'waiting_edit_description', 'trans_id': trans_id, 'user_id': user_id
        }
        return

    if data.startswith("edit_field_amount_"):
        trans_id = int(data.replace("edit_field_amount_", ""))
        await safe_edit(query, "Masukkan nominal baru (gunakan titik):\nContoh: 50.000")
        context.user_data['pending_transaction'] = {
            'step': 'waiting_edit_amount', 'trans_id': trans_id, 'user_id': user_id
        }
        return

    if data.startswith("edit_date_pick_") and "_20" in data:
        parts = data.split("_")
        trans_id = int(parts[3])
        new_date = parts[4]
        db.update_transaction(trans_id, date=new_date)
        await safe_edit(query, f"✅ Tanggal diubah ke {new_date}",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")]]))
        return

    if data.startswith("cal_prev_") or data.startswith("cal_next_"):
        parts = data.split("_")
        action, year, month = parts[1], int(parts[2]), int(parts[3])
        prefix = "_".join(parts[4:])
        if action == "prev":
            month -= 1
            if month < 1: month = 12; year -= 1
        else:
            month += 1
            if month > 12: month = 1; year += 1
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
        db.delete_note(int(data.replace("notes_delete_", "")))
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
            'step': 'waiting_category_name', 'category_type': cat_type, 'user_id': user_id
        }
        return

    if data.startswith("emoji_"):
        emoji = data.replace("emoji_", "")
        pending = context.user_data.get('pending_transaction', {})
        if pending.get('step') == 'select_emoji':
            success = db.add_category(pending['new_category_name'], pending['category_type'], emoji)
            del context.user_data['pending_transaction']
            msg = (f"✅ Kategori ditambahkan!\n\n{emoji} {pending['new_category_name']}"
                   if success else "❌ Kategori dengan nama tersebut sudah ada!")
            await safe_edit(query, msg, reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Kembali", callback_data="settings_categories")
            ]]))
        return

    if data == "cat_edit_select_type":
        await safe_edit(query, "Pilih tipe kategori yang ingin diedit:",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("💰 Pemasukan", callback_data="cat_edit_list_income")],
                            [InlineKeyboardButton("💸 Pengeluaran", callback_data="cat_edit_list_expense")],
                            get_back_and_dashboard("settings_categories", "« Batal")
                        ]))
        return

    if data.startswith("cat_edit_list_"):
        cat_type = data.replace("cat_edit_list_", "")
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
                            [InlineKeyboardButton("💰 Pemasukan", callback_data="cat_delete_list_income")],
                            [InlineKeyboardButton("💸 Pengeluaran", callback_data="cat_delete_list_expense")],
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
        success = db.delete_category(cat_name)
        msg = (f"✅ Kategori '{cat_name}' berhasil dihapus!" if success
               else f"❌ Kategori '{cat_name}' tidak bisa dihapus (masih ada transaksi)")
        await safe_edit(query, msg, reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("« Kembali", callback_data="settings_categories")
        ]]))
        return

    # ── EXPORT (semua data, dipisah per bulan) ──
    if data == "export_pdf":
        try:
            try:
                f = report_gen.generate_pdf(user_id)
            except TypeError:
                f = report_gen.generate_pdf()
            await query.message.reply_document(document=open(f, 'rb'),
                                               caption="📄 Laporan Lengkap (PDF) — semua bulan")
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
                                               caption="📊 Laporan Lengkap (Excel) — semua bulan")
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
        db.reset_user_data(user_id)
        await safe_edit(query,
            "✅ *Semua data berhasil dihapus!*\n\nDatabase sudah bersih.\n"
            "Silakan mulai tracking dari awal.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")]]))
        return

    logger.warning(f"Unhandled callback: {data}")
