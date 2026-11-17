"""Risk level, explanation and recommendation added on top of the hybrid classification card."""

import io
from unittest.mock import patch

import pymupdf
import pytest

from securewaste import create_app
from securewaste.core.extraction import PageText
from securewaste.services.classify_service import LEVELS, RECOMMENDATIONS, risk_guidance

V3 = "securewaste.web.routes_documents.predict_classification_v3_dict"


def v3(label, source="ml", confidence=0.874):
    return {"label": label, "confidence": confidence, "decision_source": source}


@pytest.mark.parametrize("label", list(LEVELS))
def test_every_label_has_level_and_recommendation(label):
    g = risk_guidance(v3(label), 0)
    assert g["risk_level"] == LEVELS[label] and g["recommendation"] == RECOMMENDATIONS[label]
    assert "87% confidence" in g["explanation"]


def test_explanation_covers_source_and_findings():
    g = risk_guidance(v3("Confidential", "rule_override"), 3)
    assert "more sensitive than the model's prediction" in g["explanation"]
    assert "3 sensitive item(s)" in g["explanation"]


def test_sensitive_label_without_findings_asks_for_manual_review():
    assert "review the document's content manually" in risk_guidance(v3("Confidential"), 0)["explanation"]
    assert "manually" not in risk_guidance(v3("Public"), 0)["explanation"]


def test_results_page_shows_risk_guidance_without_leaking_values(tmp_path):
    app = create_app(
        {"TESTING": True, "WTF_CSRF_ENABLED": False, "STORAGE_DIR": tmp_path / "s", "DATABASE_PATH": tmp_path / "t.db"}
    )
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((55, 75), "x")
        data = pdf.tobytes()
    pages = [PageText(page_number=1, text="Contact sana@example.tn")]
    with (
        patch("securewaste.services.detect_service.extract_pages", return_value=pages),
        patch(
            V3,
            return_value={
                **v3("Highly Confidential", confidence=0.91),
                "provisional_label": None,
                "ml_label": None,
                "ml_confidence": None,
                "model_version": "baseline-v1",
                "requires_review": False,
                "review_reason": None,
            },
        ),
    ):
        r = app.test_client().post(
            "/documents", data={"file": (io.BytesIO(data), "t.pdf")}, content_type="multipart/form-data"
        )
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "Risk level: Critical" in body and RECOMMENDATIONS["Highly Confidential"] in body
    assert "sana@example.tn" not in body and ' style="' not in body


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
