#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Chart Generator
v2.3 - 3D Donut chart style
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


# Warna pastel modern mirip screenshot
DONUT_COLORS = [
    '#E8A598',  # salmon pink
    '#C4A882',  # tan
    '#9DC4B8',  # teal
    '#C4A8C8',  # lavender
    '#E8C898',  # peach
    '#A8B8C8',  # slate blue
    '#B8D4A8',  # sage green
    '#D4A8B8',  # mauve
    '#C8C4A8',  # warm grey
    '#A8C4D4',  # sky blue
]


class ChartGenerator:
    def __init__(self, db: Database):
        self.db = db
        plt.rcParams['font.family'] = 'DejaVu Sans'

    def _draw_donut_3d(self, labels, sizes, percentages, title, filepath, colormap):
        """Draw a 3D-style donut chart"""
        fig = plt.figure(figsize=(12, 9), facecolor='#FAF8F5')
        ax = fig.add_subplot(111, facecolor='#FAF8F5')

        n = len(labels)
        colors = (DONUT_COLORS * 3)[:n]

        # --- Draw 3D shadow layers (bottom to top) ---
        shadow_layers = 6
        for i in range(shadow_layers, 0, -1):
            offset = i * 0.003
            alpha = 0.04
            wedges_shadow, _ = ax.pie(
                sizes,
                radius=1.0,
                startangle=90,
                colors=['#888888'] * n,
                wedgeprops=dict(width=0.45, edgecolor='none'),
                center=(offset, -offset * 1.5),
            )
            for w in wedges_shadow:
                w.set_alpha(alpha)
                w.set_zorder(1)

        # --- Main donut ---
        wedges, texts = ax.pie(
            sizes,
            radius=1.0,
            startangle=90,
            colors=colors,
            wedgeprops=dict(
                width=0.45,
                edgecolor='white',
                linewidth=2.5,
            ),
            center=(0, 0),
        )

        # Add glossy highlight on each wedge
        for w in wedges:
            w.set_zorder(5)
            # lighter edge on top-left for gloss effect
            w.set_linewidth(2.5)

        # --- Center circle decoration ---
        center_circle = plt.Circle((0, 0), 0.54, color='#FAF8F5', zorder=10)
        ax.add_patch(center_circle)
        center_ring = plt.Circle((0, 0), 0.55, color='white', fill=False, linewidth=2, zorder=11)
        ax.add_patch(center_ring)

        # --- Labels with leader lines ---
        for i, (wedge, label, pct) in enumerate(zip(wedges, labels, percentages)):
            if pct < 1.5:
                continue  # skip tiny slices

            angle = (wedge.theta2 + wedge.theta1) / 2
            angle_rad = np.deg2rad(angle)

            # Point on wedge edge
            r_mid = 0.78
            x_mid = r_mid * np.cos(angle_rad)
            y_mid = r_mid * np.sin(angle_rad)

            # Label position
            r_label = 1.22
            x_label = r_label * np.cos(angle_rad)
            y_label = r_label * np.sin(angle_rad)

            # Leader line
            ax.annotate(
                '',
                xy=(x_mid, y_mid),
                xytext=(x_label * 0.97, y_label * 0.97),
                arrowprops=dict(
                    arrowstyle='-',
                    color='#999999',
                    lw=0.8,
                ),
                zorder=12,
            )

            # Percentage label
            ha = 'left' if x_label > 0 else 'right'
            ax.text(
                x_label * 1.02, y_label * 1.02,
                f'{pct:.1f}%',
                ha=ha, va='center',
                fontsize=8.5,
                fontweight='bold',
                color='#444444',
                zorder=13,
            )

            # Category name below percentage
            ax.text(
                x_label * 1.02, y_label * 1.02 - 0.10,
                label,
                ha=ha, va='center',
                fontsize=7.5,
                color='#666666',
                zorder=13,
            )

        # --- Legend (right side) ---
        legend_patches = [
            mpatches.Patch(color=colors[i], label=f'{labels[i]} ({percentages[i]:.1f}%)')
            for i in range(n)
        ]
        ax.legend(
            handles=legend_patches,
            title='Kategori',
            title_fontsize=9,
            loc='center left',
            bbox_to_anchor=(1.05, 0.5),
            fontsize=8,
            frameon=True,
            framealpha=0.9,
            edgecolor='#DDDDDD',
        )

        ax.set_title(title, fontsize=13, fontweight='bold', color='#333333', pad=15)
        ax.set_xlim(-1.6, 1.6)
        ax.set_ylim(-1.4, 1.4)
        ax.axis('equal')

        plt.tight_layout()
        plt.savefig(filepath, dpi=180, bbox_inches='tight', facecolor='#FAF8F5')
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
        sizes = [row['total'] for row in income_data]
        percentages = [(s / total * 100) if total > 0 else 0 for s in sizes]

        return self._draw_donut_3d(labels, sizes, percentages,
                                   'Distribusi Pemasukan per Kategori',
                                   filepath, 'Greens')

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
        sizes = [row['total'] for row in data]
        percentages = [(s / total * 100) if total > 0 else 0 for s in sizes]

        return self._draw_donut_3d(labels, sizes, percentages,
                                   'Distribusi Pengeluaran per Kategori',
                                   filepath, 'Reds')

    def generate_pie_chart(self, user_id, filename: str = None) -> str:
        return self.generate_expense_pie_chart(user_id, filename)

    def generate_trend_chart(self, user_id, days=30, filename: str = None) -> str:
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

        fig, ax = plt.subplots(figsize=(12, 6), facecolor='#FAF8F5')
        ax.set_facecolor('#FAF8F5')

        ax.plot(date_objects, amounts, marker='o', linewidth=2,
                markersize=5, color='#E74C3C', zorder=5)
        ax.fill_between(date_objects, amounts, alpha=0.15, color='#E74C3C')

        ax.set_xlabel('Tanggal', fontsize=11)
        ax.set_ylabel('Pengeluaran (Rp)', fontsize=11)
        ax.set_title(f'Trend Pengeluaran Harian ({days} Hari Terakhir)',
                     fontsize=13, fontweight='bold', color='#333333')

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 10)))
        plt.xticks(rotation=45, ha='right')

        ax.grid(True, alpha=0.25, linestyle='--', color='#AAAAAA')
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'Rp{x:,.0f}'))

        for spine in ax.spines.values():
            spine.set_color('#DDDDDD')

        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='#FAF8F5')
        plt.close()
        return filepath
