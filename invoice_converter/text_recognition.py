"""Module for text extraction and recognition from PDF documents."""

from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np
import pdfplumber
import pytesseract
from PIL import Image
from rapidfuzz import fuzz


class TextRecognizer:
    """Handles OCR and text extraction from PDF documents."""

    def __init__(self) -> None:
        """Initialize the text recognizer."""
        # Check if tesseract is available
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            print(f"Warning: Tesseract OCR may not be properly installed: {e}")

    def extract_text_from_image(self, image: Image.Image) -> Tuple[str, Dict[str, Any]]:
        """Extract text from an image using OCR.

        Args:
            image: PIL Image to process.

        Returns:
            Tuple of (extracted text, OCR data including confidence)
        """
        # Convert image to numpy array if it's a PIL image
        if isinstance(image, Image.Image):
            # Convert to grayscale if it's not already
            if image.mode != "L":
                image = image.convert("L")
            img_array = np.array(image)
        else:
            img_array = image

        # Apply image preprocessing to improve OCR results
        # Resize if image is too small
        if img_array.shape[0] < 300 or img_array.shape[1] < 300:
            scale_factor = max(300 / img_array.shape[0], 300 / img_array.shape[1])
            new_size = (int(img_array.shape[1] * scale_factor), int(img_array.shape[0] * scale_factor))
            img_array = cv2.resize(img_array, new_size)

        # Apply adaptive thresholding to handle varying lighting
        _, binary = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Use pytesseract to extract text with detailed data
        ocr_data = pytesseract.image_to_data(binary, output_type=pytesseract.Output.DICT)

        # Extract text and calculate average confidence
        text_parts = []
        confidences = []

        for i in range(len(ocr_data["text"])):
            if ocr_data["conf"][i] > 0:  # Filter out low confidence items
                text_parts.append(ocr_data["text"][i])
                confidences.append(float(ocr_data["conf"][i]))

        text = " ".join(text_parts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        # Prepare OCR metadata
        ocr_metadata = {
            "confidence": avg_confidence / 100.0,  # Scale to 0-1
            "word_count": len(text_parts),
            "character_count": len(text),
        }

        return text, ocr_metadata

    def extract_text_from_pdf_region(
        self, pdf_path: str, region: Tuple[float, float, float, float], page_num: int = 0
    ) -> Tuple[str, Dict[str, Any]]:
        """Extract text from a specific region in a PDF.

        Args:
            pdf_path: Path to the PDF file.
            region: Tuple of (x1, y1, x2, y2) in relative coordinates (0-1).
            page_num: Page number (0-indexed).

        Returns:
            Tuple of (extracted text, metadata including confidence)
        """
        with pdfplumber.open(pdf_path) as pdf:
            if page_num >= len(pdf.pages):
                raise ValueError(f"Page {page_num} does not exist in PDF with {len(pdf.pages)} pages")

            page = pdf.pages[page_num]

            # Convert relative coordinates to absolute
            x1, y1, x2, y2 = region
            width, height = page.width, page.height

            abs_x1 = int(x1 * width)
            abs_y1 = int(y1 * height)
            abs_x2 = int(x2 * width)
            abs_y2 = int(y2 * height)

            # Try to extract text directly using pdfplumber
            crop = page.crop((abs_x1, abs_y1, abs_x2, abs_y2))
            text = crop.extract_text() or ""

            # If no text was extracted or confidence is needed, use OCR
            if not text:
                # Convert region to image and use OCR
                img = page.to_image(resolution=300)
                region_img = img.original.crop((abs_x1, abs_y1, abs_x2, abs_y2))
                text, ocr_metadata = self.extract_text_from_image(region_img)
                return text, ocr_metadata

            # For directly extracted text, we don't have confidence metrics
            # but we can assume high confidence since it's from PDF text
            return text, {"confidence": 0.95, "word_count": len(text.split()), "character_count": len(text)}

    def compare_text(self, text1: str, text2: str, use_fuzzy: bool = True) -> float:
        """Compare two text strings and return similarity score.

        Args:
            text1: First text string.
            text2: Second text string.
            use_fuzzy: Whether to use fuzzy matching.

        Returns:
            Similarity score between 0 and 1.
        """
        if not text1 or not text2:
            return 0.0

        if use_fuzzy:
            # Ensure we return a float value
            return float(fuzz.ratio(text1, text2) / 100.0)
        else:
            return 1.0 if text1 == text2 else 0.0


def extract_text(
    pdf_path: str, region: Optional[Tuple[float, float, float, float]] = None, page_num: int = 0
) -> Tuple[str, Dict[str, Any]]:
    """Extract text from a PDF, optionally from a specific region.

    Args:
        pdf_path: Path to the PDF file.
        region: Optional tuple of (x1, y1, x2, y2) in relative coordinates (0-1).
        page_num: Page number (0-indexed).

    Returns:
        Tuple of (extracted text, metadata)
    """
    recognizer = TextRecognizer()

    if region:
        return recognizer.extract_text_from_pdf_region(pdf_path, region, page_num)

    # Extract text from whole page
    with pdfplumber.open(pdf_path) as pdf:
        if page_num >= len(pdf.pages):
            raise ValueError(f"Page {page_num} does not exist")

        page = pdf.pages[page_num]
        text = page.extract_text() or ""

        return text, {
            "confidence": 0.95 if text else 0.0,
            "word_count": len(text.split()),
            "character_count": len(text),
        }
