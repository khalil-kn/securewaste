"""Detection route: GET /detect shows the PDF-upload form, POST /detect runs detection.

This is the web face of Issue #5. The PDF→text extraction is owned by Milestone 1 issue #4
(extract_pages); this route feeds that output to the detection engine and renders the findings
(masked values, severity, category) using the design-system tokens.
"""

from __future__ import annotations

from uuid import uuid4

from flask import Blueprint, current_app, render_template, request

from securewaste.core.errors import ExtractionFailed
from securewaste.core.upload import Limits
from securewaste.services.detect_service import scan_file

bp = Blueprint("detect", __name__)


@bp.get("/detect")
def detect_form():
    return render_template("detect.html", findings=None, error=None)


@bp.post("/detect")
def detect_run():
    document = request.files.get("document")
    if document is None or not document.filename:
        return render_template("detect.html", findings=None, error="Please choose a PDF file.")

    dest = current_app.config["STORAGE_DIR"] / "tmp" / f"{uuid4().hex}.pdf"
    document.save(dest)

    limits = Limits(
        max_bytes=current_app.config["MAX_CONTENT_LENGTH"],
        max_pdf_pages=current_app.config["MAX_PDF_PAGES"],
        max_extracted_chars=current_app.config["MAX_EXTRACTED_CHARS"],
    )
    try:
        findings, _pages = scan_file(
            dest,
            "pdf",
            limits,
            current_app.config["KEYWORDS"] or [],
            current_app.config["MIN_CONFIDENCE"],
            current_app.config["HMAC_KEY"],
        )
    except ExtractionFailed as exc:
        message = (
            "This PDF has no selectable text layer."
            if exc.code == "NO_TEXT_LAYER"
            else "Could not read text from this PDF; please try another file."
        )
        return render_template("detect.html", findings=None, error=message)
    return render_template("detect.html", findings=findings, error=None)
