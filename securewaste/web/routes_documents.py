"""Document upload and scanning routes for Secure Waste."""

from pathlib import Path

from flask import Blueprint, current_app, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

from securewaste.core.errors import ExtractionFailed
from securewaste.core.upload import (
    Limits,
    UploadRejected,
    validate_upload,
)
from securewaste.services.detect_service import scan_file

bp = Blueprint("documents", __name__)


ERROR_MESSAGES = {
    "FILE_EMPTY": "Please select a file.",
    "FILE_TOO_LARGE": "File exceeds the upload size limit.",
    "INVALID_FILE_TYPE": "Only valid PDF and TXT files are accepted.",
    "PDF_INVALID": "The PDF is invalid or corrupted.",
    "PDF_ENCRYPTED": "Password-protected PDFs are not accepted.",
    "PDF_TOO_MANY_PAGES": "PDF exceeds the page limit.",
}


@bp.get("/upload")
def upload_page():
    return render_template("upload.html")


@bp.post("/documents")
def upload_document():
    uploaded_file = request.files.get("file")

    if uploaded_file is None or not uploaded_file.filename:
        return render_template(
            "upload.html",
            error=ERROR_MESSAGES["FILE_EMPTY"],
        ), 400

    config = current_app.config

    limits = Limits(
        max_bytes=config["MAX_UPLOAD_MB"] * 1024 * 1024,
        max_pdf_pages=config["MAX_PDF_PAGES"],
        max_extracted_chars=config["MAX_EXTRACTED_CHARS"],
    )

    destination = None

    try:
        # Read at most the upload limit plus one byte.
        data = uploaded_file.stream.read(limits.max_bytes + 1)

        # Step 1: Validate the uploaded document.
        result = validate_upload(
            filename=uploaded_file.filename,
            data=data,
            limits=limits,
        )

        # Step 2: Store the document securely.
        storage_dir = Path(config["STORAGE_DIR"]) / "tmp"
        storage_dir.mkdir(parents=True, exist_ok=True)

        destination = storage_dir / result.stored_name

        # Exclusive creation prevents overwriting files.
        with destination.open("xb") as stored_file:
            stored_file.write(data)

        # Step 3: Extract text and detect sensitive information.
        try:
            findings, _pages = scan_file(
                destination,
                destination.suffix.lower().lstrip("."),
                limits,
                config["KEYWORDS"] or [],
                config["MIN_CONFIDENCE"],
                config["HMAC_KEY"],
            )

        except ExtractionFailed as error:
            message = (
                "This PDF has no selectable text layer."
                if error.code == "NO_TEXT_LAYER"
                else "Could not extract text from this document."
            )

            return render_template(
                "upload.html",
                error=message,
            ), 422

        # Step 4: Display masked detection results.
        return render_template(
            "detect.html",
            findings=findings,
            error=None,
        ), 200

    except UploadRejected as error:
        return render_template(
            "upload.html",
            error=ERROR_MESSAGES.get(
                error.code,
                "Upload failed.",
            ),
        ), 400

    except OSError:
        current_app.logger.exception("Unable to store or read uploaded document")

        return render_template(
            "upload.html",
            error="Unable to process the uploaded document.",
        ), 500

    finally:
        # Remove the temporary file after processing.
        if destination is not None:
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                current_app.logger.warning("Unable to remove temporary upload")


@bp.errorhandler(RequestEntityTooLarge)
def upload_too_large(error):
    return render_template(
        "upload.html",
        error=ERROR_MESSAGES["FILE_TOO_LARGE"],
    ), 413
