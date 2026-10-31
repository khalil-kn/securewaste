"""Detection: rules find candidates, validators confirm them, the engine merges and masks them."""

from securewaste.core.detection.engine import DetectionEngine
from securewaste.core.detection.masking import mask, value_hmac
from securewaste.core.detection.models import Candidate, Finding
from securewaste.core.detection.rules import EmailRule, PhoneRule, KeywordRule

__all__ = [
    "DetectionEngine",
    "mask",
    "value_hmac",
    "Candidate",
    "Finding",
    "EmailRule",
    "PhoneRule",
    "KeywordRule",
]
