"""Convert PDF invoice packages by updating with new format invoices."""

import argparse
import os
import re
from typing import Any, Dict, List, Optional, Set, cast

import pdfplumber
import pytesseract
from pdfrw import PdfReader, PdfWriter
from PIL import Image


def ocr_page(page: Any) -> str:
    """Perform OCR on a PDF page.

    Args:
        page: PDF page to extract text from

    Returns:
        Extracted text from the page
    """
    # Create a temporary PDF with just this page
    temp_pdf = "temp_page.pdf"
    writer = PdfWriter()
    writer.addpage(page)
    writer.write(temp_pdf)

    # Now open with pdfplumber and process
    try:
        with pdfplumber.open(temp_pdf) as pdf:
            pdf_page = pdf.pages[0]
            im = pdf_page.to_image()
            im.save("temp.png")
            text = pytesseract.image_to_string(Image.open("temp.png"))
            return cast(str, text)
    finally:
        # Clean up temporary files
        if os.path.exists(temp_pdf):
            os.remove(temp_pdf)
        if os.path.exists("temp.png"):
            os.remove("temp.png")


def extract_invoice_number(text: str) -> Optional[str]:
    """Extract invoice number from text.

    Args:
        text: Text to search for invoice number

    Returns:
        Invoice number if found, None otherwise
    """
    match = re.search(r"Invoice #\s*(\d+)", text)
    return match.group(1) if match else None


def is_new_format(text: str) -> bool:
    """Check if an invoice is in the new format.

    Args:
        text: Text content of the invoice

    Returns:
        True if invoice is in new format, False otherwise
    """
    # Check for table headers indicating the new format
    markers = [
        "Site Name #",
        "Item",
        "Qty",
        "Rate",
        "Description",
        "Subtotal",
        "Tax Rate",
    ]
    return all(marker in text for marker in markers)


def update_pdf_package(existing_pdf: str, new_invoices_dir: str, output_pdf: str) -> None:
    """Update PDF package by replacing old format invoices with new ones.

    Args:
        existing_pdf: Path to existing PDF package
        new_invoices_dir: Directory containing new invoice PDFs
        output_pdf: Path to save the updated PDF package
    """
    # Read the existing PDF
    existing_reader = PdfReader(existing_pdf)
    existing_pages = existing_reader.pages

    # Group pages into invoices
    invoice_groups: List[Dict[str, Any]] = []
    current_invoice: Optional[Dict[str, Any]] = None
    for i, page in enumerate(existing_pages):
        # Use OCR to get text from the page
        text = ocr_page(page)
        if "Service Invoice" in text:
            invoice_number = extract_invoice_number(text)
            if invoice_number:
                if current_invoice:
                    invoice_groups.append(current_invoice)
                current_invoice = {"number": invoice_number, "pages": [i]}
            elif current_invoice:
                current_invoice["pages"].append(i)
        elif current_invoice:
            current_invoice["pages"].append(i)
    if current_invoice:
        invoice_groups.append(current_invoice)

    # Determine which invoices to replace
    replace_dict: Dict[str, str] = {}
    for invoice in invoice_groups:
        # Combine text from all pages of the invoice
        pages_indices = invoice["pages"]
        page_texts = [ocr_page(existing_pages[p]) for p in pages_indices]
        invoice_text = " ".join(page_texts)
        if not is_new_format(invoice_text):
            new_path = os.path.join(new_invoices_dir, f"{invoice['number']}.pdf")
            if os.path.exists(new_path):
                replace_dict[invoice["number"]] = new_path

    # Find new invoices to append
    existing_numbers: Set[str] = {invoice["number"] for invoice in invoice_groups}
    new_invoices_to_add = [
        os.path.join(new_invoices_dir, f)
        for f in os.listdir(new_invoices_dir)
        if f.endswith(".pdf") and f[:-4] not in existing_numbers
    ]

    # Construct the new PDF
    writer = PdfWriter()
    for invoice in invoice_groups:
        if invoice["number"] in replace_dict:
            # Replace with pages from new invoice
            new_reader = PdfReader(replace_dict[invoice["number"]])
            for page in new_reader.pages:
                writer.addpage(page)
        else:
            # Keep original pages
            for page_num in invoice["pages"]:
                writer.addpage(existing_pages[page_num])

    # Append new invoices
    for new_invoice_path in new_invoices_to_add:
        new_reader = PdfReader(new_invoice_path)
        for page in new_reader.pages:
            writer.addpage(page)

    # Save the updated PDF
    with open(output_pdf, "wb") as f:
        writer.write(f)


def main() -> None:
    """Process invoice PDFs and generate updated package."""
    parser = argparse.ArgumentParser(description="Update PDF invoice packages")
    parser.add_argument(
        "--existing",
        default="/Users/aaronporter/Desktop/R6 invoices/PNW Open Invoices - unrevised.pdf",
        help="Existing PDF file path",
    )
    parser.add_argument(
        "--new-dir",
        default="/Users/aaronporter/Desktop/R6 invoices/new_invoices",
        help="Directory with new invoice PDFs",
    )
    parser.add_argument(
        "--output",
        default="/Users/aaronporter/Desktop/R6 invoices/PNW Open Invoices - updated.pdf",
        help="Output PDF file path",
    )

    args = parser.parse_args()

    # Run the update
    update_pdf_package(args.existing, args.new_dir, args.output)
    print(f"Updated PDF package saved to {args.output}")


if __name__ == "__main__":
    main()
