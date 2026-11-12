"""Legacy detection routes for Secure Waste.

All document uploads now use the validated /documents workflow.
"""

from flask import Blueprint, redirect, url_for

bp = Blueprint("detect", __name__)


@bp.route("/detect", methods=["GET", "POST"])
def detect_form():
    """Redirect legacy scanner requests to the secure upload page."""
    return redirect(url_for("documents.upload_page"), code=303)
