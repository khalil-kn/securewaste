# Architecture Decision Records

An **ADR** is a short document that captures one important technical decision: the situation (*context*), what we chose (*decision*), what else we considered (*alternatives*), and what follows from it (*consequences*, good **+** and bad **−**).

## Rules

1. One decision per file, named `NNNN-kebab-case-title.md`, numbered in order.
2. Copy [template.md](template.md) and open it in the **same pull request** as the change it justifies.
3. Status: `Proposed` → `Accepted` (after PR review) → possibly `Superseded by ADR-NNNN` or `Deprecated`.
4. Never rewrite an accepted ADR's decision. Write a new ADR that supersedes it.

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-flask-server-rendered-ui.md) | Flask with server-rendered pages and vanilla JavaScript | Accepted |
| [0003](0003-sqlite-with-plain-sql.md) | SQLite through Python's sqlite3 with plain SQL | Accepted |
| [0004](0004-pymupdf-for-extraction-and-redaction.md) | PyMuPDF for PDF extraction and redaction | Accepted (licence decision pending) |
| [0005](0005-rule-based-detection-baseline.md) | Rule-based detection with validators as the baseline | Accepted |
| [0006](0006-store-masked-values-and-keyed-hashes.md) | Store masked values and keyed hashes, never raw values | Accepted |
| [0007](0007-synchronous-scan-with-job-states.md) | Synchronous scanning with persisted job states | Accepted |
| [0008](0008-explainable-additive-risk-score.md) | Explainable additive risk score | Accepted |
| [0009](0009-verified-true-redaction.md) | True redaction verified by re-extraction | Accepted |
| [0010](0010-single-local-user-mvp.md) | Single local user in the MVP; authentication deferred | Accepted |
