import base64
import io

import pytest
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

import app as app_module
from analysis import Analysis, DocumentError, SAMPLE_ANALYSIS, SAMPLE_PAGES, extract_pages, ground_findings
from reports import make_report


def pdf_bytes(text='The resident must provide 30 days of written notice before ending the agreement.'):
    stream = io.BytesIO()
    c = canvas.Canvas(stream)
    if text:
        c.drawString(50, 750, text)
    c.showPage()
    c.save()
    return stream.getvalue()


@pytest.fixture
def client():
    return app_module.create_app({'TESTING': True, 'GEMINI_API_KEY': '', 'FIREBASE_WEB_CONFIG': {}}).test_client()


@pytest.fixture
def authenticated(monkeypatch):
    import firebase_admin
    from firebase_admin import auth
    monkeypatch.setattr(firebase_admin, 'get_app', lambda: object())
    def verify(token, check_revoked):
        assert check_revoked is True
        if token != 'valid-test-token':
            raise ValueError('invalid')
        return {'uid': 'student-test'}
    monkeypatch.setattr(auth, 'verify_id_token', verify)
    application = app_module.create_app({'TESTING': True, 'GEMINI_API_KEY': 'fake-test-key',
        'FIREBASE_WEB_CONFIG': dict(apiKey='test', authDomain='test', projectId='test', appId='test')})
    return application.test_client(), {'Authorization': 'Bearer valid-test-token'}


def test_home_and_config_without_secrets(client):
    assert client.get('/').status_code == 200
    assert client.get('/login').status_code == 200
    assert client.get('/api/config').json == {'firebase': None, 'ai_ready': False}


def test_sample_is_labeled_and_report_is_valid(client):
    response = client.get('/api/sample')
    data = response.json
    assert response.status_code == 200
    assert data['sample'] is True and len(data['findings']) == 6
    report = PdfReader(io.BytesIO(base64.b64decode(data['report'])))
    text = '\n'.join(page.extract_text() for page in report.pages)
    assert 'fictional agreement' in text and 'Rent is due by the 5th' in text
    assert response.headers['Cache-Control'] == 'no-store'


def test_auth_cannot_be_bypassed(client):
    assert client.post('/api/analyze').status_code == 401
    assert client.post('/api/analyze', headers={'Authorization': 'Bearer forged'}).status_code == 503


def test_invalid_token_is_rejected(authenticated):
    client, _ = authenticated
    assert client.post('/api/analyze', headers={'Authorization': 'Bearer forged'}).status_code == 401


def test_valid_upload_and_rate_limit(authenticated, monkeypatch):
    client, headers = authenticated
    def analyze(pages, api_key, model, language="en"):
        assert '30 days' in pages[0]
        assert api_key == 'fake-test-key'
        return ground_findings(Analysis(findings=[SAMPLE_ANALYSIS.findings[2]]), pages)
    monkeypatch.setattr(app_module, 'analyze_document', analyze)
    response = client.post('/api/analyze', headers=headers, data={'file': (io.BytesIO(pdf_bytes()), 'agreement.pdf')})
    assert response.status_code == 200
    assert response.json['sample'] is False
    assert len(response.json['findings']) == 1
    assert client.post('/api/analyze', headers=headers, data={'file': (io.BytesIO(pdf_bytes()), 'again.pdf')}).status_code == 429


def test_missing_ai_configuration(authenticated):
    client, headers = authenticated
    client.application.config['GEMINI_API_KEY'] = ''
    assert client.post('/api/analyze', headers=headers).status_code == 503


def test_bad_upload(authenticated):
    client, headers = authenticated
    response = client.post('/api/analyze', headers=headers, data={'file': (io.BytesIO(b'not pdf'), 'bad.pdf')})
    assert response.status_code == 422


def test_provider_error_does_not_leak(authenticated, monkeypatch):
    client, headers = authenticated
    def fail(*args):
        raise RuntimeError('SECRET provider data')
    monkeypatch.setattr(app_module, 'analyze_document', fail)
    response = client.post('/api/analyze', headers=headers, data={'file': (io.BytesIO(pdf_bytes()), 'agreement.pdf')})
    assert response.status_code == 502
    assert 'SECRET' not in response.text


