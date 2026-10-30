"""End-to-end test for upload -> scan -> results flow.

This test is marked xfail because it needs teammates' implementations:
- #3 (upload validation)
- #4 (extraction)
- #5 (detection engine)

Once those are merged, remove the xfail and use B's real fixture.
"""

import io
import pytest
from pathlib import Path


@pytest.mark.xfail(reason="needs #3 #4 #5", strict=False)
def test_upload_scan_results_flow(client, tmp_path):
    """Full integration test: upload B's fake 3-page invoice PDF, check masked findings appear, real email never appears."""
    # This test will use B's fixture from tests/fixtures/invoice_3page.pdf
    # Once #3, #4, #5 are merged, the fixture will exist and the test will pass.

    fixture_path = Path(__file__).parents[1] / "fixtures" / "invoice_3page.pdf"

    # For now, the fixture doesn't exist - this is expected to fail
    assert fixture_path.exists(), "Fixture not yet created by teammate B (issue #4)"

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
    assert "j••••@e•••••.com" in html or "••••@•••••.com" in html  # masked email
    assert "+44 •••• ••••••" in html or "•••• ••••••" in html  # masked phone

    # CRITICAL: Real email must NEVER appear in the page
    assert "john.doe@example.com" not in html
    assert "jane.smith@company.org" not in html

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