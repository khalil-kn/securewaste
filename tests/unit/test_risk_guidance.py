"""Classification guidance (explanation, recommendation) on the results card. Risk is NOT derived from the label."""

import io
from unittest.mock import patch

import pymupdf
import pytest

from securewaste import create_app
from securewaste.core.extraction import PageText
from securewaste.core.risk import assess
from securewaste.services.classify_service import RECOMMENDATIONS, risk_guidance

V3 = "securewaste.web.routes_documents.predict_classification_v3_dict"


def v3(label, source="ml", confidence=0.874):
    return {"label": label, "confidence": confidence, "decision_source": source}


@pytest.mark.parametrize("label", list(RECOMMENDATIONS))
def test_every_label_has_recommendation_but_no_risk_level(label):
    g = risk_guidance(v3(label), 0)
    assert g["recommendation"] == RECOMMENDATIONS[label]
    assert "87% confidence" in g["explanation"]
    assert "risk_level" not in g  # SCRUM-46: no mapping from classification to risk


def test_explanation_covers_source_and_findings():
    g = risk_guidance(v3("Confidential", "rule_override"), 3)
    assert "more sensitive than the model's prediction" in g["explanation"]
    assert "3 sensitive item(s)" in g["explanation"]


def test_sensitive_label_without_findings_asks_for_manual_review():
    assert "review the document's content manually" in risk_guidance(v3("Confidential"), 0)["explanation"]
    assert "manually" not in risk_guidance(v3("Public"), 0)["explanation"]


def render(tmp_path, **overrides):
    app = create_app(
        {"TESTING": True, "WTF_CSRF_ENABLED": False, "STORAGE_DIR": tmp_path / "s", "DATABASE_PATH": tmp_path / "t.db"}
    )
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((55, 75), "x")
        data = pdf.tobytes()
    pages = [PageText(page_number=1, text="Contact sana@example.tn")]
    result = {
        **v3("Highly Confidential", confidence=0.91),
        "provisional_label": None,
        "ml_label": None,
        "ml_confidence": None,
        "model_version": "baseline-v1",
        "requires_review": False,
        "review_reason": None,
        **overrides,
    }
    with (
        patch("securewaste.services.detect_service.extract_pages", return_value=pages),
        patch(V3, return_value=result),
    ):
        r = app.test_client().post(
            "/documents", data={"file": (io.BytesIO(data), "t.pdf")}, content_type="multipart/form-data"
        )
    assert r.status_code == 200
    return r.get_data(as_text=True)


def test_results_page_shows_guidance_without_leaking_values(tmp_path):
    body = render(tmp_path)
    assert RECOMMENDATIONS["Highly Confidential"] in body
    assert "sana@example.tn" not in body and ' style="' not in body


def test_risk_badge_is_hidden(tmp_path):
    assert "Risk level" not in render(tmp_path)


@pytest.mark.parametrize("label", list(RECOMMENDATIONS))
def test_risk_ignores_the_classification_label(tmp_path, monkeypatch, label):
    monkeypatch.setenv("SECUREWASTE_RISK_APPROVED", "true")
    # Same findings (one e-mail) under every label: the route must compute the same risk each time.
    with patch("securewaste.web.routes_documents.assess", wraps=assess) as spy:
        render(tmp_path / label.replace(" ", "_"), label=label)
    (findings,), _ = spy.call_args
    assert [f.category for f in findings] == ["email"]
    assert assess(findings).level == "informational"


@pytest.mark.parametrize(
    ("ml_confidence", "warned"), [(0.45, True), (0.59, True), (0.60, False), (0.9, False), (None, False)]
)
def test_low_ml_confidence_asks_for_human_review(tmp_path, ml_confidence, warned):
    body = render(tmp_path, ml_label="Confidential", ml_confidence=ml_confidence)
    assert ("needs human review before the document is shared" in body) is warned
    assert risk_guidance({**v3("Confidential"), "ml_confidence": ml_confidence}, 0)["low_ml_confidence"] is warned


def test_results_page_survives_classifier_failure(tmp_path, caplog):
    app = create_app(
        {"TESTING": True, "WTF_CSRF_ENABLED": False, "STORAGE_DIR": tmp_path / "s", "DATABASE_PATH": tmp_path / "t.db"}
    )
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((55, 75), "x")
        data = pdf.tobytes()
    leak_marker = "private text that must never reach the logs"
    pages = [PageText(page_number=1, text="Contact sana@example.tn")]
    with (
        patch("securewaste.services.detect_service.extract_pages", return_value=pages),
        patch(V3, side_effect=RuntimeError(leak_marker)),
        caplog.at_level("WARNING"),
    ):
        r = app.test_client().post(
            "/documents", data={"file": (io.BytesIO(data), "t.pdf")}, content_type="multipart/form-data"
        )
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "Document classification is unavailable" in body and "Risk level" not in body
    assert "s•••@e•••.tn" in body and "sana@example.tn" not in body
    assert "RuntimeError" in caplog.text and leak_marker not in caplog.text
