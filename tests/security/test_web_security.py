"""Security tests ST-06 (CSRF) and ST-11 (headers) from docs/04-threat-model.md, plus safe errors."""

from __future__ import annotations

import io

import pytest


@pytest.mark.parametrize("path", ["/", "/documents", "/does-not-exist", "/api/does-not-exist"])
def test_security_headers_on_every_page(client, path):  # ST-11
    headers = client.get(path).headers
    csp = headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp, path
    assert "frame-ancestors 'none'" in csp, path
    assert headers.get("X-Frame-Options") == "DENY", path
    assert headers.get("X-Content-Type-Options") == "nosniff", path
    assert headers.get("Referrer-Policy") == "no-referrer", path
    assert headers.get("Cache-Control") == "no-store", path


def test_post_without_csrf_token_is_rejected(app_factory):  # ST-06
    app = app_factory()  # CSRF stays ON (default)

    @app.post("/_probe")
    def probe():
        return "changed"

    response = app.test_client().post("/_probe", data={"x": "1"})
    assert response.status_code == 400
    assert b"CSRF_INVALID" in response.data


def test_real_upload_without_csrf_token_is_rejected(client):  # ST-06 on the real endpoint
    # `client` from conftest has CSRF ON
    response = client.post(
        "/documents",
        data={"file": (io.BytesIO(b"Contact: alice.secret@example.com"), "a.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert b"CSRF_INVALID" in response.data
    assert b"alice.secret" not in response.data


def test_api_errors_are_json(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


def test_unexpected_error_hides_details(app_factory):
    app = app_factory(PROPAGATE_EXCEPTIONS=False)  # get the real 500 page, not a re-raise

    @app.get("/_boom")
    def boom():
        raise RuntimeError("secret detail 4242424242424242")

    response = app.test_client().get("/_boom")
    assert response.status_code == 500
    assert b"secret detail" not in response.data
    assert b"4242" not in response.data
    assert b"Traceback" not in response.data


def test_unexpected_error_does_not_log_sensitive_values(app_factory, caplog):
    """Unexpected application errors must not expose sensitive values in logs."""
    app = app_factory(PROPAGATE_EXCEPTIONS=False)

    @app.get("/_boom")
    def boom():
        raise RuntimeError("secret detail 4242424242424242")

    with caplog.at_level("DEBUG"):
        app.test_client().get("/_boom")
    assert "4242424242424242" not in caplog.text
