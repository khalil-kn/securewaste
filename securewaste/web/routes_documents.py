"""Document routes (03-api.md §2): upload, details, delete, re-scan, redaction, report.

Milestone 1 issue #3 adds GET /upload and POST /documents here. Keep each handler thin:
parse the request, call one function in securewaste.services, render or redirect (303).
"""

from flask import Blueprint

bp = Blueprint("documents", __name__)
