# Test evidence: SCRUM-22 (classification and risk display), SCRUM-30 (metadata sync), UI redesign

Recorded 2026-11-18. Synthetic data only. Python 3.13, scikit-learn 1.6.1 and ruff 0.17.3 (the versions the repo pins).
CI runs Python 3.12 and passed on all three branches.

## Commands

```bash
pip install -r requirements-dev.txt
python -m pytest -q          # unit, Flask/template, API contract and cloud_api tests
ruff check .
ruff format --check .
```

| Branch (PR) | Commit | pytest | ruff check | ruff format |
|---|---|---|---|---|
| `feat/results-risk-guidance` (#12) | `ca6f7b0` | 180 passed, 25 skipped | clean | clean |
| `feat/ui-design-v2` (#13) | `bbd5b84` | 189 passed, 25 skipped | clean | clean |
| `feat/metadata-sync` | see `git log` | 216 passed, 25 skipped | clean | clean |

The 25 skipped tests are the `cloud_api` database tests. They need a reachable PostgreSQL (`CLOUD_DATABASE_URL`) and
run in CI.

## What the tests prove

| Requirement | Test file |
|---|---|
| Four labels, explanation, recommendation; masked values only | `tests/unit/test_risk_guidance.py` |
| Risk badge hidden but risk level still computed | `test_risk_badge_is_hidden_but_still_computed` |
| Low ML confidence (< 0.60, the classifier's `REVIEW_THRESHOLD`) asks for human review | `test_low_ml_confidence_asks_for_human_review` |
| Prediction error: findings stay visible, only the error type is logged | `test_results_page_survives_classifier_failure` |
| Missing model file: rule-based fallback, stated on the page | `tests/unit/test_result_states.py` |
| PDF without text layer, unsupported, broken or empty file: honest error, no classification | `tests/unit/test_result_states.py` |
| No inline styles (CSP), navigation state, self-hosted fonts, upload form contract | `tests/unit/test_ui_shell.py` |
| Sync sends only the 4 allowed metadata fields; token not in path, body or logs | `tests/unit/test_sync_service.py` |
| Sync payload accepted by the real `cloud_api` validator for all 4 labels | `test_payload_is_accepted_by_the_real_api_validator` |
| Sync off, 401, 403, 409, 400, 5xx, timeout, offline, malformed body, redirect: local results kept | `tests/unit/test_sync_service.py` |
| "Stored" shown only after a 201 echoing the same `event_id` | `test_page_shows_stored_only_after_a_201` |

The sync tests start a real HTTP server on `127.0.0.1` and inspect the request the client actually sends.

## Bug found and fixed

Every rejected upload (empty, `.exe`, broken PDF) returned **Error 500** on `main`: `core/upload.py` raised its own
`UploadRejected` class while the route caught the one in `core/errors.py`. Fixed in PR #12 (`ca6f7b0`), covered by
`test_rejected_upload_shows_an_error_and_no_classification`.

## Responsive and accessibility check

Seven states (dashboard, upload, results, no findings, PDF without text, rejected upload, low confidence) rendered at
1440, 768 and 390 px with Playwright, measuring horizontal overflow and interactive targets smaller than 24 px.

| | Overflow | Targets < 24 px | Visible keyboard focus |
|---|---|---|---|
| Before (`main`) | none | 12 of 21 renders (links and buttons 20-21 px high) | 2 px outline |
| After | none in all 21 renders | none | 2 px outline on every tab stop |

Screenshots (before/after, desktop, tablet, phone) are attached to the pull requests.

## Not covered yet (waiting on the team)

- A real `201` stored in PostgreSQL and a real `403` with a non-writer token (agreed to run later, SCRUM-44 QA).
## Integration QA — 2026-11-18

- Integrated metadata sync with the latest main.
- Removed risk from the payload until Sprint 4.
- Hardened cloud URL validation.
- Full Docker regression suite: 286 passed, 14 existing ML warnings.
- Real local scanner to cloud API synchronization: HTTP 201.
- PostgreSQL persistence verified.
- Classification: Highly Confidential.
- Counts: email=1, phone=1, keyword=1.
- Risk: NULL.
- Employee UUID attribution verified using a development token.
- No document content or matched values stored in PostgreSQL.

### Remaining dependencies

- Production authentication and authorization: SCRUM-29.
- Live authentication and access isolation testing after SCRUM-29.
- Persistent synchronization retries: SCRUM-31.
- Overall risk assessment: Sprint 4.
