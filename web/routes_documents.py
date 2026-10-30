from flask import (
    Blueprint,
    render_template,
    request,
    current_app
)

from pathlib import Path

from core.upload import validate_upload, UploadError


documents_bp = Blueprint("documents", __name__)

# Project root / tmp
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TMP_FOLDER = PROJECT_ROOT / "tmp"


@documents_bp.route("/upload", methods=["GET"])
def upload_page():
    return render_template("upload.html", error=None)


@documents_bp.route("/documents", methods=["POST"])
def upload_document():

    uploaded_file = request.files.get("file")

    try:
        # Validate the uploaded file
        result = validate_upload(uploaded_file)

        # Create temporary directory if necessary
        TMP_FOLDER.mkdir(parents=True, exist_ok=True)

        # Save using the generated safe filename
        destination = TMP_FOLDER / result["filename"]

        try:
            destination.write_bytes(result["content"])
        except OSError:
            destination.unlink(missing_ok=True)
            raise

        return render_template(
            "upload.html",
            error=None,
            success="File uploaded successfully!",
            filename=result["filename"],
            fingerprint=result["fingerprint"]
        )

    except UploadError as error:

        error_messages = {
            "FILE_EMPTY": "Please select a file.",
            "FILE_TOO_LARGE": "File exceeds the 10 MB limit.",
            "INVALID_FILE_TYPE": "Only valid PDF and TXT files are accepted.",
            "PDF_INVALID": "The PDF file is invalid or corrupted.",
            "PDF_ENCRYPTED": "Password-protected PDFs are not accepted.",
            "PDF_TOO_MANY_PAGES": "PDF cannot contain more than 100 pages."
        }

        return render_template(
            "upload.html",
            error=error_messages.get(str(error), "Upload failed.")
        ), 400

    except OSError:
        current_app.logger.exception("Could not save uploaded file")
        return render_template(
            "upload.html",
            error="Could not save the uploaded file."
        ), 500