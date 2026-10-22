"""Deterministic PDF rendering: persisted supplier invoice values only, no LLM."""
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether


def idr(value):
    # Preserve any quote precision beyond two decimals: independently rounding
    # line, shipping and tax could make the displayed invoice fail to add up.
    number = Decimal(str(value))
    fraction = format(number, 'f').partition('.')[2].rstrip('0')
    formatted = format(number, f',.{max(2,len(fraction))}f')
    return 'Rp ' + formatted.replace(',', '_').replace('.', ',').replace('_', '.')


def date_text(value):
    return datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(
        ZoneInfo('Asia/Jakarta')).strftime('%d/%m/%Y %H:%M WIB')


def render_pdf(order):
    out = BytesIO()
    ink, muted, navy, pale = map(colors.HexColor, ['#152033', '#56647A', '#17324D', '#EDF3F8'])
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='POBody', fontName='Helvetica', fontSize=9, leading=13,
                              textColor=ink, spaceAfter=3, splitLongWords=True))
    styles.add(ParagraphStyle(name='POMuted', parent=styles['POBody'], textColor=muted, fontSize=8, leading=11))
    styles.add(ParagraphStyle(name='POLabel', parent=styles['POBody'], fontName='Helvetica-Bold',
                              textColor=navy, fontSize=9, spaceAfter=7))
    styles.add(ParagraphStyle(name='PORight', parent=styles['POBody'], alignment=TA_RIGHT))

    def p(text, style='POBody'):
        return Paragraph(escape(str(text)), styles[style])

    def box(title, lines):
        return [p(title, 'POLabel'), *[p(line) for line in lines]]

    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=17*mm, bottomMargin=21*mm, title=order['number'],
                            author='PT PartPilot - Demo', subject='Purchase order simulasi')
    width = A4[0]-36*mm
    issuer, supplier, shipping = order['issuer'], order['supplier'], order['ship_to']
    story = [Paragraph('PT PartPilot', ParagraphStyle('Brand', fontName='Helvetica-Bold',
                       fontSize=23, leading=28, textColor=navy)),
             p('PURCHASE ORDER / PESANAN PEMBELIAN', 'POLabel'),
             p(issuer['address'], 'POMuted'),
             p(issuer['email']+' | '+issuer['phone'], 'POMuted'), Spacer(1, 5*mm)]
    banner = Table([[p('DOKUMEN DEMO - DATA KONTAK & ALAMAT DUMMY', 'POLabel')]], colWidths=[width])
    banner.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),pale),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#C9D6E3')),
                               ('LEFTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),9)]))
    story.extend([banner, Spacer(1, 5*mm)])
    details = Table([[box('PEMASOK', [supplier['name'], 'Kode: '+supplier['id'], supplier['address']]),
                      box('INFORMASI PO', ['Nomor: '+order['number'], 'Tanggal: '+date_text(order['created_at']),
                           'Mata uang: IDR', 'Status: Dibuat dari pilihan manajer'])],
                     [box('KIRIM KE', [shipping['name'], shipping['warehouse_id'], shipping['address']]),
                      box('REFERENSI PENAWARAN', ['ID: '+str(order.get('quote_id') or '-'),
                           'Revisi: '+str(order.get('quote_revision') or '-'),
                           'Estimasi tiba: '+date_text(order['delivered_eta'])])]], colWidths=[width*.50,width*.50])
    details.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),
                                ('RIGHTPADDING',(0,0),(-1,-1),14),('BOTTOMPADDING',(0,0),(-1,-1),13)]))
    story.extend([details, Spacer(1, 2*mm)])
    identity = order['identity']
    item = 'Bearing '+str(identity['brand'])+' '+str(identity['base'])+str(identity['suffix'])
    rows = [[p('No.'),p('Deskripsi barang'),p('Qty'),p('Satuan'),p('Harga satuan'),p('Jumlah')],
            [p('1'),p(item),p(order['quantity'],'PORight'),p(order['quantity_unit']),
             p(idr(order['unit_price']),'PORight'),p(idr(order['line_subtotal']),'PORight')]]
    table = Table(rows, colWidths=[width*x for x in [.055,.305,.065,.085,.24,.25]], repeatRows=1)
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),pale),('LINEBELOW',(0,0),(-1,0),.8,navy),
        ('LINEBELOW',(0,1),(-1,-1),.5,colors.HexColor('#D3DCE6')),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
    story.extend([table, Spacer(1, 4*mm)])
    totals = Table([[p(label),p(idr(order[key]),'PORight')] for label,key in [
        ('Subtotal barang','line_subtotal'),('Biaya pengiriman','shipping_amount'),
        ('Pajak sesuai penawaran','tax_amount'),('TOTAL PESANAN','total')]], colWidths=[width*.37,width*.30],hAlign='RIGHT')
    totals.setStyle(TableStyle([('BACKGROUND',(0,3),(-1,3),pale),('LINEABOVE',(0,3),(-1,3),.8,navy),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    story.extend([totals, Spacer(1, 7*mm), p('SYARAT & CATATAN', 'POLabel')])
    story.extend(p(f'{index}. {term}','POMuted') for index,term in enumerate(order['terms'],1))
    signoff = Table([[box('DISETUJUI DALAM DEMO', ['Pilihan manajer tercatat',date_text(order['approval']['approved_at'])]),
                      box('KONFIRMASI PEMASOK', ['Belum dikirim kepada pemasok','Tanda tangan: __________________'])]], colWidths=[width*.50,width*.50])
    signoff.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),
                                ('TOPPADDING',(0,0),(-1,-1),12)]))
    story.append(KeepTogether([Spacer(1,4*mm),signoff]))

    def footer(canvas, document):
        canvas.setStrokeColor(colors.HexColor('#D3DCE6'))
        canvas.line(18*mm,17*mm,A4[0]-18*mm,17*mm)
        canvas.setFillColor(muted);canvas.setFont('Helvetica',7)
        canvas.drawString(18*mm,12*mm,'PT PartPilot | Dokumen simulasi, bukan pesanan nyata')
        canvas.drawRightString(A4[0]-18*mm,12*mm,f'Halaman {document.page}')

    def stable_canvas(*args, **kwargs):
        return Canvas(*args, **dict(kwargs, invariant=1))

    doc.build(story,onFirstPage=footer,onLaterPages=footer,canvasmaker=stable_canvas)
    return out.getvalue()
