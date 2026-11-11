"""Web tests for the /detect page (Issue #5): the PDF-upload form renders and a scan returns
masked findings. The PDF→text step (extract_pages) belongs to Milestone 1 issue #4, so it is
mocked here — we test the detection UI against its output contract."""

import io
from unittest.mock import patch

from securewaste import create_app
from securewaste.core.extraction import PageText


def make_app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,  # CSRF is covered by tests/security; keep these deterministic
            "STORAGE_DIR": tmp_path / "storage",
            "DATABASE_PATH": tmp_path / "test.db",
        }
    )


def sample_pages(*texts):
    return [PageText(page_number=i + 1, text=t) for i, t in enumerate(texts)]


def test_detect_form_renders(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    response = client.get("/detect")
    assert response.status_code == 200
    assert b"Detect sensitive data" in response.data
    assert b'name="document"' in response.data


def test_detect_post_scans_extracted_pages(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    pages = sample_pages("Contact: sana@example.tn, tel +216 98 123 456")
    with patch("securewaste.services.detect_service.extract_pages", return_value=pages):
        response = client.post(
            "/detect",
            data={"document": (io.BytesIO(b"%PDF-1.4 fake contents"), "sample.pdf")},
            content_type="multipart/form-data",
        )
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "s•••@e•••.tn" in body  # masked value is shown
    assert "sana@example.tn" not in body  # raw value never appears (ST-01)
    assert "email" in body and "phone" in body
    assert "page 1" in body


def test_detect_post_no_sensitive_data(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    scanned = sample_pages("nothing sensitive here")
    with patch("securewaste.services.detect_service.extract_pages", return_value=scanned):
        response = client.post(
            "/detect",
            data={"document": (io.BytesIO(b"%PDF-1.4 fake contents"), "sample.pdf")},
            content_type="multipart/form-data",
        )
    assert response.status_code == 200
    assert "No sensitive data found" in response.get_data(as_text=True)


def test_detect_post_missing_file_shows_error(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    response = client.post("/detect", data={}, content_type="multipart/form-data")
    assert response.status_code == 200
    assert "Please choose a PDF file" in response.get_data(as_text=True)


def _render_pdf(texts):
    import pymupdf

    with pymupdf.open() as pdf:
        for text in texts:
            page = pdf.new_page()
            page.insert_text((55, 75), text, fontsize=12)
        return pdf.tobytes()


def test_detect_post_with_real_pdf_extraction(tmp_path):
    """Integration: real extract_pages (issue #4) feeds the detection engine end to end."""
    app = make_app(tmp_path)
    client = app.test_client()
    pdf_bytes = _render_pdf(["Contact: sana@example.tn, tel +216 98 123 456"])
    response = client.post(
        "/detect",
        data={"document": (io.BytesIO(pdf_bytes), "sample.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "s•••@e•••.tn" in body
    assert "sana@example.tn" not in body
    assert "page 1" in body
