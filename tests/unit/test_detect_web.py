"""Web tests for the /detect page (Issue #5): the form renders and a POST returns masked findings."""

from securewaste import create_app


def make_app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,  # CSRF is covered by tests/security; keep these deterministic
            "STORAGE_DIR": tmp_path / "storage",
            "DATABASE_PATH": tmp_path / "test.db",
        }
    )


def test_detect_form_renders(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    response = client.get("/detect")
    assert response.status_code == 200
    assert b"Detect sensitive data" in response.data
    assert b"name=\"text\"" in response.data


def test_detect_post_returns_masked_findings(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    response = client.post("/detect", data={"text": "Contact: sana@example.tn, tel +216 98 123 456"})
    assert response.status_code == 200
    # Masked values are shown; the raw e-mail never appears.
    assert b"s\xe2\x80\xa2\xe2\x80\xa2\xe2\x80\xa2@e\xe2\x80\xa2\xe2\x80\xa2\xe2\x80\xa2.tn" in response.data
    assert b"sana@example.tn" not in response.data
    assert b"email" in response.data
    assert b"phone" in response.data


def test_detect_post_empty_text_shows_no_findings(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    response = client.post("/detect", data={"text": "nothing sensitive here"})
    assert response.status_code == 200
    assert b"No sensitive data found" in response.data
