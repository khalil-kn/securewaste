"""Optional metadata sync to the cloud API (SCRUM-30).

Sends ONLY what cloud_api/validation.py allows: event_id, timestamp, classification, risk and
aggregate counts. Never the document, its text, file name, matched values, or the token in logs.
A cloud error never stops the local result: every failure becomes a status the page can show.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib import error, request
from urllib.parse import urlsplit

log = logging.getLogger(__name__)

# Page labels -> the API's three risk values. To be confirmed with Jawed.
RISK_FOR_LABEL = {"Public": "Low", "Internal": "Low", "Confidential": "Medium", "Highly Confidential": "High"}
COUNT_KEYS = ("email", "phone", "keyword")
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}

# Status codes the page can show. "stored" is used only after a 201 from the server.
MESSAGES = {
    "disabled": "Cloud sync is off. Nothing was sent.",
    "skipped": "Not sent: there is no classification to report.",
    "stored": "Metadata stored in the cloud.",
    "already_stored": "Metadata was already stored (duplicate event).",
    "not_configured": "Cloud sync is on but the URL or token is not configured. Nothing was sent.",
    "unauthorized": "Not sent: the cloud rejected the access token (401).",
    "forbidden": "Not sent: this role may not store scan events (403).",
    "rejected": "Not sent: the cloud rejected the metadata format.",
    "server_error": "Not sent: the cloud had an error. Your local results are unaffected.",
    "unreachable": "Not sent: the cloud could not be reached. Your local results are unaffected.",
    "invalid_response": "Unclear: the cloud answered in an unexpected way, so the sync is not confirmed.",
}


@dataclass(frozen=True)
class SyncResult:
    status: str

    @property
    def message(self) -> str:
        return MESSAGES[self.status]

    @property
    def ok(self) -> bool:
        return self.status in ("stored", "already_stored")


def build_event(classification: dict, findings: list) -> dict:
    """The metadata-only payload. Nothing else from the scan is ever added to it."""
    counts = dict.fromkeys(COUNT_KEYS, 0)
    for finding in findings:
        key = finding.category.value
        if key in counts:
            counts[key] += finding.occurrences
    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
        "classification": classification["label"],
        "risk": RISK_FOR_LABEL[classification["label"]],
        "counts": counts,
    }


class _NoRedirect(request.HTTPRedirectHandler):
    """Never follow redirects: urllib would forward the Authorization header to the new address."""

    def redirect_request(self, *args, **kwargs):
        return None


_opener = request.build_opener(_NoRedirect)


def _url_is_safe(url: str) -> bool:
    """The token travels in a header: require https, or plain http only to this machine."""
    parts = urlsplit(url)
    return parts.scheme == "https" or (parts.scheme == "http" and parts.hostname in LOCAL_HOSTS)


def send_event(config: dict, payload: dict) -> SyncResult:
    """POST the event. Never raises: any failure becomes a SyncResult."""
    if (
        not config.get("CLOUD_API_URL")
        or not config.get("CLOUD_API_TOKEN")
        or not _url_is_safe(config["CLOUD_API_URL"])
    ):
        return SyncResult("not_configured")
    http_request = request.Request(  # noqa: S310 - scheme is checked by _url_is_safe
        f"{config['CLOUD_API_URL']}/api/v1/scans",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {config['CLOUD_API_TOKEN']}"},
        method="POST",
    )
    try:
        with _opener.open(http_request, timeout=config["SYNC_TIMEOUT_SECONDS"]) as response:  # noqa: S310
            body = json.loads(response.read(4096))
            if response.status == 201 and isinstance(body, dict) and body.get("event_id") == payload["event_id"]:
                return SyncResult("stored")
            return SyncResult("invalid_response")
    except error.HTTPError as http_error:
        return SyncResult(
            {401: "unauthorized", 403: "forbidden", 409: "already_stored", 400: "rejected"}.get(
                http_error.code, "server_error"
            )
        )
    except (error.URLError, TimeoutError, OSError):
        return SyncResult("unreachable")
    except ValueError:  # malformed JSON from the server
        return SyncResult("invalid_response")


def sync_scan(config: dict, classification: dict | None, findings: list) -> SyncResult:
    """Entry point for the route. Logs only the status, never payloads, URLs or tokens."""
    if not config.get("SYNC_ENABLED"):
        result = SyncResult("disabled")
    elif classification is None:
        result = SyncResult("skipped")
    else:
        result = send_event(config, build_event(classification, findings))
    log.info("Cloud sync status: %s", result.status)
    return result
