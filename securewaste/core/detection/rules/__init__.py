"""One rule per file: email.py, phone.py, keywords.py, payment_card.py, iban.py, secrets.py, labels.py, …"""

from securewaste.core.detection.rules.email import EmailRule
from securewaste.core.detection.rules.phone import PhoneRule
from securewaste.core.detection.rules.keywords import KeywordRule

__all__ = [
    "EmailRule",
    "PhoneRule",
    "KeywordRule",
]
