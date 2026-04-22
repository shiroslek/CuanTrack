#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Chart Generator
v2.6 - Vertical bar chart (kategori di bawah, jumlah di samping/y-axis)
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

    def _draw_bar_chart(self, labels, sizes, percentages, title, filepath, color_bar):
        """Vertical bar chart — kategori di bawah (x), jumlah di kiri (y)"""
        n = len(labels)
        fig, ax = plt.subplots(figsize=(max(8, n * 1.1 + 2), 7), facecolor='#FAF8F5')
        ax.set_facecolor('#FAF8F5')

        x_pos = np.arange(n)

        bars = ax.bar(
            x_pos, sizes,
            color=color_bar,
            edgecolor='white',
            linewidth=0.8,
            width=0.6,
        )

        # Label di atas tiap batang: nominal + persentase
        max_val = max(sizes) if sizes else 1
        for bar, amt, pct in zip(bars, sizes, percentages):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max_val * 0.015,
                f'Rp{amt:,.0f}\n({pct:.1f}%)',
                ha='center', va='bottom',
                fontsize=7.5, color='#444444', linespacing=1.4
            )

        ax.set_xticks(x_pos)
        ax.set_xticklabels(labels, fontsize=9, rotation=25, ha='right')

        ax.set_ylabel('Jumlah (Rp)', fontsize=10)
        ax.set_title(title, fontsize=13, fontweight='bold', color='#333333', pad=14)

        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'Rp{x:,.0f}'))
        ax.set_ylim(0, max_val * 1.30)

        ax.grid(True, axis='y', alpha=0.2, linestyle='--')
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
            filepath, color_bar='#82C99F',
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
            filepath, color_bar='#F1948A',
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
