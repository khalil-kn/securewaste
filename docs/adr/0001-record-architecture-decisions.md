# ADR-0001: Record architecture decisions

| | |
|---|---|
| Status | Accepted |
| Date | 2026-10-29 |
| Deciders | SecureWaste team |

## Context

A five-person student team will make many technical choices over several months. Without a written record, people forget *why* a choice was made, newcomers repeat old debates, and reviewers of the portfolio cannot see the reasoning.

## Decision

We keep **Architecture Decision Records** (ADRs) in `docs/adr/`, one Markdown file per decision, numbered `NNNN-kebab-title.md`, using [the template](template.md). An ADR is added in the same pull request as the change it justifies. Accepted ADRs are never edited to change their meaning; a new ADR *supersedes* an old one.

## Alternatives considered

- **No record** — fastest now, costly later.
- **Wiki pages** — separate from code, drift out of date, not reviewed in PRs.
- **Long design document only** — hard to see individual decisions and their status.

## Consequences

- **(+)** Decisions are reviewable, searchable and versioned with the code.
- **(+)** Strong portfolio signal: shows engineering reasoning.
- **(−)** Small writing overhead for each significant decision.
