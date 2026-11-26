"""Risk on the results page and in cloud sync (SCRUM-46 M4). All data is synthetic."""

import io
import json
from unittest.mock import patch

import pymupdf
import pytest

from cloud_api.validation import ALLOWED_KEYS, parse_scan_payload
from securewaste import create_app
from securewaste.core.detection.catalogue import CATALOGUE, Category, Severity
from securewaste.core.detection.models import Finding
from securewaste.core.extraction import PageText
from securewaste.core.risk import assess
from securewaste.services.sync_service import CLOUD_RISK, build_event

V3 = "securewaste.web.routes_documents.predict_classification_v3_dict"
PAGES = [PageText(page_number=1, text="Contact sana@example.tn, phone +216 20 123 456.")]
TOKEN = "test-token-not-a-real-secret"  # noqa: S105


def classification(label="Confidential"):
    return {
        "label": label,
        "confidence": 0.9,
        "decision_source": "ml",
        "provisional_label": None,
        "ml_label": label,
        "ml_confidence": 0.9,
        "model_version": "baseline-v1",
        "requires_review": False,
        "review_reason": None,
    }


def post(tmp_path, monkeypatch, approved, v3=None, **config):
    monkeypatch.setenv("SECUREWASTE_RISK_APPROVED", "true" if approved else "false")
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
    v3_patch = patch(
        V3, **({"side_effect": v3} if isinstance(v3, Exception) else {"return_value": v3 or classification()})
    )
    with patch("securewaste.services.detect_service.extract_pages", return_value=PAGES), v3_patch:
        response = app.test_client().post(
            "/documents", data={"file": (io.BytesIO(data), "t.pdf")}, content_type="multipart/form-data"
        )
    assert response.status_code == 200
    return response.get_data(as_text=True)


# --- results page ----------------------------------------------------------------------------


def test_risk_is_absent_until_approved(tmp_path, monkeypatch):
    body = post(tmp_path, monkeypatch, approved=False)
    assert 'id="sr-risk-title"' not in body and "Risk level" not in body


def test_approved_risk_has_its_own_card_with_reasons(tmp_path, monkeypatch):
    body = post(tmp_path, monkeypatch, approved=True)
    assert 'id="sr-risk-title"' in body and "Risk level: Informational" in body and "5/100" in body
    assert "E-mail address" in body and "Phone number" in body  # reasons
    assert "Based only on the findings, not on the classification" in body
    assert "sana@example.tn" not in body and "123 456" not in body


def test_risk_card_survives_classifier_failure(tmp_path, monkeypatch):
    body = post(tmp_path, monkeypatch, approved=True, v3=RuntimeError("model broke"))
    assert "Document classification is unavailable" in body
    assert "Risk level: Informational" in body


@pytest.mark.parametrize("label", ["Public", "Internal", "Confidential", "Highly Confidential"])
def test_risk_card_is_the_same_under_every_label(tmp_path, monkeypatch, label):
    body = post(tmp_path / label.replace(" ", "_"), monkeypatch, approved=True, v3=classification(label))
    assert "Risk level: Informational" in body and "5/100" in body


def test_sync_offline_keeps_risk_on_the_page(tmp_path, monkeypatch):
    body = post(
        tmp_path,
        monkeypatch,
        approved=True,
        SYNC_ENABLED=True,
        CLOUD_API_URL="http://127.0.0.1:9",
        CLOUD_API_TOKEN=TOKEN,
        SYNC_TIMEOUT_SECONDS=0.5,
    )
    assert "Not sent: the cloud could not be reached" in body
    assert "Risk level: Informational" in body and TOKEN not in body


# --- sync payload ----------------------------------------------------------------------------


def finding(category, value="v1", confidence=0.95):
    return Finding(
        rule_id=f"rule.{category.value}",
        category=category,
        severity=CATALOGUE[category].severity,
        confidence=confidence,
        page_number=1,
        char_start=0,
        char_end=5,
        masked_value="m•••d",
        value_hmac=f"hmac-{category.value}-{value}",
        context="never-in-payload",
        explanation=CATALOGUE[category].explanation,
        recommendation=CATALOGUE[category].recommendation,
    )


def test_every_local_level_has_a_cloud_level():
    assert set(CLOUD_RISK) == {s.value for s in Severity}
    assert set(CLOUD_RISK.values()) == {"Low", "Medium", "High"}


@pytest.mark.parametrize(
    ("findings", "expected"),
    [
        ([], "Low"),  # informational
        ([finding(Category.KEYWORD), finding(Category.EMAIL)], "Low"),  # low
        ([finding(Category.IBAN, confidence=1.0)], "Medium"),  # 25
        ([finding(Category.PAYMENT_CARD)], "High"),  # high (floor 50)
        ([finding(Category.SECRET)], "High"),  # critical
    ],
)
def test_approved_risk_is_sent_as_a_level_the_cloud_accepts(findings, expected):
    risk = assess(findings).to_dict()
    event = build_event({"label": "Confidential"}, findings, risk)
    assert event["risk"] == expected
    assert set(event) <= ALLOWED_KEYS
    assert parse_scan_payload(event).risk == expected  # the cloud's own validator


def test_payload_carries_only_the_level_never_reasons_or_values():
    findings = [finding(Category.SECRET), finding(Category.PAYMENT_CARD)]
    risk = assess(findings).to_dict()
    raw = json.dumps(build_event({"label": "Highly Confidential"}, findings, risk))
    for forbidden in [*risk["reasons"], *risk["recommendations"], "never-in-payload", "hmac-", "m•••d", "score"]:
        assert forbidden not in raw


def test_no_approved_risk_means_no_risk_key():
    event = build_event({"label": "Public"}, [], None)
    assert "risk" not in event and parse_scan_payload(event).risk is None
