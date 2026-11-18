"""Every presentation state of a scan is honest: no state implies a classification that did not happen."""

import io

import pymupdf
import pytest

from securewaste import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(
        {"TESTING": True, "WTF_CSRF_ENABLED": False, "STORAGE_DIR": tmp_path / "s", "DATABASE_PATH": tmp_path / "t.db"}
    )
    return app.test_client()


def post(client, data, name):
    return client.post("/documents", data={"file": (io.BytesIO(data), name)}, content_type="multipart/form-data")


def pdf_bytes(text=None):
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        if text:
            page.insert_text((55, 75), text)
        return pdf.tobytes()


def test_pdf_without_text_layer_is_explained_and_not_classified(client):
    r = post(client, pdf_bytes(), "scan.pdf")
    body = r.get_data(as_text=True)
    assert r.status_code == 422
    assert "no selectable text layer" in body
    assert "Document classification" not in body and "Scan results" not in body


@pytest.mark.parametrize(
    ("data", "name"),
    [(b"MZ\x90\x00 not a document", "tool.exe"), (b"%PDF-1.7 broken", "broken.pdf"), (b"", "empty.txt")],
)
def test_rejected_upload_shows_an_error_and_no_classification(client, data, name):
    r = post(client, data, name)
    body = r.get_data(as_text=True)
    assert r.status_code in (400, 422)
    assert 'role="alert"' in body
    assert "Document classification" not in body


def test_missing_model_file_falls_back_to_rules_and_says_so(client, tmp_path, monkeypatch):
    """No model artifact: the label comes from the rules, and the page asks for human review."""
    monkeypatch.setenv("SECUREWASTE_MODEL_PATH", str(tmp_path / "missing-model.pkl"))
    r = post(client, pdf_bytes("Contact sana@example.tn about the payroll"), "doc.pdf")
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "Document classification" in body
    assert "ML model unavailable; rule-based fallback" in body
    assert "Low ML confidence" not in body  # no ML ran, so no ML confidence to warn about
    assert "sana@example.tn" not in body
