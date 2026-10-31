#!/usr/bin/env python
"""Generate synthetic test fixtures for SecureWaste.

Creates PDF and TXT files with known sensitive data for testing.
All data is SYNTHETIC - no real personal information.
"""

from __future__ import annotations

import fitz  # PyMuPDF
from pathlib import Path


def create_invoice_pdf() -> bytes:
    """Create a 3-page invoice PDF with synthetic sensitive data.

    Contains:
    - Page 1: Email, phone, CONFIDENTIAL label
    - Page 2: Payment card (Luhn-valid), IBAN
    - Page 3: API key, keyword
    """
    doc = fitz.open()

    # Page 1
    page1 = doc.new_page()
    page1.insert_text((72, 72), "INVOICE", fontsize=24)
    page1.insert_text((72, 120), "Invoice #: INV-2026-001", fontsize=12)
    page1.insert_text((72, 150), "Date: 2026-01-15", fontsize=12)
    page1.insert_text((72, 180), "Bill To:", fontsize=12)
    page1.insert_text((72, 210), "John Doe", fontsize=12)
    page1.insert_text((72, 240), "Email: john.doe@example.com", fontsize=12)
    page1.insert_text((72, 270), "Phone: +44 20 7946 0958", fontsize=12)
    page1.insert_text((72, 300), "CONFIDENTIAL", fontsize=14, color=(1, 0, 0))

    # Page 2
    page2 = doc.new_page()
    page2.insert_text((72, 72), "Payment Details", fontsize=18)
    page2.insert_text((72, 120), "Card: 4242 4242 4242 4242", fontsize=12)
    page2.insert_text((72, 150), "Expires: 12/28", fontsize=12)
    page2.insert_text((72, 180), "IBAN: GB29 NWBK 6016 1331 9268 19", fontsize=12)
    page2.insert_text((72, 210), "SWIFT: NWBKGB2L", fontsize=12)

    # Page 3
    page3 = doc.new_page()
    page3.insert_text((72, 72), "API Configuration", fontsize=18)
    page3.insert_text((72, 120), "AWS Key: AKIAIOSFODNN7EXAMPLE", fontsize=12)
    page3.insert_text((72, 150), "Secret: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", fontsize=12)
    page3.insert_text((72, 180), "Environment: production", fontsize=12)
    page3.insert_text((72, 210), "Note: This contains salary information", fontsize=12)

    # Save to bytes
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_config_txt() -> bytes:
    """Create a TXT file with config leak."""
    return b"""# Application Configuration
DATABASE_URL=postgresql://user:pass@localhost/db
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
STRIPE_API_KEY=test_stripe_key_placeholder
PASSWORD=SuperSecretPassword123
"""


def create_simple_txt() -> bytes:
    """Create a simple TXT file for basic testing."""
    return b"""Hello World

This is a test document.
Contact: test@example.com
Phone: 555-123-4567

CONFIDENTIAL - Do not share
"""


def main():
    """Generate all fixtures."""
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Invoice PDF (3 pages)
    invoice_pdf = create_invoice_pdf()
    (fixtures_dir / "invoice_3page.pdf").write_bytes(invoice_pdf)
    print(f"Created invoice_3page.pdf ({len(invoice_pdf)} bytes)")

    # Config TXT
    config_txt = create_config_txt()
    (fixtures_dir / "config_leak.txt").write_bytes(config_txt)
    print(f"Created config_leak.txt ({len(config_txt)} bytes)")

    # Simple TXT
    simple_txt = create_simple_txt()
    (fixtures_dir / "simple.txt").write_bytes(simple_txt)
    print(f"Created simple.txt ({len(simple_txt)} bytes)")

    print("\nAll fixtures created successfully!")
    print(f"Location: {fixtures_dir}")


if __name__ == "__main__":
    main()