"""Local ML document sensitivity classifier and conservative hybrid detection.

Sprint 2 (SCRUM-19/20/21). The hybrid decision is the highest sensitivity
between the model prediction and explicit sensitive-content indicators.
"""

from __future__ import annotations

import json
import pickle
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from securewaste.core.classifier import ClassificationLabel, ClassifierError

MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_PATH = MODEL_DIR / "classifier_pipeline.pkl"
METADATA_PATH = MODEL_DIR / "classifier_metadata.json"

LABELS = ["Public", "Internal", "Confidential", "Highly Confidential"]
LABEL_TO_IDX = {label: i for i, label in enumerate(LABELS)}
TFIDF_PARAMS = {
    "max_features": 3000,
    "ngram_range": (1, 2),
    "min_df": 2,
    "max_df": 0.9,
    "sublinear_tf": True,
}
LR_PARAMS = {
    "C": 0.7,
    "max_iter": 1000,
    "solver": "lbfgs",
    "random_state": 42,
    "class_weight": "balanced",
}


class ClassifierSource(StrEnum):
    ML = "ml"
    RULE_BASED = "rule_based"
    FALLBACK = "fallback"  # Hybrid rule override


@dataclass(frozen=True)
class MLClassificationResult:
    label: ClassificationLabel
    confidence: float
    all_probabilities: dict[ClassificationLabel, float]
    classifier_source: ClassifierSource = ClassifierSource.ML
    requires_review: bool = False
    review_reason: str | None = None


REVIEW_THRESHOLD = 0.30


def apply_review_policy(
    result: MLClassificationResult,
    threshold: float = REVIEW_THRESHOLD,
) -> MLClassificationResult:
    """Attach review information without changing the classification."""

    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Review threshold must be between 0 and 1")

    if result.classifier_source == ClassifierSource.FALLBACK:
        reason = "Sensitive-content rule override"
    elif result.classifier_source == ClassifierSource.RULE_BASED:
        reason = "ML model unavailable; rule-based fallback"
    elif result.confidence < threshold:
        reason = "Low ML confidence"
    else:
        reason = None

    return MLClassificationResult(
        label=result.label,
        confidence=result.confidence,
        all_probabilities=result.all_probabilities,
        classifier_source=result.classifier_source,
        requires_review=reason is not None,
        review_reason=reason,
    )


class MLClassifierError(ClassifierError):
    """Raised when ML training or prediction fails."""


class MLClassifier:
    """TF-IDF + LogisticRegression classifier."""

    def __init__(self, pipeline: Pipeline | None = None) -> None:
        self._pipeline = pipeline
        self._is_fitted = pipeline is not None

    @classmethod
    def load(cls, model_path: Path = MODEL_PATH) -> MLClassifier:
        if not model_path.exists():
            raise MLClassifierError(f"Model not found at {model_path}. Run training first.")
        # Only load locally trained/trusted pickle files; pickle is not safe for untrusted input.
        with model_path.open("rb") as f:
            pipeline = pickle.load(f)  # noqa: S301
        return cls(pipeline)

    @classmethod
    def train(
        cls,
        texts: list[str],
        labels: list[str],
        model_path: Path = MODEL_PATH,
        metadata_path: Path = METADATA_PATH,
    ) -> MLClassifier:
        if len(texts) != len(labels) or not texts:
            raise MLClassifierError("Training texts and labels must have equal nonzero lengths")
        for label in labels:
            if label not in LABEL_TO_IDX:
                raise MLClassifierError(f"Unknown label: {label}. Must be one of {LABELS}")
        y = np.array([LABEL_TO_IDX[label] for label in labels])
        pipeline = Pipeline(
            [
                ("tfidf", TfidfVectorizer(**TFIDF_PARAMS)),
                ("lr", LogisticRegression(**LR_PARAMS)),
            ]
        )
        pipeline.fit(texts, y)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with model_path.open("wb") as f:
            pickle.dump(pipeline, f)
        metadata = {
            "labels": LABELS,
            "tfidf_params": TFIDF_PARAMS,
            "lr_params": LR_PARAMS,
            "n_samples": len(texts),
            "classes": labels,
        }
        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        return cls(pipeline)

    def predict(self, text: str) -> MLClassificationResult:
        if not self._is_fitted:
            raise MLClassifierError("Model not fitted. Call train() or load() first.")
        if not text or not text.strip():
            probs = {label: 1.0 if label == ClassificationLabel.PUBLIC else 0.0 for label in ClassificationLabel}
            return MLClassificationResult(ClassificationLabel.PUBLIC, 1.0, probs)
        proba = self._pipeline.predict_proba([text])[0]
        # Map probabilities using the actual fitted class indices, which may be a subset.
        class_indices = self._pipeline.named_steps["lr"].classes_
        probabilities = {label: 0.0 for label in ClassificationLabel}
        for idx, p in zip(class_indices, proba, strict=True):
            probabilities[ClassificationLabel(LABELS[int(idx)])] = float(p)
        pred_idx = int(class_indices[int(np.argmax(proba))])
        return MLClassificationResult(
            ClassificationLabel(LABELS[pred_idx]),
            float(np.max(proba)),
            probabilities,
        )

    def predict_batch(self, texts: list[str]) -> list[MLClassificationResult]:
        return [self.predict(text) for text in texts]


