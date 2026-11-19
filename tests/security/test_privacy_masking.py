from __future__ import annotations

import pytest

from securewaste.core.detection.masking import _mask_page
from securewaste.core.extraction import PageText
from securewaste.services.detect_service import detect_pages


def scan(text):
    return detect_pages(
        [PageText(page_number=1, text=text)],
        ["CONFIDENTIAL"],
        0.30,
        b"test-key",
    )


def test_context_masks_other_findings():
    text = "Contact: alice.secret@example.com Phone: (202) 555-0104"
    findings = scan(text)

    assert findings
    for finding in findings:
        assert "alice.secret@example.com" not in finding.context
        assert "555-0104" not in finding.context


def test_context_no_half_words():
    text = "Internal documentation Contact: alice@example.com CONFIDENTIAL"
    findings = scan(text)

    assert findings
    for finding in findings:
        assert "CONFIDENTI" not in finding.context.replace("CONFIDENTIAL", "")
        assert "nternal" not in finding.context.replace("Internal", "")


@pytest.mark.parametrize(
    ("text", "secret"),
    [
        ("Password: Hunter2Example", "Hunter2Example"),
        ("API_KEY=sk-TEST-1234567890abcdef", "sk-TEST"),
        ("Token: swt_abcdefghijklmnopqrstuvwxyz", "swt_"),
        ("SECRET_TOKEN_998877", "SECRET_TOKEN_998877"),
        ("Card: 4242 4242 4242 4242", "4242 4242"),
    ],
)
def test_secret_redaction(text, secret):
    masked, _ = _mask_page(text, [])
    assert secret not in masked


def test_standard_email_mask():
    findings = scan("Contact: alice.secret@example.com")

    assert len(findings) == 1
    assert findings[0].masked_value == "a" + "\u2022" * 3 + "@e" + "\u2022" * 3 + ".com"


def test_overlapping_secret_is_fully_masked():
    findings = scan("Password: alice@example.com")

    assert findings
    for finding in findings:
        assert finding.masked_value == "\u2022" * 8
        assert "alice" not in finding.context
        assert "example.com" not in finding.context


def test_classification_keyword_is_preserved():
    findings = scan("CONFIDENTIAL document")

    assert findings
    assert findings[0].masked_value == "CONFIDENTIAL"


def test_date_is_preserved():
    text = "Date: 2026-11-19"
    assert _mask_page(text, [])[0] == text


@pytest.mark.parametrize(
    "text",
    [
        "Contact: alice@example.com\nPassword: alice@example.com",
        "Password: alice@example.com\nContact: alice@example.com",
    ],
)
def test_repeated_credential_is_always_fully_masked(text):
    findings = scan(text)

    assert len(findings) == 1
    assert findings[0].occurrences == 2
    assert findings[0].masked_value == "\u2022" * 8
    assert "alice" not in findings[0].context
    assert "example.com" not in findings[0].context
    assert "a\u2022\u2022\u2022@" not in findings[0].context
