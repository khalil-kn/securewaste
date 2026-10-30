# Milestone 1 — first five issues (ready to paste)

Issues #1 and #2 are the **tech lead's skeleton PR** and are already implemented in the package (see [git-workflow.md §4.8](git-workflow.md#48-tech-lead-merge-the-skeleton-before-anyone-else-codes)). Create them anyway and close them with that PR, so the history shows who built what. Issues #3–#5 are the first feature work for the other teammates: each fills in stub files whose signatures are already written. The fourth teammate can pair on #3, the most security-sensitive one.

To create one from Git Bash with the GitHub CLI instead of the web page:

```bash
gh issue create --title "chore: project skeleton with Flask app factory, config and pytest" \
  --label "type: task" --label "priority: must" --milestone "M1 — Walking skeleton" \
  --body-file issue-1.md
```

---

## Issue 1 — `chore: project skeleton with Flask app factory, config and pytest`

**Labels:** type: task · priority: must · **Milestone:** M1 · **Assignee:** tech lead · **Status:** delivered by the skeleton package

**What needs to be done**
Create the package layout from [Architecture §9](../02-architecture.md#9-module-structure) with an application factory, configuration from environment variables, and a test setup.

**Done when**
- [ ] `securewaste/__init__.py` exposes `create_app(test_config=None)`
- [ ] `config.py` reads `.env` (python-dotenv) and **refuses to start** if `SECUREWASTE_SECRET_KEY` or `SECUREWASTE_HMAC_KEY` is missing
- [ ] `GET /healthz` returns `{"status": "ok"}`
- [ ] `flask --app securewaste run` binds to `127.0.0.1` by default
- [ ] `requirements.txt` (Flask, Flask-WTF, PyMuPDF, python-dotenv) and `requirements-dev.txt` (pytest, pytest-cov, ruff, pip-audit) with pinned versions
- [ ] `tests/conftest.py` provides an `app` and `client` fixture using a temporary `instance/` folder
- [ ] `pytest` passes with at least one test for `/healthz` and one for the missing-key refusal
- [ ] README "Running locally" commands work on Windows/Git Bash

---

## Issue 2 — `ci: run pytest and pip-audit on every pull request`

**Labels:** type: task · priority: must · **Milestone:** M1 · **Assignee:** tech lead · **Status:** delivered by the skeleton package

**Done when**
- [ ] `.github/workflows/ci.yml` runs on `pull_request` and `push` to `main`
- [ ] Steps: checkout → set up Python 3.12 → `pip install -r requirements-dev.txt` → `ruff check` → `pytest --cov=securewaste` → `pip-audit`
- [ ] Test secrets come from workflow `env:` with dummy values (never real keys)
- [ ] A test PR shows a green check; branch protection on `main` now requires this check

---

## Issue 3 — `feat: validated PDF/TXT upload stored outside the web root`

**Labels:** type: feature · priority: must · security · **Milestone:** M1 · **Depends on:** #1

**User story:** As Sana, I want to upload a PDF or TXT file and get clear errors when it is rejected, so that I know what I can scan. (US-01, US-02 · FR-01 → FR-06)

**Acceptance criteria**
- [ ] `GET /upload` shows accepted types and the size limit
- [ ] `POST /documents` with CSRF token; `MAX_CONTENT_LENGTH` from `MAX_UPLOAD_MB`
- [ ] `core/upload.py` decides the type from content: `%PDF-` + PyMuPDF opens it; TXT = UTF-8 (BOM allowed) and no NUL bytes
- [ ] Error codes from [03-api.md](../03-api.md#error-format): `FILE_TOO_LARGE`, `UNSUPPORTED_TYPE`, `EMPTY_FILE`, `MALFORMED_PDF`, `PDF_ENCRYPTED`, `TOO_MANY_PAGES`, `NOT_UTF8`
- [ ] Stored as `instance/storage/originals/<uuid4>.<ext>`; resolved path checked to stay inside `STORAGE_DIR`; display name escaped
- [ ] SHA-256 computed
- [ ] Temporary files removed on every failure path
- [ ] Security tests ST-03, ST-04, ST-14, ST-15 implemented in `tests/security/`

**Where:** implement `validate_upload()` in `securewaste/core/upload.py` (dataclasses `Limits` and `ValidatedUpload` are already defined), add the routes to `securewaste/web/routes_documents.py`, raise `UploadRejected(code)` from `core/errors.py`.

**Notes:** the tables exist (`db/schema.sql`) but repositories arrive in M3 — return the validated metadata as JSON or keep it in memory until then.

---

## Issue 4 — `feat: page-aware text extraction for PDF and TXT`

**Labels:** type: feature · priority: must · **Milestone:** M1 · **Depends on:** #1

**User story:** As Sana, I want the document scanned automatically after upload so that I get results without extra steps. (US-03 · FR-07)

**Acceptance criteria**
- [ ] `extract_pages(path, file_type, limits) -> list[PageText]` in `core/extraction.py`
- [ ] TXT = one page; PDF = one `PageText` per page with 1-based `page_number`
- [ ] PDF with no extractable text raises `ExtractionFailed("NO_TEXT_LAYER")`
- [ ] Extraction stops at `MAX_EXTRACTED_CHARS` with a warning flag
- [ ] `scripts/make_fixtures.py` generates a synthetic 3-page PDF and a TXT (fictional data only); tests use them
- [ ] No extracted text is ever logged

**Where:** `extract_pages()` in `securewaste/core/extraction.py` (`PageText` is already defined); raise `ExtractionFailed` from `core/errors.py`.

---

## Issue 5 — `feat: first detection rules — e-mail, phone, keywords — with masking`

**Labels:** type: feature · priority: must · **Milestone:** M1 · **Depends on:** #4

**User story:** As Youssef, I want findings for e-mail addresses, phone numbers and configurable keywords, so that obvious personal data is surfaced. (US-04 · FR-08, FR-11, FR-13)

**Acceptance criteria**
- [ ] `DetectionRule` base class + `EmailRule`, `PhoneRule`, `KeywordRule` (keywords from `SECUREWASTE_KEYWORDS`)
- [ ] `masking.py`: e-mail `s•••@e•••.tn`, phone keeps last 2 digits, keyword shown as is; `value_hmac` with `SECUREWASTE_HMAC_KEY`
- [ ] Duplicates of the same value/rule/page merged with an `occurrences` count
- [ ] Each rule has positive, negative and edge-case unit tests (e.g. `name@sub.example.tn`, `not-an-email@`, phone with spaces/dots, keyword inside another word)
- [ ] Upload of the fixture TXT returns the expected findings, masked, with page numbers
- [ ] Test asserts no raw fixture value appears in the response or captured logs (start of ST-01)

**Where:** `Finding` and `Candidate` already exist in `core/detection/models.py`; subclass `DetectionRule` from `core/detection/rules/base.py`; fill in `engine.py` and `masking.py`; use `CATALOGUE` for severity, explanation and recommendation.
