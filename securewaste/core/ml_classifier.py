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
from securewaste.core.detection.catalogue import Category
from securewaste.core.detection.models import Finding

# Model configuration
MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_PATH = MODEL_DIR / "classifier_pipeline.pkl"
METADATA_PATH = MODEL_DIR / "classifier_metadata.json"

# Classification labels (must match Sprint 3 contract)
LABELS = ["Public", "Internal", "Confidential", "Highly Confidential"]
LABEL_TO_IDX = {label: i for i, label in enumerate(LABELS)}

# TF-IDF + LogisticRegression hyperparameters (fixed for reproducibility)
# TF-IDF + LogisticRegression hyperparameters (tuned to prevent overfitting on synthetic data)
TFIDF_PARAMS = {
    "max_features": 3000,      # Reduced from 5000
    "ngram_range": (1, 2),     # Unigrams + bigrams
    "min_df": 2,               # Increased from 1 - ignore terms in only 1 doc
    "max_df": 0.9,             # Reduced from 0.95 - ignore very common terms
    "sublinear_tf": True,
}

LR_PARAMS = {
    "C": 0.7,                  # Reduced from 1.0 - stronger regularization
    "max_iter": 1000,
    "solver": "lbfgs",
    "random_state": 42,
    "class_weight": "balanced",
}


from enum import StrEnum


class ClassifierSource(StrEnum):
    """Indicates which classifier was used for the prediction."""
    ML = "ml"
    RULE_BASED = "rule_based"
    FALLBACK = "fallback"


@dataclass(frozen=True)
class MLClassificationResult:
    """Result of ML classification with confidence scores."""
    label: ClassificationLabel
    """Predicted label."""

    confidence: float
    """Probability of predicted class (0-1)."""

    all_probabilities: dict[ClassificationLabel, float]
    """Probability for each class."""

    classifier_source: ClassifierSource = ClassifierSource.ML
    """Which classifier was used for this prediction."""


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
                classifier_source=ClassifierSource.ML,
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
            classifier_source=ClassifierSource.ML,
        )

    def predict_batch(self, texts: list[str]) -> list[MLClassificationResult]:
        """Predict labels for multiple texts."""
        return [self.predict(text) for text in texts]


# Convenience function matching the Sprint 3 contract
def predict_classification(text: str, model_path: Path | None = None) -> ClassificationLabel:
    """Standalone ML classification from raw text.

    Uses the trained model if available, falls back to rule-based classifier.
    This is the main entry point for Sprint 3 metadata synchronization.

    Args:
        text: Document text to classify
        model_path: Optional path to model file. Defaults to MODEL_PATH.

    Returns:
        One of the four ClassificationLabel values
    """
    path = model_path or MODEL_PATH
    # Try to load ML model
    if path.exists():
        try:
            classifier = MLClassifier.load(path)
            result = classifier.predict(text)
            return result.label
        except Exception:
            pass  # Fall back to rule-based

    # Fallback to rule-based classifier
    from securewaste.core.classifier import predict_classification as rule_predict
    return rule_predict(text)


def predict_classification_with_confidence(text: str, model_path: Path | None = None) -> MLClassificationResult:
    """ML classification with confidence scores.

    Args:
        text: Document text to classify
        model_path: Optional path to model file. Defaults to MODEL_PATH.

    Returns:
        MLClassificationResult with label, confidence, and all probabilities
    """
    path = model_path or MODEL_PATH
    if path.exists():
        try:
            classifier = MLClassifier.load(path)
            result = classifier.predict(text)
            # Ensure classifier_source is set to ML
            if result.classifier_source == ClassifierSource.ML:
                return result
            # If somehow not set, create new result with ML source
            return MLClassificationResult(
                label=result.label,
                confidence=result.confidence,
                all_probabilities=result.all_probabilities,
                classifier_source=ClassifierSource.ML,
            )
        except Exception:
            pass

    # Fallback to rule-based classifier
    from securewaste.core.classifier import predict_classification_with_confidence as rule_predict_with_confidence
    label, confidence, probs = rule_predict_with_confidence(text)
    return MLClassificationResult(
        label=label,
        confidence=confidence,
        all_probabilities=probs,
        classifier_source=ClassifierSource.RULE_BASED,
    )


def train_and_save_model(
    train_texts: list[str],
    train_labels: list[str],
    model_path: Path = MODEL_PATH,
    metadata_path: Path = METADATA_PATH,
) -> MLClassifier:
    """Train and save ML classifier. Returns trained classifier."""
    return MLClassifier.train(train_texts, train_labels, model_path, metadata_path)



# =============================================================================
# Hybrid Classification (ML + Rule-based Detection)
# =============================================================================

