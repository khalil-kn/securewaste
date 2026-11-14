import pytest

from securewaste.core.classifier import ClassificationLabel
from securewaste.core.ml_classifier import detect_sensitive_patterns


@pytest.mark.parametrize(
    "document,expected",
    [
        (
            "Our emergency root certificate authority private signing key is stored in this document.",
            ClassificationLabel.HIGHLY_CONFIDENTIAL,
        ),
        (
            "The production backup encryption recovery key is stored in the secure vault.",
            ClassificationLabel.HIGHLY_CONFIDENTIAL,
        ),
        (
            "The administrator recovery codes are stored in this document.",
            ClassificationLabel.HIGHLY_CONFIDENTIAL,
        ),
        (
            "The acquisition negotiation proposes a purchase price of 42 million dollars.",
            ClassificationLabel.CONFIDENTIAL,
        ),
        (
            "The merger agreement is under negotiation.",
            ClassificationLabel.CONFIDENTIAL,
        ),
    ],
)
def test_sensitive_business_and_security_context(document, expected):
    detected = detect_sensitive_patterns(document)
    assert expected in detected


@pytest.mark.parametrize(
    "document",
    [
        "A beginner tutorial explaining how to create strong passwords.",
        "An educational article explaining root CA private signing keys.",
        "A tutorial about acquisition negotiations and purchase prices.",
    ],
)
def test_educational_context_not_automatically_sensitive(document):
    detected = detect_sensitive_patterns(document)
    assert ClassificationLabel.HIGHLY_CONFIDENTIAL not in detected
    assert ClassificationLabel.CONFIDENTIAL not in detected


def test_real_secret_in_tutorial_still_detected():
    document = "Security tutorial showing an actual exposed credential: password=RealSecretValue123!"
    detected = detect_sensitive_patterns(document)
    assert ClassificationLabel.HIGHLY_CONFIDENTIAL in detected


def test_private_key_block_in_tutorial_still_detected():
    document = (
        "Tutorial containing a private key:\n"
        "-----BEGIN PRIVATE KEY-----\n"
        "FictionalKeyMaterialForSecurityTesting\n"
        "-----END PRIVATE KEY-----"
    )
    detected = detect_sensitive_patterns(document)
    assert ClassificationLabel.HIGHLY_CONFIDENTIAL in detected