def predict_classification(text: str, model_path: Path | None = None) -> ClassificationLabel:
    path = model_path if model_path is not None else MODEL_PATH
    if path.exists():
        try:
            return MLClassifier.load(path).predict(text).label
        except (OSError, ValueError, AttributeError, TypeError, MLClassifierError):
            pass
    from securewaste.core.classifier import predict_classification as rule_predict

    return rule_predict(text)


def predict_classification_with_confidence(text: str, model_path: Path | None = None) -> MLClassificationResult:
    path = model_path if model_path is not None else MODEL_PATH
    if path.exists():
        try:
            return MLClassifier.load(path).predict(text)
        except (OSError, ValueError, AttributeError, TypeError, MLClassifierError):
            pass
    from securewaste.core.classifier import predict_classification_with_confidence as rule_predict

    label, confidence, probs = rule_predict(text)
    return MLClassificationResult(label, confidence, probs, ClassifierSource.RULE_BASED)


def train_and_save_model(
    train_texts: list[str],
    train_labels: list[str],
    model_path: Path = MODEL_PATH,
    metadata_path: Path = METADATA_PATH,
) -> MLClassifier:
    return MLClassifier.train(train_texts, train_labels, model_path, metadata_path)


LABEL_HIERARCHY = {
    ClassificationLabel.PUBLIC: 0,
    ClassificationLabel.INTERNAL: 1,
    ClassificationLabel.CONFIDENTIAL: 2,
    ClassificationLabel.HIGHLY_CONFIDENTIAL: 3,
}


def highest_sensitivity_label(labels: list[ClassificationLabel]) -> ClassificationLabel:
    if not labels:
        return ClassificationLabel.PUBLIC
    return max(labels, key=lambda label: LABEL_HIERARCHY[label])


def _luhn_check(value: str) -> bool:
    digits = [int(ch) for ch in value if ch.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _iban_check(value: str) -> bool:
    iban = re.sub(r"[\s-]", "", value).upper()
    if not 15 <= len(iban) <= 34 or not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]+", iban):
        return False
    rearranged = iban[4:] + iban[:4]
    remainder = 0
    for char in rearranged:
        part = char if char.isdigit() else str(ord(char) - ord("A") + 10)
        for digit in part:
            remainder = (remainder * 10 + int(digit)) % 97
    return remainder == 1


# These are known publicly documented examples, not genuine AWS credentials.
KNOWN_EXAMPLE_AWS_KEYS = frozenset({"AKIAIOSFODNN7EXAMPLE", "AKIAEXAMPLEKEY12345"})


