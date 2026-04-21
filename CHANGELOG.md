# 📋 CHANGELOG - Cuan Track v2.1

## 🎉 VERSION 2.1 - April 21, 2026

### ✨ NEW FEATURES

1. **🏠 Home Button Navigation**
   - Added global "🏠 Home" button to all bot responses
   - Consistent navigation across all features

2. **⚠️ Reset Data Feature**
   - New "Reset Data" option in main menu
   - Confirmation dialog before deletion
   - Deletes: transactions, notes, custom categories
   - Preserves: default categories

3. **📊 Dual Pie Charts**
   - Separate charts for income & expense
   - Percentages shown in legends
   - Green (income) / Red (expense) color schemes

4. **📄 Synced PDF/Excel Reports**
   - Identical structure in both formats
   - Tables: Pemasukan, Pengeluaran, Summary Saldo, Notes
   - Professional formatting

### 🔧 IMPROVEMENTS

1. **Placeholder Text Updates**
   - Income: "Gaji bulanan, Jual Biawak, Profit Trading, dll"
   - Expense: "Beli geprek, Beli Ginjal, Hilang Di curi"

2. **Default Categories Refined**
   - Income (6): Starting Balance, Gaji, Freelance, Withdraw, Piutang, Lainnya
   - Expense (10): Belanja, Nongkrong, Kesehatan, Tempat Tinggal, Makan & Minum, Transportasi, Tagihan Rutin, Investasi, Utang, Lainnya

### 📁 FILES CHANGED
- config.py
- handlers.py (+60 lines)
- chart_generator.py (rewrite)
- report_generator.py (rewrite)

### 🔄 UPGRADE FROM V2.0
- 100% database compatible
- No data migration needed
- Just replace files & redeploy!

---

Full details in README.md
