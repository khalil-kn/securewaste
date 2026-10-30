"""Upload and scan orchestration (UC-01, sequence diagram seq-upload-scan).

upload_and_scan(filename, data) -> document_id:
    validate -> store original -> create scan(running) -> extract -> detect -> assess
    -> save findings + risk -> scan(completed) -> audit events.
On any error: scan(failed, error_code), remove temp files, never leave half-written rows.
Milestone 1 wires validate + extract + detect; persistence arrives in Milestone 3.
"""
