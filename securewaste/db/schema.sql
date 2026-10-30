-- SecureWaste database schema (docs/02-architecture.md §7, docs/diagrams/src/data-model.puml).
-- Owned by the tech lead: change it only through a PR that also updates the data-model diagram.
-- Raw sensitive values are NEVER stored: findings keep a masked value and a keyed hash (ADR-0006).
-- Timestamps are ISO-8601 UTC text, e.g. 2026-11-03T09:15:00Z. IDs are UUIDv4 text.

CREATE TABLE IF NOT EXISTS documents (
    id            TEXT PRIMARY KEY,
    display_name  TEXT NOT NULL,                 -- sanitised original name, display only
    stored_name   TEXT NOT NULL UNIQUE,          -- <uuid>.<ext> on disk
    file_type     TEXT NOT NULL CHECK (file_type IN ('pdf', 'txt')),
    size_bytes    INTEGER NOT NULL CHECK (size_bytes > 0),
    sha256        TEXT NOT NULL,
    page_count    INTEGER NOT NULL CHECK (page_count >= 1),
    uploaded_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scans (
    id               TEXT PRIMARY KEY,
    document_id      TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    status           TEXT NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    ruleset_version  TEXT NOT NULL,
    started_at       TEXT NOT NULL,
    finished_at      TEXT,
    risk_score       INTEGER CHECK (risk_score BETWEEN 0 AND 100),
    risk_level       TEXT CHECK (risk_level IN ('informational', 'low', 'medium', 'high', 'critical')),
    risk_reasons     TEXT,                       -- JSON array of strings
    error_code       TEXT
);

CREATE TABLE IF NOT EXISTS findings (
    id              TEXT PRIMARY KEY,
    scan_id         TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    rule_id         TEXT NOT NULL,
    category        TEXT NOT NULL,
    severity        TEXT NOT NULL CHECK (severity IN ('informational', 'low', 'medium', 'high', 'critical')),
    confidence      REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    page_number     INTEGER,
    char_start      INTEGER NOT NULL,
    char_end        INTEGER NOT NULL,
    occurrences     INTEGER NOT NULL DEFAULT 1 CHECK (occurrences >= 1),
    masked_value    TEXT NOT NULL,
    value_hmac      TEXT NOT NULL,
    context_masked  TEXT,
    explanation     TEXT NOT NULL,
    recommendation  TEXT NOT NULL,
    review_status   TEXT NOT NULL DEFAULT 'open'
                    CHECK (review_status IN ('open', 'confirmed', 'false_positive', 'resolved')),
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_actions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id   TEXT NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    from_status  TEXT NOT NULL,
    to_status    TEXT NOT NULL,
    note         TEXT CHECK (note IS NULL OR length(note) <= 500),
    actor        TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS redactions (
    id                TEXT PRIMARY KEY,
    document_id       TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    scan_id           TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    output_name       TEXT NOT NULL,
    status            TEXT NOT NULL CHECK (status IN ('verified', 'incomplete', 'failed')),
    redacted_count    INTEGER NOT NULL DEFAULT 0,
    unmappable_count  INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS redaction_items (
    redaction_id  TEXT NOT NULL REFERENCES redactions(id) ON DELETE CASCADE,
    finding_id    TEXT NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    outcome       TEXT NOT NULL CHECK (outcome IN ('redacted', 'unmappable', 'still_present')),
    PRIMARY KEY (redaction_id, finding_id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at  TEXT NOT NULL,
    actor        TEXT NOT NULL,
    event_type   TEXT NOT NULL,                  -- e.g. document.uploaded, scan.completed
    document_id  TEXT REFERENCES documents(id) ON DELETE SET NULL,   -- event survives deletion
    scan_id      TEXT,
    details      TEXT                            -- JSON: IDs and counts only, never values or filenames
);

CREATE INDEX IF NOT EXISTS idx_scans_document ON scans(document_id, started_at);
CREATE INDEX IF NOT EXISTS idx_findings_scan ON findings(scan_id);
CREATE INDEX IF NOT EXISTS idx_findings_category ON findings(category);
CREATE INDEX IF NOT EXISTS idx_findings_review ON findings(review_status);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_events(occurred_at);
