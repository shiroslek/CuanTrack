#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cuan Track Bot - Command Handlers
Patch v2.2:
  - Fix: tombol lama tidak merespons (bot restart / pesan expired)
  - Fix: fallback kirim pesan baru jika edit gagal
  - Feature: tombol Dashboard permanen di semua keyboard
"""

from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest
import calendar

from config import TIMEZONE, BOT_NAME, EMOJI_LIST, INCOME_EXAMPLE_TEXT, EXPENSE_EXAMPLE_TEXT
from database import Database
from parser import NumberParser
from calculator import Calculator
from report_generator import ReportGenerator
from chart_generator import ChartGenerator

db = Database()
calc = Calculator(db)
parser = NumberParser()
report_gen = ReportGenerator(db)
chart_gen = ChartGenerator(db)

# ==================== UTILITY FUNCTIONS ====================

def format_rupiah(amount):
    return parser.format_rupiah(amount)

def get_today():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d")

def get_now_time():
    return datetime.now(TIMEZONE).strftime("%H:%M:%S")

def get_home_button():
    """Tombol Dashboard (pengganti Home) — selalu ada di semua keyboard"""
    return InlineKeyboardButton("🏠 Dashboard", callback_data="back_to_main")

def get_back_and_dashboard(back_callback: str, back_label: str = "« Kembali"):
    """
    Baris navigasi standar: [Kembali] [Dashboard]
    Gunakan ini di semua keyboard sebagai baris terakhir.
    """
    return [
        InlineKeyboardButton(back_label, callback_data=back_callback),
        get_home_button()
    ]

# ==================== SAFE EDIT / REPLY ====================

async def safe_edit(query, text, reply_markup=None, parse_mode='Markdown'):
    """
    Coba edit pesan. Jika gagal (pesan lama / bot restart),
    kirim pesan baru sebagai fallback — tidak pernah diam.
    """
    try:
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except BadRequest:
        # Pesan terlalu lama atau sudah tidak bisa diedit → kirim baru
        await query.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )


# ==================== MAIN MENU KEYBOARD ====================

def get_main_menu_keyboard():
    keyboard = [
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
    ]
    return InlineKeyboardMarkup(keyboard)


# ==================== START & HELP ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.set_setting('admin_user_id', str(user.id))

    welcome_text = f"""
🎉 *Selamat Datang di {BOT_NAME}!*

Halo {user.first_name}! 👋

Silakan pilih menu di bawah:
"""
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = f"""
📚 *PANDUAN {BOT_NAME}*

*💰 Catat Pemasukan/Pengeluaran:*
1. Pilih kategori dari grid
2. Masukkan keterangan
3. Masukkan nominal: 50.000 atau 1.500.000

*📊 Laporan:* Lihat laporan lengkap + grafik
*💳 Saldo:* Cek saldo saat ini
*📝 Ringkasan:* Summary singkat hari ini
*📓 Notes:* Buat catatan penting
*✏️ Edit Transaksi:* Pilih tanggal → pilih transaksi → edit/hapus
*⚙️ Settings:* Kelola kategori

Ketik /start atau ketuk 🏠 Dashboard untuk kembali ke menu.
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


# ==================== INCOME/EXPENSE FLOW ====================

async def show_category_grid(update: Update, context: ContextTypes.DEFAULT_TYPE, trans_type: str):
    query = update.callback_query
    await query.answer()

    categories = db.get_categories(trans_type)

    if not categories:
        await safe_edit(query, f"❌ Belum ada kategori {trans_type}. Tambahkan di Settings.")
        return

    keyboard = []
    row = []
    for cat in categories:
        button = InlineKeyboardButton(
            f"{cat['icon']} {cat['name']}",
            callback_data=f"cat_{trans_type}_{cat['name']}"
        )
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Navigasi: Kembali + Dashboard
    keyboard.append(get_back_and_dashboard("back_to_main", "« Kembali"))

    reply_markup = InlineKeyboardMarkup(keyboard)
    icon = "💰" if trans_type == "income" else "💸"
    trans_name = "Pemasukan" if trans_type == "income" else "Pengeluaran"

    await safe_edit(
        query,
        f"{icon} *CATAT {trans_name.upper()}*\n\nPilih kategori:",
        reply_markup=reply_markup
    )

