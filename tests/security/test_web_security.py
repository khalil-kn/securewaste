"""Security tests ST-06 (CSRF) and ST-11 (headers) from docs/04-threat-model.md, plus safe errors."""

from securewaste import create_app


def test_security_headers_on_every_page(client):  # ST-11
    headers = client.get("/").headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert headers["Cache-Control"] == "no-store"


def test_post_without_csrf_token_is_rejected(tmp_path):  # ST-06
    app = create_app({"TESTING": True, "STORAGE_DIR": tmp_path / "s", "DATABASE_PATH": tmp_path / "t.db"})

    @app.post("/_probe")
    def probe():
        return "changed"

    response = app.test_client().post("/_probe", data={"x": "1"})
    assert response.status_code == 400
    assert b"CSRF_INVALID" in response.data


def test_api_errors_are_json(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


def test_unexpected_error_hides_details(tmp_path):
    app = create_app({"TESTING": True, "STORAGE_DIR": tmp_path / "s", "DATABASE_PATH": tmp_path / "t.db"})

    @app.get("/_boom")
    def boom():
        raise RuntimeError("secret detail 4242424242424242")

    response = app.test_client().get("/_boom")
    assert response.status_code == 500
    assert b"secret detail" not in response.data
    assert b"4242" not in response.data
    assert b"Traceback" not in response.data
