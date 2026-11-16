from unittest.mock import patch

from securewaste.core import ml_classifier as ml


def test_v3_dict_preserves_original_ml_prediction():
    original = ml.MLClassificationResult(
        label=ml.ClassificationLabel.INTERNAL,
        confidence=0.65,
        all_probabilities={ml.ClassificationLabel.INTERNAL: 0.65},
        classifier_source=ml.ClassifierSource.ML,
    )

    final = ml.MLClassificationResult(
        label=ml.ClassificationLabel.CONFIDENTIAL,
        confidence=0.0,
        all_probabilities=dict(original.all_probabilities),
        classifier_source=ml.ClassifierSource.FALLBACK,
        requires_review=True,
        review_reason="Sensitive-content rule override",
    )

    with (
        patch.object(ml, "predict_classification_with_confidence", return_value=original),
        patch.object(ml, "predict_classification_hybrid_with_confidence", return_value=final),
    ):
        result = ml.predict_classification_v3_dict("Synthetic confidential document")

    assert result["ml_label"] == "Internal"
    assert result["ml_confidence"] == 0.65
    assert result["label"] == "Confidential"
    assert result["decision_source"] == "rule_override"
    assert result["rule_override"] is True
    assert result["requires_review"] is True


def test_v3_dict_reports_normal_ml_decision():
    original = ml.MLClassificationResult(
        label=ml.ClassificationLabel.INTERNAL,
        confidence=0.82,
        all_probabilities={ml.ClassificationLabel.INTERNAL: 0.82},
        classifier_source=ml.ClassifierSource.ML,
    )

    with (
        patch.object(ml, "predict_classification_with_confidence", return_value=original),
        patch.object(ml, "predict_classification_hybrid_with_confidence", return_value=original),
    ):
        result = ml.predict_classification_v3_dict("Synthetic internal document")

    assert result["label"] == "Internal"
    assert result["ml_label"] == "Internal"
    assert result["decision_source"] == "ml"
    assert result["rule_override"] is False


def test_v3_dict_reports_rule_based_fallback():
    original = ml.MLClassificationResult(
        label=ml.ClassificationLabel.PUBLIC,
        confidence=0.0,
        all_probabilities={},
        classifier_source=ml.ClassifierSource.RULE_BASED,
    )

    with (
        patch.object(ml, "predict_classification_with_confidence", return_value=original),
        patch.object(ml, "predict_classification_hybrid_with_confidence", return_value=original),
    ):
        result = ml.predict_classification_v3_dict("Synthetic public document")

    assert result["label"] == "Public"
    assert result["ml_label"] is None
    assert result["ml_confidence"] is None
    assert result["decision_source"] == "rule_based"
    assert result["rule_override"] is False
