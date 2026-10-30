# ADR-0009: True redaction verified by re-extraction

| | |
|---|---|
| Status | Accepted |
| Date | 2026-10-29 |
| Deciders | SecureWaste team |

## Context

Many real data leaks come from "redactions" that only drew black boxes over text. A sanitized copy that still contains the data is worse than no copy because users trust it.

## Decision

Redaction uses PyMuPDF redaction annotations followed by `apply_redactions()` (removing text and overlapping image content), then removes metadata, XMP, annotations and embedded files, and saves with garbage collection to a **new** file. The service then **re-opens the output, re-extracts all text and re-runs the selected rules**; the redaction is `verified` only if none of the selected values remain. Values that cannot be located are reported as `unmappable` and the result is `incomplete`.

## Alternatives considered

- **Drawing rectangles** — visually hidden, trivially recoverable by copy/paste.
- **Rasterising pages to images** — removes text but destroys accessibility and searchability, and hidden data in other objects may survive.
- **Trust the library without verification** — no evidence for the user or the report.

## Consequences

- **(+)** Evidence-based claim: tests and the report show the verification result.
- **(+)** Original is never modified.
- **(−)** Text split across lines or with unusual encodings may be unmappable; we report it honestly instead of guessing.
- **(−)** Over-redaction: every occurrence of a selected value on the page is removed (safe by design).
