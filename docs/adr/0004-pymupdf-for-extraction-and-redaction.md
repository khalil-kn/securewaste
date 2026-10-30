# ADR-0004: PyMuPDF for PDF extraction and redaction

| | |
|---|---|
| Status | Accepted (licence decision pending) |
| Date | 2026-10-29 |
| Deciders | SecureWaste team |

## Context

We must extract text page by page with positions, and we must perform **genuine** redaction that removes content rather than covering it. Using one library for both keeps locations consistent between detection and redaction.

## Decision

Use **PyMuPDF** (`pymupdf`) for opening/validating PDFs, page-aware text extraction, locating text (`search_for`), redaction (`add_redact_annot` + `apply_redactions`), metadata removal and saving with garbage collection.

**Licence consequence:** PyMuPDF is dual-licensed under **GNU AGPL-3.0** or a commercial licence from Artifex. An open-source portfolio project can use it under AGPL-3.0; the simplest consistent choice is to licence SecureWaste itself under AGPL-3.0. The team must confirm this.

## Alternatives considered

- **pypdf** — pure Python and permissive (BSD), good for extraction, but no true content-removing redaction.
- **pdfplumber / pdfminer.six** — excellent text positions, MIT, but no redaction or writing.
- **pikepdf (qpdf)** — powerful low-level editing, but redaction would have to be implemented by hand in content streams — error-prone.
- **Two libraries** (pdfplumber for extraction + another for redaction) — risk of mismatched coordinates and text order.

## Consequences

- **(+)** One library, consistent coordinates, real redaction, fast (MuPDF is C).
- **(+)** Well documented.
- **(−)** AGPL licence obligations (see above).
- **(−)** Native code parses untrusted input (threat T-19): keep it updated and limit inputs.
