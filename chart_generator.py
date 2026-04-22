#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Chart Generator
v2.4 - Donut chart, fast render, no heavy shadow loops
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime, timedelta
import os

from database import Database
from config import CHART_DIR, TIMEZONE

DONUT_COLORS = [
    '#E8A598', '#C4A882', '#9DC4B8', '#C4A8C8',
    '#E8C898', '#A8B8C8', '#B8D4A8', '#D4A8B8',
    '#C8C4A8', '#A8C4D4',
]


class ChartGenerator:
    def __init__(self, db: Database):
        self.db = db
        plt.rcParams['font.family'] = 'DejaVu Sans'

    def _draw_donut(self, labels, sizes, percentages, title, filepath):
        fig, ax = plt.subplots(figsize=(11, 8), facecolor='#FAF8F5')
        ax.set_facecolor('#FAF8F5')

        n = len(labels)
        colors = (DONUT_COLORS * 3)[:n]

        # Donut chart — satu kali render, tidak ada loop shadow
        wedges, _ = ax.pie(
            sizes,
            radius=1.0,
            startangle=90,
            colors=colors,
            wedgeprops=dict(
                width=0.42,
                edgecolor='white',
                linewidth=2.2,
            ),
            shadow=True,   # shadow bawaan matplotlib, ringan
        )

        # Lingkaran dalam
        center_circle = plt.Circle((0, 0), 0.57, color='#FAF8F5', zorder=10)
        ax.add_patch(center_circle)

        # Label dengan garis leader
        for i, (wedge, label, pct) in enumerate(zip(wedges, labels, percentages)):
            if pct < 2.0:
                continue

            angle = (wedge.theta2 + wedge.theta1) / 2
            angle_rad = np.deg2rad(angle)

            x_out = 1.18 * np.cos(angle_rad)
            y_out = 1.18 * np.sin(angle_rad)
            x_in  = 0.80 * np.cos(angle_rad)
            y_in  = 0.80 * np.sin(angle_rad)

            ax.annotate('',
                xy=(x_in, y_in), xytext=(x_out * 0.96, y_out * 0.96),
                arrowprops=dict(arrowstyle='-', color='#AAAAAA', lw=0.8),
                zorder=12)

            ha = 'left' if x_out > 0 else 'right'
            ax.text(x_out * 1.03, y_out * 1.03 + 0.04,
                    f'{pct:.1f}%', ha=ha, va='center',
                    fontsize=8, fontweight='bold', color='#444444', zorder=13)
            ax.text(x_out * 1.03, y_out * 1.03 - 0.09,
                    label, ha=ha, va='center',
                    fontsize=7, color='#777777', zorder=13)

        # Legend
        legend_patches = [
            mpatches.Patch(color=colors[i], label=f'{labels[i]} ({percentages[i]:.1f}%)')
            for i in range(n)
        ]
        ax.legend(
            handles=legend_patches,
            title='Kategori', title_fontsize=9,
            loc='center left', bbox_to_anchor=(1.02, 0.5),
            fontsize=8, frameon=True, framealpha=0.9, edgecolor='#DDDDDD',
        )

        ax.set_title(title, fontsize=13, fontweight='bold', color='#333333', pad=14)
        ax.set_xlim(-1.55, 1.55)
        ax.set_ylim(-1.35, 1.35)
        ax.axis('equal')

        plt.tight_layout()
        plt.savefig(filepath, dpi=120, bbox_inches='tight', facecolor='#FAF8F5')
        plt.close()
        return filepath

    def generate_income_pie_chart(self, user_id, filename: str = None) -> str:
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'pie_income_{user_id}_{timestamp}.png'
        filepath = os.path.join(CHART_DIR, filename)

        income_data = self.db.get_income_by_category(user_id)
        if not income_data:
            return None

        total = sum(row['total'] for row in income_data)
        labels = [row['category'] for row in income_data]
        sizes  = [row['total'] for row in income_data]
        percentages = [(s / total * 100) if total > 0 else 0 for s in sizes]

        return self._draw_donut(labels, sizes, percentages,
                                'Distribusi Pemasukan per Kategori', filepath)

    def generate_expense_pie_chart(self, user_id, filename: str = None) -> str:
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'pie_expense_{user_id}_{timestamp}.png'
        filepath = os.path.join(CHART_DIR, filename)

        data = self.db.get_spending_by_category(user_id)
        if not data:
            return None

        total = sum(row['total'] for row in data)
        labels = [row['category'] for row in data]
        sizes  = [row['total'] for row in data]
        percentages = [(s / total * 100) if total > 0 else 0 for s in sizes]

        return self._draw_donut(labels, sizes, percentages,
                                'Distribusi Pengeluaran per Kategori', filepath)

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
        for spine in ax.spines.values():
            spine.set_color('#DDDDDD')

        plt.tight_layout()
        plt.savefig(filepath, dpi=120, bbox_inches='tight', facecolor='#FAF8F5')
        plt.close()
        return filepath
