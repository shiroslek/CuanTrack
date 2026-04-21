#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cuan Track Bot - Command Handlers
Complete redesign with step-by-step flow
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
    
    # Save admin user ID
    db.set_setting('admin_user_id', str(user.id))
    
    welcome_text = f"""
🎉 *Selamat Datang di {BOT_NAME}!*

Halo {user.first_name}! 👋

Silakan pilih menu di bawah:
"""
    
    # Create main menu keyboard
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
    
    # Get categories
    categories = db.get_categories(trans_type)
    
    if not categories:
        await query.edit_message_text(
            f"❌ Belum ada kategori {trans_type}. Tambahkan di Settings."
        )
        return
    
    # Create grid keyboard (2 columns)
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
    
    # Add remaining button
    if row:
        keyboard.append(row)
    
    # Add back button
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
    
    # Store in user data
    context.user_data['pending_transaction'] = {
        'type': trans_type,
        'category': category,
        'step': 'waiting_description'
    }
    
    # Get category info
    cat_info = db.get_category_by_name(category)
    icon = cat_info['icon'] if cat_info else "📌"
    
    # Get example text based on type
    example_text = INCOME_EXAMPLE_TEXT if trans_type == 'income' else EXPENSE_EXAMPLE_TEXT
    
    await query.edit_message_text(
        f"{icon} *{category}*\n\nMasukkan keterangan:\n(Contoh: {example_text})",
        parse_mode='Markdown'
    )

async def handle_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text message input during transaction flow"""
    
    text = update.message.text.strip()
    
    # Check if user is in transaction flow
    if 'pending_transaction' not in context.user_data:
        await update.message.reply_text(
            "Gunakan /start untuk memulai atau pilih menu dari tombol."
        )
        return
    
    pending = context.user_data['pending_transaction']
    step = pending.get('step')
    
    if step == 'waiting_description':
        # Store description, ask for amount
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
        # Validate and save transaction
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
        
        # Save transaction
        date = get_today()
        time = get_now_time()
        
        db.add_transaction(
            date, time, 
            pending['type'], 
            pending['category'],
            amount, 
            pending['description']
        )
        
        # Calculate new saldo
        saldo_info = calc.get_saldo_info()
        
        trans_name = "Pemasukan" if pending['type'] == 'income' else "Pengeluaran"
        icon = "💰" if pending['type'] == 'income' else "💸"
        
        # Clear pending transaction
        del context.user_data['pending_transaction']
        
        # Show success message with menu
        success_text = f"""
✅ *{trans_name} Tercatat!*

{icon} {format_rupiah(amount)}
📂 {pending['category']}
📝 {pending['description']}

