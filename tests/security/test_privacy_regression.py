"""Privacy tests for POST /documents with real .txt and .pdf uploads."""

from __future__ import annotations

import io

import pytest

try:
    import pymupdf as fitz
except ImportError:  # older PyMuPDF
    import fitz

EMAIL = "alice.secret@example.com"
PHONE = "(202) 555-0104"
KEYWORD = "CONFIDENTIAL"
TOKEN = "SECRET_TOKEN_998877"  # noqa: S105 - Synthetic test data

# How your UI shows the masked email (from your screenshot). Adjust if you change masking.
MASKED_EMAIL = "a\u2022\u2022\u2022@e\u2022\u2022\u2022.com"

LINES = [f"Contact: {EMAIL}", f"Phone: {PHONE}", f"Status: {KEYWORD}"]


def make_txt() -> bytes:
    return "\n".join(LINES).encode("utf-8")


def make_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in LINES:
        page.insert_text((72, y), line, fontsize=12)
        y += 20
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def client(no_csrf_client):
    """In this module every test uses the CSRF-off client (see conftest.py)."""
    return no_csrf_client


SENSITIVE_UPLOADS = [
    pytest.param("privacy_test.txt", make_txt, id="txt"),
    pytest.param("privacy_test.pdf", make_pdf, id="pdf"),
]

BAD_UPLOADS = [
    pytest.param("bad.pdf", f"{TOKEN} not a real pdf".encode(), id="fake-pdf"),
    pytest.param("evil.exe", f"MZ {TOKEN} not a real pdf".encode(), id="exe"),
]


def upload(client, filename: str, content: bytes):
    response = client.post(
        "/documents",
        data={"file": (io.BytesIO(content), filename)},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    # Guard against a vacuous pass: a CSRF error page contains none of our secrets.
    assert b"CSRF_INVALID" not in response.data, "CSRF blocked the upload; test proves nothing"
    assert response.status_code != 404, "/documents not found"
    assert response.status_code < 500
    return response


@pytest.mark.parametrize("filename, factory", SENSITIVE_UPLOADS)
def test_sensitive_values_masked_in_html_response(client, filename, factory):
    response = upload(client, filename, factory())
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert MASKED_EMAIL in html, "upload did not produce a masked finding"
    assert EMAIL not in html
    assert PHONE not in html
    assert KEYWORD not in html


@pytest.mark.parametrize("filename, factory", SENSITIVE_UPLOADS)
def test_sensitive_values_not_exposed_in_logs(client, caplog, capfd, filename, factory):
    with caplog.at_level("DEBUG"):
        response = upload(client, filename, factory())
    assert response.status_code == 200

    out, err = capfd.readouterr()
    everything = caplog.text + out + err
    assert EMAIL not in everything
    assert PHONE not in everything
    assert KEYWORD not in everything


@pytest.mark.parametrize("filename, payload", BAD_UPLOADS)
def test_error_messages_do_not_leak_payload_content(client, filename, payload):
    html = upload(client, filename, payload).get_data(as_text=True)
    assert TOKEN not in html
    assert "not a real pdf" not in html


@pytest.mark.parametrize("filename, payload", BAD_UPLOADS)
def test_rejected_upload_does_not_leak_sensitive_data_in_logs(client, caplog, capfd, filename, payload):
    with caplog.at_level("DEBUG"):
        upload(client, filename, payload)

    out, err = capfd.readouterr()
    everything = caplog.text + out + err
    assert TOKEN not in everything
    assert "not a real pdf" not in everything


def test_xss_escaping_in_filename(client):
    html = upload(client, "<script>alert('xss')</script>.txt", b"Normal text, no PII.").get_data(as_text=True)
    assert "<script>alert" not in html
    assert "alert('xss')" not in html


def test_xss_escaping_in_content(client):
    payload = b"<script>alert('xss2')</script>\n<img src=x onerror=alert(1)>\nPlain text."
    html = upload(client, "xss_content.txt", payload).get_data(as_text=True)
    assert "<script>alert('xss2')" not in html
    assert "<img src=x onerror" not in html