async def handle_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE, trans_type: str, category: str):
    query = update.callback_query
    await query.answer()

    context.user_data['pending_transaction'] = {
        'type': trans_type,
        'category': category,
        'step': 'waiting_description'
    }

    cat_info = db.get_category_by_name(category)
    icon = cat_info['icon'] if cat_info else "📌"
    example_text = INCOME_EXAMPLE_TEXT if trans_type == 'income' else EXPENSE_EXAMPLE_TEXT

    await safe_edit(
        query,
        f"{icon} *{category}*\n\nMasukkan keterangan:\n(Contoh: {example_text})"
    )

async def handle_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if 'pending_transaction' not in context.user_data:
        await update.message.reply_text(
            "Gunakan /start atau ketuk 🏠 Dashboard untuk membuka menu."
        )
        return

    pending = context.user_data['pending_transaction']
    step = pending.get('step')

    if step == 'waiting_description':
        pending['description'] = text
        pending['step'] = 'waiting_amount'
        context.user_data['pending_transaction'] = pending
        await update.message.reply_text(
            f"✅ Keterangan: *{text}*\n\n"
            f"Masukkan nominal (gunakan titik):\n"
            f"Contoh: 50.000 atau 1.500.000",
            parse_mode='Markdown'
        )

    elif step == 'waiting_amount':
        is_valid, error_msg = parser.validate_amount_format(text)
        if not is_valid:
            await update.message.reply_text(
                f"❌ {error_msg}\n\nFormat yang benar:\n• 50.000\n• 1.500.000\n\nCoba lagi:"
            )
            return

        amount = parser.parse_amount(text)
        date = get_today()
        time = get_now_time()

        db.add_transaction(date, time, pending['type'], pending['category'], amount, pending['description'])
        saldo_info = calc.get_saldo_info()

        trans_name = "Pemasukan" if pending['type'] == 'income' else "Pengeluaran"
        icon = "💰" if pending['type'] == 'income' else "💸"
        del context.user_data['pending_transaction']

        success_text = f"""
✅ *{trans_name} Tercatat!*

{icon} {format_rupiah(amount)}
📂 {pending['category']}
📝 {pending['description']}

💳 Saldo: *{format_rupiah(saldo_info['saldo'])}*
"""
        keyboard = [
            [InlineKeyboardButton("« Catat Lagi", callback_data=f"menu_{'income' if pending['type']=='income' else 'expense'}")],
            [get_home_button()]
        ]
        await update.message.reply_text(
            success_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif step == 'waiting_note':
        db.add_note(text)
        del context.user_data['pending_transaction']

        keyboard = [
            [InlineKeyboardButton("« Kembali ke Notes", callback_data="menu_notes")],
            [get_home_button()]
        ]
        await update.message.reply_text(
            f"✅ *Note tersimpan!*\n\n📝 {text}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif step == 'waiting_category_name':
        pending['new_category_name'] = text
        pending['step'] = 'select_emoji'
        context.user_data['pending_transaction'] = pending
        await show_emoji_selection(update, context)

    elif step == 'waiting_edit_description':
        trans_id = pending['trans_id']
        db.update_transaction(trans_id, description=text)
        del context.user_data['pending_transaction']

        await update.message.reply_text(
            f"✅ Keterangan berhasil diubah!\n\n📝 {text}",
            reply_markup=InlineKeyboardMarkup([[get_home_button()]])
        )

    elif step == 'waiting_edit_amount':
        is_valid, error_msg = parser.validate_amount_format(text)
        if not is_valid:
            await update.message.reply_text(f"❌ {error_msg}\n\nCoba lagi:")
            return

        amount = parser.parse_amount(text)
        trans_id = pending['trans_id']
        db.update_transaction(trans_id, amount=amount)
        del context.user_data['pending_transaction']

        await update.message.reply_text(
            f"✅ Nominal berhasil diubah!\n\n💰 {format_rupiah(amount)}",
            reply_markup=InlineKeyboardMarkup([[get_home_button()]])
        )


# ==================== EDIT TRANSACTION ====================

async def show_edit_transaction_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    dates = db.get_unique_dates(30)
    if not dates:
        await safe_edit(query, "❌ Belum ada transaksi.")
        return

    keyboard = []
    for date in dates[:10]:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_display = date_obj.strftime("%d %b %Y")
        keyboard.append([InlineKeyboardButton(f"📅 {date_display}", callback_data=f"edit_date_{date}")])

    keyboard.append(get_back_and_dashboard("back_to_main"))
    await safe_edit(query, "✏️ *EDIT TRANSAKSI*\n\nPilih tanggal:",
                    reply_markup=InlineKeyboardMarkup(keyboard))

async def show_transactions_by_date(update: Update, context: ContextTypes.DEFAULT_TYPE, date: str):
    query = update.callback_query
    await query.answer()

    transactions = db.get_transactions_by_date(date)
    if not transactions:
        await safe_edit(query, f"❌ Tidak ada transaksi pada {date}")
        return

    keyboard = []
    for trans in transactions:
        icon = "💰" if trans['type'] == 'income' else "💸"
        label = f"{icon} {trans['category']} - {format_rupiah(trans['amount'])}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"edit_trans_{trans['id']}")])

    keyboard.append(get_back_and_dashboard("menu_edit"))

    date_obj = datetime.strptime(date, "%Y-%m-%d")
    date_display = date_obj.strftime("%d %b %Y")
    await safe_edit(query, f"📅 *{date_display}*\n\nPilih transaksi:",
                    reply_markup=InlineKeyboardMarkup(keyboard))

async def show_transaction_options(update: Update, context: ContextTypes.DEFAULT_TYPE, trans_id: int):
    query = update.callback_query
    await query.answer()

    trans = db.get_transaction_by_id(trans_id)
    if not trans:
        await safe_edit(query, "❌ Transaksi tidak ditemukan")
        return

    icon = "💰" if trans['type'] == 'income' else "💸"
    trans_name = "Pemasukan" if trans['type'] == 'income' else "Pengeluaran"
    details = f"""
{icon} *{trans_name}*

📅 {trans['date']} {trans['time']}
📂 {trans['category']}
💰 {format_rupiah(trans['amount'])}
📝 {trans['description'] or '-'}

Pilih aksi:
"""
    keyboard = [
        [
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit_options_{trans_id}"),
            InlineKeyboardButton("🗑️ Hapus", callback_data=f"delete_confirm_{trans_id}")
        ],
        get_back_and_dashboard(f"edit_date_{trans['date']}")
    ]
    await safe_edit(query, details, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_edit_options(update: Update, context: ContextTypes.DEFAULT_TYPE, trans_id: int):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("📅 Tanggal", callback_data=f"edit_field_date_{trans_id}")],
        [InlineKeyboardButton("📝 Keterangan", callback_data=f"edit_field_desc_{trans_id}")],
        [InlineKeyboardButton("💰 Nominal", callback_data=f"edit_field_amount_{trans_id}")],
        get_back_and_dashboard(f"edit_trans_{trans_id}")
    ]
    await safe_edit(query, "Apa yang ingin diubah?", reply_markup=InlineKeyboardMarkup(keyboard))


# ==================== CALENDAR DATE PICKER ====================

async def show_date_picker(update: Update, context: ContextTypes.DEFAULT_TYPE, trans_id: int):
    query = update.callback_query
    await query.answer()
    context.user_data['editing_trans_id'] = trans_id
    now = datetime.now(TIMEZONE)
    await show_calendar_month(query, now.year, now.month, f"edit_date_pick_{trans_id}")

async def show_calendar_month(query, year: int, month: int, callback_prefix: str):
    month_name = calendar.month_name[month]
    cal = calendar.monthcalendar(year, month)
    keyboard = []

    keyboard.append([
        InlineKeyboardButton("«", callback_data=f"cal_prev_{year}_{month}_{callback_prefix}"),
        InlineKeyboardButton(f"{month_name} {year}", callback_data="cal_ignore"),
        InlineKeyboardButton("»", callback_data=f"cal_next_{year}_{month}_{callback_prefix}")
    ])
    keyboard.append([InlineKeyboardButton(d, callback_data="cal_ignore")
                     for d in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]])

    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="cal_ignore"))
            else:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                row.append(InlineKeyboardButton(str(day), callback_data=f"{callback_prefix}_{date_str}"))
        keyboard.append(row)

    keyboard.append([
        InlineKeyboardButton("« Batal", callback_data="menu_edit"),
        InlineKeyboardButton("🏠 Dashboard", callback_data="back_to_main")
    ])

    await query.edit_message_text(
        "📅 *Pilih Tanggal*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


# ==================== NOTES ====================

async def show_notes_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📝 Tambah Note", callback_data="notes_add")],
        [InlineKeyboardButton("📋 Lihat Semua Notes", callback_data="notes_list")],
        get_back_and_dashboard("back_to_main")
    ]
    await safe_edit(query, "📓 *NOTES*\n\nCatatan penting kamu:",
                    reply_markup=InlineKeyboardMarkup(keyboard))

