"""Checksum validators. Owner: Milestone 2.

luhn_valid(number: str) -> bool     — payment cards ("4242424242424242" is valid)
iban_valid(iban: str) -> bool       — mod-97 == 1 ("GB82WEST12345698765432" is valid)
Both must ignore spaces and dashes and return False (never raise) on garbage input.
"""
