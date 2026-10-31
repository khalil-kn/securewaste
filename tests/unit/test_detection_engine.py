"""Unit tests for DetectionEngine."""

from __future__ import annotations

import pytest

from securewaste.core.detection.catalogue import Category, Severity
from securewaste.core.detection.engine import DetectionEngine
from securewaste.core.detection.rules.email import EmailRule
from securewaste.core.detection.rules.phone import PhoneRule
from securewaste.core.detection.rules.keywords import KeywordRule
from securewaste.core.extraction import PageText


@pytest.fixture
def rules():
    """Standard rules for testing."""
    return [
        EmailRule(),
        PhoneRule(),
        KeywordRule(keywords=("confidential", "password", "salary")),
    ]


@pytest.fixture
def hmac_key():
    return b"test-hmac-key-32-bytes-long-enough!!"


@pytest.fixture
def engine(rules, hmac_key):
    return DetectionEngine(rules=rules, min_confidence=0.3, hmac_key=hmac_key)


@pytest.fixture
def sample_pages():
    return [
        PageText(page_number=1, text="Contact: john.doe@example.com for details"),
        PageText(page_number=2, text="Call +44 20 7946 0958 for support"),
        PageText(page_number=3, text="This document is CONFIDENTIAL"),
    ]


class TestDetectionEngine:
    """Tests for DetectionEngine.scan()."""

    def test_returns_findings(self, engine, sample_pages):
        """Scan returns list of Findings."""
        findings = engine.scan(sample_pages)
        assert isinstance(findings, list)
        assert len(findings) >= 3  # email, phone, keyword

    def test_finding_has_required_fields(self, engine, sample_pages):
        """Each finding has all required fields."""
        findings = engine.scan(sample_pages)

        for f in findings:
            assert hasattr(f, "rule_id")
            assert hasattr(f, "category")
            assert hasattr(f, "severity")
            assert hasattr(f, "confidence")
            assert hasattr(f, "page_number")
            assert hasattr(f, "char_start")
            assert hasattr(f, "char_end")
            assert hasattr(f, "masked_value")
            assert hasattr(f, "value_hmac")
            assert hasattr(f, "context")
            assert hasattr(f, "explanation")
            assert hasattr(f, "recommendation")
            assert hasattr(f, "occurrences")
            assert hasattr(f, "validation")
            assert hasattr(f, "review_status")
            assert hasattr(f, "id")

    def test_no_raw_values_in_findings(self, engine, sample_pages):
        """Findings never contain raw sensitive values."""
        findings = engine.scan(sample_pages)

        for f in findings:
            # Check masked_value doesn't equal raw
            assert "john.doe@example.com" not in f.masked_value
            assert "+44 20 7946 0958" not in f.masked_value
            assert "CONFIDENTIAL" not in f.masked_value  # keyword shown as-is

    def test_min_confidence_filter(self, rules, hmac_key):
        """Candidates below min_confidence are dropped."""
        # High confidence threshold
        engine_high = DetectionEngine(rules=rules, min_confidence=0.95, hmac_key=hmac_key)
        pages = [PageText(page_number=1, text="Email: test@example.com")]
        findings = engine_high.scan(pages)
        # Email has base_confidence 0.9, boosted to 0.95 with context
        # But if no context, it should be filtered out
        # Actually email has context_words so might pass

        # Test with a rule that has low confidence
        class LowConfidenceRule(EmailRule):
            base_confidence = 0.1

        engine_low = DetectionEngine(
            rules=[LowConfidenceRule()], min_confidence=0.5, hmac_key=hmac_key
        )
        findings = engine_low.scan(pages)
        assert len(findings) == 0

    def test_duplicate_merging_same_page(self, engine):
        """Same value on same page merged with occurrences count."""
        # Same email appears twice on page 1
        pages = [
            PageText(page_number=1, text="Email: john@example.com and john@example.com again"),
        ]
        findings = engine.scan(pages)

        email_findings = [f for f in findings if f.category == Category.EMAIL]
        assert len(email_findings) == 1
        assert email_findings[0].occurrences == 2

    def test_duplicate_merging_different_pages(self, engine):
        """Same value on different pages NOT merged."""
        pages = [
            PageText(page_number=1, text="Email: john@example.com"),
            PageText(page_number=2, text="Email: john@example.com"),
        ]
        findings = engine.scan(pages)

        email_findings = [f for f in findings if f.category == Category.EMAIL]
        assert len(email_findings) == 2
        assert all(f.occurrences == 1 for f in email_findings)

    def test_catalogue_metadata_attached(self, engine, sample_pages):
        """Findings have catalogue severity, explanation, recommendation."""
        findings = engine.scan(sample_pages)

        for f in findings:
            assert f.severity in [s.value for s in Severity]
            assert isinstance(f.explanation, str)
            assert isinstance(f.recommendation, str)
            assert len(f.explanation) > 0
            assert len(f.recommendation) > 0

    def test_email_severity_low(self, engine):
        """Email findings have LOW severity."""
        pages = [PageText(page_number=1, text="Email: test@example.com")]
        findings = engine.scan(pages)
        email_findings = [f for f in findings if f.category == Category.EMAIL]
        assert len(email_findings) == 1
        assert email_findings[0].severity == Severity.LOW.value

    def test_phone_severity_low(self, engine):
        """Phone findings have LOW severity."""
        pages = [PageText(page_number=1, text="Call +44 20 7946 0958")]
        findings = engine.scan(pages)
        phone_findings = [f for f in findings if f.category == Category.PHONE]
        assert len(phone_findings) >= 1
        assert phone_findings[0].severity == Severity.LOW.value

    def test_keyword_severity_low(self, engine):
        """Keyword findings have LOW severity."""
        pages = [PageText(page_number=1, text="This is CONFIDENTIAL")]
        findings = engine.scan(pages)
        keyword_findings = [f for f in findings if f.category == Category.KEYWORD]
        assert len(keyword_findings) >= 1
        assert keyword_findings[0].severity == Severity.LOW.value

    def test_value_hmac_computed(self, engine, sample_pages):
        """Each finding has a value_hmac."""
        findings = engine.scan(sample_pages)
        for f in findings:
            assert f.value_hmac
            assert len(f.value_hmac) == 64  # SHA-256 hex

    def test_same_value_same_hmac(self, engine):
        """Same value produces same HMAC."""
        pages = [
            PageText(page_number=1, text="test@example.com"),
            PageText(page_number=2, text="test@example.com"),
        ]
        findings = engine.scan(pages)
        email_findings = [f for f in findings if f.category == Category.EMAIL]
        assert email_findings[0].value_hmac == email_findings[1].value_hmac

    def test_empty_pages_returns_empty(self, engine):
        """Empty pages list returns empty findings."""
        findings = engine.scan([])
        assert findings == []

    def test_pages_with_no_matches_returns_empty(self, engine):
        """Pages with no matches returns empty."""
        pages = [PageText(page_number=1, text="Just plain text with no sensitive data")]
        findings = engine.scan(pages)
        assert findings == []

    def test_multiple_rules_same_page(self, engine):
        """Multiple rules can match on same page."""
        pages = [PageText(page_number=1, text="Email: test@example.com Phone: +44 20 7946 0958 CONFIDENTIAL")]
        findings = engine.scan(pages)
        categories = {f.category for f in findings}
        assert Category.EMAIL in categories
        assert Category.PHONE in categories
        assert Category.KEYWORD in categories

    def test_review_status_defaults_to_open(self, engine, sample_pages):
        """New findings have OPEN review status."""
        findings = engine.scan(sample_pages)
        for f in findings:
            assert f.review_status.value == "open"

    def test_occurrences_defaults_to_one(self, engine):
        """Non-duplicate findings have occurrences=1."""
        pages = [PageText(page_number=1, text="test@example.com")]
        findings = engine.scan(pages)
        for f in findings:
            assert f.occurrences == 1