#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Database Handler
v2.2 - Multi-user support (user_id added to all tables)
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
        self._migrate_add_user_id()

    def init_db(self):
        """Initialize database schema"""
        # Transactions table with user_id
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 0,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount INTEGER NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Categories table (global/shared across all users)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                is_default BOOLEAN DEFAULT 0,
                icon TEXT
            )
        """)

        # Notes table with user_id
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 0,
                description TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Settings table (key prefixed with user_id internally)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        self.conn.commit()
        self._init_default_categories()

    def _migrate_add_user_id(self):
        """Add user_id column to existing tables if not present (safe migration)"""
        for table in ['transactions', 'notes']:
            cursor = self.conn.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in cursor.fetchall()]
            if 'user_id' not in cols:
                self.conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0"
                )
        self.conn.commit()

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

    def add_transaction(self, user_id, date, time, trans_type, category, amount, description=""):
        """Add new transaction for a user"""
        self.cursor.execute("""
            INSERT INTO transactions (user_id, date, time, type, category, amount, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, date, time, trans_type, category, amount, description))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_transactions(self, user_id, trans_type=None, limit=None, start_date=None, end_date=None):
        """Get transactions with filters for a user"""
        query = "SELECT * FROM transactions WHERE user_id = ?"
        params = [user_id]

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

    def get_transactions_by_date(self, user_id, date):
        """Get all transactions for a specific date for a user"""
        self.cursor.execute("""
            SELECT * FROM transactions
            WHERE user_id = ? AND date = ?
            ORDER BY time DESC
        """, (user_id, date))
        return self.cursor.fetchall()

    def get_transaction_by_id(self, trans_id):
        """Get transaction by ID (no user_id filter - used for edit/delete by ID)"""
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

    def get_total_by_type(self, user_id, trans_type, start_date=None, end_date=None):
        """Get total amount by type for a user"""
        query = "SELECT COALESCE(SUM(amount), 0) as total FROM transactions WHERE user_id = ? AND type = ?"
        params = [user_id, trans_type]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        self.cursor.execute(query, params)
        return self.cursor.fetchone()['total']

    def get_spending_by_category(self, user_id, start_date=None, end_date=None):
        """Get expense spending grouped by category for a user"""
        query = """
            SELECT category, SUM(amount) as total, COUNT(*) as count
            FROM transactions
            WHERE user_id = ? AND type = 'expense'
        """
        params = [user_id]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " GROUP BY category ORDER BY total DESC"
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def get_income_by_category(self, user_id, start_date=None, end_date=None):
        """Get income grouped by category for a user"""
        query = """
            SELECT category, SUM(amount) as total, COUNT(*) as count
            FROM transactions
            WHERE user_id = ? AND type = 'income'
        """
        params = [user_id]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)

        query += " GROUP BY category ORDER BY total DESC"
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def get_unique_dates(self, user_id, limit=30):
        """Get unique transaction dates for a user (most recent first)"""
        self.cursor.execute("""
            SELECT DISTINCT date
            FROM transactions
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT ?
        """, (user_id, limit))
        return [row['date'] for row in self.cursor.fetchall()]

    def reset_user_data(self, user_id):
        """Reset all transactions and notes for a specific user"""
        self.cursor.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        self.cursor.execute("DELETE FROM notes WHERE user_id = ?", (user_id,))
        self.cursor.execute("DELETE FROM settings WHERE key LIKE ?", (f"{user_id}_%",))
        self.conn.commit()

    # ==================== CATEGORIES (Global / Shared) ====================

    def get_categories(self, trans_type=None):
        """Get categories (shared across all users)"""
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
            return False

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
        self.cursor.execute("""
            SELECT COUNT(*) as count FROM transactions WHERE category = ?
        """, (name,))
        if self.cursor.fetchone()['count'] > 0:
            return False

        self.cursor.execute("DELETE FROM categories WHERE name = ?", (name,))
        self.conn.commit()
        return True

    def get_category_by_name(self, name):
        """Get category by name"""
        self.cursor.execute("SELECT * FROM categories WHERE name = ?", (name,))
        return self.cursor.fetchone()

    # ==================== NOTES ====================

    def add_note(self, user_id, description):
        """Add note for a user"""
        self.cursor.execute("""
            INSERT INTO notes (user_id, description)
            VALUES (?, ?)
        """, (user_id, description))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_all_notes(self, user_id):
        """Get all notes for a user"""
        self.cursor.execute("""
            SELECT * FROM notes
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        return self.cursor.fetchall()

    def delete_note(self, note_id):
        """Delete note"""
        self.cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.conn.commit()

    # ==================== SETTINGS ====================

    def set_setting(self, user_id, key, value):
        """Set setting for a user (key auto-prefixed with user_id)"""
        full_key = f"{user_id}_{key}"
        self.cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        """, (full_key, value))
        self.conn.commit()

    def get_setting(self, user_id, key, default=None):
        """Get setting for a user"""
        full_key = f"{user_id}_{key}"
        self.cursor.execute("SELECT value FROM settings WHERE key = ?", (full_key,))
        result = self.cursor.fetchone()
        return result['value'] if result else default

    def close(self):
        """Close database connection"""
        self.conn.close()
