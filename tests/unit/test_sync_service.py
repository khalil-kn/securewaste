"""Metadata sync: real HTTP requests to a fake cloud server, so the outgoing request can be inspected."""

import io
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace
from unittest.mock import patch

import pymupdf
import pytest

from securewaste import create_app
from securewaste.core.detection.catalogue import Category
from securewaste.core.extraction import PageText
from securewaste.services.sync_service import RISK_FOR_LABEL, build_event, send_event, sync_scan

TOKEN = "test-token-not-a-real-secret"  # noqa: S105
ALLOWED_KEYS = {"event_id", "timestamp", "classification", "risk", "counts"}
FINDINGS = [
    SimpleNamespace(category=Category.EMAIL, occurrences=2),
    SimpleNamespace(category=Category.PHONE, occurrences=1),
]
CLASSIFICATION = {"label": "Confidential"}


class FakeCloud:
    """Answers every POST with the configured status/body and remembers what it received."""

    def __init__(self, status=201, body=None, delay=0, headers=None):
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                outer.requests.append({"path": self.path, "headers": dict(self.headers), "body": raw})
                time.sleep(delay)
                payload = json.loads(raw)
                answer = body if body is not None else json.dumps({"event_id": payload["event_id"], "status": "stored"})
                self.send_response(status)
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(answer.encode())

            def log_message(self, *args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def cloud():
    made = []

    def make(**kwargs):
        made.append(FakeCloud(**kwargs))
        return made[-1]

    yield make
    for c in made:
        c.close()


def cfg(url, **extra):
    return {"SYNC_ENABLED": True, "CLOUD_API_URL": url, "CLOUD_API_TOKEN": TOKEN, "SYNC_TIMEOUT_SECONDS": 1, **extra}


# --- the outgoing request ---------------------------------------------------------------------------------


def test_outgoing_request_contains_only_allowed_metadata(cloud):
    server = cloud()
    result = sync_scan(cfg(server.url), CLASSIFICATION, FINDINGS)

    assert result.status == "stored"
    sent = server.requests[0]
    payload = json.loads(sent["body"])
    assert set(payload) == ALLOWED_KEYS
    assert payload["classification"] == "Confidential" and payload["risk"] == RISK_FOR_LABEL["Confidential"]
    assert payload["counts"] == {"email": 2, "phone": 1, "keyword": 0}
    assert sent["path"] == "/api/v1/scans"
    assert sent["headers"]["Authorization"] == f"Bearer {TOKEN}"
    assert TOKEN not in sent["path"] and TOKEN not in sent["body"].decode()


def test_event_ids_are_unique_uuids_per_scan():
    ids = {build_event(CLASSIFICATION, FINDINGS)["event_id"] for _ in range(5)}
    assert len(ids) == 5


# --- every failure keeps the local result usable ----------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (409, "already_stored"),
        (401, "unauthorized"),
        (403, "forbidden"),
        (400, "rejected"),
        (500, "server_error"),
        (503, "server_error"),
    ],
)
def test_http_errors_map_to_a_status(cloud, status, expected):
    result = sync_scan(cfg(cloud(status=status, body="{}").url), CLASSIFICATION, FINDINGS)
    assert result.status == expected


@pytest.mark.parametrize("body", ["not json", "[]", '{"event_id": "someone-else"}'])
def test_unexpected_success_body_is_not_reported_as_stored(cloud, body):
    assert sync_scan(cfg(cloud(body=body).url), CLASSIFICATION, FINDINGS).status == "invalid_response"


def test_timeout_is_bounded(cloud):
    started = time.monotonic()
    result = sync_scan(cfg(cloud(delay=2).url, SYNC_TIMEOUT_SECONDS=0.2), CLASSIFICATION, FINDINGS)
    assert result.status == "unreachable" and time.monotonic() - started < 1.5


