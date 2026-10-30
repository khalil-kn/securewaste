# 01 — Requirements

| | |
|---|---|
| Project | SecureWaste — Sensitive Data Exposure Prevention Platform |
| Document status | Draft for Milestone 0 review |
| Owners | SecureWaste team (5 members) |
| Related | [Architecture](02-architecture.md) · [Interface contract](03-api.md) · [Threat model](04-threat-model.md) |

> **How to read this document.** Section 4 tells *who* uses the product, section 5 *what* they want (user stories), section 6 turns that into testable *requirements*, and section 8 says how we will know the MVP is done. Every requirement has an ID so code, tests, issues and pull requests can point back to it.

## 1. Problem statement

Organisations routinely share documents that contain confidential data: customer records, invoices, contracts, employee files, internal reports, identity numbers, and sometimes live API keys or passwords. Employees can send these documents to the wrong people by accident. Manual review before sharing is slow, inconsistent, and does not scale. Enterprise DLP suites solve this but are expensive, tied to a cloud ecosystem, and opaque to the small teams that most need simple help.

**SecureWaste** helps a user find potentially sensitive information in a document *before* sharing it, understand *why* it matters, see a documented risk estimate, and produce a sanitized copy.

## 2. Goals

| ID | Goal | Measured by |
|---|---|---|
| G-1 | Detect the MVP categories of sensitive data in TXT and text-based PDF files | Detection tests on a synthetic corpus pass (see §8) |
| G-2 | Explain every finding and the document's overall risk | Each finding has explanation + recommendation; the risk card lists weighted reasons |
| G-3 | Never become a leak itself | No raw sensitive value in DB, logs, HTML or reports (security tests ST-xx) |
| G-4 | Let a human stay in control | Every finding has a review status; nothing is deleted or shared automatically |
| G-5 | Produce redacted PDFs whose removed text cannot be recovered | Redaction verification test re-extracts text and finds 0 matches |
| G-6 | Be a credible, reproducible portfolio project | README setup works on a clean machine; CI is green; docs match the code |

## 3. Non-goals (for the MVP)

- Guaranteeing regulatory compliance (GDPR, PCI DSS, Tunisian Organic Law 2004-63, …).
- Scanning scanned/image-only PDFs (no OCR).
- Formats other than PDF and TXT (DOCX, XLSX, e-mail, images).
- Monitoring e-mail, chat, endpoints, network traffic or cloud storage. SecureWaste scans files a user chooses to upload.
- Blocking or sending documents. SecureWaste advises; it does not enforce.
- Multi-user accounts and role-based access control (planned, see *Future direction*).
- AI / machine-learning classification.
- Running as an internet-facing service.

## 4. Personas

| Persona | Role | Needs | Frustration today |
|---|---|---|---|
| **Sana** | IT administrator at a 40-person accounting firm | Check client files quickly before they leave the firm | No budget for an enterprise DLP suite |
| **Youssef** | Junior security analyst | Triage findings, dismiss false positives, keep a record | Regex scripts give raw matches with no context or history |
| **Leila** | Data-protection / compliance officer | An auditable report showing what was found and what was done | Reviews by hand are inconsistent and leave no trail |
| **Recruiter / reviewer** (secondary) | Evaluates the GitHub portfolio | Understand the problem, architecture and security controls in minutes | Student projects without docs or tests |

All personas are fictional.

## 5. User stories

Format: *As a ‹persona›, I want ‹capability› so that ‹benefit›.* Priority uses **MoSCoW**: **M**ust, **S**hould, **C**ould, **W**on't (this release).

