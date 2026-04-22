#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Chart Generator
v2.2 - Multi-user support (user_id added to all methods)
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import os

from database import Database
from config import CHART_DIR, TIMEZONE


class ChartGenerator:
    def __init__(self, db: Database):
        self.db = db
        plt.rcParams['font.family'] = 'DejaVu Sans'

    def generate_income_pie_chart(self, user_id, filename: str = None) -> str:
        """Generate pie chart for income by category"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'pie_income_{user_id}_{timestamp}.png'
        filepath = os.path.join(CHART_DIR, filename)

        income_data = self.db.get_income_by_category(user_id)

        if not income_data:
            return None

        total_income = sum(row['total'] for row in income_data)
        labels = []
        sizes = []
        percentages = []

        for row in income_data:
            pct = (row['total'] / total_income * 100) if total_income > 0 else 0
            labels.append(row['category'])
            sizes.append(row['total'])
            percentages.append(pct)

        fig, ax = plt.subplots(figsize=(10, 8))
        n = len(labels)
        colors = plt.cm.Greens([50/255 + i * (150/255) / max(n-1, 1) for i in range(n)])

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=None,
            autopct='%1.1f%%',
            colors=colors,
            startangle=90
        )

        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
            autotext.set_weight('bold')

        legend_labels = [f"{label} ({pct:.1f}%)" for label, pct in zip(labels, percentages)]
        ax.legend(
            legend_labels,
            title="Kategori Pemasukan",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=9
        )

        ax.set_title('Distribusi Pemasukan per Kategori', fontsize=14, weight='bold', pad=20)
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        return filepath

    def generate_expense_pie_chart(self, user_id, filename: str = None) -> str:
        """Generate pie chart for expenses by category"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'pie_expense_{user_id}_{timestamp}.png'
        filepath = os.path.join(CHART_DIR, filename)

        data = self.db.get_spending_by_category(user_id)

        if not data:
            return None

        total_expense = sum(row['total'] for row in data)
        labels = []
        sizes = []
        percentages = []

        for row in data:
            pct = (row['total'] / total_expense * 100) if total_expense > 0 else 0
            labels.append(row['category'])
            sizes.append(row['total'])
            percentages.append(pct)

        fig, ax = plt.subplots(figsize=(10, 8))
        n = len(labels)
        colors = plt.cm.Reds([50/255 + i * (150/255) / max(n-1, 1) for i in range(n)])

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=None,
            autopct='%1.1f%%',
            colors=colors,
            startangle=90
        )

        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
            autotext.set_weight('bold')

        legend_labels = [f"{label} ({pct:.1f}%)" for label, pct in zip(labels, percentages)]
        ax.legend(
            legend_labels,
            title="Kategori Pengeluaran",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=9
        )

        ax.set_title('Distribusi Pengeluaran per Kategori', fontsize=14, weight='bold', pad=20)
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        return filepath

    def generate_pie_chart(self, user_id, filename: str = None) -> str:
        """Legacy method - generates expense pie chart"""
        return self.generate_expense_pie_chart(user_id, filename)

    def generate_trend_chart(self, user_id, days=30, filename: str = None) -> str:
        """Generate trend chart for daily spending"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'trend_chart_{user_id}_{timestamp}.png'
        filepath = os.path.join(CHART_DIR, filename)

        end_date = datetime.now(TIMEZONE)
        start_date = end_date - timedelta(days=days)

        daily_data = {}
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            daily_expense = self.db.get_total_by_type(user_id, 'expense', date_str, date_str)
            daily_data[date_str] = daily_expense
            current_date += timedelta(days=1)

        if not daily_data or sum(daily_data.values()) == 0:
            return None

        dates = list(daily_data.keys())
        amounts = list(daily_data.values())
        date_objects = [datetime.strptime(d, "%Y-%m-%d") for d in dates]

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(date_objects, amounts, marker='o', linewidth=2, markersize=4, color='#e74c3c')
        ax.fill_between(date_objects, amounts, alpha=0.3, color='#e74c3c')

        ax.set_xlabel('Tanggal', fontsize=12)
        ax.set_ylabel('Pengeluaran (Rp)', fontsize=12)
        ax.set_title(f'Trend Pengeluaran Harian ({days} Hari Terakhir)', fontsize=14, weight='bold')

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 10)))
        plt.xticks(rotation=45, ha='right')

        ax.grid(True, alpha=0.3, linestyle='--')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'Rp{x:,.0f}'))

        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        return filepath
