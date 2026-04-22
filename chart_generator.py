#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Chart Generator
v2.2 - Fixed colormap issue, using explicit hex colors
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import os

from database import Database
from config import CHART_DIR, TIMEZONE

# Hardcoded colors — menghindari bug plt.cm.Colormap(range(...))
INCOME_COLORS = [
    '#2ecc71', '#27ae60', '#1abc9c', '#16a085',
    '#a8e6cf', '#3d9970', '#00b894', '#55efc4',
    '#00cec9', '#6c5ce7'
]

EXPENSE_COLORS = [
    '#e74c3c', '#c0392b', '#e67e22', '#d35400',
    '#ff6b6b', '#ee5a24', '#fd79a8', '#e84393',
    '#f39c12', '#e17055'
]


class ChartGenerator:
    def __init__(self, db: Database):
        self.db = db
        plt.rcParams['font.family'] = 'DejaVu Sans'

    def generate_income_pie_chart(self, filename: str = None) -> str:
        """Generate pie chart for income by category"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'pie_income_{timestamp}.png'

        filepath = os.path.join(str(CHART_DIR), str(filename))

        query = """
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE type = 'income'
            GROUP BY category
            ORDER BY total DESC
        """
        self.db.cursor.execute(query)
        income_data = self.db.cursor.fetchall()

        if not income_data:
            return None

        total_income = float(sum(row['total'] for row in income_data))
        if total_income == 0:
            return None

        labels = []
        sizes = []
        percentages = []

        for row in income_data:
            sizes.append(float(row['total']))  # pastikan float
            pct = float(row['total']) / total_income * 100.0
            labels.append(str(row['category']))
            percentages.append(pct)

        # Pilih warna dari daftar hardcoded (bukan colormap)
        colors = [INCOME_COLORS[i % len(INCOME_COLORS)] for i in range(len(labels))]

        fig, ax = plt.subplots(figsize=(10, 8))

        ax.pie(
            sizes,
            labels=None,
            autopct='%1.1f%%',
            colors=colors,
            startangle=90,
            pctdistance=0.75
        )

        for text in ax.texts:
            text.set_fontsize(10)

        legend_labels = [f"{lbl} ({pct:.1f}%)" for lbl, pct in zip(labels, percentages)]
        ax.legend(
            legend_labels,
            title="Kategori",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=9
        )

        # Tidak pakai set_title agar tidak nabrak header PDF
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return filepath

    def generate_expense_pie_chart(self, filename: str = None) -> str:
        """Generate pie chart for expenses by category"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'pie_expense_{timestamp}.png'

        filepath = os.path.join(str(CHART_DIR), str(filename))

        data = self.db.get_spending_by_category()

        if not data:
            return None

        total_expense = float(sum(row['total'] for row in data))
        if total_expense == 0:
            return None

        labels = []
        sizes = []
        percentages = []

        for row in data:
            sizes.append(float(row['total']))  # pastikan float
            pct = float(row['total']) / total_expense * 100.0
            labels.append(str(row['category']))
            percentages.append(pct)

        # Pilih warna dari daftar hardcoded (bukan colormap)
        colors = [EXPENSE_COLORS[i % len(EXPENSE_COLORS)] for i in range(len(labels))]

        fig, ax = plt.subplots(figsize=(10, 8))

        ax.pie(
            sizes,
            labels=None,
            autopct='%1.1f%%',
            colors=colors,
            startangle=90,
            pctdistance=0.75
        )

        for text in ax.texts:
            text.set_fontsize(10)

        legend_labels = [f"{lbl} ({pct:.1f}%)" for lbl, pct in zip(labels, percentages)]
        ax.legend(
            legend_labels,
            title="Kategori",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=9
        )

        # Tidak pakai set_title agar tidak nabrak header PDF
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return filepath

    def generate_pie_chart(self, filename: str = None) -> str:
        """Legacy method - generates expense pie chart for compatibility"""
        return self.generate_expense_pie_chart(filename)

    def generate_trend_chart(self, days=30, filename: str = None) -> str:
        """Generate trend chart for daily spending"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'trend_chart_{timestamp}.png'

        filepath = os.path.join(str(CHART_DIR), str(filename))

        end_date = datetime.now(TIMEZONE)
        start_date = end_date - timedelta(days=days)

        daily_data = {}
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            val = self.db.get_total_by_type('expense', date_str, date_str)
            daily_data[date_str] = float(val) if val else 0.0  # pastikan float
            current_date += timedelta(days=1)

        if not daily_data or sum(daily_data.values()) == 0:
            return None

        dates = list(daily_data.keys())
        amounts = [float(v) for v in daily_data.values()]  # pastikan semua float
        date_objects = [datetime.strptime(d, "%Y-%m-%d") for d in dates]

        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(date_objects, amounts, marker='o', linewidth=2, markersize=4, color='#e74c3c')
        ax.fill_between(date_objects, amounts, alpha=0.3, color='#e74c3c')

        ax.set_xlabel('Tanggal', fontsize=12)
        ax.set_ylabel('Pengeluaran (Rp)', fontsize=12)
        ax.set_title(
            f'Trend Pengeluaran Harian ({days} Hari Terakhir)',
            fontsize=14, weight='bold'
        )

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 10)))
        plt.xticks(rotation=45, ha='right')

        ax.grid(True, alpha=0.3, linestyle='--')

        # float-safe formatter
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, p: f'Rp{float(x):,.0f}')
        )

        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return filepath
