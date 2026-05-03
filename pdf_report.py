"""
FUNDAAZ – pdf_report.py  (v2 — wrapping fix)
All table cells use Paragraph objects so long text wraps inside cells.
Column widths recalculated to fit A4 page width exactly.
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
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart

# ── Brand colours ──────────────────────────────────────────────────
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
MARGIN     = 1.8 * cm
CONTENT_W  = PAGE_W - 2 * MARGIN   # usable width = 17.4 cm on A4


def pct_colour(p):
    if p >= 75: return GRN
    if p >= 50: return AMB
    return RED


def grade(p):
    if p >= 90: return 'A+'
    if p >= 80: return 'A'
    if p >= 70: return 'B+'
    if p >= 60: return 'B'
    if p >= 50: return 'C'
    if p >= 40: return 'D'    
    return 'F'


# ── Shared cell paragraph styles ───────────────────────────────────
def _cell_style(bold=False, size=8, colour=BLK, align=TA_LEFT):
    return ParagraphStyle(
        'cell',
        fontName='Helvetica-Bold' if bold else 'Helvetica',
        fontSize=size,
        textColor=colour,
        leading=size * 1.35,
        alignment=align,
        wordWrap='CJK',          # enables wrapping for all content
        spaceAfter=0,
        spaceBefore=0,
    )

# Pre-built styles used across all tables
_S_HDR   = _cell_style(bold=True,  size=8,   colour=WHT,  align=TA_CENTER)
_S_HDR_L = _cell_style(bold=True,  size=8,   colour=WHT,  align=TA_LEFT)
_S_BODY  = _cell_style(bold=False, size=8,   colour=BLK,  align=TA_LEFT)
_S_BODY_C= _cell_style(bold=False, size=8,   colour=BLK,  align=TA_CENTER)
_S_BOLD  = _cell_style(bold=True,  size=8,   colour=BLK,  align=TA_CENTER)
_S_LABEL = _cell_style(bold=False, size=7.5, colour=GRY,  align=TA_LEFT)
_S_VALUE = _cell_style(bold=True,  size=8.5, colour=BLK,  align=TA_LEFT)


def P(text, style=None):
    """Shorthand: wrap any string in a Paragraph so it wraps in cells."""
    return Paragraph(str(text) if text else '—', style or _S_BODY)


def PC(text, style=None):
    """Centred paragraph."""
    return Paragraph(str(text) if text else '—', style or _S_BODY_C)


def _base_table_style(header_bg=G1):
    """Common table style commands shared by all tables."""
    return [
        ('BACKGROUND',    (0, 0), (-1, 0), header_bg),
        ('TEXTCOLOR',     (0, 0), (-1, 0), WHT),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1,  0), 8),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [WHT, G6]),
        ('GRID',          (0, 0), (-1, -1), 0.3, BRD),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]


# ── Page header / footer ───────────────────────────────────────────

def _header_footer(canvas, doc, student, date_range_label):
    canvas.saveState()
    W = PAGE_W

    # Header bar
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

    # Footer
    canvas.setFillColor(G6)
    canvas.rect(0, 0, W, 1.1*cm, fill=1, stroke=0)
    canvas.setStrokeColor(G3)
    canvas.setLineWidth(1)
    canvas.line(MARGIN, 1.1*cm, W - MARGIN, 1.1*cm)
    canvas.setFillColor(GRY)
    canvas.setFont('Helvetica', 8)
    canvas.drawString(MARGIN, 0.42*cm, f"Student: {student['name']}  |  {date_range_label}")
    canvas.drawRightString(W - MARGIN, 0.42*cm, f"Page {doc.page}")
    canvas.restoreState()


# ── Profile block ──────────────────────────────────────────────────

def _profile_block(student, date_range_label, styles):
    info = [
        ['Student Name',    student['name'],              'Login ID',   student['login_id']],
        ['Class',           student['class'],             'Batch',      student['batch']],
        ['Parent/Guardian', student['parent_name'] or '—','Contact',    student['parent_contact'] or '—'],
        ['Report Period',   date_range_label,             'Generated',  datetime.now().strftime('%d %b %Y')],
    ]

    rows = []
    for row in info:
        rows.append([
            P(row[0], _S_LABEL),
            P(row[1], _S_VALUE),
            P(row[2], _S_LABEL),
            P(row[3], _S_VALUE),
        ])

    # label cols narrow, value cols wide
    col_w = [3.0*cm, 6.0*cm, 3.0*cm, 5.4*cm]
    t = Table(rows, colWidths=col_w)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), G6),
        ('BOX',           (0, 0), (-1, -1), 0.5, G3),
        ('INNERGRID',     (0, 0), (-1, -1), 0.3, BRD),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]))
    return [t, Spacer(1, 12)]


# ── Summary stats ──────────────────────────────────────────────────

def _summary_table(student, results, styles):
    if not results:
        return []
    pcts  = [round(r['marks'] / r['total_marks'] * 100, 1) for r in results]
    avg   = round(sum(pcts) / len(pcts), 1)
    best  = max(pcts)
    worst = min(pcts)
    total = len(pcts)

    def stat_cell(label, value, colour):
        return [
            Paragraph(f'<b>{value}</b>',
                      ParagraphStyle('sv', fontName='Helvetica-Bold', fontSize=20,
                                     textColor=colour, alignment=TA_CENTER, leading=22)),
            Paragraph(label, ParagraphStyle('sl', fontName='Helvetica', fontSize=8,
                                            textColor=GRY, alignment=TA_CENTER, leading=11)),
        ]

    data = [[
        stat_cell('Average Score', f'{avg}%',   pct_colour(avg)),
        stat_cell('Best Score',    f'{best}%',  GRN),
        stat_cell('Lowest Score',  f'{worst}%', RED),
        stat_cell('Tests Taken',   str(total),  G2),
    ]]

    t = Table(data, colWidths=[CONTENT_W / 4] * 4)
    t.setStyle(TableStyle([
        ('BOX',           (0, 0), (-1, -1), 0.5, BRD),
        ('INNERGRID',     (0, 0), (-1, -1), 0.5, BRD),
        ('BACKGROUND',    (0, 0), (-1, -1), G6),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return [t, Spacer(1, 14)]


# ── Subject table ──────────────────────────────────────────────────

def _subject_table(results, styles):
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

    # Column widths — total must equal CONTENT_W
    # Subject(4.5) Tests(2) TotalMarks(3) Obtained(2.5) Avg%(2.8) Grade(2.6)
    col_w = [4.5*cm, 2.0*cm, 3.0*cm, 2.5*cm, 2.8*cm, 2.6*cm]

    header = [
        P('Subject',     _S_HDR_L),
        PC('Tests',      _S_HDR),
        PC('Total Marks',_S_HDR),
        PC('Obtained',   _S_HDR),
        PC('Average %',  _S_HDR),
        PC('Grade',      _S_HDR),
    ]
    rows = [header]

    for s, v in sorted(subj.items()):
        pct = round(v['marks'] / v['total'] * 100, 1)
        pct_style = _cell_style(bold=True, size=8, colour=pct_colour(pct), align=TA_CENTER)
        g = grade(pct)
        g_col = GRN if pct >= 70 else AMB if pct >= 50 else RED
        grade_style = _cell_style(bold=True, size=8, colour=g_col, align=TA_CENTER)
        rows.append([
            P(s),
            PC(str(v['count'])),
            PC(str(v['total'])),
            PC(str(v['marks'])),
            Paragraph(f'{pct}%', pct_style),
            Paragraph(g, grade_style),
        ])

    style = _base_table_style(G2)
    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle(style))
    return [
        Paragraph('Subject-wise Performance', styles['section']),
        t,
        Spacer(1, 14),
    ]


# ── Chapter & Topic table ──────────────────────────────────────────

def _chapter_topic_table(results, styles):
    has_ct = any(r['chapter'] or r['topic'] for r in results)
    if not has_ct:
        return []

    chapters = {}
    for r in results:
        ch  = r['chapter'] or 'Uncategorised'
        tp  = r['topic']   or 'General'
        key = (ch, tp)
        if key not in chapters:
            chapters[key] = {'marks': 0, 'total': 0, 'count': 0, 'subject': r['subject']}
        chapters[key]['marks'] += r['marks']
        chapters[key]['total'] += r['total_marks']
        chapters[key]['count'] += 1

    # Column widths that add to CONTENT_W (17.4 cm)
    # Chapter(3.8) Topic(3.8) Subject(2.8) Tests(1.4) Obtained(1.8) Max(1.4) %(1.6) Strength(2.4) = 19.0 too wide
    # Reduce: Chapter(3.4) Topic(3.4) Subject(2.6) Tests(1.2) Obtained(1.6) Max(1.2) %(1.5) Strength(2.5) = 17.4 ✓
    col_w = [3.4*cm, 3.4*cm, 2.6*cm, 1.2*cm, 1.6*cm, 1.2*cm, 1.5*cm, 2.5*cm]

    header = [
        P('Chapter',  _S_HDR_L),
        P('Topic',    _S_HDR_L),
        P('Subject',  _S_HDR_L),
        PC('Tests',   _S_HDR),
        PC('Obtained',_S_HDR),
        PC('Max',     _S_HDR),
        PC('%',       _S_HDR),
        PC('Strength',_S_HDR),
    ]
    rows = [header]

    for (ch, tp), v in sorted(chapters.items()):
        pct = round(v['marks'] / v['total'] * 100, 1)
        strength = ('Strong \u2713' if pct >= 75 else
                    'Average ~'     if pct >= 50 else
                    'Needs Work \u2717')
        pct_style   = _cell_style(bold=True,  size=8, colour=pct_colour(pct), align=TA_CENTER)
        str_colour  = GRN if pct >= 75 else AMB if pct >= 50 else RED
        str_style   = _cell_style(bold=True,  size=7.5, colour=str_colour, align=TA_CENTER)

        rows.append([
            P(ch),
            P(tp),
            P(v['subject']),
            PC(str(v['count'])),
            PC(str(v['marks'])),
            PC(str(v['total'])),
            Paragraph(f'{pct}%', pct_style),
            Paragraph(strength, str_style),
        ])

    style = _base_table_style(G1)
    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle(style))
    return [
        Paragraph('Chapter &amp; Topic Analysis', styles['section']),
        t,
        Spacer(1, 14),
    ]


# ── Test history table ─────────────────────────────────────────────

def _results_table(results, styles):
    # Column widths for 9 columns — total = CONTENT_W (17.4 cm)
    # Date(2.0) Code(2.0) Subject(2.4) Chapter(2.8) Topic(3.2) Marks(1.5) Total(1.5) %(1.5) Grade(1.5) = 18.4 too wide
    # Adjusted: Date(1.8) Code(1.9) Subject(2.2) Chapter(2.6) Topic(3.0) Marks(1.4) Total(1.4) %(1.6) Grade(1.5) = 17.4 ✓
    col_w = [1.8*cm, 1.9*cm, 2.2*cm, 2.6*cm, 3.0*cm, 1.4*cm, 1.4*cm, 1.6*cm, 1.5*cm]

    header = [
        P('Date',      _S_HDR_L),
        P('Test Code', _S_HDR_L),
        P('Subject',   _S_HDR_L),
        P('Chapter',   _S_HDR_L),
        P('Topic',     _S_HDR_L),
        PC('Marks',    _S_HDR),
        PC('Total',    _S_HDR),
        PC('%',        _S_HDR),
        PC('Grade',    _S_HDR),
    ]
    rows = [header]

    style_cmds = _base_table_style(G1)

    for i, r in enumerate(results, start=1):
        pct = round(r['marks'] / r['total_marks'] * 100, 1)
        g   = grade(pct)
        pct_style   = _cell_style(bold=True,  size=8, colour=pct_colour(pct), align=TA_CENTER)
        g_col       = GRN if pct >= 70 else AMB if pct >= 50 else RED
        grade_style = _cell_style(bold=True,  size=8, colour=g_col, align=TA_CENTER)

        rows.append([
            P(r['date']),
            P(r['code']),
            P(r['subject']),
            P(r['chapter'] or '—'),
            P(r['topic']   or '—'),
            PC(str(r['marks'])),
            PC(str(r['total_marks'])),
            Paragraph(f'{pct}%', pct_style),
            Paragraph(g, grade_style),
        ])

    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle(style_cmds))
    return [
        Paragraph('Test History', styles['section']),
        t,
        Spacer(1, 14),
    ]


# ── Bar chart ──────────────────────────────────────────────────────

def _bar_chart(results, styles):
    subj = {}
    for r in results:
        s = r['subject']
        if s not in subj:
            subj[s] = {'marks': 0, 'total': 0}
        subj[s]['marks'] += r['marks']
        subj[s]['total'] += r['total_marks']

    if not subj:
        return []

    labels = list(subj.keys())
    values = [round(v['marks'] / v['total'] * 100, 1) for v in subj.values()]

    chart_h = 5.5 * cm
    d = Drawing(CONTENT_W, chart_h + 1.2*cm)

    bc = VerticalBarChart()
    bc.x      = 1.5 * cm
    bc.y      = 1.0 * cm
    bc.width  = CONTENT_W - 2.5*cm
    bc.height = chart_h - 0.5*cm
    bc.data   = [values]
    bc.categoryAxis.categoryNames   = labels
    bc.categoryAxis.labels.fontSize = 8
    bc.categoryAxis.labels.fontName = 'Helvetica'
    bc.valueAxis.valueMin  = 0
    bc.valueAxis.valueMax  = 100
    bc.valueAxis.valueStep = 25
    bc.valueAxis.labels.fontSize = 8
    bc.valueAxis.labels.fontName = 'Helvetica'
    bc.bars[0].fillColor   = G2
    bc.bars[0].strokeColor = G1
    bc.bars[0].strokeWidth = 0.5
    bc.groupSpacing = 8
    d.add(bc)

    return [
        Paragraph('Subject Performance Chart', styles['section']),
        d,
        Spacer(1, 14),
    ]


# ── Section heading style ──────────────────────────────────────────

def make_styles():
    styles = {}
    styles['title'] = ParagraphStyle(
        'Title', fontName='Helvetica-Bold',
        fontSize=20, textColor=G1,
        spaceAfter=4, spaceBefore=0, leading=24,
    )
    styles['subtitle'] = ParagraphStyle(
        'Subtitle', fontName='Helvetica',
        fontSize=10, textColor=GRY,
        spaceAfter=2, leading=13,
    )
    styles['section'] = ParagraphStyle(
        'Section', fontName='Helvetica-Bold',
        fontSize=12, textColor=G1,
        spaceBefore=14, spaceAfter=6, leading=15,
    )
    styles['body'] = ParagraphStyle(
        'Body', fontName='Helvetica',
        fontSize=9, textColor=BLK,
        leading=13, spaceAfter=2,
    )
    return styles


# ── Main entry point ───────────────────────────────────────────────

def generate_pdf(student, results, date_range_label='All Time'):
    """
    student  : sqlite3.Row or dict — name, login_id, class, batch, parent_name, parent_contact
    results  : list of rows       — marks, total_marks, code, subject, date, chapter, topic
    Returns  : bytes (PDF content)
    """
    buf    = io.BytesIO()
    styles = make_styles()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2.0*cm,  bottomMargin=1.8*cm,
        title=f"FUNDAAZ – {student['name']} Report",
        author='FUNDAAZ System',
    )

    def _hf(canvas, doc):
        _header_footer(canvas, doc, student, date_range_label)

    story = []

    story.append(Spacer(1, 4))
    story.append(Paragraph('Academic Performance Report', styles['title']))
    story.append(Paragraph(f'Period: {date_range_label}', styles['subtitle']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=G3, spaceAfter=10))

    story += _profile_block(student, date_range_label, styles)

    if not results:
        story.append(Paragraph(
            'No test results found for the selected period.', styles['body']
        ))
        doc.build(story, onFirstPage=_hf, onLaterPages=_hf)
        return buf.getvalue()

    story += _summary_table(student, results, styles)
    story += _bar_chart(results, styles)
    story += _subject_table(results, styles)
    story += _chapter_topic_table(results, styles)
    story += _results_table(results, styles)

    doc.build(story, onFirstPage=_hf, onLaterPages=_hf)
    return buf.getvalue()
