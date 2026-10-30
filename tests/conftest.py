











"""Shared pytest fixtures: a fresh app with its own temporary database and storage for every test."""
 
import pytest
 
from securewaste import create_app
from securewaste.db.connection import get_db, init_db
 
TEST_SECRET = "test-secret-key-not-for-production"  # noqa: S105 - dummy test value
TEST_HMAC = "test-hmac-key-not-for-production"
 
 
@pytest.fixture(autouse=True)
def env(monkeypatch):
    # Tests control the environment themselves: never read the developer's real .env file.
    monkeypatch.setattr("securewaste.config.load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setenv("SECUREWASTE_SECRET_KEY", TEST_SECRET)
    monkeypatch.setenv("SECUREWASTE_HMAC_KEY", TEST_HMAC)
 
 
@pytest.fixture
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "STORAGE_DIR": tmp_path / "storage",
            "DATABASE_PATH": tmp_path / "test.db",
        }
    )
    with app.app_context():
        init_db()
    yield app
 
 
@pytest.fixture
def client(app):
    return app.test_client()
 
 
@pytest.fixture
def db(app):
    with app.app_context():
        yield get_db()
 
