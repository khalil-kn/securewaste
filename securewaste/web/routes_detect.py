"""Detection route: GET /detect shows the text-input form, POST /detect runs detection.

This is the web face of Issue #5. It scans pasted text with the detection engine and renders
the findings (masked values, severity, category) using the design-system tokens.
"""

from __future__ import annotations

from flask import Blueprint, current_app, render_template, request

from securewaste.services.detect_service import detect_text

bp = Blueprint("detect", __name__)


@bp.get("/detect")
def detect_form():
    return render_template("detect.html", findings=None, text="")


@bp.post("/detect")
def detect_run():
    text = request.form.get("text", "")
    keywords = current_app.config["KEYWORDS"] or []
    findings, masked_text = detect_text(
        text,
        keywords,
        current_app.config["MIN_CONFIDENCE"],
        current_app.config["HMAC_KEY"],
    )
    # Echo back the masked text, never the original — the raw value must not appear on the page.
    return render_template("detect.html", findings=findings, text=masked_text)