def test_pdf_extraction():
    assert '30 days' in extract_pages(pdf_bytes())[0]


@pytest.mark.parametrize('data', [b'bad', b'%PDF-garbage', pdf_bytes('')])
def test_unreadable_documents(data):
    with pytest.raises(DocumentError):
        extract_pages(data)


def test_encrypted_document():
    writer = PdfWriter()
    writer.append(io.BytesIO(pdf_bytes()))
    writer.encrypt('secret')
    stream = io.BytesIO()
    writer.write(stream)
    with pytest.raises(DocumentError, match='password protected'):
        extract_pages(stream.getvalue())


def test_too_many_pages():
    writer = PdfWriter()
    for _ in range(31):
        writer.add_blank_page(width=100, height=100)
    stream = io.BytesIO()
    writer.write(stream)
    with pytest.raises(DocumentError, match='1–30'):
        extract_pages(stream.getvalue())


def test_grounding_rejects_fabricated_quotes_and_pages():
    good = SAMPLE_ANALYSIS.findings[0]
    bad_quote = good.model_copy(update={'quote': 'You owe one million rupees.'})
    bad_page = good.model_copy(update={'page': 2})
    findings, rejected = ground_findings(Analysis(findings=[good, good, bad_quote, bad_page]), SAMPLE_PAGES)
    assert len(findings) == 1 and rejected == 2


def test_report_escapes_markup_and_handles_rupee():
    finding = SAMPLE_ANALYSIS.findings[0].model_dump()
    finding['quote'] = '<script>alert(1)</script> Payment is ₹8,000.'
    report = make_report('test.pdf', [finding])
    text = ''.join(page.extract_text() for page in PdfReader(io.BytesIO(report)).pages)
    assert '<script>' in text and '₹8,000' in text


@pytest.mark.parametrize('finish_reason', ['STOP', 'MAX_TOKENS'])
def test_gemini_response_validation(monkeypatch, finish_reason):
    from unittest.mock import MagicMock
    from google import genai
    from google.genai import types
    from analysis import analyze_document
    client = MagicMock()
    client.__enter__.return_value = client
    client.models.generate_content.return_value = types.GenerateContentResponse(candidates=[
        types.Candidate(finish_reason=finish_reason, content=types.Content(parts=[
            types.Part(text=SAMPLE_ANALYSIS.model_dump_json())]))])
    monkeypatch.setattr(genai, 'Client', lambda **kwargs: client)
    if finish_reason == 'MAX_TOKENS':
        with pytest.raises(DocumentError, match='could not complete'):
            analyze_document(SAMPLE_PAGES, 'fake-gemini-key', 'gemini-3.8-flash')
    else:
        findings, rejected = analyze_document(SAMPLE_PAGES, 'fake-gemini-key', 'gemini-3.8-flash')
        assert len(findings) == 6 and rejected == 0
        config = client.models.generate_content.call_args.kwargs['config']
        assert config.response_mime_type == 'application/json'
        item_schema = config.response_json_schema['properties']['findings']['items']
        assert set(item_schema['required']) <= set(item_schema['properties'])
        assert item_schema['properties']['title']['type'] == 'string'


def test_gemini_quota_error(monkeypatch):
    from unittest.mock import MagicMock
    from google import genai
    from google.genai import errors
    from analysis import analyze_document
    client = MagicMock()
    client.__enter__.return_value = client
    client.models.generate_content.side_effect = errors.ClientError(429, {'error': {'message': 'Quota exceeded'}})
    monkeypatch.setattr(genai, 'Client', lambda **kwargs: client)
    with pytest.raises(DocumentError, match='quota'):
        analyze_document(SAMPLE_PAGES, 'fake-gemini-key', 'gemini-3.8-flash')


