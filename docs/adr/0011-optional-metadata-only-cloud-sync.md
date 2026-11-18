# ADR-0011: Optional metadata-only sync to the cloud API

| | |
|---|---|
| Status | Proposed |
| Date | 2026-11-18 |
| Deciders | Khalil, Jawed, Yosr and integration QA |

## Context

SCRUM-30 enables the local scanner to report scan metadata
to the cloud API without transferring document content.

SCRUM-45 introduces nullable risk and employee attribution
in the PostgreSQL schema.

Classification and risk assessment are separate concepts.
Overall risk assessment is deferred to Sprint 4.

## Decision

- Cloud sync is disabled by default.
- The client sends only event_id, timestamp,
  classification and aggregate counts.
- Risk is omitted until Sprint 4.
- Employee identity is derived server-side from authentication.
- Per-employee authentication is handled by SCRUM-29.
- No document content, filenames, paths or matched values
  are transmitted.
- HTTPS is required outside localhost development.
- Malformed URLs and embedded credentials are rejected.
- HTTP redirects are not followed.
- The default network timeout is three seconds.
- Each scan receives a unique event UUID.
- Cloud failures must not prevent local scan results.
- Persistent retries are deferred to SCRUM-31.

## Consequences

- Local scanning remains available offline.
- Document content remains on the local machine.
- Server-side validation provides additional privacy protection.
- Risk remains NULL in PostgreSQL until Sprint 4.
- Failed synchronization is not automatically retried.
- Production cloud access requires completed authentication
  and authorization controls.