# 💰 Cuan Track by Shiroslek

**Version 2.1** - Modern Telegram Bot for Personal Finance Tracking

---

## 🚀 Quick Deploy (Railway.app - FREE!)

1. Upload all files to Github repo
2. Connect to Railway.app
3. Add Volume: `/app/data`
4. Update config.py: `DB_NAME = "/app/data/finbot.db"`
5. Deploy! ✅

**Deployment time: ~30 minutes**

---

## ✨ Features

### Core
- 💰 Income & Expense Tracking (step-by-step)
- ✏️ Edit/Delete Transactions (with calendar)
- 📊 Reports (PDF & Excel synced)
- 📓 Simple Notes
- ⚙️ Dynamic Categories (add/edit/delete)
- ⚠️ Reset Data (with confirmation)

### Reports Include
- ✅ Tabel Pemasukan + Total
- ✅ Tabel Pengeluaran + Total
- ✅ Summary Saldo
- ✅ Daftar Notes
- ✅ 2 Pie Charts (Income & Expense with percentages)

---

## 📱 How to Use

### Input Flow
1. Click "💰 Catat Pemasukan" or "💸 Catat Pengeluaran"
2. Select category
3. Enter description
4. Enter amount (must use dots: `50.000`)
5. Done! ✅

### Edit Transaction
1. Click "✏️ Edit Transaksi"
2. Select date from calendar
3. Select transaction
4. Edit or Delete

### Reset Data
1. Click "⚠️ Reset Data"
2. Confirm deletion
3. All data cleared (except default categories)

---

## 💾 Amount Format

✅ CORRECT:
- 50.000
- 1.500.000
- 250.000

❌ WRONG:
- 50,000 (comma)
- 50k (suffix)
- 50rb (abbreviation)

**Use dots for thousands separator!**

---

## 📂 Project Files

```
bot.py                  # Main entry
config.py               # Settings & categories
database.py             # SQLite operations
handlers.py             # All bot handlers
parser.py               # Amount validation
calculator.py           # Balance calculations
report_generator.py     # PDF & Excel
chart_generator.py      # Pie charts
```

---

## 🆕 What's New in v2.1

1. 🏠 Home button everywhere
2. ⚠️ Reset Data feature
3. 📊 Dual pie charts (income + expense)
4. 📄 Synced PDF/Excel format
5. Updated placeholder text
6. Refined default categories

See CHANGELOG.md for details.

---

## 🛠️ Tech Stack

- Python 3.11
- python-telegram-bot 20.7
- SQLite3
- Matplotlib
- ReportLab (PDF)
- openpyxl (Excel)

---

## 📊 Database Schema

Tables:
- transactions (date, type, category, amount, description)
- categories (name, type, icon, is_default)
- notes (description, created_at)
- settings (key, value)

---

## 🔐 Security

- Never commit bot token to public repos
- Use Railway environment variables
- Set repo to private
- Regenerate token after testing

---

## 🐛 Troubleshooting

**Bot not responding?**
- Check Railway logs
- Verify bot token
- Check @BotFather status

**Database resets?**
- Ensure Volume mounted: /app/data
- Check DB_NAME path in config.py

**Invalid amount format?**
- Must use dots: 50.000
- No commas, no suffixes

---

## 📞 Support

- Bot: @ShirosTrackBot
- Developer: Shiroslek

---

## 📄 License

Personal use. Modify as needed!

---

**Made with ❤️ by Shiroslek**
*v2.1 - April 21, 2026*
