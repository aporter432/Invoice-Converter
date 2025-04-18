"""Module for analyzing the layout of invoices."""

from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np
import pdfplumber

from invoice_converter.field_recognition import FieldRecognizer


class LayoutAnalyzer:
    """Analyzes and compares invoice layouts with template."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the layout analyzer.

        Args:
            config_path: Path to pyproject.toml containing configuration.
        """
        self.field_recognizer = FieldRecognizer(config_path)
        self.template_path = self.field_recognizer.template_path
        self.template_fingerprint = None

    def _extract_layout_fingerprint(self, pdf_path: str) -> np.ndarray:
        """Extract a layout fingerprint from a PDF.

        This creates a simplified representation of the document layout
        that can be used for comparison.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Numpy array representing the layout fingerprint.
        """
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) < 1:
                raise ValueError("PDF has no pages")

            page = pdf.pages[0]  # Assume first page

            # Get page image
            img = page.to_image()
            pil_img = img.original

            # Convert to grayscale
            gray_img = pil_img.convert("L")

            # Convert to numpy array
            np_img = np.array(gray_img)

            # Apply threshold to get binary image
            _, binary = cv2.threshold(np_img, 200, 255, cv2.THRESH_BINARY_INV)

            # Resize to standard dimensions for comparison
            resized = cv2.resize(binary, (100, 150))

            return resized

    def get_template_fingerprint(self) -> np.ndarray:
        """Get the fingerprint of the template document.

        Returns:
            Numpy array representing the template fingerprint.
        """
        if self.template_fingerprint is None:
            self.template_fingerprint = self._extract_layout_fingerprint(self.template_path)
        return self.template_fingerprint

    def compare_layout(self, pdf_path: str) -> Tuple[float, Dict[str, Any]]:
        """Compare a PDF layout with the template.

        Args:
            pdf_path: Path to the PDF to compare.

        Returns:
            Tuple of (similarity_score, details)
        """
        # Get template fingerprint
        template_fp = self.get_template_fingerprint()

        # Get document fingerprint
        doc_fp = self._extract_layout_fingerprint(pdf_path)

        # Compare fingerprints using structural similarity
        # For simplicity, we'll use a normalized L2 distance here
        diff = np.linalg.norm(template_fp.astype(float) - doc_fp.astype(float))
        max_diff = np.sqrt(template_fp.size) * 255  # Maximum possible difference
        similarity = 1.0 - (diff / max_diff)

        # Get field recognition results for additional context
        is_match, field_similarity, field_details = self.field_recognizer.compare_with_template(pdf_path)

        details = {"field_similarity": field_similarity, "field_details": field_details, "field_match": is_match}

        return similarity, details

    def analyze_document(self, pdf_path: str) -> Dict[str, Any]:
        """Analyze a document and compare with template.

        Args:
            pdf_path: Path to the PDF to analyze.

        Returns:
            Dict containing analysis results.
        """
        layout_similarity, details = self.compare_layout(pdf_path)

        return {
            "pdf_path": pdf_path,
            "layout_similarity": layout_similarity,
            "is_similar_layout": layout_similarity > 0.8,  # Threshold can be adjusted
            "field_similarity": details["field_similarity"],
            "is_similar_content": details["field_match"],
            "field_details": details["field_details"],
        }


def analyze_layout(pdf_path: str, config_path: Optional[str] = None) -> Dict[str, Any]:
    """Analyze the layout of a PDF document.

    Args:
        pdf_path: Path to the PDF file.
        config_path: Path to configuration file.

    Returns:
        Dict containing analysis results.
    """
    analyzer = LayoutAnalyzer(config_path)
    return analyzer.analyze_document(pdf_path)
