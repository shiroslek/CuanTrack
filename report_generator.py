#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Report Generator
v2.1 - Synced PDF/Excel format with dual pie charts
"""

from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
import os

from database import Database
from calculator import Calculator
from config import EXPORT_DIR, TIMEZONE
from parser import NumberParser
from chart_generator import ChartGenerator

class ReportGenerator:
    def __init__(self, db: Database):
        self.db = db
        self.calc = Calculator(db)
        self.parser = NumberParser()
        self.chart_gen = ChartGenerator(db)
    
    def format_rupiah(self, amount):
        """Format number to rupiah"""
        return self.parser.format_rupiah(amount)
    
    def generate_text_report(self) -> str:
        """Generate text report for Telegram"""
        
        # Get data
        saldo_info = self.calc.get_saldo_info()
        top_categories = self.calc.get_top_categories(limit=5)
        insights = self.calc.generate_insights()
        notes = self.db.get_all_notes()
        
        # Get recent transactions
        recent_income = self.db.get_transactions('income', limit=5)
        recent_expense = self.db.get_transactions('expense', limit=10)
        
        # Build report
        report = "📊 *LAPORAN KEUANGAN LENGKAP*\n"
        report += "═══════════════════════\n\n"
        
        # Summary
        report += "*💰 RINGKASAN*\n"
        report += f"Total Pemasukan: {self.format_rupiah(saldo_info['total_income'])}\n"
        report += f"Total Pengeluaran: {self.format_rupiah(saldo_info['total_expense'])}\n"
        report += "────────────────\n"
        report += f"*Saldo: {self.format_rupiah(saldo_info['saldo'])}*\n\n"
        
        # Top Categories
        if top_categories:
            report += "*📊 TOP PENGELUARAN*\n"
            total_expense = saldo_info['total_expense']
            
            for i, cat in enumerate(top_categories, 1):
                pct = (cat['total'] / total_expense * 100) if total_expense > 0 else 0
                report += f"{i}. {cat['category']}: {self.format_rupiah(cat['total'])} ({pct:.1f}%)\n"
            
            report += "\n"
        
        # Insights
        if insights:
            report += "*💡 INSIGHTS*\n"
            for insight in insights:
                report += f"• {insight}\n"
            report += "\n"
        
        # Recent Income
        if recent_income:
            report += "*💰 PEMASUKAN TERAKHIR*\n"
            for trans in recent_income[:5]:
                report += f"• {trans['date']}: {self.format_rupiah(trans['amount'])}\n"
                report += f"  {trans['category']} - {trans['description'] or '-'}\n"
            report += "\n"
        
        # Recent Expense
        if recent_expense:
            report += "*💸 PENGELUARAN TERAKHIR (10)*\n"
            for trans in recent_expense[:10]:
                report += f"• {trans['date']}: {self.format_rupiah(trans['amount'])}\n"
                report += f"  {trans['category']} - {trans['description'] or '-'}\n"
            report += "\n"
        
        # Notes
        if notes:
            report += "*📓 NOTES AKTIF*\n"
            for i, note in enumerate(notes, 1):
                report += f"{i}. {note['description']}\n"
            report += "\n"
        
        report += "═══════════════════════\n"
        report += f"_Generated: {datetime.now(TIMEZONE).strftime('%d %b %Y %H:%M')}_"
        
        return report
    
    def generate_pdf(self, filename: str = None) -> str:
        """Generate PDF report with synced format"""
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'laporan_keuangan_{timestamp}.pdf'
        
        filepath = os.path.join(EXPORT_DIR, filename)
        
        # Create PDF
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        title = Paragraph("LAPORAN KEUANGAN PERSONAL", title_style)
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Get data
        saldo_info = self.calc.get_saldo_info()
        income_transactions = self.db.get_transactions('income')
        expense_transactions = self.db.get_transactions('expense')
        notes = self.db.get_all_notes()
        
        # === TABEL PEMASUKAN ===
        income_title = Paragraph("TABEL PEMASUKAN", styles['Heading2'])
        story.append(income_title)
        story.append(Spacer(1, 12))
        
        income_data = [['Tanggal', 'Kategori', 'Keterangan', 'Jumlah']]
        
        for trans in income_transactions:
            income_data.append([
                trans['date'],
                trans['category'],
                trans['description'] or '-',
                self.format_rupiah(trans['amount'])
            ])
        
        # Add total row
        income_data.append(['', '', 'TOTAL PEMASUKAN', self.format_rupiah(saldo_info['total_income'])])
        
        income_table = Table(income_data, colWidths=[3*cm, 4*cm, 6*cm, 4*cm])
        income_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27AE60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#D5F4E6')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(income_table)
        story.append(Spacer(1, 20))
        
        # === TABEL PENGELUARAN ===
        expense_title = Paragraph("TABEL PENGELUARAN", styles['Heading2'])
        story.append(expense_title)
        story.append(Spacer(1, 12))
        
        expense_data = [['Tanggal', 'Kategori', 'Keterangan', 'Jumlah']]
        
        for trans in expense_transactions:
            expense_data.append([
                trans['date'],
                trans['category'],
                trans['description'] or '-',
                self.format_rupiah(trans['amount'])
            ])
        
        # Add total row
        expense_data.append(['', '', 'TOTAL PENGELUARAN', self.format_rupiah(saldo_info['total_expense'])])
        
        expense_table = Table(expense_data, colWidths=[3*cm, 4*cm, 6*cm, 4*cm])
        expense_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E74C3C')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.lightgrey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FADBD8')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(expense_table)
        story.append(Spacer(1, 20))
        
        # === SUMMARY SALDO ===
        saldo_title = Paragraph("SUMMARY SALDO", styles['Heading2'])
        story.append(saldo_title)
        story.append(Spacer(1, 12))
        
        saldo_data = [
            ['Total Pemasukan', self.format_rupiah(saldo_info['total_income'])],
            ['Total Pengeluaran', self.format_rupiah(saldo_info['total_expense'])],
            ['SALDO AKHIR', self.format_rupiah(saldo_info['saldo'])]
        ]
        
        saldo_table = Table(saldo_data, colWidths=[10*cm, 6*cm])
        saldo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 1), colors.beige),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0, 2), (-1, 2), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 2), (-1, 2), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(saldo_table)
        story.append(Spacer(1, 20))
        
        # === DAFTAR NOTES ===
        if notes:
            notes_title = Paragraph("DAFTAR NOTES", styles['Heading2'])
            story.append(notes_title)
            story.append(Spacer(1, 12))
            
            notes_data = [['No', 'Catatan']]
            
            for i, note in enumerate(notes, 1):
                notes_data.append([str(i), note['description']])
            
            notes_table = Table(notes_data, colWidths=[2*cm, 14*cm])
            notes_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F39C12')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgoldenrodyellow),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(notes_table)
            story.append(PageBreak())
        
        # === PIE CHARTS ===
        # Generate income pie chart
        income_chart_file = self.chart_gen.generate_income_pie_chart()
        if income_chart_file:
            chart_title = Paragraph("DISTRIBUSI PEMASUKAN PER KATEGORI", styles['Heading2'])
            story.append(chart_title)
            story.append(Spacer(1, 12))
            
            img = Image(income_chart_file, width=15*cm, height=12*cm)
            story.append(img)
            story.append(Spacer(1, 20))
        
        # Generate expense pie chart
        expense_chart_file = self.chart_gen.generate_expense_pie_chart()
        if expense_chart_file:
            chart_title = Paragraph("DISTRIBUSI PENGELUARAN PER KATEGORI", styles['Heading2'])
            story.append(chart_title)
            story.append(Spacer(1, 12))
            
            img = Image(expense_chart_file, width=15*cm, height=12*cm)
            story.append(img)
        
        # Build PDF
        doc.build(story)
        
        return filepath
    
    def generate_excel(self, filename: str = None) -> str:
        """Generate Excel report with synced format"""
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'laporan_keuangan_{timestamp}.xlsx'
        
        filepath = os.path.join(EXPORT_DIR, filename)
        
        # Create workbook
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        
        # Create sheets matching PDF structure
        self._create_income_sheet(wb)
        self._create_expense_sheet(wb)
        self._create_saldo_sheet(wb)
        self._create_notes_sheet(wb)
        
        # Save
        wb.save(filepath)
        
        return filepath
    
    def _create_income_sheet(self, wb):
        """Create income sheet"""
        
        ws = wb.create_sheet('Tabel Pemasukan')
        
        # Title
        ws['A1'] = 'TABEL PEMASUKAN'
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:D1')
        
        # Headers
        headers = ['Tanggal', 'Kategori', 'Keterangan', 'Jumlah']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(3, col, header)
            cell.fill = PatternFill(start_color='27AE60', end_color='27AE60', fill_type='solid')
            cell.font = Font(color='FFFFFF', bold=True)
            cell.alignment = Alignment(horizontal='center')
        
        # Data
        transactions = self.db.get_transactions('income')
        
        row = 4
        for trans in transactions:
            ws.cell(row, 1, trans['date'])
            ws.cell(row, 2, trans['category'])
            ws.cell(row, 3, trans['description'] or '-')
            ws.cell(row, 4, trans['amount'])
            ws.cell(row, 4).number_format = '#,##0'
            row += 1
        
        # Total
        total_income = self.db.get_total_by_type('income')
        ws.cell(row, 3, 'TOTAL PEMASUKAN')
        ws.cell(row, 3).font = Font(bold=True)
        ws.cell(row, 4, total_income)
        ws.cell(row, 4).number_format = '#,##0'
        ws.cell(row, 4).font = Font(bold=True)
        ws.cell(row, 4).fill = PatternFill(start_color='D5F4E6', end_color='D5F4E6', fill_type='solid')
        
        # Column widths
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 35
        ws.column_dimensions['D'].width = 15
    
    def _create_expense_sheet(self, wb):
        """Create expense sheet"""
        
        ws = wb.create_sheet('Tabel Pengeluaran')
        
        # Title
        ws['A1'] = 'TABEL PENGELUARAN'
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:D1')
        
        # Headers
        headers = ['Tanggal', 'Kategori', 'Keterangan', 'Jumlah']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(3, col, header)
            cell.fill = PatternFill(start_color='E74C3C', end_color='E74C3C', fill_type='solid')
            cell.font = Font(color='FFFFFF', bold=True)
            cell.alignment = Alignment(horizontal='center')
        
        # Data
        transactions = self.db.get_transactions('expense')
        
        row = 4
        for trans in transactions:
            ws.cell(row, 1, trans['date'])
            ws.cell(row, 2, trans['category'])
            ws.cell(row, 3, trans['description'] or '-')
            ws.cell(row, 4, trans['amount'])
            ws.cell(row, 4).number_format = '#,##0'
            row += 1
        
        # Total
        total_expense = self.db.get_total_by_type('expense')
        ws.cell(row, 3, 'TOTAL PENGELUARAN')
        ws.cell(row, 3).font = Font(bold=True)
        ws.cell(row, 4, total_expense)
        ws.cell(row, 4).number_format = '#,##0'
        ws.cell(row, 4).font = Font(bold=True)
        ws.cell(row, 4).fill = PatternFill(start_color='FADBD8', end_color='FADBD8', fill_type='solid')
        
        # Column widths
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 35
        ws.column_dimensions['D'].width = 15
    
    def _create_saldo_sheet(self, wb):
        """Create saldo summary sheet"""
        
        ws = wb.create_sheet('Summary Saldo')
        
        # Title
        ws['A1'] = 'SUMMARY SALDO'
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:B1')
        
        saldo_info = self.calc.get_saldo_info()
        
        ws['A3'] = 'Total Pemasukan'
        ws['B3'] = saldo_info['total_income']
        ws['B3'].number_format = '#,##0'
        
        ws['A4'] = 'Total Pengeluaran'
        ws['B4'] = saldo_info['total_expense']
        ws['B4'].number_format = '#,##0'
        
        ws['A5'] = 'SALDO AKHIR'
        ws['B5'] = saldo_info['saldo']
        ws['B5'].number_format = '#,##0'
        ws['A5'].font = Font(bold=True, size=12)
        ws['B5'].font = Font(bold=True, size=12)
        ws['B5'].fill = PatternFill(start_color='3498DB', end_color='3498DB', fill_type='solid')
        ws['B5'].font = Font(color='FFFFFF', bold=True, size=12)
        
        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 20
    
    def _create_notes_sheet(self, wb):
        """Create notes sheet"""
        
        ws = wb.create_sheet('Daftar Notes')
        
        # Title
        ws['A1'] = 'DAFTAR NOTES'
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:B1')
        
        # Headers
        headers = ['No', 'Catatan']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(3, col, header)
            cell.fill = PatternFill(start_color='F39C12', end_color='F39C12', fill_type='solid')
            cell.font = Font(color='FFFFFF', bold=True)
            cell.alignment = Alignment(horizontal='center')
        
        # Data
        notes = self.db.get_all_notes()
        
        for row, note in enumerate(notes, 4):
            ws.cell(row, 1, row - 3)
            ws.cell(row, 2, note['description'])
        
        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 60