def test_missing_admin_credentials_explains_setup(monkeypatch):
    import firebase_admin
    from google.auth.exceptions import DefaultCredentialsError
    def missing_app():
        raise ValueError('No default app')
    def missing_credentials(**kwargs):
        raise DefaultCredentialsError('No credentials')
    monkeypatch.setattr(firebase_admin, 'get_app', missing_app)
    monkeypatch.setattr(firebase_admin, 'initialize_app', missing_credentials)
    client = app_module.create_app({'TESTING': True, 'FIREBASE_WEB_CONFIG':
        dict(apiKey='test', authDomain='test', projectId='test', appId='test')}).test_client()
    response = client.post('/api/analyze', headers={'Authorization': 'Bearer test'})
    assert response.status_code == 503
    assert 'server authentication setup is incomplete' in response.json['error']


@pytest.mark.parametrize('language', ['en', 'hi', 'mr'])
def test_report_languages(client, language):
    response = client.get('/api/sample?language=' + language)
    assert response.status_code == 200
    data = response.json
    assert data['language'] == language
    assert data['findings'][0]['quote'] == SAMPLE_ANALYSIS.findings[0].quote
    if language != 'en':
        assert any('\u0900' <= char <= '\u097f' for char in data['findings'][0]['explanation'])
    assert base64.b64decode(data['report']).startswith(b'%PDF')


def test_invalid_language(client):
    assert client.get('/api/sample?language=invalid').status_code == 400


def test_offer_score_deduplicates_and_rejects_false_evidence():
    from analysis import offer_assessment, OfferAnalysis
    finding = dict(category='Upfront payment', title='Payment requested', explanation='Verify this fee.', quote='Pay a joining fee of INR 5000.', page=1, needs_clarification=True, question='Why is this required?')
    result = OfferAnalysis(findings=[finding, finding])
    supported, rejected = ground_findings(result, ['Pay a joining fee of INR 5000.'])
    assert len(supported) == 1
    assert offer_assessment(supported, rejected)['score'] == 45
    supported, rejected = ground_findings(result, ['No joining fee is required for this role.'])
    assert not supported
    assert offer_assessment(supported, rejected)['score'] is None
    assert offer_assessment([], 0)['verdict'] == 'Authenticity unverified'


def test_offer_upload_includes_score_and_pdf(authenticated, monkeypatch):
    client, headers = authenticated
    def analyze(pages, api_key, model, language, mode):
        assert mode == 'offer'
        return [dict(category='Pressure', title='Urgent payment request', explanation='Verify this request.', quote=pages[0], page=1, needs_clarification=True, question='Can HR confirm this?')], 0
    monkeypatch.setattr(app_module, 'analyze_document', analyze)
    result = client.post('/api/analyze', headers=headers, data={'mode':'offer', 'file':(io.BytesIO(pdf_bytes()), 'offer.pdf')})
    assert result.status_code == 200
    assert result.json['assessment']['score'] == 10
    text = ''.join(p.extract_text() for p in PdfReader(io.BytesIO(base64.b64decode(result.json['report']))).pages)
    assert 'Authenticity unverified' in text


def test_offer_provider_outage_returns_labeled_report(authenticated, monkeypatch):
    client, headers = authenticated
    def unavailable(*args, **kwargs):
        raise DocumentError('Gemini is temporarily busy or unavailable.')
    monkeypatch.setattr(app_module, 'analyze_document', unavailable)
    result = client.post('/api/analyze', headers=headers, data={'mode':'offer','language':'mr', 'file':(io.BytesIO(pdf_bytes('You must pay a joining fee of INR 5000 to secure this job.')), 'offer.pdf')})
    assert result.status_code == 200
    assert result.json['language'] == 'en'
    assert result.json['assessment']['score'] == 45
    assert 'Basic English screening' in result.json['assessment']['analysis_method']
    assert result.json['findings'][0]['quote'] == 'You must pay a joining fee of INR 5000 to secure this job.'
    assert base64.b64decode(result.json['report']).startswith(b'%PDF')


def test_basic_offer_screening_ignores_prohibitions():
    from offer_review import basic_offer_review
    assert not basic_offer_review(['You must not pay a joining fee of INR 5000. Never share your password.'])


