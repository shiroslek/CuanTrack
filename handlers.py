#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cuan Track Bot - Command Handlers
v2.2 - Multi-user support (user_id passed to all db/calc calls)

NOTE: report_generator.py dan chart_generator.py juga perlu diupdate
      untuk menerima parameter user_id di method generate-nya.
      Contoh: generate_text_report(user_id), generate_pie_chart(user_id), dst.
"""

from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
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
    """Format number to rupiah"""
    return parser.format_rupiah(amount)

def get_today():
    """Get today's date in Jakarta timezone"""
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d")

def get_now_time():
    """Get current time in Jakarta timezone"""
    return datetime.now(TIMEZONE).strftime("%H:%M:%S")

def get_home_button():
    """Get home button for navigation"""
    return InlineKeyboardButton("🏠 Home", callback_data="back_to_main")

# ==================== START & HELP ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - Main menu with inline keyboard"""
    user = update.effective_user
    user_id = user.id

    db.set_setting(user_id, 'last_seen', str(datetime.now(TIMEZONE)))

    welcome_text = f"""
🎉 *Selamat Datang di {BOT_NAME}!*

Halo {user.first_name}! 👋

Silakan pilih menu di bawah:
"""

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

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = f"""
📚 *PANDUAN {BOT_NAME}*

*💰 Catat Pemasukan/Pengeluaran:*
1. Pilih kategori dari grid
2. Masukkan keterangan
3. Masukkan nominal dengan format titik
   Contoh: 50.000 atau 1.500.000

*📊 Laporan:*
Lihat laporan lengkap dengan grafik

*💳 Saldo:*
Cek saldo saat ini

*📝 Ringkasan:*
Summary singkat

*📓 Notes:*
Buat catatan penting

*✏️ Edit Transaksi:*
1. Pilih tanggal
2. Pilih transaksi
3. Edit atau Hapus

*⚙️ Settings:*
Kelola kategori & pengaturan lainnya

Ketik /start untuk kembali ke menu utama.
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ==================== INCOME/EXPENSE FLOW ====================

async def show_category_grid(update: Update, context: ContextTypes.DEFAULT_TYPE, trans_type: str):
    """Show category selection grid"""
    query = update.callback_query
    await query.answer()

    categories = db.get_categories(trans_type)

    if not categories:
        await query.edit_message_text(
            f"❌ Belum ada kategori {trans_type}. Tambahkan di Settings."
        )
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

    keyboard.append([InlineKeyboardButton("« Kembali", callback_data="back_to_main")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    icon = "💰" if trans_type == "income" else "💸"
    trans_name = "Pemasukan" if trans_type == "income" else "Pengeluaran"

    await query.edit_message_text(
        f"{icon} *CATAT {trans_name.upper()}*\n\nPilih kategori:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE, trans_type: str, category: str):
    """Handle category selection - ask for description"""
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

    await query.edit_message_text(
        f"{icon} *{category}*\n\nMasukkan keterangan:\n(Contoh: {example_text})",
        parse_mode='Markdown'
    )

async def handle_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text message input during transaction flow"""
    text = update.message.text.strip()
    user_id = update.effective_user.id

    if 'pending_transaction' not in context.user_data:
        await update.message.reply_text(
            "Gunakan /start untuk memulai atau pilih menu dari tombol."
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
                f"❌ {error_msg}\n\n"
                f"Contoh format yang benar:\n"
                f"• 50.000\n"
                f"• 1.500.000\n"
                f"• 250.000\n\n"
                f"Coba lagi:"
            )
            return

        amount = parser.parse_amount(text)

        date = get_today()
        time = get_now_time()

        db.add_transaction(
            user_id, date, time,
            pending['type'],
            pending['category'],
            amount,
            pending['description']
        )

        saldo_info = calc.get_saldo_info(user_id)
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

        keyboard = [[InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            success_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    elif step == 'waiting_note':
        db.add_note(user_id, text)
        del context.user_data['pending_transaction']

        keyboard = [[InlineKeyboardButton("« Kembali ke Notes", callback_data="menu_notes")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ *Note tersimpan!*\n\n📝 {text}",
            reply_markup=reply_markup,
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
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")
            ]])
        )

    elif step == 'waiting_edit_amount':
        is_valid, error_msg = parser.validate_amount_format(text)

        if not is_valid:
            await update.message.reply_text(
                f"❌ {error_msg}\n\nCoba lagi:"
            )
            return

        amount = parser.parse_amount(text)
        trans_id = pending['trans_id']
        db.update_transaction(trans_id, amount=amount)
        del context.user_data['pending_transaction']

        await update.message.reply_text(
            f"✅ Nominal berhasil diubah!\n\n💰 {format_rupiah(amount)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")
            ]])
        )