# Label ordering for highest-sensitivity-wins
LABEL_HIERARCHY = {
    ClassificationLabel.PUBLIC: 0,
    ClassificationLabel.INTERNAL: 1,
    ClassificationLabel.CONFIDENTIAL: 2,
    ClassificationLabel.HIGHLY_CONFIDENTIAL: 3,
}


def highest_sensitivity_label(labels: list[ClassificationLabel]) -> ClassificationLabel:
    """Return the highest sensitivity label from a list."""
    if not labels:
        return ClassificationLabel.PUBLIC
    return max(labels, key=lambda l: LABEL_HIERARCHY[l])


def detect_sensitive_patterns(text: str) -> list[ClassificationLabel]:
    """Run lightweight detection to find sensitive patterns.
    
    Returns list of labels corresponding to detected patterns,
    ordered by sensitivity (highest last).
    Includes safeguards against common false positives.
    """
    detected_labels = []
    
    if not text or not text.strip():
        return detected_labels
    
    import re
    
    # Helper: Luhn checksum for payment cards
    def luhn_check(card_num: str) -> bool:
        digits = [int(d) for d in card_num if d.isdigit()]
        if len(digits) < 13:
            return False
        odd = digits[-1::-2]
        even = digits[-2::-2]
        total = sum(odd)
        for d in even:
            total += sum(divmod(d * 2, 10))
        return total % 10 == 0
    
    # Helper: IBAN mod-97 check
    def iban_check(iban: str) -> bool:
        iban = iban.replace(" ", "").replace("-", "").upper()
        if len(iban) < 15 or len(iban) > 34:
            return False
        # Move first 4 chars to end
        rearranged = iban[4:] + iban[:4]
        # Convert letters to numbers (A=10, B=11, ...)
        numeric = ""
        for ch in rearranged:
            if ch.isalpha():
                numeric += str(ord(ch) - ord('A') + 10)
            else:
                numeric += ch
        try:
            return int(numeric) % 97 == 1
        except ValueError:
            return False
    
    # High-sensitivity patterns (Highly Confidential)
    secret_pattern = re.compile(
        r"\b(AKIA[0-9A-Z]{16}|api[_-]?key\s*[:=]\s*[\"']?[a-zA-Z0-9_\-]{20,}|"
        r"secret[_-]?key\s*[:=]\s*[\"']?[a-zA-Z0-9_\-]{20,}|"
        r"password\s*[:=]\s*[\"']?[^\s\"']{8,}|"
        r"BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY\b)",
        re.IGNORECASE,
    )
    # Safeguard: check if content appears in a tutorial/example context
    # Use word boundaries to avoid false matches like "test.com"
    tutorial_indicators = [
        r"\btutorial\b", r"\bdemo\b", r"\bsample\b", r"\bplaceholder\b",
        r"\bfake\b", r"\bdummy\b", r"\binvalid\b", r"xxxx", r"yyyy", r"zzzz", r"1234",
        r"do not use", r"do not commit", r"never hardcode", r"environment variable",
        r"os\.environ", r"getenv", r"dotenv", r"vault", r"secrets manager",
    ]
    is_tutorial_context = any(re.search(indicator, text.lower()) for indicator in tutorial_indicators)
    
    if secret_pattern.search(text):
        # Check if AWS key is present
        aws_match = re.search(r"AKIA[0-9A-Z]{16}", text)
        if aws_match:
            # AWS key: check tutorial context
            if is_tutorial_context:
                key = aws_match.group(0)
                known_examples = ["AKIAIOSFODNN7EXAMPLE", "AKIAEXAMPLEKEY12345"]
                if key not in known_examples:
                    detected_labels.append(ClassificationLabel.HIGHLY_CONFIDENTIAL)
            else:
                detected_labels.append(ClassificationLabel.HIGHLY_CONFIDENTIAL)
        else:
            # Other secret patterns (API keys, passwords, private keys)
            # Check tutorial context for these too
            if not is_tutorial_context:
                detected_labels.append(ClassificationLabel.HIGHLY_CONFIDENTIAL)
    
    # Payment card pattern (Confidential) - with Luhn check
    card_pattern = re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b")
    for match in card_pattern.finditer(text):
        card = match.group(0)
        # Safeguard: check for tutorial/test patterns
        if not is_tutorial_context and luhn_check(card):
            detected_labels.append(ClassificationLabel.CONFIDENTIAL)
            break  # One valid card is enough
    
    # IBAN pattern (Confidential) - with mod-97 check
    iban_pattern = re.compile(
        r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}",
        re.IGNORECASE,
    )
    for match in iban_pattern.finditer(text):
        iban = match.group(0)
        if not is_tutorial_context and iban_check(iban):
            detected_labels.append(ClassificationLabel.CONFIDENTIAL)
            break
    
    # National ID / Passport patterns (Confidential)
    id_pattern = re.compile(r"\b\d{8}\b")  # 8-digit national ID
    passport_pattern = re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")  # Passport-like
    # Safeguard: these are weak patterns, only flag if not in tutorial context
    if not is_tutorial_context:
        if id_pattern.search(text) or passport_pattern.search(text):
            detected_labels.append(ClassificationLabel.CONFIDENTIAL)
    
    # Explicit confidentiality labels (Confidential)
    label_pattern = re.compile(r"(?<!\w)(CONFIDENTIAL|INTERNAL|RESTRICTED)(?!\w)")
    if label_pattern.search(text.upper()):
        # Safeguard: if in tutorial context, don't flag
        if not is_tutorial_context:
            detected_labels.append(ClassificationLabel.CONFIDENTIAL)
    
    # Email/phone/keyword patterns (Internal)
    # Safeguard: emails/phones in tutorials are common, be more conservative
    email_pattern = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
    phone_pattern = re.compile(r"\b(?:\+?\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}\b")
    if email_pattern.search(text) or phone_pattern.search(text):
        if not is_tutorial_context:
            detected_labels.append(ClassificationLabel.INTERNAL)
    
    return detected_labels


