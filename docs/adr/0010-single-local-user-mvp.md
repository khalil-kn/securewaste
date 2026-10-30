# ADR-0010: Single local user in the MVP; authentication deferred

| | |
|---|---|
| Status | Accepted |
| Date | 2026-10-29 |
| Deciders | SecureWaste team |

## Context

Authentication, sessions, password storage and per-user authorisation are a full milestone of security work. The brief asks to finish the document pipeline first.

## Decision

The MVP has **no login**. It must run bound to `127.0.0.1`, with debug off by default, and the README states it must not be exposed to a network. All service functions take an `actor` argument (currently `"local-user"`) and repositories are written so that an `owner_id` filter can be added in one place.

## Alternatives considered

- **Implement accounts now** — delays the core value and spreads a small team thin.
- **HTTP Basic auth** — gives a false sense of security without proper sessions, rate limiting and HTTPS.

## Consequences

- **(+)** Team focuses on detection, risk and redaction quality.
- **(+)** Clear upgrade path (threat T-21, user story US-25).
- **(−)** Not usable as a shared service until the accounts milestone (residual risk R-01).
