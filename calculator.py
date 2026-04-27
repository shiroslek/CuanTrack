#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Calculator
v2.2 - Multi-user support (user_id added to all methods)
"""

from datetime import datetime, timedelta
from database import Database
from config import TIMEZONE


class Calculator:
    def __init__(self, db: Database):
        self.db = db

    def get_saldo_info(self, user_id):
        """Get current saldo information for a user"""
        total_income = self.db.get_total_by_type(user_id, 'income')
        total_expense = self.db.get_total_by_type(user_id, 'expense')
        saldo = total_income - total_expense

        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'saldo': saldo
        }

    def get_top_categories(self, user_id, limit=5):
        """Get top spending categories for a user"""
        return self.db.get_spending_by_category(user_id)[:limit]

    def calculate_percentage_by_category(self, user_id):
        """Calculate spending percentage by category for a user"""
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
        """Get summary for the last N days for a user"""
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

    def generate_insights(self, user_id):
        """Generate simple insights for a user"""
        insights = []

        this_week = self.get_period_summary(user_id, 7)
        last_week = self.get_period_summary(user_id, 14)
        last_week_expense = last_week['expense'] - this_week['expense']

        if last_week_expense > 0:
            diff_pct = ((this_week['expense'] - last_week_expense) / last_week_expense * 100)
            if abs(diff_pct) > 10:
                if diff_pct > 0:
                    insights.append(f"Pengeluaran minggu ini naik {diff_pct:.0f}% dari minggu lalu")
                else:
                    insights.append(f"Pengeluaran minggu ini turun {abs(diff_pct):.0f}% dari minggu lalu")

        top_cats = self.get_top_categories(user_id, 1)
        if top_cats:
            total_expense = self.db.get_total_by_type(user_id, 'expense')
            pct = (top_cats[0]['total'] / total_expense * 100) if total_expense > 0 else 0
            insights.append(f"Kategori terbesar: {top_cats[0]['category']} ({pct:.0f}% dari total)")

        return insights