def detect_sensitive_patterns(text: str) -> list[ClassificationLabel]:
    """Return content-based sensitivity indicators, without exposing matched values.

    Tutorial wording does not disable detection: a real secret can appear in
    instructional material. This detector is heuristic, not a full DLP engine.
    """
    if not text or not text.strip():
        return []
    detected: set[ClassificationLabel] = set()

    # A known public AWS example can be ignored only when the document
    # explicitly identifies itself as instructional/example material.
    # Unknown AWS-key-shaped strings are still flagged in tutorials.
    instructional_context = bool(re.search(r"\b(?:tutorial|example|sample|dummy|fake)\b", text, re.IGNORECASE))
    for match in re.finditer(r"\bAKIA[0-9A-Z]{16}\b", text):
        key = match.group(0)
        if key in KNOWN_EXAMPLE_AWS_KEYS and instructional_context:
            continue
        detected.add(ClassificationLabel.HIGHLY_CONFIDENTIAL)
        break
    other_secret_pattern = re.compile(
        r"\b(?:api[_-]?key|secret[_-]?key)\s*[:=]\s*['\"]?([a-zA-Z0-9_-]{20,})"
        r"|\bpassword\s*[:=]\s*['\"]?([^\s'\"]{8,})"
        r"|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        re.IGNORECASE,
    )
    for match in other_secret_pattern.finditer(text):
        candidate = next((group for group in match.groups() if group), None)
        # Ignore clearly marked placeholder assignments, not entire tutorials.
        if candidate is not None:
            if re.search(r"(?:example|placeholder|dummy|fake|sample)", candidate, re.I):
                continue
            # An environment-variable reference is not a literal secret.
            if re.match(r"(?:os\.environ(?:\.get)?|os\.getenv)\s*[\[(]", candidate, re.I):
                continue
        detected.add(ClassificationLabel.HIGHLY_CONFIDENTIAL)
        break

    card_pattern = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")
    if any(_luhn_check(match.group(0)) for match in card_pattern.finditer(text)):
        detected.add(ClassificationLabel.CONFIDENTIAL)

    iban_pattern = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", re.IGNORECASE)
    if any(_iban_check(match.group(0)) for match in iban_pattern.finditer(text)):
        detected.add(ClassificationLabel.CONFIDENTIAL)

    # Weak ID patterns can produce false positives; require an identity context.
    id_context = re.search(r"\b(?:national\s+id|identity\s+(?:card|number)|passport)\b", text, re.I)
    if id_context and (re.search(r"\b\d{8}\b", text) or re.search(r"\b[A-Z]{1,2}\d{6,9}\b", text, re.I)):
        detected.add(ClassificationLabel.CONFIDENTIAL)

    # Explicit labels: each word maps to its OWN level.
    # Confirm with team whether RESTRICTED means Highly Confidential.
    label_mapping = {
        "INTERNAL": ClassificationLabel.INTERNAL,
        "CONFIDENTIAL": ClassificationLabel.CONFIDENTIAL,
        "RESTRICTED": ClassificationLabel.HIGHLY_CONFIDENTIAL,
    }
    for match in re.finditer(r"\b(INTERNAL|CONFIDENTIAL|RESTRICTED)\b", text, re.I):
        detected.add(label_mapping[match.group(1).upper()])

    # Context-aware indicators. These require combinations of terms rather
    # than treating isolated mentions of "key" or "acquisition" as secrets.
    # A tutorial is not automatically sensitive, but explicit secret values
    # detected above are never suppressed by educational wording.
    educational_context = bool(
        re.search(
            r"\b(?:tutorial|beginner\s+guide|educational\s+article|"
            r"training\s+exercise|how\s+to)\b",
            text,
            re.I,
        )
    )

    critical_key_context = re.search(
        r"\b(?:root\s+(?:certificate\s+authority|ca)|production|emergency|backup)\b"
        r".{0,100}\b(?:private\s+(?:signing\s+)?key|signing\s+key|"
        r"encryption\s+recovery\s+key)\b",
        text,
        re.I | re.S,
    )
    critical_access_context = re.search(
        r"\b(?:production|administrator|admin|privileged)\b"
        r".{0,100}\b(?:recovery\s+codes?|access\s+tokens?|"
        r"deployment\s+credentials?)\b",
        text,
        re.I | re.S,
    )
    commercial_context = re.search(
        r"\b(?:acquisition|merger|takeover)\b"
        r".{0,100}\b(?:negotiation|purchase\s+price|offer|valuation|agreement)\b",
        text,
        re.I | re.S,
    )

    if not educational_context:
        if critical_key_context or critical_access_context:
            detected.add(ClassificationLabel.HIGHLY_CONFIDENTIAL)
        if commercial_context:
            detected.add(ClassificationLabel.CONFIDENTIAL)

    email_pattern = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
    phone_pattern = re.compile(r"\b(?:\+?\d{1,3}[ -]?)?\(?\d{3}\)?[ -]?\d{3}[ -]?\d{4}\b")
    if email_pattern.search(text) or phone_pattern.search(text):
        detected.add(ClassificationLabel.INTERNAL)

    return sorted(detected, key=lambda label: LABEL_HIERARCHY[label])


def predict_classification_hybrid_with_confidence(text: str, model_path: Path | None = None) -> MLClassificationResult:
    """Combine ML and sensitive-content rules, then apply review policy.

    On rule override, confidence=0.0 means unavailable, not zero
    certainty. Probabilities retain the original model distribution.
    """
    ml_result = predict_classification_with_confidence(text, model_path)
    detected = detect_sensitive_patterns(text)

    final_label = highest_sensitivity_label([ml_result.label, *detected])

    if final_label != ml_result.label:
        result = MLClassificationResult(
            label=final_label,
            confidence=0.0,
            all_probabilities=dict(ml_result.all_probabilities),
            classifier_source=ClassifierSource.FALLBACK,
        )
    else:
        result = ml_result

    return apply_review_policy(result)


def predict_classification_hybrid(text: str, model_path: Path | None = None) -> ClassificationLabel:
    """Hybrid label-only entry point (Sprint 3 contract)."""
    return predict_classification_hybrid_with_confidence(text, model_path).label


def predict_classification_dict(text: str) -> dict:
    """Return the hybrid classification using the existing API schema."""
    result = predict_classification_hybrid_with_confidence(text)

    return {
        "label": result.label.value,
        "confidence": round(result.confidence, 4),
        "model_version": "baseline-v1",
    }


__all__ = [
    "MLClassifier",
    "MLClassificationResult",
    "MLClassifierError",
    "ClassifierSource",
    "predict_classification",
    "predict_classification_with_confidence",
    "predict_classification_hybrid",
    "predict_classification_hybrid_with_confidence",
    "detect_sensitive_patterns",
    "highest_sensitivity_label",
    "predict_classification_dict",
    "train_and_save_model",
    "LABELS",
    "MODEL_PATH",
]
