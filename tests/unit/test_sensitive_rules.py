"""Card, IBAN, secret and confidentiality-label detection (SCRUM-46). All values are public test numbers
or fictional; none is a real card, account or credential."""

import time

import pytest

from securewaste.core.detection.catalogue import Category
from securewaste.core.detection.rules.financial import IbanRule, PaymentCardRule
from securewaste.core.detection.rules.label import ConfidentialityLabelRule
from securewaste.core.detection.rules.secret import SecretRule
from securewaste.core.detection.validators import iban_valid, luhn_valid
from securewaste.core.extraction import PageText
from securewaste.core.risk import assess
from securewaste.services.detect_service import detect_pages

HMAC_KEY = b"test-only-hmac-key"
CARD = "4111 1111 1111 1111"  # public Visa test number
IBAN = "TN59 1000 6035 1835 9847 8831"  # standard Tunisian IBAN example
AWS = "AKIAQWERTYUIOPASDFGH"  # fictional, from scripts/evaluate_realistic.py


def values(rule, text):
    return [c.raw_value for c in rule.find(PageText(page_number=1, text=text))]


def scan(text):
    return detect_pages([PageText(page_number=1, text=text)], [], 0.3, HMAC_KEY)


# --- validators ------------------------------------------------------------------------------


@pytest.mark.parametrize("number", ["4242424242424242", CARD, "5500-0000-0000-0004", "378282246310005"])
def test_luhn_accepts_test_cards(number):
    assert luhn_valid(number)


@pytest.mark.parametrize("number", ["4242424242424241", "0000 0000 0000 0000", "1234", "abcd" * 4, "", None])
def test_luhn_rejects_bad_input_without_raising(number):
    assert not luhn_valid(number)


@pytest.mark.parametrize("iban", ["GB82WEST12345698765432", "gb82 west 1234 5698 7654 32", IBAN])
def test_iban_accepts_valid(iban):
    assert iban_valid(iban)


@pytest.mark.parametrize("iban", ["GB83WEST12345698765432", "TN59", "hello world", "", None, "٤٢" * 10])
def test_iban_rejects_bad_input_without_raising(iban):
    assert not iban_valid(iban)


# --- cards and IBANs -------------------------------------------------------------------------


def test_card_rule_keeps_only_luhn_valid_numbers():
    text = f"Card {CARD}, typo 4111 1111 1111 1112, order 20261126, phone +216 20 123 456."
    assert values(PaymentCardRule(), text) == [CARD]


def test_card_rule_ignores_digits_inside_longer_numbers():
    assert values(PaymentCardRule(), "ref 4111111111111111999999 and id-4111111111111111") == []


def test_iban_rule():
    text = f"RIB: {IBAN}. Wrong: TN59 1000 6035 1835 9847 8832. Code AB12CD."
    assert values(IbanRule(), text) == [IBAN]


# --- secrets ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "secret"),
    [
        (f"aws_access_key_id = {AWS}", AWS),
        ("-----BEGIN RSA PRIVATE KEY-----\nMIIfake\n", "-----BEGIN RSA PRIVATE KEY-----"),
        ("stripe: sk_live_51Qm7T9xP2zA8bC6dE4fG", "sk_live_51Qm7T9xP2zA8bC6dE4fG"),
        ("token ghp_" + "a1B2" * 9, "ghp_" + "a1B2" * 9),
        ("password: D7v!q9Lz#2Kp", "D7v!q9Lz#2Kp"),
        ('API_KEY="Zk3mP9qR7tW2xY5vB8nC"', "Zk3mP9qR7tW2xY5vB8nC"),
        ("postgresql://root:V3ryS3cret!@db.internal:5432/prod", "V3ryS3cret!"),
    ],
)
def test_secret_rule_finds_credentials(text, secret):
    assert secret in values(SecretRule(), text)


@pytest.mark.parametrize(
    "text",
    [
        "AWS docs example: AKIAIOSFODNN7EXAMPLE",
        "password: changeme123",
        "password = <your password here>",
        'api_key = os.environ["API_KEY"]',
        "Use a strong password and rotate your API keys.",
        "password: short",
    ],
)
def test_secret_rule_ignores_placeholders_and_prose(text):
    assert values(SecretRule(), text) == []


def test_high_and_lower_confidence_secrets():
    page = PageText(page_number=1, text=f"key {AWS} and password: D7v!q9Lz#2Kp")
    confidences = {c.raw_value: c.confidence for c in SecretRule().find(page)}
    assert confidences[AWS] == 0.95 and confidences["D7v!q9Lz#2Kp"] == 0.8


# --- labels ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("STRICTLY CONFIDENTIAL - board pack", "STRICTLY CONFIDENTIAL"),
        ("Header: RESTRICTED", "RESTRICTED"),
        ("Classification: Confidential", "Confidential"),
        ("Sensitivity - internal use only", "internal use only"),
    ],
)
def test_label_rule_finds_markings(text, label):
    assert values(ConfidentialityLabelRule(), text) == [label]


@pytest.mark.parametrize("text", ["Please keep this confidential.", "Our secret sauce is speed.", "Internal tools"])
def test_label_rule_ignores_ordinary_words(text):
    assert values(ConfidentialityLabelRule(), text) == []


# --- end to end: masking, privacy, risk ------------------------------------------------------

DOCUMENT = f"CONFIDENTIAL\nPay with card {CARD} or to IBAN {IBAN}.\naws_access_key_id = {AWS}\n"


def test_raw_values_never_reach_findings():
    findings = scan(DOCUMENT)
    assert {f.category for f in findings} == {
        Category.PAYMENT_CARD,
        Category.IBAN,
        Category.SECRET,
        Category.CONFIDENTIALITY_LABEL,
    }
    exposed = " ".join(f"{f.masked_value} {f.context}" for f in findings)
    for raw in (CARD, CARD.replace(" ", ""), IBAN, IBAN.replace(" ", ""), AWS, "CONFIDENTIAL"):
        assert raw not in exposed


def test_card_finding_records_its_validation():
    (card,) = [f for f in scan(DOCUMENT) if f.category is Category.PAYMENT_CARD]
    assert card.validation == "Luhn checksum passed"


def test_real_document_now_scores_critical():
    result = assess(scan(DOCUMENT))
    assert result.level == "critical" and result.score >= 75
    codes = {factor.code for factor in result.factors}
    assert {"combination_bonus", "label_amplifier"} <= codes


@pytest.mark.parametrize("rule", [PaymentCardRule(), IbanRule(), SecretRule(), ConfidentialityLabelRule()])
def test_rules_stay_fast_on_hostile_input(rule):
    hostile = ("1 " * 50_000) + ("A1" * 50_000) + ("password:" + "x" * 50_000) + ("Classification:" + " " * 50_000)
    start = time.perf_counter()
    rule.find(PageText(page_number=1, text=hostile))
    assert time.perf_counter() - start < 2.0
