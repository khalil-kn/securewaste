"""Issue #6: results presentation consumes Jawed's findings without duplicating detection."""

import io
from unittest.mock import patch

from securewaste import create_app
from securewaste.core.extraction import PageText


def test_results_page_uses_existing_detection_and_masks_values(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "STORAGE_DIR": tmp_path / "storage",
            "DATABASE_PATH": tmp_path / "test.db",
        }
    )
    pages = [PageText(page_number=2, text="Contact sana@example.tn or +216 98 123 456")]
    with patch("securewaste.services.detect_service.extract_pages", return_value=pages):
        response = app.test_client().post(
            "/detect",
            data={"document": (io.BytesIO(b"%PDF-1.4 test"), "test.pdf")},
            content_type="multipart/form-data",
        )
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Scan results" in body
    assert "Page 2" in body
    assert "s•••@e•••.tn" in body
    assert "sana@example.tn" not in body
    assert "+216 98 123 456" not in body
    assert "Recommended action" in body


def test_results_page_empty_state(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "STORAGE_DIR": tmp_path / "storage",
            "DATABASE_PATH": tmp_path / "test.db",
        }
    )
    with patch(
        "securewaste.services.detect_service.extract_pages", return_value=[PageText(page_number=1, text="Hello world")]
    ):
        response = app.test_client().post(
            "/detect",
            data={"document": (io.BytesIO(b"%PDF-1.4 test"), "test.pdf")},
            content_type="multipart/form-data",
        )
    assert response.status_code == 200
    assert b"No findings detected" in response.data
