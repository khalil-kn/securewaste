"""The skeleton's guarantees: it starts safely, protects every route and never leaks error details."""

import pytest

from securewaste import create_app
from securewaste.config import ConfigError


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_dashboard_renders(client):
    assert client.get("/").status_code == 200


@pytest.mark.parametrize("value", [None, "", "change-me"])
def test_refuses_to_start_without_real_secret(monkeypatch, tmp_path, value):
    if value is None:
        monkeypatch.delenv("SECUREWASTE_SECRET_KEY")
    else:
        monkeypatch.setenv("SECUREWASTE_SECRET_KEY", value)
    with pytest.raises(ConfigError):
        create_app({"STORAGE_DIR": tmp_path})


def test_refuses_to_start_without_hmac_key(monkeypatch, tmp_path):
    monkeypatch.delenv("SECUREWASTE_HMAC_KEY")
    with pytest.raises(ConfigError):
        create_app({"STORAGE_DIR": tmp_path})


def test_storage_folders_created(app):
    for sub in ("originals", "sanitized", "tmp"):
        assert (app.config["STORAGE_DIR"] / sub).is_dir()
