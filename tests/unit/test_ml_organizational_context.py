"""Regression tests for organizational sensitivity and credential context."""

import pytest

from securewaste.core.classifier import ClassificationLabel
from securewaste.core.ml_classifier import detect_organizational_context


@pytest.mark.parametrize(
    "text,expected",
    [
        ("The engineering team will review sprint progress on Thursday.", ClassificationLabel.INTERNAL),
        ("Please update the project board before the weekly planning meeting.", ClassificationLabel.INTERNAL),
        ("Employees should complete the annual security awareness course.", ClassificationLabel.INTERNAL),
        (
            "Customer billing records contain account balances and transaction histories.",
            ClassificationLabel.CONFIDENTIAL,
        ),
        (
            "Employee salary review: the proposed annual compensation is 92000 dollars.",
            ClassificationLabel.CONFIDENTIAL,
        ),
        ("This document contains a patient's medical history and treatment details.", ClassificationLabel.CONFIDENTIAL),
        (
            "DATABASE_URL=postgresql://root:V3ryS3cret!@db.internal:5432/production",
            ClassificationLabel.HIGHLY_CONFIDENTIAL,
        ),
        (
            "The signing secret used by our authentication service is: 8dF!2gH@9jK#4mN.",
            ClassificationLabel.HIGHLY_CONFIDENTIAL,
        ),
        (
            "An exposed deployment credential grants administrator access to production systems.",
            ClassificationLabel.HIGHLY_CONFIDENTIAL,
        ),
    ],
)
def test_organizational_context(text, expected):
    assert expected in detect_organizational_context(text)


@pytest.mark.parametrize(
    "text",
    [
        "A beginner tutorial explaining how to create strong passwords.",
        "This educational article explains the format of an IBAN.",
        "Welcome to our website. Learn more about our products and services.",
        "Our company will attend the annual technology exhibition next month.",
        "Example: signing secret = YOUR_SECRET_HERE",
    ],
)
def test_public_content_not_automatically_sensitive(text):
    assert not detect_organizational_context(text)
