#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Number Parser
Strict validation - only accepts dot format (50.000)
"""

import re

class NumberParser:
    
    @staticmethod
    def parse_amount(text):
        """
        Parse amount with strict dot format validation
        
        Args:
            text: Input string (e.g., "50.000", "1.500.000")
        
        Returns:
            int: Parsed amount or None if invalid
        """
        if not text:
            return None
        
        # Remove whitespace
        text = text.strip()
        
        # Check if it matches dot format pattern
        # Valid: 50.000, 1.500.000, 123.456.789
        # Invalid: 50000, 50k, 50rb, 50,000
        
        # Pattern: digits with dots every 3 digits from right
        # OR just plain digits (1000, 5000, etc)
        pattern = r'^[\d.]+$'
        
        if not re.match(pattern, text):
            return None
        
        # Remove dots and convert to int
        try:
            # Remove all dots
            clean_text = text.replace('.', '')
            
            # Check if it's all digits
            if not clean_text.isdigit():
                return None
            
            amount = int(clean_text)
            
            # Validate amount is reasonable (not 0, not too large)
            if amount <= 0 or amount > 999999999999:  # Max ~1 trillion
                return None
            
            return amount
            
        except (ValueError, AttributeError):
            return None
    
    @staticmethod
    def validate_amount_format(text):
        """
        Validate if amount follows correct dot format
        
        Returns:
            (bool, str): (is_valid, error_message)
        """
        if not text:
            return False, "Jumlah tidak boleh kosong"
        
        text = text.strip()
        
        # Check basic pattern
        if not re.match(r'^[\d.]+$', text):
            return False, "Format salah! Gunakan angka dengan titik (contoh: 50.000)"
        
        # Try to parse
        amount = NumberParser.parse_amount(text)
        
        if amount is None:
            return False, "Format salah! Gunakan titik untuk pemisah ribuan (contoh: 50.000)"
        
        if amount <= 0:
            return False, "Jumlah harus lebih dari 0"
        
        return True, ""
    
    @staticmethod
    def format_rupiah(amount):
        """Format number to rupiah with dots"""
        if amount < 0:
            return f"-Rp{abs(amount):,}".replace(",", ".")
        return f"Rp{amount:,}".replace(",", ".")
