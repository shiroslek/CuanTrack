#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Notifier
Handles scheduled notifications
"""

from datetime import datetime
import asyncio
from telegram import Bot

from database import Database
from calculator import Calculator
from config import TELEGRAM_BOT_TOKEN, TIMEZONE

class Notifier:
    def __init__(self, db: Database):
        self.db = db
        self.calc = Calculator(db)
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    def format_rupiah(self, amount):
        """Format number to rupiah"""
        return f"Rp{amount:,}".replace(",", ".")
    
    async def send_morning_notification(self):
        """Send morning notification with daily limit"""
        
        # Get admin user ID
        admin_id = self.db.get_setting('admin_user_id')
        
        if not admin_id:
            print("Admin user ID not set")
            return
        
        # Get saldo info
        saldo_info = self.calc.get_saldo_info()
        
        # Get target info
        target = self.db.get_active_target()
        
        # Build message
        text = "☀️ *SELAMAT PAGI!*\n"
        text += "━━━━━━━━━━━━━━━━\n\n"
        text += f"💳 Saldo: *{self.format_rupiah(saldo_info['saldo'])}*\n"
        
        if target:
            days_left = self.calc.get_days_until_date(target['target_date'])
            daily_limit = self.calc.calculate_daily_limit(
                target['target_date'], 
                target['target_amount']
            )
            
            text += f"📊 Limit Hari Ini: *{self.format_rupiah(daily_limit)}*\n\n"
            text += f"📅 {days_left} hari lagi deadline ({target['target_date']})\n"
        
        # Get active notes
        piutang = self.db.get_active_notes('piutang')
        
        if piutang:
            text += "\n⚠️ *Reminder:*\n"
            for note in piutang:
                text += f"   • Piutang {note['person']}: {self.format_rupiah(note['amount'])}\n"
        
        text += "\n_Semangat hari ini! 💪_"
        
        try:
            await self.bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode='Markdown'
            )
            print(f"✅ Morning notification sent to {admin_id}")
        except Exception as e:
            print(f"❌ Error sending morning notification: {e}")
    
    async def send_night_recap(self):
        """Send night recap with daily summary"""
        
        # Get admin user ID
        admin_id = self.db.get_setting('admin_user_id')
        
        if not admin_id:
            print("Admin user ID not set")
            return
        
        today = datetime.now(TIMEZONE).strftime('%Y-%m-%d')
        
        # Get today's transactions
        income_today = self.db.get_total_by_type('income', today, today)
        expense_today = self.db.get_total_by_type('expense', today, today)
        
        # Get saldo
        saldo_info = self.calc.get_saldo_info()
        
        # Get today's spending by category
        spending = self.db.get_spending_by_category(today, today)
        
        # Build message
        text = f"🌙 *RECAP HARI INI ({today})*\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        text += f"📥 Pemasukan: {self.format_rupiah(income_today)}\n"
        text += f"📤 Pengeluaran: {self.format_rupiah(expense_today)}\n\n"
        
        # Top spending today
        if spending:
            text += "🔝 *Top Spending:*\n"
            for i, cat in enumerate(spending[:3], 1):
                text += f"{i}. {cat['category']} - {self.format_rupiah(cat['total'])}\n"
            text += "\n"
        
        # Check against limit
        target = self.db.get_active_target()
        
        if target:
            days_left = self.calc.get_days_until_date(target['target_date'])
            daily_limit = self.calc.calculate_daily_limit(
                target['target_date'], 
                target['target_amount']
            )
            
            if expense_today > daily_limit:
                over = expense_today - daily_limit
                pct = (expense_today / daily_limit * 100) if daily_limit > 0 else 0
                text += f"⚠️ Over limit: {self.format_rupiah(over)} ({pct:.0f}% dari target!)\n\n"
                text += "💡 Besok lebih hemat ya! 😊\n"
            else:
                text += "✅ Masih dalam limit!\n\n"
            
            # Tomorrow's limit
            tomorrow_limit = self.calc.calculate_daily_limit(
                target['target_date'], 
                target['target_amount']
            )
            text += f"📊 Limit besok: {self.format_rupiah(tomorrow_limit)}\n"
        
        text += f"\n💳 Saldo: *{self.format_rupiah(saldo_info['saldo'])}*"
        
        try:
            await self.bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode='Markdown'
            )
            print(f"✅ Night recap sent to {admin_id}")
        except Exception as e:
            print(f"❌ Error sending night recap: {e}")
    
    async def send_target_reminder(self):
        """Send reminder when approaching target deadline"""
        
        # Get admin user ID
        admin_id = self.db.get_setting('admin_user_id')
        
        if not admin_id:
            return
        
        target = self.db.get_active_target()
        
        if not target:
            return
        
        days_left = self.calc.get_days_until_date(target['target_date'])
        
        # Only send if 3, 2, or 1 days left
        if days_left not in [3, 2, 1]:
            return
        
        saldo_info = self.calc.get_saldo_info()
        saldo = saldo_info['saldo']
        
        text = "⏰ *PENGINGAT TARGET*\n"
        text += "━━━━━━━━━━━━━━━━\n\n"
        text += f"🎯 Target: {self.format_rupiah(target['target_amount'])}\n"
        text += f"📅 Deadline: {target['target_date']} (*{days_left} hari lagi!*)\n"
        text += f"💳 Saldo sekarang: {self.format_rupiah(saldo)}\n\n"
        
        if saldo < target['target_amount']:
            diff = target['target_amount'] - saldo
            text += f"❌ KURANG: {self.format_rupiah(diff)}\n\n"
            text += "💡 *Tips:*\n"
            text += "   • Kurangi pengeluaran yang tidak perlu\n"
            text += "   • Cari tambahan pemasukan?\n"
            
            # Check piutang
            piutang = self.db.get_active_notes('piutang')
            if piutang:
                total_piutang = sum(n['amount'] for n in piutang)
                text += f"   • Tagih piutang ({self.format_rupiah(total_piutang)})\n"
        else:
            diff = saldo - target['target_amount']
            text += f"✅ LEBIH: {self.format_rupiah(diff)}\n"
            text += "\n🎉 Kamu on track! Pertahankan!\n"
        
        try:
            await self.bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode='Markdown'
            )
            print(f"✅ Target reminder sent to {admin_id}")
        except Exception as e:
            print(f"❌ Error sending target reminder: {e}")

# Standalone functions for cron jobs
async def send_morning():
    """Standalone function for morning notification"""
    db = Database()
    notifier = Notifier(db)
    await notifier.send_morning_notification()
    db.close()

async def send_night():
    """Standalone function for night recap"""
    db = Database()
    notifier = Notifier(db)
    await notifier.send_night_recap()
    db.close()

async def send_reminder():
    """Standalone function for target reminder"""
    db = Database()
    notifier = Notifier(db)
    await notifier.send_target_reminder()
    db.close()

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        notif_type = sys.argv[1]
        
        if notif_type == 'morning':
            asyncio.run(send_morning())
        elif notif_type == 'night':
            asyncio.run(send_night())
        elif notif_type == 'reminder':
            asyncio.run(send_reminder())
        else:
            print("Usage: python notifier.py [morning|night|reminder]")
    else:
        print("Usage: python notifier.py [morning|night|reminder]")
