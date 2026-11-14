"""Classification on the results page: ML label -> risk level, explanation, recommendation."""

import io
from types import SimpleNamespace
from unittest.mock import patch

import pymupdf
import pytest

from securewaste import create_app
from securewaste.core.classifier import ClassificationLabel
from securewaste.core.extraction import PageText
from securewaste.core.ml_classifier import ClassifierSource, MLClassificationResult
from securewaste.services.classify_service import LEVELS, RECOMMENDATIONS, classify_document

PREDICT = "securewaste.core.ml_classifier.predict_classification_hybrid_with_confidence"


def ml_result(label, confidence=0.87, source=ClassifierSource.ML):
    probs = {lbl: 0.0 for lbl in ClassificationLabel}
    probs[label] = confidence
    return MLClassificationResult(label=label, confidence=confidence, all_probabilities=probs, classifier_source=source)


def make_app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "STORAGE_DIR": tmp_path / "storage",
            "DATABASE_PATH": tmp_path / "test.db",
        }
    )


def upload_pdf(client):
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((55, 75), "Test document")
        data = pdf.tobytes()
    return client.post(
        "/documents",
        data={"file": (io.BytesIO(data), "test.pdf")},
        content_type="multipart/form-data",
    )


# --- service ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("label", list(ClassificationLabel))
def test_every_label_has_level_and_recommendation(label):
    with patch(PREDICT, return_value=ml_result(label, 0.874)):
        result = classify_document([PageText(1, "text")], [])

    assert result["label"] == label.value
    assert result["level"] == LEVELS[label.value]
    assert result["recommendation"] == RECOMMENDATIONS[label.value]
    assert result["confidence_pct"] == 87
    assert "87% confidence" in result["explanation"]


def test_explanation_mentions_detected_items_and_source():
    findings = [SimpleNamespace(occurrences=2), SimpleNamespace(occurrences=1)]
    with patch(PREDICT, return_value=ml_result(ClassificationLabel.CONFIDENTIAL, source=ClassifierSource.FALLBACK)):
        result = classify_document([PageText(1, "text")], findings)

    assert "3 sensitive item(s)" in result["explanation"]
    assert "Rule-based checks found a pattern" in result["explanation"]


def test_sensitive_label_without_findings_asks_for_manual_review():
    with patch(PREDICT, return_value=ml_result(ClassificationLabel.CONFIDENTIAL)):
        result = classify_document([PageText(1, "text")], [])

    assert "review the document's content manually" in result["explanation"]


def test_public_without_findings_has_no_manual_review_warning():
    with patch(PREDICT, return_value=ml_result(ClassificationLabel.PUBLIC)):
        result = classify_document([PageText(1, "text")], [])

    assert "manually" not in result["explanation"]


def test_classifier_failure_returns_none():
    with patch(PREDICT, side_effect=RuntimeError("model broken")):
        assert classify_document([PageText(1, "text")], []) is None


def test_failure_log_never_contains_document_text(caplog):
    document_text = "private text that must never reach the logs"
    with patch(PREDICT, side_effect=ValueError(document_text)), caplog.at_level("WARNING"):
        classify_document([PageText(1, document_text)], [])

    assert document_text not in caplog.text
    assert "ValueError" in caplog.text


# --- results page ----------------------------------------------------------------------------------------


def test_results_page_shows_classification_without_leaking_values(tmp_path):
    app = make_app(tmp_path)
    pages = [PageText(page_number=1, text="Contact sana@example.tn")]

    with (
        patch("securewaste.services.detect_service.extract_pages", return_value=pages),
        patch(PREDICT, return_value=ml_result(ClassificationLabel.HIGHLY_CONFIDENTIAL, 0.91)),
    ):
        response = upload_pdf(app.test_client())

    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Document classification" in body
    assert "Highly Confidential" in body
    assert "Risk level: Critical" in body
    assert "91% confidence" in body
    assert RECOMMENDATIONS["Highly Confidential"] in body
    assert "sana@example.tn" not in body


def test_results_page_survives_classifier_failure(tmp_path):
    app = make_app(tmp_path)
    pages = [PageText(page_number=1, text="Contact sana@example.tn")]

    with (
        patch("securewaste.services.detect_service.extract_pages", return_value=pages),
        patch(PREDICT, side_effect=RuntimeError("model broken")),
    ):
        response = upload_pdf(app.test_client())

    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Document classification is unavailable" in body
    assert "s•••@e•••.tn" in body  # findings still shown


def test_real_model_end_to_end(tmp_path):
    """No mock on the classifier: the committed model file loads and the card renders."""
    app = make_app(tmp_path)
    pages = [PageText(page_number=1, text="aws_access_key_id = AKIAIOSFODNN7EXAMPLE")]

    with patch("securewaste.services.detect_service.extract_pages", return_value=pages):
        response = upload_pdf(app.test_client())

    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "automated estimate" in body
    assert "Highly Confidential" in body
    assert "AKIAIOSFODNN7EXAMPLE" not in body
