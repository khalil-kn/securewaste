"""Checksum validators (FR-09, FR-10). SCRUM-46.

luhn_valid(number: str) -> bool     — payment cards ("4242424242424242" is valid)
iban_valid(iban: str) -> bool       — mod-97 == 1 ("GB82WEST12345698765432" is valid)
Both ignore spaces and dashes and return False (never raise) on garbage input.

A passing checksum means "this has the shape of a real card/IBAN", not "this card/account exists".
"""

from __future__ import annotations

import re

_SEPARATORS = re.compile(r"[\s-]")
_IBAN_SHAPE = re.compile(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}")


def _compact(value: str) -> str:
    return _SEPARATORS.sub("", value) if isinstance(value, str) else ""


def luhn_valid(number: str) -> bool:
    digits = _compact(number)
    if not 13 <= len(digits) <= 19 or not digits.isascii() or not digits.isdigit():
        return False
    if len(set(digits)) == 1:  # 0000 0000 0000 0000 passes Luhn but is filler, not a card
        return False
    total = 0
    for index, char in enumerate(reversed(digits)):
        digit = int(char)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def iban_valid(iban: str) -> bool:
    value = _compact(iban).upper()
    if not value.isascii() or not _IBAN_SHAPE.fullmatch(value):
        return False
    rearranged = value[4:] + value[:4]
    remainder = 0
    for char in rearranged:
        for digit in char if char.isdigit() else str(ord(char) - ord("A") + 10):
            remainder = (remainder * 10 + int(digit)) % 97
    return remainder == 1
