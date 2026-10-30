"""Typed errors raised by core and services. Routes map each `code` to an HTTP status (03-api.md)."""


class SecureWasteError(Exception):
    code = "INTERNAL_ERROR"

    def __init__(self, code: str | None = None, message: str = ""):
        self.code = code or self.code
        super().__init__(message or self.code)


class UploadRejected(SecureWasteError):
    """FILE_TOO_LARGE, UNSUPPORTED_TYPE, EMPTY_FILE, MALFORMED_PDF, PDF_ENCRYPTED, TOO_MANY_PAGES, NOT_UTF8."""


class ExtractionFailed(SecureWasteError):
    """NO_TEXT_LAYER, EXTRACTION_ERROR."""


class NotFound(SecureWasteError):
    code = "NOT_FOUND"


class InvalidTransition(SecureWasteError):
    code = "INVALID_TRANSITION"
