# 03 — Interface contract

| | |
|---|---|
| Document status | Draft for Milestone 0 — **written before any code** |
| Base URL (local) | `http://127.0.0.1:5000` |
| Related | [Requirements](01-requirements.md) · [Architecture](02-architecture.md) |

> **Why write this first?** The contract is a promise between the people who build pages and the people who build logic. Once it is agreed, both sides can work in parallel and tests can be written against it. Any change to this file goes through a pull request.

SecureWaste is mostly **server-rendered**: the browser asks for HTML pages and submits HTML forms. A few small **JSON endpoints** (`/api/…`) let vanilla JavaScript update parts of a page without reloading it.

## 1. Conventions

| Topic | Rule |
|---|---|
| IDs | Documents, scans, findings and redactions use UUIDv4 strings. Unknown or malformed IDs return **404** (never 500). |
| HTML forms | `POST` with `application/x-www-form-urlencoded` or `multipart/form-data`; successful writes answer **303 See Other** to a page (Post/Redirect/Get), so refreshing never resubmits. |
| JSON | `Content-Type: application/json; charset=utf-8`, `snake_case` keys, ISO-8601 UTC timestamps (`2026-11-03T09:15:00Z`). |
| CSRF | Every `POST`/`PATCH`/`DELETE` requires a CSRF token: hidden field `csrf_token` in forms, header `X-CSRFToken` for `fetch()`. Missing/invalid token → **400** `CSRF_INVALID`. |
| Masking | No response ever contains a raw detected value. Fields called `masked_value` and `context` are already masked. |
| Auth | MVP: single local user, no login. Every endpoint is listed with the permission it will need in the *Future direction* RBAC model. |
| Caching | Pages showing findings send `Cache-Control: no-store`. |

### Error format

HTML routes render an error page with a short message. JSON routes return:

```json
{ "error": { "code": "INVALID_TRANSITION", "message": "A resolved finding can only be reopened." } }
```

| HTTP | Code(s) | When |
|---|---|---|
| 400 | `CSRF_INVALID`, `BAD_REQUEST` | Missing token, malformed form/JSON |
| 404 | `NOT_FOUND` | Unknown ID or route |
| 409 | `INVALID_TRANSITION`, `NOT_A_PDF` | Review state machine violation; redaction requested on a TXT |
| 413 | `FILE_TOO_LARGE` | Body above `MAX_UPLOAD_MB` |
| 415 | `UNSUPPORTED_TYPE` | Content is neither PDF nor UTF-8 text |
| 422 | `EMPTY_FILE`, `MALFORMED_PDF`, `PDF_ENCRYPTED`, `TOO_MANY_PAGES`, `NO_TEXT_LAYER`, `NOT_UTF8` | File understood but unusable |
| 500 | `INTERNAL_ERROR` | Unexpected failure; response includes a `correlation_id`, never a stack trace |

## 2. HTML pages and form actions

| Method | Path | Purpose | Success | Errors | Future permission |
|---|---|---|---|---|---|
| GET | `/` | Dashboard: KPIs, risk distribution, findings by category, recent scans, unresolved findings | 200 | — | `view` |
| GET | `/upload` | Upload form showing accepted types and limits | 200 | — | `upload` |
| POST | `/documents` | Upload **and scan** a file (`multipart/form-data`, field `file`) | 303 → `/documents/{id}` | 400, 413, 415, 422 | `upload` |
| GET | `/documents` | Scan history with filters (§2.1) and pagination | 200 | 400 on bad filter values | `view` |
| GET | `/documents/{document_id}` | Details: metadata, latest scan, risk card, findings grouped by category | 200 | 404 | `view` |
| POST | `/documents/{document_id}/rescan` | New scan with current rules | 303 → `/documents/{id}` | 404 | `upload` |
| POST | `/documents/{document_id}/delete` | Delete document, files, scans, findings, redactions | 303 → `/documents` | 404 | `delete` |
| GET | `/documents/{document_id}/redact` | Redaction page: page list, selectable findings | 200 | 404, 409 `NOT_A_PDF` | `redact` |
| POST | `/documents/{document_id}/redactions` | Create sanitized copy; form field `finding_ids` (repeated) | 303 → `/redactions/{id}` | 400 none selected, 404, 409 | `redact` |
| GET | `/redactions/{redaction_id}` | Verification result: redacted / unmappable / still present | 200 | 404 | `redact` |
| GET | `/redactions/{redaction_id}/download` | Download the sanitized PDF (`Content-Disposition: attachment`) | 200 `application/pdf` | 404 | `redact` |
| GET | `/scans/{scan_id}/report` | Printable HTML report (masked values only) | 200 | 404 | `view` |
| GET | `/healthz` | Liveness check | 200 `{"status":"ok"}` | — | none |

There is **no** route that serves an original upload back to the browser in the MVP; originals are only read by the server.

### 2.1 Filters for `GET /documents`

| Parameter | Values | Example |
|---|---|---|
| `risk` | `informational`, `low`, `medium`, `high`, `critical` (repeatable) | `?risk=high&risk=critical` |
| `category` | `email`, `phone`, `national_id`, `passport`, `payment_card`, `iban`, `secret`, `confidentiality_label`, `keyword` | `?category=secret` |
| `review_status` | `open`, `confirmed`, `false_positive`, `resolved` | `?review_status=open` |
| `from`, `to` | ISO date `YYYY-MM-DD` (inclusive) | `?from=2026-11-01&to=2026-11-30` |
| `page` | integer ≥ 1 (25 per page) | `?page=2` |

