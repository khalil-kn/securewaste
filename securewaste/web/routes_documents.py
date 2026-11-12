
"""Document upload routes for Secure Waste."""

from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
)
from werkzeug.exceptions import RequestEntityTooLarge

from securewaste.core.upload import (
    Limits,
    UploadRejected,
    validate_upload,
)

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

    try:
        # Read only up to the configured limit plus one byte.
        data = uploaded_file.stream.read(limits.max_bytes + 1)

        result = validate_upload(
            filename=uploaded_file.filename,
            data=data,
            limits=limits,
        )

        # Store uploaded content outside the public static directory.
        storage_dir = Path(config["STORAGE_DIR"]) / "tmp"
        storage_dir.mkdir(parents=True, exist_ok=True)

        destination = storage_dir / result.stored_name

        # Exclusive creation prevents overwriting an existing file.
        with destination.open("xb") as stored_file:
            stored_file.write(data)

        return render_template(
            "upload.html",
            success="File uploaded successfully!",
            filename=result.display_name,
            fingerprint=result.sha256,
        ), 201

    except UploadRejected as error:
        return render_template(
            "upload.html",
            error=ERROR_MESSAGES.get(error.code, "Upload failed."),
        ), 400

    except OSError:
        current_app.logger.exception("Unable to store uploaded document")
        return render_template(
            "upload.html",
            error="Unable to save the uploaded document.",
        ), 500


@bp.errorhandler(RequestEntityTooLarge)
def upload_too_large(error):
    return render_template(
        "upload.html",
        error=ERROR_MESSAGES["FILE_TOO_LARGE"],
    ), 413
