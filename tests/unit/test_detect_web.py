"""Tests for the validated document scanning workflow."""

import io
from unittest.mock import patch

import pymupdf

from securewaste import create_app
from securewaste.core.extraction import PageText


def make_app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "STORAGE_DIR": tmp_path / "storage",
            "DATABASE_PATH": tmp_path / "test.db",
        }
    )


def sample_pages(*texts):
    return [PageText(page_number=i + 1, text=text) for i, text in enumerate(texts)]


def render_pdf(texts):
    with pymupdf.open() as pdf:
        for text in texts:
            page = pdf.new_page()
            page.insert_text((55, 75), text, fontsize=12)
        return pdf.tobytes()


def upload_pdf(client, pdf_bytes):
    return client.post(
        "/documents",
        data={"file": (io.BytesIO(pdf_bytes), "sample.pdf")},
        content_type="multipart/form-data",
    )


def test_detect_redirects_to_upload(tmp_path):
    client = make_app(tmp_path).test_client()

    for method in ("get", "post"):
        response = getattr(client, method)("/detect")
        assert response.status_code == 303
        assert response.headers["Location"].endswith("/upload")


def test_upload_form_renders(tmp_path):
    client = make_app(tmp_path).test_client()
    response = client.get("/upload")

    assert response.status_code == 200
    assert b'name="file"' in response.data
    assert b"/documents" in response.data


def test_document_scans_extracted_pages(tmp_path):
    client = make_app(tmp_path).test_client()
    pages = sample_pages("Contact: sana@example.tn, tel +216 98 123 456")
    pdf_bytes = render_pdf(["Test document"])

    with patch(
        "securewaste.services.detect_service.extract_pages",
        return_value=pages,
    ):
        response = upload_pdf(client, pdf_bytes)

    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert "sana@example.tn" not in body
    assert "s•••@e•••.tn" in body
    assert "email" in body.lower()
    assert "phone" in body.lower()
    assert "page 1" in body.lower()


def test_document_no_sensitive_data(tmp_path):
    client = make_app(tmp_path).test_client()
    pdf_bytes = render_pdf(["Nothing sensitive here"])

    with patch(
        "securewaste.services.detect_service.extract_pages",
        return_value=sample_pages("Nothing sensitive here"),
    ):
        response = upload_pdf(client, pdf_bytes)

    assert response.status_code == 200
    assert "No sensitive data found" in response.get_data(as_text=True)


def test_document_missing_file_shows_error(tmp_path):
    client = make_app(tmp_path).test_client()

    response = client.post(
        "/documents",
        data={},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "Please select a file" in response.get_data(as_text=True)


def test_document_with_real_pdf_extraction(tmp_path):
    client = make_app(tmp_path).test_client()
    pdf_bytes = render_pdf(["Contact: sana@example.tn, tel +216 98 123 456"])

    response = upload_pdf(client, pdf_bytes)

    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert "sana@example.tn" not in body
    assert "s•••@e•••.tn" in body
    assert "page 1" in body.lower()

    temporary_files = list((tmp_path / "storage" / "tmp").glob("*"))
    assert temporary_files == []
