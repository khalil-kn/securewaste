"""Unit tests for detection rules (email, phone, keywords)."""

from __future__ import annotations

import pytest

from securewaste.core.detection.catalogue import Category
from securewaste.core.detection.models import Candidate
from securewaste.core.detection.rules.email import EmailRule
from securewaste.core.detection.rules.phone import PhoneRule
from securewaste.core.detection.rules.keywords import KeywordRule
from securewaste.core.extraction import PageText


class TestEmailRule:
    """Tests for EmailRule."""

    @pytest.fixture
    def rule(self):
        return EmailRule()

    @pytest.fixture
    def page(self):
        return PageText(page_number=1, text="Contact: john.doe@example.com for details")

    def test_finds_standard_email(self, rule, page):
        """Finds standard email addresses."""
        candidates = rule.find(page)
        assert len(candidates) == 1
        assert candidates[0].raw_value == "john.doe@example.com"
        assert candidates[0].category == Category.EMAIL
        assert candidates[0].rule_id == "email.basic"
        assert candidates[0].confidence >= 0.9

    def test_finds_email_with_subdomain(self, rule):
        """Finds emails with subdomains."""
        page = PageText(page_number=1, text="Email: user@mail.company.co.uk")
        candidates = rule.find(page)
        assert len(candidates) == 1
        assert candidates[0].raw_value == "user@mail.company.co.uk"

    def test_finds_email_with_plus(self, rule):
        """Finds emails with plus addressing."""
        page = PageText(page_number=1, text="Email: user+tag@example.com")
        candidates = rule.find(page)
        assert len(candidates) == 1
        assert candidates[0].raw_value == "user+tag@example.com"

    def test_rejects_invalid_email_no_tld(self, rule):
        """Rejects email without TLD."""
        page = PageText(page_number=1, text="Invalid: user@localhost")
        candidates = rule.find(page)
        assert len(candidates) == 0

    def test_rejects_invalid_email_double_dot(self, rule):
        """Rejects email with double dot in domain."""
        page = PageText(page_number=1, text="Invalid: user@example..com")
        candidates = rule.find(page)
        assert len(candidates) == 0

    def test_rejects_email_starting_with_dot(self, rule):
        """Rejects email with domain starting with dot."""
        page = PageText(page_number=1, text="Invalid: user@.example.com")
        candidates = rule.find(page)
        assert len(candidates) == 0

    def test_confidence_boost_with_context(self, rule):
        """Confidence increases with context words nearby."""
        page_with_context = PageText(page_number=1, text="Please contact john@example.com for info")
        page_without_context = PageText(page_number=1, text="Random text john@example.com here")

        with_ctx = rule.find(page_with_context)
        without_ctx = rule.find(page_without_context)

        assert with_ctx[0].confidence > without_ctx[0].confidence

    def test_multiple_emails_same_page(self, rule):
        """Finds multiple emails on same page."""
        page = PageText(page_number=1, text="Email a@a.com and b@b.com")
        candidates = rule.find(page)
        assert len(candidates) == 2

    def test_email_at_page_boundaries(self, rule):
        """Finds email at start/end of page."""
        page_start = PageText(page_number=1, text="john@example.com is the email")
        page_end = PageText(page_number=1, text="The email is john@example.com")

        assert len(rule.find(page_start)) == 1
        assert len(rule.find(page_end)) == 1

    def test_page_number_preserved(self, rule):
        """Page number is preserved in candidates."""
        page = PageText(page_number=5, text="john@example.com")
        candidates = rule.find(page)
        assert candidates[0].page_number == 5


