"""JSON endpoints under /api (03-api.md §3) plus the /healthz liveness check.

Planned here: GET /api/stats (M3), GET /api/scans/<id> and /findings (M2-M3), PATCH /api/findings/<id> (M4).
"""

from flask import Blueprint, jsonify

bp = Blueprint("api", __name__)


@bp.get("/healthz")
def healthz():
    return jsonify(status="ok")
