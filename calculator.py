#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Calculator
Simplified - No target logic
"""

from datetime import datetime, timedelta
from database import Database
from config import TIMEZONE

class Calculator:
    def __init__(self, db: Database):
        self.db = db
    
    def get_saldo_info(self):
        """Get current saldo information"""
        total_income = self.db.get_total_by_type('income')
        total_expense = self.db.get_total_by_type('expense')
        saldo = total_income - total_expense
        
        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'saldo': saldo
        }
    
    def get_top_categories(self, limit=5):
        """Get top spending categories"""
        return self.db.get_spending_by_category()[:limit]
    
    def calculate_percentage_by_category(self):
        """Calculate spending percentage by category"""
        categories = self.db.get_spending_by_category()
        total_expense = self.db.get_total_by_type('expense')
        
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
    
    def get_period_summary(self, days=7):
        """Get summary for the last N days"""
        today = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
        start_date = (datetime.now(TIMEZONE) - timedelta(days=days)).strftime("%Y-%m-%d")
        
        income = self.db.get_total_by_type('income', start_date, today)
        expense = self.db.get_total_by_type('expense', start_date, today)
        
        return {
            'period_days': days,
            'start_date': start_date,
            'end_date': today,
            'income': income,
            'expense': expense,
            'balance': income - expense
        }
    
    def generate_insights(self):
        """Generate simple insights"""
        insights = []
        
        # Get this week and last week data
        this_week = self.get_period_summary(7)
        last_week = self.get_period_summary(14)
        last_week_expense = last_week['expense'] - this_week['expense']
        
        # Compare with last week
        if last_week_expense > 0:
            diff_pct = ((this_week['expense'] - last_week_expense) / last_week_expense * 100)
            if abs(diff_pct) > 10:
                if diff_pct > 0:
                    insights.append(f"Pengeluaran minggu ini naik {diff_pct:.0f}% dari minggu lalu")
                else:
                    insights.append(f"Pengeluaran minggu ini turun {abs(diff_pct):.0f}% dari minggu lalu")
        
        # Top category
        top_cats = self.get_top_categories(1)
        if top_cats:
            total_expense = self.db.get_total_by_type('expense')
            pct = (top_cats[0]['total'] / total_expense * 100) if total_expense > 0 else 0
            insights.append(f"Kategori terbesar: {top_cats[0]['category']} ({pct:.0f}% dari total)")
        
        return insights
