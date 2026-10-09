"""Limited local screening when the AI provider is unavailable.

Only explicit English-language requests are matched; absence of a match proves nothing.
"""
import re

RULES = [
 ('Upfront payment', r'\b(?:must|required to|need to) pay\b.{0,100}\b(?:joining|registration|recruitment|processing|security) (?:fee|deposit)\b',
  'Payment required to obtain the job', 'The letter asks the candidate to pay a fee to obtain the job. Verify this request independently before paying.'),
 ('Pressure', r'\b(?:send|make|complete)\b.{0,60}\bpayment\b.{0,40}\bwithin (?:two|2|one|1|24) hours?\b',
  'Urgent payment deadline', 'A short payment deadline pressures the candidate to act before checking the offer.'),
 ('Unverified contact', r'\b(?:all|only)\b.{0,100}\b(?:personal messaging|personal email|whatsapp)\b',
  'Recruitment restricted to a personal channel', 'A personal-only recruitment channel warrants independent confirmation with the employer. It does not by itself prove fraud.'),
 ('Sensitive credentials', r'\b(?:send|share|provide)\b.{0,45}\b(?:password|OTP|PIN)\b',
  'Secret credentials requested', 'Requests to share passwords, OTPs or PINs are a serious warning sign. Do not share these credentials.'),
]


def basic_offer_review(pages):
    findings = []
    for page_number, page in enumerate(pages, 1):
        for sentence in re.split(r'(?<=[.!?])\s+', page):
            # Avoid treating explicit prohibitions as suspicious requests.
            if re.search(r'\b(?:not|never|no|avoid|do not)\b', sentence, re.I):
                continue
            for category, pattern, title, explanation in RULES:
                if len(sentence) <= 2500 and re.search(pattern, sentence, re.I):
                    findings.append(dict(category=category, title=title, explanation=explanation,
                        quote=sentence, page=page_number, needs_clarification=True,
                        question='Can the employer confirm this clause through independently obtained official contact details?'))
    return findings
