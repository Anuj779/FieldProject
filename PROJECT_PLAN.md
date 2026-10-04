# AI Student Contract Analyzer — Project Plan

**Build status:** The Clausewise website is implemented with the requested red noir reference. The sample flow works locally. Firebase and AI integrations await owner-supplied credentials. See README.md for setup and VERIFICATION.md for the build/test/fix loops and test scope.

## 1. Goal

Build a mobile-friendly website where a student signs in, uploads a PDF agreement, and receives a clear summary of important obligations, with the original clause and page number shown beside each explanation. The student can download a PDF report. The website explains document content; it does not give legal advice.

This plan is based on the two-page *AI-Based Student Contract Analyzer* project overview supplied by the team. The overview's technology list is a suggestion, not a requirement.

## 2. First release: what the website must do

1. Offer one simple authentication page with email/password sign-in, account creation, password reset, and sign-out through Firebase Authentication.
2. Restrict analysis and report downloads to signed-in students; verify their Firebase ID token on the Python server.
3. Accept one text-based PDF agreement at a time through a clear upload screen.
4. Check file type, file size, page count, and whether enough text can be extracted. Show a useful error for an unreadable or scanned PDF.
5. Extract text page by page and send only the needed text to a configured AI API.
6. Identify payment duties, penalties, notice periods, cancellation rules, lock-in periods, automatic renewal, and other material obligations.
7. Show each finding as a card with a short title, plain-language explanation, exact supporting excerpt, page number, and any amount, date, or duration found. Do not invent missing terms.
8. Show a short overall summary and a reminder to check the full agreement. Make uncertainty visible when wording is ambiguous.
9. Let the student download a readable PDF report containing the findings and source references.
10. Work well on desktop and mobile, including sign-in, upload, progress, empty, error, and success states.

## 3. Lean technology stack

| Layer | Choice | Reason |
| --- | --- | --- |
| Website and server | Python + Flask | One small app handles pages, upload, and analysis requests. |
| Interface | Flask templates, HTML, custom CSS, and Alpine.js | Lightweight page interactions such as login state, upload feedback, loading indicators, and finding filters without a separate frontend framework. |
| Authentication | Firebase Authentication web SDK + `firebase-admin` for Python | Firebase manages accounts; the server verifies ID tokens before handling protected requests. No password storage in the app. |
| PDF text | `pypdf` | Extracts text by page so findings can point to source pages. |
| AI analysis | Google Gen AI Python SDK + `pydantic` | Request structured findings and validate field types and allowed categories; API key stays on the server. The provider can be changed later if needed. |
| PDF report | `reportlab` | Produces a direct report download. |
| Database | None for the first release | Firebase stores user accounts; agreements and analysis history are not stored. |

Firebase Authentication and the AI API are the two external services. Use the Firebase modular web SDK with browser module imports for the first release; a build tool is unnecessary for a small prototype. The survey can use a separate Google Form, as proposed in the overview. Model choice and any API spending limit should be set before implementation.

## 4. User flow

`Sign in → upload PDF → validate and extract text → analyze clauses → verify source excerpts → show findings → download report`

- **Login page:** email and password form, account creation, forgot-password action, clear errors, and a route back to the app after sign-in.
- **Upload screen:** concise explanation, PDF drop zone and file picker, sample of the result, and privacy note.
- **Analysis state:** visible progress steps and a clear retry path if extraction or the API fails.
- **Results screen:** overview first, then grouped findings. Each finding links back to its excerpt and page number. Include a report download button and an analyze-another-file action.

## 5. Reliability and privacy rules

