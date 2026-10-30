"""Guards on the shared contracts every teammate builds on."""

from dataclasses import fields
from pathlib import Path

from securewaste.core.detection.catalogue import CATALOGUE, REVIEW_TRANSITIONS, Category, ReviewStatus
from securewaste.core.detection.models import Finding

CORE = Path(__file__).resolve().parents[2] / "securewaste" / "core"


def test_finding_never_carries_a_raw_value():  # ADR-0006
    names = {f.name for f in fields(Finding)}
    assert {"masked_value", "value_hmac"} <= names
    assert not names & {"raw_value", "value", "match", "text"}


def test_catalogue_covers_every_category():
    assert set(CATALOGUE) == set(Category)


def test_review_transitions_match_architecture_doc():
    assert REVIEW_TRANSITIONS[ReviewStatus.RESOLVED] == {ReviewStatus.OPEN}
    assert ReviewStatus.RESOLVED not in REVIEW_TRANSITIONS[ReviewStatus.FALSE_POSITIVE]


def test_core_never_imports_flask():  # NFR-08: core stays testable without a web server
    offenders = [
        p.name
        for p in CORE.rglob("*.py")
        if "import flask" in p.read_text().lower() or "from flask" in p.read_text().lower()
    ]
    assert offenders == []