| ID | User story | Priority | Milestone |
|---|---|---|---|
| US-01 | As Sana, I want to upload a PDF or TXT file and see the accepted formats and size limit, so that I know what I can scan. | M | M1 |
| US-02 | As Sana, I want clear error messages when a file is rejected (wrong type, too big, malformed, empty), so that I can fix the problem. | M | M1 |
| US-03 | As Sana, I want the document scanned automatically after upload, so that I get results without extra steps. | M | M1 |
| US-04 | As Youssef, I want findings for e-mail addresses, phone numbers and configurable keywords, so that obvious personal data is surfaced. | M | M1 |
| US-05 | As Youssef, I want payment-card numbers validated with the Luhn checksum and IBANs with mod-97, so that random digit strings are not reported as high-severity. | M | M2 |
| US-06 | As Youssef, I want API keys, tokens and private-key blocks detected, so that leaked credentials can be rotated. | M | M2 |
| US-07 | As Leila, I want confidentiality labels (CONFIDENTIAL, INTERNAL, RESTRICTED) detected, so that labelled documents are not shared by mistake. | M | M2 |
| US-08 | As Youssef, I want every finding to show category, page, masked value, confidence, severity, explanation and recommendation, so that I can judge it without seeing the raw value. | M | M2 |
| US-09 | As Sana, I want an overall risk level with the reasons that produced it, so that I can decide quickly whether a document is safe to share. | M | M2 |
| US-10 | As Sana, I want my scans saved so that I can come back to previous results. | M | M3 |
| US-11 | As Sana, I want a dashboard with totals, risk distribution, findings by category, recent scans and unresolved findings, so that I see the overall situation at a glance. | M | M3 |
| US-12 | As Youssef, I want a document detail page with findings grouped by category, so that I can review one document thoroughly. | M | M3 |
| US-13 | As Youssef, I want to mark a finding as confirmed, false positive or resolved (with an optional note), so that the record reflects human judgement. | M | M4 |
| US-14 | As Sana, I want to delete a document together with its findings and generated files, so that sensitive files are not kept longer than needed. | M | M3 |
| US-15 | As Leila, I want important actions (upload, scan, review, redaction, report, deletion) recorded in an audit log without sensitive values, so that there is an accountable trail. | M | M4 |
| US-16 | As Youssef, I want to filter scan history and findings by severity, category, review status and date, so that I can focus on what matters. | S | M3 |
| US-17 | As Sana, I want to select findings and generate a redacted copy of a PDF whose removed text cannot be recovered, so that I can share a safe version. | S | M4 |
| US-18 | As Sana, I want to be told when a finding cannot be mapped to a location in the PDF, so that I never trust an incomplete redaction. | S | M4 |
| US-19 | As Leila, I want a printable HTML report of a scan (counts, risk explanation, statuses, redaction history), so that I can attach it to a review. | S | M4 |
| US-20 | As Youssef, I want a configurable national-ID rule (first: Tunisian CIN, only with nearby context words), so that local identifiers are detected without flooding false positives. | S | M2 |
| US-21 | As Sana, I want to re-scan a document after rules change, so that results reflect the current rule set. | S | M4 |
| US-22 | As a developer, I want to run the whole app with one Docker command, so that a demo is reproducible. | C | M5 |
| US-23 | As Youssef, I want passport-number rules for selected countries (context-gated), so that travel documents are flagged. | C | M5 |
| US-24 | As Leila, I want to download the report as PDF. | C | M5 |
| US-25 | As an organisation, I want user accounts with roles and per-user document separation. | W | Future |
| US-26 | As Sana, I want scanned (image) PDFs processed with OCR. | W | Future |
| US-27 | As Youssef, I want AI-assisted classification of document sensitivity. | W | Future |

## 6. Functional requirements

### 6.1 Upload & validation

| ID | Requirement | Story |
|---|---|---|
| FR-01 | The system shall accept `.pdf` and `.txt` uploads through a web form and display the accepted formats and maximum size. | US-01 |
| FR-02 | The system shall reject files larger than `MAX_UPLOAD_MB` (default **10 MB**) with HTTP 413 and a readable message. | US-02 |
| FR-03 | The system shall determine the real type from content: PDF must start with `%PDF-` and open with PyMuPDF; TXT must decode as UTF-8 (BOM allowed) and contain no NUL bytes. The extension and browser MIME type are never trusted alone. | US-02 |
| FR-04 | The system shall reject PDFs that are encrypted, malformed, have more than `MAX_PDF_PAGES` (default **100**) pages, or contain no extractable text (likely scanned), each with a distinct error code. | US-02 |
| FR-05 | The system shall store each upload under a random server-generated name (`<uuid4>.<ext>`) in a storage directory outside the static web folder. The original filename is kept only as sanitized display text. | US-01 |
| FR-06 | The system shall compute and store the SHA-256 hash of each upload. | US-15 |

### 6.2 Extraction & detection

