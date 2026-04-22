#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Chart Generator
v2.5 - Bar chart (horizontal) untuk income & expense
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
        plt.rcParams['font.family'] = 'DejaVu Sans'

    def _draw_bar_chart(self, labels, sizes, percentages, title, filepath, color_main, color_bar):
        """Horizontal bar chart dengan label persentase"""
        n = len(labels)
        fig, ax = plt.subplots(figsize=(10, max(4, n * 0.55 + 1.5)), facecolor='#FAF8F5')
        ax.set_facecolor('#FAF8F5')

        y_pos = np.arange(n)

        # Bar
        bars = ax.barh(
            y_pos, sizes,
            color=color_bar,
            edgecolor='white',
            linewidth=0.8,
            height=0.6,
        )

        # Label di ujung bar: nominal + persentase
        max_val = max(sizes) if sizes else 1
        for i, (bar, amt, pct) in enumerate(zip(bars, sizes, percentages)):
            ax.text(
                bar.get_width() + max_val * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f'Rp{amt:,.0f}  ({pct:.1f}%)',
                va='center', ha='left',
                fontsize=8, color='#444444'
            )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.invert_yaxis()  # terbesar di atas

        ax.set_xlabel('Jumlah (Rp)', fontsize=10)
        ax.set_title(title, fontsize=13, fontweight='bold', color='#333333', pad=14)

        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'Rp{x:,.0f}'))
        plt.xticks(rotation=20, ha='right', fontsize=8)

        # Extend x-axis biar label tidak terpotong
        ax.set_xlim(0, max_val * 1.45)

        ax.grid(True, axis='x', alpha=0.2, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        for spine in ['left', 'bottom']:
            ax.spines[spine].set_color('#DDDDDD')

        plt.tight_layout()
        plt.savefig(filepath, dpi=130, bbox_inches='tight', facecolor='#FAF8F5')
        plt.close()
        return filepath

    def generate_income_pie_chart(self, user_id, filename: str = None) -> str:
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'bar_income_{user_id}_{timestamp}.png'
        filepath = os.path.join(CHART_DIR, filename)

        income_data = self.db.get_income_by_category(user_id)
        if not income_data:
            return None

        total = sum(row['total'] for row in income_data)
        labels = [row['category'] for row in income_data]
        sizes  = [row['total'] for row in income_data]
        percentages = [(s / total * 100) if total > 0 else 0 for s in sizes]

        return self._draw_bar_chart(
            labels, sizes, percentages,
            'Distribusi Pemasukan per Kategori',
            filepath,
            color_main='#27AE60',
            color_bar='#82C99F',
        )

    def generate_expense_pie_chart(self, user_id, filename: str = None) -> str:
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'bar_expense_{user_id}_{timestamp}.png'
        filepath = os.path.join(CHART_DIR, filename)

        data = self.db.get_spending_by_category(user_id)
        if not data:
            return None

        total = sum(row['total'] for row in data)
        labels = [row['category'] for row in data]
        sizes  = [row['total'] for row in data]
        percentages = [(s / total * 100) if total > 0 else 0 for s in sizes]

        return self._draw_bar_chart(
            labels, sizes, percentages,
            'Distribusi Pengeluaran per Kategori',
            filepath,
            color_main='#E74C3C',
            color_bar='#F1948A',
        )

    def generate_pie_chart(self, user_id, filename: str = None) -> str:
        return self.generate_expense_pie_chart(user_id, filename)

    def generate_trend_chart(self, user_id, days=30, filename: str = None) -> str:
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'trend_chart_{user_id}_{timestamp}.png'
        filepath = os.path.join(CHART_DIR, filename)

        end_date   = datetime.now(TIMEZONE)
        start_date = end_date - timedelta(days=days)

        daily_data = {}
        current = start_date
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            daily_data[date_str] = self.db.get_total_by_type(user_id, 'expense', date_str, date_str)
            current += timedelta(days=1)

        if not daily_data or sum(daily_data.values()) == 0:
            return None

        date_objects = [datetime.strptime(d, "%Y-%m-%d") for d in daily_data]
        amounts = list(daily_data.values())

        fig, ax = plt.subplots(figsize=(11, 5), facecolor='#FAF8F5')
        ax.set_facecolor('#FAF8F5')

        ax.plot(date_objects, amounts, marker='o', linewidth=2,
                markersize=4, color='#E74C3C', zorder=5)
        ax.fill_between(date_objects, amounts, alpha=0.15, color='#E74C3C')

        ax.set_xlabel('Tanggal', fontsize=11)
        ax.set_ylabel('Pengeluaran (Rp)', fontsize=11)
        ax.set_title(f'Trend Pengeluaran Harian ({days} Hari Terakhir)',
                     fontsize=13, fontweight='bold', color='#333333')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 10)))
        plt.xticks(rotation=45, ha='right')
        ax.grid(True, alpha=0.2, linestyle='--')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'Rp{x:,.0f}'))
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        for spine in ['left', 'bottom']:
            ax.spines[spine].set_color('#DDDDDD')

        plt.tight_layout()
        plt.savefig(filepath, dpi=120, bbox_inches='tight', facecolor='#FAF8F5')
        plt.close()
        return filepath
