#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Chart Generator
v2.1 - Separate income/expense pie charts with percentages
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime, timedelta
import os

from database import Database
from config import CHART_DIR, TIMEZONE


class ChartGenerator:
    def __init__(self, db: Database):
        self.db = db
        # Set font
        plt.rcParams['font.family'] = 'DejaVu Sans'

    def generate_income_pie_chart(self, filename: str = None) -> str:
        """Generate pie chart for income by category"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'pie_income_{timestamp}.png'

        filepath = os.path.join(CHART_DIR, filename)

        # Get income data grouped by category
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

        # Calculate total and percentages
        total_income = sum(row['total'] for row in income_data)

        # Prepare data
        labels = []
        sizes = []
        percentages = []

        for row in income_data:
            pct = (row['total'] / total_income * 100) if total_income > 0 else 0
            labels.append(f"{row['category']}")
            sizes.append(float(row['total']))  # FIX: convert to float
            percentages.append(pct)

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 8))

        # FIX: use np.linspace(0.3, 0.8) — colormap expects float values 0.0-1.0
        # The original range(50, 200, ...) was incorrect and caused TypeError
        colors = [plt.cm.Greens(i) for i in np.linspace(0.3, 0.8, len(labels))]

        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=None,
            autopct='%1.1f%%',
            colors=colors,
            startangle=90
        )

        # Style percentage text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
            autotext.set_weight('bold')

        # Add legend with percentages
        legend_labels = [f"{label} ({pct:.1f}%)" for label, pct in zip(labels, percentages)]
        ax.legend(
            legend_labels,
            title="Kategori",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=9
        )

        # FIX: Hapus set_title agar tidak nabrak header "DISTRIBUSI PEMASUKAN" di PDF
        plt.tight_layout()
        plt.subplots_adjust(top=0.95)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return filepath

    def generate_expense_pie_chart(self, filename: str = None) -> str:
        """Generate pie chart for expenses by category"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'pie_expense_{timestamp}.png'

        filepath = os.path.join(CHART_DIR, filename)

        # Get expense data
        data = self.db.get_spending_by_category()

        if not data:
            return None

        # Calculate total
        total_expense = sum(row['total'] for row in data)

        # Prepare data
        labels = []
        sizes = []
        percentages = []

        for row in data:
            pct = (row['total'] / total_expense * 100) if total_expense > 0 else 0
            labels.append(f"{row['category']}")
            sizes.append(float(row['total']))  # FIX: convert to float
            percentages.append(pct)

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 8))

        # FIX: use np.linspace(0.3, 0.8) — colormap expects float values 0.0-1.0
        colors = [plt.cm.Reds(i) for i in np.linspace(0.3, 0.8, len(labels))]

        # Create pie chart
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=None,
            autopct='%1.1f%%',
            colors=colors,
            startangle=90
        )

        # Style percentage text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(10)
            autotext.set_weight('bold')

        # Add legend with percentages
        legend_labels = [f"{label} ({pct:.1f}%)" for label, pct in zip(labels, percentages)]
        ax.legend(
            legend_labels,
            title="Kategori",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=9
        )

        # FIX: Hapus set_title agar tidak nabrak header "DISTRIBUSI PENGELUARAN" di PDF
        plt.tight_layout()
        plt.subplots_adjust(top=0.95)
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

        filepath = os.path.join(CHART_DIR, filename)

        # Get date range
        end_date = datetime.now(TIMEZONE)
        start_date = end_date - timedelta(days=days)

        # Get daily spending
        daily_data = {}
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            daily_expense = self.db.get_total_by_type('expense', date_str, date_str)
            daily_data[date_str] = daily_expense
            current_date += timedelta(days=1)

        if not daily_data or sum(daily_data.values()) == 0:
            return None

        # Prepare data
        dates = list(daily_data.keys())
        # FIX: convert to float — large rupiah integers cause "Python int too large to convert to C int"
        amounts = [float(v) for v in daily_data.values()]

        # Convert dates to datetime
        date_objects = [datetime.strptime(d, "%Y-%m-%d") for d in dates]

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))

        # Plot
        ax.plot(date_objects, amounts, marker='o', linewidth=2, markersize=4, color='#e74c3c')
        ax.fill_between(date_objects, amounts, alpha=0.3, color='#e74c3c')

        # Format
        ax.set_xlabel('Tanggal', fontsize=12)
        ax.set_ylabel('Pengeluaran (Rp)', fontsize=12)
        ax.set_title(f'Trend Pengeluaran Harian ({days} Hari Terakhir)', fontsize=14, weight='bold')

        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 10)))
        plt.xticks(rotation=45, ha='right')

        # Grid
        ax.grid(True, alpha=0.3, linestyle='--')

        # FIX: float-safe y-axis formatter
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'Rp{float(x):,.0f}'))

        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return filepath
