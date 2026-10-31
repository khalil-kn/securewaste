"""End-to-end test for upload -> scan -> results flow.

Tests the complete flow: upload -> validate -> extract -> detect -> results page.
"""

import io
import pytest
from pathlib import Path


def test_upload_scan_results_flow(client, tmp_path):
    """Full integration test: upload 3-page invoice PDF, check masked findings appear, real email never appears."""
    fixture_path = Path(__file__).parents[1] / "fixtures" / "invoice_3page.pdf"

    # Ensure fixture exists
    assert fixture_path.exists(), f"Fixture not found at {fixture_path}. Run scripts/make_fixtures.py"

    with open(fixture_path, "rb") as f:
        pdf_data = f.read()

    # Upload the file
    response = client.post(
        "/documents",
        data={"file": (io.BytesIO(pdf_data), "invoice_3page.pdf")},
        content_type="multipart/form-data",
    )

    # Should render results page successfully
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Check the file name is displayed
    assert "invoice_3page.pdf" in html

    # Check that masked findings appear (no raw values)
    # Email: j••••@e•••••.com
    assert "j••••@e•••••.com" in html or "j•••@e•••••.com" in html

    # Phone: +44 •••• ••••••
    assert "+44 ••••" in html or "•••• ••••••" in html

    # Payment card: •••• •••• •••• 4242
    assert "•••• •••• •••• 4242" in html

    # IBAN: masked
    assert "•••• •••• •••• ••••" in html

    # Secret: AKIA••••••••
    assert "AKIA••••" in html

    # Keyword: CONFIDENTIAL (shown as-is)
    assert "CONFIDENTIAL" in html

    # CRITICAL: Real email must NEVER appear in the page
    assert "john.doe@example.com" not in html
    assert "jane.smith@company.org" not in html

    # Real phone must NEVER appear
    assert "+44 20 7946 0958" not in html

    # Real card must NEVER appear
    assert "4242 4242 4242 4242" not in html

    # Real IBAN must NEVER appear
    assert "GB29 NWBK 6016 1331 9268 19" not in html

    # Real secret must NEVER appear
    assert "AKIAIOSFODNN7EXAMPLE" not in html

    # Check findings table structure
    assert "Findings:" in html
    assert "Category" in html
    assert "Masked Value" in html
    assert "Page" in html
    assert "Occurrences" in html
    assert "Severity" in html
    assert "Status" in html

    # Check severity meters and status pills
    assert "Needs review" in html
    assert "sw-severity-meter" in html
    assert "sw-status-pill" in html


def test_upload_txt_file(client):
    """Test uploading a TXT file."""
    fixture_path = Path(__file__).parents[1] / "fixtures" / "simple.txt"

    assert fixture_path.exists(), f"Fixture not found at {fixture_path}"

    with open(fixture_path, "rb") as f:
        txt_data = f.read()

    response = client.post(
        "/documents",
        data={"file": (io.BytesIO(txt_data), "simple.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "simple.txt" in html
    # Email and phone should be found
    assert "t•••@e•••.com" in html or "•••@•••.com" in html


def test_upload_empty_file_rejected(client):
    """Empty file should be rejected."""
    response = client.post(
        "/documents",
        data={"file": (io.BytesIO(b""), "empty.pdf")},
        content_type="multipart/form-data",
    )

    # Should show error page
    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert "EMPTY_FILE" in html or "empty" in html.lower()


def test_upload_exe_as_pdf_rejected(client):
    """.exe file renamed to .pdf should be rejected."""
    exe_data = b"MZ\x90\x00" + b"x" * 100  # PE header

    response = client.post(
        "/documents",
        data={"file": (io.BytesIO(exe_data), "malicious.pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert "UNSUPPORTED_TYPE" in html or "unsupported" in html.lower()