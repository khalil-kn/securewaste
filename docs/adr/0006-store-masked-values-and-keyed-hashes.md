# ADR-0006: Store masked values and keyed hashes, never raw values

| | |
|---|---|
| Status | Accepted |
| Date | 2026-10-29 |
| Deciders | SecureWaste team |

## Context

A DLP tool's own database must not become a second copy of the sensitive data. But the app must still show findings, merge duplicates and later locate values for redaction.

## Decision

For every finding store only: a **masked value** (e.g. `•••• •••• •••• 4242`), a short **masked context**, and `value_hmac = HMAC-SHA256(SECUREWASTE_HMAC_KEY, rule_id + normalized_value)`. Raw values exist only in memory during a scan or redaction request. Logs and audit events never contain values or document text.

## Alternatives considered

- **Store raw values** — simplest, but a DB leak equals a document leak.
- **Encrypt raw values** — reversible; key management complexity; a stolen key reveals everything.
- **Plain SHA-256 hash** — short values (8-digit IDs, card numbers) can be brute-forced without any key.

## Consequences

- **(+)** A stolen DB alone reveals only masks and keyed hashes.
- **(+)** Duplicate merging and redaction matching still work.
- **(−)** Redaction must re-scan the original file (slightly slower).
- **(−)** Changing the HMAC key invalidates matching for old scans (re-scan needed).
