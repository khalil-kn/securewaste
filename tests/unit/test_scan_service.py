"""Unit tests for scan_service.upload_and_scan with monkeypatched stubs."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from securewaste.core.detection.catalogue import Category, Severity
from securewaste.core.detection.models import Finding
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.extraction import PageText
from securewaste.core.upload import Limits, ValidatedUpload
from securewaste.core.errors import UploadRejected, ExtractionFailed
from securewaste.services.scan_service import upload_and_scan


class FakeRule(DetectionRule):
    rule_id = "fake.rule"
    category = Category.EMAIL
    base_confidence = 0.9
    context_words = ()

    def find(self, page: PageText) -> list:
        return []


@pytest.fixture
def fake_finding():
    return Finding(
        rule_id="email.basic",
        category=Category.EMAIL,
        severity=Severity.LOW,
        confidence=0.95,
        page_number=1,
        char_start=100,
        char_end=130,
        masked_value="j••••@e•••••.com",
        value_hmac="a1b2c3d4e5f6",
        context="Contact: j••••@e•••••.com for details",
        explanation="An e-mail address is personal data.",
        recommendation="Keep it only if the recipient needs it.",
        occurrences=2,
        validation="",
        review_status="open",
        id="f1",
    )


@pytest.fixture
def fake_validated_upload():
    return ValidatedUpload(
        file_type="pdf",
        display_name="test.pdf",
        stored_name=f"{uuid.uuid4()}.pdf",
        size_bytes=1024,
        sha256="abc123",
        page_count=3,
    )


@pytest.fixture
def fake_pages():
    return [
        PageText(page_number=1, text="Page 1 content"),
        PageText(page_number=2, text="Page 2 content"),
        PageText(page_number=3, text="Page 3 content"),
    ]


@pytest.fixture
def temp_storage_dir(tmp_path):
    """Create a temporary storage directory with tmp subdir."""
    storage = tmp_path / "storage"
    (storage / "tmp").mkdir(parents=True)
    return storage


class TestUploadAndScan:
    """Tests for upload_and_scan function."""

    def test_returns_findings_on_success(
        self, temp_storage_dir, fake_validated_upload, fake_pages, fake_finding
    ):
        """upload_and_scan returns findings when all steps succeed."""
        rules = [FakeRule()]
        hmac_key = b"test-hmac-key-32-bytes-long-enough!!"

        with patch("securewaste.services.scan_service.validate_upload") as mock_validate:
            with patch("securewaste.services.scan_service.extract_pages") as mock_extract:
                with patch("securewaste.services.scan_service.DetectionEngine") as mock_engine_class:
                    # Setup mocks
                    mock_validate.return_value = fake_validated_upload
                    mock_extract.return_value = fake_pages
                    mock_engine = MagicMock()
                    mock_engine.scan.return_value = [fake_finding]
                    mock_engine_class.return_value = mock_engine

                    # Call
                    findings = upload_and_scan(
                        filename="test.pdf",
                        data=b"fake pdf content",
                        rules=rules,
                        min_confidence=0.3,
                        hmac_key=hmac_key,
                        storage_dir=temp_storage_dir,
                    )

                    # Assert
                    assert findings == [fake_finding]
                    mock_validate.assert_called_once()
                    mock_extract.assert_called_once()
                    mock_engine.scan.assert_called_once_with(fake_pages)

    def test_temp_file_removed_on_success(
        self, temp_storage_dir, fake_validated_upload, fake_pages, fake_finding
    ):
        """Temp file is deleted after successful scan."""
        rules = [FakeRule()]
        hmac_key = b"test-hmac-key-32-bytes-long-enough!!"

        with patch("securewaste.services.scan_service.validate_upload") as mock_validate:
            with patch("securewaste.services.scan_service.extract_pages") as mock_extract:
                with patch("securewaste.services.scan_service.DetectionEngine") as mock_engine_class:
                    mock_validate.return_value = fake_validated_upload
                    mock_extract.return_value = fake_pages
                    mock_engine = MagicMock()
                    mock_engine.scan.return_value = [fake_finding]
                    mock_engine_class.return_value = mock_engine

                    upload_and_scan(
                        filename="test.pdf",
                        data=b"fake pdf content",
                        rules=rules,
                        min_confidence=0.3,
                        hmac_key=hmac_key,
                        storage_dir=temp_storage_dir,
                    )

                    # Check temp file was deleted
                    tmp_files = list((temp_storage_dir / "tmp").glob("*"))
                    assert len(tmp_files) == 0, f"Temp files remain: {tmp_files}"

    def test_temp_file_removed_when_extraction_fails(
        self, temp_storage_dir, fake_validated_upload
    ):
        """Temp file is deleted even when extract_pages raises ExtractionFailed."""
        rules = [FakeRule()]
        hmac_key = b"test-hmac-key-32-bytes-long-enough!!"

        with patch("securewaste.services.scan_service.validate_upload") as mock_validate:
            with patch("securewaste.services.scan_service.extract_pages") as mock_extract:
                mock_validate.return_value = fake_validated_upload
                mock_extract.side_effect = ExtractionFailed("NO_TEXT_LAYER")

                with pytest.raises(ExtractionFailed):
                    upload_and_scan(
                        filename="test.pdf",
                        data=b"fake pdf content",
                        rules=rules,
                        min_confidence=0.3,
                        hmac_key=hmac_key,
                        storage_dir=temp_storage_dir,
                    )

                # Check temp file was deleted even on extraction failure
                tmp_files = list((temp_storage_dir / "tmp").glob("*"))
                assert len(tmp_files) == 0, f"Temp files remain after extraction failure: {tmp_files}"

    def test_temp_file_removed_when_detection_fails(
        self, temp_storage_dir, fake_validated_upload, fake_pages
    ):
        """Temp file is deleted even when DetectionEngine.scan raises an exception."""
        rules = [FakeRule()]
        hmac_key = b"test-hmac-key-32-bytes-long-enough!!"

        with patch("securewaste.services.scan_service.validate_upload") as mock_validate:
            with patch("securewaste.services.scan_service.extract_pages") as mock_extract:
                with patch("securewaste.services.scan_service.DetectionEngine") as mock_engine_class:
                    mock_validate.return_value = fake_validated_upload
                    mock_extract.return_value = fake_pages
                    mock_engine = MagicMock()
                    mock_engine.scan.side_effect = RuntimeError("Detection crashed")
                    mock_engine_class.return_value = mock_engine

                    with pytest.raises(RuntimeError, match="Detection crashed"):
                        upload_and_scan(
                            filename="test.pdf",
                            data=b"fake pdf content",
                            rules=rules,
                            min_confidence=0.3,
                            hmac_key=hmac_key,
                            storage_dir=temp_storage_dir,
                        )

                    # Check temp file was deleted even on detection failure
                    tmp_files = list((temp_storage_dir / "tmp").glob("*"))
                    assert len(tmp_files) == 0, f"Temp files remain after detection failure: {tmp_files}"

    def test_steps_run_in_order_validate_extract_detect(
        self, temp_storage_dir, fake_validated_upload, fake_pages, fake_finding
    ):
        """Steps run in correct order: validate -> extract -> detect."""
        rules = [FakeRule()]
        hmac_key = b"test-hmac-key-32-bytes-long-enough!!"
        call_order = []

        with patch("securewaste.services.scan_service.validate_upload") as mock_validate:
            with patch("securewaste.services.scan_service.extract_pages") as mock_extract:
                with patch("securewaste.services.scan_service.DetectionEngine") as mock_engine_class:
                    def track_validate(*args, **kwargs):
                        call_order.append("validate")
                        return fake_validated_upload

                    def track_extract(*args, **kwargs):
                        call_order.append("extract")
                        return fake_pages

                    def track_engine_init(*args, **kwargs):
                        call_order.append("engine_init")
                        mock_engine = MagicMock()
                        def track_scan(*a, **k):
                            call_order.append("detect")
                            return [fake_finding]
                        mock_engine.scan = track_scan
                        return mock_engine

                    mock_validate.side_effect = track_validate
                    mock_extract.side_effect = track_extract
                    mock_engine_class.side_effect = track_engine_init

                    upload_and_scan(
                        filename="test.pdf",
                        data=b"fake pdf content",
                        rules=rules,
                        min_confidence=0.3,
                        hmac_key=hmac_key,
                        storage_dir=temp_storage_dir,
                    )

                    # Verify order
                    assert call_order == ["validate", "extract", "engine_init", "detect"]

    def test_upload_rejected_propagates(self, temp_storage_dir):
        """UploadRejected from validate_upload propagates without saving temp file."""
        rules = [FakeRule()]
        hmac_key = b"test-hmac-key-32-bytes-long-enough!!"

        with patch("securewaste.services.scan_service.validate_upload") as mock_validate:
            mock_validate.side_effect = UploadRejected("FILE_TOO_LARGE")

            with pytest.raises(UploadRejected, match="FILE_TOO_LARGE"):
                upload_and_scan(
                    filename="huge.pdf",
                    data=b"x" * (20 * 1024 * 1024),
                    rules=rules,
                    min_confidence=0.3,
                    hmac_key=hmac_key,
                    storage_dir=temp_storage_dir,
                )

            # No temp file should have been created
            tmp_files = list((temp_storage_dir / "tmp").glob("*"))
            assert len(tmp_files) == 0

    def test_logs_only_counts_and_hashes(
        self, temp_storage_dir, fake_validated_upload, fake_pages, fake_finding, caplog
    ):
        """Logs only finding count and short hashes, never raw values."""
        rules = [FakeRule()]
        hmac_key = b"test-hmac-key-32-bytes-long-enough!!"

        with patch("securewaste.services.scan_service.validate_upload") as mock_validate:
            with patch("securewaste.services.scan_service.extract_pages") as mock_extract:
                with patch("securewaste.services.scan_service.DetectionEngine") as mock_engine_class:
                    mock_validate.return_value = fake_validated_upload
                    mock_extract.return_value = fake_pages
                    mock_engine = MagicMock()
                    mock_engine.scan.return_value = [fake_finding]
                    mock_engine_class.return_value = mock_engine

                    with caplog.at_level("INFO"):
                        upload_and_scan(
                            filename="test.pdf",
                            data=b"fake pdf content",
                            rules=rules,
                            min_confidence=0.3,
                            hmac_key=hmac_key,
                            storage_dir=temp_storage_dir,
                        )

                    # Check log output
                    log_messages = [record.message for record in caplog.records]
                    assert any("1 findings" in msg for msg in log_messages)
                    assert any("a1b2c3d4" in msg for msg in log_messages)  # short hash
                    # Never log raw value
                    for msg in log_messages:
                        assert "j••••@e•••••.com" not in msg or "masked_value" in msg  # masked is ok
                        assert "test@email.com" not in msg  # raw never appears