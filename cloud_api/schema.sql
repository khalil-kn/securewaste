-- SCRUM-27: schema for the scan_events table of the SecureWaste cloud metadata API.
--
-- Privacy invariant: this table holds metadata only. There is no column for raw text, extracted
-- text, documents, filenames, file paths, findings, snippets or matched values, and the test
-- suite fails if one is ever added. The local scanner (securewaste/) sends counts, never content.
--
-- The script is idempotent: running it again on an existing database changes nothing.

CREATE TABLE IF NOT EXISTS scan_events (
    event_id        UUID        PRIMARY KEY,
    event_timestamp TIMESTAMPTZ NOT NULL,
    classification  TEXT        NOT NULL,
    risk            TEXT        NOT NULL,
    email_count     INTEGER     NOT NULL DEFAULT 0,
    phone_count     INTEGER     NOT NULL DEFAULT 0,
    keyword_count   INTEGER     NOT NULL DEFAULT 0,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT scan_events_classification_check
        CHECK (classification IN ('Public', 'Internal', 'Confidential', 'Highly Confidential')),
    CONSTRAINT scan_events_risk_check
        CHECK (risk IN ('Low', 'Medium', 'High')),
    CONSTRAINT scan_events_email_count_check CHECK (email_count >= 0),
    CONSTRAINT scan_events_phone_count_check CHECK (phone_count >= 0),
    CONSTRAINT scan_events_keyword_count_check CHECK (keyword_count >= 0)
);

-- The dashboard reads recent events first.
-- An owner identifier is deliberately absent.
CREATE INDEX IF NOT EXISTS scan_events_received_at_idx ON scan_events (received_at DESC);
