"""GET / (dashboard) and GET /documents (scan history with filters). Filled in Milestone 3 (US-11, US-16)."""

from flask import Blueprint, render_template

bp = Blueprint("dashboard", __name__)


@bp.get("/")
def index():
    return render_template("dashboard.html")