class TestPhoneRule:
    """Tests for PhoneRule."""

    @pytest.fixture
    def rule(self):
        return PhoneRule()

    def test_finds_international_format(self, rule):
        """Finds international phone format."""
        page = PageText(page_number=1, text="Call +44 20 7946 0958 for support")
        candidates = rule.find(page)
        assert len(candidates) >= 1
        assert candidates[0].category == Category.PHONE
        assert candidates[0].rule_id == "phone.international"
        assert "+44" in candidates[0].raw_value

    def test_finds_us_format(self, rule):
        """Finds US phone format."""
        page = PageText(page_number=1, text="Call (555) 123-4567")
        candidates = rule.find(page)
        assert len(candidates) >= 1

    def test_finds_simple_format(self, rule):
        """Finds simple XXX-XXX-XXXX format."""
        page = PageText(page_number=1, text="Call 555-123-4567")
        candidates = rule.find(page)
        assert len(candidates) >= 1

    def test_finds_7_digit_local(self, rule):
        """Finds 7-digit local numbers."""
        page = PageText(page_number=1, text="Call 555-1234")
        candidates = rule.find(page)
        assert len(candidates) >= 1

    def test_rejects_too_short(self, rule):
        """Rejects numbers with < 7 digits."""
        page = PageText(page_number=1, text="Not a phone: 123-45")
        candidates = rule.find(page)
        # May still match but should be filtered by digit count
        for c in candidates:
            digits = sum(ch.isdigit() for ch in c.raw_value)
            assert digits >= 7

    def test_rejects_too_long(self, rule):
        """Rejects numbers with > 15 digits."""
        page = PageText(page_number=1, text="Too long: +1 555 123 4567 8901 2345")
        candidates = rule.find(page)
        for c in candidates:
            digits = sum(ch.isdigit() for ch in c.raw_value)
            assert digits <= 15

    def test_confidence_boost_international(self, rule):
        """International format gets confidence boost."""
        page_intl = PageText(page_number=1, text="Call +44 20 7946 0958")
        page_nat = PageText(page_number=1, text="Call 555-123-4567")

        intl_cand = rule.find(page_intl)
        nat_cand = rule.find(page_nat)

        if intl_cand and nat_cand:
            assert intl_cand[0].confidence >= nat_cand[0].confidence

    def test_confidence_boost_context(self, rule):
        """Context words boost confidence."""
        page_with = PageText(page_number=1, text="Phone: +44 20 7946 0958")
        page_without = PageText(page_number=1, text="Number +44 20 7946 0958 here")

        with_ctx = rule.find(page_with)
        without_ctx = rule.find(page_without)

        if with_ctx and without_ctx:
            assert with_ctx[0].confidence >= without_ctx[0].confidence


class TestKeywordRule:
    """Tests for KeywordRule."""

    def test_finds_configured_keywords(self):
        """Finds configured keywords (case-insensitive)."""
        rule = KeywordRule(keywords=("confidential", "password", "salary"))
        page = PageText(page_number=1, text="This document is CONFIDENTIAL and has password info")
        candidates = rule.find(page)
        assert len(candidates) == 2
        values = {c.raw_value.lower() for c in candidates}
        assert "confidential" in values
        assert "password" in values

    def test_keyword_whole_word_only(self):
        """Keywords match whole words only."""
        rule = KeywordRule(keywords=("secret",))
        page = PageText(page_number=1, text="The secretary has a secret")
        candidates = rule.find(page)
        # Should only match "secret" not "secretary"
        assert len(candidates) == 1
        assert candidates[0].raw_value.lower() == "secret"

    def test_empty_keywords_returns_none(self):
        """Empty keyword list returns no candidates."""
        rule = KeywordRule(keywords=())
        page = PageText(page_number=1, text="confidential password secret")
        candidates = rule.find(page)
        assert len(candidates) == 0

    def test_keyword_special_chars_escaped(self):
        """Special regex chars in keywords are escaped."""
        rule = KeywordRule(keywords=("C++", "a.b", "test*"))
        page = PageText(page_number=1, text="C++ and a.b and test*")
        candidates = rule.find(page)
        assert len(candidates) == 3

    def test_case_insensitive(self):
        """Keywords match case-insensitively."""
        rule = KeywordRule(keywords=("PASSWORD",))
        page = PageText(page_number=1, text="password PASSWORD Password")
        candidates = rule.find(page)
        assert len(candidates) == 3

    def test_multiple_pages(self):
        """Keywords found on multiple pages."""
        rule = KeywordRule(keywords=("confidential",))
        pages = [
            PageText(page_number=1, text="Page 1: confidential"),
            PageText(page_number=2, text="Page 2: confidential"),
        ]
        total = 0
        for page in pages:
            candidates = rule.find(page)
            total += len(candidates)
        assert total == 2


class TestDetectionRuleBase:
    """Tests for base DetectionRule functionality."""

    def test_candidate_creation(self):
        """Candidate has all required fields."""
        page = PageText(page_number=1, text="test@example.com")
        rule = EmailRule()
        candidates = rule.find(page)

        cand = candidates[0]
        assert hasattr(cand, "rule_id")
        assert hasattr(cand, "category")
        assert hasattr(cand, "page_number")
        assert hasattr(cand, "char_start")
        assert hasattr(cand, "char_end")
        assert hasattr(cand, "raw_value")
        assert hasattr(cand, "confidence")
        assert hasattr(cand, "validation")

    def test_candidate_immutable(self):
        """Candidate is a frozen dataclass."""
        page = PageText(page_number=1, text="test@example.com")
        rule = EmailRule()
        candidates = rule.find(page)

        cand = candidates[0]
        with pytest.raises(AttributeError):
            cand.raw_value = "modified"