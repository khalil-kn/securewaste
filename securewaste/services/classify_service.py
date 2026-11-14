"""Document classification for the results page.

Runs the ML classifier on the extracted text and turns its label into what the page shows: a risk level,
an explanation and a recommendation. Returns None when the classifier cannot run, so the page still shows
the findings. Extracted text is never logged (see core/extraction.py).
"""

from __future__ import annotations

import logging

from securewaste.core.extraction import PageText

log = logging.getLogger(__name__)

# Model label -> level. The level reuses the existing sr-severity-* CSS classes.
LEVELS = {
    "Public": "informational",
    "Internal": "low",
    "Confidential": "high",
    "Highly Confidential": "critical",
}

# One fixed, reviewable text per label. Never generated from the document.
RECOMMENDATIONS = {
    "Public": "No action needed. Share only after a quick manual check.",
    "Internal": "Share only inside your organisation. Check recipients before sending.",
    "Confidential": "Do not share outside authorised people. Remove or mask sensitive data first.",
    "Highly Confidential": "Do not share this document. Remove or protect the sensitive data and ask its owner first.",
}

# Where the label came from (MLClassificationResult.classifier_source).
SOURCE_NOTES = {
    "ml": "The label comes from the trained model.",
    "fallback": (
        "Rule-based checks found a pattern more sensitive than the model's own prediction, "
        "so the higher label was kept."
    ),
    "rule_based": "The trained model was unavailable, so rule-based checks decided the label.",
}


def _explain(label: str, confidence_pct: int, source: str, occurrences: int) -> str:
    parts = [
        f"The classifier estimates this document as {label} ({confidence_pct}% confidence).",
        SOURCE_NOTES.get(source, ""),
    ]
    if occurrences:
        parts.append(f"{occurrences} sensitive item(s) were detected and are listed below.")
    elif label != "Public":
        parts.append("No specific value matched the detection rules, so review the document's content manually.")
    return " ".join(p for p in parts if p)


def classify_document(pages: list[PageText], findings: list) -> dict | None:
    """Return the classification view model for the template, or None if classification is unavailable."""
    try:
        # Imported here so a missing scikit-learn cannot stop the whole app from starting.
        from securewaste.core.ml_classifier import predict_classification_hybrid_with_confidence

        text = "\n".join(page.text for page in pages)
        result = predict_classification_hybrid_with_confidence(text)
        label = result.label.value
        confidence_pct = round(result.confidence * 100)
        occurrences = sum(f.occurrences for f in findings)
        return {
            "label": label,
            "level": LEVELS[label],
            "confidence_pct": confidence_pct,
            "explanation": _explain(label, confidence_pct, result.classifier_source.value, occurrences),
            "recommendation": RECOMMENDATIONS[label],
            "source": result.classifier_source.value,
        }
    except Exception as error:
        # Log only the error type: messages can contain pieces of the input text.
        log.warning("Document classification unavailable: %s", type(error).__name__)
        return None
