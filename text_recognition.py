"""Module for extracting and processing text from PDF documents."""

import logging
import os
from typing import Any

import pdfplumber

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def extract_text_from_page(page: Any) -> str:
    """Extract text from a PDF page.

    Args:
        page: pdfplumber page object

    Returns:
        Extracted text as a string
    """
    text = page.extract_text() or ""
    logger.info(f"Extracted {len(text)} characters")
    return text


def extract_text_from_pdf(pdf_path: str) -> list[str]:
    """Extract text from all pages of a PDF.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of text strings, one for each page
    """
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file does not exist: {pdf_path}")
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    logger.info(f"Extracting text from PDF: {pdf_path}")

    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            logger.info(f"Processing page {i+1}/{len(pdf.pages)}")
            text = extract_text_from_page(page)
            pages_text.append(text)

    return pages_text


def save_page_snippet(page_num: int, text: str, matches: bool, output_dir: str) -> None:
    """Save a snippet of the page text to a file for later analysis.

    Args:
        page_num: Page number
        text: Text content of the page
        matches: Whether the page matches the template
        output_dir: Directory to save snippets to
    """
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Define the snippet file name
    result_type = "match" if matches else "nomatch"
    snippet_file = os.path.join(output_dir, f"page_{page_num:03d}_{result_type}.txt")

    # Take a snippet of the text (first 1000 chars) and save it
    snippet = text[:1000] if len(text) > 1000 else text

    with open(snippet_file, "w") as f:
        f.write(f"Page {page_num} - {'MATCH' if matches else 'NO MATCH'}\n")
        f.write("-" * 40 + "\n")
        f.write(snippet)

        # Also save positional diagnostic information
        f.write("\n\n" + "-" * 40 + "\n")
        f.write("POSITIONAL DIAGNOSTICS\n")

        # Identify line starts for the first 20 lines
        lines = text.split("\n")[:20]
        f.write("\nLine positions (first 20 lines):\n")
        for i, line in enumerate(lines):
            if line.strip():
                f.write(f"Line {i+1}: '{line[:30]}{'...' if len(line) > 30 else ''}'\n")

        # Look for key landmark positions
        landmarks = ["Site Name #", "Bill To", "Customer ID", "Service Period", "Invoice #"]
        f.write("\nKey landmark positions:\n")
        for landmark in landmarks:
            if landmark in text:
                # Find the line containing the landmark
                for i, line in enumerate(text.split("\n")):
                    if landmark in line:
                        f.write(f"{landmark}: Found on line {i+1}, position {line.find(landmark)}\n")
                        f.write(f"  Line content: '{line[:50]}{'...' if len(line) > 50 else ''}'\n")
                        break

    logger.info(f"Saved enhanced snippet to {snippet_file}")
