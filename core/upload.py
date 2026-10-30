import hashlib
import uuid
from pathlib import Path
from io import BytesIO

from pypdf import PdfReader

MAX_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_PAGES = 100

class UploadError(Exception):
    pass

def validate_upload(file):

    if not file or not file.filename:
        raise UploadError("FILE_EMPTY")

    extension = Path(file.filename).suffix.lower()

    # Read maximum 10 MB + 1 byte
    content = file.stream.read(MAX_SIZE + 1)

    if not content:
        raise UploadError("FILE_EMPTY")

    if len(content) > MAX_SIZE:
        raise UploadError("FILE_TOO_LARGE")

    # PDF validation
    if extension == ".pdf":

        if not content.startswith(b"%PDF-"):
            raise UploadError("INVALID_FILE_TYPE")

        try:
            reader = PdfReader(BytesIO(content), strict=True)

            if reader.is_encrypted:
                raise UploadError("PDF_ENCRYPTED")

            if len(reader.pages) > MAX_PAGES:
                raise UploadError("PDF_TOO_MANY_PAGES")

        except UploadError:
            raise

        except Exception:
            raise UploadError("PDF_INVALID")

    # TXT validation
    elif extension == ".txt":

        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            raise UploadError("INVALID_FILE_TYPE")

    else:
        raise UploadError("INVALID_FILE_TYPE")

    # Generate secure filename
    safe_filename = str(uuid.uuid4()) + extension

    # Calculate SHA-256
    fingerprint = hashlib.sha256(content).hexdigest()

    return {
        "filename": safe_filename,
        "content": content,
        "fingerprint": fingerprint,
        "extension": extension
    }
