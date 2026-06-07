"""
Exporta datos de APP MIO a PDF.

Uso:
  1. En la app: Configuracion > Exportar datos (JSON)
  2. pip install reportlab
  3. python exportar_pdf.py APP_MIO_datos_2025-01-01.json
"""
import json
import sys
from datetime import datetime

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)

PRIMARY = colors.HexColor('#6366F1')
LIGHT   = colors.HexColor('#F0F0FF')
DARK    = colors.HexColor('#1E1B4B')
GREY    = colors.HexColor('#64748B')

def fmt_date(iso):
    if not iso:
        return ''
    try:
        return datetime.fromisoformat(iso[:10]).strftime('%d/%m/%Y')
    except Exception:
        return iso[:10]

def fmt_money(n):
    try:
        return f'${float(n):,.2f}'
    except Exception:
        return str(n)

def build_table(head, rows, col_widths=None):
    data = [head] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, 0),  PRIMARY),
        ('TEXTCOLOR',    (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',     (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',     (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, LIGHT]),
        ('GRID',         (0, 0), (-1, -1), 0.4, colors.HexColor('#E2E8F0')),
        ('ALIGN',        (0, 0), (-1, 0),  'CENTER'),
        ('ALIGN',        (0, 1), (-1, -1), 'LEFT'),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING',      (0, 0), (-1, -1), 5),
        ('TOPPADDING',   (0, 0), (-1, 0),  7),
        ('BOTTOMPADDING',(0, 0), (-1, 0),  7),
        ('WORDWRAP',     (0, 0), (-1, -1), True),
    ]))
    return t

def main():
    json_file = sys.argv[1] if len(sys.argv) > 1 else 'datos.json'
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f'Error: no se encontro el archivo "{json_file}"')
        print('Uso: python exportar_pdf.py APP_MIO_datos.json')
        sys.exit(1)

    people   = data.get('people', [])
    payrolls = data.get('payrolls', [])
    p_map    = {p['id']: p for p in people}

    out = f'APP_MIO_reporte_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    doc = SimpleDocTemplate(
        out,
        pagesize=landscape(A4),
        topMargin=1.5*cm, bottomMargin=1.5*cm,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
    )

    styles = getSampleStyleSheet()
    title_s   = ParagraphStyle('T', fontSize=20, textColor=PRIMARY, fontName='Helvetica-Bold', spaceAfter=2)
    sub_s     = ParagraphStyle('S', fontSize=9,  textColor=GREY,    spaceAfter=4)
    section_s = ParagraphStyle('H', fontSize=12, textColor=PRIMARY, fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6)

    elems = []
    elems.append(Paragraph('APP MIO — Reporte de Datos', title_s))
    elems.append(Paragraph(
        f'Generado el {datetime.now().strftime("%d/%m/%Y a las %H:%M")}  ·  '
        f'{len(people)} personas  ·  {len(payrolls)} nominas',
        sub_s))
    elems.append(HRFlowable(width='100%', thickness=1, color=PRIMARY, spaceAfter=10))

    # ── Tabla personas ───────────────────────────────────────
    elems.append(Paragraph('Personas', section_s))
    p_head = [['Nombre', 'DNI', 'Pasaporte', 'IBAN / Cuenta', 'Wallets', 'Registrado']]
    p_rows = []
    for p in people:
        banks  = p.get('bankAccounts', [])
        wallets = p.get('wallets', [])
        bank_s = '\n'.join(filter(None, [b.get('iban') or b.get('accountNumber') or b.get('bankName','') for b in banks])) or '—'
        wal_s  = '\n'.join(f"{w.get('network','')} {w.get('address','')}".strip() for w in wallets) or '—'
        p_rows.append([p.get('fullName',''), p.get('dni','—'), p.get('passport','—'), bank_s, wal_s, fmt_date(p.get('createdAt',''))])

    page_w = landscape(A4)[0] - 3*cm
    elems.append(build_table(p_head, p_rows, [page_w*0.22, page_w*0.10, page_w*0.10, page_w*0.22, page_w*0.26, page_w*0.10]))

    # ── Tabla nominas ─────────────────────────────────────────
    if payrolls:
        elems.append(Paragraph('Historial de Nominas', section_s))
        n_head = [['Persona', 'DNI', 'Monto', 'Fecha vigencia', 'Notas']]
        n_rows = []
        for pay in sorted(payrolls, key=lambda x: x.get('effectiveDate',''), reverse=True):
            p = p_map.get(pay.get('personId'), {})
            n_rows.append([
                p.get('fullName', '(eliminada)'),
                p.get('dni', ''),
                fmt_money(pay.get('amount', 0)),
                pay.get('effectiveDate', ''),
                pay.get('notes', ''),
            ])
        elems.append(build_table(n_head, n_rows, [page_w*0.28, page_w*0.12, page_w*0.12, page_w*0.14, page_w*0.34]))

    doc.build(elems)
    print(f'PDF generado: {out}')
    print(f'  {len(people)} personas  |  {len(payrolls)} nominas')

if __name__ == '__main__':
    main()