def test_transient_provider_error_uses_backup(monkeypatch):
    import analysis
    calls = []
    monkeypatch.setenv('GEMINI_FALLBACK_MODEL', 'backup-model')
    monkeypatch.setattr(analysis.time, 'sleep', lambda _: None)
    def generate(pages, key, model, **kwargs):
        calls.append((model, kwargs))
        if model == 'primary-model':
            raise analysis.ProviderUnavailable('temporary')
        return [], 0
    monkeypatch.setattr(analysis, '_analyze_once', generate)
    assert analysis.analyze_document(['test'], 'fake', 'primary-model', language='mr', mode='offer') == ([], 0)
    assert [m for m, _ in calls] == ['primary-model', 'backup-model']
    assert calls[1][1] == {'language': 'mr', 'mode': 'offer'}


def test_provider_retries_are_bounded(monkeypatch):
    import analysis
    calls = []
    monkeypatch.setattr(analysis.time, 'sleep', lambda _: None)
    def unavailable(*args, **kwargs):
        calls.append(1)
        raise analysis.ProviderUnavailable('temporary')
    monkeypatch.setattr(analysis, '_analyze_once', unavailable)
    with pytest.raises(analysis.ProviderUnavailable):
        analysis.analyze_document(['test'], 'fake', 'primary')
    assert len(calls) == 3


def test_invalid_pdf_does_not_block_retry(authenticated, monkeypatch):
    client, headers = authenticated
    monkeypatch.setattr(app_module, 'analyze_document', lambda *args, **kwargs: ([], 0))
    invalid = client.post('/api/analyze', headers=headers, data={'file': (io.BytesIO(b'broken'), 'broken.pdf')})
    assert invalid.status_code == 422
    valid = client.post('/api/analyze', headers=headers, data={'file': (io.BytesIO(pdf_bytes()), 'valid.pdf')})
    assert valid.status_code == 200


def test_provider_failure_does_not_block_retry(authenticated, monkeypatch):
    client, headers = authenticated
    def unavailable(*args, **kwargs):
        raise DocumentError('Provider unavailable')
    monkeypatch.setattr(app_module, 'analyze_document', unavailable)
    assert client.post('/api/analyze', headers=headers, data={'file': (io.BytesIO(pdf_bytes()), 'valid.pdf')}).status_code == 422
    monkeypatch.setattr(app_module, 'analyze_document', lambda *args, **kwargs: ([], 0))
    assert client.post('/api/analyze', headers=headers, data={'file': (io.BytesIO(pdf_bytes()), 'valid.pdf')}).status_code == 200


def test_distinct_uploads_generate_distinct_reports(authenticated, monkeypatch):
    import hashlib
    from firebase_admin import auth
    client, _ = authenticated
    monkeypatch.setattr(auth, 'verify_id_token', lambda token, check_revoked: {'uid': token})
    seen = []
    def analyze(pages, *args, **kwargs):
        seen.append(pages[0])
        return [dict(category='Payment', title='Payment stated in this PDF', explanation=pages[0], quote=pages[0], page=1, needs_clarification=False, question='')], 0
    monkeypatch.setattr(app_module, 'analyze_document', analyze)
    statements = ['The tenant pays INR 12345 each month for Apartment ALPHA.', 'The intern receives INR 67890 per month at Employer BETA.']
    responses = []
    for index, statement in enumerate(statements):
        pdf = pdf_bytes(statement)
        response = client.post('/api/analyze', headers={'Authorization': 'Bearer user-'+str(index)}, data={'file':(io.BytesIO(pdf), 'document.pdf')})
        assert response.status_code == 200
        result = response.json
        assert result['sample'] is False
        assert result['analysis_source'] == 'live_ai'
        assert result['document_hash'] == hashlib.sha256(pdf).hexdigest()
        assert result['findings'][0]['quote'] == statement
        report = ''.join(page.extract_text() for page in PdfReader(io.BytesIO(base64.b64decode(result['report']))).pages)
        assert statement in report
        assert 'Rent is due by the 5th' not in report
        responses.append(result)
    assert seen == statements
    assert responses[0]['document_hash'] != responses[1]['document_hash']
    assert responses[0]['report'] != responses[1]['report']
