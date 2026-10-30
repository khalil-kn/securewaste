# SecureWaste — Sensitive Data Exposure Prevention Platform

> Find sensitive information in a document **before** you share it, understand the risk, and produce a safely redacted copy.

![Status](https://img.shields.io/badge/status-Milestone%200%20%E2%80%94%20design-blue)
![Python](https://img.shields.io/badge/python-3.12-informational)
![License](https://img.shields.io/badge/license-AGPL--3.0%20(proposed)-lightgrey)

SecureWaste is a local web application inspired by **Data Loss Prevention (DLP)** tools. A user uploads a PDF or TXT file; the application extracts its text, detects potentially sensitive data (emails, phone numbers, payment cards, IBANs, API keys, confidentiality labels, configurable identifiers and keywords), validates candidates where possible (Luhn, IBAN mod-97), scores the document's risk with an explainable rule-based model, and lets a reviewer confirm findings, dismiss false positives, and generate a **truly redacted** PDF copy.

It is an educational, team-built portfolio project. It is **not** a certified enterprise DLP product.

## Why

People share contracts, invoices, HR files and reports every day. Hidden inside them are card numbers, ID numbers or live API keys. Manual review is slow and inconsistent. SecureWaste gives a fast, explainable second pair of eyes — and shows each finding with a masked value, a reason, and a recommended action, so a human stays in charge of the decision.

## What the MVP does

| Step | What happens |
|---|---|
| 1. Upload | PDF/TXT only, size and page limits, real format check (magic bytes), safe server-side name |
| 2. Extract | Page-aware text extraction with PyMuPDF (text-based PDFs only, no OCR) |
| 3. Detect | Modular rules: regex + validators (Luhn, IBAN) + context keywords → findings with confidence |
| 4. Assess | Weighted, explainable risk score (0–100) → informational / low / medium / high / critical |
| 5. Review | Mark each finding *confirmed*, *false positive* or *resolved*; risk is recalculated |
| 6. Redact | Genuine PDF redaction, then re-extraction to verify nothing is recoverable |
| 7. Report | Printable HTML report with masked values only, plus an audit trail |

## Tech stack

| Layer | Choice | Why (see [ADRs](docs/adr/README.md)) |
|---|---|---|
| Language | Python 3.12 | Rich security and document libraries; readable for a learning team |
| Web framework | Flask 3 (server-rendered Jinja2 templates) | Small, explicit, easy to reason about ([ADR-0002](docs/adr/0002-flask-server-rendered-ui.md)) |
| PDF processing | PyMuPDF | Text extraction with positions **and** real redaction ([ADR-0004](docs/adr/0004-pymupdf-for-extraction-and-redaction.md)) |
| Detection | `re` + validator functions + rule config | Transparent, testable baseline ([ADR-0005](docs/adr/0005-rule-based-detection-baseline.md)) |
| Database | SQLite via Python's `sqlite3` | Zero setup, real SQL, foreign keys ([ADR-0003](docs/adr/0003-sqlite-with-plain-sql.md)) |
| Frontend | HTML, CSS, vanilla JavaScript | No build step; design tokens from the Figma design system |
| CSRF / forms | Flask-WTF | Proven CSRF protection instead of hand-rolled tokens |
| Tests | pytest (+ pytest-cov) | De-facto Python standard |
| CI | GitHub Actions | Runs tests and `pip-audit` on every pull request |
| Packaging | Docker (Milestone 5) | Reproducible demo environment |

## Documentation

| Document | Contents |
|---|---|
| [Requirements](docs/01-requirements.md) | Problem, goals, personas, user stories (US-xx, MoSCoW), FR/NFR, acceptance criteria |
| [Architecture](docs/02-architecture.md) | Context, components, deployment, sequences, state machines, data model, modules |
| [Interface contract](docs/03-api.md) | Every HTTP route and JSON endpoint, written before code |
| [Threat model](docs/04-threat-model.md) | Assets, trust boundaries, STRIDE, residual risks, security test cases |
| [Decisions (ADRs)](docs/adr/README.md) | Why each key technical choice was made |
| [Diagrams](docs/diagrams/README.md) | PlantUML sources, SVG exports, editable draw.io files |
| [Learning guide](docs/guides/learning-guide.md) | Every concept in this package, explained from zero |
| [Git workflow guide](docs/guides/git-workflow.md) | How the team works with Git and GitHub |
| [Cahier des charges](docs/cahier-des-charges/SecureWaste-Cahier-des-charges.pdf) | Academic requirements specification ([Word version](docs/cahier-des-charges/SecureWaste-Cahier-des-charges.docx)) |
| [Milestone 1 issues](docs/guides/milestone-1-issues.md) | The first five GitHub issues, ready to paste |
| [Contributing](CONTRIBUTING.md) | Issue → branch → PR → squash merge, commit style, Definition of Done |

![Component diagram](docs/diagrams/svg/component.svg)

## Roadmap

| Milestone | Goal | Status |
|---|---|---|
| **M0 — Foundations on paper** | Requirements, architecture, threat model, ADRs, diagrams, repo workflow | ✅ this package |
| **M1 — Walking skeleton** | Flask app, validated upload, TXT/PDF extraction, email/phone/keyword rules, tests, CI | 🚧 skeleton, schema and CI in place; features in progress |
| **M2 — Detection & risk engine** | All MVP rules with validators, masking, confidence, explainable risk score | |
| **M3 — Persistence & dashboard** | SQLite schema, scan history, dashboard, document details, filters | |
| **M4 — Review & remediation** | Review states, recommendations, verified PDF redaction, HTML report, audit log | |
| **M5 — Hardening & release** | Security review, upload/abuse tests, retention, Docker, demo with fictional documents | |
| **Future direction** | Authentication & RBAC, OCR, more formats, contextual/AI-assisted classification, accuracy benchmark | |

## Running locally

```bash
git clone https://github.com/<your-username>/securewaste.git
cd securewaste
python -m venv .venv
source .venv/Scripts/activate        # Git Bash on Windows (Linux/macOS: source .venv/bin/activate)
pip install -r requirements-dev.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"   # run twice: paste into SECUREWASTE_SECRET_KEY and SECUREWASTE_HMAC_KEY in .env
flask --app securewaste init-db      # creates instance/securewaste.db
flask --app securewaste run          # http://127.0.0.1:5000 — /healthz answers {"status": "ok"}
pytest                               # all tests should pass
```

The app refuses to start while either key is missing or still a placeholder. That is deliberate.

### Where things go

| Folder | Contains | Owner |
|---|---|---|
| `securewaste/web/` | Flask routes (one blueprint per file), security middleware, templates, static files | Routes: feature authors · `security.py`: tech lead |
| `securewaste/services/` | One function per use case (scan, review, redaction, audit) | Feature authors |
| `securewaste/core/` | Pure logic: upload validation, extraction, detection, risk, redaction. No Flask imports | Contracts: tech lead · logic: feature authors |
| `securewaste/db/` | `schema.sql`, connection handling, repositories (all SQL) | Schema: tech lead · repositories: feature authors |
| `tests/` | `unit/`, `integration/`, `security/`, `fixtures/` (synthetic data only) | Everyone |

See [CONTRIBUTING.md](CONTRIBUTING.md#roles-the-tech-lead-owns-the-structure-everyone-owns-a-module) for who changes what.

## Team

Built by a team of five computer-science students specialising in cybersecurity. Names and roles: *to be completed*.

## Disclaimer

SecureWaste is an **educational portfolio project**. Detection is heuristic: it produces *potential* findings that a human must review, it will miss some sensitive data (false negatives) and flag some harmless data (false positives). The risk score is an **application-defined estimate**, not a standardised or regulatory score. Using SecureWaste does not make an organisation compliant with GDPR, PCI DSS, Tunisia's Organic Law 2004-63 or any other regulation. Use only synthetic or properly authorised documents. Never upload real customer data to a demo instance.

## License

Proposed: **GNU AGPL-3.0**, because PyMuPDF is distributed under AGPL-3.0 (see [ADR-0004](docs/adr/0004-pymupdf-for-extraction-and-redaction.md)). The team must confirm this before the first release and add a `LICENSE` file.
