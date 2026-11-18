"""Risk guidance for the results page: turns the classifier's label into a risk level, explanation and action.

Works on the dict from predict_classification_v3_dict. Text is fixed and reviewable, never built from the
document, and nothing here reads or logs document content.
"""

from __future__ import annotations

from securewaste.core.ml_classifier import REVIEW_THRESHOLD

# Label -> level. The level reuses the sr-severity-* CSS classes.
LEVELS = {
    "Public": "informational",
    "Internal": "low",
    "Confidential": "high",
    "Highly Confidential": "critical",
}

RECOMMENDATIONS = {
    "Public": "No action needed. Share only after a quick manual check.",
    "Internal": "Share only inside your organisation. Check recipients before sending.",
    "Confidential": "Do not share outside authorised people. Remove or mask sensitive data first.",
    "Highly Confidential": "Do not share this document. Remove or protect the sensitive data and ask its owner first.",
}

DECISION_NOTES = {
    "ml": "The label comes from the trained model.",
    "rule_override": (
        "Rule-based checks found a pattern more sensitive than the model's prediction, so the higher label was kept."
    ),
    "rule_based": "The trained model was unavailable, so rule-based checks decided the label.",
}


def risk_guidance(classification: dict, occurrences: int) -> dict:
    """Return risk_level, explanation and recommendation for a classification dict."""
    label = classification["label"]
    parts = [
        (
            f"The classifier estimates this document as {label} ({round(classification['confidence'] * 100)}% confidence)."
            if classification.get("decision_source") == "ml"
            else f"The final classification is {label}, based on sensitive-content rules."
        ),
        DECISION_NOTES.get(classification.get("decision_source"), ""),
    ]
    if occurrences:
        parts.append(f"{occurrences} sensitive item(s) were detected and are listed below.")
    elif label != "Public":
        parts.append("No specific value matched the detection rules, so review the document's content manually.")
    ml_confidence = classification.get("ml_confidence")
    return {
        # Below the classifier's own review threshold: a human must check the label before sharing.
        "low_ml_confidence": ml_confidence is not None and ml_confidence < REVIEW_THRESHOLD,
        "risk_level": LEVELS[label],
        "explanation": " ".join(p for p in parts if p),
        "recommendation": RECOMMENDATIONS[label],
    }
