# 04 — Threat model

| | |
|---|---|
| Document status | Draft for Milestone 0 — revisit at the end of every milestone |
| Method | Data-flow based, **STRIDE** per element, then risk = likelihood × impact |
| Related | [Architecture](02-architecture.md) · [Requirements](01-requirements.md) |

> **Why a security tool needs a threat model.** SecureWaste holds exactly the data it is meant to protect. If it leaks a card number through a log line or a "redacted" PDF, it has made things worse. The threat model answers four questions: *What are we building? What can go wrong? What are we doing about it? Did we do a good job?*

## 1. Scope and assumptions

- MVP runs on a single trusted computer, bound to `127.0.0.1`, used by one person.
- The operating system account running SecureWaste is trusted; full-disk encryption is the user's responsibility.
- **Uploaded files are untrusted**: they may be malformed or deliberately malicious.
- Dependencies come from PyPI and are pinned; the supply chain is partly trusted (monitored with `pip-audit`).
- Out of scope: physical attacks, a compromised OS, internet exposure (explicitly unsupported in the MVP).

## 2. Assets

| ID | Asset | Why it matters | Where |
|---|---|---|---|
| A1 | Original uploaded documents | Contain the sensitive data | `instance/storage/originals/` |
| A2 | Sanitized copies | Users will share them believing they are safe | `instance/storage/sanitized/` |
| A3 | Findings (masked values, hashes, context) | Reveal *where* sensitive data is and partial values | SQLite |
| A4 | Audit trail | Accountability, evidence of review | SQLite |
| A5 | Secret keys (`SECUREWASTE_SECRET_KEY`, `SECUREWASTE_HMAC_KEY`) | Session/CSRF integrity; hash brute-force resistance | `.env` |
| A6 | Application availability | User needs a result before sharing | Flask process |
| A7 | Source repository and CI | Integrity of the code everyone runs | GitHub |

## 3. Trust boundaries

![Trust boundaries](diagrams/svg/trust-boundaries.svg)

| ID | Boundary | Crossing data |
|---|---|---|
| TB1 | Browser ⇄ Flask (HTTP on localhost) | Uploads, form posts, JSON, HTML responses |
| TB2 | Flask ⇄ **document parser** (PyMuPDF / MuPDF native code) | Untrusted bytes parsed by C code |
| TB3 | Flask ⇄ file storage | Originals, sanitized copies, temp files |
| TB4 | Flask ⇄ SQLite | Findings, audit events |
| TB5 | Developer machine ⇄ GitHub / CI | Source code, fixtures, dependency manifests |

## 4. STRIDE analysis

STRIDE = **S**poofing, **T**ampering, **R**epudiation, **I**nformation disclosure, **D**enial of service, **E**levation of privilege. Risk: L = likelihood, I = impact (Low/Med/High).

| ID | STRIDE | Element / boundary | Threat | L | I | Mitigation (requirement) | Test |
|---|---|---|---|---|---|---|---|
| T-01 | S | TB1 | A malicious web page makes the user's browser send a forged POST (CSRF) to delete documents or change review states | M | M | Flask-WTF CSRF tokens on every state change; `SameSite=Lax` cookie (NFR-02) | ST-06 |
| T-02 | S | TB1 | Another local user / LAN host reaches the app | L | H | Bind to `127.0.0.1`; refuse `0.0.0.0` unless `ALLOW_REMOTE=1` with a warning (NFR-04) | ST-12 |
| T-03 | T | TB3 | Path traversal via a crafted filename (`../../app.py`) overwrites files | M | H | Server-generated `uuid4` names; original name never used in paths; resolved path must stay under `STORAGE_DIR` (FR-05) | ST-03 |
| T-04 | T | A2 | "Redaction" only draws boxes; text still extractable | M | H | PyMuPDF `apply_redactions()`, metadata scrub, **re-extraction verification** (FR-25, FR-26) | ST-08 |
| T-05 | T | TB4 | SQL injection through filters or IDs | L | H | Parameterised queries only; whitelisted filter values (NFR-05) | ST-07 |
| T-06 | T | A7 | Malicious or vulnerable dependency | M | H | Pinned versions, `pip-audit` in CI, Dependabot alerts, minimal dependencies | CI |
| T-07 | R | A4 | A reviewer denies having marked a finding false positive | L | M | Append-only `review_actions` + audit events with timestamp and actor | ST-10 |
| T-08 | I | Logs | Raw values written to logs or error messages | M | H | No request bodies, text or raw matches in logs; typed errors with codes (NFR-01) | ST-01 |
| T-09 | I | A3 | Raw values stored in DB | M | H | Only masked values + HMAC (ADR-0006) | ST-01 |
| T-10 | I | TB1 | Stored XSS through filename, keyword or review note | M | M | Jinja2 autoescape, CSP `default-src 'self'` without inline script, notes as plain text (NFR-03) | ST-05 |
| T-11 | I | A2 | Sanitized PDF keeps metadata (author, title), annotations, or embedded files revealing data | M | M | `set_metadata({})`, remove XMP, drop annotations/attachments, `save(garbage=4, clean=True)` | ST-08 |
| T-12 | I | Context snippet | Snippet shows undetected sensitive data next to a finding | M | M | ±30 chars max, mask all detected values inside window; residual risk accepted (R-03) | ST-02 |
| T-13 | I | A3 | Brute-forcing `value_hmac` to recover short values (e.g. 8-digit IDs) | L | M | Keyed HMAC-SHA256; key outside DB; residual accepted if DB **and** key stolen (R-02) | — |
| T-14 | I | Browser | Clickjacking / caching of finding pages | L | L | `frame-ancestors 'none'`, `X-Frame-Options: DENY`, `Cache-Control: no-store` | ST-11 |
| T-15 | I | A7 | Real personal data or secrets committed as fixtures | M | H | Synthetic generator script only; `.gitignore`; gitleaks check before release (NFR-12) | CI |
| T-16 | D | TB1 | Huge upload exhausts memory/disk | M | M | `MAX_CONTENT_LENGTH`, page limit (FR-02, FR-04) | ST-04 |
| T-17 | D | TB2 | PDF bomb (huge decompressed streams, thousands of pages) | M | M | Page limit, extraction char cap, per-scan time budget; worker subprocess with timeout in *Future direction* | ST-09 |
| T-18 | D | Detection | Regex catastrophic backtracking (ReDoS) on crafted text | L | M | Patterns reviewed for nested quantifiers; bounded quantifiers; worst-case test strings | ST-13 |
| T-19 | E | TB2 | Memory-safety bug in MuPDF triggered by malicious PDF leads to code execution | L | H | Keep PyMuPDF updated; run as non-root (Docker, M5); OS sandbox/subprocess isolation as *Future direction* | — |
| T-20 | E | Config | Debug mode enabled → Werkzeug debugger allows code execution | L | H | `FLASK_DEBUG` off by default; startup refuses debug when not bound to localhost | ST-12 |
| T-21 | I/E | IDOR | Any user can open any document by ID | — | — | Not applicable while single-user; **becomes critical** when accounts are added: every query filtered by owner | Future |

