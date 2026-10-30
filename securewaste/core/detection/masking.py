"""Masking and keyed hashing (FR-13, ADR-0006). Owner: Milestone 1 issue #5.

mask(category, value)        -> "•••• •••• •••• 4242", "s•••@e•••.tn", "AKIA••••••••"
value_hmac(key, rule_id, v)  -> HMAC-SHA256 hex of rule_id + normalised value (use hmac + hashlib)
"""
