import base64
import json
import os
import threading
import time
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, g
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from analysis import DocumentError, extract_pages, analyze_document, ground_findings, SAMPLE_ANALYSIS, SAMPLE_PAGES
from reports import make_report

load_dotenv()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=4 * 1024 * 1024 + 65536, GEMINI_API_KEY=os.getenv('GEMINI_API_KEY', ''),
                      GEMINI_MODEL=os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite'))
    try:
        raw = json.loads(os.getenv('FIREBASE_WEB_CONFIG', '{}'))
    except (ValueError, TypeError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    app.config['FIREBASE_WEB_CONFIG'] = {k: raw.get(k, '') for k in ('apiKey', 'authDomain', 'projectId', 'appId')}
    if test_config:
        app.config.update(test_config)
    slots = threading.BoundedSemaphore(3)
    lock = threading.Lock()
    recent = {}

    def ready():
        return all(app.config['FIREBASE_WEB_CONFIG'].get(k) for k in ('apiKey', 'authDomain', 'projectId', 'appId'))

    def require_user(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            token = request.headers.get('Authorization', '')
            if not token.startswith('Bearer ') or len(token) > 10000:
                return jsonify(error='Please sign in to analyze your agreement.'), 401
            if not ready():
                return jsonify(error='Firebase sign-in has not been configured yet.'), 503
            from google.auth.exceptions import DefaultCredentialsError
            try:
                import firebase_admin
                from firebase_admin import auth
                with lock:
                    try:
                        firebase_admin.get_app()
                    except ValueError:
                        raw_credentials = os.getenv('FIREBASE_ADMIN_CREDENTIALS', '')
                        if raw_credentials:
                            from firebase_admin import credentials
                            credential_data = json.loads(raw_credentials)
                            if credential_data.get('project_id') != app.config['FIREBASE_WEB_CONFIG']['projectId']:
                                raise DefaultCredentialsError('Firebase project mismatch')
                            firebase_admin.initialize_app(credentials.Certificate(credential_data), options={'projectId': credential_data['project_id']})
                        else:
                            firebase_admin.initialize_app(options={'projectId': app.config['FIREBASE_WEB_CONFIG']['projectId']})
                g.uid = auth.verify_id_token(token[7:], check_revoked=True)['uid']
            except DefaultCredentialsError:
                return jsonify(error='Your PDF has not been analyzed because server authentication setup is incomplete. Configure the Firebase Admin service-account file, then try again.'), 503
            except Exception as exc:
                app.logger.warning('Firebase verification failed: %s', type(exc).__name__)
                return jsonify(error='Your session could not be verified. Please sign in again. If this continues, check the Firebase server configuration.'), 401
            return fn(*args, **kwargs)
        return wrapped

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(error):
        return jsonify(error='The upload is too large. Choose a PDF smaller than 4 MB.'), 413

    @app.get('/')
    @app.get('/login')
    @app.get('/workspace')
    def index():
        return render_template('index.html')

    @app.get('/api/config')
    def config():
        return jsonify(firebase=app.config['FIREBASE_WEB_CONFIG'] if ready() else None,
                       ai_ready=bool(app.config['GEMINI_API_KEY']))

    def payload(filename, pages, findings, rejected, sample=False, language="en", assessment=None):
        from localization import CATEGORIES
        for finding in findings:
            finding['category_label'] = CATEGORIES.get(language, {}).get(finding['category'], finding['category'])
        report = make_report(filename, findings, sample=sample, rejected=rejected, language=language, assessment=assessment)
        return jsonify(filename=filename, pages=len(pages), findings=findings, rejected=rejected,
                       sample=sample, language=language, assessment=assessment, report=base64.b64encode(report).decode('ascii'))

    @app.get('/api/sample')
    def sample():
        findings, rejected = ground_findings(SAMPLE_ANALYSIS, SAMPLE_PAGES)
        from localization import SAMPLE_TRANSLATIONS
        language = request.args.get('language', 'en')
        if language not in ('en', 'hi', 'mr'):
            return jsonify(error='Choose English, Hindi or Marathi.'), 400
        if language != 'en':
            for finding, translation in zip(findings, SAMPLE_TRANSLATIONS[language]):
                finding['title'], finding['explanation'] = translation
        return payload('Sample housing agreement.pdf', SAMPLE_PAGES, findings, rejected, sample=True, language=language)

    @app.post('/api/analyze')
    @require_user
    def analyze():
        mode = request.form.get('mode', 'agreement')
        if mode not in ('agreement', 'offer'):
            return jsonify(error='Choose agreement or offer letter review.'), 400
        language = request.form.get('language', 'en')
        if language not in ('en', 'hi', 'mr'):
            return jsonify(error='Choose English, Hindi or Marathi.'), 400
        if not app.config['GEMINI_API_KEY']:
            return jsonify(error='Live AI analysis is not configured yet. You can explore the sample review.'), 503
        file = request.files.get('file')
        if not file or not file.filename.lower().endswith('.pdf'):
            return jsonify(error='Choose a PDF agreement to continue.'), 400
        if not slots.acquire(blocking=False):
            return jsonify(error='All analysis slots are busy. Please try again shortly.'), 429
        reserved = False
        completed = False
        try:
            data = file.read()
            if len(data) > 4 * 1024 * 1024:
                return jsonify(error='Choose a PDF smaller than 4 MB.'), 413
            pages = extract_pages(data)
            with lock:
                now = time.monotonic()
                for uid in list(recent):
                    if now - recent[uid] > 60:
                        del recent[uid]
                if g.uid in recent:
                    return jsonify(error='Please wait one minute between analyses.'), 429
                recent[g.uid] = now
            reserved = True
            kwargs = {'language': language}
            if mode == 'offer':
                kwargs['mode'] = mode
            fallback = False
            try:
                findings, rejected = analyze_document(pages, app.config['GEMINI_API_KEY'], app.config['GEMINI_MODEL'], **kwargs)
            except DocumentError as exc:
                if mode != 'offer' or 'temporarily busy or unavailable' not in str(exc):
                    raise
                from offer_review import basic_offer_review
                findings, rejected = basic_offer_review(pages), 0
                fallback = True
                language = 'en'
            from analysis import offer_assessment
            assessment = offer_assessment(findings, rejected) if mode == 'offer' else None
            if assessment:
                assessment['analysis_method'] = ('Basic English screening: Gemini was unavailable. Only explicit payment, urgency, personal-contact and credential requests were checked. Other warning signs may be missed. Retry later for a full AI review in your chosen language.' if fallback else 'AI-assisted document screening with exact source checks. No external authenticity verification.')
                assessment['status'] = ('Review incomplete' if rejected else 'Suspicious offer — verify before proceeding' if assessment['score'] >= 45 else 'Needs verification' if assessment['score'] else 'No matched warning signs — not verified real')
            filename = secure_filename(file.filename)[:120] or 'Agreement.pdf'
            response = payload(filename, pages, findings, rejected, language=language, assessment=assessment)
            completed = True
            return response
        except DocumentError as exc:
            return jsonify(error=str(exc)), 422
        except Exception:
            # Never log document text, tokens or provider exception bodies.
            app.logger.warning('Analysis failed; check provider configuration or availability.')
            return jsonify(error='Analysis is unavailable right now. Check your connection and try again later.'), 502
        finally:
            if reserved and not completed:
                with lock:
                    recent.pop(g.uid, None)
            slots.release()

    return app


app = create_app()

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='127.0.0.1', port=int(os.getenv('PORT', '5000')), threads=6)
