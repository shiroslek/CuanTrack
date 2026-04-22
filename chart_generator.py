#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Chart Generator
v2.7 - Optimized: single DB query for trend, smaller figure, lower DPI
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import os

from database import Database
from config import CHART_DIR, TIMEZONE


class ChartGenerator:
    def __init__(self, db: Database):
        self.db = db
        plt.rcParams['font.family'] = 'DejaVu Sans'
        plt.rcParams['figure.max_open_warning'] = 0

    def _draw_bar_chart(self, labels, sizes, percentages, title, filepath, color_bar):
        n = len(labels)
        fig, ax = plt.subplots(figsize=(max(7, n * 0.9 + 1.5), 5.5), facecolor='#FAF8F5')
        ax.set_facecolor('#FAF8F5')

        x_pos = np.arange(n)
        bars = ax.bar(x_pos, sizes, color=color_bar, edgecolor='white', linewidth=0.8, width=0.6)

        max_val = max(sizes) if sizes else 1
        for bar, amt, pct in zip(bars, sizes, percentages):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max_val * 0.015,
                f'Rp{amt:,.0f}\n({pct:.1f}%)',
                ha='center', va='bottom', fontsize=7, color='#444444', linespacing=1.3
            )

        ax.set_xticks(x_pos)
        ax.set_xticklabels(labels, fontsize=8.5, rotation=25, ha='right')
        ax.set_ylabel('Jumlah (Rp)', fontsize=9)
        ax.set_title(title, fontsize=12, fontweight='bold', color='#333333', pad=12)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'Rp{x:,.0f}'))
        ax.set_ylim(0, max_val * 1.28)
        ax.grid(True, axis='y', alpha=0.2, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        for spine in ['left', 'bottom']:
            ax.spines[spine].set_color('#DDDDDD')

        plt.tight_layout()
        plt.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='#FAF8F5')
        plt.close(fig)
        return filepath

    def generate_income_pie_chart(self, user_id, filename: str = None) -> str:
        if not filename:
            filename = f'bar_income_{user_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        filepath = os.path.join(CHART_DIR, filename)

        income_data = self.db.get_income_by_category(user_id)
        if not income_data:
            return None

        total = sum(row['total'] for row in income_data)
        labels = [row['category'] for row in income_data]
        sizes  = [row['total'] for row in income_data]
        percentages = [(s / total * 100) if total > 0 else 0 for s in sizes]

        return self._draw_bar_chart(labels, sizes, percentages,
                                    'Distribusi Pemasukan per Kategori', filepath, '#82C99F')

    def generate_expense_pie_chart(self, user_id, filename: str = None) -> str:
        if not filename:
            filename = f'bar_expense_{user_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        filepath = os.path.join(CHART_DIR, filename)

        data = self.db.get_spending_by_category(user_id)
        if not data:
            return None

        total = sum(row['total'] for row in data)
        labels = [row['category'] for row in data]
        sizes  = [row['total'] for row in data]
        percentages = [(s / total * 100) if total > 0 else 0 for s in sizes]

        return self._draw_bar_chart(labels, sizes, percentages,
                                    'Distribusi Pengeluaran per Kategori', filepath, '#F1948A')

    def generate_pie_chart(self, user_id, filename: str = None) -> str:
        return self.generate_expense_pie_chart(user_id, filename)

    def generate_trend_chart(self, user_id, days=30, filename: str = None) -> str:
        if not filename:
            filename = f'trend_{user_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        filepath = os.path.join(CHART_DIR, filename)

        end_date   = datetime.now(TIMEZONE)
        start_date = end_date - timedelta(days=days)
        start_str  = start_date.strftime("%Y-%m-%d")
        end_str    = end_date.strftime("%Y-%m-%d")

        # 1 query saja, bukan loop 30x
        self.db.cursor.execute("""
            SELECT date, SUM(amount) as total
            FROM transactions
            WHERE user_id = ? AND type = 'expense'
              AND date >= ? AND date <= ?
            GROUP BY date
        """, (user_id, start_str, end_str))
        rows = self.db.cursor.fetchall()

        if not rows:
            return None

        # Isi tanggal yang tidak ada transaksi dengan 0
        daily = defaultdict(int)
        for row in rows:
            daily[row['date']] = row['total']

        all_dates = []
        current = start_date
        while current <= end_date:
            all_dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        amounts = [daily[d] for d in all_dates]

        if sum(amounts) == 0:
            return None

        date_objects = [datetime.strptime(d, "%Y-%m-%d") for d in all_dates]

        fig, ax = plt.subplots(figsize=(10, 4.5), facecolor='#FAF8F5')
        ax.set_facecolor('#FAF8F5')
        ax.plot(date_objects, amounts, marker='o', linewidth=1.8,
                markersize=3.5, color='#E74C3C', zorder=5)
        ax.fill_between(date_objects, amounts, alpha=0.13, color='#E74C3C')
        ax.set_xlabel('Tanggal', fontsize=10)
        ax.set_ylabel('Pengeluaran (Rp)', fontsize=10)
        ax.set_title(f'Trend Pengeluaran Harian ({days} Hari Terakhir)',
                     fontsize=12, fontweight='bold', color='#333333')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 10)))
        plt.xticks(rotation=40, ha='right', fontsize=8)
        ax.grid(True, alpha=0.18, linestyle='--')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'Rp{x:,.0f}'))
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        for spine in ['left', 'bottom']:
            ax.spines[spine].set_color('#DDDDDD')

        plt.tight_layout()
        plt.savefig(filepath, dpi=100, bbox_inches='tight', facecolor='#FAF8F5')
        plt.close(fig)
        return filepath
