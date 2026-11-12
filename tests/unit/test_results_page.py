"""Issue #6: Test the results page using the validated scanning workflow."""

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


def make_pdf(text="Test document"):
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((55, 75), text)
        return pdf.tobytes()


def upload_document(client):
    return client.post(
        "/documents",
        data={
            "file": (
                io.BytesIO(make_pdf()),
                "test.pdf",
            )
        },
        content_type="multipart/form-data",
    )


def test_results_page_uses_existing_detection_and_masks_values(tmp_path):
    app = make_app(tmp_path)

    pages = [
        PageText(
            page_number=2,
            text="Contact sana@example.tn or +216 98 123 456",
        )
    ]

    with patch(
        "securewaste.services.detect_service.extract_pages",
        return_value=pages,
    ):
        response = upload_document(app.test_client())

    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Scan results" in body
    assert "Page 2" in body
    assert "s•••@e•••.tn" in body
    assert "sana@example.tn" not in body
    assert "+216 98 123 456" not in body
    assert "Recommended action" in body


def test_results_page_empty_state(tmp_path):
    app = make_app(tmp_path)

    pages = [
        PageText(
            page_number=1,
            text="Hello world",
        )
    ]

    with patch(
        "securewaste.services.detect_service.extract_pages",
        return_value=pages,
    ):
        response = upload_document(app.test_client())

    assert response.status_code == 200
    assert b"No findings detected" in response.data