async def add_note_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['pending_transaction'] = {'step': 'waiting_note'}
    await safe_edit(
        query,
        "📝 *TAMBAH NOTE*\n\nKetik catatan kamu:\n(Contoh: Reminder bayar listrik tanggal 25)"
    )

async def show_notes_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    notes = db.get_all_notes()

    if not notes:
        keyboard = [
            [InlineKeyboardButton("📝 Tambah Note", callback_data="notes_add")],
            get_back_and_dashboard("menu_notes")
        ]
        await safe_edit(query, "📋 Belum ada notes.\n\nTambah note pertama?",
                        reply_markup=InlineKeyboardMarkup(keyboard))
        return

    text = "📋 *SEMUA NOTES*\n\n"
    keyboard = []
    for i, note in enumerate(notes, 1):
        text += f"{i}. {note['description']}\n"
        keyboard.append([InlineKeyboardButton(f"🗑️ Hapus Note {i}", callback_data=f"notes_delete_{note['id']}")])

    keyboard.append(get_back_and_dashboard("menu_notes"))
    await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(keyboard))

async def delete_note_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, note_id: int):
    query = update.callback_query
    await query.answer("Note dihapus!")
    db.delete_note(note_id)
    await show_notes_list(update, context)


# ==================== SETTINGS ====================

