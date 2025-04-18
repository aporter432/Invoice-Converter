"""Convert PDF invoice packages by updating with new format invoices."""

import argparse
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, cast

import pdfplumber
import pytesseract
from pdfrw import PdfReader, PdfWriter
from PIL import Image

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


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
    logger.info(f"Created temporary PDF for OCR at {temp_pdf}")

    # Now open with pdfplumber and process
    try:
        with pdfplumber.open(temp_pdf) as pdf:
            logger.info(f"Opened temporary PDF with {len(pdf.pages)} pages")
            pdf_page = pdf.pages[0]
            im = pdf_page.to_image()
            im.save("temp.png")
            logger.info("Saved page image for OCR")
            text = pytesseract.image_to_string(Image.open("temp.png"))
            logger.info(f"OCR extracted {len(text)} characters of text")
            return cast(str, text)
    except Exception as e:
        logger.error(f"Error during OCR processing: {e}")
        raise
    finally:
        # Clean up temporary files
        if os.path.exists(temp_pdf):
            os.remove(temp_pdf)
            logger.info(f"Removed temporary PDF: {temp_pdf}")
        if os.path.exists("temp.png"):
            os.remove("temp.png")
            logger.info("Removed temporary image")


def extract_invoice_number(text: str) -> Optional[str]:
    """Extract invoice number from text.

    Args:
        text: Text to search for invoice number

    Returns:
        Invoice number if found, None otherwise
    """
    match = re.search(r"Invoice #\s*(\d+)", text)
    result = match.group(1) if match else None
    logger.info(f"Extracted invoice number: {result}")
    return result


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
    result = all(marker in text for marker in markers)
    logger.info(f"Invoice format check: {'new' if result else 'old'} format")
    return result


