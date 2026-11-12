"""ML-based document sensitivity classifier (Sprint 2: SCRUM-19/20/21).

TF-IDF + LogisticRegression baseline. Local-only, no external dependencies.
Provides predict_classification(text) -> (label, confidence) for Sprint 3 integration.
"""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from securewaste.core.classifier import ClassificationLabel, ClassifierError

# Model configuration
MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_PATH = MODEL_DIR / "classifier_pipeline.pkl"
METADATA_PATH = MODEL_DIR / "classifier_metadata.json"

# Classification labels (must match Sprint 3 contract)
LABELS = ["Public", "Internal", "Confidential", "Highly Confidential"]
LABEL_TO_IDX = {label: i for i, label in enumerate(LABELS)}

# TF-IDF + LogisticRegression hyperparameters (fixed for reproducibility)
TFIDF_PARAMS = {
    "max_features": 5000,
    "ngram_range": (1, 2),
    "min_df": 1,
    "max_df": 0.95,
    "sublinear_tf": True,
}

LR_PARAMS = {
    "C": 1.0,
    "max_iter": 1000,
    "solver": "lbfgs",
    "random_state": 42,
    "class_weight": "balanced",
}


@dataclass(frozen=True)
class MLClassificationResult:
    """Result of ML classification with confidence scores."""

    label: ClassificationLabel
    """Predicted label."""

    confidence: float
    """Probability of predicted class (0-1)."""

    all_probabilities: dict[ClassificationLabel, float]
    """Probability for each class."""


class MLClassifierError(ClassifierError):
    """Raised when ML classification fails."""


class MLClassifier:
    """TF-IDF + LogisticRegression document classifier."""

    def __init__(self, pipeline: Pipeline | None = None) -> None:
        self._pipeline = pipeline
        self._is_fitted = pipeline is not None

    @classmethod
    def load(cls, model_path: Path = MODEL_PATH) -> "MLClassifier":
        """Load trained model from disk."""
        if not model_path.exists():
            raise MLClassifierError(f"Model not found at {model_path}. Run training first.")
        with model_path.open("rb") as f:
            pipeline = pickle.load(f)
        return cls(pipeline)

    @classmethod
    def train(
        cls,
        texts: list[str],
        labels: list[str],
        model_path: Path = MODEL_PATH,
        metadata_path: Path = METADATA_PATH,
    ) -> "MLClassifier":
        """Train new classifier and save to disk."""
        # Validate labels
        for label in labels:
            if label not in LABEL_TO_IDX:
                raise MLClassifierError(f"Unknown label: {label}. Must be one of {LABELS}")

        # Convert labels to indices
        y = np.array([LABEL_TO_IDX[label] for label in labels])

        # Build pipeline
        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(**TFIDF_PARAMS)),
            ("lr", LogisticRegression(**LR_PARAMS)),
        ])

        # Train
        pipeline.fit(texts, y)

        # Save model
        model_path.parent.mkdir(parents=True, exist_ok=True)
        with model_path.open("wb") as f:
            pickle.dump(pipeline, f)

        # Save metadata
        metadata = {
            "labels": LABELS,
            "tfidf_params": TFIDF_PARAMS,
            "lr_params": LR_PARAMS,
            "n_samples": len(texts),
            "classes": labels,
        }
        with metadata_path.open("w") as f:
            json.dump(metadata, f, indent=2)

        return cls(pipeline)

    def predict(self, text: str) -> MLClassificationResult:
        """Predict label with confidence for a single text."""
        if not self._is_fitted:
            raise MLClassifierError("Model not fitted. Call train() or load() first.")

        if not text or not text.strip():
            # Default to Public for empty text
            probs = {label: 1.0 if label == ClassificationLabel.PUBLIC else 0.0 for label in ClassificationLabel}
            return MLClassificationResult(
                label=ClassificationLabel.PUBLIC,
                confidence=1.0,
                all_probabilities=probs,
            )

        # Get probabilities
        proba = self._pipeline.predict_proba([text])[0]
        pred_idx = int(np.argmax(proba))
        pred_label = ClassificationLabel(LABELS[pred_idx])
        confidence = float(proba[pred_idx])

        all_probs = {ClassificationLabel(LABELS[i]): float(proba[i]) for i in range(len(LABELS))}

        return MLClassificationResult(
            label=pred_label,
            confidence=confidence,
            all_probabilities=all_probs,
        )

    def predict_batch(self, texts: list[str]) -> list[MLClassificationResult]:
        """Predict labels for multiple texts."""
        return [self.predict(text) for text in texts]


# Convenience function matching the Sprint 3 contract
def predict_classification(text: str) -> ClassificationLabel:
    """Standalone ML classification from raw text.

    Uses the trained model if available, falls back to rule-based classifier.
    This is the main entry point for Sprint 3 metadata synchronization.

    Args:
        text: Document text to classify

    Returns:
        One of the four ClassificationLabel values
    """
    # Try to load ML model
    if MODEL_PATH.exists():
        try:
            classifier = MLClassifier.load()
            result = classifier.predict(text)
            return result.label
        except Exception:
            pass  # Fall back to rule-based

    # Fallback to rule-based classifier
    from securewaste.core.classifier import predict_classification as rule_predict
    return rule_predict(text)


def predict_classification_with_confidence(text: str) -> MLClassificationResult:
    """ML classification with confidence scores.

    Args:
        text: Document text to classify

    Returns:
        MLClassificationResult with label, confidence, and all probabilities
    """
    if MODEL_PATH.exists():
        try:
            classifier = MLClassifier.load()
            return classifier.predict(text)
        except Exception:
            pass

    # Fallback
    from securewaste.core.classifier import predict_classification as rule_predict
    label = rule_predict(text)
    probs = {l: 1.0 if l == label else 0.0 for l in ClassificationLabel}
    return MLClassificationResult(
        label=label,
        confidence=1.0,
        all_probabilities=probs,
    )


def train_and_save_model(
    train_texts: list[str],
    train_labels: list[str],
    model_path: Path = MODEL_PATH,
    metadata_path: Path = METADATA_PATH,
) -> MLClassifier:
    """Train and save ML classifier. Returns trained classifier."""
    return MLClassifier.train(train_texts, train_labels, model_path, metadata_path)


__all__ = [
    "MLClassifier",
    "MLClassificationResult",
    "MLClassifierError",
    "predict_classification",
    "predict_classification_with_confidence",
    "train_and_save_model",
    "LABELS",
    "MODEL_PATH",
]