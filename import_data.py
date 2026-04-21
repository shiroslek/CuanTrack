#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cuan Track - Data Import Script
PRIVATE: For initial data migration only
Run this ONCE before starting the bot
"""

import sqlite3
from datetime import datetime
import os
import sys

# Try to import from config.py (Railway setup)
try:
    from config import DB_NAME
    print(f"✅ Using database path from config.py: {DB_NAME}")
except ImportError:
    # Fallback for local testing
    DB_NAME = "finbot.db"
    print(f"⚠️  config.py not found, using default: {DB_NAME}")

class DataImporter:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self.cursor = self.conn.cursor()
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema if not exists"""
        
        # Transactions table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount INTEGER NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Categories table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                is_default BOOLEAN DEFAULT 0,
                icon TEXT
            )
        """)
        
        # Notes table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Settings table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        self.conn.commit()
        print("✅ Database schema initialized")
    
    def import_income_transactions(self):
        """Import pemasukan data"""
        
        income_data = [
            ("2026-03-27", "10:00:00", "Saldo Awal (Starting Balance)", "Saldo Awal", 3808409),
            ("2026-04-04", "10:00:00", "Withdraw Polymarket", "Withdraw", 418527),
            ("2026-04-06", "10:00:00", "Withdraw Polymarket", "Withdraw", 421225),
            ("2026-04-08", "10:00:00", "Dana tambahan", "Dana Tambahan", 2090000),
            ("2026-04-12", "10:00:00", "Freelance", "Freelance", 73000),
            ("2026-04-18", "10:00:00", "Pemasukan Joki", "Freelance", 300000),
            ("2026-04-19", "10:00:00", "Pendapatan Domino", "Lainnya", 5000),
            ("2026-04-19", "11:00:00", "Pendapatan Joki", "Freelance", 75000),
            ("2026-04-19", "12:00:00", "Pendapatan Joki", "Freelance", 60000),
        ]
        
        for date, time, description, category, amount in income_data:
            self.cursor.execute("""
                INSERT INTO transactions (date, time, type, category, amount, description)
                VALUES (?, ?, 'income', ?, ?, ?)
            """, (date, time, category, amount, description))
        
        self.conn.commit()
        print(f"✅ Imported {len(income_data)} income transactions")
    
    def import_expense_transactions(self):
        """Import pengeluaran data"""
        
        expense_data = [
            ("2026-03-27", "10:00:00", "Meutangi Aji rokok", "Piutang", 27000),
            ("2026-03-27", "11:00:00", "Alokasi dana tambahan", "Alokasi Khusus", 1786106),
            ("2026-03-28", "10:00:00", "Penyelesaian listrik", "Tagihan Rutin", 50000),
            ("2026-03-28", "11:00:00", "Beli rokok purple taste", "Rokok/Vape", 23000),
            ("2026-03-28", "12:00:00", "Kopsus 2, mineral 2", "Nongkrong", 36000),
            ("2026-03-28", "13:00:00", "Beli nasi gila bts", "Makanan", 25000),
            ("2026-03-28", "14:00:00", "Parkir nordu", "Transportasi", 4000),
            ("2026-03-29", "10:00:00", "ShopeeFood ayam geprek", "Makanan", 32000),
            ("2026-03-30", "10:00:00", "Ayam geprek", "Makanan", 10000),
            ("2026-03-30", "11:00:00", "Beli rokok purple taste", "Rokok/Vape", 23000),
            ("2026-03-31", "10:00:00", "Beli geprek 2 porsi", "Makanan", 20000),
            ("2026-03-31", "11:00:00", "Gacoan", "Makanan", 29000),
            ("2026-04-01", "10:00:00", "Penyelesaian biaya kos", "Tempat Tinggal", 500000),
            ("2026-04-01", "11:00:00", "Nasi kuning", "Makanan", 13000),
            ("2026-04-01", "12:00:00", "Bensin", "Transportasi", 12000),
            ("2026-04-01", "13:00:00", "Cimory", "Makanan", 10000),
            ("2026-04-01", "14:00:00", "Pentol", "Makanan", 10000),
            ("2026-04-01", "15:00:00", "Alokasi Dana PM", "Investasi", 459000),
            ("2026-04-01", "16:00:00", "Rokok Purple taste", "Rokok/Vape", 24000),
            ("2026-04-01", "17:00:00", "Redvelvet", "Nongkrong", 25000),
            ("2026-04-01", "18:00:00", "Parkir", "Transportasi", 2000),
            ("2026-04-01", "19:00:00", "Nasi ayam", "Makanan", 15000),
            ("2026-04-02", "10:00:00", "Naskun", "Makanan", 14000),
            ("2026-04-02", "11:00:00", "Nasi campur", "Makanan", 10000),
            ("2026-04-02", "12:00:00", "Minuman API", "Makanan", 42500),
            ("2026-04-02", "13:00:00", "Penyelesaian PDAM", "Tagihan Rutin", 26000),
            ("2026-04-03", "10:00:00", "Gacoan", "Makanan", 50000),
            ("2026-04-03", "11:00:00", "Mineral + mitos goreng", "Makanan", 22000),
            ("2026-04-03", "12:00:00", "Parkir dua asa", "Transportasi", 2000),
            ("2026-04-04", "10:00:00", "Bensin", "Transportasi", 12000),
            ("2026-04-04", "11:00:00", "Mie ayam + air es", "Makanan", 14000),
            ("2026-04-04", "12:00:00", "Purple taste", "Rokok/Vape", 23000),
            ("2026-04-04", "13:00:00", "Teh pucuk", "Makanan", 4000),
            ("2026-04-04", "14:00:00", "Tiket domino", "Hiburan", 15000),
            ("2026-04-04", "15:00:00", "Burger + jus mangga", "Makanan", 20000),
            ("2026-04-04", "16:00:00", "ShopeeFood ayam mak dura", "Makanan", 33000),
            ("2026-04-05", "10:00:00", "Beli es teh", "Makanan", 3000),
            ("2026-04-05", "11:00:00", "Beli rokok purple taste", "Rokok/Vape", 23000),
            ("2026-04-05", "12:00:00", "Beli redvelvet", "Nongkrong", 25000),
            ("2026-04-05", "13:00:00", "Beli bakmi ayam", "Makanan", 20000),
            ("2026-04-05", "14:00:00", "Bayar parkir", "Transportasi", 2000),
            ("2026-04-05", "15:00:00", "Meutangi Pai rokok", "Piutang", 23000),
            ("2026-04-05", "16:00:00", "Meutangi Pai bakmi", "Piutang", 20000),
            ("2026-04-05", "17:00:00", "Meutangi Pai matcha", "Piutang", 22000),
            ("2026-04-06", "10:00:00", "Beli burger", "Makanan", 20000),
            ("2026-04-06", "11:00:00", "Sabun muka Kahf", "Skincare/Suplemen", 34000),
            ("2026-04-06", "12:00:00", "Beli geprek", "Makanan", 10000),
            ("2026-04-06", "13:00:00", "Serum Elsheskin", "Skincare/Suplemen", 55000),
            ("2026-04-06", "14:00:00", "Meprothion box", "Skincare/Suplemen", 234000),
            ("2026-04-06", "15:00:00", "Newlab C-Gluta", "Skincare/Suplemen", 164000),
            ("2026-04-06", "16:00:00", "Dbesto gofood", "Makanan", 30000),
            ("2026-04-07", "10:00:00", "Beli burger", "Makanan", 10000),
            ("2026-04-07", "11:00:00", "Beli geprek", "Makanan", 10000),
            ("2026-04-07", "12:00:00", "Rokok click purple", "Rokok/Vape", 23000),
            ("2026-04-07", "13:00:00", "Pisang keju", "Makanan", 15000),
            ("2026-04-07", "14:00:00", "Jus sirsak", "Makanan", 5000),
            ("2026-04-07", "15:00:00", "Beli galon", "Makanan", 8000),
            ("2026-04-07", "16:00:00", "Mie ayam", "Makanan", 18000),
            ("2026-04-07", "17:00:00", "Beli odol", "Lainnya", 5000),
            ("2026-04-08", "10:00:00", "Ice roast + cemilan", "Nongkrong", 29000),
            ("2026-04-08", "11:00:00", "Beli geprek", "Makanan", 10000),
            ("2026-04-08", "12:00:00", "Beli bensin", "Transportasi", 40000),
            ("2026-04-08", "13:00:00", "Beli mie ayam", "Makanan", 14000),
            ("2026-04-08", "14:00:00", "Beli gacoan", "Makanan", 33000),
            ("2026-04-08", "15:00:00", "Meutangi Fai gacoan", "Piutang", 42000),
            ("2026-04-09", "10:00:00", "Alokasi Claude + admin", "Tagihan Rutin", 60000),
            ("2026-04-09", "11:00:00", "Naik gojek", "Transportasi", 18000),
            ("2026-04-09", "12:00:00", "Beli geprek", "Makanan", 10000),
            ("2026-04-09", "13:00:00", "Biaya gojek", "Transportasi", 21500),
            ("2026-04-09", "14:00:00", "Admin top up Gopay", "Lainnya", 3000),
            ("2026-04-09", "15:00:00", "Rokok + mie", "Rokok/Vape", 24000),
            ("2026-04-10", "10:00:00", "Beli mie", "Makanan", 5000),
            ("2026-04-10", "11:00:00", "Naik gojek", "Transportasi", 19500),
            ("2026-04-11", "10:00:00", "Beli dcelup", "Makanan", 24000),
            ("2026-04-11", "11:00:00", "Beli rokok", "Rokok/Vape", 23000),
            ("2026-04-11", "12:00:00", "Beli americano", "Nongkrong", 22000),
            ("2026-04-11", "13:00:00", "Makan di koe", "Makanan", 37000),
            ("2026-04-11", "14:00:00", "Beef teriyaki", "Makanan", 37000),
            ("2026-04-11", "15:00:00", "Beli dom", "Hiburan", 4000),
            ("2026-04-11", "16:00:00", "Mineral", "Makanan", 13500),
            ("2026-04-11", "17:00:00", "Penyelesaian transaksi Fai", "Alokasi Khusus", 4000),
            ("2026-04-12", "10:00:00", "Beli lele nasi", "Makanan", 10000),
            ("2026-04-12", "11:00:00", "Rokok", "Rokok/Vape", 25000),
            ("2026-04-12", "12:00:00", "Dcelup nasi", "Makanan", 24000),
            ("2026-04-12", "13:00:00", "Penyelesaian kamar", "Tempat Tinggal", 75000),
            ("2026-04-12", "14:00:00", "Beli kuota", "Tagihan Rutin", 80000),
            ("2026-04-12", "15:00:00", "Pentol/minum/kereta", "Makanan", 30000),
            ("2026-04-12", "16:00:00", "Extrajoss susu", "Makanan", 8000),
            ("2026-04-12", "17:00:00", "Surya isi 12", "Rokok/Vape", 30000),
            ("2026-04-13", "10:00:00", "Tiket Tahura", "Hiburan", 15000),
            ("2026-04-13", "11:00:00", "Makan", "Makanan", 30000),
            ("2026-04-13", "12:00:00", "Bensin", "Transportasi", 50000),
            ("2026-04-13", "13:00:00", "Pentol", "Makanan", 10000),
            ("2026-04-13", "14:00:00", "Bebek Sinjay", "Makanan", 25000),
            ("2026-04-14", "10:00:00", "Ayam Ganja", "Makanan", 15000),
            ("2026-04-14", "11:00:00", "Gojek", "Transportasi", 19000),
            ("2026-04-14", "12:00:00", "Geprek", "Makanan", 10000),
            ("2026-04-14", "13:00:00", "Gojek", "Transportasi", 21500),
            ("2026-04-14", "14:00:00", "Rokok", "Rokok/Vape", 21000),
            ("2026-04-15", "10:00:00", "Gojek", "Transportasi", 18500),
            ("2026-04-15", "11:00:00", "Minuman dan bilahan", "Makanan", 7000),
            ("2026-04-15", "12:00:00", "Excel click white", "Rokok/Vape", 21000),
            ("2026-04-15", "13:00:00", "Grab", "Transportasi", 16000),
            ("2026-04-15", "14:00:00", "Perbaikan motor", "Kendaraan", 240000),
            ("2026-04-15", "15:00:00", "Creamy coffee", "Nongkrong", 25000),
            ("2026-04-15", "16:00:00", "Pentol", "Makanan", 10000),
            ("2026-04-15", "17:00:00", "Parkir", "Transportasi", 2000),
            ("2026-04-16", "10:00:00", "Beli geprek", "Makanan", 10000),
            ("2026-04-16", "11:00:00", "Beli click purple", "Rokok/Vape", 23000),
            ("2026-04-16", "12:00:00", "Minuman nordu + nasi gila", "Makanan", 55000),
            ("2026-04-16", "13:00:00", "Parkir nordu", "Transportasi", 2000),
            ("2026-04-17", "10:00:00", "Beli pentol (pagi)", "Makanan", 6000),
            ("2026-04-17", "11:00:00", "Infaq Jum'at", "Lainnya", 1000),
            ("2026-04-17", "12:00:00", "Beli pentol (sore)", "Makanan", 10000),
            ("2026-04-17", "13:00:00", "Beli minuman latte bitten", "Makanan", 21000),
            ("2026-04-17", "14:00:00", "Bayar parkir", "Transportasi", 2000),
            ("2026-04-17", "15:00:00", "Beli nasi ayam", "Makanan", 10000),
            ("2026-04-18", "10:00:00", "Beli Claude AI Pro", "Tagihan Rutin", 350000),
            ("2026-04-18", "11:00:00", "Beli Nescafe kaleng", "Makanan", 7000),
            ("2026-04-18", "12:00:00", "Cek Turnitin (Sesi 1)", "Lainnya", 6000),
            ("2026-04-18", "13:00:00", "Bayar print-an", "Lainnya", 18000),
            ("2026-04-18", "14:00:00", "Cek Turnitin (Sesi 2)", "Lainnya", 2500),
            ("2026-04-18", "15:00:00", "Beli mie ayam", "Makanan", 13000),
            ("2026-04-18", "16:00:00", "Belikan bapak kuota", "Lainnya", 77000),
            ("2026-04-18", "17:00:00", "Beli rokok", "Rokok/Vape", 24000),
            ("2026-04-18", "18:00:00", "Beli makan", "Makanan", 10000),
            ("2026-04-18", "19:00:00", "Beli americano", "Nongkrong", 15000),
            ("2026-04-18", "20:00:00", "Dana tidak ingat", "Lainnya", 8000),
            ("2026-04-19", "10:00:00", "Beli makan", "Makanan", 12000),
            ("2026-04-19", "11:00:00", "Beli Redvelvet Neir", "Makanan", 17000),
            ("2026-04-20", "10:00:00", "Bayar parkir Neir (2 orang)", "Transportasi", 5000),
            ("2026-04-20", "11:00:00", "Beli nasi campur", "Makanan", 11000),
            ("2026-04-20", "12:00:00", "Beli geprek", "Makanan", 10000),
            ("2026-04-20", "13:00:00", "Kahf Water Based Pomade 70g", "Skincare/Suplemen", 33604),
            ("2026-04-20", "14:00:00", "Makarizo Hair Energy Shampoo", "Skincare/Suplemen", 26500),
            ("2026-04-20", "15:00:00", "VIVA Milk Cleanser Lemon 100ml", "Skincare/Suplemen", 11191),
            ("2026-04-20", "16:00:00", "Kapas Sariayu 50gr", "Skincare/Suplemen", 21000),
            ("2026-04-20", "17:00:00", "SR12 Deodorant Spray Tawas", "Skincare/Suplemen", 60500),
            ("2026-04-20", "18:00:00", "Gentle Gen Deterjen Cair", "Lainnya", 15000),
            ("2026-04-20", "19:00:00", "2 Tiket Bioskop \"Ayah Ini Arahnya Ke Mana Ya?\"", "Hiburan", 108400),
            ("2026-04-20", "20:00:00", "2 Minuman Hopes + Parkir", "Nongkrong", 60000),
            ("2026-04-20", "21:00:00", "Beli rokok", "Rokok/Vape", 25000),
            ("2026-04-20", "22:00:00", "Beli siomay", "Makanan", 10000),
            ("2026-04-20", "23:00:00", "Uang hilang", "Lainnya", 14000),
            ("2026-04-20", "23:30:00", "Meutangi Adit (Geprek)", "Piutang", 10000),
        ]
        
        for date, time, description, category, amount in expense_data:
            self.cursor.execute("""
                INSERT INTO transactions (date, time, type, category, amount, description)
                VALUES (?, ?, 'expense', ?, ?, ?)
            """, (date, time, category, amount, description))
        
        self.conn.commit()
        print(f"✅ Imported {len(expense_data)} expense transactions")
    
    def import_notes(self):
        """Import notes"""
        
        notes_data = [
            "Piutang: Aji Rp10.000",
            "Piutang: Adit Rp10.000 (Geprek)",
            "Alokasi Admin Tambahan: Rp2.298.000 (Pengingat, belum dikurangi dari saldo operasional)"
        ]
        
        for note in notes_data:
            self.cursor.execute("""
                INSERT INTO notes (description)
                VALUES (?)
            """, (note,))
        
        self.conn.commit()
        print(f"✅ Imported {len(notes_data)} notes")
    
    def verify_balance(self):
        """Verify final balance"""
        
        # Get total income
        self.cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'income'")
        total_income = self.cursor.fetchone()[0]
        
        # Get total expense
        self.cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'expense'")
        total_expense = self.cursor.fetchone()[0]
        
        # Calculate balance
        balance = total_income - total_expense
        
        print("\n" + "="*50)
        print("📊 VERIFICATION REPORT")
        print("="*50)
        print(f"💰 Total Pemasukan:  Rp{total_income:,}".replace(",", "."))
        print(f"💸 Total Pengeluaran: Rp{total_expense:,}".replace(",", "."))
        print(f"💳 Saldo Akhir:       Rp{balance:,}".replace(",", "."))
        print("="*50)
        
        expected_balance = 597360
        
        if balance == expected_balance:
            print("✅ SALDO COCOK! Import berhasil!")
            print("📝 Note: Saldo ini adalah hasil import apa adanya dari data Anda")
        else:
            print(f"⚠️  SALDO TIDAK COCOK!")
            print(f"   Expected: Rp{expected_balance:,}".replace(",", "."))
            print(f"   Got:      Rp{balance:,}".replace(",", "."))
            print(f"   Diff:     Rp{abs(balance - expected_balance):,}".replace(",", "."))
        
        print("\n")
    
    def run_import(self):
        """Run full import process"""
        
        print("\n" + "="*50)
        print("🚀 STARTING DATA IMPORT")
        print("="*50 + "\n")
        
        # Check if data already exists
        self.cursor.execute("SELECT COUNT(*) FROM transactions")
        existing_count = self.cursor.fetchone()[0]
        
        if existing_count > 0:
            print(f"⚠️  WARNING: Database already has {existing_count} transactions!")
            response = input("Continue anyway? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Import cancelled")
                return
        
        # Import data
        self.import_income_transactions()
        self.import_expense_transactions()
        self.import_notes()
        
        # Verify
        self.verify_balance()
        
        print("✅ Import complete!")
        print("\n💡 You can now start the bot with: python bot.py")
    
    def close(self):
        """Close database connection"""
        self.conn.close()

if __name__ == '__main__':
    print("""
╔═══════════════════════════════════════════════════════╗
║       CUAN TRACK - DATA IMPORT UTILITY                ║
║       Private script for initial data migration       ║
╚═══════════════════════════════════════════════════════╝
""")
    
    importer = DataImporter()
    
    try:
        importer.run_import()
    except Exception as e:
        print(f"\n❌ ERROR during import: {e}")
        import traceback
        traceback.print_exc()
    finally:
        importer.close()
