#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Database Handler
Updated for Cuan Track v2
"""

import sqlite3
from datetime import datetime
from config import DB_NAME, DEFAULT_INCOME_CATEGORIES, DEFAULT_EXPENSE_CATEGORIES

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.init_db()
    
    def init_db(self):
        """Initialize database schema"""
        
        # Transactions table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount INTEGER NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Categories table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                is_default BOOLEAN DEFAULT 0,
                icon TEXT
            )
        """)
        
        # Notes table - SIMPLIFIED (just text notes)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Settings table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        
        self.conn.commit()
        
        # Initialize default categories
        self._init_default_categories()
    
    def _init_default_categories(self):
        """Initialize default categories"""
        for cat in DEFAULT_INCOME_CATEGORIES:
            self.cursor.execute("""
                INSERT OR IGNORE INTO categories (name, type, is_default, icon)
                VALUES (?, 'income', 1, ?)
            """, (cat['name'], cat['icon']))
        
        for cat in DEFAULT_EXPENSE_CATEGORIES:
            self.cursor.execute("""
                INSERT OR IGNORE INTO categories (name, type, is_default, icon)
                VALUES (?, 'expense', 1, ?)
            """, (cat['name'], cat['icon']))
        
        self.conn.commit()
    
    # ==================== TRANSACTIONS ====================
    
    def add_transaction(self, date, time, trans_type, category, amount, description=""):
        """Add new transaction"""
        self.cursor.execute("""
            INSERT INTO transactions (date, time, type, category, amount, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (date, time, trans_type, category, amount, description))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_transactions(self, trans_type=None, limit=None, start_date=None, end_date=None):
        """Get transactions with filters"""
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []
        
        if trans_type:
            query += " AND type = ?"
            params.append(trans_type)
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date DESC, time DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        self.cursor.execute(query, params)
        return self.cursor.fetchall()
    
    def get_transactions_by_date(self, date):
        """Get all transactions for a specific date"""
        self.cursor.execute("""
            SELECT * FROM transactions 
            WHERE date = ?
            ORDER BY time DESC
        """, (date,))
        return self.cursor.fetchall()
    
    def get_transaction_by_id(self, trans_id):
        """Get transaction by ID"""
        self.cursor.execute("SELECT * FROM transactions WHERE id = ?", (trans_id,))
        return self.cursor.fetchone()
    
    def update_transaction(self, trans_id, date=None, description=None, amount=None):
        """Update transaction"""
        updates = []
        params = []
        
        if date is not None:
            updates.append("date = ?")
            params.append(date)
        
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        
        if amount is not None:
            updates.append("amount = ?")
            params.append(amount)
        
        if not updates:
            return False
        
        params.append(trans_id)
        query = f"UPDATE transactions SET {', '.join(updates)} WHERE id = ?"
        
        self.cursor.execute(query, params)
        self.conn.commit()
        return True
    
    def delete_transaction(self, trans_id):
        """Delete transaction by ID"""
        self.cursor.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))
        self.conn.commit()
    
    def get_total_by_type(self, trans_type, start_date=None, end_date=None):
        """Get total amount by type"""
        query = "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE type = ?"
        params = [trans_type]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        self.cursor.execute(query, params)
        return self.cursor.fetchone()['total']
    
    def get_spending_by_category(self, start_date=None, end_date=None):
        """Get spending grouped by category"""
        query = """
            SELECT category, SUM(amount) as total, COUNT(*) as count
            FROM transactions 
            WHERE type = 'expense'
        """
        params = []
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " GROUP BY category ORDER BY total DESC"
        
        self.cursor.execute(query, params)
        return self.cursor.fetchall()
    
    def get_unique_dates(self, limit=30):
        """Get unique transaction dates (most recent first)"""
        self.cursor.execute("""
            SELECT DISTINCT date 
            FROM transactions 
            ORDER BY date DESC 
            LIMIT ?
        """, (limit,))
        return [row['date'] for row in self.cursor.fetchall()]
    
    # ==================== CATEGORIES ====================
    
    def get_categories(self, trans_type=None):
        """Get categories"""
        if trans_type:
            self.cursor.execute("""
                SELECT * FROM categories WHERE type = ? ORDER BY name
            """, (trans_type,))
        else:
            self.cursor.execute("SELECT * FROM categories ORDER BY type, name")
        
        return self.cursor.fetchall()
    
    def add_category(self, name, trans_type, icon="📌"):
        """Add custom category"""
        try:
            self.cursor.execute("""
                INSERT INTO categories (name, type, is_default, icon)
                VALUES (?, ?, 0, ?)
            """, (name, trans_type, icon))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Category already exists
    
    def update_category(self, old_name, new_name=None, new_icon=None):
        """Update category name and/or icon"""
        updates = []
        params = []
        
        if new_name:
            updates.append("name = ?")
            params.append(new_name)
        
        if new_icon:
            updates.append("icon = ?")
            params.append(new_icon)
        
        if not updates:
            return False
        
        params.append(old_name)
        query = f"UPDATE categories SET {', '.join(updates)} WHERE name = ?"
        
        try:
            self.cursor.execute(query, params)
            
            # Also update transactions with this category
            if new_name:
                self.cursor.execute("""
                    UPDATE transactions SET category = ? WHERE category = ?
                """, (new_name, old_name))
            
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def delete_category(self, name):
        """Delete category (only if no transactions use it)"""
        # Check if any transactions use this category
        self.cursor.execute("""
            SELECT COUNT(*) as count FROM transactions WHERE category = ?
        """, (name,))
        
        if self.cursor.fetchone()['count'] > 0:
            return False  # Cannot delete category with transactions
        
        self.cursor.execute("DELETE FROM categories WHERE name = ?", (name,))
        self.conn.commit()
        return True
    
    def get_category_by_name(self, name):
        """Get category by name"""
        self.cursor.execute("SELECT * FROM categories WHERE name = ?", (name,))
        return self.cursor.fetchone()
    
    # ==================== NOTES ====================
    
    def add_note(self, description):
        """Add note"""
        self.cursor.execute("""
            INSERT INTO notes (description)
            VALUES (?)
        """, (description,))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_all_notes(self):
        """Get all notes"""
        self.cursor.execute("""
            SELECT * FROM notes 
            ORDER BY created_at DESC
        """)
        return self.cursor.fetchall()
    
    def delete_note(self, note_id):
        """Delete note"""
        self.cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.conn.commit()
    
    # ==================== SETTINGS ====================
    
    def set_setting(self, key, value):
        """Set setting"""
        self.cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        """, (key, value))
        self.conn.commit()
    
    def get_setting(self, key, default=None):
        """Get setting"""
        self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = self.cursor.fetchone()
        return result['value'] if result else default
    
    def close(self):
        """Close database connection"""
        self.conn.close()
