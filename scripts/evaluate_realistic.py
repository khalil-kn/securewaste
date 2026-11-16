"""
Secure Waste - Independent Classifier Evaluation

40 fictional examples, 10 per class.
Does not train, overwrite, or modify the existing ML model.
"""

from collections import Counter

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

from securewaste.core.ml_classifier import (
    predict_classification,
    predict_classification_hybrid,
)

LABELS = [
    "Public",
    "Internal",
    "Confidential",
    "Highly Confidential",
]

# Each entry is: (expected classification, document text).
# Examples are intentionally different from the training templates.

CASES = [
    # PUBLIC
    ("Public", "Our company will attend the annual technology exhibition next month."),
    ("Public", "Welcome to our website. Learn more about our products and services."),
    ("Public", "The museum opens at nine and closes at six every weekday."),
    ("Public", "This article explains why encryption is important for internet security."),
    ("Public", "The public conference will discuss cybersecurity and cloud computing."),
    ("Public", "A beginner tutorial explaining how to create strong passwords."),
    ("Public", "Our new mobile application is available for download today."),
    ("Public", "This educational article explains the format of an IBAN."),
    ("Public", "The weather forecast predicts rain and strong winds tomorrow."),
    ("Public", "An introductory guide to detecting phishing emails and malicious links."),
    # INTERNAL
    ("Internal", "The engineering team will review sprint progress on Thursday."),
    ("Internal", "Please update the project board before the weekly planning meeting."),
    ("Internal", "The office WiFi maintenance is scheduled for Friday evening."),
    ("Internal", "Employees should complete the annual security awareness course."),
    ("Internal", "The internal documentation portal will be unavailable during maintenance."),
    ("Internal", "Our development team has postponed the next software release."),
    ("Internal", "Please send your timesheet to the department manager."),
    ("Internal", "The QA team identified three bugs in the staging environment."),
    ("Internal", "Our employee onboarding checklist has been updated."),
    ("Internal", "The product team will discuss next quarter's feature priorities."),
    # CONFIDENTIAL
    ("Confidential", "Customer billing records contain account balances and transaction histories."),
    ("Confidential", "The acquisition negotiation proposes a purchase price of 42 million dollars."),
    ("Confidential", "Employee salary review: the proposed annual compensation is 92000 dollars."),
    ("Confidential", "The board has not yet approved the company's private financial forecast."),
    ("Confidential", "This document contains a patient's medical history and treatment details."),
    ("Confidential", "The legal department is preparing an undisclosed settlement agreement."),
    ("Confidential", "Customer account number 9876543210 belongs to the private billing ledger."),
    ("Confidential", "The unreleased product strategy includes confidential pricing negotiations."),
    ("Confidential", "The HR investigation report includes private employee complaints."),
    ("Confidential", "The supplier contract includes non-public negotiated discounts and payment terms."),
    # HIGHLY CONFIDENTIAL
    ("Highly Confidential", "Production database password: D7v!q9Lz#2Kp."),
    ("Highly Confidential", "AWS access key ID: AKIAQWERTYUIOPASDFGH."),
    ("Highly Confidential", "Production API token: sk_live_51Qm7T9xP2zA8bC6dE4fG."),
    (
        "Highly Confidential",
        "-----BEGIN PRIVATE KEY-----\nFictionalKeyMaterialForSecurityTesting\n-----END PRIVATE KEY-----",
    ),
    ("Highly Confidential", "The administrator recovery codes are 7842-9911 and 3810-6625."),
    ("Highly Confidential", "DATABASE_URL=postgresql://root:V3ryS3cret!@db.internal:5432/production"),
    ("Highly Confidential", "The signing secret used by our authentication service is: 8dF!2gH@9jK#4mN."),
    ("Highly Confidential", "An exposed deployment credential grants administrator access to production systems."),
    ("Highly Confidential", "Our emergency root certificate authority private signing key is stored in this document."),
    (
        "Highly Confidential",
        "The production backup encryption recovery key is included in the sealed disaster recovery instructions.",
    ),
]


SEVERITY = {
    "Public": 0,
    "Internal": 1,
    "Confidential": 2,
    "Highly Confidential": 3,
}


def main():
    actual = []
    ml_predictions = []
    hybrid_predictions = []

    print("INDEPENDENT CLASSIFIER EVALUATION")
    print("=" * 72)
    print("Examples:", len(CASES))
    print("Distribution:", dict(Counter(label for label, _ in CASES)))

    for expected, document in CASES:
        ml = predict_classification(document).value
        hybrid = predict_classification_hybrid(document).value

        actual.append(expected)
        ml_predictions.append(ml)
        hybrid_predictions.append(hybrid)

    for name, predictions in [
        ("ML ONLY", ml_predictions),
        ("HYBRID", hybrid_predictions),
    ]:
        print("\n" + "=" * 72)
        print(name)
        print("=" * 72)

        print(
            "Accuracy:",
            f"{accuracy_score(actual, predictions):.2%}",
        )

        print(
            classification_report(
                actual,
                predictions,
                labels=LABELS,
                zero_division=0,
            )
        )

        print("Confusion matrix:")
        print("Rows = actual, columns = predicted")
        print("Order:", LABELS)
        print(
            confusion_matrix(
                actual,
                predictions,
                labels=LABELS,
            )
        )

        underclassified = []
        overclassified = []

        for index, (expected, predicted) in enumerate(zip(actual, predictions, strict=True), start=1):
            if SEVERITY[predicted] < SEVERITY[expected]:
                underclassified.append(index)
            elif SEVERITY[predicted] > SEVERITY[expected]:
                overclassified.append(index)

        print("\nDangerous underclassifications:", len(underclassified))
        print("Overclassifications:", len(overclassified))

        print("\nMISCLASSIFIED DOCUMENTS")

        for index, (expected, predicted) in enumerate(zip(actual, predictions, strict=True), start=1):
            if expected != predicted:
                print(f"\nCase {index}")
                print("Expected:", expected)
                print("Predicted:", predicted)
                print("Text:", CASES[index - 1][1])

        if not underclassified and not overclassified:
            print("No misclassifications.")

    print("\n" + "=" * 72)
    print("EVALUATION COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()