| ID | Requirement | Story |
|---|---|---|
| FR-07 | The system shall extract text page by page (TXT = one page) and keep the page number for every finding. Extraction stops at `MAX_EXTRACTED_CHARS` (default 2,000,000) with a warning. | US-03 |
| FR-08 | The detection engine shall run every enabled rule; each rule returns candidate findings with category, page, character offsets, confidence (0–1) and the rule ID. | US-04 |
| FR-09 | MVP rules: e-mail, phone-number-like, configurable keywords (M1); payment card + Luhn, IBAN + mod-97, secrets/tokens, confidentiality labels (M2); national ID (TN CIN, context-gated) (M2, Should). | US-04–07, US-20 |
| FR-10 | Confidence shall be raised by successful validation or context words and lowered by failed validation; candidates below `MIN_CONFIDENCE` (default 0.30) are discarded. Confidence is shown as *Low / Medium / High*. | US-05 |
| FR-11 | Duplicate matches of the same value by the same rule on the same page shall be merged into one finding with an occurrence count. | US-08 |
| FR-12 | Every finding shall carry a severity derived from its category and validation result, an explanation and a recommendation from the rule catalogue. | US-08 |
| FR-13 | Values shall be masked before they leave the detection engine (e.g. card `•••• •••• •••• 4242`, e-mail `s•••@e•••.tn`, secret `AKIA••••••••`). Context snippets are at most 30 characters each side, with every detected value inside them masked. | US-08 |

### 6.3 Risk assessment