# ==================== EDIT TRANSACTION FLOW ====================

async def show_edit_transaction_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show edit transaction menu - select date"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    dates = db.get_unique_dates(user_id, 30)

    if not dates:
        await query.edit_message_text(
            "❌ Belum ada transaksi.\n\nGunakan /start untuk kembali."
        )
        return

    keyboard = []
    for date in dates[:10]:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_display = date_obj.strftime("%d %b %Y")
        keyboard.append([InlineKeyboardButton(
            f"📅 {date_display}",
            callback_data=f"edit_date_{date}"
        )])

    keyboard.append([InlineKeyboardButton("« Kembali", callback_data="back_to_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "✏️ *EDIT TRANSAKSI*\n\nPilih tanggal:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_transactions_by_date(update: Update, context: ContextTypes.DEFAULT_TYPE, date: str):
    """Show transactions for selected date"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    transactions = db.get_transactions_by_date(user_id, date)

    if not transactions:
        await query.edit_message_text(
            f"❌ Tidak ada transaksi pada {date}"
        )
        return

    keyboard = []
    for trans in transactions:
        icon = "💰" if trans['type'] == 'income' else "💸"
        label = f"{icon} {trans['category']} - {format_rupiah(trans['amount'])}"
        keyboard.append([InlineKeyboardButton(
            label,
            callback_data=f"edit_trans_{trans['id']}"
        )])

    keyboard.append([InlineKeyboardButton("« Kembali", callback_data="menu_edit")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    date_obj = datetime.strptime(date, "%Y-%m-%d")
    date_display = date_obj.strftime("%d %b %Y")

    await query.edit_message_text(
        f"📅 *{date_display}*\n\nPilih transaksi:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_transaction_options(update: Update, context: ContextTypes.DEFAULT_TYPE, trans_id: int):
    """Show edit/delete options for transaction"""
    query = update.callback_query
    await query.answer()

    trans = db.get_transaction_by_id(trans_id)

    if not trans:
        await query.edit_message_text("❌ Transaksi tidak ditemukan")
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
        [InlineKeyboardButton("« Kembali", callback_data=f"edit_date_{trans['date']}")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        details,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_edit_options(update: Update, context: ContextTypes.DEFAULT_TYPE, trans_id: int):
    """Show edit options - what to edit"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("📅 Tanggal", callback_data=f"edit_field_date_{trans_id}")],
        [InlineKeyboardButton("📝 Keterangan", callback_data=f"edit_field_desc_{trans_id}")],
        [InlineKeyboardButton("💰 Nominal", callback_data=f"edit_field_amount_{trans_id}")],
        [InlineKeyboardButton("« Kembali", callback_data=f"edit_trans_{trans_id}")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "Apa yang ingin diubah?",
        reply_markup=reply_markup
    )

# ==================== CALENDAR DATE PICKER ====================

async def show_date_picker(update: Update, context: ContextTypes.DEFAULT_TYPE, trans_id: int):
    """Show calendar for date selection"""
    query = update.callback_query
    await query.answer()

    context.user_data['editing_trans_id'] = trans_id

    now = datetime.now(TIMEZONE)
    year = now.year
    month = now.month

    await show_calendar_month(query, year, month, f"edit_date_pick_{trans_id}")

async def show_calendar_month(query, year: int, month: int, callback_prefix: str):
    """Generate calendar keyboard for month"""
    month_name = calendar.month_name[month]
    cal = calendar.monthcalendar(year, month)

    keyboard = []

    keyboard.append([
        InlineKeyboardButton("«", callback_data=f"cal_prev_{year}_{month}_{callback_prefix}"),
        InlineKeyboardButton(f"{month_name} {year}", callback_data="cal_ignore"),
        InlineKeyboardButton("»", callback_data=f"cal_next_{year}_{month}_{callback_prefix}")
    ])

    day_header = [InlineKeyboardButton(d, callback_data="cal_ignore")
                  for d in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]]
    keyboard.append(day_header)

    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="cal_ignore"))
            else:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                row.append(InlineKeyboardButton(
                    str(day),
                    callback_data=f"{callback_prefix}_{date_str}"
                ))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("« Batal", callback_data="menu_edit")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "📅 *Pilih Tanggal*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ==================== NOTES MENU ====================