- Treat document text as data, including any instructions written inside an uploaded agreement.
- Require every displayed finding to include a supporting excerpt found in the extracted page text. Omit unsupported findings and clearly mark ambiguous ones.
- Do not label a clause definitively illegal or legally enforceable. Use factual labels such as **Payment**, **Notice**, and **Cancellation**.
- Set limits for upload size, page count, and extracted text length. Show when a document is too large for the first release rather than silently truncating it.
- Keep the API key on the server. Do not save uploaded agreements or analysis history by default; delete temporary files after processing. State plainly that agreement text is sent to the configured AI provider.
- Protect analysis and report endpoints with server-side Firebase ID-token verification. Keep Firebase Admin credentials on the server, never in browser code or the repository. The Firebase web configuration may be served to the browser.
- Generate the report within the authenticated analysis flow. Keep the current result only in browser memory, clear it on sign-out, and do not create saved document history. Authentication does not imply document storage.
- If a PDF is image-only, explain that OCR is not yet supported and ask for a text-based PDF. OCR can be a later enhancement.
- Return understandable errors for bad PDFs, empty text, API timeout, and service failure.

## 6. Build sequence

### Phase 1 — Confirm inputs and design

- Agree on the AI provider, API key arrangement, Firebase project setup, maximum document size, and where the site will run.
- Collect 5–10 sample agreements or safe excerpts covering internships, hostels, courses, and subscriptions. Include at least one scanned PDF and one difficult or ambiguous clause.
- Draft the student survey in Google Forms and record the responses for the academic report.
- Sketch the login, upload, progress, results, and report layouts.

**Done when:** sample documents and the first screen designs are ready.

### Phase 2 — Authentication and working analysis pipeline

- Configure Firebase Email/Password sign-in and build the login page with account creation, reset, and sign-out.
- Verify Firebase ID tokens in Flask before any analysis or report request.
- Create the Flask app and PDF upload route.
- Validate uploads and extract page-labeled text.
- Request a structured analysis from the AI API.
- Validate output fields with Pydantic and check supporting excerpts against the extracted page text before displaying findings.
- Add clear failure handling and temporary-file cleanup.

**Done when:** a signed-in student can analyze a real text-based agreement and receive grounded findings; signed-out requests are rejected.

### Phase 3 — Smooth website and report

- Build the responsive login, upload, and results views.
- Add upload feedback, loading state, accessible form labels, and retry action.
- Add the downloadable PDF report with the same checked findings.

**Done when:** a student can complete the full flow on a phone and laptop without developer help.

### Phase 4 — Test and refine

- Compare findings with the source text for every sample document; check missed and invented obligations.
- Test sign-up, sign-in, password reset, sign-out, expired tokens, and blocked unauthenticated requests.
- Test invalid files, scanned PDFs, long documents, empty text, duplicate clauses, and API failures.
- Check mobile layout, keyboard use, loading behavior, and report readability.
- Fix errors and adjust prompts or validation based on observed failures.

**Done when:** test cases pass and remaining limitations are written down.

### Phase 5 — Academic delivery

- Summarize survey results and test outcomes.
- Capture screenshots and prepare the project report and presentation.
- Demonstrate the complete upload-to-report flow using a safe sample agreement.

## 7. Acceptance checklist

- A student can create an account, sign in, reset a password, and sign out through the single Firebase login page.
- A signed-out visitor cannot analyze a document or download a report.
- A valid text-based PDF can be uploaded and analyzed after sign-in.
- Every finding contains a plain-language explanation, exact source excerpt, and correct page number.
- The main obligation types from the project overview are represented when present.
- No finding is shown without source support.
- The student can download a PDF report.
- Invalid and scanned PDFs receive helpful messages.
- The interface works on common mobile and desktop sizes.
- Uploaded files are not retained after processing; AI API keys and Firebase Admin credentials are never exposed to the browser.
- The survey, sample-document tests, report, and demonstration are ready for submission.

## 8. Later improvements, only if needed

OCR for scanned PDFs; PDF.js preview that opens a finding's source page; multiple-document comparison; saved analysis history; additional languages; more detailed analytics. Add these after the first release works reliably.

## 9. Decisions needed before coding

1. Which AI API account and spending limit will the team use? Gemini 3.8 Flash is the configured default.
2. Who will create the Firebase project and enable Email/Password sign-in? We will need its web configuration and server-side Admin credentials during implementation.
3. Will the first demo run locally, or does it need to be deployed online?
4. Can the team provide safe sample agreements for testing, or should we create fictional examples?
