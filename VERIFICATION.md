# Build / test / fix log

## Loop 1: Functional core

Implemented PDF validation, structured findings, exact source checks, authentication enforcement and in-memory report generation. Added a fictional sample path that explicitly identifies prepared output.

Tests caught an empty Firebase configuration being treated as ready (`all([])`). Fixed readiness checks to require every expected configuration field. Kept missing credentials and invalid sessions as explicit failures.

## Loop 2: Interface

Implemented the supplied red noir direction with crimson buttons, black surfaces, a pill navigation and Manrope typography. Built sign-in/account/reset modes, upload feedback, results filtering and clause expansion. Bundled Alpine.js and fonts locally.

Browser tests passed for the sample review, category filtering, expanded evidence, report download, account mode switching, missing-configuration state, invalid file feedback and 390px mobile overflow checks. No JavaScript page errors were observed. Upload layout checks use a simulated client identity; backend authentication is tested independently and has no bypass.

## Loop 3: Visual fixes

Visual inspection found a downloaded static bold font incorrectly labeled as a variable font, and a report finding split across pages. Replaced the website font with the actual variable file, added a regular report font, reduced the hero heading size and kept report findings together. Inspected the desktop/mobile pages and both report pages. Removed the duplicate native file-picker button.

## Verified

- 16 backend tests passed using pytest.
- Desktop (1440px) and mobile (390px) browser checks passed using Playwright/Chromium.
- Sample report downloads as a valid PDF; rupee glyph and escaped markup verified.
- Source excerpts with invented text or invalid page numbers are excluded.
- Scanned/empty, encrypted, malformed and excessive-page PDFs are rejected.
- Missing/forged authentication and provider failure states are handled.

## Animation update

Added native IntersectionObserver/WAAPI slide reveals, staggered content entry, floating document panels, 3D pointer hover, button shine, sticky navigation, expanding clause transitions and CSS scroll progress where supported. Motion respects the operating system's reduced-motion preference. `tests/motion.cjs` passed for normal animation, scroll-triggered entry, FAQ expansion, reduced-motion cancellation, mobile overflow and navigation. Existing browser interaction checks also passed after this change. No new frontend dependency was added.

## Requires owner configuration (live services)

**Gemini migration:** The app uses Google Gen AI SDK with `GEMINI_API_KEY` and default model `gemini-3.8-flash`. The supplied key is stored only in the ignored local `.env`; the previous OpenAI configuration has been removed. A live fictional sample analysis returned six grounded findings with zero rejected excerpts and generated a valid PDF. The provider rejected the older model for new users, and schema compatibility was corrected by sending an inline schema subset while retaining full local Pydantic validation.

All 19 backend tests pass, including response validation, truncated-output rejection and quota-error handling. Firebase account creation, password-reset delivery and real token verification remain unverified because Firebase is not configured. A full authenticated upload cycle still requires Firebase web configuration and server credentials.

This is a local prototype. OCR, saved histories, public deployment, survey collection and academic presentation are not included in this website build. No external accounts or paid infrastructure were created.

## Pre-push verification - 2026-10-05

20 backend tests pass. Desktop/mobile browser and motion checks pass with no JavaScript errors. Browser configuration is mocked so local credentials do not change test expectations. The valid sample PDF is accepted and consent enables analysis. Missing Firebase Admin credentials now produce a specific setup error instead of an instruction to sign in again. Firebase web configuration is saved locally; Admin credentials remain missing, so a live authenticated upload is not yet verified.

## Gemini availability repair

Gemini 3.8 Flash repeatedly returned 503. Live fictional offer testing with 3.5 Flash-Lite produced three grounded Marathi findings and a valid PDF. Backup 3.1 Flash-Lite returned seven grounded agreement findings. Configured the tested models with bounded transient-error failover; no billing changes.

## Vercel preparation - 2026-10-09

30 backend tests pass. Desktop/mobile browser checks pass. Firebase service credentials authenticated successfully; live Hindi analysis of the fictional offer produced three grounded findings with zero rejected excerpts and a valid PDF. Added private environment-variable credentials, 4 MB upload limits, Python 3.12 configuration and a CDN asset build. Production deployment and real-user sign-in/upload on Vercel are not yet verified. No secrets are included in the deployment source.

## Upload retry repair - 2026-10-12

32 backend tests passed. Invalid PDFs and failed analysis no longer consume the cooldown; successful analysis still does. File reselection resets the picker so the same PDF can be selected again. Added clear non-JSON hosting error messages. Browser upload regression verifies actual FormData PDF bytes, consent, hosting 413, same-file retry and inline results with mocked external services. Deployed URL was not provided, so production upload has not been verified.

## Document-specific report verification - 2026-10-19

Restored the missing local workspace from GitHub. Public production config and JavaScript at clausewise-bay.vercel.app were inspected. Removed the workspace demo action when a PDF is selected and explicitly labelled demo versus uploaded-file results. Upload responses now include the PDF SHA-256 fingerprint and analysis source; the browser rejects sample or mismatched responses. 33 backend tests passed, including distinct text, distinct report bytes, and distinct hashes for two PDFs with the same filename (AI/auth mocked). Browser upload tests reject injected sample responses and accept matching uploads. A new signed-in production AI run was not performed: local credentials were lost with the original folder.
