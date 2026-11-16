from securewaste.core.classifier import ClassificationLabel
from securewaste.core.ml_classifier import (
    ClassifierSource,
    MLClassificationResult,
    apply_review_policy,
    predict_classification_hybrid_with_confidence,
)


def make_result(label, confidence, source=ClassifierSource.ML):
    return MLClassificationResult(
        label=label,
        confidence=confidence,
        all_probabilities={label: confidence},
        classifier_source=source,
    )


def test_low_confidence_requires_review():
    result = make_result(ClassificationLabel.PUBLIC, 0.27)
    reviewed = apply_review_policy(result)

    assert reviewed.requires_review is True
    assert reviewed.review_reason == "Low ML confidence"
    assert reviewed.label == ClassificationLabel.PUBLIC


def test_high_confidence_does_not_require_review():
    result = make_result(ClassificationLabel.INTERNAL, 0.75)
    reviewed = apply_review_policy(result)

    assert reviewed.requires_review is False
    assert reviewed.review_reason is None


def test_rule_override_requires_review():
    result = make_result(
        ClassificationLabel.HIGHLY_CONFIDENTIAL,
        0.0,
        ClassifierSource.FALLBACK,
    )
    reviewed = apply_review_policy(result)

    assert reviewed.requires_review is True
    assert reviewed.review_reason == "Sensitive-content rule override"


def test_rule_based_fallback_requires_review():
    result = make_result(
        ClassificationLabel.CONFIDENTIAL,
        0.85,
        ClassifierSource.RULE_BASED,
    )
    reviewed = apply_review_policy(result)

    assert reviewed.requires_review is True


def test_hybrid_applies_review_policy(tmp_path):
    missing_model = tmp_path / "nonexistent.pkl"

    result = predict_classification_hybrid_with_confidence(
        "Ordinary document without sensitive information.",
        model_path=missing_model,
    )

    assert result.requires_review is True
    assert result.classifier_source == ClassifierSource.RULE_BASED
    assert result.review_reason == "ML model unavailable; rule-based fallback"


def test_invalid_threshold():
    import pytest

    result = make_result(ClassificationLabel.PUBLIC, 0.50)

    with pytest.raises(ValueError):
        apply_review_policy(result, threshold=1.5)