def predict_classification_hybrid(text: str, model_path: Path | None = None) -> tuple[ClassificationLabel, list[ClassificationLabel]]:
    """Hybrid classification combining ML and rule-based detection.
    
    Implements highest-sensitivity-wins: if any detection finds a higher
    sensitivity than the ML prediction, the higher sensitivity wins.
    
    Args:
        text: Document text to classify
        model_path: Optional path to ML model
        
    Returns:
        Tuple of (final_label, detected_labels)
    """
    # Get ML prediction
    ml_result = predict_classification_with_confidence(text, model_path)
    ml_label = ml_result.label
    
    # Run detection
    detected_labels = detect_sensitive_patterns(text)
    
    # Highest-sensitivity-wins
    all_labels = [ml_label] + detected_labels
    final_label = highest_sensitivity_label(all_labels)
    
    return final_label, detected_labels


def predict_classification_hybrid_with_confidence(text: str, model_path: Path | None = None) -> MLClassificationResult:
    """Hybrid classification with confidence scores.
    
    Args:
        text: Document text to classify
        model_path: Optional path to ML model
        
    Returns:
        MLClassificationResult with final label, confidence, and metadata
    """
    # Get ML result
    ml_result = predict_classification_with_confidence(text, model_path)
    ml_label = ml_result.label
    ml_confidence = ml_result.confidence
    
    # Run detection
    detected_labels = detect_sensitive_patterns(text)
    
    # Highest-sensitivity-wins
    all_labels = [ml_label] + detected_labels
    final_label = highest_sensitivity_label(all_labels)
    
    # Determine confidence
    if final_label != ml_label:
        # Detection overrode ML - use rule-based confidence
        # Lower confidence since we're overriding ML
        final_confidence = 0.85
        classifier_source = ClassifierSource.FALLBACK
    else:
        # ML label matches or exceeds detection
        final_confidence = ml_confidence
        classifier_source = ml_result.classifier_source
    
    # Build combined probabilities
    combined_probs = dict(ml_result.all_probabilities)
    # Boost probability of detected labels
    for det_label in detected_labels:
        if det_label in combined_probs:
            combined_probs[det_label] = max(combined_probs[det_label], 0.9)
    
    # Renormalize
    total = sum(combined_probs.values())
    if total > 0:
        combined_probs = {k: v / total for k, v in combined_probs.items()}
    
    return MLClassificationResult(
        label=final_label,
        confidence=final_confidence,
        all_probabilities=combined_probs,
        classifier_source=classifier_source,
    )


def predict_classification_hybrid(text: str, model_path: Path | None = None) -> ClassificationLabel:
    """Hybrid classification returning only the label (for Sprint 3 contract)."""
    result = predict_classification_hybrid_with_confidence(text, model_path)
    return result.label


def predict_classification_dict(text: str) -> dict:
    """Sprint 2 ML -> Full-stack contract: returns dict with label, confidence, model_version.

    Matches the exact interface specified in the Sprint 2 execution guide.
    """
    result = predict_classification_with_confidence(text)
    return {
        "label": result.label.value,
        "confidence": round(result.confidence, 4),
        "model_version": "baseline-v1",
    }


__all__ = [
    "MLClassifier",
    "MLClassificationResult",
    "MLClassifierError",
    "predict_classification",
    "predict_classification_with_confidence",
    "predict_classification_dict",
    "train_and_save_model",
    "LABELS",
    "MODEL_PATH",
]