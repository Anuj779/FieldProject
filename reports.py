"""In-memory reports. All document/model text is escaped before rendering."""
import io
import re
from pathlib import Path
from html import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('Manrope', str(Path(__file__).parent / 'static/vendor/manrope-regular.ttf')))
pdfmetrics.registerFont(TTFont('Devanagari', str(Path(__file__).parent / 'static/vendor/noto-devanagari.ttf')))
pdfmetrics.registerFontFamily('Devanagari', normal='Devanagari', bold='Devanagari', italic='Devanagari', boldItalic='Devanagari')
pdfmetrics.registerFontFamily('Manrope', normal='Manrope', bold='Manrope', italic='Manrope', boldItalic='Manrope')


def make_report(filename, findings, sample=False, rejected=0, language="en", assessment=None):
    from localization import LABELS
    labels = LABELS[language]
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, title='Clausewise | Agreement review', author='Clausewise',
                            rightMargin=44, leftMargin=44, topMargin=44, bottomMargin=44)
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = 'Devanagari' if language != 'en' else 'Manrope'
        style.shaping = language != "en"
        if hasattr(style, "leading"):
            style.leading = max(style.leading, style.fontSize * 1.6)
    styles.add(ParagraphStyle(name='QuoteBox', parent=styles['BodyText'], textColor=colors.HexColor('#444444'),
                              backColor=colors.HexColor('#f3f3f3'), borderPadding=10, spaceBefore=10, spaceAfter=14))
    styles['Title'].alignment = TA_LEFT
    styles['Title'].textColor = colors.HexColor('#b5122d')
    safe = lambda value: escape(str(value))
    story = [Paragraph('CLAUSEWISE', styles['Title']), Paragraph('OFFER LETTER RISK REPORT' if assessment else safe(labels[0]), styles['Heading2']),
             Paragraph(safe(filename), styles['BodyText']), Spacer(1, 12)]
    if assessment:
        story.extend([Paragraph(safe(assessment.get('status', 'Authenticity unverified')), styles['Heading2']),
            Paragraph(safe(str(assessment['score']) + '/100 - ' + assessment['level'] if assessment['score'] is not None else 'Score unavailable: incomplete review'), styles['Heading2']),
            Paragraph(safe(assessment['verdict'] + '. ' + assessment['method']), styles['BodyText']),
            Paragraph(safe(assessment.get('analysis_method', 'Document-only screening.')), styles['BodyText']),
            Paragraph('Verify the offer through contact details independently obtained from the employer official website. Do not use the letter as proof of authenticity.', styles['BodyText'])])
    if sample:
        story.append(Paragraph(safe(labels[4]), styles['BodyText']))
    story.append(Paragraph(safe(f'{len(findings)} {labels[1]}'), styles['BodyText']))
    if rejected:
        story.append(Paragraph(safe(f'{rejected} {labels[5]}'), styles['BodyText']))
    story.append(Spacer(1, 16))
    for i, finding in enumerate(findings, 1):
        block = [HRFlowable(width='100%', color=colors.HexColor('#dddddd')),
                      Paragraph(f"{i}. {safe(finding['title'])}", styles['Heading2']),
                      Paragraph(f"{safe(finding.get('category_label', finding['category']))} | {safe(labels[2])} {finding['page']}", styles['BodyText']),
                      Spacer(1, 6), Paragraph(safe(finding['explanation']), styles['BodyText']),
                      Paragraph(safe(finding['quote']), styles['QuoteBox'])]
        if finding['needs_clarification']:
            block.append(Paragraph(safe(labels[3]) + ' ' + safe(finding['question']), styles['BodyText']))
        block.append(Spacer(1, 12))
        story.append(KeepTogether(block))
    def footer(canvas, document):
        canvas.setFont('Manrope', 9)
        canvas.setFillColor(colors.grey)
        canvas.drawString(44, 25, 'Clausewise | Read carefully. Decide confidently.')
        canvas.drawRightString(document.pagesize[0]-44, 25, str(document.page))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
