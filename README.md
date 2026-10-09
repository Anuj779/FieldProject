# Clausewise

A student contract analyzer with a red noir interface, Firebase email/password authentication, grounded AI findings and PDF reports.

## Run on Windows

Python 3.11+ is required. In PowerShell, from this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000. The sample review and its report work without credentials. Live authentication and AI analysis require the configuration below. The installed `.venv` in this workspace is already ready to run.

## Connect Firebase

1. Create a project in the [Firebase console](https://console.firebase.google.com/), then register a Web app.
2. In Authentication, enable the **Email/Password** provider. Set a password policy (at least 8 characters) and enable email enumeration protection.
3. In Authentication settings, add `localhost`, `127.0.0.1`, and your eventual deployed domain to authorized domains as needed.
4. Copy the web configuration into `FIREBASE_WEB_CONFIG` in `.env` as one JSON line. Include `apiKey`, `authDomain`, `projectId`, and `appId`.
5. In Project settings > Service accounts, obtain an Admin SDK service-account key for local development. Keep the JSON outside this repository. Put its absolute path in `GOOGLE_APPLICATION_CREDENTIALS` in `.env`, preferably using forward slashes. On cloud hosts, prefer a managed service identity.
6. Restart the server. Create an account on the login page, then sign in. Password reset uses Firebase's email templates. Enable/configure those in the Firebase console.

The browser sends a Firebase ID token with each upload. Python verifies its signature, project, expiry and revocation before processing. Passwords are handled by Firebase. There is no custom authentication bypass.

## Connect AI

Create a Gemini API key at https://aistudio.google.com/apikey and put it in `GEMINI_API_KEY` in `.env`. The default `GEMINI_MODEL` is `gemini-3.5-flash-lite`. Its free tier has model/project quotas; check your actual limits in AI Studio. Restart the server after configuration. Signing in to the Gemini chat app does not configure this API key.

The app sends page-numbered extracted text to Google Gemini. Free-tier data may be used to improve Google products: use fictional or redacted agreements for demonstrations. Pydantic validates returned fields, and the app rejects excerpts absent from the stated source page. This does not prove the explanation is correct or complete: review the findings against your document. Provider retention policies still apply.

## What is implemented

- Responsive landing, account, upload, and results screens using the supplied red noir aesthetic.
- Email/password sign-up, sign-in, reset and sign-out with Firebase; credentials must be supplied by the owner.
- Text PDF validation, up to 4 MB / 30 pages / 65,000 extracted characters; no OCR.
- Structured clause extraction, page references, evidence expansion and category filters.
- PDF report included in the authenticated analysis response; no report database or public report URLs.
- An explicitly labeled fictional sample with prepared findings, available without sign-in.
- Session state and analysis results kept in memory; files are not intentionally saved. Flask may spool larger uploads to temporary OS files for the request lifetime.
- Per-user cooldown and three concurrent analysis slots for a single server process.

## Tests and engineering loop

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

We use a short loop: define a user-visible outcome, implement a small slice, run relevant tests, inspect the browser, fix failures, and record remaining limits. See `VERIFICATION.md` for this build's results.

The backend tests mock external identity verification and AI responses. They test authentication boundaries, PDF errors, evidence grounding, safe reports and provider failures. Actual Firebase emails, real accounts and real AI quality must be verified after credentials are connected.

## Deployment

`app.py` runs Waitress bound to `127.0.0.1`, suitable for local review. For an online deployment, use a Python host, HTTPS, environment secrets, an authorized Firebase domain and a production WSGI entry point (`app:app`). Add service-wide request quotas and isolated PDF processing before exposing the app to untrusted public traffic; current cooldown/concurrency controls are per-process. Configure the proxy's upload limit and analysis timeout. No deployment or paid services have been created.

## Files

- `app.py`: routes, identity verification, upload handling, limits.
- `analysis.py`: PDF extraction, AI schema, grounding checks and fictional sample.
- `reports.py`: in-memory PDF generation.
- `templates/index.html`, `static/style.css`, `static/app.js`: interface.
- `.env.example`: configuration template. Never commit `.env` or Admin credentials.

## Technology references

[Flask](https://flask.palletsprojects.com/), [Firebase token verification](https://firebase.google.com/docs/auth/admin/verify-id-tokens), [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output), [Pydantic](https://docs.pydantic.dev/), [pypdf](https://pypdf.readthedocs.io/), [ReportLab](https://docs.reportlab.com/), [Alpine.js](https://alpinejs.dev/).

Bundled assets: Alpine.js 3.14.9 (MIT) and Manrope (SIL Open Font License). License copies are in `static/vendor/`.

## Offer letter review

Select **Offer letter** before uploading. Gemini extracts quoted warning signs; unsupported excerpts are discarded. The app calculates a heuristic score from unique categories: upfront payment 45, check forwarding 60, sensitive credentials 50, unverified contact 10, pressure 10, conflicting details 15. Scores are capped at 100; 45+ is high risk. These are product heuristics, not statistically calibrated fraud probabilities. Rejected evidence makes the score unavailable. A zero score does not prove authenticity. The app does not verify employers, senders, domains, signatures or company registrations. Independently confirm offers with the employer. Background guidance: https://consumer.ftc.gov/articles/job-scams.

Reports support English, Hindi and Marathi explanations with unchanged source quotes. The offer assessment summary currently uses English. Noto Devanagari and HarfBuzz provide PDF text shaping.

Temporary provider errors use up to three attempts (primary, backup, primary), with short delays and 35-second request timeouts. `GEMINI_FALLBACK_MODEL` defaults to `gemini-3.1-flash-lite`. Language and review type stay the same across attempts. Quota and credential errors are not retried. Basic offer screening remains labelled if all AI attempts fail.

## Deploy to Vercel

Import `Anuj779/FieldProject`, branch `main`, using the Flask framework preset. The repository includes `vercel.json`, a Python 3.12 version file, and `build.py` to publish frontend assets under `public/static`. Maximum PDF upload size is 4 MB to stay within Vercel request limits.

Set these private server environment variables in Vercel before deploying:
- `GEMINI_API_KEY`: your Gemini key.
- `GEMINI_MODEL`: `gemini-3.5-flash-lite`.
- `GEMINI_FALLBACK_MODEL`: `gemini-3.1-flash-lite`.
- `FIREBASE_WEB_CONFIG`: the same single-line web configuration JSON used locally.
- `FIREBASE_ADMIN_CREDENTIALS`: the complete Firebase service-account JSON, stored as a sensitive environment variable. Do not commit this file or use a public/frontend environment variable.

Do not set the local Windows `GOOGLE_APPLICATION_CREDENTIALS` path on Vercel. Add the final deployment hostname to Firebase Authentication authorized domains. Redeploy after changing environment variables. Verify sign-in, authenticated upload, report language changes and PDF download on the deployed domain.

Limits: the current cooldown/concurrency controls are per process, so Vercel instances do not share them. They are not a global usage cap. Provider quotas still apply. Browser speech depends on available device voices; offer authenticity cannot be certified from a document alone. Public hosting and authenticated production uploads must be checked after deployment.
