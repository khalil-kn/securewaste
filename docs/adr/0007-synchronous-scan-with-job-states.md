# ADR-0007: Synchronous scanning with persisted job states

| | |
|---|---|
| Status | Accepted |
| Date | 2026-10-29 |
| Deciders | SecureWaste team |

## Context

MVP documents are small (≤ 10 MB, ≤ 100 pages). A job queue (Celery/RQ + Redis) adds infrastructure the brief asks us to avoid, yet we want to grow towards background processing.

## Decision

Run the scan **inside the upload request**, but model it as a `scans` row with states `queued → running → completed | failed`. The upload page shows a "Scanning…" indicator while the request is in flight; `GET /api/scans/{id}` exposes status.

## Alternatives considered

- **Background queue now** — realistic for production, but needs Redis and a worker process on every laptop.
- **Threads inside Flask** — easy to start, hard to get right (lost jobs on restart, shared SQLite connections).

## Consequences

- **(+)** Simple to build, test and debug.
- **(+)** Data model already supports a future worker.
- **(−)** Long scans block a request; mitigated by limits.
- **(−)** Parser crashes affect the web process (R-07).
