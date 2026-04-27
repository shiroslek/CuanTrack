#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Financial Tracker Bot - Report Generator
v2.3 - Multi-user + Monthly separation in PDF/Excel
"""

from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar as cal_module

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image, PageBreak, HRFlowable
)
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


def _get_all_months(user_id, db) -> list:
    """
    Ambil semua bulan yang ada transaksinya untuk user ini.
    Return list of (year, month) sorted ascending.
    """
    db.cursor.execute("""
        SELECT DISTINCT substr(date, 1, 7) as ym
        FROM transactions
        WHERE user_id = ?
        ORDER BY ym ASC
    """, (user_id,))
    rows = db.cursor.fetchall()
    result = []
    for row in rows:
        ym = row[0]  # "2026-04"
        y, m = int(ym[:4]), int(ym[5:7])
        result.append((y, m))
    return result


def _month_range(year: int, month: int):
    """Return (start_date, end_date) string untuk satu bulan."""
    start = f"{year:04d}-{month:02d}-01"
    last_day = cal_module.monthrange(year, month)[1]
    end = f"{year:04d}-{month:02d}-{last_day:02d}"
    return start, end


def _month_label(year: int, month: int) -> str:
    dt = datetime(year, month, 1)
    # Format: "April 2026"
    bulan_id = {
        1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
        5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
        9: "September", 10: "Oktober", 11: "November", 12: "Desember"
    }
    return f"{bulan_id[month]} {year}"


class ReportGenerator:
    def __init__(self, db: Database):
        self.db = db
        self.calc = Calculator(db)
        self.parser = NumberParser()
        self.chart_gen = ChartGenerator(db)

    def format_rupiah(self, amount):
        return self.parser.format_rupiah(amount)

    # ──────────────────────────────────────────────
    # TEXT REPORT (bulan tertentu atau default bulan ini)
    # ──────────────────────────────────────────────

    def generate_text_report(self, user_id, start_date=None, end_date=None) -> str:
        """Generate text report. Default: bulan berjalan."""
        now = datetime.now(TIMEZONE)
        if start_date is None:
            start_date = now.replace(day=1).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = now.strftime("%Y-%m-%d")

        # Ambil label bulan dari start_date
        sd = datetime.strptime(start_date, "%Y-%m-%d")
        label = _month_label(sd.year, sd.month)

        total_income = self.db.get_total_by_type(user_id, 'income', start_date, end_date)
        total_expense = self.db.get_total_by_type(user_id, 'expense', start_date, end_date)
        saldo = total_income - total_expense

        top_cats = self.db.get_spending_by_category(user_id, start_date, end_date)[:5]
        insights = self.calc.generate_insights(user_id)
        recent_income = self.db.get_transactions(user_id, 'income', limit=5,
                                                  start_date=start_date, end_date=end_date)
        recent_expense = self.db.get_transactions(user_id, 'expense', limit=10,
                                                   start_date=start_date, end_date=end_date)
        notes = self.db.get_all_notes(user_id)

        report = f"📊 *LAPORAN KEUANGAN — {label}*\n"
        report += "═══════════════════════\n\n"

        report += "*💰 RINGKASAN*\n"
        report += f"Total Pemasukan: {self.format_rupiah(total_income)}\n"
        report += f"Total Pengeluaran: {self.format_rupiah(total_expense)}\n"
        report += "────────────────\n"
        report += f"*Saldo: {self.format_rupiah(saldo)}*\n\n"

        if top_cats:
            report += f"*📊 TOP PENGELUARAN {label.upper()}*\n"
            for i, cat in enumerate(top_cats, 1):
                pct = (cat['total'] / total_expense * 100) if total_expense > 0 else 0
                report += f"{i}. {cat['category']}: {self.format_rupiah(cat['total'])} ({pct:.1f}%)\n"
            report += "\n"

        if insights:
            report += "*💡 INSIGHTS*\n"
            for insight in insights:
                report += f"• {insight}\n"
            report += "\n"

        if recent_income:
            report += f"*💰 PEMASUKAN TERAKHIR — {label}*\n"
            for trans in recent_income:
                report += f"• {trans['date']}: {self.format_rupiah(trans['amount'])}\n"
                report += f"  {trans['category']} - {trans['description'] or '-'}\n"
            report += "\n"

        if recent_expense:
            report += f"*💸 PENGELUARAN TERAKHIR (10) — {label}*\n"
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

    # ──────────────────────────────────────────────
    # PDF (semua data, dipisah per bulan)
    # ──────────────────────────────────────────────

    def generate_pdf(self, user_id, filename: str = None) -> str:
        if not filename:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'laporan_keuangan_{ts}.pdf'
        filepath = os.path.join(EXPORT_DIR, filename)

        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(
            'Title', parent=styles['Heading1'],
            fontSize=18, textColor=colors.HexColor('#2C3E50'),
            spaceAfter=20, alignment=TA_CENTER
        )
        h2_style = ParagraphStyle(
            'H2', parent=styles['Heading2'],
            fontSize=13, textColor=colors.HexColor('#2C3E50'), spaceAfter=8
        )
        month_style = ParagraphStyle(
            'Month', parent=styles['Heading1'],
            fontSize=15, textColor=colors.white,
            spaceAfter=8, spaceBefore=16, alignment=TA_CENTER
        )

        story.append(Paragraph("LAPORAN KEUANGAN PERSONAL", title_style))
        story.append(Paragraph(
            f"Generated: {datetime.now(TIMEZONE).strftime('%d %B %Y %H:%M')}",
            ParagraphStyle('gen', fontSize=9, textColor=colors.grey, alignment=TA_CENTER)
        ))
        story.append(Spacer(1, 12))

        months = _get_all_months(user_id, self.db)
        if not months:
            story.append(Paragraph("Belum ada data transaksi.", styles['Normal']))
            doc.build(story)
            return filepath

        # ── Overall summary ──
        all_income = self.db.get_total_by_type(user_id, 'income')
        all_expense = self.db.get_total_by_type(user_id, 'expense')
        all_saldo = all_income - all_expense

        story.append(Paragraph("RINGKASAN KESELURUHAN", h2_style))
        overall_data = [
            ['Keterangan', 'Jumlah'],
            ['Total Pemasukan', self.format_rupiah(all_income)],
            ['Total Pengeluaran', self.format_rupiah(all_expense)],
            ['SALDO AKHIR', self.format_rupiah(all_saldo)],
        ]
        ot = Table(overall_data, colWidths=[10*cm, 6*cm])
        ot.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2C3E50')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#3498DB')),
            ('TEXTCOLOR', (0,3), (-1,3), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('TOPPADDING', (0,0), (-1,-1), 7),
            ('BOTTOMPADDING', (0,0), (-1,-1), 7),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(ot)
        story.append(Spacer(1, 16))

        # ── Notes ──
        notes = self.db.get_all_notes(user_id)
        if notes:
            story.append(Paragraph("CATATAN (NOTES)", h2_style))
            notes_data = [['No', 'Catatan']]
            for i, note in enumerate(notes, 1):
                notes_data.append([str(i), note['description']])
            nt = Table(notes_data, colWidths=[1.5*cm, 14.5*cm])
            nt.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F39C12')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING', (0,0), (-1,-1), 8),
                ('BACKGROUND', (0,1), (-1,-1), colors.lightgoldenrodyellow),
            ]))
            story.append(nt)
            story.append(Spacer(1, 12))

        story.append(PageBreak())

        # ── Per bulan ──
        for year, month in months:
            start_date, end_date = _month_range(year, month)
            label = _month_label(year, month)

            inc_transactions = self.db.get_transactions(user_id, 'income',
                                                         start_date=start_date, end_date=end_date)
            exp_transactions = self.db.get_transactions(user_id, 'expense',
                                                         start_date=start_date, end_date=end_date)
            total_inc = self.db.get_total_by_type(user_id, 'income', start_date, end_date)
            total_exp = self.db.get_total_by_type(user_id, 'expense', start_date, end_date)
            saldo = total_inc - total_exp

            # Month header banner
            month_banner_data = [[Paragraph(f"📅  {label.upper()}", month_style)]]
            mb = Table(month_banner_data, colWidths=[16*cm])
            mb.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#2C3E50')),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(mb)
            story.append(Spacer(1, 10))

            # Summary bulan
            sum_data = [
                ['Pemasukan', self.format_rupiah(total_inc)],
                ['Pengeluaran', self.format_rupiah(total_exp)],
                ['Saldo', self.format_rupiah(saldo)],
            ]
            st = Table(sum_data, colWidths=[8*cm, 8*cm])
            st.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#2C3E50')),
                ('GRID', (0,0), (-1,-1), 0.4, colors.lightgrey),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ('LEFTPADDING', (0,0), (-1,-1), 10),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EBF5FB')),
                ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#D6EAF8')),
            ]))
            story.append(st)
            story.append(Spacer(1, 10))

            # Tabel pemasukan bulan ini
            if inc_transactions:
                story.append(Paragraph(f"Pemasukan — {label}", h2_style))
                inc_data = [['Tanggal', 'Kategori', 'Keterangan', 'Jumlah']]
                for t in inc_transactions:
                    inc_data.append([t['date'], t['category'],
                                     t['description'] or '-', self.format_rupiah(t['amount'])])
                inc_data.append(['', '', 'TOTAL', self.format_rupiah(total_inc)])

                it = Table(inc_data, colWidths=[3*cm, 4*cm, 6*cm, 3.5*cm])
                it.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#27AE60')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,-1), 8.5),
                    ('GRID', (0,0), (-1,-1), 0.4, colors.grey),
                    ('TOPPADDING', (0,0), (-1,-1), 5),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                    ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ('BACKGROUND', (0,1), (-1,-2), colors.HexColor('#E8F8F5')),
                    ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#D5F4E6')),
                    ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
                ]))
                story.append(it)
                story.append(Spacer(1, 8))

            # Tabel pengeluaran bulan ini
            if exp_transactions:
                story.append(Paragraph(f"Pengeluaran — {label}", h2_style))
                exp_data = [['Tanggal', 'Kategori', 'Keterangan', 'Jumlah']]
                for t in exp_transactions:
                    exp_data.append([t['date'], t['category'],
                                     t['description'] or '-', self.format_rupiah(t['amount'])])
                exp_data.append(['', '', 'TOTAL', self.format_rupiah(total_exp)])

                et = Table(exp_data, colWidths=[3*cm, 4*cm, 6*cm, 3.5*cm])
                et.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E74C3C')),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,-1), 8.5),
                    ('GRID', (0,0), (-1,-1), 0.4, colors.grey),
                    ('TOPPADDING', (0,0), (-1,-1), 5),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                    ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ('BACKGROUND', (0,1), (-1,-2), colors.HexColor('#FDEDEC')),
                    ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FADBD8')),
                    ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
                ]))
                story.append(et)
                story.append(Spacer(1, 8))

            story.append(PageBreak())

        doc.build(story)
        return filepath

    # ──────────────────────────────────────────────
    # EXCEL (semua data, sheet per bulan)
    # ──────────────────────────────────────────────

    def generate_excel(self, user_id, filename: str = None) -> str:
        if not filename:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'laporan_keuangan_{ts}.xlsx'
        filepath = os.path.join(EXPORT_DIR, filename)

        wb = openpyxl.Workbook()
        wb.remove(wb.active)

        months = _get_all_months(user_id, self.db)

        # ── Sheet Ringkasan Keseluruhan ──
        self._create_overall_sheet(wb, user_id)

        # ── Sheet per bulan ──
        for year, month in months:
            start_date, end_date = _month_range(year, month)
            label = _month_label(year, month)
            self._create_month_sheet(wb, user_id, year, month,
                                     start_date, end_date, label)

        # ── Sheet Notes ──
        self._create_notes_sheet(wb, user_id)

        wb.save(filepath)
        return filepath

    def _create_overall_sheet(self, wb, user_id):
        ws = wb.create_sheet('Ringkasan Keseluruhan')

        ws['A1'] = 'RINGKASAN KESELURUHAN'
        ws['A1'].font = Font(size=14, bold=True)
        ws.merge_cells('A1:B1')

        all_income = self.db.get_total_by_type(user_id, 'income')
        all_expense = self.db.get_total_by_type(user_id, 'expense')
        all_saldo = all_income - all_expense

        months = _get_all_months(user_id, self.db)

        # Header tabel per bulan
        headers = ['Bulan', 'Pemasukan', 'Pengeluaran', 'Saldo']
        for col, h in enumerate(headers, 1):
            c = ws.cell(3, col, h)
            c.fill = PatternFill(start_color='2C3E50', end_color='2C3E50', fill_type='solid')
            c.font = Font(color='FFFFFF', bold=True)
            c.alignment = Alignment(horizontal='center')

        row = 4
        for year, month in months:
            start_date, end_date = _month_range(year, month)
            label = _month_label(year, month)
            inc = self.db.get_total_by_type(user_id, 'income', start_date, end_date)
            exp = self.db.get_total_by_type(user_id, 'expense', start_date, end_date)
            sal = inc - exp
            ws.cell(row, 1, label)
            ws.cell(row, 2, inc).number_format = '#,##0'
            ws.cell(row, 3, exp).number_format = '#,##0'
            ws.cell(row, 4, sal).number_format = '#,##0'
            row += 1

        # Total row
        ws.cell(row, 1, 'TOTAL').font = Font(bold=True)
        for col, val in [(2, all_income), (3, all_expense), (4, all_saldo)]:
            c = ws.cell(row, col, val)
            c.number_format = '#,##0'
            c.font = Font(bold=True)
            c.fill = PatternFill(start_color='3498DB', end_color='3498DB', fill_type='solid')
            c.font = Font(color='FFFFFF', bold=True)

        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 18
        ws.column_dimensions['C'].width = 18
        ws.column_dimensions['D'].width = 18

    def _create_month_sheet(self, wb, user_id, year, month,
                             start_date, end_date, label):
        # Sheet name max 31 chars
        sheet_name = label[:31]
        ws = wb.create_sheet(sheet_name)

        inc_transactions = self.db.get_transactions(user_id, 'income',
                                                     start_date=start_date, end_date=end_date)
        exp_transactions = self.db.get_transactions(user_id, 'expense',
                                                     start_date=start_date, end_date=end_date)
        total_inc = self.db.get_total_by_type(user_id, 'income', start_date, end_date)
        total_exp = self.db.get_total_by_type(user_id, 'expense', start_date, end_date)

        current_row = 1

        # Title
        ws.cell(current_row, 1, f'LAPORAN {label.upper()}')
        ws.cell(current_row, 1).font = Font(size=13, bold=True)
        ws.merge_cells(f'A{current_row}:D{current_row}')
        current_row += 2

        # Summary
        for label_txt, val in [
            ('Total Pemasukan', total_inc),
            ('Total Pengeluaran', total_exp),
            ('Saldo', total_inc - total_exp)
        ]:
            ws.cell(current_row, 1, label_txt).font = Font(bold=True)
            c = ws.cell(current_row, 2, val)
            c.number_format = '#,##0'
            current_row += 1
        current_row += 1

        # Pemasukan
        ws.cell(current_row, 1, 'PEMASUKAN')
        ws.cell(current_row, 1).font = Font(size=11, bold=True)
        ws.merge_cells(f'A{current_row}:D{current_row}')
        current_row += 1

        headers = ['Tanggal', 'Kategori', 'Keterangan', 'Jumlah']
        for col, h in enumerate(headers, 1):
            c = ws.cell(current_row, col, h)
            c.fill = PatternFill(start_color='27AE60', end_color='27AE60', fill_type='solid')
            c.font = Font(color='FFFFFF', bold=True)
            c.alignment = Alignment(horizontal='center')
        current_row += 1

        for t in inc_transactions:
            ws.cell(current_row, 1, t['date'])
            ws.cell(current_row, 2, t['category'])
            ws.cell(current_row, 3, t['description'] or '-')
            ws.cell(current_row, 4, t['amount']).number_format = '#,##0'
            current_row += 1

        ws.cell(current_row, 3, 'TOTAL').font = Font(bold=True)
        c = ws.cell(current_row, 4, total_inc)
        c.number_format = '#,##0'
        c.font = Font(bold=True)
        c.fill = PatternFill(start_color='D5F4E6', end_color='D5F4E6', fill_type='solid')
        current_row += 2

        # Pengeluaran
        ws.cell(current_row, 1, 'PENGELUARAN')
        ws.cell(current_row, 1).font = Font(size=11, bold=True)
        ws.merge_cells(f'A{current_row}:D{current_row}')
        current_row += 1

        for col, h in enumerate(headers, 1):
            c = ws.cell(current_row, col, h)
            c.fill = PatternFill(start_color='E74C3C', end_color='E74C3C', fill_type='solid')
            c.font = Font(color='FFFFFF', bold=True)
            c.alignment = Alignment(horizontal='center')
        current_row += 1

        for t in exp_transactions:
            ws.cell(current_row, 1, t['date'])
            ws.cell(current_row, 2, t['category'])
            ws.cell(current_row, 3, t['description'] or '-')
            ws.cell(current_row, 4, t['amount']).number_format = '#,##0'
            current_row += 1

        ws.cell(current_row, 3, 'TOTAL').font = Font(bold=True)
        c = ws.cell(current_row, 4, total_exp)
        c.number_format = '#,##0'
        c.font = Font(bold=True)
        c.fill = PatternFill(start_color='FADBD8', end_color='FADBD8', fill_type='solid')

        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 35
        ws.column_dimensions['D'].width = 15

    def _create_notes_sheet(self, wb, user_id):
        ws = wb.create_sheet('Catatan')
        ws['A1'] = 'DAFTAR CATATAN'
        ws['A1'].font = Font(size=13, bold=True)
        ws.merge_cells('A1:B1')

        for col, h in enumerate(['No', 'Catatan'], 1):
            c = ws.cell(3, col, h)
            c.fill = PatternFill(start_color='F39C12', end_color='F39C12', fill_type='solid')
            c.font = Font(color='FFFFFF', bold=True)

        notes = self.db.get_all_notes(user_id)
        for row, note in enumerate(notes, 4):
            ws.cell(row, 1, row - 3)
            ws.cell(row, 2, note['description'])

        ws.column_dimensions['A'].width = 6
        ws.column_dimensions['B'].width = 60
