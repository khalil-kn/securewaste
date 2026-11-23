# ADR-0011: Optional metadata-only sync to the cloud API

| | |
|---|---|
| Status | Proposed |
| Date | 2026-11-18 |
| Deciders | Khalil (SCRUM-30), with Jawed (cloud API) and Yosr (auth, SCRUM-29) |

## Context

SCRUM-30 asks the local scanner to report each scan to the cloud API (`POST /api/v1/scans`, merged in PR #11) without
moving any document data off the machine. The API and the `scan_events` table accept only `event_id`, `timestamp`,
`classification`, `risk` (`Low`/`Medium`/`High`) and `counts` (`email`/`phone`/`keyword`), and have no owner column.
The results page uses four risk levels, so a mapping is needed. A cloud failure must never hide the local results.

## Decision

- Sync is **off by default** and runs only with `SYNC_ENABLED=true`; URL, token and timeout come from the environment.
- The client sends **only** the five allowed fields. No document, text, filename, matched value or owner identity.
- **Risk mapping:** Public → Low, Internal → Low, Confidential → Medium, Highly Confidential → High.
- **Auth:** the existing `Authorization: Bearer <token>` header, with **one token per employee**. No extra header and no
  owner field in the payload.
- **Idempotency:** one new UUID `event_id` per scan; a `409 duplicate_event` is reported as "already stored".
  No retry queue (deferred to SCRUM-31).
- **Transport:** 3 s timeout, redirects never followed, `https` required except for `localhost`/`127.0.0.1`.
- The results page shows a separate "Cloud sync" status; "stored" only after a `201` echoing the same `event_id`.
- Nothing is sent when classification failed, so no invented label reaches the database.

## Alternatives considered

- **Map Internal → Medium.** Rejected: Internal documents may be shared inside the organisation, so the cloud would
  overstate their risk next to Confidential ones.
- **Send the four-level risk.** Rejected: the schema's `CHECK` constraint allows only Low/Medium/High.
- **One shared token per machine.** Rejected: one leaked token could not be revoked without breaking every user.
- **Retry with a persistent queue.** Deferred to SCRUM-31 to keep this change small.

## Consequences

- **(+)** Document content cannot reach the cloud even by mistake: the server refuses unknown fields.
- **(+)** Local scanning works offline; every cloud failure becomes a visible, honest status.
- **(−)** Public and Internal look the same in cloud statistics.
- **(−)** A token stored in `.env` is usable by anyone with access to that machine's files.
- **(−)** A failed sync is not retried; the event is simply missing from the cloud until SCRUM-31.