async def show_notes_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show notes main menu"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("📝 Tambah Note", callback_data="notes_add")],
        [InlineKeyboardButton("📋 Lihat Semua Notes", callback_data="notes_list")],
        [InlineKeyboardButton("« Kembali", callback_data="back_to_main")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "📓 *NOTES*\n\nCatatan penting kamu:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def add_note_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to add note"""
    query = update.callback_query
    await query.answer()

    context.user_data['pending_transaction'] = {
        'step': 'waiting_note'
    }

    await query.edit_message_text(
        "📝 *TAMBAH NOTE*\n\nKetik catatan kamu:\n(Contoh: Reminder bayar listrik tanggal 25)",
        parse_mode='Markdown'
    )

async def show_notes_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all notes"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    notes = db.get_all_notes(user_id)

    if not notes:
        keyboard = [
            [InlineKeyboardButton("📝 Tambah Note", callback_data="notes_add")],
            [InlineKeyboardButton("« Kembali", callback_data="menu_notes")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "📋 Belum ada notes.\n\nTambah note pertama?",
            reply_markup=reply_markup
        )
        return

    text = "📋 *SEMUA NOTES*\n\n"
    keyboard = []

    for i, note in enumerate(notes, 1):
        text += f"{i}. {note['description']}\n"
        keyboard.append([
            InlineKeyboardButton(
                f"🗑️ Hapus Note {i}",
                callback_data=f"notes_delete_{note['id']}"
            )
        ])

    keyboard.append([InlineKeyboardButton("« Kembali", callback_data="menu_notes")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def delete_note_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, note_id: int):
    """Confirm and delete note"""
    query = update.callback_query
    await query.answer("Note dihapus!")

    db.delete_note(note_id)
    await show_notes_list(update, context)

# ==================== SETTINGS MENU ====================

async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings main menu"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("📂 Kelola Kategori", callback_data="settings_categories")],
        [InlineKeyboardButton("« Kembali", callback_data="back_to_main")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "⚙️ *SETTINGS*\n\nPilih menu:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_category_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show category management menu"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("➕ Tambah Kategori", callback_data="cat_add")],
        [InlineKeyboardButton("✏️ Edit Kategori", callback_data="cat_edit_select_type")],
        [InlineKeyboardButton("🗑️ Hapus Kategori", callback_data="cat_delete_select_type")],
        [InlineKeyboardButton("« Kembali", callback_data="menu_settings")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "📂 *KELOLA KATEGORI*\n\nPilih aksi:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_emoji_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show emoji selection grid"""
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
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Pilih emoji untuk kategori:",
        reply_markup=reply_markup
    )

# ==================== SALDO, LAPORAN, RINGKASAN ====================

async def show_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current balance"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    saldo_info = calc.get_saldo_info(user_id)

    text = f"""
💳 *SALDO*

💰 Saldo Saat Ini:
*{format_rupiah(saldo_info['saldo'])}*

Total Pemasukan: {format_rupiah(saldo_info['total_income'])}
Total Pengeluaran: {format_rupiah(saldo_info['total_expense'])}
"""

    keyboard = [[InlineKeyboardButton("« Kembali", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_ringkasan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show summary"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    today = get_today()

    income_today = db.get_total_by_type(user_id, 'income', today, today)
    expense_today = db.get_total_by_type(user_id, 'expense', today, today)

    saldo_info = calc.get_saldo_info(user_id)
    spending = db.get_spending_by_category(user_id, today, today)

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

    keyboard = [[InlineKeyboardButton("« Kembali", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_laporan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show full report"""
    query = update.callback_query
    await query.answer("Generating laporan...")
    user_id = query.from_user.id

    # NOTE: report_generator.py perlu diupdate untuk menerima user_id
    # Ubah method generate_text_report() menjadi generate_text_report(user_id)
    report_text = report_gen.generate_text_report(user_id)
    await query.message.reply_text(report_text, parse_mode='Markdown')

    # NOTE: chart_generator.py perlu diupdate untuk menerima user_id
    try:
        chart_file = chart_gen.generate_pie_chart(user_id)
        if chart_file:
            await query.message.reply_photo(
                photo=open(chart_file, 'rb'),
                caption="📊 Distribusi Pengeluaran per Kategori"
            )
    except Exception as e:
        print(f"Error generating pie chart: {e}")

    try:
        trend_file = chart_gen.generate_trend_chart(user_id)
        if trend_file:
            await query.message.reply_photo(
                photo=open(trend_file, 'rb'),
                caption="📈 Trend Pengeluaran Harian"
            )
    except Exception as e:
        print(f"Error generating trend chart: {e}")

    keyboard = [
        [
            InlineKeyboardButton("📄 Export PDF", callback_data="export_pdf"),
            InlineKeyboardButton("📊 Export Excel", callback_data="export_excel")
        ],
        [InlineKeyboardButton("« Kembali", callback_data="back_to_main")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "📥 *Export Laporan:*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# ==================== CALLBACK HANDLER (Main Router) ====================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries from inline keyboards"""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if data == "cal_ignore":
        await query.answer()
        return

    # ==================== MAIN MENU ====================

    if data == "back_to_main":
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
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.answer()
        await query.edit_message_text(
            f"🏠 *Menu Utama {BOT_NAME}*\n\nPilih menu:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return

    # ==================== INCOME/EXPENSE ====================

    if data == "menu_income":
        await show_category_grid(update, context, "income")
        return

    if data == "menu_expense":
        await show_category_grid(update, context, "expense")
        return

    if data.startswith("cat_income_"):
        category = data.replace("cat_income_", "")
        await handle_category_selected(update, context, "income", category)
        return

    if data.startswith("cat_expense_"):
        category = data.replace("cat_expense_", "")
        await handle_category_selected(update, context, "expense", category)
        return

    # ==================== EDIT TRANSACTION ====================

    if data == "menu_edit":
        await show_edit_transaction_menu(update, context)
        return

    if data.startswith("edit_date_") and not data.startswith("edit_date_pick"):
        date = data.replace("edit_date_", "")
        await show_transactions_by_date(update, context, date)
        return

    if data.startswith("edit_trans_"):
        trans_id = int(data.replace("edit_trans_", ""))
        await show_transaction_options(update, context, trans_id)
        return

    if data.startswith("edit_options_"):
        trans_id = int(data.replace("edit_options_", ""))
        await show_edit_options(update, context, trans_id)
        return

    if data.startswith("delete_confirm_"):
        trans_id = int(data.replace("delete_confirm_", ""))
        trans = db.get_transaction_by_id(trans_id)
        if trans:
            keyboard = [
                [
                    InlineKeyboardButton("✅ Ya, Hapus", callback_data=f"delete_yes_{trans_id}"),
                    InlineKeyboardButton("❌ Batal", callback_data=f"edit_trans_{trans_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.answer()
            await query.edit_message_text(
                f"⚠️ Yakin hapus transaksi ini?\n\n{format_rupiah(trans['amount'])} - {trans['category']}",
                reply_markup=reply_markup
            )
        return

    if data.startswith("delete_yes_"):
        trans_id = int(data.replace("delete_yes_", ""))
        db.delete_transaction(trans_id)
        await query.answer("✅ Transaksi dihapus!")
        await query.edit_message_text(
            "✅ Transaksi berhasil dihapus!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")
            ]])
        )
        return

    if data.startswith("edit_field_date_"):
        trans_id = int(data.replace("edit_field_date_", ""))
        await show_date_picker(update, context, trans_id)
        return

    if data.startswith("edit_field_desc_"):
        trans_id = int(data.replace("edit_field_desc_", ""))
        await query.answer()
        await query.edit_message_text("Masukkan keterangan baru:")
        context.user_data['pending_transaction'] = {
            'step': 'waiting_edit_description',
            'trans_id': trans_id
        }
        return

    if data.startswith("edit_field_amount_"):
        trans_id = int(data.replace("edit_field_amount_", ""))
        await query.answer()
        await query.edit_message_text(
            "Masukkan nominal baru (gunakan titik):\nContoh: 50.000"
        )
        context.user_data['pending_transaction'] = {
            'step': 'waiting_edit_amount',
            'trans_id': trans_id
        }
        return

    # Calendar date pick for edit
    if data.startswith("edit_date_pick_") and "_20" in data:
        parts = data.split("_")
        # Format: edit_date_pick_{trans_id}_{YYYY-MM-DD}
        date_str = parts[-1]
        trans_id = int(parts[3])
        db.update_transaction(trans_id, date=date_str)
        await query.answer("✅ Tanggal diubah!")
        await query.edit_message_text(
            f"✅ Tanggal berhasil diubah ke *{date_str}*",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")
            ]]),
            parse_mode='Markdown'
        )
        return

    # ==================== CALENDAR NAVIGATION ====================

    if data.startswith("cal_prev_"):
        # Format: cal_prev_{year}_{month}_{prefix}
        parts = data.split("_", 4)
        year = int(parts[2])
        month = int(parts[3])
        prefix = parts[4]

        month -= 1
        if month < 1:
            month = 12
            year -= 1

        await show_calendar_month(query, year, month, prefix)
        return

    if data.startswith("cal_next_"):
        parts = data.split("_", 4)
        year = int(parts[2])
        month = int(parts[3])
        prefix = parts[4]

        month += 1
        if month > 12:
            month = 1
            year += 1

        await show_calendar_month(query, year, month, prefix)
        return

    # ==================== NOTES ====================

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
        note_id = int(data.replace("notes_delete_", ""))
        await delete_note_confirm(update, context, note_id)
        return

    # ==================== LAPORAN, SALDO, RINGKASAN ====================

    if data == "menu_laporan":
        await show_laporan(update, context)
        return

    if data == "menu_saldo":
        await show_saldo(update, context)
        return

    if data == "menu_ringkasan":
        await show_ringkasan(update, context)
        return

    # ==================== EXPORT ====================

    if data == "export_pdf":
        await query.answer("Generating PDF...")
        try:
            # NOTE: report_generator.py perlu diupdate untuk menerima user_id
            pdf_file = report_gen.generate_pdf_report(user_id)
            if pdf_file:
                await query.message.reply_document(
                    document=open(pdf_file, 'rb'),
                    filename="laporan_keuangan.pdf",
                    caption="📄 Laporan Keuangan (PDF)"
                )
            else:
                await query.message.reply_text("❌ Gagal generate PDF.")
        except Exception as e:
            await query.message.reply_text(f"❌ Error: {str(e)}")
        return

    if data == "export_excel":
        await query.answer("Generating Excel...")
        try:
            # NOTE: report_generator.py perlu diupdate untuk menerima user_id
            excel_file = report_gen.generate_excel_report(user_id)
            if excel_file:
                await query.message.reply_document(
                    document=open(excel_file, 'rb'),
                    filename="laporan_keuangan.xlsx",
                    caption="📊 Laporan Keuangan (Excel)"
                )
            else:
                await query.message.reply_text("❌ Gagal generate Excel.")
        except Exception as e:
            await query.message.reply_text(f"❌ Error: {str(e)}")
        return

    # ==================== SETTINGS ====================

    if data == "menu_settings":
        await show_settings_menu(update, context)
        return

    if data == "settings_categories":
        await show_category_management(update, context)
        return

    # ==================== CATEGORY MANAGEMENT ====================

    if data == "cat_add":
        keyboard = [
            [
                InlineKeyboardButton("💰 Pemasukan", callback_data="cat_add_type_income"),
                InlineKeyboardButton("💸 Pengeluaran", callback_data="cat_add_type_expense")
            ],
            [InlineKeyboardButton("« Kembali", callback_data="settings_categories")]
        ]
        await query.answer()
        await query.edit_message_text(
            "➕ *TAMBAH KATEGORI*\n\nPilih jenis kategori:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    if data.startswith("cat_add_type_"):
        trans_type = data.replace("cat_add_type_", "")
        context.user_data['pending_transaction'] = {
            'step': 'waiting_category_name',
            'trans_type': trans_type
        }
        await query.answer()
        await query.edit_message_text(
            f"➕ Ketik nama kategori baru:"
        )
        return

    if data.startswith("emoji_"):
        emoji = data.replace("emoji_", "")
        pending = context.user_data.get('pending_transaction', {})
        cat_name = pending.get('new_category_name')
        trans_type = pending.get('trans_type')

        if cat_name and trans_type:
            success = db.add_category(cat_name, trans_type, emoji)
            if success:
                msg = f"✅ Kategori *{emoji} {cat_name}* berhasil ditambahkan!"
            else:
                msg = f"❌ Kategori *{cat_name}* sudah ada."

            del context.user_data['pending_transaction']

            await query.edit_message_text(
                msg,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Kembali ke Settings", callback_data="settings_categories")
                ]]),
                parse_mode='Markdown'
            )
        return

    if data == "cat_edit_select_type":
        keyboard = [
            [
                InlineKeyboardButton("💰 Pemasukan", callback_data="cat_edit_type_income"),
                InlineKeyboardButton("💸 Pengeluaran", callback_data="cat_edit_type_expense")
            ],
            [InlineKeyboardButton("« Kembali", callback_data="settings_categories")]
        ]
        await query.answer()
        await query.edit_message_text(
            "✏️ *EDIT KATEGORI*\n\nPilih jenis:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    if data.startswith("cat_edit_type_"):
        trans_type = data.replace("cat_edit_type_", "")
        categories = db.get_categories(trans_type)
        keyboard = []
        for cat in categories:
            keyboard.append([InlineKeyboardButton(
                f"{cat['icon']} {cat['name']}",
                callback_data=f"cat_edit_name_{cat['name']}"
            )])
        keyboard.append([InlineKeyboardButton("« Kembali", callback_data="cat_edit_select_type")])
        await query.answer()
        await query.edit_message_text(
            "Pilih kategori yang ingin diedit:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("cat_edit_name_"):
        cat_name = data.replace("cat_edit_name_", "")
        cat = db.get_category_by_name(cat_name)
        if cat:
            keyboard = [
                [InlineKeyboardButton("✏️ Ubah Nama", callback_data=f"cat_rename_{cat_name}")],
                [InlineKeyboardButton("🎨 Ubah Icon", callback_data=f"cat_reicon_{cat_name}")],
                [InlineKeyboardButton("« Kembali", callback_data=f"cat_edit_type_{cat['type']}")]
            ]
            await query.answer()
            await query.edit_message_text(
                f"Kategori: {cat['icon']} *{cat_name}*\n\nPilih aksi:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        return

    if data == "cat_delete_select_type":
        keyboard = [
            [
                InlineKeyboardButton("💰 Pemasukan", callback_data="cat_delete_type_income"),
                InlineKeyboardButton("💸 Pengeluaran", callback_data="cat_delete_type_expense")
            ],
            [InlineKeyboardButton("« Kembali", callback_data="settings_categories")]
        ]
        await query.answer()
        await query.edit_message_text(
            "🗑️ *HAPUS KATEGORI*\n\nPilih jenis:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    if data.startswith("cat_delete_type_"):
        trans_type = data.replace("cat_delete_type_", "")
        categories = [c for c in db.get_categories(trans_type) if not c['is_default']]
        if not categories:
            await query.answer("Tidak ada kategori custom yang bisa dihapus.", show_alert=True)
            return
        keyboard = []
        for cat in categories:
            keyboard.append([InlineKeyboardButton(
                f"{cat['icon']} {cat['name']}",
                callback_data=f"cat_delete_confirm_{cat['name']}"
            )])
        keyboard.append([InlineKeyboardButton("« Kembali", callback_data="cat_delete_select_type")])
        await query.answer()
        await query.edit_message_text(
            "Pilih kategori yang ingin dihapus:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("cat_delete_confirm_"):
        cat_name = data.replace("cat_delete_confirm_", "")
        keyboard = [
            [
                InlineKeyboardButton("✅ Ya, Hapus", callback_data=f"cat_delete_yes_{cat_name}"),
                InlineKeyboardButton("❌ Batal", callback_data="settings_categories")
            ]
        ]
        await query.answer()
        await query.edit_message_text(
            f"⚠️ Yakin hapus kategori *{cat_name}*?\n(Hanya bisa dihapus jika tidak ada transaksi)",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    if data.startswith("cat_delete_yes_"):
        cat_name = data.replace("cat_delete_yes_", "")
        success = db.delete_category(cat_name)
        if success:
            msg = f"✅ Kategori *{cat_name}* berhasil dihapus!"
        else:
            msg = f"❌ Tidak bisa hapus *{cat_name}* karena masih ada transaksi yang menggunakannya."
        await query.answer()
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Kembali ke Settings", callback_data="settings_categories")
            ]]),
            parse_mode='Markdown'
        )
        return

    # ==================== RESET DATA ====================

    if data == "menu_reset_data":
        keyboard = [
            [
                InlineKeyboardButton("⚠️ Ya, Lanjut", callback_data="reset_confirm"),
                InlineKeyboardButton("❌ Batal", callback_data="back_to_main")
            ]
        ]
        await query.answer()
        await query.edit_message_text(
            "⚠️ *RESET DATA*\n\nIni akan menghapus SEMUA transaksi dan notes kamu.\n\nYakin ingin melanjutkan?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    if data == "reset_confirm":
        keyboard = [
            [
                InlineKeyboardButton("🗑️ Ya, Hapus Semua!", callback_data="reset_yes"),
                InlineKeyboardButton("❌ Batal", callback_data="back_to_main")
            ]
        ]
        await query.answer()
        await query.edit_message_text(
            "🚨 *KONFIRMASI TERAKHIR*\n\nSemua data akan dihapus permanen dan tidak bisa dikembalikan!\n\nBenar-benar yakin?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    if data == "reset_yes":
        db.reset_user_data(user_id)
        await query.answer("✅ Data direset!")
        await query.edit_message_text(
            "✅ *Data berhasil direset!*\n\nSemua transaksi dan notes kamu telah dihapus.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Kembali ke Menu", callback_data="back_to_main")
            ]]),
            parse_mode='Markdown'
        )
        return

    # Fallback
    await query.answer()
