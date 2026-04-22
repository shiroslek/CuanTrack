#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Report Generator
v2.2 - Multi-user support + proper text wrapping in PDF tables
"""

from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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

        # Paragraph styles for table cells
        self.styles = getSampleStyleSheet()
        self.cell_style = ParagraphStyle(
            'CellStyle',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10,
            wordWrap='CJK',
        )
        self.cell_bold = ParagraphStyle(
            'CellBold',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10,
            fontName='Helvetica-Bold',
            wordWrap='CJK',
        )
        self.cell_right = ParagraphStyle(
            'CellRight',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10,
            alignment=TA_RIGHT,
            wordWrap='CJK',
        )
        self.cell_right_bold = ParagraphStyle(
            'CellRightBold',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10,
            fontName='Helvetica-Bold',
            alignment=TA_RIGHT,
            wordWrap='CJK',
        )
        self.header_style = ParagraphStyle(
            'HeaderStyle',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=11,
            fontName='Helvetica-Bold',
            textColor=colors.whitesmoke,
            wordWrap='CJK',
        )

    def p(self, text, style=None):
        """Shorthand to create a Paragraph"""
        return Paragraph(str(text), style or self.cell_style)

    def format_rupiah(self, amount):
        return self.parser.format_rupiah(amount)

    def generate_text_report(self, user_id) -> str:
        """Generate text report for Telegram"""
        saldo_info = self.calc.get_saldo_info(user_id)
        top_categories = self.calc.get_top_categories(user_id, limit=5)
        insights = self.calc.generate_insights(user_id)
        notes = self.db.get_all_notes(user_id)
        recent_income = self.db.get_transactions(user_id, 'income', limit=5)
        recent_expense = self.db.get_transactions(user_id, 'expense', limit=10)

        report = "📊 *LAPORAN KEUANGAN LENGKAP*\n"
        report += "═══════════════════════\n\n"

        report += "*💰 RINGKASAN*\n"
        report += f"Total Pemasukan: {self.format_rupiah(saldo_info['total_income'])}\n"
        report += f"Total Pengeluaran: {self.format_rupiah(saldo_info['total_expense'])}\n"
        report += "────────────────\n"
        report += f"*Saldo: {self.format_rupiah(saldo_info['saldo'])}*\n\n"

        if top_categories:
            report += "*📊 TOP PENGELUARAN*\n"
            total_expense = saldo_info['total_expense']
            for i, cat in enumerate(top_categories, 1):
                pct = (cat['total'] / total_expense * 100) if total_expense > 0 else 0
                report += f"{i}. {cat['category']}: {self.format_rupiah(cat['total'])} ({pct:.1f}%)\n"
            report += "\n"

        if insights:
            report += "*💡 INSIGHTS*\n"
            for insight in insights:
                report += f"• {insight}\n"
            report += "\n"

        if recent_income:
            report += "*💰 PEMASUKAN TERAKHIR*\n"
            for trans in recent_income:
                report += f"• {trans['date']}: {self.format_rupiah(trans['amount'])}\n"
                report += f"  {trans['category']} - {trans['description'] or '-'}\n"
            report += "\n"

        if recent_expense:
            report += "*💸 PENGELUARAN TERAKHIR (10)*\n"
            for trans in recent_expense:
                report += f"• {trans['date']}: {self.format_rupiah(trans['amount'])}\n"
                report += f"  {trans['category']} - {trans['description'] or '-'}\n"
            report += "\n"

        if notes:
            report += "*📓 NOTES AKTIF*\n"
            for i, note in enumerate(notes, 1):
                report += f"{i}. {note['description']}\n"
            report += "\n"

        report += "═══════════════════════\n"
        report += f"_Generated: {datetime.now(TIMEZONE).strftime('%d %b %Y %H:%M')}_"
        return report

    def generate_pdf_report(self, user_id, filename: str = None) -> str:
        """Generate PDF report with proper text wrapping"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'laporan_{user_id}_{timestamp}.pdf'
        filepath = os.path.join(EXPORT_DIR, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            leftMargin=1.5*cm,
            rightMargin=1.5*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        story = []
        styles = self.styles

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=20,
            alignment=TA_CENTER
        )

        story.append(Paragraph("LAPORAN KEUANGAN PERSONAL", title_style))
        story.append(Paragraph(
            f"Generated: {datetime.now(TIMEZONE).strftime('%d %B %Y %H:%M')}",
            ParagraphStyle('sub', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, textColor=colors.grey)
        ))
        story.append(Spacer(1, 16))

        saldo_info = self.calc.get_saldo_info(user_id)
        income_transactions = self.db.get_transactions(user_id, 'income')
        expense_transactions = self.db.get_transactions(user_id, 'expense')
        notes = self.db.get_all_notes(user_id)

        # Column widths - total usable width ~18cm
        col_w = [2.5*cm, 3.5*cm, 8*cm, 4*cm]

        # === TABEL PEMASUKAN ===
        story.append(Paragraph("TABEL PEMASUKAN", styles['Heading2']))
        story.append(Spacer(1, 8))

        income_data = [[
            self.p('Tanggal', self.header_style),
            self.p('Kategori', self.header_style),
            self.p('Keterangan', self.header_style),
            self.p('Jumlah', self.header_style),
        ]]
        for trans in income_transactions:
            income_data.append([
                self.p(trans['date']),
                self.p(trans['category']),
                self.p(trans['description'] or '-'),
                self.p(self.format_rupiah(trans['amount']), self.cell_right),
            ])
        income_data.append([
            self.p(''),
            self.p(''),
            self.p('TOTAL PEMASUKAN', self.cell_bold),
            self.p(self.format_rupiah(saldo_info['total_income']), self.cell_right_bold),
        ])

        income_table = Table(income_data, colWidths=col_w, repeatRows=1)
        income_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27AE60')),
            ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#F9FFF9')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#D5F4E6')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F0FFF4')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#27AE60')),
            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.HexColor('#27AE60')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(income_table)
        story.append(Spacer(1, 20))

        # === TABEL PENGELUARAN ===
        story.append(Paragraph("TABEL PENGELUARAN", styles['Heading2']))
        story.append(Spacer(1, 8))

        expense_data = [[
            self.p('Tanggal', self.header_style),
            self.p('Kategori', self.header_style),
            self.p('Keterangan', self.header_style),
            self.p('Jumlah', self.header_style),
        ]]
        for trans in expense_transactions:
            expense_data.append([
                self.p(trans['date']),
                self.p(trans['category']),
                self.p(trans['description'] or '-'),
                self.p(self.format_rupiah(trans['amount']), self.cell_right),
            ])
        expense_data.append([
            self.p(''),
            self.p(''),
            self.p('TOTAL PENGELUARAN', self.cell_bold),
            self.p(self.format_rupiah(saldo_info['total_expense']), self.cell_right_bold),
        ])

        expense_table = Table(expense_data, colWidths=col_w, repeatRows=1)
        expense_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E74C3C')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#FFF5F5')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FADBD8')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#E74C3C')),
            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.HexColor('#E74C3C')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(expense_table)
        story.append(Spacer(1, 20))

        # === SUMMARY SALDO ===
        story.append(Paragraph("SUMMARY SALDO", styles['Heading2']))
        story.append(Spacer(1, 8))

        saldo_style_white = ParagraphStyle('sw', parent=self.cell_right_bold, textColor=colors.whitesmoke)
        saldo_data = [
            [self.p('Total Pemasukan', self.cell_bold), self.p(self.format_rupiah(saldo_info['total_income']), self.cell_right)],
            [self.p('Total Pengeluaran', self.cell_bold), self.p(self.format_rupiah(saldo_info['total_expense']), self.cell_right)],
            [self.p('SALDO AKHIR', self.cell_bold), self.p(self.format_rupiah(saldo_info['saldo']), self.cell_right_bold)],
        ]
        saldo_table = Table(saldo_data, colWidths=[10*cm, 8*cm])
        saldo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor('#EBF5FB')),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#2E86C1')),
            ('TEXTCOLOR', (0, 2), (-1, 2), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(saldo_table)
        story.append(Spacer(1, 20))

        # === DAFTAR NOTES ===
        if notes:
            story.append(Paragraph("DAFTAR NOTES", styles['Heading2']))
            story.append(Spacer(1, 8))

            notes_data = [[
                self.p('No', self.header_style),
                self.p('Catatan', self.header_style),
            ]]
            for i, note in enumerate(notes, 1):
                notes_data.append([
                    self.p(str(i)),
                    self.p(note['description']),
                ])

            notes_table = Table(notes_data, colWidths=[1.5*cm, 16.5*cm], repeatRows=1)
            notes_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F39C12')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FEF9E7')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ]))
            story.append(notes_table)
            story.append(PageBreak())

        # === PIE CHARTS ===
        income_chart_file = self.chart_gen.generate_income_pie_chart(user_id)
        if income_chart_file:
            story.append(Paragraph("DISTRIBUSI PEMASUKAN PER KATEGORI", styles['Heading2']))
            story.append(Spacer(1, 8))
            story.append(Image(income_chart_file, width=16*cm, height=12*cm))
            story.append(Spacer(1, 20))

        expense_chart_file = self.chart_gen.generate_expense_pie_chart(user_id)
        if expense_chart_file:
            story.append(Paragraph("DISTRIBUSI PENGELUARAN PER KATEGORI", styles['Heading2']))
            story.append(Spacer(1, 8))
            story.append(Image(expense_chart_file, width=16*cm, height=12*cm))

        doc.build(story)
        return filepath

    def generate_excel_report(self, user_id, filename: str = None) -> str:
        """Generate Excel report"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'laporan_{user_id}_{timestamp}.xlsx'
        filepath = os.path.join(EXPORT_DIR, filename)

        wb = openpyxl.Workbook()
        wb.remove(wb.active)

        self._create_income_sheet(wb, user_id)
        self._create_expense_sheet(wb, user_id)
        self._create_saldo_sheet(wb, user_id)
        self._create_notes_sheet(wb, user_id)

        wb.save(filepath)
        return filepath

    def _create_income_sheet(self, wb, user_id):
        ws = wb.create_sheet('Tabel Pemasukan')
        ws['A1'] = 'TABEL PEMASUKAN'
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:D1')

        headers = ['Tanggal', 'Kategori', 'Keterangan', 'Jumlah']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(3, col, header)
            cell.fill = PatternFill(start_color='27AE60', end_color='27AE60', fill_type='solid')
            cell.font = Font(color='FFFFFF', bold=True)
            cell.alignment = Alignment(horizontal='center', wrap_text=True)

        transactions = self.db.get_transactions(user_id, 'income')
        row = 4
        for trans in transactions:
            ws.cell(row, 1, trans['date'])
            ws.cell(row, 2, trans['category'])
            c = ws.cell(row, 3, trans['description'] or '-')
            c.alignment = Alignment(wrap_text=True)
            ws.cell(row, 4, trans['amount']).number_format = '#,##0'
            row += 1

        total_income = self.db.get_total_by_type(user_id, 'income')
        ws.cell(row, 3, 'TOTAL PEMASUKAN').font = Font(bold=True)
        total_cell = ws.cell(row, 4, total_income)
        total_cell.number_format = '#,##0'
        total_cell.font = Font(bold=True)
        total_cell.fill = PatternFill(start_color='D5F4E6', end_color='D5F4E6', fill_type='solid')

        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 40
        ws.column_dimensions['D'].width = 18

    def _create_expense_sheet(self, wb, user_id):
        ws = wb.create_sheet('Tabel Pengeluaran')
        ws['A1'] = 'TABEL PENGELUARAN'
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:D1')

        headers = ['Tanggal', 'Kategori', 'Keterangan', 'Jumlah']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(3, col, header)
            cell.fill = PatternFill(start_color='E74C3C', end_color='E74C3C', fill_type='solid')
            cell.font = Font(color='FFFFFF', bold=True)
            cell.alignment = Alignment(horizontal='center', wrap_text=True)

        transactions = self.db.get_transactions(user_id, 'expense')
        row = 4
        for trans in transactions:
            ws.cell(row, 1, trans['date'])
            ws.cell(row, 2, trans['category'])
            c = ws.cell(row, 3, trans['description'] or '-')
            c.alignment = Alignment(wrap_text=True)
            ws.cell(row, 4, trans['amount']).number_format = '#,##0'
            row += 1

        total_expense = self.db.get_total_by_type(user_id, 'expense')
        ws.cell(row, 3, 'TOTAL PENGELUARAN').font = Font(bold=True)
        total_cell = ws.cell(row, 4, total_expense)
        total_cell.number_format = '#,##0'
        total_cell.font = Font(bold=True)
        total_cell.fill = PatternFill(start_color='FADBD8', end_color='FADBD8', fill_type='solid')

        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 40
        ws.column_dimensions['D'].width = 18

    def _create_saldo_sheet(self, wb, user_id):
        ws = wb.create_sheet('Summary Saldo')
        ws['A1'] = 'SUMMARY SALDO'
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:B1')

        saldo_info = self.calc.get_saldo_info(user_id)

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
        ws['B5'].fill = PatternFill(start_color='2E86C1', end_color='2E86C1', fill_type='solid')
        ws['B5'].font = Font(color='FFFFFF', bold=True, size=12)

        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 20

    def _create_notes_sheet(self, wb, user_id):
        ws = wb.create_sheet('Daftar Notes')
        ws['A1'] = 'DAFTAR NOTES'
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:B1')

        headers = ['No', 'Catatan']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(3, col, header)
            cell.fill = PatternFill(start_color='F39C12', end_color='F39C12', fill_type='solid')
            cell.font = Font(color='FFFFFF', bold=True)
            cell.alignment = Alignment(horizontal='center')

        notes = self.db.get_all_notes(user_id)
        for row, note in enumerate(notes, 4):
            ws.cell(row, 1, row - 3)
            c = ws.cell(row, 2, note['description'])
            c.alignment = Alignment(wrap_text=True)

        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 60

    def generate_pdf(self, user_id, filename=None):
        return self.generate_pdf_report(user_id, filename)

    def generate_excel(self, user_id, filename=None):
        return self.generate_excel_report(user_id, filename)


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
        return self.parser.format_rupiah(amount)

    def generate_text_report(self, user_id) -> str:
        """Generate text report for Telegram"""
        saldo_info = self.calc.get_saldo_info(user_id)
        top_categories = self.calc.get_top_categories(user_id, limit=5)
        insights = self.calc.generate_insights(user_id)
        notes = self.db.get_all_notes(user_id)
        recent_income = self.db.get_transactions(user_id, 'income', limit=5)
        recent_expense = self.db.get_transactions(user_id, 'expense', limit=10)

        report = "📊 *LAPORAN KEUANGAN LENGKAP*\n"
        report += "═══════════════════════\n\n"

        report += "*💰 RINGKASAN*\n"
        report += f"Total Pemasukan: {self.format_rupiah(saldo_info['total_income'])}\n"
        report += f"Total Pengeluaran: {self.format_rupiah(saldo_info['total_expense'])}\n"
        report += "────────────────\n"
        report += f"*Saldo: {self.format_rupiah(saldo_info['saldo'])}*\n\n"

        if top_categories:
            report += "*📊 TOP PENGELUARAN*\n"
            total_expense = saldo_info['total_expense']
            for i, cat in enumerate(top_categories, 1):
                pct = (cat['total'] / total_expense * 100) if total_expense > 0 else 0
                report += f"{i}. {cat['category']}: {self.format_rupiah(cat['total'])} ({pct:.1f}%)\n"
            report += "\n"

        if insights:
            report += "*💡 INSIGHTS*\n"
            for insight in insights:
                report += f"• {insight}\n"
            report += "\n"

        if recent_income:
            report += "*💰 PEMASUKAN TERAKHIR*\n"
            for trans in recent_income:
                report += f"• {trans['date']}: {self.format_rupiah(trans['amount'])}\n"
                report += f"  {trans['category']} - {trans['description'] or '-'}\n"
            report += "\n"

        if recent_expense:
            report += "*💸 PENGELUARAN TERAKHIR (10)*\n"
            for trans in recent_expense:
                report += f"• {trans['date']}: {self.format_rupiah(trans['amount'])}\n"
                report += f"  {trans['category']} - {trans['description'] or '-'}\n"
            report += "\n"

        if notes:
            report += "*📓 NOTES AKTIF*\n"
            for i, note in enumerate(notes, 1):
                report += f"{i}. {note['description']}\n"
            report += "\n"

        report += "═══════════════════════\n"
        report += f"_Generated: {datetime.now(TIMEZONE).strftime('%d %b %Y %H:%M')}_"

        return report

    def generate_pdf_report(self, user_id, filename: str = None) -> str:
        """Generate PDF report"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'laporan_{user_id}_{timestamp}.pdf'
        filepath = os.path.join(EXPORT_DIR, filename)

        doc = SimpleDocTemplate(filepath, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        story.append(Paragraph("LAPORAN KEUANGAN PERSONAL", title_style))
        story.append(Spacer(1, 12))

        saldo_info = self.calc.get_saldo_info(user_id)
        income_transactions = self.db.get_transactions(user_id, 'income')
        expense_transactions = self.db.get_transactions(user_id, 'expense')
        notes = self.db.get_all_notes(user_id)

        # === TABEL PEMASUKAN ===
        story.append(Paragraph("TABEL PEMASUKAN", styles['Heading2']))
        story.append(Spacer(1, 12))

        income_data = [['Tanggal', 'Kategori', 'Keterangan', 'Jumlah']]
        for trans in income_transactions:
            income_data.append([
                trans['date'], trans['category'],
                trans['description'] or '-',
                self.format_rupiah(trans['amount'])
            ])
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
        story.append(Paragraph("TABEL PENGELUARAN", styles['Heading2']))
        story.append(Spacer(1, 12))

        expense_data = [['Tanggal', 'Kategori', 'Keterangan', 'Jumlah']]
        for trans in expense_transactions:
            expense_data.append([
                trans['date'], trans['category'],
                trans['description'] or '-',
                self.format_rupiah(trans['amount'])
            ])
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
        story.append(Paragraph("SUMMARY SALDO", styles['Heading2']))
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
            story.append(Paragraph("DAFTAR NOTES", styles['Heading2']))
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
        income_chart_file = self.chart_gen.generate_income_pie_chart(user_id)
        if income_chart_file:
            story.append(Paragraph("DISTRIBUSI PEMASUKAN PER KATEGORI", styles['Heading2']))
            story.append(Spacer(1, 12))
            story.append(Image(income_chart_file, width=15*cm, height=12*cm))
            story.append(Spacer(1, 20))

        expense_chart_file = self.chart_gen.generate_expense_pie_chart(user_id)
        if expense_chart_file:
            story.append(Paragraph("DISTRIBUSI PENGELUARAN PER KATEGORI", styles['Heading2']))
            story.append(Spacer(1, 12))
            story.append(Image(expense_chart_file, width=15*cm, height=12*cm))

        doc.build(story)
        return filepath

    def generate_excel_report(self, user_id, filename: str = None) -> str:
        """Generate Excel report"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'laporan_{user_id}_{timestamp}.xlsx'
        filepath = os.path.join(EXPORT_DIR, filename)

        wb = openpyxl.Workbook()
        wb.remove(wb.active)

        self._create_income_sheet(wb, user_id)
        self._create_expense_sheet(wb, user_id)
        self._create_saldo_sheet(wb, user_id)
        self._create_notes_sheet(wb, user_id)

        wb.save(filepath)
        return filepath

    def _create_income_sheet(self, wb, user_id):
        ws = wb.create_sheet('Tabel Pemasukan')
        ws['A1'] = 'TABEL PEMASUKAN'
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:D1')

        headers = ['Tanggal', 'Kategori', 'Keterangan', 'Jumlah']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(3, col, header)
            cell.fill = PatternFill(start_color='27AE60', end_color='27AE60', fill_type='solid')
            cell.font = Font(color='FFFFFF', bold=True)
            cell.alignment = Alignment(horizontal='center')

        transactions = self.db.get_transactions(user_id, 'income')
        row = 4
        for trans in transactions:
            ws.cell(row, 1, trans['date'])
            ws.cell(row, 2, trans['category'])
            ws.cell(row, 3, trans['description'] or '-')
            ws.cell(row, 4, trans['amount'])
            ws.cell(row, 4).number_format = '#,##0'
            row += 1

        total_income = self.db.get_total_by_type(user_id, 'income')
        ws.cell(row, 3, 'TOTAL PEMASUKAN').font = Font(bold=True)
        ws.cell(row, 4, total_income)
        ws.cell(row, 4).number_format = '#,##0'
        ws.cell(row, 4).font = Font(bold=True)
        ws.cell(row, 4).fill = PatternFill(start_color='D5F4E6', end_color='D5F4E6', fill_type='solid')

        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 35
        ws.column_dimensions['D'].width = 15

    def _create_expense_sheet(self, wb, user_id):
        ws = wb.create_sheet('Tabel Pengeluaran')
        ws['A1'] = 'TABEL PENGELUARAN'
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:D1')

        headers = ['Tanggal', 'Kategori', 'Keterangan', 'Jumlah']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(3, col, header)
            cell.fill = PatternFill(start_color='E74C3C', end_color='E74C3C', fill_type='solid')
            cell.font = Font(color='FFFFFF', bold=True)
            cell.alignment = Alignment(horizontal='center')

        transactions = self.db.get_transactions(user_id, 'expense')
        row = 4
        for trans in transactions:
            ws.cell(row, 1, trans['date'])
            ws.cell(row, 2, trans['category'])
            ws.cell(row, 3, trans['description'] or '-')
            ws.cell(row, 4, trans['amount'])
            ws.cell(row, 4).number_format = '#,##0'
            row += 1

        total_expense = self.db.get_total_by_type(user_id, 'expense')
        ws.cell(row, 3, 'TOTAL PENGELUARAN').font = Font(bold=True)
        ws.cell(row, 4, total_expense)
        ws.cell(row, 4).number_format = '#,##0'
        ws.cell(row, 4).font = Font(bold=True)
        ws.cell(row, 4).fill = PatternFill(start_color='FADBD8', end_color='FADBD8', fill_type='solid')

        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 35
        ws.column_dimensions['D'].width = 15

    def _create_saldo_sheet(self, wb, user_id):
        ws = wb.create_sheet('Summary Saldo')
        ws['A1'] = 'SUMMARY SALDO'
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:B1')

        saldo_info = self.calc.get_saldo_info(user_id)

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
        ws['B5'].fill = PatternFill(start_color='3498DB', end_color='3498DB', fill_type='solid')
        ws['B5'].font = Font(color='FFFFFF', bold=True, size=12)

        ws.column_dimensions['A'].width = 25
        ws.column_dimensions['B'].width = 20

    def _create_notes_sheet(self, wb, user_id):
        ws = wb.create_sheet('Daftar Notes')
        ws['A1'] = 'DAFTAR NOTES'
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:B1')

        headers = ['No', 'Catatan']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(3, col, header)
            cell.fill = PatternFill(start_color='F39C12', end_color='F39C12', fill_type='solid')
            cell.font = Font(color='FFFFFF', bold=True)
            cell.alignment = Alignment(horizontal='center')

        notes = self.db.get_all_notes(user_id)
        for row, note in enumerate(notes, 4):
            ws.cell(row, 1, row - 3)
            ws.cell(row, 2, note['description'])

        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 60

    # Legacy method aliases (backward compat)
    def generate_pdf(self, user_id, filename=None):
        return self.generate_pdf_report(user_id, filename)

    def generate_excel(self, user_id, filename=None):
        return self.generate_excel_report(user_id, filename)