| ID | Requirement | Story |
|---|---|---|
| FR-14 | The risk engine shall compute a 0–100 score from category weights, confidence, repetition, label presence and category combinations, as documented in [Architecture §8](02-architecture.md#8-risk-scoring-model). | US-09 |
| FR-15 | The score shall map to *informational / low / medium / high / critical* using configurable thresholds; certain findings enforce a floor: a high-confidence secret makes the document at least *critical*, a Luhn-valid card at least *high*. | US-09 |
| FR-16 | The system shall show the list of weighted reasons behind the score and label it "application-defined risk estimate". | US-09 |
| FR-17 | Findings marked *false positive* shall be excluded and the risk recalculated. | US-13 |

### 6.4 Persistence, dashboard & review

| ID | Requirement | Story |
|---|---|---|
| FR-18 | The system shall persist documents, scan jobs, findings, review actions, redactions and audit events in SQLite with foreign keys enabled. | US-10 |
| FR-19 | The dashboard shall show total documents, total findings, documents per risk level, findings per category, recent scans and unresolved findings. | US-11 |
| FR-20 | The scan history shall support filters on severity, category, review status and date range. | US-16 |
| FR-21 | The document page shall show metadata, scan status, risk card and findings grouped by category with severity, confidence, page, masked value, recommendation and review status. | US-12 |
| FR-22 | A reviewer shall be able to move a finding between *open*, *confirmed*, *false positive* and *resolved* following the state machine in [Architecture §6](02-architecture.md#6-state-machines); each change is stored as a review action. | US-13 |
| FR-23 | Deleting a document shall remove its stored file, redacted copies, scans and findings, and write an audit event that contains no filename or content. | US-14 |
| FR-24 | The system shall record audit events for: upload, scan completed/failed, review change, redaction created, report generated, document deleted. | US-15 |

### 6.5 Redaction & reporting

| ID | Requirement | Story |
|---|---|---|
| FR-25 | For PDFs, the user shall select findings to redact; the system shall locate each value on its page, apply genuine redactions (content removed, not covered), strip document metadata, and save a new file named `<original-stem>__SANITIZED.pdf`. The original is preserved. | US-17 |
| FR-26 | After redaction the system shall re-extract the text of the sanitized file and re-run the selected rules; the redaction is marked *verified* only if no selected value remains. | US-17 |
| FR-27 | Findings that cannot be located in the PDF shall be listed as *unmappable* and the redaction marked *incomplete*; the UI must show this. | US-18 |
| FR-28 | The system shall generate an HTML report per scan with metadata, timestamp, categories, counts by severity, risk score and explanation, recommendations, review statuses and redaction history, containing only masked values. | US-19 |
| FR-29 | The user shall be able to re-scan a document; this creates a new scan job and keeps the previous one. | US-21 |

## 7. Non-functional requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Security | No raw sensitive value is written to the database, logs, HTML responses, reports or audit events. Only masked values and keyed hashes (HMAC-SHA256) are stored. |
| NFR-02 | Security | All state-changing requests use POST/PATCH/DELETE with a valid CSRF token; cookies are `HttpOnly` and `SameSite=Lax`. |
| NFR-03 | Security | Responses carry a strict Content-Security-Policy, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and frame-blocking headers. Jinja2 auto-escaping stays on. |
| NFR-04 | Security | The development server binds to `127.0.0.1` by default; debug mode is off unless explicitly enabled; the secret key comes from the environment. |
| NFR-05 | Security | All SQL uses parameterised queries. |
| NFR-06 | Performance | A 10-page text PDF (≈ 30 KB of text) is scanned in under **3 s** on a typical student laptop. |
| NFR-07 | Reliability | A malformed file never crashes the app; it produces a *failed* scan with an error code and the temporary files are removed. |
| NFR-08 | Maintainability | Business logic lives in plain Python modules (no Flask imports) under `securewaste/core/`; route handlers stay thin. |
| NFR-09 | Testability | Line coverage ≥ **80 %** for `core/detection`, `core/risk`, `core/redaction`; CI runs on every pull request. |
| NFR-10 | Usability / accessibility | Responsive from 390 px to desktop; WCAG 2.1 AA contrast; every control reachable by keyboard; severity never conveyed by colour alone. |
| NFR-11 | Portability | Runs on Windows, macOS and Linux with Python 3.12; no external services required. |
| NFR-12 | Privacy | Only synthetic test data in the repository; `gitleaks` or equivalent check before release. |
| NFR-13 | Transparency | The rule catalogue (patterns, weights, explanations) is documented and versioned (`RULESET_VERSION`), and each scan stores the version used. |
| NFR-14 | Data retention | Originals and sanitized copies are kept until the user deletes them; there is no hidden copy. Retention is described in the README. |

## 8. MVP acceptance criteria

The MVP (end of Milestone 4) is accepted when **all** of the following are demonstrated on the synthetic demo corpus:

1. Uploading `tests/fixtures/invoice_with_card.pdf` (3 pages) produces findings for the e-mail, phone, Luhn-valid card and IBAN it contains, each with the correct page number.
2. A 16-digit number that fails Luhn is **not** reported as a payment card (or is reported as Low confidence, never High severity).
3. A synthetic AWS-style access key in `tests/fixtures/config_leak.txt` produces a *critical* risk level with "credential exposed" in the explanation.
4. Uploading a renamed `.exe` as `.pdf`, an 11 MB file, an empty file and an encrypted PDF each returns its documented error, and no file remains in the storage folder.
5. Marking the card finding *false positive* lowers the score and the new explanation no longer mentions it.
6. Redacting the card and IBAN produces `invoice_with_card__SANITIZED.pdf`; `pytest tests/redaction` proves that text extraction of the copy finds neither value, and the original file is unchanged (same SHA-256).
7. The HTML report and the database contain no unmasked card number, IBAN or secret (checked by an automated test that greps the DB file, logs and report).
8. Deleting the document removes its files, scans and findings; an audit event "document.deleted" remains.
9. `pytest` passes in CI with ≥ 80 % coverage on core modules; the README instructions work on a clean Windows machine.

## 9. Out of scope (this release)

Authentication and RBAC, OCR, non-PDF/TXT formats, AI classification, e-mail/endpoint/cloud integrations, automatic blocking or sharing, internet deployment, PDF reports (Could), and formal accuracy benchmarking beyond the synthetic corpus.

## 10. Future direction

Stretch ideas that are **not** committed. They are listed so the design can leave room for them.

- **Accounts and roles** (admin, analyst, viewer) with per-user document separation, password hashing (Argon2/scrypt) and login rate limiting.
- **Background scanning** with a job queue so large files do not block a request.
- **OCR** for scanned PDFs (e.g. Tesseract), only after measuring how often it is needed.
- **More formats**: DOCX, XLSX, CSV, e-mail (.eml).
- **Contextual / AI-assisted classification** (public / internal / confidential), preferably with local inference, evaluated against the rule-based baseline using precision, recall and false-positive rate.
- **Detection accuracy benchmark** with a labelled synthetic corpus.
- **Integrations**: CLI or pre-commit mode, REST API for other tools.
- **PostgreSQL** for multi-user deployments.
