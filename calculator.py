#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Calculator
v2.4 - Powerful insights + actionable suggestions
"""

from datetime import datetime, timedelta
from database import Database
from config import TIMEZONE


class Calculator:
    def __init__(self, db: Database):
        self.db = db

    def get_saldo_info(self, user_id):
        total_income = self.db.get_total_by_type(user_id, 'income')
        total_expense = self.db.get_total_by_type(user_id, 'expense')
        saldo = total_income - total_expense
        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'saldo': saldo
        }

    def get_top_categories(self, user_id, limit=5):
        return self.db.get_spending_by_category(user_id)[:limit]

    def calculate_percentage_by_category(self, user_id):
        categories = self.db.get_spending_by_category(user_id)
        total_expense = self.db.get_total_by_type(user_id, 'expense')
        result = []
        for cat in categories:
            percentage = (cat['total'] / total_expense * 100) if total_expense > 0 else 0
            result.append({
                'category': cat['category'],
                'amount': cat['total'],
                'count': cat['count'],
                'percentage': percentage
            })
        return result

    def get_period_summary(self, user_id, days=7):
        today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
        start_date = (datetime.now(TIMEZONE) - timedelta(days=days)).strftime("%Y-%m-%d")
        income = self.db.get_total_by_type(user_id, 'income', start_date, today)
        expense = self.db.get_total_by_type(user_id, 'expense', start_date, today)
        return {
            'period_days': days,
            'start_date': start_date,
            'end_date': today,
            'income': income,
            'expense': expense,
            'balance': income - expense
        }

    def _fmt(self, amount):
        if amount >= 1_000_000:
            return f"Rp{amount/1_000_000:.1f}jt"
        elif amount >= 1_000:
            return f"Rp{amount/1_000:.0f}rb"
        return f"Rp{amount:,}"

    def _get_month_range(self):
        now = datetime.now(TIMEZONE)
        start = now.replace(day=1).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")
        return start, end

    def _get_last_month_range(self):
        now = datetime.now(TIMEZONE)
        last_day_prev = now.replace(day=1) - timedelta(days=1)
        start = last_day_prev.replace(day=1).strftime("%Y-%m-%d")
        end = last_day_prev.strftime("%Y-%m-%d")
        return start, end

    def _days_in_current_month(self):
        now = datetime.now(TIMEZONE)
        if now.month == 12:
            return 31
        next_month = now.replace(month=now.month + 1, day=1)
        return (next_month - timedelta(days=1)).day

    def generate_insights(self, user_id) -> list:
        """
        Generate insights + saran keuangan.
        Setiap item adalah string siap tampil di Telegram.
        """
        insights = []
        now = datetime.now(TIMEZONE)
        today_str = now.strftime("%Y-%m-%d")
        days_passed = now.day
        days_in_month = self._days_in_current_month()
        days_left = days_in_month - days_passed

        month_start, month_end = self._get_month_range()
        last_start, last_end = self._get_last_month_range()

        # ── Ambil semua data yang diperlukan ──
        inc_month  = self.db.get_total_by_type(user_id, 'income',   month_start, month_end)
        exp_month  = self.db.get_total_by_type(user_id, 'expense',  month_start, month_end)
        inc_last   = self.db.get_total_by_type(user_id, 'income',   last_start,  last_end)
        exp_last   = self.db.get_total_by_type(user_id, 'expense',  last_start,  last_end)
        cats_month = self.db.get_spending_by_category(user_id, month_start, month_end)
        cats_last  = self.db.get_spending_by_category(user_id, last_start,  last_end)

        week_start      = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        prev_week_start = (now - timedelta(days=14)).strftime("%Y-%m-%d")
        prev_week_end   = (now - timedelta(days=8)).strftime("%Y-%m-%d")
        exp_7d      = self.db.get_total_by_type(user_id, 'expense', week_start,      today_str)
        exp_prev7d  = self.db.get_total_by_type(user_id, 'expense', prev_week_start, prev_week_end)
        exp_today   = self.db.get_total_by_type(user_id, 'expense', today_str, today_str)

        # ════════════════════════════════════════
        # 1. TREND MINGGUAN
        # ════════════════════════════════════════
        if exp_prev7d > 0 and exp_7d > 0:
            diff_pct = (exp_7d - exp_prev7d) / exp_prev7d * 100
            if diff_pct > 20:
                insights.append(
                    f"⚠️ *Trend Mingguan — Naik*\n"
                    f"Pengeluaran minggu ini *naik {diff_pct:.0f}%* "
                    f"({self._fmt(exp_7d)} vs {self._fmt(exp_prev7d)} minggu lalu).\n"
                    f"💡 _Saran: Cek transaksi terbesar minggu ini dan tentukan mana yang bisa ditunda atau dikurangi._"
                )
            elif diff_pct < -20:
                insights.append(
                    f"✅ *Trend Mingguan — Turun*\n"
                    f"Pengeluaran minggu ini *turun {abs(diff_pct):.0f}%* "
                    f"({self._fmt(exp_7d)} vs {self._fmt(exp_prev7d)} minggu lalu).\n"
                    f"💡 _Saran: Pertahankan kebiasaan ini! Alokasikan selisihnya ke tabungan._"
                )

        # ════════════════════════════════════════
        # 2. PERBANDINGAN BULAN INI VS BULAN LALU
        # ════════════════════════════════════════
        if exp_last > 0 and exp_month > 0:
            diff_pct = (exp_month - exp_last) / exp_last * 100
            if diff_pct > 15:
                insights.append(
                    f"📈 *Bulan Ini vs Bulan Lalu — Lebih Boros*\n"
                    f"Pengeluaran bulan ini *{self._fmt(exp_month)}*, "
                    f"lebih tinggi *{diff_pct:.0f}%* dari bulan lalu ({self._fmt(exp_last)}).\n"
                    f"💡 _Saran: Identifikasi kategori yang paling meningkat dan buat anggaran batas untuk bulan depan._"
                )
            elif diff_pct < -15:
                insights.append(
                    f"📉 *Bulan Ini vs Bulan Lalu — Lebih Hemat*\n"
                    f"Pengeluaran bulan ini *{self._fmt(exp_month)}*, "
                    f"lebih hemat *{abs(diff_pct):.0f}%* dari bulan lalu ({self._fmt(exp_last)}).\n"
                    f"💡 _Saran: Kerja bagus! Konsistenkan dan investasikan selisihnya._"
                )

        # ════════════════════════════════════════
        # 3. SAVING RATE
        # ════════════════════════════════════════
        if inc_month > 0:
            saving = inc_month - exp_month
            rate = saving / inc_month * 100
            if rate >= 30:
                insights.append(
                    f"🏆 *Saving Rate — Sangat Baik*\n"
                    f"Saving rate bulan ini *{rate:.0f}%* — kamu berhasil menyisihkan "
                    f"*{self._fmt(saving)}* dari {self._fmt(inc_month)}.\n"
                    f"💡 _Saran: Pertimbangkan alokasikan sebagian ke investasi (reksa dana, saham) "
                    f"atau perkuat dana darurat (idealnya 3-6× pengeluaran bulanan)._"
                )
            elif rate >= 20:
                insights.append(
                    f"✅ *Saving Rate — Baik*\n"
                    f"Saving rate bulan ini *{rate:.0f}%* ({self._fmt(saving)}) — sudah di atas standar minimal.\n"
                    f"💡 _Saran: Coba naikkan ke 30% dengan mengurangi 1 kategori non-esensial._"
                )
            elif rate >= 10:
                insights.append(
                    f"⚠️ *Saving Rate — Perlu Ditingkatkan*\n"
                    f"Saving rate bulan ini *{rate:.0f}%* ({self._fmt(saving)}). Idealnya minimal 20%.\n"
                    f"💡 _Saran: Coba metode 50/30/20 — 50% kebutuhan pokok, 30% keinginan, 20% tabungan. "
                    f"Mulai dari kurangi pengeluaran terbesar yang bukan kebutuhan._"
                )
            elif rate > 0:
                insights.append(
                    f"🚨 *Saving Rate — Rendah*\n"
                    f"Saving rate bulan ini hanya *{rate:.0f}%* ({self._fmt(saving)}).\n"
                    f"💡 _Saran: Coba prinsip 'bayar diri sendiri dulu' — sisihkan minimal 10% "
                    f"langsung setelah terima pemasukan, sebelum mulai belanja._"
                )
            else:
                insights.append(
                    f"🚨 *Pengeluaran Melebihi Pemasukan!*\n"
                    f"Defisit bulan ini: *{self._fmt(abs(saving))}* "
                    f"(pemasukan {self._fmt(inc_month)}, pengeluaran {self._fmt(exp_month)}).\n"
                    f"💡 _Saran: Segera buat daftar pengeluaran yang bisa dipotong. "
                    f"Prioritaskan kebutuhan pokok saja hingga akhir bulan._"
                )

        # ════════════════════════════════════════
        # 4. KATEGORI DOMINAN
        # ════════════════════════════════════════
        if cats_month and exp_month > 0:
            top = cats_month[0]
            pct = top['total'] / exp_month * 100
            if pct > 40:
                insights.append(
                    f"🔍 *Kategori Dominan — {top['category']}*\n"
                    f"Menyumbang *{pct:.0f}%* dari total pengeluaran bulan ini "
                    f"({self._fmt(top['total'])}).\n"
                    f"💡 _Saran: Wajar jika ini kebutuhan pokok. Jika bukan, pertimbangkan "
                    f"menetapkan batas budget untuk kategori ini bulan depan._"
                )
            elif pct > 25:
                insights.append(
                    f"📊 *Top Pengeluaran — {top['category']}*\n"
                    f"Kategori terbesar bulan ini dengan *{pct:.0f}%* dari total "
                    f"({self._fmt(top['total'])})."
                )

        # ════════════════════════════════════════
        # 5. KATEGORI YANG MELONJAK
        # ════════════════════════════════════════
        if cats_month and cats_last:
            last_dict = {c['category']: c['total'] for c in cats_last}
            for cat in cats_month[:5]:
                prev = last_dict.get(cat['category'], 0)
                if prev > 0:
                    pct_change = (cat['total'] - prev) / prev * 100
                    if pct_change > 50 and cat['total'] > 50_000:
                        insights.append(
                            f"📌 *Lonjakan Kategori — {cat['category']}*\n"
                            f"Naik *{pct_change:.0f}%* vs bulan lalu "
                            f"({self._fmt(prev)} → {self._fmt(cat['total'])}).\n"
                            f"💡 _Saran: Cek apakah ada pengeluaran tidak terduga di kategori ini "
                            f"dan pertimbangkan apakah bisa diefisienkan bulan depan._"
                        )
                        break

        # ════════════════════════════════════════
        # 6. ESTIMASI AKHIR BULAN
        # ════════════════════════════════════════
        if days_passed >= 7 and exp_month > 0 and days_left > 0:
            daily_avg = exp_month / days_passed
            est_total = daily_avg * days_in_month
            est_saving = inc_month - est_total if inc_month > 0 else None

            insight_est = (
                f"🔮 *Estimasi Akhir Bulan*\n"
                f"Rata-rata harian: *{self._fmt(int(daily_avg))}* "
                f"→ estimasi total: *{self._fmt(int(est_total))}* "
                f"({days_left} hari tersisa).\n"
            )
            if est_saving is not None:
                if est_saving > 0:
                    est_rate = est_saving / inc_month * 100
                    insight_est += (
                        f"💡 _Saran: Di jalur untuk saving rate {est_rate:.0f}%. "
                    )
                    if est_rate < 20:
                        insight_est += f"Kurangi pengeluaran ~{self._fmt(int((inc_month*0.2 - est_saving)/days_left))}/hari "
                        insight_est += f"agar mencapai saving rate 20%._"
                    else:
                        insight_est += f"Tetap konsisten hingga akhir bulan!_"
                else:
                    insight_est += (
                        f"💡 _Saran: Tren ini mengarah ke defisit! "
                        f"Kurangi pengeluaran sekitar {self._fmt(int(abs(est_saving)/days_left))}/hari "
                        f"agar tidak minus akhir bulan._"
                    )
            insights.append(insight_est.rstrip())

        # ════════════════════════════════════════
        # 7. FREKUENSI TRANSAKSI
        # ════════════════════════════════════════
        if cats_month and days_passed > 0:
            total_tx = sum(c['count'] for c in cats_month)
            freq = total_tx / days_passed
            if freq > 5:
                insights.append(
                    f"🛒 *Frekuensi Transaksi Tinggi*\n"
                    f"Rata-rata *{freq:.1f} transaksi per hari* bulan ini ({total_tx} total).\n"
                    f"💡 _Saran: Transaksi kecil yang sering cenderung tidak disadari totalnya. "
                    f"Coba batching belanja 2-3× seminggu dan buat daftar belanja sebelum pergi._"
                )

        # ════════════════════════════════════════
        # 8. HARI INI VS RATA-RATA HARIAN
        # ════════════════════════════════════════
        if exp_today > 0 and exp_month > 0 and days_passed > 1:
            daily_avg = exp_month / days_passed
            ratio = exp_today / daily_avg
            if ratio >= 3:
                insights.append(
                    f"💸 *Pengeluaran Hari Ini — Sangat Tinggi*\n"
                    f"Hari ini *{self._fmt(exp_today)}* — "
                    f"{ratio:.1f}× rata-rata harian ({self._fmt(int(daily_avg))}).\n"
                    f"💡 _Saran: Hari yang boros terjadi. Seimbangkan dengan berhemat "
                    f"1-2 hari ke depan agar estimasi bulanan tetap aman._"
                )
            elif ratio >= 2:
                insights.append(
                    f"💸 *Pengeluaran Hari Ini — Di Atas Rata-rata*\n"
                    f"Hari ini *{self._fmt(exp_today)}* — "
                    f"2× rata-rata harian ({self._fmt(int(daily_avg))}).\n"
                    f"💡 _Saran: Wajar sesekali, tapi pantau agar tidak terjadi terlalu sering._"
                )

        # ════════════════════════════════════════
        # 9. TIDAK ADA PEMASUKAN
        # ════════════════════════════════════════
        if inc_month == 0 and exp_month > 0:
            insights.append(
                f"📭 *Pemasukan Belum Dicatat*\n"
                f"Ada pengeluaran {self._fmt(exp_month)} bulan ini "
                f"tapi belum ada pemasukan tercatat.\n"
                f"💡 _Saran: Jangan lupa catat pemasukan agar saldo dan saving rate akurat._"
            )

        # ════════════════════════════════════════
        # 10. FALLBACK — DATA MINIM
        # ════════════════════════════════════════
        if not insights:
            insights.append(
                f"📝 *Data Masih Minim*\n"
                f"Terus catat transaksi harian untuk mendapatkan insights yang akurat.\n"
                f"💡 _Saran: Minimal 2 minggu data diperlukan untuk analisis yang bermakna. "
                f"Usahakan catat setiap transaksi di hari yang sama._"
            )

        return insights