💳 Saldo: *{format_rupiah(saldo_info['saldo'])}*
"""
        
        # Add back to menu button
        keyboard = [[InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            success_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif step == 'waiting_note':
        # Handle note input
        db.add_note(text)
        
        del context.user_data['pending_transaction']
        
        keyboard = [[InlineKeyboardButton("« Kembali ke Notes", callback_data="menu_notes")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ *Note tersimpan!*\n\n📝 {text}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif step == 'waiting_category_name':
        # Handle new category name
        pending['new_category_name'] = text
        pending['step'] = 'select_emoji'
        context.user_data['pending_transaction'] = pending
        
        # Show emoji selection
        await show_emoji_selection(update, context)
    
    elif step == 'waiting_edit_description':
        # Handle edit description
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
        # Handle edit amount
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
    
    # Get unique dates (last 30 days)
    dates = db.get_unique_dates(30)
    
    if not dates:
        await query.edit_message_text(
            "❌ Belum ada transaksi.\n\nGunakan /start untuk kembali."
        )
        return
    
    # Create date selection keyboard
    keyboard = []
    
    for date in dates[:10]:  # Show last 10 dates
        # Format date nicely
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
    
    transactions = db.get_transactions_by_date(date)
    
    if not transactions:
        await query.edit_message_text(
            f"❌ Tidak ada transaksi pada {date}"
        )
        return
    
    # Create transaction selection keyboard
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
    
    # Format date nicely
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
    
    # Show transaction details with options
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

# TO BE CONTINUED IN NEXT FILE...
# ==================== CALENDAR DATE PICKER ====================

async def show_date_picker(update: Update, context: ContextTypes.DEFAULT_TYPE, trans_id: int):
    """Show calendar for date selection"""
    
    query = update.callback_query
    await query.answer()
    
    # Store transaction ID for later
    context.user_data['editing_trans_id'] = trans_id
    
    # Get current month
    now = datetime.now(TIMEZONE)
    year = now.year
    month = now.month
    
    # Show calendar keyboard
    await show_calendar_month(query, year, month, f"edit_date_pick_{trans_id}")

async def show_calendar_month(query, year: int, month: int, callback_prefix: str):
    """Generate calendar keyboard for month"""
    
    # Month name
    month_name = calendar.month_name[month]
    
    # Get calendar matrix
    cal = calendar.monthcalendar(year, month)
    
    keyboard = []
    
    # Header with month/year and navigation
    keyboard.append([
        InlineKeyboardButton("«", callback_data=f"cal_prev_{year}_{month}_{callback_prefix}"),
        InlineKeyboardButton(f"{month_name} {year}", callback_data="cal_ignore"),
        InlineKeyboardButton("»", callback_data=f"cal_next_{year}_{month}_{callback_prefix}")
    ])
    
    # Day headers
    day_header = [InlineKeyboardButton(d, callback_data="cal_ignore") 
                  for d in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]]
    keyboard.append(day_header)
    
    # Date buttons
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
    
    # Back button
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
    
    notes = db.get_all_notes()
    
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
    
    # Show notes with delete buttons
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
    
    # Refresh notes list
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
    
    # Create emoji grid (5 per row)
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
    
    saldo_info = calc.get_saldo_info()
    
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
    
    today = get_today()
    
    # Get today's data
    income_today = db.get_total_by_type('income', today, today)
    expense_today = db.get_total_by_type('expense', today, today)
    
    # Get overall
    saldo_info = calc.get_saldo_info()
    
    # Top spending today
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
    
    # Generate report text
    report_text = report_gen.generate_text_report()
    
    # Send report
    await query.message.reply_text(report_text, parse_mode='Markdown')
    
    # Generate and send charts
    try:
        chart_file = chart_gen.generate_pie_chart()
        if chart_file:
            await query.message.reply_photo(
                photo=open(chart_file, 'rb'),
                caption="📊 Distribusi Pengeluaran per Kategori"
            )
    except Exception as e:
        print(f"Error generating pie chart: {e}")
    
    try:
        trend_file = chart_gen.generate_trend_chart()
        if trend_file:
            await query.message.reply_photo(
                photo=open(trend_file, 'rb'),
                caption="📈 Trend Pengeluaran Harian"
            )
    except Exception as e:
        print(f"Error generating trend chart: {e}")
    
    # Export options
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

# TO BE CONTINUED IN PART 3 (CALLBACK HANDLER)
# ==================== CALLBACK HANDLER (Main Router) ====================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries from inline keyboards"""
    
    query = update.callback_query
    data = query.data
    
    # Ignore calendar ignore callbacks
    if data == "cal_ignore":
        await query.answer()
        return
    
    # ==================== MAIN MENU ====================
    
    if data == "back_to_main":
        # Show main menu
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
    
    if data.startswith("edit_date_pick_") and "_20" in data:
        # Date selected from calendar
        parts = data.split("_")
        trans_id = int(parts[3])
        new_date = parts[4]  # YYYY-MM-DD
        
        db.update_transaction(trans_id, date=new_date)
        
        await query.answer("✅ Tanggal diubah!")
        await query.edit_message_text(
            f"✅ Tanggal berhasil diubah ke {new_date}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Kembali ke Menu", callback_data="back_to_main")
            ]])
        )
        return
    
    # Calendar navigation
    if data.startswith("cal_prev_") or data.startswith("cal_next_"):
        parts = data.split("_")
        action = parts[1]  # prev or next
        year = int(parts[2])
        month = int(parts[3])
        callback_prefix = "_".join(parts[4:])
        
        if action == "prev":
            month -= 1
            if month < 1:
                month = 12
                year -= 1
        else:
            month += 1
            if month > 12:
                month = 1
                year += 1
        
        await show_calendar_month(query, year, month, callback_prefix)
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
    
    # ==================== SETTINGS ====================
    
    if data == "menu_settings":
        await show_settings_menu(update, context)
        return
    
    if data == "settings_categories":
        await show_category_management(update, context)
        return
    
    if data == "cat_add":
        # Ask for category type
        keyboard = [
            [InlineKeyboardButton("💰 Pemasukan", callback_data="cat_add_income")],
            [InlineKeyboardButton("💸 Pengeluaran", callback_data="cat_add_expense")],
            [InlineKeyboardButton("« Batal", callback_data="settings_categories")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.answer()
        await query.edit_message_text(
            "Pilih tipe kategori:",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("cat_add_"):
        cat_type = data.replace("cat_add_", "")
        
        await query.answer()
        await query.edit_message_text(
            f"Masukkan nama kategori {cat_type}:"
        )
        
        context.user_data['pending_transaction'] = {
            'step': 'waiting_category_name',
            'category_type': cat_type
        }
        return
    
    if data.startswith("emoji_"):
        emoji = data.replace("emoji_", "")
        
        pending = context.user_data.get('pending_transaction', {})
        
        if pending.get('step') == 'select_emoji':
            # Add category
            cat_name = pending['new_category_name']
            cat_type = pending['category_type']
            
            success = db.add_category(cat_name, cat_type, emoji)
            
            del context.user_data['pending_transaction']
            
            if success:
                await query.answer("✅ Kategori ditambahkan!")
                await query.edit_message_text(
                    f"✅ Kategori berhasil ditambahkan!\n\n{emoji} {cat_name}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Kembali", callback_data="settings_categories")
                    ]])
                )
            else:
                await query.answer("❌ Kategori sudah ada!")
                await query.edit_message_text(
                    "❌ Kategori dengan nama tersebut sudah ada!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Kembali", callback_data="settings_categories")
                    ]])
                )
        return
    
    if data == "cat_edit_select_type":
        keyboard = [
            [InlineKeyboardButton("💰 Pemasukan", callback_data="cat_edit_list_income")],
            [InlineKeyboardButton("💸 Pengeluaran", callback_data="cat_edit_list_expense")],
            [InlineKeyboardButton("« Batal", callback_data="settings_categories")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.answer()
        await query.edit_message_text(
            "Pilih tipe kategori yang ingin diedit:",
            reply_markup=reply_markup
        )
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
        
        keyboard.append([InlineKeyboardButton("« Batal", callback_data="settings_categories")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.answer()
        await query.edit_message_text(
            "Pilih kategori yang ingin diedit:",
            reply_markup=reply_markup
        )
        return
    
    if data == "cat_delete_select_type":
        keyboard = [
            [InlineKeyboardButton("💰 Pemasukan", callback_data="cat_delete_list_income")],
            [InlineKeyboardButton("💸 Pengeluaran", callback_data="cat_delete_list_expense")],
            [InlineKeyboardButton("« Batal", callback_data="settings_categories")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.answer()
        await query.edit_message_text(
            "Pilih tipe kategori yang ingin dihapus:",
            reply_markup=reply_markup
        )
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
        
        keyboard.append([InlineKeyboardButton("« Batal", callback_data="settings_categories")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.answer()
        await query.edit_message_text(
            "Pilih kategori yang ingin dihapus:",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("cat_delete_confirm_"):
        cat_name = data.replace("cat_delete_confirm_", "")
        
        success = db.delete_category(cat_name)
        
        if success:
            await query.answer("✅ Kategori dihapus!")
            await query.edit_message_text(
                f"✅ Kategori '{cat_name}' berhasil dihapus!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Kembali", callback_data="settings_categories")
                ]])
            )
        else:
            await query.answer("❌ Tidak bisa dihapus!")
            await query.edit_message_text(
                f"❌ Kategori '{cat_name}' tidak bisa dihapus\n(masih ada transaksi yang menggunakannya)",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("« Kembali", callback_data="settings_categories")
                ]])
            )
        return
    
    # ==================== SALDO, LAPORAN, RINGKASAN ====================
    
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
    
    # ==================== RESET DATA ====================
    
    if data == "menu_reset_data":
        # Show confirmation dialog
        keyboard = [
            [
                InlineKeyboardButton("✅ Ya, Hapus Semua", callback_data="reset_data_confirm"),
                InlineKeyboardButton("❌ Batal", callback_data="back_to_main")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.answer()
        await query.edit_message_text(
            "⚠️ *RESET DATA*\n\n"
            "Yakin hapus semua data?\n\n"
            "Ini akan menghapus:\n"
            "• Semua transaksi\n"
            "• Semua notes\n"
            "• Custom categories (default categories tetap ada)\n\n"
            "❗ *Tindakan ini TIDAK BISA dibatalkan!*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    if data == "reset_data_confirm":
        # Delete all data
        try:
            # Delete all transactions
            db.cursor.execute("DELETE FROM transactions")
            
            # Delete all notes
            db.cursor.execute("DELETE FROM notes")
            
            # Delete custom categories (keep default ones)
            db.cursor.execute("DELETE FROM categories WHERE is_default = 0")
            
            # Commit changes
            db.conn.commit()
            
            await query.answer("✅ Data dihapus!")
            await query.edit_message_text(
                "✅ *Semua data berhasil dihapus!*\n\n"
                "Database sudah bersih.\n"
                "Silakan mulai tracking dari awal.",
                reply_markup=InlineKeyboardMarkup([[get_home_button()]]),
                parse_mode='Markdown'
            )
        except Exception as e:
            await query.answer("❌ Error!")
            await query.edit_message_text(
                f"❌ Error saat reset data:\n{str(e)}",
                reply_markup=InlineKeyboardMarkup([[get_home_button()]])
            )
        
        return
    
    # Default - unknown callback
    await query.answer("Unknown action")
