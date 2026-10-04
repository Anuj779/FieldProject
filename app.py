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
    app.config.update(MAX_CONTENT_LENGTH=10 * 1024 * 1024, GEMINI_API_KEY=os.getenv('GEMINI_API_KEY', ''),
                      GEMINI_MODEL=os.getenv('GEMINI_MODEL', 'gemini-3.8-flash'))
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
                        firebase_admin.initialize_app(options={'projectId': app.config['FIREBASE_WEB_CONFIG']['projectId']})
                g.uid = auth.verify_id_token(token[7:], check_revoked=True)['uid']
            except DefaultCredentialsError:
                return jsonify(error='Your PDF has not been analyzed because server authentication setup is incomplete. Configure the Firebase Admin service-account file, then try again.'), 503
            except Exception:
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
        return jsonify(error='The upload is too large. Choose a PDF smaller than 10 MB.'), 413

    @app.get('/')
    @app.get('/login')
    @app.get('/workspace')
    def index():
        return render_template('index.html')

    @app.get('/api/config')
    def config():
        return jsonify(firebase=app.config['FIREBASE_WEB_CONFIG'] if ready() else None,
                       ai_ready=bool(app.config['GEMINI_API_KEY']))

    def payload(filename, pages, findings, rejected, sample=False):
        report = make_report(filename, findings, sample=sample, rejected=rejected)
        return jsonify(filename=filename, pages=len(pages), findings=findings, rejected=rejected,
                       sample=sample, report=base64.b64encode(report).decode('ascii'))

    @app.get('/api/sample')
    def sample():
        findings, rejected = ground_findings(SAMPLE_ANALYSIS, SAMPLE_PAGES)
        return payload('Sample housing agreement.pdf', SAMPLE_PAGES, findings, rejected, sample=True)

    @app.post('/api/analyze')
    @require_user
    def analyze():
        if not app.config['GEMINI_API_KEY']:
            return jsonify(error='Live AI analysis is not configured yet. You can explore the sample review.'), 503
        with lock:
            now = time.monotonic()
            for uid in list(recent):
                if now - recent[uid] > 60:
                    del recent[uid]
            if g.uid in recent:
                return jsonify(error='Please wait one minute between analyses.'), 429
            recent[g.uid] = now
        file = request.files.get('file')
        if not file or not file.filename.lower().endswith('.pdf'):
            return jsonify(error='Choose a PDF agreement to continue.'), 400
        if not slots.acquire(blocking=False):
            return jsonify(error='All analysis slots are busy. Please try again shortly.'), 429
        try:
            pages = extract_pages(file.read())
            findings, rejected = analyze_document(pages, app.config['GEMINI_API_KEY'], app.config['GEMINI_MODEL'])
            filename = secure_filename(file.filename)[:120] or 'Agreement.pdf'
            return payload(filename, pages, findings, rejected)
        except DocumentError as exc:
            return jsonify(error=str(exc)), 422
        except Exception:
            # Never log document text, tokens or provider exception bodies.
            app.logger.warning('Analysis failed; check provider configuration or availability.')
            return jsonify(error='Analysis is unavailable right now. Check your connection and try again later.'), 502
        finally:
            slots.release()

    return app


app = create_app()

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='127.0.0.1', port=int(os.getenv('PORT', '5000')), threads=6)
