"""The schema enforces the data model: all tables exist, foreign keys and cascades work."""

import sqlite3

import pytest

TABLES = {"documents", "scans", "findings", "review_actions", "redactions", "redaction_items", "audit_events"}
NOW = "2026-11-03T09:15:00Z"


def insert_document(db, doc_id="d1"):
    db.execute(
        "INSERT INTO documents VALUES (?, 'invoice.pdf', ?, 'pdf', 10, 'abc', 1, ?)", (doc_id, f"{doc_id}.pdf", NOW)
    )


def test_all_tables_exist(db):
    names = {r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert TABLES <= names


def test_foreign_keys_are_enforced(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO scans (id, document_id, status, ruleset_version, started_at) "
            "VALUES ('s1', 'missing-doc', 'running', 'v', ?)",
            (NOW,),
        )


def test_deleting_document_cascades_but_keeps_audit(db):
    insert_document(db)
    db.execute(
        "INSERT INTO scans (id, document_id, status, ruleset_version, started_at) "
        "VALUES ('s1', 'd1', 'completed', 'v', ?)",
        (NOW,),
    )
    db.execute(
        "INSERT INTO audit_events (occurred_at, actor, event_type, document_id) "
        "VALUES (?, 'local-user', 'document.uploaded', 'd1')",
        (NOW,),
    )
    db.execute("DELETE FROM documents WHERE id = 'd1'")
    assert db.execute("SELECT COUNT(*) FROM scans").fetchone()[0] == 0
    event = db.execute("SELECT document_id FROM audit_events").fetchone()
    assert event["document_id"] is None  # ON DELETE SET NULL


def test_review_status_check_constraint(db):
    insert_document(db)
    db.execute(
        "INSERT INTO scans (id, document_id, status, ruleset_version, started_at) "
        "VALUES ('s1', 'd1', 'completed', 'v', ?)",
        (NOW,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO findings (id, scan_id, rule_id, category, severity, confidence, char_start, "
            "char_end, masked_value, value_hmac, explanation, recommendation, review_status, updated_at) "
            "VALUES ('f1', 's1', 'r', 'email', 'low', 0.9, 0, 5, 'm', 'h', 'e', 'r', 'resloved', ?)",
            (NOW,),
        )
