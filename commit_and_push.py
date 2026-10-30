#!/usr/bin/env python3
"""Script to commit and push changes for Issue #6."""
import subprocess
import os

os.chdir(r'C:\Users\medkh\projects\securewaste')

# Add all
result = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True)
print("Add:", result.returncode, result.stdout, result.stderr)

# Commit
commit_msg = """Issue #6: Results page and scan service orchestration

- results.html: designed findings table with severity meter, status pill, masked values
- app.css: component styles for findings table, severity bars, status pills, responsive layout
- scan_service.py: upload_and_scan() with validate->save->extract->detect flow, temp file cleanup in finally
- routes_documents.py: POST /documents wiring with readable error messages, /results/demo route
- tests/unit/test_scan_service.py: monkeypatch tests for success, cleanup, error handling, order
- tests/integration/test_upload_scan_e2e.py: xfail e2e test for full upload-to-results flow

Co-Authored-By: Claude Code <noreply@anthropic.com>"""

result = subprocess.run(['git', 'commit', '-m', commit_msg], capture_output=True, text=True)
print("Commit:", result.returncode, result.stdout, result.stderr)

# Check status
result = subprocess.run(['git', 'status'], capture_output=True, text=True)
print("Status:", result.stdout)

# Push
result = subprocess.run(['git', 'push', 'origin', 'feature/6-results-page'], capture_output=True, text=True)
print("Push:", result.returncode, result.stdout, result.stderr)

# Create PR
pr_body = """## Summary
Implements the results page and scan orchestration for Issue #6.

## Changes
- **results.html**: Findings table with category, masked value, page, occurrences, severity meter (4 bars), status pill
- **app.css**: Component styles using design tokens (dark console theme)
- **scan_service.py**: `upload_and_scan()` orchestrating validate → save → extract → detect with temp file cleanup in finally block
- **routes_documents.py**: POST /documents wired to scan service + temporary /results/demo route
- **__init__.py**: Added UPLOAD_LIMITS and DETECTION_RULES config
- **tests/unit/test_scan_service.py**: 7 monkeypatch tests
- **tests/integration/test_upload_scan_e2e.py**: Xfail e2e test (blocked by #3, #4, #5)

## Checklists
- [ ] **Page + flow with fakes**: /results/demo shows 3 fake findings, no raw values, severity meters work, status pills show "Needs review"
- [ ] **Integration (blocked by #3, #4, #5)**: Full upload-to-results flow test passes with B's fixture

## Testing
- Run `python -m pytest tests/unit/test_scan_service.py -v` (passes)
- Visit `/results/demo` to see the page with fake data"""

result = subprocess.run(['gh', 'pr', 'create', '--draft', '--title', 'Issue #6: Results page and scan service orchestration', '--body', pr_body], capture_output=True, text=True)
print("PR Create:", result.returncode, result.stdout, result.stderr)