def test_connection_refused_is_unreachable():
    assert sync_scan(cfg("http://127.0.0.1:9"), CLASSIFICATION, FINDINGS).status == "unreachable"


def test_redirects_are_not_followed_so_the_token_cannot_leak(cloud):
    other = cloud()
    redirecting = cloud(status=307, body="{}", headers={"Location": f"{other.url}/steal"})
    assert sync_scan(cfg(redirecting.url), CLASSIFICATION, FINDINGS).status == "server_error"
    assert other.requests == []


def test_disabled_and_missing_classification_send_nothing(cloud):
    server = cloud()
    assert sync_scan(cfg(server.url, SYNC_ENABLED=False), CLASSIFICATION, FINDINGS).status == "disabled"
    assert sync_scan(cfg(server.url), None, FINDINGS).status == "skipped"
    assert server.requests == []


@pytest.mark.parametrize("url", ["", "http://cloud.example.com", "ftp://127.0.0.1", "file:///etc/passwd"])
def test_unsafe_or_missing_url_is_not_used(url):
    assert send_event(cfg(url), build_event(CLASSIFICATION, FINDINGS)).status == "not_configured"
    assert send_event(cfg("http://127.0.0.1:1", CLOUD_API_TOKEN=""), build_event(CLASSIFICATION, [])).status == (
        "not_configured"
    )


def test_token_and_payload_never_reach_the_logs(cloud, caplog):
    with caplog.at_level("DEBUG"):
        sync_scan(cfg(cloud(status=500, body="{}").url), CLASSIFICATION, FINDINGS)
    assert TOKEN not in caplog.text and "Confidential" not in caplog.text


# --- the results page -------------------------------------------------------------------------------------


def results_page(tmp_path, **config):
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "STORAGE_DIR": tmp_path / "s",
            "DATABASE_PATH": tmp_path / "t.db",
            **config,
        }
    )
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((55, 75), "x")
        data = pdf.tobytes()
    pages = [PageText(page_number=1, text="Contact sana@example.tn")]
    with patch("securewaste.services.detect_service.extract_pages", return_value=pages):
        return app.test_client().post(
            "/documents", data={"file": (io.BytesIO(data), "secret-name.pdf")}, content_type="multipart/form-data"
        )


def test_page_shows_stored_only_after_a_201(tmp_path, cloud):
    server = cloud()
    body = results_page(
        tmp_path, SYNC_ENABLED=True, CLOUD_API_URL=server.url, CLOUD_API_TOKEN=TOKEN, SYNC_TIMEOUT_SECONDS=1
    ).get_data(as_text=True)
    assert "Metadata stored in the cloud." in body
    sent = json.loads(server.requests[0]["body"])
    assert set(sent) == ALLOWED_KEYS
    raw = server.requests[0]["body"].decode()
    assert "sana@example.tn" not in raw and "secret-name" not in raw and "Contact" not in raw


def test_cloud_down_keeps_local_results_and_never_says_stored(tmp_path):
    response = results_page(
        tmp_path, SYNC_ENABLED=True, CLOUD_API_URL="http://127.0.0.1:9", CLOUD_API_TOKEN=TOKEN, SYNC_TIMEOUT_SECONDS=0.5
    )
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "s•••@e•••.tn" in body and "Scan results" in body
    assert "Not sent: the cloud could not be reached" in body
    assert "stored in the cloud" not in body and TOKEN not in body


def test_sync_off_by_default(tmp_path):
    body = results_page(tmp_path).get_data(as_text=True)
    assert "Cloud sync is off. Nothing was sent." in body


@pytest.mark.parametrize("label", list(RISK_FOR_LABEL))
def test_payload_is_accepted_by_the_real_api_validator(label):
    """Contract test: the cloud API's own parser accepts what the client builds for every label."""
    from cloud_api.validation import parse_scan_payload

    event = parse_scan_payload(build_event({"label": label}, FINDINGS))
    assert event.classification == label and event.risk == RISK_FOR_LABEL[label]
