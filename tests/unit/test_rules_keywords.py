"""Unit tests for KeywordRule: what it should find, what it should not find, and tricky cases."""

from securewaste.core.detection.models import Candidate
from securewaste.core.detection.rules.keywords import KeywordRule
from securewaste.core.extraction import PageText


def rule(*keywords: str) -> KeywordRule:
    return KeywordRule(list(keywords))


def scan(text: str, *keywords: str) -> list[Candidate]:
    return rule(*keywords).find(PageText(page_number=1, text=text))


def test_finds_configured_keyword():
    found = scan("The salary is 1000 dt", "salary")
    assert len(found) == 1
    assert found[0].raw_value == "salary"


def test_finds_all_configured_keywords():
    found = scan("salary and password", "salary", "password")
    assert {f.raw_value for f in found} == {"salary", "password"}


def test_does_not_match_inside_longer_word():
    assert scan("salary123", "salary") == []
    assert scan("my salarytoday", "salary") == []


def test_does_not_match_partial_word():
    assert scan("lie", "salary") == []


def test_no_keywords_matches_nothing():
    assert scan("anything at all") == []


def test_keyword_not_present_does_not_match():
    assert scan("nothing sensitive here", "salary") == []
