"""Upload and scan orchestration (UC-01, sequence diagram seq-upload-scan).

upload_and_scan(filename, data) -> document_id:
    validate -> store original -> create scan(running) -> extract -> detect -> assess
    -> save findings + risk -> scan(completed) -> audit events.
On any error: scan(failed, error_code), remove temp files, never leave half-written rows.
Milestone 1 wires validate + extract + detect; persistence arrives in Milestone 3.
"""

from __future__ import annotations

import logging
from pathlib import Path

from securewaste.core.detection.engine import DetectionEngine
from securewaste.core.detection.models import Finding
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.errors import ExtractionFailed, UploadRejected
from securewaste.core.extraction import extract_pages
from securewaste.core.upload import Limits, ValidatedUpload, validate_upload

logger = logging.getLogger(__name__)


def upload_and_scan(
    filename: str,
    data: bytes,
    rules: list[DetectionRule],
    min_confidence: float,
    hmac_key: bytes,
    storage_dir: Path,
    upload_limits: Limits | dict | None = None,
) -> list[Finding]:
    """
    Orchestrate the full upload-and-scan flow.

    Steps:
    1. validate_upload - returns ValidatedUpload with safe stored_name
    2. Save file to storage/tmp/<stored_name>
    3. extract_pages - returns list[PageText]
    4. DetectionEngine.scan - returns list[Finding]

    The temp file is ALWAYS deleted in finally block, even if extraction fails.
    """
    # Step 1: Validate - convert dict to Limits if needed
    if upload_limits is None:
        limits_obj = Limits(
            max_bytes=10 * 1024 * 1024,
            max_pdf_pages=100,
            max_extracted_chars=2_000_000,
        )
    elif isinstance(upload_limits, dict):
        limits_obj = Limits(
            max_bytes=upload_limits["max_bytes"],
            max_pdf_pages=upload_limits["max_pdf_pages"],
            max_extracted_chars=upload_limits["max_extracted_chars"],
        )
    else:
        limits_obj = upload_limits

    validated: ValidatedUpload = validate_upload(filename, data, limits_obj)

    # Step 2: Save to temp location
    tmp_path = storage_dir / "tmp" / validated.stored_name
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_bytes(data)

    try:
        # Step 3: Extract
        pages = extract_pages(tmp_path, validated.file_type, limits_obj)

        # Step 4: Detect
        engine = DetectionEngine(rules=rules, min_confidence=min_confidence, hmac_key=hmac_key)
        findings = engine.scan(pages)

        # Log only counts and short hash, never raw values
        finding_count = len(findings)
        sample_hashes = [f.value_hmac[:8] for f in findings[:3]]
        logger.info("Scan completed: %d findings, sample hashes: %s", finding_count, sample_hashes)

        return findings

    except UploadRejected:
        # Re-raise upload errors as-is
        raise
    except ExtractionFailed:
        # Re-raise extraction errors as-is
        raise
    finally:
        # ALWAYS clean up temp file, even if extraction/detection failed
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError as e:
            logger.warning("Failed to delete temp file %s: %s", tmp_path, e)