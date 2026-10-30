"""Repositories: the only place that writes SQL (ADR-0003).

Rules for everyone adding functions here:
  * parameterised queries only — conn.execute("... WHERE id = ?", (doc_id,)), never f-strings (T-05);
  * one small function per query (insert_document, get_document, list_findings, ...);
  * never accept or return raw sensitive values — findings carry masked_value and value_hmac only.

Filled in Milestone 3 (persistence). Example of the expected style:

    def get_document(conn, document_id: str) -> sqlite3.Row | None:
        return conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
"""
