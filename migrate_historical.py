#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_historical.py
Script migrasi data keuangan historis untuk user: 6717489864

Cara pakai di Railway:
  railway run python migrate_historical.py

Atau jalankan lokal jika DB sudah didownload:
  python migrate_historical.py

Script ini AMAN dijalankan berkali-kali (idempotent) karena
cek dulu apakah data sudah ada sebelum insert.
"""

import sqlite3
import sys
import os

# ============================================================
# CONFIG - Sesuaikan jika path DB berbeda
# ============================================================
DB_PATH = os.environ.get("DB_NAME", "/app/data/finbot.db")
MY_USER_ID = 6717489864

# ============================================================
# PEMETAAN KATEGORI
# (kategori lama -> kategori default di bot)
# ============================================================
# Pemasukan
INCOME_CAT_MAP = {
    "Saldo Awal":    "Starting Balance",
    "Withdraw":      "Withdraw",
    "Dana Tambahan": "Lainnya",
    "Freelance":     "Freelance",
    "Lainnya":       "Lainnya",
}

# Pengeluaran
EXPENSE_CAT_MAP = {
    "Piutang":          "Utang",        # uang dipinjamkan ke orang
    "Alokasi Khusus":   "Lainnya",
    "Tagihan":          "Tagihan Rutin",
    "Rokok/Vape":       "Belanja",
    "Nongkrong":        "Nongkrong",
    "Makanan":          "Makan & Minum",
    "Transportasi":     "Transportasi",
    "Tempat Tinggal":   "Tempat Tinggal",
    "Investasi":        "Investasi",
    "Hiburan":          "Lainnya",
    "Skincare/Suplemen":"Kesehatan",
    "Lainnya":          "Lainnya",
    "Kendaraan":        "Lainnya",
    "Rokok/Makan":      "Makan & Minum",
    "Makanan/Transp":   "Makan & Minum",
}

# ============================================================
# DATA PEMASUKAN HISTORIS
# Format: (date, time, category_lama, description, amount)
# ============================================================
INCOME_DATA = [
    ("2026-03-27", "08:00:00", "Saldo Awal",    "Saldo Awal (Starting Balance)",  3_808_409),
    ("2026-04-04", "10:00:00", "Withdraw",       "Withdraw Polymarket",              418_527),
    ("2026-04-06", "10:00:00", "Withdraw",       "Withdraw Polymarket",              421_225),
    ("2026-04-08", "09:00:00", "Dana Tambahan",  "Dana tambahan",                  2_090_000),
    ("2026-04-12", "14:00:00", "Freelance",      "Freelance",                          73_000),
    ("2026-04-18", "16:00:00", "Freelance",      "Pemasukan Joki",                    300_000),
    ("2026-04-19", "10:00:00", "Lainnya",        "Pendapatan Domino",                   5_000),
    ("2026-04-19", "11:00:00", "Freelance",      "Pendapatan Joki",                    75_000),
    ("2026-04-19", "12:00:00", "Freelance",      "Pendapatan Joki",                    60_000),
]

# ============================================================
# DATA PENGELUARAN HISTORIS
# Format: (date, time, category_lama, description, amount)
# ============================================================
EXPENSE_DATA = [
    # 27 Mar
    ("2026-03-27", "09:00:00", "Piutang",        "Meutangi Aji rokok",               27_000),
    ("2026-03-27", "09:30:00", "Alokasi Khusus", "Alokasi dana tambahan",         1_786_106),
    # 28 Mar
    ("2026-03-28", "08:00:00", "Tagihan",        "Penyelesaian listrik",              50_000),
    ("2026-03-28", "09:00:00", "Rokok/Vape",     "Beli rokok purple taste",           23_000),
    ("2026-03-28", "19:00:00", "Nongkrong",      "Kopsus 2, mineral 2",               36_000),
    ("2026-03-28", "20:00:00", "Makanan",        "Beli nasi gila bts",                25_000),
    ("2026-03-28", "20:30:00", "Transportasi",   "Parkir nordu",                       4_000),
    # 29 Mar
    ("2026-03-29", "12:00:00", "Makanan",        "ShopeeFood ayam geprek",            32_000),
    # 30 Mar
    ("2026-03-30", "12:00:00", "Makanan",        "Ayam geprek",                       10_000),
    ("2026-03-30", "18:00:00", "Rokok/Vape",     "Beli rokok purple taste",           23_000),
    # 31 Mar
    ("2026-03-31", "12:00:00", "Makanan",        "Beli geprek 2 porsi",               20_000),
    ("2026-03-31", "19:00:00", "Makanan",        "Gacoan",                            29_000),
    # 1 Apr
    ("2026-04-01", "08:00:00", "Tempat Tinggal", "Penyelesaian biaya kos",           500_000),
    ("2026-04-01", "09:00:00", "Makanan",        "Nasi kuning",                       13_000),
    ("2026-04-01", "10:00:00", "Transportasi",   "Bensin",                            12_000),
    ("2026-04-01", "11:00:00", "Makanan",        "Cimory",                            10_000),
    ("2026-04-01", "12:00:00", "Makanan",        "Pentol",                            10_000),
    ("2026-04-01", "13:00:00", "Investasi",      "Alokasi Dana PM",                  459_000),
    ("2026-04-01", "14:00:00", "Rokok/Vape",     "Rokok Purple taste",                24_000),
    ("2026-04-01", "19:00:00", "Nongkrong",      "Redvelvet",                         25_000),
    ("2026-04-01", "19:30:00", "Transportasi",   "Parkir",                             2_000),
    ("2026-04-01", "20:00:00", "Makanan",        "Nasi ayam",                         15_000),
    # 2 Apr
    ("2026-04-02", "08:00:00", "Makanan",        "Naskun",                            14_000),
    ("2026-04-02", "12:00:00", "Makanan",        "Nasi campur",                       10_000),
    ("2026-04-02", "13:00:00", "Makanan",        "Minuman API",                       42_500),
    ("2026-04-02", "14:00:00", "Tagihan",        "Penyelesaian PDAM",                 26_000),
    # 3 Apr
    ("2026-04-03", "12:00:00", "Makanan",        "Gacoan",                            50_000),
    ("2026-04-03", "13:00:00", "Makanan",        "Mineral + mitos goreng",            22_000),
    ("2026-04-03", "13:30:00", "Transportasi",   "Parkir dua asa",                     2_000),
    # 4 Apr
    ("2026-04-04", "10:00:00", "Transportasi",   "Bensin",                            12_000),
    ("2026-04-04", "12:00:00", "Makanan",        "Mie ayam + air es",                 14_000),
    ("2026-04-04", "13:00:00", "Rokok/Vape",     "Purple taste",                      23_000),
    ("2026-04-04", "14:00:00", "Makanan",        "Teh pucuk",                          4_000),
    ("2026-04-04", "15:00:00", "Hiburan",        "Tiket domino",                      15_000),
    ("2026-04-04", "19:00:00", "Makanan",        "Burger + jus mangga",               20_000),
    ("2026-04-04", "20:00:00", "Makanan",        "ShopeeFood ayam mak dura",          33_000),
    # 5 Apr
    ("2026-04-05", "09:00:00", "Makanan",        "Beli es teh",                        3_000),
    ("2026-04-05", "10:00:00", "Rokok/Vape",     "Beli rokok purple taste",           23_000),
    ("2026-04-05", "19:00:00", "Nongkrong",      "Beli redvelvet",                    25_000),
    ("2026-04-05", "19:30:00", "Makanan",        "Beli bakmi ayam",                   20_000),
    ("2026-04-05", "20:00:00", "Transportasi",   "Bayar parkir",                       2_000),
    ("2026-04-05", "20:30:00", "Piutang",        "Meutangi Pai rokok",                23_000),
    ("2026-04-05", "20:31:00", "Piutang",        "Meutangi Pai bakmi",                20_000),
    ("2026-04-05", "20:32:00", "Piutang",        "Meutangi Pai matcha",               22_000),
    # 6 Apr
    ("2026-04-06", "09:00:00", "Makanan",        "Beli burger",                       20_000),
    ("2026-04-06", "10:00:00", "Skincare/Suplemen","Sabun muka Kahf",                 34_000),
    ("2026-04-06", "12:00:00", "Makanan",        "Beli geprek",                       10_000),
    ("2026-04-06", "13:00:00", "Skincare/Suplemen","Serum Elsheskin",                 55_000),
    ("2026-04-06", "14:00:00", "Skincare/Suplemen","Meprothion box",                 234_000),
    ("2026-04-06", "15:00:00", "Skincare/Suplemen","Newlab C-Gluta",                 164_000),
    ("2026-04-06", "19:00:00", "Makanan",        "Dbesto gofood",                     30_000),
    # 7 Apr
    ("2026-04-07", "09:00:00", "Makanan",        "Beli burger",                       10_000),
    ("2026-04-07", "12:00:00", "Makanan",        "Beli geprek",                       10_000),
    ("2026-04-07", "13:00:00", "Rokok/Vape",     "Rokok click purple",                23_000),
    ("2026-04-07", "14:00:00", "Makanan",        "Pisang keju",                       15_000),
    ("2026-04-07", "15:00:00", "Makanan",        "Jus sirsak",                         5_000),
    ("2026-04-07", "16:00:00", "Makanan",        "Beli galon",                         8_000),
    ("2026-04-07", "19:00:00", "Makanan",        "Mie ayam",                          18_000),
    ("2026-04-07", "20:00:00", "Rokok/Vape",     "Beli odol",                          5_000),
    # 8 Apr
    ("2026-04-08", "10:00:00", "Nongkrong",      "Ice roast + cemilan",               29_000),
    ("2026-04-08", "12:00:00", "Makanan",        "Beli geprek",                       10_000),
    ("2026-04-08", "13:00:00", "Transportasi",   "Beli bensin",                       40_000),
    ("2026-04-08", "14:00:00", "Makanan",        "Beli mie ayam",                     14_000),
    ("2026-04-08", "19:00:00", "Makanan",        "Beli gacoan",                       33_000),
    ("2026-04-08", "20:00:00", "Piutang",        "Meutangi Fai gacoan",               42_000),
    # 9 Apr
    ("2026-04-09", "09:00:00", "Tagihan",        "Alokasi Claude + admin",            60_000),
    ("2026-04-09", "10:00:00", "Transportasi",   "Naik gojek",                        18_000),
    ("2026-04-09", "12:00:00", "Makanan",        "Beli geprek",                       10_000),
    ("2026-04-09", "13:00:00", "Transportasi",   "Biaya gojek",                       21_500),
    ("2026-04-09", "14:00:00", "Lainnya",        "Admin top up Gopay",                 3_000),
    ("2026-04-09", "19:00:00", "Rokok/Makan",    "Rokok + mie",                       24_000),
    # 10 Apr
    ("2026-04-10", "12:00:00", "Makanan",        "Beli mie",                           5_000),
    ("2026-04-10", "13:00:00", "Transportasi",   "Naik gojek",                        19_500),
    # 11 Apr
    ("2026-04-11", "09:00:00", "Makanan",        "Beli dcelup",                       24_000),
    ("2026-04-11", "10:00:00", "Rokok/Vape",     "Beli rokok",                        23_000),
    ("2026-04-11", "19:00:00", "Nongkrong",      "Beli americano",                    22_000),
    ("2026-04-11", "19:30:00", "Makanan",        "Makan di koe",                      37_000),
    ("2026-04-11", "20:00:00", "Makanan",        "Beef teriyaki",                     37_000),
    ("2026-04-11", "20:30:00", "Hiburan",        "Beli dom",                           4_000),
    ("2026-04-11", "21:00:00", "Makanan",        "Mineral",                           13_500),
    ("2026-04-11", "21:30:00", "Alokasi Khusus", "Penyelesaian transaksi Fai",         4_000),
    # 12 Apr
    ("2026-04-12", "08:00:00", "Makanan",        "Beli lele nasi",                    10_000),
    ("2026-04-12", "09:00:00", "Rokok/Vape",     "Rokok",                             25_000),
    ("2026-04-12", "12:00:00", "Makanan",        "Dcelup nasi",                       24_000),
    ("2026-04-12", "13:00:00", "Tempat Tinggal", "Penyelesaian kamar",                75_000),
    ("2026-04-12", "14:00:00", "Tagihan",        "Beli kuota",                        80_000),
    ("2026-04-12", "16:00:00", "Makanan/Transp", "Pentol/minum/kereta",               30_000),
    ("2026-04-12", "17:00:00", "Makanan",        "Extrajoss susu",                     8_000),
    ("2026-04-12", "18:00:00", "Rokok/Vape",     "Surya isi 12",                      30_000),
    # 13 Apr
    ("2026-04-13", "09:00:00", "Hiburan",        "Tiket Tahura",                      15_000),
    ("2026-04-13", "12:00:00", "Makanan",        "Makan",                             30_000),
    ("2026-04-13", "13:00:00", "Transportasi",   "Bensin",                            50_000),
    ("2026-04-13", "14:00:00", "Makanan",        "Pentol",                            10_000),
    ("2026-04-13", "19:00:00", "Makanan",        "Bebek Sinjay",                      25_000),
    # 14 Apr
    ("2026-04-14", "09:00:00", "Makanan",        "Ayam Ganja",                        15_000),
    ("2026-04-14", "10:00:00", "Transportasi",   "Gojek",                             19_000),
    ("2026-04-14", "12:00:00", "Makanan",        "Geprek",                            10_000),
    ("2026-04-14", "13:00:00", "Transportasi",   "Gojek",                             21_500),
    ("2026-04-14", "18:00:00", "Rokok/Vape",     "Rokok",                             21_000),
    # 15 Apr
    ("2026-04-15", "08:00:00", "Transportasi",   "Gojek",                             18_500),
    ("2026-04-15", "09:00:00", "Makanan",        "Minuman dan bilahan",                7_000),
    ("2026-04-15", "10:00:00", "Rokok/Vape",     "Excel click white",                 21_000),
    ("2026-04-15", "11:00:00", "Transportasi",   "Grab",                              16_000),
    ("2026-04-15", "13:00:00", "Kendaraan",      "Perbaikan motor",                  240_000),
    ("2026-04-15", "19:00:00", "Nongkrong",      "Creamy coffee",                     25_000),
    ("2026-04-15", "19:30:00", "Makanan",        "Pentol",                            10_000),
    ("2026-04-15", "20:00:00", "Transportasi",   "Parkir",                             2_000),
    # 16 Apr
    ("2026-04-16", "12:00:00", "Makanan",        "Beli geprek",                       10_000),
    ("2026-04-16", "13:00:00", "Rokok/Vape",     "Beli click purple",                 23_000),
    ("2026-04-16", "19:00:00", "Makanan",        "Minuman nordu + nasi gila",         55_000),
    ("2026-04-16", "19:30:00", "Transportasi",   "Parkir nordu",                       2_000),
    # 17 Apr
    ("2026-04-17", "07:00:00", "Makanan",        "Beli pentol (pagi)",                 6_000),
    ("2026-04-17", "12:00:00", "Lainnya",        "Infaq Jum'at",                       1_000),
    ("2026-04-17", "16:00:00", "Makanan",        "Beli pentol (sore)",                10_000),
    ("2026-04-17", "17:00:00", "Makanan",        "Beli minuman latte bitten",         21_000),
    ("2026-04-17", "18:00:00", "Transportasi",   "Bayar parkir",                       2_000),
    ("2026-04-17", "19:00:00", "Makanan",        "Beli nasi ayam",                    10_000),
    # 18 Apr
    ("2026-04-18", "08:00:00", "Tagihan",        "Beli Claude AI Pro",               350_000),
    ("2026-04-18", "09:00:00", "Makanan",        "Beli Nescafe kaleng",                7_000),
    ("2026-04-18", "10:00:00", "Lainnya",        "Cek Turnitin (Sesi 1)",              6_000),
    ("2026-04-18", "11:00:00", "Lainnya",        "Bayar print-an",                    18_000),
    ("2026-04-18", "11:30:00", "Lainnya",        "Cek Turnitin (Sesi 2)",              2_500),
    ("2026-04-18", "12:00:00", "Makanan",        "Beli mie ayam",                     13_000),
    ("2026-04-18", "13:00:00", "Lainnya",        "Belikan bapak kuota",               77_000),
    ("2026-04-18", "14:00:00", "Rokok/Vape",     "Beli rokok",                        24_000),
    ("2026-04-18", "15:00:00", "Makanan",        "Beli makan",                        10_000),
    ("2026-04-18", "19:00:00", "Nongkrong",      "Beli americano",                    15_000),
    ("2026-04-18", "23:00:00", "Lainnya",        "Dana tidak ingat",                   8_000),
    # 19 Apr
    ("2026-04-19", "12:00:00", "Makanan",        "Beli makan",                        12_000),
    ("2026-04-19", "19:00:00", "Makanan",        "Beli Redvelvet Neir",               17_000),
    # 20 Apr
    ("2026-04-20", "09:00:00", "Transportasi",   "Bayar parkir Neir (2 orang)",        5_000),
    ("2026-04-20", "12:00:00", "Makanan",        "Beli nasi campur",                  11_000),
    ("2026-04-20", "13:00:00", "Makanan",        "Beli geprek",                       10_000),
    ("2026-04-20", "14:00:00", "Skincare/Suplemen","Kahf Water Based Pomade 70g",     33_604),
    ("2026-04-20", "14:01:00", "Skincare/Suplemen","Makarizo Hair Energy Shampoo",    26_500),
    ("2026-04-20", "14:02:00", "Skincare/Suplemen","VIVA Milk Cleanser Lemon 100ml",  11_191),
    ("2026-04-20", "14:03:00", "Skincare/Suplemen","Kapas Sariayu 50gr",              21_000),
    ("2026-04-20", "14:04:00", "Skincare/Suplemen","SR12 Deodorant Spray Tawas",      60_500),
    ("2026-04-20", "14:05:00", "Lainnya",        "Gentle Gen Deterjen Cair",          15_000),
    ("2026-04-20", "19:00:00", "Hiburan",        "2 Tiket Bioskop - Ayah Ini Arahnya Ke Mana Ya?", 108_400),
    ("2026-04-20", "21:00:00", "Nongkrong",      "2 Minuman Hopes + Parkir",          60_000),
    ("2026-04-20", "21:30:00", "Rokok/Vape",     "Beli rokok",                        25_000),
    ("2026-04-20", "22:00:00", "Makanan",        "Beli siomay",                       10_000),
    ("2026-04-20", "23:00:00", "Lainnya",        "Uang hilang",                       14_000),
    ("2026-04-20", "23:30:00", "Piutang",        "Meutangi Adit (Geprek)",            10_000),
]

# ============================================================
# NOTES HISTORIS
# ============================================================
HISTORICAL_NOTES = [
    "Piutang (Uang di orang): Aji Rp10.000. Adit Rp10.000 (Geprek).",
    "Alokasi Admin Tambahan: Rp2.298.000 (Hanya sebagai pengingat, belum dikurangi dari saldo operasional).",
]


def migrate():
    print(f"🔌 Connecting to database: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print(f"❌ Database tidak ditemukan di {DB_PATH}")
        print("   Pastikan bot sudah pernah dijalankan minimal sekali untuk membuat DB.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Cek apakah user_id column sudah ada
    cursor.execute("PRAGMA table_info(transactions)")
    cols = [row[1] for row in cursor.fetchall()]
    if 'user_id' not in cols:
        print("❌ Kolom user_id belum ada di tabel transactions.")
        print("   Deploy dulu database.py yang baru, baru jalankan script ini.")
        conn.close()
        sys.exit(1)

    # Cek data existing (idempotent check)
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM transactions WHERE user_id = ?",
        (MY_USER_ID,)
    )
    existing = cursor.fetchone()['cnt']

    if existing > 0:
        print(f"⚠️  Sudah ada {existing} transaksi untuk user {MY_USER_ID}.")
        answer = input("   Mau lanjut insert ulang? (y/N): ").strip().lower()
        if answer != 'y':
            print("❌ Dibatalkan.")
            conn.close()
            sys.exit(0)

    print(f"\n👤 Migrasi untuk user_id: {MY_USER_ID}")
    print("=" * 50)

    # ==================== INSERT PEMASUKAN ====================
    print("\n💰 Inserting PEMASUKAN...")
    income_count = 0

    for date, time, cat_lama, desc, amount in INCOME_DATA:
        category = INCOME_CAT_MAP.get(cat_lama, "Lainnya")
        cursor.execute("""
            INSERT INTO transactions (user_id, date, time, type, category, amount, description)
            VALUES (?, ?, ?, 'income', ?, ?, ?)
        """, (MY_USER_ID, date, time, category, amount, desc))
        income_count += 1
        print(f"   ✅ {date} | {category} | {desc} | Rp{amount:,}")

    # ==================== INSERT PENGELUARAN ====================
    print(f"\n💸 Inserting PENGELUARAN...")
    expense_count = 0

    for date, time, cat_lama, desc, amount in EXPENSE_DATA:
        category = EXPENSE_CAT_MAP.get(cat_lama, "Lainnya")
        cursor.execute("""
            INSERT INTO transactions (user_id, date, time, type, category, amount, description)
            VALUES (?, ?, ?, 'expense', ?, ?, ?)
        """, (MY_USER_ID, date, time, category, amount, desc))
        expense_count += 1
        print(f"   ✅ {date} | {category} | {desc} | Rp{amount:,}")

    # ==================== INSERT NOTES ====================
    print(f"\n📓 Inserting NOTES...")

    # Cek apakah notes sudah ada
    cursor.execute("PRAGMA table_info(notes)")
    note_cols = [row[1] for row in cursor.fetchall()]
    has_user_id_notes = 'user_id' in note_cols

    notes_count = 0
    for note_text in HISTORICAL_NOTES:
        if has_user_id_notes:
            cursor.execute("""
                INSERT INTO notes (user_id, description)
                VALUES (?, ?)
            """, (MY_USER_ID, note_text))
        else:
            cursor.execute("""
                INSERT INTO notes (description)
                VALUES (?)
            """, (note_text,))
        notes_count += 1
        print(f"   ✅ {note_text[:60]}...")

    conn.commit()

    # ==================== SUMMARY ====================
    total_income = sum(row[4] for row in INCOME_DATA)
    total_expense = sum(row[4] for row in EXPENSE_DATA)
    saldo = total_income - total_expense

    print("\n" + "=" * 50)
    print("🎉 MIGRASI SELESAI!")
    print(f"   💰 Pemasukan: {income_count} transaksi | Total: Rp{total_income:,}")
    print(f"   💸 Pengeluaran: {expense_count} transaksi | Total: Rp{total_expense:,}")
    print(f"   📓 Notes: {notes_count} catatan")
    print(f"   💳 Saldo bersih: Rp{saldo:,}")
    print("=" * 50)

    conn.close()
    print("\n✅ Database closed. Selesai!")


if __name__ == "__main__":
    migrate()
