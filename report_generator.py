#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Report Generator
v2.3 - Proper text wrapping in all PDF tables
"""

from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
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
        self.styles = getSampleStyleSheet()

        self.cell_style = ParagraphStyle('CellStyle', parent=self.styles['Normal'], fontSize=8, leading=11)
        self.cell_bold = ParagraphStyle('CellBold', parent=self.styles['Normal'], fontSize=8, leading=11, fontName='Helvetica-Bold')
        self.cell_right = ParagraphStyle('CellRight', parent=self.styles['Normal'], fontSize=8, leading=11, alignment=TA_RIGHT)
        self.cell_right_bold = ParagraphStyle('CellRightBold', parent=self.styles['Normal'], fontSize=8, leading=11, fontName='Helvetica-Bold', alignment=TA_RIGHT)
        self.header_style = ParagraphStyle('HeaderStyle', parent=self.styles['Normal'], fontSize=9, leading=11, fontName='Helvetica-Bold', textColor=colors.whitesmoke)
        self.header_right = ParagraphStyle('HeaderRight', parent=self.styles['Normal'], fontSize=9, leading=11, fontName='Helvetica-Bold', textColor=colors.whitesmoke, alignment=TA_RIGHT)

    def p(self, text, style=None):
        return Paragraph(str(text), style or self.cell_style)

    def format_rupiah(self, amount):
        return self.parser.format_rupiah(amount)

    def generate_text_report(self, user_id) -> str:
        saldo_info = self.calc.get_saldo_info(user_id)
        top_categories = self.calc.get_top_categories(user_id, limit=5)
        insights = self.calc.generate_insights(user_id)
        notes = self.db.get_all_notes(user_id)
        recent_income = self.db.get_transactions(user_id, 'income', limit=5)
        recent_expense = self.db.get_transactions(user_id, 'expense', limit=10)

        report = "📊 *LAPORAN KEUANGAN LENGKAP*\n═══════════════════════\n\n"
        report += f"*💰 RINGKASAN*\nTotal Pemasukan: {self.format_rupiah(saldo_info['total_income'])}\n"
        report += f"Total Pengeluaran: {self.format_rupiah(saldo_info['total_expense'])}\n────────────────\n"
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
                report += f"• {trans['date']}: {self.format_rupiah(trans['amount'])}\n  {trans['category']} - {trans['description'] or '-'}\n"
            report += "\n"

        if recent_expense:
            report += "*💸 PENGELUARAN TERAKHIR (10)*\n"
            for trans in recent_expense:
                report += f"• {trans['date']}: {self.format_rupiah(trans['amount'])}\n  {trans['category']} - {trans['description'] or '-'}\n"
            report += "\n"

        if notes:
            report += "*📓 NOTES AKTIF*\n"
            for i, note in enumerate(notes, 1):
                report += f"{i}. {note['description']}\n"
            report += "\n"

        report += "═══════════════════════\n"
        report += f"_Generated: {datetime.now(TIMEZONE).strftime('%d %b %Y %H:%M')}_"
        return report

    def _make_trans_table(self, transactions, total_amount, header_hex, total_hex, label):
        # col widths: Tanggal=2.5 | Kategori=3.2 | Keterangan=8.3 | Jumlah=4.0 → total 18cm
        col_w = [2.5*cm, 3.2*cm, 8.3*cm, 4.0*cm]

        data = [[
            self.p('Tanggal', self.header_style),
            self.p('Kategori', self.header_style),
            self.p('Keterangan', self.header_style),
            self.p('Jumlah', self.header_right),
        ]]
        for trans in transactions:
            data.append([
                self.p(trans['date']),
                self.p(trans['category']),
                self.p(trans['description'] or '-'),
                self.p(self.format_rupiah(trans['amount']), self.cell_right),
            ])
        data.append([
            self.p(''), self.p(''),
            self.p(label, self.cell_bold),
            self.p(self.format_rupiah(total_amount), self.cell_right_bold),
        ])

        tbl = Table(data, colWidths=col_w, repeatRows=1)
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(header_hex)),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F7F7F7')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor(total_hex)),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#DDDDDD')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor(header_hex)),
            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.HexColor(header_hex)),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        return tbl

    def generate_pdf_report(self, user_id, filename: str = None) -> str:
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'laporan_{user_id}_{timestamp}.pdf'
        filepath = os.path.join(EXPORT_DIR, filename)

        doc = SimpleDocTemplate(
            filepath, pagesize=A4,
            leftMargin=1.5*cm, rightMargin=1.5*cm,
            topMargin=2*cm, bottomMargin=2*cm,
        )
        story = []
        styles = self.styles

        title_style = ParagraphStyle('T', parent=styles['Heading1'], fontSize=16,
            textColor=colors.HexColor('#2C3E50'), spaceAfter=6, alignment=TA_CENTER)
        sub_style = ParagraphStyle('S', parent=styles['Normal'], alignment=TA_CENTER,
            fontSize=9, textColor=colors.grey, spaceAfter=12)

        story.append(Paragraph("LAPORAN KEUANGAN PERSONAL", title_style))
        story.append(Paragraph(f"Generated: {datetime.now(TIMEZONE).strftime('%d %B %Y %H:%M')}", sub_style))
        story.append(Spacer(1, 8))

        saldo_info = self.calc.get_saldo_info(user_id)
        income_transactions = self.db.get_transactions(user_id, 'income')
        expense_transactions = self.db.get_transactions(user_id, 'expense')
        notes = self.db.get_all_notes(user_id)

        # TABEL PEMASUKAN
        story.append(Paragraph("TABEL PEMASUKAN", styles['Heading2']))
        story.append(Spacer(1, 6))
        story.append(self._make_trans_table(
            income_transactions, saldo_info['total_income'],
            '#27AE60', '#D5F4E6', 'TOTAL PEMASUKAN'
        ))
        story.append(Spacer(1, 18))

        # TABEL PENGELUARAN
        story.append(Paragraph("TABEL PENGELUARAN", styles['Heading2']))
        story.append(Spacer(1, 6))
        story.append(self._make_trans_table(
            expense_transactions, saldo_info['total_expense'],
            '#E74C3C', '#FADBD8', 'TOTAL PENGELUARAN'
        ))
        story.append(Spacer(1, 18))

        # SUMMARY SALDO
        story.append(Paragraph("SUMMARY SALDO", styles['Heading2']))
        story.append(Spacer(1, 6))

        white_bold = ParagraphStyle('WB', parent=self.cell_bold, textColor=colors.whitesmoke, fontSize=10)
        white_right_bold = ParagraphStyle('WRB', parent=self.cell_right_bold, textColor=colors.whitesmoke, fontSize=10)

        saldo_data = [
            [self.p('Total Pemasukan', self.cell_bold), self.p(self.format_rupiah(saldo_info['total_income']), self.cell_right)],
            [self.p('Total Pengeluaran', self.cell_bold), self.p(self.format_rupiah(saldo_info['total_expense']), self.cell_right)],
            [self.p('SALDO AKHIR', white_bold), self.p(self.format_rupiah(saldo_info['saldo']), white_right_bold)],
        ]
        saldo_table = Table(saldo_data, colWidths=[10*cm, 8*cm])
        saldo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor('#EBF5FB')),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#2E86C1')),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#CCCCCC')),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(saldo_table)
        story.append(Spacer(1, 18))

        # DAFTAR NOTES
        if notes:
            story.append(Paragraph("DAFTAR NOTES", styles['Heading2']))
            story.append(Spacer(1, 6))

            notes_data = [[
                self.p('No', self.header_style),
                self.p('Catatan', self.header_style),
            ]]
            for i, note in enumerate(notes, 1):
                notes_data.append([self.p(str(i)), self.p(note['description'])])

            # 1.5cm + 16.5cm = 18cm total, teks catatan wraps dalam 16.5cm
            notes_table = Table(notes_data, colWidths=[1.5*cm, 16.5*cm], repeatRows=1)
            notes_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F39C12')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FEF9E7')]),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#DDDDDD')),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ]))
            story.append(notes_table)
            story.append(PageBreak())

        # BAR CHARTS - masing-masing halaman sendiri
        income_chart = self.chart_gen.generate_income_pie_chart(user_id)
        if income_chart:
            story.append(Paragraph("DISTRIBUSI PEMASUKAN PER KATEGORI", styles['Heading2']))
            story.append(Spacer(1, 8))
            story.append(Image(income_chart, width=17*cm, height=11*cm))
            story.append(PageBreak())

        expense_chart = self.chart_gen.generate_expense_pie_chart(user_id)
        if expense_chart:
            story.append(Paragraph("DISTRIBUSI PENGELUARAN PER KATEGORI", styles['Heading2']))
            story.append(Spacer(1, 8))
            story.append(Image(expense_chart, width=17*cm, height=11*cm))

        doc.build(story)
        return filepath

    def generate_excel_report(self, user_id, filename: str = None) -> str:
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

    def _make_excel_trans_sheet(self, wb, user_id, trans_type, sheet_name, header_color, total_color):
        ws = wb.create_sheet(sheet_name)
        title = 'TABEL PEMASUKAN' if trans_type == 'income' else 'TABEL PENGELUARAN'
        ws['A1'] = title
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:D1')

        for col, header in enumerate(['Tanggal', 'Kategori', 'Keterangan', 'Jumlah'], 1):
            cell = ws.cell(3, col, header)
            cell.fill = PatternFill(start_color=header_color, end_color=header_color, fill_type='solid')
            cell.font = Font(color='FFFFFF', bold=True)
            cell.alignment = Alignment(horizontal='center', wrap_text=True)

        transactions = self.db.get_transactions(user_id, trans_type)
        row = 4
        for trans in transactions:
            ws.cell(row, 1, trans['date'])
            ws.cell(row, 2, trans['category'])
            c = ws.cell(row, 3, trans['description'] or '-')
            c.alignment = Alignment(wrap_text=True, vertical='top')
            amt = ws.cell(row, 4, trans['amount'])
            amt.number_format = '#,##0'
            amt.alignment = Alignment(horizontal='right')
            row += 1

        label = 'TOTAL PEMASUKAN' if trans_type == 'income' else 'TOTAL PENGELUARAN'
        total = self.db.get_total_by_type(user_id, trans_type)
        ws.cell(row, 3, label).font = Font(bold=True)
        tc = ws.cell(row, 4, total)
        tc.number_format = '#,##0'
        tc.font = Font(bold=True)
        tc.fill = PatternFill(start_color=total_color, end_color=total_color, fill_type='solid')
        tc.alignment = Alignment(horizontal='right')

        ws.column_dimensions['A'].width = 13
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 42
        ws.column_dimensions['D'].width = 18

    def _create_income_sheet(self, wb, user_id):
        self._make_excel_trans_sheet(wb, user_id, 'income', 'Tabel Pemasukan', '27AE60', 'D5F4E6')

    def _create_expense_sheet(self, wb, user_id):
        self._make_excel_trans_sheet(wb, user_id, 'expense', 'Tabel Pengeluaran', 'E74C3C', 'FADBD8')

    def _create_saldo_sheet(self, wb, user_id):
        ws = wb.create_sheet('Summary Saldo')
        ws['A1'] = 'SUMMARY SALDO'
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:B1')

        saldo_info = self.calc.get_saldo_info(user_id)
        for i, (label, val) in enumerate([
            ('Total Pemasukan', saldo_info['total_income']),
            ('Total Pengeluaran', saldo_info['total_expense']),
            ('SALDO AKHIR', saldo_info['saldo']),
        ], 3):
            ws.cell(i, 1, label)
            c = ws.cell(i, 2, val)
            c.number_format = '#,##0'
            c.alignment = Alignment(horizontal='right')

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

        for col, header in enumerate(['No', 'Catatan'], 1):
            cell = ws.cell(3, col, header)
            cell.fill = PatternFill(start_color='F39C12', end_color='F39C12', fill_type='solid')
            cell.font = Font(color='FFFFFF', bold=True)
            cell.alignment = Alignment(horizontal='center')

        notes = self.db.get_all_notes(user_id)
        for row, note in enumerate(notes, 4):
            ws.cell(row, 1, row - 3).alignment = Alignment(horizontal='center')
            c = ws.cell(row, 2, note['description'])
            c.alignment = Alignment(wrap_text=True, vertical='top')

        ws.column_dimensions['A'].width = 8
        ws.column_dimensions['B'].width = 65

    def generate_pdf(self, user_id, filename=None):
        return self.generate_pdf_report(user_id, filename)

    def generate_excel(self, user_id, filename=None):
        return self.generate_excel_report(user_id, filename)
