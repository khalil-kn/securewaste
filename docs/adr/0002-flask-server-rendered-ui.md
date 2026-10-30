# ADR-0002: Flask with server-rendered pages and vanilla JavaScript

| | |
|---|---|
| Status | Accepted |
| Date | 2026-10-29 |
| Deciders | SecureWaste team |

## Context

We need a web UI and backend that a student team can learn quickly, that keeps security controls (CSRF, escaping, headers) simple, and that runs locally with no build step. The project brief forbids Angular, Spring Boot and microservices for the first version.

## Decision

Use **Flask 3** with **Jinja2 server-rendered templates** and small **vanilla JavaScript** modules for progressive enhancement (review status changes, upload progress). Business logic stays out of route handlers, in `services/` and `core/`.

## Alternatives considered

- **FastAPI + React/Angular SPA** — modern, but two codebases, a JS build pipeline, token handling and CORS; too much for the MVP.
- **Django** — batteries included (ORM, admin, auth) but heavier and more magic to learn; most of its features are unused before accounts exist.
- **Streamlit** — very fast to prototype, but limited control over HTTP security, layout and multi-page workflows; looks less like a real product.

## Consequences

- **(+)** One language for most code, no build step, easy local run.
- **(+)** Jinja2 autoescaping and Flask-WTF give strong defaults against XSS and CSRF.
- **(+)** Layered design allows a JSON API or SPA later without rewriting `core/`.
- **(−)** Less interactive than a SPA; page reloads after most actions.
- **(−)** Flask leaves structure to us, so we must follow the module layout in the architecture doc.
