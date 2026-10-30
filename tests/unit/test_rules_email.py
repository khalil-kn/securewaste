"""Unit tests for EmailRule: what it should find, what it should not find, and tricky cases."""

from securewaste.core.detection.models import Candidate
from securewaste.core.detection.rules.email import EmailRule
from securewaste.core.extraction import PageText

RULE = EmailRule()


def scan(text: str) -> list[Candidate]:
    return RULE.find(PageText(page_number=1, text=text))


def test_finds_simple_email():
    found = scan("Contact: sana@example.tn")
    assert len(found) == 1
    assert found[0].raw_value == "sana@example.tn"
    assert found[0].page_number == 1
    assert found[0].rule_id == "email.basic"


def test_finds_subdomain_email():
    found = scan("name@sub.example.tn")
    assert len(found) == 1
    assert found[0].raw_value == "name@sub.example.tn"


def test_finds_multiple_emails():
    found = scan("a@ex.com and b@ex.org")
    assert [f.raw_value for f in found] == ["a@ex.com", "b@ex.org"]


def test_rejects_missing_domain():
    assert scan("not-an-email@") == []
    assert scan("missing-domain@") == []


def test_rejects_plain_words():
    assert scan("just some words with email nowhere") == []


def test_rejects_domain_without_tld():
    assert scan("user@localhost") == []


def test_rejects_invalid_tld():
    assert scan("user@example.t") == []


def test_does_not_span_extra_leading_local_part():
    # The leading "abc@" is not followed by a valid domain, so only the trailing email matches.
    found = scan("abc@sana@example.tn")
    assert [f.raw_value for f in found] == ["sana@example.tn"]


def test_finds_email_adjacent_to_punctuation():
    assert scan("See (sana@example.tn).")[0].raw_value == "sana@example.tn"
