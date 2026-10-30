"""Generate fictional test files for SecureWaste. Run: python scripts/make_fixtures.py"""

from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def make_fixtures() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)

    texts = [
        "DEMO INVOICE SW-001\nCustomer: Alex Example\nEmail: alex@example.invalid",
        "ITEMS\nService: Security review\nTotal: 900 TND",
        "HR NOTE\nPhone: +216 20 000 000\nSalary: 2500 TND (fictional)",
    ]
    with pymupdf.open() as pdf:
        for text in texts:
            page = pdf.new_page()
            page.insert_text((55, 75), text, fontsize=12)
        pdf.save(FIXTURES / "three_page_invoice.pdf")

    # PDF with only vector graphics and no selectable text.
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.draw_rect(pymupdf.Rect(40, 40, 300, 250), color=(0, 0, 0), fill=(0.8, 0.8, 0.8))
        pdf.save(FIXTURES / "image_only.pdf")

    (FIXTURES / "sample_records.txt").write_text(
        "Employee: Jamie Example\nEmail: jamie@example.invalid\nPhone: +216 20 000 000\nSalary: 2500 TND (fictional)\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    make_fixtures()
    print(f"Synthetic fixtures generated in {FIXTURES}")
