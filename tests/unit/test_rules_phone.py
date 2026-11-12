"""Unit tests for PhoneRule: what it should find, what it should not find, and tricky cases."""

from securewaste.core.detection.models import Candidate
from securewaste.core.detection.rules.phone import PhoneRule
from securewaste.core.extraction import PageText

RULE = PhoneRule()


def scan(text: str) -> list[Candidate]:
    return RULE.find(PageText(page_number=1, text=text))


def test_finds_tunisian_8_digits():
    found = scan("call 98123456 now")
    assert len(found) == 1
    assert found[0].raw_value == "98123456"


def test_finds_plus216_with_spaces():
    found = scan("+216 98 123 456")
    assert len(found) == 1
    assert found[0].raw_value == "+216 98 123 456"


def test_finds_grouped_with_dots_and_dashes():
    assert scan("98.123.456")[0].raw_value == "98.123.456"
    assert scan("98-123-456")[0].raw_value == "98-123-456"


def test_finds_with_leading_zero():
    found = scan("0 98 123 456")
    assert len(found) == 1


def test_rejects_too_short():
    assert scan("12345") == []
    assert scan("+216 98") == []


def test_rejects_too_long_run():
    assert scan("981234567890") == []


def test_rejects_all_zero_one_leading():
    assert scan("00000000") == []
    assert scan("11111111") == []


def test_rejects_letters():
    assert scan("abcdefgh") == []
