"""Tests of the public health endpoint."""

from __future__ import annotations


def test_health_is_public(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "service": "securewaste-cloud"}
