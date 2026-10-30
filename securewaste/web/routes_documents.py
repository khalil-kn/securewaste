"""Document routes (03-api.md §2): upload, details, delete, re-scan, redaction, report.

Milestone 1 issue #3 adds GET /upload and POST /documents here. Keep each handler thin:
parse the request, call one function in securewaste.services, render or redirect (303).
"""

from flask import Blueprint, render_template, request, redirect, url_for, current_app

from securewaste.core.detection.catalogue import Category, ReviewStatus, Severity
from securewaste.core.detection.models import Finding
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.errors import UploadRejected, ExtractionFailed
from securewaste.services.scan_service import upload_and_scan

bp = Blueprint("documents", __name__)

# Human-readable error messages for user-facing codes
ERROR_MESSAGES = {
    "FILE_TOO_LARGE": "The file is too large. Maximum size is 10 MB.",
    "UNSUPPORTED_TYPE": "Unsupported file type. Only PDF and TXT files are accepted.",
    "EMPTY_FILE": "The uploaded file is empty.",
    "MALFORMED_PDF": "The PDF file is corrupted or malformed.",
    "PDF_ENCRYPTED": "The PDF is encrypted and cannot be scanned. Please remove the password.",
    "TOO_MANY_PAGES": "The PDF has too many pages. Maximum is 100 pages.",
    "NOT_UTF8": "The text file is not valid UTF-8 encoding.",
    "NO_TEXT_LAYER": "The PDF has no extractable text layer (may be scanned images only).",
    "EXTRACTION_ERROR": "Failed to extract text from the document.",
}


def _demo_findings() -> list[Finding]:
    """Return fake Finding objects for the /results/demo route."""
    return [
        Finding(
            rule_id="email.basic",
            category=Category.EMAIL,
            severity=Severity.LOW,
            confidence=0.95,
            page_number=1,
            char_start=100,
            char_end=130,
            masked_value="j••••@e•••••.com",
            value_hmac="a1b2c3d4e5f6",
            context="Contact: j••••@e•••••.com for details",
            explanation="An e-mail address is personal data.",
            recommendation="Keep it only if the recipient needs it.",
            occurrences=2,
            validation="",
            review_status=ReviewStatus.OPEN,
            id="f1",
        ),
        Finding(
            rule_id="phone.international",
            category=Category.PHONE,
            severity=Severity.MEDIUM,
            confidence=0.88,
            page_number=1,
            char_start=200,
            char_end=220,
            masked_value="+44 •••• ••••••",
            value_hmac="b2c3d4e5f6a1",
            context="Call +44 •••• •••••• for support",
            explanation="A phone number is personal data.",
            recommendation="Keep it only if the recipient needs it.",
            occurrences=1,
            validation="",
            review_status=ReviewStatus.OPEN,
            id="f2",
        ),
        Finding(
            rule_id="keyword.confidential",
            category=Category.KEYWORD,
            severity=Severity.INFORMATIONAL,
            confidence=0.92,
            page_number=2,
            char_start=50,
            char_end=80,
            masked_value="CONFIDENTIAL",
            value_hmac="c3d4e5f6a1b2",
            context="This document is marked CONFIDENTIAL",
            explanation="A keyword your organisation marked as sensitive appears in the document.",
            recommendation="Review the surrounding text before sharing.",
            occurrences=3,
            validation="",
            review_status=ReviewStatus.OPEN,
            id="f3",
        ),
    ]


@bp.get("/results/demo")
def results_demo():
    """Temporary demo route showing the results page with fake data."""
    findings = _demo_findings()
    return render_template("results.html", file_name="invoice_sample.pdf", findings=findings)


@bp.post("/documents")
def upload_document():
    """Handle file upload and scan, then render results."""
    # Get uploaded file
    file = request.files.get("file")
    if not file or not file.filename:
        return render_template("error.html", message="No file selected"), 400

    # Read file data
    data = file.read()
    if not data:
        return render_template("error.html", message="The uploaded file is empty"), 400

    # Get app config for limits and rules
    upload_limits = current_app.config.get("UPLOAD_LIMITS")
    rules = current_app.config.get("DETECTION_RULES", [])
    min_confidence = current_app.config.get("MIN_CONFIDENCE", 0.3)
    hmac_key = current_app.config.get("HMAC_KEY", b"")
    storage_dir = current_app.config.get("STORAGE_DIR")

    try:
        # Call the scan service
        findings = upload_and_scan(
            filename=file.filename,
            data=data,
            rules=rules,
            min_confidence=min_confidence,
            hmac_key=hmac_key,
            storage_dir=storage_dir,
            upload_limits=upload_limits,
        )

        # Render results page
        return render_template("results.html", file_name=file.filename, findings=findings)

    except UploadRejected as e:
        message = ERROR_MESSAGES.get(e.code, f"Upload rejected: {e.code}")
        return render_template("error.html", message=message, status=400, code=e.code), 400
    except ExtractionFailed as e:
        message = ERROR_MESSAGES.get(e.code, f"Extraction failed: {e.code}")
        return render_template("error.html", message=message, status=400, code=e.code), 400
    except Exception as e:
        current_app.logger.exception("Unexpected error during upload and scan")
        return render_template("error.html", message="An unexpected error occurred. Please try again.", status=500, code="INTERNAL_ERROR"), 500
