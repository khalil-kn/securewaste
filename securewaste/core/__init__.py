"""Core: pure business logic. No Flask imports allowed here (NFR-08) — it must be testable in milliseconds."""

from securewaste.core.classifier import (
    ClassificationLabel,
    ClassificationResult,
    ClassifierError,
    ClassificationError,
    classify_document,
)
from securewaste.core.ml_classifier import (
    MLClassificationResult,
    MLClassifier,
    MLClassifierError,
    predict_classification,
    predict_classification_with_confidence,
    predict_classification_dict,
    train_and_save_model,
)

__all__ = [
    "ClassificationLabel",
    "ClassificationResult",
    "ClassifierError",
    "ClassificationError",
    "classify_document",
    "predict_classification",
    "predict_classification_with_confidence",
    "predict_classification_dict",
    "train_and_save_model",
    "MLClassifier",
    "MLClassificationResult",
    "MLClassifierError",
]