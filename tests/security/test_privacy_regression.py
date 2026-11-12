from __future__ import annotations

import io
from securewaste import create_app


def create_test_client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_sensitive_values_masked_in_html_response() -> None:
    """Verify raw emails, phone numbers, and keywords do not leak into rendered HTML."""
    client = create_test_client()
    secret_email = "alice.secret@example.com"
    secret_phone = "(202) 555-0104"
    secret_keyword = "CONFIDENTIAL"

    content = f"Contact: {secret_email}\nPhone: {secret_phone}\nStatus: {secret_keyword}".encode("utf-8")
    data = {"file": (io.BytesIO(content), "privacy_test.txt")}

    response = client.post("/detect", data=data, content_type="multipart/form-data", follow_redirects=True)
    html = response.get_data(as_text=True)

    # Ensure raw PII does not appear unmasked in the HTML response
    assert secret_email not in html
    assert secret_phone not in html


def test_error_messages_do_not_leak_payload_content() -> None:
    """Ensure rejected uploads never echo raw file contents or sensitive strings in error responses."""
    client = create_test_client()
    sensitive_payload = b"SECRET_TOKEN_998877 not a real pdf"
    data = {"file": (io.BytesIO(sensitive_payload), "bad.pdf")}

    response = client.post("/detect", data=data, content_type="multipart/form-data", follow_redirects=True)
    html = response.get_data(as_text=True)

    assert "SECRET_TOKEN_998877" not in html


def test_xss_escaping_in_filename_and_content() -> None:
    """Verify Jinja2 auto-escaping prevents XSS via filenames or text content."""
    client = create_test_client()
    malicious_filename = "<script>alert('xss')</script>.txt"
    content = b"Normal document text with no PII."
    data = {"file": (io.BytesIO(content), malicious_filename)}

    response = client.post("/detect", data=data, content_type="multipart/form-data", follow_redirects=True)
    html = response.get_data(as_text=True)

    assert "<script>alert('xss')</script>" not in html