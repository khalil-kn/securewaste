"""Tests of the token guard."""

from __future__ import annotations

from cloud_api.app import create_app
from cloud_api.config import Settings


def test_a_request_without_a_token_is_refused(client, valid_payload):
    response = client.post("/api/v1/scans", json=valid_payload)
    assert response.status_code == 401


def test_a_request_with_an_unknown_token_is_refused(client, valid_payload):
    response = client.post(
        "/api/v1/scans",
        json=valid_payload,
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


def test_a_request_without_the_bearer_prefix_is_refused(client, valid_payload):
    response = client.post("/api/v1/scans", json=valid_payload, headers={"Authorization": "employee-token"})
    assert response.status_code == 401


def test_a_role_that_may_not_write_is_refused(client, valid_payload):
    response = client.post(
        "/api/v1/scans",
        json=valid_payload,
        headers={"Authorization": "Bearer auditor-token"},
    )
    assert response.status_code == 403


def test_a_valid_token_reaches_the_endpoint(client, valid_payload):
    response = client.post(
        "/api/v1/scans",
        json={**valid_payload, "risk": "Critical"},
        headers={"Authorization": "Bearer employee-token"},
    )
    assert response.status_code == 400


def test_without_configured_tokens_every_write_is_refused(migrated_database, valid_payload):
    app = create_app(Settings(database_url=migrated_database), tokens={})
    response = app.test_client().post("/api/v1/scans", json=valid_payload)
    assert response.status_code == 401


def test_the_health_endpoint_stays_public_without_tokens(migrated_database):
    app = create_app(Settings(database_url=migrated_database), tokens={})
    response = app.test_client().get("/health")
    assert response.status_code == 200
