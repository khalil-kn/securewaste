"""Risk score (SCRUM-46 M2). All data is synthetic. Worked example from architecture §8."""

import json
import math

import pytest

from securewaste.core.detection.catalogue import CATALOGUE, Category, ReviewStatus, Severity
from securewaste.core.detection.models import Finding
from securewaste.core.risk import NO_FINDINGS_REASON, SCORE_VERSION, assess, level_for

MASKED = "SHOULD-NEVER-APPEAR-masked"
CONTEXT = "SHOULD-NEVER-APPEAR-context"


def f(category, confidence=0.95, value="v1", page=1, status=ReviewStatus.OPEN, occurrences=1):
    return Finding(
        rule_id=f"rule.{category.value}",
        category=category,
        severity=CATALOGUE[category].severity,
        confidence=confidence,
        page_number=page,
        char_start=0,
        char_end=5,
        masked_value=f"{MASKED}-{value}",
        value_hmac=f"hmac-{category.value}-{value}",
        context=CONTEXT,
        explanation=CATALOGUE[category].explanation,
        recommendation=CATALOGUE[category].recommendation,
        occurrences=occurrences,
        review_status=status,
    )


def reconciles(result):
    return math.isclose(sum(x.points for x in result.factors), result.score, abs_tol=1e-9)


# --- worked example and basics ---------------------------------------------------------------


def test_worked_example_from_architecture():
    # 2.7 + 2.4 + 38 + 23.75 + 10 + 10 (combination) + 10 (label amplifier) = 96.85 -> 97 -> critical
    result = assess(
        [
            f(Category.EMAIL, 0.9),
            f(Category.PHONE, 0.6),
            f(Category.PAYMENT_CARD, 0.95),
            f(Category.IBAN, 0.95),
            f(Category.CONFIDENTIALITY_LABEL, 1.0),
        ]
    )
    assert result.score == 97
    assert result.level == Severity.CRITICAL
    codes = [x.code for x in result.factors]
    assert "combination_bonus" in codes and "label_amplifier" in codes
    assert reconciles(result)


def test_empty_document_is_informational():
    result = assess([])
    assert (result.score, result.level, result.factors) == (0, Severity.INFORMATIONAL, ())
    assert result.reasons == [NO_FINDINGS_REASON] and result.recommendations == []


def test_false_positives_are_ignored():
    result = assess([f(Category.SECRET, 0.95, status=ReviewStatus.FALSE_POSITIVE), f(Category.EMAIL, 1.0)])
    assert result.score == 3
    assert all("secret" not in x.code for x in result.factors)


def test_only_false_positives_equals_empty():
    assert assess([f(Category.PAYMENT_CARD, status=ReviewStatus.FALSE_POSITIVE)]).score == 0


# --- repetition is capped --------------------------------------------------------------------


def test_same_value_repeated_adds_nothing():
    once = assess([f(Category.EMAIL, 1.0)])
    many = assess([f(Category.EMAIL, 1.0, occurrences=500), f(Category.EMAIL, 1.0, page=2)])  # same value_hmac
    assert once.score == many.score == 3


def test_distinct_values_have_diminishing_effect_and_cap():
    # Phone W=4: first 4 + 3 extras x 0.8 = 6.4 -> 6. The 4th..10th extra values add nothing.
    ten = [f(Category.PHONE, 1.0, value=str(i)) for i in range(10)]
    four = ten[:4]
    assert assess(ten).score == assess(four).score == 6
    assert "only 4 counted" in assess(ten).reasons[0]


def test_many_emails_cannot_outscore_one_secret():
    emails = assess([f(Category.EMAIL, 1.0, value=str(i)) for i in range(1000)])
    secret = assess([f(Category.SECRET, 0.9)])
    assert emails.score < secret.score


# --- confidence, floors, levels --------------------------------------------------------------


def test_low_confidence_counts_less():
    assert assess([f(Category.IBAN, 0.4)]).score < assess([f(Category.IBAN, 0.95)]).score