## 5. Accepted residual risks

| ID | Risk | Why accepted now | Revisit when |
|---|---|---|---|
| R-01 | No authentication: anyone with access to the logged-in OS session can use the app | Single-user localhost MVP; documented in README | Accounts milestone |
| R-02 | If both the DB and `SECUREWASTE_HMAC_KEY` are stolen, short identifiers can be brute-forced from `value_hmac` | Needed to locate values for redaction without storing them | Before any shared deployment |
| R-03 | Context snippets may expose undetected sensitive text | Snippets are short and help review; can be disabled with `SHOW_CONTEXT=0` (Could) | After accuracy benchmark |
| R-04 | Originals are stored unencrypted at rest | Relies on OS disk encryption; app-level encryption adds key management complexity | Shared deployment |
| R-05 | Detection misses data (false negatives) | Inherent to pattern-based detection; disclaimer in UI and README | Accuracy benchmark / contextual detection |
| R-06 | Audit log can be edited by someone with file access | Local trust model | Production database / external log sink |
| R-07 | MuPDF parsing runs in the web process | Simplicity for MVP; limits reduce exposure | Background worker milestone |

## 6. Security test cases

| ID | Test | Expected result | Covers |
|---|---|---|---|
| ST-01 | Scan the fixture corpus, then grep the DB file, log output and generated report for each raw fixture value (card, IBAN, secret, CIN) | Zero matches | T-08, T-09 |
| ST-02 | Finding API response for a card finding | Only `masked_value` with last 4 digits; context masked | T-12 |
| ST-03 | Upload with filename `../../evil.pdf`, `C:\\x.pdf`, `<script>.pdf`, very long name | Stored as `uuid.pdf` inside `originals/`; display name escaped | T-03, T-10 |
| ST-04 | Upload 11 MB file; empty file | 413 `FILE_TOO_LARGE`; 422 `EMPTY_FILE`; `tmp/` empty afterwards | T-16 |
| ST-05 | Review note `<img src=x onerror=alert(1)>` then load details page | Rendered as text; CSP header present | T-10 |
| ST-06 | POST `/documents/{id}/delete` without CSRF token | 400 `CSRF_INVALID`; document still exists | T-01 |
| ST-07 | `GET /documents?risk=high' OR 1=1--` | 400 `BAD_REQUEST`; no SQL error | T-05 |
| ST-08 | Redact card + IBAN in fixture; extract text with PyMuPDF **and** `pdftotext`; inspect metadata | No selected value present; metadata empty; original hash unchanged | T-04, T-11 |
| ST-09 | Upload a 101-page PDF; a PDF with a 50 MB decompressed stream | 422 `TOO_MANY_PAGES`; scan fails cleanly within budget | T-17 |
| ST-10 | Change a finding status twice | Two `review_actions` rows and two audit events, ordered | T-07 |
| ST-11 | Check response headers on `/documents/{id}` | CSP, `X-Frame-Options: DENY`, `nosniff`, `no-store` | T-14 |
| ST-12 | Start app with debug on and host `0.0.0.0` without override | App refuses to start | T-02, T-20 |
| ST-13 | Run every rule against 100 KB adversarial strings (`aaaa…@`, long digit runs) | Each completes < 1 s | T-18 |
| ST-14 | Upload `.exe` renamed to `.pdf`; PDF renamed to `.txt` | 415 `UNSUPPORTED_TYPE` / type taken from content | FR-03 |
| ST-15 | Encrypted PDF | 422 `PDF_ENCRYPTED`, no partial data stored | FR-04 |

## 7. Review checklist per milestone

- [ ] New inputs listed and validated at the boundary?
- [ ] Any new place where raw values could be stored, logged or rendered?
- [ ] New dependency justified, pinned and `pip-audit` clean?
- [ ] New security test added to §6 and to `tests/security/`?
- [ ] Residual risks still acceptable?
