"""Design shell: no inline styles (CSP), nav state, self-hosted fonts, upload form contract unchanged."""

import io
import re
from unittest.mock import patch

import pymupdf
import pytest

from securewaste import create_app
from securewaste.core.extraction import PageText


@pytest.fixture
def client(tmp_path):
    app = create_app(
        {"TESTING": True, "WTF_CSRF_ENABLED": False, "STORAGE_DIR": tmp_path / "s", "DATABASE_PATH": tmp_path / "t.db"}
    )
    return app.test_client()


def results_page(client):
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((55, 75), "x")
        data = pdf.tobytes()
    pages = [PageText(page_number=1, text="Contact sana@example.tn")]
    with patch("securewaste.services.detect_service.extract_pages", return_value=pages):
        return client.post("/documents", data={"file": (io.BytesIO(data), "t.pdf")}, content_type="multipart/form-data")


@pytest.mark.parametrize("path", ["/", "/upload"])
def test_no_inline_styles(client, path):
    assert ' style="' not in client.get(path).get_data(as_text=True)


def test_results_page_has_no_inline_styles(client):
    assert ' style="' not in results_page(client).get_data(as_text=True)


def test_rail_marks_current_page(client):
    home = client.get("/").get_data(as_text=True)
    upload = client.get("/upload").get_data(as_text=True)
    assert len(re.findall('aria-current="page"', home)) == 1 and 'aria-label="Overview"' in home
    assert re.search(r'aria-label="Upload and scan"[^>]*aria-current="page"', upload)


@pytest.mark.parametrize(
    "name",
    [
        "public-sans-latin-wght-normal.woff2",
        "ibm-plex-mono-latin-400-normal.woff2",
        "ibm-plex-mono-latin-500-normal.woff2",
    ],
)
def test_fonts_are_served_locally(client, name):
    assert client.get(f"/static/fonts/{name}").status_code == 200


def test_csp_allows_no_external_hosts(client):
    csp = client.get("/").headers["Content-Security-Policy"]
    assert "http" not in csp


def test_upload_form_contract_unchanged(client):
    body = client.get("/upload").get_data(as_text=True)
    assert 'name="file"' in body and 'name="csrf_token"' in body and 'action="/documents"' in body
