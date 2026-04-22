#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Chart Generator
v2.2 - Bar charts for income & expense categories
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

    def generate_income_pie_chart(self, filename: str = None) -> str:
        """Generate bar chart for income by category"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'bar_income_{timestamp}.png'
        filepath = os.path.join(CHART_DIR, filename)

        query = """
            SELECT category, SUM(amount) as total, COUNT(*) as count
            FROM transactions
            WHERE type = 'income'
            GROUP BY category
            ORDER BY total DESC
        """
        self.db.cursor.execute(query)
        income_data = self.db.cursor.fetchall()

        if not income_data:
            return None

        total_income = sum(row['total'] for row in income_data)
        labels = [row['category'] for row in income_data]
        sizes  = [row['total'] for row in income_data]
        percentages = [(s / total_income * 100) if total_income > 0 else 0 for s in sizes]

        fig, ax = plt.subplots(figsize=(10, 6))

        colors = plt.cm.Greens([0.4 + 0.5 * i / max(len(labels) - 1, 1) for i in range(len(labels))])
        bars = ax.barh(labels[::-1], sizes[::-1], color=colors[::-1])

        # Label nilai & persentase di ujung bar
        for bar, size, pct in zip(bars, sizes[::-1], percentages[::-1]):
            ax.text(
                bar.get_width() + total_income * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f'Rp{size:,.0f}  ({pct:.1f}%)',
                va='center', fontsize=9
            )

        ax.set_xlabel('Jumlah (Rp)', fontsize=11)
        ax.set_title('Distribusi Pemasukan per Kategori', fontsize=14, weight='bold', pad=15)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'Rp{x:,.0f}'))
        ax.set_xlim(0, max(sizes) * 1.4)
        ax.grid(True, axis='x', alpha=0.3, linestyle='--')
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        return filepath

    def generate_expense_pie_chart(self, filename: str = None) -> str:
        """Generate bar chart for expenses by category"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'bar_expense_{timestamp}.png'
        filepath = os.path.join(CHART_DIR, filename)

        data = self.db.get_spending_by_category()
        if not data:
            return None

        total_expense = sum(row['total'] for row in data)
        labels = [row['category'] for row in data]
        sizes  = [row['total'] for row in data]
        percentages = [(s / total_expense * 100) if total_expense > 0 else 0 for s in sizes]

        fig, ax = plt.subplots(figsize=(10, 6))

        colors = plt.cm.Reds([0.4 + 0.5 * i / max(len(labels) - 1, 1) for i in range(len(labels))])
        bars = ax.barh(labels[::-1], sizes[::-1], color=colors[::-1])

        for bar, size, pct in zip(bars, sizes[::-1], percentages[::-1]):
            ax.text(
                bar.get_width() + total_expense * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f'Rp{size:,.0f}  ({pct:.1f}%)',
                va='center', fontsize=9
            )

        ax.set_xlabel('Jumlah (Rp)', fontsize=11)
        ax.set_title('Distribusi Pengeluaran per Kategori', fontsize=14, weight='bold', pad=15)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'Rp{x:,.0f}'))
        ax.set_xlim(0, max(sizes) * 1.4)
        ax.grid(True, axis='x', alpha=0.3, linestyle='--')
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        return filepath

    def generate_pie_chart(self, filename: str = None) -> str:
        """Legacy method - compatibility"""
        return self.generate_expense_pie_chart(filename)

    def generate_trend_chart(self, days=30, filename: str = None) -> str:
        """Generate trend chart for daily spending"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'trend_chart_{timestamp}.png'
        filepath = os.path.join(CHART_DIR, filename)

        end_date   = datetime.now(TIMEZONE)
        start_date = end_date - timedelta(days=days)

        daily_data = {}
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            daily_data[date_str] = self.db.get_total_by_type('expense', date_str, date_str)
            current_date += timedelta(days=1)

        if not daily_data or sum(daily_data.values()) == 0:
            return None

        dates   = list(daily_data.keys())
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
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        return filepath
