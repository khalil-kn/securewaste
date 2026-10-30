import io
import pytest

from core.upload import validate_upload, UploadError

class FakeFile:
    def __init__(self, filename, content):
        self.filename = filename
        self.stream = io.BytesIO(content)

def test_empty_file():
    file = FakeFile("empty.txt", b"")

    with pytest.raises(UploadError, match="FILE_EMPTY"):
        validate_upload(file)

def test_large_file():
    file = FakeFile("large.txt", b"A" * (11 * 1024 * 1024))

    with pytest.raises(UploadError, match="FILE_TOO_LARGE"):
        validate_upload(file)

def test_renamed_exe():
    file = FakeFile("virus.pdf", b"MZ" + b"\x00" * 100)

    with pytest.raises(UploadError, match="INVALID_FILE_TYPE"):
        validate_upload(file)

def test_invalid_txt():
    file = FakeFile("document.txt", b"\xff\xfe\xff")

    with pytest.raises(UploadError, match="INVALID_FILE_TYPE"):
        validate_upload(file)

def test_valid_txt():
    file = FakeFile("document.txt", b"Hello Secure Waste!")

    result = validate_upload(file)

    assert result["extension"] == ".txt"
    assert result["filename"].endswith(".txt")
    assert len(result["fingerprint"]) == 64

def test_unsupported_extension():
    file = FakeFile("image.png", b"some content")

    with pytest.raises(UploadError, match="INVALID_FILE_TYPE"):
        validate_upload(file)