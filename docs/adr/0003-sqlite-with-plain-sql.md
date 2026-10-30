# ADR-0003: SQLite through Python's sqlite3 with plain SQL

| | |
|---|---|
| Status | Accepted |
| Date | 2026-10-29 |
| Deciders | SecureWaste team |

## Context

We need durable storage for documents' metadata, scans, findings, reviews, redactions and audit events. The app is local and single-user; the team is learning databases.

## Decision

Use **SQLite** via the standard-library **`sqlite3`** module, with the schema in `db/schema.sql`, parameterised queries in `db/repositories.py`, `PRAGMA foreign_keys = ON` on every connection, and simple numbered migration scripts if the schema changes.

## Alternatives considered

- **SQLAlchemy ORM** — portable and powerful, but adds a second abstraction to learn and hides the SQL we want to understand; can be introduced later.
- **PostgreSQL** — production-grade, but needs a server, credentials and setup on every laptop.
- **JSON files** — no constraints, no transactions, no queries.

## Consequences

- **(+)** Zero installation; the DB is one file; real SQL with constraints and indexes.
- **(+)** Repository layer keeps SQL in one place, so moving to PostgreSQL later is contained.
- **(−)** Limited concurrency (fine for one user).
- **(−)** We write migrations by hand.
