"""Tests of authentication, authorization and ownership of the cloud API."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime

import pytest  # type: ignore[reportMissingImports]

from cloud_api import auth
from cloud_api.app import create_app
from cloud_api.auth import AuthConfigError
from cloud_api.config import Settings

from .conftest import EMPLOYEE_A, EMPLOYEE_B

SCANS = "/api/v1/scans"


# ---- 401: authentication --------------------------------------------------- #
def test_a_request_without_a_token_is_refused(client, valid_payload):
    response = client.post(SCANS, json=valid_payload)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_a_request_with_an_unknown_token_is_refused(client, valid_payload):
    response = client.post(SCANS, json=valid_payload, headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_a_request_without_the_bearer_prefix_is_refused(client, valid_payload, auth_tokens):
    raw_token = auth_tokens["employee_a"][0]
    response = client.post(SCANS, json=valid_payload, headers={"Authorization": raw_token})
    assert response.status_code == 401


def test_an_expired_token_is_refused(client, valid_payload, bearer, monkeypatch):
    monkeypatch.setattr(auth, "_now", lambda: time.time() + 7200)  # tokens live 3600 s
    response = client.post(SCANS, json=valid_payload, headers=bearer("employee_a"))
    assert response.status_code == 401


def test_expired_and_unknown_tokens_get_the_same_answer(client, valid_payload, bearer, monkeypatch):
    unknown = client.post(SCANS, json=valid_payload, headers={"Authorization": "Bearer swt_unknown"})
    monkeypatch.setattr(auth, "_now", lambda: time.time() + 7200)
    expired = client.post(SCANS, json=valid_payload, headers=bearer("employee_a"))
    assert expired.get_json() == unknown.get_json()  # no oracle for token probing


def test_the_stored_hash_is_not_a_usable_token(client, valid_payload, auth_tokens):
    config_entry = auth_tokens["admin"][1]
    leaked_hash = config_entry.split(":")[0]
    response = client.post(SCANS, json=valid_payload, headers={"Authorization": f"Bearer {leaked_hash}"})
    assert response.status_code == 401


def test_reading_requires_authentication(client):
    assert client.get(f"{SCANS}/{uuid.uuid4()}").status_code == 401


def test_without_configured_credentials_every_write_is_refused(migrated_database, valid_payload):
    app = create_app(Settings(database_url=migrated_database), credentials={})
    assert app.test_client().post(SCANS, json=valid_payload).status_code == 401


def test_the_health_endpoint_stays_public_without_credentials(migrated_database):
    app = create_app(Settings(database_url=migrated_database), credentials={})
    assert app.test_client().get("/health").status_code == 200


# ---- 403: roles ------------------------------------------------------------ #
def test_a_role_that_may_not_write_is_refused(client, valid_payload, bearer):
    # The security officer is read-only by design (see ROLE_PERMISSIONS).
    response = client.post(SCANS, json=valid_payload, headers=bearer("security_officer"))
    assert response.status_code == 403


def test_a_valid_token_reaches_the_endpoint(client, valid_payload, bearer):
    # An invalid risk value makes validation answer 400, which proves auth passed without touching the DB.
    response = client.post(SCANS, json={**valid_payload, "risk": "Critical"}, headers=bearer("employee_a"))
    assert response.status_code == 400


def test_a_client_cannot_choose_its_role_or_identity_with_headers(client, new_event, bearer):
    headers = {**bearer("employee_a"), "X-Role": "admin", "X-Employee-Id": EMPLOYEE_B}
    created = client.post(SCANS, json=new_event(), headers=headers)
    assert created.status_code == 201
    event_id = created.get_json()["event_id"]
    stored = client.get(f"{SCANS}/{event_id}", headers=bearer("employee_a")).get_json()
    assert stored["employee_id"] == EMPLOYEE_A


# ---- ownership --------------------------------------------------------------- #
def test_the_owner_is_derived_from_the_token(client, new_event, bearer):
    created = client.post(SCANS, json=new_event(), headers=bearer("employee_a"))
    assert created.status_code == 201
    stored = client.get(f"{SCANS}/{created.get_json()['event_id']}", headers=bearer("employee_a"))
    assert stored.status_code == 200
    assert stored.get_json()["employee_id"] == EMPLOYEE_A


def test_a_client_supplied_other_employee_id_is_refused_and_nothing_is_stored(client, new_event, bearer):
    event = new_event(employee_id=EMPLOYEE_B)
    response = client.post(SCANS, json=event, headers=bearer("employee_a"))
    assert response.status_code == 400  # forbidden field (SCRUM-45 contract)
    # Nothing was written: the admin sees no such event.
    assert client.get(f"{SCANS}/{event['event_id']}", headers=bearer("admin")).status_code == 404


def test_a_client_supplied_employee_id_is_refused_even_if_it_matches(client, new_event, bearer):
    response = client.post(SCANS, json=new_event(employee_id=EMPLOYEE_A), headers=bearer("employee_a"))
    assert response.status_code == 400


def test_a_garbage_client_supplied_employee_id_is_refused(client, new_event, bearer):
    response = client.post(SCANS, json=new_event(employee_id="not-a-uuid"), headers=bearer("employee_a"))
    assert response.status_code == 400


def test_an_admin_cannot_impersonate_an_employee(client, new_event, bearer):
    event = new_event(employee_id=EMPLOYEE_A)
    response = client.post(SCANS, json=event, headers=bearer("admin"))
    assert response.status_code == 400
    assert client.get(f"{SCANS}/{event['event_id']}", headers=bearer("admin")).status_code == 404


def test_an_employee_cannot_read_another_employees_event(client, new_event, bearer):
    created = client.post(SCANS, json=new_event(), headers=bearer("employee_a"))
    event_id = created.get_json()["event_id"]
    assert client.get(f"{SCANS}/{event_id}", headers=bearer("employee_b")).status_code == 404
    assert client.get(f"{SCANS}/{event_id}", headers=bearer("employee_a")).status_code == 200


def test_security_officer_and_admin_can_read_any_event(client, new_event, bearer):
    created = client.post(SCANS, json=new_event(), headers=bearer("employee_a"))
    event_id = created.get_json()["event_id"]
    for who in ("security_officer", "admin"):
        response = client.get(f"{SCANS}/{event_id}", headers=bearer(who))
        assert response.status_code == 200, who


def test_a_malformed_event_id_is_not_found(client, bearer):
    assert client.get(f"{SCANS}/not-a-uuid", headers=bearer("employee_a")).status_code == 404


def test_an_unknown_event_is_not_found(client, bearer):
    assert client.get(f"{SCANS}/{uuid.uuid4()}", headers=bearer("employee_a")).status_code == 404


# ---- secret leakage ---------------------------------------------------------- #
def test_tokens_never_appear_in_responses_or_logs(client, valid_payload, caplog):
    caplog.set_level(logging.DEBUG)
    bad_token = "swt_" + "z" * 40
    response = client.post(SCANS, json=valid_payload, headers={"Authorization": f"Bearer {bad_token}"})
    assert bad_token not in response.get_data(as_text=True)
    assert bad_token not in caplog.text


def test_auth_failures_are_not_cacheable(client, valid_payload):
    assert client.post(SCANS, json=valid_payload).headers["Cache-Control"] == "no-store"


# ---- configuration ----------------------------------------------------------- #
def test_a_malformed_credential_list_stops_the_application(migrated_database, monkeypatch):
    monkeypatch.setenv("CLOUD_API_CREDENTIALS", "plain-token:employee")  # the old, insecure format
    with pytest.raises(AuthConfigError):
        create_app(Settings(database_url=migrated_database))


def test_credentials_are_loaded_from_the_environment(migrated_database, monkeypatch, auth_tokens, valid_payload):
    token, entry = auth_tokens["employee_a"]
    monkeypatch.setenv("CLOUD_API_CREDENTIALS", entry)
    app = create_app(Settings(database_url=migrated_database))
    response = app.test_client().post(
        SCANS, json={**valid_payload, "risk": "Critical"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400  # authenticated, then rejected by validation


def test_authentication_is_checked_before_the_body(client):
    response = client.post(SCANS, data="not json", headers={"Content-Type": "text/plain"})
    assert response.status_code == 401  # not 415: an anonymous caller learns nothing about the contract


def test_legacy_unattributed_event_is_visible_only_to_officer_and_admin(client, db_connection, bearer):
    event_id = str(uuid.uuid4())
    db_connection.execute(
        """
        INSERT INTO scan_events (
            event_id, event_timestamp, classification, risk,
            email_count, phone_count, keyword_count, employee_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)        """,
        (event_id, datetime.now(UTC), "Internal", None, 0, 0, 0, None),
    )
    db_connection.commit()
    assert client.get(f"{SCANS}/{event_id}", headers=bearer("employee_a")).status_code == 404
    assert client.get(f"{SCANS}/{event_id}", headers=bearer("security_officer")).status_code == 200
    assert client.get(f"{SCANS}/{event_id}", headers=bearer("admin")).status_code == 200


def test_a_duplicate_event_is_still_a_conflict_for_the_same_employee(client, new_event, bearer):
    event = new_event()
    assert client.post(SCANS, json=event, headers=bearer("employee_a")).status_code == 201
    assert client.post(SCANS, json=event, headers=bearer("employee_a")).status_code == 409