def update_pdf_package(existing_pdf: str, new_invoices_dir: str, output_pdf: str) -> None:
    """Update PDF package by replacing old format invoices with new ones.

    Args:
        existing_pdf: Path to existing PDF package
        new_invoices_dir: Directory containing new invoice PDFs
        output_pdf: Path to save the updated PDF package
    """
    # Create new_invoices_dir if it doesn't exist
    if not os.path.exists(new_invoices_dir):
        os.makedirs(new_invoices_dir)
        logger.info(f"Created directory: {new_invoices_dir}")

    # Check if existing PDF exists
    if not os.path.exists(existing_pdf):
        logger.error(f"Input PDF file does not exist: {existing_pdf}")
        raise FileNotFoundError(f"Input PDF not found: {existing_pdf}")

    logger.info(f"Processing existing PDF: {existing_pdf}")

    # Read the existing PDF
    existing_reader = PdfReader(existing_pdf)
    existing_pages = existing_reader.pages

    logger.info(f"Input PDF has {len(existing_pages)} pages")
    if not existing_pages:
        logger.error("Input PDF has no pages!")
        raise ValueError("Input PDF has no pages")

    # Group pages into invoices
    invoice_groups: List[Dict[str, Any]] = []
    current_invoice: Optional[Dict[str, Any]] = None
    for i, page in enumerate(existing_pages):
        logger.info(f"Processing page {i+1}/{len(existing_pages)}")
        # Use OCR to get text from the page
        text = ocr_page(page)
        if "Service Invoice" in text:
            invoice_number = extract_invoice_number(text)
            if invoice_number:
                if current_invoice:
                    invoice_groups.append(current_invoice)
                    logger.info(f"Completed invoice group with {len(current_invoice['pages'])} pages")
                current_invoice = {"number": invoice_number, "pages": [i]}
                logger.info(f"Found new invoice: #{invoice_number} starting at page {i+1}")
            elif current_invoice:
                current_invoice["pages"].append(i)
                logger.info(f"Added page {i+1} to current invoice #{current_invoice['number']}")
        elif current_invoice:
            current_invoice["pages"].append(i)
            logger.info(f"Added page {i+1} to current invoice #{current_invoice['number']}")
    if current_invoice:
        invoice_groups.append(current_invoice)
        logger.info(f"Completed final invoice group with {len(current_invoice['pages'])} pages")

    logger.info(f"Found {len(invoice_groups)} invoices in the PDF")

    # Determine which invoices to replace
    replace_dict: Dict[str, str] = {}
    for invoice in invoice_groups:
        # Combine text from all pages of the invoice
        pages_indices = invoice["pages"]
        logger.info(f"Processing invoice #{invoice['number']} with {len(pages_indices)} pages")
        page_texts = [ocr_page(existing_pages[p]) for p in pages_indices]
        invoice_text = " ".join(page_texts)
        if not is_new_format(invoice_text):
            new_path = os.path.join(new_invoices_dir, f"{invoice['number']}.pdf")
            if os.path.exists(new_path):
                replace_dict[invoice["number"]] = new_path
                logger.info(f"Will replace invoice #{invoice['number']} with {new_path}")

    # Find new invoices to append
    existing_numbers: Set[str] = {invoice["number"] for invoice in invoice_groups}
    logger.info(f"Existing invoice numbers: {existing_numbers}")

    new_invoice_files = [f for f in os.listdir(new_invoices_dir) if f.endswith(".pdf")]
    logger.info(f"Found {len(new_invoice_files)} files in new invoices directory")

    new_invoices_to_add = [
        os.path.join(new_invoices_dir, f) for f in new_invoice_files if f[:-4] not in existing_numbers
    ]
    logger.info(f"Will add {len(new_invoices_to_add)} new invoices: {new_invoices_to_add}")

    # Construct the new PDF
    logger.info("Creating new PDF package")
    writer = PdfWriter()
    pages_added = 0

    for invoice in invoice_groups:
        if invoice["number"] in replace_dict:
            # Replace with pages from new invoice
            new_path = replace_dict[invoice["number"]]
            logger.info(f"Adding replacement invoice from {new_path}")
            try:
                new_reader = PdfReader(new_path)
                logger.info(f"Replacement invoice has {len(new_reader.pages)} pages")
                for page in new_reader.pages:
                    writer.addpage(page)
                    pages_added += 1
            except Exception as e:
                logger.error(f"Error adding replacement invoice: {e}")
        else:
            # Keep original pages
            logger.info(f"Keeping original invoice #{invoice['number']}")
            for page_num in invoice["pages"]:
                writer.addpage(existing_pages[page_num])
                pages_added += 1

    # Append new invoices
    for new_invoice_path in new_invoices_to_add:
        logger.info(f"Adding new invoice from {new_invoice_path}")
        try:
            new_reader = PdfReader(new_invoice_path)
            logger.info(f"New invoice has {len(new_reader.pages)} pages")
            for page in new_reader.pages:
                writer.addpage(page)
                pages_added += 1
        except Exception as e:
            logger.error(f"Error adding new invoice: {e}")

    logger.info(f"Total pages in output PDF: {pages_added}")
    if pages_added == 0:
        logger.error("No pages were added to the output PDF!")
        raise ValueError("Failed to add any pages to the output PDF")

    # Save the updated PDF
    output_dir = os.path.dirname(os.path.abspath(output_pdf))
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created output directory: {output_dir}")

    logger.info(f"Writing output PDF to {output_pdf}")
    with open(output_pdf, "wb") as f:
        writer.write(f)

    # Verify the output file
    if os.path.exists(output_pdf):
        try:
            verification_reader = PdfReader(output_pdf)
            logger.info(f"Output PDF created successfully with {len(verification_reader.pages)} pages")
        except Exception as e:
            logger.error(f"Error verifying output PDF: {e}")
    else:
        logger.error("Failed to create output PDF!")


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

    logger.info("Starting PDF invoice package update")
    logger.info(f"Input PDF: {args.existing}")
    logger.info(f"New invoices directory: {args.new_dir}")
    logger.info(f"Output PDF: {args.output}")

    # Run the update
    try:
        update_pdf_package(args.existing, args.new_dir, args.output)
        logger.info(f"Updated PDF package saved to {args.output}")
    except Exception as e:
        logger.error(f"Error updating PDF package: {e}")
        raise


if __name__ == "__main__":
    main()
