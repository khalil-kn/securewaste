from __future__ import annotations

import logging

from securewaste.core.privacy import (
    build_masked_context,
    install_log_redaction,
    mask_value,
    scrub,
)

TEXT = "Internal Waste Report Contact: alice.secret@example.com Phone: (202) 555-0104 Status: CONFIDENTIAL"
EMAIL = {"start": TEXT.index("alice"), "end": TEXT.index(" Phone"), "type": "email"}


def test_context_masks_other_findings():
    ctx = build_masked_context(TEXT, [EMAIL], EMAIL, window=200)
    assert "alice.secret@example.com" not in ctx
    assert "555-0104" not in ctx  # phone masked even though not passed
    assert "CONFIDENTIAL" not in ctx  # keyword masked
    assert "a\u2022\u2022\u2022@e\u2022\u2022\u2022.com" in ctx


def test_context_no_half_words():
    ctx = build_masked_context(TEXT, [EMAIL], EMAIL, window=12)
    assert "CONFIDENTI" not in ctx and "nternal" not in ctx.replace("Internal", "")


def test_scrub_secrets_and_tokens():
    s = scrub("key sk-TEST-1234567890abcdef Password: Hunter2 SECRET_TOKEN_998877 +216 71 123 456")
    for bad in ("sk-TEST", "Hunter2", "SECRET_TOKEN_998877", "71 123 456"):
        assert bad not in s


def test_mask_value_email():
    assert mask_value("alice.secret@example.com", "email") == "a\u2022\u2022\u2022@e\u2022\u2022\u2022.com"


def test_logs_are_redacted(caplog):
    install_log_redaction()
    log = logging.getLogger("t")
    with caplog.at_level("DEBUG"):
        log.info("got %s and %s", "alice.secret@example.com", "(202) 555-0104")
        try:
            raise ValueError("bad SECRET_TOKEN_998877")
        except ValueError:
            log.exception("failed")
    assert "alice.secret" not in caplog.text
    assert "555-0104" not in caplog.text
    assert "SECRET_TOKEN_998877" not in caplog.text