Unknown values return 400 rather than being silently ignored.

## 3. JSON endpoints

### `GET /api/stats`

Dashboard numbers (used to refresh KPI cards).

```json
{
  "documents_total": 12,
  "findings_total": 87,
  "findings_unresolved": 31,
  "documents_by_risk": { "informational": 2, "low": 3, "medium": 4, "high": 2, "critical": 1 },
  "findings_by_category": { "email": 30, "phone": 18, "payment_card": 4, "iban": 3, "secret": 2,
                            "confidentiality_label": 9, "keyword": 15, "national_id": 6, "passport": 0 }
}
```

### `GET /api/scans/{scan_id}`

Scan status (used by the upload page and, later, by a background worker UI).

```json
{
  "id": "6f0c…",
  "document_id": "1b2e…",
  "status": "completed",
  "ruleset_version": "2026.11.0",
  "started_at": "2026-11-03T09:15:00Z",
  "finished_at": "2026-11-03T09:15:01Z",
  "risk": { "score": 97, "level": "critical",
            "reasons": ["+38 Payment card number (Luhn-valid, high confidence)", "+10 Confidentiality label with high-sensitivity data"],
            "label": "Application-defined risk estimate" },
  "error_code": null
}
```

`status` ∈ `queued | running | completed | failed`. When `failed`, `risk` is `null` and `error_code` is set.

### `GET /api/scans/{scan_id}/findings`

Query parameters: `category`, `severity`, `review_status` (all optional, repeatable).

```json
{
  "items": [
    {
      "id": "a91d…",
      "rule_id": "payment_card.luhn",
      "category": "payment_card",
      "severity": "high",
      "confidence": 0.95,
      "confidence_label": "High",
      "page_number": 2,
      "occurrences": 1,
      "masked_value": "•••• •••• •••• 4242",
      "context": "Card used: •••• •••• •••• 4242 exp 08/2…",
      "validation": "Luhn checksum passed",
      "explanation": "A 16-digit number that passes the Luhn checksum is likely a real payment card number.",
      "recommendation": "Remove or mask the card number and follow your payment-data handling procedure.",
      "review_status": "open",
      "updated_at": "2026-11-03T09:15:01Z"
    }
  ]
}
```

### `PATCH /api/findings/{finding_id}`

Change review status. Header `X-CSRFToken` required.

Request:

```json
{ "review_status": "false_positive", "note": "Test card number from our sandbox documentation." }
```

| Field | Rule |
|---|---|
| `review_status` | Required; one of `open`, `confirmed`, `false_positive`, `resolved`; must be an allowed transition ([Architecture §6](02-architecture.md#6-state-machines)) |
| `note` | Optional, ≤ 500 characters, stored as plain text and HTML-escaped on display. Reviewers are told not to paste sensitive values here. |

Response **200**:

```json
{
  "finding": { "id": "a91d…", "review_status": "false_positive", "updated_at": "2026-11-03T09:20:44Z" },
  "risk": { "score": 59, "level": "high", "reasons": ["…"] }
}
```

Errors: 400 (bad JSON / note too long / CSRF), 404, 409 `INVALID_TRANSITION`.

## 4. Configuration contract (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `SECUREWASTE_SECRET_KEY` | *(none — required)* | Flask session and CSRF signing key. 32+ random bytes. |
| `SECUREWASTE_HMAC_KEY` | *(none — required)* | Separate key for `value_hmac` (one key per purpose). Changing it makes old findings un-matchable for redaction until re-scanned. |
| `MAX_UPLOAD_MB` | `10` | Request body limit |
| `MAX_PDF_PAGES` | `100` | Page limit |
| `MAX_EXTRACTED_CHARS` | `2000000` | Extraction cap |
| `MIN_CONFIDENCE` | `0.30` | Candidates below are discarded |
| `STORAGE_DIR` | `instance/storage` | Originals (`originals/`), sanitized copies (`sanitized/`), temp (`tmp/`) |
| `DATABASE_PATH` | `instance/securewaste.db` | SQLite file |
| `SECUREWASTE_KEYWORDS` | `salary,password,confidential agreement` | Comma-separated custom keywords |

## 5. Internal Python contracts (core)

These signatures are the boundary between `services` and `core`; they are what unit tests target.

```python
validate_upload(filename: str, data: bytes, limits: Limits) -> ValidatedUpload        # raises UploadRejected(code)
extract_pages(path: Path, file_type: Literal["pdf", "txt"], limits: Limits) -> list[PageText]  # raises ExtractionFailed(code)
DetectionEngine(rules: list[DetectionRule], min_confidence: float).scan(pages: list[PageText]) -> list[Finding]
RiskEngine(catalogue: Catalogue).assess(findings: list[Finding]) -> RiskAssessment   # ignores false positives
Redactor().redact(src: Path, dst: Path, targets: list[RedactionTarget]) -> RedactionResult
```

`Finding` (dataclass) carries `rule_id, category, severity, confidence, page_number, char_start, char_end, occurrences, masked_value, value_hmac, context, explanation, recommendation`. It never carries the raw value; `RedactionTarget` (in memory only, during a redaction request) does.
