# Contributing to SecureWaste

This is how our team of five works. The full explanation, with diagrams and a recovery toolkit, is in the [Git workflow guide](docs/guides/git-workflow.md).

## Roles: the tech lead owns the structure, everyone owns a module

**The tech lead** builds and guards the skeleton everyone else builds on:

- the package layout, the application factory (`securewaste/__init__.py`) and configuration (`config.py`);
- cross-cutting security in `web/security.py` (CSRF, headers, error pages);
- the database schema (`db/schema.sql`) and connection handling;
- the **shared contracts**: `core/errors.py`, `core/detection/models.py`, `core/detection/catalogue.py`, `core/detection/rules/base.py`, and the signatures in every stub module;
- dependencies (`requirements*.txt`, `pyproject.toml`), CI (`.github/`), the interface contract (`docs/03-api.md`) and ADRs.

These paths are listed in [`.github/CODEOWNERS`](.github/CODEOWNERS), so GitHub automatically asks the tech lead to review any PR that touches them.

**Everyone else** (the tech lead included, for their own issues) fills in the stub modules behind those contracts, one issue at a time:

| Area | Files you edit | First issue |
|---|---|---|
| Upload & storage | `core/upload.py`, `web/routes_documents.py`, `web/templates/upload.html` | M1 #3 |
| Extraction & fixtures | `core/extraction.py`, `scripts/make_fixtures.py`, `tests/fixtures/` | M1 #4 |
| Detection | `core/detection/engine.py`, `masking.py`, `rules/*.py` | M1 #5 |
| Validators & risk | `core/detection/validators.py`, `core/risk.py` | M2 |
| Persistence & UI | `db/repositories.py`, `services/*`, `web/routes_dashboard.py`, templates, `static/` | M3 |

**Rules for merging into the skeleton**

1. Implement the stub's signature as written. If you need to change a shared contract (a dataclass field, a function signature, the schema, a catalogue value), open a small separate PR for it first, with the tech lead as reviewer. Then build your feature on top.
2. Add routes in your own blueprint file, styles in your own section of `app.css`, scripts in your own `static/js/<feature>.js`. Never edit `create_app()` just to add a feature. That is how five people avoid merge conflicts.
3. Replace `raise NotImplementedError(...)` with your code and add tests next to the existing ones. CI must stay green: `ruff check .`, `ruff format --check .`, `pytest`, `pip-audit`.
4. Keep `core/` free of Flask imports. A test enforces it.

## The workflow: issue → branch → pull request → squash merge

1. **Issue first.** Every piece of work starts as a GitHub issue (use a template). It has acceptance criteria, a MoSCoW priority, a milestone and one assignee.
2. **Branch from an up-to-date `main`.**
   ```bash
   git switch main
   git pull
   git switch -c feat/12-upload-validation
   ```
   Branch names: `type/<issue-number>-short-kebab-description`, e.g. `feat/12-upload-validation`, `fix/31-luhn-off-by-one`, `docs/7-threat-model`.
3. **Commit small, meaningful steps** using Conventional Commits (below). Push early: `git push -u origin feat/12-upload-validation`.
4. **Open a pull request** to `main` as soon as you want feedback (draft PRs are fine). Title in Conventional Commits form with the issue reference, e.g. `feat: validate uploads by magic bytes (closes #12)`; put `Closes #12` in the description so GitHub closes the issue on merge. Fill in the template.
5. **Review.** At least **one** teammate approves. CI must be green. The author resolves every comment (fix it or explain).
6. **Squash and merge.** All commits of the branch become one commit on `main` whose message is the PR title.
7. **Delete the branch only after the PR shows "Merged".** Then locally: `git switch main && git pull && git branch -d feat/12-upload-validation`.

`main` is protected: no direct pushes, no force-pushes, PR + 1 approval + passing CI required.

## Conventional Commits

```
<type>(<optional scope>): <imperative summary, lowercase, no final period, ≤ 72 chars>

<optional body: why, not how>

<optional footer: Closes #12, BREAKING CHANGE: …>
```

| Type | Use for | Example |
|---|---|---|
| `feat` | New user-visible capability | `feat(detection): add IBAN rule with mod-97 validation` |
| `fix` | Bug fix | `fix(upload): reject PDFs with zero pages` |
| `docs` | Documentation only | `docs(adr): add ADR-0011 for background worker` |
| `test` | Tests only | `test(risk): cover label amplifier` |
| `refactor` | Code change without behaviour change | `refactor(db): move filters into repository` |
| `chore` | Tooling, dependencies, housekeeping | `chore: pin pymupdf to 1.26.x` |
| `ci` | GitHub Actions | `ci: run pip-audit on pull requests` |
| `style` | Formatting only | `style: apply ruff format` |

## Definition of Done

A change is done only when **all** are true:

- [ ] Acceptance criteria of the issue are met.
- [ ] Business logic is in `core/` or `services/`, not in route handlers.
- [ ] Unit tests for new logic; `pytest` passes locally and in CI.
- [ ] Only synthetic data in tests and fixtures. No real names, IDs, card numbers or keys — ever.
- [ ] No raw sensitive values written to logs, the database, responses or reports.
- [ ] User-visible text is clear; UI works at 390 px width and with the keyboard.
- [ ] Docs updated when behaviour, API, data model or a decision changed (with a new ADR for significant decisions).
- [ ] PR approved by a teammate and squash-merged.

## Code conventions

- Python 3.12, formatted with `ruff format`, linted with `ruff check`; type hints on public functions.
- `snake_case` for modules, functions, variables; `PascalCase` for classes; `UPPER_SNAKE_CASE` for constants.
- Templates and static files in `kebab-case`; CSS classes prefixed `sw-`; colours only through `var(--sw-*)` tokens.
- One rule per file in `core/detection/rules/`, each with positive, negative and edge-case tests.

## Reporting security issues

Do not open a public issue for a vulnerability. Use GitHub's private security advisory ("Security" tab → "Report a vulnerability").
