"""
FUNDAAZ – pdf_report.py
Generates beautiful PDF reports for student test history.
Uses ReportLab Platypus for layout.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics import renderPDF

# ── Brand colours ──
G1  = colors.HexColor('#0a3d1f')
G2  = colors.HexColor('#1a6b3a')
G3  = colors.HexColor('#2a9d5c')
G4  = colors.HexColor('#4ade80')
G5  = colors.HexColor('#bbf7d0')
G6  = colors.HexColor('#f0fdf4')
RED = colors.HexColor('#dc2626')
AMB = colors.HexColor('#d97706')
GRN = colors.HexColor('#16a34a')
GRY = colors.HexColor('#64748b')
WHT = colors.white
BLK = colors.HexColor('#0f172a')
LGT = colors.HexColor('#f8fafc')
BRD = colors.HexColor('#e2e8f0')

PAGE_W, PAGE_H = A4
MARGIN = 2 * cm

def pct_colour(p):
    if p >= 75: return GRN
    if p >= 50: return AMB
    return RED

def grade(p):
    if p >= 90: return 'A+'
    if p >= 80: return 'A'
    if p >= 70: return 'B'
    if p >= 60: return 'C'
    if p >= 50: return 'D'
    return 'F'

# ── Styles ──
def make_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles['title'] = ParagraphStyle(
        'Title', fontName='Helvetica-Bold',
        fontSize=22, textColor=G1,
        spaceAfter=4, spaceBefore=0, leading=26
    )
    styles['subtitle'] = ParagraphStyle(
        'Subtitle', fontName='Helvetica',
        fontSize=11, textColor=GRY,
        spaceAfter=2, leading=14
    )
    styles['section'] = ParagraphStyle(
        'Section', fontName='Helvetica-Bold',
        fontSize=13, textColor=G1,
        spaceBefore=16, spaceAfter=8, leading=16,
        borderPad=4,
    )
    styles['body'] = ParagraphStyle(
        'Body', fontName='Helvetica',
        fontSize=9, textColor=BLK,
        leading=13, spaceAfter=2
    )
    styles['small'] = ParagraphStyle(
        'Small', fontName='Helvetica',
        fontSize=8, textColor=GRY, leading=11
    )
    styles['bold_small'] = ParagraphStyle(
        'BoldSmall', fontName='Helvetica-Bold',
        fontSize=8, textColor=BLK, leading=11
    )
    styles['center'] = ParagraphStyle(
        'Center', fontName='Helvetica',
        fontSize=9, textColor=BLK,
        alignment=TA_CENTER, leading=13
    )
    styles['label'] = ParagraphStyle(
        'Label', fontName='Helvetica',
        fontSize=7.5, textColor=GRY,
        leading=10, spaceAfter=1
    )
    styles['value'] = ParagraphStyle(
        'Value', fontName='Helvetica-Bold',
        fontSize=9.5, textColor=BLK,
        leading=12
    )
    return styles


def _header_footer(canvas, doc, student, date_range_label):
    """Draws header and footer on every page."""
    canvas.saveState()
    W = PAGE_W

    # ── Header bar ──
    canvas.setFillColor(G1)
    canvas.rect(0, PAGE_H - 1.4*cm, W, 1.4*cm, fill=1, stroke=0)
    canvas.setFillColor(G4)
    canvas.setFont('Helvetica-BoldOblique', 14)
    canvas.drawString(MARGIN, PAGE_H - 0.95*cm, 'FUNDAAZ')
    canvas.setFillColor(WHT)
    canvas.setFont('Helvetica', 9)
    canvas.drawString(MARGIN + 2.4*cm, PAGE_H - 0.95*cm, '– Academic Performance Report')
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(W - MARGIN, PAGE_H - 0.95*cm,
                           f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")

    # ── Footer ──
    canvas.setFillColor(G6)
    canvas.rect(0, 0, W, 1.1*cm, fill=1, stroke=0)
    canvas.setStrokeColor(G3)
    canvas.setLineWidth(1)
    canvas.line(MARGIN, 1.1*cm, W - MARGIN, 1.1*cm)
    canvas.setFillColor(GRY)
    canvas.setFont('Helvetica', 8)
    canvas.drawString(MARGIN, 0.42*cm, f"Student: {student['name']}  |  {date_range_label}")
    canvas.drawRightString(W - MARGIN, 0.42*cm,
                           f"Page {doc.page}")
    canvas.restoreState()


def _summary_table(student, results, styles):
    """4-cell summary stat boxes at top."""
    if not results:
        return []
    pcts = [round(r['marks'] / r['total_marks'] * 100, 1) for r in results]
    avg  = round(sum(pcts) / len(pcts), 1)
    best = max(pcts)
    worst= min(pcts)
    total= len(pcts)

    def stat_cell(label, value, colour):
        return [
            Paragraph(f'<b>{value}</b>',
                      ParagraphStyle('sv', fontName='Helvetica-Bold', fontSize=20,
                                     textColor=colour, alignment=TA_CENTER, leading=22)),
            Paragraph(label, ParagraphStyle('sl', fontName='Helvetica', fontSize=8,
                                            textColor=GRY, alignment=TA_CENTER, leading=11))
        ]

    data = [[
        stat_cell('Average Score', f'{avg}%', pct_colour(avg)),
        stat_cell('Best Score',    f'{best}%', GRN),
        stat_cell('Lowest Score',  f'{worst}%', RED),
        stat_cell('Tests Taken',   str(total), G2),
    ]]

    t = Table(data, colWidths=[(PAGE_W - 2*MARGIN)/4]*4)
    t.setStyle(TableStyle([
        ('BOX',        (0,0), (-1,-1), 0.5, BRD),
        ('INNERGRID',  (0,0), (-1,-1), 0.5, BRD),
        ('BACKGROUND', (0,0), (-1,-1), G6),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('ROUNDEDCORNERS', [6]),
    ]))
    return [t, Spacer(1, 14)]


def _results_table(results, styles):
    """Full test history table."""
    header = ['Date', 'Test Code', 'Subject', 'Chapter', 'Topic', 'Marks', 'Total', '%', 'Grade']
    rows = [header]
    for r in results:
        pct = round(r['marks'] / r['total_marks'] * 100, 1)
        rows.append([
            r['date'],
            r['code'],
            r['subject'],
            r['chapter'] or '—',
            r['topic']   or '—',
            str(r['marks']),
            str(r['total_marks']),
            f"{pct}%",
            grade(pct),
        ])

    col_w = [2.0*cm, 2.2*cm, 2.8*cm, 3.0*cm, 3.2*cm, 1.4*cm, 1.4*cm, 1.4*cm, 1.4*cm]
    t = Table(rows, colWidths=col_w, repeatRows=1)

    style = [
        # Header
        ('BACKGROUND',   (0,0), (-1,0), G1),
        ('TEXTCOLOR',    (0,0), (-1,0), WHT),
        ('FONTNAME',     (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',     (0,0), (-1,0), 7.5),
        ('TOPPADDING',   (0,0), (-1,0), 6),
        ('BOTTOMPADDING',(0,0), (-1,0), 6),
        # Data rows
        ('FONTNAME',     (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE',     (0,1), (-1,-1), 7.5),
        ('TOPPADDING',   (0,1), (-1,-1), 5),
        ('BOTTOMPADDING',(0,1), (-1,-1), 5),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [WHT, G6]),
        ('GRID',         (0,0), (-1,-1), 0.3, BRD),
        ('ALIGN',        (5,0), (-1,-1), 'CENTER'),
    ]
    # Colour the % column per row
    for i, r in enumerate(results, start=1):
        pct = round(r['marks'] / r['total_marks'] * 100, 1)
        c = pct_colour(pct)
        style.append(('TEXTCOLOR', (7,i), (7,i), c))
        style.append(('FONTNAME',  (7,i), (7,i), 'Helvetica-Bold'))
        # Grade colour
        g_colour = GRN if pct >= 70 else AMB if pct >= 50 else RED
        style.append(('TEXTCOLOR', (8,i), (8,i), g_colour))
        style.append(('FONTNAME',  (8,i), (8,i), 'Helvetica-Bold'))

    t.setStyle(TableStyle(style))
    return [
        Paragraph('Test History', styles['section']),
        t,
        Spacer(1, 14)
    ]


def _subject_table(results, styles):
    """Subject-wise aggregated performance table."""
    subj = {}
    for r in results:
        s = r['subject']
        if s not in subj:
            subj[s] = {'marks': 0, 'total': 0, 'count': 0}
        subj[s]['marks'] += r['marks']
        subj[s]['total'] += r['total_marks']
        subj[s]['count'] += 1

    if not subj:
        return []

    header = ['Subject', 'Tests', 'Total Marks', 'Obtained', 'Average %', 'Grade']
    rows = [header]
    for s, v in sorted(subj.items()):
        pct = round(v['marks'] / v['total'] * 100, 1)
        rows.append([s, str(v['count']), str(v['total']),
                     str(v['marks']), f"{pct}%", grade(pct)])

    col_w = [4*cm, 2*cm, 3*cm, 2.5*cm, 3*cm, 2.3*cm]
    t = Table(rows, colWidths=col_w, repeatRows=1)
    style = [
        ('BACKGROUND',   (0,0), (-1,0), G2),
        ('TEXTCOLOR',    (0,0), (-1,0), WHT),
        ('FONTNAME',     (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',     (0,0), (-1,-1), 8),
        ('TOPPADDING',   (0,0), (-1,-1), 6),
        ('BOTTOMPADDING',(0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [WHT, G6]),
        ('GRID',         (0,0), (-1,-1), 0.3, BRD),
        ('ALIGN',        (1,0), (-1,-1), 'CENTER'),
    ]
    for i, (s, v) in enumerate(sorted(subj.items()), start=1):
        pct = round(v['marks'] / v['total'] * 100, 1)
        style.append(('TEXTCOLOR', (4,i), (4,i), pct_colour(pct)))
        style.append(('FONTNAME',  (4,i), (4,i), 'Helvetica-Bold'))
    t.setStyle(TableStyle(style))

    return [
        Paragraph('Subject-wise Performance', styles['section']),
        t,
        Spacer(1, 14)
    ]


def _chapter_topic_table(results, styles):
    """Chapter and topic breakdown — only included if any test has chapter/topic."""
    has_ct = any(r['chapter'] or r['topic'] for r in results)
    if not has_ct:
        return []

    # Aggregate by chapter
    chapters = {}
    for r in results:
        ch = r['chapter'] or 'Uncategorised'
        tp = r['topic']   or 'General'
        key = (ch, tp)
        if key not in chapters:
            chapters[key] = {'marks': 0, 'total': 0, 'count': 0, 'subject': r['subject']}
        chapters[key]['marks'] += r['marks']
        chapters[key]['total'] += r['total_marks']
        chapters[key]['count'] += 1

    header = ['Chapter', 'Topic', 'Subject', 'Tests', 'Obtained', 'Max', '%', 'Strength']
    rows = [header]

    for (ch, tp), v in sorted(chapters.items()):
        pct = round(v['marks'] / v['total'] * 100, 1)
        strength = ('Strong ✓' if pct >= 75 else
                    'Average ~' if pct >= 50 else
                    'Needs Work ✗')
        rows.append([ch, tp, v['subject'], str(v['count']),
                     str(v['marks']), str(v['total']), f"{pct}%", strength])

    col_w = [3.2*cm, 3.2*cm, 2.5*cm, 1.4*cm, 1.8*cm, 1.4*cm, 1.5*cm, 2.3*cm]
    t = Table(rows, colWidths=col_w, repeatRows=1)
    style = [
        ('BACKGROUND',   (0,0), (-1,0), G1),
        ('TEXTCOLOR',    (0,0), (-1,0), WHT),
        ('FONTNAME',     (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',     (0,0), (-1,-1), 7.5),
        ('TOPPADDING',   (0,0), (-1,-1), 5),
        ('BOTTOMPADDING',(0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [WHT, G6]),
        ('GRID',         (0,0), (-1,-1), 0.3, BRD),
        ('ALIGN',        (3,0), (-1,-1), 'CENTER'),
    ]
    for i, ((ch, tp), v) in enumerate(sorted(chapters.items()), start=1):
        pct = round(v['marks'] / v['total'] * 100, 1)
        style.append(('TEXTCOLOR', (6,i), (6,i), pct_colour(pct)))
        style.append(('FONTNAME',  (6,i), (6,i), 'Helvetica-Bold'))
        strength_col = GRN if pct >= 75 else AMB if pct >= 50 else RED
        style.append(('TEXTCOLOR', (7,i), (7,i), strength_col))
        style.append(('FONTNAME',  (7,i), (7,i), 'Helvetica-Bold'))
    t.setStyle(TableStyle(style))

    return [
        Paragraph('Chapter &amp; Topic Analysis', styles['section']),
        t,
        Spacer(1, 14)
    ]


def _bar_chart(results, styles):
    """Subject-wise bar chart using ReportLab graphics."""
    subj = {}
    for r in results:
        s = r['subject']
        if s not in subj:
            subj[s] = {'marks': 0, 'total': 0}
        subj[s]['marks'] += r['marks']
        subj[s]['total'] += r['total_marks']

    if len(subj) < 1:
        return []

    labels = list(subj.keys())
    values = [round(v['marks'] / v['total'] * 100, 1) for v in subj.values()]

    chart_w = PAGE_W - 2*MARGIN
    chart_h = 5.5*cm
    d = Drawing(chart_w, chart_h + 1.2*cm)

    bc = VerticalBarChart()
    bc.x      = 1.5*cm
    bc.y      = 1.0*cm
    bc.width  = chart_w - 2.5*cm
    bc.height = chart_h - 0.5*cm
    bc.data   = [values]
    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontSize  = 8
    bc.categoryAxis.labels.fontName  = 'Helvetica'
    bc.categoryAxis.labels.textAnchor = 'middle'
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 100
    bc.valueAxis.valueStep = 25
    bc.valueAxis.labels.fontSize = 8
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.bars[0].fillColor = G2
    bc.bars[0].strokeColor = G1
    bc.bars[0].strokeWidth = 0.5
    bc.groupSpacing = 8

    d.add(bc)
    return [
        Paragraph('Subject Performance Chart', styles['section']),
        d,
        Spacer(1, 14)
    ]


def _profile_block(student, date_range_label, styles):
    """Student profile info block."""
    info = [
        ['Student Name',  student['name'],    'Login ID',    student['login_id']],
        ['Class',         student['class'],   'Batch',       student['batch']],
        ['Parent/Guardian', student['parent_name'] or '—', 'Contact', student['parent_contact'] or '—'],
        ['Report Period', date_range_label,   'Generated',   datetime.now().strftime('%d %b %Y')],
    ]

    rows = []
    for row in info:
        rows.append([
            Paragraph(row[0], ParagraphStyle('lbl', fontName='Helvetica', fontSize=8, textColor=GRY)),
            Paragraph(str(row[1]), ParagraphStyle('val', fontName='Helvetica-Bold', fontSize=9, textColor=BLK)),
            Paragraph(row[2], ParagraphStyle('lbl', fontName='Helvetica', fontSize=8, textColor=GRY)),
            Paragraph(str(row[3]), ParagraphStyle('val', fontName='Helvetica-Bold', fontSize=9, textColor=BLK)),
        ])

    col_w = [3.5*cm, 5.5*cm, 3.5*cm, 5.5*cm]
    t = Table(rows, colWidths=col_w)
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,-1), G6),
        ('BOX',          (0,0), (-1,-1), 0.5, G3),
        ('INNERGRID',    (0,0), (-1,-1), 0.3, BRD),
        ('TOPPADDING',   (0,0), (-1,-1), 6),
        ('BOTTOMPADDING',(0,0), (-1,-1), 6),
        ('LEFTPADDING',  (0,0), (-1,-1), 8),
    ]))
    return [t, Spacer(1, 14)]


def generate_pdf(student, results, date_range_label='All Time'):
    """
    Main entry point.
    student  : sqlite3.Row or dict with keys: name, login_id, class, batch, parent_name, parent_contact
    results  : list of sqlite3.Row with: marks, total_marks, code, subject, date, chapter, topic
    Returns  : bytes (PDF content)
    """
    buf    = io.BytesIO()
    styles = make_styles()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2.0*cm, bottomMargin=1.8*cm,
        title=f"FUNDAAZ – {student['name']} Report",
        author='FUNDAAZ System',
    )

    def _hf(canvas, doc):
        _header_footer(canvas, doc, student, date_range_label)

    story = []

    # ── Title block ──
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Academic Performance Report", styles['title']))
    story.append(Paragraph(f"Period: {date_range_label}", styles['subtitle']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=G3, spaceAfter=10))

    # ── Profile ──
    story += _profile_block(student, date_range_label, styles)

    if not results:
        story.append(Paragraph('No test results found for the selected period.',
                                styles['body']))
        doc.build(story, onFirstPage=_hf, onLaterPages=_hf)
        return buf.getvalue()

    # ── Summary stats ──
    story += _summary_table(student, results, styles)

    # ── Subject bar chart ──
    story += _bar_chart(results, styles)

    # ── Subject table ──
    story += _subject_table(results, styles)

    # ── Chapter/Topic analysis (only if data exists) ──
    story += _chapter_topic_table(results, styles)

    # ── Full test history ──
    story += _results_table(results, styles)

    doc.build(story, onFirstPage=_hf, onLaterPages=_hf)
    return buf.getvalue()