def test_high_confidence_secret_floor():
    result = assess([f(Category.SECRET, 0.9)])  # 45 x 0.9 = 40.5 -> 41, floor -> 75
    assert result.score == 75 and result.level == Severity.CRITICAL
    assert "floor:secret" in [x.code for x in result.factors]
    assert reconciles(result)


def test_low_confidence_secret_gets_no_floor():
    result = assess([f(Category.SECRET, 0.6)])  # 27, medium
    assert result.score == 27 and result.level == Severity.MEDIUM


def test_payment_card_floor():
    result = assess([f(Category.PAYMENT_CARD, 0.95)])  # 38 -> floor 50
    assert result.score == 50 and result.level == Severity.HIGH and reconciles(result)


def test_score_is_capped_at_100():
    findings = [f(c, 1.0, value=str(i)) for c in Category for i in range(4)]
    result = assess(findings)
    assert result.score == 100 and "cap" in [x.code for x in result.factors] and reconciles(result)


@pytest.mark.parametrize(
    ("score", "level"),
    [
        (0, Severity.INFORMATIONAL),
        (9, Severity.INFORMATIONAL),
        (10, Severity.LOW),
        (24, Severity.LOW),
        (25, Severity.MEDIUM),
        (49, Severity.MEDIUM),
        (50, Severity.HIGH),
        (74, Severity.HIGH),
        (75, Severity.CRITICAL),
        (100, Severity.CRITICAL),
    ],
)
def test_level_boundaries(score, level):
    assert level_for(score) == level


def test_half_point_rounds_up_at_a_boundary():
    # IBAN W=25 x 0.98 = 24.5 -> 25 (medium). Python's round(24.5) would give 24 (low).
    result = assess([f(Category.IBAN, 0.98)])
    assert result.score == 25 and result.level == Severity.MEDIUM


def test_label_alone_gets_no_amplifier():
    result = assess([f(Category.CONFIDENTIALITY_LABEL, 1.0), f(Category.EMAIL, 1.0)])
    assert result.score == 13 and "label_amplifier" not in [x.code for x in result.factors]


# --- explanation, determinism, privacy -------------------------------------------------------


def test_factors_always_reconcile_with_score():
    cases = [
        [f(Category.EMAIL, 0.9)],
        [f(Category.SECRET, 0.95), f(Category.PAYMENT_CARD, 0.95)],
        [f(Category.KEYWORD, 0.7, value=str(i)) for i in range(7)],
        [f(c, 0.55, value=str(i)) for c in Category for i in range(2)],
    ]
    for findings in cases:
        assert reconciles(assess(findings))


def test_same_input_same_output_regardless_of_order():
    findings = [f(Category.EMAIL, 0.9), f(Category.IBAN, 0.95), f(Category.PHONE, 0.6, value="x")]
    assert assess(findings) == assess(list(reversed(findings))) == assess(findings)


def test_output_never_contains_sensitive_strings():
    findings = [f(c, 0.9, value=f"secret-{c.value}") for c in Category]
    payload = json.dumps(assess(findings).to_dict())
    assert MASKED not in payload and CONTEXT not in payload and "hmac-" not in payload


def test_recommendations_come_from_catalogue_and_include_manual_review():
    result = assess([f(Category.SECRET, 0.95), f(Category.PAYMENT_CARD, 0.95)])
    assert result.recommendations[0] == CATALOGUE[Category.SECRET].recommendation
    assert any("manual review" in r for r in result.recommendations)


def test_listed_reasons_add_up_to_the_score():
    # Each reason shows one decimal and rounding is listed when visible, so a reader can check the sum.
    findings = [
        f(Category.KEYWORD, 0.6),
        f(Category.PHONE, 0.7),
        f(Category.EMAIL, 0.8, value="a"),
        f(Category.EMAIL, 0.8, value="b"),
    ]
    result = assess(findings)
    shown = sum(float(reason.split()[0]) for reason in result.reasons)
    assert math.isclose(shown, result.score, abs_tol=0.051 * len(result.reasons))
    assert result.score == 10 and any("Rounded" in r for r in result.reasons)


def test_score_is_versioned():
    assert assess([]).score_version == SCORE_VERSION
    assert assess([]).to_dict()["score_version"] == SCORE_VERSION