async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📂 Kelola Kategori", callback_data="settings_categories")],
        get_back_and_dashboard("back_to_main")
    ]
    await safe_edit(query, "⚙️ *SETTINGS*\n\nPilih menu:",
                    reply_markup=InlineKeyboardMarkup(keyboard))

async def show_category_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("➕ Tambah Kategori", callback_data="cat_add")],
        [InlineKeyboardButton("✏️ Edit Kategori", callback_data="cat_edit_select_type")],
        [InlineKeyboardButton("🗑️ Hapus Kategori", callback_data="cat_delete_select_type")],
        get_back_and_dashboard("menu_settings")
    ]
    await safe_edit(query, "📂 *KELOLA KATEGORI*\n\nPilih aksi:",
                    reply_markup=InlineKeyboardMarkup(keyboard))

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
    keyboard.append([
        InlineKeyboardButton("« Batal", callback_data="settings_categories"),
        get_home_button()
    ])
    await update.message.reply_text(
        "Pilih emoji untuk kategori:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================== SALDO, LAPORAN, RINGKASAN ====================

async def show_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    saldo_info = calc.get_saldo_info()
    text = f"""
💳 *SALDO*

💰 Saldo Saat Ini:
*{format_rupiah(saldo_info['saldo'])}*

Total Pemasukan: {format_rupiah(saldo_info['total_income'])}
Total Pengeluaran: {format_rupiah(saldo_info['total_expense'])}
"""
    keyboard = [get_back_and_dashboard("back_to_main")]
    await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_ringkasan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    today = get_today()
    income_today = db.get_total_by_type('income', today, today)
    expense_today = db.get_total_by_type('expense', today, today)
    saldo_info = calc.get_saldo_info()
    spending = db.get_spending_by_category(today, today)

    text = f"""
📝 *RINGKASAN*

*Overall:*
Pemasukan: {format_rupiah(saldo_info['total_income'])}
Pengeluaran: {format_rupiah(saldo_info['total_expense'])}
Saldo: *{format_rupiah(saldo_info['saldo'])}*

*Hari Ini ({today}):*
💰 Masuk: {format_rupiah(income_today)}
💸 Keluar: {format_rupiah(expense_today)}
"""
    if spending:
        text += "\n🔝 *Top Spending Hari Ini:*\n"
        for i, cat in enumerate(spending[:3], 1):
            text += f"{i}. {cat['category']} - {format_rupiah(cat['total'])}\n"

    keyboard = [get_back_and_dashboard("back_to_main")]
    await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_laporan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Generating laporan...")

    report_text = report_gen.generate_text_report()
    await query.message.reply_text(report_text, parse_mode='Markdown')

    try:
        chart_file = chart_gen.generate_pie_chart()
        if chart_file:
            await query.message.reply_photo(
                photo=open(chart_file, 'rb'),
                caption="📊 Distribusi Pengeluaran per Kategori"
            )
    except Exception as e:
        print(f"Error pie chart: {e}")

    try:
        trend_file = chart_gen.generate_trend_chart()
        if trend_file:
            await query.message.reply_photo(
                photo=open(trend_file, 'rb'),
                caption="📈 Trend Pengeluaran Harian"
            )
    except Exception as e:
        print(f"Error trend chart: {e}")

    keyboard = [
        [
            InlineKeyboardButton("📄 Export PDF", callback_data="export_pdf"),
            InlineKeyboardButton("📊 Export Excel", callback_data="export_excel")
        ],
        [get_home_button()]
    ]
    await query.message.reply_text(
        "📥 *Export Laporan:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


# ==================== CALLBACK HANDLER ====================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "cal_ignore":
        await query.answer()
        return

    # ── MAIN MENU / DASHBOARD ──
    if data == "back_to_main":
        await query.answer()
        text = f"🏠 *Dashboard — {BOT_NAME}*\n\nPilih menu:"
        try:
            await query.edit_message_text(
                text,
                reply_markup=get_main_menu_keyboard(),
                parse_mode='Markdown'
            )
        except BadRequest:
            # Pesan lama → kirim baru
            await query.message.reply_text(
                text,
                reply_markup=get_main_menu_keyboard(),
                parse_mode='Markdown'
            )
        return

    # ── INCOME / EXPENSE ──
    if data == "menu_income":
        await show_category_grid(update, context, "income")
        return
    if data == "menu_expense":
        await show_category_grid(update, context, "expense")
        return
    if data.startswith("cat_income_"):
        await handle_category_selected(update, context, "income", data.replace("cat_income_", ""))
        return
    if data.startswith("cat_expense_"):
        await handle_category_selected(update, context, "expense", data.replace("cat_expense_", ""))
        return

    # ── EDIT TRANSAKSI ──
    if data == "menu_edit":
        await show_edit_transaction_menu(update, context)
        return
    if data.startswith("edit_date_") and not data.startswith("edit_date_pick"):
        await show_transactions_by_date(update, context, data.replace("edit_date_", ""))
        return
    if data.startswith("edit_trans_"):
        await show_transaction_options(update, context, int(data.replace("edit_trans_", "")))
        return
    if data.startswith("edit_options_"):
        await show_edit_options(update, context, int(data.replace("edit_options_", "")))
        return

    if data.startswith("delete_confirm_"):
        trans_id = int(data.replace("delete_confirm_", ""))
        trans = db.get_transaction_by_id(trans_id)
        if trans:
            keyboard = [
                [
                    InlineKeyboardButton("✅ Ya, Hapus", callback_data=f"delete_yes_{trans_id}"),
                    InlineKeyboardButton("❌ Batal", callback_data=f"edit_trans_{trans_id}")
                ],
                [get_home_button()]
            ]
            await query.answer()
            await safe_edit(
                query,
                f"⚠️ Yakin hapus transaksi ini?\n\n{format_rupiah(trans['amount'])} - {trans['category']}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

    if data.startswith("delete_yes_"):
        trans_id = int(data.replace("delete_yes_", ""))
        db.delete_transaction(trans_id)
        await query.answer("✅ Transaksi dihapus!")
        await safe_edit(
            query,
            "✅ Transaksi berhasil dihapus!",
            reply_markup=InlineKeyboardMarkup([[get_home_button()]])
        )
        return

    if data.startswith("edit_field_date_"):
        await show_date_picker(update, context, int(data.replace("edit_field_date_", "")))
        return

    if data.startswith("edit_field_desc_"):
        trans_id = int(data.replace("edit_field_desc_", ""))
        await query.answer()
        await safe_edit(query, "Masukkan keterangan baru:")
        context.user_data['pending_transaction'] = {
            'step': 'waiting_edit_description',
            'trans_id': trans_id
        }
        return

    if data.startswith("edit_field_amount_"):
        trans_id = int(data.replace("edit_field_amount_", ""))
        await query.answer()
        await safe_edit(query, "Masukkan nominal baru (gunakan titik):\nContoh: 50.000")
        context.user_data['pending_transaction'] = {
            'step': 'waiting_edit_amount',
            'trans_id': trans_id
        }
        return

    if data.startswith("edit_date_pick_") and "_20" in data:
        parts = data.split("_")
        trans_id = int(parts[3])
        new_date = parts[4]
        db.update_transaction(trans_id, date=new_date)
        await query.answer("✅ Tanggal diubah!")
        await safe_edit(
            query,
            f"✅ Tanggal berhasil diubah ke {new_date}",
            reply_markup=InlineKeyboardMarkup([[get_home_button()]])
        )
        return

    # Calendar navigation
    if data.startswith("cal_prev_") or data.startswith("cal_next_"):
        parts = data.split("_")
        action = parts[1]
        year = int(parts[2])
        month = int(parts[3])
        callback_prefix = "_".join(parts[4:])
        if action == "prev":
            month -= 1
            if month < 1:
                month = 12; year -= 1
        else:
            month += 1
            if month > 12:
                month = 1; year += 1
        await show_calendar_month(query, year, month, callback_prefix)
        return

    # ── NOTES ──
    if data == "menu_notes":
        await show_notes_menu(update, context)
        return
    if data == "notes_add":
        await add_note_prompt(update, context)
        return
    if data == "notes_list":
        await show_notes_list(update, context)
        return
    if data.startswith("notes_delete_"):
        await delete_note_confirm(update, context, int(data.replace("notes_delete_", "")))
        return

    # ── SETTINGS ──
    if data == "menu_settings":
        await show_settings_menu(update, context)
        return
    if data == "settings_categories":
        await show_category_management(update, context)
        return

    if data == "cat_add":
        keyboard = [
            [InlineKeyboardButton("💰 Pemasukan", callback_data="cat_add_income")],
            [InlineKeyboardButton("💸 Pengeluaran", callback_data="cat_add_expense")],
            get_back_and_dashboard("settings_categories", "« Batal")
        ]
        await query.answer()
        await safe_edit(query, "Pilih tipe kategori:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("cat_add_") and data in ("cat_add_income", "cat_add_expense"):
        cat_type = data.replace("cat_add_", "")
        await query.answer()
        await safe_edit(query, f"Masukkan nama kategori {cat_type}:")
        context.user_data['pending_transaction'] = {
            'step': 'waiting_category_name',
            'category_type': cat_type
        }
        return

    if data.startswith("emoji_"):
        emoji = data.replace("emoji_", "")
        pending = context.user_data.get('pending_transaction', {})
        if pending.get('step') == 'select_emoji':
            cat_name = pending['new_category_name']
            cat_type = pending['category_type']
            success = db.add_category(cat_name, cat_type, emoji)
            del context.user_data['pending_transaction']
            if success:
                await query.answer("✅ Kategori ditambahkan!")
                await query.edit_message_text(
                    f"✅ Kategori berhasil ditambahkan!\n\n{emoji} {cat_name}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Kembali", callback_data="settings_categories"),
                        get_home_button()
                    ]])
                )
            else:
                await query.answer("❌ Kategori sudah ada!")
                await query.edit_message_text(
                    "❌ Kategori dengan nama tersebut sudah ada!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Kembali", callback_data="settings_categories"),
                        get_home_button()
                    ]])
                )
        return

    if data == "cat_edit_select_type":
        keyboard = [
            [InlineKeyboardButton("💰 Pemasukan", callback_data="cat_edit_list_income")],
            [InlineKeyboardButton("💸 Pengeluaran", callback_data="cat_edit_list_expense")],
            get_back_and_dashboard("settings_categories", "« Batal")
        ]
        await query.answer()
        await safe_edit(query, "Pilih tipe kategori yang ingin diedit:",
                        reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("cat_edit_list_"):
        cat_type = data.replace("cat_edit_list_", "")
        categories = db.get_categories(cat_type)
        keyboard = []
        for cat in categories:
            keyboard.append([InlineKeyboardButton(
                f"{cat['icon']} {cat['name']}",
                callback_data=f"cat_edit_select_{cat['name']}"
            )])
        keyboard.append(get_back_and_dashboard("settings_categories", "« Batal"))
        await query.answer()
        await safe_edit(query, "Pilih kategori yang ingin diedit:",
                        reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "cat_delete_select_type":
        keyboard = [
            [InlineKeyboardButton("💰 Pemasukan", callback_data="cat_delete_list_income")],
            [InlineKeyboardButton("💸 Pengeluaran", callback_data="cat_delete_list_expense")],
            get_back_and_dashboard("settings_categories", "« Batal")
        ]
        await query.answer()
        await safe_edit(query, "Pilih tipe kategori yang ingin dihapus:",
                        reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("cat_delete_list_"):
        cat_type = data.replace("cat_delete_list_", "")
        categories = db.get_categories(cat_type)
        keyboard = []
        for cat in categories:
            keyboard.append([InlineKeyboardButton(
                f"{cat['icon']} {cat['name']}",
                callback_data=f"cat_delete_confirm_{cat['name']}"
            )])
        keyboard.append(get_back_and_dashboard("settings_categories", "« Batal"))
        await query.answer()
        await safe_edit(query, "Pilih kategori yang ingin dihapus:",
                        reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("cat_delete_confirm_"):
        cat_name = data.replace("cat_delete_confirm_", "")
        success = db.delete_category(cat_name)
        if success:
            await query.answer("✅ Kategori dihapus!")
            await safe_edit(
                query,
                f"✅ Kategori '{cat_name}' berhasil dihapus!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Kembali", callback_data="settings_categories"),
                    get_home_button()
                ]])
            )
        else:
            await query.answer("❌ Tidak bisa dihapus!")
            await safe_edit(
                query,
                f"❌ Kategori '{cat_name}' tidak bisa dihapus\n(masih ada transaksi yang menggunakannya)",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Kembali", callback_data="settings_categories"),
                    get_home_button()
                ]])
            )
        return

    # ── SALDO, LAPORAN, RINGKASAN ──
    if data == "menu_saldo":
        await show_saldo(update, context)
        return
    if data == "menu_ringkasan":
        await show_ringkasan(update, context)
        return
    if data == "menu_laporan":
        await show_laporan(update, context)
        return

    if data == "export_pdf":
        await query.answer("Generating PDF...")
        try:
            file_path = report_gen.generate_pdf()
            await query.message.reply_document(
                document=open(file_path, 'rb'),
                caption="📄 Laporan Keuangan (PDF)"
            )
        except Exception as e:
            await query.message.reply_text(f"❌ Error: {str(e)}")
        return

    if data == "export_excel":
        await query.answer("Generating Excel...")
        try:
            file_path = report_gen.generate_excel()
            await query.message.reply_document(
                document=open(file_path, 'rb'),
                caption="📊 Laporan Keuangan (Excel)"
            )
        except Exception as e:
            await query.message.reply_text(f"❌ Error: {str(e)}")
        return

    # ── RESET DATA ──
    if data == "menu_reset_data":
        keyboard = [
            [
                InlineKeyboardButton("✅ Ya, Hapus Semua", callback_data="reset_data_confirm"),
                InlineKeyboardButton("❌ Batal", callback_data="back_to_main")
            ]
        ]
        await query.answer()
        await safe_edit(
            query,
            "⚠️ *RESET DATA*\n\n"
            "Yakin hapus semua data?\n\n"
            "Ini akan menghapus:\n"
            "• Semua transaksi\n"
            "• Semua notes\n"
            "• Custom categories (default categories tetap ada)\n\n"
            "❗ *Tindakan ini TIDAK BISA dibatalkan!*",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "reset_data_confirm":
        try:
            db.cursor.execute("DELETE FROM transactions")
            db.cursor.execute("DELETE FROM notes")
            db.cursor.execute("DELETE FROM categories WHERE is_default = 0")
            db.conn.commit()
            await query.answer("✅ Data dihapus!")
            await safe_edit(
                query,
                "✅ *Semua data berhasil dihapus!*\n\n"
                "Database sudah bersih.\n"
                "Silakan mulai tracking dari awal.",
                reply_markup=InlineKeyboardMarkup([[get_home_button()]])
            )
        except Exception as e:
            await query.answer("❌ Error!")
            await safe_edit(
                query,
                f"❌ Error saat reset data:\n{str(e)}",
                reply_markup=InlineKeyboardMarkup([[get_home_button()]])
            )
        return

    # Default
    await query.answer("Unknown action")
