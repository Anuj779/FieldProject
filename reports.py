"""In-memory reports. All document/model text is escaped before rendering."""
import io
from pathlib import Path
from html import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('Manrope', str(Path(__file__).parent / 'static/vendor/manrope-regular.ttf')))
pdfmetrics.registerFontFamily('Manrope', normal='Manrope', bold='Manrope', italic='Manrope', boldItalic='Manrope')


def make_report(filename, findings, sample=False, rejected=0):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, title='Clausewise | Agreement review', author='Clausewise',
                            rightMargin=44, leftMargin=44, topMargin=44, bottomMargin=44)
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = 'Manrope'
    styles.add(ParagraphStyle(name='QuoteBox', parent=styles['BodyText'], textColor=colors.HexColor('#444444'),
                              backColor=colors.HexColor('#f3f3f3'), borderPadding=10, spaceBefore=10, spaceAfter=14))
    styles['Title'].alignment = TA_LEFT
    styles['Title'].textColor = colors.HexColor('#b5122d')
    safe = lambda value: escape(str(value))
    story = [Paragraph('CLAUSEWISE', styles['Title']), Paragraph('Student agreement review', styles['Heading2']),
             Paragraph(safe(filename), styles['BodyText']), Spacer(1, 12)]
    if sample:
        story.append(Paragraph('SAMPLE REPORT — fictional agreement, prepared explanations; not a live AI analysis.', styles['BodyText']))
    story.append(Paragraph(f'{len(findings)} source-backed findings. This review may miss terms. Read your full agreement; it is not legal advice.', styles['BodyText']))
    if rejected:
        story.append(Paragraph(f'{rejected} unsupported finding(s) were excluded. The analysis may be incomplete.', styles['BodyText']))
    story.append(Spacer(1, 16))
    for i, finding in enumerate(findings, 1):
        block = [HRFlowable(width='100%', color=colors.HexColor('#dddddd')),
                      Paragraph(f"{i}. {safe(finding['title'])}", styles['Heading2']),
                      Paragraph(f"{safe(finding['category'])} | Page {finding['page']}", styles['BodyText']),
                      Spacer(1, 6), Paragraph(safe(finding['explanation']), styles['BodyText']),
                      Paragraph(safe(finding['quote']), styles['QuoteBox'])]
        if finding['needs_clarification']:
            block.append(Paragraph('Ask the provider: ' + safe(finding['question']), styles['BodyText']))
        block.append(Spacer(1, 12))
        story.append(KeepTogether(block))
    def footer(canvas, document):
        canvas.setFont('Manrope', 9)
        canvas.setFillColor(colors.grey)
        canvas.drawString(44, 25, 'Clausewise | Read carefully. Decide confidently.')
        canvas.drawRightString(document.pagesize[0]-44, 25, str(document.page))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
