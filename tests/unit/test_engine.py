"""Unit tests for DetectionEngine: orchestration, duplicate merging, confidence floor, masking,
and the guarantee that the real value never appears in any result (ST-01 / ADR-0006)."""

from securewaste.core.detection.engine import DetectionEngine
from securewaste.core.detection.models import Candidate
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.detection.rules.email import EmailRule
from securewaste.core.detection.rules.keywords import KeywordRule
from securewaste.core.detection.rules.phone import PhoneRule
from securewaste.core.extraction import PageText

HMAC_KEY = b"test-hmac-key-not-for-production"


def engine(rules, min_confidence=0.30):
    return DetectionEngine(rules, min_confidence, HMAC_KEY)


def test_email_rule_via_engine_masks_value_and_context():
    e = engine([EmailRule()])
    findings = e.scan([PageText(page_number=1, text="Contact: sana@example.tn")])
    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "email.basic"
    assert f.category.value == "email"
    assert f.masked_value == "s•••@e•••.tn"
    # Context is masked too: the real value must not appear anywhere in the result.
    assert f.value_hmac  # a fingerprint exists
    blob = " ".join([f.masked_value, f.context, f.explanation, f.recommendation])
    assert "sana@example.tn" not in blob
    assert "sana" not in f.masked_value


def test_real_email_never_appears_in_results_st01():
    e = engine([EmailRule()])
    text = "Contact: sana@example.tn"
    findings = e.scan([PageText(page_number=1, text=text)])
    serialized = str(findings)
    assert "sana@example.tn" not in serialized
    assert "sana" not in serialized


def test_merges_duplicates_on_same_page():
    e = engine([EmailRule()])
    findings = e.scan([PageText(page_number=1, text="a@ex.com a@ex.com a@ex.com")])
    assert len(findings) == 1
    assert findings[0].occurrences == 3


def test_confidence_below_floor_is_dropped():
    class LowConfidenceRule(DetectionRule):
        rule_id = "low.confidence"
        category = EmailRule.category
        base_confidence = 0.1

        def find(self, page):
            return [
                Candidate(
                    rule_id=self.rule_id,
                    category=self.category,
                    page_number=page.page_number,
                    char_start=0,
                    char_end=5,
                    raw_value="a@ex.com",
                    confidence=self.base_confidence,
                )
            ]

    e = engine([LowConfidenceRule()], min_confidence=0.30)
    assert e.scan([PageText(page_number=1, text="a@ex.com")]) == []


def test_phone_and_keyword_rules_run_together():
    e = engine([PhoneRule(), KeywordRule(["salary"])])
    findings = e.scan([PageText(page_number=1, text="call 98123456, salary 1000")])
    categories = {f.category.value for f in findings}
    assert categories == {"phone", "keyword"}
